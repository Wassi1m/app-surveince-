#!/bin/bash

echo "🚀 Démarrage du Système de Surveillance Intelligente avec WebSockets"
echo "=================================================================="

echo "📦 Activation de l'environnement virtuel..."
source surveillance_env/bin/activate

echo "🔍 Vérification de Redis..."
redis-cli ping > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Redis est actif"
else
    echo "⚠️  Redis n'est pas actif. Démarrage de Redis..."
    redis-server --daemonize yes
    sleep 2
    redis-cli ping > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✅ Redis démarré avec succès"
    else
        echo "❌ Impossible de démarrer Redis. Vérifiez l'installation."
        echo "   Installation Redis: sudo apt-get install redis-server"
        exit 1
    fi
fi

echo "🗃️  Application des migrations..."
python manage.py migrate --verbosity=0

echo "📊 Mise à jour des données de démonstration..."
python create_demo_data.py > /dev/null 2>&1

echo "🔄 Collecte des fichiers statiques..."
python manage.py collectstatic --noinput --clear > /dev/null 2>&1

echo ""
echo "🎯 Application prête avec WebSockets!"
echo "====================================="
echo ""
echo "🌐 URL d'accès:"
echo "   • Interface principale : http://localhost:8001/"
echo "   • Administration Django : http://localhost:8001/admin/"
echo ""
echo "🔐 Comptes de connexion:"
echo "   • Admin     : admin / admin123"
echo "   • Sécurité  : security / security123"
echo "   • Manager   : manager / manager123"
echo ""
echo "📋 Fonctionnalités WebSocket actives:"
echo "   • 📹 Streaming vidéo en temps réel"
echo "   • 🚨 Alertes instantanées"
echo "   • 📊 Mise à jour du dashboard en direct"
echo "   • 🔔 Notifications push en temps réel"
echo ""
echo "🚀 Démarrage du serveur ASGI (Daphne) avec WebSockets..."
echo "   (Ctrl+C pour arrêter)"
echo ""

# Arrêter tout serveur précédent
pkill -f "daphne" > /dev/null 2>&1
pkill -f "python manage.py runserver" > /dev/null 2>&1
sleep 1

# Démarrer avec Daphne sur localhost pour éviter les problèmes CORS
daphne -b localhost -p 8001 --access-log /dev/stdout surveillance_system.asgi:application 