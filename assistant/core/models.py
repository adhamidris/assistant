from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.conf import settings
from django.utils.text import slugify
import uuid
from datetime import datetime, timezone
import re


class AppUser(models.Model):
    """
    Extended user model for APP users (business owners)
    These are the main users of the application who have their own workspaces
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link to Django's built-in User model
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='app_profile')
    
    # Business Information
    business_name = models.CharField(max_length=255, blank=True, null=True)
    business_type = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    
    # Profile Information
    full_name = models.CharField(max_length=255, blank=True, null=True)
    occupation = models.CharField(max_length=255, blank=True, null=True)
    industry = models.CharField(max_length=255, blank=True, null=True)
    
    # Account Status
    is_verified = models.BooleanField(default=False)
    subscription_status = models.CharField(max_length=20, choices=[
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ], default='trial')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'app_users'
        verbose_name = 'App User'
        verbose_name_plural = 'App Users'
    
    def __str__(self):
        return f"{self.full_name or self.user.username} ({self.business_name or 'No Business'})"
    
    @property
    def display_name(self):
        return self.full_name or self.user.username
    
    @property
    def username(self):
        return self.user.username
    
    @property
    def email(self):
        return self.user.email
    
    @property
    def workspace(self):
        """Get the user's primary workspace"""
        return self.user.workspaces.first()  # Each user has one primary workspace


class Workspace(models.Model):
    """Business account/workspace model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link to the APP user (business owner)
    owner = models.ForeignKey(
        'auth.User', 
        on_delete=models.CASCADE, 
        related_name='workspaces',
        null=True, blank=True  # Temporary for migration
    )
    
    name = models.CharField(max_length=255)
    timezone = models.CharField(max_length=50, default='UTC')
    auto_reply_mode = models.BooleanField(default=True)
    assistant_name = models.CharField(max_length=100, default='Assistant')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Google Calendar Integration
    google_calendar_connected = models.BooleanField(default=False)
    google_refresh_token = models.TextField(blank=True, null=True)
    google_calendar_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Business Hours (stored as JSON or separate model if complex)
    business_hours = models.JSONField(default=dict, blank=True)
    
    # Owner Profile for AI Personalization
    owner_name = models.CharField(max_length=255, blank=True, null=True)
    owner_occupation = models.CharField(max_length=255, blank=True, null=True)
    industry = models.CharField(max_length=255, blank=True, null=True)
    ai_role = models.CharField(max_length=100, choices=[
        ('general', 'General Assistant'),
        ('banker', 'Banking Assistant'),
        ('medical', 'Medical Assistant'),
        ('legal', 'Legal Assistant'),
        ('real_estate', 'Real Estate Assistant'),
        ('restaurant', 'Restaurant Assistant'),
        ('retail', 'Retail Assistant'),
        ('tech_support', 'Technical Support'),
        ('secretary', 'Personal Secretary'),
        ('customer_service', 'Customer Service'),
        ('consultant', 'Business Consultant'),
        ('educator', 'Educational Assistant'),
    ], default='general')
    ai_personality = models.CharField(max_length=100, choices=[
        ('professional', 'Professional'),
        ('friendly', 'Friendly'),
        ('formal', 'Formal'),
        ('casual', 'Casual'),
        ('empathetic', 'Empathetic'),
        ('direct', 'Direct'),
    ], default='professional')
    custom_instructions = models.TextField(blank=True, null=True, help_text="Custom instructions for AI behavior")
    profile_completed = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'workspaces'
        
    def __str__(self):
        return self.name
    
    @property
    def portal_slug(self):
        """Generate a user-friendly portal URL slug"""
        try:
            # Get the AppUser profile
            app_user = self.owner.app_profile
            
            # If it's a business user (has business_name), use: company-name/employee-name
            if app_user.business_name and app_user.business_name.strip():
                company_slug = slugify(app_user.business_name)
                employee_slug = slugify(app_user.full_name or self.owner.username)
                return f"{company_slug}/{employee_slug}"
            
            # If it's a personal user (no business_name), use: user-name
            else:
                user_slug = slugify(app_user.full_name or self.owner.username)
                return user_slug
                
        except Exception:
            # Fallback to workspace ID if anything goes wrong
            return str(self.id)
    
    @property
    def portal_url(self):
        """Get the full portal URL"""
        from django.conf import settings
        base_url = getattr(settings, 'FRONTEND_BASE_URL', 'http://localhost:3000')
        return f"{base_url}/portal/{self.portal_slug}"
    
    def ensure_unique_portal_slug(self):
        """Ensure the portal slug is unique by adding a number suffix if needed"""
        base_slug = self.portal_slug
        
        # Check if this slug is already taken by another workspace
        counter = 1
        test_slug = base_slug
        
        while Workspace.objects.exclude(id=self.id).filter(
            owner__app_profile__business_name__isnull=False
        ).annotate(
            computed_slug=models.Case(
                models.When(
                    owner__app_profile__business_name__isnull=False,
                    then=models.Concat(
                        models.F('owner__app_profile__business_name'),
                        models.Value('/'),
                        models.Coalesce(
                            models.F('owner__app_profile__full_name'),
                            models.F('owner__username')
                        )
                    )
                ),
                default=models.Coalesce(
                    models.F('owner__app_profile__full_name'),
                    models.F('owner__username')
                )
            )
        ).filter(computed_slug=test_slug).exists():
            counter += 1
            test_slug = f"{base_slug}-{counter}"
        
        return test_slug


class Contact(models.Model):
    """Customer identity model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='contacts')
    
    # Phone number in E.164 format
    phone_validator = RegexValidator(
        regex=r'^\+[1-9]\d{1,14}$',
        message='Phone number must be in E.164 format (e.g., +1234567890)'
    )
    phone_e164 = models.CharField(max_length=16, validators=[phone_validator])
    
    name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'contacts'
        unique_together = ['workspace', 'phone_e164']
        
    def __str__(self):
        return f"{self.name or 'Unknown'} ({self.phone_e164[-4:]})"  # Mask phone number
    
    @property
    def masked_phone(self):
        """Return masked phone number showing only last 2 digits"""
        return f"***{self.phone_e164[-2:]}"


class Session(models.Model):
    """Chat session tracking model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='sessions')
    session_token = models.CharField(max_length=255, unique=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'sessions'
        
    def __str__(self):
        return f"Session {self.session_token[:8]}... for {self.contact}"


class Conversation(models.Model):
    """Conversation thread model"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('resolved', 'Resolved'),
        ('archived', 'Archived'),
    ]
    
    INTENT_CHOICES = [
        ('inquiry', 'General Inquiry'),
        ('request', 'Service Request'),
        ('complaint', 'Complaint'),
        ('appointment', 'Appointment Request'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='conversations')
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='conversations')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='conversations')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    last_intent = models.CharField(max_length=20, choices=INTENT_CHOICES, default='other')
    
    # AI Analysis Fields
    summary = models.TextField(blank=True, null=True, help_text="AI-generated conversation summary")
    key_points = models.JSONField(default=list, blank=True, help_text="Key points extracted from conversation")
    resolution_status = models.CharField(max_length=20, blank=True, null=True, help_text="AI-determined resolution status")
    action_items = models.JSONField(default=list, blank=True, help_text="Action items identified by AI")
    sentiment_score = models.IntegerField(default=3, help_text="Customer satisfaction score (1-5)")
    sentiment_data = models.JSONField(default=dict, blank=True, help_text="Detailed sentiment analysis results")
    extracted_entities = models.JSONField(default=dict, blank=True, help_text="Entities extracted from conversation")
    conversation_metrics = models.JSONField(default=dict, blank=True, help_text="Conversation metrics and statistics")
    insights_generated_at = models.DateTimeField(blank=True, null=True, help_text="When AI insights were last generated")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'conversations'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['workspace', '-updated_at']),
            models.Index(fields=['status', '-updated_at']),
            models.Index(fields=['sentiment_score', '-updated_at']),
            models.Index(fields=['resolution_status', '-updated_at']),
        ]
    
    @property
    def has_ai_insights(self):
        """Check if AI insights have been generated"""
        return self.insights_generated_at is not None
    
    @property
    def sentiment_label(self):
        """Get human-readable sentiment label"""
        if not self.sentiment_data:
            return 'Unknown'
        return self.sentiment_data.get('overall_sentiment', 'neutral').replace('_', ' ').title()
    
    @property
    def message_count(self):
        """Get the number of messages in this conversation"""
        return self.messages.count()
        
    def __str__(self):
        return f"Conversation {str(self.id)[:8]}... with {self.contact}"
