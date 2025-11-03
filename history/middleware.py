from django.utils.deprecation import MiddlewareMixin
from .signals import set_current_request, set_current_user


class HistoryMiddleware(MiddlewareMixin):
    """
    Middleware pour capturer les informations de requête et d'utilisateur
    pour le système d'historisation
    """
    
    def process_request(self, request):
        """
        Stocke la requête et l'utilisateur courant dans le thread local
        """
        set_current_request(request)
        
        if hasattr(request, 'user') and request.user.is_authenticated:
            set_current_user(request.user)
        else:
            set_current_user(None)
        
        return None
    
    def process_response(self, request, response):
        """
        Nettoie les données du thread local après la requête
        """
        # On pourrait nettoyer ici, mais on laisse les données disponibles
        # au cas où d'autres processus en auraient besoin
        return response
