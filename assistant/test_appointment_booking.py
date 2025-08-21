#!/usr/bin/env python
"""
Test script to verify appointment booking system
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
from calendar_integration.models import Appointment

def test_appointment_booking():
    print("🧪 Testing Appointment Booking System...")
    
    try:
        # Get the demo workspace and set it up as medical assistant
        workspace = Workspace.objects.first()
        workspace.ai_role = 'medical'
        workspace.ai_personality = 'empathetic'
        workspace.owner_name = 'Dr. Sarah Johnson'
        workspace.industry = 'Healthcare'
        workspace.save()
        
        # Get a contact and conversation
        contact = Contact.objects.filter(workspace=workspace).first()
        session, _ = Session.objects.get_or_create(
            contact=contact,
            defaults={'session_token': 'appointment_test_session', 'is_active': True}
        )
        conversation, _ = Conversation.objects.get_or_create(
            workspace=workspace,
            contact=contact,
            session=session,
            defaults={'status': 'active'}
        )
        
        # Test appointment booking messages
        test_messages = [
            "I'd like to book an appointment for tomorrow at 2 PM",
            "Can I schedule a consultation for next week?",
            "I need to see the doctor for a checkup"
        ]
        
        initial_appointment_count = Appointment.objects.filter(workspace=workspace).count()
        print(f"📊 Initial appointments in database: {initial_appointment_count}")
        
        for i, message_text in enumerate(test_messages):
            print(f"\n🔄 Testing appointment message {i+1}: '{message_text}'")
            
            # Create test message
            test_message = Message.objects.create(
                conversation=conversation,
                sender='client',
                message_type='text',
                text=message_text,
                status='sent'
            )
            
            # Generate AI response
            generate_ai_response(str(test_message.id))
            
            # Check if appointment was created
            new_appointments = Appointment.objects.filter(workspace=workspace).count()
            if new_appointments > initial_appointment_count:
                latest_appointment = Appointment.objects.filter(workspace=workspace).order_by('-created_at').first()
                print(f"✅ Appointment created: {latest_appointment.title}")
                print(f"   📅 Scheduled for: {latest_appointment.start_time}")
                print(f"   👤 Contact: {latest_appointment.contact.name}")
                print(f"   📝 Notes: {latest_appointment.customer_notes[:100]}...")
                initial_appointment_count = new_appointments
            else:
                print("❌ No appointment was created")
            
            # Check AI response
            ai_messages = Message.objects.filter(
                conversation=conversation,
                sender='assistant'
            ).order_by('-created_at')
            
            if ai_messages.exists():
                latest_response = ai_messages.first()
                print(f"🤖 AI Response: {latest_response.text[:100]}...")
                
                # Check for system confirmation message
                system_messages = Message.objects.filter(
                    conversation=conversation,
                    sender='assistant',
                    message_type='system'
                ).order_by('-created_at')
                
                if system_messages.exists():
                    confirmation = system_messages.first()
                    print(f"✅ System Confirmation: {confirmation.text}")
        
        final_appointment_count = Appointment.objects.filter(workspace=workspace).count()
        print(f"\n📊 Final appointments in database: {final_appointment_count}")
        print(f"🎉 Created {final_appointment_count - initial_appointment_count} new appointments!")
        
        # List all appointments
        print("\n📅 All Appointments:")
        appointments = Appointment.objects.filter(workspace=workspace).order_by('-created_at')
        for apt in appointments:
            print(f"  - {apt.title} | {apt.start_time} | {apt.contact.name} | Status: {apt.status}")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_appointment_booking()
