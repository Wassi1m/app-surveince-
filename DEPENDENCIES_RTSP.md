# 📦 DÉPENDANCES RTSP - SURVEILLANCE IA

**Date :** 2 Janvier 2026  
**Version :** 1.0

---

## 🎯 BIBLIOTHÈQUES AJOUTÉES POUR RTSP

### **Nouvelles dépendances dans requirements.txt :**

```txt
# Bibliothèques pour l'intégration RTSP et streaming vidéo
imutils==0.5.4          # Utilitaires pour OpenCV
aiortc==1.14.0          # WebRTC pour streaming avancé
ffmpeg-python==0.2.0    # Interface Python pour FFmpeg
```

### **Dépendances existantes utilisées :**

```txt
opencv-python-headless==4.10.0.84  # Traitement vidéo RTSP
numpy==2.1.1                       # Calculs matriciels pour images
Django==5.2.6                      # Framework web
djangorestframework==3.16.1        # API REST
Pillow==11.3.0                     # Traitement d'images
```

---

## 🔧 INSTALLATION

### **Méthode 1 : Script automatique**
```bash
cd "/home/user/Bureau/app suc"
source venv/bin/activate
./install_rtsp_dependencies.sh
```

### **Méthode 2 : Installation manuelle**
```bash
cd "/home/user/Bureau/app suc"
source venv/bin/activate
pip install -r requirements.txt
```

### **Méthode 3 : Installation individuelle**
```bash
pip install imutils==0.5.4
pip install aiortc==1.14.0
pip install ffmpeg-python==0.2.0
```

---

## 📋 DÉTAIL DES BIBLIOTHÈQUES

### **1. imutils (0.5.4)**
- **Usage :** Utilitaires pour OpenCV
- **Fonctions utilisées :**
  - Redimensionnement d'images
  - Rotation et transformations
  - Optimisations de performance

### **2. aiortc (1.14.0)**
- **Usage :** WebRTC pour streaming avancé
- **Fonctions potentielles :**
  - Streaming bidirectionnel
  - Codec vidéo optimisés
  - Réduction de latence

### **3. ffmpeg-python (0.2.0)**
- **Usage :** Interface Python pour FFmpeg
- **Fonctions potentielles :**
  - Conversion de formats vidéo
  - Optimisation des codecs
  - Traitement audio/vidéo

### **4. opencv-python-headless (4.10.0.84)**
- **Usage :** Traitement vidéo RTSP (déjà installé)
- **Fonctions utilisées :**
  - `cv2.VideoCapture()` : Connexion RTSP
  - `cv2.putText()` : Overlay de texte
  - `cv2.resize()` : Redimensionnement
  - `cv2.imencode()` : Encodage JPEG

---

## 🧪 TESTS DE VALIDATION

### **Test 1 : Imports Python**
```python
import cv2          # OpenCV
import numpy        # NumPy
import imutils      # Utilitaires
import aiortc       # WebRTC
import ffmpeg       # FFmpeg
```

### **Test 2 : Connexion RTSP**
```python
import cv2
cap = cv2.VideoCapture('rtsp://197.2.23.47:554/media/video1')
print("Connexion:", cap.isOpened())
```

### **Test 3 : Traitement de frame**
```python
ret, frame = cap.read()
if ret:
    print(f"Frame: {frame.shape}")
```

---

## ⚠️ DÉPENDANCES SYSTÈME

### **Ubuntu/Debian :**
```bash
sudo apt update
sudo apt install -y python3-opencv
sudo apt install -y ffmpeg
sudo apt install -y libavformat-dev libavcodec-dev
```

### **CentOS/RHEL :**
```bash
sudo yum install -y opencv-python
sudo yum install -y ffmpeg-devel
```

---

## 🔍 VÉRIFICATION D'INSTALLATION

### **Script de vérification :**
```bash
python -c "
import cv2, numpy, imutils, aiortc
print('✅ Toutes les dépendances sont installées')
print(f'OpenCV: {cv2.__version__}')
print(f'NumPy: {numpy.__version__}')
"
```

### **Test de streaming :**
```bash
cd "/home/user/Bureau/app suc"
source venv/bin/activate
python manage.py shell -c "
from monitoring.views import generate_frames
frames = generate_frames(174)
print('✅ Générateur de frames fonctionnel')
"
```

---

## 📊 TAILLES DES PACKAGES

| **Package** | **Taille approximative** |
|-------------|---------------------------|
| opencv-python-headless | ~40 MB |
| numpy | ~15 MB |
| imutils | ~1 MB |
| aiortc | ~5 MB |
| ffmpeg-python | ~1 MB |
| **Total ajouté** | **~7 MB** |

---

## 🚨 RÉSOLUTION DE PROBLÈMES

### **Erreur : "No module named 'cv2'"**
```bash
pip uninstall opencv-python opencv-python-headless
pip install opencv-python-headless==4.10.0.84
```

### **Erreur : "RTSP connection failed"**
- Vérifier la connectivité réseau
- Tester avec `ffplay rtsp://197.2.23.47:554/media/video1`
- Vérifier les paramètres de la caméra

### **Erreur : "Frame encoding failed"**
```bash
pip install --upgrade Pillow numpy
```

### **Performance lente :**
- Réduire la résolution dans `generate_frames()`
- Diminuer les FPS (actuellement 15)
- Optimiser la qualité JPEG (actuellement 85%)

---

## 🔄 MISE À JOUR

### **Commandes de mise à jour :**
```bash
pip install --upgrade opencv-python-headless
pip install --upgrade imutils
pip install --upgrade aiortc
pip install --upgrade ffmpeg-python
```

### **Vérification après mise à jour :**
```bash
./install_rtsp_dependencies.sh
```

---

## ✅ STATUT ACTUEL

- ✅ **opencv-python-headless** : Installé et fonctionnel
- ✅ **imutils** : Installé
- ✅ **aiortc** : Installé  
- ✅ **ffmpeg-python** : Installé
- ✅ **Streaming RTSP** : Opérationnel
- ✅ **Interface web** : Fonctionnelle

**Dernière vérification :** 2 Janvier 2026  
**Statut :** 🟢 TOUTES LES DÉPENDANCES OPÉRATIONNELLES
