# 🏢 Système de Sous-entreprises - Documentation Complète

## 📋 Vue d'ensemble

Le système de sous-entreprises permet une gestion hiérarchique et granulaire des organisations au sein de l'application de surveillance. Chaque entreprise peut maintenant être divisée en sous-entreprises avec des managers et employés spécifiques, une isolation complète des données, et des permissions personnalisées.

## 🎯 Fonctionnalités Principales

### ✨ Gestion Hiérarchique
- **Entreprises parentes** : Structure principale existante
- **Sous-entreprises** : Divisions, départements, sites, filiales
- **Sous-entreprise par défaut** : Créée automatiquement lors de la création d'une entreprise
- **Références uniques** : Système de génération automatique (ex: `ABC123-SUB01`)

### 👥 Gestion des Utilisateurs
- **Owners** : Accès global à toutes les entreprises et sous-entreprises
- **Managers** : Accès à toutes les sous-entreprises de leur entreprise
- **Employés** : Accès limité aux sous-entreprises assignées
- **Assignations multiples** : Un utilisateur peut être assigné à plusieurs sous-entreprises
- **Permissions granulaires** : Contrôle précis par sous-entreprise

### 🔒 Isolation des Données
- **Localisations** : Assignées à une sous-entreprise spécifique
- **Caméras** : Héritent de la sous-entreprise de leur localisation
- **Zones** : Liées à la sous-entreprise via leur localisation
- **Alertes** : Isolées par sous-entreprise
- **Historique** : Tracking séparé par sous-entreprise
- **Rapports** : Données filtrées automatiquement

### 🎛️ Interface Utilisateur
- **Sélecteur de sous-entreprise** : Dropdown dans la barre de navigation
- **Assistant de configuration** : Wizard en 5 étapes pour la configuration
- **Tableau de bord adaptatif** : Affichage des données selon la sous-entreprise courante
- **Filtrage automatique** : Toutes les vues respectent l'isolation des données

## 🏗️ Architecture Technique

### 📊 Modèles de Données

#### SubCompany
```python
class SubCompany(models.Model):
    parent_company = models.ForeignKey(Company, ...)
    name = models.CharField(max_length=200)
    reference = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    max_users = models.PositiveIntegerField(default=20)
    max_cameras = models.PositiveIntegerField(default=10)
    max_locations = models.PositiveIntegerField(default=3)
    settings = models.JSONField(default=dict)
```

#### SubCompanyUser (Liaison)
```python
class SubCompanyUser(models.Model):
    company_user = models.ForeignKey(CompanyUser, ...)
    subcompany = models.ForeignKey(SubCompany, ...)
    can_manage_users = models.BooleanField(default=False)
    can_manage_cameras = models.BooleanField(default=False)
    can_manage_alerts = models.BooleanField(default=False)
    can_view_reports = models.BooleanField(default=True)
    can_manage_locations = models.BooleanField(default=False)
    assigned_by = models.ForeignKey(User, ...)
    is_active = models.BooleanField(default=True)
```

#### Modèles Étendus
Tous les modèles principaux ont été étendus avec un champ `subcompany` :
- `Location.subcompany`
- `Alert.subcompany`
- `AlertRule.subcompany`
- `HistoryEntry.subcompany`

### 🔧 Middleware et Utilitaires

#### SubCompanyMiddleware
- Détecte la sous-entreprise courante de l'utilisateur
- Ajoute `request.current_subcompany` et `request.accessible_subcompanies`
- Gère automatiquement la sélection par défaut

#### Utilitaires (companies/utils.py)
- `get_user_data_filters()` : Génère les filtres appropriés selon le rôle
- `get_accessible_locations()` : Retourne les localisations accessibles
- `can_access_subcompany_data()` : Vérifie l'accès aux données
- `get_user_permissions_for_subcompany()` : Récupère les permissions spécifiques

### 🎨 Interface Utilisateur

#### Assistant de Configuration (Wizard)
1. **Étape 1** : Informations de l'entreprise
2. **Étape 2** : Création des sous-entreprises
3. **Étape 3** : Création des managers
4. **Étape 4** : Assignation des managers aux sous-entreprises
5. **Étape 5** : Confirmation et résumé

#### Sélecteur de Sous-entreprise
- Dropdown dans la barre de navigation pour les managers/employés
- Changement en temps réel avec rechargement de page
- Affichage de la sous-entreprise courante
- API AJAX pour le changement (`/companies/api/subcompany-selector/`)

## 🚀 Utilisation

### 👑 Pour les Owners

1. **Créer une entreprise** via le dashboard owner
2. **Lancer l'assistant** depuis le détail de l'entreprise
3. **Configurer les sous-entreprises** selon l'organisation
4. **Créer et assigner les managers** aux sous-entreprises appropriées
5. **Surveiller l'activité** via les rapports globaux

### 👔 Pour les Managers

1. **Sélectionner la sous-entreprise** via le dropdown de navigation
2. **Gérer les employés** de la sous-entreprise courante
3. **Créer des employés** et les assigner automatiquement
4. **Configurer les alertes** spécifiques à la sous-entreprise
5. **Consulter l'historique** filtré par sous-entreprise

### 👷 Pour les Employés

1. **Accès automatique** à la sous-entreprise assignée
2. **Consultation des données** limitées à leur périmètre
3. **Rapports et alertes** filtrés automatiquement
4. **Pas de gestion** des autres utilisateurs ou sous-entreprises

## 🔐 Sécurité et Permissions

### Niveaux d'Accès
- **Owner** : Accès global, toutes permissions
- **Manager** : Accès à son entreprise, permissions configurables par sous-entreprise
- **Employee** : Accès limité aux sous-entreprises assignées, permissions restreintes

### Isolation des Données
- **Filtrage automatique** : Toutes les requêtes sont filtrées par sous-entreprise
- **Vérifications d'accès** : Contrôles systématiques avant affichage des données
- **Sessions sécurisées** : La sous-entreprise courante est stockée en session
- **Audit trail** : Toutes les actions sont tracées avec la sous-entreprise

### Permissions Granulaires
Chaque assignation utilisateur/sous-entreprise peut avoir des permissions spécifiques :
- `can_manage_users` : Gérer les utilisateurs de la sous-entreprise
- `can_manage_cameras` : Gérer les caméras et équipements
- `can_manage_alerts` : Configurer les alertes et règles
- `can_view_reports` : Consulter les rapports et statistiques
- `can_manage_locations` : Gérer les localisations et zones

## 📈 Migration et Compatibilité

### Migration Automatique
- **Sous-entreprises par défaut** créées automatiquement
- **Données existantes** migrées vers les sous-entreprises par défaut
- **Utilisateurs existants** assignés automatiquement
- **Références générées** pour toutes les sous-entreprises

### Rétrocompatibilité
- **Ancien système** continue de fonctionner
- **Filtrage par entreprise** maintenu en fallback
- **Pas de rupture** dans les fonctionnalités existantes
- **Migration progressive** possible

## 🛠️ Configuration

### Variables d'Environnement
Aucune nouvelle variable requise. Le système utilise la configuration Django existante.

### Middleware
Ajout requis dans `settings.py` :
```python
MIDDLEWARE = [
    # ... middleware existants
    'companies.subcompany_middleware.SubCompanyMiddleware',
    # ... autres middleware
]
```

### URLs
Nouvelles routes ajoutées :
- `/companies/subcompany-wizard/<company_id>/` : Assistant de configuration
- `/companies/subcompanies/<company_id>/` : Liste des sous-entreprises
- `/companies/api/subcompany-selector/` : API de changement de sous-entreprise

## 📊 Statistiques et Monitoring

### Métriques Disponibles
- Nombre de sous-entreprises par entreprise
- Utilisateurs assignés par sous-entreprise
- Données (localisations, caméras, alertes) par sous-entreprise
- Activité (historique) par sous-entreprise

### Rapports
- **Dashboard owner** : Vue globale de toutes les sous-entreprises
- **Dashboard manager** : Vue filtrée par sous-entreprise courante
- **Historique** : Tracking complet des actions par sous-entreprise
- **Alertes** : Isolation complète par sous-entreprise

## 🔧 Maintenance

### Tâches Régulières
- **Nettoyage des assignations** inactives
- **Vérification de l'intégrité** des références
- **Audit des permissions** par sous-entreprise
- **Archivage des données** anciennes par sous-entreprise

### Dépannage
- **Utilisateur sans sous-entreprise** : Assignation automatique à la première accessible
- **Données orphelines** : Scripts de migration disponibles
- **Permissions manquantes** : Réassignation via l'interface admin
- **Références dupliquées** : Régénération automatique

## 🎉 Avantages

### Pour l'Organisation
- **Séparation claire** des responsabilités
- **Gestion décentralisée** mais contrôlée
- **Évolutivité** : Ajout facile de nouvelles divisions
- **Flexibilité** : Permissions adaptables selon les besoins

### Pour les Utilisateurs
- **Interface intuitive** avec sélecteur de contexte
- **Données pertinentes** : Affichage filtré automatiquement
- **Sécurité renforcée** : Accès limité au périmètre autorisé
- **Performance** : Requêtes optimisées par filtrage

### Pour les Développeurs
- **Code modulaire** : Utilitaires réutilisables
- **Filtrage automatique** : Pas de modification des vues existantes
- **Extensibilité** : Ajout facile de nouveaux modèles
- **Tests complets** : Validation de tous les scénarios

## 📞 Support

Pour toute question ou problème :
1. Consulter cette documentation
2. Vérifier les logs de l'application
3. Utiliser les scripts de diagnostic fournis
4. Contacter l'équipe de développement

---

**Version** : 1.0  
**Date** : Novembre 2025  
**Statut** : ✅ Opérationnel et testé
