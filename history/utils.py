from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
import json


def get_client_ip(request):
    """
    Récupère l'adresse IP du client depuis la requête
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_user_agent(request):
    """
    Récupère le User-Agent depuis la requête
    """
    return request.META.get('HTTP_USER_AGENT', '')[:500]  # Limiter à 500 caractères


def get_model_category(model_class):
    """
    Détermine la catégorie d'un modèle pour l'historisation
    """
    app_label = model_class._meta.app_label
    model_name = model_class._meta.model_name
    
    # Mapping des modèles vers les catégories
    category_mapping = {
        # Utilisateurs et authentification
        'auth.user': 'user',
        'companies.companyuser': 'user',
        'companies.companyinvitation': 'user',
        
        # Entreprises
        'companies.company': 'company',
        'companies.companysettings': 'settings',
        
        # Surveillance
        'monitoring.location': 'location',
        'monitoring.zone': 'zone',
        'monitoring.camera': 'camera',
        'monitoring.detectionevent': 'detection',
        'monitoring.incident': 'incident',
        'monitoring.videorecording': 'recording',
        'monitoring.eventtype': 'settings',
        'monitoring.companyeventtype': 'settings',
        
        # Alertes
        'alerts.alert': 'alert',
        'alerts.alertrule': 'alert',
        'alerts.notificationlog': 'notification',
        'alerts.notificationtemplate': 'notification',
        
        # Analytics
        'analytics.performancemetric': 'report',
        'analytics.heatmapdata': 'report',
    }
    
    model_key = f"{app_label}.{model_name}"
    return category_mapping.get(model_key, 'system')


def get_object_name(instance):
    """
    Récupère un nom lisible pour un objet
    """
    # Essayer différentes méthodes pour obtenir un nom
    if hasattr(instance, 'name'):
        return str(instance.name)
    elif hasattr(instance, 'title'):
        return str(instance.title)
    elif hasattr(instance, 'get_full_name'):
        full_name = instance.get_full_name()
        if full_name:
            return full_name
    elif hasattr(instance, 'username'):
        return str(instance.username)
    elif hasattr(instance, 'email'):
        return str(instance.email)
    
    # Fallback sur la représentation string
    return str(instance)


def get_changed_fields(old_instance, new_instance):
    """
    Compare deux instances d'un modèle et retourne les champs modifiés
    """
    changed_fields = []
    old_values = {}
    new_values = {}
    
    # Obtenir tous les champs du modèle
    fields = new_instance._meta.fields
    
    for field in fields:
        field_name = field.name
        
        # Ignorer certains champs automatiques
        if field_name in ['id', 'created_at', 'updated_at', 'last_login']:
            continue
        
        old_value = getattr(old_instance, field_name, None)
        new_value = getattr(new_instance, field_name, None)
        
        # Comparer les valeurs
        if old_value != new_value:
            changed_fields.append(field_name)
            old_values[field_name] = serialize_field_value(old_value)
            new_values[field_name] = serialize_field_value(new_value)
    
    return changed_fields, old_values, new_values


def serialize_field_value(value):
    """
    Sérialise une valeur de champ pour le stockage JSON
    """
    if value is None:
        return None
    
    # Gérer les types spéciaux
    if hasattr(value, 'isoformat'):  # DateTime, Date, Time
        return value.isoformat()
    elif hasattr(value, '__dict__'):  # Objets complexes
        return str(value)
    else:
        try:
            # Essayer de sérialiser avec le JSONEncoder de Django
            return json.loads(json.dumps(value, cls=DjangoJSONEncoder))
        except (TypeError, ValueError):
            return str(value)


def format_history_description(action, category, object_name, changed_fields=None):
    """
    Formate une description lisible pour une entrée d'historique
    """
    action_labels = {
        'create': 'Création',
        'update': 'Modification',
        'delete': 'Suppression',
        'login': 'Connexion',
        'logout': 'Déconnexion',
        'view': 'Consultation',
        'export': 'Exportation',
        'import': 'Importation',
        'activate': 'Activation',
        'deactivate': 'Désactivation',
    }
    
    category_labels = {
        'user': 'utilisateur',
        'company': 'entreprise',
        'location': 'localisation',
        'zone': 'zone',
        'camera': 'caméra',
        'alert': 'alerte',
        'detection': 'détection',
        'incident': 'incident',
        'recording': 'enregistrement',
        'settings': 'paramètres',
        'system': 'système',
        'auth': 'authentification',
        'report': 'rapport',
        'notification': 'notification',
    }
    
    action_label = action_labels.get(action, action)
    category_label = category_labels.get(category, category)
    
    description = f"{action_label} de {category_label} '{object_name}'"
    
    if changed_fields and action == 'update':
        if len(changed_fields) == 1:
            description += f" (champ modifié: {changed_fields[0]})"
        else:
            description += f" ({len(changed_fields)} champs modifiés)"
    
    return description


def get_history_stats(company=None, date_from=None, date_to=None):
    """
    Calcule des statistiques sur l'historique
    """
    from django.db import models
    from .models import HistoryEntry
    
    queryset = HistoryEntry.objects.all()
    
    if company:
        queryset = queryset.filter(company=company)
    
    if date_from:
        queryset = queryset.filter(timestamp__gte=date_from)
    
    if date_to:
        queryset = queryset.filter(timestamp__lte=date_to)
    
    stats = {
        'total_entries': queryset.count(),
        'by_action': {},
        'by_category': {},
        'by_user': {},
        'by_day': {},
    }
    
    # Statistiques par action
    for action, _ in HistoryEntry.ACTION_CHOICES:
        count = queryset.filter(action=action).count()
        if count > 0:
            stats['by_action'][action] = count
    
    # Statistiques par catégorie
    for category, _ in HistoryEntry.CATEGORY_CHOICES:
        count = queryset.filter(category=category).count()
        if count > 0:
            stats['by_category'][category] = count
    
    # Top 10 utilisateurs les plus actifs
    user_stats = queryset.values('user__username', 'user__first_name', 'user__last_name')\
                         .annotate(count=models.Count('id'))\
                         .order_by('-count')[:10]
    
    for user_stat in user_stats:
        username = user_stat['user__username']
        full_name = f"{user_stat['user__first_name']} {user_stat['user__last_name']}".strip()
        display_name = full_name if full_name else username
        stats['by_user'][display_name] = user_stat['count']
    
    return stats


def export_history_to_csv(queryset, filename):
    """
    Exporte un queryset d'historique vers un fichier CSV
    """
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    writer = csv.writer(response)
    
    # En-têtes
    writer.writerow([
        'Date/Heure',
        'Utilisateur',
        'Action',
        'Catégorie',
        'Objet',
        'Description',
        'Champs modifiés',
        'Adresse IP',
        'Entreprise',
        'Localisation',
    ])
    
    # Données
    for entry in queryset:
        writer.writerow([
            entry.timestamp.strftime('%d/%m/%Y %H:%M:%S'),
            entry.user.get_full_name() or entry.user.username if entry.user else 'Système',
            entry.get_action_display(),
            entry.get_category_display(),
            entry.object_name,
            entry.description,
            entry.get_changed_fields_display(),
            entry.ip_address or '',
            entry.company.name if entry.company else '',
            entry.location.name if entry.location else '',
        ])
    
    return response
