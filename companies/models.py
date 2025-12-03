from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
import secrets
import string
import os
from PIL import Image
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile


class Company(models.Model):
    """Modèle représentant une entreprise"""
    name = models.CharField(max_length=200, verbose_name="Nom de l'entreprise")
    reference = models.CharField(
        max_length=20, 
        unique=True, 
        verbose_name="Référence unique",
        help_text="Référence unique générée automatiquement"
    )
    description = models.TextField(blank=True, verbose_name="Description")
    address = models.TextField(blank=True, verbose_name="Adresse")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    email = models.EmailField(blank=True, verbose_name="Email de contact")
    website = models.URLField(blank=True, verbose_name="Site web")
    
    # Informations de gestion
    is_active = models.BooleanField(default=True, verbose_name="Entreprise active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Limites et quotas
    max_users = models.PositiveIntegerField(default=50, verbose_name="Nombre maximum d'utilisateurs")
    max_cameras = models.PositiveIntegerField(default=20, verbose_name="Nombre maximum de caméras")
    max_locations = models.PositiveIntegerField(default=5, verbose_name="Nombre maximum de lieux")
    
    # Configuration personnalisée
    settings = models.JSONField(
        default=dict, 
        verbose_name="Paramètres personnalisés",
        help_text="Configuration spécifique à l'entreprise"
    )
    
    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self.generate_unique_reference()
        super().save(*args, **kwargs)
    
    def generate_unique_reference(self):
        """Génère une référence unique pour l'entreprise"""
        while True:
            # Génère une référence de 8 caractères alphanumériques
            reference = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
            if not Company.objects.filter(reference=reference).exists():
                return reference
    
    def __str__(self):
        return f"{self.name} ({self.reference})"
    
    @property
    def user_count(self):
        """Nombre d'utilisateurs dans l'entreprise"""
        return self.company_users.count()
    
    @property
    def camera_count(self):
        """Nombre de caméras dans l'entreprise"""
        return sum(location.cameras.count() for location in self.locations.all())
    
    @property
    def location_count(self):
        """Nombre de lieux dans l'entreprise"""
        return self.locations.count()
    
    @property
    def subcompany_count(self):
        """Nombre de sous-entreprises"""
        return self.subcompanies.count()
    
    def create_default_subcompany(self):
        """Crée une sous-entreprise par défaut lors de la création de l'entreprise"""
        if not self.subcompanies.exists():
            SubCompany.objects.create(
                parent_company=self,
                name=f"{self.name} - Principal",
                reference=f"{self.reference}-MAIN",
                is_default=True,
                description="Sous-entreprise principale créée automatiquement"
            )
    
    class Meta:
        verbose_name = "Entreprise"
        verbose_name_plural = "Entreprises"
        ordering = ['name']


class SubCompany(models.Model):
    """Modèle représentant une sous-entreprise"""
    parent_company = models.ForeignKey(
        Company, 
        on_delete=models.CASCADE, 
        related_name='subcompanies',
        verbose_name="Entreprise parente"
    )
    name = models.CharField(max_length=200, verbose_name="Nom de la sous-entreprise")
    reference = models.CharField(
        max_length=30, 
        unique=True, 
        verbose_name="Référence unique",
        help_text="Référence unique générée automatiquement"
    )
    description = models.TextField(blank=True, verbose_name="Description")
    
    # Informations de gestion
    is_active = models.BooleanField(default=True, verbose_name="Sous-entreprise active")
    is_default = models.BooleanField(default=False, verbose_name="Sous-entreprise par défaut")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Créé par"
    )
    
    # Limites spécifiques à la sous-entreprise
    max_users = models.PositiveIntegerField(default=20, verbose_name="Nombre maximum d'utilisateurs")
    max_cameras = models.PositiveIntegerField(default=10, verbose_name="Nombre maximum de caméras")
    max_locations = models.PositiveIntegerField(default=3, verbose_name="Nombre maximum de lieux")
    
    # Configuration personnalisée
    settings = models.JSONField(
        default=dict, 
        verbose_name="Paramètres personnalisés",
        help_text="Configuration spécifique à la sous-entreprise"
    )
    
    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self.generate_unique_reference()
        super().save(*args, **kwargs)
    
    def generate_unique_reference(self):
        """Génère une référence unique pour la sous-entreprise"""
        base_ref = self.parent_company.reference
        counter = 1
        while True:
            reference = f"{base_ref}-SUB{counter:02d}"
            if not SubCompany.objects.filter(reference=reference).exists():
                return reference
            counter += 1
    
    def __str__(self):
        return f"{self.name} ({self.reference})"
    
    @property
    def user_count(self):
        """Nombre d'utilisateurs dans la sous-entreprise"""
        return self.subcompany_users.count()
    
    @property
    def camera_count(self):
        """Nombre de caméras dans la sous-entreprise"""
        return sum(location.cameras.count() for location in self.locations.all())
    
    @property
    def location_count(self):
        """Nombre de lieux dans la sous-entreprise"""
        return self.locations.count()
    
    @property
    def full_name(self):
        """Nom complet avec entreprise parente"""
        return f"{self.parent_company.name} > {self.name}"
    
    class Meta:
        verbose_name = "Sous-entreprise"
        verbose_name_plural = "Sous-entreprises"
        ordering = ['parent_company__name', 'name']
        unique_together = ['parent_company', 'name']


class CompanyUser(models.Model):
    """Modèle étendant User pour inclure les informations d'entreprise"""
    ROLE_CHOICES = [
        ('owner', 'Propriétaire de l\'application'),
        ('manager', 'Manager d\'entreprise'),
        ('employee', 'Employé'),
        ('viewer', 'Observateur'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='company_profile')
    company = models.ForeignKey(
        Company, 
        on_delete=models.CASCADE, 
        related_name='company_users',
        null=True, 
        blank=True
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    
    # Sous-entreprises auxquelles l'utilisateur a accès
    subcompanies = models.ManyToManyField(
        SubCompany,
        through='SubCompanyUser',
        related_name='users',
        blank=True,
        verbose_name="Sous-entreprises"
    )
    
    # Sous-entreprise actuellement sélectionnée (pour les managers)
    current_subcompany = models.ForeignKey(
        SubCompany,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_users',
        verbose_name="Sous-entreprise courante"
    )
    
    # Informations supplémentaires
    employee_id = models.CharField(max_length=50, blank=True, verbose_name="ID employé")
    department = models.CharField(max_length=100, blank=True, verbose_name="Département")
    position = models.CharField(max_length=100, blank=True, verbose_name="Poste")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Téléphone")
    
    # Permissions et accès
    is_active = models.BooleanField(default=True, verbose_name="Utilisateur actif")
    can_manage_users = models.BooleanField(default=False, verbose_name="Peut gérer les utilisateurs")
    can_manage_cameras = models.BooleanField(default=False, verbose_name="Peut gérer les caméras")
    can_manage_alerts = models.BooleanField(default=False, verbose_name="Peut gérer les alertes")
    can_view_reports = models.BooleanField(default=True, verbose_name="Peut voir les rapports")
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_company = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        company_name = self.company.name if self.company else "Aucune entreprise"
        return f"{self.user.get_full_name() or self.user.username} - {company_name} ({self.get_role_display()})"
    
    @property
    def is_owner(self):
        """Vérifie si l'utilisateur est propriétaire de l'application"""
        return self.role == 'owner'
    
    @property
    def is_manager(self):
        """Vérifie si l'utilisateur est manager d'entreprise"""
        return self.role == 'manager'
    
    @property
    def is_employee(self):
        """Vérifie si l'utilisateur est employé"""
        return self.role in ['employee', 'viewer']
    
    @property
    def full_name(self):
        """Nom complet de l'utilisateur"""
        return self.user.get_full_name() or self.user.username
    
    def get_accessible_subcompanies(self):
        """Retourne les sous-entreprises accessibles selon le rôle"""
        if self.is_owner:
            # Les owners voient toutes les sous-entreprises de toutes les entreprises
            return SubCompany.objects.filter(is_active=True)
        elif self.is_manager:
            # Vérifier si le manager a des assignations spécifiques
            assigned_subcompanies = self.subcompanies.filter(is_active=True)
            if assigned_subcompanies.exists():
                # Manager avec accès limité : seulement ses assignations
                return assigned_subcompanies
            else:
                # Manager sans assignations : accès à toutes les sous-entreprises de son entreprise
                return self.company.subcompanies.filter(is_active=True)
        else:
            # Les employés voient seulement leurs sous-entreprises assignées
            return self.subcompanies.filter(is_active=True)
    
    def can_access_subcompany(self, subcompany):
        """Vérifie si l'utilisateur peut accéder à une sous-entreprise"""
        if self.is_owner:
            return True
        elif self.is_manager:
            return subcompany.parent_company == self.company
        else:
            return self.subcompanies.filter(id=subcompany.id).exists()
    
    def set_current_subcompany(self, subcompany):
        """Définit la sous-entreprise courante"""
        if self.can_access_subcompany(subcompany):
            self.current_subcompany = subcompany
            self.save()
            return True
        return False
    
    def has_permission(self, permission):
        """Vérifie si l'utilisateur a une permission spécifique"""
        if self.is_owner:
            return True
        
        permission_map = {
            'manage_users': self.can_manage_users,
            'manage_cameras': self.can_manage_cameras,
            'manage_alerts': self.can_manage_alerts,
            'view_reports': self.can_view_reports,
        }
        
        return permission_map.get(permission, False)
    
    class Meta:
        verbose_name = "Utilisateur d'entreprise"
        verbose_name_plural = "Utilisateurs d'entreprise"
        unique_together = ['user', 'company']
        ordering = ['company__name', 'user__last_name', 'user__first_name']


class CompanyInvitation(models.Model):
    """Invitations pour rejoindre une entreprise"""
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('accepted', 'Acceptée'),
        ('declined', 'Refusée'),
        ('expired', 'Expirée'),
    ]
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='invitations')
    email = models.EmailField(verbose_name="Email de l'invité")
    role = models.CharField(max_length=20, choices=CompanyUser.ROLE_CHOICES, default='employee')
    
    # Informations de l'invitation
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')
    invitation_token = models.UUIDField(default=uuid.uuid4, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Permissions proposées
    can_manage_users = models.BooleanField(default=False)
    can_manage_cameras = models.BooleanField(default=False)
    can_manage_alerts = models.BooleanField(default=False)
    can_view_reports = models.BooleanField(default=True)
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    accepted_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='accepted_invitations'
    )
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            # L'invitation expire dans 7 jours
            self.expires_at = timezone.now() + timezone.timedelta(days=7)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Vérifie si l'invitation a expiré"""
        return timezone.now() > self.expires_at
    
    @property
    def is_pending(self):
        """Vérifie si l'invitation est en attente"""
        return self.status == 'pending' and not self.is_expired
    
    def __str__(self):
        return f"Invitation {self.email} -> {self.company.name} ({self.get_status_display()})"
    
    class Meta:
        verbose_name = "Invitation d'entreprise"
        verbose_name_plural = "Invitations d'entreprise"
        unique_together = ['company', 'email', 'status']
        ordering = ['-created_at']


class CompanySettings(models.Model):
    """Paramètres spécifiques à chaque entreprise"""
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='company_settings')
    
    # Paramètres de sécurité
    password_policy = models.JSONField(
        default=dict,
        help_text="Politique de mots de passe (longueur min, complexité, etc.)"
    )
    session_timeout = models.PositiveIntegerField(
        default=7200,
        help_text="Timeout de session en secondes"
    )
    max_login_attempts = models.PositiveIntegerField(
        default=5,
        help_text="Nombre maximum de tentatives de connexion"
    )
    
    # Paramètres de notification
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    push_notifications = models.BooleanField(default=True)
    
    # Paramètres de surveillance
    ai_confidence_threshold = models.FloatField(
        default=0.75,
        help_text="Seuil de confiance pour l'IA"
    )
    auto_archive_days = models.PositiveIntegerField(
        default=90,
        help_text="Archivage automatique après X jours"
    )
    max_storage_gb = models.PositiveIntegerField(
        default=100,
        help_text="Stockage maximum en GB"
    )
    
    # Paramètres d'interface
    theme = models.CharField(
        max_length=20,
        choices=[('light', 'Clair'), ('dark', 'Sombre'), ('auto', 'Automatique')],
        default='light'
    )
    language = models.CharField(
        max_length=10,
        choices=[('fr', 'Français'), ('en', 'English')],
        default='fr'
    )
    timezone = models.CharField(
        max_length=50,
        default='Europe/Paris'
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Paramètres {self.company.name}"
    
    class Meta:
        verbose_name = "Paramètres d'entreprise"
        verbose_name_plural = "Paramètres d'entreprise"


class SubCompanyUser(models.Model):
    """Modèle de liaison entre utilisateurs et sous-entreprises"""
    company_user = models.ForeignKey(
        CompanyUser,
        on_delete=models.CASCADE,
        related_name='subcompany_assignments'
    )
    subcompany = models.ForeignKey(
        SubCompany,
        on_delete=models.CASCADE,
        related_name='subcompany_users'
    )
    
    # Permissions spécifiques à cette sous-entreprise (simplifiées)
    can_manage_monitoring = models.BooleanField(default=False, verbose_name="Surveillance (Caméras, Zones, Localisations)")
    can_manage_alerts = models.BooleanField(default=False, verbose_name="Gérer les alertes")
    can_manage_alert_rules = models.BooleanField(default=False, verbose_name="Règles d'alerte")
    can_view_reports = models.BooleanField(default=True, verbose_name="Voir les rapports")
    
    # Métadonnées
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Assigné par"
    )
    is_active = models.BooleanField(default=True, verbose_name="Assignation active")
    
    def __str__(self):
        return f"{self.company_user.user.username} -> {self.subcompany.name}"
    
    class Meta:
        verbose_name = "Assignation sous-entreprise"
        verbose_name_plural = "Assignations sous-entreprises"
        unique_together = ['company_user', 'subcompany']
        ordering = ['subcompany__name', 'company_user__user__username']


def upload_employee_image(instance, filename):
    """Fonction pour définir le chemin d'upload des images d'employés ciblés"""
    # Créer un nom de fichier unique
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4().hex}.{ext}"
    
    # Organiser par entreprise et sous-entreprise
    company_ref = instance.company.reference if instance.company else 'no-company'
    subcompany_ref = instance.subcompany.reference if instance.subcompany else 'no-subcompany'
    
    return f'employees_cibles/{company_ref}/{subcompany_ref}/{filename}'


class EmployeCible(models.Model):
    """Modèle pour les employés ciblés avec reconnaissance d'images"""
    
    STATUS_CHOICES = [
        ('pending', 'En attente de validation'),
        ('validated', 'Validé'),
        ('rejected', 'Rejeté'),
        ('archived', 'Archivé'),
    ]
    
    DETECTION_STATUS_CHOICES = [
        ('not_processed', 'Non traité'),
        ('processing', 'En cours de traitement'),
        ('face_detected', 'Visage détecté'),
        ('no_face_detected', 'Aucun visage détecté'),
        ('multiple_faces', 'Plusieurs visages détectés'),
        ('low_quality', 'Qualité insuffisante'),
    ]
    
    # Relations
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='employes_cibles',
        verbose_name="Entreprise"
    )
    subcompany = models.ForeignKey(
        SubCompany,
        on_delete=models.CASCADE,
        related_name='employes_cibles',
        null=True,
        blank=True,
        verbose_name="Sous-entreprise"
    )
    
    # Image et métadonnées
    image_originale = models.ImageField(
        upload_to=upload_employee_image,
        verbose_name="Image originale",
        help_text="Image importée par le système"
    )
    image_miniature = models.ImageField(
        upload_to=upload_employee_image,
        null=True,
        blank=True,
        verbose_name="Miniature",
        help_text="Miniature générée automatiquement"
    )
    image_visage = models.ImageField(
        upload_to=upload_employee_image,
        null=True,
        blank=True,
        verbose_name="Visage extrait",
        help_text="Visage extrait par l'IA"
    )
    
    # Informations de l'employé (saisies par le manager)
    prenom = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Prénom"
    )
    nom = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Nom"
    )
    employee_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="ID Employé",
        help_text="Identifiant unique de l'employé"
    )
    poste = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Poste"
    )
    departement = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Département"
    )
    
    # Métadonnées de traitement
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Statut"
    )
    detection_status = models.CharField(
        max_length=20,
        choices=DETECTION_STATUS_CHOICES,
        default='not_processed',
        verbose_name="Statut de détection"
    )
    
    # Informations techniques de l'image
    image_width = models.PositiveIntegerField(null=True, blank=True, verbose_name="Largeur image")
    image_height = models.PositiveIntegerField(null=True, blank=True, verbose_name="Hauteur image")
    image_size = models.PositiveIntegerField(null=True, blank=True, verbose_name="Taille fichier (bytes)")
    image_format = models.CharField(max_length=10, blank=True, verbose_name="Format image")
    
    # Données de reconnaissance faciale (JSON)
    face_encoding = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Encodage facial",
        help_text="Données d'encodage facial pour la reconnaissance"
    )
    face_landmarks = models.JSONField(
        null=True,
        blank=True,
        verbose_name="Points faciaux",
        help_text="Points de repère du visage détectés"
    )
    detection_confidence = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Confiance de détection",
        help_text="Score de confiance de la détection faciale (0-1)"
    )
    
    # Informations de gestion
    importe_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employes_cibles_importes',
        verbose_name="Importé par"
    )
    valide_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employes_cibles_valides',
        verbose_name="Validé par"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")
    validated_at = models.DateTimeField(null=True, blank=True, verbose_name="Validé le")
    
    # Flags additionnels
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    
    # Relation pour regrouper les images du même employé
    employee_group = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='additional_images',
        verbose_name="Groupe d'employé",
        help_text="Premier enregistrement du groupe pour regrouper les images du même employé"
    )
    
    class Meta:
        verbose_name = "Employé ciblé"
        verbose_name_plural = "Employés ciblés"
        ordering = ['-created_at']
    is_priority = models.BooleanField(default=False, verbose_name="Prioritaire")
    notes = models.TextField(blank=True, verbose_name="Notes")
    
    def save(self, *args, **kwargs):
        """Traitement automatique lors de la sauvegarde"""
        if self.image_originale and not self.pk:
            # Première sauvegarde - traiter l'image
            self._process_image()
        
        super().save(*args, **kwargs)
        
        # Post-traitement après sauvegarde
        if self.image_originale and self.detection_status == 'not_processed':
            self._detect_face()
    
    def _process_image(self):
        """Traite l'image originale pour extraire les métadonnées"""
        try:
            # Ouvrir l'image avec Pillow
            with Image.open(self.image_originale) as img:
                self.image_width = img.width
                self.image_height = img.height
                self.image_format = img.format
                
                # Calculer la taille du fichier
                self.image_originale.seek(0, 2)  # Aller à la fin
                self.image_size = self.image_originale.tell()
                self.image_originale.seek(0)  # Revenir au début
                
                # Créer une miniature
                self._create_thumbnail(img)
                
        except Exception as e:
            print(f"Erreur lors du traitement de l'image: {e}")
    
    def _create_thumbnail(self, img):
        """Crée une miniature de l'image"""
        try:
            # Créer une copie pour la miniature
            thumbnail = img.copy()
            
            # Convertir PNG avec transparence en RGB pour JPEG
            if img.format == 'PNG' and img.mode in ('RGBA', 'LA', 'P'):
                # Créer un fond blanc pour les PNG transparents
                background = Image.new('RGB', thumbnail.size, (255, 255, 255))
                if thumbnail.mode == 'P':
                    thumbnail = thumbnail.convert('RGBA')
                background.paste(thumbnail, mask=thumbnail.split()[-1] if thumbnail.mode == 'RGBA' else None)
                thumbnail = background
            elif img.mode not in ('RGB', 'L'):
                thumbnail = thumbnail.convert('RGB')
            
            thumbnail.thumbnail((300, 300), Image.Resampling.LANCZOS)
            
            # Sauvegarder la miniature
            from io import BytesIO
            thumb_io = BytesIO()
            thumbnail.save(thumb_io, format='JPEG', quality=85)
            thumb_io.seek(0)
            
            # Générer un nom de fichier pour la miniature
            original_name = os.path.basename(self.image_originale.name)
            name_without_ext = os.path.splitext(original_name)[0]
            thumb_name = f"{name_without_ext}_thumb.jpg"
            
            self.image_miniature.save(
                thumb_name,
                ContentFile(thumb_io.read()),
                save=False
            )
            
        except Exception as e:
            print(f"Erreur lors de la création de la miniature: {e}")
    
    def _detect_face(self):
        """Détecte et extrait le visage de l'image (simulation)"""
        try:
            self.detection_status = 'processing'
            self.save(update_fields=['detection_status'])
            
            # Ici, vous pourriez intégrer une vraie détection faciale
            # Pour l'instant, on simule une détection réussie
            import random
            import time
            
            # Simuler un traitement
            time.sleep(0.5)
            
            # Simuler différents résultats
            outcomes = ['face_detected', 'no_face_detected', 'multiple_faces', 'low_quality']
            weights = [0.7, 0.1, 0.1, 0.1]  # 70% de chance de succès
            
            result = random.choices(outcomes, weights=weights)[0]
            self.detection_status = result
            
            if result == 'face_detected':
                # Simuler des données de reconnaissance
                self.detection_confidence = random.uniform(0.75, 0.95)
                self.face_encoding = {
                    'encoding': [random.uniform(-1, 1) for _ in range(128)],
                    'version': '1.0'
                }
                self.face_landmarks = {
                    'left_eye': [random.randint(50, 100), random.randint(50, 100)],
                    'right_eye': [random.randint(150, 200), random.randint(50, 100)],
                    'nose': [random.randint(100, 150), random.randint(100, 150)],
                    'mouth': [random.randint(100, 150), random.randint(180, 220)]
                }
                
                # Créer une image de visage simulée (copie de la miniature)
                if self.image_miniature:
                    self._create_face_image()
            
            self.save(update_fields=['detection_status', 'detection_confidence', 'face_encoding', 'face_landmarks'])
            
        except Exception as e:
            print(f"Erreur lors de la détection faciale: {e}")
            self.detection_status = 'low_quality'
            self.save(update_fields=['detection_status'])
    
    def _create_face_image(self):
        """Crée une image du visage extrait (simulation)"""
        try:
            if not self.image_miniature:
                return
            
            # Pour la démo, on copie simplement la miniature
            # Dans un vrai système, on extrairait le visage détecté
            with default_storage.open(self.image_miniature.name, 'rb') as f:
                face_content = f.read()
            
            # Générer un nom pour l'image de visage
            original_name = os.path.basename(self.image_originale.name)
            name_without_ext = os.path.splitext(original_name)[0]
            face_name = f"{name_without_ext}_face.jpg"
            
            self.image_visage.save(
                face_name,
                ContentFile(face_content),
                save=False
            )
            
        except Exception as e:
            print(f"Erreur lors de la création de l'image de visage: {e}")
    
    def validate(self, user):
        """Valide l'employé ciblé"""
        self.status = 'validated'
        self.valide_par = user
        self.validated_at = timezone.now()
        self.save(update_fields=['status', 'valide_par', 'validated_at'])
    
    def reject(self, user):
        """Rejette l'employé ciblé"""
        self.status = 'rejected'
        self.valide_par = user
        self.validated_at = timezone.now()
        self.save(update_fields=['status', 'valide_par', 'validated_at'])
    
    @property
    def images_count(self):
        """Retourne le nombre total d'images pour cet employé"""
        if self.employee_group:
            # Si cet employé fait partie d'un groupe, compter toutes les images du groupe
            return EmployeCible.objects.filter(
                models.Q(id=self.employee_group.id) | models.Q(employee_group=self.employee_group)
            ).count()
        else:
            # Si c'est le groupe principal, compter toutes les images du groupe
            return EmployeCible.objects.filter(
                models.Q(id=self.id) | models.Q(employee_group=self)
            ).count()
    
    @property
    def all_images(self):
        """Retourne toutes les images de cet employé"""
        if self.employee_group:
            return EmployeCible.objects.filter(
                models.Q(id=self.employee_group.id) | models.Q(employee_group=self.employee_group)
            )
        else:
            return EmployeCible.objects.filter(
                models.Q(id=self.id) | models.Q(employee_group=self)
            )
    
    @property
    def nom_complet(self):
        """Retourne le nom complet de l'employé"""
        if self.prenom and self.nom:
            return f"{self.prenom} {self.nom}"
        elif self.prenom:
            return self.prenom
        elif self.nom:
            return self.nom
        else:
            return f"Employé #{self.pk}"
    
    @property
    def has_face_data(self):
        """Vérifie si des données faciales sont disponibles"""
        return self.face_encoding is not None and self.detection_status == 'face_detected'
    
    @property
    def is_ready_for_recognition(self):
        """Vérifie si l'employé est prêt pour la reconnaissance"""
        return (
            self.status == 'validated' and
            self.has_face_data and
            self.prenom and
            self.nom and
            self.is_active
        )
    
    @property
    def detection_status_color(self):
        """Retourne la couleur associée au statut de détection"""
        colors = {
            'not_processed': 'secondary',
            'processing': 'warning',
            'face_detected': 'success',
            'no_face_detected': 'danger',
            'multiple_faces': 'warning',
            'low_quality': 'danger',
        }
        return colors.get(self.detection_status, 'secondary')
    
    @property
    def status_color(self):
        """Retourne la couleur associée au statut"""
        colors = {
            'pending': 'warning',
            'validated': 'success',
            'rejected': 'danger',
            'archived': 'secondary',
        }
        return colors.get(self.status, 'secondary')
    
    def __str__(self):
        return f"{self.nom_complet} - {self.company.name}"
    
    class Meta:
        verbose_name = "Employé ciblé"
        verbose_name_plural = "Employés ciblés"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'status']),
            models.Index(fields=['subcompany', 'status']),
            models.Index(fields=['detection_status']),
            models.Index(fields=['created_at']),
        ]


class EmployeCibleImportBatch(models.Model):
    """Modèle pour gérer les lots d'import d'employés ciblés"""
    
    STATUS_CHOICES = [
        ('uploading', 'Upload en cours'),
        ('processing', 'Traitement en cours'),
        ('completed', 'Terminé'),
        ('failed', 'Échec'),
    ]
    
    # Relations
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name='import_batches',
        verbose_name="Entreprise"
    )
    subcompany = models.ForeignKey(
        SubCompany,
        on_delete=models.CASCADE,
        related_name='import_batches',
        null=True,
        blank=True,
        verbose_name="Sous-entreprise"
    )
    
    # Informations du lot
    nom_lot = models.CharField(
        max_length=200,
        verbose_name="Nom du lot",
        help_text="Nom descriptif pour ce lot d'import"
    )
    description = models.TextField(
        blank=True,
        verbose_name="Description"
    )
    
    # Statistiques
    total_images = models.PositiveIntegerField(default=0, verbose_name="Total d'images")
    images_traitees = models.PositiveIntegerField(default=0, verbose_name="Images traitées")
    images_reussies = models.PositiveIntegerField(default=0, verbose_name="Images réussies")
    images_echouees = models.PositiveIntegerField(default=0, verbose_name="Images échouées")
    
    # Statut et métadonnées
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='uploading',
        verbose_name="Statut"
    )
    
    # Gestion
    cree_par = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Créé par"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Terminé le")
    
    # Logs et erreurs
    logs = models.JSONField(
        default=list,
        verbose_name="Logs de traitement",
        help_text="Historique des opérations"
    )
    erreurs = models.JSONField(
        default=list,
        verbose_name="Erreurs rencontrées",
        help_text="Liste des erreurs durant le traitement"
    )
    
    @property
    def progress_percentage(self):
        """Calcule le pourcentage de progression"""
        if self.total_images == 0:
            return 0
        return int((self.images_traitees / self.total_images) * 100)
    
    @property
    def success_rate(self):
        """Calcule le taux de réussite"""
        if self.images_traitees == 0:
            return 0
        return int((self.images_reussies / self.images_traitees) * 100)
    
    def add_log(self, message, level='info'):
        """Ajoute une entrée de log"""
        log_entry = {
            'timestamp': timezone.now().isoformat(),
            'level': level,
            'message': message
        }
        self.logs.append(log_entry)
        self.save(update_fields=['logs'])
    
    def add_error(self, error_message, filename=None):
        """Ajoute une erreur"""
        error_entry = {
            'timestamp': timezone.now().isoformat(),
            'filename': filename,
            'error': error_message
        }
        self.erreurs.append(error_entry)
        self.images_echouees += 1
        self.save(update_fields=['erreurs', 'images_echouees'])
    
    def mark_completed(self):
        """Marque le lot comme terminé"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])
    
    def __str__(self):
        return f"{self.nom_lot} - {self.company.name} ({self.get_status_display()})"
    
    class Meta:
        verbose_name = "Lot d'import d'employés"
        verbose_name_plural = "Lots d'import d'employés"
        ordering = ['-created_at']