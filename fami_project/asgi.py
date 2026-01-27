"""
ASGI config for fami_project project.

It exposes the ASGI callable as a module-level variable named ``application``.
"""

import os
from django.core.asgi import get_asgi_application

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fami_project.settings')
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # type: ignore
from channels.auth import AuthMiddlewareStack  # type: ignore

application = ProtocolTypeRouter({
    # Django's ASGI application to handle traditional HTTP requests
    "http": django_asgi_app,

    # WebSocket handler (We will define websocket_urlpatterns later)
    "websocket": AuthMiddlewareStack(
        URLRouter(
            [
                # routes will be added here in future tasks
            ]
        )
    ),
})
