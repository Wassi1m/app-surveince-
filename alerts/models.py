from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from monitoring.models import DetectionEvent, Location, Camera


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
    
    name = models.CharField(max_length=200, verbose_name="Nom de la règle")
    description = models.TextField(blank=True)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='alert_rules')
    trigger_type = models.CharField(max_length=20, choices=TRIGGER_TYPES)
    trigger_conditions = models.JSONField(help_text="Conditions de déclenchement")
    is_active = models.BooleanField(default=True)
    priority = models.PositiveIntegerField(default=1, help_text="Priorité (1 = plus haute)")
    cooldown_minutes = models.PositiveIntegerField(default=5, help_text="Délai avant nouvelle alerte")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    last_triggered = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.location.name})"
    
    class Meta:
        verbose_name = "Règle d'alerte"
        verbose_name_plural = "Règles d'alerte"
        ordering = ['priority', '-created_at']


class NotificationChannel(models.Model):
    """Canaux de notification (email, SMS, webhook, etc.)"""
    CHANNEL_TYPES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('webhook', 'Webhook'),
        ('push', 'Notification push'),
        ('slack', 'Slack'),
        ('teams', 'Microsoft Teams'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Nom du canal")
    channel_type = models.CharField(max_length=20, choices=CHANNEL_TYPES)
    configuration = models.JSONField(help_text="Configuration spécifique au canal")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_channel_type_display()})"
    
    class Meta:
        verbose_name = "Canal de notification"
        verbose_name_plural = "Canaux de notification"


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


class NotificationLog(models.Model):
    """Journal des notifications envoyées"""
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('sending', 'Envoi en cours'),
        ('sent', 'Envoyée'),
        ('delivered', 'Délivrée'),
        ('failed', 'Échec'),
        ('bounced', 'Rejetée'),
    ]
    
    alert = models.ForeignKey(Alert, on_delete=models.CASCADE, related_name='notifications')
    channel = models.ForeignKey(NotificationChannel, on_delete=models.CASCADE)
    recipient = models.CharField(max_length=255, help_text="Email, numéro de téléphone, etc.")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    external_id = models.CharField(max_length=255, blank=True, help_text="ID externe du service")
    retry_count = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict)
    
    def __str__(self):
        return f"Notification {self.alert.title} -> {self.recipient}"
    
    class Meta:
        verbose_name = "Journal de notification"
        verbose_name_plural = "Journal des notifications"
        ordering = ['-sent_at']


class AlertRecipient(models.Model):
    """Destinataires des alertes"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    channels = models.ManyToManyField(NotificationChannel)
    is_active = models.BooleanField(default=True)
    priority_filter = models.JSONField(default=list, help_text="Priorités d'alertes à recevoir")
    time_restrictions = models.JSONField(default=dict, help_text="Restrictions horaires")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.location.name}"
    
    class Meta:
        verbose_name = "Destinataire d'alerte"
        verbose_name_plural = "Destinataires d'alerte"
        unique_together = ['user', 'location']


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
