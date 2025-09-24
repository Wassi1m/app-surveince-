from django.urls import path
from . import views

app_name = 'alerts_api'

urlpatterns = [
    # API Alertes
    path('active/', views.api_active_alerts, name='active_alerts'),
    path('stats/', views.api_alert_stats, name='alert_stats'),
] 