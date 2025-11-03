from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import HistoryEntry, HistoryFilter, HistoryExport, HistorySettings


@admin.register(HistoryEntry)
class HistoryEntryAdmin(admin.ModelAdmin):
    list_display = [
        'timestamp', 'user_display', 'action', 'category', 
        'object_name', 'company_display', 'ip_address'
    ]
    list_filter = [
        'action', 'category', 'timestamp', 'company', 
        'is_sensitive', 'is_system_action'
    ]
    search_fields = [
        'object_name', 'description', 'user__username', 
        'user__first_name', 'user__last_name', 'ip_address'
    ]
    readonly_fields = [
        'timestamp', 'user', 'action', 'category', 'content_type', 
        'object_id', 'object_name', 'description', 'old_values', 
        'new_values', 'changed_fields', 'ip_address', 'user_agent', 
        'session_key', 'company', 'location', 'is_sensitive', 'is_system_action'
    ]
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    
    def user_display(self, obj):
        if obj.user:
            return obj.user.get_full_name() or obj.user.username
        return "Système"
    user_display.short_description = "Utilisateur"
    
    def company_display(self, obj):
        if obj.company:
            return obj.company.name
        return "-"
    company_display.short_description = "Entreprise"
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Seuls les superutilisateurs peuvent supprimer l'historique
        return request.user.is_superuser


@admin.register(HistoryFilter)
class HistoryFilterAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'is_default', 'is_shared', 'created_at']
    list_filter = ['is_default', 'is_shared', 'created_at']
    search_fields = ['name', 'description', 'user__username']
    readonly_fields = ['created_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            qs = qs.filter(user=request.user)
        return qs


@admin.register(HistoryExport)
class HistoryExportAdmin(admin.ModelAdmin):
    list_display = [
        'created_at', 'user', 'company', 'format', 
        'status', 'record_count', 'file_size_display'
    ]
    list_filter = ['status', 'format', 'created_at', 'company']
    search_fields = ['user__username', 'company__name']
    readonly_fields = [
        'created_at', 'completed_at', 'file_path', 
        'file_size', 'record_count', 'error_message'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    def file_size_display(self, obj):
        if obj.file_size:
            if obj.file_size < 1024:
                return f"{obj.file_size} B"
            elif obj.file_size < 1024 * 1024:
                return f"{obj.file_size / 1024:.1f} KB"
            else:
                return f"{obj.file_size / (1024 * 1024):.1f} MB"
        return "-"
    file_size_display.short_description = "Taille du fichier"
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            # Les utilisateurs ne voient que leurs propres exports
            if hasattr(request.user, 'company_profile'):
                qs = qs.filter(company=request.user.company_profile.company)
            else:
                qs = qs.filter(user=request.user)
        return qs


@admin.register(HistorySettings)
class HistorySettingsAdmin(admin.ModelAdmin):
    list_display = [
        'company', 'retention_days', 'auto_archive', 
        'track_views', 'notify_sensitive_actions'
    ]
    list_filter = ['auto_archive', 'track_views', 'notify_sensitive_actions']
    search_fields = ['company__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Entreprise', {
            'fields': ('company',)
        }),
        ('Paramètres de rétention', {
            'fields': ('retention_days', 'auto_archive')
        }),
        ('Paramètres de tracking', {
            'fields': (
                'track_views', 'track_exports', 'track_system_actions',
                'enabled_categories'
            )
        }),
        ('Notifications', {
            'fields': ('notify_sensitive_actions', 'notification_emails')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Création
            obj.updated_by = request.user
        else:  # Modification
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            # Les utilisateurs ne voient que les paramètres de leur entreprise
            if hasattr(request.user, 'company_profile'):
                qs = qs.filter(company=request.user.company_profile.company)
        return qs


# Configuration de l'admin
admin.site.site_header = "Administration - Système d'Historisation"
admin.site.site_title = "Historique"
admin.site.index_title = "Gestion de l'Historique"