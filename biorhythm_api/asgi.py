"""
ASGI config for biorhythm_api project.

It exposes the ASGI callable as a module-level variable named ``application``.
Configured for Daphne server with Django Channels support.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'biorhythm_api.settings')

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    # WebSocket support can be added here if needed in the future
    # "websocket": AuthMiddlewareStack(
    #     URLRouter([
    #         # WebSocket URL patterns would go here
    #     ])
    # ),
})
