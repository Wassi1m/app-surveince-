from django.urls import path
from . import views

app_name = 'monitoring'

urlpatterns = [
    # Vue principale de surveillance live
    path('live/', views.live_view, name='live_view'),
    
    # Gestion des caméras
    path('cameras/', views.camera_list, name='cameras'),
    path('cameras/<int:camera_id>/', views.camera_detail, name='camera_detail'),
    path('cameras/create/', views.create_camera, name='create_camera'),
    
    # Gestion des zones
    path('zones/', views.zone_list, name='zones'),
    path('zones/create/', views.create_zone, name='create_zone'),
    
    # Gestion des détections
    path('detections/', views.detection_list, name='detections'),
    path('detections/<int:detection_id>/', views.detection_detail, name='detection_detail'),
    path('detections/<int:detection_id>/verify/', views.verify_detection, name='verify_detection'),
    
    # Administration système
    path('system/health/', views.system_health, name='system_health'),
] 