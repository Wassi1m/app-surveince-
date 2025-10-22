#!/usr/bin/env python
"""
Script de création de notifications de test pour tester les filtres
"""

import os
import sys
import django
from datetime import datetime, timedelta
import random

# Configuration Django
sys.path.append('/home/user/Bureau/app suc')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'surveillance_system.settings')
django.setup()

from django.contrib.auth.models import User
from alerts.notification_service import notification_service

def create_test_notifications():
    """Créer diverses notifications de test"""
    
    print("🧪 Création de notifications de test pour les filtres...")
    
    try:
        admin_user = User.objects.get(username='admin')
    except User.DoesNotExist:
        print("❌ Utilisateur admin non trouvé")
        return
    
    # Notifications d'alertes avec différentes priorités
    alert_notifications = [
        {
            'title': 'Intrusion détectée - Zone sécurisée',
            'message': 'Une intrusion a été détectée dans la zone sécurisée du bâtiment principal. Intervention immédiate requise.',
            'type': 'alert',
            'priority': 1,  # Critique
            'action_url': '/monitoring/live/',
            'action_label': 'Voir caméras'
        },
        {
            'title': 'Mouvement suspect - Parking',
            'message': 'Activité suspecte détectée dans le parking. Une personne rôde autour des véhicules.',
            'type': 'alert',
            'priority': 2,  # Élevée
            'action_url': '/monitoring/live/',
            'action_label': 'Vérifier'
        },
        {
            'title': 'Détection de présence - Bureau',
            'message': 'Présence détectée dans le bureau après les heures d\'ouverture.',
            'type': 'alert',
            'priority': 3,  # Normale
            'action_url': '/alerts/',
            'action_label': 'Voir détails'
        },
        {
            'title': 'Mouvement mineur - Couloir',
            'message': 'Léger mouvement détecté dans le couloir, probablement un animal.',
            'type': 'alert',
            'priority': 4,  # Faible
        }
    ]
    
    # Notifications d'avertissement
    warning_notifications = [
        {
            'title': 'Caméra déconnectée',
            'message': 'La caméra CAM-03 ne répond plus. Vérification de la connexion nécessaire.',
            'type': 'warning',
            'priority': 2,
            'action_url': '/monitoring/cameras/',
            'action_label': 'Diagnostiquer'
        },
        {
            'title': 'Espace disque faible',
            'message': 'L\'espace disque disponible est inférieur à 10%. Nettoyage recommandé.',
            'type': 'warning',
            'priority': 3,
            'action_url': '/analytics/reports/',
            'action_label': 'Voir rapports'
        },
        {
            'title': 'Qualité vidéo dégradée',
            'message': 'La qualité vidéo de la caméra CAM-01 s\'est dégradée. Nettoyage de l\'objectif recommandé.',
            'type': 'warning',
            'priority': 4,
        }
    ]
    
    # Notifications d'erreur
    error_notifications = [
        {
            'title': 'Échec de sauvegarde',
            'message': 'La sauvegarde automatique des enregistrements a échoué. Vérification du système de stockage nécessaire.',
            'type': 'error',
            'priority': 1,
            'action_url': '/analytics/reports/',
            'action_label': 'Diagnostiquer'
        },
        {
            'title': 'Erreur de connexion IA',
            'message': 'Impossible de se connecter au service d\'analyse IA. Certaines fonctionnalités sont indisponibles.',
            'type': 'error',
            'priority': 2,
        },
        {
            'title': 'Erreur de synchronisation',
            'message': 'Erreur lors de la synchronisation des données avec le serveur distant.',
            'type': 'error',
            'priority': 3,
        }
    ]
    
    # Notifications de succès
    success_notifications = [
        {
            'title': 'Mise à jour installée',
            'message': 'La mise à jour du système de surveillance a été installée avec succès.',
            'type': 'success',
            'priority': 3,
        },
        {
            'title': 'Sauvegarde terminée',
            'message': 'La sauvegarde hebdomadaire des données a été effectuée avec succès.',
            'type': 'success',
            'priority': 4,
        },
        {
            'title': 'Nouvelle caméra ajoutée',
            'message': 'La caméra CAM-05 a été ajoutée et configurée avec succès dans le système.',
            'type': 'success',
            'priority': 3,
            'action_url': '/monitoring/cameras/',
            'action_label': 'Voir caméras'
        }
    ]
    
    # Notifications d'information
    info_notifications = [
        {
            'title': 'Rapport mensuel disponible',
            'message': 'Le rapport d\'activité mensuel est maintenant disponible dans la section analytics.',
            'type': 'info',
            'priority': 4,
            'action_url': '/analytics/reports/',
            'action_label': 'Voir rapport'
        },
        {
            'title': 'Nouvelle fonctionnalité',
            'message': 'Une nouvelle fonctionnalité de détection de visages a été ajoutée au système.',
            'type': 'info',
            'priority': 3,
        },
        {
            'title': 'Statistiques de performance',
            'message': 'Les statistiques de performance du système sont maintenant disponibles en temps réel.',
            'type': 'info',
            'priority': 4,
            'action_url': '/dashboard/',
            'action_label': 'Voir dashboard'
        }
    ]
    
    # Notifications système
    system_notifications = [
        {
            'title': 'Redémarrage programmé',
            'message': 'Un redémarrage du système est programmé ce soir à 3h00 pour maintenance.',
            'type': 'system',
            'priority': 2,
            'expires_in_hours': 12
        },
        {
            'title': 'Mise à jour de sécurité',
            'message': 'Une mise à jour de sécurité critique sera appliquée dans les prochaines 24h.',
            'type': 'system',
            'priority': 1,
            'expires_in_hours': 24
        },
        {
            'title': 'Optimisation des performances',
            'message': 'Le système a été optimisé pour de meilleures performances de détection.',
            'type': 'system',
            'priority': 4,
        }
    ]
    
    # Créer toutes les notifications
    all_notifications = (
        alert_notifications + warning_notifications + error_notifications + 
        success_notifications + info_notifications + system_notifications
    )
    
    print(f"\n📝 Création de {len(all_notifications)} notifications de test...")
    
    created_count = 0
    for i, notif_data in enumerate(all_notifications):
        try:
            # Varier les destinataires
            user = admin_user if i % 3 != 0 else None
            user_group = None if user else 'all'
            
            notification = notification_service.create_notification(
                title=notif_data['title'],
                message=notif_data['message'],
                notification_type=notif_data['type'],
                priority=notif_data['priority'],
                user=user,
                user_group=user_group,
                action_url=notif_data.get('action_url'),
                action_label=notif_data.get('action_label'),
                expires_in_hours=notif_data.get('expires_in_hours')
            )
            
            # Marquer quelques notifications comme lues (pour tester le filtre)
            if i % 5 == 0:  # 20% des notifications marquées comme lues
                notification.mark_as_read()
            
            created_count += 1
            print(f"✅ {notif_data['type'].upper()}: {notif_data['title']}")
            
        except Exception as e:
            print(f"❌ Erreur création notification: {e}")
    
    print(f"\n🎉 {created_count} notifications de test créées !")
    
    # Statistiques par type
    from alerts.models_notifications import Notification
    
    print("\n📊 Répartition par type:")
    for notif_type, display_name in Notification.NOTIFICATION_TYPES:
        count = Notification.objects.filter(notification_type=notif_type).count()
        print(f"   • {display_name}: {count}")
    
    print("\n📊 Répartition par priorité:")
    for priority, display_name in Notification.PRIORITY_LEVELS:
        count = Notification.objects.filter(priority=priority).count()
        print(f"   • {display_name}: {count}")
    
    total_notifications = Notification.objects.count()
    unread_notifications = Notification.objects.filter(read_at__isnull=True).count()
    
    print(f"\n📈 Statistiques globales:")
    print(f"   • Total: {total_notifications}")
    print(f"   • Non lues: {unread_notifications}")
    print(f"   • Lues: {total_notifications - unread_notifications}")
    
    print(f"\n🚀 Testez les filtres : http://127.0.0.1:8002/alerts/notifications/")

if __name__ == '__main__':
    create_test_notifications()
