"""
Modèles pour le système de notifications avancé
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from monitoring.models import DetectionEvent
import json


class NotificationChannel(models.Model):
    """Canaux de notification (Email, SMS, Push, Slack, etc.)"""
    CHANNEL_TYPES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Notification Push'),
        ('slack', 'Slack'),
        ('teams', 'Microsoft Teams'),
        ('webhook', 'Webhook'),
        ('in_app', 'Notification In-App'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Nom du canal")
    channel_type = models.CharField(max_length=20, choices=CHANNEL_TYPES)
    configuration = models.JSONField(help_text="Configuration du canal (endpoints, tokens, etc.)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_channel_type_display()})"
    
    class Meta:
        verbose_name = "Canal de notification"
        verbose_name_plural = "Canaux de notification"
        db_table = 'alerts_notification_channel'


class NotificationTemplate(models.Model):
    """Templates pour les notifications"""
    TEMPLATE_TYPES = [
        ('alert_created', 'Alerte créée'),
        ('alert_resolved', 'Alerte résolue'),
        ('system_status', 'Statut système'),
        ('maintenance', 'Maintenance'),
        ('security_breach', 'Violation de sécurité'),
        ('camera_offline', 'Caméra hors ligne'),
        ('daily_report', 'Rapport quotidien'),
        ('weekly_report', 'Rapport hebdomadaire'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Nom du template")
    template_type = models.CharField(max_length=30, choices=TEMPLATE_TYPES)
    subject_template = models.CharField(max_length=200, verbose_name="Modèle de sujet")
    body_template = models.TextField(verbose_name="Modèle de contenu")
    variables = models.JSONField(default=dict, help_text="Variables disponibles")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"
    
    def render(self, context):
        """Rendre le template avec le contexte donné"""
        subject = self.subject_template
        body = self.body_template
        
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            subject = subject.replace(placeholder, str(value))
            body = body.replace(placeholder, str(value))
            
        return subject, body
    
    class Meta:
        verbose_name = "Template de notification"
        verbose_name_plural = "Templates de notification"
        db_table = 'alerts_notification_template'


class Notification(models.Model):
    """Notifications envoyées aux utilisateurs"""
    NOTIFICATION_TYPES = [
        ('info', 'Information'),
        ('warning', 'Avertissement'),
        ('error', 'Erreur'),
        ('success', 'Succès'),
        ('alert', 'Alerte'),
        ('system', 'Système'),
    ]
    
    PRIORITY_LEVELS = [
        (1, 'Critique'),
        (2, 'Élevée'),
        (3, 'Normale'),
        (4, 'Faible'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('sent', 'Envoyée'),
        ('delivered', 'Délivrée'),
        ('read', 'Lue'),
        ('failed', 'Échec'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="Titre")
    message = models.TextField(verbose_name="Message")
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    priority = models.IntegerField(choices=PRIORITY_LEVELS, default=3)
    
    # Destinataires
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    user_group = models.CharField(max_length=50, blank=True, help_text="Groupe d'utilisateurs")
    
    # Relations
    alert = models.ForeignKey('Alert', on_delete=models.CASCADE, null=True, blank=True)
    detection_event = models.ForeignKey(DetectionEvent, on_delete=models.CASCADE, null=True, blank=True)
    
    # Métadonnées
    metadata = models.JSONField(default=dict, help_text="Données supplémentaires")
    channels_sent = models.JSONField(default=list, help_text="Canaux utilisés pour l'envoi")
    
    # Statut et timing
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Actions
    action_url = models.URLField(blank=True, help_text="URL d'action")
    action_label = models.CharField(max_length=50, blank=True, help_text="Libellé du bouton d'action")
    
    def __str__(self):
        return f"{self.title} - {self.user or self.user_group}"
    
    def mark_as_read(self):
        """Marquer la notification comme lue"""
        if not self.read_at:
            self.read_at = timezone.now()
            self.status = 'read'
            self.save()
    
    def is_expired(self):
        """Vérifier si la notification a expiré"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    @property
    def is_urgent(self):
        """Vérifier si la notification est urgente"""
        return self.priority <= 2
    
    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']
        db_table = 'alerts_notification'


class NotificationPreference(models.Model):
    """Préférences de notification par utilisateur"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Canaux préférés par type de notification
    alert_channels = models.ManyToManyField(NotificationChannel, related_name='alert_users', blank=True)
    system_channels = models.ManyToManyField(NotificationChannel, related_name='system_users', blank=True)
    report_channels = models.ManyToManyField(NotificationChannel, related_name='report_users', blank=True)
    
    # Paramètres de fréquence
    digest_frequency = models.CharField(
        max_length=20,
        choices=[
            ('immediate', 'Immédiat'),
            ('hourly', 'Toutes les heures'),
            ('daily', 'Quotidien'),
            ('weekly', 'Hebdomadaire'),
            ('never', 'Jamais'),
        ],
        default='immediate'
    )
    
    # Horaires de notification
    quiet_hours_start = models.TimeField(null=True, blank=True, help_text="Début des heures silencieuses")
    quiet_hours_end = models.TimeField(null=True, blank=True, help_text="Fin des heures silencieuses")
    
    # Filtres
    min_priority = models.IntegerField(
        choices=Notification.PRIORITY_LEVELS,
        default=3,
        help_text="Priorité minimale pour recevoir des notifications"
    )
    
    # Paramètres avancés
    enable_sound = models.BooleanField(default=True)
    enable_vibration = models.BooleanField(default=True)
    enable_email_digest = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Préférences de {self.user.username}"
    
    class Meta:
        verbose_name = "Préférence de notification"
        verbose_name_plural = "Préférences de notification"
        db_table = 'alerts_notification_preference'
