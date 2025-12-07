# 1. Créer les dossiers
ssh ubuntu@51.75.253.11
cd /var/www/surveillance-ia

sudo mkdir -p /var/www/surveillance-ia/media/employees_cibles

# 2. Créer l'utilisateur et le groupe (si nécessaire)
sudo useradd -r -s /bin/false webadmin 2>/dev/null || true
sudo groupadd webadmin 2>/dev/null || true
sudo usermod -a -G webadmin webadmin 2>/dev/null || true

# 3. Fixer les permissions
sudo chmod -R 775 /var/www/surveillance-ia/media
sudo chown -R webadmin:webadmin /var/www/surveillance-ia/media

# 4. Vérifier
ls -ld /var/www/surveillance-ia/media
ls -ld /var/www/surveillance-ia/media/employees_cibles

# 5. Test d'écriture
sudo -u webadmin touch /var/www/surveillance-ia/media/.test_write && sudo rm /var/www/surveillance-ia/media/.test_write && echo "✅ Permissions OK!"