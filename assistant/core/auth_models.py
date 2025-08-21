"""
Authentication models for APP users (business owners)
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

class AppUser(AbstractUser):
    """
    Custom user model for APP users (business owners)
    These are the main users of the application who have their own workspaces
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
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
        return f"{self.full_name or self.username} ({self.business_name or 'No Business'})"
    
    @property
    def display_name(self):
        return self.full_name or self.username
    
    @property
    def workspace(self):
        """Get the user's workspace"""
        return self.workspaces.first()  # Each user has one primary workspace
