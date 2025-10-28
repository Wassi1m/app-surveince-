from django.urls import path
from . import views

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
    
    # Dashboard Manager
    path('manager/', views.manager_dashboard, name='manager_dashboard'),
    path('manager/employees/', views.manage_employees, name='manage_employees'),
    path('manager/employees/create/', views.create_employee, name='create_employee'),
    path('manager/employees/<int:pk>/', views.employee_detail, name='employee_detail'),
    path('manager/employees/<int:pk>/edit/', views.edit_employee, name='edit_employee'),
    path('manager/employees/<int:pk>/delete/', views.delete_employee, name='delete_employee'),
]
