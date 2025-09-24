from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from monitoring.models import Location, Camera, DetectionEvent, Zone
from alerts.models import Alert


class StatisticsSummary(models.Model):
    """Résumé statistique par période"""
    PERIOD_TYPES = [
        ('hour', 'Heure'),
        ('day', 'Jour'),
        ('week', 'Semaine'),
        ('month', 'Mois'),
        ('quarter', 'Trimestre'),
        ('year', 'Année'),
    ]
    
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='statistics')
    period_type = models.CharField(max_length=10, choices=PERIOD_TYPES)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    # Métriques de détection
    total_detections = models.PositiveIntegerField(default=0)
    theft_detections = models.PositiveIntegerField(default=0)
    intrusion_detections = models.PositiveIntegerField(default=0)
    suspicious_detections = models.PositiveIntegerField(default=0)
    accident_detections = models.PositiveIntegerField(default=0)
    fire_detections = models.PositiveIntegerField(default=0)
    other_detections = models.PositiveIntegerField(default=0)
    
    # Métriques d'alertes
    total_alerts = models.PositiveIntegerField(default=0)
    critical_alerts = models.PositiveIntegerField(default=0)
    high_alerts = models.PositiveIntegerField(default=0)
    medium_alerts = models.PositiveIntegerField(default=0)
    low_alerts = models.PositiveIntegerField(default=0)
    
    # Métriques de performance
    false_positives = models.PositiveIntegerField(default=0)
    true_positives = models.PositiveIntegerField(default=0)
    average_response_time = models.FloatField(null=True, blank=True, help_text="Temps de réponse moyen en secondes")
    camera_uptime_percentage = models.FloatField(default=100.0)
    
    # Métriques temporelles
    peak_activity_hour = models.PositiveIntegerField(null=True, blank=True)
    activity_distribution = models.JSONField(default=dict, help_text="Distribution de l'activité par heure")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Stats {self.location.name} - {self.period_start.strftime('%d/%m/%Y')} ({self.get_period_type_display()})"
    
    @property
    def detection_accuracy(self):
        """Calcule la précision des détections"""
        total = self.false_positives + self.true_positives
        if total == 0:
            return None
        return (self.true_positives / total) * 100
    
    class Meta:
        verbose_name = "Résumé statistique"
        verbose_name_plural = "Résumés statistiques"
        unique_together = ['location', 'period_type', 'period_start']
        ordering = ['-period_start']


class HeatMapData(models.Model):
    """Données pour les cartes de chaleur des zones sensibles"""
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='heatmap_data')
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='heatmap_data')
    date = models.DateField()
    
    # Compteurs d'événements
    detection_count = models.PositiveIntegerField(default=0)
    alert_count = models.PositiveIntegerField(default=0)
    incident_count = models.PositiveIntegerField(default=0)
    
    # Données de densité
    activity_density = models.FloatField(default=0.0, help_text="Densité d'activité (0.0-1.0)")
    risk_score = models.FloatField(default=0.0, help_text="Score de risque calculé")
    
    # Métadonnées
    peak_hours = models.JSONField(default=list, help_text="Heures de pic d'activité")
    event_types = models.JSONField(default=dict, help_text="Distribution des types d'événements")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"HeatMap {self.zone.name} - {self.date.strftime('%d/%m/%Y')}"
    
    class Meta:
        verbose_name = "Données de carte de chaleur"
        verbose_name_plural = "Données de cartes de chaleur"
        unique_together = ['zone', 'date']
        ordering = ['-date']


class Report(models.Model):
    """Rapports générés automatiquement ou manuellement"""
    REPORT_TYPES = [
        ('daily', 'Rapport quotidien'),
        ('weekly', 'Rapport hebdomadaire'),
        ('monthly', 'Rapport mensuel'),
        ('incident', 'Rapport d\'incident'),
        ('security_audit', 'Audit de sécurité'),
        ('performance', 'Rapport de performance'),
        ('custom', 'Rapport personnalisé'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('generating', 'Génération en cours'),
        ('completed', 'Terminé'),
        ('failed', 'Échec'),
        ('archived', 'Archivé'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="Titre du rapport")
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='reports')
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    file_path = models.CharField(max_length=500, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    
    # Contenu du rapport
    content = models.JSONField(default=dict, help_text="Contenu structuré du rapport")
    summary = models.TextField(blank=True, verbose_name="Résumé exécutif")
    recommendations = models.TextField(blank=True, verbose_name="Recommandations")
    
    # Métadonnées
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_automatic = models.BooleanField(default=False)
    
    # Partage et accès
    is_public = models.BooleanField(default=False)
    shared_with = models.ManyToManyField(User, blank=True, related_name='shared_reports')
    download_count = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"{self.title} - {self.period_start.strftime('%d/%m/%Y')}"
    
    @property
    def duration_days(self):
        """Durée couverte par le rapport en jours"""
        return (self.period_end - self.period_start).days
    
    class Meta:
        verbose_name = "Rapport"
        verbose_name_plural = "Rapports"
        ordering = ['-created_at']


class PerformanceMetric(models.Model):
    """Métriques de performance du système"""
    METRIC_TYPES = [
        ('detection_latency', 'Latence de détection'),
        ('alert_response_time', 'Temps de réponse aux alertes'),
        ('camera_uptime', 'Disponibilité des caméras'),
        ('ai_accuracy', 'Précision de l\'IA'),
        ('storage_usage', 'Utilisation du stockage'),
        ('bandwidth_usage', 'Utilisation de la bande passante'),
        ('cpu_usage', 'Utilisation CPU'),
        ('memory_usage', 'Utilisation mémoire'),
    ]
    
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='performance_metrics')
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, null=True, blank=True, related_name='performance_metrics')
    metric_type = models.CharField(max_length=30, choices=METRIC_TYPES)
    value = models.FloatField()
    unit = models.CharField(max_length=50, help_text="Unité de mesure")
    timestamp = models.DateTimeField(default=timezone.now)
    
    # Métadonnées
    threshold_min = models.FloatField(null=True, blank=True)
    threshold_max = models.FloatField(null=True, blank=True)
    is_alert_triggered = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict)
    
    def __str__(self):
        camera_name = f" - {self.camera.name}" if self.camera else ""
        return f"{self.get_metric_type_display()}{camera_name}: {self.value} {self.unit}"
    
    @property
    def is_within_threshold(self):
        """Vérifie si la valeur est dans les seuils acceptables"""
        if self.threshold_min is not None and self.value < self.threshold_min:
            return False
        if self.threshold_max is not None and self.value > self.threshold_max:
            return False
        return True
    
    class Meta:
        verbose_name = "Métrique de performance"
        verbose_name_plural = "Métriques de performance"
        ordering = ['-timestamp']


class TrendAnalysis(models.Model):
    """Analyse des tendances sur les données de surveillance"""
    TREND_TYPES = [
        ('detection_frequency', 'Fréquence des détections'),
        ('incident_severity', 'Gravité des incidents'),
        ('response_times', 'Temps de réponse'),
        ('zone_activity', 'Activité par zone'),
        ('temporal_patterns', 'Motifs temporels'),
        ('seasonal_trends', 'Tendances saisonnières'),
    ]
    
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='trend_analyses')
    trend_type = models.CharField(max_length=30, choices=TREND_TYPES)
    analysis_period_start = models.DateTimeField()
    analysis_period_end = models.DateTimeField()
    
    # Résultats de l'analyse
    trend_direction = models.CharField(max_length=20, choices=[
        ('increasing', 'Croissante'),
        ('decreasing', 'Décroissante'),
        ('stable', 'Stable'),
        ('volatile', 'Volatile'),
    ])
    trend_strength = models.FloatField(help_text="Force de la tendance (0.0-1.0)")
    correlation_coefficient = models.FloatField(null=True, blank=True)
    
    # Données de la tendance
    data_points = models.JSONField(help_text="Points de données pour la visualisation")
    statistical_summary = models.JSONField(help_text="Résumé statistique")
    predictions = models.JSONField(default=dict, help_text="Prédictions futures")
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    algorithm_used = models.CharField(max_length=100, blank=True)
    confidence_level = models.FloatField(default=0.95)
    
    def __str__(self):
        return f"Tendance {self.get_trend_type_display()} - {self.location.name}"
    
    class Meta:
        verbose_name = "Analyse de tendance"
        verbose_name_plural = "Analyses de tendance"
        ordering = ['-created_at']
