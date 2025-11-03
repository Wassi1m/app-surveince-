# 📚 Documentation du Système d'Historisation

## 🎯 Vue d'ensemble

Le système d'historisation intégré permet de suivre et d'enregistrer automatiquement toutes les actions effectuées dans l'application de surveillance. Il offre une traçabilité complète des modifications, créations, suppressions et connexions des utilisateurs.

## ✨ Fonctionnalités principales

### 🔍 Tracking automatique
- **Créations** : Enregistrement automatique de tous les nouveaux objets
- **Modifications** : Suivi détaillé des champs modifiés avec anciennes/nouvelles valeurs
- **Suppressions** : Historique des objets supprimés
- **Connexions/Déconnexions** : Suivi des sessions utilisateurs
- **Actions système** : Enregistrement des actions automatiques

### 📊 Interface de consultation
- **Tableau de bord** : Vue d'ensemble avec statistiques et graphiques
- **Liste complète** : Historique détaillé avec filtres avancés
- **Détails d'entrée** : Vue complète d'une action spécifique
- **Export** : Possibilité d'exporter l'historique en CSV

### 🎛️ Filtres avancés
- **Par utilisateur** : Voir les actions d'un utilisateur spécifique
- **Par date** : Filtrer par période (date de début/fin)
- **Par action** : Créations, modifications, suppressions, etc.
- **Par catégorie** : Utilisateurs, caméras, zones, localisations, etc.
- **Par localisation** : Actions liées à un lieu spécifique
- **Recherche textuelle** : Recherche dans les descriptions et noms d'objets

## 🚀 Accès à l'interface

### Pour les Managers
1. Connectez-vous à l'application
2. Cliquez sur le menu **"Gestion Équipe"** dans la barre de navigation
3. Sélectionnez **"Historique des Actions"**

### Navigation dans l'interface
- **Tableau de bord** : Vue d'ensemble avec statistiques
- **Historique complet** : Liste détaillée avec filtres
- **Paramètres** : Configuration de l'historisation

## 📋 Types d'actions trackées

| Action | Description | Exemple |
|--------|-------------|---------|
| `create` | Création d'un nouvel objet | Nouvelle caméra ajoutée |
| `update` | Modification d'un objet existant | Changement de statut d'une caméra |
| `delete` | Suppression d'un objet | Suppression d'une zone |
| `login` | Connexion d'un utilisateur | Connexion au système |
| `logout` | Déconnexion d'un utilisateur | Déconnexion du système |
| `view` | Consultation d'un objet | Visualisation d'un rapport |
| `export` | Export de données | Export de l'historique |
| `activate` | Activation d'un élément | Activation d'une alerte |
| `deactivate` | Désactivation d'un élément | Désactivation d'une caméra |

## 🏷️ Catégories d'objets

| Catégorie | Description | Objets concernés |
|-----------|-------------|------------------|
| `user` | Utilisateurs et comptes | Utilisateurs, profils d'entreprise |
| `company` | Entreprises | Entreprises, paramètres d'entreprise |
| `location` | Localisations | Lieux de surveillance |
| `zone` | Zones | Zones de surveillance |
| `camera` | Caméras | Caméras de surveillance |
| `alert` | Alertes | Alertes, règles d'alerte |
| `detection` | Détections | Événements détectés par l'IA |
| `incident` | Incidents | Incidents de sécurité |
| `recording` | Enregistrements | Enregistrements vidéo |
| `settings` | Paramètres | Configurations système |
| `auth` | Authentification | Connexions, déconnexions |
| `notification` | Notifications | Notifications envoyées |

## ⚙️ Configuration

### Paramètres d'historisation

Accessible via **Gestion Équipe > Historique des Actions > Paramètres**

#### 📦 Rétention des données
- **Durée de rétention** : Nombre de jours avant archivage (défaut: 365 jours)
- **Archivage automatique** : Activation/désactivation de l'archivage automatique

#### 👁️ Suivi des actions
- **Traquer les consultations** : Enregistrer les actions de lecture/consultation
- **Traquer les exports** : Enregistrer les exports de données
- **Traquer les actions système** : Enregistrer les actions automatiques

#### 🏷️ Catégories à historiser
Sélection des types d'objets à suivre :
- Utilisateurs
- Entreprises
- Localisations
- Zones
- Caméras
- Alertes
- Détections
- Incidents
- Paramètres

#### 🔔 Notifications
- **Notifier les actions sensibles** : Alertes pour les actions critiques
- **Emails de notification** : Liste des destinataires pour les alertes

## 📊 Utilisation des filtres

### Filtres de base
1. **Utilisateur** : Sélectionner un utilisateur spécifique
2. **Action** : Choisir le type d'action (création, modification, etc.)
3. **Catégorie** : Filtrer par type d'objet
4. **Date de début/fin** : Définir une période

### Filtres avancés
1. **Localisation** : Actions liées à un lieu spécifique
2. **Recherche textuelle** : Recherche dans les descriptions et noms

### Raccourcis clavier
- **Ctrl+F** : Focus sur la recherche textuelle
- **Ctrl+E** : Lancer un export
- **Échap** : Retour à la liste (depuis le détail)

## 📤 Export des données

### Formats disponibles
- **CSV** : Format tableur compatible Excel
- **JSON** : Format de données structurées (à venir)
- **PDF** : Rapport formaté (à venir)
- **Excel** : Format Excel natif (à venir)

### Processus d'export
1. Appliquer les filtres souhaités
2. Cliquer sur **"Exporter"**
3. Le fichier se télécharge automatiquement

## 🔒 Sécurité et permissions

### Accès à l'historique
- **Propriétaires** : Accès complet à tous les historiques
- **Managers** : Accès à l'historique de leur entreprise
- **Employés** : Pas d'accès par défaut

### Données sensibles
- Certaines actions sont marquées comme "sensibles"
- Les données sensibles peuvent déclencher des notifications
- Masquage automatique des informations critiques

### Intégrité des données
- Les entrées d'historique sont en lecture seule
- Seuls les super-administrateurs peuvent supprimer l'historique
- Horodatage automatique et immuable

## 🛠️ Administration technique

### Modèles de données

#### HistoryEntry
Modèle principal stockant chaque action :
- `timestamp` : Date/heure de l'action
- `user` : Utilisateur ayant effectué l'action
- `action` : Type d'action (create, update, delete, etc.)
- `category` : Catégorie d'objet
- `object_name` : Nom de l'objet concerné
- `description` : Description de l'action
- `old_values` / `new_values` : Valeurs avant/après modification
- `changed_fields` : Liste des champs modifiés
- `ip_address` : Adresse IP de l'utilisateur
- `company` : Entreprise associée

#### HistorySettings
Configuration par entreprise :
- `retention_days` : Durée de rétention
- `enabled_categories` : Catégories à traquer
- `notification_emails` : Emails pour les alertes

### Signaux Django
Le système utilise les signaux Django pour le tracking automatique :
- `post_save` : Détection des créations/modifications
- `post_delete` : Détection des suppressions
- `user_logged_in` / `user_logged_out` : Suivi des connexions

### Middleware
- `HistoryMiddleware` : Capture les informations de requête (IP, User-Agent)

## 🚨 Dépannage

### Problèmes courants

#### L'historique ne se remplit pas
1. Vérifier que l'application `history` est dans `INSTALLED_APPS`
2. Vérifier que le middleware `HistoryMiddleware` est activé
3. Contrôler les paramètres d'historisation de l'entreprise

#### Erreurs d'affichage
1. Vérifier que les templates sont correctement chargés
2. Contrôler les permissions utilisateur
3. Vérifier la configuration des filtres de template

#### Performance lente
1. Vérifier les index de base de données
2. Ajuster la durée de rétention
3. Optimiser les requêtes avec `select_related`

### Logs et debug
- Les erreurs d'historisation sont loggées mais ne bloquent pas l'application
- Activer le debug Django pour plus de détails
- Consulter les logs dans `logs/surveillance.log`

## 📈 Bonnes pratiques

### Configuration recommandée
- **Durée de rétention** : 365 jours pour la plupart des entreprises
- **Catégories** : Activer au minimum user, camera, location, zone, alert
- **Notifications** : Configurer pour les actions sensibles uniquement

### Maintenance
- Surveiller la taille de la base de données
- Configurer l'archivage automatique
- Exporter régulièrement les données importantes

### Sécurité
- Limiter l'accès aux managers uniquement
- Configurer les notifications pour les actions critiques
- Auditer régulièrement les accès à l'historique

## 🔄 Évolutions futures

### Fonctionnalités prévues
- **Exports avancés** : PDF, Excel, JSON
- **Graphiques détaillés** : Analyse temporelle, heatmaps
- **Alertes intelligentes** : Détection d'anomalies
- **API REST** : Accès programmatique à l'historique
- **Intégration SIEM** : Export vers systèmes de sécurité
- **Rapports automatiques** : Génération périodique de rapports

### Améliorations techniques
- **Performance** : Optimisation des requêtes
- **Stockage** : Compression des anciennes données
- **Recherche** : Moteur de recherche full-text
- **Temps réel** : Notifications instantanées

---

## 📞 Support

Pour toute question ou problème concernant le système d'historisation :

1. Consulter cette documentation
2. Vérifier les logs d'application
3. Contacter l'administrateur système
4. Utiliser le script de test : `python test_history_system.py`

---

*Documentation mise à jour le 3 novembre 2025*

