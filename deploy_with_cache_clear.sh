#!/bin/bash

set -e

echo "🚀 === DÉPLOIEMENT SURVEILLANCE IA ROBUSTE === $(date)"

# Variables
APP_DIR="/var/www/surveillance-ia"
VENV_PATH="$APP_DIR/surveillance_env"

echo "📁 Workspace Jenkins: $(pwd)"
echo "👤 Utilisateur Jenkins: $(whoami)"

# Aller dans le dossier de production
cd "$APP_DIR"

echo "🔧 Nettoyage Git et mise à jour forcée..."

# Sauvegarder les modifications locales importantes (si nécessaire)
git add . 2>/dev/null || true
git stash 2>/dev/null || true

# Mise à jour forcée depuis GitHub
git fetch origin
git reset --hard origin/main
git clean -fd

echo "✅ Code mis à jour depuis GitHub"

# ==========================================
# 🧹 BLOC NETTOYAGE CACHE COMPLET
# ==========================================
echo "🧹 === NETTOYAGE CACHE COMPLET ==="

# Supprimer les anciens fichiers statiques
echo "🗑️  Suppression des anciens fichiers statiques..."
rm -rf "$APP_DIR/staticfiles"/* 2>/dev/null || true

# Supprimer le cache Python
echo "🐍 Nettoyage cache Python..."
find "$APP_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$APP_DIR" -name "*.pyc" -delete 2>/dev/null || true

# Générer nouvelle version de cache avec timestamp
NEW_CACHE_VERSION="v$(date +%Y%m%d-%H%M%S)"
echo "🏷️  Nouvelle version cache: $NEW_CACHE_VERSION"

# Mettre à jour la version de cache dans les settings
if [ -f "surveillance_system/settings.py" ]; then
    sed -i "s/CACHE_VERSION = .*/CACHE_VERSION = '$NEW_CACHE_VERSION'/" surveillance_system/settings.py 2>/dev/null || true
    echo "✅ settings.py mis à jour avec version $NEW_CACHE_VERSION"
fi

if [ -f "surveillance_system/settings_production.py" ]; then
    sed -i "s/CACHE_VERSION = .*/CACHE_VERSION = '$NEW_CACHE_VERSION'/" surveillance_system/settings_production.py 2>/dev/null || true
    echo "✅ settings_production.py mis à jour avec version $NEW_CACHE_VERSION"
fi

# Nettoyer le cache Nginx si présent
if [ -d "/var/cache/nginx" ]; then
    echo "🌐 Nettoyage cache Nginx..."
    sudo rm -rf /var/cache/nginx/* 2>/dev/null || true
    echo "✅ Cache Nginx nettoyé"
fi

# Nettoyer le cache système (optionnel)
echo "💾 Nettoyage cache système..."
sudo sync && echo 3 | sudo tee /proc/sys/vm/drop_caches >/dev/null 2>&1 || true

echo "✅ === NETTOYAGE CACHE TERMINÉ ==="
# ==========================================

# Vérifier et corriger l'environnement virtuel avec test plus robuste
echo "🔍 Vérification de l'environnement virtuel..."

# Test plus complet : vérifier pip ET python
VENV_OK=true

if ! "$VENV_PATH/bin/python" --version >/dev/null 2>&1; then
    echo "⚠️ Python défaillant dans l'environnement virtuel"
    VENV_OK=false
fi

if ! "$VENV_PATH/bin/pip" --version >/dev/null 2>&1; then
    echo "⚠️ Pip défaillant dans l'environnement virtuel"
    VENV_OK=false
fi

# Vérifier les chemins dans les scripts
if grep -q "/home/user/Bureau" "$VENV_PATH/bin/pip" 2>/dev/null; then
    echo "⚠️ Chemins incorrects détectés dans l'environnement virtuel"
    VENV_OK=false
fi

if [ "$VENV_OK" = false ]; then
    echo "🔄 Recréation complète de l'environnement virtuel..."
    
    # Sauvegarder requirements.txt
    cp requirements.txt /tmp/requirements_backup.txt
    
    # Supprimer complètement l'ancien environnement
    rm -rf "$VENV_PATH"
    
    # Créer un nouvel environnement virtuel
    python3 -m venv "$VENV_PATH"
    
    # Mettre à jour pip
    "$VENV_PATH/bin/pip" install --upgrade pip
    
    echo "✅ Nouvel environnement virtuel créé"
else
    echo "✅ Environnement virtuel OK"
fi

# Corriger les permissions
echo "🔐 Correction des permissions..."
sudo chown -R jenkins:www-data "$APP_DIR"
sudo chmod -R 755 "$APP_DIR"
sudo chmod -R 775 "$APP_DIR/logs" 2>/dev/null || true

# Installation des dépendances
echo "📦 Installation des dépendances..."
"$VENV_PATH/bin/pip" install -r requirements.txt --quiet

# Django
echo "🗄️ Configuration Django..."
export DJANGO_SETTINGS_MODULE=surveillance_system.settings_production

# Vérifier que Django fonctionne
if ! "$VENV_PATH/bin/python" -c "import django" >/dev/null 2>&1; then
    echo "❌ Problème avec Django, réinstallation..."
    "$VENV_PATH/bin/pip" install Django --quiet
fi

# Migrations
echo "🔄 Migrations Django..."
"$VENV_PATH/bin/python" manage.py migrate --noinput

# Fichiers statiques avec nouvelle version de cache
echo "📁 Collecte des fichiers statiques avec version $NEW_CACHE_VERSION..."
"$VENV_PATH/bin/python" manage.py collectstatic --noinput --clear

# Compter les fichiers statiques collectés
STATIC_FILES_COUNT=$(find "$APP_DIR/staticfiles" -type f 2>/dev/null | wc -l)
echo "✅ $STATIC_FILES_COUNT fichiers statiques collectés"

# Redémarrage des services
echo "🔄 Redémarrage des services..."
sudo systemctl restart surveillance-django
sudo systemctl restart surveillance-websocket

# Recharger Nginx si disponible
if command -v nginx >/dev/null 2>&1; then
    echo "🌐 Rechargement Nginx..."
    sudo nginx -s reload 2>/dev/null || true
    echo "✅ Nginx rechargé"
fi

# Vérification
echo "🔍 Vérification des services..."
sleep 3

if systemctl is-active --quiet surveillance-django; then
    echo "✅ surveillance-django: ACTIF"
else
    echo "❌ surveillance-django: PROBLÈME"
    sudo systemctl status surveillance-django --no-pager
fi

if systemctl is-active --quiet surveillance-websocket; then
    echo "✅ surveillance-websocket: ACTIF"
else
    echo "❌ surveillance-websocket: PROBLÈME"
    sudo systemctl status surveillance-websocket --no-pager
fi

# Test de connectivité
echo "🌐 Test de l'application..."
if curl -s -I http://localhost/ | grep -q "HTTP/1.1"; then
    echo "✅ Application accessible"
else
    echo "⚠️ Problème de connectivité"
fi

# ==========================================
# 📊 RÉSUMÉ FINAL AVEC INFORMATIONS CACHE
# ==========================================
echo ""
echo "📊 === RÉSUMÉ DÉPLOIEMENT ==="
echo "🏷️  Version cache: $NEW_CACHE_VERSION"
echo "📁 Fichiers statiques: $STATIC_FILES_COUNT fichiers"
echo "🕒 Déploiement terminé: $(date)"
echo ""
echo "🎯 Pour forcer le rechargement du cache navigateur:"
echo "   - Appuyez sur Ctrl+F5 (Windows/Linux)"
echo "   - Ou Cmd+Shift+R (Mac)"
echo "   - Ou videz le cache manuellement"
echo ""
# ==========================================

echo "🎉 === DÉPLOIEMENT TERMINÉ === $(date)"
