from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('api/search/', views.search_api, name='search_api'),
    path('api/add/', views.add_memory_api, name='add_memory_api'),
    path('api/kg/query/', views.kg_query_api, name='kg_query_api'),
    path('api/kg/add/', views.kg_add_api, name='kg_add_api'),
    path('api/kg/invalidate/', views.kg_invalidate_api, name='kg_invalidate_api'),
    path('api/kg/stats/', views.kg_stats_api, name='kg_stats_api'),
    path('api/kg/timeline/', views.kg_timeline_api, name='kg_timeline_api'),
]
