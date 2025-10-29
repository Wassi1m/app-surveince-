from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
import logging

# Configuration du logger pour les authentifications
logger = logging.getLogger('companies')

from .models import Company, CompanyUser
from .forms import ManagerLoginForm


class CompanyLoginView(LoginView):
    """Vue de connexion personnalisée avec gestion des entreprises"""
    template_name = 'auth/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        """Redirection après connexion réussie selon le rôle"""
        try:
            company_user = self.request.user.company_profile
            if company_user.is_owner:
                return reverse_lazy('companies:owner_dashboard')
            elif company_user.is_manager:
                return reverse_lazy('companies:manager_dashboard')
            else:
                return reverse_lazy('dashboard')
        except CompanyUser.DoesNotExist:
            return reverse_lazy('dashboard')
    
    def form_valid(self, form):
        """Traitement personnalisé du formulaire de connexion"""
        company_reference = self.request.POST.get('company_reference', '').strip().upper()
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        
        if not company_reference:
            messages.error(self.request, "La référence d'entreprise est requise.")
            return self.form_invalid(form)
        
        # Authentifier l'utilisateur
        user = authenticate(self.request, username=username, password=password)
        
        if user is None:
            messages.error(self.request, "Nom d'utilisateur ou mot de passe incorrect.")
            return self.form_invalid(form)
        
        if not user.is_active:
            messages.error(self.request, "Ce compte est désactivé.")
            return self.form_invalid(form)
        
        # Vérifier le profil d'entreprise
        try:
            company_user = user.company_profile
            
            # Si c'est un owner, la référence d'entreprise est ignorée
            if company_user.is_owner:
                login(self.request, user)
                messages.success(self.request, f"Bienvenue {user.get_full_name() or user.username} !")
                return redirect(self.get_success_url())
            
            # Pour les autres utilisateurs, vérifier l'entreprise
            if not company_user.company:
                messages.error(self.request, "Votre compte n'est associé à aucune entreprise.")
                return self.form_invalid(form)
            
            # Vérifier la référence d'entreprise
            if company_user.company.reference != company_reference:
                messages.error(self.request, "Référence d'entreprise incorrecte.")
                return self.form_invalid(form)
            
            # Vérifier que l'entreprise est active
            if not company_user.company.is_active:
                messages.error(self.request, "Votre entreprise n'est pas active. Contactez l'administrateur.")
                return self.form_invalid(form)
            
            # Vérifier que l'utilisateur est actif dans l'entreprise
            if not company_user.is_active:
                messages.error(self.request, "Votre compte est désactivé. Contactez votre manager.")
                return self.form_invalid(form)
            
            # Connexion réussie
            login(self.request, user)
            company_user.last_login_company = timezone.now()
            company_user.save()
            
            messages.success(
                self.request, 
                f"Bienvenue {user.get_full_name() or user.username} chez {company_user.company.name} !"
            )
            
            return redirect(self.get_success_url())
            
        except CompanyUser.DoesNotExist:
            messages.error(self.request, "Votre compte n'est pas configuré pour une entreprise. Contactez l'administrateur.")
            return self.form_invalid(form)
    
    def get_context_data(self, **kwargs):
        """Ajouter des données au contexte du template"""
        context = super().get_context_data(**kwargs)
        context['company_reference'] = self.request.POST.get('company_reference', '')
        return context


@sensitive_post_parameters()
@csrf_protect
@never_cache
def company_login_view(request):
    """Vue de connexion avec gestion des entreprises (fonction)"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        company_reference = request.POST.get('company_reference', '').strip().upper()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        if not all([company_reference, username, password]):
            messages.error(request, "Tous les champs sont requis.")
            return render(request, 'auth/login.html', {
                'company_reference': company_reference,
                'username': username
            })
        
        # Authentifier l'utilisateur
        user = authenticate(request, username=username, password=password)
        
        if user is None:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
            return render(request, 'auth/login.html', {
                'company_reference': company_reference,
                'username': username
            })
        
        if not user.is_active:
            messages.error(request, "Ce compte est désactivé.")
            return render(request, 'auth/login.html', {
                'company_reference': company_reference,
                'username': username
            })
        
        # Vérifier le profil d'entreprise
        try:
            company_user = user.company_profile
            
            # Si c'est un owner, la référence d'entreprise est ignorée
            if company_user.is_owner:
                login(request, user)
                messages.success(request, f"Bienvenue {user.get_full_name() or user.username} !")
                
                next_url = request.GET.get('next') or request.POST.get('next')
                if next_url:
                    return redirect(next_url)
                return redirect('companies:owner_dashboard')
            
            # Pour les autres utilisateurs, vérifier l'entreprise
            if not company_user.company:
                messages.error(request, "Votre compte n'est associé à aucune entreprise.")
                return render(request, 'auth/login.html', {
                    'company_reference': company_reference,
                    'username': username
                })
            
            # Vérifier la référence d'entreprise
            if company_user.company.reference != company_reference:
                messages.error(request, "Référence d'entreprise incorrecte.")
                return render(request, 'auth/login.html', {
                    'company_reference': company_reference,
                    'username': username
                })
            
            # Vérifier que l'entreprise est active
            if not company_user.company.is_active:
                messages.error(request, "Votre entreprise n'est pas active. Contactez l'administrateur.")
                return render(request, 'auth/login.html', {
                    'company_reference': company_reference,
                    'username': username
                })
            
            # Vérifier que l'utilisateur est actif dans l'entreprise
            if not company_user.is_active:
                messages.error(request, "Votre compte est désactivé. Contactez votre manager.")
                return render(request, 'auth/login.html', {
                    'company_reference': company_reference,
                    'username': username
                })
            
            # Connexion réussie
            login(request, user)
            company_user.last_login_company = timezone.now()
            company_user.save()
            
            messages.success(
                request, 
                f"Bienvenue {user.get_full_name() or user.username} chez {company_user.company.name} !"
            )
            
            # Redirection selon le rôle
            next_url = request.GET.get('next') or request.POST.get('next')
            if next_url:
                return redirect(next_url)
            
            if company_user.is_manager:
                return redirect('companies:manager_dashboard')
            else:
                return redirect('dashboard')
            
        except CompanyUser.DoesNotExist:
            print(f"DEBUG: Aucun profil d'entreprise trouvé pour {user.username}")
            messages.error(request, "Votre compte n'est pas configuré pour une entreprise. Contactez l'administrateur.")
            return render(request, 'auth/login.html', {
                'company_reference': company_reference,
                'username': username
            })
        except Exception as e:
            print(f"DEBUG: Erreur inattendue lors de l'accès au profil: {e}")
            messages.error(request, "Erreur lors de la connexion. Contactez l'administrateur.")
            return render(request, 'auth/login.html', {
                'company_reference': company_reference,
                'username': username
            })
    
    # GET request
    return render(request, 'auth/login.html', {
        'company_reference': request.GET.get('company_reference', ''),
        'next': request.GET.get('next', '')
    })
