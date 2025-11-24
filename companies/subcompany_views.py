from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib.auth.models import User
from django.db import transaction

from .models import Company, CompanyUser, SubCompany, SubCompanyUser
from .forms import SubCompanyForm, SubCompanyUserForm


@login_required
def subcompany_management_wizard(request, company_id):
    """
    Assistant de création d'entreprise avec sous-entreprises et managers
    """
    # Vérifier les permissions (owner uniquement)
    if not hasattr(request.user, 'company_profile') or not request.user.company_profile.is_owner:
        messages.error(request, "Vous n'avez pas les permissions pour accéder à cette page.")
        return redirect('dashboard')
    
    company = get_object_or_404(Company, id=company_id)
    
    # Étapes du wizard
    step = request.GET.get('step', '1')
    
    context = {
        'company': company,
        'step': step,
        'steps': {
            '1': 'Informations de l\'entreprise',
            '2': 'Création des sous-entreprises',
            '3': 'Création des managers',
            '4': 'Assignation des managers',
            '5': 'Confirmation'
        }
    }
    
    if step == '1':
        return render(request, 'companies/subcompany_wizard/step1_company.html', context)
    elif step == '2':
        return subcompany_wizard_step2(request, company, context)
    elif step == '3':
        return subcompany_wizard_step3(request, company, context)
    elif step == '4':
        return subcompany_wizard_step4(request, company, context)
    elif step == '5':
        return subcompany_wizard_step5(request, company, context)
    else:
        return redirect(f'/companies/subcompany-wizard/{company_id}/?step=1')


def subcompany_wizard_step2(request, company, context):
    """Étape 2: Création des sous-entreprises"""
    
    if request.method == 'POST':
        subcompany_names = request.POST.getlist('subcompany_names[]')
        subcompany_descriptions = request.POST.getlist('subcompany_descriptions[]')
        
        created_subcompanies = []
        
        try:
            with transaction.atomic():
                for i, name in enumerate(subcompany_names):
                    if name.strip():
                        description = subcompany_descriptions[i] if i < len(subcompany_descriptions) else ""
                        
                        subcompany = SubCompany.objects.create(
                            parent_company=company,
                            name=name.strip(),
                            description=description.strip(),
                            created_by=request.user,
                            max_users=20,
                            max_cameras=10,
                            max_locations=3
                        )
                        created_subcompanies.append(subcompany)
                
                messages.success(request, f"{len(created_subcompanies)} sous-entreprise(s) créée(s) avec succès.")
                return redirect(f'/companies/subcompany-wizard/{company.id}/?step=3')
                
        except Exception as e:
            messages.error(request, f"Erreur lors de la création des sous-entreprises: {str(e)}")
    
    # Récupérer les sous-entreprises existantes
    context['existing_subcompanies'] = company.subcompanies.all()
    
    return render(request, 'companies/subcompany_wizard/step2_subcompanies.html', context)


def subcompany_wizard_step3(request, company, context):
    """Étape 3: Création des managers"""
    
    if request.method == 'POST':
        usernames = request.POST.getlist('usernames[]')
        emails = request.POST.getlist('emails[]')
        first_names = request.POST.getlist('first_names[]')
        last_names = request.POST.getlist('last_names[]')
        passwords = request.POST.getlist('passwords[]')
        
        created_managers = []
        
        try:
            with transaction.atomic():
                for i, username in enumerate(usernames):
                    if username.strip():
                        # Vérifier si l'utilisateur existe déjà
                        if User.objects.filter(username=username).exists():
                            messages.warning(request, f"L'utilisateur {username} existe déjà.")
                            continue
                        
                        # Créer l'utilisateur
                        user = User.objects.create_user(
                            username=username.strip(),
                            email=emails[i].strip() if i < len(emails) else "",
                            first_name=first_names[i].strip() if i < len(first_names) else "",
                            last_name=last_names[i].strip() if i < len(last_names) else "",
                            password=passwords[i] if i < len(passwords) else "temp123456"
                        )
                        
                        # Créer le profil d'entreprise
                        company_user = CompanyUser.objects.create(
                            user=user,
                            company=company,
                            role='manager',
                            can_manage_users=True,
                            can_manage_cameras=True,
                            can_manage_alerts=True,
                            can_view_reports=True
                        )
                        
                        created_managers.append(company_user)
                
                messages.success(request, f"{len(created_managers)} manager(s) créé(s) avec succès.")
                return redirect(f'/companies/subcompany-wizard/{company.id}/?step=4')
                
        except Exception as e:
            messages.error(request, f"Erreur lors de la création des managers: {str(e)}")
    
    # Récupérer les managers existants
    context['existing_managers'] = company.company_users.filter(role='manager')
    
    return render(request, 'companies/subcompany_wizard/step3_managers.html', context)


def subcompany_wizard_step4(request, company, context):
    """Étape 4 : Assignation des managers aux sous-entreprises"""

    managers = company.company_users.filter(role='manager')
    subcompanies = company.subcompanies.all()

    if request.method == 'POST':

        # DEBUG : Voir ce qui est envoyé par le formulaire
        print("=== RAW POST DATA ===")
        for key, value in request.POST.lists():
            print(key, "=>", value)
        print("=====================")

        # Bouton passer étape
        if "skip" in request.POST:
            return redirect(f'/companies/subcompany-wizard/{company.id}/?step=5')

        try:
            with transaction.atomic():

                for manager in managers:
                    # Récupération des IDs envoyées par le template
                    selected_subcompanies = request.POST.getlist(f"manager_{manager.id}_subcompanies")

                    # Supprime les anciennes assignations
                    SubCompanyUser.objects.filter(company_user=manager).delete()

                    # Ajout des nouvelles assignations
                    for sub_id in selected_subcompanies:
                        sub = SubCompany.objects.get(id=sub_id, parent_company=company)

                        SubCompanyUser.objects.create(
                            company_user=manager,
                            subcompany=sub,
                            can_manage_monitoring=True,
                            can_manage_alert_rules=True,
                            can_manage_alerts=True,
                            can_view_reports=True,

                        )

                    # Définir sous-entreprise courante si vide
                    if selected_subcompanies and not manager.current_subcompany:
                        manager.current_subcompany = SubCompany.objects.get(id=selected_subcompanies[0])
                        manager.save()

            messages.success(request, "Assignations enregistrées avec succès.")
            return redirect(f'/companies/subcompany-wizard/{company.id}/?step=5')

        except Exception as e:
            messages.error(request, f"Erreur lors de l'assignation : {e}")

    # CONTEXTE
    context['managers'] = managers
    context['subcompanies'] = subcompanies
    context['existing_assignments'] = SubCompanyUser.objects.filter(
        subcompany__parent_company=company
    )

    return render(request, 'companies/subcompany_wizard/step4_assignments.html', context)


def subcompany_wizard_step5(request, company, context):
    """Étape 5: Confirmation et résumé"""
    
    # Statistiques finales
    context.update({
        'subcompanies': company.subcompanies.all(),
        'managers': company.company_users.filter(role='manager'),
        'assignments': SubCompanyUser.objects.filter(
            subcompany__parent_company=company
        ).select_related('company_user', 'subcompany'),
        'total_users': company.company_users.count(),
        'total_locations': company.locations.count(),
    })
    
    return render(request, 'companies/subcompany_wizard/step5_confirmation.html', context)


@login_required
def subcompany_list(request, company_id):
    """Liste des sous-entreprises d'une entreprise"""
    
    # Vérifier les permissions
    if not hasattr(request.user, 'company_profile'):
        messages.error(request, "Vous devez être associé à une entreprise.")
        return redirect('dashboard')
    
    company_user = request.user.company_profile
    
    if company_user.is_owner:
        company = get_object_or_404(Company, id=company_id)
    elif company_user.is_manager:
        company = company_user.company
        if company.id != int(company_id):
            messages.error(request, "Vous ne pouvez voir que les sous-entreprises de votre entreprise.")
            return redirect('dashboard')
    else:
        messages.error(request, "Vous n'avez pas les permissions pour voir cette page.")
        return redirect('dashboard')
    
    subcompanies = company.subcompanies.all().annotate(
        user_count=Count('subcompany_users'),
        location_count=Count('locations')
    )
    
    context = {
        'company': company,
        'subcompanies': subcompanies,
        'can_create': company_user.is_owner or company_user.is_manager,
    }
    
    return render(request, 'companies/subcompany_list.html', context)


@login_required
def subcompany_create(request, company_id):
    """Création d'une nouvelle sous-entreprise"""
    
    # Vérifier les permissions
    if not hasattr(request.user, 'company_profile'):
        messages.error(request, "Vous devez être associé à une entreprise.")
        return redirect('dashboard')
    
    company_user = request.user.company_profile
    
    if company_user.is_owner:
        company = get_object_or_404(Company, id=company_id)
    elif company_user.is_manager:
        company = company_user.company
        if company.id != int(company_id):
            messages.error(request, "Vous ne pouvez créer des sous-entreprises que dans votre entreprise.")
            return redirect('dashboard')
    else:
        messages.error(request, "Vous n'avez pas les permissions pour créer une sous-entreprise.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = SubCompanyForm(request.POST)
        if form.is_valid():
            subcompany = form.save(commit=False)
            subcompany.parent_company = company
            subcompany.created_by = request.user
            subcompany.save()
            
            messages.success(request, f"Sous-entreprise '{subcompany.name}' créée avec succès.")
            return redirect('companies:subcompany_list', company_id=company.id)
    else:
        form = SubCompanyForm()
    
    context = {
        'company': company,
        'form': form,
    }
    
    return render(request, 'companies/subcompany_form.html', context)


@login_required
def subcompany_selector(request):
    """Sélecteur de sous-entreprise pour les managers"""
    
    if not hasattr(request.user, 'company_profile'):
        return JsonResponse({'error': 'Utilisateur non associé à une entreprise'}, status=403)
    
    company_user = request.user.company_profile
    
    if request.method == 'POST':
        subcompany_id = request.POST.get('subcompany_id')
        
        try:
            subcompany = SubCompany.objects.get(id=subcompany_id)
            
            if company_user.can_access_subcompany(subcompany):
                company_user.set_current_subcompany(subcompany)
                return JsonResponse({
                    'success': True,
                    'message': f'Sous-entreprise changée vers {subcompany.name}',
                    'subcompany': {
                        'id': subcompany.id,
                        'name': subcompany.name,
                        'reference': subcompany.reference
                    }
                })
            else:
                return JsonResponse({'error': 'Accès non autorisé à cette sous-entreprise'}, status=403)
                
        except SubCompany.DoesNotExist:
            return JsonResponse({'error': 'Sous-entreprise non trouvée'}, status=404)
    
    # GET: Retourner les sous-entreprises accessibles
    accessible_subcompanies = company_user.get_accessible_subcompanies()
    
    subcompanies_data = []
    for subcompany in accessible_subcompanies:
        subcompanies_data.append({
            'id': subcompany.id,
            'name': subcompany.name,
            'reference': subcompany.reference,
            'full_name': subcompany.full_name,
            'is_current': subcompany.id == (company_user.current_subcompany.id if company_user.current_subcompany else None)
        })
    
    return JsonResponse({
        'subcompanies': subcompanies_data,
        'current_subcompany': {
            'id': company_user.current_subcompany.id if company_user.current_subcompany else None,
            'name': company_user.current_subcompany.name if company_user.current_subcompany else None,
        } if company_user.current_subcompany else None
    })
