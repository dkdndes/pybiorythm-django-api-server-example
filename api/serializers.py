"""
Django REST Framework serializers for biorhythm data API.

These serializers handle the conversion between Python objects and JSON
for the REST API endpoints with proper validation and formatting.
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from biorhythm_data.models import Person, BiorhythmCalculation, BiorhythmData, BiorhythmAnalysis


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model (for token authentication responses)."""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined']
        read_only_fields = ['id', 'date_joined']


class PersonSerializer(serializers.ModelSerializer):
    """Serializer for Person model with computed fields."""
    
    age_in_days = serializers.ReadOnlyField()
    biorhythm_data_count = serializers.SerializerMethodField()
    latest_calculation_date = serializers.SerializerMethodField()
    
    class Meta:
        model = Person
        fields = [
            'id', 'name', 'birthdate', 'email', 'notes',
            'created_at', 'updated_at', 'age_in_days', 
            'biorhythm_data_count', 'latest_calculation_date'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_biorhythm_data_count(self, obj):
        """Get count of biorhythm data points for this person."""
        return obj.get_biorhythm_data_count()
    
    def get_latest_calculation_date(self, obj):
        """Get the date of the most recent calculation."""
        latest_calc = obj.calculations.first()  # Already ordered by -calculation_date
        return latest_calc.calculation_date if latest_calc else None


class BiorhythmCalculationSerializer(serializers.ModelSerializer):
    """Serializer for BiorhythmCalculation model."""
    
    person_name = serializers.CharField(source='person.name', read_only=True)
    data_points_count = serializers.SerializerMethodField()
    date_range = serializers.SerializerMethodField()
    
    class Meta:
        model = BiorhythmCalculation
        fields = [
            'id', 'person', 'person_name', 'start_date', 'end_date', 
            'days_calculated', 'calculation_date', 'target_date',
            'pybiorythm_version', 'notes', 'data_points_count', 'date_range'
        ]
        read_only_fields = ['id', 'calculation_date']
    
    def get_data_points_count(self, obj):
        """Get count of data points for this calculation."""
        return obj.data_points.count()
    
    def get_date_range(self, obj):
        """Get human-readable date range."""
        return obj.date_range_str


class BiorhythmDataSerializer(serializers.ModelSerializer):
    """Serializer for BiorhythmData model with cycle analysis."""
    
    person_name = serializers.CharField(source='person.name', read_only=True)
    critical_cycles = serializers.ReadOnlyField()
    is_any_critical = serializers.ReadOnlyField()
    cycle_summary = serializers.ReadOnlyField()
    
    class Meta:
        model = BiorhythmData
        fields = [
            'id', 'person', 'person_name', 'calculation', 'date', 'days_alive',
            'physical', 'emotional', 'intellectual',
            'is_physical_critical', 'is_emotional_critical', 'is_intellectual_critical',
            'critical_cycles', 'is_any_critical', 'cycle_summary', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class BiorhythmDataSimpleSerializer(serializers.ModelSerializer):
    """Simplified serializer for BiorhythmData (for large datasets)."""
    
    class Meta:
        model = BiorhythmData
        fields = [
            'id', 'date', 'days_alive', 'physical', 'emotional', 'intellectual',
            'is_physical_critical', 'is_emotional_critical', 'is_intellectual_critical'
        ]


class BiorhythmAnalysisSerializer(serializers.ModelSerializer):
    """Serializer for BiorhythmAnalysis model."""
    
    person_name = serializers.CharField(source='person.name', read_only=True)
    date_range = serializers.SerializerMethodField()
    
    class Meta:
        model = BiorhythmAnalysis
        fields = [
            'id', 'person', 'person_name', 'analysis_type', 
            'start_date', 'end_date', 'date_range', 'analysis_date',
            'results', 'summary', 'data_points_analyzed', 'analysis_parameters'
        ]
        read_only_fields = ['id', 'analysis_date']
    
    def get_date_range(self, obj):
        """Get human-readable date range."""
        return f"{obj.start_date} to {obj.end_date}"


class PersonBiorhythmTimeseriesSerializer(serializers.Serializer):
    """
    Custom serializer for person's biorhythm timeseries data.
    Used for optimized timeseries API endpoints.
    """
    
    person_id = serializers.IntegerField()
    person_name = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    data_points = serializers.IntegerField()
    timeseries = BiorhythmDataSimpleSerializer(many=True)
    statistics = serializers.DictField(read_only=True)
    critical_days_summary = serializers.DictField(read_only=True)


class BiorhythmCalculationRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting new biorhythm calculations via API.
    Used for POST endpoints that trigger PyBiorythm calculations.
    """
    
    person_id = serializers.IntegerField()
    days = serializers.IntegerField(min_value=1, max_value=3650, default=365)
    target_date = serializers.DateField(required=False)
    notes = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    
    def validate_person_id(self, value):
        """Validate that the person exists."""
        try:
            Person.objects.get(id=value)
        except Person.DoesNotExist:
            raise serializers.ValidationError("Person with this ID does not exist.")
        return value


class TokenAuthSerializer(serializers.Serializer):
    """Serializer for token authentication requests."""
    
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        """Validate credentials and return user if valid."""
        from django.contrib.auth import authenticate
        
        username = attrs.get('username')
        password = attrs.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            if user:
                if user.is_active:
                    attrs['user'] = user
                    return attrs
                else:
                    raise serializers.ValidationError('User account is disabled.')
            else:
                raise serializers.ValidationError('Invalid credentials.')
        else:
            raise serializers.ValidationError('Must include username and password.')


class ApiInfoSerializer(serializers.Serializer):
    """Serializer for API information and documentation."""
    
    api_name = serializers.CharField()
    version = serializers.CharField()
    description = serializers.CharField()
    authentication = serializers.CharField()
    endpoints = serializers.DictField()
    pagination = serializers.DictField()
    server_time = serializers.DateTimeField()
    pybiorythm_available = serializers.BooleanField()


class StatisticsSerializer(serializers.Serializer):
    """Serializer for biorhythm statistics responses."""
    
    total_people = serializers.IntegerField()
    total_calculations = serializers.IntegerField()
    total_data_points = serializers.IntegerField()
    total_critical_days = serializers.IntegerField()
    date_range = serializers.DictField()
    cycle_statistics = serializers.DictField()
    recent_activity = serializers.DictField()