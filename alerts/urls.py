from django.urls import path
from . import views

app_name = 'alerts'

urlpatterns = [
    # Centre des alertes
    path('', views.alert_center, name='alert_center'),
    path('<int:alert_id>/', views.alert_detail, name='alert_detail'),
    path('<int:alert_id>/acknowledge/', views.acknowledge_alert, name='acknowledge_alert'),
    path('<int:alert_id>/resolve/', views.resolve_alert, name='resolve_alert'),
    
    # Règles d'alerte
    path('rules/', views.rules_list, name='rules'),
    path('rules/<int:rule_id>/', views.rule_detail, name='rule_detail'),
    path('rules/create/', views.create_rule, name='create_rule'),
    path('rules/<int:rule_id>/toggle/', views.toggle_rule, name='toggle_rule'),
    
    # Canaux de notification
    path('channels/', views.notification_channels, name='notification_channels'),
    path('channels/create/', views.create_channel, name='create_channel'),
    path('channels/<int:channel_id>/test/', views.test_channel, name='test_channel'),
    
    # Historique des notifications
    path('notifications/history/', views.notification_history, name='notification_history'),
] 