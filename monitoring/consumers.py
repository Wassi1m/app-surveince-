import json
import asyncio
import cv2
import base64
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import Camera, DetectionEvent, Location
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger('monitoring')


class VideoStreamConsumer(AsyncWebsocketConsumer):
    """Consumer pour le streaming vidéo en temps réel"""
    
    async def connect(self):
        self.camera_id = self.scope['url_route']['kwargs']['camera_id']
        self.camera_group_name = f'camera_{self.camera_id}'
        
        # Rejoindre le groupe de la caméra
        await self.channel_layer.group_add(
            self.camera_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Démarrer le streaming vidéo
        await self.start_video_stream()
    
    async def disconnect(self, close_code):
        # Quitter le groupe
        await self.channel_layer.group_discard(
            self.camera_group_name,
            self.channel_name
        )
        
        # Arrêter le streaming
        self.streaming = False
    
    async def start_video_stream(self):
        """Démarre le streaming vidéo depuis la caméra"""
        try:
            camera = await self.get_camera()
            if not camera:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Caméra introuvable'
                }))
                return
            
            self.streaming = True
            
            # Simuler le streaming vidéo (en production, utiliser RTSP/OpenCV)
            while self.streaming:
                # Ici, vous intégreriez OpenCV pour capturer les frames réelles
                frame_data = await self.get_camera_frame(camera)
                
                if frame_data:
                    await self.send(text_data=json.dumps({
                        'type': 'video_frame',
                        'data': frame_data,
                        'timestamp': datetime.now().isoformat(),
                        'camera_id': self.camera_id
                    }))
                
                # Attendre selon le FPS configuré
                await asyncio.sleep(1.0 / camera.fps)
                
        except Exception as e:
            logger.error(f"Erreur streaming caméra {self.camera_id}: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Erreur de streaming: {str(e)}'
            }))
    
    @database_sync_to_async
    def get_camera(self):
        try:
            return Camera.objects.get(id=self.camera_id, status='online')
        except Camera.DoesNotExist:
            return None
    
    async def get_camera_frame(self, camera):
        """Capture une frame de la caméra (simulation)"""
        try:
            # En production, utiliser cv2.VideoCapture avec l'URL RTSP
            # cap = cv2.VideoCapture(camera.stream_url)
            # ret, frame = cap.read()
            
            # Pour la démo, créer une image de test
            frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            
            # Encoder en base64 pour transmission WebSocket
            _, buffer = cv2.imencode('.jpg', frame)
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            return frame_base64
        except Exception as e:
            logger.error(f"Erreur capture frame: {e}")
            return None
    
    async def video_detection(self, event):
        """Recevoir une détection et l'envoyer au client"""
        await self.send(text_data=json.dumps({
            'type': 'detection',
            'detection_data': event['detection_data']
        }))


class DetectionConsumer(AsyncWebsocketConsumer):
    """Consumer pour les détections IA en temps réel"""
    
    async def connect(self):
        self.location_id = self.scope['url_route']['kwargs']['location_id']
        self.location_group_name = f'detections_{self.location_id}'
        
        await self.channel_layer.group_add(
            self.location_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Envoyer les détections récentes
        await self.send_recent_detections()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.location_group_name,
            self.channel_name
        )
    
    @database_sync_to_async
    def get_recent_detections(self):
        """Récupère les détections récentes pour ce lieu"""
        from django.utils import timezone
        
        last_hour = timezone.now() - timedelta(hours=1)
        
        detections = DetectionEvent.objects.filter(
            camera__location_id=self.location_id,
            detected_at__gte=last_hour
        ).select_related('camera', 'zone').order_by('-detected_at')[:20]
        
        detection_data = []
        for detection in detections:
            detection_data.append({
                'id': detection.id,
                'event_type': detection.event_type,
                'event_type_display': detection.get_event_type_display(),
                'severity': detection.severity,
                'confidence': detection.confidence,
                'detected_at': detection.detected_at.isoformat(),
                'camera_name': detection.camera.name,
                'zone_name': detection.zone.name,
                'description': detection.description,
                'bounding_boxes': detection.bounding_boxes,
            })
        
        return detection_data
    
    async def send_recent_detections(self):
        """Envoie les détections récentes au client"""
        detections = await self.get_recent_detections()
        await self.send(text_data=json.dumps({
            'type': 'recent_detections',
            'detections': detections
        }))
    
    async def new_detection(self, event):
        """Diffuser une nouvelle détection aux clients connectés"""
        await self.send(text_data=json.dumps({
            'type': 'new_detection',
            'detection': event['detection']
        }))


class DashboardConsumer(AsyncWebsocketConsumer):
    """Consumer pour le tableau de bord principal"""
    
    async def connect(self):
        self.dashboard_group_name = 'dashboard'
        
        await self.channel_layer.group_add(
            self.dashboard_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Envoyer les statistiques initiales
        await self.send_dashboard_stats()
        
        # Démarrer les mises à jour périodiques
        await self.start_periodic_updates()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.dashboard_group_name,
            self.channel_name
        )
        
        self.updating = False
    
    @database_sync_to_async
    def get_dashboard_stats(self):
        """Récupère les statistiques pour le tableau de bord"""
        from django.utils import timezone
        from django.db.models import Count, Q
        
        now = timezone.now()
        today = now.date()
        
        # Statistiques globales
        total_cameras = Camera.objects.count()
        online_cameras = Camera.objects.filter(status='online').count()
        
        # Détections aujourd'hui
        today_detections = DetectionEvent.objects.filter(
            detected_at__date=today
        ).aggregate(
            total=Count('id'),
            critical=Count('id', filter=Q(severity='critical')),
            high=Count('id', filter=Q(severity='high')),
            theft=Count('id', filter=Q(event_type='theft')),
            intrusion=Count('id', filter=Q(event_type='intrusion'))
        )
        
        # Alertes récentes
        recent_alerts_count = DetectionEvent.objects.filter(
            detected_at__gte=now - timedelta(hours=1)
        ).count()
        
        return {
            'cameras': {
                'total': total_cameras,
                'online': online_cameras,
                'offline': total_cameras - online_cameras
            },
            'detections_today': today_detections,
            'recent_alerts': recent_alerts_count,
            'last_update': now.isoformat()
        }
    
    async def send_dashboard_stats(self):
        """Envoie les statistiques du tableau de bord"""
        stats = await self.get_dashboard_stats()
        await self.send(text_data=json.dumps({
            'type': 'dashboard_stats',
            'stats': stats
        }))
    
    async def start_periodic_updates(self):
        """Démarre les mises à jour périodiques du tableau de bord"""
        self.updating = True
        
        while self.updating:
            await asyncio.sleep(30)  # Mise à jour toutes les 30 secondes
            if self.updating:
                await self.send_dashboard_stats()
    
    async def dashboard_update(self, event):
        """Recevoir une mise à jour du tableau de bord"""
        await self.send(text_data=json.dumps({
            'type': 'dashboard_update',
            'update': event['update']
        })) 