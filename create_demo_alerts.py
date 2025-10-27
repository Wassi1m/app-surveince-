#!/usr/bin/env python
"""
Script de création de données de démonstration pour le modèle Alert
"""

import os
import sys
import django
from datetime import datetime, timedelta
import random

# Configuration Django
sys.path.append('/home/user/Bureau/app suc')  # Modifie le chemin vers ton projet
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'surveillance_system.settings')
django.setup()

from django.contrib.auth.models import User
from alerts.models import Alert
from monitoring.models import DetectionEvent 
from alerts.models import AlertRule

def create_demo_alerts():
    """Créer des alertes de démonstration"""
    print("🚀 Création des alertes de démonstration...")

    # Récupérer un utilisateur admin
    try:
        admin_user = User.objects.get(username='admin')
    except User.DoesNotExist:
        print("⚠️  Utilisateur admin non trouvé")
        return

    # Récupérer des DetectionEvent et AlertRule existants
    detection_events = list(DetectionEvent.objects.all())
    alert_rules = list(AlertRule.objects.all())

    if not detection_events or not alert_rules:
        print("⚠️  Aucun DetectionEvent ou AlertRule trouvé")
        return

    priorities = ['low', 'medium', 'high', 'critical']
    statuses = ['pending', 'sent', 'acknowledged', 'resolved', 'failed']

    # Créer 10 alertes de démonstration
    for i in range(1, 11):
        alert = Alert.objects.create(
            detection_event=random.choice(detection_events),
            alert_rule=random.choice(alert_rules),
            title=f"Alerte de test {i}",
            message=f"Ceci est un message de test pour l'alerte {i}.",
            priority=random.choice(priorities),
            status=random.choice(statuses),
            acknowledged_by=admin_user if random.choice([True, False]) else None,
            resolved_by=admin_user if random.choice([True, False]) else None,
            metadata={
                "source": "demo_script",
                "test_number": i
            }
        )
        print(f"✅ Alerte créée : {alert.title} (status: {alert.status}, priorité: {alert.priority})")

    print("\n🎉 Données de démonstration créées avec succès !")
    print(f"📋 Total alertes : {Alert.objects.count()}")

if __name__ == '__main__':
    create_demo_alerts()
