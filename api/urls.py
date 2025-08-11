"""
URL configuration for the PyBiorythm REST API.

Defines all API endpoints with proper routing and versioning.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Create router and register ViewSets
router = DefaultRouter()
router.register(r'people', views.PersonViewSet, basename='person')
router.register(r'calculations', views.BiorhythmCalculationViewSet, basename='calculation')
router.register(r'biorhythm-data', views.BiorhythmDataViewSet, basename='biorhythm-data')
router.register(r'analyses', views.BiorhythmAnalysisViewSet, basename='analysis')

app_name = 'api'

urlpatterns = [
    # Authentication endpoints
    path('auth/token/', views.CustomAuthToken.as_view(), name='auth_token'),
    
    # API information and statistics
    path('', views.api_info, name='api_info'),
    path('statistics/', views.global_statistics, name='global_statistics'),
    
    # Include router URLs
    path('', include(router.urls)),
]