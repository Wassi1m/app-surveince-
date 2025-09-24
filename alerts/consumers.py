import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Alert, AlertRule, NotificationLog
from monitoring.models import DetectionEvent, Location
from datetime import datetime, timedelta
import logging

logger = logging.getLogger('alerts')


class AlertConsumer(AsyncWebsocketConsumer):
    """Consumer pour les alertes en temps réel par lieu"""
    
    async def connect(self):
        self.location_id = self.scope['url_route']['kwargs']['location_id']
        self.alert_group_name = f'alerts_{self.location_id}'
        
        await self.channel_layer.group_add(
            self.alert_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Envoyer les alertes récentes
        await self.send_recent_alerts()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.alert_group_name,
            self.channel_name
        )
    
    @database_sync_to_async
    def get_recent_alerts(self):
        """Récupère les alertes récentes pour ce lieu"""
        from django.utils import timezone
        
        last_24h = timezone.now() - timedelta(hours=24)
        
        alerts = Alert.objects.filter(
            detection_event__camera__location_id=self.location_id,
            created_at__gte=last_24h,
            status__in=['pending', 'sent', 'acknowledged']
        ).select_related(
            'detection_event', 
            'detection_event__camera', 
            'detection_event__zone',
            'alert_rule'
        ).order_by('-created_at')[:50]
        
        alerts_data = []
        for alert in alerts:
            alerts_data.append({
                'id': alert.id,
                'title': alert.title,
                'message': alert.message,
                'priority': alert.priority,
                'priority_display': alert.get_priority_display(),
                'status': alert.status,
                'status_display': alert.get_status_display(),
                'created_at': alert.created_at.isoformat(),
                'age_seconds': int(alert.age_seconds),
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
                'response_time': alert.response_time_seconds,
            })
        
        return alerts_data
    
    async def send_recent_alerts(self):
        """Envoie les alertes récentes au client"""
        alerts = await self.get_recent_alerts()
        await self.send(text_data=json.dumps({
            'type': 'recent_alerts',
            'alerts': alerts
        }))
    
    async def receive(self, text_data):
        """Traiter les messages reçus du client"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'acknowledge_alert':
                await self.acknowledge_alert(data)
            elif message_type == 'resolve_alert':
                await self.resolve_alert(data)
            elif message_type == 'get_alert_details':
                await self.send_alert_details(data)
            
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Format JSON invalide'
            }))
    
    @database_sync_to_async
    def acknowledge_alert(self, data):
        """Marque une alerte comme accusée de réception"""
        try:
            alert_id = data.get('alert_id')
            user_id = self.scope.get('user', {}).get('id')
            
            if not user_id:
                return {'success': False, 'error': 'Utilisateur non authentifié'}
            
            alert = Alert.objects.get(id=alert_id)
            if alert.status == 'pending' or alert.status == 'sent':
                alert.status = 'acknowledged'
                alert.acknowledged_at = timezone.now()
                alert.acknowledged_by_id = user_id
                alert.save()
                
                return {'success': True, 'alert_id': alert_id}
            
        except Alert.DoesNotExist:
            return {'success': False, 'error': 'Alerte introuvable'}
        except Exception as e:
            logger.error(f"Erreur acknowledgement alerte: {e}")
            return {'success': False, 'error': str(e)}
    
    @database_sync_to_async
    def resolve_alert(self, data):
        """Marque une alerte comme résolue"""
        try:
            alert_id = data.get('alert_id')
            user_id = self.scope.get('user', {}).get('id')
            
            if not user_id:
                return {'success': False, 'error': 'Utilisateur non authentifié'}
            
            alert = Alert.objects.get(id=alert_id)
            alert.status = 'resolved'
            alert.resolved_at = timezone.now()
            alert.resolved_by_id = user_id
            alert.save()
            
            return {'success': True, 'alert_id': alert_id}
            
        except Alert.DoesNotExist:
            return {'success': False, 'error': 'Alerte introuvable'}
        except Exception as e:
            logger.error(f"Erreur résolution alerte: {e}")
            return {'success': False, 'error': str(e)}
    
    async def new_alert(self, event):
        """Diffuser une nouvelle alerte aux clients connectés"""
        await self.send(text_data=json.dumps({
            'type': 'new_alert',
            'alert': event['alert'],
            'sound': event.get('sound', True),
            'notification_popup': event.get('notification_popup', True)
        }))
    
    async def alert_update(self, event):
        """Diffuser une mise à jour d'alerte"""
        await self.send(text_data=json.dumps({
            'type': 'alert_update',
            'alert': event['alert']
        }))


class NotificationConsumer(AsyncWebsocketConsumer):
    """Consumer pour les notifications personnelles d'un utilisateur"""
    
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.notification_group_name = f'notifications_{self.user_id}'
        
        # Vérifier que l'utilisateur peut accéder à ces notifications
        user = self.scope.get('user')
        if not user or str(user.id) != self.user_id:
            await self.close()
            return
        
        await self.channel_layer.group_add(
            self.notification_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Envoyer les notifications non lues
        await self.send_unread_notifications()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.notification_group_name,
            self.channel_name
        )
    
    @database_sync_to_async
    def get_unread_notifications(self):
        """Récupère les notifications non lues pour cet utilisateur"""
        try:
            user = User.objects.get(id=self.user_id)
            
            # Récupérer les alertes non lues destinées à cet utilisateur
            from alerts.models import AlertRecipient
            
            recipients = AlertRecipient.objects.filter(
                user=user,
                is_active=True
            ).values_list('location_id', flat=True)
            
            notifications = NotificationLog.objects.filter(
                alert__detection_event__camera__location_id__in=recipients,
                status__in=['pending', 'sent', 'delivered'],
                recipient=user.email  # ou autre identifiant
            ).select_related(
                'alert', 
                'alert__detection_event', 
                'channel'
            ).order_by('-sent_at')[:20]
            
            notifications_data = []
            for notif in notifications:
                notifications_data.append({
                    'id': notif.id,
                    'alert_id': notif.alert.id,
                    'alert_title': notif.alert.title,
                    'alert_priority': notif.alert.priority,
                    'channel_type': notif.channel.channel_type,
                    'status': notif.status,
                    'sent_at': notif.sent_at.isoformat() if notif.sent_at else None,
                    'error_message': notif.error_message,
                })
            
            return notifications_data
            
        except User.DoesNotExist:
            return []
    
    async def send_unread_notifications(self):
        """Envoie les notifications non lues"""
        notifications = await self.get_unread_notifications()
        await self.send(text_data=json.dumps({
            'type': 'unread_notifications',
            'notifications': notifications,
            'count': len(notifications)
        }))
    
    async def receive(self, text_data):
        """Traiter les messages reçus du client"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'mark_read':
                await self.mark_notification_read(data)
            elif message_type == 'get_notification_history':
                await self.send_notification_history(data)
            
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Format JSON invalide'
            }))
    
    @database_sync_to_async
    def mark_notification_read(self, data):
        """Marque une notification comme lue"""
        try:
            notification_id = data.get('notification_id')
            
            notification = NotificationLog.objects.get(
                id=notification_id,
                recipient__contains=self.user_id  # Vérification de sécurité
            )
            
            if notification.status in ['sent', 'delivered']:
                notification.status = 'read'
                notification.save()
                
                return {'success': True, 'notification_id': notification_id}
                
        except NotificationLog.DoesNotExist:
            return {'success': False, 'error': 'Notification introuvable'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    async def new_notification(self, event):
        """Recevoir une nouvelle notification et l'envoyer au client"""
        await self.send(text_data=json.dumps({
            'type': 'new_notification',
            'notification': event['notification'],
            'show_popup': event.get('show_popup', True),
            'play_sound': event.get('play_sound', True)
        }))
    
    async def notification_update(self, event):
        """Recevoir une mise à jour de notification"""
        await self.send(text_data=json.dumps({
            'type': 'notification_update',
            'notification': event['notification']
        })) 