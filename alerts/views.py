from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Count, Q, Avg
from django.contrib import messages
from django.db import models
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import json
import logging
from datetime import datetime, timedelta
from .models import Alert, AlertRule
from .models_notifications import NotificationChannel, Notification, NotificationPreference
from monitoring.models import Location, Camera, Zone, DetectionEvent

logger = logging.getLogger('alerts')


@login_required
def alert_center(request):
    """Centre des alertes"""
    # Filtres
    status_filter = request.GET.get('status', 'active')
    priority_filter = request.GET.get('priority')
    location_filter = request.GET.get('location')
    
    alerts = Alert.objects.all().select_related(
        'detection_event', 'detection_event__camera', 'detection_event__zone', 'alert_rule'
    )
    
    # Filtrage par statut
    if status_filter == 'active':
        alerts = alerts.filter(status__in=['pending', 'sent', 'acknowledged'])
    elif status_filter == 'resolved':
        alerts = alerts.filter(status__in=['resolved', 'closed'])
    elif status_filter != 'all':
        alerts = alerts.filter(status=status_filter)
    
    # Autres filtres
    if priority_filter:
        alerts = alerts.filter(priority=priority_filter)
    if location_filter:
        alerts = alerts.filter(detection_event__camera__location_id=location_filter)
    
    alerts = alerts.order_by('-created_at')[:100]
    
    # Statistiques rapides
    now = timezone.now()
    today = now.date()
    
    stats = {
        'critical': Alert.objects.filter(
            priority='critical',
            status__in=['pending', 'sent', 'acknowledged']
        ).count(),
        'high': Alert.objects.filter(
            priority='high',
            status__in=['pending', 'sent', 'acknowledged']
        ).count(),
        'medium': Alert.objects.filter(
            priority='medium',
            status__in=['pending', 'sent', 'acknowledged']
        ).count(),
        'resolved_today': Alert.objects.filter(
            resolved_at__date=today
        ).count(),
    }
    
    # Options pour les filtres
    locations = Location.objects.filter(is_active=True)
    priority_choices = Alert.PRIORITY_LEVELS
    status_choices = Alert.STATUS_CHOICES
    
    context = {
        'alerts': alerts,
        'stats': stats,
        'locations': locations,
        'priority_choices': priority_choices,
        'status_choices': status_choices,
        'current_filters': {
            'status': status_filter,
            'priority': priority_filter,
            'location': location_filter,
        }
    }
    
    return render(request, 'alerts/alert_center.html', context)


@login_required
def alert_detail(request, alert_id):
    """Détails d'une alerte"""
    alert = get_object_or_404(Alert, id=alert_id)
    
    # Notifications liées
    notifications = Notification.objects.filter(
        alert=alert
    ).order_by('-sent_at')
    
    # Historique des actions
    actions = []
    if alert.acknowledged_at:
        actions.append({
            'action': 'Accusé de réception',
            'user': alert.acknowledged_by,
            'timestamp': alert.acknowledged_at,
            'icon': 'check',
            'class': 'text-info'
        })
    
    if alert.resolved_at:
        actions.append({
            'action': 'Résolu',
            'user': alert.resolved_by,
            'timestamp': alert.resolved_at,
            'icon': 'check-circle',
            'class': 'text-success'
        })
    
    actions.sort(key=lambda x: x['timestamp'], reverse=True)
    
    context = {
        'alert': alert,
        'notifications': notifications,
        'actions': actions,
    }
    
    return render(request, 'alerts/alert_detail.html', context)


@login_required
@require_http_methods(["POST"])
def acknowledge_alert(request, alert_id):
    """Accuser réception d'une alerte"""
    alert = get_object_or_404(Alert, id=alert_id)
    
    if alert.status in ['pending', 'sent']:
        alert.status = 'acknowledged'
        alert.acknowledged_at = timezone.now()
        alert.acknowledged_by = request.user
        alert.save()
        
        messages.success(request, "Alerte accusée de réception")
        logger.info(f"Alerte {alert.id} accusée de réception par {request.user}")
        
        return JsonResponse({'success': True, 'status': 'acknowledged'})
    
    return JsonResponse({'success': False, 'error': 'Statut invalide'}, status=400)


@login_required
@require_http_methods(["POST"])
def resolve_alert(request, alert_id):
    """Résoudre une alerte"""
    alert = get_object_or_404(Alert, id=alert_id)
    
    try:
        data = json.loads(request.body)
        notes = data.get('notes', '')
        
        alert.status = 'resolved'
        alert.resolved_at = timezone.now()
        alert.resolved_by = request.user
        
        # Ajouter les notes aux métadonnées
        if notes:
            alert.metadata = alert.metadata or {}
            alert.metadata['resolution_notes'] = notes
        
        alert.save()
        
        messages.success(request, "Alerte résolue")
        logger.info(f"Alerte {alert.id} résolue par {request.user}")
        
        return JsonResponse({'success': True, 'status': 'resolved'})
        
    except Exception as e:
        logger.error(f"Erreur résolution alerte {alert_id}: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def rules_list(request):
    """Liste des règles d'alerte"""
    rules = AlertRule.objects.all().select_related('location', 'created_by').order_by('-id')
    locations = Location.objects.filter(is_active=True)
    
    context = {
        'rules': rules,
        'locations': locations,
    }
    
    return render(request, 'alerts/rules.html', context)


@login_required
def rule_detail(request, rule_id):
    """Détails d'une règle d'alerte"""
    rule = get_object_or_404(AlertRule, id=rule_id)
    
    # Alertes générées par cette règle
    recent_alerts = Alert.objects.filter(
        alert_rule=rule
    ).order_by('-created_at')[:20]
    
    # Statistiques
    now = timezone.now()
    last_week = now - timedelta(days=7)
    
    stats = {
        'alerts_last_week': recent_alerts.filter(created_at__gte=last_week).count(),
        'avg_response_time': recent_alerts.filter(
            acknowledged_at__isnull=False
        ).aggregate(
            avg_time=models.Avg(
                models.ExpressionWrapper(
                    models.F('acknowledged_at') - models.F('created_at'),
                    output_field=models.DurationField()
                )
            )
        )['avg_time'],
        'last_triggered': rule.last_triggered,
    }
    
    context = {
        'rule': rule,
        'recent_alerts': recent_alerts,
        'stats': stats,
    }
    
    return render(request, 'alerts/rule_detail.html', context)


@login_required
@require_http_methods(["POST"])
def create_rule(request):
    """Créer une nouvelle règle d'alerte"""
    try:
        data = json.loads(request.body)
        
        rule = AlertRule.objects.create(
            name=data['name'],
            description=data.get('description', ''),
            location_id=data['location_id'],
            trigger_type=data['trigger_type'],
            trigger_conditions=data.get('trigger_conditions', {}),
            is_active=data.get('is_active', True),
            priority=data.get('priority', 1),
            cooldown_minutes=data.get('cooldown_minutes', 5),
            created_by=request.user,
        )
        
        messages.success(request, f"Règle '{rule.name}' créée avec succès")
        logger.info(f"Règle d'alerte créée: {rule.id} par {request.user}")
        
        return JsonResponse({'success': True, 'rule_id': rule.id})
        
    except Exception as e:
        logger.error(f"Erreur création règle: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def toggle_rule(request, rule_id):
    """Activer/désactiver une règle"""
    rule = get_object_or_404(AlertRule, id=rule_id)
    
    rule.is_active = not rule.is_active
    rule.save()
    
    status_text = "activée" if rule.is_active else "désactivée"
    messages.success(request, f"Règle '{rule.name}' {status_text}")
    
    return JsonResponse({
        'success': True, 
        'is_active': rule.is_active,
        'status': status_text
    })


@login_required
def notification_channels(request):
    """Gestion des canaux de notification"""
    channels = NotificationChannel.objects.all().order_by('channel_type', 'name')
    
    context = {
        'channels': channels,
        'channel_types': NotificationChannel.CHANNEL_TYPES,
    }
    
    return render(request, 'alerts/notification_channels.html', context)


@login_required
@require_http_methods(["POST"])
def create_channel(request):
    """Créer un nouveau canal de notification"""
    try:
        data = json.loads(request.body)
        
        channel = NotificationChannel.objects.create(
            name=data['name'],
            channel_type=data['channel_type'],
            configuration=data.get('configuration', {}),
            is_active=data.get('is_active', True),
        )
        
        messages.success(request, f"Canal '{channel.name}' créé avec succès")
        logger.info(f"Canal de notification créé: {channel.id}")
        
        return JsonResponse({'success': True, 'channel_id': channel.id})
        
    except Exception as e:
        logger.error(f"Erreur création canal: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
@require_http_methods(["POST"])
def test_channel(request, channel_id):
    """Tester un canal de notification"""
    channel = get_object_or_404(NotificationChannel, id=channel_id)
    
    try:
        # Simuler l'envoi d'un message de test
        from .utils import send_test_notification
        success = send_test_notification(channel, request.user)
        
        if success:
            messages.success(request, f"Test du canal '{channel.name}' réussi")
            return JsonResponse({'success': True, 'message': 'Test réussi'})
        else:
            messages.error(request, f"Échec du test du canal '{channel.name}'")
            return JsonResponse({'success': False, 'error': 'Test échoué'})
            
    except Exception as e:
        logger.error(f"Erreur test canal {channel_id}: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def notifications_center(request):
    """Centre de notifications avancé"""
    return render(request, 'alerts/notifications.html')



@login_required
def notification_history(request):
    """Historique des notifications"""
    notifications = Notification.objects.all().select_related(
        'alert', 'alert__detection_event'
    ).order_by('-sent_at')[:100]
    
    # Statistiques
    now = timezone.now()
    today = now.date()
    last_week = now - timedelta(days=7)
    
    stats = {
        'sent_today': notifications.filter(sent_at__date=today, status='sent').count(),
        'failed_today': notifications.filter(sent_at__date=today, status='failed').count(),
        'success_rate_week': 0,  # Calculé ci-dessous
    }
    
    week_notifications = Notification.objects.filter(sent_at__gte=last_week)
    week_total = week_notifications.count()
    week_success = week_notifications.filter(status__in=['sent', 'delivered']).count()
    
    if week_total > 0:
        stats['success_rate_week'] = round((week_success / week_total) * 100, 1)
    
    context = {
        'notifications': notifications,
        'stats': stats,
    }
    
    return render(request, 'alerts/notification_history.html', context)

# API Endpoints

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_active_alerts(request):
    """API: Alertes actives"""
    try:
        location_id = request.GET.get('location_id')
        rule_id = request.GET.get('rule_id')
        
        alerts = Alert.objects.filter(
            status__in=['pending', 'sent', 'acknowledged']
        ).select_related(
            'detection_event', 'detection_event__camera', 'detection_event__zone'
        )
        
        if location_id:
            alerts = alerts.filter(detection_event__camera__location_id=location_id)
            
        if rule_id:
            alerts = alerts.filter(alert_rule_id=rule_id)
        
        alerts = alerts.order_by('-created_at')[:50]
        
        alerts_data = []
        for alert in alerts:
            alerts_data.append({
                'id': alert.id,
                'title': alert.title,
                'message': alert.message,
                'priority': alert.priority,
                'status': alert.status,
                'created_at': alert.created_at.isoformat(),
                'age_seconds': int(alert.age_seconds),
                'detection_event': {
                    'id': alert.detection_event.id if alert.detection_event else None,
                    'event_type': alert.detection_event.event_type if alert.detection_event else None,
                    'camera_name': alert.detection_event.camera.name if alert.detection_event else None,
                    'zone_name': alert.detection_event.zone.name if alert.detection_event else None,
                } if alert.detection_event else None,
            })
        
        return Response({'alerts': alerts_data})
        
    except Exception as e:
        logger.error(f"Erreur API active alerts: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_alert_stats(request):
    """API: Statistiques des alertes"""
    try:
        # Période (par défaut: 7 derniers jours)
        days = int(request.GET.get('days', 7))
        location_id = request.GET.get('location_id')
        
        start_date = timezone.now() - timedelta(days=days)
        
        alerts = Alert.objects.filter(created_at__gte=start_date)
        if location_id:
            alerts = alerts.filter(detection_event__camera__location_id=location_id)
        
        # Statistiques par priorité
        priority_stats = alerts.values('priority').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Statistiques par statut
        status_stats = alerts.values('status').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Temps de réponse moyen
        avg_response = alerts.filter(
            acknowledged_at__isnull=False
        ).aggregate(
            avg_time=models.Avg(
                models.ExpressionWrapper(
                    models.F('acknowledged_at') - models.F('created_at'),
                    output_field=models.DurationField()
                )
            )
        )['avg_time']
        
        avg_response_minutes = None
        if avg_response:
            avg_response_minutes = avg_response.total_seconds() / 60
        
        return Response({
            'total_alerts': alerts.count(),
            'priority_distribution': list(priority_stats),
            'status_distribution': list(status_stats),
            'avg_response_time_minutes': avg_response_minutes,
            'period_days': days,
        })
        
    except Exception as e:
        logger.error(f"Erreur API alert stats: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_create_rule(request):
    """API pour créer une nouvelle règle"""
    try:
        data = request.data
        
        # Vérifier que la localisation existe
        from monitoring.models import Location
        location = get_object_or_404(Location, id=data.get('location_id'))
        
        rule = AlertRule.objects.create(
            name=data.get('name'),
            description=data.get('description', ''),
            location=location,
            trigger_type=data.get('trigger_type', 'detection'),
            trigger_conditions=data.get('trigger_conditions', {}),
            priority=data.get('priority', 2),
            cooldown_minutes=data.get('cooldown_minutes', 5),
            is_active=data.get('is_active', True),
            created_by=request.user
        )
        
        return Response({
            'success': True,
            'message': 'Règle créée avec succès',
            'rule_id': rule.id
        })
        
    except Exception as e:
        logger.error(f"Erreur création règle: {e}")
        return Response({'success': False, 'error': str(e)}, status=400)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def api_rule_detail(request, rule_id):
    """API pour les détails des règles"""
    rule = get_object_or_404(AlertRule, id=rule_id)
    
    if request.method == 'GET':
        return Response({
            'id': rule.id,
            'name': rule.name,
            'description': rule.description,
            'trigger_type': rule.trigger_type,
            'trigger_conditions': rule.trigger_conditions,
            'priority': rule.priority,
            'cooldown_minutes': rule.cooldown_minutes,
            'is_active': rule.is_active,
            'location_id': rule.location.id,
        })
    
    elif request.method == 'PUT':
        try:
            data = request.data
            
            # Validation des champs requis
            if 'name' in data and not data['name'].strip():
                return Response({'success': False, 'error': 'Le nom est requis'}, status=400)
            
            if 'trigger_type' in data and not data['trigger_type']:
                return Response({'success': False, 'error': 'Le type de déclenchement est requis'}, status=400)
            
            if 'priority' in data and data['priority'] not in [1, 2, 3, 4]:
                return Response({'success': False, 'error': 'Priorité invalide (1-4)'}, status=400)
            
            # Mise à jour des champs
            if 'name' in data:
                rule.name = data['name'].strip()
            if 'description' in data:
                rule.description = data['description']
            if 'trigger_type' in data:
                rule.trigger_type = data['trigger_type']
            if 'trigger_conditions' in data:
                rule.trigger_conditions = data['trigger_conditions']
            if 'priority' in data:
                rule.priority = int(data['priority'])
            if 'cooldown_minutes' in data:
                rule.cooldown_minutes = int(data['cooldown_minutes'])
            if 'is_active' in data:
                rule.is_active = bool(data['is_active'])
            
            rule.save()
            
            return Response({
                'success': True,
                'message': 'Règle mise à jour'
            })
            
        except Exception as e:
            logger.error(f"Erreur config règle {rule_id}: {e}")
            return Response({'success': False, 'error': str(e)}, status=400)
    
    elif request.method == 'DELETE':
        try:
            rule_name = rule.name
            rule.delete()
            
            logger.info(f"Règle supprimée: {rule_name} (ID: {rule_id}) par {request.user}")
            
            return Response({
                'success': True,
                'message': f'Règle "{rule_name}" supprimée avec succès'
            })
            
        except Exception as e:
            logger.error(f"Erreur suppression règle {rule_id}: {e}")
            return Response({'success': False, 'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_test_rule(request, rule_id):
    """API pour tester une règle"""
    rule = get_object_or_404(AlertRule, id=rule_id)
    
    try:
        # Créer une alerte de test
        from monitoring.models import Camera, DetectionEvent
        
        # Prendre une caméra de la même localisation
        camera = Camera.objects.filter(location=rule.location).first()
        if not camera:
            return Response({
                'success': False,
                'error': 'Aucune caméra disponible pour le test'
            }, status=400)
        
        # Créer une détection de test
        detection = DetectionEvent.objects.create(
            camera=camera,
            zone=camera.zone,
            event_type='test',
            severity='medium',
            confidence=0.95,
            description=f'Test de la règle: {rule.name}',
            bounding_boxes=[{'x': 100, 'y': 100, 'width': 50, 'height': 50}]
        )
        
        # Créer une alerte de test
        alert = Alert.objects.create(
            title=f'[TEST] {rule.name}',
            message=f'Alerte de test générée pour la règle "{rule.name}"',
            priority='medium',
            alert_rule=rule,
            detection_event=detection,
            status='sent'
        )
        
        logger.info(f"Alerte de test créée: {alert.id} pour la règle {rule.id}")
        
        return Response({
            'success': True,
            'message': 'Test réussi - Alerte de test créée',
            'alert_id': alert.id
        })
        
    except Exception as e:
        logger.error(f"Erreur test règle {rule_id}: {e}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_rule_stats(request, rule_id):
    """API pour les statistiques d'une règle"""
    rule = get_object_or_404(AlertRule, id=rule_id)
    
    try:
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        # Période d'analyse (dernier mois)
        last_month = timezone.now() - timedelta(days=30)
        
        # Alertes déclenchées par cette règle
        rule_alerts = Alert.objects.filter(
            alert_rule=rule,
            created_at__gte=last_month
        )
        
        # Statistiques
        triggers_this_month = rule_alerts.count()
        
        # Taux de précision (alertes résolues vs total)
        resolved_alerts = rule_alerts.filter(status='resolved').count()
        accuracy_rate = (resolved_alerts / triggers_this_month * 100) if triggers_this_month > 0 else 0
        
        # Temps de réponse moyen
        resolved_with_time = rule_alerts.filter(
            status='resolved',
            resolved_at__isnull=False
        )
        
        if resolved_with_time.exists():
            total_response_time = sum([
                (alert.resolved_at - alert.created_at).total_seconds() / 60
                for alert in resolved_with_time
            ])
            avg_response_time = total_response_time / resolved_with_time.count()
        else:
            avg_response_time = 0
        
        # Alertes par statut
        status_breakdown = {
            'pending': rule_alerts.filter(status='pending').count(),
            'sent': rule_alerts.filter(status='sent').count(),
            'resolved': rule_alerts.filter(status='resolved').count(),
        }
        
        stats = {
            'triggers_this_month': triggers_this_month,
            'accuracy_rate': round(accuracy_rate, 1),
            'avg_response_time': round(avg_response_time, 1),
            'status_breakdown': status_breakdown,
            'last_trigger': rule_alerts.order_by('-created_at').first().created_at.isoformat() if rule_alerts.exists() else None
        }
        
        return Response(stats)
        
    except Exception as e:
        logger.error(f"Erreur stats règle {rule_id}: {e}")
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_unread_notifications(request):
    """API pour les notifications non lues"""
    try:
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        # Récupérer les alertes récentes non résolues comme "notifications"
        recent_alerts = Alert.objects.filter(
            status__in=['pending', 'sent'],
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).order_by('-created_at')[:10]
        
        notifications = []
        for alert in recent_alerts:
            notifications.append({
                'id': alert.id,
                'type': 'alert',
                'title': alert.title,
                'message': alert.message,
                'priority': alert.priority,
                'created_at': alert.created_at.isoformat(),
                'is_read': False  # Pour l'instant, toutes sont non lues
            })
        
        return Response({
            'notifications': notifications,
            'count': len(notifications)
        })
        
    except Exception as e:
        logger.error(f"Erreur notifications: {e}")
        return Response({'error': str(e)}, status=500)


# ===== NOUVELLES API NOTIFICATIONS AVANCÉES =====

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_notifications_list(request):
    """Liste des notifications de l'utilisateur avec pagination"""
    try:
        from .notification_service import notification_service
        
        # Paramètres de requête
        unread_only = request.GET.get('unread_only', 'false').lower() == 'true'
        limit = min(int(request.GET.get('limit', 20)), 100)  # Max 100
        
        notifications = notification_service.get_user_notifications(
            user=request.user,
            unread_only=unread_only,
            limit=limit
        )
        
        notifications_data = []
        for notif in notifications:
            notifications_data.append({
                'id': notif.id,
                'title': notif.title,
                'message': notif.message,
                'type': notif.notification_type,
                'priority': notif.priority,
                'priority_display': notif.get_priority_display(),
                'status': notif.status,
                'is_read': bool(notif.read_at),
                'is_urgent': notif.is_urgent,
                'created_at': notif.created_at.isoformat(),
                'read_at': notif.read_at.isoformat() if notif.read_at else None,
                'action_url': notif.action_url,
                'action_label': notif.action_label,
                'metadata': notif.metadata,
            })
        
        return Response({
            'notifications': notifications_data,
            'count': len(notifications_data),
            'unread_count': len([n for n in notifications_data if not n['is_read']])
        })
        
    except Exception as e:
        logger.error(f"Erreur liste notifications: {e}")
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_mark_notification_read(request, notification_id):
    """Marquer une notification comme lue"""
    try:
        from .notification_service import notification_service
        
        success = notification_service.mark_as_read(notification_id, request.user)
        
        if success:
            return Response({'message': 'Notification marquée comme lue'})
        else:
            return Response({'error': 'Notification non trouvée'}, status=404)
            
    except Exception as e:
        logger.error(f"Erreur marquage lecture: {e}")
        return Response({'error': str(e)}, status=500)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def api_notification_preferences(request):
    """Gérer les préférences de notification de l'utilisateur"""
    try:
        from .models import NotificationPreference, NotificationChannel
        
        # Obtenir ou créer les préférences
        preferences, created = NotificationPreference.objects.get_or_create(
            user=request.user,
            defaults={
                'digest_frequency': 'immediate',
                'min_priority': 3,
                'enable_sound': True,
                'enable_vibration': True,
                'enable_email_digest': True,
            }
        )
        
        if request.method == 'GET':
            return Response({
                'digest_frequency': preferences.digest_frequency,
                'quiet_hours_start': preferences.quiet_hours_start.strftime('%H:%M') if preferences.quiet_hours_start else None,
                'quiet_hours_end': preferences.quiet_hours_end.strftime('%H:%M') if preferences.quiet_hours_end else None,
                'min_priority': preferences.min_priority,
                'enable_sound': preferences.enable_sound,
                'enable_vibration': preferences.enable_vibration,
                'enable_email_digest': preferences.enable_email_digest,
                'alert_channels': [ch.id for ch in preferences.alert_channels.all()],
                'system_channels': [ch.id for ch in preferences.system_channels.all()],
                'report_channels': [ch.id for ch in preferences.report_channels.all()],
            })
        
        elif request.method == 'PUT':
            data = request.data
            
            # Mettre à jour les préférences
            if 'digest_frequency' in data:
                preferences.digest_frequency = data['digest_frequency']
            if 'min_priority' in data:
                preferences.min_priority = data['min_priority']
            if 'enable_sound' in data:
                preferences.enable_sound = data['enable_sound']
            if 'enable_vibration' in data:
                preferences.enable_vibration = data['enable_vibration']
            if 'enable_email_digest' in data:
                preferences.enable_email_digest = data['enable_email_digest']
            
            # Horaires silencieux
            if 'quiet_hours_start' in data:
                from datetime import datetime
                if data['quiet_hours_start']:
                    preferences.quiet_hours_start = datetime.strptime(data['quiet_hours_start'], '%H:%M').time()
                else:
                    preferences.quiet_hours_start = None
                    
            if 'quiet_hours_end' in data:
                from datetime import datetime
                if data['quiet_hours_end']:
                    preferences.quiet_hours_end = datetime.strptime(data['quiet_hours_end'], '%H:%M').time()
                else:
                    preferences.quiet_hours_end = None
            
            preferences.save()
            
            # Mettre à jour les canaux
            if 'alert_channels' in data:
                channels = NotificationChannel.objects.filter(id__in=data['alert_channels'])
                preferences.alert_channels.set(channels)
                
            if 'system_channels' in data:
                channels = NotificationChannel.objects.filter(id__in=data['system_channels'])
                preferences.system_channels.set(channels)
                
            if 'report_channels' in data:
                channels = NotificationChannel.objects.filter(id__in=data['report_channels'])
                preferences.report_channels.set(channels)
            
            return Response({'message': 'Préférences mises à jour'})
            
    except Exception as e:
        logger.error(f"Erreur préférences: {e}")
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_notification_channels(request):
    """Liste des canaux de notification disponibles"""
    try:
        from .models import NotificationChannel
        
        channels = NotificationChannel.objects.filter(is_active=True)
        
        channels_data = []
        for channel in channels:
            channels_data.append({
                'id': channel.id,
                'name': channel.name,
                'type': channel.channel_type,
                'type_display': channel.get_channel_type_display(),
                'created_at': channel.created_at.isoformat(),
            })
        
        return Response({'channels': channels_data})
        
    except Exception as e:
        logger.error(f"Erreur canaux: {e}")
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_send_notification(request):
    """Envoyer une notification (pour les admins)"""
    try:
        if not request.user.is_staff:
            return Response({'error': 'Permission refusée'}, status=403)
        
        from .notification_service import notification_service
        from django.contrib.auth.models import User
        
        data = request.data
        
        # Validation des données
        required_fields = ['title', 'message']
        for field in required_fields:
            if not data.get(field):
                return Response({'error': f'Le champ {field} est requis'}, status=400)
        
        # Destinataire
        user = None
        if data.get('user_id'):
            try:
                user = User.objects.get(id=data['user_id'])
            except User.DoesNotExist:
                return Response({'error': 'Utilisateur non trouvé'}, status=404)
        
        # Créer et envoyer la notification
        notification = notification_service.create_notification(
            title=data['title'],
            message=data['message'],
            notification_type=data.get('type', 'info'),
            priority=data.get('priority', 3),
            user=user,
            user_group=data.get('user_group'),
            metadata=data.get('metadata', {}),
            action_url=data.get('action_url'),
            action_label=data.get('action_label'),
            expires_in_hours=data.get('expires_in_hours')
        )
        
        return Response({
            'message': 'Notification créée et envoyée',
            'notification_id': notification.id
        })
        
    except Exception as e:
        logger.error(f"Erreur envoi notification: {e}")
        return Response({'error': str(e)}, status=500)

