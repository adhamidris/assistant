from django.db import models
from django.utils import timezone
from core.models import Workspace, Contact
import uuid
from datetime import datetime, timedelta


class Appointment(models.Model):
    """Calendar booking model"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='appointments')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='appointments')
    
    # Appointment details
    title = models.CharField(max_length=255, default='Customer Appointment')
    description = models.TextField(blank=True, null=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Google Calendar integration
    google_event_id = models.CharField(max_length=255, blank=True, null=True)
    google_calendar_id = models.CharField(max_length=255, blank=True, null=True)
    google_meet_link = models.URLField(blank=True, null=True)
    
    # Location details
    location_type = models.CharField(max_length=20, choices=[
        ('in_person', 'In Person'),
        ('video_call', 'Video Call'),
        ('phone_call', 'Phone Call'),
    ], default='video_call')
    location_details = models.TextField(blank=True, null=True, help_text="Address or meeting link")
    
    # Customer information
    customer_email = models.EmailField(blank=True, null=True)
    customer_notes = models.TextField(blank=True, null=True)
    
    # Notification settings
    email_reminder = models.BooleanField(default=True)
    reminder_minutes_before = models.IntegerField(default=15)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'appointments'
        ordering = ['start_time']
        indexes = [
            models.Index(fields=['workspace', 'start_time']),
            models.Index(fields=['status', 'start_time']),
        ]
        
    def __str__(self):
        return f"{self.title} - {self.start_time.strftime('%Y-%m-%d %H:%M')} ({self.contact})"
    
    @property
    def duration_minutes(self):
        """Return appointment duration in minutes"""
        delta = self.end_time - self.start_time
        return int(delta.total_seconds() / 60)
    
    @property
    def is_upcoming(self):
        """Check if appointment is in the future"""
        return self.start_time > timezone.now()
    
    @property
    def is_today(self):
        """Check if appointment is today"""
        return self.start_time.date() == timezone.now().date()
    
    @property
    def time_until_appointment(self):
        """Get time until appointment"""
        if self.is_upcoming:
            delta = self.start_time - timezone.now()
            return delta
        return None


class AvailabilitySlot(models.Model):
    """Available time slots for booking"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='availability_slots')
    
    # Time slot details
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_available = models.BooleanField(default=True)
    
    # Booking constraints
    max_bookings = models.PositiveIntegerField(default=1)  # For multiple bookings per slot
    current_bookings = models.PositiveIntegerField(default=0)
    
    # Recurring slot information
    is_recurring = models.BooleanField(default=False)
    recurrence_rule = models.JSONField(blank=True, null=True)  # Store RRULE data
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'availability_slots'
        ordering = ['start_time']
        indexes = [
            models.Index(fields=['workspace', 'start_time', 'is_available']),
        ]
        
    def __str__(self):
        return f"Slot {self.start_time.strftime('%Y-%m-%d %H:%M')}-{self.end_time.strftime('%H:%M')} ({'Available' if self.is_available else 'Unavailable'})"
    
    @property
    def is_fully_booked(self):
        """Check if slot is fully booked"""
        return self.current_bookings >= self.max_bookings


class GoogleCalendarSync(models.Model):
    """Track Google Calendar synchronization"""
    SYNC_STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('error', 'Error'),
        ('disconnected', 'Disconnected'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.OneToOneField(Workspace, on_delete=models.CASCADE, related_name='google_calendar_sync')
    
    # Google OAuth credentials
    google_calendar_id = models.CharField(max_length=255)
    access_token = models.TextField()
    refresh_token = models.TextField()
    token_expires_at = models.DateTimeField()
    
    # Sync details
    last_sync_at = models.DateTimeField(null=True, blank=True)
    sync_token = models.CharField(max_length=255, blank=True, null=True)  # For incremental sync
    sync_status = models.CharField(max_length=20, choices=SYNC_STATUS_CHOICES, default='active')
    
    # Sync settings
    sync_direction = models.CharField(max_length=20, default='bidirectional', choices=[
        ('to_google', 'To Google Only'),
        ('from_google', 'From Google Only'),
        ('bidirectional', 'Bidirectional'),
    ])
    
    # Calendar settings
    calendar_name = models.CharField(max_length=255, blank=True, null=True)
    calendar_description = models.TextField(blank=True, null=True)
    
    # Sync status
    is_successful = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, null=True)
    error_count = models.IntegerField(default=0)
    
    # Statistics
    events_synced = models.PositiveIntegerField(default=0)
    appointments_created = models.PositiveIntegerField(default=0)
    appointments_updated = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'google_calendar_syncs'
        ordering = ['-last_sync_at']
    
    @property
    def is_token_expired(self):
        """Check if access token is expired"""
        return timezone.now() >= self.token_expires_at
    
    @property
    def needs_refresh(self):
        """Check if token needs refresh (expires in next 5 minutes)"""
        return timezone.now() >= (self.token_expires_at - timedelta(minutes=5))
        
    def __str__(self):
        return f"Google Calendar Sync for {self.workspace.name}"
