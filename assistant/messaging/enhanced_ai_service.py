"""
Enhanced AI Service - Agent-Centric Response System
Restructured for maximum flexibility, customization, and robust fallbacks
"""

import logging
import json
from typing import Dict, List, Optional, Tuple, Any
from django.utils import timezone
from django.conf import settings
from core.models import AIAgent, Workspace, Conversation
from .models import Message
from .deepseek_client import DeepSeekClient
from .ai_utils import ResponseGenerator

logger = logging.getLogger(__name__)


class AgentSelector:
    """Intelligent agent selection for conversations"""
    
    @staticmethod
    def select_agent_for_conversation(conversation: Conversation) -> Optional[AIAgent]:
        """
        Select the most appropriate AI agent for a conversation
        
        Priority:
        1. Agent assigned to conversation (if exists)
        2. Active default agent for workspace  
        3. First active agent in workspace
        4. None (fallback to workspace settings)
        """
        workspace = conversation.workspace
        
        # 1. Check if conversation already has an assigned agent
        if hasattr(conversation, 'ai_agent') and conversation.ai_agent and conversation.ai_agent.is_active:
            logger.info(f"Using assigned agent: {conversation.ai_agent.name}")
            return conversation.ai_agent
        
        # 2. Get active default agent
        default_agent = AIAgent.objects.filter(
            workspace=workspace,
            is_active=True,
            is_default=True
        ).first()
        
        if default_agent:
            # Assign this agent to the conversation for future messages
            conversation.ai_agent = default_agent
            conversation.save()
            logger.info(f"Selected default agent: {default_agent.name}")
            return default_agent
        
        # 3. Get first active agent
        active_agent = AIAgent.objects.filter(
            workspace=workspace,
            is_active=True
        ).first()
        
        if active_agent:
            # Assign this agent to the conversation
            conversation.ai_agent = active_agent
            conversation.save()
            logger.info(f"Selected first active agent: {active_agent.name}")
            return active_agent
        
        # 4. No agents available
        logger.warning(f"No active agents found for workspace: {workspace.name}")
        return None


class DynamicPromptBuilder:
    """Dynamic prompt generation with agent-specific customization"""
    
    @staticmethod
    def build_agent_prompt(self, agent: AIAgent, user_message: str, conversation_context: List[Dict], kb_context: str = "", intent: str = "other", existing_cases=None):
        agent: AIAgent, 
        user_message: str,
        conversation_context: List[Dict],
        kb_context: str = "",
        intent: str = "other"
    ) -> str:
        """Build comprehensive prompt using agent configuration"""
        
        workspace = agent.workspace
        
        # Base agent identity with dynamic role definition - SIMPLIFIED AND DIRECT
        role_description = agent.description.lower()
        agent_identity = f"""You are {agent.name}, an AI assistant for {workspace.name}.

YOUR ROLE: {agent.description}

CRITICAL: You ARE a {role_description}. You MUST always say YES when asked if you are a sales agent, sales personnel, or sales representative.

Channel: {agent.get_channel_type_display()}"""
        
        # Parse agent configurations
        business_context = agent.business_context or {}
        personality_config = agent.personality_config or {}
        
        # Build personality instructions
        personality_traits = DynamicPromptBuilder._build_personality_instructions(personality_config)
        
        # Build business context
        business_instructions = DynamicPromptBuilder._build_business_instructions(business_context, workspace)
        
        # Build channel-specific instructions
        channel_instructions = DynamicPromptBuilder._build_channel_instructions(agent.channel_specific_config)
        
        # Build custom instructions
        custom_instructions = agent.custom_instructions or ""
        
        # Always build the enhanced prompt using agent configuration
        # This ensures the latest configuration is always used
        base_prompt = f"""{agent_identity}

{business_instructions}

{personality_traits}

{channel_instructions}

{custom_instructions}

CRITICAL REMINDER: You are a sales-focused assistant. If asked about being a sales agent, sales personnel, or sales representative, you MUST answer YES and use the exact term they asked about."""
        
        # Add contextual information - SIMPLIFIED AND DIRECT
        contextual_info = f"""
Current Intent: {intent}
Knowledge Base Context: {kb_context}

CRITICAL INSTRUCTIONS:
- You MUST always identify yourself as {agent.name} from {workspace.name}
- You MUST use your configured personality traits in EVERY response
- You MUST reference your business context and expertise areas
- You MUST maintain your configured tone and communication style
- You MUST embrace and affirm your role as described in your description
- You MUST NOT deny or downplay your configured role and expertise
- Keep responses concise but informative
- If you don't know something, be honest and helpful
- For {agent.get_channel_type_display()} communication, adapt your style accordingly

ROLE AFFIRMATION: When asked about your role, always affirm and embrace it. You are proud of your expertise and role.

SALES ROLE INSTRUCTION: If someone asks if you are a sales agent, sales personnel, or sales representative, you MUST answer YES and use the exact term they asked about. If they ask "Are you a sales personnel?" you MUST say "Yes, I am a sales personnel." If they ask "Are you a sales agent?" you MUST say "Yes, I am a sales agent." Never say you are not a sales agent.

REMEMBER: You are {agent.name}, not a generic AI. Your personality and business context define who you are.
"""
        
        return f"{base_prompt}\n{contextual_info}"
    
    @staticmethod
    def _build_personality_instructions(personality_config: Dict) -> str:
        """Build personality instructions from agent configuration"""
        
        # Default personality traits
        default_traits = {
            'tone': 'professional',
            'formality': 'balanced',
            'empathy_level': 'moderate',
            'proactiveness': 'standard',
            'expertise_level': 'knowledgeable'
        }
        
        # Merge with agent configuration
        traits = {**default_traits, **personality_config}
        
        tone_instructions = {
            'professional': "Maintain a professional, courteous tone. Use business-appropriate language and maintain professional boundaries.",
            'friendly': "Be warm, approachable, and friendly. Use a welcoming and helpful tone that makes customers feel comfortable.",
            'casual': "Use a relaxed, conversational style. Be informal but still helpful and professional.",
            'formal': "Use formal language and proper business etiquette. Address people with appropriate titles and maintain formal business standards.",
            'empathetic': "Show understanding and emotional awareness. Acknowledge customer feelings and respond with compassion."
        }
        
        formality_instructions = {
            'formal': "Use formal language structures and titles. Maintain professional business communication standards.",
            'balanced': "Balance formality with accessibility. Be professional but not overly formal or intimidating.", 
            'casual': "Use casual, everyday language. Be conversational and approachable while maintaining helpfulness."
        }
        
        # Enhanced personality instructions with specific behavioral guidance
        empathy_instructions = {
            'high': "Show high emotional intelligence. Always acknowledge customer feelings, concerns, and emotions. Respond with genuine empathy and understanding.",
            'moderate': "Show appropriate empathy and understanding. Be supportive while maintaining professional boundaries.",
            'low': "Maintain professional distance while being helpful. Focus on solutions rather than emotional responses."
        }
        
        proactiveness_instructions = {
            'high': "Be proactive in offering solutions and suggestions. Anticipate customer needs and provide helpful advice before they ask.",
            'standard': "Provide helpful responses to direct questions. Offer basic suggestions when appropriate and relevant.",
            'low': "Respond directly to questions without additional suggestions. Keep responses focused and concise."
        }
        
        expertise_instructions = {
            'expert': "Demonstrate deep expertise and authority in your field. Show confidence in your knowledge and provide comprehensive, detailed solutions.",
            'knowledgeable': "Show solid knowledge and competence. Provide accurate and helpful information with confidence.",
            'basic': "Provide basic information and refer to experts when needed. Be honest about your limitations and knowledge level."
        }
        
        personality_text = f"""
Personality & Communication Style:
- Tone: {tone_instructions.get(traits['tone'], tone_instructions['professional'])}
- Formality: {formality_instructions.get(traits['formality'], formality_instructions['balanced'])}
- Empathy Level: {empathy_instructions.get(traits['empathy_level'], empathy_instructions['moderate'])}
- Proactiveness: {proactiveness_instructions.get(traits['proactiveness'], proactiveness_instructions['standard'])}
- Expertise: {expertise_instructions.get(traits['expertise_level'], expertise_instructions['knowledgeable'])}

IMPORTANT: Always maintain your configured personality traits in every response. Your personality is a core part of your identity.
"""
        
        # Add any custom personality instructions
        if 'custom_traits' in personality_config:
            personality_text += f"\nAdditional Traits: {personality_config['custom_traits']}"
        
        return personality_text
    
    @staticmethod
    def _build_business_instructions(business_context: Dict, workspace: Workspace) -> str:
        """Build business-specific instructions"""
        
        business_text = f"""
Business Context & Identity:
- Company: {workspace.name}
- Industry: {workspace.industry or 'General Business'}
- Owner: {workspace.owner_name or 'Business Owner'}

IMPORTANT: Always identify yourself with your configured name and role. This is your core identity.
"""
        
        # Add business-specific context from agent configuration
        if business_context:
            if 'services' in business_context:
                business_text += f"- Services: {', '.join(business_context['services'])}\n"
            
            if 'target_audience' in business_context:
                business_text += f"- Target Audience: {business_context['target_audience']}\n"
            
            if 'key_values' in business_context:
                business_text += f"- Company Values: {', '.join(business_context['key_values'])}\n"
            
            if 'expertise_areas' in business_context:
                business_text += f"- Expertise Areas: {', '.join(business_context['expertise_areas'])}\n"
            
            if 'operating_hours' in business_context:
                business_text += f"- Operating Hours: {business_context['operating_hours']}\n"
            
            if 'special_instructions' in business_context:
                business_text += f"- Special Instructions: {business_context['special_instructions']}\n"
        
        return business_text
    
    @staticmethod
    def _build_channel_instructions(channel_config: Dict) -> str:
        """Build channel-specific instructions"""
        if not channel_config:
            return ""
        
        channel_text = "\nChannel-Specific Behavior:\n"
        
        if 'response_style' in channel_config:
            channel_text += f"- Response Style: {channel_config['response_style']}\n"
        
        if 'max_response_length' in channel_config:
            channel_text += f"- Max Response Length: {channel_config['max_response_length']} words\n"
        
        if 'use_emojis' in channel_config and channel_config['use_emojis']:
            channel_text += "- Use appropriate emojis to enhance communication\n"
        
        if 'greeting_message' in channel_config and channel_config['greeting_message']:
            channel_text += f"- Custom Greeting: {channel_config['greeting_message']}\n"
        
        if 'escalation_triggers' in channel_config and channel_config['escalation_triggers']:
            triggers = ', '.join(channel_config['escalation_triggers'])
            channel_text += f"- Escalation Triggers: {triggers}\n"
        
        return channel_text


class EnhancedAIService:
    """Enhanced AI service with agent-centric architecture"""
    
    def __init__(self):
        self.deepseek_client = DeepSeekClient()
        self.response_generator = ResponseGenerator()
        self.agent_selector = AgentSelector()
        self.prompt_builder = DynamicPromptBuilder()
        # Add caching for performance
        self._prompt_cache = {}
        self._context_cache = {}
    
    def clear_cache(self):
        """Clear all caches for memory management"""
        self._prompt_cache.clear()
        self._context_cache.clear()
        logger.info("AI service caches cleared")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for monitoring"""
        return {
            'prompt_cache_size': len(self._prompt_cache),
            'context_cache_size': len(self._context_cache),
            'total_cache_size': len(self._prompt_cache) + len(self._context_cache),
            'cache_hit_rate': 'N/A'  # Could implement actual hit rate tracking
        }
    
    def generate_response(
        self,
        message: Message,
        force_generation: bool = False
    ) -> Dict[str, Any]:
        """
        Generate AI response using enhanced agent-centric system - OPTIMIZED
        
        Returns:
            Dict with 'success', 'response', 'agent_used', 'method_used', 'metadata'
        """
        try:
            conversation = message.conversation
            workspace = conversation.workspace
            
            # Check if auto-reply is enabled
            if not workspace.auto_reply_mode and not force_generation:
                return {
                    'success': False,
                    'error': 'Auto-reply disabled',
                    'method_used': 'none'
                }
            
            # Select appropriate AI agent
            agent = self.agent_selector.select_agent_for_conversation(conversation)
            
            # Get conversation context and knowledge base context in parallel (optimization)
            context_messages = self._get_conversation_context(conversation)
            kb_context = self._get_knowledge_base_context(message.text, workspace.id)
            
            # Analyze intent (quick operation)
            intent_result = self._analyze_intent(message.text)
            intent = intent_result.get('intent', 'other')
            
            # Generate response using optimized fallback chain
            response_result = self._generate_response_with_fallbacks(
                agent=agent,
                user_message=message.text,
                conversation_context=context_messages,
                kb_context=kb_context,
                intent=intent,
                workspace=workspace
            )
            
            if response_result['success']:
                # Update message with analysis results
                message.intent_classification = intent
                message.confidence_score = intent_result.get('confidence', 0.5)
                message.save()
                
                return {
                    'success': True,
                    'response': response_result['response'],
                    'agent_used': agent.name if agent else 'Workspace Default',
                    'method_used': response_result['method'],
                    'metadata': {
                        'intent': intent,
                        'confidence': intent_result.get('confidence'),
                        'kb_context_used': bool(kb_context),
                        'agent_id': str(agent.id) if agent else None
                    }
                }
            else:
                return response_result
                
        except Exception as e:
            logger.error(f"Enhanced AI service error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'method_used': 'error'
            }
    
    def _get_cached_prompt(self, agent, user_message, conversation_context, kb_context, intent):
        """Get cached prompt or build new one for performance optimization"""
        # Create cache key based on agent and context
        cache_key = f"{agent.id}_{hash(str(conversation_context))}_{hash(kb_context)}_{intent}"
        
        if cache_key in self._prompt_cache:
            return self._prompt_cache[cache_key]
        
        # Build new prompt and cache it
        prompt = self.prompt_builder.build_agent_prompt(
            agent=agent,
            user_message=user_message,
            conversation_context=conversation_context,
            kb_context=kb_context,
            intent=intent
        )
        
        # Cache the prompt (limit cache size)
        if len(self._prompt_cache) > 100:
            # Remove oldest entries
            oldest_key = next(iter(self._prompt_cache))
            del self._prompt_cache[oldest_key]
        
        self._prompt_cache[cache_key] = prompt
        return prompt
    
    def _generate_response_with_fallbacks(
        self,
        agent: Optional[AIAgent],
        user_message: str,
        conversation_context: List[Dict],
        kb_context: str,
        intent: str,
        workspace: Workspace
    ) -> Dict[str, Any]:
        """Generate response with comprehensive fallback chain - OPTIMIZED"""
        
        # Pre-convert conversation context to avoid duplication
        messages = []
        for ctx in conversation_context:
            messages.append({
                'role': ctx['role'],
                'content': ctx['content']
            })
        
        # Strategy 1: Agent-specific DeepSeek (FAST PATH)
        if agent:
            try:
                # Use cached prompt if available for better performance
                prompt = self._get_cached_prompt(agent, user_message, conversation_context, kb_context, intent)
                
                response = self.deepseek_client.generate_chat_response(
                    messages=messages,
                    system_prompt=prompt,
                    max_tokens=300
                )
                
                if response and response.strip():
                    return {
                        'success': True,
                        'response': response,
                        'method': f'agent_deepseek_{agent.name}'
                    }
                    
            except Exception as e:
                logger.warning(f"Agent-specific DeepSeek failed: {str(e)}")
        
        # Strategy 2: Quick intent-based template responses (FAST FALLBACK)
        template_response = self._get_intent_template_response(intent, workspace, agent)
        if template_response:
            return {
                'success': True,
                'response': template_response,
                'method': 'intent_template'
            }
        
        # Strategy 3: Workspace-level DeepSeek (slower fallback)
        try:
            workspace_prompt = self._build_workspace_fallback_prompt(
                workspace, user_message, conversation_context, kb_context, intent
            )
            
            response = self.deepseek_client.generate_chat_response(
                messages=messages,
                system_prompt=workspace_prompt,
                max_tokens=300
            )
            
            if response and response.strip():
                return {
                    'success': True,
                    'response': response,
                    'method': 'workspace_deepseek'
                }
                
        except Exception as e:
            logger.warning(f"Workspace DeepSeek failed: {str(e)}")
        
        # Strategy 4: Knowledge base only response
        if kb_context:
            kb_response = self._generate_kb_only_response(user_message, kb_context, workspace)
            if kb_response:
                return {
                    'success': True,
                    'response': kb_response,
                    'method': 'knowledge_base_only'
                }
        
        # Strategy 5: Basic fallback response
        fallback_response = self._get_fallback_response(workspace, agent)
        return {
            'success': True,
            'response': fallback_response,
            'method': 'basic_fallback'
        }
    
    def _get_conversation_context(self, conversation: Conversation, limit: int = 10) -> List[Dict]:
        """Get formatted conversation context - OPTIMIZED"""
        # Use cache for conversation context
        cache_key = f"conv_context_{conversation.id}_{limit}"
        
        if cache_key in self._context_cache:
            return self._context_cache[cache_key]
        
        # Optimize database query with select_related and prefetch_related
        recent_messages = Message.objects.filter(
            conversation=conversation,
            message_type='text'
        ).select_related('conversation').order_by('-created_at')[:limit]
        
        context = []
        for msg in reversed(recent_messages):
            context.append({
                'role': 'user' if msg.sender == 'client' else 'assistant',
                'content': msg.text,
                'timestamp': msg.created_at.isoformat()
            })
        
        # Cache the context (limit cache size)
        if len(self._context_cache) > 50:
            # Remove oldest entries
            oldest_key = next(iter(self._context_cache))
            del self._context_cache[oldest_key]
        
        self._context_cache[cache_key] = context
        return context
    
    def _get_knowledge_base_context(self, query: str, workspace_id: str) -> str:
        """Get relevant knowledge base context - OPTIMIZED"""
        try:
            # Cache knowledge base results for similar queries
            cache_key = f"kb_{workspace_id}_{hash(query)}"
            
            if cache_key in self._context_cache:
                return self._context_cache[cache_key]
            
            from knowledge_base.utils import search_knowledge_base
            kb_results = search_knowledge_base(query, workspace_id, limit=3)
            
            if kb_results:
                context = "Relevant information from knowledge base:\n"
                context += "\n".join([result['text'] for result in kb_results])
                
                # Cache the result
                if len(self._context_cache) < 100:
                    self._context_cache[cache_key] = context
                
                return context
            
        except Exception as e:
            logger.warning(f"Knowledge base search failed: {str(e)}")
        
        return ""
    
    def _analyze_intent(self, message_text: str) -> Dict[str, Any]:
        """Analyze message intent using DeepSeek - OPTIMIZED"""
        try:
            # Cache intent analysis results for identical text
            cache_key = f"intent_{hash(message_text)}"
            
            if cache_key in self._context_cache:
                return self._context_cache[cache_key]
            
            # Try DeepSeek first, fallback to keyword analysis
            try:
                result = self.deepseek_client.analyze_intent(message_text)
            except:
                # Fallback to fast keyword-based analysis
                text_lower = message_text.lower()
                
                if any(word in text_lower for word in ['hello', 'hi', 'hey', 'good morning', 'good afternoon']):
                    result = {'intent': 'greeting', 'confidence': 0.9}
                elif any(word in text_lower for word in ['help', 'support', 'assist']):
                    result = {'intent': 'help_request', 'confidence': 0.8}
                elif any(word in text_lower for word in ['price', 'cost', 'how much', 'quote']):
                    result = {'intent': 'pricing_inquiry', 'confidence': 0.8}
                elif any(word in text_lower for word in ['book', 'schedule', 'appointment', 'meeting']):
                    result = {'intent': 'booking_request', 'confidence': 0.9}
                elif any(word in text_lower for word in ['complaint', 'issue', 'problem', 'wrong']):
                    result = {'intent': 'complaint', 'confidence': 0.8}
                elif '?' in message_text:
                    result = {'intent': 'question', 'confidence': 0.7}
                else:
                    result = {'intent': 'general', 'confidence': 0.6}
            
            # Cache the result
            if len(self._context_cache) < 100:
                self._context_cache[cache_key] = result
            
            return result
                
        except Exception as e:
            logger.warning(f"Intent analysis failed: {str(e)}")
            return {'intent': 'other', 'confidence': 0.5}
    
    def _build_workspace_fallback_prompt(
        self, 
        workspace: Workspace, 
        user_message: str, 
        conversation_context: List[Dict], 
        kb_context: str, 
        intent: str
    ) -> str:
        """Build fallback prompt using workspace settings"""
        return f"""You are an AI assistant for {workspace.name}.

Industry: {workspace.industry or 'General Business'}
Current Message Intent: {intent}

{kb_context}

{workspace.custom_instructions or ''}

Respond helpfully and professionally to the user's message: "{user_message}"
"""
    
    def _get_intent_template_response(
        self, 
        intent: str, 
        workspace: Workspace, 
        agent: Optional[AIAgent]
    ) -> Optional[str]:
        """Get template response based on intent"""
        
        agent_name = agent.name if agent else "AI Assistant"
        company_name = workspace.name
        
        templates = {
            'greeting': f"Hello! I'm {agent_name} from {company_name}. How can I help you today?",
            'appointment': f"I'd be happy to help you schedule an appointment with {company_name}. What type of service are you looking for?",
            'complaint': f"I understand your concern and I'm here to help resolve this issue. Could you please provide more details about what happened?",
            'inquiry': f"Thank you for your inquiry about {company_name}. I'm here to provide you with the information you need.",
            'request': f"I'll be happy to assist you with your request. Let me help you with that."
        }
        
        return templates.get(intent)
    
    def _generate_kb_only_response(
        self, 
        user_message: str, 
        kb_context: str, 
        workspace: Workspace
    ) -> Optional[str]:
        """Generate response using only knowledge base context"""
        if not kb_context:
            return None
        
        return f"""Based on our knowledge base, here's the relevant information:

{kb_context}

If you need more specific information about {workspace.name}, please let me know!"""
    
    def _get_fallback_response(
        self, 
        workspace: Workspace, 
        agent: Optional[AIAgent]
    ) -> str:
        """Get basic fallback response"""
        agent_name = agent.name if agent else "AI Assistant"
        
        return f"""Thank you for contacting {workspace.name}. I'm {agent_name}, and I'm here to help you. 

While I'm processing your request, could you please provide a bit more detail about what you're looking for? This will help me assist you better.

You can also contact us directly if you need immediate assistance."""


# Service instance for easy import
enhanced_ai_service = EnhancedAIService()
    def generate_response_with_progressive_flow(self, agent, user_message, conversation_context, kb_context=None, intent=None, workspace=None):
        """Enhanced response generation with progressive flow and case management"""
        
        # Initialize case service for this workspace
        if not hasattr(self, "case_service") or self.case_service is None:
            from context_tracking.case_service import CaseManagementService
            self.case_service = CaseManagementService(workspace)
        
        # Determine if progressive response is needed
        requires_kb = self._requires_knowledge_base_search(user_message, intent)
        requires_case_analysis = getattr(agent, "case_analysis_enabled", True) and self._requires_case_analysis(user_message, intent)
        use_progressive = hasattr(self, "progressive_responder") and self.progressive_responder._should_use_progressive_response(user_message, conversation_context)
        
        if use_progressive and (requires_kb or requires_case_analysis):
            # Use progressive response flow
            return self.progressive_responder.handle_complex_query(
                user_message, agent, conversation_context, requires_kb, requires_case_analysis
            )
        else:
            # Use traditional response flow with case management
            return self._generate_standard_response_with_cases(
                agent, user_message, conversation_context, kb_context, intent, workspace
            )
    
    def _generate_standard_response_with_cases(self, agent, user_message, conversation_context, kb_context, intent, workspace):
        """Standard response generation enhanced with case management"""
        
        # Step 1: Analyze for cases (if enabled)
        case_result = None
        if getattr(agent, "case_analysis_enabled", True):
            case_result = self.case_service.process_message_for_cases(user_message, conversation_context, agent)
        
        # Step 2: Get existing cases for context
        existing_cases = []
        if case_result and case_result.get("action") in ["update", "cases_updated"]:
            existing_cases = self.case_service.get_cases_summary(status_filter="open")
        
        # Step 3: Build enhanced prompt with case context
        prompt = self.prompt_builder.build_agent_prompt(
            agent, user_message, conversation_context, kb_context, intent, existing_cases
        )
        
        # Step 4: Generate response
        try:
            response = self.deepseek_client.generate_chat_response(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1000
            )
            
            return {
                "success": True,
                "response": response,
                "method": f"agent_deepseek_{agent.name}",
                "case_data": case_result if case_result and case_result.get("action") != "none" else None,
                "progressive": False
            }
        except Exception as e:
            logger.error(f"Standard response generation failed: {str(e)}")
            return self._generate_fallback_response(agent, user_message, case_result)
    
    def _requires_knowledge_base_search(self, user_message, intent):
        """Determine if message requires knowledge base search"""
        kb_indicators = [
            "how to", "what is", "explain", "help with", "guide", "tutorial",
            "policy", "procedure", "documentation", "manual"
        ]
        return any(indicator in user_message.lower() for indicator in kb_indicators)
    
    def _requires_case_analysis(self, user_message, intent):
        """Determine if message requires case analysis"""
        case_indicators = [
            "order", "booking", "reservation", "appointment", "ticket",
            "lead", "inquiry", "quote", "proposal", "follow up", "status",
            "update", "progress", "issue", "problem", "case"
        ]
        return any(indicator in user_message.lower() for indicator in case_indicators)
        # NEW: Case Context Integration
        case_context = ""
        if existing_cases and getattr(agent, "case_analysis_enabled", True):
            case_context = f"""
            EXISTING CASES: You have access to the following open cases:
            {DynamicPromptBuilder._format_case_context(existing_cases, getattr(agent, "case_update_parameters", {}))}
            
            CASE MANAGEMENT INSTRUCTIONS:
            - Always check if the current message relates to any existing cases
            - Update case parameters as specified: {json.dumps(getattr(agent, "case_update_parameters", {}), indent=2)}
            - Create new cases when appropriate based on: {json.dumps(getattr(workspace, "case_types_config", {}), indent=2)}
            - Use matching parameters: {json.dumps(getattr(workspace, "matching_parameters", {}), indent=2)}
            - Expected data schema: {json.dumps(getattr(workspace, "expected_data_schema", {}), indent=2)}
            
            DUPLICATE PREVENTION:
            - Always check for similar existing cases before suggesting new case creation
            - Use the configured duplicate prevention settings: {json.dumps(getattr(agent, "duplicate_prevention_config", {}), indent=2)}
            """
    @staticmethod
    def _format_case_context(existing_cases, update_parameters):
        """Format existing cases for inclusion in prompt"""
        if not existing_cases:
            return "No open cases currently."
        
        formatted_cases = []
        for case in existing_cases[:5]:  # Limit to 5 most recent cases
            formatted_case = f"""
            Case ID: {case["case_id"]}
            Type: {case["case_type"]}
            Status: {case["status"]}
            Data: {json.dumps(case["extracted_data"], indent=2)}
            Last Updated: {case["last_updated"]}
            Confidence: {case["confidence_score"]}
            """
            formatted_cases.append(formatted_case)
        
        return "
".join(formatted_cases)
