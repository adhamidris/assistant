"""
Calendar integration serializers
"""

from rest_framework import serializers
from django.utils import timezone
from datetime import datetime, timedelta

from .models import Appointment, AvailabilitySlot, GoogleCalendarSync


class AppointmentSerializer(serializers.ModelSerializer):
    """Serializer for Appointment model"""
    
    contact_name = serializers.CharField(source='contact.name', read_only=True)
    contact_phone = serializers.CharField(source='contact.masked_phone', read_only=True)
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    duration_minutes = serializers.ReadOnlyField()
    is_upcoming = serializers.ReadOnlyField()
    is_today = serializers.ReadOnlyField()
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'workspace', 'contact', 'title', 'description',
            'start_time', 'end_time', 'status', 'location_type',
            'location_details', 'customer_email', 'customer_notes',
            'google_event_id', 'google_meet_link', 'email_reminder',
            'reminder_minutes_before', 'created_at', 'updated_at',
            # Read-only fields
            'contact_name', 'contact_phone', 'workspace_name',
            'duration_minutes', 'is_upcoming', 'is_today'
        ]
        read_only_fields = ['id', 'workspace', 'google_event_id', 'google_meet_link', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate appointment data"""
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        if start_time and end_time:
            if start_time >= end_time:
                raise serializers.ValidationError("End time must be after start time")
            
            if start_time < timezone.now():
                raise serializers.ValidationError("Start time cannot be in the past")
            
            # Check duration is reasonable (15 minutes to 8 hours)
            duration = end_time - start_time
            if duration < timedelta(minutes=15):
                raise serializers.ValidationError("Appointment must be at least 15 minutes long")
            if duration > timedelta(hours=8):
                raise serializers.ValidationError("Appointment cannot be longer than 8 hours")
        
        return data


class AvailabilitySlotSerializer(serializers.ModelSerializer):
    """Serializer for AvailabilitySlot model"""
    
    weekday_display = serializers.CharField(source='get_weekday_display', read_only=True)
    
    class Meta:
        model = AvailabilitySlot
        fields = [
            'id', 'workspace', 'weekday', 'weekday_display',
            'start_time', 'end_time', 'is_available',
            'max_bookings', 'current_bookings', 'is_recurring',
            'recurrence_rule', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'workspace', 'current_bookings', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Validate availability slot data"""
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        
        if start_time and end_time:
            if start_time >= end_time:
                raise serializers.ValidationError("End time must be after start time")
        
        return data


class GoogleCalendarSyncSerializer(serializers.ModelSerializer):
    """Serializer for GoogleCalendarSync model"""
    
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    is_token_expired = serializers.ReadOnlyField()
    needs_refresh = serializers.ReadOnlyField()
    
    class Meta:
        model = GoogleCalendarSync
        fields = [
            'id', 'workspace', 'workspace_name', 'google_calendar_id',
            'last_sync_at', 'sync_status', 'sync_direction',
            'calendar_name', 'calendar_description', 'is_successful',
            'error_message', 'error_count', 'events_synced',
            'appointments_created', 'appointments_updated',
            'created_at', 'updated_at', 'is_token_expired', 'needs_refresh'
        ]
        read_only_fields = [
            'id', 'workspace', 'google_calendar_id', 'last_sync_at',
            'is_successful', 'error_message', 'error_count',
            'events_synced', 'appointments_created', 'appointments_updated',
            'created_at', 'updated_at', 'is_token_expired', 'needs_refresh'
        ]


class AppointmentBookingSerializer(serializers.Serializer):
    """Serializer for booking appointments via API"""
    
    workspace_id = serializers.UUIDField()
    phone_number = serializers.CharField(max_length=16)
    customer_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    customer_email = serializers.EmailField(required=False, allow_blank=True)
    
    title = serializers.CharField(max_length=255, default='Customer Appointment')
    description = serializers.CharField(required=False, allow_blank=True)
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    
    location_type = serializers.ChoiceField(
        choices=['in_person', 'video_call', 'phone_call'],
        default='video_call'
    )
    location_details = serializers.CharField(required=False, allow_blank=True)
    customer_notes = serializers.CharField(required=False, allow_blank=True)
    
    def validate_phone_number(self, value):
        """Validate phone number format (E.164)"""
        if not value.startswith('+'):
            raise serializers.ValidationError("Phone number must be in E.164 format (e.g., +1234567890)")
        
        # Remove '+' and check if remaining characters are digits
        digits = value[1:]
        if not digits.isdigit():
            raise serializers.ValidationError("Phone number must contain only digits after the '+' sign")
        
        if len(digits) < 10 or len(digits) > 15:
            raise serializers.ValidationError("Phone number must be between 10 and 15 digits")
        
        return value
    
    def validate(self, data):
        """Validate booking data"""
        start_time = data['start_time']
        end_time = data['end_time']
        
        if start_time >= end_time:
            raise serializers.ValidationError("End time must be after start time")
        
        if start_time < timezone.now():
            raise serializers.ValidationError("Start time cannot be in the past")
        
        # Check duration is reasonable
        duration = end_time - start_time
        if duration < timedelta(minutes=15):
            raise serializers.ValidationError("Appointment must be at least 15 minutes long")
        if duration > timedelta(hours=8):
            raise serializers.ValidationError("Appointment cannot be longer than 8 hours")
        
        return data


class AvailableSlotSerializer(serializers.Serializer):
    """Serializer for available time slots"""
    
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    duration_minutes = serializers.IntegerField()
    
    def to_representation(self, instance):
        """Convert datetime objects to ISO format strings"""
        return {
            'start_time': instance['start_time'].isoformat(),
            'end_time': instance['end_time'].isoformat(),
            'duration_minutes': instance['duration_minutes']
        }


class AppointmentSummarySerializer(serializers.ModelSerializer):
    """Simplified serializer for appointment summaries"""
    
    contact_name = serializers.CharField(source='contact.name', read_only=True)
    duration_minutes = serializers.ReadOnlyField()
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'title', 'start_time', 'end_time', 'status',
            'contact_name', 'duration_minutes', 'location_type'
        ]

