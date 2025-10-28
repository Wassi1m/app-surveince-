#!/usr/bin/env python
"""
Script pour créer un utilisateur owner (propriétaire de l'application)
"""
import os
import sys
import django

# Configuration de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'surveillance_system.settings')
django.setup()

from django.contrib.auth.models import User
from companies.models import CompanyUser
import getpass


def create_owner_user():
    """Créer un utilisateur owner"""
    print("=== Création d'un utilisateur Owner ===")
    print("Le propriétaire de l'application peut créer et gérer toutes les entreprises.")
    print()
    
    # Vérifier s'il existe déjà un owner
    existing_owners = CompanyUser.objects.filter(role='owner')
    if existing_owners.exists():
        print("⚠️  Un ou plusieurs utilisateurs owner existent déjà:")
        for owner in existing_owners:
            print(f"   - {owner.user.username} ({owner.user.email})")
        
        response = input("\nVoulez-vous créer un autre owner ? (o/N): ").lower()
        if response not in ['o', 'oui', 'y', 'yes']:
            print("Annulé.")
            return
    
    # Collecter les informations
    print("\n📝 Informations de l'utilisateur owner:")
    
    while True:
        username = input("Nom d'utilisateur: ").strip()
        if not username:
            print("❌ Le nom d'utilisateur est requis.")
            continue
        
        if User.objects.filter(username=username).exists():
            print("❌ Ce nom d'utilisateur existe déjà.")
            continue
        
        break
    
    while True:
        email = input("Email: ").strip()
        if not email:
            print("❌ L'email est requis.")
            continue
        
        if User.objects.filter(email=email).exists():
            print("❌ Cet email existe déjà.")
            continue
        
        break
    
    first_name = input("Prénom (optionnel): ").strip()
    last_name = input("Nom (optionnel): ").strip()
    
    while True:
        password = getpass.getpass("Mot de passe: ")
        if len(password) < 8:
            print("❌ Le mot de passe doit contenir au moins 8 caractères.")
            continue
        
        password_confirm = getpass.getpass("Confirmer le mot de passe: ")
        if password != password_confirm:
            print("❌ Les mots de passe ne correspondent pas.")
            continue
        
        break
    
    # Créer l'utilisateur
    try:
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # Créer le profil CompanyUser
        company_user = CompanyUser.objects.create(
            user=user,
            role='owner',
            company=None,  # Les owners n'appartiennent à aucune entreprise spécifique
            can_manage_users=True,
            can_manage_cameras=True,
            can_manage_alerts=True,
            can_view_reports=True
        )
        
        print(f"\n✅ Utilisateur owner créé avec succès!")
        print(f"   Nom d'utilisateur: {username}")
        print(f"   Email: {email}")
        print(f"   Nom complet: {user.get_full_name() or 'Non défini'}")
        print()
        print("🔐 Connexion:")
        print("   1. Allez sur /companies/login/")
        print("   2. Utilisez n'importe quelle référence d'entreprise (elle sera ignorée)")
        print("   3. Connectez-vous avec vos identifiants")
        print("   4. Vous serez redirigé vers le dashboard owner")
        print()
        print("📋 Prochaines étapes:")
        print("   1. Créer des entreprises via le dashboard owner")
        print("   2. Chaque entreprise aura un manager avec des identifiants générés")
        print("   3. Les managers pourront créer des comptes employés")
        
    except Exception as e:
        print(f"❌ Erreur lors de la création: {e}")
        return


def list_owners():
    """Lister tous les utilisateurs owner"""
    owners = CompanyUser.objects.filter(role='owner').select_related('user')
    
    if not owners.exists():
        print("Aucun utilisateur owner trouvé.")
        return
    
    print("=== Utilisateurs Owner ===")
    for owner in owners:
        user = owner.user
        print(f"• {user.username} ({user.email})")
        if user.get_full_name():
            print(f"  Nom: {user.get_full_name()}")
        print(f"  Créé le: {user.date_joined.strftime('%d/%m/%Y %H:%M')}")
        print(f"  Dernière connexion: {user.last_login.strftime('%d/%m/%Y %H:%M') if user.last_login else 'Jamais'}")
        print()


def main():
    """Menu principal"""
    while True:
        print("\n=== Gestion des utilisateurs Owner ===")
        print("1. Créer un utilisateur owner")
        print("2. Lister les utilisateurs owner")
        print("3. Quitter")
        
        choice = input("\nVotre choix (1-3): ").strip()
        
        if choice == '1':
            create_owner_user()
        elif choice == '2':
            list_owners()
        elif choice == '3':
            print("Au revoir!")
            break
        else:
            print("❌ Choix invalide.")


if __name__ == '__main__':
    main()
