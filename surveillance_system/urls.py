"""
URL Configuration for surveillance_system project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect
from monitoring.views import dashboard

# Redirection de la racine vers le tableau de bord
def root_redirect(request):
    return redirect('dashboard')

urlpatterns = [
    # Administration Django
    path('admin/', admin.site.urls),
    
    # Racine - redirection vers dashboard
    path('', root_redirect, name='root'),
    path('dashboard/', dashboard, name='dashboard'),
    
    # Applications
    path('monitoring/', include('monitoring.urls')),
    path('alerts/', include('alerts.urls')),
    path('analytics/', include('analytics.urls')),
    
    # API
    path('api/', include('monitoring.api_urls')),
    path('api/alerts/', include('alerts.api_urls')),
    path('api/analytics/', include('analytics.api_urls')),
    
    # Authentification
    path('login/', auth_views.LoginView.as_view(
        template_name='auth/login.html',
        redirect_authenticated_user=True,
        next_page='dashboard'
    ), name='login'),
    
    path('logout/', auth_views.LogoutView.as_view(
        next_page='login'
    ), name='logout'),
    
    path('password_change/', auth_views.PasswordChangeView.as_view(
        template_name='auth/password_change.html',
        success_url='/dashboard/'
    ), name='password_change'),
    
    # path('profile/', include('accounts.urls')),  # App accounts pas encore créée
]

# Configuration pour les fichiers statiques et media en développement
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # URLs de debug pour le développement - commenté car debug_toolbar pas installé
    # import debug_toolbar
    # urlpatterns = [
    #     path('__debug__/', include(debug_toolbar.urls)),
    # ] + urlpatterns

# Configuration de l'admin
admin.site.site_header = "Administration - Surveillance IA"
admin.site.site_title = "Surveillance IA"
admin.site.index_title = "Gestion du Système de Surveillance"
