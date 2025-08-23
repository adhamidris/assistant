import json
import logging
import time
from typing import Dict, List, Any, Optional
from django.utils import timezone
from django.db import transaction

from messaging.deepseek_client import DeepSeekClient
from .models import ConversationContext, ContextHistory, BusinessRule, RuleExecution

logger = logging.getLogger(__name__)


class EnhancedContextExtraction:
    """Enhanced context extraction with AI-powered field discovery and pattern recognition"""
    
    def __init__(self):
        self.deepseek_client = DeepSeekClient()
        self.pattern_cache = {}  # Cache for discovered patterns
        self.field_suggestions = {}  # Cache for field suggestions
    
    def discover_new_fields(
        self, 
        workspace_id: str, 
        conversation_texts: List[str],
        existing_schema: Dict = None
    ) -> List[Dict]:
        """
        Discover new fields that could be added to the schema based on conversation patterns
        
        Args:
            workspace_id: ID of the workspace
            conversation_texts: List of conversation texts to analyze
            existing_schema: Current schema to avoid duplicates
            
        Returns:
            List of discovered field suggestions
        """
        try:
            # Analyze conversation patterns
            patterns = self._analyze_conversation_patterns(conversation_texts)
            
            # Extract potential field candidates
            field_candidates = self._extract_field_candidates(patterns, existing_schema)
            
            # Score and rank candidates
            scored_candidates = self._score_field_candidates(field_candidates, patterns)
            
            # Generate field suggestions
            field_suggestions = self._generate_field_suggestions(scored_candidates, workspace_id)
            
            return field_suggestions
            
        except Exception as e:
            logger.error(f"Field discovery failed: {str(e)}")
            return []
    
    def _analyze_conversation_patterns(self, texts: List[str]) -> Dict[str, Any]:
        """Analyze conversation texts for recurring patterns and entities"""
        patterns = {
            'entities': {},
            'phrases': {},
            'contextual_clues': {},
            'temporal_patterns': {},
            'numerical_patterns': {},
            'categorical_patterns': {}
        }
        
        for text in texts:
            # Extract named entities
            entities = self._extract_named_entities(text)
            for entity_type, entities_list in entities.items():
                if entity_type not in patterns['entities']:
                    patterns['entities'][entity_type] = {}
                for entity in entities_list:
                    if entity not in patterns['entities'][entity_type]:
                        patterns['entities'][entity_type][entity] = 0
                    patterns['entities'][entity_type][entity] += 1
            
            # Extract recurring phrases
            phrases = self._extract_recurring_phrases(text)
            for phrase in phrases:
                if phrase not in patterns['phrases']:
                    patterns['phrases'][phrase] = 0
                patterns['phrases'][phrase] += 1
            
            # Extract contextual clues
            clues = self._extract_contextual_clues(text)
            for clue_type, clue_values in clues.items():
                if clue_type not in patterns['contextual_clues']:
                    patterns['contextual_clues'][clue_type] = {}
                for clue in clue_values:
                    if clue not in patterns['contextual_clues'][clue_type]:
                        patterns['contextual_clues'][clue_type][clue] = 0
                    patterns['contextual_clues'][clue_type][clue] += 1
        
        return patterns
    
    def _extract_named_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities from text using AI"""
        try:
            prompt = f"""Extract named entities from this business conversation text. Categorize them by type:

Text: "{text}"

Return as JSON:
{{
    "persons": ["list of person names"],
    "organizations": ["list of company/organization names"],
    "locations": ["list of places, addresses"],
    "dates": ["list of dates, times"],
    "products": ["list of product names"],
    "services": ["list of service names"],
    "custom_fields": ["list of other business-specific entities"]
}}

Only include entities that are clearly identifiable."""
            
            response = self.deepseek_client.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a named entity recognition specialist for business conversations."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            response_text = response["choices"][0]["message"]["content"].strip()
            entities = json.loads(response_text)
            return entities
            
        except Exception as e:
            logger.warning(f"Named entity extraction failed: {str(e)}")
            return {}
    
    def _extract_recurring_phrases(self, text: str) -> List[str]:
        """Extract recurring phrases that might indicate field patterns"""
        try:
            prompt = f"""Identify recurring phrases or patterns in this business conversation that might represent data fields:

Text: "{text}"

Look for:
- Repeated questions or requests
- Consistent data points mentioned
- Standard business processes
- Recurring customer needs

Return as JSON array of phrases:
["phrase 1", "phrase 2", "phrase 3"]"""
            
            response = self.deepseek_client.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a business process analyst identifying recurring patterns."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=300
            )
            
            response_text = response["choices"][0]["message"]["content"].strip()
            phrases = json.loads(response_text)
            return phrases
            
        except Exception as e:
            logger.warning(f"Phrase extraction failed: {str(e)}")
            return []
    
    def _extract_contextual_clues(self, text: str) -> Dict[str, List[str]]:
        """Extract contextual clues that suggest field types"""
        try:
            prompt = f"""Analyze this business conversation for contextual clues that suggest data field types:

Text: "{text}"

Look for:
- Data types (numbers, dates, text, choices)
- Business processes (statuses, workflows, priorities)
- Customer attributes (preferences, history, demographics)
- Business metrics (scores, ratings, measurements)

Return as JSON:
{{
    "data_types": ["text", "number", "date", "choice"],
    "business_processes": ["status", "workflow", "priority"],
    "customer_attributes": ["preference", "history", "demographic"],
    "business_metrics": ["score", "rating", "measurement"]
}}"""
            
            response = self.deepseek_client.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a business analyst identifying data field patterns."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=400
            )
            
            response_text = response["choices"][0]["message"]["content"].strip()
            clues = json.loads(response_text)
            return clues
            
        except Exception as e:
            logger.warning(f"Contextual clue extraction failed: {str(e)}")
            return {}
    
    def _extract_field_candidates(self, patterns: Dict, existing_schema: Dict) -> List[Dict]:
        """Extract potential field candidates from patterns"""
        candidates = []
        
        # Extract from named entities
        for entity_type, entities in patterns['entities'].items():
            for entity, frequency in entities.items():
                if frequency >= 2:  # Only consider frequently mentioned entities
                    candidate = {
                        'name': entity.lower().replace(' ', '_'),
                        'label': entity,
                        'type': self._infer_field_type(entity_type, entity),
                        'source': 'named_entity',
                        'frequency': frequency,
                        'confidence': min(frequency / 5.0, 1.0)  # Scale confidence by frequency
                    }
                    candidates.append(candidate)
        
        # Extract from recurring phrases
        for phrase, frequency in patterns['phrases'].items():
            if frequency >= 2:
                candidate = {
                    'name': phrase.lower().replace(' ', '_').replace('-', '_'),
                    'label': phrase,
                    'type': self._infer_field_type_from_phrase(phrase),
                    'source': 'recurring_phrase',
                    'frequency': frequency,
                    'confidence': min(frequency / 5.0, 1.0)
                }
                candidates.append(candidate)
        
        # Extract from contextual clues
        for clue_type, clues in patterns['contextual_clues'].items():
            for clue, frequency in clues.items():
                if frequency >= 2:
                    candidate = {
                        'name': clue.lower().replace(' ', '_'),
                        'label': clue,
                        'type': self._infer_field_type_from_clue(clue_type, clue),
                        'source': 'contextual_clue',
                        'frequency': frequency,
                        'confidence': min(frequency / 5.0, 1.0)
                    }
                    candidates.append(candidate)
        
        return candidates
    
    def _infer_field_type(self, entity_type: str, entity: str) -> str:
        """Infer field type from entity type"""
        type_mapping = {
            'persons': 'text',
            'organizations': 'text',
            'locations': 'text',
            'dates': 'date',
            'products': 'choice',
            'services': 'choice',
            'custom_fields': 'text'
        }
        return type_mapping.get(entity_type, 'text')
    
    def _infer_field_type_from_phrase(self, phrase: str) -> str:
        """Infer field type from recurring phrase"""
        phrase_lower = phrase.lower()
        
        if any(word in phrase_lower for word in ['date', 'time', 'when', 'schedule']):
            return 'date'
        elif any(word in phrase_lower for word in ['number', 'amount', 'quantity', 'count']):
            return 'number'
        elif any(word in phrase_lower for word in ['status', 'state', 'condition']):
            return 'choice'
        elif any(word in phrase_lower for word in ['priority', 'level', 'rating']):
            return 'choice'
        else:
            return 'text'
    
    def _infer_field_type_from_clue(self, clue_type: str, clue: str) -> str:
        """Infer field type from contextual clue"""
        type_mapping = {
            'data_types': 'text',
            'business_processes': 'choice',
            'customer_attributes': 'text',
            'business_metrics': 'number'
        }
        return type_mapping.get(clue_type, 'text')
    
    def _score_field_candidates(self, candidates: List[Dict], patterns: Dict) -> List[Dict]:
        """Score and rank field candidates based on business value and confidence"""
        scored_candidates = []
        
        for candidate in candidates:
            # Base score from confidence
            score = candidate['confidence']
            
            # Boost score for business-critical fields
            business_keywords = ['customer', 'order', 'payment', 'status', 'priority', 'date', 'time']
            if any(keyword in candidate['name'] for keyword in business_keywords):
                score += 0.2
            
            # Boost score for frequently mentioned fields
            if candidate['frequency'] >= 3:
                score += 0.1
            
            # Boost score for structured data types
            if candidate['type'] in ['date', 'number', 'choice']:
                score += 0.1
            
            # Cap score at 1.0
            score = min(score, 1.0)
            
            candidate['business_value_score'] = score
            scored_candidates.append(candidate)
        
        # Sort by business value score (descending)
        scored_candidates.sort(key=lambda x: x['business_value_score'], reverse=True)
        
        return scored_candidates
    
    def _generate_field_suggestions(self, candidates: List[Dict], workspace_id: str) -> List[Dict]:
        """Generate final field suggestions for the workspace"""
        suggestions = []
        
        for candidate in candidates:
            if candidate['business_value_score'] >= 0.5:  # Only suggest high-value fields
                suggestion = {
                    'suggested_field_name': candidate['name'],
                    'field_type': candidate['type'],
                    'description': f"Discovered from {candidate['source']} analysis",
                    'frequency_detected': candidate['frequency'],
                    'confidence_score': candidate['confidence'],
                    'business_value_score': candidate['business_value_score'],
                    'detection_pattern': candidate['source'],
                    'sample_values': [candidate['label']],
                    'workspace_id': workspace_id
                }
                suggestions.append(suggestion)
        
        return suggestions


class FieldSuggestionService:
    """Service for managing AI-discovered field suggestions and user approval workflow"""
    
    def __init__(self):
        self.enhanced_extraction = EnhancedContextExtraction()
    
    def generate_suggestions_for_workspace(
        self, 
        workspace_id: str, 
        limit: int = 10
    ) -> List[Dict]:
        """
        Generate field suggestions for a workspace based on recent conversations
        
        Args:
            workspace_id: ID of the workspace
            limit: Maximum number of suggestions to generate
            
        Returns:
            List of field suggestions
        """
        try:
            from .models import ConversationContext, Conversation
            from core.models import Workspace
            
            # Get workspace and existing schemas
            workspace = Workspace.objects.get(id=workspace_id)
            existing_schemas = workspace.context_schemas.all()
            
            # Get recent conversations for analysis
            recent_conversations = Conversation.objects.filter(
                workspace=workspace
            ).order_by('-created_at')[:50]  # Last 50 conversations
            
            # Extract conversation texts
            conversation_texts = []
            for conv in recent_conversations:
                # Get messages from conversation
                messages = conv.messages.all()
                for msg in messages:
                    if msg.text:
                        conversation_texts.append(msg.text)
            
            if not conversation_texts:
                return []
            
            # Discover new fields using enhanced extraction
            suggestions = self.enhanced_extraction.discover_new_fields(
                workspace_id=workspace_id,
                conversation_texts=conversation_texts,
                existing_schema=existing_schemas.first() if existing_schemas.exists() else None
            )
            
            # Filter out suggestions that already exist in schemas
            filtered_suggestions = self._filter_existing_fields(suggestions, existing_schemas)
            
            # Limit suggestions
            limited_suggestions = filtered_suggestions[:limit]
            
            # Create DynamicFieldSuggestion objects
            created_suggestions = []
            for suggestion in limited_suggestions:
                from .models import DynamicFieldSuggestion
                
                field_suggestion = DynamicFieldSuggestion.objects.create(
                    workspace=workspace,
                    suggested_field_name=suggestion['suggested_field_name'],
                    field_type=suggestion['field_type'],
                    description=suggestion['description'],
                    frequency_detected=suggestion['frequency_detected'],
                    sample_values=suggestion['sample_values'],
                    confidence_score=suggestion['confidence_score'],
                    business_value_score=suggestion['business_value_score'],
                    detection_pattern=suggestion['detection_pattern'],
                    context_examples=conversation_texts[:3]  # Store first 3 examples
                )
                created_suggestions.append(field_suggestion)
            
            return created_suggestions
            
        except Exception as e:
            logger.error(f"Failed to generate suggestions for workspace {workspace_id}: {str(e)}")
            return []
    
    def _filter_existing_fields(self, suggestions: List[Dict], existing_schemas) -> List[Dict]:
        """Filter out suggestions that already exist in schemas"""
        filtered_suggestions = []
        
        # Get all existing field names
        existing_field_names = set()
        for schema in existing_schemas:
            if schema.fields:
                for field in schema.fields:
                    existing_field_names.add(field.get('name', '').lower())
        
        # Filter suggestions
        for suggestion in suggestions:
            if suggestion['suggested_field_name'].lower() not in existing_field_names:
                filtered_suggestions.append(suggestion)
        
        return filtered_suggestions
    
    def approve_suggestion(
        self, 
        suggestion_id: str, 
        user_id: str,
        target_schema_id: str = None,
        notes: str = ""
    ) -> bool:
        """
        Approve a field suggestion and optionally implement it in a schema
        
        Args:
            suggestion_id: ID of the DynamicFieldSuggestion
            user_id: ID of the user approving the suggestion
            target_schema_id: ID of the schema to implement the field in
            notes: Additional notes about the implementation
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from .models import DynamicFieldSuggestion
            from django.contrib.auth.models import User
            
            suggestion = DynamicFieldSuggestion.objects.get(id=suggestion_id)
            user = User.objects.get(id=user_id)
            
            # Approve the suggestion
            if target_schema_id:
                from .models import WorkspaceContextSchema
                target_schema = WorkspaceContextSchema.objects.get(id=target_schema_id)
                suggestion.approve(user, target_schema, notes)
            else:
                suggestion.approve(user, notes=notes)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to approve suggestion {suggestion_id}: {str(e)}")
            return False
    
    def reject_suggestion(
        self, 
        suggestion_id: str, 
        user_id: str,
        notes: str = ""
    ) -> bool:
        """
        Reject a field suggestion
        
        Args:
            suggestion_id: ID of the DynamicFieldSuggestion
            user_id: ID of the user rejecting the suggestion
            notes: Reason for rejection
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from .models import DynamicFieldSuggestion
            from django.contrib.auth.models import User
            
            suggestion = DynamicFieldSuggestion.objects.get(id=suggestion_id)
            user = User.objects.get(id=user_id)
            
            suggestion.reject(user, notes)
            return True
            
        except Exception as e:
            logger.error(f"Failed to reject suggestion {suggestion_id}: {str(e)}")
            return False
    
    def get_suggestion_analytics(self, workspace_id: str) -> Dict[str, Any]:
        """
        Get analytics about field suggestions for a workspace
        
        Args:
            workspace_id: ID of the workspace
            
        Returns:
            Dictionary with analytics data
        """
        try:
            from .models import DynamicFieldSuggestion
            
            suggestions = DynamicFieldSuggestion.objects.filter(workspace_id=workspace_id)
            
            total_suggestions = suggestions.count()
            approved_suggestions = suggestions.filter(is_approved=True).count()
            rejected_suggestions = suggestions.filter(is_reviewed=True, is_approved=False).count()
            pending_suggestions = suggestions.filter(is_reviewed=False).count()
            
            # Field type distribution
            field_type_counts = {}
            for suggestion in suggestions:
                field_type = suggestion.field_type
                if field_type not in field_type_counts:
                    field_type_counts[field_type] = 0
                field_type_counts[field_type] += 1
            
            # Confidence score distribution
            high_confidence = suggestions.filter(confidence_score__gte=0.8).count()
            medium_confidence = suggestions.filter(confidence_score__gte=0.6, confidence_score__lt=0.8).count()
            low_confidence = suggestions.filter(confidence_score__lt=0.6).count()
            
            # Business value distribution
            high_value = suggestions.filter(business_value_score__gte=0.8).count()
            medium_value = suggestions.filter(business_value_score__gte=0.6, business_value_score__lt=0.8).count()
            low_value = suggestions.filter(business_value_score__lt=0.6).count()
            
            return {
                'total_suggestions': total_suggestions,
                'approved_suggestions': approved_suggestions,
                'rejected_suggestions': rejected_suggestions,
                'pending_suggestions': pending_suggestions,
                'approval_rate': approved_suggestions / total_suggestions if total_suggestions > 0 else 0,
                'field_type_distribution': field_type_counts,
                'confidence_distribution': {
                    'high': high_confidence,
                    'medium': medium_confidence,
                    'low': low_confidence
                },
                'business_value_distribution': {
                    'high': high_value,
                    'medium': medium_value,
                    'low': low_value
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get suggestion analytics for workspace {workspace_id}: {str(e)}")
            return {}


class ContextExtractionService:
    """Service for extracting context from conversations using AI"""
    
    def __init__(self):
        self.deepseek_client = DeepSeekClient()
    
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
            
            # Use DeepSeek for context extraction
            response = self.deepseek_client.chat_completion(
                messages=messages,
                temperature=0.1,
                max_tokens=1000
            )
            
            # Parse DeepSeek response format
            if "choices" not in response or not response["choices"]:
                logger.warning("DeepSeek context extraction failed: No choices in response")
                return {}
            
            response_text = response["choices"][0]["message"]["content"].strip()
            
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
            
            # Use DeepSeek for title generation
            response = self.deepseek_client.chat_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=50
            )
            
            # Parse DeepSeek response format
            if "choices" not in response or not response["choices"]:
                logger.warning("DeepSeek title generation failed: No choices in response")
                return f"Conversation {conversation.id[:8]}"
            
            title = response["choices"][0]["message"]["content"].strip().strip('"\'')
            
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
        self.logger = logging.getLogger(__name__)
    
    def _safe_get_context_data(self, context: ConversationContext) -> Dict[str, Any]:
        """Safely extract context data with fallbacks for None values"""
        try:
            return {
                'context_data': context.context_data or {},
                'status': context.status or 'new',
                'priority': context.priority or 'medium',
                'completion_percentage': getattr(context, 'completion_percentage', 0) or 0,
                'tags': context.tags or [],
                'created_at': getattr(context, 'created_at', None),
                'updated_at': getattr(context, 'updated_at', None)
            }
        except Exception as e:
            self.logger.error(f"Error extracting context data: {str(e)}")
            return {
                'context_data': {},
                'status': 'new',
                'priority': 'medium',
                'completion_percentage': 0,
                'tags': [],
                'created_at': None,
                'updated_at': None
            }
    
    def evaluate_context_change(
        self, 
        context: ConversationContext, 
        changed_fields: Dict[str, Any]
    ):
        """Evaluate rules triggered by context field changes"""
        
        # Ensure changed_fields is a dict, not None
        if changed_fields is None:
            changed_fields = {}
        
        workspace = context.conversation.workspace
        rules = BusinessRule.objects.filter(
            workspace=workspace,
            is_active=True,
            trigger_type__in=['context_change', 'completion_rate']
        ).order_by('priority')
        
        context_data = self._safe_get_context_data(context)
        
        # Ensure context_data is a dict
        if not isinstance(context_data, dict):
            context_data = {}
        
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
        
        context_data = self._safe_get_context_data(context)
        
        # Ensure context_data is a dict
        if not isinstance(context_data, dict):
            context_data = {}
        
        context_data['status'] = new_status  # Override with new status
        
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
        
        context_data = self._safe_get_context_data(context)
        
        # Ensure context_data is a dict
        if not isinstance(context_data, dict):
            context_data = {}
        
        context_data['message_data'] = message_data
        
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
        
        context_data = self._safe_get_context_data(context)
        
        # Ensure context_data is a dict
        if not isinstance(context_data, dict):
            context_data = {}
        
        context_data['priority'] = new_priority  # Override with new priority
        
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
            # Validate rule and context
            if not rule or not context:
                self.logger.error("Invalid rule or context provided")
                return
            
            # Ensure context has required attributes
            if not hasattr(context, 'id') or not hasattr(context, 'conversation'):
                self.logger.error("Context missing required attributes")
                return
            
            # Ensure trigger_data has required fields
            if not trigger_data:
                trigger_data = {'trigger_type': 'unknown'}
            elif not isinstance(trigger_data, dict):
                trigger_data = {'trigger_type': 'unknown'}
            
            # Evaluate conditions
            try:
                # Ensure context_data is properly formatted
                if not isinstance(context_data, dict):
                    context_data = {}
                
                conditions_met = rule.evaluate_conditions(context_data)
            except Exception as condition_error:
                self.logger.error(f"Condition evaluation failed for rule {rule.id}: {str(condition_error)}")
                conditions_met = False
            
            if conditions_met:
                self.logger.info(f"Executing rule {rule.name} for context {context.id}")
                
                try:
                    # Execute actions
                    execution_result = rule.execute_actions(context, trigger_data)
                    
                    execution_time = time.time() - start_time
                    
                    # Ensure execution_result is a list
                    if not isinstance(execution_result, list):
                        execution_result = []
                    
                    success = all(action.get('success', False) for action in execution_result)
                    
                    # Log execution
                    try:
                        RuleExecution.objects.create(
                            rule=rule,
                            context=context,
                            trigger_type=trigger_data.get('trigger_type', 'unknown'),
                            trigger_data=trigger_data,
                            execution_result=execution_result,
                            success=success,
                            execution_time=execution_time
                        )
                    except Exception as log_error:
                        self.logger.error(f"Failed to log rule execution: {str(log_error)}")
                    
                    self.logger.info(f"Rule {rule.name} executed successfully in {execution_time:.2f}s")
                    
                except Exception as action_error:
                    self.logger.error(f"Action execution failed for rule {rule.name}: {str(action_error)}")
                    raise
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            # Log failed execution
            try:
                RuleExecution.objects.create(
                    rule=rule,
                    context=context,
                    trigger_type=trigger_data.get('trigger_type', 'unknown'),
                    trigger_data=trigger_data,
                    execution_result={},
                    success=False,
                    error_message=str(e),
                    execution_time=execution_time
                )
            except Exception as log_error:
                self.logger.error(f"Failed to log failed rule execution: {str(log_error)}")
            
            self.logger.error(f"Rule {rule.name} execution failed: {str(e)}")
            # Don't raise the error - just log it to prevent cascading failures
            # raise
    
    def create_default_rules_for_workspace(self, workspace_id: str):
        """Create default business rules for a new workspace"""
        try:
            from core.models import Workspace
            from .models import BusinessRule
            
            workspace = Workspace.objects.get(id=workspace_id)
            
            # Check if default rules already exist
            existing_rules = BusinessRule.objects.filter(workspace=workspace, is_default=True)
            if existing_rules.exists():
                self.logger.info(f"Default rules already exist for workspace {workspace_id}")
                return
            
            # Create default rules
            default_rules = [
                {
                    'name': 'High Priority Escalation',
                    'description': 'Automatically escalate high priority conversations',
                    'trigger_type': 'priority_change',
                    'trigger_conditions': {
                        'operator': 'and',
                        'rules': [
                            {'field': 'priority', 'operator': 'equals', 'value': 'high'},
                            {'field': 'status', 'operator': 'equals', 'value': 'new'}
                        ]
                    },
                    'actions': [
                        {
                            'type': 'change_status',
                            'config': {'status': 'in_progress'}
                        },
                        {
                            'type': 'assign_tag',
                            'config': {'tag': 'escalated'}
                        }
                    ],
                    'priority': 1,
                    'is_default': True
                },
                {
                    'name': 'Completion Rate Alert',
                    'description': 'Alert when conversation completion rate is low',
                    'trigger_type': 'completion_rate',
                    'trigger_conditions': {
                        'operator': 'and',
                        'rules': [
                            {'field': 'completion_rate', 'operator': 'less_than', 'value': 50},
                            {'field': 'status', 'operator': 'equals', 'value': 'in_progress'}
                        ]
                    },
                    'actions': [
                        {
                            'type': 'assign_tag',
                            'config': {'tag': 'needs_attention'}
                        },
                        {
                            'type': 'send_notification',
                            'config': {'message': 'Conversation completion rate is below 50%'}
                        }
                    ],
                    'priority': 2,
                    'is_default': True
                },
                {
                    'name': 'New Message Auto-Reply',
                    'description': 'Send automatic response for new messages',
                    'trigger_type': 'new_message',
                    'trigger_conditions': {
                        'operator': 'and',
                        'rules': [
                            {'field': 'status', 'operator': 'equals', 'value': 'new'}
                        ]
                    },
                    'actions': [
                        {
                            'type': 'assign_tag',
                            'config': {'tag': 'auto_replied'}
                        },
                        {
                            'type': 'generate_ai_response',
                            'config': {}
                        }
                    ],
                    'priority': 3,
                    'is_default': True
                }
            ]
            
            for rule_data in default_rules:
                BusinessRule.objects.create(
                    workspace=workspace,
                    **rule_data
                )
            
            self.logger.info(f"Created {len(default_rules)} default rules for workspace {workspace_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to create default rules for workspace {workspace_id}: {str(e)}")
    
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
            context_data = self._safe_get_context_data(context)
            
            # Ensure context_data is a dict
            if not isinstance(context_data, dict):
                context_data = {}
            
            # Add time-based calculations
            if context.created_at:
                context_data['hours_since_created'] = (timezone.now() - context.created_at).total_seconds() / 3600
            if context.updated_at:
                context_data['hours_since_updated'] = (timezone.now() - context.updated_at).total_seconds() / 3600
            
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
