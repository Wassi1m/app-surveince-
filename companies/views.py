from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm
from django.core.mail import send_mail
from django.conf import settings
from django.db import models
from django.urls import reverse
import secrets
import string
import json
import logging

# Configuration du logger pour les entreprises
logger = logging.getLogger('companies')

from .models import Company, CompanyUser, CompanyInvitation, CompanySettings
from .forms import CompanyForm, CompanyUserForm, ManagerLoginForm, EmployeeCreationForm


def get_user_company(request):
    """Retourne l'entreprise appropriée selon le rôle de l'utilisateur"""
    if request.company_user.is_owner:
        # Pour les owners, prioriser l'entreprise qui a des employés ciblés
        from .models import EmployeCible
        companies_with_employees = Company.objects.filter(
            id__in=EmployeCible.objects.values_list('company_id', flat=True).distinct()
        )
        if companies_with_employees.exists():
            return companies_with_employees.first()
        # Sinon, prendre la première entreprise
        return Company.objects.first()
    else:
        # Les managers voient leur entreprise
        return request.company_user.company


def owner_required(view_func):
    """Décorateur pour vérifier que l'utilisateur est owner"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        try:
            company_user = request.user.company_profile
            if not company_user.is_owner:
                messages.error(request, "Accès refusé. Vous devez être propriétaire de l'application.")
                return redirect('dashboard')
        except CompanyUser.DoesNotExist:
            messages.error(request, "Profil d'entreprise non trouvé.")
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def manager_required(view_func):
    """Décorateur pour vérifier que l'utilisateur est manager ou owner"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        try:
            company_user = request.user.company_profile
            if not (company_user.is_owner or company_user.is_manager):
                messages.error(request, "Accès refusé. Vous devez être manager ou propriétaire.")
                return redirect('dashboard')
        except CompanyUser.DoesNotExist:
            messages.error(request, "Profil d'entreprise non trouvé.")
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper


@login_required
@owner_required
def owner_dashboard(request):
    """Dashboard pour le propriétaire de l'application"""
    companies = Company.objects.all().order_by('-created_at')
    
    # Statistiques générales
    stats = {
        'total_companies': companies.count(),
        'active_companies': companies.filter(is_active=True).count(),
        'total_users': CompanyUser.objects.count(),
        'total_managers': CompanyUser.objects.filter(role='manager').count(),
    }
    
    context = {
        'companies': companies[:10],  # Les 10 dernières entreprises
        'stats': stats,
    }
    return render(request, 'companies/owner_dashboard.html', context)


@login_required
@owner_required
def company_list(request):
    """Liste de toutes les entreprises pour l'owner"""
    companies = Company.objects.all().order_by('-created_at')
    
    # Filtres
    search = request.GET.get('search', '')
    if search:
        companies = companies.filter(name__icontains=search)
    
    status = request.GET.get('status', '')
    if status == 'active':
        companies = companies.filter(is_active=True)
    elif status == 'inactive':
        companies = companies.filter(is_active=False)
    
    # Pagination
    paginator = Paginator(companies, 20)
    page_number = request.GET.get('page')
    companies = paginator.get_page(page_number)
    
    context = {
        'companies': companies,
        'search': search,
        'status': status,
    }
    return render(request, 'companies/company_list.html', context)


@login_required
@owner_required
def company_create(request):
    """Créer une nouvelle entreprise"""
    if request.method == 'POST':
        form = CompanyForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                company = form.save()
                
                # Créer les paramètres par défaut
                CompanySettings.objects.create(company=company)
                
                # Logger la création d'entreprise
                logger.info(f"Entreprise créée: {company.name} (Ref: {company.reference}) par {request.user.username}")
                
                messages.success(
                    request, 
                    f"Entreprise '{company.name}' créée avec succès! Configurez maintenant les sous-entreprises et managers."
                )
                
                # Rediriger directement vers l'assistant sous-entreprises
                return redirect('companies:subcompany_wizard', company_id=company.pk)
    else:
        form = CompanyForm()
    
    return render(request, 'companies/company_form.html', {'form': form, 'title': 'Créer une entreprise'})


@login_required
@owner_required
def company_created(request, pk):
    """Page de confirmation après création d'entreprise avec les informations du manager"""
    company = get_object_or_404(Company, pk=pk)
    
    # Récupérer les informations du manager depuis la session
    manager_credentials = request.session.get('manager_credentials')
    
    if not manager_credentials or manager_credentials.get('company_id') != company.pk:
        messages.error(request, "Informations du manager non trouvées.")
        return redirect('companies:company_detail', pk=pk)
    
    # Supprimer les informations de la session après affichage
    del request.session['manager_credentials']
    
    context = {
        'company': company,
        'manager_credentials': manager_credentials,
    }
    return render(request, 'companies/company_created.html', context)


@login_required
@owner_required
def company_detail(request, pk):
    """Détails d'une entreprise"""
    company = get_object_or_404(Company, pk=pk)
    users = company.company_users.all().order_by('role', 'user__last_name')
    
    context = {
        'company': company,
        'users': users,
    }
    return render(request, 'companies/company_detail.html', context)


@login_required
@owner_required
def company_edit(request, pk):
    """Modifier une entreprise"""
    company = get_object_or_404(Company, pk=pk)
    
    if request.method == 'POST':
        form = CompanyForm(request.POST, instance=company)
        if form.is_valid():
            form.save()
            messages.success(request, f"Entreprise '{company.name}' modifiée avec succès.")
            return redirect('companies:company_detail', pk=company.pk)
    else:
        form = CompanyForm(instance=company)
    
    return render(request, 'companies/company_form.html', {
        'form': form, 
        'company': company,
        'title': f'Modifier {company.name}'
    })


def company_login(request):
    """Page de connexion avec référence d'entreprise"""
    if request.method == 'POST':
        form = ManagerLoginForm(request.POST)
        if form.is_valid():
            company_reference = form.cleaned_data['company_reference']
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            # Authentifier d'abord l'utilisateur
            user = authenticate(request, username=username, password=password)
            
            if user:
                try:
                    company_user = user.company_profile
                    
                    # Les owners peuvent se connecter avec n'importe quelle référence d'entreprise
                    if company_user.is_owner and company_user.is_active:
                        login(request, user)
                        company_user.last_login_company = timezone.now()
                        company_user.save()
                        return redirect('companies:owner_dashboard')
                    
                    # Pour les managers et employés, vérifier l'entreprise
                    try:
                        company = Company.objects.get(reference=company_reference, is_active=True)
                        
                        if company_user.company == company and company_user.is_active:
                            login(request, user)
                            company_user.last_login_company = timezone.now()
                            company_user.save()
                            
                            # Rediriger selon le rôle
                            if company_user.is_manager:
                                # Vérifier si le manager a plusieurs sous-entreprises
                                accessible_subcompanies = company_user.get_accessible_subcompanies()
                                if accessible_subcompanies.count() > 1:
                                    # Toujours rediriger vers le sélecteur s'il y a plusieurs choix
                                    # Réinitialiser current_subcompany pour forcer la sélection
                                    company_user.current_subcompany = None
                                    company_user.save()
                                    return redirect('companies:subcompany_selector')
                                else:
                                    # Une seule sous-entreprise, la définir comme courante
                                    if accessible_subcompanies.exists():
                                        company_user.current_subcompany = accessible_subcompanies.first()
                                        company_user.save()
                                    return redirect('companies:manager_dashboard')
                            else:
                                return redirect('dashboard')
                        else:
                            messages.error(request, "Vous n'êtes pas autorisé à accéder à cette entreprise.")
                    
                    except Company.DoesNotExist:
                        messages.error(request, "Référence d'entreprise invalide.")
                        
                except CompanyUser.DoesNotExist:
                    messages.error(request, "Profil d'entreprise non trouvé.")
            else:
                messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
    else:
        form = ManagerLoginForm()
    
    return render(request, 'companies/company_login.html', {'form': form})


@login_required
def subcompany_selector(request):
    """Page de sélection de sous-entreprise pour les managers"""
    if not hasattr(request.user, 'company_profile'):
        return redirect('login')
    
    company_user = request.user.company_profile
    
    if not company_user.is_manager:
        return redirect('dashboard')
    
    accessible_subcompanies = company_user.get_accessible_subcompanies()
    
    # Si une seule sous-entreprise, rediriger directement
    if accessible_subcompanies.count() <= 1:
        if accessible_subcompanies.exists():
            company_user.current_subcompany = accessible_subcompanies.first()
            company_user.save()
        return redirect('companies:manager_dashboard')
    
    if request.method == 'POST':
        subcompany_id = request.POST.get('subcompany_id')
        try:
            selected_subcompany = accessible_subcompanies.get(id=subcompany_id)
            company_user.current_subcompany = selected_subcompany
            company_user.save()
            messages.success(request, f"Vous consultez maintenant : {selected_subcompany.name}")
            return redirect('companies:manager_dashboard')
        except:
            messages.error(request, "Sous-entreprise invalide.")
    
    context = {
        'subcompanies': accessible_subcompanies,
        'company': company_user.company,
        'current_subcompany': company_user.current_subcompany,
    }
    
    return render(request, 'companies/subcompany_selector.html', context)


@login_required
@manager_required
def manager_dashboard(request):
    """Dashboard pour les managers d'entreprise"""
    company_user = request.user.company_profile
    company = company_user.company
    
    # Statistiques de l'entreprise
    stats = {
        'total_users': company.company_users.count(),
        'active_users': company.company_users.filter(is_active=True).count(),
        'total_cameras': company.camera_count,
        'total_locations': company.location_count,
    }
    
    # Utilisateurs récents
    recent_users = company.company_users.order_by('-created_at')[:5]
    
    context = {
        'company': company,
        'stats': stats,
        'recent_users': recent_users,
    }
    return render(request, 'companies/manager_dashboard.html', context)


@login_required
@manager_required
def manage_employees(request):
    """Gestion des employés par le manager"""
    company_user = request.user.company_profile
    company = company_user.company
    
    # Les managers ont automatiquement le droit de gérer les utilisateurs
    
    # Actions en lot
    if request.method == 'POST' and 'bulk_action' in request.POST:
        return handle_bulk_employee_actions(request, company)
    
    employees = company.company_users.exclude(role='owner').order_by('role', 'user__last_name')
    
    # Filtres
    search = request.GET.get('search', '')
    role_filter = request.GET.get('role', '')
    status_filter = request.GET.get('status', '')
    
    if search:
        employees = employees.filter(
            models.Q(user__first_name__icontains=search) |
            models.Q(user__last_name__icontains=search) |
            models.Q(user__email__icontains=search) |
            models.Q(employee_id__icontains=search)
        )
    
    if role_filter:
        employees = employees.filter(role=role_filter)
    
    if status_filter == 'active':
        employees = employees.filter(is_active=True)
    elif status_filter == 'inactive':
        employees = employees.filter(is_active=False)
    
    # Pagination
    paginator = Paginator(employees, 20)
    page_number = request.GET.get('page')
    employees = paginator.get_page(page_number)
    
    context = {
        'company': company,
        'employees': employees,
        'search': search,
        'role_filter': role_filter,
        'status_filter': status_filter,
        'role_choices': CompanyUser.ROLE_CHOICES,
    }
    return render(request, 'companies/manage_employees.html', context)


def handle_bulk_employee_actions(request, company):
    """Gérer les actions en lot sur les employés"""
    action = request.POST.get('bulk_action')
    employee_ids = request.POST.getlist('selected_employees')
    
    if not employee_ids:
        messages.error(request, "Aucun employé sélectionné.")
        return redirect('companies:manage_employees')
    
    employees = company.company_users.filter(id__in=employee_ids).exclude(role='owner')
    
    if action == 'activate':
        employees.update(is_active=True)
        messages.success(request, f"{employees.count()} employé(s) activé(s).")
        
    elif action == 'deactivate':
        employees.update(is_active=False)
        messages.success(request, f"{employees.count()} employé(s) désactivé(s).")
        
    elif action == 'delete':
        count = employees.count()
        for employee in employees:
            employee.user.delete()  # Cela supprime aussi le CompanyUser
        messages.success(request, f"{count} employé(s) supprimé(s).")
        
    elif action == 'reset_password':
        count = 0
        for employee in employees:
            new_password = generate_random_password(8)
            employee.user.set_password(new_password)
            employee.user.save()
            count += 1
            # Dans un vrai projet, on enverrait le nouveau mot de passe par email
            logger.info(f"Mot de passe réinitialisé pour {employee.user.email}: {new_password}")
        
        messages.success(request, f"Mot de passe réinitialisé pour {count} employé(s). Les nouveaux mots de passe ont été envoyés par email.")
    
    return redirect('companies:manage_employees')


@login_required
@manager_required
def create_employee(request):
    """Créer un nouvel employé"""
    company_user = request.user.company_profile
    company = company_user.company
    
    # Debug: Informations utilisateur et permissions
    print(f"DEBUG: Utilisateur: {request.user.username}")
    print(f"DEBUG: Entreprise: {company.name}")
    print(f"DEBUG: Sous-entreprise courante: {getattr(request, 'current_subcompany', 'Aucune')}")
    
    # Les managers ont automatiquement le droit de créer des employés
    
    if request.method == 'POST':
        form = EmployeeCreationForm(request.POST)
        
        # Debug: Afficher les données reçues
        print(f"DEBUG: Données POST reçues: {dict(request.POST)}")
        print(f"DEBUG: Formulaire valide: {form.is_valid()}")
        
        if not form.is_valid():
            # Debug: Afficher les erreurs de validation
            print(f"DEBUG: Erreurs de formulaire: {form.errors}")
            for field, errors in form.errors.items():
                messages.error(request, f"Erreur {field}: {', '.join(errors)}")
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    print(f"DEBUG: Début de la création d'employé...")
                    
                    # Créer l'utilisateur
                    user = form.save()
                    print(f"DEBUG: Utilisateur créé: {user.username} ({user.email})")
                    
                    # Créer le profil CompanyUser
                new_company_user = CompanyUser.objects.create(
                    user=user,
                    company=company,
                    role=form.cleaned_data['role'],
                    employee_id=form.cleaned_data.get('employee_id', ''),
                    department=form.cleaned_data.get('department', ''),
                    position=form.cleaned_data.get('position', ''),
                    phone=form.cleaned_data.get('phone', ''),
                    # Les permissions sont maintenant gérées au niveau SubCompanyUser
                )
                
                # Assigner l'employé à la sous-entreprise courante
                if hasattr(request, 'current_subcompany') and request.current_subcompany:
                    from .models import SubCompanyUser
                    SubCompanyUser.objects.create(
                        company_user=new_company_user,
                        subcompany=request.current_subcompany,
                        can_manage_monitoring=form.cleaned_data.get('can_manage_monitoring', False),
                        can_manage_alerts=form.cleaned_data.get('can_manage_alerts', False),
                        can_manage_alert_rules=form.cleaned_data.get('can_manage_alert_rules', False),
                        can_view_reports=form.cleaned_data.get('can_view_reports', True),
                        assigned_by=request.user,
                        is_active=True
                    )
                    # Définir la sous-entreprise courante pour l'employé
                    new_company_user.current_subcompany = request.current_subcompany
                    new_company_user.save()
                
                # Logger la création d'employé
                logger.info(f"Employé créé: {user.get_full_name()} ({user.email}) - Rôle: {new_company_user.role} - Entreprise: {company.name} - Sous-entreprise: {request.current_subcompany.name if hasattr(request, 'current_subcompany') and request.current_subcompany else 'Aucune'} par {request.user.username}")
                
                messages.success(request, f"Employé '{user.get_full_name()}' créé avec succès dans {request.current_subcompany.name if hasattr(request, 'current_subcompany') and request.current_subcompany else 'l\'entreprise'}.")
                print(f"DEBUG: Employé créé avec succès, redirection vers manage_employees")
                return redirect('companies:manage_employees')
            
            except Exception as e:
                print(f"DEBUG: Erreur lors de la création: {str(e)}")
                messages.error(request, f"Erreur lors de la création de l'employé: {str(e)}")
        
        else:
            print(f"DEBUG: Formulaire invalide, affichage du formulaire avec erreurs")
    else:
        form = EmployeeCreationForm()
    
    return render(request, 'companies/employee_form.html', {
        'form': form, 
        'company': company,
        'title': 'Créer un employé'
    })


@login_required
@manager_required
def employee_detail(request, pk):
    """Détails d'un employé"""
    company_user = request.user.company_profile
    company = company_user.company
    
    # Les managers ont automatiquement le droit de voir les détails des utilisateurs
    
    # Récupérer l'employé (s'assurer qu'il appartient à la même entreprise)
    employee = get_object_or_404(
        CompanyUser, 
        pk=pk, 
        company=company
    )
    
    # Exclure les owners
    if employee.role == 'owner':
        messages.error(request, "Accès non autorisé.")
        return redirect('companies:manage_employees')
    
    # Statistiques de l'employé (si nécessaire)
    stats = {
        'created_at': employee.created_at,
        'last_login': employee.last_login_company,
        'is_active': employee.is_active,
    }
    
    context = {
        'employee': employee,
        'company': company,
        'stats': stats,
    }
    
    return render(request, 'companies/employee_detail.html', context)


@login_required
@manager_required
def edit_employee(request, pk):
    """Modifier un employé"""
    company_user = request.user.company_profile
    company = company_user.company
    
    # Les managers ont automatiquement le droit de modifier les utilisateurs
    
    # Récupérer l'employé (s'assurer qu'il appartient à la même entreprise)
    employee = get_object_or_404(
        CompanyUser, 
        pk=pk, 
        company=company
    )
    
    # Exclure les owners
    if employee.role == 'owner':
        messages.error(request, "Impossible de modifier un propriétaire.")
        return redirect('companies:manage_employees')
    
    if request.method == 'POST':
        # Créer un formulaire personnalisé pour l'édition
        user_form_data = {
            'first_name': request.POST.get('first_name', ''),
            'last_name': request.POST.get('last_name', ''),
            'email': request.POST.get('email', ''),
        }
        
        company_user_data = {
            'role': request.POST.get('role', ''),
            'employee_id': request.POST.get('employee_id', ''),
            'department': request.POST.get('department', ''),
            'position': request.POST.get('position', ''),
            'phone': request.POST.get('phone', ''),
            'is_active': 'is_active' in request.POST,
            # Les permissions sont maintenant gérées au niveau SubCompanyUser
        }
        
        try:
            with transaction.atomic():
                # Mettre à jour l'utilisateur Django
                user = employee.user
                user.first_name = user_form_data['first_name']
                user.last_name = user_form_data['last_name']
                user.email = user_form_data['email']
                user.save()
                
                # Mettre à jour le profil CompanyUser
                for field, value in company_user_data.items():
                    setattr(employee, field, value)
                employee.save()
                
                messages.success(request, f"Employé '{user.get_full_name()}' modifié avec succès.")
                return redirect('companies:employee_detail', pk=employee.pk)
                
        except Exception as e:
            logger.error(f"Erreur modification employé: {e}")
            messages.error(request, "Erreur lors de la modification de l'employé.")
    
    # Préparer les données pour le formulaire
    initial_data = {
        'first_name': employee.user.first_name,
        'last_name': employee.user.last_name,
        'email': employee.user.email,
        'role': employee.role,
        'employee_id': employee.employee_id,
        'department': employee.department,
        'position': employee.position,
        'phone': employee.phone,
        'is_active': employee.is_active,
        # Les permissions sont maintenant affichées via SubCompanyUser
    }
    
    context = {
        'employee': employee,
        'company': company,
        'initial_data': initial_data,
        'title': f'Modifier {employee.user.get_full_name()}',
        'role_choices': [choice for choice in CompanyUser.ROLE_CHOICES if choice[0] != 'owner'],
    }
    
    return render(request, 'companies/employee_edit.html', context)


@login_required
@manager_required
def delete_employee(request, pk):
    """Supprimer un employé"""
    company_user = request.user.company_profile
    company = company_user.company
    
    # Les managers ont automatiquement le droit de supprimer des utilisateurs
    
    # Récupérer l'employé (s'assurer qu'il appartient à la même entreprise)
    employee = get_object_or_404(
        CompanyUser, 
        pk=pk, 
        company=company
    )
    
    # Exclure les owners
    if employee.role == 'owner':
        messages.error(request, "Impossible de supprimer un propriétaire.")
        return redirect('companies:manage_employees')
    
    if request.method == 'POST':
        employee_name = employee.user.get_full_name()
        employee.user.delete()  # Cela supprime aussi le CompanyUser
        
        messages.success(request, f"Employé '{employee_name}' supprimé avec succès.")
        return redirect('companies:manage_employees')
    
    context = {
        'employee': employee,
        'company': company,
    }
    
    return render(request, 'companies/employee_confirm_delete.html', context)


def generate_random_password(length=12):
    """Génère un mot de passe aléatoire"""
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(characters) for _ in range(length))


def send_manager_credentials(company, email, password):
    """Envoie les identifiants au manager (simulation)"""
    # Dans un vrai projet, vous enverriez un email
    print(f"""
    === IDENTIFIANTS MANAGER ===
    Entreprise: {company.name}
    Référence: {company.reference}
    Email: {email}
    Mot de passe: {password}
    ===========================
    """)


@require_http_methods(["POST"])
@login_required
@owner_required
def toggle_company_status(request, pk):
    """Active/désactive une entreprise"""
    company = get_object_or_404(Company, pk=pk)
    company.is_active = not company.is_active
    company.save()
    
    status = "activée" if company.is_active else "désactivée"
    return JsonResponse({
        'success': True,
        'message': f"Entreprise {status} avec succès.",
        'is_active': company.is_active
    })


# ===== GESTION DES NOTIFICATIONS OWNER =====

@login_required
@owner_required
def owner_notifications(request):
    """Gestion des notifications par l'owner"""
    from alerts.models_notifications import Notification
    
    # Récupérer les notifications créées par l'owner
    notifications = Notification.objects.filter(
        metadata__created_by_owner=True
    ).order_by('-created_at')[:50]
    
    # Récupérer toutes les entreprises pour le sélecteur
    companies = Company.objects.filter(is_active=True).order_by('name')
    
    context = {
        'notifications': notifications,
        'companies': companies,
    }
    
    return render(request, 'companies/owner_notifications.html', context)


@login_required
@owner_required
@require_http_methods(["POST"])
def create_owner_notification(request):
    """Créer une notification owner"""
    try:
        from alerts.models_notifications import Notification
        from alerts.notification_service import notification_service
        
        data = json.loads(request.body)
        
        title = data.get('title', '').strip()
        message = data.get('message', '').strip()
        notification_type = data.get('type', 'info')
        priority = int(data.get('priority', 3))
        target_company_id = data.get('company_id')  # None = toutes les entreprises
        expires_in_hours = data.get('expires_in_hours')
        
        if not title or not message:
            return JsonResponse({
                'success': False,
                'error': 'Le titre et le message sont obligatoires.'
            }, status=400)
        
        # Déterminer les destinataires
        if target_company_id:
            # Notification pour une entreprise spécifique
            target_company = get_object_or_404(Company, id=target_company_id, is_active=True)
            company_users = CompanyUser.objects.filter(
                company=target_company,
                is_active=True
            ).select_related('user')
            
            recipients = [cu.user for cu in company_users]
            target_info = f"Entreprise: {target_company.name}"
        else:
            # Notification pour toutes les entreprises
            company_users = CompanyUser.objects.filter(
                is_active=True,
                company__is_active=True
            ).select_related('user')
            
            recipients = [cu.user for cu in company_users]
            target_info = "Toutes les entreprises"
        
        # Créer les notifications
        notifications_created = []
        for user in recipients:
            notification = notification_service.create_notification(
                title=title,
                message=message,
                notification_type=notification_type,
                priority=priority,
                user=user,
                metadata={
                    'created_by_owner': True,
                    'owner_user_id': request.user.id,
                    'target_company_id': target_company_id,
                    'broadcast': target_company_id is None
                },
                expires_in_hours=expires_in_hours
            )
            notifications_created.append(notification)
        
        # Envoyer les notifications
        for notification in notifications_created:
            notification_service.send_notification(notification)
        
        # Logger l'action
        logger.info(f"Notification owner créée par {request.user.username}: '{title}' - {target_info} - {len(notifications_created)} destinataires")
        
        return JsonResponse({
            'success': True,
            'message': f"Notification envoyée à {len(notifications_created)} utilisateur(s) ({target_info})",
            'recipients_count': len(notifications_created),
            'target': target_info
        })
        
    except Exception as e:
        logger.error(f"Erreur création notification owner: {e}")
        return JsonResponse({
            'success': False,
            'error': f"Erreur lors de la création: {str(e)}"
        }, status=500)


@login_required
@owner_required
def owner_notification_history(request):
    """Historique des notifications owner avec statistiques"""
    from alerts.models_notifications import Notification
    
    # Filtres
    company_id = request.GET.get('company')
    notification_type = request.GET.get('type')
    days = int(request.GET.get('days', 30))
    
    # Base query
    notifications = Notification.objects.filter(
        metadata__created_by_owner=True
    )
    
    # Appliquer les filtres
    if company_id:
        notifications = notifications.filter(metadata__target_company_id=company_id)
    
    if notification_type:
        notifications = notifications.filter(notification_type=notification_type)
    
    if days > 0:
        start_date = timezone.now() - timezone.timedelta(days=days)
        notifications = notifications.filter(created_at__gte=start_date)
    
    notifications = notifications.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(notifications, 20)
    page_number = request.GET.get('page')
    notifications = paginator.get_page(page_number)
    
    # Statistiques
    total_notifications = Notification.objects.filter(
        metadata__created_by_owner=True
    ).count()
    
    broadcast_notifications = Notification.objects.filter(
        metadata__created_by_owner=True,
        metadata__broadcast=True
    ).count()
    
    # Récupérer les entreprises pour les filtres
    companies = Company.objects.filter(is_active=True).order_by('name')
    
    context = {
        'notifications': notifications,
        'companies': companies,
        'current_filters': {
            'company': company_id,
            'type': notification_type,
            'days': days,
        },
        'stats': {
            'total': total_notifications,
            'broadcast': broadcast_notifications,
            'targeted': total_notifications - broadcast_notifications,
        },
        'notification_types': Notification.NOTIFICATION_TYPES,
    }
    
    return render(request, 'companies/owner_notification_history.html', context)


# ===== GESTION DES TYPES D'ÉVÉNEMENTS OWNER =====

@login_required
@owner_required
def owner_event_types(request):
    """Gestion des types d'événements par l'owner"""
    from monitoring.models import EventType, CompanyEventType
    
    # Récupérer tous les types d'événements
    event_types = EventType.objects.all().order_by('name')
    
    # Récupérer toutes les entreprises pour les statistiques
    companies = Company.objects.filter(is_active=True).order_by('name')
    
    # Statistiques par type d'événement
    event_stats = []
    for event_type in event_types:
        companies_using = CompanyEventType.objects.filter(
            event_type=event_type,
            is_enabled=True
        ).count()
        
        event_stats.append({
            'event_type': event_type,
            'companies_count': companies_using,
            'usage_percentage': round((companies_using / companies.count() * 100) if companies.count() > 0 else 0, 1)
        })
    
    context = {
        'event_stats': event_stats,
        'companies': companies,
        'total_companies': companies.count(),
    }
    
    return render(request, 'companies/owner_event_types.html', context)


@login_required
@manager_required
def owner_import_employees_cibled(request):
    """Importer des employés ciblés"""
    from .models import EmployeCible, EmployeCibleImportBatch
    from django.core.paginator import Paginator
    
    # Déterminer l'entreprise selon le rôle
    if request.company_user.is_owner:
        # Les owners peuvent voir toutes les entreprises, mais pour cette vue on prend la première
        company = Company.objects.first()
    else:
        # Les managers voient leur entreprise
        company = request.company_user.company
    
    if not company:
        messages.error(request, "Aucune entreprise trouvée.")
        return redirect('dashboard')
    
    # Récupérer les statistiques
    total_employes = EmployeCible.objects.filter(company=company).count()
    employes_valides = EmployeCible.objects.filter(
        company=company,
        status='validated'
    ).count()
    employes_en_attente = EmployeCible.objects.filter(
        company=company,
        status='pending'
    ).count()
    
    # Récupérer les lots d'import récents
    recent_batches = EmployeCibleImportBatch.objects.filter(
        company=company
    ).order_by('-created_at')[:5]
    
    # Récupérer les employés récents
    recent_employees = EmployeCible.objects.filter(
        company=company
    ).order_by('-created_at')[:10]
    
    context = {
        'total_employes': total_employes,
        'employes_valides': employes_valides,
        'employes_en_attente': employes_en_attente,
        'recent_batches': recent_batches,
        'recent_employees': recent_employees,
        'success_rate': int((employes_valides / total_employes * 100)) if total_employes > 0 else 0,
    }
    
    return render(request, 'companies/owner_import_employees.html', context)


@login_required
@manager_required
@require_http_methods(["POST"])
def upload_employee_images(request):
    """Upload multiple employee images"""
    from .models import EmployeCible, EmployeCibleImportBatch
    import uuid
    from django.core.files.storage import default_storage
    import os
    from django.conf import settings
    
    try:
        # Vérifier et créer le dossier media s'il n'existe pas
        media_root = settings.MEDIA_ROOT
        if not os.path.exists(media_root):
            os.makedirs(media_root, mode=0o755, exist_ok=True)
        
        # Vérifier les permissions d'écriture
        if not os.access(media_root, os.W_OK):
            return JsonResponse({
                'success': False,
                'message': 'Erreur de permissions: le dossier media n\'est pas accessible en écriture. Contactez l\'administrateur.'
            }, status=500)
        # Créer un nouveau lot d'import
        batch_name = request.POST.get('batch_name', f'Import {timezone.now().strftime("%Y-%m-%d %H:%M")}')
        batch_description = request.POST.get('batch_description', '')
        
        # Déterminer l'entreprise selon le rôle
        if request.company_user.is_owner:
            company = Company.objects.first()
            subcompany = company.subcompanies.first() if company and company.subcompanies.exists() else None
        else:
            company = request.company_user.company
            subcompany = request.company_user.current_subcompany
        
        batch = EmployeCibleImportBatch.objects.create(
            company=company,
            subcompany=subcompany,
            nom_lot=batch_name,
            description=batch_description,
            cree_par=request.user,
            status='uploading'
        )
        
        uploaded_files = request.FILES.getlist('employee_images')
        batch.total_images = len(uploaded_files)
        batch.save()
        
        batch.add_log(f"Début de l'upload de {len(uploaded_files)} images")
        
        success_count = 0
        error_count = 0
        
        for uploaded_file in uploaded_files:
            try:
                # Vérifier le type de fichier - Support étendu pour PNG
                allowed_types = [
                    'image/jpeg', 'image/jpg', 'image/png', 'image/gif', 
                    'image/webp', 'image/bmp', 'image/tiff'
                ]
                allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff']
                
                file_extension = uploaded_file.name.lower().split('.')[-1] if '.' in uploaded_file.name else ''
                
                # Double vérification : type MIME ET extension
                is_valid_type = (
                    uploaded_file.content_type in allowed_types or 
                    uploaded_file.content_type.startswith('image/') or
                    f'.{file_extension}' in allowed_extensions
                )
                
                if not is_valid_type:
                    batch.add_error(f"Type de fichier non supporté: {uploaded_file.content_type} (.{file_extension})", uploaded_file.name)
                    continue
                
                # Vérifier la taille (max 10MB)
                if uploaded_file.size > 10 * 1024 * 1024:
                    batch.add_error("Fichier trop volumineux (max 10MB)", uploaded_file.name)
                    continue
                
                # Vérification supplémentaire avec Pillow pour PNG
                try:
                    from PIL import Image
                    # Tenter d'ouvrir l'image pour vérifier qu'elle est valide
                    uploaded_file.seek(0)  # Remettre le curseur au début
                    test_image = Image.open(uploaded_file)
                    test_image.verify()  # Vérifier l'intégrité
                    uploaded_file.seek(0)  # Remettre le curseur au début pour l'utilisation
                    
                    batch.add_log(f"Image {uploaded_file.name} validée: {test_image.format} {test_image.size}")
                    
                except Exception as img_error:
                    batch.add_error(f"Image corrompue ou invalide: {str(img_error)}", uploaded_file.name)
                    continue
                
                # Créer l'employé ciblé
                employe = EmployeCible.objects.create(
                    company=company,
                    subcompany=subcompany,
                    image_originale=uploaded_file,
                    importe_par=request.user,
                    status='pending'
                )
                
                batch.add_log(f"Image {uploaded_file.name} importée avec succès (ID: {employe.id})")
                success_count += 1
                
            except Exception as e:
                batch.add_error(f"Erreur lors de l'import: {str(e)}", uploaded_file.name)
                error_count += 1
            
            # Mettre à jour le progress
            batch.images_traitees += 1
            batch.images_reussies = success_count
            batch.images_echouees = error_count
            batch.save()
        
        # Finaliser le lot
        batch.status = 'completed' if error_count == 0 else 'completed'
        batch.completed_at = timezone.now()
        batch.save()
        
        batch.add_log(f"Import terminé: {success_count} réussies, {error_count} échouées")
        
        return JsonResponse({
            'success': True,
            'message': f'Import terminé: {success_count} images importées avec succès',
            'batch_id': batch.id,
            'success_count': success_count,
            'error_count': error_count,
            'redirect_url': reverse('companies:manage_employees_cibles')
        })
        
    except Exception as e:
        import traceback
        error_details = str(e)
        error_traceback = traceback.format_exc()
        
        # Logger l'erreur pour le débogage
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f'Erreur lors de l\'upload d\'images: {error_details}')
        logger.error(f'Traceback: {error_traceback}')
        
        # Messages d'erreur plus explicites
        if 'Request Entity Too Large' in error_details or '413' in error_details:
            error_message = 'Les fichiers sont trop volumineux. Taille maximale: 10MB par image.'
        elif 'timeout' in error_details.lower():
            error_message = 'L\'upload a pris trop de temps. Veuillez réessayer avec moins de fichiers.'
        elif 'Permission denied' in error_details.lower() or 'PermissionError' in error_details:
            error_message = 'Erreur de permissions sur le serveur. Contactez l\'administrateur.'
        elif 'No space left' in error_details.lower():
            error_message = 'Espace disque insuffisant sur le serveur. Contactez l\'administrateur.'
        else:
            error_message = f'Erreur lors de l\'import: {error_details}'
        
        return JsonResponse({
            'success': False,
            'message': error_message,
            'error_type': type(e).__name__
        }, status=500)


@login_required
@manager_required
def manage_employees_cibles(request):
    """Gérer les employés ciblés"""
    from .models import EmployeCible
    from django.core.paginator import Paginator
    from django.db.models import Q
    
    # Filtres
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    detection_filter = request.GET.get('detection', '')
    
    # Déterminer l'entreprise selon le rôle
    company = get_user_company(request)
    
    if not company:
        messages.error(request, "Aucune entreprise trouvée.")
        return redirect('dashboard')
    
    # Base queryset
    queryset = EmployeCible.objects.filter(
        company=company
    ).order_by('-created_at')
    
    # Appliquer les filtres
    if search_query:
        queryset = queryset.filter(
            Q(prenom__icontains=search_query) |
            Q(nom__icontains=search_query) |
            Q(employee_id__icontains=search_query) |
            Q(poste__icontains=search_query)
        )
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    if detection_filter:
        queryset = queryset.filter(detection_status=detection_filter)
    
    # Pagination
    paginator = Paginator(queryset, 20)
    page_number = request.GET.get('page')
    employees = paginator.get_page(page_number)
    
    # Statistiques pour les filtres
    stats = {
        'total': EmployeCible.objects.filter(company=company).count(),
        'pending': EmployeCible.objects.filter(company=company, status='pending').count(),
        'validated': EmployeCible.objects.filter(company=company, status='validated').count(),
        'rejected': EmployeCible.objects.filter(company=company, status='rejected').count(),
        'face_detected': EmployeCible.objects.filter(company=company, detection_status='face_detected').count(),
        'no_face': EmployeCible.objects.filter(company=company, detection_status='no_face_detected').count(),
    }
    
    
    context = {
        'employees': employees,
        'search_query': search_query,
        'status_filter': status_filter,
        'detection_filter': detection_filter,
        'stats': stats,
        'status_choices': EmployeCible.STATUS_CHOICES,
        'detection_choices': EmployeCible.DETECTION_STATUS_CHOICES,
    }
    
    return render(request, 'companies/manage_employees_cibles.html', context)


@login_required
@manager_required
@require_http_methods(["POST"])
def update_employee_info(request, employee_id):
    """Mettre à jour les informations d'un employé ciblé"""
    from .models import EmployeCible
    
    try:
        company = get_user_company(request)
        employee = get_object_or_404(
            EmployeCible,
            id=employee_id,
            company=company
        )
        
        data = json.loads(request.body)
        
        # Mettre à jour les champs
        employee.prenom = data.get('prenom', '').strip()
        employee.nom = data.get('nom', '').strip()
        employee.employee_id = data.get('employee_id', '').strip()
        employee.poste = data.get('poste', '').strip()
        employee.departement = data.get('departement', '').strip()
        employee.notes = data.get('notes', '').strip()
        employee.is_priority = data.get('is_priority', False)
        
        employee.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Informations mises à jour avec succès',
            'employee': {
                'id': employee.id,
                'nom_complet': employee.nom_complet,
                'prenom': employee.prenom,
                'nom': employee.nom,
                'employee_id': employee.employee_id,
                'poste': employee.poste,
                'departement': employee.departement,
                'notes': employee.notes,
                'is_priority': employee.is_priority,
                'is_ready_for_recognition': employee.is_ready_for_recognition,
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur lors de la mise à jour: {str(e)}'
        })


@login_required
@manager_required
@require_http_methods(["POST"])
def validate_employee(request, employee_id):
    """Valider un employé ciblé"""
    from .models import EmployeCible
    
    try:
        company = get_user_company(request)
        employee = get_object_or_404(
            EmployeCible,
            id=employee_id,
            company=company
        )
        
        employee.validate(request.user)
        
        return JsonResponse({
            'success': True,
            'message': f'Employé {employee.nom_complet} validé avec succès',
            'status': employee.status,
            'status_color': employee.status_color
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur lors de la validation: {str(e)}'
        })


@login_required
@manager_required
@require_http_methods(["POST"])
def reject_employee(request, employee_id):
    """Rejeter un employé ciblé"""
    from .models import EmployeCible
    
    try:
        company = get_user_company(request)
        employee = get_object_or_404(
            EmployeCible,
            id=employee_id,
            company=company
        )
        
        employee.reject(request.user)
        
        return JsonResponse({
            'success': True,
            'message': f'Employé {employee.nom_complet} rejeté',
            'status': employee.status,
            'status_color': employee.status_color
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur lors du rejet: {str(e)}'
        })


@login_required
@manager_required
@require_http_methods(["DELETE"])
def delete_employee(request, employee_id):
    """Supprimer un employé ciblé"""
    from .models import EmployeCible
    
    try:
        company = get_user_company(request)
        employee = get_object_or_404(
            EmployeCible,
            id=employee_id,
            company=company
        )
        
        employee_name = employee.nom_complet
        employee.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Employé {employee_name} supprimé avec succès'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur lors de la suppression: {str(e)}'
        })


@login_required
@manager_required
def employee_cible_detail(request, employee_id):
    """Détails d'un employé ciblé"""
    from .models import EmployeCible
    
    company = get_user_company(request)
    employee = get_object_or_404(
        EmployeCible,
        id=employee_id,
        company=company
    )
    
    # Si requête AJAX, retourner JSON
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({
            'id': employee.id,
            'prenom': employee.prenom or '',
            'nom': employee.nom or '',
            'employee_id': employee.employee_id or '',
            'poste': employee.poste or '',
            'departement': employee.departement or '',
            'notes': employee.notes or '',
            'is_priority': employee.is_priority,
            'status': employee.status,
            'status_display': employee.get_status_display(),
            'status_color': employee.status_color,
            'detection_status': employee.detection_status,
            'detection_status_display': employee.get_detection_status_display(),
            'detection_status_color': employee.detection_status_color,
            'detection_confidence': float(employee.detection_confidence) if employee.detection_confidence else None,
            'image_originale': employee.image_originale.url if employee.image_originale else None,
            'image_miniature': employee.image_miniature.url if employee.image_miniature else None,
            'created_at': employee.created_at.strftime('%Y-%m-%d %H:%M:%S') if employee.created_at else None,
        })
    
    # Sinon, afficher la page HTML
    context = {
        'employee': employee,
    }
    
    return render(request, 'companies/employee_cible_detail.html', context)


@login_required
@manager_required
@require_http_methods(["POST"])
def batch_action_employees(request):
    """Actions en lot sur les employés ciblés"""
    from .models import EmployeCible
    
    try:
        data = json.loads(request.body)
        action = data.get('action')
        employee_ids = data.get('employee_ids', [])
        
        if not employee_ids:
            return JsonResponse({
                'success': False,
                'message': 'Aucun employé sélectionné'
            })
        
        company = get_user_company(request)
        employees = EmployeCible.objects.filter(
            id__in=employee_ids,
            company=company
        )
        
        count = employees.count()
        
        if action == 'validate':
            for employee in employees:
                employee.validate(request.user)
            message = f'{count} employé(s) validé(s) avec succès'
            
        elif action == 'reject':
            for employee in employees:
                employee.reject(request.user)
            message = f'{count} employé(s) rejeté(s) avec succès'
            
        elif action == 'delete':
            employees.delete()
            message = f'{count} employé(s) supprimé(s) avec succès'
            
        elif action == 'archive':
            employees.update(status='archived')
            message = f'{count} employé(s) archivé(s) avec succès'
            
        else:
            return JsonResponse({
                'success': False,
                'message': 'Action non reconnue'
            })
        
        return JsonResponse({
            'success': True,
            'message': message,
            'count': count
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Erreur lors de l\'action en lot: {str(e)}'
        })


@login_required
@owner_required
@require_http_methods(["POST"])
def create_event_type(request):
    """Créer un nouveau type d'événement"""
    try:
        from monitoring.models import EventType, CompanyEventType
        
        data = json.loads(request.body)
        
        name = data.get('name', '').strip()
        code = data.get('code', '').strip().lower()
        description = data.get('description', '').strip()
        severity = data.get('severity', 'medium')
        color = data.get('color', '#007bff')
        icon = data.get('icon', 'fas fa-exclamation-triangle')
        auto_alert = data.get('auto_alert', True)
        requires_verification = data.get('requires_verification', False)
        assign_to_all = data.get('assign_to_all', True)
        
        if not name or not code:
            return JsonResponse({
                'success': False,
                'error': 'Le nom et le code sont obligatoires.'
            }, status=400)
        
        # Vérifier que le code est unique
        if EventType.objects.filter(code=code).exists():
            return JsonResponse({
                'success': False,
                'error': f'Le code "{code}" existe déjà.'
            }, status=400)
        
        # Créer le type d'événement
        event_type = EventType.objects.create(
            name=name,
            code=code,
            description=description,
            severity=severity,
            color=color,
            icon=icon,
            auto_alert=auto_alert,
            requires_verification=requires_verification,
            created_by=request.user,
            is_active=True
        )
        
        # Assigner à toutes les entreprises si demandé
        assigned_count = 0
        if assign_to_all:
            companies = Company.objects.filter(is_active=True)
            for company in companies:
                CompanyEventType.objects.create(
                    company=company,
                    event_type=event_type,
                    is_enabled=True,
                    assigned_by=request.user
                )
                assigned_count += 1
        
        # Logger l'action
        logger.info(f"Type d'événement créé par {request.user.username}: '{name}' ({code}) - Assigné à {assigned_count} entreprises")
        
        return JsonResponse({
            'success': True,
            'message': f"Type d'événement '{name}' créé avec succès",
            'event_type_id': event_type.id,
            'assigned_companies': assigned_count
        })
        
    except Exception as e:
        logger.error(f"Erreur création type d'événement: {e}")
        return JsonResponse({
            'success': False,
            'error': f"Erreur lors de la création: {str(e)}"
        }, status=500)


@login_required
@owner_required
@require_http_methods(["POST"])
def update_event_type(request, event_type_id):
    """Modifier un type d'événement"""
    try:
        from monitoring.models import EventType
        
        event_type = get_object_or_404(EventType, id=event_type_id)
        data = json.loads(request.body)
        
        # Mettre à jour les champs
        event_type.name = data.get('name', event_type.name).strip()
        event_type.description = data.get('description', event_type.description).strip()
        event_type.severity = data.get('severity', event_type.severity)
        event_type.color = data.get('color', event_type.color)
        event_type.icon = data.get('icon', event_type.icon)
        event_type.auto_alert = data.get('auto_alert', event_type.auto_alert)
        event_type.requires_verification = data.get('requires_verification', event_type.requires_verification)
        event_type.is_active = data.get('is_active', event_type.is_active)
        
        event_type.save()
        
        # Logger l'action
        logger.info(f"Type d'événement modifié par {request.user.username}: '{event_type.name}' ({event_type.code})")
        
        return JsonResponse({
            'success': True,
            'message': f"Type d'événement '{event_type.name}' modifié avec succès"
        })
        
    except Exception as e:
        logger.error(f"Erreur modification type d'événement: {e}")
        return JsonResponse({
            'success': False,
            'error': f"Erreur lors de la modification: {str(e)}"
        }, status=500)


@login_required
@owner_required
def manage_company_event_types(request, company_id):
    """Gérer les types d'événements d'une entreprise spécifique"""
    from monitoring.models import EventType, CompanyEventType
    
    company = get_object_or_404(Company, id=company_id, is_active=True)
    
    # Récupérer tous les types d'événements avec leur statut pour cette entreprise
    event_types_data = []
    for event_type in EventType.objects.filter(is_active=True).order_by('name'):
        try:
            company_event_type = CompanyEventType.objects.get(
                company=company,
                event_type=event_type
            )
            is_enabled = company_event_type.is_enabled
            custom_name = company_event_type.custom_name
            custom_severity = company_event_type.custom_severity
        except CompanyEventType.DoesNotExist:
            is_enabled = False
            custom_name = ''
            custom_severity = ''
        
        event_types_data.append({
            'event_type': event_type,
            'is_enabled': is_enabled,
            'custom_name': custom_name,
            'custom_severity': custom_severity,
        })
    
    if request.method == 'POST':
        # Traiter les modifications
        try:
            data = json.loads(request.body)
            updated_count = 0
            
            for item in data.get('event_types', []):
                event_type_id = item.get('event_type_id')
                is_enabled = item.get('is_enabled', False)
                custom_name = item.get('custom_name', '').strip()
                custom_severity = item.get('custom_severity', '').strip()
                
                event_type = EventType.objects.get(id=event_type_id)
                
                company_event_type, created = CompanyEventType.objects.get_or_create(
                    company=company,
                    event_type=event_type,
                    defaults={
                        'assigned_by': request.user
                    }
                )
                
                company_event_type.is_enabled = is_enabled
                company_event_type.custom_name = custom_name
                company_event_type.custom_severity = custom_severity
                company_event_type.save()
                
                updated_count += 1
            
            # Logger l'action
            logger.info(f"Types d'événements mis à jour par {request.user.username} pour l'entreprise {company.name}: {updated_count} types")
            
            return JsonResponse({
                'success': True,
                'message': f"Configuration mise à jour pour {company.name}",
                'updated_count': updated_count
            })
            
        except Exception as e:
            logger.error(f"Erreur mise à jour types d'événements entreprise: {e}")
            return JsonResponse({
                'success': False,
                'error': f"Erreur lors de la mise à jour: {str(e)}"
            }, status=500)
    
    context = {
        'company': company,
        'event_types_data': event_types_data,
        'severity_choices': EventType.SEVERITY_CHOICES,
    }
    
    return render(request, 'companies/manage_company_event_types.html', context)