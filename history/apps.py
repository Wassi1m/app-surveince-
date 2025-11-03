from django.apps import AppConfig


class HistoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'history'
    verbose_name = 'Historique'
    
    def ready(self):
        """
        Méthode appelée quand l'application est prête.
        Ici on importe les signaux pour activer le tracking automatique.
        """
        import history.signals