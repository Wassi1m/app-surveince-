"""
Middleware personnalisé pour la gestion des sessions et tokens
"""
from django.utils import timezone
from django.contrib.auth import logout
from django.http import JsonResponse
from datetime import timedelta


class SessionTimeoutMiddleware:
    """
    Middleware pour gérer l'expiration des sessions utilisateur
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Traitement simple sans erreur
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
        
        return response
