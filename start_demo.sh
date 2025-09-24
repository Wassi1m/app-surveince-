#!/bin/bash

# Script de démarrage de l'application de surveillance avec données de démonstration
echo "🚀 Démarrage du Système de Surveillance Intelligente"
echo "=================================================="

# Activation de l'environnement virtuel
echo "📦 Activation de l'environnement virtuel..."
source surveillance_env/bin/activate

# Vérifier si Redis est lancé
echo "🔍 Vérification de Redis..."
redis-cli ping > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Redis est actif"
else
    echo "⚠️  Redis n'est pas actif. Vous devrez le lancer manuellement:"
    echo "   redis-server"
fi

# Appliquer les migrations si nécessaire
echo "🗃️  Application des migrations..."
python manage.py migrate --verbosity=0

# Créer les données de démonstration
echo "📊 Création des données de démonstration..."
python create_demo_data.py

echo ""
echo "🎯 Application prête!"
echo "===================="
echo ""
echo "🌐 URL d'accès:"
echo "   • Interface principale : http://127.0.0.1:8000/"
echo "   • Administration Django : http://127.0.0.1:8000/admin/"
echo ""
echo "🔐 Comptes de connexion:"
echo "   • Admin     : admin / admin123"
echo "   • Sécurité  : security / security123"
echo "   • Manager   : manager / manager123"
echo ""
echo "📋 Fonctionnalités disponibles:"
echo "   • 📊 Tableau de bord avec surveillance live"
echo "   • 🚨 Centre d'alertes en temps réel"
echo "   • 📈 Analytics et rapports"
echo "   • 📹 Gestion des caméras"
echo "   • ⚙️  Configuration des règles d'alerte"
echo ""
echo "🚀 Démarrage du serveur de développement..."
echo "   (Ctrl+C pour arrêter)"
echo ""

# Démarrer le serveur Django
python manage.py runserver 0.0.0.0:8000 