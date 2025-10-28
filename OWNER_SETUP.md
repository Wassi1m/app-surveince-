# 🏢 Configuration du Compte Owner

Ce guide explique comment créer un compte Owner pour gérer le système de surveillance multi-entreprises.

## 📋 Prérequis

1. **Environnement virtuel activé** :
   ```bash
   source venv/bin/activate
   ```

2. **Base de données migrée** :
   ```bash
   python manage.py migrate
   ```

## 🚀 Méthodes de Création

### 1. Script Simple (Recommandé)

**Création rapide avec paramètres par défaut :**
```bash
python create_owner_simple.py
```
- Utilisateur : `admin`
- Mot de passe : `admin123`
- Email : `admin@surveillance.com`

**Création avec paramètres personnalisés :**
```bash
python create_owner_simple.py [username] [password]
```

**Exemples :**
```bash
python create_owner_simple.py owner mypassword
python create_owner_simple.py surveillance_admin secure123
```

### 2. Script Interactif (Complet)

**Création avec interface interactive :**
```bash
python create_owner_account.py
```

Ce script vous demandera :
- Nom d'utilisateur
- Email
- Prénom et nom
- Mot de passe (avec confirmation)

## 🔐 Connexion Owner

1. **Démarrer le serveur :**
   ```bash
   python manage.py runserver 8001
   ```

2. **Accéder à la page de connexion :**
   ```
   http://localhost:8001/login/
   ```

3. **Se connecter avec :**
   - **Utilisateur :** `admin` (ou votre nom d'utilisateur)
   - **Mot de passe :** `admin123` (ou votre mot de passe)
   - **Référence entreprise :** *(laisser vide pour Owner)*

## 🎯 Fonctionnalités Owner

Une fois connecté en tant qu'Owner, vous pouvez :

### 📊 Dashboard Owner
- Vue d'ensemble de toutes les entreprises
- Statistiques globales du système
- Gestion centralisée

### 🏢 Gestion des Entreprises
- **Créer** de nouvelles entreprises
- **Configurer** les paramètres d'entreprise
- **Gérer** les managers d'entreprise
- **Activer/Désactiver** les entreprises

### 👥 Gestion des Utilisateurs
- Voir tous les utilisateurs du système
- Gérer les rôles et permissions
- Réinitialiser les mots de passe

### 📢 Notifications Globales
- Envoyer des notifications à toutes les entreprises
- Cibler des entreprises spécifiques
- Gérer l'historique des notifications

### ⚙️ Types d'Événements
- Configurer les types d'événements détectables
- Assigner des types à des entreprises
- Personnaliser les paramètres de détection

## 🔧 Dépannage

### Problème : "Utilisateur déjà existant"
```bash
# Mettre à jour un utilisateur existant vers Owner
python create_owner_simple.py existing_username new_password
```

### Problème : "Erreur de base de données"
```bash
# Vérifier les migrations
python manage.py showmigrations
python manage.py migrate
```

### Problème : "Module non trouvé"
```bash
# Vérifier l'environnement virtuel
source venv/bin/activate
pip install -r requirements.txt
```

## 📝 Notes Importantes

1. **Sécurité :** Changez le mot de passe par défaut en production
2. **Accès :** L'Owner a accès à TOUTES les données de TOUTES les entreprises
3. **Sauvegarde :** Sauvegardez régulièrement la base de données
4. **Logs :** Surveillez les logs pour les activités suspectes

## 🎉 Prochaines Étapes

Après avoir créé votre compte Owner :

1. **Connectez-vous** à l'interface web
2. **Créez votre première entreprise** depuis le dashboard Owner
3. **Configurez les types d'événements** pour l'IA
4. **Invitez les managers** d'entreprise
5. **Configurez les notifications** globales

## 📞 Support

Si vous rencontrez des problèmes :
1. Vérifiez les logs : `logs/surveillance.log`
2. Consultez la documentation Django
3. Vérifiez la configuration de la base de données

---

**🚀 Bon déploiement !**
