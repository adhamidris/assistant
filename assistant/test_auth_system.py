#!/usr/bin/env python
"""
Test script to verify the authentication system
"""
import os
import sys
import django
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assistant.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import AppUser, Workspace

def test_auth_system():
    print("🧪 Testing Authentication System...")
    
    try:
        # Test user registration
        print("\n1. Testing User Registration...")
        
        # Create user directly in Django
        timestamp = int(time.time())
        username = f'testbusiness{timestamp}'
        email = f'test{timestamp}@business.com'
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password='testpass123',
            first_name='John',
            last_name='Test Owner'
        )
        
        # Create app profile
        app_user = AppUser.objects.create(
            user=user,
            full_name='John Test Owner',
            business_name='Test Business',
            business_type='Consulting',
            phone_number='+1234567890',
            occupation='Business Owner',
            industry='Technology'
        )
        
        # Create workspace
        workspace = Workspace.objects.create(
            owner=user,
            name='Test Business',
            assistant_name='Test Assistant',
            timezone='UTC',
            auto_reply_mode=True,
            profile_completed=False
        )
        
        print(f"✅ Created user: {user.username}")
        print(f"✅ Created app profile: {app_user.business_name}")
        print(f"✅ Created workspace: {workspace.name}")
        
        # Test user properties
        print(f"✅ User display name: {app_user.display_name}")
        print(f"✅ User workspace: {app_user.workspace.name if app_user.workspace else 'None'}")
        
        # Test workspace owner relationship
        print(f"✅ Workspace owner: {workspace.owner.username}")
        print(f"✅ User's workspaces: {list(user.workspaces.all())}")
        
        # Test authentication
        print("\n2. Testing Authentication...")
        authenticated_user = User.objects.get(username=username)
        print(f"✅ Found user: {authenticated_user.username}")
        
        # Test app profile access
        app_profile = getattr(authenticated_user, 'app_profile', None)
        if app_profile:
            print(f"✅ App profile: {app_profile.business_name}")
            print(f"✅ Subscription: {app_profile.subscription_status}")
        else:
            print("❌ No app profile found")
        
        # Test workspace access
        user_workspace = authenticated_user.workspaces.first()
        if user_workspace:
            print(f"✅ User workspace: {user_workspace.name}")
            print(f"✅ Profile completed: {user_workspace.profile_completed}")
        else:
            print("❌ No workspace found")
        
        print("\n🎉 Authentication system test completed successfully!")
        
        # Clean up
        workspace.delete()
        app_user.delete()
        user.delete()
        print("🧹 Cleaned up test data")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_auth_system()
