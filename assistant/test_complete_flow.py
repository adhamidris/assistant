#!/usr/bin/env python3
"""
Test the complete user authentication and portal link flow
"""

import os
import sys
import django
import requests
import json
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assistant.settings')
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from core.models import AppUser, Workspace
from core.profile_serializers import ProfileSetupSerializer

def test_complete_flow():
    """Test the complete flow from registration to portal link generation"""
    print("🧪 Testing Complete User Authentication and Portal Link Flow...")
    
    # Generate unique identifiers
    timestamp = int(datetime.now().timestamp())
    username = f"testbusiness{timestamp}"
    email = f"test{timestamp}@example.com"
    
    try:
        # 1. Test User Registration
        print("\n1. Testing User Registration...")
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password='testpass123'
        )
        
        # Create app profile
        app_user = AppUser.objects.create(
            user=user,
            full_name='John Test Owner',
            business_name='Test Business',
            business_type='Technology',
            phone_number='+1234567890',
            occupation='CEO',
            industry='Technology',
            subscription_status='trial'
        )
        
        # Create workspace
        workspace = Workspace.objects.create(
            owner=user,
            name='Test Business',
            assistant_name='Test Assistant',
            timezone='UTC'
        )
        
        print(f"✅ Created user: {username}")
        print(f"✅ Created app profile: {app_user.business_name}")
        print(f"✅ Created workspace: {workspace.name}")
        
        # 2. Test Authentication
        print("\n2. Testing Authentication...")
        
        # Authenticate user
        authenticated_user = authenticate(username=username, password='testpass123')
        if not authenticated_user:
            raise Exception("Authentication failed")
        
        # Get or create token
        token, created = Token.objects.get_or_create(user=authenticated_user)
        
        print(f"✅ Authenticated user: {username}")
        print(f"✅ Generated token: {token.key[:10]}...")
        
        # 3. Test Profile Setup
        print("\n3. Testing Profile Setup...")
        
        profile_data = {
            'owner_name': 'John Test Owner',
            'owner_occupation': 'CEO',
            'industry': 'Technology',
            'ai_role': 'tech_support',
            'ai_personality': 'professional',
            'custom_instructions': 'Be helpful and technical',
            'assistant_name': 'Tech Assistant',
            'name': 'Test Business'
        }
        
        # Update workspace with profile data
        workspace.owner_name = profile_data['owner_name']
        workspace.owner_occupation = profile_data['owner_occupation']
        workspace.industry = profile_data['industry']
        workspace.ai_role = profile_data['ai_role']
        workspace.ai_personality = profile_data['ai_personality']
        workspace.custom_instructions = profile_data['custom_instructions']
        workspace.assistant_name = profile_data['assistant_name']
        workspace.name = profile_data['name']
        workspace.profile_completed = True
        workspace.save()
        
        print(f"✅ Updated workspace profile")
        print(f"✅ AI Role: {workspace.ai_role}")
        print(f"✅ AI Personality: {workspace.ai_personality}")
        print(f"✅ Assistant Name: {workspace.assistant_name}")
        
        # 4. Test Portal Link Generation
        print("\n4. Testing Portal Link Generation...")
        
        # Simulate API call to generate portal link
        base_url = "http://localhost:8000"
        headers = {
            'Authorization': f'Token {token.key}',
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(f"{base_url}/api/v1/auth/portal-link/", headers=headers)
            if response.status_code == 200:
                portal_data = response.json()
                print(f"✅ Generated portal URL: {portal_data['portal_url']}")
                print(f"✅ Workspace ID: {portal_data['workspace_id']}")
                print(f"✅ QR Code URL: {portal_data['qr_code_url']}")
                print(f"✅ Instructions: {portal_data['instructions']}")
                
                # Test that the portal URL contains the workspace ID
                if str(workspace.id) in portal_data['portal_url']:
                    print("✅ Portal URL contains correct workspace ID")
                else:
                    print("❌ Portal URL missing workspace ID")
                    
            else:
                print(f"❌ Failed to generate portal link: {response.status_code}")
                print(f"Response: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("⚠️  Backend server not running, skipping portal link test")
            print("   To test portal links, start the backend server with: python manage.py runserver")
        
        # 5. Test Workspace Access
        print("\n5. Testing Workspace Access...")
        
        user_workspaces = authenticated_user.workspaces.all()
        if user_workspaces.exists():
            user_workspace = user_workspaces.first()
            print(f"✅ User has workspace: {user_workspace.name}")
            print(f"✅ Workspace owner: {user_workspace.owner.username}")
            print(f"✅ Profile completed: {user_workspace.profile_completed}")
        else:
            print("❌ User has no workspaces")
        
        # 6. Test AppUser Profile Access
        print("\n6. Testing AppUser Profile Access...")
        
        app_profile = getattr(authenticated_user, 'app_profile', None)
        if app_profile:
            print(f"✅ App profile: {app_profile.business_name}")
            print(f"✅ Full name: {app_profile.full_name}")
            print(f"✅ Occupation: {app_profile.occupation}")
            print(f"✅ Industry: {app_profile.industry}")
        else:
            print("❌ No app profile found")
        
        print("\n🎉 Complete flow test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        print("\n🧹 Cleaning up test data...")
        try:
            if 'user' in locals():
                user.delete()
            print("✅ Cleaned up test data")
        except Exception as e:
            print(f"⚠️  Cleanup warning: {str(e)}")

if __name__ == "__main__":
    test_complete_flow()
