"""
URL configuration for PyBiorythm Django REST API Server.

Provides comprehensive REST API endpoints for biorhythm data management
with token authentication, ASGI support, and Django admin interface.
"""

from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from rest_framework.permissions import AllowAny

@require_http_methods(["GET"])
def api_root(request):
    """Root API endpoint providing server information and endpoint discovery."""
    return JsonResponse({
        'api_name': 'PyBiorythm REST API Server',
        'version': '1.0.0',
        'description': 'Django ASGI REST API for biorhythm data with token authentication',
        'server': 'Daphne ASGI',
        'authentication': 'Token-based authentication required',
        'endpoints': {
            'api_info': '/api/',
            'auth_token': '/api/auth/token/',
            'admin': '/admin/',
            'people': '/api/people/',
            'calculations': '/api/calculations/',
            'biorhythm_data': '/api/biorhythm-data/',
            'analyses': '/api/analyses/',
            'statistics': '/api/statistics/'
        },
        'documentation': {
            'browsable_api': 'Available at each endpoint when authenticated',
            'admin_interface': '/admin/ (superuser required)',
            'token_auth': 'POST username/password to /api/auth/token/ to get token'
        }
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('', api_root, name='api_root'),
]
