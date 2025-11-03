#!/usr/bin/env python
"""
Script pour créer un utilisateur et une entreprise avec des paramètres spécifiques

Usage:
    python setup_user_and_company.py
    
Ce script crée:
- Un utilisateur newowner avec le mot de passe StrongPassword123!!
- Une entreprise avec la référence TEST1234
- L'association entre l'utilisateur et l'entreprise
"""

import os
import sys
import django
from django.contrib.auth import get_user_model
from django.db import transaction

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'surveillance_system.settings')
django.setup()

User = get_user_model()

def setup_user_and_company():
    """Créer un utilisateur et une entreprise"""
    
    print("=" * 70)
    print("🚀 CONFIGURATION UTILISATEUR ET ENTREPRISE")
    print("=" * 70)
    print()
    
    try:
        with transaction.atomic():
            # 1. Créer ou mettre à jour l'utilisateur newowner
            print("📝 Étape 1 : Configuration de l'utilisateur 'newowner'...")
            username = "newowner"
            password = "StrongPassword123!!"
            email = "newowner@surveillance.com"
            
            if User.objects.filter(username=username).exists():
                user = User.objects.get(username=username)
                user.set_password(password)
                user.email = email
                user.is_staff = True
                user.is_superuser = True
                user.first_name = "New"
                user.last_name = "Owner"
                user.save()
                print(f"✅ Utilisateur '{username}' mis à jour.")
            else:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name="New",
                    last_name="Owner",
                    is_staff=True,
                    is_superuser=True
                )
                print(f"✅ Utilisateur '{username}' créé.")
            
            # 2. Créer le profil CompanyUser (Owner)
            print()
            print("📝 Étape 2 : Configuration du profil Owner...")
            from companies.models import CompanyUser, Company, CompanySettings
            
            company_user, created = CompanyUser.objects.get_or_create(
                user=user,
                defaults={
                    'role': 'owner',
                    'is_active': True,
                    'company': None,  # Owner n'appartient à aucune entreprise
                    'can_manage_users': True,
                    'can_manage_cameras': True,
                    'can_manage_alerts': True,
                    'can_view_reports': True,
                }
            )
            
            if not created:
                company_user.role = 'owner'
                company_user.is_active = True
                company_user.company = None
                company_user.can_manage_users = True
                company_user.can_manage_cameras = True
                company_user.can_manage_alerts = True
                company_user.can_view_reports = True
                company_user.save()
                print(f"✅ Profil Owner mis à jour.")
            else:
                print(f"✅ Profil Owner créé.")
            
            # 3. Créer ou récupérer l'entreprise TEST1234
            print()
            print("📝 Étape 3 : Configuration de l'entreprise TEST1234...")
            
            company, company_created = Company.objects.get_or_create(
                reference="TEST1234",
                defaults={
                    'name': 'Entreprise de Test',
                    'description': 'Entreprise de test pour les démonstrations',
                    'address': '123 Rue de Test, 75001 Paris',
                    'phone': '+33 1 23 45 67 89',
                    'email': 'contact@test1234.com',
                    'website': 'https://www.test1234.com',
                    'is_active': True,
                    'max_users': 100,
                    'max_cameras': 50,
                    'max_locations': 10,
                }
            )
            
            if company_created:
                # Créer les paramètres de l'entreprise
                CompanySettings.objects.create(company=company)
                print(f"✅ Entreprise 'TEST1234' créée.")
            else:
                print(f"✅ Entreprise 'TEST1234' trouvée (déjà existante).")
            
            print()
            print("=" * 70)
            print("🎉 CONFIGURATION TERMINÉE AVEC SUCCÈS !")
            print("=" * 70)
            print()
            print("📋 INFORMATIONS DE CONNEXION :")
            print(f"   🌐 URL : http://localhost:8001/login/")
            print(f"   👤 Nom d'utilisateur : {username}")
            print(f"   🔐 Mot de passe : {password}")
            print()
            print("🏢 INFORMATIONS DE L'ENTREPRISE :")
            print(f"   📝 Nom : {company.name}")
            print(f"   🔖 Référence : {company.reference}")
            print(f"   📧 Email : {company.email}")
            print()
            print("👤 TYPE DE COMPTE :")
            print(f"   ✅ Propriétaire de l'application (Owner)")
            print(f"   ✅ Peut gérer toutes les entreprises")
            print(f"   ✅ Peut créer/supprimer des entreprises")
            print(f"   ✅ Accès complet au système")
            print()
            print("=" * 70)
            print()
            print("🚀 PROCHAINES ÉTAPES :")
            print("1. Démarrer le serveur : python manage.py runserver 8001")
            print("2. Se connecter avec les identifiants ci-dessus")
            print("3. Créer et gérer vos entreprises")
            print()
            
            return True
            
    except Exception as e:
        print(f"❌ Erreur lors de la configuration : {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Fonction principale"""
    
    success = setup_user_and_company()
    
    if not success:
        print("❌ Échec de la configuration.")
        sys.exit(1)

if __name__ == "__main__":
    main()



