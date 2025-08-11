"""
Django REST Framework views for biorhythm data API.

Provides comprehensive REST API endpoints for biorhythm data with token authentication,
filtering, pagination, and real-time calculation capabilities.
"""

from rest_framework import viewsets, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Q, Count, Avg, Min, Max
from django.utils import timezone
from datetime import datetime, date, timedelta
import pandas as pd

from biorhythm_data.models import Person, BiorhythmCalculation, BiorhythmData, BiorhythmAnalysis
from .serializers import (
    PersonSerializer, BiorhythmCalculationSerializer, BiorhythmDataSerializer,
    BiorhythmDataSimpleSerializer, BiorhythmAnalysisSerializer, UserSerializer,
    PersonBiorhythmTimeseriesSerializer, BiorhythmCalculationRequestSerializer,
    TokenAuthSerializer, ApiInfoSerializer, StatisticsSerializer
)

# Import PyBiorythm
try:
    from biorythm import BiorhythmCalculator
    BIORYTHM_AVAILABLE = True
except ImportError:
    BIORYTHM_AVAILABLE = False


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for API responses."""
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 1000


class PersonViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing people with biorhythm data.
    
    Provides CRUD operations for people and their biorhythm information.
    """
    
    queryset = Person.objects.all()
    serializer_class = PersonSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'email', 'notes']
    ordering_fields = ['name', 'birthdate', 'created_at']
    ordering = ['name']
    
    @action(detail=True, methods=['get'])
    def biorhythm_data(self, request, pk=None):
        """Get all biorhythm data for a specific person."""
        person = self.get_object()
        
        # Query parameters for filtering
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        limit = request.query_params.get('limit')
        
        queryset = person.biorhythm_entries.all()
        
        # Apply date filtering
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                queryset = queryset.filter(date__gte=start_date)
            except ValueError:
                return Response(
                    {'error': 'Invalid start_date format. Use YYYY-MM-DD'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(date__lte=end_date)
            except ValueError:
                return Response(
                    {'error': 'Invalid end_date format. Use YYYY-MM-DD'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        queryset = queryset.order_by('date')
        
        # Get date range before applying limit
        date_range_start = None
        date_range_end = None
        if queryset.exists():
            date_range_start = queryset.first().date
            date_range_end = queryset.last().date
        
        # Apply limit after calculating date range
        if limit:
            try:
                limit = int(limit)
                if limit > 0:
                    queryset = queryset[:limit]
            except ValueError:
                pass
        
        # Use simple serializer for performance
        serializer = BiorhythmDataSimpleSerializer(queryset, many=True)
        
        return Response({
            'person': {
                'id': person.id,
                'name': person.name,
                'birthdate': person.birthdate
            },
            'data_points': len(serializer.data),
            'date_range': {
                'start': date_range_start,
                'end': date_range_end
            },
            'biorhythm_data': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get statistical summary for a person's biorhythm data."""
        person = self.get_object()
        
        # Get data for analysis
        data_queryset = person.biorhythm_entries.all()
        
        if not data_queryset.exists():
            return Response({
                'person': {'id': person.id, 'name': person.name},
                'message': 'No biorhythm data available for this person'
            })
        
        # Calculate statistics
        stats = data_queryset.aggregate(
            count=Count('id'),
            avg_physical=Avg('physical'),
            avg_emotional=Avg('emotional'),
            avg_intellectual=Avg('intellectual'),
            min_date=Min('date'),
            max_date=Max('date'),
            critical_days=Count('id', filter=Q(
                is_physical_critical=True
            ) | Q(
                is_emotional_critical=True
            ) | Q(
                is_intellectual_critical=True
            ))
        )
        
        # Critical days breakdown
        critical_breakdown = {
            'physical': data_queryset.filter(is_physical_critical=True).count(),
            'emotional': data_queryset.filter(is_emotional_critical=True).count(),
            'intellectual': data_queryset.filter(is_intellectual_critical=True).count(),
        }
        
        return Response({
            'person': {
                'id': person.id,
                'name': person.name,
                'birthdate': person.birthdate
            },
            'statistics': {
                'total_data_points': stats['count'],
                'date_range': {
                    'start': stats['min_date'],
                    'end': stats['max_date'],
                    'days_covered': (stats['max_date'] - stats['min_date']).days + 1 if stats['min_date'] and stats['max_date'] else 0
                },
                'cycle_averages': {
                    'physical': round(stats['avg_physical'], 3) if stats['avg_physical'] else None,
                    'emotional': round(stats['avg_emotional'], 3) if stats['avg_emotional'] else None,
                    'intellectual': round(stats['avg_intellectual'], 3) if stats['avg_intellectual'] else None,
                },
                'critical_days': {
                    'total': stats['critical_days'],
                    'breakdown': critical_breakdown,
                    'percentage': round((stats['critical_days'] / stats['count'] * 100), 2) if stats['count'] > 0 else 0
                }
            }
        })


class BiorhythmCalculationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing biorhythm calculations.
    
    Provides CRUD operations and the ability to trigger new calculations.
    """
    
    queryset = BiorhythmCalculation.objects.all()
    serializer_class = BiorhythmCalculationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['person__name', 'notes', 'pybiorythm_version']
    ordering_fields = ['calculation_date', 'days_calculated', 'start_date', 'end_date']
    ordering = ['-calculation_date']
    
    def get_queryset(self):
        """Filter calculations by query parameters."""
        queryset = super().get_queryset()
        
        person_id = self.request.query_params.get('person_id')
        if person_id:
            queryset = queryset.filter(person__id=person_id)
            
        return queryset
    
    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """
        Trigger a new biorhythm calculation for a person.
        
        Body parameters:
        - person_id: ID of the person
        - days: Number of days to calculate (1-3650)
        - target_date: Start date for calculation (optional, defaults to today)
        - notes: Optional notes for this calculation
        """
        if not BIORYTHM_AVAILABLE:
            return Response(
                {'error': 'PyBiorythm library not available'}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        
        serializer = BiorhythmCalculationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            person = Person.objects.get(id=serializer.validated_data['person_id'])
            days = serializer.validated_data.get('days', 365)
            target_date = serializer.validated_data.get('target_date', date.today())
            notes = serializer.validated_data.get('notes', '')
            
            # Generate biorhythm data using PyBiorythm
            calc = BiorhythmCalculator(days=days)
            birthdate_dt = datetime.combine(person.birthdate, datetime.min.time())
            target_date_dt = datetime.combine(target_date, datetime.min.time())
            
            biorhythm_json = calc.generate_timeseries_json(birthdate_dt, target_date_dt)
            
            # Create calculation record
            start_date = datetime.strptime(biorhythm_json['data'][0]['date'], '%Y-%m-%d').date()
            end_date = datetime.strptime(biorhythm_json['data'][-1]['date'], '%Y-%m-%d').date()
            
            calculation = BiorhythmCalculation.objects.create(
                person=person,
                start_date=start_date,
                end_date=end_date,
                days_calculated=len(biorhythm_json['data']),
                target_date=target_date,
                pybiorythm_version=biorhythm_json.get('meta', {}).get('version', 'unknown'),
                notes=notes
            )
            
            # Create biorhythm data records
            data_points = []
            for day_data in biorhythm_json['data']:
                critical_cycles = day_data.get('critical_cycles', [])
                
                data_point = BiorhythmData(
                    person=person,
                    calculation=calculation,
                    date=datetime.strptime(day_data['date'], '%Y-%m-%d').date(),
                    days_alive=day_data['days_alive'],
                    physical=day_data['physical'],
                    emotional=day_data['emotional'],
                    intellectual=day_data['intellectual'],
                    is_physical_critical='Physical' in critical_cycles,
                    is_emotional_critical='Emotional' in critical_cycles,
                    is_intellectual_critical='Intellectual' in critical_cycles,
                )
                data_points.append(data_point)
            
            BiorhythmData.objects.bulk_create(data_points)
            
            # Return calculation details
            response_serializer = BiorhythmCalculationSerializer(calculation)
            return Response({
                'message': 'Biorhythm calculation completed successfully',
                'calculation': response_serializer.data,
                'data_points_created': len(data_points)
            }, status=status.HTTP_201_CREATED)
            
        except Person.DoesNotExist:
            return Response(
                {'error': 'Person not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Calculation failed: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BiorhythmDataViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ReadOnly ViewSet for biorhythm data points.
    
    Provides read-only access to individual biorhythm data points with filtering.
    """
    
    queryset = BiorhythmData.objects.all()
    serializer_class = BiorhythmDataSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['person__name']
    ordering_fields = ['date', 'days_alive', 'physical', 'emotional', 'intellectual']
    ordering = ['-date']
    
    def get_queryset(self):
        """Filter biorhythm data by query parameters."""
        queryset = super().get_queryset()
        
        # Filter by person
        person_id = self.request.query_params.get('person_id')
        if person_id:
            queryset = queryset.filter(person__id=person_id)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                queryset = queryset.filter(date__gte=start_date)
            except ValueError:
                pass
        
        end_date = self.request.query_params.get('end_date')
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                queryset = queryset.filter(date__lte=end_date)
            except ValueError:
                pass
        
        # Filter by critical days
        critical_only = self.request.query_params.get('critical_only')
        if critical_only and critical_only.lower() == 'true':
            queryset = queryset.filter(
                Q(is_physical_critical=True) |
                Q(is_emotional_critical=True) |
                Q(is_intellectual_critical=True)
            )
        
        return queryset.select_related('person', 'calculation')


class BiorhythmAnalysisViewSet(viewsets.ModelViewSet):
    """
    ViewSet for biorhythm analysis results.
    
    Provides CRUD operations for stored analysis results.
    """
    
    queryset = BiorhythmAnalysis.objects.all()
    serializer_class = BiorhythmAnalysisSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['person__name', 'analysis_type', 'summary']
    ordering_fields = ['analysis_date', 'analysis_type', 'data_points_analyzed']
    ordering = ['-analysis_date']
    
    def get_queryset(self):
        """Filter analyses by query parameters."""
        queryset = super().get_queryset()
        
        person_id = self.request.query_params.get('person_id')
        if person_id:
            queryset = queryset.filter(person__id=person_id)
            
        analysis_type = self.request.query_params.get('analysis_type')
        if analysis_type:
            queryset = queryset.filter(analysis_type=analysis_type)
            
        return queryset


class CustomAuthToken(ObtainAuthToken):
    """Custom token authentication endpoint with additional user info."""
    
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'token': token.key,
            'user': UserSerializer(user).data,
            'created': created,
            'expires_in_hours': 24  # Based on settings
        })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def api_info(request):
    """Get API information and available endpoints."""
    
    info_data = {
        'api_name': 'PyBiorythm REST API',
        'version': '1.0.0',
        'description': 'Django REST API for biorhythm data management with token authentication',
        'authentication': 'Token-based authentication required for all endpoints',
        'endpoints': {
            'auth': {
                'token': '/api/auth/token/',
                'description': 'Obtain authentication token'
            },
            'people': {
                'list': '/api/people/',
                'detail': '/api/people/{id}/',
                'biorhythm_data': '/api/people/{id}/biorhythm_data/',
                'statistics': '/api/people/{id}/statistics/',
                'description': 'Manage people and their biorhythm data'
            },
            'calculations': {
                'list': '/api/calculations/',
                'detail': '/api/calculations/{id}/',
                'calculate': '/api/calculations/calculate/',
                'description': 'Manage biorhythm calculations'
            },
            'biorhythm_data': {
                'list': '/api/biorhythm-data/',
                'detail': '/api/biorhythm-data/{id}/',
                'description': 'Read biorhythm data points'
            },
            'analyses': {
                'list': '/api/analyses/',
                'detail': '/api/analyses/{id}/',
                'description': 'Manage biorhythm analyses'
            },
            'statistics': {
                'global': '/api/statistics/',
                'description': 'Global statistics about biorhythm data'
            }
        },
        'pagination': {
            'page_size': 100,
            'max_page_size': 1000,
            'page_query_param': 'page',
            'page_size_query_param': 'page_size'
        },
        'server_time': timezone.now(),
        'pybiorythm_available': BIORYTHM_AVAILABLE
    }
    
    serializer = ApiInfoSerializer(info_data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def global_statistics(request):
    """Get global statistics about all biorhythm data."""
    
    # Basic counts
    total_people = Person.objects.count()
    total_calculations = BiorhythmCalculation.objects.count()
    total_data_points = BiorhythmData.objects.count()
    
    # Critical days count
    total_critical_days = BiorhythmData.objects.filter(
        Q(is_physical_critical=True) |
        Q(is_emotional_critical=True) |
        Q(is_intellectual_critical=True)
    ).count()
    
    # Date range
    date_stats = BiorhythmData.objects.aggregate(
        earliest_date=Min('date'),
        latest_date=Max('date')
    )
    
    # Cycle statistics
    cycle_stats = BiorhythmData.objects.aggregate(
        avg_physical=Avg('physical'),
        avg_emotional=Avg('emotional'),
        avg_intellectual=Avg('intellectual'),
        min_physical=Min('physical'),
        max_physical=Max('physical'),
        min_emotional=Min('emotional'),
        max_emotional=Max('emotional'),
        min_intellectual=Min('intellectual'),
        max_intellectual=Max('intellectual'),
    )
    
    # Recent activity (last 7 days)
    week_ago = timezone.now() - timedelta(days=7)
    recent_calculations = BiorhythmCalculation.objects.filter(
        calculation_date__gte=week_ago
    ).count()
    recent_people = Person.objects.filter(
        created_at__gte=week_ago
    ).count()
    
    stats_data = {
        'total_people': total_people,
        'total_calculations': total_calculations,
        'total_data_points': total_data_points,
        'total_critical_days': total_critical_days,
        'date_range': {
            'earliest': date_stats['earliest_date'],
            'latest': date_stats['latest_date'],
            'span_days': (date_stats['latest_date'] - date_stats['earliest_date']).days + 1 if date_stats['earliest_date'] and date_stats['latest_date'] else 0
        },
        'cycle_statistics': {
            'physical': {
                'average': round(cycle_stats['avg_physical'], 3) if cycle_stats['avg_physical'] else None,
                'min': round(cycle_stats['min_physical'], 3) if cycle_stats['min_physical'] else None,
                'max': round(cycle_stats['max_physical'], 3) if cycle_stats['max_physical'] else None,
            },
            'emotional': {
                'average': round(cycle_stats['avg_emotional'], 3) if cycle_stats['avg_emotional'] else None,
                'min': round(cycle_stats['min_emotional'], 3) if cycle_stats['min_emotional'] else None,
                'max': round(cycle_stats['max_emotional'], 3) if cycle_stats['max_emotional'] else None,
            },
            'intellectual': {
                'average': round(cycle_stats['avg_intellectual'], 3) if cycle_stats['avg_intellectual'] else None,
                'min': round(cycle_stats['min_intellectual'], 3) if cycle_stats['min_intellectual'] else None,
                'max': round(cycle_stats['max_intellectual'], 3) if cycle_stats['max_intellectual'] else None,
            },
        },
        'recent_activity': {
            'new_calculations_7_days': recent_calculations,
            'new_people_7_days': recent_people,
            'average_data_points_per_person': round(total_data_points / total_people, 2) if total_people > 0 else 0,
            'critical_days_percentage': round((total_critical_days / total_data_points * 100), 2) if total_data_points > 0 else 0
        }
    }
    
    serializer = StatisticsSerializer(stats_data)
    return Response(serializer.data)
