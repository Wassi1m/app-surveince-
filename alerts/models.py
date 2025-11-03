from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from monitoring.models import DetectionEvent, Location, Camera, Zone
import json

# Import des nouveaux modèles de notifications
from .models_notifications import (
    NotificationChannel, NotificationTemplate, 
    Notification, NotificationPreference
)


class AlertRule(models.Model):
    """Règles de déclenchement d'alertes"""
    TRIGGER_TYPES = [
        ('detection_type', 'Type de détection'),
        ('severity_level', 'Niveau de gravité'),
        ('camera', 'Caméra spécifique'),
        ('zone', 'Zone spécifique'),
        ('time_window', 'Fenêtre temporelle'),
        ('confidence_threshold', 'Seuil de confiance'),
    ]
    
    company = models.ForeignKey('companies.Company', on_delete=models.CASCADE, related_name='alert_rules', verbose_name="Entreprise", null=True, blank=True)
    subcompany = models.ForeignKey('companies.SubCompany', on_delete=models.CASCADE, related_name='alert_rules', verbose_name="Sous-entreprise", null=True, blank=True)
    name = models.CharField(max_length=200, verbose_name="Nom de la règle")
    description = models.TextField(blank=True)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='alert_rules', verbose_name="Zone", null=True, blank=True)
    trigger_type = models.CharField(max_length=20, choices=TRIGGER_TYPES)
    trigger_conditions = models.JSONField(help_text="Conditions de déclenchement")
    is_active = models.BooleanField(default=True)
    priority = models.PositiveIntegerField(default=1, help_text="Priorité (1 = plus haute)")
    cooldown_minutes = models.PositiveIntegerField(default=5, help_text="Délai avant nouvelle alerte")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    last_triggered = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.zone.name if self.zone else 'Aucune zone'})"
    
    class Meta:
        verbose_name = "Règle d'alerte"
        verbose_name_plural = "Règles d'alerte"
        ordering = ['priority', '-created_at']


class Alert(models.Model):
    """Alertes générées par le système"""
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('sent', 'Envoyée'),
        ('acknowledged', 'Accusée de réception'),
        ('resolved', 'Résolue'),
        ('failed', 'Échec'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Faible'),
        ('medium', 'Moyenne'),
        ('high', 'Haute'),
        ('critical', 'Critique'),
    ]
    
    company = models.ForeignKey('companies.Company', on_delete=models.CASCADE, related_name='alerts', verbose_name="Entreprise", null=True, blank=True)
    subcompany = models.ForeignKey('companies.SubCompany', on_delete=models.CASCADE, related_name='alerts', verbose_name="Sous-entreprise", null=True, blank=True)
    detection_event = models.ForeignKey(DetectionEvent, on_delete=models.CASCADE, related_name='alerts')
    alert_rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE, related_name='alerts')
    title = models.CharField(max_length=200, verbose_name="Titre de l'alerte")
    message = models.TextField(verbose_name="Message")
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_alerts')
    metadata = models.JSONField(default=dict, help_text="Métadonnées supplémentaires")
    
    def __str__(self):
        return f"ALERT-{self.id:06d} - {self.title}"
    
    @property
    def age_seconds(self):
        """Âge de l'alerte en secondes"""
        return (timezone.now() - self.created_at).total_seconds()
    
    @property
    def response_time_seconds(self):
        """Temps de réponse en secondes"""
        if self.acknowledged_at:
            return (self.acknowledged_at - self.created_at).total_seconds()
        return None
    
    class Meta:
        verbose_name = "Alerte"
        verbose_name_plural = "Alertes"
        ordering = ['-created_at']


# Anciens modèles NotificationLog et AlertRecipient supprimés
# Remplacés par le nouveau système de notifications avancé


class CameraAlertRule(models.Model):
    """Association entre une caméra et les règles d'alerte qu'elle utilise"""
    
    camera = models.ForeignKey('monitoring.Camera', on_delete=models.CASCADE, 
                              related_name='alert_rules', verbose_name="Caméra")
    alert_rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE, 
                                  related_name='cameras', verbose_name="Règle d'alerte")
    
    # Configuration spécifique à cette association
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    priority_override = models.IntegerField(null=True, blank=True, verbose_name="Priorité personnalisée",
                                          help_text="Laissez vide pour utiliser la priorité de la règle")
    
    # Métadonnées
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   verbose_name="Assigné par")
    
    def get_effective_priority(self):
        """Retourne la priorité effective (personnalisée ou de la règle)"""
        return self.priority_override or self.alert_rule.priority
    
    def __str__(self):
        return f"{self.camera.name} - {self.alert_rule.name}"
    
    class Meta:
        verbose_name = "Règle d'alerte de caméra"
        verbose_name_plural = "Règles d'alerte de caméras"
        unique_together = ['camera', 'alert_rule']
        ordering = ['camera__name', 'alert_rule__name']


class AlertSchedule(models.Model):
    """Planification des alertes"""
    SCHEDULE_TYPES = [
        ('immediate', 'Immédiat'),
        ('delayed', 'Différée'),
        ('recurring', 'Récurrente'),
        ('conditional', 'Conditionnelle'),
    ]
    
    DAY_CHOICES = [
        ('monday', 'Lundi'),
        ('tuesday', 'Mardi'),
        ('wednesday', 'Mercredi'),
        ('thursday', 'Jeudi'),
        ('friday', 'Vendredi'),
        ('saturday', 'Samedi'),
        ('sunday', 'Dimanche'),
    ]
    
    alert_rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE, related_name='schedules')
    schedule_type = models.CharField(max_length=15, choices=SCHEDULE_TYPES, default='immediate')
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    days_of_week = models.JSONField(default=list, help_text="Jours de la semaine actifs")
    delay_minutes = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Planning {self.alert_rule.name}"
    
    class Meta:
        verbose_name = "Planification d'alerte"
        verbose_name_plural = "Planifications d'alerte"
