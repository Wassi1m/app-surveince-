#!/usr/bin/env python
"""
Script simple pour créer rapidement un compte Owner

Usage:
    python create_owner_simple.py [username] [password]

Exemples:
    python create_owner_simple.py
    python create_owner_simple.py admin password123
    python create_owner_simple.py myowner mypassword
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

def create_owner(username="admin", password="admin123", email=None):
    """Créer un compte owner rapidement"""
    
    if not email:
        email = f"{username}@surveillance.com"
    
    try:
        with transaction.atomic():
            print(f"🏢 Création du compte Owner '{username}'...")
            
            # Créer ou mettre à jour l'utilisateur
            if User.objects.filter(username=username).exists():
                user = User.objects.get(username=username)
                user.set_password(password)
                user.email = email
                user.is_staff = True
                user.is_superuser = True
                user.save()
                print(f"✅ Utilisateur '{username}' mis à jour.")
            else:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name="Owner",
                    last_name="Admin",
                    is_staff=True,
                    is_superuser=True
                )
                print(f"✅ Utilisateur '{username}' créé.")
            
            # Créer le profil CompanyUser Owner
            from companies.models import CompanyUser
            
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
                # Mettre à jour le profil existant
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
            
            print()
            print("🎉 COMPTE OWNER CRÉÉ AVEC SUCCÈS !")
            print("=" * 50)
            print("📋 Informations de connexion :")
            print(f"   🌐 URL : http://localhost:8001/login/")
            print(f"   👤 Utilisateur : {username}")
            print(f"   🔐 Mot de passe : {password}")
            print(f"   📧 Email : {email}")
            print(f"   🏢 Référence entreprise : (laisser vide)")
            print("=" * 50)
            
            return True
            
    except Exception as e:
        print(f"❌ Erreur lors de la création : {e}")
        return False

def main():
    """Fonction principale"""
    
    # Récupérer les arguments de la ligne de commande
    username = sys.argv[1] if len(sys.argv) > 1 else "admin"
    password = sys.argv[2] if len(sys.argv) > 2 else "admin123"
    
    print("🚀 CRÉATION RAPIDE D'UN COMPTE OWNER")
    print("=" * 50)
    
    success = create_owner(username, password)
    
    if success:
        print()
        print("🎯 PROCHAINES ÉTAPES :")
        print("1. Démarrer le serveur : python manage.py runserver 8001")
        print("2. Se connecter avec les identifiants ci-dessus")
        print("3. Créer vos entreprises depuis l'interface Owner")
        print()
    else:
        print("❌ Échec de la création du compte Owner.")
        sys.exit(1)

if __name__ == "__main__":
    main()
