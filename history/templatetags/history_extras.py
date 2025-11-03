from django import template
import json
import pprint

register = template.Library()


@register.filter
def lookup(dictionary, key):
    """
    Filtre pour accéder à une valeur dans un dictionnaire
    Usage: {{ dict|lookup:key }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key, '')
    return ''


@register.filter
def pprint(value):
    """
    Filtre pour formater joliment les données JSON/Python
    Usage: {{ data|pprint }}
    """
    try:
        if isinstance(value, str):
            # Essayer de parser comme JSON
            try:
                parsed = json.loads(value)
                return json.dumps(parsed, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                return value
        else:
            # Utiliser pprint pour les autres types
            return pprint.pformat(value, indent=2, width=80)
    except Exception:
        return str(value)


@register.filter
def pluralize_fr(value, forms=""):
    """
    Filtre de pluralisation en français
    Usage: {{ count|pluralize_fr:"singulier,pluriel" }}
    """
    try:
        count = int(value)
    except (ValueError, TypeError):
        return ""
    
    if not forms:
        return "s" if count > 1 else ""
    
    if "," in forms:
        singular, plural = forms.split(",", 1)
        return plural if count > 1 else singular
    else:
        return forms if count > 1 else ""


@register.simple_tag
def history_badge_class(action):
    """
    Tag pour obtenir la classe CSS d'un badge d'action
    Usage: {% history_badge_class entry.action %}
    """
    classes = {
        'create': 'bg-success',
        'update': 'bg-warning',
        'delete': 'bg-danger',
        'login': 'bg-info',
        'logout': 'bg-secondary',
        'view': 'bg-light text-dark',
        'export': 'bg-primary',
        'import': 'bg-primary',
        'activate': 'bg-success',
        'deactivate': 'bg-secondary',
        'assign': 'bg-info',
        'unassign': 'bg-warning',
    }
    return classes.get(action, 'bg-secondary')


@register.simple_tag
def history_icon(action):
    """
    Tag pour obtenir l'icône d'une action
    Usage: {% history_icon entry.action %}
    """
    icons = {
        'create': 'fas fa-plus',
        'update': 'fas fa-edit',
        'delete': 'fas fa-trash',
        'login': 'fas fa-sign-in-alt',
        'logout': 'fas fa-sign-out-alt',
        'view': 'fas fa-eye',
        'export': 'fas fa-download',
        'import': 'fas fa-upload',
        'activate': 'fas fa-toggle-on',
        'deactivate': 'fas fa-toggle-off',
        'assign': 'fas fa-user-plus',
        'unassign': 'fas fa-user-minus',
    }
    return icons.get(action, 'fas fa-question')


@register.inclusion_tag('history/widgets/action_badge.html')
def action_badge(action, size='sm'):
    """
    Tag d'inclusion pour afficher un badge d'action
    Usage: {% action_badge entry.action %}
    """
    return {
        'action': action,
        'size': size,
        'badge_class': history_badge_class(action),
        'icon': history_icon(action),
    }


@register.inclusion_tag('history/widgets/category_badge.html')
def category_badge(category, size='sm'):
    """
    Tag d'inclusion pour afficher un badge de catégorie
    Usage: {% category_badge entry.category %}
    """
    return {
        'category': category,
        'size': size,
    }


@register.filter
def format_file_size(bytes_value):
    """
    Formate une taille de fichier en bytes vers une unité lisible
    Usage: {{ file_size|format_file_size }}
    """
    try:
        bytes_value = int(bytes_value)
    except (ValueError, TypeError):
        return "0 B"
    
    if bytes_value == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size = float(bytes_value)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.1f} {units[unit_index]}"


@register.filter
def truncate_ip(ip_address):
    """
    Tronque une adresse IP pour l'affichage
    Usage: {{ ip|truncate_ip }}
    """
    if not ip_address:
        return ""
    
    # Pour IPv4, afficher seulement les 3 premiers octets
    if '.' in ip_address and ':' not in ip_address:
        parts = ip_address.split('.')
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.{parts[2]}.***"
    
    # Pour IPv6 ou autres, tronquer à 15 caractères
    if len(ip_address) > 15:
        return ip_address[:12] + "..."
    
    return ip_address
