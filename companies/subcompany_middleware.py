from django.utils.deprecation import MiddlewareMixin
from .models import CompanyUser, SubCompany


class SubCompanyMiddleware(MiddlewareMixin):
    """
    Middleware pour gérer la sous-entreprise courante de l'utilisateur
    """
    
    def process_request(self, request):
        """
        Ajoute les informations de sous-entreprise à la requête
        """
        # Initialiser les attributs de sous-entreprise
        request.current_subcompany = None
        request.accessible_subcompanies = []
        
        # Vérifier si l'utilisateur est authentifié et a un profil d'entreprise
        if request.user.is_authenticated and hasattr(request.user, 'company_profile'):
            company_user = request.user.company_profile
            
            # Récupérer les sous-entreprises accessibles
            request.accessible_subcompanies = company_user.get_accessible_subcompanies()
            
            # Définir la sous-entreprise courante
            if company_user.current_subcompany:
                request.current_subcompany = company_user.current_subcompany
            elif request.accessible_subcompanies.exists():
                # Si pas de sous-entreprise courante définie, prendre la première accessible
                first_subcompany = request.accessible_subcompanies.first()
                company_user.current_subcompany = first_subcompany
                company_user.save()
                request.current_subcompany = first_subcompany
        
        return None
    
    def process_template_response(self, request, response):
        """
        Ajoute les informations de sous-entreprise au contexte du template
        """
        if hasattr(response, 'context_data') and response.context_data is not None:
            response.context_data.update({
                'current_subcompany': getattr(request, 'current_subcompany', None),
                'accessible_subcompanies': getattr(request, 'accessible_subcompanies', []),
            })
        
        return response
