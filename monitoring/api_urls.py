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
    path('cameras/<int:camera_id>/test-stream/', views.api_test_camera_stream, name='test_camera_stream'),
    
    # API Simulation (pour tests)
    path('simulate/detection/', views.api_simulate_detection, name='simulate_detection'),
    
    # API Configuration caméras
    path('cameras/', views.api_cameras_list, name='cameras_list'),
    path('cameras/create/', views.api_create_camera, name='create_camera'),
    path('cameras/<int:camera_id>/config/', views.api_camera_config, name='camera_config'),
    path('cameras/<int:camera_id>/stats/', views.api_camera_stats, name='camera_stats'),
    
    path('zones/', views.api_zones_list, name='zones_list'),
    path('zones/create/', views.api_create_zone, name='create_zone'),
    path('zones/<int:zone_id>/', views.api_zone_detail, name='zone_detail'),
    path('zones/<int:zone_id>/activity/', views.api_zone_activity, name='zone_activity'),
    
    path('dashboard/stats/', views.api_dashboard_stats, name='dashboard_stats'),
] 