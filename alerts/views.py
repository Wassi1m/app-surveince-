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
from .models import Alert, AlertRule, NotificationChannel, AlertRecipient, NotificationLog
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
        'total_today': Alert.objects.filter(created_at__date=today).count(),
        'critical_active': Alert.objects.filter(
            priority='critical',
            status__in=['pending', 'sent', 'acknowledged']
        ).count(),
        'avg_response_time': Alert.objects.filter(
            acknowledged_at__isnull=False
        ).aggregate(
            avg_time=models.Avg(
                models.ExpressionWrapper(
                    models.F('acknowledged_at') - models.F('created_at'),
                    output_field=models.DurationField()
                )
            )
        )['avg_time'],
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
    notifications = NotificationLog.objects.filter(
        alert=alert
    ).select_related('channel').order_by('-sent_at')
    
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
    rules = AlertRule.objects.all().select_related('location', 'created_by').order_by('location', 'priority')
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
def notification_history(request):
    """Historique des notifications"""
    notifications = NotificationLog.objects.all().select_related(
        'alert', 'alert__detection_event', 'channel'
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
    
    week_notifications = NotificationLog.objects.filter(sent_at__gte=last_week)
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
        
        alerts = Alert.objects.filter(
            status__in=['pending', 'sent', 'acknowledged']
        ).select_related(
            'detection_event', 'detection_event__camera', 'detection_event__zone'
        )
        
        if location_id:
            alerts = alerts.filter(detection_event__camera__location_id=location_id)
        
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
