cat > /var/www/surveillance-ia/CORRECTION_ERREUR_500.md << 'EOF'
# 🔧 CORRECTION ERREUR 500 - SURVEILLANCE IA

**Date de correction :** 5 Novembre 2025  
**Problème résolu :** Erreur 500 "User has no company_profile"

---

## 🔐 ACCÈS OWNER CRÉÉ

### Informations de connexion

| **Champ** | **Valeur** |
|-----------|------------|
| 🌐 **URL** | `http://51.75.253.11:8090/` |
| 👤 **Nom d'utilisateur** | `admin` |
| 🔐 **Mot de passe** | `admin123` |
| 📧 **Email** | `admin@surveillance.local` |
| 🏢 **Entreprise** | `Surveillance IA Corp` |
| 🆔 **Référence entreprise** | `SURV001` |
| 👔 **Rôle** | `owner` (Propriétaire) |
| 🆔 **ID Employé** | `EMP001` |
| 🏢 **Département** | `Administration` |
| 💼 **Poste** | `Directeur Général` |

### Permissions du compte Owner

✅ **Toutes les permissions activées :**
- can_manage_users : Gérer les utilisateurs
- can_manage_cameras : Gérer les caméras  
- can_manage_alerts : Gérer les alertes
- can_view_reports : Voir les rapports

---

## ✅ SOLUTIONS APPLIQUÉES

### 1. Correction de l'ordre des middlewares

**Fichier modifié :** surveillance_system/settings_production.py

Le MessageMiddleware a été placé AVANT CompanyMiddleware pour éviter l'erreur.

### 2. Création de l'entreprise et du profil utilisateur

**Commandes PostgreSQL exécutées :**

```sql
-- 1. Créer l'entreprise
INSERT INTO companies_company (
    name, reference, description, address, phone, email, website, 
    is_active, max_users, max_cameras, max_locations, settings, 
    created_at, updated_at
) VALUES (
    'Surveillance IA Corp', 
    'SURV001', 
    'Entreprise principale de surveillance', 
    '123 Rue de la Surveillance', 
    '+33123456789', 
    'contact@surveillance-ia.com', 
    'https://surveillance-ia.com',
    true, 
    100, 
    50, 
    20, 
    '{}',
    NOW(), 
    NOW()
);

-- 2. Créer le profil CompanyUser pour admin
INSERT INTO companies_companyuser (
    user_id, company_id, role, employee_id, department, position, phone,
    is_active, can_manage_users, can_manage_cameras, can_manage_alerts, can_view_reports,
    created_at, updated_at
) 
SELECT 
    u.id, c.id, 'owner', 'EMP001', 'Administration', 'Directeur Général', '+33123456789',
    true, true, true, true, true, NOW(), NOW()
FROM auth_user u, companies_company c
WHERE u.username = 'admin' AND c.reference = 'SURV001';
```

---

## 🛠️ COMMANDES DE VÉRIFICATION

### Vérifier le profil d'entreprise
```bash
sudo -u postgres psql -d surveillance_db -c "
SELECT u.username, cu.role, cu.employee_id, c.name, c.reference 
FROM companies_companyuser cu 
JOIN companies_company c ON cu.company_id = c.id 
JOIN auth_user u ON cu.user_id = u.id 
WHERE u.username = 'admin';
"
```

### Vérifier les services
```bash
sudo systemctl status surveillance-django
sudo systemctl status surveillance-websocket
```

---

## 🎯 PROCHAINES ÉTAPES

1. **Se connecter au système :**
   - Aller sur http://51.75.253.11:8090/
   - Utiliser les identifiants ci-dessus

2. **Configurer l'entreprise :**
   - Ajouter des utilisateurs
   - Configurer les caméras
   - Définir les zones de surveillance

**Dernière mise à jour :** 5 Novembre 2025
EOF