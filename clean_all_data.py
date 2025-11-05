#!/usr/bin/env python
"""
Script pour supprimer toutes les instances des modèles personnalisés
À exécuter avant la création d'un nouveau compte owner pour nettoyer la base de données
"""
import os
import sys
import django

# Configuration Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'surveillance_system.settings')
django.setup()

def clean_all_data():
    """Supprime toutes les instances des modèles personnalisés"""
    
    print("=" * 60)
    print("NETTOYAGE DE LA BASE DE DONNÉES")
    print("=" * 60)
    
    # Application monitoring
    print("\n[1/3] Suppression des données de l'application MONITORING...")
    from monitoring.models import Location, Zone, Camera, DetectionEvent, Incident, VideoRecording
    
    count_video = VideoRecording.objects.all().count()
    VideoRecording.objects.all().delete()
    print(f"  ✓ {count_video} VideoRecording supprimés")
    
    count_incident = Incident.objects.all().count()
    Incident.objects.all().delete()
    print(f"  ✓ {count_incident} Incident supprimés")
    
    count_detection = DetectionEvent.objects.all().count()
    DetectionEvent.objects.all().delete()
    print(f"  ✓ {count_detection} DetectionEvent supprimés")
    
    count_camera = Camera.objects.all().count()
    Camera.objects.all().delete()
    print(f"  ✓ {count_camera} Camera supprimées")
    
    count_zone = Zone.objects.all().count()
    Zone.objects.all().delete()
    print(f"  ✓ {count_zone} Zone supprimées")
    
    count_location = Location.objects.all().count()
    Location.objects.all().delete()
    print(f"  ✓ {count_location} Location supprimées")
    
    # Application alerts
    print("\n[2/3] Suppression des données de l'application ALERTS...")
    from alerts.models import NotificationChannel, NotificationTemplate, Notification, NotificationPreference, AlertRule, Alert, AlertSchedule
    
    count_schedule = AlertSchedule.objects.all().count()
    AlertSchedule.objects.all().delete()
    print(f"  ✓ {count_schedule} AlertSchedule supprimés")
    
    count_alert = Alert.objects.all().count()
    Alert.objects.all().delete()
    print(f"  ✓ {count_alert} Alert supprimées")
    
    count_rule = AlertRule.objects.all().count()
    AlertRule.objects.all().delete()
    print(f"  ✓ {count_rule} AlertRule supprimées")
    
    count_pref = NotificationPreference.objects.all().count()
    NotificationPreference.objects.all().delete()
    print(f"  ✓ {count_pref} NotificationPreference supprimées")
    
    count_notif = Notification.objects.all().count()
    Notification.objects.all().delete()
    print(f"  ✓ {count_notif} Notification supprimées")
    
    count_template = NotificationTemplate.objects.all().count()
    NotificationTemplate.objects.all().delete()
    print(f"  ✓ {count_template} NotificationTemplate supprimés")
    
    count_channel = NotificationChannel.objects.all().count()
    NotificationChannel.objects.all().delete()
    print(f"  ✓ {count_channel} NotificationChannel supprimés")
    
    # Application analytics
    print("\n[3/3] Suppression des données de l'application ANALYTICS...")
    from analytics.models import StatisticsSummary, HeatMapData, Report, PerformanceMetric, TrendAnalysis
    
    count_trend = TrendAnalysis.objects.all().count()
    TrendAnalysis.objects.all().delete()
    print(f"  ✓ {count_trend} TrendAnalysis supprimées")
    
    count_perf = PerformanceMetric.objects.all().count()
    PerformanceMetric.objects.all().delete()
    print(f"  ✓ {count_perf} PerformanceMetric supprimées")
    
    count_report = Report.objects.all().count()
    Report.objects.all().delete()
    print(f"  ✓ {count_report} Report supprimés")
    
    count_heatmap = HeatMapData.objects.all().count()
    HeatMapData.objects.all().delete()
    print(f"  ✓ {count_heatmap} HeatMapData supprimées")
    
    count_stats = StatisticsSummary.objects.all().count()
    StatisticsSummary.objects.all().delete()
    print(f"  ✓ {count_stats} StatisticsSummary supprimés")
    
    print("\n" + "=" * 60)
    print("✅ TOUTES LES DONNÉES ONT ÉTÉ SUPPRIMÉES AVEC SUCCÈS !")
    print("=" * 60)

if __name__ == '__main__':
    try:
        clean_all_data()
    except Exception as e:
        print(f"\n❌ ERREUR : {e}")
        sys.exit(1)

