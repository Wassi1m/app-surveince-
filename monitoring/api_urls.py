from django.urls import path
from . import views

app_name = 'monitoring_api'

urlpatterns = [
    # API Événements et statistiques
    path('events/recent/', views.api_recent_events, name='recent_events'),
    path('stats/detections/', views.api_detection_stats, name='detection_stats'),
    path('stats/zone-activity/', views.api_zone_activity, name='zone_activity'),
    
    # API Caméras
    path('cameras/status/', views.api_camera_status, name='camera_status'),
    path('cameras/<int:camera_id>/test/', views.api_test_camera, name='test_camera'),
    
    # API Simulation (pour tests)
    path('simulate/detection/', views.api_simulate_detection, name='simulate_detection'),
] 