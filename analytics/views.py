from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Count, Avg, Q, Sum
from django.contrib import messages
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import json
import logging
from datetime import datetime, timedelta, date
from .models import Report, StatisticsSummary, HeatMapData, PerformanceMetric, TrendAnalysis
from monitoring.models import Location, Camera, DetectionEvent, Zone
from alerts.models import Alert

logger = logging.getLogger('analytics')


@login_required
def reports_list(request):
    """Liste des rapports"""
    # Filtres
    report_type = request.GET.get('type')
    location_id = request.GET.get('location')
    status_filter = request.GET.get('status')
    
    reports = Report.objects.all().select_related('location', 'generated_by')
    
    # Appliquer les filtres
    if report_type:
        reports = reports.filter(report_type=report_type)
    if location_id:
        reports = reports.filter(location_id=location_id)
    if status_filter:
        reports = reports.filter(status=status_filter)
    
    reports = reports.order_by('-created_at')[:50]
    
    # Options pour les filtres
    locations = Location.objects.filter(is_active=True)
    report_types = Report.REPORT_TYPES
    status_choices = Report.STATUS_CHOICES
    
    context = {
        'reports': reports,
        'locations': locations,
        'report_types': report_types,
        'status_choices': status_choices,
        'current_filters': {
            'type': report_type,
            'location': location_id,
            'status': status_filter,
        }
    }
    
    return render(request, 'analytics/reports.html', context)


@login_required
def report_detail(request, report_id):
    """Détails d'un rapport"""
    report = get_object_or_404(Report, id=report_id)
    
    context = {
        'report': report,
    }
    
    return render(request, 'analytics/report_detail.html', context)


@login_required
@require_http_methods(["POST"])
def generate_report(request):
    """Générer un nouveau rapport"""
    try:
        data = json.loads(request.body)
        
        report = Report.objects.create(
            title=data['title'],
            report_type=data['report_type'],
            location_id=data['location_id'],
            period_start=datetime.fromisoformat(data['period_start']),
            period_end=datetime.fromisoformat(data['period_end']),
            generated_by=request.user,
            status='generating',
        )
        
        # Démarrer la génération du rapport en arrière-plan
        from .tasks import generate_report_task
        generate_report_task.delay(report.id)
        
        messages.success(request, f"Rapport '{report.title}' en cours de génération")
        logger.info(f"Rapport {report.id} créé par {request.user}")
        
        return JsonResponse({'success': True, 'report_id': report.id})
        
    except Exception as e:
        logger.error(f"Erreur génération rapport: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@login_required
def statistics_dashboard(request):
    """Tableau de bord des statistiques"""
    # Paramètres de période
    days = int(request.GET.get('days', 30))
    location_id = request.GET.get('location')
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # Filtrer par localisation si spécifiée
    base_detections = DetectionEvent.objects.filter(
        detected_at__gte=start_date,
        detected_at__lte=end_date
    )
    base_alerts = Alert.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date
    )
    
    if location_id:
        base_detections = base_detections.filter(camera__location_id=location_id)
        base_alerts = base_alerts.filter(detection_event__camera__location_id=location_id)
    
    # Statistiques générales
    total_detections = base_detections.count()
    total_alerts = base_alerts.count()
    
    # Répartition par type d'événement
    event_types = base_detections.values('event_type').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Répartition par gravité
    severity_stats = base_detections.values('severity').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Évolution temporelle (par jour)
    daily_stats = []
    for i in range(days):
        day = (end_date - timedelta(days=i)).date()
        day_detections = base_detections.filter(detected_at__date=day).count()
        day_alerts = base_alerts.filter(created_at__date=day).count()
        
        daily_stats.append({
            'date': day.isoformat(),
            'detections': day_detections,
            'alerts': day_alerts
        })
    
    daily_stats.reverse()  # Ordre chronologique
    
    # Top caméras par détections
    top_cameras = base_detections.values(
        'camera__name', 'camera__location__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Top zones par activité
    top_zones = base_detections.values(
        'zone__name', 'zone__risk_level'
    ).annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Précision de l'IA
    verified_detections = base_detections.filter(is_verified=True)
    true_positives = verified_detections.filter(false_positive=False).count()
    false_positives = verified_detections.filter(false_positive=True).count()
    
    ai_accuracy = 0
    if verified_detections.count() > 0:
        ai_accuracy = (true_positives / verified_detections.count()) * 100
    
    # Temps de réponse moyen aux alertes
    resolved_alerts = base_alerts.filter(acknowledged_at__isnull=False)
    avg_response_time = 0
    if resolved_alerts.count() > 0:
        total_seconds = sum([
            (alert.acknowledged_at - alert.created_at).total_seconds()
            for alert in resolved_alerts
        ])
        avg_response_time = total_seconds / resolved_alerts.count() / 60  # en minutes
    
    context = {
        'period_days': days,
        'location_id': location_id,
        'total_detections': total_detections,
        'total_alerts': total_alerts,
        'event_types': list(event_types),
        'severity_stats': list(severity_stats),
        'daily_stats': daily_stats,
        'top_cameras': list(top_cameras),
        'top_zones': list(top_zones),
        'ai_accuracy': round(ai_accuracy, 1),
        'avg_response_time': round(avg_response_time, 1),
        'locations': Location.objects.filter(is_active=True),
    }
    
    return render(request, 'analytics/statistics_dashboard.html', context)


@login_required
def heatmap_view(request):
    """Vue de la carte de chaleur"""
    location_id = request.GET.get('location')
    date_filter = request.GET.get('date', timezone.now().date().isoformat())
    
    try:
        target_date = datetime.fromisoformat(date_filter).date()
    except:
        target_date = timezone.now().date()
    
    # Données de la carte de chaleur
    heatmap_data = HeatMapData.objects.filter(date=target_date)
    if location_id:
        heatmap_data = heatmap_data.filter(location_id=location_id)
    
    heatmap_data = heatmap_data.select_related('zone', 'location').order_by('location', 'zone')
    
    # Préparer les données pour la visualisation
    zones_data = []
    for data in heatmap_data:
        zones_data.append({
            'zone_id': data.zone.id,
            'zone_name': data.zone.name,
            'location_name': data.location.name,
            'risk_level': data.zone.risk_level,
            'detection_count': data.detection_count,
            'alert_count': data.alert_count,
            'activity_density': data.activity_density,
            'risk_score': data.risk_score,
            'peak_hours': data.peak_hours,
        })
    
    context = {
        'zones_data': zones_data,
        'target_date': target_date,
        'locations': Location.objects.filter(is_active=True),
        'location_id': location_id,
    }
    
    return render(request, 'analytics/heatmap.html', context)


@login_required
def performance_metrics(request):
    """Métriques de performance du système"""
    # Paramètres
    days = int(request.GET.get('days', 7))
    location_id = request.GET.get('location')
    
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # Métriques de performance
    metrics = PerformanceMetric.objects.filter(
        timestamp__gte=start_date,
        timestamp__lte=end_date
    )
    
    if location_id:
        metrics = metrics.filter(location_id=location_id)
    
    # Grouper par type de métrique
    metrics_by_type = {}
    for metric_type, display_name in PerformanceMetric.METRIC_TYPES:
        type_metrics = metrics.filter(metric_type=metric_type).order_by('timestamp')
        
        metrics_data = []
        for metric in type_metrics:
            metrics_data.append({
                'timestamp': metric.timestamp.isoformat(),
                'value': metric.value,
                'unit': metric.unit,
                'is_within_threshold': metric.is_within_threshold,
                'camera': metric.camera.name if metric.camera else None,
            })
        
        metrics_by_type[metric_type] = {
            'display_name': display_name,
            'data': metrics_data,
            'current_value': type_metrics.last().value if type_metrics.exists() else 0,
        }
    
    # Alertes de performance
    performance_alerts = metrics.filter(is_alert_triggered=True).order_by('-timestamp')[:20]
    
    context = {
        'period_days': days,
        'location_id': location_id,
        'metrics_by_type': metrics_by_type,
        'performance_alerts': performance_alerts,
        'locations': Location.objects.filter(is_active=True),
    }
    
    return render(request, 'analytics/performance_metrics.html', context)


@login_required
def trends_analysis(request):
    """Analyse des tendances"""
    location_id = request.GET.get('location')
    trend_type = request.GET.get('trend_type', 'detection_frequency')
    
    # Récupérer les analyses de tendance
    trends = TrendAnalysis.objects.filter(trend_type=trend_type)
    if location_id:
        trends = trends.filter(location_id=location_id)
    
    trends = trends.order_by('-created_at')[:10]
    
    # Données pour les graphiques
    trends_data = []
    for trend in trends:
        trends_data.append({
            'id': trend.id,
            'trend_direction': trend.trend_direction,
            'trend_strength': trend.trend_strength,
            'correlation_coefficient': trend.correlation_coefficient,
            'data_points': trend.data_points,
            'predictions': trend.predictions,
            'period_start': trend.analysis_period_start.isoformat(),
            'period_end': trend.analysis_period_end.isoformat(),
            'created_at': trend.created_at.isoformat(),
        })
    
    context = {
        'location_id': location_id,
        'trend_type': trend_type,
        'trends_data': trends_data,
        'trend_types': TrendAnalysis.TREND_TYPES,
        'locations': Location.objects.filter(is_active=True),
    }
    
    return render(request, 'analytics/trends_analysis.html', context)


# API Endpoints

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_statistics_summary(request):
    """API: Résumé statistique"""
    try:
        days = int(request.GET.get('days', 7))
        location_id = request.GET.get('location_id')
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Récupérer ou créer le résumé statistique
        summary = get_or_create_statistics_summary(
            location_id, start_date, end_date, 'day'
        )
        
        return Response({
            'period_days': days,
            'total_detections': summary.total_detections,
            'detection_breakdown': {
                'theft': summary.theft_detections,
                'intrusion': summary.intrusion_detections,
                'suspicious': summary.suspicious_detections,
                'accident': summary.accident_detections,
                'fire': summary.fire_detections,
                'other': summary.other_detections,
            },
            'alert_breakdown': {
                'total': summary.total_alerts,
                'critical': summary.critical_alerts,
                'high': summary.high_alerts,
                'medium': summary.medium_alerts,
                'low': summary.low_alerts,
            },
            'performance': {
                'false_positives': summary.false_positives,
                'true_positives': summary.true_positives,
                'accuracy': summary.detection_accuracy,
                'avg_response_time': summary.average_response_time,
                'camera_uptime': summary.camera_uptime_percentage,
            },
            'peak_activity_hour': summary.peak_activity_hour,
            'activity_distribution': summary.activity_distribution,
        })
        
    except Exception as e:
        logger.error(f"Erreur API statistics summary: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_heatmap_data(request):
    """API: Données de carte de chaleur"""
    try:
        location_id = request.GET.get('location_id')
        date_str = request.GET.get('date', timezone.now().date().isoformat())
        
        try:
            target_date = datetime.fromisoformat(date_str).date()
        except:
            target_date = timezone.now().date()
        
        heatmap_data = HeatMapData.objects.filter(date=target_date)
        if location_id:
            heatmap_data = heatmap_data.filter(location_id=location_id)
        
        heatmap_data = heatmap_data.select_related('zone', 'location')
        
        zones_data = []
        for data in heatmap_data:
            zones_data.append({
                'zone_id': data.zone.id,
                'zone_name': data.zone.name,
                'location_name': data.location.name,
                'coordinates': data.zone.coordinates,
                'detection_count': data.detection_count,
                'alert_count': data.alert_count,
                'activity_density': data.activity_density,
                'risk_score': data.risk_score,
                'peak_hours': data.peak_hours,
                'event_types': data.event_types,
            })
        
        return Response({
            'date': target_date.isoformat(),
            'zones': zones_data
        })
        
    except Exception as e:
        logger.error(f"Erreur API heatmap data: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_generate_report(request):
    """API: Générer un rapport"""
    try:
        data = request.data
        
        report = Report.objects.create(
            title=data['title'],
            report_type=data['report_type'],
            location_id=data['location_id'],
            period_start=datetime.fromisoformat(data['period_start']),
            period_end=datetime.fromisoformat(data['period_end']),
            generated_by=request.user,
            status='generating',
            is_automatic=False,
        )
        
        # Démarrer la génération (simulation pour la démo)
        generate_report_content(report)
        
        return Response({
            'success': True,
            'report_id': report.id,
            'status': report.status
        })
        
    except Exception as e:
        logger.error(f"Erreur API generate report: {e}")
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Fonctions utilitaires

def get_or_create_statistics_summary(location_id, start_date, end_date, period_type):
    """Récupère ou crée un résumé statistique"""
    if location_id:
        location = get_object_or_404(Location, id=location_id)
        summary, created = StatisticsSummary.objects.get_or_create(
            location=location,
            period_type=period_type,
            period_start=start_date,
            defaults={
                'period_end': end_date,
            }
        )
    else:
        # Créer un résumé global
        summary = StatisticsSummary(
            period_type=period_type,
            period_start=start_date,
            period_end=end_date,
        )
        created = True
    
    if created:
        # Calculer les statistiques
        calculate_statistics_summary(summary, location_id)
    
    return summary


def calculate_statistics_summary(summary, location_id=None):
    """Calcule les statistiques pour un résumé"""
    start_date = summary.period_start
    end_date = summary.period_end
    
    # Base des détections
    detections = DetectionEvent.objects.filter(
        detected_at__gte=start_date,
        detected_at__lte=end_date
    )
    
    if location_id:
        detections = detections.filter(camera__location_id=location_id)
    
    # Compter les détections par type
    summary.total_detections = detections.count()
    summary.theft_detections = detections.filter(event_type='theft').count()
    summary.intrusion_detections = detections.filter(event_type='intrusion').count()
    summary.suspicious_detections = detections.filter(event_type='suspicious').count()
    summary.accident_detections = detections.filter(event_type='accident').count()
    summary.fire_detections = detections.filter(event_type='fire').count()
    summary.other_detections = summary.total_detections - (
        summary.theft_detections + summary.intrusion_detections + 
        summary.suspicious_detections + summary.accident_detections + 
        summary.fire_detections
    )
    
    # Alertes
    alerts = Alert.objects.filter(
        created_at__gte=start_date,
        created_at__lte=end_date
    )
    
    if location_id:
        alerts = alerts.filter(detection_event__camera__location_id=location_id)
    
    summary.total_alerts = alerts.count()
    summary.critical_alerts = alerts.filter(priority='critical').count()
    summary.high_alerts = alerts.filter(priority='high').count()
    summary.medium_alerts = alerts.filter(priority='medium').count()
    summary.low_alerts = alerts.filter(priority='low').count()
    
    # Métriques de performance
    verified = detections.filter(is_verified=True)
    summary.true_positives = verified.filter(false_positive=False).count()
    summary.false_positives = verified.filter(false_positive=True).count()
    
    # Temps de réponse moyen
    responded_alerts = alerts.filter(acknowledged_at__isnull=False)
    if responded_alerts.exists():
        total_seconds = sum([
            (alert.acknowledged_at - alert.created_at).total_seconds()
            for alert in responded_alerts
        ])
        summary.average_response_time = total_seconds / responded_alerts.count()
    
    # Disponibilité des caméras
    if location_id:
        cameras = Camera.objects.filter(location_id=location_id)
        online_cameras = cameras.filter(status='online').count()
        total_cameras = cameras.count()
        if total_cameras > 0:
            summary.camera_uptime_percentage = (online_cameras / total_cameras) * 100
    
    summary.save()


def generate_report_content(report):
    """Génère le contenu d'un rapport"""
    try:
        report.status = 'generating'
        report.save()
        
        # Collecter les données selon le type de rapport
        content = {}
        
        if report.report_type == 'daily':
            content = generate_daily_report_content(report)
        elif report.report_type == 'weekly':
            content = generate_weekly_report_content(report)
        elif report.report_type == 'monthly':
            content = generate_monthly_report_content(report)
        elif report.report_type == 'incident':
            content = generate_incident_report_content(report)
        
        # Générer le résumé et les recommandations
        summary, recommendations = generate_report_insights(content, report)
        
        # Mettre à jour le rapport
        report.content = content
        report.summary = summary
        report.recommendations = recommendations
        report.status = 'completed'
        report.completed_at = timezone.now()
        report.save()
        
        logger.info(f"Rapport {report.id} généré avec succès")
        
    except Exception as e:
        logger.error(f"Erreur génération rapport {report.id}: {e}")
        report.status = 'failed'
        report.save()


def generate_daily_report_content(report):
    """Génère le contenu d'un rapport quotidien"""
    # Implémentation simplifiée pour la démo
    return {
        'type': 'daily',
        'detections_summary': {
            'total': 42,
            'by_type': {'theft': 5, 'intrusion': 3, 'suspicious': 34},
            'by_severity': {'critical': 2, 'high': 8, 'medium': 25, 'low': 7}
        },
        'alerts_summary': {
            'total': 15,
            'resolved': 12,
            'pending': 3
        }
    }


def generate_weekly_report_content(report):
    """Génère le contenu d'un rapport hebdomadaire"""
    return {
        'type': 'weekly',
        'summary': 'Rapport hebdomadaire simulé'
    }


def generate_monthly_report_content(report):
    """Génère le contenu d'un rapport mensuel"""
    return {
        'type': 'monthly',
        'summary': 'Rapport mensuel simulé'
    }


def generate_incident_report_content(report):
    """Génère le contenu d'un rapport d'incident"""
    return {
        'type': 'incident',
        'summary': 'Rapport d\'incident simulé'
    }


def generate_report_insights(content, report):
    """Génère le résumé et les recommandations d'un rapport"""
    summary = f"Rapport {report.get_report_type_display()} pour {report.location.name} " \
             f"du {report.period_start.strftime('%d/%m/%Y')} au {report.period_end.strftime('%d/%m/%Y')}"
    
    recommendations = [
        "Surveiller les zones à forte activité",
        "Optimiser la précision de l'IA",
        "Réduire le temps de réponse aux alertes"
    ]
    
    return summary, "\n".join(f"- {rec}" for rec in recommendations)
