from django.urls import path
from . import views

app_name = 'monitoring'

urlpatterns = [
    # Vue principale de surveillance live
    path('live/', views.live_view, name='live_view'),
    
    # Gestion des localisations
    path('locations/', views.location_list, name='locations'),
    path('locations/create/', views.create_location, name='create_location'),
    path('locations/<int:location_id>/', views.location_detail, name='location_detail'),
    path('locations/<int:location_id>/edit/', views.edit_location, name='edit_location'),
    path('locations/<int:location_id>/delete/', views.delete_location, name='delete_location'),
    
    # Gestion des caméras
    path('cameras/', views.camera_list, name='cameras'),
    path('cameras/<int:camera_id>/', views.camera_detail, name='camera_detail'),
    path('cameras/create/', views.create_camera, name='create_camera'),
    path('cameras/<int:camera_id>/rules/create/', views.create_camera_rule, name='create_camera_rule'),
    path('cameras/<int:camera_id>/rules/assign/', views.assign_rule_to_camera, name='assign_rule_to_camera'),
    path('cameras/<int:camera_id>/rules/<int:rule_id>/unassign/', views.unassign_rule_from_camera, name='unassign_rule_from_camera'),
    path('cameras/<int:camera_id>/rules/<int:rule_id>/toggle/', views.toggle_camera_rule, name='toggle_camera_rule'),
    
    # Gestion des zones
    path('zones/', views.zone_list, name='zones'),
    path('zones/create/', views.create_zone, name='create_zone'),
    path('zones/<int:zone_id>/', views.zone_detail, name='zone_detail'),
    path('zones/<int:zone_id>/rules/create/', views.create_zone_rule, name='create_zone_rule'),
    path('zones/<int:zone_id>/rules/assign/', views.assign_rule_to_zone, name='assign_rule_to_zone'),
    
    # Gestion des détections
    path('detections/', views.detection_list, name='detections'),
    path('detections/<int:detection_id>/', views.detection_detail, name='detection_detail'),
    path('detections/<int:detection_id>/verify/', views.verify_detection, name='verify_detection'),
    
    # Administration système
    path('system/health/', views.system_health, name='system_health'),
] 