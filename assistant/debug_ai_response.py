#!/usr/bin/env python
"""
Debug script for AI response generation issue
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append('/Users/adham/assistant/assistant')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assistant.settings')
django.setup()

from core.models import Workspace
from messaging.models import Message, Conversation
from messaging.tasks import generate_ai_response

def debug_ai_response():
    print('🔍 AI Response Generation Debug')
    print('=' * 50)
    
    # Check workspaces
    print('📊 WORKSPACES:')
    workspaces = Workspace.objects.all()
    for ws in workspaces:
        print(f'  • {ws.name} (ID: {ws.id}) - Auto-reply: {ws.auto_reply_mode}')
    
    # Check latest messages
    print('\n📝 LATEST CLIENT MESSAGES:')
    latest_messages = Message.objects.filter(sender='client').order_by('-created_at')[:3]
    for msg in latest_messages:
        print(f'  • {msg.id} | {msg.text[:50]}... | Workspace: {msg.conversation.workspace.name} (auto-reply: {msg.conversation.workspace.auto_reply_mode})')
    
    if not latest_messages:
        print('  ❌ No client messages found')
        return
    
    # Test AI response generation
    latest_msg = latest_messages[0]
    print(f'\n🤖 TESTING AI RESPONSE GENERATION:')
    print(f'  Message ID: {latest_msg.id}')
    print(f'  Text: {latest_msg.text}')
    print(f'  Workspace: {latest_msg.conversation.workspace.name}')
    print(f'  Auto-reply enabled: {latest_msg.conversation.workspace.auto_reply_mode}')
    
    try:
        print('\n⏳ Calling generate_ai_response synchronously...')
        result = generate_ai_response(str(latest_msg.id))
        print(f'✅ Result: {result}')
        
        # Check if response was created
        print('\n📤 CHECKING FOR AI RESPONSE:')
        ai_responses = Message.objects.filter(
            conversation=latest_msg.conversation,
            sender='assistant',
            created_at__gt=latest_msg.created_at
        ).order_by('-created_at')
        
        if ai_responses:
            for response in ai_responses:
                print(f'  ✅ AI Response: {response.text[:100]}...')
        else:
            print('  ❌ No AI response found')
            
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    debug_ai_response()
