#!/usr/bin/env python
"""
Script pour changer le mot de passe d'un utilisateur

Usage:
    python change_password.py [username] [new_password]

Exemples:
    python change_password.py
    python change_password.py newowner StrongPassword123!!
    python change_password.py admin newpassword123
"""

import os
import sys
import django
from django.contrib.auth import get_user_model

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'surveillance_system.settings')
django.setup()

User = get_user_model()

def change_password(username, new_password):
    """Changer le mot de passe d'un utilisateur"""
    
    try:
        print(f"🔐 Changement du mot de passe pour l'utilisateur '{username}'...")
        
        # Vérifier si l'utilisateur existe
        if not User.objects.filter(username=username).exists():
            print(f"❌ Erreur : L'utilisateur '{username}' n'existe pas.")
            return False
        
        # Récupérer l'utilisateur
        user = User.objects.get(username=username)
        
        # Changer le mot de passe
        user.set_password(new_password)
        user.save()
        
        print(f"✅ Mot de passe changé avec succès pour l'utilisateur '{username}'!")
        print()
        print("=" * 60)
        print("📋 Nouveaux identifiants de connexion :")
        print(f"   👤 Utilisateur : {username}")
        print(f"   🔐 Nouveau mot de passe : {new_password}")
        
        # Afficher les informations de l'entreprise si applicable
        if hasattr(user, 'company_profile'):
            company_profile = user.company_profile
            if company_profile.company:
                print(f"   🏢 Entreprise : {company_profile.company.name} ({company_profile.company.reference})")
            else:
                print(f"   🏢 Entreprise : Propriétaire de l'application")
            print(f"   👥 Rôle : {company_profile.get_role_display()}")
        
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du changement de mot de passe : {e}")
        return False

def main():
    """Fonction principale"""
    
    # Récupérer les arguments de la ligne de commande
    if len(sys.argv) < 3:
        print("🚀 CHANGEMENT DE MOT DE PASSE")
        print("=" * 60)
        
        if len(sys.argv) > 1:
            username = sys.argv[1]
            print(f"❌ Erreur : Veuillez fournir le nouveau mot de passe.")
            print(f"\nUsage: python change_password.py <username> <new_password>")
            print(f"\nExemple: python change_password.py {username} StrongPassword123!!")
        else:
            print("❌ Erreur : Arguments manquants.")
            print("\nUsage: python change_password.py <username> <new_password>")
            print("\nExemples:")
            print("  python change_password.py newowner StrongPassword123!!")
            print("  python change_password.py admin newpassword123")
        
        sys.exit(1)
    
    username = sys.argv[1]
    new_password = sys.argv[2]
    
    print("🚀 CHANGEMENT DE MOT DE PASSE")
    print("=" * 60)
    
    success = change_password(username, new_password)
    
    if success:
        print()
        print("🎯 PROCHAINES ÉTAPES :")
        print("1. Vous pouvez maintenant vous connecter avec le nouveau mot de passe")
        print("2. URL de connexion : http://localhost:8001/login/")
        print()
    else:
        print("❌ Échec du changement de mot de passe.")
        sys.exit(1)

if __name__ == "__main__":
    main()

