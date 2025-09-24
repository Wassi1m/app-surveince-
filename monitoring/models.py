from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import json


class Location(models.Model):
    """Représente un lieu de surveillance (magasin, entrepôt, etc.)"""
    name = models.CharField(max_length=200, verbose_name="Nom du lieu")
    address = models.TextField(verbose_name="Adresse")
    description = models.TextField(blank=True, verbose_name="Description")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Lieu"
        verbose_name_plural = "Lieux"


class Zone(models.Model):
    """Zones de surveillance dans un lieu"""
    RISK_LEVELS = [
        ('high', 'Risque élevé'),
        ('medium', 'Risque moyen'),
        ('low', 'Risque faible'),
    ]
    
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='zones')
    name = models.CharField(max_length=100, verbose_name="Nom de la zone")
    risk_level = models.CharField(max_length=10, choices=RISK_LEVELS, default='medium')
    coordinates = models.JSONField(help_text="Coordonnées de la zone [x1,y1,x2,y2]")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.location.name} - {self.name}"
    
    class Meta:
        verbose_name = "Zone"
        verbose_name_plural = "Zones"


class Camera(models.Model):
    """Caméras de surveillance"""
    STATUS_CHOICES = [
        ('online', 'En ligne'),
        ('offline', 'Hors ligne'),
        ('maintenance', 'Maintenance'),
        ('error', 'Erreur'),
    ]
    
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='cameras')
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='cameras')
    name = models.CharField(max_length=100, verbose_name="Nom de la caméra")
    ip_address = models.GenericIPAddressField(verbose_name="Adresse IP")
    port = models.PositiveIntegerField(default=554)
    username = models.CharField(max_length=100, blank=True)
    password = models.CharField(max_length=100, blank=True)
    stream_url = models.URLField(help_text="URL de streaming RTSP/HTTP")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='offline')
    resolution = models.CharField(max_length=20, default='1920x1080')
    fps = models.PositiveIntegerField(default=30)
    last_seen = models.DateTimeField(null=True, blank=True)
    is_ai_enabled = models.BooleanField(default=True, verbose_name="IA activée")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.location.name})"
    
    class Meta:
        verbose_name = "Caméra"
        verbose_name_plural = "Caméras"


class DetectionEvent(models.Model):
    """Événements détectés par l'IA"""
    EVENT_TYPES = [
        ('intrusion', 'Intrusion'),
        ('theft', 'Vol'),
        ('suspicious', 'Comportement suspect'),
        ('abandoned_object', 'Objet abandonné'),
        ('accident', 'Accident'),
        ('fire', 'Incendie'),
        ('crowd', 'Attroupement'),
        ('violence', 'Violence'),
        ('vandalism', 'Vandalisme'),
        ('weapon', 'Arme détectée'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Faible'),
        ('medium', 'Moyen'),
        ('high', 'Élevé'),
        ('critical', 'Critique'),
    ]
    
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name='detections')
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='detections')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS, default='medium')
    confidence = models.FloatField(help_text="Niveau de confiance de l'IA (0.0-1.0)")
    detected_at = models.DateTimeField(default=timezone.now)
    bounding_boxes = models.JSONField(help_text="Coordonnées des objets détectés")
    description = models.TextField(blank=True)
    image_path = models.CharField(max_length=500, blank=True)
    video_clip_path = models.CharField(max_length=500, blank=True)
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    false_positive = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.get_event_type_display()} - {self.camera.name} - {self.detected_at.strftime('%d/%m/%Y %H:%M')}"
    
    @property
    def duration_seconds(self):
        """Durée depuis la détection en secondes"""
        return (timezone.now() - self.detected_at).total_seconds()
    
    class Meta:
        verbose_name = "Détection"
        verbose_name_plural = "Détections"
        ordering = ['-detected_at']


class Incident(models.Model):
    """Incidents de sécurité regroupant plusieurs détections"""
    STATUS_CHOICES = [
        ('open', 'Ouvert'),
        ('investigating', 'En cours d\'investigation'),
        ('resolved', 'Résolu'),
        ('closed', 'Fermé'),
        ('false_alarm', 'Fausse alarme'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Faible'),
        ('medium', 'Moyenne'),
        ('high', 'Haute'),
        ('urgent', 'Urgente'),
    ]
    
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='incidents')
    title = models.CharField(max_length=200, verbose_name="Titre de l'incident")
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    detections = models.ManyToManyField(DetectionEvent, related_name='incidents')
    created_at = models.DateTimeField(auto_now_add=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_incidents')
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_incidents')
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    def __str__(self):
        return f"INC-{self.id:05d} - {self.title}"
    
    @property
    def duration_minutes(self):
        """Durée de l'incident en minutes"""
        if self.resolved_at:
            return (self.resolved_at - self.created_at).total_seconds() / 60
        return (timezone.now() - self.created_at).total_seconds() / 60
    
    class Meta:
        verbose_name = "Incident"
        verbose_name_plural = "Incidents"
        ordering = ['-created_at']


class VideoRecording(models.Model):
    """Enregistrements vidéo"""
    camera = models.ForeignKey(Camera, on_delete=models.CASCADE, related_name='recordings')
    detection = models.ForeignKey(DetectionEvent, on_delete=models.CASCADE, null=True, blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    file_path = models.CharField(max_length=500)
    file_size = models.BigIntegerField(help_text="Taille en bytes")
    duration_seconds = models.PositiveIntegerField()
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Enregistrement {self.camera.name} - {self.start_time.strftime('%d/%m/%Y %H:%M')}"
    
    class Meta:
        verbose_name = "Enregistrement"
        verbose_name_plural = "Enregistrements"
        ordering = ['-start_time']
