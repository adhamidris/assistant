from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

class Notification(models.Model):
    """Base notification model"""
    NOTIFICATION_TYPES = [
        ('new_message', 'New Message'),
        ('appointment_booking', 'Appointment Booking'),
        ('appointment_reminder', 'Appointment Reminder'),
        ('system_alert', 'System Alert'),
        ('welcome', 'Welcome'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Related object references
    related_conversation = models.ForeignKey(
        'core.Conversation', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='notifications'
    )
    related_appointment = models.ForeignKey(
        'calendar_integration.Appointment', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='notifications'
    )
    
    class Meta:
        ordering = ['-created_at']
        db_table = 'notifications'
    
    def __str__(self):
        return f"{self.notification_type} - {self.user.username}"

class EmailTemplate(models.Model):
    """Email template for notifications"""
    TEMPLATE_TYPES = [
        ('new_message', 'New Message Notification'),
        ('appointment_booking', 'Appointment Booking Confirmation'),
        ('appointment_reminder', 'Appointment Reminder'),
        ('welcome', 'Welcome Email'),
        ('system_alert', 'System Alert'),
    ]
    
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPES, unique=True)
    subject = models.CharField(max_length=255)
    html_content = models.TextField()
    text_content = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'email_templates'
    
    def __str__(self):
        return f"{self.template_type} - {self.subject}"

class NotificationPreference(models.Model):
    """User notification preferences"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Email preferences
    email_new_messages = models.BooleanField(default=True)
    email_appointment_bookings = models.BooleanField(default=True)
    email_appointment_reminders = models.BooleanField(default=True)
    email_system_alerts = models.BooleanField(default=True)
    email_welcome = models.BooleanField(default=True)
    
    # Frequency preferences
    email_frequency = models.CharField(
        max_length=20,
        choices=[
            ('immediate', 'Immediate'),
            ('hourly', 'Hourly'),
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
        ],
        default='immediate'
    )
    
    # Time preferences
    quiet_hours_start = models.TimeField(default='22:00')
    quiet_hours_end = models.TimeField(default='08:00')
    timezone = models.CharField(max_length=50, default='UTC')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notification_preferences'
    
    def __str__(self):
        return f"Preferences for {self.user.username}"
