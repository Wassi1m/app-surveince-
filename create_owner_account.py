#!/usr/bin/env python
"""
Script pour créer un compte Owner dans le système de surveillance

Usage:
    python create_owner_account.py

Ce script crée un utilisateur avec les privilèges Owner pour gérer toutes les entreprises.
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

def create_owner_account():
    """Créer un compte owner avec interaction utilisateur"""
    
    print("=" * 60)
    print("🏢 CRÉATION D'UN COMPTE OWNER")
    print("=" * 60)
    print()
    
    # Demander les informations
    print("📝 Veuillez saisir les informations du compte Owner :")
    print()
    
    username = input("👤 Nom d'utilisateur : ").strip()
    if not username:
        print("❌ Le nom d'utilisateur est requis.")
        return False
    
    email = input("📧 Email : ").strip()
    if not email:
        print("❌ L'email est requis.")
        return False
    
    first_name = input("👨 Prénom : ").strip()
    last_name = input("👩 Nom de famille : ").strip()
    
    print()
    password = input("🔐 Mot de passe : ").strip()
    if not password:
        print("❌ Le mot de passe est requis.")
        return False
    
    password_confirm = input("🔐 Confirmer le mot de passe : ").strip()
    if password != password_confirm:
        print("❌ Les mots de passe ne correspondent pas.")
        return False
    
    print()
    print("📋 Récapitulatif :")
    print(f"   👤 Utilisateur : {username}")
    print(f"   📧 Email : {email}")
    print(f"   👨 Prénom : {first_name}")
    print(f"   👩 Nom : {last_name}")
    print()
    
    confirm = input("✅ Confirmer la création ? (o/N) : ").strip().lower()
    if confirm not in ['o', 'oui', 'y', 'yes']:
        print("❌ Création annulée.")
        return False
    
    try:
        with transaction.atomic():
            # Vérifier si l'utilisateur existe déjà
            if User.objects.filter(username=username).exists():
                print(f"⚠️  L'utilisateur '{username}' existe déjà.")
                update = input("🔄 Mettre à jour vers Owner ? (o/N) : ").strip().lower()
                if update not in ['o', 'oui', 'y', 'yes']:
                    print("❌ Opération annulée.")
                    return False
                
                user = User.objects.get(username=username)
                user.email = email
                user.first_name = first_name
                user.last_name = last_name
                user.set_password(password)
                user.is_staff = True
                user.is_superuser = True
                user.save()
                
                print(f"🔄 Utilisateur '{username}' mis à jour.")
                
            else:
                # Créer le nouvel utilisateur
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    is_staff=True,
                    is_superuser=True
                )
                print(f"✅ Utilisateur '{username}' créé avec succès.")
            
            # Créer ou mettre à jour le profil CompanyUser
            from companies.models import CompanyUser
            
            company_user, created = CompanyUser.objects.get_or_create(
                user=user,
                defaults={
                    'role': 'owner',
                    'is_active': True,
                    'company': None,  # Owner n'appartient à aucune entreprise spécifique
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
                print(f"🔄 Profil Owner mis à jour pour '{username}'.")
            else:
                print(f"✅ Profil Owner créé pour '{username}'.")
            
            print()
            print("🎉 COMPTE OWNER CRÉÉ AVEC SUCCÈS !")
            print("=" * 60)
            print("📋 Informations de connexion :")
            print(f"   🌐 URL : http://localhost:8001/login/")
            print(f"   👤 Utilisateur : {username}")
            print(f"   🔐 Mot de passe : {password}")
            print(f"   🏢 Référence entreprise : (laisser vide pour Owner)")
            print("=" * 60)
            print()
            print("🚀 Vous pouvez maintenant vous connecter et gérer les entreprises !")
            
            return True
            
    except Exception as e:
        print(f"❌ Erreur lors de la création : {e}")
        return False

def create_quick_owner():
    """Créer rapidement un compte owner par défaut"""
    
    print("⚡ CRÉATION RAPIDE D'UN COMPTE OWNER")
    print("=" * 50)
    
    username = "admin"
    email = "admin@surveillance.com"
    password = "admin123"
    
    try:
        with transaction.atomic():
            # Vérifier si l'utilisateur existe déjà
            if User.objects.filter(username=username).exists():
                user = User.objects.get(username=username)
                user.set_password(password)
                user.is_staff = True
                user.is_superuser = True
                user.save()
                print(f"🔄 Utilisateur '{username}' mis à jour.")
            else:
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name="Admin",
                    last_name="Owner",
                    is_staff=True,
                    is_superuser=True
                )
                print(f"✅ Utilisateur '{username}' créé.")
            
            # Créer le profil Owner
            from companies.models import CompanyUser
            
            company_user, created = CompanyUser.objects.get_or_create(
                user=user,
                defaults={
                    'role': 'owner',
                    'is_active': True,
                    'company': None,
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
            
            print("✅ Profil Owner configuré.")
            print()
            print("🎉 COMPTE OWNER CRÉÉ !")
            print(f"   👤 Utilisateur : {username}")
            print(f"   🔐 Mot de passe : {password}")
            print(f"   📧 Email : {email}")
            
            return True
            
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return False

def main():
    """Fonction principale"""
    
    print()
    print("🏢 SCRIPT DE CRÉATION DE COMPTE OWNER")
    print("=" * 60)
    print()
    print("Choisissez une option :")
    print("1. 📝 Création interactive (recommandé)")
    print("2. ⚡ Création rapide (admin/admin123)")
    print("3. ❌ Annuler")
    print()
    
    choice = input("Votre choix (1-3) : ").strip()
    
    if choice == "1":
        print()
        success = create_owner_account()
    elif choice == "2":
        print()
        success = create_quick_owner()
    elif choice == "3":
        print("❌ Opération annulée.")
        return
    else:
        print("❌ Choix invalide.")
        return
    
    if success:
        print()
        print("🎯 PROCHAINES ÉTAPES :")
        print("1. 🚀 Démarrer le serveur : python manage.py runserver 8001")
        print("2. 🌐 Ouvrir : http://localhost:8001/login/")
        print("3. 🏢 Se connecter avec les identifiants Owner")
        print("4. ✨ Créer vos premières entreprises !")
        print()

if __name__ == "__main__":
    main()
