"""
AI Integration for Dynamic Context System

This module integrates the dynamic context tracking system with the existing AI pipeline,
enhancing it to work with customizable schemas and business rules.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from django.utils import timezone

from messaging.deepseek_client import DeepSeekClient
from messaging.ai_utils import ResponseGenerator as BaseResponseGenerator
from core.models import Conversation
from .models import ConversationContext, WorkspaceContextSchema
from .services import ContextExtractionService, RuleEngineService

logger = logging.getLogger(__name__)


class ContextAwareResponseGenerator(BaseResponseGenerator):
    """
    Enhanced response generator that leverages dynamic context
    """
    
    def __init__(self):
        super().__init__()
        self.context_service = ContextExtractionService()
        self.rule_engine = RuleEngineService()
    
    def generate_response(
        self, 
        user_message: str,
        conversation_context: List[Dict],
        workspace,
        kb_context: str = "",
        intent: str = "other"
    ) -> Dict:
        """
        Enhanced response generation with dynamic context awareness
        """
        try:
            # Get or create conversation context
            conversation = self._get_conversation_from_context(conversation_context, workspace)
            dynamic_context = self._get_or_create_dynamic_context(conversation)
            
            # Extract context from the user message
            if dynamic_context and user_message:
                self._extract_context_async(dynamic_context, user_message)
            
            # Build enhanced system prompt with context
            enhanced_system_prompt = self._build_context_aware_system_prompt(
                workspace, dynamic_context, kb_context
            )
            
            # Generate response using enhanced prompt
            response = super().generate_response(
                user_message, conversation_context, workspace, kb_context, intent
            )
            
            # Post-process response with context rules
            if dynamic_context and response.get('success'):
                self._apply_context_rules(dynamic_context, response, user_message)
            
            return response
            
        except Exception as e:
            logger.error(f"Context-aware response generation failed: {str(e)}")
            # Fallback to base response generation
            return super().generate_response(
                user_message, conversation_context, workspace, kb_context, intent
            )
    
    def _get_conversation_from_context(self, conversation_context: List[Dict], workspace) -> Optional[Conversation]:
        """Extract conversation from context messages"""
        try:
            # This would need to be implemented based on how conversation_context is structured
            # For now, we'll use a simple approach
            if hasattr(workspace, 'conversations'):
                return workspace.conversations.filter(status='active').first()
            return None
        except Exception as e:
            logger.error(f"Failed to get conversation from context: {str(e)}")
            return None
    
    def _get_or_create_dynamic_context(self, conversation) -> Optional[ConversationContext]:
        """Get or create dynamic context for conversation"""
        if not conversation:
            return None
        
        try:
            return ConversationContext.objects.get(conversation=conversation)
        except ConversationContext.DoesNotExist:
            # This should be handled by signals, but as a fallback
            try:
                default_schema = WorkspaceContextSchema.objects.filter(
                    workspace=conversation.workspace,
                    is_default=True,
                    is_active=True
                ).first()
                
                if default_schema:
                    return ConversationContext.objects.create(
                        conversation=conversation,
                        schema=default_schema,
                        title="",
                        context_data={},
                        status="new",
                        priority="medium"
                    )
            except Exception as e:
                logger.error(f"Failed to create dynamic context: {str(e)}")
            
            return None
    
    def _extract_context_async(self, dynamic_context: ConversationContext, user_message: str):
        """Extract context from user message asynchronously"""
        try:
            # Schedule async extraction to avoid blocking response
            from django.db import transaction
            
            def extract_later():
                try:
                    self.context_service.extract_context_from_text(
                        context=dynamic_context,
                        text=user_message,
                        force_extraction=False
                    )
                except Exception as e:
                    logger.error(f"Async context extraction failed: {str(e)}")
            
            transaction.on_commit(extract_later)
            
        except Exception as e:
            logger.error(f"Failed to schedule context extraction: {str(e)}")
    
    def _build_context_aware_system_prompt(
        self, 
        workspace, 
        dynamic_context: Optional[ConversationContext], 
        kb_context: str
    ) -> str:
        """Build system prompt enhanced with dynamic context information"""
        
        # Start with base prompt
        base_prompt = self.build_system_prompt(workspace, kb_context)
        
        if not dynamic_context:
            return base_prompt
        
        try:
            # Add context-specific instructions
            context_instructions = self._build_context_instructions(dynamic_context)
            
            enhanced_prompt = f"""{base_prompt}

CONVERSATION CONTEXT:
{context_instructions}

Context-Aware Instructions:
- Use the conversation context to provide more personalized and relevant responses
- If context fields are missing but could be inferred from the conversation, gently ask clarifying questions
- Adapt your communication style based on the context (e.g., urgency level, customer type)
- Reference relevant context information when appropriate to show understanding
- If the context suggests this is a follow-up to a previous issue, acknowledge the history

Remember: You have access to structured context about this conversation. Use it to provide better, more contextual assistance."""
            
            return enhanced_prompt
            
        except Exception as e:
            logger.error(f"Failed to build context-aware prompt: {str(e)}")
            return base_prompt
    
    def _build_context_instructions(self, dynamic_context: ConversationContext) -> str:
        """Build context instructions from dynamic context data"""
        
        instructions = []
        schema = dynamic_context.schema
        context_data = dynamic_context.context_data
        
        # Add schema information
        instructions.append(f"Schema: {schema.name}")
        if schema.description:
            instructions.append(f"Purpose: {schema.description}")
        
        # Add current status and priority
        instructions.append(f"Status: {dynamic_context.status}")
        instructions.append(f"Priority: {dynamic_context.priority}")
        
        # Add context field information
        if context_data:
            instructions.append("\nKnown Context:")
            for field in schema.fields:
                field_id = field['id']
                field_label = field['label']
                value = context_data.get(field_id)
                
                if value:
                    confidence = dynamic_context.ai_confidence_scores.get(field_id, 0)
                    confidence_note = f" (AI confidence: {confidence:.2f})" if confidence > 0 else ""
                    instructions.append(f"- {field_label}: {value}{confidence_note}")
        
        # Add tags if any
        if dynamic_context.tags:
            instructions.append(f"\nTags: {', '.join(dynamic_context.tags)}")
        
        # Add completion status
        completion = dynamic_context.completion_percentage
        instructions.append(f"\nContext Completion: {completion}%")
        
        return "\n".join(instructions)
    
    def _apply_context_rules(
        self, 
        dynamic_context: ConversationContext, 
        response: Dict[str, Any], 
        user_message: str
    ):
        """Apply context-based rules to the generated response"""
        
        try:
            # Trigger business rules based on the AI response
            message_data = {
                'text': user_message,
                'ai_response': response.get('response', ''),
                'intent': response.get('intent', 'other'),
                'confidence': response.get('confidence', 0.0)
            }
            
            # Evaluate rules asynchronously to avoid blocking response
            from django.db import transaction
            
            def evaluate_rules():
                try:
                    self.rule_engine.evaluate_new_message(dynamic_context, message_data)
                except Exception as e:
                    logger.error(f"Rule evaluation failed: {str(e)}")
            
            transaction.on_commit(evaluate_rules)
            
            # Check if response should be modified based on context
            self._modify_response_based_on_context(dynamic_context, response)
            
        except Exception as e:
            logger.error(f"Failed to apply context rules: {str(e)}")
    
    def _modify_response_based_on_context(
        self, 
        dynamic_context: ConversationContext, 
        response: Dict[str, Any]
    ):
        """Modify response based on context state"""
        
        try:
            # Add context-aware response modifications
            modifications = []
            
            # High priority contexts get more urgent language
            if dynamic_context.priority in ['high', 'urgent']:
                modifications.append("priority_urgent")
            
            # Low completion rate might trigger information gathering
            if dynamic_context.completion_percentage < 50:
                modifications.append("gather_info")
            
            # Status-based modifications
            if dynamic_context.status == 'new':
                modifications.append("initial_contact")
            elif dynamic_context.status == 'in_progress':
                modifications.append("follow_up")
            
            # Store modifications in response metadata
            if modifications:
                response['context_modifications'] = modifications
                response['context_status'] = dynamic_context.status
                response['context_priority'] = dynamic_context.priority
                response['context_completion'] = dynamic_context.completion_percentage
            
        except Exception as e:
            logger.error(f"Failed to modify response based on context: {str(e)}")


class ContextAwareIntentClassifier:
    """
    Enhanced intent classifier that uses dynamic context
    """
    
    def __init__(self):
        self.deepseek_client = DeepSeekClient()
    
    def classify_with_context(
        self, 
        text: str, 
        dynamic_context: Optional[ConversationContext] = None
    ) -> Tuple[str, float, Dict[str, Any]]:
        """
        Classify intent with context awareness
        
        Returns:
            Tuple of (intent, confidence, context_updates)
        """
        try:
            # Build context-aware classification prompt
            prompt = self._build_classification_prompt(text, dynamic_context)
            
            # Call AI for classification
            result = self._call_ai_classification(prompt)
            
            if result['success']:
                intent = result['data'].get('intent', 'other')
                confidence = result['data'].get('confidence', 0.0)
                context_updates = result['data'].get('context_updates', {})
                
                return intent, confidence, context_updates
            else:
                return 'other', 0.0, {}
            
        except Exception as e:
            logger.error(f"Context-aware intent classification failed: {str(e)}")
            return 'other', 0.0, {}
    
    def _build_classification_prompt(
        self, 
        text: str, 
        dynamic_context: Optional[ConversationContext]
    ) -> str:
        """Build classification prompt with context"""
        
        base_prompt = f"""Classify the intent of this customer message and identify any context information:

Message: "{text}"
"""
        
        if dynamic_context:
            schema = dynamic_context.schema
            context_data = dynamic_context.context_data
            
            base_prompt += f"""
Current Context:
- Schema: {schema.name}
- Status: {dynamic_context.status}
- Priority: {dynamic_context.priority}
- Existing data: {json.dumps(context_data, indent=2) if context_data else 'None'}

Available fields to extract:
"""
            for field in schema.fields:
                if field.get('ai_extractable', True):
                    base_prompt += f"- {field['id']} ({field['label']}): {field['type']}\n"
                    if field.get('choices'):
                        base_prompt += f"  Choices: {', '.join(field['choices'])}\n"
        
        base_prompt += """
Standard intents:
- inquiry: General questions or information requests
- request: Specific service or action requests
- complaint: Issues, problems, or dissatisfaction
- appointment: Scheduling or calendar-related
- support: Technical or customer support
- sales: Purchase interest or product questions
- other: Anything else

Return JSON with:
{
    "intent": "intent_name",
    "confidence": 0.85,
    "reasoning": "Brief explanation",
    "context_updates": {
        "field_id": "extracted_value"
    }
}

Only include context_updates for fields you're confident about (>0.7 confidence)."""
        
        return base_prompt
    
    def _call_ai_classification(self, prompt: str) -> Dict[str, Any]:
        """Call AI for intent classification"""
        try:
            messages = [
                {"role": "system", "content": "You are a professional intent classifier that also extracts business context."},
                {"role": "user", "content": prompt}
            ]
            
            # Use DeepSeek for intent classification
            response = self.deepseek_client.chat_completion(
                messages=messages,
                temperature=0.1,
                max_tokens=500
            )
            
            # Parse DeepSeek response format
            if "choices" not in response or not response["choices"]:
                logger.warning("DeepSeek intent classification failed: No choices in response")
                return {
                    'intent': 'other',
                    'confidence': 0.0,
                    'context_updates': {},
                    'reasoning': 'DeepSeek API error'
                }
            
            response_text = response["choices"][0]["message"]["content"].strip()
            
            # Parse JSON response
            try:
                response_data = json.loads(response_text)
                return {'success': True, 'data': response_data}
            except json.JSONDecodeError:
                # Try to extract JSON from response
                if '```json' in response_text:
                    json_start = response_text.find('```json') + 7
                    json_end = response_text.find('```', json_start)
                    json_text = response_text[json_start:json_end].strip()
                    response_data = json.loads(json_text)
                    return {'success': True, 'data': response_data}
                else:
                    raise Exception("Could not parse AI response as JSON")
            
        except Exception as e:
            logger.error(f"AI classification call failed: {str(e)}")
            return {'success': False, 'error': str(e)}


class ContextAwareConversationAnalyzer:
    """
    Enhanced conversation analyzer that generates context-aware summaries
    """
    
    def __init__(self):
        self.deepseek_client = DeepSeekClient()
    
    def analyze_with_context(
        self, 
        messages: List[Dict], 
        dynamic_context: Optional[ConversationContext] = None
    ) -> Dict[str, Any]:
        """
        Analyze conversation with context awareness
        """
        try:
            # Build context-aware analysis prompt
            prompt = self._build_analysis_prompt(messages, dynamic_context)
            
            # Call AI for analysis
            result = self._call_ai_analysis(prompt)
            
            if result['success']:
                return result['data']
            else:
                return {'success': False, 'error': result.get('error')}
            
        except Exception as e:
            logger.error(f"Context-aware conversation analysis failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _build_analysis_prompt(
        self, 
        messages: List[Dict], 
        dynamic_context: Optional[ConversationContext]
    ) -> str:
        """Build analysis prompt with context"""
        
        # Format messages
        conversation_text = "\n".join([
            f"{msg.get('sender', 'Unknown')}: {msg.get('text', '')}"
            for msg in messages if msg.get('text')
        ])
        
        base_prompt = f"""Analyze this customer service conversation and provide insights:

Conversation:
{conversation_text}
"""
        
        if dynamic_context:
            schema = dynamic_context.schema
            context_data = dynamic_context.context_data
            
            base_prompt += f"""
Current Context:
- Schema: {schema.name} ({schema.description or 'No description'})
- Status: {dynamic_context.status}
- Priority: {dynamic_context.priority}
- Completion: {dynamic_context.completion_percentage}%
- Context Data: {json.dumps(context_data, indent=2) if context_data else 'None'}
- Tags: {', '.join(dynamic_context.tags) if dynamic_context.tags else 'None'}
"""
        
        base_prompt += """
Provide analysis in JSON format:
{
    "summary": "Conversation summary",
    "key_points": ["point1", "point2", "point3"],
    "customer_sentiment": "positive/neutral/negative",
    "resolution_status": "resolved/pending/escalated",
    "action_items": ["action1", "action2"],
    "next_steps": ["step1", "step2"],
    "context_quality": "high/medium/low",
    "missing_information": ["info1", "info2"],
    "recommended_status": "new/in_progress/resolved",
    "recommended_priority": "low/medium/high/urgent",
    "tags_suggestions": ["tag1", "tag2"]
}

Focus on actionable insights and context completeness."""
        
        return base_prompt
    
    def _call_ai_analysis(self, prompt: str) -> Dict[str, Any]:
        """Call AI for conversation analysis"""
        try:
            messages = [
                {"role": "system", "content": "You are a professional conversation analyzer specializing in business context extraction."},
                {"role": "user", "content": prompt}
            ]
            
            # Use DeepSeek for conversation analysis
            response = self.deepseek_client.chat_completion(
                messages=messages,
                temperature=0.2,
                max_tokens=1000
            )
            
            # Parse DeepSeek response format
            if "choices" not in response or not response["choices"]:
                logger.warning("DeepSeek conversation analysis failed: No choices in response")
                return {}
            
            response_text = response["choices"][0]["message"]["content"].strip()
            
            # Parse JSON response
            try:
                response_data = json.loads(response_text)
                return {'success': True, 'data': response_data}
            except json.JSONDecodeError:
                if '```json' in response_text:
                    json_start = response_text.find('```json') + 7
                    json_end = response_text.find('```', json_start)
                    json_text = response_text[json_start:json_end].strip()
                    response_data = json.loads(json_text)
                    return {'success': True, 'data': response_data}
                else:
                    raise Exception("Could not parse AI response as JSON")
            
        except Exception as e:
            logger.error(f"AI analysis call failed: {str(e)}")
            return {'success': False, 'error': str(e)}


# Integration functions for existing codebase
def enhance_message_processing_with_context():
    """
    Enhancement function to integrate context tracking with existing message processing
    """
    # This would be used to patch existing message processing functions
    pass


def create_default_schemas_for_existing_workspaces():
    """
    Utility function to create default schemas for workspaces that don't have any
    """
    from core.models import Workspace
    
    workspaces_without_schemas = Workspace.objects.filter(
        context_schemas__isnull=True
    ).distinct()
    
    created_count = 0
    
    for workspace in workspaces_without_schemas:
        try:
            # Create industry-specific default schema
            schema_config = _get_default_schema_for_industry(workspace.industry)
            
            WorkspaceContextSchema.objects.create(
                workspace=workspace,
                name=schema_config['name'],
                description=schema_config['description'],
                fields=schema_config['fields'],
                status_workflow=schema_config['status_workflow'],
                priority_config=schema_config['priority_config'],
                is_default=True,
                is_active=True
            )
            
            created_count += 1
            logger.info(f"Created default schema for workspace {workspace.id}")
            
        except Exception as e:
            logger.error(f"Failed to create default schema for workspace {workspace.id}: {str(e)}")
    
    return created_count


def _get_default_schema_for_industry(industry: Optional[str]) -> Dict[str, Any]:
    """Get default schema configuration based on industry"""
    
    # Default fields that work for most industries
    base_fields = [
        {
            "id": "customer_name",
            "label": "Customer Name",
            "type": "text",
            "required": False,
            "ai_extractable": True,
            "display_order": 1
        },
        {
            "id": "contact_method",
            "label": "Preferred Contact Method",
            "type": "choice",
            "choices": ["email", "phone", "chat", "in_person"],
            "required": False,
            "ai_extractable": True,
            "display_order": 2
        },
        {
            "id": "inquiry_type",
            "label": "Inquiry Type",
            "type": "choice",
            "choices": ["general", "support", "sales", "complaint", "appointment"],
            "required": False,
            "ai_extractable": True,
            "display_order": 3
        },
        {
            "id": "urgency",
            "label": "Urgency Level",
            "type": "choice",
            "choices": ["low", "medium", "high", "urgent"],
            "required": False,
            "ai_extractable": True,
            "display_order": 4
        },
        {
            "id": "description",
            "label": "Description",
            "type": "textarea",
            "required": False,
            "ai_extractable": True,
            "display_order": 5
        }
    ]
    
    # Industry-specific customizations
    industry_customizations = {
        'real_estate': {
            'name': 'Real Estate Inquiries',
            'description': 'Track real estate client inquiries and property interests',
            'additional_fields': [
                {
                    "id": "property_type",
                    "label": "Property Type",
                    "type": "choice",
                    "choices": ["apartment", "house", "commercial", "land"],
                    "required": False,
                    "ai_extractable": True,
                    "display_order": 6
                },
                {
                    "id": "budget_range",
                    "label": "Budget Range",
                    "type": "text",
                    "required": False,
                    "ai_extractable": True,
                    "display_order": 7
                },
                {
                    "id": "location_preference",
                    "label": "Location Preference",
                    "type": "text",
                    "required": False,
                    "ai_extractable": True,
                    "display_order": 8
                }
            ]
        },
        'legal': {
            'name': 'Legal Consultations',
            'description': 'Track legal consultation requests and case information',
            'additional_fields': [
                {
                    "id": "legal_area",
                    "label": "Legal Area",
                    "type": "choice",
                    "choices": ["family", "corporate", "criminal", "personal_injury", "estate"],
                    "required": False,
                    "ai_extractable": True,
                    "display_order": 6
                },
                {
                    "id": "case_urgency",
                    "label": "Case Urgency",
                    "type": "choice",
                    "choices": ["low", "medium", "high", "emergency"],
                    "required": False,
                    "ai_extractable": True,
                    "display_order": 7
                }
            ]
        },
        'medical': {
            'name': 'Medical Appointments',
            'description': 'Track patient appointment requests and medical concerns',
            'additional_fields': [
                {
                    "id": "appointment_type",
                    "label": "Appointment Type",
                    "type": "choice",
                    "choices": ["consultation", "follow_up", "emergency", "routine_checkup"],
                    "required": False,
                    "ai_extractable": True,
                    "display_order": 6
                },
                {
                    "id": "symptoms",
                    "label": "Symptoms/Concerns",
                    "type": "textarea",
                    "required": False,
                    "ai_extractable": True,
                    "display_order": 7
                }
            ]
        }
    }
    
    # Get industry-specific config or use default
    config = industry_customizations.get(industry, {
        'name': 'General Business Inquiries',
        'description': 'Track general business customer inquiries',
        'additional_fields': []
    })
    
    # Combine base fields with industry-specific fields
    all_fields = base_fields + config.get('additional_fields', [])
    
    # Default status workflow
    status_workflow = {
        "statuses": [
            {"id": "new", "label": "New", "color": "blue"},
            {"id": "in_progress", "label": "In Progress", "color": "yellow"},
            {"id": "resolved", "label": "Resolved", "color": "green"},
            {"id": "closed", "label": "Closed", "color": "gray"}
        ],
        "transitions": {
            "new": ["in_progress", "resolved"],
            "in_progress": ["resolved", "new"],
            "resolved": ["closed", "in_progress"],
            "closed": ["in_progress"]
        }
    }
    
    # Default priority configuration
    priority_config = {
        "default_priority": "medium",
        "rules": [
            {
                "conditions": [
                    {"field": "urgency", "operator": "equals", "value": "urgent"}
                ],
                "priority": "urgent"
            },
            {
                "conditions": [
                    {"field": "urgency", "operator": "equals", "value": "high"}
                ],
                "priority": "high"
            }
        ]
    }
    
    return {
        'name': config['name'],
        'description': config['description'],
        'fields': all_fields,
        'status_workflow': status_workflow,
        'priority_config': priority_config
    }
