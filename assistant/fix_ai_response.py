#!/usr/bin/env python
"""
Fix AI response generation issues
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append('/Users/adham/assistant/assistant')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assistant.settings')

# Set the DeepSeek API key in environment if not already set
if not os.environ.get('DEEPSEEK_API_KEY'):
    os.environ['DEEPSEEK_API_KEY'] = 'sk-8283fa77a01e4f859b8491eff28ef6a3'

django.setup()

from django.conf import settings
from core.models import Workspace
from messaging.models import Message, Conversation
from messaging.tasks import generate_ai_response
from messaging.deepseek_client import DeepSeekClient

def fix_ai_response_issues():
    print('🔧 AI Response Generation Fix')
    print('=' * 50)
    
    # 1. Check API Key Configuration
    print('🔑 CHECKING API KEY CONFIGURATION:')
    deepseek_key = getattr(settings, 'DEEPSEEK_API_KEY', None) or os.environ.get('DEEPSEEK_API_KEY')
    if deepseek_key:
        print(f'  ✅ DeepSeek API Key: {deepseek_key[:10]}...')
    else:
        print('  ❌ DeepSeek API Key NOT found')
        return
    
    # 2. Test DeepSeek Client
    print('\n🤖 TESTING DEEPSEEK CLIENT:')
    try:
        client = DeepSeekClient()
        test_response = client.generate_response(
            prompt="Hello, this is a test.",
            system_prompt="You are a helpful assistant. Respond with 'Test successful!'"
        )
        print(f'  ✅ DeepSeek Client Test: {test_response[:50]}...')
    except Exception as e:
        print(f'  ❌ DeepSeek Client Error: {e}')
        return
    
    # 3. Enable Auto-Reply for All Workspaces
    print('\n⚙️ ENABLING AUTO-REPLY FOR ALL WORKSPACES:')
    workspaces = Workspace.objects.all()
    for ws in workspaces:
        if not ws.auto_reply_mode:
            ws.auto_reply_mode = True
            ws.save()
            print(f'  ✅ Enabled auto-reply for: {ws.name}')
        else:
            print(f'  ☑️ Auto-reply already enabled for: {ws.name}')
    
    # 4. Create Test Message and Generate Response
    print('\n💬 TESTING MESSAGE CREATION AND AI RESPONSE:')
    if workspaces:
        workspace = workspaces.first()
        
        # Get or create a test conversation
        from core.models import Contact, Session
        
        # Get or create a test contact
        test_contact, created = Contact.objects.get_or_create(
            workspace=workspace,
            name="Test User",
            defaults={
                'phone_number': '+1234567890',
                'email': 'test@example.com'
            }
        )
        
        # Get or create a test session
        test_session, created = Session.objects.get_or_create(
            contact=test_contact,
            defaults={'session_token': 'test-session-token-123'}
        )
        
        # Get or create a test conversation
        test_conversation, created = Conversation.objects.get_or_create(
            workspace=workspace,
            session=test_session,
            contact=test_contact,
            defaults={'status': 'active'}
        )
        
        # Create a test message
        test_message = Message.objects.create(
            conversation=test_conversation,
            sender='client',
            message_type='text',
            text='Hello, can you help me with my account?',
            status='sent'
        )
        
        print(f'  ✅ Created test message: {test_message.id}')
        print(f'  📝 Message text: {test_message.text}')
        print(f'  🏢 Workspace: {workspace.name} (auto-reply: {workspace.auto_reply_mode})')
        
        # Test AI response generation
        print('\n🤖 GENERATING AI RESPONSE:')
        try:
            result = generate_ai_response(str(test_message.id))
            print(f'  ✅ AI Response Task Result: {result}')
            
            # Check if AI response was created
            ai_responses = Message.objects.filter(
                conversation=test_conversation,
                sender='assistant',
                created_at__gt=test_message.created_at
            ).order_by('-created_at')
            
            if ai_responses:
                latest_response = ai_responses.first()
                print(f'  ✅ AI Response Created: {latest_response.text[:100]}...')
                print(f'  📅 Response ID: {latest_response.id}')
            else:
                print('  ❌ No AI response was created')
                
        except Exception as e:
            print(f'  ❌ AI Response Generation Error: {e}')
            import traceback
            traceback.print_exc()
    
    print('\n🎉 AI Response Fix Complete!')
    print('Now try sending a message through the portal - AI should respond!')

if __name__ == '__main__':
    fix_ai_response_issues()
