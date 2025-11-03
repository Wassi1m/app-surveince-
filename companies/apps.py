from django.apps import AppConfig


class CompaniesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'companies'
    verbose_name = 'Gestion des Entreprises'
    
    def ready(self):
        """
        Méthode appelée quand l'application est prête.
        Ici on importe les signaux.
        """
        import companies.signals
