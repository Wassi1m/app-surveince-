"""
Utilitaires pour le système d'alertes
"""
import logging
from django.utils import timezone
from django.db import transaction
from .models import AlertRule, Alert, NotificationChannel, NotificationLog, AlertRecipient
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

logger = logging.getLogger('alerts')


def process_detection(detection_event):
    """
    Traite une détection et génère les alertes appropriées
    """
    logger.info(f"Traitement de la détection {detection_event.id}")
    
    # Récupérer les règles applicables
    applicable_rules = AlertRule.objects.filter(
        location=detection_event.camera.location,
        is_active=True
    )
    
    alerts_created = []
    
    for rule in applicable_rules:
        if should_trigger_alert(rule, detection_event):
            alert = create_alert_from_rule(rule, detection_event)
            if alert:
                alerts_created.append(alert)
                
                # Envoyer les notifications
                send_alert_notifications(alert)
                
                # Mettre à jour la règle
                rule.last_triggered = timezone.now()
                rule.save()
    
    logger.info(f"Détection {detection_event.id}: {len(alerts_created)} alerte(s) créée(s)")
    return alerts_created


def should_trigger_alert(rule, detection_event):
    """
    Vérifie si une règle doit déclencher une alerte pour cette détection
    """
    conditions = rule.trigger_conditions
    
    # Vérifier le délai de cooldown
    if rule.last_triggered:
        cooldown = timezone.timedelta(minutes=rule.cooldown_minutes)
        if timezone.now() - rule.last_triggered < cooldown:
            return False
    
    # Évaluer les conditions selon le type de déclencheur
    if rule.trigger_type == 'detection_type':
        return detection_event.event_type in conditions.get('event_types', [])
    
    elif rule.trigger_type == 'severity_level':
        required_severity = conditions.get('min_severity', 'low')
        severity_order = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
        return severity_order.get(detection_event.severity, 0) >= severity_order.get(required_severity, 0)
    
    elif rule.trigger_type == 'confidence_threshold':
        return detection_event.confidence >= conditions.get('min_confidence', 0.5)
    
    elif rule.trigger_type == 'camera':
        return detection_event.camera_id in conditions.get('camera_ids', [])
    
    elif rule.trigger_type == 'zone':
        return detection_event.zone_id in conditions.get('zone_ids', [])
    
    elif rule.trigger_type == 'time_window':
        current_hour = timezone.now().hour
        time_windows = conditions.get('time_windows', [])
        return any(window['start'] <= current_hour <= window['end'] for window in time_windows)
    
    return True


@transaction.atomic
def create_alert_from_rule(rule, detection_event):
    """
    Crée une alerte basée sur une règle et une détection
    """
    try:
        # Déterminer la priorité
        priority = determine_alert_priority(rule, detection_event)
        
        # Générer le titre et le message
        title = f"{detection_event.get_event_type_display()} - {detection_event.camera.name}"
        message = f"Détection {detection_event.get_event_type_display().lower()} dans la zone {detection_event.zone.name} " \
                 f"avec un niveau de confiance de {detection_event.confidence:.0%}"
        
        # Créer l'alerte
        alert = Alert.objects.create(
            detection_event=detection_event,
            alert_rule=rule,
            title=title,
            message=message,
            priority=priority,
            status='pending',
            metadata={
                'camera_id': detection_event.camera_id,
                'zone_id': detection_event.zone_id,
                'confidence': detection_event.confidence,
                'severity': detection_event.severity,
            }
        )
        
        logger.info(f"Alerte créée: {alert.id} - {alert.title}")
        return alert
        
    except Exception as e:
        logger.error(f"Erreur création alerte: {e}")
        return None


def determine_alert_priority(rule, detection_event):
    """
    Détermine la priorité d'une alerte
    """
    # Priorité basée sur la gravité de la détection
    if detection_event.severity == 'critical':
        return 'critical'
    elif detection_event.severity == 'high':
        return 'high'
    elif detection_event.severity == 'medium':
        return 'medium'
    else:
        return 'low'


def send_alert_notifications(alert):
    """
    Envoie les notifications pour une alerte
    """
    logger.info(f"Envoi des notifications pour l'alerte {alert.id}")
    
    # Récupérer les destinataires
    recipients = AlertRecipient.objects.filter(
        location=alert.detection_event.camera.location,
        is_active=True
    ).prefetch_related('channels')
    
    # Filtrer par priorité
    filtered_recipients = []
    for recipient in recipients:
        priority_filter = recipient.priority_filter
        if not priority_filter or alert.priority in priority_filter:
            # Vérifier les restrictions horaires
            if is_within_time_restrictions(recipient.time_restrictions):
                filtered_recipients.append(recipient)
    
    # Envoyer les notifications
    for recipient in filtered_recipients:
        for channel in recipient.channels.filter(is_active=True):
            send_notification_via_channel(alert, channel, recipient.user)
    
    # Notification WebSocket temps réel
    send_realtime_alert(alert)


def send_notification_via_channel(alert, channel, user):
    """
    Envoie une notification via un canal spécifique
    """
    try:
        # Créer le log de notification
        notification_log = NotificationLog.objects.create(
            alert=alert,
            channel=channel,
            recipient=user.email,  # ou phone, selon le canal
            status='pending',
        )
        
        # Envoyer selon le type de canal
        success = False
        
        if channel.channel_type == 'email':
            success = send_email_notification(alert, channel, user, notification_log)
        elif channel.channel_type == 'sms':
            success = send_sms_notification(alert, channel, user, notification_log)
        elif channel.channel_type == 'webhook':
            success = send_webhook_notification(alert, channel, user, notification_log)
        elif channel.channel_type == 'push':
            success = send_push_notification(alert, channel, user, notification_log)
        
        # Mettre à jour le statut
        if success:
            notification_log.status = 'sent'
            notification_log.sent_at = timezone.now()
            channel.last_used = timezone.now()
            channel.save()
        else:
            notification_log.status = 'failed'
            notification_log.error_message = "Erreur d'envoi"
        
        notification_log.save()
        
        logger.info(f"Notification {notification_log.id}: {notification_log.status}")
        
    except Exception as e:
        logger.error(f"Erreur envoi notification: {e}")


def send_email_notification(alert, channel, user, notification_log):
    """
    Envoie une notification par email
    """
    try:
        from django.core.mail import send_mail
        from django.conf import settings
        
        config = channel.configuration
        subject = f"[SURVEILLANCE] {alert.title}"
        
        message = f"""
        Nouvelle alerte de surveillance détectée :
        
        Titre: {alert.title}
        Priorité: {alert.get_priority_display()}
        Heure: {alert.created_at.strftime('%d/%m/%Y %H:%M:%S')}
        
        Détails:
        {alert.message}
        
        Caméra: {alert.detection_event.camera.name}
        Zone: {alert.detection_event.zone.name}
        Confiance: {alert.detection_event.confidence:.0%}
        
        Veuillez accuser réception dans le système de surveillance.
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Erreur email: {e}")
        return False


def send_sms_notification(alert, channel, user, notification_log):
    """
    Envoie une notification par SMS (simulation)
    """
    try:
        # Ici, vous intégreriez avec un service SMS comme Twilio
        # Pour la simulation, on marque comme réussi
        
        config = channel.configuration
        phone = config.get('phone_number', user.profile.phone if hasattr(user, 'profile') else None)
        
        if not phone:
            return False
        
        message = f"[SURVEILLANCE] {alert.title} - Priorité: {alert.priority} - {alert.created_at.strftime('%H:%M')}"
        
        # Simulation d'envoi SMS
        logger.info(f"SMS simulé vers {phone}: {message}")
        return True
        
    except Exception as e:
        logger.error(f"Erreur SMS: {e}")
        return False


def send_webhook_notification(alert, channel, user, notification_log):
    """
    Envoie une notification via webhook
    """
    try:
        import requests
        
        config = channel.configuration
        webhook_url = config.get('webhook_url')
        
        if not webhook_url:
            return False
        
        payload = {
            'alert_id': alert.id,
            'title': alert.title,
            'message': alert.message,
            'priority': alert.priority,
            'status': alert.status,
            'created_at': alert.created_at.isoformat(),
            'detection': {
                'event_type': alert.detection_event.event_type,
                'camera': alert.detection_event.camera.name,
                'zone': alert.detection_event.zone.name,
                'confidence': alert.detection_event.confidence,
            }
        }
        
        headers = {'Content-Type': 'application/json'}
        auth_headers = config.get('headers', {})
        headers.update(auth_headers)
        
        response = requests.post(
            webhook_url,
            json=payload,
            headers=headers,
            timeout=30
        )
        
        notification_log.external_id = response.headers.get('X-Message-ID', '')
        notification_log.metadata = {
            'status_code': response.status_code,
            'response': response.text[:500]  # Limite la taille
        }
        
        return response.status_code < 400
        
    except Exception as e:
        logger.error(f"Erreur webhook: {e}")
        notification_log.error_message = str(e)
        return False


def send_push_notification(alert, channel, user, notification_log):
    """
    Envoie une notification push (simulation)
    """
    try:
        # Ici, vous intégreriez avec un service push comme FCM
        logger.info(f"Push notification simulée pour {user.username}: {alert.title}")
        return True
        
    except Exception as e:
        logger.error(f"Erreur push: {e}")
        return False


def send_realtime_alert(alert):
    """
    Envoie l'alerte en temps réel via WebSocket
    """
    try:
        channel_layer = get_channel_layer()
        location_id = alert.detection_event.camera.location_id
        
        # Données de l'alerte pour WebSocket
        alert_data = {
            'id': alert.id,
            'title': alert.title,
            'message': alert.message,
            'priority': alert.priority,
            'status': alert.status,
            'created_at': alert.created_at.isoformat(),
            'detection_event': {
                'id': alert.detection_event.id,
                'event_type': alert.detection_event.event_type,
                'event_type_display': alert.detection_event.get_event_type_display(),
                'severity': alert.detection_event.severity,
                'confidence': alert.detection_event.confidence,
                'camera_name': alert.detection_event.camera.name,
                'zone_name': alert.detection_event.zone.name,
                'detected_at': alert.detection_event.detected_at.isoformat(),
            },
            'rule_name': alert.alert_rule.name,
        }
        
        # Envoyer aux groupes WebSocket
        async_to_sync(channel_layer.group_send)(
            f'alerts_{location_id}',
            {
                'type': 'new_alert',
                'alert': alert_data,
                'sound': alert.priority in ['high', 'critical'],
                'notification_popup': alert.priority == 'critical',
            }
        )
        
        # Envoyer au tableau de bord global
        async_to_sync(channel_layer.group_send)(
            'dashboard',
            {
                'type': 'dashboard_update',
                'update': {
                    'type': 'new_alert',
                    'alert': alert_data
                }
            }
        )
        
        logger.info(f"Alerte temps réel envoyée: {alert.id}")
        
    except Exception as e:
        logger.error(f"Erreur WebSocket alerte: {e}")


def is_within_time_restrictions(time_restrictions):
    """
    Vérifie si l'heure actuelle respecte les restrictions horaires
    """
    if not time_restrictions:
        return True
    
    now = timezone.now()
    current_time = now.time()
    current_weekday = now.weekday()  # 0 = Lundi, 6 = Dimanche
    
    # Vérifier les jours de la semaine
    allowed_days = time_restrictions.get('allowed_days')
    if allowed_days and current_weekday not in allowed_days:
        return False
    
    # Vérifier les heures
    start_time = time_restrictions.get('start_time')
    end_time = time_restrictions.get('end_time')
    
    if start_time and end_time:
        from datetime import time
        start = time.fromisoformat(start_time) if isinstance(start_time, str) else start_time
        end = time.fromisoformat(end_time) if isinstance(end_time, str) else end_time
        
        if start <= end:
            return start <= current_time <= end
        else:  # Période qui traverse minuit
            return current_time >= start or current_time <= end
    
    return True


def send_test_notification(channel, user):
    """
    Envoie une notification de test
    """
    try:
        # Créer une alerte de test fictive
        test_alert = type('TestAlert', (), {
            'id': 'TEST',
            'title': 'Test de notification',
            'message': f'Ceci est un test du canal {channel.name}',
            'priority': 'medium',
            'get_priority_display': lambda: 'Moyenne',
            'created_at': timezone.now(),
        })()
        
        # Ajouter un événement de détection fictif
        test_alert.detection_event = type('TestDetection', (), {
            'camera': type('TestCamera', (), {'name': 'Caméra Test'})(),
            'zone': type('TestZone', (), {'name': 'Zone Test'})(),
            'confidence': 0.95,
        })()
        
        # Créer un log de notification de test
        notification_log = NotificationLog.objects.create(
            alert=None,  # Pas d'alerte réelle
            channel=channel,
            recipient=user.email,
            status='pending',
            metadata={'test': True}
        )
        
        # Envoyer selon le type
        success = False
        if channel.channel_type == 'email':
            success = send_email_notification(test_alert, channel, user, notification_log)
        elif channel.channel_type == 'sms':
            success = send_sms_notification(test_alert, channel, user, notification_log)
        elif channel.channel_type == 'webhook':
            success = send_webhook_notification(test_alert, channel, user, notification_log)
        elif channel.channel_type == 'push':
            success = send_push_notification(test_alert, channel, user, notification_log)
        
        # Mettre à jour le statut
        notification_log.status = 'sent' if success else 'failed'
        if success:
            notification_log.sent_at = timezone.now()
        notification_log.save()
        
        return success
        
    except Exception as e:
        logger.error(f"Erreur test notification: {e}")
        return False 