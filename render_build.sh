#!/usr/bin/env bash
# exit on error
set -o errexit

echo "🚀 Début du déploiement sur Render"

echo "📦 Installation des dépendances..."
pip install --upgrade pip
pip install -r requirements.txt

# Vérifier si les variables d'environnement sont définies
echo "🔍 Vérification des variables d'environnement..."
if [ -z "$SECRET_KEY" ]; then
    echo "⚠️ SECRET_KEY non définie, utilisation de la valeur par défaut"
    export SECRET_KEY="django-insecure-default-key-for-render-deployment-change-me"
fi

if [ -z "$DATABASE_URL" ]; then
    echo "⚠️ DATABASE_URL non définie, utilisation de SQLite"
    export DATABASE_URL="sqlite:///db.sqlite3"
fi

echo "🗃️ Application des migrations..."
python manage.py migrate --settings=surveillance_system.settings_production

echo "🎭 Création du superutilisateur..."
python manage.py shell --settings=surveillance_system.settings_production << EOF
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@surveillance.com', 'AdminRender2024!')
    print("✅ Superutilisateur créé: admin / AdminRender2024!")
else:
    print("ℹ️ Superutilisateur existe déjà")
EOF

echo "📊 Chargement des données de démonstration..."
python create_demo_data.py --settings=surveillance_system.settings_production || {
    echo "⚠️ Erreur lors du chargement des données de démonstration, poursuite du déploiement..."
}

echo "🎨 Collection des fichiers statiques..."
python manage.py collectstatic --noinput --settings=surveillance_system.settings_production

echo "✅ Build terminé avec succès !" 