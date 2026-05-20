import os
import json
import hashlib
import logging
from datetime import datetime, date
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie

from mempalace.config import MempalaceConfig
from mempalace.palace import get_collection
from mempalace.searcher import search_memories
from mempalace.knowledge_graph import KnowledgeGraph
from mempalace.backends.chroma import hnsw_capacity_status

logger = logging.getLogger(__name__)

# Initialize MemPalace Config
config = MempalaceConfig()
PALACE_PATH = config.palace_path

def get_palace_collection(create=True):
    """Safely get or create the ChromaDB collection."""
    os.makedirs(PALACE_PATH, exist_ok=True)
    try:
        return get_collection(PALACE_PATH, create=create)
    except Exception as e:
        logger.error(f"Error getting collection: {e}")
        return None

def get_kg_instance():
    """Get the Knowledge Graph connection."""
    os.makedirs(PALACE_PATH, exist_ok=True)
    db_path = os.path.join(PALACE_PATH, "knowledge_graph.sqlite3")
    return KnowledgeGraph(db_path=db_path)

@ensure_csrf_cookie
def dashboard(request):
    """Render the main memory palace dashboard."""
    # Ensure palace directory exists
    os.makedirs(PALACE_PATH, exist_ok=True)
    
    # Pre-calculate simple stats for initial page load
    col = get_palace_collection(create=True)
    total_drawers = 0
    wings = {}
    rooms = {}
    
    if col:
        try:
            total_drawers = col.count()
            # Fetch all metadata to extract unique wings/rooms
            # col.get() with include=['metadatas']
            res = col.get(include=['metadatas'])
            for meta in (res.metadatas or []):
                if meta:
                    w = meta.get('wing', 'unknown')
                    r = meta.get('room', 'unknown')
                    wings[w] = wings.get(w, 0) + 1
                    rooms[r] = rooms.get(r, 0) + 1
        except Exception as e:
            logger.error(f"Failed to load dashboard stats: {e}")

    # Knowledge Graph stats
    kg_entities_count = 0
    kg_triples_count = 0
    try:
        kg = get_kg_instance()
        stats = kg.stats()
        kg_entities_count = stats.get('entities', 0)
        kg_triples_count = stats.get('triples', 0)
    except Exception as e:
        logger.error(f"Failed to load KG stats: {e}")

    # Vector status
    vec_status = "unknown"
    try:
        cap = hnsw_capacity_status(PALACE_PATH)
        vec_status = cap.get('status', 'unknown')
    except Exception:
        pass

    context = {
        'total_drawers': total_drawers,
        'wings': wings,
        'rooms': rooms,
        'kg_entities': kg_entities_count,
        'kg_triples': kg_triples_count,
        'vector_status': vec_status,
        'palace_path': PALACE_PATH,
    }
    return render(request, 'memory/index.html', context)

@require_http_methods(["GET"])
def search_api(request):
    """Semantic and hybrid search API."""
    query = request.GET.get('query', '').strip()
    wing = request.GET.get('wing', '').strip() or None
    room = request.GET.get('room', '').strip() or None
    strategy = request.GET.get('strategy', 'vector').strip()
    limit = int(request.GET.get('limit', 10))

    if not query:
        return JsonResponse({'error': 'Query parameter is required'}, status=400)

    # Validate strategy
    if strategy not in ['vector', 'union']:
        strategy = 'vector'

    try:
        # Check capacity / disabled status
        cap = hnsw_capacity_status(PALACE_PATH)
        vector_disabled = cap.get('status') == 'diverged'

        results = search_memories(
            query=query,
            palace_path=PALACE_PATH,
            wing=wing,
            room=room,
            n_results=limit,
            vector_disabled=vector_disabled,
            candidate_strategy=strategy
        )
        return JsonResponse(results)
    except Exception as e:
        logger.exception("Search failed")
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["POST"])
def add_memory_api(request):
    """File new verbatim content into a wing/room with duplicate detection."""
    try:
        data = json.loads(request.body)
        wing = data.get('wing', '').strip()
        room = data.get('room', '').strip()
        content = data.get('content', '').strip()
        source_file = data.get('source_file', '').strip() or None
        force = data.get('force', False)

        if not wing or not room or not content:
            return JsonResponse({'error': 'Wing, Room, and Content are required'}, status=400)

        col = get_palace_collection(create=True)
        if not col:
            return JsonResponse({'error': 'Could not open Memory Palace collection'}, status=500)

        # 1. Duplicate detection check
        if not force:
            try:
                # Query nearest matching documents to check cosine similarity
                res = col.query(
                    query_texts=[content],
                    n_results=1,
                    include=["metadatas", "documents", "distances"]
                )
                if res.ids and res.ids[0]:
                    dist = res.distances[0][0]
                    similarity = 1 - dist
                    if similarity >= 0.9:
                        existing_meta = res.metadatas[0][0] or {}
                        return JsonResponse({
                            'duplicate': True,
                            'similarity': round(similarity, 3),
                            'existing': {
                                'id': res.ids[0][0],
                                'wing': existing_meta.get('wing', 'unknown'),
                                'room': existing_meta.get('room', 'unknown'),
                                'content': res.documents[0][0][:200]
                            }
                        })
            except Exception as e:
                logger.error(f"Duplicate detection failed: {e}")

        # 2. Perform insert
        drawer_id = f"drawer_{wing}_{room}_{hashlib.sha256((wing + room + content).encode()).hexdigest()[:24]}"
        
        col.upsert(
            ids=[drawer_id],
            documents=[content],
            metadatas=[{
                "wing": wing,
                "room": room,
                "source_file": source_file or "",
                "chunk_index": 0,
                "added_by": "django_app",
                "filed_at": datetime.now().isoformat()
            }]
        )

        return JsonResponse({
            'success': True,
            'drawer_id': drawer_id,
            'wing': wing,
            'room': room
        })

    except Exception as e:
        logger.exception("Filing memory failed")
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def kg_query_api(request):
    """Query knowledge graph relationships for a given entity."""
    entity = request.GET.get('entity', '').strip()
    direction = request.GET.get('direction', 'both').strip()
    as_of = request.GET.get('as_of', '').strip() or None

    if not entity:
        return JsonResponse({'error': 'Entity name is required'}, status=400)

    if direction not in ['outgoing', 'incoming', 'both']:
        direction = 'both'

    try:
        kg = get_kg_instance()
        results = kg.query_entity(entity, as_of=as_of, direction=direction)
        return JsonResponse({
            'entity': entity,
            'direction': direction,
            'facts': results,
            'count': len(results)
        })
    except Exception as e:
        logger.exception("KG query failed")
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["POST"])
def kg_add_api(request):
    """Add a relationship triple to the knowledge graph."""
    try:
        data = json.loads(request.body)
        subject = data.get('subject', '').strip()
        predicate = data.get('predicate', '').strip()
        obj = data.get('object', '').strip()
        valid_from = data.get('valid_from', '').strip() or None
        valid_to = data.get('valid_to', '').strip() or None
        source_drawer_id = data.get('source_drawer_id', '').strip() or None

        if not subject or not predicate or not obj:
            return JsonResponse({'error': 'Subject, Predicate, and Object are required'}, status=400)

        kg = get_kg_instance()
        triple_id = kg.add_triple(
            subject=subject,
            predicate=predicate,
            obj=obj,
            valid_from=valid_from,
            valid_to=valid_to,
            source_closet=None,
            source_file=None,
            source_drawer_id=source_drawer_id
        )

        return JsonResponse({
            'success': True,
            'triple_id': triple_id,
            'fact': f"{subject} → {predicate} → {obj}"
        })
    except Exception as e:
        logger.exception("KG add failed")
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["POST"])
def kg_invalidate_api(request):
    """Invalidate a fact in the knowledge graph."""
    try:
        data = json.loads(request.body)
        subject = data.get('subject', '').strip()
        predicate = data.get('predicate', '').strip()
        obj = data.get('object', '').strip()
        ended = data.get('ended', '').strip() or date.today().isoformat()

        if not subject or not predicate or not obj:
            return JsonResponse({'error': 'Subject, Predicate, and Object are required'}, status=400)

        kg = get_kg_instance()
        kg.invalidate(subject, predicate, obj, ended=ended)

        return JsonResponse({
            'success': True,
            'fact': f"{subject} → {predicate} → {obj}",
            'ended': ended
        })
    except Exception as e:
        logger.exception("KG invalidate failed")
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def kg_stats_api(request):
    """Fetch Knowledge Graph overall stats."""
    try:
        kg = get_kg_instance()
        stats = kg.stats()
        return JsonResponse(stats)
    except Exception as e:
        logger.exception("KG stats retrieval failed")
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["GET"])
def kg_timeline_api(request):
    """Retrieve chronological timeline of facts in the knowledge graph."""
    entity = request.GET.get('entity', '').strip() or None
    try:
        kg = get_kg_instance()
        timeline = kg.timeline(entity)
        return JsonResponse({
            'entity': entity or 'all',
            'timeline': timeline,
            'count': len(timeline)
        })
    except Exception as e:
        logger.exception("KG timeline failed")
        return JsonResponse({'error': str(e)}, status=500)
