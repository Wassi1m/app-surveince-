from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import Company, CompanyUser, CompanyInvitation


class CompanyForm(forms.ModelForm):
    """Formulaire pour créer/modifier une entreprise"""
    manager_email = forms.EmailField(
        label="Email du manager",
        help_text="Un compte manager sera créé avec cet email"
    )
    manager_first_name = forms.CharField(
        max_length=30,
        label="Prénom du manager",
        required=False
    )
    manager_last_name = forms.CharField(
        max_length=30,
        label="Nom du manager",
        required=False
    )
    
    class Meta:
        model = Company
        fields = [
            'name', 'description', 'address', 'phone', 'email', 'website',
            'max_users', 'max_cameras', 'max_locations'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si on modifie une entreprise existante, on n'a pas besoin des champs manager
        if self.instance and self.instance.pk:
            del self.fields['manager_email']
            del self.fields['manager_first_name']
            del self.fields['manager_last_name']
    
    def clean_manager_email(self):
        email = self.cleaned_data.get('manager_email')
        if email and User.objects.filter(email=email).exists():
            raise ValidationError("Un utilisateur avec cet email existe déjà.")
        return email


class CompanyUserForm(forms.ModelForm):
    """Formulaire pour créer/modifier un utilisateur d'entreprise"""
    
    class Meta:
        model = CompanyUser
        fields = [
            'role', 'employee_id', 'department', 'position', 'phone',
            'is_active', 'can_manage_users', 'can_manage_cameras',
            'can_manage_alerts', 'can_view_reports'
        ]
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        
        # Les owners ne peuvent pas être modifiés par les managers
        if self.company:
            role_choices = [choice for choice in CompanyUser.ROLE_CHOICES if choice[0] != 'owner']
            self.fields['role'].choices = role_choices


class ManagerLoginForm(forms.Form):
    """Formulaire de connexion avec référence d'entreprise"""
    company_reference = forms.CharField(
        max_length=20,
        label="Référence de l'entreprise",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: ABC12345'
        })
    )
    username = forms.CharField(
        max_length=150,
        label="Nom d'utilisateur / Email",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Votre email'
        })
    )
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control'
        })
    )
    
    def clean_company_reference(self):
        reference = self.cleaned_data.get('company_reference')
        if reference:
            reference = reference.upper().strip()
        return reference


class EmployeeCreationForm(UserCreationForm):
    """Formulaire pour créer un employé"""
    email = forms.EmailField(required=True, label="Email")
    first_name = forms.CharField(max_length=30, required=True, label="Prénom")
    last_name = forms.CharField(max_length=30, required=True, label="Nom")
    
    # Champs CompanyUser
    role = forms.ChoiceField(
        choices=[choice for choice in CompanyUser.ROLE_CHOICES if choice[0] not in ['owner']],
        initial='employee',
        label="Rôle"
    )
    employee_id = forms.CharField(
        max_length=50,
        required=False,
        label="ID Employé"
    )
    department = forms.CharField(
        max_length=100,
        required=False,
        label="Département"
    )
    position = forms.CharField(
        max_length=100,
        required=False,
        label="Poste"
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        label="Téléphone"
    )
    
    # Permissions
    can_manage_users = forms.BooleanField(
        required=False,
        label="Peut gérer les utilisateurs"
    )
    can_manage_cameras = forms.BooleanField(
        required=False,
        label="Peut gérer les caméras"
    )
    can_manage_alerts = forms.BooleanField(
        required=False,
        label="Peut gérer les alertes"
    )
    can_view_reports = forms.BooleanField(
        initial=True,
        required=False,
        label="Peut voir les rapports"
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Utiliser l'email comme nom d'utilisateur par défaut
        self.fields['username'].help_text = "Laissez vide pour utiliser l'email comme nom d'utilisateur"
        self.fields['username'].required = False
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Un utilisateur avec cet email existe déjà.")
        return email
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        email = self.cleaned_data.get('email')
        
        # Si pas de username fourni, utiliser l'email
        if not username and email:
            username = email
        
        if User.objects.filter(username=username).exists():
            raise ValidationError("Ce nom d'utilisateur existe déjà.")
        
        return username
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        
        # Utiliser l'email comme username si pas fourni
        if not user.username:
            user.username = self.cleaned_data['email']
        
        if commit:
            user.save()
        return user


class CompanyInvitationForm(forms.ModelForm):
    """Formulaire pour inviter un utilisateur"""
    
    class Meta:
        model = CompanyInvitation
        fields = [
            'email', 'role', 'can_manage_users', 'can_manage_cameras',
            'can_manage_alerts', 'can_view_reports'
        ]
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop('company', None)
        self.invited_by = kwargs.pop('invited_by', None)
        super().__init__(*args, **kwargs)
        
        # Exclure le rôle owner
        role_choices = [choice for choice in CompanyUser.ROLE_CHOICES if choice[0] != 'owner']
        self.fields['role'].choices = role_choices
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        
        # Vérifier si l'utilisateur existe déjà dans cette entreprise
        if self.company:
            existing_user = User.objects.filter(email=email).first()
            if existing_user:
                try:
                    company_user = existing_user.company_profile
                    if company_user.company == self.company:
                        raise ValidationError("Cet utilisateur fait déjà partie de votre entreprise.")
                except CompanyUser.DoesNotExist:
                    pass
            
            # Vérifier s'il y a déjà une invitation en attente
            if CompanyInvitation.objects.filter(
                company=self.company,
                email=email,
                status='pending'
            ).exists():
                raise ValidationError("Une invitation est déjà en attente pour cet email.")
        
        return email


class CompanySettingsForm(forms.Form):
    """Formulaire pour les paramètres d'entreprise"""
    
    # Paramètres de sécurité
    session_timeout = forms.IntegerField(
        min_value=300,  # 5 minutes minimum
        max_value=86400,  # 24 heures maximum
        initial=7200,
        label="Timeout de session (secondes)",
        help_text="Durée avant déconnexion automatique"
    )
    max_login_attempts = forms.IntegerField(
        min_value=3,
        max_value=10,
        initial=5,
        label="Tentatives de connexion maximum"
    )
    
    # Paramètres de notification
    email_notifications = forms.BooleanField(
        required=False,
        initial=True,
        label="Notifications par email"
    )
    sms_notifications = forms.BooleanField(
        required=False,
        label="Notifications par SMS"
    )
    push_notifications = forms.BooleanField(
        required=False,
        initial=True,
        label="Notifications push"
    )
    
    # Paramètres de surveillance
    ai_confidence_threshold = forms.FloatField(
        min_value=0.1,
        max_value=1.0,
        initial=0.75,
        label="Seuil de confiance IA",
        help_text="Niveau minimum de confiance pour déclencher une alerte"
    )
    auto_archive_days = forms.IntegerField(
        min_value=7,
        max_value=365,
        initial=90,
        label="Archivage automatique (jours)"
    )
    max_storage_gb = forms.IntegerField(
        min_value=10,
        max_value=1000,
        initial=100,
        label="Stockage maximum (GB)"
    )
    
    # Paramètres d'interface
    theme = forms.ChoiceField(
        choices=[('light', 'Clair'), ('dark', 'Sombre'), ('auto', 'Automatique')],
        initial='light',
        label="Thème"
    )
    language = forms.ChoiceField(
        choices=[('fr', 'Français'), ('en', 'English')],
        initial='fr',
        label="Langue"
    )
    timezone = forms.CharField(
        max_length=50,
        initial='Europe/Paris',
        label="Fuseau horaire"
    )
