from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from .models import CompanyUser


class CompanyMiddleware:
    """
    Middleware pour gérer l'isolation des données par entreprise
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # URLs qui ne nécessitent pas de vérification d'entreprise
        self.exempt_urls = [
            '/admin/',
            '/companies/login/',
            '/login/',
            '/logout/',
            '/static/',
            '/media/',
            # '/api/',  # Commenté pour permettre le filtrage par entreprise dans les APIs
        ]
    
    def __call__(self, request):
        # Debug pour les APIs d'alertes et les pages de monitoring
        if request.path.startswith('/api/alerts/') or request.path.startswith('/monitoring/'):
            print(f"🌐 MIDDLEWARE: Requête: {request.method} {request.path}")
            print(f"🌐 MIDDLEWARE: User: {request.user}")
        
        # Vérifier si l'URL est exemptée
        if any(request.path.startswith(url) for url in self.exempt_urls):
            if request.path.startswith('/api/alerts/'):
                print(f"🌐 MIDDLEWARE: URL exemptée, passage direct")
            return self.get_response(request)
        
        # Si l'utilisateur n'est pas authentifié, laisser Django gérer
        if not request.user.is_authenticated:
            return self.get_response(request)
        
        # Vérifier si l'utilisateur a un profil d'entreprise
        try:
            company_user = request.user.company_profile
            
            # Si l'utilisateur est owner, il a accès à tout
            if company_user.is_owner:
                request.current_company = None  # Owner n'a pas d'entreprise spécifique
                request.company_user = company_user
                if request.path.startswith('/monitoring/'):
                    print(f"🌐 MIDDLEWARE: Utilisateur OWNER - Pas de filtrage")
                return self.get_response(request)
            
            # Vérifier si l'entreprise est active
            if not company_user.company or not company_user.company.is_active:
                messages.error(request, "Votre entreprise n'est pas active. Contactez l'administrateur.")
                return redirect('companies:company_login')
            
            # Vérifier si l'utilisateur est actif
            if not company_user.is_active:
                messages.error(request, "Votre compte est désactivé. Contactez votre manager.")
                return redirect('companies:company_login')
            
            # Ajouter les informations d'entreprise à la requête
            request.current_company = company_user.company
            request.company_user = company_user
            if request.path.startswith('/monitoring/'):
                print(f"🌐 MIDDLEWARE: Utilisateur {company_user.get_role_display()} - Filtrage par entreprise: {company_user.company.name}")
            
        except CompanyUser.DoesNotExist:
            # L'utilisateur n'a pas de profil d'entreprise
            # Rediriger vers la page de connexion d'entreprise
            messages.error(request, "Vous devez vous connecter avec une référence d'entreprise.")
            return redirect('companies:company_login')
        
        return self.get_response(request)


class CompanyDataFilterMixin:
    """
    Mixin pour filtrer automatiquement les données par entreprise
    """
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Si l'utilisateur est owner, retourner toutes les données
        if hasattr(self.request, 'company_user') and self.request.company_user.is_owner:
            return queryset
        
        # Filtrer par entreprise si le modèle a un champ company
        if hasattr(self.request, 'current_company') and self.request.current_company:
            if hasattr(queryset.model, 'company'):
                return queryset.filter(company=self.request.current_company)
        
        return queryset
    
    def form_valid(self, form):
        # Ajouter automatiquement l'entreprise lors de la création
        if hasattr(self.request, 'current_company') and self.request.current_company:
            if hasattr(form.instance, 'company') and not form.instance.company:
                form.instance.company = self.request.current_company
        
        return super().form_valid(form)


def company_required(view_func):
    """
    Décorateur pour s'assurer qu'un utilisateur appartient à une entreprise
    """
    def wrapper(request, *args, **kwargs):
        if not hasattr(request, 'current_company') or not request.current_company:
            if not (hasattr(request, 'company_user') and request.company_user.is_owner):
                messages.error(request, "Accès refusé. Vous devez appartenir à une entreprise.")
                return redirect('companies:company_login')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def permission_required(permission):
    """
    Décorateur pour vérifier les permissions spécifiques à l'entreprise
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not hasattr(request, 'company_user'):
                messages.error(request, "Accès refusé.")
                return redirect('companies:company_login')
            
            company_user = request.company_user
            
            # Les owners ont toutes les permissions
            if company_user.is_owner:
                return view_func(request, *args, **kwargs)
            
            # Vérifier la permission spécifique
            if not company_user.has_permission(permission):
                messages.error(request, f"Vous n'avez pas la permission '{permission}'.")
                return redirect('companies:manager_dashboard')
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator
