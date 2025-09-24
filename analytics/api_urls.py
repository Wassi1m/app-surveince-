from django.urls import path
from . import views

app_name = 'analytics_api'

urlpatterns = [
    # API Statistiques
    path('statistics/summary/', views.api_statistics_summary, name='statistics_summary'),
    path('heatmap/data/', views.api_heatmap_data, name='heatmap_data'),
    
    # API Rapports
    path('reports/generate/', views.api_generate_report, name='generate_report'),
] 