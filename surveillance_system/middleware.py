"""
Middleware personnalisé pour la gestion des sessions et tokens
"""
from django.utils import timezone
from django.contrib.auth import logout
from django.http import JsonResponse
from rest_framework.authtoken.models import Token
from datetime import timedelta


class TokenExpirationMiddleware:
    """
    Middleware pour gérer l'expiration des tokens API (2 heures)
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Vérifier l'expiration des tokens API
        if hasattr(request, 'auth') and isinstance(request.auth, Token):
            token = request.auth
            # Vérifier si le token a plus de 2 heures
            if token.created < timezone.now() - timedelta(hours=2):
                token.delete()  # Supprimer le token expiré
                return JsonResponse({
                    'error': 'Token expiré',
                    'message': 'Votre session a expiré. Veuillez vous reconnecter.',
                    'code': 'TOKEN_EXPIRED'
                }, status=401)

        response = self.get_response(request)
        return response


class SessionTimeoutMiddleware:
    """
    Middleware pour gérer l'expiration des sessions utilisateur
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Vérifier la dernière activité
            last_activity = request.session.get('last_activity')
            if last_activity:
                last_activity = timezone.datetime.fromisoformat(last_activity)
                # Si plus de 2 heures d'inactivité
                if timezone.now() - last_activity > timedelta(hours=2):
                    logout(request)
                    request.session.flush()
            
            # Mettre à jour la dernière activité
            request.session['last_activity'] = timezone.now().isoformat()

        response = self.get_response(request)
        return response


class SecurityHeadersMiddleware:
    """
    Middleware pour ajouter des en-têtes de sécurité
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Ajouter des en-têtes de sécurité
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Cache control pour les pages sensibles
        if request.path.startswith('/admin/') or request.path.startswith('/dashboard/'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        return response
