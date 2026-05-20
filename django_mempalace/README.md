# MemPalace Django Web Dashboard

A beautiful, containerized Django web application that wraps the **MemPalace** cognitive storage engine. This dashboard exposes a sleek glassmorphic user interface to query, write, and explore semantic memories (using ChromaDB vector index) and trace temporal entity relationships (using an SQLite-backed Knowledge Graph).

---

## Features

- 🧠 **Memory Palace Panel**: Semantic & hybrid search (combining HNSW vector distance and Okapi-BM25 text scoring) with dynamic filters for Wings and Rooms.
- ✍️ **Filing Drawers**: Write verbatim memories with a built-in semantic duplicate detection pre-check.
- 🕸️ **Knowledge Graph Explorer**: Explorer for entity relationship triples, outgoing/incoming graph traversal, fact invalidation, and a global chronological timeline audit log.
- 🩺 **Diagnostics Board**: Real-time HNSW element check and SQLite stats.
- 🐳 **Fully Dockerized**: Easily runnable locally and pre-configured for a zero-downtime persistent deployment on Render.

---

## Local Setup & Run

### Prerequisites
- Docker and Docker Compose installed on your system.

### Build and Run with Docker
1. Clone the repository and navigate to the project directory:
   ```bash
   cd django_mempalace
   ```
2. Build the Docker image:
   ```bash
   docker build -t django-mempalace .
   ```
3. Run the container:
   ```bash
   docker run -p 8000:8000 -e SECRET_KEY="your-secret-key" -e DEBUG="True" django-mempalace
   ```
4. Access the web dashboard at: `http://localhost:8000/`

---

## Deploying on Render (Web Service)

This application is designed to be deployed directly as a Render Web Service without requiring blueprints. Because MemPalace writes databases locally, you **must mount a persistent disk** so your memories and knowledge graph connections survive redeployments.

### Step-by-Step Render Setup

1. **Create a Web Service**:
   - Log in to your [Render Dashboard](https://dashboard.render.com/).
   - Click **New +** and select **Web Service**.
   - Connect your GitHub repository containing the files (point it to `django_mempalace/` as the root directory, or keep root if the workspace is structured that way).

2. **Configure Service Settings**:
   - **Name**: `mempalace-dashboard`
   - **Environment**: `Docker` (Render will detect the `Dockerfile` in the root).
   - **Instance Type**: Select your preferred tier (Free or Starter).

3. **Add Environment Variables**:
   Under the **Environment** tab of your service, add the following variables:
   - `SECRET_KEY` : *A long random string for Django security.*
   - `DEBUG` : `False` *(Enables production mode)*
   - `ALLOWED_HOSTS` : `*` or your custom Render URL (e.g. `mempalace.onrender.com`).
   - `MEMPALACE_PALACE_PATH` : `/data/.mempalace/palace` *(Forces ChromaDB segment indexes to write to the persistent mount)*
   - `HOME` : `/data` *(Forces SQLite databases and default config folders to reside on the persistent disk)*

4. **Attach a Persistent Disk**:
   - Navigate to the **Disks** section in the service settings.
   - Click **Add Disk**.
   - **Name**: `mempalace-data`
   - **Mount Path**: `/data`
   - **Size**: `1 GB` (or larger, depending on your database volume).
   - Click **Save**.

5. **Deploy**:
   - Render will start building the Docker image using the `Dockerfile` and boot the server using `start.sh` (which executes migrations, compiles static assets, and launches the production Gunicorn server).
   - Once completed, visit your `.onrender.com` URL to access your private cognitive memory database!

---

## Technical Architecture

- **ChromaDB Path Redirection**: By setting `HOME=/data`, the default database paths redirect from `~/.mempalace/` to `/data/.mempalace/`. This keeps SQLite (`/data/.mempalace/knowledge_graph.sqlite3`) and ChromaDB vector files securely mounted to the Render persistent disk.
- **Server Gateway**: Gunicorn runs the server with production optimizations, handling traffic routing securely.
