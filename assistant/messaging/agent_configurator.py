"""
AI Agent Configuration Manager
Provides easy-to-use methods for customizing AI agent behavior
"""

import json
from typing import Dict, List, Optional, Any
from core.models import AIAgent, Workspace


class AgentConfigurator:
    """Manages AI agent configuration and customization"""
    
    @staticmethod
    def configure_agent_personality(
        agent: AIAgent,
        tone: str = 'professional',
        formality: str = 'balanced',
        empathy_level: str = 'moderate',
        proactiveness: str = 'standard',
        expertise_level: str = 'knowledgeable',
        custom_traits: Optional[str] = None
    ) -> AIAgent:
        """
        Configure agent personality traits
        
        Args:
            agent: AIAgent instance
            tone: professional, friendly, casual, formal, empathetic
            formality: formal, balanced, casual
            empathy_level: high, moderate, low
            proactiveness: high, standard, low
            expertise_level: expert, knowledgeable, basic
            custom_traits: Additional custom personality description
        """
        personality_config = {
            'tone': tone,
            'formality': formality,
            'empathy_level': empathy_level,
            'proactiveness': proactiveness,
            'expertise_level': expertise_level
        }
        
        if custom_traits:
            personality_config['custom_traits'] = custom_traits
        
        agent.personality_config = personality_config
        agent.save()
        return agent
    
    @staticmethod
    def configure_business_context(
        agent: AIAgent,
        services: Optional[List[str]] = None,
        target_audience: Optional[str] = None,
        key_values: Optional[List[str]] = None,
        expertise_areas: Optional[List[str]] = None,
        operating_hours: Optional[str] = None,
        special_instructions: Optional[str] = None
    ) -> AIAgent:
        """
        Configure business-specific context for agent
        
        Args:
            agent: AIAgent instance
            services: List of services offered
            target_audience: Description of target customers
            key_values: Company core values
            expertise_areas: Areas of specialization
            operating_hours: Business operating hours
            special_instructions: Any special handling instructions
        """
        business_context = {}
        
        if services:
            business_context['services'] = services
        if target_audience:
            business_context['target_audience'] = target_audience
        if key_values:
            business_context['key_values'] = key_values
        if expertise_areas:
            business_context['expertise_areas'] = expertise_areas
        if operating_hours:
            business_context['operating_hours'] = operating_hours
        if special_instructions:
            business_context['special_instructions'] = special_instructions
        
        agent.business_context = business_context
        agent.save()
        return agent
    
    @staticmethod
    def configure_channel_behavior(
        agent: AIAgent,
        response_style: Optional[str] = None,
        max_response_length: Optional[int] = None,
        use_emojis: bool = False,
        greeting_message: Optional[str] = None,
        escalation_triggers: Optional[List[str]] = None
    ) -> AIAgent:
        """
        Configure channel-specific behavior
        
        Args:
            agent: AIAgent instance
            response_style: conversational, formal, brief, detailed
            max_response_length: Maximum response length in words
            use_emojis: Whether to use emojis in responses
            greeting_message: Custom greeting for new conversations
            escalation_triggers: Keywords that trigger human handoff
        """
        channel_config = agent.channel_specific_config or {}
        
        if response_style:
            channel_config['response_style'] = response_style
        if max_response_length:
            channel_config['max_response_length'] = max_response_length
        if use_emojis is not None:
            channel_config['use_emojis'] = use_emojis
        if greeting_message:
            channel_config['greeting_message'] = greeting_message
        if escalation_triggers:
            channel_config['escalation_triggers'] = escalation_triggers
        
        agent.channel_specific_config = channel_config
        agent.save()
        return agent
    
    @staticmethod
    def generate_custom_prompt(
        agent: AIAgent,
        regenerate: bool = False
    ) -> str:
        """
        Generate or regenerate custom prompt based on agent configuration
        
        Args:
            agent: AIAgent instance
            regenerate: Whether to regenerate even if prompt exists
        """
        if agent.generated_prompt and not regenerate:
            return agent.generated_prompt
        
        # Build comprehensive prompt from configurations
        prompt_parts = []
        
        # Basic identity
        prompt_parts.append(f"You are {agent.name}, an AI assistant for {agent.workspace.name}.")
        
        if agent.description:
            prompt_parts.append(agent.description)
        
        # Channel context
        prompt_parts.append(f"You communicate via {agent.get_channel_type_display()}.")
        
        # Business context
        business_context = agent.business_context or {}
        if business_context:
            prompt_parts.append("\nBusiness Information:")
            
            if 'services' in business_context:
                prompt_parts.append(f"- Services offered: {', '.join(business_context['services'])}")
            
            if 'target_audience' in business_context:
                prompt_parts.append(f"- Target audience: {business_context['target_audience']}")
            
            if 'key_values' in business_context:
                prompt_parts.append(f"- Company values: {', '.join(business_context['key_values'])}")
            
            if 'expertise_areas' in business_context:
                prompt_parts.append(f"- Expertise areas: {', '.join(business_context['expertise_areas'])}")
            
            if 'operating_hours' in business_context:
                prompt_parts.append(f"- Operating hours: {business_context['operating_hours']}")
        
        # Personality configuration
        personality_config = agent.personality_config or {}
        if personality_config:
            prompt_parts.append("\nCommunication Style:")
            
            tone = personality_config.get('tone', 'professional')
            tone_instructions = {
                'professional': "Maintain a professional, courteous tone",
                'friendly': "Be warm, approachable, and friendly",
                'casual': "Use a relaxed, conversational style",
                'formal': "Use formal language and proper business etiquette",
                'empathetic': "Show understanding and emotional awareness"
            }
            prompt_parts.append(f"- Tone: {tone_instructions.get(tone, tone_instructions['professional'])}")
            
            formality = personality_config.get('formality', 'balanced')
            formality_instructions = {
                'formal': "Use formal language structures and titles",
                'balanced': "Balance formality with accessibility",
                'casual': "Use casual, everyday language"
            }
            prompt_parts.append(f"- Formality: {formality_instructions.get(formality, formality_instructions['balanced'])}")
            
            empathy = personality_config.get('empathy_level', 'moderate')
            prompt_parts.append(f"- Empathy level: {empathy} - respond to emotional context appropriately")
            
            proactiveness = personality_config.get('proactiveness', 'standard')
            prompt_parts.append(f"- Proactiveness: {proactiveness} - offer helpful suggestions when relevant")
            
            expertise = personality_config.get('expertise_level', 'knowledgeable')
            prompt_parts.append(f"- Expertise: Position yourself as {expertise} in your domain")
            
            if 'custom_traits' in personality_config:
                prompt_parts.append(f"- Additional traits: {personality_config['custom_traits']}")
        
        # Channel-specific behavior
        channel_config = agent.channel_specific_config or {}
        if channel_config:
            prompt_parts.append("\nChannel-Specific Guidelines:")
            
            if 'response_style' in channel_config:
                prompt_parts.append(f"- Response style: {channel_config['response_style']}")
            
            if 'max_response_length' in channel_config:
                prompt_parts.append(f"- Keep responses under {channel_config['max_response_length']} words")
            
            if channel_config.get('use_emojis'):
                prompt_parts.append("- You may use appropriate emojis to enhance communication")
            
            if 'escalation_triggers' in channel_config:
                triggers = ', '.join(channel_config['escalation_triggers'])
                prompt_parts.append(f"- Escalate to human for: {triggers}")
        
        # Custom instructions
        if agent.custom_instructions:
            prompt_parts.append(f"\nSpecial Instructions:\n{agent.custom_instructions}")
        
        # Final guidelines
        prompt_parts.append(f"""
Core Guidelines:
- Always represent {agent.workspace.name} professionally
- Provide accurate, helpful information
- If you don't know something, be honest and offer alternatives
- Guide users appropriately for their needs
- Maintain consistency with your defined personality and role""")
        
        generated_prompt = '\n'.join(prompt_parts)
        
        # Save generated prompt
        agent.generated_prompt = generated_prompt
        agent.prompt_version = "2.0"  # Enhanced version
        agent.save()
        
        return generated_prompt
    
    @staticmethod
    def create_agent_preset(
        workspace: Workspace,
        preset_type: str,
        name: str,
        channel_type: str = 'website'
    ) -> AIAgent:
        """
        Create agent with predefined configuration presets
        
        Args:
            workspace: Workspace instance
            preset_type: customer_support, sales, appointment, technical, general
            name: Agent name
            channel_type: Communication channel
        """
        presets = {
            'customer_support': {
                'description': 'Dedicated customer support specialist focused on resolving issues and providing assistance.',
                'personality': {
                    'tone': 'empathetic',
                    'formality': 'balanced',
                    'empathy_level': 'high',
                    'proactiveness': 'high',
                    'expertise_level': 'knowledgeable'
                },
                'business_context': {
                    'expertise_areas': ['customer service', 'issue resolution', 'product support'],
                    'special_instructions': 'Always prioritize customer satisfaction and quick issue resolution'
                },
                'custom_instructions': 'Focus on understanding customer issues thoroughly and providing step-by-step solutions. Escalate complex technical problems to human support when needed.'
            },
            'sales': {
                'description': 'Sales-focused assistant that helps prospects learn about products and services.',
                'personality': {
                    'tone': 'friendly',
                    'formality': 'casual',
                    'empathy_level': 'moderate',
                    'proactiveness': 'high',
                    'expertise_level': 'expert'
                },
                'business_context': {
                    'expertise_areas': ['product knowledge', 'sales process', 'lead qualification'],
                    'special_instructions': 'Focus on understanding customer needs and matching them with appropriate solutions'
                },
                'custom_instructions': 'Ask qualifying questions to understand customer needs. Highlight relevant benefits and features. Guide prospects toward scheduling consultations or demos when appropriate.'
            },
            'appointment': {
                'description': 'Appointment scheduling specialist for booking meetings and managing calendars.',
                'personality': {
                    'tone': 'professional',
                    'formality': 'balanced',
                    'empathy_level': 'moderate',
                    'proactiveness': 'high',
                    'expertise_level': 'knowledgeable'
                },
                'business_context': {
                    'expertise_areas': ['scheduling', 'calendar management', 'appointment coordination'],
                    'special_instructions': 'Streamline the booking process and confirm all appointment details'
                },
                'custom_instructions': 'Guide users through appointment booking step-by-step. Confirm dates, times, and contact information. Provide booking confirmations and reminders about upcoming appointments.'
            },
            'technical': {
                'description': 'Technical support specialist for handling complex technical inquiries.',
                'personality': {
                    'tone': 'professional',
                    'formality': 'formal',
                    'empathy_level': 'moderate',
                    'proactiveness': 'standard',
                    'expertise_level': 'expert'
                },
                'business_context': {
                    'expertise_areas': ['technical support', 'troubleshooting', 'system configuration'],
                    'special_instructions': 'Provide detailed technical guidance and escalate when needed'
                },
                'custom_instructions': 'Break down technical concepts into understandable steps. Ask for specific technical details when troubleshooting. Provide clear, actionable solutions and escalate complex issues to technical teams.'
            },
            'general': {
                'description': 'General-purpose assistant that can handle various types of inquiries.',
                'personality': {
                    'tone': 'friendly',
                    'formality': 'balanced',
                    'empathy_level': 'moderate',
                    'proactiveness': 'standard',
                    'expertise_level': 'knowledgeable'
                },
                'business_context': {
                    'expertise_areas': ['general assistance', 'information provision', 'customer guidance'],
                    'special_instructions': 'Provide helpful information and direct users to appropriate resources'
                },
                'custom_instructions': 'Be helpful and informative across various topics. Route specialized questions to appropriate departments or resources when needed.'
            }
        }
        
        preset_config = presets.get(preset_type, presets['general'])
        
        # Create agent
        agent = AIAgent.objects.create(
            workspace=workspace,
            name=name,
            slug=f"{name.lower().replace(' ', '-')}-{preset_type}",
            description=preset_config['description'],
            channel_type=channel_type,
            custom_instructions=preset_config['custom_instructions'],
            personality_config=preset_config['personality'],
            business_context=preset_config['business_context']
        )
        
        # Generate prompt
        AgentConfigurator.generate_custom_prompt(agent)
        
        return agent


# Easy-to-use configurator instance
agent_configurator = AgentConfigurator()
