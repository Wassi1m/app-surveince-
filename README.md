# 🚀 Système de Surveillance Intelligente avec IA

Une application web moderne de surveillance utilisant l'intelligence artificielle pour détecter automatiquement les problèmes de sécurité dans les magasins, supermarchés, entrepôts et autres lieux commerciaux.

![Dashboard](static/img/dashboard-preview.png)

## ✨ Fonctionnalités Principales

### 🎯 Détection IA Avancée
- **Détection automatique** : Vol, intrusion, comportements suspects, accidents, incendies
- **Analyse en temps réel** : Traitement vidéo live avec overlay des détections
- **Zones de surveillance configurables** : Définition de zones à risque élevé, moyen, faible
- **Précision ajustable** : Seuils de confiance personnalisables

### 📊 Interface Intuitive
- **Tableau de bord central** : Vue d'ensemble avec flux vidéo principal
- **Multi-caméras** : Grille d'aperçu de plusieurs caméras simultanément
- **Indicateurs visuels** : Encadrés colorés autour des zones détectées
  - 🟢 Vert = Normal
  - 🟠 Orange = Suspect  
  - 🔴 Rouge = Danger confirmé

### 🚨 Système d'Alertes Intelligent
- **Notifications temps réel** : WebSocket pour les alertes instantanées
- **Canaux multiples** : Email, SMS, webhooks, notifications push
- **Règles personnalisables** : Conditions de déclenchement flexibles
- **Escalade automatique** : Priorité critique avec popup d'urgence
- **Sons d'alerte** : Notifications audio configurables

### 📈 Analytics et Rapports
- **Historique intelligent** : Clips vidéo automatiques avant/pendant/après incident
- **Indexation avancée** : Recherche par type, date, zone, gravité
- **Timeline interactive** : Chronologie complète des événements
- **Statistiques détaillées** : Métriques de performance et tendances
- **Carte de chaleur** : Visualisation des zones sensibles
- **Rapports exportables** : Formats compatibles police/assurance

## 🛠️ Architecture Technique

### Technologies Utilisées
- **Backend** : Django 5.2 + Django REST Framework
- **Frontend** : HTML5, CSS3, JavaScript ES6, Bootstrap 5
- **Temps réel** : Django Channels + WebSockets + Redis
- **Vision** : OpenCV pour le traitement vidéo
- **IA/ML** : scikit-learn pour l'analyse des données
- **Base de données** : SQLite (développement) / PostgreSQL (production)

### Structure du Projet
```
surveillance_system/
├── monitoring/          # Gestion des caméras et détections
├── alerts/             # Système d'alertes et notifications  
├── analytics/          # Rapports et statistiques
├── templates/          # Templates HTML
├── static/            # CSS, JS, images
├── media/             # Fichiers uploadés
└── logs/              # Journaux système
```

## 📦 Installation et Configuration

### Prérequis
- Python 3.8+
- Redis Server (pour WebSockets)
- Git

### Installation Rapide

1. **Cloner le projet**
```bash
git clone <repository-url>
cd surveillance_system
```

2. **Créer l'environnement virtuel**
```bash
python3 -m venv surveillance_env
source surveillance_env/bin/activate  # Linux/Mac
# surveillance_env\Scripts\activate   # Windows
```

3. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

4. **Configuration de la base de données**
```bash
python manage.py migrate
```

5. **Créer un superutilisateur**
```bash
python manage.py createsuperuser
```

6. **Démarrer Redis** (requis pour WebSockets)
```bash
redis-server
```

7. **Lancer l'application avec WebSockets**
```bash
# Option 1: Script automatique (RECOMMANDÉ)
./start_surveillance.sh

# Option 2: Manuel avec Daphne (serveur ASGI + WebSockets)
source surveillance_env/bin/activate
daphne -b 127.0.0.1 -p 8001 surveillance_system.asgi:application

# Option 3: Django standard (sans WebSockets temps réel)
python manage.py runserver 8000
```

8. **Accéder à l'application**
- Interface principale : http://localhost:8001/
- Administration : http://localhost:8001/admin/

**⚠️ Important :** Pour les fonctionnalités WebSocket (streaming vidéo temps réel, alertes instantanées), utilisez le script `./start_surveillance.sh` qui démarre l'application avec Daphne.

### Comptes de Démonstration
- **Admin** : admin / admin123
- **Email** : admin@surveillance.local

## 🎮 Guide d'Utilisation

### Configuration Initiale

1. **Créer un lieu de surveillance**
   - Administration → Lieux → Ajouter
   - Nom, adresse, description

2. **Définir les zones**
   - Administration → Zones → Ajouter
   - Coordonnées, niveau de risque

3. **Ajouter des caméras**
   - Interface → Monitoring → Caméras → Créer
   - IP, port, credentials, URL de streaming

4. **Configurer les règles d'alerte**
   - Interface → Alertes → Règles → Créer
   - Types de détection, seuils, destinataires

### Surveillance Live

1. **Tableau de bord principal**
   - Flux vidéo central avec détections IA
   - Grille multi-caméras
   - Alertes temps réel dans le panneau latéral

2. **Interactions**
   - Clic sur alerte → Détails complets
   - Bouton "Accuser réception" → Marquer comme vu
   - Capture d'écran → Sauvegarder l'image
   - Plein écran → Mode immersif

### Analytics et Rapports

1. **Statistiques**
   - Vue globale des détections par type/gravité
   - Évolution temporelle
   - Top caméras/zones actives
   - Précision IA et temps de réponse

2. **Génération de rapports**
   - Quotidiens, hebdomadaires, mensuels
   - Rapports d'incidents spécifiques
   - Export PDF/Excel pour autorités

## 🔧 Configuration Avancée

### Variables d'Environnement
Créer un fichier `.env` :
```
DEBUG=False
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:pass@localhost/surveillance
REDIS_URL=redis://localhost:6379/0
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=alerts@votredomain.com
EMAIL_HOST_PASSWORD=your-app-password
```

### Configuration Caméras RTSP
```python
# Exemple d'URL RTSP
CAMERA_URL = "rtsp://username:password@192.168.1.100:554/stream1"
```

### Règles d'Alerte Avancées
```json
{
  "trigger_type": "detection_type",
  "trigger_conditions": {
    "event_types": ["theft", "weapon"],
    "min_confidence": 0.8,
    "time_windows": [
      {"start": 18, "end": 8}  // 18h-8h
    ]
  }
}
```

## 🚀 Déploiement Production

### Docker (Recommandé)
```bash
# À venir - Dockerfile en préparation
docker-compose up -d
```

### Serveur Linux
```bash
# Utiliser Gunicorn + Nginx
pip install gunicorn
gunicorn surveillance_system.wsgi:application --bind 0.0.0.0:8000

# Configuration Nginx pour proxy reverse
# Voir documentation déploiement complète
```

## 🤝 Contribution

### Structure de Développement
- `monitoring/` : Caméras, zones, détections IA
- `alerts/` : Règles, notifications, canaux
- `analytics/` : Statistiques, rapports, tendances

### Ajout de Nouvelles Fonctionnalités
1. Créer une branche : `git checkout -b feature/nom-fonctionnalite`
2. Développer avec tests
3. Pull Request avec description détaillée

### Tests
```bash
python manage.py test
```

## 📞 Support et Documentation

### Ressources
- **Documentation complète** : `/docs/` (à venir)
- **API Reference** : `/api/docs/` (à venir)
- **Issues GitHub** : Pour bugs et suggestions

### Contact
- **Email** : support@surveillance-ia.com
- **GitHub Issues** : Questions techniques

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 🔮 Roadmap

### Version 1.1
- [ ] Intégration Telegram/Slack
- [ ] App mobile (React Native)
- [ ] Reconnaissance faciale
- [ ] IA prédictive

### Version 1.2  
- [ ] Multi-tenant (SaaS)
- [ ] API RESTful complète
- [ ] Plugins tiers
- [ ] Cloud déployment

---

**🔒 Surveillance Intelligente** - Sécurisez votre activité avec l'IA 