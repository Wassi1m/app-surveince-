/**
 * Surveillance System Main JavaScript
 * Fonctionnalités principales pour l'interface de surveillance
 */

class SurveillanceSystem {
    constructor() {
        this.websockets = {};
        this.isInitialized = false;
        this.config = {
            reconnectInterval: 5000,
            maxReconnectAttempts: 5,
            alertSoundEnabled: true,
            notificationTimeout: 5000
        };
        this.reconnectAttempts = {};
        
        // Initialiser après le chargement du DOM
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }

    /**
     * Initialisation du système
     */
    init() {
        if (this.isInitialized) return;
        
        console.log('🚀 Initialisation du Système de Surveillance');
        
        this.setupEventListeners();
        this.initializeWebSockets();
        this.startPeriodicUpdates();
        this.loadUserPreferences();
        
        this.isInitialized = true;
        console.log('✅ Système de Surveillance initialisé');
    }

    /**
     * Configuration des gestionnaires d'événements
     */
    setupEventListeners() {
        // Gestion de la visibilité de la page
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.pauseNonEssentialUpdates();
            } else {
                this.resumeUpdates();
            }
        });

        // Gestion de la fermeture/rechargement de la page
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });

        // Gestion des erreurs globales
        window.addEventListener('error', (e) => {
            console.error('Erreur globale:', e.error);
            this.handleError(e.error);
        });

        // Raccourcis clavier
        document.addEventListener('keydown', (e) => {
            this.handleKeyboardShortcuts(e);
        });
    }

    /**
     * Initialisation des connexions WebSocket
     */
    initializeWebSockets() {
        const userId = this.getCurrentUserId();
        const locationId = this.getCurrentLocationId();

        // WebSocket pour les notifications utilisateur
        if (userId) {
            this.connectWebSocket('notifications', `/ws/notifications/${userId}/`, {
                onMessage: (data) => this.handleNotification(data),
                onError: (error) => console.error('Erreur WebSocket notifications:', error)
            });
        }

        // WebSocket pour les alertes de localisation
        if (locationId) {
            this.connectWebSocket('alerts', `/ws/alerts/${locationId}/`, {
                onMessage: (data) => this.handleAlert(data),
                onError: (error) => console.error('Erreur WebSocket alertes:', error)
            });
        }

        // WebSocket pour le tableau de bord
        this.connectWebSocket('dashboard', '/ws/monitoring/dashboard/', {
            onMessage: (data) => this.handleDashboardUpdate(data),
            onError: (error) => console.error('Erreur WebSocket dashboard:', error)
        });
    }

    /**
     * Connexion WebSocket générique avec reconnexion automatique
     */
    connectWebSocket(name, path, handlers = {}) {
        const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}${path}`;
        
        const ws = new WebSocket(wsUrl);
        this.websockets[name] = ws;
        this.reconnectAttempts[name] = 0;

        ws.onopen = () => {
            console.log(`✅ WebSocket ${name} connecté`);
            this.reconnectAttempts[name] = 0;
            this.updateConnectionStatus(name, 'connected');
            
            if (handlers.onOpen) {
                handlers.onOpen();
            }
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (handlers.onMessage) {
                    handlers.onMessage(data);
                }
            } catch (error) {
                console.error(`Erreur parsing message WebSocket ${name}:`, error);
            }
        };

        ws.onerror = (error) => {
            console.error(`❌ Erreur WebSocket ${name}:`, error);
            this.updateConnectionStatus(name, 'error');
            
            if (handlers.onError) {
                handlers.onError(error);
            }
        };

        ws.onclose = (event) => {
            console.log(`🔌 WebSocket ${name} fermé:`, event.code, event.reason);
            this.updateConnectionStatus(name, 'disconnected');
            
            // Tentative de reconnexion automatique
            if (this.reconnectAttempts[name] < this.config.maxReconnectAttempts) {
                setTimeout(() => {
                    this.reconnectAttempts[name]++;
                    console.log(`🔄 Tentative de reconnexion ${name} (${this.reconnectAttempts[name]}/${this.config.maxReconnectAttempts})`);
                    this.connectWebSocket(name, path, handlers);
                }, this.config.reconnectInterval);
            }
        };

        return ws;
    }

    /**
     * Gestion des notifications
     */
    handleNotification(data) {
        console.log('📢 Notification reçue:', data);

        switch (data.type) {
            case 'new_notification':
                this.displayNotification(data.notification);
                if (data.play_sound && this.config.alertSoundEnabled) {
                    this.playNotificationSound();
                }
                if (data.show_popup && data.notification.alert_priority === 'critical') {
                    this.showEmergencyPopup(data.notification);
                }
                break;

            case 'unread_notifications':
                this.updateNotificationCount(data.count);
                this.loadNotificationList(data.notifications);
                break;
        }
    }

    /**
     * Gestion des alertes
     */
    handleAlert(data) {
        console.log('🚨 Alerte reçue:', data);

        switch (data.type) {
            case 'new_alert':
                this.displayAlert(data.alert);
                this.updateAlertCounters();
                
                if (data.sound && this.config.alertSoundEnabled) {
                    this.playAlertSound();
                }
                
                if (data.alert.priority === 'critical') {
                    this.handleCriticalAlert(data.alert);
                }
                break;

            case 'recent_alerts':
                this.loadRecentAlerts(data.alerts);
                break;

            case 'alert_update':
                this.updateAlertDisplay(data.alert);
                break;
        }
    }

    /**
     * Gestion des mises à jour du tableau de bord
     */
    handleDashboardUpdate(data) {
        console.log('📊 Mise à jour dashboard:', data);

        switch (data.type) {
            case 'dashboard_stats':
                this.updateDashboardStats(data.stats);
                break;

            case 'dashboard_update':
                this.applyDashboardUpdate(data.update);
                break;
        }
    }

    /**
     * Affichage d'une notification
     */
    displayNotification(notification) {
        // Mettre à jour le compteur
        const badge = document.getElementById('notification-badge');
        if (badge) {
            const currentCount = parseInt(badge.textContent) || 0;
            badge.textContent = currentCount + 1;
            badge.classList.add('pulse');
        }

        // Ajouter à la liste des notifications
        const notificationList = document.getElementById('notification-list');
        if (notificationList) {
            const notificationElement = this.createNotificationElement(notification);
            
            // Supprimer le message "aucune notification" s'il existe
            const noNotifications = notificationList.querySelector('.text-muted');
            if (noNotifications) {
                noNotifications.remove();
            }
            
            notificationList.insertBefore(notificationElement, notificationList.firstChild);
        }

        // Toast notification
        this.showToast(notification.alert_title, {
            body: `Nouvelle alerte: ${notification.alert_priority}`,
            priority: notification.alert_priority,
            autoHide: true
        });
    }

    /**
     * Création d'un élément de notification
     */
    createNotificationElement(notification) {
        const div = document.createElement('div');
        div.className = 'dropdown-item notification-item fade-in';
        div.dataset.notificationId = notification.id;
        
        const priorityClass = this.getPriorityClass(notification.alert_priority);
        const timeString = this.formatRelativeTime(notification.sent_at);
        
        div.innerHTML = `
            <div class="d-flex justify-content-between align-items-start">
                <div class="flex-grow-1">
                    <div class="fw-bold">${this.escapeHtml(notification.alert_title)}</div>
                    <div class="small text-muted">${timeString}</div>
                    ${notification.message ? `<div class="small mt-1">${this.escapeHtml(notification.message)}</div>` : ''}
                </div>
                <div class="text-end">
                    <span class="badge bg-${priorityClass}">${notification.alert_priority}</span>
                </div>
            </div>
        `;
        
        div.addEventListener('click', () => {
            this.markNotificationAsRead(notification.id);
            this.showNotificationDetails(notification);
        });
        
        return div;
    }

    /**
     * Affichage d'une alerte
     */
    displayAlert(alert) {
        const alertPanel = document.getElementById('real-time-alerts');
        if (!alertPanel) return;

        // Supprimer le message "aucune alerte"
        const noAlerts = alertPanel.querySelector('#no-alerts');
        if (noAlerts) {
            noAlerts.remove();
        }

        const alertElement = this.createAlertElement(alert);
        alertPanel.insertBefore(alertElement, alertPanel.firstChild);

        // Limiter le nombre d'alertes affichées
        const alerts = alertPanel.querySelectorAll('.alert-item');
        if (alerts.length > 10) {
            alerts[alerts.length - 1].remove();
        }
    }

    /**
     * Création d'un élément d'alerte
     */
    createAlertElement(alert) {
        const div = document.createElement('div');
        div.className = `alert-item ${alert.priority} slide-in`;
        div.dataset.alertId = alert.id;
        
        const priorityClass = this.getPriorityClass(alert.priority);
        const timeString = this.formatRelativeTime(alert.created_at);
        
        div.innerHTML = `
            <div class="d-flex justify-content-between align-items-start">
                <div class="flex-grow-1">
                    <div class="fw-bold">${this.escapeHtml(alert.title)}</div>
                    <div class="small text-muted mb-2">
                        ${alert.detection_event ? `${alert.detection_event.camera_name} - ${alert.detection_event.zone_name}` : 'Système'}
                    </div>
                    <div class="small">${this.escapeHtml(alert.message)}</div>
                </div>
                <div class="text-end">
                    <span class="badge bg-${priorityClass}">${alert.priority}</span>
                    <div class="small text-muted mt-1">${timeString}</div>
                </div>
            </div>
            <div class="mt-2">
                <button class="btn btn-outline-light btn-sm me-2" onclick="surveillance.acknowledgeAlert('${alert.id}')">
                    <i class="fas fa-check"></i> Accuser réception
                </button>
                <button class="btn btn-outline-primary btn-sm" onclick="surveillance.showAlertDetails('${alert.id}')">
                    <i class="fas fa-info-circle"></i> Détails
                </button>
            </div>
        `;
        
        return div;
    }

    /**
     * Mise à jour des statistiques du tableau de bord
     */
    updateDashboardStats(stats) {
        // Mise à jour des compteurs de caméras
        this.updateElement('camera-count', stats.cameras?.total || 0);
        this.updateElement('online-cameras', stats.cameras?.online || 0);
        
        // Mise à jour des compteurs d'alertes
        this.updateElement('active-alerts', stats.recent_alerts || 0);
        
        // Mise à jour des détections
        if (stats.detections_today) {
            this.updateElement('detections-today', stats.detections_today.total || 0);
        }
        
        // Mise à jour de l'heure de dernière mise à jour
        if (stats.last_update) {
            const lastUpdate = new Date(stats.last_update);
            this.updateElement('last-update', lastUpdate.toLocaleTimeString('fr-FR'));
        }

        // Mise à jour du statut système
        this.updateSystemStatus(stats);
    }

    /**
     * Mise à jour du statut système
     */
    updateSystemStatus(stats) {
        const systemStatus = document.getElementById('system-status');
        if (!systemStatus) return;

        const totalCameras = stats.cameras?.total || 0;
        const onlineCameras = stats.cameras?.online || 0;
        const offlinePercentage = totalCameras > 0 ? ((totalCameras - onlineCameras) / totalCameras) * 100 : 0;

        let statusClass = 'bg-success';
        let statusText = 'Système Actif';
        
        if (offlinePercentage > 30) {
            statusClass = 'bg-danger';
            statusText = 'Problème Système';
        } else if (offlinePercentage > 10) {
            statusClass = 'bg-warning';
            statusText = 'Surveillance Partielle';
        }

        systemStatus.className = `badge ${statusClass} me-2`;
        systemStatus.innerHTML = `<i class="fas fa-circle pulse"></i> ${statusText}`;
    }

    /**
     * Sons et notifications audio
     */
    playNotificationSound() {
        this.playSound('notification');
    }

    playAlertSound() {
        this.playSound('alert');
    }

    playSound(type) {
        const audio = document.getElementById(`${type}-sound`);
        if (audio && this.config.alertSoundEnabled) {
            audio.currentTime = 0;
            audio.play().catch(e => {
                console.warn(`Impossible de jouer le son ${type}:`, e);
            });
        }
    }

    /**
     * Toast notifications
     */
    showToast(title, options = {}) {
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-white border-0 fade-in';
        
        const bgClass = this.getPriorityClass(options.priority || 'info');
        toast.classList.add(`bg-${bgClass}`);
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <div class="fw-bold">${this.escapeHtml(title)}</div>
                    ${options.body ? `<div class="small">${this.escapeHtml(options.body)}</div>` : ''}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        // Créer le conteneur de toasts s'il n'existe pas
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '9999';
            document.body.appendChild(toastContainer);
        }
        
        toastContainer.appendChild(toast);
        
        // Initialiser le toast Bootstrap
        const bsToast = new bootstrap.Toast(toast, {
            autohide: options.autoHide !== false,
            delay: options.delay || this.config.notificationTimeout
        });
        
        bsToast.show();
        
        // Nettoyer après fermeture
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
        
        return bsToast;
    }

    /**
     * Gestion des alertes critiques
     */
    handleCriticalAlert(alert) {
        // Animation de l'indicateur système
        const systemStatus = document.getElementById('system-status');
        if (systemStatus) {
            systemStatus.classList.add('critical-alert');
            setTimeout(() => systemStatus.classList.remove('critical-alert'), 10000);
        }

        // Notification système si disponible
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification('ALERTE CRITIQUE - Surveillance', {
                body: alert.title,
                icon: '/static/img/alert-icon.png',
                requireInteraction: true,
                tag: 'critical-alert'
            });
        }

        // Modal d'urgence
        this.showEmergencyModal(alert);
    }

    /**
     * Modal d'alerte d'urgence
     */
    showEmergencyModal(alert) {
        const modal = document.getElementById('emergencyAlertModal');
        if (!modal) return;

        const content = document.getElementById('emergency-alert-content');
        if (content) {
            content.innerHTML = `
                <div class="alert alert-danger critical-alert">
                    <h5><i class="fas fa-exclamation-triangle me-2"></i>${this.escapeHtml(alert.title)}</h5>
                    <p>${this.escapeHtml(alert.message || 'Alerte critique détectée')}</p>
                    <div class="mt-3">
                        <div class="row">
                            <div class="col-md-6">
                                <strong>Heure:</strong> ${new Date(alert.created_at).toLocaleString('fr-FR')}<br>
                                <strong>Priorité:</strong> <span class="badge bg-danger">${alert.priority}</span><br>
                                ${alert.detection_event ? `<strong>Caméra:</strong> ${alert.detection_event.camera_name}<br>` : ''}
                                ${alert.detection_event ? `<strong>Zone:</strong> ${alert.detection_event.zone_name}` : ''}
                            </div>
                            <div class="col-md-6">
                                ${alert.detection_event ? `
                                    <strong>Type:</strong> ${alert.detection_event.event_type_display}<br>
                                    <strong>Confiance:</strong> ${Math.round((alert.detection_event.confidence || 0) * 100)}%<br>
                                    <strong>Gravité:</strong> ${alert.detection_event.severity}
                                ` : ''}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        const bsModal = new bootstrap.Modal(modal, { backdrop: 'static' });
        bsModal.show();
        
        // Configurer le bouton d'accusé de réception
        const acknowledgeBtn = document.getElementById('acknowledge-emergency');
        if (acknowledgeBtn) {
            acknowledgeBtn.onclick = () => {
                this.acknowledgeAlert(alert.id);
                bsModal.hide();
            };
        }
    }

    /**
     * Actions sur les alertes
     */
    acknowledgeAlert(alertId) {
        if (this.websockets.alerts && this.websockets.alerts.readyState === WebSocket.OPEN) {
            this.websockets.alerts.send(JSON.stringify({
                type: 'acknowledge_alert',
                alert_id: alertId
            }));
            
            // Mise à jour visuelle immédiate
            const alertElement = document.querySelector(`[data-alert-id="${alertId}"]`);
            if (alertElement) {
                alertElement.classList.add('acknowledged');
                const badge = alertElement.querySelector('.badge');
                if (badge) {
                    badge.textContent = 'Accusé de réception';
                    badge.className = 'badge bg-info';
                }
            }
            
            this.showToast('Alerte accusée de réception', { priority: 'success' });
        }
    }

    resolveAlert(alertId) {
        if (this.websockets.alerts && this.websockets.alerts.readyState === WebSocket.OPEN) {
            this.websockets.alerts.send(JSON.stringify({
                type: 'resolve_alert',
                alert_id: alertId
            }));
            
            this.showToast('Alerte résolue', { priority: 'success' });
        }
    }

    /**
     * Fonctions utilitaires
     */
    updateElement(id, value) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }

    getPriorityClass(priority) {
        const classes = {
            'critical': 'danger',
            'high': 'warning',
            'medium': 'info',
            'low': 'secondary'
        };
        return classes[priority] || 'secondary';
    }

    formatRelativeTime(timestamp) {
        const now = new Date();
        const time = new Date(timestamp);
        const diffInSeconds = Math.floor((now - time) / 1000);
        
        if (diffInSeconds < 60) {
            return 'À l\'instant';
        } else if (diffInSeconds < 3600) {
            const minutes = Math.floor(diffInSeconds / 60);
            return `Il y a ${minutes} min`;
        } else if (diffInSeconds < 86400) {
            const hours = Math.floor(diffInSeconds / 3600);
            return `Il y a ${hours}h`;
        } else {
            return time.toLocaleDateString('fr-FR');
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    getCurrentUserId() {
        // Récupérer l'ID utilisateur depuis le DOM ou une variable globale
        const userElement = document.querySelector('[data-user-id]');
        return userElement ? userElement.dataset.userId : null;
    }

    getCurrentLocationId() {
        // Récupérer l'ID de localisation depuis le DOM ou une variable globale
        const locationElement = document.querySelector('[data-location-id]');
        return locationElement ? locationElement.dataset.locationId : null;
    }

    /**
     * Gestion des raccourcis clavier
     */
    handleKeyboardShortcuts(e) {
        // Ctrl/Cmd + Shift + A: Afficher toutes les alertes
        if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'A') {
            e.preventDefault();
            this.showAllAlerts();
        }
        
        // Échap: Fermer les modales
        if (e.key === 'Escape') {
            this.closeModals();
        }
    }

    /**
     * Nettoyage lors de la fermeture
     */
    cleanup() {
        console.log('🧹 Nettoyage du système de surveillance');
        
        // Fermer toutes les connexions WebSocket
        Object.values(this.websockets).forEach(ws => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.close();
            }
        });
        
        // Arrêter les timers
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
        }
    }

    /**
     * Gestion des erreurs globales
     */
    handleError(error) {
        console.error('💥 Erreur système:', error);
        
        // Afficher une notification d'erreur discrète
        this.showToast('Une erreur est survenue', 'error');
        
        // Optionnel: Envoyer l'erreur au serveur pour le logging
        if (this.config.errorReporting) {
            this.reportError(error);
        }
    }

    /**
     * Mettre en pause les mises à jour non essentielles
     */
    pauseNonEssentialUpdates() {
        console.log('⏸️ Mise en pause des mises à jour non essentielles');
        this.isPaused = true;
        
        // Arrêter les timers de mise à jour
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }

    /**
     * Reprendre les mises à jour
     */
    resumeUpdates() {
        console.log('▶️ Reprise des mises à jour');
        this.isPaused = false;
        
        // Redémarrer les timers
        this.startPeriodicUpdates();
    }

    /**
     * Afficher un toast de notification
     */
    showToast(message, type = 'info') {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type === 'error' ? 'danger' : 'primary'} border-0`;
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        setTimeout(() => toast.remove(), 5000);
    }

    /**
     * Signaler une erreur au serveur
     */
    reportError(error) {
        fetch('/api/system/error-report/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': this.getCsrfToken()
            },
            body: JSON.stringify({
                error: error.toString(),
                stack: error.stack,
                url: window.location.href,
                timestamp: new Date().toISOString()
            })
        }).catch(e => console.warn('Impossible de signaler l\'erreur:', e));
    }

    /**
     * Mises à jour périodiques
     */
    startPeriodicUpdates() {
        this.updateInterval = setInterval(() => {
            if (!document.hidden) {
                this.updateRelativeTimes();
                this.checkConnectionHealth();
            }
        }, 30000); // Toutes les 30 secondes
    }

    updateRelativeTimes() {
        // Mettre à jour les temps relatifs dans les notifications et alertes
        document.querySelectorAll('[data-timestamp]').forEach(element => {
            const timestamp = element.dataset.timestamp;
            element.textContent = this.formatRelativeTime(timestamp);
        });
    }

    checkConnectionHealth() {
        Object.entries(this.websockets).forEach(([name, ws]) => {
            if (ws.readyState !== WebSocket.OPEN) {
                console.warn(`⚠️ WebSocket ${name} déconnecté, tentative de reconnexion...`);
                // La reconnexion se fait automatiquement dans connectWebSocket
            }
        });
    }

    /**
     * Gestion de l'état de connection
     */
    updateConnectionStatus(name, status) {
        const statusElement = document.getElementById(`${name}-connection-status`);
        if (statusElement) {
            statusElement.className = `connection-status ${status}`;
            statusElement.textContent = status === 'connected' ? 'Connecté' : 
                                     status === 'error' ? 'Erreur' : 'Déconnecté';
        }
    }

    /**
     * Chargement des préférences utilisateur
     */
    loadUserPreferences() {
        const preferences = localStorage.getItem('surveillance-preferences');
        if (preferences) {
            try {
                const parsed = JSON.parse(preferences);
                this.config = { ...this.config, ...parsed };
            } catch (e) {
                console.warn('Erreur chargement préférences:', e);
            }
        }
    }

    /**
     * Sauvegarde des préférences utilisateur
     */
    saveUserPreferences() {
        localStorage.setItem('surveillance-preferences', JSON.stringify(this.config));
    }
}

// Créer l'instance globale
const surveillance = new SurveillanceSystem();

// Exporter pour usage global
window.surveillance = surveillance; 