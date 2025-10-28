from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Company, CompanyUser, CompanyInvitation, CompanySettings


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'reference', 'user_count', 'camera_count', 
        'location_count', 'is_active', 'created_at'
    ]
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'reference', 'email']
    readonly_fields = ['reference', 'created_at', 'updated_at', 'user_count', 'camera_count', 'location_count']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('name', 'reference', 'description', 'is_active')
        }),
        ('Contact', {
            'fields': ('address', 'phone', 'email', 'website')
        }),
        ('Limites et quotas', {
            'fields': ('max_users', 'max_cameras', 'max_locations')
        }),
        ('Statistiques', {
            'fields': ('user_count', 'camera_count', 'location_count'),
            'classes': ('collapse',)
        }),
        ('Configuration', {
            'fields': ('settings',),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_count(self, obj):
        count = obj.user_count
        url = reverse('admin:companies_companyuser_changelist') + f'?company__id__exact={obj.id}'
        return format_html('<a href="{}">{} utilisateurs</a>', url, count)
    user_count.short_description = "Utilisateurs"
    
    def camera_count(self, obj):
        return f"{obj.camera_count} caméras"
    camera_count.short_description = "Caméras"
    
    def location_count(self, obj):
        return f"{obj.location_count} lieux"
    location_count.short_description = "Lieux"


@admin.register(CompanyUser)
class CompanyUserAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'company', 'role', 'is_active', 
        'can_manage_users', 'can_manage_cameras', 'created_at'
    ]
    list_filter = ['role', 'is_active', 'company', 'can_manage_users', 'can_manage_cameras']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'user__email', 'company__name']
    raw_id_fields = ['user', 'company']
    readonly_fields = ['created_at', 'updated_at', 'last_login_company']
    
    fieldsets = (
        ('Utilisateur et entreprise', {
            'fields': ('user', 'company', 'role', 'is_active')
        }),
        ('Informations professionnelles', {
            'fields': ('employee_id', 'department', 'position', 'phone')
        }),
        ('Permissions', {
            'fields': (
                'can_manage_users', 'can_manage_cameras', 
                'can_manage_alerts', 'can_view_reports'
            )
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at', 'last_login_company'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'company')


@admin.register(CompanyInvitation)
class CompanyInvitationAdmin(admin.ModelAdmin):
    list_display = [
        'email', 'company', 'role', 'status', 
        'invited_by', 'created_at', 'expires_at', 'is_expired'
    ]
    list_filter = ['status', 'role', 'company', 'created_at']
    search_fields = ['email', 'company__name', 'invited_by__username']
    readonly_fields = ['invitation_token', 'created_at', 'accepted_at', 'accepted_by', 'is_expired']
    raw_id_fields = ['company', 'invited_by', 'accepted_by']
    
    fieldsets = (
        ('Invitation', {
            'fields': ('company', 'email', 'role', 'status')
        }),
        ('Permissions proposées', {
            'fields': (
                'can_manage_users', 'can_manage_cameras', 
                'can_manage_alerts', 'can_view_reports'
            )
        }),
        ('Informations système', {
            'fields': ('invitation_token', 'invited_by', 'accepted_by'),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('created_at', 'expires_at', 'accepted_at', 'is_expired'),
            'classes': ('collapse',)
        }),
    )
    
    def is_expired(self, obj):
        if obj.is_expired:
            return format_html('<span style="color: red;">Expiré</span>')
        return format_html('<span style="color: green;">Valide</span>')
    is_expired.short_description = "État"


@admin.register(CompanySettings)
class CompanySettingsAdmin(admin.ModelAdmin):
    list_display = ['company', 'theme', 'language', 'timezone', 'updated_at']
    list_filter = ['theme', 'language', 'email_notifications', 'sms_notifications']
    search_fields = ['company__name']
    raw_id_fields = ['company']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Entreprise', {
            'fields': ('company',)
        }),
        ('Sécurité', {
            'fields': (
                'password_policy', 'session_timeout', 
                'max_login_attempts'
            )
        }),
        ('Notifications', {
            'fields': (
                'email_notifications', 'sms_notifications', 
                'push_notifications'
            )
        }),
        ('Surveillance', {
            'fields': (
                'ai_confidence_threshold', 'auto_archive_days', 
                'max_storage_gb'
            )
        }),
        ('Interface', {
            'fields': ('theme', 'language', 'timezone')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


# Extension de l'admin User pour inclure les informations d'entreprise
class CompanyUserInline(admin.StackedInline):
    model = CompanyUser
    can_delete = False
    verbose_name_plural = "Informations d'entreprise"
    fields = [
        'company', 'role', 'is_active', 'employee_id', 
        'department', 'position', 'phone'
    ]
    extra = 0


class UserAdmin(BaseUserAdmin):
    inlines = (CompanyUserInline,)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('company_profile__company')


# Réenregistrer UserAdmin avec les inlines
admin.site.unregister(User)
admin.site.register(User, UserAdmin)