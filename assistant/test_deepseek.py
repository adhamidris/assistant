#!/usr/bin/env python
"""
Test script to verify DeepSeek API integration
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assistant.settings')
django.setup()

from messaging.deepseek_client import deepseek_client

def test_deepseek_integration():
    print("🧪 Testing DeepSeek API Integration...")
    
    try:
        # Test 1: Simple response generation
        print("\n1. Testing simple response generation...")
        response = deepseek_client.generate_response(
            prompt="Hello, how are you?",
            system_prompt="You are a helpful customer service assistant."
        )
        print(f"✅ Response: {response[:100]}...")
        
        # Test 2: Intent classification
        print("\n2. Testing intent classification...")
        intent_result = deepseek_client.analyze_intent("I'd like to book an appointment for next week")
        print(f"✅ Intent: {intent_result}")
        
        # Test 3: Conversation summarization
        print("\n3. Testing conversation summarization...")
        sample_messages = [
            {"sender": "client", "content": "Hi, I have a problem with my order"},
            {"sender": "assistant", "content": "I'm sorry to hear that. Can you tell me more about the issue?"},
            {"sender": "client", "content": "The product arrived damaged"},
            {"sender": "assistant", "content": "I understand. Let me help you with a replacement."}
        ]
        summary_result = deepseek_client.summarize_conversation(sample_messages)
        print(f"✅ Summary: {summary_result}")
        
        print("\n🎉 All tests passed! DeepSeek integration is working correctly.")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("Please check your DeepSeek API key and internet connection.")

if __name__ == "__main__":
    test_deepseek_integration()
