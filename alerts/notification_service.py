"""
Service de notifications avancé pour le système de surveillance
"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.db.models import Q

from .models import (
    Notification, NotificationChannel, NotificationTemplate, 
    NotificationPreference, Alert
)

logger = logging.getLogger(__name__)


class NotificationService:
    """Service principal pour la gestion des notifications"""
    
    def __init__(self):
        self.channels = {
            'email': self._send_email,
            'in_app': self._send_in_app,
            'webhook': self._send_webhook,
            'slack': self._send_slack,
        }
    
    def create_notification(
        self,
        title: str,
        message: str,
        notification_type: str = 'info',
        priority: int = 3,
        user: Optional[User] = None,
        user_group: Optional[str] = None,
        alert: Optional[Alert] = None,
        metadata: Optional[Dict] = None,
        action_url: Optional[str] = None,
        action_label: Optional[str] = None,
        expires_in_hours: Optional[int] = None
    ) -> Notification:
        """Créer une nouvelle notification"""
        
        expires_at = None
        if expires_in_hours:
            expires_at = timezone.now() + timedelta(hours=expires_in_hours)
        
        notification = Notification.objects.create(
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            user=user,
            user_group=user_group or '',
            alert=alert,
            metadata=metadata or {},
            action_url=action_url or '',
            action_label=action_label or '',
            expires_at=expires_at
        )
        
        # Envoyer immédiatement si priorité élevée
        if priority <= 2:
            self.send_notification(notification)
        
        logger.info(f"Notification créée: {notification.id} - {title}")
        return notification
    
    def send_notification(self, notification: Notification) -> bool:
        """Envoyer une notification via les canaux appropriés"""
        
        if notification.status != 'pending':
            return False
        
        success = False
        channels_used = []
        
        # Déterminer les destinataires
        users = self._get_notification_users(notification)
        
        for user in users:
            # Obtenir les préférences utilisateur
            preferences = self._get_user_preferences(user)
            
            # Vérifier les heures silencieuses
            if self._is_quiet_hours(preferences):
                continue
            
            # Vérifier la priorité minimale
            if notification.priority > preferences.min_priority:
                continue
            
            # Obtenir les canaux pour ce type de notification
            channels = self._get_user_channels(user, notification.notification_type)
            
            # Envoyer via chaque canal
            for channel in channels:
                try:
                    if self._send_via_channel(notification, channel, user):
                        channels_used.append(channel.name)
                        success = True
                except Exception as e:
                    logger.error(f"Erreur envoi notification {notification.id} via {channel.name}: {e}")
        
        # Mettre à jour le statut
        notification.channels_sent = list(set(channels_used))
        notification.status = 'sent' if success else 'failed'
        notification.sent_at = timezone.now()
        notification.save()
        
        return success
    
    def _get_notification_users(self, notification: Notification) -> List[User]:
        """Obtenir la liste des utilisateurs destinataires"""
        users = []
        
        if notification.user:
            users.append(notification.user)
        elif notification.user_group:
            # Logique pour les groupes d'utilisateurs
            if notification.user_group == 'admins':
                users.extend(User.objects.filter(is_staff=True))
            elif notification.user_group == 'security':
                users.extend(User.objects.filter(groups__name='Security'))
            elif notification.user_group == 'all':
                users.extend(User.objects.filter(is_active=True))
        
        return users
    
    def _get_user_preferences(self, user: User) -> NotificationPreference:
        """Obtenir ou créer les préférences utilisateur"""
        preferences, created = NotificationPreference.objects.get_or_create(
            user=user,
            defaults={
                'digest_frequency': 'immediate',
                'min_priority': 3,
                'enable_sound': True,
                'enable_vibration': True,
                'enable_email_digest': True,
            }
        )
        return preferences
    
    def _is_quiet_hours(self, preferences: NotificationPreference) -> bool:
        """Vérifier si nous sommes dans les heures silencieuses"""
        if not preferences.quiet_hours_start or not preferences.quiet_hours_end:
            return False
        
        now = timezone.now().time()
        start = preferences.quiet_hours_start
        end = preferences.quiet_hours_end
        
        if start <= end:
            return start <= now <= end
        else:  # Période qui traverse minuit
            return now >= start or now <= end
    
    def _get_user_channels(self, user: User, notification_type: str) -> List[NotificationChannel]:
        """Obtenir les canaux de notification pour un utilisateur"""
        preferences = self._get_user_preferences(user)
        
        if notification_type in ['alert', 'error']:
            return list(preferences.alert_channels.filter(is_active=True))
        elif notification_type == 'system':
            return list(preferences.system_channels.filter(is_active=True))
        else:
            return list(preferences.report_channels.filter(is_active=True))
    
    def _send_via_channel(self, notification: Notification, channel: NotificationChannel, user: User) -> bool:
        """Envoyer une notification via un canal spécifique"""
        handler = self.channels.get(channel.channel_type)
        if not handler:
            logger.warning(f"Canal non supporté: {channel.channel_type}")
            return False
        
        return handler(notification, channel, user)
    
    def _send_email(self, notification: Notification, channel: NotificationChannel, user: User) -> bool:
        """Envoyer une notification par email"""
        try:
            subject = f"[Surveillance IA] {notification.title}"
            
            # Utiliser un template si disponible
            template = NotificationTemplate.objects.filter(
                template_type='alert_created' if notification.notification_type == 'alert' else 'system_status',
                is_active=True
            ).first()
            
            if template:
                context = {
                    'user_name': user.get_full_name() or user.username,
                    'title': notification.title,
                    'message': notification.message,
                    'priority': notification.get_priority_display(),
                    'created_at': notification.created_at.strftime('%d/%m/%Y %H:%M'),
                    'action_url': notification.action_url,
                    'action_label': notification.action_label,
                }
                subject, message = template.render(context)
            else:
                message = f"""
Bonjour {user.get_full_name() or user.username},

{notification.message}

Priorité: {notification.get_priority_display()}
Date: {notification.created_at.strftime('%d/%m/%Y à %H:%M')}

{f'Action: {notification.action_url}' if notification.action_url else ''}

---
Système de Surveillance IA
                """.strip()
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False
            )
            
            logger.info(f"Email envoyé à {user.email} pour notification {notification.id}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi email: {e}")
            return False
    
    def _send_in_app(self, notification: Notification, channel: NotificationChannel, user: User) -> bool:
        """Notification in-app (déjà créée en base)"""
        return True
    
    def _send_webhook(self, notification: Notification, channel: NotificationChannel, user: User) -> bool:
        """Envoyer une notification via webhook"""
        try:
            import requests
            
            config = channel.configuration
            webhook_url = config.get('url')
            
            if not webhook_url:
                return False
            
            payload = {
                'title': notification.title,
                'message': notification.message,
                'type': notification.notification_type,
                'priority': notification.priority,
                'user': user.username,
                'timestamp': notification.created_at.isoformat(),
                'metadata': notification.metadata
            }
            
            headers = config.get('headers', {})
            
            response = requests.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Erreur webhook: {e}")
            return False
    
    def _send_slack(self, notification: Notification, channel: NotificationChannel, user: User) -> bool:
        """Envoyer une notification Slack"""
        try:
            import requests
            
            config = channel.configuration
            webhook_url = config.get('webhook_url')
            
            if not webhook_url:
                return False
            
            # Couleur selon le type
            color_map = {
                'error': '#ff0000',
                'warning': '#ff9900',
                'success': '#00ff00',
                'info': '#0099ff',
                'alert': '#ff3300'
            }
            
            payload = {
                'text': f"🚨 {notification.title}",
                'attachments': [{
                    'color': color_map.get(notification.notification_type, '#0099ff'),
                    'fields': [
                        {
                            'title': 'Message',
                            'value': notification.message,
                            'short': False
                        },
                        {
                            'title': 'Priorité',
                            'value': notification.get_priority_display(),
                            'short': True
                        },
                        {
                            'title': 'Utilisateur',
                            'value': user.get_full_name() or user.username,
                            'short': True
                        }
                    ],
                    'footer': 'Surveillance IA',
                    'ts': int(notification.created_at.timestamp())
                }]
            }
            
            if notification.action_url:
                payload['attachments'][0]['actions'] = [{
                    'type': 'button',
                    'text': notification.action_label or 'Voir',
                    'url': notification.action_url
                }]
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Erreur Slack: {e}")
            return False
    
    def get_user_notifications(self, user: User, unread_only: bool = False, limit: int = 50) -> List[Notification]:
        """Obtenir les notifications d'un utilisateur"""
        queryset = Notification.objects.filter(
            Q(user=user) | Q(user_group__in=['all', 'admins'] if user.is_staff else ['all'])
        )
        
        # Filtrer par entreprise si l'utilisateur n'est pas owner
        if hasattr(user, 'company_profile') and user.company_profile:
            if not user.company_profile.is_owner:
                # Pour les utilisateurs non-owner : notifications de leur entreprise + notifications owner ciblées
                queryset = queryset.filter(
                    Q(alert__company=user.company_profile.company) |  # Notifications d'alertes de l'entreprise
                    Q(alert__isnull=True, metadata__created_by_owner=True) |  # Notifications owner générales
                    Q(alert__isnull=True, metadata__target_company_id=user.company_profile.company.id)  # Notifications owner ciblées
                )
            # Si l'utilisateur est owner, pas de filtrage - il voit toutes les notifications
        
        if unread_only:
            queryset = queryset.filter(read_at__isnull=True)
        
        # Exclure les notifications expirées
        queryset = queryset.filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
        )
        
        return list(queryset.order_by('-created_at')[:limit])
    
    def mark_as_read(self, notification_id: int, user: User) -> bool:
        """Marquer une notification comme lue"""
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user=user
            )
            notification.mark_as_read()
            return True
        except Notification.DoesNotExist:
            return False
    
    def cleanup_old_notifications(self, days: int = 30):
        """Nettoyer les anciennes notifications"""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        # Supprimer les notifications lues anciennes
        deleted_count = Notification.objects.filter(
            read_at__lt=cutoff_date
        ).delete()[0]
        
        # Supprimer les notifications expirées
        expired_count = Notification.objects.filter(
            expires_at__lt=timezone.now()
        ).delete()[0]
        
        logger.info(f"Nettoyage: {deleted_count} notifications anciennes, {expired_count} expirées")
        return deleted_count + expired_count


# Instance globale du service
notification_service = NotificationService()
