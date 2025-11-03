from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from datetime import datetime, timedelta
import json

from .models import HistoryEntry, HistoryFilter, HistoryExport, HistorySettings
from .utils import get_history_stats, export_history_to_csv
from companies.models import CompanyUser


@login_required
def history_dashboard(request):
    """
    Tableau de bord principal de l'historique
    """
    # Vérifier les permissions
    if not hasattr(request.user, 'company_profile'):
        messages.error(request, "Vous devez être associé à une entreprise pour accéder à l'historique.")
        return redirect('dashboard')
    
    company_user = request.user.company_profile
    if not company_user.is_manager and not company_user.is_owner:
        messages.error(request, "Vous n'avez pas les permissions pour accéder à l'historique.")
        return redirect('dashboard')
    
    company = company_user.company
    
    # Statistiques des 7 derniers jours
    week_ago = timezone.now() - timedelta(days=7)
    stats = get_history_stats(company=company, date_from=week_ago)
    
    # Dernières entrées
    recent_entries = HistoryEntry.objects.filter(company=company)\
                                        .select_related('user', 'company', 'location')\
                                        .order_by('-timestamp')[:10]
    
    # Activité par jour (7 derniers jours)
    daily_activity = []
    for i in range(7):
        date = timezone.now().date() - timedelta(days=i)
        count = HistoryEntry.objects.filter(
            company=company,
            timestamp__date=date
        ).count()
        daily_activity.append({
            'date': date.strftime('%d/%m'),
            'count': count
        })
    daily_activity.reverse()
    
    context = {
        'stats': stats,
        'recent_entries': recent_entries,
        'daily_activity': daily_activity,
        'company': company,
    }
    
    return render(request, 'history/dashboard_simple.html', context)


@login_required
def history_list(request):
    """
    Liste complète de l'historique avec filtres
    """
    # Vérifier les permissions
    if not hasattr(request.user, 'company_profile'):
        messages.error(request, "Vous devez être associé à une entreprise pour accéder à l'historique.")
        return redirect('dashboard')
    
    company_user = request.user.company_profile
    if not company_user.is_manager and not company_user.is_owner:
        messages.error(request, "Vous n'avez pas les permissions pour accéder à l'historique.")
        return redirect('dashboard')
    
    company = company_user.company
    
    # Base queryset - ISOLATION PAR ENTREPRISE
    queryset = HistoryEntry.objects.filter(company=company)\
                                  .select_related('user', 'company', 'location', 'content_type')\
                                  .order_by('-timestamp')
    
    # Sécurité supplémentaire : s'assurer qu'on ne voit que les données de notre entreprise
    queryset = queryset.exclude(company__isnull=True)
    
    # Filtres
    filters = {}
    
    # Filtre par utilisateur
    user_filter = request.GET.get('user')
    if user_filter:
        queryset = queryset.filter(user_id=user_filter)
        filters['user'] = user_filter
    
    # Filtre par action
    action_filter = request.GET.get('action')
    if action_filter:
        queryset = queryset.filter(action=action_filter)
        filters['action'] = action_filter
    
    # Filtre par catégorie
    category_filter = request.GET.get('category')
    if category_filter:
        queryset = queryset.filter(category=category_filter)
        filters['category'] = category_filter
    
    # Filtre par date
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            queryset = queryset.filter(timestamp__gte=date_from_obj)
            filters['date_from'] = date_from
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            # Inclure toute la journée
            date_to_obj = date_to_obj.replace(hour=23, minute=59, second=59)
            queryset = queryset.filter(timestamp__lte=date_to_obj)
            filters['date_to'] = date_to
        except ValueError:
            pass
    
    # Filtre par localisation
    location_filter = request.GET.get('location')
    if location_filter:
        queryset = queryset.filter(location_id=location_filter)
        filters['location'] = location_filter
    
    # Recherche textuelle
    search = request.GET.get('search')
    if search:
        queryset = queryset.filter(
            Q(object_name__icontains=search) |
            Q(description__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search)
        )
        filters['search'] = search
    
    # Pagination
    paginator = Paginator(queryset, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Données pour les filtres - ISOLATION PAR ENTREPRISE
    users = company.company_users.select_related('user').all()
    locations = company.locations.all()
    
    # S'assurer que les utilisateurs dans les filtres appartiennent à l'entreprise
    user_filter_queryset = queryset.filter(user__isnull=False).values_list('user_id', flat=True).distinct()
    users = users.filter(user_id__in=user_filter_queryset)
    
    context = {
        'page_obj': page_obj,
        'filters': filters,
        'users': users,
        'locations': locations,
        'action_choices': HistoryEntry.ACTION_CHOICES,
        'category_choices': HistoryEntry.CATEGORY_CHOICES,
        'company': company,
        'total_count': queryset.count(),
    }
    
    return render(request, 'history/list_simple.html', context)


@login_required
def history_detail(request, entry_id):
    """
    Détail d'une entrée d'historique
    """
    # Vérifier les permissions
    if not hasattr(request.user, 'company_profile'):
        messages.error(request, "Vous devez être associé à une entreprise.")
        return redirect('dashboard')
    
    company_user = request.user.company_profile
    if not company_user.is_manager and not company_user.is_owner:
        messages.error(request, "Vous n'avez pas les permissions pour accéder à l'historique.")
        return redirect('dashboard')
    
    company = company_user.company
    
    # ISOLATION PAR ENTREPRISE : s'assurer que l'entrée appartient à l'entreprise du manager
    entry = get_object_or_404(HistoryEntry, id=entry_id, company=company)
    
    # Sécurité supplémentaire
    if entry.company != company:
        messages.error(request, "Vous n'avez pas accès à cette entrée d'historique.")
        return redirect('history:dashboard')
    
    context = {
        'entry': entry,
        'company': company,
    }
    
    return render(request, 'history/detail.html', context)


@login_required
@require_http_methods(["POST"])
def export_history(request):
    """
    Exporte l'historique selon les critères spécifiés
    """
    # Vérifier les permissions
    if not hasattr(request.user, 'company_profile'):
        return JsonResponse({'error': 'Permissions insuffisantes'}, status=403)
    
    company_user = request.user.company_profile
    if not company_user.is_manager and not company_user.is_owner:
        return JsonResponse({'error': 'Permissions insuffisantes'}, status=403)
    
    company = company_user.company
    
    try:
        data = json.loads(request.body)
        
        # Construire le queryset avec les filtres
        queryset = HistoryEntry.objects.filter(company=company)\
                                      .select_related('user', 'company', 'location')\
                                      .order_by('-timestamp')
        
        # Appliquer les filtres
        if data.get('user'):
            queryset = queryset.filter(user_id=data['user'])
        
        if data.get('action'):
            queryset = queryset.filter(action=data['action'])
        
        if data.get('category'):
            queryset = queryset.filter(category=data['category'])
        
        if data.get('date_from'):
            date_from = datetime.strptime(data['date_from'], '%Y-%m-%d')
            queryset = queryset.filter(timestamp__gte=date_from)
        
        if data.get('date_to'):
            date_to = datetime.strptime(data['date_to'], '%Y-%m-%d')
            date_to = date_to.replace(hour=23, minute=59, second=59)
            queryset = queryset.filter(timestamp__lte=date_to)
        
        if data.get('location'):
            queryset = queryset.filter(location_id=data['location'])
        
        # Générer le nom du fichier
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        filename = f"historique_{company.reference}_{timestamp}.csv"
        
        # Exporter en CSV
        return export_history_to_csv(queryset, filename)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def history_settings(request):
    """
    Paramètres de l'historisation - Version simplifiée (catégories uniquement)
    """
    # Vérifier les permissions
    if not hasattr(request.user, 'company_profile'):
        messages.error(request, "Vous devez être associé à une entreprise.")
        return redirect('dashboard')
    
    company_user = request.user.company_profile
    if not company_user.is_manager and not company_user.is_owner:
        messages.error(request, "Vous n'avez pas les permissions pour modifier les paramètres.")
        return redirect('dashboard')
    
    company = company_user.company
    
    # Récupérer ou créer les paramètres
    settings, created = HistorySettings.objects.get_or_create(
        company=company,
        defaults={
            'updated_by': request.user,
            'enabled_categories': ['user', 'company', 'location', 'zone', 'camera', 'alert']
        }
    )
    
    if request.method == 'POST':
        try:
            # Catégories activées (seul paramètre modifiable)
            enabled_categories = request.POST.getlist('enabled_categories')
            
            if not enabled_categories:
                messages.error(request, "Vous devez sélectionner au moins une catégorie à historiser.")
            else:
                settings.enabled_categories = enabled_categories
                settings.updated_by = request.user
                settings.save()
                
                messages.success(request, f"Paramètres mis à jour avec succès. {len(enabled_categories)} catégorie(s) sélectionnée(s).")
                return redirect('history:settings')
            
        except Exception as e:
            messages.error(request, f"Erreur lors de la mise à jour : {str(e)}")
    
    context = {
        'settings': settings,
        'company': company,
        'category_choices': HistoryEntry.CATEGORY_CHOICES,
    }
    
    return render(request, 'history/settings_simple.html', context)


@login_required
def history_stats_api(request):
    """
    API pour récupérer les statistiques d'historique
    """
    # Vérifier les permissions
    if not hasattr(request.user, 'company_profile'):
        return JsonResponse({'error': 'Permissions insuffisantes'}, status=403)
    
    company_user = request.user.company_profile
    if not company_user.is_manager and not company_user.is_owner:
        return JsonResponse({'error': 'Permissions insuffisantes'}, status=403)
    
    company = company_user.company
    
    # Paramètres de période
    days = int(request.GET.get('days', 30))
    date_from = timezone.now() - timedelta(days=days)
    
    stats = get_history_stats(company=company, date_from=date_from)
    
    return JsonResponse(stats)