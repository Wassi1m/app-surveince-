#!/usr/bin/env python
"""
Script pour déboguer les comptes employés
"""
import os
import sys
import django

# Configuration Django
sys.path.append('/home/user/Bureau/app suc')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'surveillance_system.settings')
django.setup()

from django.contrib.auth.models import User
from companies.models import CompanyUser, Company

def debug_employees():
    print("=== DEBUG DES COMPTES EMPLOYÉS ===\n")
    
    # Lister toutes les entreprises
    companies = Company.objects.all()
    print(f"Nombre d'entreprises: {companies.count()}")
    
    for company in companies:
        print(f"\n--- Entreprise: {company.name} (Référence: {company.reference}) ---")
        print(f"Active: {company.is_active}")
        
        # Lister tous les utilisateurs de cette entreprise
        company_users = CompanyUser.objects.filter(company=company)
        print(f"Nombre d'utilisateurs: {company_users.count()}")
        
        for company_user in company_users:
            user = company_user.user
            print(f"\n  Utilisateur: {user.get_full_name()} ({user.username})")
            print(f"  Email: {user.email}")
            print(f"  Rôle: {company_user.role}")
            print(f"  Actif (Django): {user.is_active}")
            print(f"  Actif (Entreprise): {company_user.is_active}")
            print(f"  Mot de passe défini: {bool(user.password)}")
            print(f"  Peut se connecter: {user.has_usable_password()}")
            
            # Tester l'authentification avec un mot de passe commun
            from django.contrib.auth import authenticate
            test_passwords = ['password123', '123456', 'admin', user.username]
            
            for test_pwd in test_passwords:
                test_user = authenticate(username=user.username, password=test_pwd)
                if test_user:
                    print(f"  ✓ Mot de passe trouvé: {test_pwd}")
                    break
            else:
                print(f"  ✗ Aucun mot de passe testé ne fonctionne")

def reset_employee_password():
    """Réinitialise le mot de passe d'un employé pour les tests"""
    print("\n=== RÉINITIALISATION DE MOT DE PASSE ===")
    
    # Chercher les employés (non-owners)
    employees = CompanyUser.objects.exclude(role='owner')
    
    if not employees.exists():
        print("Aucun employé trouvé.")
        return
    
    print("Employés disponibles:")
    for i, emp in enumerate(employees, 1):
        print(f"{i}. {emp.user.get_full_name()} ({emp.user.username}) - {emp.company.name}")
    
    try:
        choice = input("\nChoisir un employé (numéro): ").strip()
        if choice.isdigit():
            employee = employees[int(choice) - 1]
            new_password = "123456"  # Mot de passe simple pour les tests
            
            employee.user.set_password(new_password)
            employee.user.save()
            
            print(f"\n✓ Mot de passe réinitialisé pour {employee.user.get_full_name()}")
            print(f"  Nom d'utilisateur: {employee.user.username}")
            print(f"  Email: {employee.user.email}")
            print(f"  Nouveau mot de passe: {new_password}")
            print(f"  Référence entreprise: {employee.company.reference}")
            
    except (ValueError, IndexError):
        print("Choix invalide.")
    except KeyboardInterrupt:
        print("\nOpération annulée.")

if __name__ == '__main__':
    debug_employees()
    
    print("\n" + "="*50)
    reset_choice = input("Voulez-vous réinitialiser le mot de passe d'un employé ? (o/n): ").strip().lower()
    if reset_choice in ['o', 'oui', 'y', 'yes']:
        reset_employee_password()
