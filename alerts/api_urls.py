from django.urls import path
from . import views

app_name = 'alerts_api'

urlpatterns = [
    # API Alertes
    path('active/', views.api_active_alerts, name='active_alerts'),
    path('stats/', views.api_alert_stats, name='alert_stats'),
    
    # API Notifications
    path('notifications/unread/', views.api_unread_notifications, name='unread_notifications'),
    path('notifications/', views.api_notifications_list, name='notifications_list'),
    path('notifications/<int:notification_id>/read/', views.api_mark_notification_read, name='mark_notification_read'),
    path('notifications/preferences/', views.api_notification_preferences, name='notification_preferences'),
    path('notifications/channels/', views.api_notification_channels, name='notification_channels'),
    path('notifications/send/', views.api_send_notification, name='send_notification'),
    
    # API Règles
    path('rules/create/', views.api_create_rule, name='create_rule'),
    path('rules/<int:rule_id>/', views.api_rule_detail, name='rule_detail'),
    path('rules/<int:rule_id>/stats/', views.api_rule_stats, name='rule_stats'),
    path('rules/<int:rule_id>/test/', views.api_test_rule, name='test_rule'),
] 