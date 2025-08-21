#!/usr/bin/env python3
"""
Test script for Message Details API endpoints
"""

import requests
import json

# Configuration
BASE_URL = 'http://localhost:8000'
API_BASE = f'{BASE_URL}/api/v1'

def test_message_details_endpoints():
    """Test the message details API endpoints"""
    
    print("🧪 Testing Message Details API Endpoints")
    print("=" * 50)
    
    # First, let's get some conversations to find messages
    try:
        print("\n1. Getting conversations...")
        response = requests.get(f'{API_BASE}/core/conversations/')
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            conversations = response.json()
            print(f"Found {len(conversations.get('results', []))} conversations")
            
            if conversations.get('results'):
                # Get the first conversation
                conversation = conversations['results'][0]
                conversation_id = conversation['id']
                print(f"Using conversation: {conversation_id}")
                
                # Get messages for this conversation
                print("\n2. Getting messages...")
                messages_response = requests.get(f'{API_BASE}/messaging/messages/', params={'conversation': conversation_id})
                print(f"Status: {messages_response.status_code}")
                
                if messages_response.status_code == 200:
                    messages = messages_response.json()
                    print(f"Found {len(messages.get('results', []))} messages")
                    
                    if messages.get('results'):
                        # Test message details endpoint
                        message = messages['results'][0]
                        message_id = message['id']
                        print(f"\n3. Testing message details for: {message_id}")
                        
                        details_response = requests.get(f'{API_BASE}/messaging/messages/{message_id}/details/')
                        print(f"Status: {details_response.status_code}")
                        
                        if details_response.status_code == 200:
                            details = details_response.json()
                            print("✅ Message details retrieved successfully!")
                            print(f"Message: {details.get('text', 'No text')[:50]}...")
                            print(f"Sender: {details.get('sender_display')}")
                            print(f"Status: {details.get('status_display')}")
                            print(f"Type: {details.get('type_display')}")
                        else:
                            print(f"❌ Failed to get message details: {details_response.text}")
                        
                        # Test message status update
                        print(f"\n4. Testing message status update...")
                        status_data = {'status': 'sent'}
                        status_response = requests.put(f'{API_BASE}/messaging/messages/{message_id}/status/', json=status_data)
                        print(f"Status: {status_response.status_code}")
                        
                        if status_response.status_code == 200:
                            print("✅ Message status updated successfully!")
                        else:
                            print(f"❌ Failed to update message status: {status_response.text}")
                        
                        # Test message reply
                        print(f"\n5. Testing message reply...")
                        reply_data = {'text': 'This is a test reply from the API'}
                        reply_response = requests.post(f'{API_BASE}/messaging/messages/{message_id}/reply/', json=reply_data)
                        print(f"Status: {reply_response.status_code}")
                        
                        if reply_response.status_code == 201:
                            print("✅ Message reply created successfully!")
                        else:
                            print(f"❌ Failed to create message reply: {reply_response.text}")
                    else:
                        print("No messages found in conversation")
                else:
                    print(f"Failed to get messages: {messages_response.text}")
            else:
                print("No conversations found")
        else:
            print(f"Failed to get conversations: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to the server. Make sure Django is running on localhost:8000")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    test_message_details_endpoints()
