"""
AI processing utilities for the messaging system
"""

import openai
import tiktoken
import logging
from typing import List, Dict, Optional, Tuple
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
import hashlib
import json
from .deepseek_client import deepseek_client

logger = logging.getLogger(__name__)

# Set OpenAI API key (fallback)
if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
    openai.api_key = settings.OPENAI_API_KEY


class OpenAIClient:
    """OpenAI API client with error handling and caching"""
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.encoding = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken"""
        return len(self.encoding.encode(text))
    
    def truncate_to_token_limit(self, text: str, max_tokens: int = 3000) -> str:
        """Truncate text to fit within token limit"""
        tokens = self.encoding.encode(text)
        if len(tokens) <= max_tokens:
            return text
        
        # Truncate and decode back to text
        truncated_tokens = tokens[:max_tokens]
        return self.encoding.decode(truncated_tokens)
    
    def transcribe_audio(self, audio_file_path: str, language: Optional[str] = None) -> Dict:
        """
        Transcribe audio using OpenAI Whisper
        
        Args:
            audio_file_path: Path to audio file
            language: Optional language code (e.g., 'en', 'es')
            
        Returns:
            Dict with transcription results
        """
        try:
            with open(audio_file_path, 'rb') as audio_file:
                params = {
                    "model": "whisper-1",
                    "file": audio_file,
                    "response_format": "verbose_json"
                }
                
                if language:
                    params["language"] = language
                
                response = openai.Audio.transcribe(**params)
                
                return {
                    'text': response.text,
                    'language': getattr(response, 'language', None),
                    'duration': getattr(response, 'duration', None),
                    'confidence': None,  # Whisper doesn't provide confidence scores
                    'success': True
                }
                
        except Exception as e:
            logger.error(f"Audio transcription failed: {str(e)}")
            return {
                'text': '',
                'error': str(e),
                'success': False
            }
    
    def generate_chat_response(
        self, 
        messages: List[Dict], 
        model: str = "gpt-3.5-turbo",
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> Dict:
        """
        Generate chat response using OpenAI GPT
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: OpenAI model to use
            max_tokens: Maximum tokens in response
            temperature: Response creativity (0-1)
            
        Returns:
            Dict with response data
        """
        try:
            # Check token count for input
            total_tokens = sum(self.count_tokens(msg['content']) for msg in messages)
            if total_tokens > 3500:  # Leave room for response
                logger.warning(f"Input too long ({total_tokens} tokens), truncating...")
                # Truncate older messages but keep system message
                system_msg = messages[0] if messages[0]['role'] == 'system' else None
                recent_messages = messages[-5:]  # Keep last 5 messages
                
                if system_msg:
                    messages = [system_msg] + recent_messages
                else:
                    messages = recent_messages
            
            response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                presence_penalty=0.1,
                frequency_penalty=0.1
            )
            
            return {
                'text': response.choices[0].message.content.strip(),
                'model': model,
                'tokens_used': response.usage.total_tokens,
                'finish_reason': response.choices[0].finish_reason,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Chat response generation failed: {str(e)}")
            return {
                'text': "I apologize, but I'm having trouble generating a response right now. Please try again.",
                'error': str(e),
                'success': False
            }
    
    def generate_embeddings(self, text: str, model: str = "text-embedding-ada-002") -> Optional[List[float]]:
        """
        Generate embeddings for text
        
        Args:
            text: Text to embed
            model: Embedding model to use
            
        Returns:
            List of floats representing the embedding, or None if failed
        """
        try:
            # Cache embeddings to avoid redundant API calls
            cache_key = f"embedding:{hashlib.md5(text.encode()).hexdigest()}"
            cached_embedding = cache.get(cache_key)
            if cached_embedding:
                return cached_embedding
            
            # Use OpenAI client if available, otherwise skip embeddings
            if hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
                from openai import OpenAI
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                response = client.embeddings.create(
                    model=model,
                    input=text
                )
                embedding = response.data[0].embedding
            else:
                # Skip embeddings if OpenAI not configured
                logger.warning("OpenAI API key not configured, skipping embeddings")
                return None
            
            # Cache for 24 hours
            cache.set(cache_key, embedding, 86400)
            
            return embedding
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            return None
    
    def classify_intent(self, text: str) -> Tuple[str, float]:
        """
        Classify message intent
        
        Args:
            text: Message text to classify
            
        Returns:
            Tuple of (intent, confidence)
        """
        try:
            # Cache intent classifications
            cache_key = f"intent:{hashlib.md5(text.encode()).hexdigest()}"
            cached_result = cache.get(cache_key)
            if cached_result:
                return cached_result
            
            # Use DeepSeek for intent classification
            result = deepseek_client.analyze_intent(text)
            intent = result.get('intent', 'other')
            confidence = result.get('confidence', 0.5)
            
            # Validate intent
            valid_intents = ['inquiry', 'request', 'complaint', 'appointment', 'other']
            if intent not in valid_intents:
                intent = 'other'
            
            # Cache for 1 hour
            cache.set(cache_key, (intent, confidence), 3600)
            
            return intent, confidence
            
        except Exception as e:
            logger.error(f"Intent classification failed: {str(e)}")
            return 'other', 0.0


class ConversationAnalyzer:
    """Advanced conversation analysis and summarization"""
    
    def __init__(self):
        self.openai_client = OpenAIClient()
    
    def summarize_conversation(self, messages: List[Dict], max_length: int = 150) -> Dict:
        """
        Generate a concise summary of the conversation
        
        Args:
            messages: List of conversation messages
            max_length: Maximum length of summary in words
            
        Returns:
            Dict with summary data
        """
        try:
            if not messages:
                return {
                    'success': False,
                    'error': 'No messages to summarize'
                }
            
            # Format messages for summarization
            conversation_text = self._format_messages_for_analysis(messages)
            
            if len(conversation_text.split()) < 10:
                return {
                    'success': True,
                    'summary': conversation_text,
                    'key_points': [],
                    'word_count': len(conversation_text.split())
                }
            
            # Create summarization prompt
            system_prompt = f"""You are a professional conversation summarizer. Create a concise summary of this customer service conversation.

Requirements:
- Maximum {max_length} words
- Focus on key issues, requests, and resolutions
- Use professional, objective language
- Highlight important customer needs or concerns
- Include any action items or next steps

Format your response as JSON with these fields:
- "summary": Main conversation summary
- "key_points": Array of 3-5 key points
- "customer_sentiment": "positive", "neutral", or "negative"
- "resolution_status": "resolved", "pending", or "escalated"
- "action_items": Array of any follow-up actions needed
"""

            messages_for_api = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Conversation to summarize:\n\n{conversation_text}"}
            ]
            
            response = self.openai_client.generate_chat_response(
                messages=messages_for_api,
                temperature=0.3,
                max_tokens=400
            )
            
            if response['success']:
                try:
                    import json
                    summary_data = json.loads(response['text'])
                    summary_data['success'] = True
                    summary_data['word_count'] = len(summary_data['summary'].split())
                    return summary_data
                except json.JSONDecodeError:
                    # Fallback if JSON parsing fails
                    return {
                        'success': True,
                        'summary': response['text'],
                        'key_points': [],
                        'customer_sentiment': 'neutral',
                        'resolution_status': 'pending',
                        'action_items': [],
                        'word_count': len(response['text'].split())
                    }
            else:
                return {
                    'success': False,
                    'error': response.get('error', 'Summarization failed')
                }
                
        except Exception as e:
            logger.error(f"Conversation summarization failed: {str(e)}")
            return {
                'success': False,
                'error': f'Summarization error: {str(e)}'
            }
    
    def extract_entities(self, text: str) -> Dict:
        """
        Extract entities from conversation text
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict with extracted entities
        """
        try:
            system_prompt = """You are an entity extraction specialist. Extract relevant entities from this customer service text.

Extract and return as JSON:
- "people": Array of person names mentioned
- "organizations": Array of company/organization names
- "products": Array of products or services mentioned
- "dates": Array of dates mentioned (in YYYY-MM-DD format if possible)
- "locations": Array of locations mentioned
- "contact_info": Array of phone numbers, emails mentioned
- "monetary_amounts": Array of prices, costs, amounts mentioned
- "issues": Array of problems or issues mentioned
- "requests": Array of specific requests made

Only include entities that are clearly mentioned. Use empty arrays for categories with no entities."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Text to analyze:\n\n{text}"}
            ]
            
            response = self.openai_client.generate_chat_response(
                messages=messages,
                temperature=0.1,
                max_tokens=300
            )
            
            if response['success']:
                try:
                    import json
                    entities = json.loads(response['text'])
                    entities['success'] = True
                    return entities
                except json.JSONDecodeError:
                    return {
                        'success': False,
                        'error': 'Failed to parse entity extraction results'
                    }
            else:
                return {
                    'success': False,
                    'error': response.get('error', 'Entity extraction failed')
                }
                
        except Exception as e:
            logger.error(f"Entity extraction failed: {str(e)}")
            return {
                'success': False,
                'error': f'Entity extraction error: {str(e)}'
            }
    
    def analyze_sentiment(self, text: str) -> Dict:
        """
        Analyze sentiment of conversation or message
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict with sentiment analysis
        """
        try:
            system_prompt = """You are a sentiment analysis expert. Analyze the sentiment of this customer service text.

Provide analysis as JSON with:
- "overall_sentiment": "very_positive", "positive", "neutral", "negative", or "very_negative"
- "confidence": Float between 0.0 and 1.0
- "emotional_indicators": Array of emotional words/phrases found
- "satisfaction_level": Integer from 1-5 (1=very dissatisfied, 5=very satisfied)
- "urgency_level": "low", "medium", or "high"
- "tone": "professional", "casual", "frustrated", "happy", etc.

Be objective and consider context of customer service interactions."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Text to analyze:\n\n{text}"}
            ]
            
            response = self.openai_client.generate_chat_response(
                messages=messages,
                temperature=0.2,
                max_tokens=250
            )
            
            if response['success']:
                try:
                    import json
                    sentiment_data = json.loads(response['text'])
                    sentiment_data['success'] = True
                    return sentiment_data
                except json.JSONDecodeError:
                    return {
                        'success': False,
                        'error': 'Failed to parse sentiment analysis results'
                    }
            else:
                return {
                    'success': False,
                    'error': response.get('error', 'Sentiment analysis failed')
                }
                
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {str(e)}")
            return {
                'success': False,
                'error': f'Sentiment analysis error: {str(e)}'
            }
    
    def generate_conversation_insights(self, messages: List[Dict]) -> Dict:
        """
        Generate comprehensive insights about a conversation
        
        Args:
            messages: List of conversation messages
            
        Returns:
            Dict with conversation insights
        """
        try:
            conversation_text = self._format_messages_for_analysis(messages)
            
            # Get summary
            summary_result = self.summarize_conversation(messages)
            
            # Get sentiment analysis
            sentiment_result = self.analyze_sentiment(conversation_text)
            
            # Get entity extraction
            entities_result = self.extract_entities(conversation_text)
            
            # Calculate conversation metrics
            metrics = self._calculate_conversation_metrics(messages)
            
            return {
                'success': True,
                'summary': summary_result,
                'sentiment': sentiment_result,
                'entities': entities_result,
                'metrics': metrics,
                'generated_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Conversation insights generation failed: {str(e)}")
            return {
                'success': False,
                'error': f'Insights generation error: {str(e)}'
            }
    
    def _format_messages_for_analysis(self, messages: List[Dict]) -> str:
        """Format messages for AI analysis"""
        formatted = []
        
        for msg in messages:
            sender = msg.get('sender', 'unknown')
            text = msg.get('text', '')
            message_type = msg.get('message_type', 'text')
            
            if message_type == 'system' or not text:
                continue
                
            sender_label = {
                'client': 'Customer',
                'assistant': 'AI Assistant',
                'owner': 'Support Agent'
            }.get(sender, sender.title())
            
            formatted.append(f"{sender_label}: {text}")
        
        return "\n".join(formatted)
    
    def _calculate_conversation_metrics(self, messages: List[Dict]) -> Dict:
        """Calculate conversation metrics"""
        total_messages = len(messages)
        client_messages = len([m for m in messages if m.get('sender') == 'client'])
        assistant_messages = len([m for m in messages if m.get('sender') == 'assistant'])
        owner_messages = len([m for m in messages if m.get('sender') == 'owner'])
        
        # Calculate word counts
        total_words = sum(len(m.get('text', '').split()) for m in messages)
        client_words = sum(len(m.get('text', '').split()) for m in messages if m.get('sender') == 'client')
        
        # Calculate time span if timestamps available
        timestamps = [m.get('created_at') for m in messages if m.get('created_at')]
        duration_minutes = 0
        if len(timestamps) >= 2:
            try:
                from datetime import datetime
                first = datetime.fromisoformat(timestamps[0].replace('Z', '+00:00'))
                last = datetime.fromisoformat(timestamps[-1].replace('Z', '+00:00'))
                duration_minutes = (last - first).total_seconds() / 60
            except:
                pass
        
        return {
            'total_messages': total_messages,
            'client_messages': client_messages,
            'assistant_messages': assistant_messages,
            'owner_messages': owner_messages,
            'total_words': total_words,
            'client_words': client_words,
            'avg_words_per_message': total_words / max(total_messages, 1),
            'duration_minutes': round(duration_minutes, 2),
            'human_involvement': owner_messages > 0
        }


class ResponseGenerator:
    """Generate contextual responses using AI"""
    
    def __init__(self):
        self.openai_client = OpenAIClient()
    
    def build_system_prompt(self, workspace, kb_context: str = "") -> str:
        """Build personalized system prompt based on workspace profile"""
        assistant_name = workspace.assistant_name
        workspace_name = workspace.name
        
        # Base role-specific prompts
        role_prompts = {
            'banker': f"You are {assistant_name}, a professional banking assistant for {workspace_name}. You help clients with banking services, account inquiries, loan information, and financial guidance. Always maintain confidentiality and professionalism.",
            'medical': f"You are {assistant_name}, a medical assistant for {workspace_name}. You help patients with appointment scheduling, general health information, and connecting them with appropriate healthcare services. Always remind users to consult healthcare professionals for medical advice.",
            'legal': f"You are {assistant_name}, a legal assistant for {workspace_name}. You help clients with legal inquiries, document preparation, and appointment scheduling. Always remind users that you provide general information, not legal advice.",
            'real_estate': f"You are {assistant_name}, a real estate assistant for {workspace_name}. You help clients with property inquiries, showings, market information, and connecting them with real estate services.",
            'restaurant': f"You are {assistant_name}, a restaurant assistant for {workspace_name}. You help customers with reservations, menu inquiries, dietary information, and special requests.",
            'retail': f"You are {assistant_name}, a retail assistant for {workspace_name}. You help customers with product information, orders, returns, and store services.",
            'tech_support': f"You are {assistant_name}, a technical support assistant for {workspace_name}. You help users troubleshoot technical issues, provide product support, and guide them through solutions.",
            'secretary': f"You are {assistant_name}, a personal secretary for {workspace.owner_name or workspace_name}. You help with scheduling, reminders, information organization, and administrative tasks.",
            'customer_service': f"You are {assistant_name}, a customer service representative for {workspace_name}. You help customers with inquiries, complaints, support requests, and connecting them with appropriate services.",
            'consultant': f"You are {assistant_name}, a business consultant assistant for {workspace_name}. You help clients with business inquiries, consultation scheduling, and providing general business guidance.",
            'educator': f"You are {assistant_name}, an educational assistant for {workspace_name}. You help students and parents with course information, scheduling, educational resources, and academic support.",
            'general': f"You are {assistant_name}, a helpful AI assistant for {workspace_name}."
        }
        
        # Get role-specific prompt
        base_prompt = role_prompts.get(workspace.ai_role, role_prompts['general'])
        
        # Add personality traits
        personality_traits = {
            'professional': "Maintain a professional, courteous tone in all interactions.",
            'friendly': "Be warm, approachable, and friendly while remaining helpful.",
            'formal': "Use formal language and maintain proper business etiquette.",
            'casual': "Use a relaxed, conversational tone while staying helpful.",
            'empathetic': "Show understanding and empathy in your responses, especially for concerns or problems.",
            'direct': "Be clear, concise, and straightforward in your communication."
        }
        
        personality_instruction = personality_traits.get(workspace.ai_personality, personality_traits['professional'])
        
        # Build complete prompt
        full_prompt = f"""{base_prompt}

Industry Context: {workspace.industry or 'General Business'}
Owner: {workspace.owner_name or 'Business Owner'}

Personality & Communication Style:
- {personality_instruction}
- Keep responses concise but informative (under 200 words)
- If you don't know something, say so politely and offer to help find the information
- For appointment requests, guide users through the booking process
- Use the knowledge base information when relevant

{kb_context}

{workspace.custom_instructions or ''}

Remember: You represent {workspace_name} and should provide accurate, helpful information while maintaining the appropriate tone and expertise for your role."""
        
        return full_prompt
    
    def build_conversation_context(self, messages: List[Dict], max_messages: int = 10) -> List[Dict]:
        """
        Build conversation context from recent messages
        
        Args:
            messages: List of message objects
            max_messages: Maximum number of messages to include
            
        Returns:
            List of formatted messages for OpenAI
        """
        context = []
        
        for message in messages[-max_messages:]:
            role = "user" if message.get('sender') == "client" else "assistant"
            
            # Skip system messages or empty messages
            if message.get('message_type') == 'system' or not message.get('text'):
                continue
            
            context.append({
                "role": role,
                "content": message['text']
            })
        
        return context
    
    def generate_response(
        self, 
        user_message: str,
        conversation_context: List[Dict],
        workspace,  # Changed to workspace object
        kb_context: str = "",
        intent: str = "other"
    ) -> Dict:
        """
        Generate AI response with full context
        
        Args:
            user_message: Latest user message
            conversation_context: Previous conversation messages
            workspace_name: Name of the business
            assistant_name: Name of the AI assistant
            kb_context: Relevant knowledge base content
            intent: Classified intent of the message
            
        Returns:
            Dict with response data
        """
        try:
            # Build system prompt
            system_prompt = self.build_system_prompt(workspace, kb_context)
            
            # Add intent-specific guidance
            if intent == 'appointment':
                system_prompt += "\n\nThis message is about appointment booking. Guide the user through the process and ask for necessary details like preferred date/time."
            elif intent == 'complaint':
                system_prompt += "\n\nThis message expresses a concern or complaint. Be empathetic and focus on understanding and resolving the issue."
            elif intent == 'request':
                system_prompt += "\n\nThis is a specific service request. Provide clear information about how to proceed."
            
            # Build message list
            messages = [{"role": "system", "content": system_prompt}]
            messages.extend(conversation_context)
            messages.append({"role": "user", "content": user_message})
            
            # Generate response using DeepSeek
            context_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_context])
            response = deepseek_client.generate_response(
                prompt=user_message,
                context=context_text,
                system_prompt=system_prompt
            )
            
            return {
                'text': response,
                'success': True,
                'model_used': 'deepseek-chat'
            }
            
        except Exception as e:
            logger.error(f"Response generation failed: {str(e)}")
            return {
                'text': "I apologize, but I'm having trouble processing your message right now. Please try again in a moment.",
                'error': str(e),
                'success': False
            }


# Global instances
openai_client = OpenAIClient()
response_generator = ResponseGenerator()
conversation_analyzer = ConversationAnalyzer()
