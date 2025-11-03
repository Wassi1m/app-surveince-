from django.urls import path
from . import views

app_name = 'history'

urlpatterns = [
    # Tableau de bord de l'historique
    path('', views.history_dashboard, name='dashboard'),
    
    # Liste complète avec filtres
    path('list/', views.history_list, name='list'),
    
    # Détail d'une entrée
    path('detail/<int:entry_id>/', views.history_detail, name='detail'),
    
    # Export
    path('export/', views.export_history, name='export'),
    
    # Paramètres
    path('settings/', views.history_settings, name='settings'),
    
    # API pour les statistiques
    path('api/stats/', views.history_stats_api, name='stats_api'),
]
