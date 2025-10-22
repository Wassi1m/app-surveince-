#!/usr/bin/env python
"""
Script de création de données de démonstration pour le système de notifications
"""

import os
import sys
import django
from datetime import datetime, timedelta

# Configuration Django
sys.path.append('/home/user/Bureau/app suc')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'surveillance_system.settings')
django.setup()

from django.contrib.auth.models import User
from alerts.models_notifications import NotificationChannel, NotificationTemplate, Notification, NotificationPreference
from alerts.notification_service import notification_service

def create_demo_data():
    """Créer des données de démonstration"""
    
    print("🚀 Création des données de démonstration pour les notifications...")
    
    # 1. Créer des canaux de notification
    print("\n📡 Création des canaux de notification...")
    
    email_channel, created = NotificationChannel.objects.get_or_create(
        name="Email Principal",
        defaults={
            'channel_type': 'email',
            'configuration': {
                'smtp_host': 'localhost',
                'smtp_port': 587,
                'use_tls': True
            },
            'is_active': True
        }
    )
    if created:
        print(f"✅ Canal email créé: {email_channel}")
    
    in_app_channel, created = NotificationChannel.objects.get_or_create(
        name="Notifications In-App",
        defaults={
            'channel_type': 'in_app',
            'configuration': {},
            'is_active': True
        }
    )
    if created:
        print(f"✅ Canal in-app créé: {in_app_channel}")
    
    webhook_channel, created = NotificationChannel.objects.get_or_create(
        name="Webhook Test",
        defaults={
            'channel_type': 'webhook',
            'configuration': {
                'url': 'https://webhook.site/test',
                'headers': {
                    'Content-Type': 'application/json'
                }
            },
            'is_active': False  # Désactivé par défaut
        }
    )
    if created:
        print(f"✅ Canal webhook créé: {webhook_channel}")
    
    # 2. Créer des templates de notification
    print("\n📝 Création des templates de notification...")
    
    alert_template, created = NotificationTemplate.objects.get_or_create(
        name="Alerte de Sécurité",
        template_type="alert_created",
        defaults={
            'subject_template': '🚨 [ALERTE] {{title}}',
            'body_template': '''Bonjour {{user_name}},

Une nouvelle alerte de sécurité a été détectée :

📍 **Titre :** {{title}}
📋 **Message :** {{message}}
⚠️  **Priorité :** {{priority}}
🕒 **Date :** {{created_at}}

{{#action_url}}
👉 **Action requise :** [{{action_label}}]({{action_url}})
{{/action_url}}

---
🤖 Système de Surveillance IA
''',
            'variables': {
                'user_name': 'Nom de l\'utilisateur',
                'title': 'Titre de l\'alerte',
                'message': 'Message de l\'alerte',
                'priority': 'Niveau de priorité',
                'created_at': 'Date de création',
                'action_url': 'URL d\'action (optionnel)',
                'action_label': 'Libellé du bouton d\'action'
            },
            'is_active': True
        }
    )
    if created:
        print(f"✅ Template alerte créé: {alert_template}")
    
    system_template, created = NotificationTemplate.objects.get_or_create(
        name="Notification Système",
        template_type="system_status",
        defaults={
            'subject_template': '🔧 [SYSTÈME] {{title}}',
            'body_template': '''Bonjour {{user_name}},

Information système :

📋 **Message :** {{message}}
🕒 **Date :** {{created_at}}

---
🤖 Système de Surveillance IA
''',
            'variables': {
                'user_name': 'Nom de l\'utilisateur',
                'title': 'Titre de la notification',
                'message': 'Message de la notification',
                'created_at': 'Date de création'
            },
            'is_active': True
        }
    )
    if created:
        print(f"✅ Template système créé: {system_template}")
    
    # 3. Configurer les préférences pour l'utilisateur admin
    print("\n👤 Configuration des préférences utilisateur...")
    
    try:
        admin_user = User.objects.get(username='admin')
        
        preferences, created = NotificationPreference.objects.get_or_create(
            user=admin_user,
            defaults={
                'digest_frequency': 'immediate',
                'min_priority': 3,
                'enable_sound': True,
                'enable_vibration': True,
                'enable_email_digest': True,
            }
        )
        
        # Associer les canaux
        preferences.alert_channels.add(email_channel, in_app_channel)
        preferences.system_channels.add(in_app_channel)
        preferences.report_channels.add(email_channel)
        
        if created:
            print(f"✅ Préférences créées pour {admin_user.username}")
        else:
            print(f"✅ Préférences mises à jour pour {admin_user.username}")
            
    except User.DoesNotExist:
        print("⚠️  Utilisateur admin non trouvé, création des préférences ignorée")
    
    # 4. Créer des notifications de démonstration
    print("\n🔔 Création de notifications de démonstration...")
    
    # Obtenir l'utilisateur admin
    try:
        admin_user = User.objects.get(username='admin')
        
        # Notification d'information
        notification1 = notification_service.create_notification(
            title="Système de notifications activé",
            message="Le nouveau système de notifications avancé est maintenant opérationnel. Vous pouvez configurer vos préférences dans le centre de notifications.",
            notification_type='success',
            priority=3,
            user=admin_user,
            action_url='/alerts/notifications/',
            action_label='Configurer'
        )
        print(f"✅ Notification créée: {notification1.title}")
        
        # Notification d'alerte
        notification2 = notification_service.create_notification(
            title="Détection de mouvement suspect",
            message="Un mouvement suspect a été détecté dans la zone d'entrée principale. Vérification recommandée.",
            notification_type='alert',
            priority=2,
            user=admin_user,
            action_url='/monitoring/live/',
            action_label='Voir la caméra',
            expires_in_hours=24
        )
        print(f"✅ Notification d'alerte créée: {notification2.title}")
        
        # Notification système
        notification3 = notification_service.create_notification(
            title="Mise à jour système",
            message="Le système de surveillance a été mis à jour avec de nouvelles fonctionnalités d'IA.",
            notification_type='system',
            priority=4,
            user=admin_user
        )
        print(f"✅ Notification système créée: {notification3.title}")
        
        # Notification pour tous les utilisateurs
        notification4 = notification_service.create_notification(
            title="Maintenance programmée",
            message="Une maintenance du système est programmée ce soir de 2h à 4h. Aucune interruption de service n'est prévue.",
            notification_type='warning',
            priority=3,
            user_group='all',
            expires_in_hours=48
        )
        print(f"✅ Notification globale créée: {notification4.title}")
        
    except User.DoesNotExist:
        print("⚠️  Utilisateur admin non trouvé, notifications de démonstration ignorées")
    
    print("\n🎉 Données de démonstration créées avec succès !")
    print("\n📋 Résumé :")
    print(f"   • {NotificationChannel.objects.count()} canaux de notification")
    print(f"   • {NotificationTemplate.objects.count()} templates")
    print(f"   • {NotificationPreference.objects.count()} préférences utilisateur")
    print(f"   • {Notification.objects.count()} notifications")
    
    print("\n🚀 Accédez au centre de notifications : http://127.0.0.1:8002/alerts/notifications/")

if __name__ == '__main__':
    create_demo_data()
