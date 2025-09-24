from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/video/(?P<camera_id>\w+)/$', consumers.VideoStreamConsumer.as_asgi()),
    re_path(r'ws/detections/(?P<location_id>\w+)/$', consumers.DetectionConsumer.as_asgi()),
    re_path(r'ws/monitoring/dashboard/$', consumers.DashboardConsumer.as_asgi()),
] 