#!/bin/bash

echo "🚀 Démarrage de l'application sur Render..."
echo "PORT=$PORT"

# Vérification de l'environnement
echo "DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE"
echo "PYTHONPATH=$PYTHONPATH"

# Essayer d'abord avec Daphne
echo "Tentative de démarrage avec Daphne sur le port $PORT"
daphne -b 0.0.0.0 -p $PORT surveillance_system.asgi:application || {
    echo "⚠️ Échec du démarrage avec Daphne, tentative avec Gunicorn..."
    gunicorn -c gunicorn_config.py surveillance_system.asgi:application
} 