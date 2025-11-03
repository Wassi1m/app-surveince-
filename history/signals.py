from django.db.models.signals import post_save, post_delete, pre_save
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.utils import timezone
import threading
import json

from .models import HistoryEntry, HistorySettings
from .utils import get_client_ip, get_user_agent, get_model_category, get_object_name, get_changed_fields


# Thread local storage pour stocker les informations de la requête
_thread_locals = threading.local()


def set_current_request(request):
    """Stocke la requête courante dans le thread local"""
    _thread_locals.request = request


def get_current_request():
    """Récupère la requête courante depuis le thread local"""
    return getattr(_thread_locals, 'request', None)


def set_current_user(user):
    """Stocke l'utilisateur courant dans le thread local"""
    _thread_locals.user = user


def get_current_user():
    """Récupère l'utilisateur courant depuis le thread local"""
    return getattr(_thread_locals, 'user', None)


def should_track_model(model_class, company=None):
    """
    Détermine si un modèle doit être tracké selon la configuration
    """
    # Éviter de traquer les modèles d'historique eux-mêmes
    if model_class._meta.app_label == 'history':
        return False
    
    # Éviter de traquer certains modèles système
    excluded_models = [
        'contenttypes.contenttype',
        'auth.permission',
        'sessions.session',
        'admin.logentry',
    ]
    
    model_name = f"{model_class._meta.app_label}.{model_class._meta.model_name}"
    if model_name in excluded_models:
        return False
    
    # Vérifier les paramètres de l'entreprise si disponible
    if company:
        try:
            settings = HistorySettings.objects.get(company=company)
            category = get_model_category(model_class)
            return category in settings.enabled_categories
        except HistorySettings.DoesNotExist:
            pass
    
    return True


def create_history_entry(action, instance, user=None, old_values=None, new_values=None, changed_fields=None):
    """
    Crée une entrée d'historique
    """
    request = get_current_request()
    if not user:
        user = get_current_user()
    
    # Déterminer l'entreprise associée
    company = None
    location = None
    
    # Essayer de récupérer l'entreprise depuis l'objet
    if hasattr(instance, 'company'):
        company = instance.company
    elif hasattr(instance, 'location') and hasattr(instance.location, 'company'):
        company = instance.location.company
        location = instance.location
    elif hasattr(instance, 'camera') and hasattr(instance.camera, 'location'):
        company = instance.camera.location.company
        location = instance.camera.location
    elif user and hasattr(user, 'company_profile'):
        company = user.company_profile.company
    
    # Vérifier si on doit traquer ce modèle
    if not should_track_model(instance.__class__, company):
        return
    
    # Récupérer les informations de la requête
    ip_address = None
    user_agent = ""
    session_key = ""
    
    if request:
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)
        if hasattr(request, 'session'):
            session_key = request.session.session_key or ""
    
    # Créer l'entrée d'historique
    try:
        HistoryEntry.objects.create(
            user=user,
            action=action,
            category=get_model_category(instance.__class__),
            content_type=ContentType.objects.get_for_model(instance),
            object_id=instance.pk,
            object_name=get_object_name(instance),
            description=f"{action.title()} {instance.__class__._meta.verbose_name} '{get_object_name(instance)}'",
            old_values=old_values,
            new_values=new_values,
            changed_fields=changed_fields,
            ip_address=ip_address,
            user_agent=user_agent,
            session_key=session_key,
            company=company,
            location=location,
            is_system_action=(user is None),
        )
    except Exception as e:
        # En cas d'erreur, on ne veut pas faire planter l'application principale
        print(f"Erreur lors de la création de l'entrée d'historique: {e}")


# Stockage temporaire des valeurs avant modification
_pre_save_instances = {}


@receiver(pre_save)
def track_pre_save(sender, instance, **kwargs):
    """
    Signal appelé avant la sauvegarde pour capturer les anciennes valeurs
    """
    if not should_track_model(sender):
        return
    
    if instance.pk:  # Modification d'un objet existant
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            _pre_save_instances[f"{sender.__name__}_{instance.pk}"] = old_instance
        except sender.DoesNotExist:
            pass


@receiver(post_save)
def track_post_save(sender, instance, created, **kwargs):
    """
    Signal appelé après la sauvegarde pour traquer les créations et modifications
    """
    if not should_track_model(sender):
        return
    
    user = get_current_user()
    
    if created:
        # Création d'un nouvel objet
        create_history_entry('create', instance, user)
    else:
        # Modification d'un objet existant
        old_instance_key = f"{sender.__name__}_{instance.pk}"
        old_instance = _pre_save_instances.get(old_instance_key)
        
        if old_instance:
            # Comparer les valeurs pour détecter les changements
            changed_fields, old_values, new_values = get_changed_fields(old_instance, instance)
            
            if changed_fields:
                create_history_entry(
                    'update', 
                    instance, 
                    user, 
                    old_values=old_values, 
                    new_values=new_values, 
                    changed_fields=changed_fields
                )
            
            # Nettoyer le stockage temporaire
            del _pre_save_instances[old_instance_key]


@receiver(post_delete)
def track_post_delete(sender, instance, **kwargs):
    """
    Signal appelé après la suppression pour traquer les suppressions
    """
    if not should_track_model(sender):
        return
    
    user = get_current_user()
    create_history_entry('delete', instance, user)


@receiver(user_logged_in)
def track_user_login(sender, request, user, **kwargs):
    """
    Signal appelé lors de la connexion d'un utilisateur
    """
    set_current_request(request)
    set_current_user(user)
    
    # Créer une entrée d'historique pour la connexion
    try:
        # Créer un objet fictif pour la connexion
        class LoginEvent:
            pk = user.pk
            __class__ = User
            
            class _meta:
                verbose_name = "session de connexion"
                app_label = "auth"
                model_name = "user"
        
        login_event = LoginEvent()
        
        HistoryEntry.objects.create(
            user=user,
            action='login',
            category='auth',
            content_type=ContentType.objects.get_for_model(User),
            object_id=user.pk,
            object_name=user.get_full_name() or user.username,
            description=f"Connexion de l'utilisateur {user.get_full_name() or user.username}",
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            session_key=request.session.session_key or "",
            company=getattr(user, 'company_profile', None) and user.company_profile.company,
            is_system_action=False,
        )
    except Exception as e:
        print(f"Erreur lors du tracking de connexion: {e}")


@receiver(user_logged_out)
def track_user_logout(sender, request, user, **kwargs):
    """
    Signal appelé lors de la déconnexion d'un utilisateur
    """
    if user:
        try:
            HistoryEntry.objects.create(
                user=user,
                action='logout',
                category='auth',
                content_type=ContentType.objects.get_for_model(User),
                object_id=user.pk,
                object_name=user.get_full_name() or user.username,
                description=f"Déconnexion de l'utilisateur {user.get_full_name() or user.username}",
                ip_address=get_client_ip(request),
                user_agent=get_user_agent(request),
                session_key=request.session.session_key or "",
                company=getattr(user, 'company_profile', None) and user.company_profile.company,
                is_system_action=False,
            )
        except Exception as e:
            print(f"Erreur lors du tracking de déconnexion: {e}")
