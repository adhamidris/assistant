#!/usr/bin/env python
"""
Test script to debug message flow and AI response generation
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

def test_message_flow():
    print("🧪 Testing Message Flow and AI Response...")
    
    try:
        # Get the demo workspace
        workspace = Workspace.objects.first()
        print(f"✅ Found workspace: {workspace.name}")
        print(f"✅ Auto-reply enabled: {workspace.auto_reply_mode}")
        
        # Get a contact
        contact = Contact.objects.filter(workspace=workspace).first()
        if not contact:
            print("❌ No contacts found")
            return
        print(f"✅ Found contact: {contact.name} ({contact.phone_e164})")
        
        # Get or create a session
        session, created = Session.objects.get_or_create(
            contact=contact,
            defaults={
                'session_token': 'test_session_123',
                'is_active': True
            }
        )
        print(f"✅ Session: {session.session_token} (created: {created})")
        
        # Get or create a conversation
        conversation, created = Conversation.objects.get_or_create(
            workspace=workspace,
            contact=contact,
            session=session,
            defaults={'status': 'active'}
        )
        print(f"✅ Conversation: {conversation.id} (created: {created})")
        
        # Create a test message
        test_message = Message.objects.create(
            conversation=conversation,
            sender='client',
            message_type='text',
            text='Hello, I need help with my account',
            status='sent'
        )
        print(f"✅ Created test message: {test_message.id}")
        
        # Manually trigger AI response generation
        print("🤖 Triggering AI response generation...")
        generate_ai_response(str(test_message.id))
        
        # Check if AI response was created
        ai_messages = Message.objects.filter(
            conversation=conversation,
            sender='assistant'
        ).order_by('-created_at')
        
        if ai_messages.exists():
            latest_ai_message = ai_messages.first()
            print(f"✅ AI Response created: {latest_ai_message.text[:100]}...")
            print(f"✅ Message ID: {latest_ai_message.id}")
        else:
            print("❌ No AI response was created")
            
        print("\n📊 Conversation Messages:")
        messages = Message.objects.filter(conversation=conversation).order_by('created_at')
        for msg in messages:
            print(f"  {msg.sender}: {msg.text[:50]}... (ID: {msg.id})")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_message_flow()
