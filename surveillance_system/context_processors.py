from django.conf import settings

def cache_version(request):
    """
    Context processor pour ajouter la version de cache aux templates.
    Permet de forcer le rechargement des fichiers statiques.
    """
    return {
        'CACHE_VERSION': getattr(settings, 'CACHE_VERSION', '1.0.0')
    }
