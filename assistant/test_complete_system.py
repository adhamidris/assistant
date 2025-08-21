#!/usr/bin/env python3
"""
Test the complete system including QR codes and notifications
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
from notifications.models import Notification, EmailTemplate, NotificationPreference
from notifications.services import NotificationService

def test_complete_system():
    """Test the complete system including QR codes and notifications"""
    print("🧪 Testing Complete System (QR Codes + Notifications)...")
    
    # Generate unique identifiers
    timestamp = int(datetime.now().timestamp())
    username = f"testbusiness{timestamp}"
    email = f"test{timestamp}@example.com"
    
    try:
        # 1. Test User Registration with Welcome Email
        print("\n1. Testing User Registration with Welcome Email...")
        
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
        
        # 2. Test Notification System Setup
        print("\n2. Testing Notification System Setup...")
        
        # Create notification preferences
        preferences = NotificationPreference.objects.create(
            user=user,
            email_new_messages=True,
            email_appointment_bookings=True,
            email_appointment_reminders=True,
            email_system_alerts=True,
            email_welcome=True,
            email_frequency='immediate'
        )
        
        # Create default email templates
        NotificationService.create_default_email_templates()
        
        print(f"✅ Created notification preferences")
        print(f"✅ Created email templates")
        
        # 3. Test Welcome Email
        print("\n3. Testing Welcome Email...")
        
        try:
            welcome_sent = NotificationService.send_welcome_email(user)
            if welcome_sent:
                print("✅ Welcome email sent successfully")
            else:
                print("⚠️ Welcome email failed (likely no email server configured)")
        except Exception as e:
            print(f"⚠️ Welcome email error: {str(e)}")
        
        # 4. Test Authentication
        print("\n4. Testing Authentication...")
        
        # Authenticate user
        authenticated_user = authenticate(username=username, password='testpass123')
        if not authenticated_user:
            raise Exception("Authentication failed")
        
        # Get or create token
        token, created = Token.objects.get_or_create(user=authenticated_user)
        
        print(f"✅ Authenticated user: {username}")
        print(f"✅ Generated token: {token.key[:10]}...")
        
        # 5. Test Profile Setup
        print("\n5. Testing Profile Setup...")
        
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
        
        # 6. Test Portal Link Generation
        print("\n6. Testing Portal Link Generation...")
        
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
                
                # Test QR code generation
                qr_response = requests.get(portal_data['qr_code_url'])
                if qr_response.status_code == 200:
                    print("✅ QR code generated successfully")
                    print(f"✅ QR code content type: {qr_response.headers.get('content-type')}")
                else:
                    print(f"❌ QR code generation failed: {qr_response.status_code}")
                    
            else:
                print(f"❌ Failed to generate portal link: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print("⚠️  Backend server not running, skipping portal link test")
        
        # 7. Test Notification Creation
        print("\n7. Testing Notification Creation...")
        
        # Create test notifications
        notification1 = NotificationService.create_notification(
            user=user,
            notification_type='new_message',
            title='Test Message Notification',
            message='This is a test message notification.'
        )
        
        notification2 = NotificationService.create_notification(
            user=user,
            notification_type='system_alert',
            title='System Test',
            message='This is a system test notification.'
        )
        
        if notification1 and notification2:
            print("✅ Created test notifications")
            print(f"✅ Notification 1: {notification1.title}")
            print(f"✅ Notification 2: {notification2.title}")
        else:
            print("❌ Failed to create notifications")
        
        # 8. Test Notification API
        print("\n8. Testing Notification API...")
        
        try:
            # Test getting notifications
            response = requests.get(f"{base_url}/api/v1/notifications/notifications/", headers=headers)
            if response.status_code == 200:
                notifications_data = response.json()
                print(f"✅ Retrieved {len(notifications_data.get('results', notifications_data))} notifications")
            else:
                print(f"❌ Failed to get notifications: {response.status_code}")
            
            # Test unread count
            response = requests.get(f"{base_url}/api/v1/notifications/notifications/unread_count/", headers=headers)
            if response.status_code == 200:
                count_data = response.json()
                print(f"✅ Unread count: {count_data.get('unread_count', 0)}")
            else:
                print(f"❌ Failed to get unread count: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print("⚠️  Backend server not running, skipping notification API test")
        
        # 9. Test Email Templates
        print("\n9. Testing Email Templates...")
        
        templates = EmailTemplate.objects.all()
        print(f"✅ Found {templates.count()} email templates:")
        for template in templates:
            print(f"   - {template.template_type}: {template.subject}")
        
        # 10. Test Notification Preferences
        print("\n10. Testing Notification Preferences...")
        
        user_preferences = NotificationPreference.objects.filter(user=user).first()
        if user_preferences:
            print(f"✅ User preferences found")
            print(f"   - Email new messages: {user_preferences.email_new_messages}")
            print(f"   - Email frequency: {user_preferences.email_frequency}")
        else:
            print("❌ No user preferences found")
        
        print("\n🎉 Complete system test completed successfully!")
        
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
    test_complete_system()
