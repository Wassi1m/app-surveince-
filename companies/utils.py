"""
Utilitaires pour la gestion des entreprises et sous-entreprises
"""
from django.db.models import Q
from .models import CompanyUser, SubCompany


def get_user_data_filters(request):
    """
    Retourne les filtres appropriés selon le rôle de l'utilisateur et sa sous-entreprise courante
    """
    filters = {
        'camera_filter': {},
        'alert_filter': {},
        'detection_filter': {},
        'incident_filter': {},
        'zone_filter': {},
        'location_filter': {},
        'user_filter': {},
        'history_filter': {},
    }
    
    if not request.user.is_authenticated:
        return filters
    
    # Vérifier si l'utilisateur a un profil d'entreprise
    if not hasattr(request.user, 'company_profile'):
        return filters
    
    company_user = request.user.company_profile
    
    # Owner : accès à tout
    if company_user.is_owner:
        return filters
    
    # Manager ou Employee : filtrer par sous-entreprise courante
    if hasattr(request, 'current_subcompany') and request.current_subcompany:
        subcompany = request.current_subcompany
        
        # Filtres pour les différents modèles
        filters['camera_filter'] = {'location__subcompany': subcompany}
        filters['alert_filter'] = {'subcompany': subcompany}
        filters['detection_filter'] = {'camera__location__subcompany': subcompany}
        filters['incident_filter'] = {'location__subcompany': subcompany}
        filters['zone_filter'] = {'location__subcompany': subcompany}
        filters['location_filter'] = {'subcompany': subcompany}
        filters['history_filter'] = {'subcompany': subcompany}
        
        # Filtrer les utilisateurs par sous-entreprise
        if company_user.is_manager:
            # Les managers voient tous les utilisateurs de leur entreprise
            filters['user_filter'] = {'company': subcompany.parent_company}
        else:
            # Les employés ne voient que leur propre profil
            filters['user_filter'] = {'id': company_user.id}
    
    elif hasattr(request, 'current_company') and request.current_company:
        # Fallback : filtrer par entreprise si pas de sous-entreprise
        company = request.current_company
        
        filters['camera_filter'] = {'location__company': company}
        filters['alert_filter'] = {'company': company}
        filters['detection_filter'] = {'camera__location__company': company}
        filters['incident_filter'] = {'location__company': company}
        filters['zone_filter'] = {'location__company': company}
        filters['location_filter'] = {'company': company}
        filters['history_filter'] = {'company': company}
        
        if company_user.is_manager:
            filters['user_filter'] = {'company': company}
        else:
            filters['user_filter'] = {'id': company_user.id}
    
    return filters


def get_accessible_locations(request):
    """
    Retourne les localisations accessibles à l'utilisateur
    """
    if not request.user.is_authenticated or not hasattr(request.user, 'company_profile'):
        return []
    
    company_user = request.user.company_profile
    
    # Owner : toutes les localisations
    if company_user.is_owner:
        from monitoring.models import Location
        return Location.objects.all()
    
    # Manager : toutes les localisations de son entreprise
    if company_user.is_manager and company_user.company:
        return company_user.company.locations.all()
    
    # Employee : localisations des sous-entreprises accessibles
    accessible_subcompanies = company_user.get_accessible_subcompanies()
    if accessible_subcompanies.exists():
        from monitoring.models import Location
        return Location.objects.filter(subcompany__in=accessible_subcompanies)
    
    return []


def get_accessible_cameras(request):
    """
    Retourne les caméras accessibles à l'utilisateur
    """
    locations = get_accessible_locations(request)
    if not locations:
        return []
    
    from monitoring.models import Camera
    return Camera.objects.filter(location__in=locations)


def get_accessible_zones(request):
    """
    Retourne les zones accessibles à l'utilisateur
    """
    locations = get_accessible_locations(request)
    if not locations:
        return []
    
    from monitoring.models import Zone
    return Zone.objects.filter(location__in=locations)


def get_accessible_users(request):
    """
    Retourne les utilisateurs accessibles selon le rôle
    """
    if not request.user.is_authenticated or not hasattr(request.user, 'company_profile'):
        return CompanyUser.objects.none()
    
    company_user = request.user.company_profile
    
    # Owner : tous les utilisateurs
    if company_user.is_owner:
        return CompanyUser.objects.all()
    
    # Manager : utilisateurs de son entreprise
    if company_user.is_manager and company_user.company:
        return CompanyUser.objects.filter(company=company_user.company)
    
    # Employee : seulement lui-même
    return CompanyUser.objects.filter(id=company_user.id)


def can_manage_subcompany(user, subcompany):
    """
    Vérifie si un utilisateur peut gérer une sous-entreprise
    """
    if not hasattr(user, 'company_profile'):
        return False
    
    company_user = user.company_profile
    
    # Owner : peut tout gérer
    if company_user.is_owner:
        return True
    
    # Manager : peut gérer les sous-entreprises de son entreprise
    if company_user.is_manager:
        return subcompany.parent_company == company_user.company
    
    return False


def can_access_subcompany_data(user, subcompany):
    """
    Vérifie si un utilisateur peut accéder aux données d'une sous-entreprise
    """
    if not hasattr(user, 'company_profile'):
        return False
    
    company_user = user.company_profile
    
    # Owner : accès à tout
    if company_user.is_owner:
        return True
    
    # Vérifier l'accès via les assignations
    return company_user.can_access_subcompany(subcompany)


def get_user_permissions_for_subcompany(user, subcompany):
    """
    Retourne les permissions d'un utilisateur pour une sous-entreprise spécifique
    """
    if not hasattr(user, 'company_profile'):
        return {}
    
    company_user = user.company_profile
    
    # Owner : toutes les permissions
    if company_user.is_owner:
        return {
            'can_manage_monitoring': True,
            'can_manage_alerts': True,
            'can_manage_alert_rules': True,
            'can_view_reports': True,
        }
    
    # Manager : toutes les permissions automatiquement sur son entreprise
    if company_user.is_manager and subcompany.parent_company == company_user.company:
        return {
            'can_manage_monitoring': True,
            'can_manage_alerts': True,
            'can_manage_alert_rules': True,
            'can_view_reports': True,
        }
    
    # Employé : récupérer les permissions via l'assignation
    try:
        from .models import SubCompanyUser
        assignment = SubCompanyUser.objects.get(
            company_user=company_user,
            subcompany=subcompany,
            is_active=True
        )
        return {
            'can_manage_monitoring': assignment.can_manage_monitoring,
            'can_manage_alerts': assignment.can_manage_alerts,
            'can_manage_alert_rules': assignment.can_manage_alert_rules,
            'can_view_reports': assignment.can_view_reports,
        }
    except:
        return {
            'can_manage_monitoring': False,
            'can_manage_alerts': False,
            'can_manage_alert_rules': False,
            'can_view_reports': False,
        }


def ensure_user_has_subcompany_access(request):
    """
    S'assure que l'utilisateur a une sous-entreprise courante définie
    """
    if not request.user.is_authenticated or not hasattr(request.user, 'company_profile'):
        return False
    
    company_user = request.user.company_profile
    
    # Owner : pas besoin de sous-entreprise spécifique
    if company_user.is_owner:
        return True
    
    # Vérifier si une sous-entreprise courante est définie
    if not company_user.current_subcompany:
        # Essayer de définir la première sous-entreprise accessible
        accessible = company_user.get_accessible_subcompanies()
        if accessible.exists():
            company_user.current_subcompany = accessible.first()
            company_user.save()
            return True
        return False
    
    # Vérifier que la sous-entreprise courante est toujours accessible
    if not company_user.can_access_subcompany(company_user.current_subcompany):
        # Redéfinir vers une sous-entreprise accessible
        accessible = company_user.get_accessible_subcompanies()
        if accessible.exists():
            company_user.current_subcompany = accessible.first()
            company_user.save()
            return True
        else:
            company_user.current_subcompany = None
            company_user.save()
            return False
    
    return True
