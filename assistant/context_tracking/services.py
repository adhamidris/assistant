import json
import logging
import time
from typing import Dict, List, Any, Optional
from django.utils import timezone
from django.db import transaction

from messaging.ai_utils import OpenAIClient
from .models import ConversationContext, ContextHistory, BusinessRule, RuleExecution

logger = logging.getLogger(__name__)


class ContextExtractionService:
    """Service for extracting context from conversations using AI"""
    
    def __init__(self):
        self.openai_client = OpenAIClient()
    
    def extract_context_from_text(
        self, 
        context: ConversationContext, 
        text: str, 
        force_extraction: bool = False,
        fields_to_extract: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Extract context information from text using AI
        
        Args:
            context: ConversationContext instance
            text: Text to extract from
            force_extraction: Force extraction even for low-confidence results
            fields_to_extract: Specific fields to extract (if None, extract all)
            
        Returns:
            Dict with extracted fields and confidence scores
        """
        try:
            schema = context.schema
            
            # Determine which fields to extract
            extractable_fields = [
                field for field in schema.fields 
                if field.get('ai_extractable', True)
            ]
            
            if fields_to_extract:
                extractable_fields = [
                    field for field in extractable_fields 
                    if field['id'] in fields_to_extract
                ]
            
            if not extractable_fields:
                return {'extracted_fields': {}, 'confidence_scores': {}}
            
            # Build extraction prompt
            extraction_prompt = self._build_extraction_prompt(
                schema, extractable_fields, text, context.context_data
            )
            
            # Call AI for extraction
            extraction_result = self._call_ai_extraction(extraction_prompt)
            
            if not extraction_result['success']:
                raise Exception(extraction_result.get('error', 'AI extraction failed'))
            
            extracted_data = extraction_result['data']
            
            # Process and validate extracted data
            processed_results = self._process_extraction_results(
                extracted_data, extractable_fields, context, force_extraction
            )
            
            # Update context with extracted data
            with transaction.atomic():
                self._update_context_with_extraction(
                    context, processed_results, text
                )
            
            return {
                'success': True,
                'extracted_fields': processed_results['field_updates'],
                'confidence_scores': processed_results['confidence_scores']
            }
            
        except Exception as e:
            logger.error(f"Context extraction failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'extracted_fields': {},
                'confidence_scores': {}
            }
    
    def _build_extraction_prompt(
        self, 
        schema, 
        fields: List[Dict], 
        text: str, 
        existing_context: Dict
    ) -> str:
        """Build the AI prompt for context extraction"""
        
        field_descriptions = []
        for field in fields:
            field_desc = f"- {field['id']} ({field['label']}): {field['type']}"
            
            if field.get('choices'):
                field_desc += f" - Choices: {', '.join(field['choices'])}"
            
            if field.get('extraction_keywords'):
                field_desc += f" - Keywords: {', '.join(field['extraction_keywords'])}"
            
            if field.get('help_text'):
                field_desc += f" - Description: {field['help_text']}"
            
            field_descriptions.append(field_desc)
        
        prompt = f"""Extract information from this conversation text for the following business context fields:

Schema: {schema.name}
Business Type: {schema.workspace.industry or 'General Business'}

Fields to extract:
{chr(10).join(field_descriptions)}

Conversation text:
"{text}"

Existing context data:
{json.dumps(existing_context, indent=2) if existing_context else 'None'}

Instructions:
1. Only extract information you're confident about (>0.7 confidence)
2. For choice fields, only use the exact values from the choices list
3. For existing fields, only update if you find contradictory or additional information
4. Provide a confidence score (0.0-1.0) for each extracted field
5. Include brief reasoning for each extraction

Return your response as JSON with this structure:
{{
    "extractions": [
        {{
            "field_id": "field_name",
            "value": "extracted_value",
            "confidence": 0.85,
            "reasoning": "Why you extracted this value"
        }}
    ]
}}

Only include fields where you found relevant information with high confidence."""
        
        return prompt
    
    def _call_ai_extraction(self, prompt: str) -> Dict[str, Any]:
        """Call OpenAI for context extraction"""
        try:
            messages = [
                {"role": "system", "content": "You are a professional information extraction assistant. Extract structured business context from conversations with high accuracy."},
                {"role": "user", "content": prompt}
            ]
            
            response = self.openai_client.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.1,
                max_tokens=1000
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Try to parse JSON response
            try:
                response_data = json.loads(response_text)
                return {
                    'success': True,
                    'data': response_data
                }
            except json.JSONDecodeError:
                # Try to extract JSON from response if it's wrapped in markdown
                if '```json' in response_text:
                    json_start = response_text.find('```json') + 7
                    json_end = response_text.find('```', json_start)
                    json_text = response_text[json_start:json_end].strip()
                    response_data = json.loads(json_text)
                    return {
                        'success': True,
                        'data': response_data
                    }
                else:
                    raise Exception("Could not parse AI response as JSON")
            
        except Exception as e:
            logger.error(f"AI extraction call failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _process_extraction_results(
        self, 
        extracted_data: Dict, 
        fields: List[Dict], 
        context: ConversationContext,
        force_extraction: bool
    ) -> Dict[str, Any]:
        """Process and validate extraction results"""
        
        field_updates = {}
        confidence_scores = {}
        
        extractions = extracted_data.get('extractions', [])
        
        for extraction in extractions:
            field_id = extraction.get('field_id')
            value = extraction.get('value')
            confidence = extraction.get('confidence', 0.0)
            reasoning = extraction.get('reasoning', '')
            
            # Find field definition
            field_def = None
            for field in fields:
                if field['id'] == field_id:
                    field_def = field
                    break
            
            if not field_def:
                logger.warning(f"Unknown field ID in extraction: {field_id}")
                continue
            
            # Validate confidence threshold
            min_confidence = 0.7
            if not force_extraction and confidence < min_confidence:
                logger.info(f"Skipping {field_id} due to low confidence: {confidence}")
                continue
            
            # Validate value based on field type
            validated_value = self._validate_field_value(value, field_def)
            if validated_value is None:
                logger.warning(f"Invalid value for field {field_id}: {value}")
                continue
            
            # Check if this is a meaningful update
            current_value = context.context_data.get(field_id)
            if current_value == validated_value:
                continue  # No change needed
            
            field_updates[field_id] = validated_value
            confidence_scores[field_id] = confidence
            
            logger.info(f"Extracted {field_id}: {validated_value} (confidence: {confidence})")
        
        return {
            'field_updates': field_updates,
            'confidence_scores': confidence_scores
        }
    
    def _validate_field_value(self, value: Any, field_def: Dict) -> Any:
        """Validate extracted value against field definition"""
        field_type = field_def['type']
        
        if value is None or value == '':
            return None
        
        try:
            if field_type == 'text' or field_type == 'textarea':
                return str(value)
            
            elif field_type == 'choice':
                choices = field_def.get('choices', [])
                if str(value) in choices:
                    return str(value)
                else:
                    # Try case-insensitive match
                    for choice in choices:
                        if str(value).lower() == choice.lower():
                            return choice
                    return None
            
            elif field_type == 'multi_choice':
                if isinstance(value, list):
                    validated_choices = []
                    choices = field_def.get('choices', [])
                    for v in value:
                        if str(v) in choices:
                            validated_choices.append(str(v))
                    return validated_choices if validated_choices else None
                else:
                    return None
            
            elif field_type == 'number':
                return int(float(value))
            
            elif field_type == 'decimal':
                return float(value)
            
            elif field_type == 'boolean':
                if isinstance(value, bool):
                    return value
                str_value = str(value).lower()
                if str_value in ['true', 'yes', '1', 'on']:
                    return True
                elif str_value in ['false', 'no', '0', 'off']:
                    return False
                return None
            
            elif field_type == 'tags':
                if isinstance(value, list):
                    return [str(v) for v in value]
                elif isinstance(value, str):
                    # Split by comma if it's a string
                    return [tag.strip() for tag in value.split(',') if tag.strip()]
                return None
            
            elif field_type in ['email', 'phone', 'url']:
                return str(value)
            
            elif field_type == 'priority':
                if str(value) in ['low', 'medium', 'high', 'urgent']:
                    return str(value)
                return None
            
            else:
                return str(value)
        
        except (ValueError, TypeError):
            return None
    
    def _update_context_with_extraction(
        self, 
        context: ConversationContext, 
        results: Dict[str, Any],
        source_text: str
    ):
        """Update context with extraction results"""
        field_updates = results['field_updates']
        confidence_scores = results['confidence_scores']
        
        if not field_updates:
            return
        
        # Update context data
        for field_id, value in field_updates.items():
            old_value = context.context_data.get(field_id)
            context.set_field_value(field_id, value, confidence_scores.get(field_id), is_ai_update=True)
            
            # Create history entry
            ContextHistory.objects.create(
                context=context,
                action_type='ai_updated',
                field_name=field_id,
                old_value=old_value,
                new_value=value,
                changed_by_ai=True,
                confidence_score=confidence_scores.get(field_id),
                metadata={
                    'source_text': source_text[:500],  # Truncate for storage
                    'extraction_method': 'openai_gpt4'
                }
            )
        
        # Auto-generate title if not set
        if not context.title and field_updates:
            context.title = self._generate_context_title(context, field_updates)
        
        # Recalculate priority
        context.recalculate_priority()
        context.save()
    
    def _generate_context_title(
        self, 
        context: ConversationContext, 
        field_updates: Dict[str, Any]
    ) -> str:
        """Generate a context title based on extracted data"""
        try:
            schema = context.schema
            workspace = schema.workspace
            
            # Build title generation prompt
            prompt = f"""Generate a concise, business-appropriate title for this conversation context:

Business Type: {workspace.industry or 'General Business'}
Schema: {schema.name}

Context Data:
{json.dumps(field_updates, indent=2)}

Requirements:
- 3-8 words maximum
- Professional and descriptive
- Focus on the main topic or need
- Make it actionable if possible

Examples for {workspace.industry or 'business'}:
- "Property Inquiry - Downtown Apartment"
- "Legal Consultation - Contract Review" 
- "Technical Support - Software Issue"
- "Medical Appointment - Annual Checkup"

Return only the title, no additional text."""

            messages = [
                {"role": "system", "content": "You are a professional assistant that creates concise, descriptive titles for business conversations."},
                {"role": "user", "content": prompt}
            ]
            
            response = self.openai_client.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.3,
                max_tokens=50
            )
            
            title = response.choices[0].message.content.strip().strip('"\'')
            
            # Validate title length
            if len(title) > 100:
                title = title[:97] + "..."
            
            return title or "Conversation Context"
            
        except Exception as e:
            logger.error(f"Title generation failed: {str(e)}")
            return "Conversation Context"


class RuleEngineService:
    """Service for evaluating and executing business rules"""
    
    def __init__(self):
        pass
    
    def evaluate_context_change(
        self, 
        context: ConversationContext, 
        changed_fields: Dict[str, Any]
    ):
        """Evaluate rules triggered by context field changes"""
        
        workspace = context.conversation.workspace
        rules = BusinessRule.objects.filter(
            workspace=workspace,
            is_active=True,
            trigger_type__in=['context_change', 'completion_rate']
        ).order_by('priority')
        
        context_data = {
            'context_data': context.context_data,
            'status': context.status,
            'priority': context.priority,
            'completion_percentage': context.completion_percentage,
            'tags': context.tags
        }
        
        trigger_data = {
            'trigger_type': 'context_change',
            'changed_fields': changed_fields,
            'context_id': str(context.id)
        }
        
        for rule in rules:
            try:
                self._evaluate_and_execute_rule(rule, context, context_data, trigger_data)
            except Exception as e:
                logger.error(f"Rule evaluation failed for rule {rule.id}: {str(e)}")
    
    def evaluate_status_change(
        self, 
        context: ConversationContext, 
        new_status: str
    ):
        """Evaluate rules triggered by status changes"""
        
        workspace = context.conversation.workspace
        rules = BusinessRule.objects.filter(
            workspace=workspace,
            is_active=True,
            trigger_type='status_change'
        ).order_by('priority')
        
        context_data = {
            'context_data': context.context_data,
            'status': new_status,
            'priority': context.priority,
            'completion_percentage': context.completion_percentage,
            'tags': context.tags
        }
        
        trigger_data = {
            'trigger_type': 'status_change',
            'old_status': context.status,
            'new_status': new_status,
            'context_id': str(context.id)
        }
        
        for rule in rules:
            try:
                self._evaluate_and_execute_rule(rule, context, context_data, trigger_data)
            except Exception as e:
                logger.error(f"Rule evaluation failed for rule {rule.id}: {str(e)}")
    
    def evaluate_new_message(
        self, 
        context: ConversationContext, 
        message_data: Dict[str, Any]
    ):
        """Evaluate rules triggered by new messages"""
        
        workspace = context.conversation.workspace
        rules = BusinessRule.objects.filter(
            workspace=workspace,
            is_active=True,
            trigger_type='new_message'
        ).order_by('priority')
        
        context_data = {
            'context_data': context.context_data,
            'status': context.status,
            'priority': context.priority,
            'completion_percentage': context.completion_percentage,
            'tags': context.tags,
            'message_data': message_data
        }
        
        trigger_data = {
            'trigger_type': 'new_message',
            'message': message_data,
            'context_id': str(context.id)
        }
        
        for rule in rules:
            try:
                self._evaluate_and_execute_rule(rule, context, context_data, trigger_data)
            except Exception as e:
                logger.error(f"Rule evaluation failed for rule {rule.id}: {str(e)}")
    
    def evaluate_priority_change(
        self, 
        context: ConversationContext, 
        old_priority: str, 
        new_priority: str
    ):
        """Evaluate rules triggered by priority changes"""
        
        workspace = context.conversation.workspace
        rules = BusinessRule.objects.filter(
            workspace=workspace,
            is_active=True,
            trigger_type='priority_change'
        ).order_by('priority')
        
        context_data = {
            'context_data': context.context_data,
            'status': context.status,
            'priority': new_priority,
            'completion_percentage': context.completion_percentage,
            'tags': context.tags
        }
        
        trigger_data = {
            'trigger_type': 'priority_change',
            'old_priority': old_priority,
            'new_priority': new_priority,
            'context_id': str(context.id)
        }
        
        for rule in rules:
            try:
                self._evaluate_and_execute_rule(rule, context, context_data, trigger_data)
            except Exception as e:
                logger.error(f"Rule evaluation failed for rule {rule.id}: {str(e)}")
    
    def _evaluate_and_execute_rule(
        self, 
        rule: BusinessRule, 
        context: ConversationContext,
        context_data: Dict[str, Any], 
        trigger_data: Dict[str, Any]
    ):
        """Evaluate and execute a single rule"""
        
        start_time = time.time()
        
        try:
            # Evaluate conditions
            conditions_met = rule.evaluate_conditions(context_data)
            
            if conditions_met:
                logger.info(f"Executing rule {rule.name} for context {context.id}")
                
                # Execute actions
                execution_result = rule.execute_actions(context, trigger_data)
                
                execution_time = time.time() - start_time
                success = all(action.get('success', False) for action in execution_result)
                
                # Log execution
                RuleExecution.objects.create(
                    rule=rule,
                    context=context,
                    trigger_type=trigger_data['trigger_type'],
                    trigger_data=trigger_data,
                    execution_result=execution_result,
                    success=success,
                    execution_time=execution_time
                )
                
                logger.info(f"Rule {rule.name} executed successfully in {execution_time:.2f}s")
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Log failed execution
            RuleExecution.objects.create(
                rule=rule,
                context=context,
                trigger_type=trigger_data['trigger_type'],
                trigger_data=trigger_data,
                execution_result={},
                success=False,
                error_message=str(e),
                execution_time=execution_time
            )
            
            logger.error(f"Rule {rule.name} execution failed: {str(e)}")
            raise
    
    def evaluate_time_based_rules(self, workspace_id: str):
        """Evaluate time-based rules for a workspace"""
        
        from core.models import Workspace
        workspace = Workspace.objects.get(id=workspace_id)
        
        rules = BusinessRule.objects.filter(
            workspace=workspace,
            is_active=True,
            trigger_type='time_elapsed'
        ).order_by('priority')
        
        # Get contexts that might trigger time-based rules
        contexts = ConversationContext.objects.filter(
            conversation__workspace=workspace,
            status__in=['new', 'in_progress']  # Only active contexts
        )
        
        for context in contexts:
            context_data = {
                'context_data': context.context_data,
                'status': context.status,
                'priority': context.priority,
                'completion_percentage': context.completion_percentage,
                'tags': context.tags,
                'created_at': context.created_at,
                'updated_at': context.updated_at,
                'hours_since_created': (timezone.now() - context.created_at).total_seconds() / 3600,
                'hours_since_updated': (timezone.now() - context.updated_at).total_seconds() / 3600
            }
            
            trigger_data = {
                'trigger_type': 'time_elapsed',
                'context_id': str(context.id),
                'evaluated_at': timezone.now()
            }
            
            for rule in rules:
                try:
                    self._evaluate_and_execute_rule(rule, context, context_data, trigger_data)
                except Exception as e:
                    logger.error(f"Time-based rule evaluation failed for rule {rule.id}: {str(e)}")


class ContextMigrationService:
    """Service for migrating existing conversations to dynamic context system"""
    
    def __init__(self):
        self.extraction_service = ContextExtractionService()
    
    def migrate_workspace_conversations(self, workspace_id: str, schema_id: str):
        """Migrate all conversations in a workspace to use dynamic context"""
        
        from core.models import Workspace, Conversation
        from .models import WorkspaceContextSchema
        
        workspace = Workspace.objects.get(id=workspace_id)
        schema = WorkspaceContextSchema.objects.get(id=schema_id)
        
        conversations = Conversation.objects.filter(
            workspace=workspace
        ).exclude(
            dynamic_context__isnull=False  # Skip conversations that already have context
        )
        
        migrated_count = 0
        failed_count = 0
        
        for conversation in conversations:
            try:
                self._migrate_single_conversation(conversation, schema)
                migrated_count += 1
            except Exception as e:
                logger.error(f"Failed to migrate conversation {conversation.id}: {str(e)}")
                failed_count += 1
        
        return {
            'migrated_count': migrated_count,
            'failed_count': failed_count,
            'total_conversations': conversations.count()
        }
    
    def _migrate_single_conversation(self, conversation, schema):
        """Migrate a single conversation to dynamic context"""
        
        # Create new context
        context = ConversationContext.objects.create(
            conversation=conversation,
            schema=schema,
            title=conversation.summary[:255] if conversation.summary else "Migrated Conversation",
            context_data={},
            status='new',
            priority='medium'
        )
        
        # Try to extract context from existing data
        existing_data = {
            'summary': conversation.summary,
            'key_points': conversation.key_points,
            'action_items': conversation.action_items,
            'sentiment_score': conversation.sentiment_score,
            'extracted_entities': conversation.extracted_entities
        }
        
        # If there's existing summary, try to extract context from it
        if conversation.summary:
            try:
                self.extraction_service.extract_context_from_text(
                    context=context,
                    text=conversation.summary,
                    force_extraction=True
                )
            except Exception as e:
                logger.warning(f"Failed to extract context from summary: {str(e)}")
        
        # Map existing fields to context data where possible
        self._map_existing_fields(context, existing_data)
        
        context.save()
        
        logger.info(f"Migrated conversation {conversation.id} to dynamic context")
    
    def _map_existing_fields(self, context, existing_data):
        """Map existing conversation data to context fields"""
        
        # Map sentiment score to priority
        sentiment_score = existing_data.get('sentiment_score', 3)
        if sentiment_score <= 2:
            context.priority = 'high'  # Low satisfaction = high priority
        elif sentiment_score >= 4:
            context.priority = 'low'   # High satisfaction = low priority
        else:
            context.priority = 'medium'
        
        # Map resolution status
        if existing_data.get('resolution_status') == 'resolved':
            context.status = 'resolved'
        elif existing_data.get('action_items'):
            context.status = 'in_progress'
        else:
            context.status = 'new'
        
        # Add existing entities as tags
        entities = existing_data.get('extracted_entities', {})
        tags = []
        for entity_type, entity_values in entities.items():
            if isinstance(entity_values, list):
                tags.extend(entity_values)
            elif isinstance(entity_values, str):
                tags.append(entity_values)
        
        context.tags = tags[:10]  # Limit to 10 tags
        
        # Store original data in metadata
        context.metadata = {
            'migrated_from_legacy': True,
            'original_summary': existing_data.get('summary'),
            'original_key_points': existing_data.get('key_points'),
            'original_action_items': existing_data.get('action_items'),
            'migration_date': timezone.now().isoformat()
        }
