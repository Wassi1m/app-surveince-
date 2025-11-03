from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
import json


class HistoryEntry(models.Model):
    """
    Modèle principal pour stocker l'historique de tous les changements dans le système
    """
    ACTION_CHOICES = [
        ('create', 'Création'),
        ('update', 'Modification'),
        ('delete', 'Suppression'),
        ('login', 'Connexion'),
        ('logout', 'Déconnexion'),
        ('view', 'Consultation'),
        ('export', 'Exportation'),
        ('import', 'Importation'),
        ('activate', 'Activation'),
        ('deactivate', 'Désactivation'),
        ('assign', 'Attribution'),
        ('unassign', 'Retrait d\'attribution'),
    ]
    
    CATEGORY_CHOICES = [
        ('user', 'Utilisateur'),
        ('company', 'Entreprise'),
        ('location', 'Localisation'),
        ('zone', 'Zone'),
        ('camera', 'Caméra'),
        ('alert', 'Alerte'),
        ('detection', 'Détection'),
        ('incident', 'Incident'),
        ('recording', 'Enregistrement'),
        ('settings', 'Paramètres'),
        ('system', 'Système'),
        ('auth', 'Authentification'),
        ('report', 'Rapport'),
        ('notification', 'Notification'),
    ]
    
    # Informations de base
    timestamp = models.DateTimeField(default=timezone.now, verbose_name="Horodatage")
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='history_entries',
        verbose_name="Utilisateur"
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="Action")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name="Catégorie")
    
    # Objet concerné (utilisation de GenericForeignKey pour pointer vers n'importe quel modèle)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Détails de l'action
    object_name = models.CharField(max_length=255, verbose_name="Nom de l'objet", help_text="Nom/titre de l'objet modifié")
    description = models.TextField(verbose_name="Description", help_text="Description détaillée de l'action")
    
    # Données de changement (pour les modifications)
    old_values = models.JSONField(null=True, blank=True, verbose_name="Anciennes valeurs")
    new_values = models.JSONField(null=True, blank=True, verbose_name="Nouvelles valeurs")
    changed_fields = models.JSONField(null=True, blank=True, verbose_name="Champs modifiés")
    
    # Métadonnées techniques
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="Adresse IP")
    user_agent = models.TextField(blank=True, verbose_name="User Agent")
    session_key = models.CharField(max_length=40, blank=True, verbose_name="Clé de session")
    
    # Informations contextuelles
    company = models.ForeignKey(
        'companies.Company', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='history_entries',
        verbose_name="Entreprise"
    )
    location = models.ForeignKey(
        'monitoring.Location', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='history_entries',
        verbose_name="Localisation"
    )
    
    # Flags
    is_sensitive = models.BooleanField(default=False, verbose_name="Données sensibles")
    is_system_action = models.BooleanField(default=False, verbose_name="Action système")
    
    class Meta:
        verbose_name = "Entrée d'historique"
        verbose_name_plural = "Entrées d'historique"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['company', 'timestamp']),
            models.Index(fields=['category', 'timestamp']),
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['content_type', 'object_id']),
        ]
    
    def __str__(self):
        user_str = self.user.get_full_name() or self.user.username if self.user else "Système"
        return f"{self.timestamp.strftime('%d/%m/%Y %H:%M')} - {user_str} - {self.get_action_display()} - {self.object_name}"
    
    def get_changed_fields_display(self):
        """Retourne une représentation lisible des champs modifiés"""
        if not self.changed_fields:
            return ""
        
        changes = []
        for field in self.changed_fields:
            old_val = self.old_values.get(field, '') if self.old_values else ''
            new_val = self.new_values.get(field, '') if self.new_values else ''
            changes.append(f"{field}: '{old_val}' → '{new_val}'")
        
        return " | ".join(changes)
    
    def get_summary(self):
        """Retourne un résumé de l'action"""
        if self.action == 'create':
            return f"Création de {self.get_category_display().lower()} '{self.object_name}'"
        elif self.action == 'update':
            return f"Modification de {self.get_category_display().lower()} '{self.object_name}'"
        elif self.action == 'delete':
            return f"Suppression de {self.get_category_display().lower()} '{self.object_name}'"
        else:
            return f"{self.get_action_display()} - {self.object_name}"


class HistoryFilter(models.Model):
    """
    Filtres sauvegardés pour l'historique
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='history_filters')
    name = models.CharField(max_length=100, verbose_name="Nom du filtre")
    description = models.TextField(blank=True, verbose_name="Description")
    
    # Critères de filtre
    filter_data = models.JSONField(verbose_name="Données de filtre")
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    is_default = models.BooleanField(default=False, verbose_name="Filtre par défaut")
    is_shared = models.BooleanField(default=False, verbose_name="Partagé avec l'équipe")
    
    class Meta:
        verbose_name = "Filtre d'historique"
        verbose_name_plural = "Filtres d'historique"
        unique_together = ['user', 'name']
        ordering = ['name']
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"


class HistoryExport(models.Model):
    """
    Exports d'historique générés
    """
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('processing', 'En cours'),
        ('completed', 'Terminé'),
        ('failed', 'Échoué'),
    ]
    
    FORMAT_CHOICES = [
        ('csv', 'CSV'),
        ('excel', 'Excel'),
        ('pdf', 'PDF'),
        ('json', 'JSON'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='history_exports')
    company = models.ForeignKey('companies.Company', on_delete=models.CASCADE, related_name='history_exports')
    
    # Paramètres d'export
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default='csv')
    filter_data = models.JSONField(verbose_name="Critères de filtre appliqués")
    date_from = models.DateTimeField(verbose_name="Date de début")
    date_to = models.DateTimeField(verbose_name="Date de fin")
    
    # Statut et résultat
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    file_path = models.CharField(max_length=500, blank=True, verbose_name="Chemin du fichier")
    file_size = models.BigIntegerField(null=True, blank=True, verbose_name="Taille du fichier")
    record_count = models.PositiveIntegerField(null=True, blank=True, verbose_name="Nombre d'enregistrements")
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, verbose_name="Message d'erreur")
    
    class Meta:
        verbose_name = "Export d'historique"
        verbose_name_plural = "Exports d'historique"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Export {self.format.upper()} - {self.user.username} - {self.created_at.strftime('%d/%m/%Y %H:%M')}"


class HistorySettings(models.Model):
    """
    Paramètres de configuration de l'historisation par entreprise
    """
    company = models.OneToOneField(
        'companies.Company', 
        on_delete=models.CASCADE, 
        related_name='history_settings'
    )
    
    # Paramètres de rétention
    retention_days = models.PositiveIntegerField(
        default=365, 
        verbose_name="Durée de rétention (jours)",
        help_text="Nombre de jours avant archivage automatique"
    )
    auto_archive = models.BooleanField(
        default=True, 
        verbose_name="Archivage automatique"
    )
    
    # Paramètres de tracking
    track_views = models.BooleanField(
        default=False, 
        verbose_name="Traquer les consultations",
        help_text="Enregistrer les actions de consultation/lecture"
    )
    track_exports = models.BooleanField(
        default=True, 
        verbose_name="Traquer les exports"
    )
    track_system_actions = models.BooleanField(
        default=False, 
        verbose_name="Traquer les actions système"
    )
    
    # Catégories à traquer
    enabled_categories = models.JSONField(
        default=list,
        verbose_name="Catégories activées",
        help_text="Liste des catégories à historiser"
    )
    
    # Paramètres de notification
    notify_sensitive_actions = models.BooleanField(
        default=True, 
        verbose_name="Notifier les actions sensibles"
    )
    notification_emails = models.JSONField(
        default=list,
        verbose_name="Emails de notification",
        help_text="Liste des emails à notifier pour les actions sensibles"
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Modifié par"
    )
    
    class Meta:
        verbose_name = "Paramètres d'historique"
        verbose_name_plural = "Paramètres d'historique"
    
    def __str__(self):
        return f"Paramètres historique - {self.company.name}"
    
    def save(self, *args, **kwargs):
        # Valeurs par défaut pour les catégories activées
        if not self.enabled_categories:
            self.enabled_categories = [
                'user', 'company', 'location', 'zone', 'camera', 
                'alert', 'detection', 'incident', 'settings'
            ]
        super().save(*args, **kwargs)