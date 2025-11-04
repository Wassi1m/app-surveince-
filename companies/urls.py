from django.urls import path
from . import views, subcompany_views

app_name = 'companies'

urlpatterns = [
    # Dashboard Owner
    path('owner/', views.owner_dashboard, name='owner_dashboard'),
    path('owner/companies/', views.company_list, name='company_list'),
    path('owner/companies/create/', views.company_create, name='company_create'),
    path('owner/companies/<int:pk>/created/', views.company_created, name='company_created'),
    path('owner/companies/<int:pk>/', views.company_detail, name='company_detail'),
    path('owner/companies/<int:pk>/edit/', views.company_edit, name='company_edit'),
    path('owner/companies/<int:pk>/toggle-status/', views.toggle_company_status, name='toggle_company_status'),
    
    # Notifications Owner
    path('owner/notifications/', views.owner_notifications, name='owner_notifications'),
    path('owner/notifications/create/', views.create_owner_notification, name='create_owner_notification'),
    path('owner/notifications/history/', views.owner_notification_history, name='owner_notification_history'),
    
    # Types d'événements Owner
    path('owner/event-types/', views.owner_event_types, name='owner_event_types'),
    path('owner/event-types/create/', views.create_event_type, name='create_event_type'),
    path('owner/event-types/<int:event_type_id>/update/', views.update_event_type, name='update_event_type'),
    path('owner/companies/<int:company_id>/event-types/', views.manage_company_event_types, name='manage_company_event_types'),
    
    # Employés ciblés Owner
    path('owner/employees-cibles/', views.owner_import_employees_cibled, name='owner_import_employees_cibled'),
    path('owner/employees-cibles/upload/', views.upload_employee_images, name='upload_employee_images'),
    path('owner/employees-cibles/manage/', views.manage_employees_cibles, name='manage_employees_cibles'),
    path('owner/employees-cibles/<int:employee_id>/', views.employee_cible_detail, name='employee_cible_detail'),
    path('owner/employees-cibles/<int:employee_id>/update/', views.update_employee_info, name='update_employee_info'),
    path('owner/employees-cibles/<int:employee_id>/validate/', views.validate_employee, name='validate_employee'),
    path('owner/employees-cibles/<int:employee_id>/reject/', views.reject_employee, name='reject_employee'),
    path('owner/employees-cibles/<int:employee_id>/delete/', views.delete_employee, name='delete_employee_cible'),
    path('owner/employees-cibles/batch-action/', views.batch_action_employees, name='batch_action_employees'),
    
    # Dashboard Manager
    path('manager/', views.manager_dashboard, name='manager_dashboard'),
    path('manager/subcompany-selector/', views.subcompany_selector, name='subcompany_selector'),
    path('manager/employees/', views.manage_employees, name='manage_employees'),
    path('manager/employees/create/', views.create_employee, name='create_employee'),
    path('manager/employees/<int:pk>/', views.employee_detail, name='employee_detail'),
    path('manager/employees/<int:pk>/edit/', views.edit_employee, name='edit_employee'),
    path('manager/employees/<int:pk>/delete/', views.delete_employee, name='delete_employee'),
    
    # Gestion des sous-entreprises
    path('subcompany-wizard/<int:company_id>/', subcompany_views.subcompany_management_wizard, name='subcompany_wizard'),
    path('subcompanies/<int:company_id>/', subcompany_views.subcompany_list, name='subcompany_list'),
    path('subcompanies/<int:company_id>/create/', subcompany_views.subcompany_create, name='subcompany_create'),
    
    # Sélecteur de sous-entreprise (AJAX)
    path('api/subcompany-selector/', subcompany_views.subcompany_selector, name='api_subcompany_selector'),
]
