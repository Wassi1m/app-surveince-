#!/usr/bin/env python3
"""
Script de génération de données de démonstration
pour le système de surveillance intelligente
"""
import os
import django
import random
from datetime import datetime, timedelta
from django.utils import timezone

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'surveillance_system.settings')
django.setup()


from django.contrib.auth.models import User
from monitoring.models import Location, Zone, Camera, DetectionEvent, VideoRecording
from alerts.models import AlertRule, NotificationChannel, AlertRecipient
from analytics.models import HeatMapData, StatisticsSummary, PerformanceMetric


def create_demo_data():
    """Crée des données de démonstration"""
    print("🚀 Création des données de démonstration...")
    
    # Créer des utilisateurs de démonstration
    create_demo_users()
    
    # Créer des lieux et zones
    locations = create_demo_locations()
    
    # Créer des caméras
    cameras = create_demo_cameras(locations)
    
    # Créer des canaux de notification
    channels = create_demo_channels()
    
    # Créer des règles d'alerte
    rules = create_demo_alert_rules(locations)
    
    # Créer des détections simulées
    create_demo_detections(cameras)
    
    # Créer des données de carte de chaleur
    create_demo_heatmap_data(locations)
    
    print("✅ Données de démonstration créées avec succès!")
    print("\n📊 Résumé:")
    print(f"- Lieux: {Location.objects.count()}")
    print(f"- Zones: {Zone.objects.count()}")
    print(f"- Caméras: {Camera.objects.count()}")
    print(f"- Détections: {DetectionEvent.objects.count()}")
    print(f"- Règles d'alerte: {AlertRule.objects.count()}")
    print(f"- Canaux de notification: {NotificationChannel.objects.count()}")
    
    print("\n🔐 Comptes de connexion:")
    print("- Admin: admin / admin123")
    print("- Sécurité: security / security123")
    print("- Manager: manager / manager123")
    
    print("\n🌐 Accès à l'application:")
    print("- http://127.0.0.1:8000/ (Interface principale)")
    print("- http://127.0.0.1:8000/admin/ (Administration)")


def create_demo_users():
    """Crée des utilisateurs de démonstration"""
    users_data = [
        {'username': 'security', 'email': 'security@surveillance.local', 'password': 'security123', 'first_name': 'Agent', 'last_name': 'Sécurité'},
        {'username': 'manager', 'email': 'manager@surveillance.local', 'password': 'manager123', 'first_name': 'Manager', 'last_name': 'Surveillance'},
    ]
    
    for user_data in users_data:
        user, created = User.objects.get_or_create(
            username=user_data['username'],
            defaults={
                'email': user_data['email'],
                'first_name': user_data['first_name'],
                'last_name': user_data['last_name'],
                'is_staff': True if user_data['username'] == 'manager' else False,
            }
        )
        if created:
            user.set_password(user_data['password'])
            user.save()
            print(f"👤 Utilisateur créé: {user.username}")


def create_demo_locations():
    """Crée des lieux de démonstration"""
    locations_data = [
        {
            'name': 'SuperMarché Central',
            'address': '123 Rue du Commerce, 75001 Paris',
            'description': 'Supermarché de 1500m² avec 8 rayons principaux',
        },
        {
            'name': 'Entrepôt Logistique Nord',
            'address': '45 Zone Industrielle, 95100 Argenteuil',
            'description': 'Entrepôt de stockage et distribution de 5000m²',
        },
        {
            'name': 'Boutique Premium Center',
            'address': '78 Avenue des Champs, 75008 Paris',
            'description': 'Boutique de vêtements haut de gamme 300m²',
        }
    ]
    
    locations = []
    for loc_data in locations_data:
        location, created = Location.objects.get_or_create(
            name=loc_data['name'],
            defaults=loc_data
        )
        if created:
            print(f"📍 Lieu créé: {location.name}")
            
            # Créer des zones pour ce lieu
            zones_data = get_zones_for_location(location.name)
            for zone_data in zones_data:
                zone, zone_created = Zone.objects.get_or_create(
                    location=location,
                    name=zone_data['name'],
                    defaults=zone_data
                )
                if zone_created:
                    print(f"  🏢 Zone créée: {zone.name} ({zone.risk_level})")
        
        locations.append(location)
    
    return locations


def get_zones_for_location(location_name):
    """Retourne les zones selon le type de lieu"""
    if 'SuperMarché' in location_name:
        return [
            {'name': 'Entrée Principale', 'risk_level': 'high', 'coordinates': [0, 0, 100, 50], 'description': 'Zone d\'entrée et sortie'},
            {'name': 'Caisses', 'risk_level': 'high', 'coordinates': [100, 0, 200, 50], 'description': 'Espace des caisses enregistreuses'},
            {'name': 'Rayon Électronique', 'risk_level': 'medium', 'coordinates': [0, 50, 100, 100], 'description': 'Produits électroniques'},
            {'name': 'Rayon Alimentaire', 'risk_level': 'low', 'coordinates': [100, 50, 200, 100], 'description': 'Produits alimentaires'},
            {'name': 'Réserve', 'risk_level': 'medium', 'coordinates': [200, 0, 300, 100], 'description': 'Zone de stockage'},
        ]
    elif 'Entrepôt' in location_name:
        return [
            {'name': 'Quai de Chargement', 'risk_level': 'high', 'coordinates': [0, 0, 150, 50], 'description': 'Zone de chargement des camions'},
            {'name': 'Zone Stockage A', 'risk_level': 'medium', 'coordinates': [0, 50, 75, 150], 'description': 'Stockage produits A'},
            {'name': 'Zone Stockage B', 'risk_level': 'medium', 'coordinates': [75, 50, 150, 150], 'description': 'Stockage produits B'},
            {'name': 'Bureau Administration', 'risk_level': 'low', 'coordinates': [150, 0, 200, 50], 'description': 'Bureaux administratifs'},
        ]
    else:  # Boutique
        return [
            {'name': 'Vitrine', 'risk_level': 'high', 'coordinates': [0, 0, 80, 30], 'description': 'Espace vitrine'},
            {'name': 'Espace Vente', 'risk_level': 'medium', 'coordinates': [0, 30, 80, 80], 'description': 'Zone de vente principale'},
            {'name': 'Caisse', 'risk_level': 'high', 'coordinates': [80, 0, 100, 30], 'description': 'Zone de paiement'},
            {'name': 'Réserve', 'risk_level': 'low', 'coordinates': [80, 30, 100, 80], 'description': 'Stockage boutique'},
        ]


def create_demo_cameras(locations):
    """Crée des caméras de démonstration"""
    cameras = []
    camera_id = 1
    
    for location in locations:
        zones = Zone.objects.filter(location=location)
        
        for i, zone in enumerate(zones):
            camera = Camera.objects.create(
                location=location,
                zone=zone,
                name=f"CAM-{camera_id:02d}-{zone.name.replace(' ', '')}",
                ip_address=f"192.168.1.{100 + camera_id}",
                port=554,
                username="admin",
                password="admin123",
                stream_url=f"rtsp://admin:admin123@192.168.1.{100 + camera_id}:554/stream1",
                status=random.choice(['online', 'online', 'online', 'offline']),  # 75% online
                resolution="1920x1080",
                fps=30,
                is_ai_enabled=True,
                last_seen=timezone.now() - timedelta(minutes=random.randint(0, 30))
            )
            cameras.append(camera)
            camera_id += 1
            print(f"📹 Caméra créée: {camera.name} ({camera.status})")
    
    return cameras


def create_demo_channels():
    """Crée des canaux de notification de démonstration"""
    channels_data = [
        {
            'name': 'Email Sécurité',
            'channel_type': 'email',
            'configuration': {
                'from_email': 'alerts@surveillance.local',
                'smtp_host': 'smtp.gmail.com',
                'smtp_port': 587
            }
        },
        {
            'name': 'SMS Urgence',
            'channel_type': 'sms',
            'configuration': {
                'api_key': 'demo_api_key',
                'sender': 'SURVEILLANCE'
            }
        },
        {
            'name': 'Webhook Central',
            'channel_type': 'webhook',
            'configuration': {
                'webhook_url': 'https://hooks.example.com/surveillance',
                'headers': {'Authorization': 'Bearer demo_token'}
            }
        },
        {
            'name': 'Slack Sécurité',
            'channel_type': 'slack',
            'configuration': {
                'webhook_url': 'https://hooks.slack.com/services/demo',
                'channel': '#surveillance'
            }
        }
    ]
    
    channels = []
    for channel_data in channels_data:
        channel, created = NotificationChannel.objects.get_or_create(
            name=channel_data['name'],
            defaults=channel_data
        )
        if created:
            print(f"📢 Canal créé: {channel.name} ({channel.channel_type})")
        channels.append(channel)
    
    return channels


def create_demo_alert_rules(locations):
    """Crée des règles d'alerte de démonstration"""
    admin_user = User.objects.get(username='admin')
    
    rules_data = [
        {
            'name': 'Vol Détecté',
            'description': 'Alerte en cas de détection de vol',
            'trigger_type': 'detection_type',
            'trigger_conditions': {
                'event_types': ['theft'],
                'min_confidence': 0.7
            },
            'priority': 1,
            'cooldown_minutes': 2,
        },
        {
            'name': 'Intrusion Nocturne',
            'description': 'Détection d\'intrusion en dehors des heures d\'ouverture',
            'trigger_type': 'time_window',
            'trigger_conditions': {
                'event_types': ['intrusion', 'suspicious'],
                'time_windows': [{'start': 20, 'end': 7}]
            },
            'priority': 1,
            'cooldown_minutes': 5,
        },
        {
            'name': 'Incident Sécurité',
            'description': 'Tout incident nécessitant une attention',
            'trigger_type': 'severity_level',
            'trigger_conditions': {
                'min_severity': 'high'
            },
            'priority': 2,
            'cooldown_minutes': 10,
        }
    ]
    
    rules = []
    for location in locations:
        for rule_data in rules_data:
            rule = AlertRule.objects.create(
                location=location,
                created_by=admin_user,
                **rule_data
            )
            rules.append(rule)
            print(f"⚠️  Règle créée: {rule.name} pour {location.name}")
    
    return rules


def create_demo_detections(cameras):
    """Crée des détections simulées"""
    event_types = ['theft', 'intrusion', 'suspicious', 'abandoned_object', 'accident', 'fire', 'crowd', 'violence']
    severity_levels = ['low', 'medium', 'high', 'critical']
    
    # Créer des détections pour les derniers jours
    for days_ago in range(7):
        detection_date = timezone.now() - timedelta(days=days_ago)
        num_detections = random.randint(3, 15)  # 3-15 détections par jour
        
        for _ in range(num_detections):
            camera = random.choice(cameras)
            event_type = random.choice(event_types)
            
            # Ajuster la probabilité selon le type de zone
            if camera.zone.risk_level == 'high':
                severity = random.choices(severity_levels, weights=[10, 20, 40, 30])[0]
            elif camera.zone.risk_level == 'medium':
                severity = random.choices(severity_levels, weights=[20, 40, 30, 10])[0]
            else:
                severity = random.choices(severity_levels, weights=[50, 30, 15, 5])[0]
            
            detection_time = detection_date.replace(
                hour=random.randint(6, 22),
                minute=random.randint(0, 59),
                second=random.randint(0, 59)
            )
            
            detection = DetectionEvent.objects.create(
                camera=camera,
                zone=camera.zone,
                event_type=event_type,
                severity=severity,
                confidence=random.uniform(0.6, 0.95),
                detected_at=detection_time,
                bounding_boxes=[{
                    'x': random.randint(50, 200),
                    'y': random.randint(30, 150),
                    'width': random.randint(80, 150),
                    'height': random.randint(100, 200)
                }],
                description=f"Détection {event_type} avec {severity} gravité",
                is_verified=random.choice([True, False]) if days_ago > 1 else False,
                false_positive=random.choice([True, False, False, False]) if random.choice([True, False]) else False
            )
            
            # Déclencher les alertes pour cette détection
            if days_ago < 2:  # Seulement pour les détections récentes
                try:
                    from alerts.utils import process_detection
                    process_detection(detection)
                except ImportError:
                    pass  # Le module utils n'est peut-être pas encore disponible
    
    print(f"🔍 {DetectionEvent.objects.count()} détections créées")


def create_demo_heatmap_data(locations):
    """Crée des données de carte de chaleur"""
    for location in locations:
        zones = Zone.objects.filter(location=location)
        
        # Créer des données pour les 30 derniers jours
        for days_ago in range(30):
            date = (timezone.now() - timedelta(days=days_ago)).date()
            
            for zone in zones:
                # Calculer les détections pour cette zone ce jour-là
                detections_count = DetectionEvent.objects.filter(
                    zone=zone,
                    detected_at__date=date
                ).count()
                
                # Calculer la densité d'activité basée sur le niveau de risque et les détections
                base_density = {'high': 0.7, 'medium': 0.4, 'low': 0.2}[zone.risk_level]
                activity_density = min(1.0, base_density + (detections_count * 0.05))
                
                # Score de risque calculé
                risk_multiplier = {'high': 2.0, 'medium': 1.5, 'low': 1.0}[zone.risk_level]
                risk_score = activity_density * risk_multiplier * random.uniform(0.8, 1.2)
                
                # Heures de pic (simulation)
                peak_hours = []
                if detections_count > 3:
                    peak_hours = random.sample(range(8, 20), min(3, detections_count // 2))
                
                HeatMapData.objects.update_or_create(
                    location=location,
                    zone=zone,
                    date=date,
                    defaults={
                        'detection_count': detections_count,
                        'alert_count': max(0, detections_count - 2),  # Approximation
                        'activity_density': activity_density,
                        'risk_score': min(1.0, risk_score),
                        'peak_hours': peak_hours,
                        'event_types': {
                            'theft': random.randint(0, detections_count // 2),
                            'suspicious': random.randint(0, detections_count // 2),
                            'intrusion': random.randint(0, max(1, detections_count // 4))
                        }
                    }
                )
    
    print(f"🗺️  {HeatMapData.objects.count()} entrées de carte de chaleur créées")


if __name__ == '__main__':
    try:
        create_demo_data()
    except Exception as e:
        print(f"❌ Erreur lors de la création des données: {e}")
        import traceback
        traceback.print_exc() 