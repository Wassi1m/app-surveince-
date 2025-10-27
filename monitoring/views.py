from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Count, Q, Avg
from django.contrib import messages
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import json
import logging
from datetime import datetime, timedelta
import cv2
import numpy as np
from .models import Location, Camera, Zone, DetectionEvent, Incident, VideoRecording
from alerts.models import Alert, AlertRule
from analytics.models import StatisticsSummary, HeatMapData

logger = logging.getLogger('monitoring')


@login_required
def dashboard(request):
    """Vue principale du tableau de bord"""
    try:
        # Statistiques globales
        total_cameras = Camera.objects.count()
        online_cameras = Camera.objects.filter(status='online').count()
        
        # Alertes actives (dernières 24h)
        now = timezone.now()
        active_alerts = Alert.objects.filter(
            created_at__gte=now - timedelta(hours=24),
            status__in=['pending', 'sent', 'acknowledged']
        ).count()
        
        # Détections aujourd'hui
        today = now.date()
        detections_today = DetectionEvent.objects.filter(
            detected_at__date=today
        ).count()
        
        # Incidents cette semaine
        week_start = now - timedelta(days=7)
        incidents_week = Incident.objects.filter(
            created_at__gte=week_start
        ).count()
        
        # Caméras pour le streaming
        cameras_queryset = Camera.objects.filter(status='online').select_related('location', 'zone')
        cameras = list(cameras_queryset[:10])  # Convertir en liste pour éviter les problèmes de slice
        
        # Zones avec niveau d'activité
        zones = []
        for zone in Zone.objects.filter(is_active=True).select_related('location'):
            detection_count = DetectionEvent.objects.filter(
                zone=zone,
                detected_at__gte=now - timedelta(hours=24)
            ).count()
            
            # Calculer le niveau d'activité
            if detection_count > 20:
                activity_level = 'high-activity'
            elif detection_count > 5:
                activity_level = 'medium-activity'
            else:
                activity_level = 'low-activity'
            
            zones.append({
                'id': zone.id,
                'name': zone.name,
                'risk_level': zone.risk_level,
                'detection_count': detection_count,
                'activity_level': activity_level,
            })
        
        # Localisation par défaut (première disponible)
        location = request.user.profile.location if hasattr(request.user, 'profile') else Location.objects.first()
        
        context = {
            'total_cameras': total_cameras,
            'online_cameras': online_cameras,
            'active_alerts': active_alerts,
            'cameras': cameras,
            'zones': zones,
            'location_id': location.id if location else None,
            'stats': {
                'detections_today': detections_today,
                'incidents_week': incidents_week,
            },
            'ai_accuracy': 85.3,  # Pourrait être calculé dynamiquement
            'last_update': now,
        }
        
        return render(request, 'dashboard.html', context)
        
    except Exception as e:
        logger.error(f"Erreur dashboard: {e}")
        messages.error(request, "Erreur lors du chargement du tableau de bord")
        return render(request, 'dashboard.html', {'cameras': [], 'zones': []})


@login_required
def live_view(request):
    """Vue de surveillance en direct"""
    cameras = Camera.objects.filter().select_related('location', 'zone').order_by('status')
    locations = Location.objects.filter(is_active=True)
    
    context = {
        'cameras': cameras,
        'locations': locations,
    }
    
    return render(request, 'monitoring/live_view.html', context)


@login_required
def camera_list(request):
    """Liste des caméras"""
    cameras = Camera.objects.all().select_related('location', 'zone').order_by('status')
    locations = Location.objects.filter(is_active=True)
    zones = Zone.objects.filter(is_active=True)
    
    context = {
        'cameras': cameras,
        'locations': locations,
        'zones': zones,
    }
    
    return render(request, 'monitoring/cameras.html', context)





@login_required
def camera_detail(request, camera_id):
    """Détails d'une caméra"""
    camera = get_object_or_404(Camera, id=camera_id)
    
    # QuerySet de base pour les détections de cette caméra
    camera_detections = DetectionEvent.objects.filter(camera=camera)
    
    # Détections récentes (limitées à 50)
    recent_detections = camera_detections.order_by('-detected_at')[:50]
    
    # Statistiques (utiliser le QuerySet de base, pas la version slicée)
    today = timezone.now().date()
    stats = {
        'detections_today': camera_detections.filter(detected_at__date=today).count(),
        'false_positives': camera_detections.filter(false_positive=True).count(),
        'avg_confidence': camera_detections.aggregate(
            avg_conf=Avg('confidence')
        )['avg_conf'] or 0,
    }
    
    context = {
        'camera': camera,
        'recent_detections': recent_detections,
        'stats': stats,
    }
    
    return render(request, 'monitoring/camera_detail.html', context)


@login_required
@require_http_methods(["POST"])
def create_camera(request):
    """Créer une nouvelle caméra"""
    try:
        data = json.loads(request.body)
        
        camera = Camera.objects.create(
            location_id=data['location_id'],
            zone_id=data['zone_id'],
            name=data['name'],
            ip_address=data['ip_address'],
            port=data.get('port', 554),
            username=data.get('username', ''),
            password=data.get('password', ''),
            stream_url=data['stream_url'],
            resolution=data.get('resolution', '1920x1080'),
            fps=data.get('fps', 30),
            is_ai_enabled=data.get('is_ai_enabled', True),
        )
        
        messages.success(request, f"Caméra '{camera.name}' créée avec succès")
        return JsonResponse({'success': True, 'camera_id': camera.id})
        
    except Exception as e:
        logger.error(f"Erreur création caméra: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def zone_list(request):
    """Liste des zones de surveillance"""
    zones = Zone.objects.all().select_related('location').order_by('-id')
    locations = Location.objects.filter(is_active=True)
    
    context = {
        'zones': zones,
        'locations': locations,
    }
    
    return render(request, 'monitoring/zones.html', context)


@login_required
@require_http_methods(["POST"])
def create_zone(request):
    """Créer une nouvelle zone"""
    try:
        data = json.loads(request.body)
        
        zone = Zone.objects.create(
            location_id=data['location_id'],
            name=data['name'],
            risk_level=data.get('risk_level', 'medium'),
            coordinates=data.get('coordinates', []),
            description=data.get('description', ''),
        )
        
        messages.success(request, f"Zone '{zone.name}' créée avec succès")
        return JsonResponse({'success': True, 'zone_id': zone.id})
        
    except Exception as e:
        logger.error(f"Erreur création zone: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def detection_list(request):
    """Liste des détections"""
    # Filtres
    camera_id = request.GET.get('camera')
    event_type = request.GET.get('type')
    severity = request.GET.get('severity')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    detections = DetectionEvent.objects.all().select_related('camera', 'zone')
    
    # Appliquer les filtres
    if camera_id:
        detections = detections.filter(camera_id=camera_id)
    if event_type:
        detections = detections.filter(event_type=event_type)
    if severity:
        detections = detections.filter(severity=severity)
    if date_from:
        detections = detections.filter(detected_at__date__gte=date_from)
    if date_to:
        detections = detections.filter(detected_at__date__lte=date_to)
    
    detections = detections.order_by('-detected_at')[:100]
    
    # Options pour les filtres
    cameras = Camera.objects.filter(status='online')
    event_types = DetectionEvent.EVENT_TYPES
    severity_levels = DetectionEvent.SEVERITY_LEVELS
    
    context = {
        'detections': detections,
        'cameras': cameras,
        'event_types': event_types,
        'severity_levels': severity_levels,
        'filters': {
            'camera': camera_id,
            'type': event_type,
            'severity': severity,
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    
    return render(request, 'monitoring/detections.html', context)


@login_required
def detection_detail(request, detection_id):
    """Détails d'une détection"""
    detection = get_object_or_404(DetectionEvent, id=detection_id)
    
    # Alertes liées
    related_alerts = Alert.objects.filter(detection_event=detection)
    
    context = {
        'detection': detection,
        'related_alerts': related_alerts,
    }
    
    return render(request, 'monitoring/detection_detail.html', context)


@login_required
@require_http_methods(["POST"])
def verify_detection(request, detection_id):
    """Vérifier/invalider une détection"""
    detection = get_object_or_404(DetectionEvent, id=detection_id)
    
    try:
        data = json.loads(request.body)
        is_valid = data.get('is_valid', True)
        
        detection.is_verified = True
        detection.verified_by = request.user
        detection.verified_at = timezone.now()
        detection.false_positive = not is_valid
        detection.save()
        
        action = "validée" if is_valid else "marquée comme faux positif"
        messages.success(request, f"Détection {action}")
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        logger.error(f"Erreur vérification détection: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# API Endpoints

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_recent_events(request):
    """API: Événements récents"""
    try:
        limit = int(request.GET.get('limit', 20))
        location_id = request.GET.get('location_id')
        
        events = DetectionEvent.objects.all()
        if location_id:
            events = events.filter(camera__location_id=location_id)
        
        events = events.select_related('camera', 'zone').order_by('-detected_at')[:limit]
        
        events_data = []
        for event in events:
            events_data.append({
                'id': event.id,
                'title': f"{event.get_event_type_display()} détecté",
                'camera_name': event.camera.name,
                'zone_name': event.zone.name,
                'severity': event.severity,
                'confidence': event.confidence,
                'timestamp': event.detected_at.isoformat(),
                'description': event.description,
            })
        
        return Response({'events': events_data})
        
    except Exception as e:
        logger.error(f"Erreur API events: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_camera_status(request):
    """API: Statut des caméras"""
    try:
        cameras = Camera.objects.all().select_related('location', 'zone')
        
        cameras_data = []
        for camera in cameras:
            cameras_data.append({
                'id': camera.id,
                'name': camera.name,
                'location': camera.location.name,
                'zone': camera.zone.name,
                'status': camera.status,
                'status_display': camera.get_status_display(),
                'is_ai_enabled': camera.is_ai_enabled,
                'last_seen': camera.last_seen.isoformat() if camera.last_seen else None,
                'resolution': camera.resolution,
                'fps': camera.fps,
            })
        
        return Response({'cameras': cameras_data})
        
    except Exception as e:
        logger.error(f"Erreur API camera status: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_test_camera(request, camera_id):
    """API: Tester la connexion d'une caméra"""
    camera = get_object_or_404(Camera, id=camera_id)
    
    try:
        # Simuler un test de connexion (en production, utiliser OpenCV ou similar)
        # cap = cv2.VideoCapture(camera.stream_url)
        # success = cap.isOpened()
        # cap.release()
        
        # Pour la simulation
        import random
        success = random.choice([True, True, False])  # 66% de succès
        
        if success:
            camera.status = 'online'
            camera.last_seen = timezone.now()
            camera.save()
            
            return Response({
                'success': True,
                'message': 'Caméra accessible',
                'status': 'online'
            })
        else:
            camera.status = 'error'
            camera.save()
            
            return Response({
                'success': False,
                'message': 'Impossible de se connecter à la caméra',
                'status': 'error'
            })
            
    except Exception as e:
        logger.error(f"Erreur test caméra {camera_id}: {e}")
        camera.status = 'error'
        camera.save()
        
        return Response({
            'success': False,
            'error': str(e),
            'status': 'error'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_detection_stats(request):
    """API: Statistiques de détection"""
    try:
        # Période (par défaut: 7 derniers jours)
        days = int(request.GET.get('days', 7))
        location_id = request.GET.get('location_id')
        
        start_date = timezone.now() - timedelta(days=days)
        
        detections = DetectionEvent.objects.filter(detected_at__gte=start_date)
        if location_id:
            detections = detections.filter(camera__location_id=location_id)
        
        # Statistiques par type d'événement
        event_stats = detections.values('event_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Statistiques par gravité
        severity_stats = detections.values('severity').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Statistiques quotidiennes
        daily_stats = []
        for i in range(days):
            date = (timezone.now() - timedelta(days=i)).date()
            count = detections.filter(detected_at__date=date).count()
            daily_stats.append({
                'date': date.isoformat(),
                'count': count
            })
        
        return Response({
            'total_detections': detections.count(),
            'event_types': list(event_stats),
            'severity_levels': list(severity_stats),
            'daily_stats': daily_stats[::-1],  # Ordre chronologique
            'period_days': days,
        })
        
    except Exception as e:
        logger.error(f"Erreur API detection stats: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Simulateur de détection IA (pour démonstration)
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_simulate_detection(request):
    """API: Simuler une détection IA (pour tests)"""
    try:
        data = request.data
        camera_id = data.get('camera_id')
        event_type = data.get('event_type', 'suspicious')
        
        camera = get_object_or_404(Camera, id=camera_id)
        
        # Créer une détection simulée
        detection = DetectionEvent.objects.create(
            camera=camera,
            zone=camera.zone,
            event_type=event_type,
            severity=data.get('severity', 'medium'),
            confidence=data.get('confidence', 0.85),
            bounding_boxes=data.get('bounding_boxes', [
                {'x': 100, 'y': 50, 'width': 200, 'height': 150}
            ]),
            description=data.get('description', f'Détection simulée: {event_type}'),
        )
        
        # Déclencher les alertes si nécessaire
        from alerts.utils import process_detection
        process_detection(detection)
        
        logger.info(f"Détection simulée créée: {detection.id}")
        
        return Response({
            'success': True,
            'detection_id': detection.id,
            'message': 'Détection simulée créée'
        })
        
    except Exception as e:
        logger.error(f"Erreur simulation détection: {e}")
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Utilitaires pour l'administration

@login_required
def system_health(request):
    """Santé du système"""
    if not request.user.is_staff:
        messages.error(request, "Accès non autorisé")
        return redirect('dashboard')
    
    # Statistiques système
    total_cameras = Camera.objects.count()
    online_cameras = Camera.objects.filter(status='online').count()
    error_cameras = Camera.objects.filter(status='error').count()
    
    # Détections récentes
    last_hour = timezone.now() - timedelta(hours=1)
    recent_detections = DetectionEvent.objects.filter(
        detected_at__gte=last_hour
    ).count()
    
    # Alertes non résolues
    unresolved_alerts = Alert.objects.filter(
        status__in=['pending', 'sent', 'acknowledged']
    ).count()
    
    # Espace disque (simulation)
    disk_usage = {
        'used': 65.4,  # %
        'total': '2 TB',
        'available': '700 GB'
    }
    
    context = {
        'system_stats': {
            'total_cameras': total_cameras,
            'online_cameras': online_cameras,
            'error_cameras': error_cameras,
            'uptime_percentage': (online_cameras / total_cameras * 100) if total_cameras > 0 else 0,
            'recent_detections': recent_detections,
            'unresolved_alerts': unresolved_alerts,
            'disk_usage': disk_usage,
        }
    }
    
    return render(request, 'monitoring/system_health.html', context)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_zone_activity(request):
    """API pour récupérer l'activité des zones"""
    try:
        from datetime import timedelta
        now = timezone.now()
        
        zones_data = []
        for zone in Zone.objects.filter(is_active=True).select_related('location'):
            detection_count = DetectionEvent.objects.filter(
                zone=zone,
                detected_at__gte=now - timedelta(hours=24)
            ).count()
            
            # Calculer le niveau d'activité
            if detection_count > 20:
                activity_level = 'high-activity'
            elif detection_count > 5:
                activity_level = 'medium-activity'
            else:
                activity_level = 'low-activity'
            
            zones_data.append({
                'id': zone.id,
                'name': zone.name,
                'risk_level': zone.risk_level,
                'detection_count': detection_count,
                'activity_level': activity_level,
            })
        
        return Response({
            'success': True,
            'zones': zones_data
        })
        
    except Exception as e:
        logger.error(f"Erreur zone activity: {e}")
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_create_camera(request):
    """API pour créer une nouvelle caméra"""
    try:
        data = request.data
        
        # Vérifier que la zone existe
        zone = get_object_or_404(Zone, id=data.get('zone_id'))
        
        camera = Camera.objects.create(
            location=zone.location,
            zone=zone,
            name=data.get('name'),
            ip_address=data.get('ip_address'),
            port=data.get('port', 554),
            stream_url=data.get('stream_url'),
            resolution=data.get('resolution', '1920x1080'),
            fps=data.get('fps', 30),
            is_ai_enabled=data.get('is_ai_enabled', True),
            status='offline'  # Par défaut offline jusqu'au test
        )
        
        return Response({
            'success': True,
            'message': 'Caméra créée avec succès',
            'camera_id': camera.id
        })
        
    except Exception as e:
        logger.error(f"Erreur création caméra: {e}")
        return Response({'success': False, 'error': str(e)}, status=400)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def api_camera_config(request, camera_id):
    """API pour la configuration des caméras"""
    camera = get_object_or_404(Camera, id=camera_id)
    
    if request.method == 'GET':
        return Response({
            'id': camera.id,
            'name': camera.name,
            'ip_address': camera.ip_address,
            'port': camera.port,
            'resolution': camera.resolution,
            'fps': camera.fps,
            'is_ai_enabled': camera.is_ai_enabled,
            'location_id': camera.location.id,
            'zone_id': camera.zone.id if camera.zone else None,
        })
    
    elif request.method == 'PUT':
        try:
            data = request.data
            
            camera.name = data.get('name', camera.name)
            camera.ip_address = data.get('ip_address', camera.ip_address)
            camera.port = data.get('port', camera.port)
            camera.resolution = data.get('resolution', camera.resolution)
            camera.fps = data.get('fps', camera.fps)
            camera.is_ai_enabled = data.get('is_ai_enabled', camera.is_ai_enabled)
            
            camera.save()
            
            return Response({
                'success': True,
                'message': 'Configuration mise à jour'
            })
            
        except Exception as e:
            logger.error(f"Erreur config caméra {camera_id}: {e}")
            return Response({'success': False, 'error': str(e)}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_camera_stats(request, camera_id):
    """API pour les statistiques des caméras"""
    camera = get_object_or_404(Camera, id=camera_id)
    
    try:
        # Statistiques des détections
        today = timezone.now().date()
        detections_today = DetectionEvent.objects.filter(
            camera=camera,
            detected_at__date=today
        ).count()
        
        # Calcul de la disponibilité
        uptime_percentage = 95.5 if camera.status == 'online' else 0
        
        # Confiance moyenne
        avg_confidence = DetectionEvent.objects.filter(
            camera=camera
        ).aggregate(avg=Avg('confidence'))['avg'] or 0
        
        # Faux positifs
        false_positives = DetectionEvent.objects.filter(
            camera=camera,
            false_positive=True
        ).count()
        
        # Détections par type
        detections_by_type = {}
        event_types = DetectionEvent.objects.filter(camera=camera).values('event_type').annotate(
            count=Count('id')
        )
        
        total_detections = sum(item['count'] for item in event_types)
        for item in event_types:
            detections_by_type[item['event_type']] = item['count']
        
        return Response({
            'detections_today': detections_today,
            'uptime_percentage': uptime_percentage,
            'avg_confidence': round(avg_confidence * 100, 1) if avg_confidence else 0,
            'false_positives': false_positives,
            'detections_by_type': detections_by_type,
            'total_detections': total_detections
        })
        
    except Exception as e:
        logger.error(f"Erreur stats caméra {camera_id}: {e}")
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_cameras_list(request):
    """API pour lister les caméras avec filtrage optionnel par zone"""
    try:
        cameras = Camera.objects.all().select_related('zone', 'location')
        
        # Filtrer par zone si spécifié
        zone_id = request.GET.get('zone_id')
        if zone_id:
            cameras = cameras.filter(zone_id=zone_id)
        
        # Ordonner par date de création (plus récentes en premier)
        cameras = cameras.order_by('status')
        
        cameras_data = []
        for camera in cameras:
            cameras_data.append({
                'id': camera.id,
                'name': camera.name,
                'ip_address': camera.ip_address,
                'port': camera.port,
                'stream_url': camera.stream_url,
                'resolution': camera.resolution,
                'fps': camera.fps,
                'status': camera.status,
                'is_ai_enabled': camera.is_ai_enabled,
                'zone_id': camera.zone.id,
                'zone_name': camera.zone.name,
                'location_name': camera.location.name
            })
        
        return Response(cameras_data)
        
    except Exception as e:
        logger.error(f"Erreur liste caméras: {e}")
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_zones_list(request):
    """API pour lister toutes les zones"""
    try:
        zones = Zone.objects.all().select_related('location').order_by('-id')
        zones_data = []
        
        for zone in zones:
            zones_data.append({
                'id': zone.id,
                'name': zone.name,
                'description': zone.description,
                'risk_level': zone.risk_level,
                'location_name': zone.location.name,
                'location_id': zone.location.id,
                'is_active': zone.is_active,
                'camera_count': zone.cameras.count()
            })
        
        return Response(zones_data)
        
    except Exception as e:
        logger.error(f"Erreur liste zones: {e}")
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_create_zone(request):
    """API pour créer une nouvelle zone"""
    try:
        data = request.data
        
        # Vérifier que la localisation existe
        location = get_object_or_404(Location, id=data.get('location_id'))
        
        zone = Zone.objects.create(
            location=location,
            name=data.get('name'),
            description=data.get('description', ''),
            risk_level=data.get('risk_level', 'medium'),
            coordinates=data.get('coordinates', []),
            is_active=True
        )
        
        return Response({
            'success': True,
            'message': 'Zone créée avec succès',
            'zone_id': zone.id
        })
        
    except Exception as e:
        logger.error(f"Erreur création zone: {e}")
        return Response({'success': False, 'error': str(e)}, status=400)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def api_zone_detail(request, zone_id):
    """API pour les détails des zones"""
    zone = get_object_or_404(Zone, id=zone_id)
    
    if request.method == 'GET':
        return Response({
            'id': zone.id,
            'name': zone.name,
            'description': zone.description,
            'risk_level': zone.risk_level,
            'coordinates': zone.coordinates,
            'location_id': zone.location.id,
            'is_active': zone.is_active,
        })
    
    elif request.method == 'PUT':
        try:
            data = request.data
            
            zone.name = data.get('name', zone.name)
            zone.description = data.get('description', zone.description)
            zone.risk_level = data.get('risk_level', zone.risk_level)
            zone.coordinates = data.get('coordinates', zone.coordinates)
            
            zone.save()
            
            return Response({
                'success': True,
                'message': 'Zone mise à jour'
            })
            
        except Exception as e:
            logger.error(f"Erreur config zone {zone_id}: {e}")
            return Response({'success': False, 'error': str(e)}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_zone_activity(request, zone_id):
    """API pour l'activité d'une zone"""
    zone = get_object_or_404(Zone, id=zone_id)
    
    try:
        from datetime import datetime, timedelta
        from django.utils import timezone
        from alerts.models import Alert
        
        today = timezone.now().date()
        
        # Compter les détections aujourd'hui
        detections_today = DetectionEvent.objects.filter(
            zone=zone,
            detected_at__date=today
        ).count()
        
        # Compter les alertes actives
        active_alerts = Alert.objects.filter(
            detection_event__zone=zone,
            status__in=['pending', 'sent']
        ).count()
        
        # Dernière détection
        last_detection = DetectionEvent.objects.filter(
            zone=zone
        ).order_by('-detected_at').first()
        
        # Calculer le niveau d'activité basé sur les détections
        if detections_today == 0:
            activity_level = 'low'
        elif detections_today < 10:
            activity_level = 'medium'
        else:
            activity_level = 'high'
        
        return Response({
            'detections_today': detections_today,
            'active_alerts': active_alerts,
            'level': activity_level,
            'last_detection': last_detection.detected_at if last_detection else None
        })
        
    except Exception as e:
        logger.error(f"Erreur activité zone {zone_id}: {e}")
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_dashboard_stats(request):
    """API pour les statistiques du dashboard"""
    try:
        from datetime import datetime, timedelta
        from django.utils import timezone
        from alerts.models import Alert
        
        # Statistiques des caméras
        total_cameras = Camera.objects.count()
        online_cameras = Camera.objects.filter(status='online').count()
        
        # Statistiques des zones
        total_zones = Zone.objects.count()
        active_zones = Zone.objects.filter(is_active=True).count()
        
        # Alertes récentes (dernières 24h)
        last_24h = timezone.now() - timedelta(hours=24)
        recent_alerts = Alert.objects.filter(
            created_at__gte=last_24h
        ).count()
        
        # Détections récentes (dernières 24h) - utiliser detected_at au lieu de created_at
        recent_detections = DetectionEvent.objects.filter(
            detected_at__gte=last_24h
        ).count()
        
        # Alertes actives
        active_alerts = Alert.objects.filter(
            status__in=['pending', 'sent']
        ).count()
        
        
        stats = {
            'cameras': {
                'total': total_cameras,
                'online': online_cameras,
                'offline': total_cameras - online_cameras
            },
            'zones': {
                'total': total_zones,
                'active': active_zones
            },
            'recent_alerts': recent_alerts,
            'active_alerts': active_alerts,
            'recent_detections': recent_detections,
            'last_updated': timezone.now().isoformat()
        }
        
        return Response({'stats': stats})
        
    except Exception as e:
        logger.error(f"Erreur stats dashboard: {e}")
        return Response({'error': str(e)}, status=500)
