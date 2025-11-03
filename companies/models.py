from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
import secrets
import string


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