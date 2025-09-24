from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    # Rapports
    path('reports/', views.reports_list, name='reports'),
    path('reports/<int:report_id>/', views.report_detail, name='report_detail'),
    path('reports/generate/', views.generate_report, name='generate_report'),
    
    # Tableaux de bord
    path('statistics/', views.statistics_dashboard, name='statistics_dashboard'),
    path('heatmap/', views.heatmap_view, name='heatmap'),
    path('performance/', views.performance_metrics, name='performance_metrics'),
    path('trends/', views.trends_analysis, name='trends_analysis'),
] 