from django.db.models.signals import post_save, pre_delete, pre_save, post_delete  # Ajouter post_delete ici
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.utils import timezone
import threading
import json

from .models import HistoryEntry, HistorySettings
from .utils import get_client_ip, get_user_agent, get_model_category, get_object_name, get_changed_fields
from django.core.exceptions import ObjectDoesNotExist
import datetime


# Thread local storage pour stocker les informations de la requête
_thread_locals = threading.local()

# Stockage temporaire pour les suppressions
_deletion_data = {}


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


def get_company_from_instance(instance):
    """Récupère l'entreprise depuis une instance"""
    company = None
    location = None
    
    if hasattr(instance, 'company'):
        company = instance.company
    elif hasattr(instance, 'location') and hasattr(instance.location, 'company'):
        company = instance.location.company
        location = instance.location
    elif hasattr(instance, 'camera') and hasattr(instance.camera, 'location'):
        company = instance.camera.location.company
        location = instance.camera.location
    
    return company, location


def should_track_model(model_class, company=None):
    """
    Détermine si un modèle doit être tracké selon la configuration
    """
    try:
        # Éviter de traquer les modèles d'historique eux-mêmes
        if model_class._meta.app_label == 'history':
            return False
        
        # Éviter de traquer pendant les migrations
        import sys
        if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
            return False
        
        # Éviter de traquer certains modèles système
        excluded_models = [
            'contenttypes.ContentType',
            'auth.Permission',
            'sessions.Session',
            'admin.LogEntry',
            'history.HistoryEntry',
            'history.HistorySettings',
        ]
        
        model_name = f"{model_class._meta.app_label}.{model_class._meta.model_name}"
        if model_name in excluded_models:
            return False
        
        # 🔥 VÉRIFICATION CRITIQUE : PK numérique
        if not hasattr(model_class._meta, 'pk') or model_class._meta.pk is None:
            return False
        
        pk = model_class._meta.pk
        if not hasattr(pk, 'get_internal_type'):
            return False
        
        pk_type = pk.get_internal_type()
        
        # Accepter uniquement les PK numériques
        allowed_pk_types = ['AutoField', 'BigAutoField', 'IntegerField', 'BigIntegerField']
        if pk_type not in allowed_pk_types:
            return False
        
        # Vérifier que le modèle a bien un champ 'id' ou PK
        if not any(field.primary_key for field in model_class._meta.fields):
            return False
        
        # Vérifier les paramètres de l'entreprise si disponible
        if company:
            try:
                settings = HistorySettings.objects.get(company=company)
                category = get_model_category(model_class)
                if hasattr(settings, 'enabled_categories'):
                    return category in settings.enabled_categories
            except HistorySettings.DoesNotExist:
                pass
        
        return True
        
    except Exception as e:
        # En cas d'erreur, ne pas tracker pour éviter les problèmes
        print(f"Erreur dans should_track_model pour {model_class}: {e}")
        return False


def get_instance_field_data(instance):
    """Récupère les données d'une instance sous forme de dict sérialisable"""
    data = {}
    for field in instance._meta.fields:
        field_name = field.name
        try:
            value = getattr(instance, field_name)
            
            # Sérialiser les types complexes
            if hasattr(value, 'pk'):  # Relation ForeignKey
                data[field_name] = str(value.pk)
            elif isinstance(value, (datetime.date, datetime.time)):
                data[field_name] = value.isoformat()
            else:
                data[field_name] = str(value) if value is not None else None
                
        except (AttributeError, ValueError, ObjectDoesNotExist):
            data[field_name] = None
    
    return data


def create_history_entry(action, instance, user=None, old_values=None, new_values=None, changed_fields=None):
    """
    Crée une entrée d'historique
    """
    request = get_current_request()
    if not user:
        user = get_current_user()
    
    # Déterminer l'entreprise associée
    company, location = get_company_from_instance(instance)
    
    # Si pas d'entreprise trouvée via l'instance, essayer via l'utilisateur
    if not company and user and hasattr(user, 'company_profile'):
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
    company, _ = get_company_from_instance(instance)
    if not should_track_model(sender, company):
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
    company, _ = get_company_from_instance(instance)
    if not should_track_model(sender, company):
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
            if old_instance_key in _pre_save_instances:
                del _pre_save_instances[old_instance_key]


@receiver(pre_delete)
def track_pre_delete(sender, instance, **kwargs):
    """
    Signal appelé avant la suppression pour capturer les données
    """
    company, location = get_company_from_instance(instance)
    if not should_track_model(sender, company):
        return
    
    # Capturer les données avant suppression
    old_values = get_instance_field_data(instance)
    user = get_current_user()
    
    # Stocker les données pour la création de l'entrée d'historique
    key = f"{sender.__name__}_{instance.pk}"
    _deletion_data[key] = {
        'old_values': old_values,
        'user': user,
        'company': company,
        'location': location,
        'content_type': ContentType.objects.get_for_model(instance),
        'object_name': get_object_name(instance),
        'category': get_model_category(instance.__class__),
    }


@receiver(post_delete)
def track_post_delete(sender, instance, **kwargs):
    """
    Signal appelé après la suppression pour créer l'entrée d'historique
    """
    key = f"{sender.__name__}_{instance.pk}"
    deletion_info = _deletion_data.get(key)
    
    if not deletion_info:
        return
    
    # Récupérer les informations de la requête
    request = get_current_request()
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
            user=deletion_info['user'],
            action='delete',
            category=deletion_info['category'],
            content_type=deletion_info['content_type'],
            object_id=instance.pk,  # PK toujours disponible même après suppression
            object_name=deletion_info['object_name'],
            description=f"Delete {instance.__class__._meta.verbose_name} '{deletion_info['object_name']}'",
            old_values=deletion_info['old_values'],
            new_values=None,
            changed_fields=list(deletion_info['old_values'].keys()) if deletion_info['old_values'] else None,
            ip_address=ip_address,
            user_agent=user_agent,
            session_key=session_key,
            company=deletion_info['company'],
            location=deletion_info['location'],
            is_system_action=(deletion_info['user'] is None),
        )
    except Exception as e:
        print(f"Erreur lors de la création de l'entrée d'historique de suppression: {e}")
    finally:
        # Nettoyer les données temporaires
        if key in _deletion_data:
            del _deletion_data[key]


@receiver(user_logged_in)
def track_user_login(sender, request, user, **kwargs):
    """
    Signal appelé lors de la connexion d'un utilisateur
    """
    set_current_request(request)
    set_current_user(user)
    
    # Créer une entrée d'historique pour la connexion
    try:
        company = getattr(user, 'company_profile', None) and user.company_profile.company
        
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
            company=company,
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
            company = getattr(user, 'company_profile', None) and user.company_profile.company
            
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
                company=company,
                is_system_action=False,
            )
        except Exception as e:
            print(f"Erreur lors du tracking de déconnexion: {e}")