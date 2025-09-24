# 🚀 Guide de Déploiement sur Render

## 📋 Étapes de Déploiement

### 1. Préparation du Repository

1. **Initialisez Git** (si pas déjà fait) :
```bash
git init
git add .
git commit -m "Initial commit - Surveillance IA System"
```

2. **Poussez sur GitHub** :
```bash
git remote add origin https://github.com/VOTRE-USERNAME/surveillance-ia.git
git branch -M main
git push -u origin main
```

### 2. Configuration sur Render

1. **Allez sur [render.com](https://render.com)** et connectez-vous
2. **Cliquez "New +"** → **"Web Service"**
3. **Connectez votre repository GitHub**
4. **Configuration** :
   - **Name** : `surveillance-ia`
   - **Environment** : `Python 3`
   - **Build Command** : `./build.sh`
   - **Start Command** : `daphne -b 0.0.0.0 -p $PORT surveillance_system.asgi:application`

### 3. Variables d'Environnement

Dans les **Environment Variables** de Render, ajoutez :

```
PYTHON_VERSION=3.12.0
DEBUG=False
SECRET_KEY=GenerezUneCleSecrete123456789!
DJANGO_SETTINGS_MODULE=surveillance_system.settings_production
```

### 4. Base de Données PostgreSQL

1. **Créez une base** : New + → PostgreSQL
2. **Name** : `surveillance-db`
3. **Copiez l'URL** de connexion
4. **Ajoutez** `DATABASE_URL=postgresql://...` dans les variables

### 5. Redis

1. **Créez Redis** : New + → Redis
2. **Name** : `surveillance-redis`
3. **Copiez l'URL** de connexion
4. **Ajoutez** `REDIS_URL=redis://...` dans les variables

### 6. Déploiement

1. **Cliquez "Create Web Service"**
2. **Attendez le build** (5-10 minutes)
3. **URL finale** : `https://surveillance-ia.onrender.com`

## 🔐 Comptes par Défaut

- **Admin** : `admin` / `AdminRender2024!`
- **Sécurité** : `security` / `security123`
- **Manager** : `manager` / `manager123`

## 🎥 Avantages HTTPS

- ✅ **Webcam fonctionne** automatiquement
- ✅ **WebSockets sécurisés** (wss://)
- ✅ **Notifications push** actives
- ✅ **API géolocalisation** disponible
- ✅ **Performance optimisée**

## 📊 URLs Importantes

- **Dashboard** : `https://surveillance-ia.onrender.com/`
- **Admin** : `https://surveillance-ia.onrender.com/admin/`
- **API** : `https://surveillance-ia.onrender.com/api/`

## 🛠️ Debugging

Si problème au déploiement :
1. Vérifiez les logs Render
2. Testez le build localement : `chmod +x build.sh && ./build.sh`
3. Vérifiez les variables d'environnement

## 💰 Coûts Render (Plan Gratuit)

- **Web Service** : Gratuit (750h/mois)
- **PostgreSQL** : Gratuit (1 mois, puis $7/mois)
- **Redis** : Gratuit (30 jours, puis $7/mois)

Total mensuel après période gratuite : **~$14/mois** 