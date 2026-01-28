from django.urls import re_path
from core import consumers

websocket_urlpatterns = [
    # Regex to capture the group name (e.g., 'kitchen', 'cashier')
    re_path(r'ws/notifications/(?P<group_name>\w+)/$', consumers.NotificationConsumer.as_asgi()),
]
