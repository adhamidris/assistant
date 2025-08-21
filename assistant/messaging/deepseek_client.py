"""
DeepSeek AI Client for the AI Personal Business Assistant.
"""
import requests
import json
import logging
from typing import Dict, List, Optional, Any
from django.conf import settings

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """
    Client for interacting with DeepSeek API.
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.DEEPSEEK_API_KEY
        self.base_url = "https://api.deepseek.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        model: str = "deepseek-chat",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Generate chat completion using DeepSeek API.
        
        Args:
            messages: List of message objects with 'role' and 'content'
            model: Model to use for completion
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stream: Whether to stream the response
            
        Returns:
            API response containing the completion
        """
        try:
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": stream
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"DeepSeek API request failed: {str(e)}")
            raise Exception(f"DeepSeek API error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error in DeepSeek chat completion: {str(e)}")
            raise
    
    def generate_response(
        self, 
        prompt: str, 
        context: str = "", 
        system_prompt: str = None
    ) -> str:
        """
        Generate a simple text response.
        
        Args:
            prompt: User prompt/question
            context: Additional context for the response
            system_prompt: System prompt to guide behavior
            
        Returns:
            Generated response text
        """
        try:
            messages = []
            
            # Add system prompt
            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })
            
            # Add context if provided
            if context:
                messages.append({
                    "role": "system",
                    "content": f"Context: {context}"
                })
            
            # Add user prompt
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            response = self.chat_completion(messages=messages)
            
            # Extract the response text
            if response and "choices" in response and len(response["choices"]) > 0:
                return response["choices"][0]["message"]["content"].strip()
            else:
                logger.warning("No valid response from DeepSeek API")
                return "I apologize, but I'm having trouble generating a response right now. Please try again."
                
        except Exception as e:
            logger.error(f"Error generating DeepSeek response: {str(e)}")
            return "I apologize, but I'm experiencing technical difficulties. Please try again later."
    
    def analyze_intent(self, text: str) -> Dict[str, Any]:
        """
        Analyze the intent of user text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Intent analysis results
        """
        try:
            system_prompt = """You are an intent classification system. Analyze the user's message and classify it into one of these categories:
            - inquiry: General questions or requests for information
            - request: Specific service requests or actions needed
            - complaint: Issues, problems, or dissatisfaction
            - appointment: Booking, scheduling, or calendar-related requests
            - other: Anything that doesn't fit the above categories
            
            Respond with a JSON object containing:
            - intent: the category name
            - confidence: confidence score from 0.0 to 1.0
            - reasoning: brief explanation of the classification
            """
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Classify this message: {text}"}
            ]
            
            response = self.chat_completion(messages=messages, temperature=0.3)
            
            if response and "choices" in response:
                content = response["choices"][0]["message"]["content"].strip()
                try:
                    # Try to parse JSON response
                    result = json.loads(content)
                    return {
                        "intent": result.get("intent", "other"),
                        "confidence": result.get("confidence", 0.5),
                        "reasoning": result.get("reasoning", "Intent classification")
                    }
                except json.JSONDecodeError:
                    # Fallback if JSON parsing fails
                    return {
                        "intent": "other",
                        "confidence": 0.5,
                        "reasoning": "Could not parse intent classification"
                    }
            
            return {
                "intent": "other",
                "confidence": 0.5,
                "reasoning": "No response from intent classifier"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing intent: {str(e)}")
            return {
                "intent": "other",
                "confidence": 0.0,
                "reasoning": f"Error in intent analysis: {str(e)}"
            }
    
    def summarize_conversation(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Generate a summary of a conversation.
        
        Args:
            messages: List of conversation messages
            
        Returns:
            Summary and analysis
        """
        try:
            # Format messages for analysis
            conversation_text = "\n".join([
                f"{msg.get('sender', 'unknown')}: {msg.get('content', msg.get('text', ''))}"
                for msg in messages
            ])
            
            system_prompt = """You are a conversation analyst. Summarize the conversation and provide insights.
            
            Provide a JSON response with:
            - summary: Brief summary of the conversation (2-3 sentences)
            - key_points: List of main topics discussed
            - sentiment: Overall sentiment (positive, neutral, negative)
            - resolution_status: Whether the issue seems resolved (resolved, pending, escalated)
            - action_items: Any actions that need to be taken
            """
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze this conversation:\n\n{conversation_text}"}
            ]
            
            response = self.chat_completion(messages=messages, temperature=0.3)
            
            if response and "choices" in response:
                content = response["choices"][0]["message"]["content"].strip()
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    return {
                        "summary": "Conversation analysis completed",
                        "key_points": [],
                        "sentiment": "neutral",
                        "resolution_status": "pending",
                        "action_items": []
                    }
            
            return {
                "summary": "Unable to analyze conversation",
                "key_points": [],
                "sentiment": "neutral",
                "resolution_status": "pending",
                "action_items": []
            }
            
        except Exception as e:
            logger.error(f"Error summarizing conversation: {str(e)}")
            return {
                "summary": f"Error in conversation analysis: {str(e)}",
                "key_points": [],
                "sentiment": "neutral",
                "resolution_status": "pending",
                "action_items": []
            }


# Global instance
deepseek_client = DeepSeekClient()
