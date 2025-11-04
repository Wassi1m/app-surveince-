from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Company, CompanyUser, CompanyInvitation, CompanySettings, EmployeCible, EmployeCibleImportBatch


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


@admin.register(EmployeCible)
class EmployeCibleAdmin(admin.ModelAdmin):
    list_display = [
        'nom_complet', 'company', 'subcompany', 'status', 
        'detection_status', 'detection_confidence', 'is_priority', 
        'importe_par', 'created_at'
    ]
    list_filter = [
        'status', 'detection_status', 'is_priority', 'is_active',
        'company', 'subcompany', 'created_at'
    ]
    search_fields = [
        'prenom', 'nom', 'employee_id', 'poste', 'departement',
        'company__name', 'subcompany__name'
    ]
    readonly_fields = [
        'image_width', 'image_height', 'image_size', 'image_format',
        'face_encoding', 'face_landmarks', 'detection_confidence',
        'created_at', 'updated_at', 'validated_at'
    ]
    raw_id_fields = ['company', 'subcompany', 'importe_par', 'valide_par']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('company', 'subcompany', 'status', 'is_active', 'is_priority')
        }),
        ('Images', {
            'fields': ('image_originale', 'image_miniature', 'image_visage'),
            'description': 'Images de l\'employé ciblé'
        }),
        ('Informations personnelles', {
            'fields': ('prenom', 'nom', 'employee_id', 'poste', 'departement', 'notes')
        }),
        ('Détection faciale', {
            'fields': (
                'detection_status', 'detection_confidence', 
                'face_encoding', 'face_landmarks'
            ),
            'classes': ('collapse',)
        }),
        ('Métadonnées image', {
            'fields': (
                'image_width', 'image_height', 'image_size', 'image_format'
            ),
            'classes': ('collapse',)
        }),
        ('Gestion', {
            'fields': ('importe_par', 'valide_par', 'validated_at'),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def nom_complet(self, obj):
        if obj.prenom and obj.nom:
            name = f"{obj.prenom} {obj.nom}"
        elif obj.prenom:
            name = obj.prenom
        elif obj.nom:
            name = obj.nom
        else:
            name = f"Employé #{obj.pk}"
        
        # Ajouter des indicateurs visuels
        indicators = []
        if obj.is_priority:
            indicators.append('<span style="color: orange;">⭐</span>')
        if obj.status == 'validated':
            indicators.append('<span style="color: green;">✓</span>')
        elif obj.status == 'rejected':
            indicators.append('<span style="color: red;">✗</span>')
        
        if indicators:
            name += ' ' + ' '.join(indicators)
        
        return format_html(name)
    nom_complet.short_description = "Nom complet"
    
    def detection_confidence(self, obj):
        if obj.detection_confidence:
            confidence = obj.detection_confidence
            if confidence >= 0.8:
                color = 'green'
            elif confidence >= 0.6:
                color = 'orange'
            else:
                color = 'red'
            return format_html(
                '<span style="color: {};">{:.1f}%</span>', 
                color, confidence * 100
            )
        return '-'
    detection_confidence.short_description = "Confiance"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'company', 'subcompany', 'importe_par', 'valide_par'
        )
    
    actions = ['validate_employees', 'reject_employees', 'mark_priority']
    
    def validate_employees(self, request, queryset):
        count = 0
        for employee in queryset:
            if employee.status == 'pending':
                employee.validate(request.user)
                count += 1
        self.message_user(request, f'{count} employé(s) validé(s) avec succès.')
    validate_employees.short_description = "Valider les employés sélectionnés"
    
    def reject_employees(self, request, queryset):
        count = 0
        for employee in queryset:
            if employee.status == 'pending':
                employee.reject(request.user)
                count += 1
        self.message_user(request, f'{count} employé(s) rejeté(s).')
    reject_employees.short_description = "Rejeter les employés sélectionnés"
    
    def mark_priority(self, request, queryset):
        count = queryset.update(is_priority=True)
        self.message_user(request, f'{count} employé(s) marqué(s) comme prioritaire(s).')
    mark_priority.short_description = "Marquer comme prioritaire"


@admin.register(EmployeCibleImportBatch)
class EmployeCibleImportBatchAdmin(admin.ModelAdmin):
    list_display = [
        'nom_lot', 'company', 'subcompany', 'status', 
        'progress_display', 'success_rate_display', 'cree_par', 'created_at'
    ]
    list_filter = [
        'status', 'company', 'subcompany', 'created_at'
    ]
    search_fields = [
        'nom_lot', 'description', 'company__name', 'subcompany__name'
    ]
    readonly_fields = [
        'total_images', 'images_traitees', 'images_reussies', 'images_echouees',
        'progress_percentage', 'success_rate', 'logs', 'erreurs',
        'created_at', 'updated_at', 'completed_at'
    ]
    raw_id_fields = ['company', 'subcompany', 'cree_par']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('company', 'subcompany', 'nom_lot', 'description', 'status')
        }),
        ('Statistiques', {
            'fields': (
                'total_images', 'images_traitees', 'images_reussies', 
                'images_echouees', 'progress_percentage', 'success_rate'
            )
        }),
        ('Gestion', {
            'fields': ('cree_par',)
        }),
        ('Logs et erreurs', {
            'fields': ('logs', 'erreurs'),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def progress_display(self, obj):
        percentage = obj.progress_percentage
        if percentage == 100:
            color = 'green'
        elif percentage > 50:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<div style="width: 100px; background: #f0f0f0; border-radius: 5px;">'
            '<div style="width: {}%; background: {}; height: 20px; border-radius: 5px; '
            'text-align: center; color: white; line-height: 20px; font-size: 12px;">'
            '{}%</div></div>',
            percentage, color, percentage
        )
    progress_display.short_description = "Progression"
    
    def success_rate_display(self, obj):
        rate = obj.success_rate
        if rate >= 90:
            color = 'green'
        elif rate >= 70:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color, rate
        )
    success_rate_display.short_description = "Taux de réussite"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'company', 'subcompany', 'cree_par'
        )