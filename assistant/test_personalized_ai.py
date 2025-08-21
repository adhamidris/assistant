#!/usr/bin/env python
"""
Test script to verify personalized AI responses
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assistant.settings')
django.setup()

from core.models import Workspace, Contact, Conversation, Session
from messaging.models import Message
from messaging.tasks import generate_ai_response

def test_personalized_ai():
    print("🧪 Testing Personalized AI Responses...")
    
    try:
        # Get the demo workspace and update it with profile info
        workspace = Workspace.objects.first()
        
        # Test different AI roles
        test_profiles = [
            {
                'ai_role': 'banker',
                'ai_personality': 'professional',
                'owner_name': 'John Smith',
                'industry': 'Banking',
                'message': 'I need help with my savings account balance'
            },
            {
                'ai_role': 'medical',
                'ai_personality': 'empathetic',
                'owner_name': 'Dr. Sarah Johnson',
                'industry': 'Healthcare',
                'message': 'I want to schedule an appointment for a check-up'
            },
            {
                'ai_role': 'restaurant',
                'ai_personality': 'friendly',
                'owner_name': 'Marco Rossi',
                'industry': 'Food Service',
                'message': 'Do you have any vegetarian options on your menu?'
            }
        ]
        
        for i, profile in enumerate(test_profiles):
            print(f"\n🔄 Testing {profile['ai_role'].upper()} Assistant...")
            
            # Update workspace profile
            workspace.ai_role = profile['ai_role']
            workspace.ai_personality = profile['ai_personality']
            workspace.owner_name = profile['owner_name']
            workspace.industry = profile['industry']
            workspace.profile_completed = True
            workspace.save()
            
            # Get a contact and conversation
            contact = Contact.objects.filter(workspace=workspace).first()
            session, _ = Session.objects.get_or_create(
                contact=contact,
                defaults={'session_token': f'test_session_{i}', 'is_active': True}
            )
            conversation, _ = Conversation.objects.get_or_create(
                workspace=workspace,
                contact=contact,
                session=session,
                defaults={'status': 'active'}
            )
            
            # Create test message
            test_message = Message.objects.create(
                conversation=conversation,
                sender='client',
                message_type='text',
                text=profile['message'],
                status='sent'
            )
            
            print(f"📝 User Message: {profile['message']}")
            
            # Generate AI response
            generate_ai_response(str(test_message.id))
            
            # Get the AI response
            ai_message = Message.objects.filter(
                conversation=conversation,
                sender='assistant'
            ).order_by('-created_at').first()
            
            if ai_message:
                print(f"🤖 AI Response: {ai_message.text[:150]}...")
                print(f"✅ Role: {profile['ai_role']} | Personality: {profile['ai_personality']}")
            else:
                print("❌ No AI response generated")
        
        print("\n🎉 Personalized AI testing completed!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_personalized_ai()
