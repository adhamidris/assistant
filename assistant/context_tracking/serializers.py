from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    WorkspaceContextSchema, ConversationContext, 
    ContextHistory, BusinessRule, RuleExecution, DynamicFieldSuggestion
)


class FieldDefinitionSerializer(serializers.Serializer):
    """Serializer for field definitions within schema"""
    id = serializers.CharField(max_length=100)
    label = serializers.CharField(max_length=200)
    type = serializers.ChoiceField(choices=WorkspaceContextSchema.FIELD_TYPES)
    required = serializers.BooleanField(default=False)
    choices = serializers.ListField(child=serializers.CharField(), required=False)
    default_value = serializers.CharField(required=False, allow_blank=True)
    help_text = serializers.CharField(required=False, allow_blank=True)
    ai_extractable = serializers.BooleanField(default=True)
    extraction_keywords = serializers.ListField(child=serializers.CharField(), required=False)
    depends_on = serializers.CharField(required=False, allow_null=True)
    display_order = serializers.IntegerField(default=1)
    validation_rules = serializers.DictField(required=False)


class StatusDefinitionSerializer(serializers.Serializer):
    """Serializer for status definitions in workflow"""
    id = serializers.CharField(max_length=50)
    label = serializers.CharField(max_length=100)
    color = serializers.CharField(max_length=20, default='blue')
    description = serializers.CharField(required=False, allow_blank=True)


class WorkspaceContextSchemaSerializer(serializers.ModelSerializer):
    """Serializer for workspace context schemas"""
    
    fields = FieldDefinitionSerializer(many=True, required=False)
    field_count = serializers.ReadOnlyField()
    required_field_count = serializers.ReadOnlyField()
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkspaceContextSchema
        fields = [
            'id', 'workspace', 'name', 'description', 'fields', 
            'status_workflow', 'priority_config', 'is_active', 
            'is_default', 'field_count', 'required_field_count',
            'created_at', 'updated_at', 'created_by', 'created_by_name'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None
    
    def validate_fields(self, value):
        """Validate field definitions"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Fields must be a list")
        
        field_ids = []
        for field in value:
            field_id = field.get('id')
            if not field_id:
                raise serializers.ValidationError("Each field must have an 'id'")
            
            if field_id in field_ids:
                raise serializers.ValidationError(f"Duplicate field ID: {field_id}")
            
            field_ids.append(field_id)
            
            # Validate field type
            field_type = field.get('type')
            valid_types = [choice[0] for choice in WorkspaceContextSchema.FIELD_TYPES]
            if field_type not in valid_types:
                raise serializers.ValidationError(f"Invalid field type: {field_type}")
            
            # Validate choices for choice fields
            if field_type in ['choice', 'multi_choice'] and not field.get('choices'):
                raise serializers.ValidationError(f"Field {field_id} requires 'choices' for type {field_type}")
        
        return value
    
    def validate_status_workflow(self, value):
        """Validate status workflow configuration"""
        if not value:
            return value
        
        statuses = value.get('statuses', [])
        transitions = value.get('transitions', {})
        
        # Validate status definitions
        status_ids = []
        for status in statuses:
            status_id = status.get('id')
            if not status_id:
                raise serializers.ValidationError("Each status must have an 'id'")
            
            if status_id in status_ids:
                raise serializers.ValidationError(f"Duplicate status ID: {status_id}")
            
            status_ids.append(status_id)
        
        # Validate transitions reference valid statuses
        for from_status, to_statuses in transitions.items():
            if from_status not in status_ids:
                raise serializers.ValidationError(f"Invalid transition from status: {from_status}")
            
            for to_status in to_statuses:
                if to_status not in status_ids:
                    raise serializers.ValidationError(f"Invalid transition to status: {to_status}")
        
        return value


class ConversationContextSerializer(serializers.ModelSerializer):
    """Serializer for conversation contexts"""
    
    completion_percentage = serializers.ReadOnlyField()
    field_count = serializers.ReadOnlyField()
    high_confidence_fields = serializers.ReadOnlyField()
    schema_name = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()
    priority_label = serializers.SerializerMethodField()
    
    class Meta:
        model = ConversationContext
        fields = [
            'id', 'conversation', 'schema', 'title', 'context_data',
            'ai_confidence_scores', 'status', 'priority', 'tags', 'metadata',
            'completion_percentage', 'field_count', 'high_confidence_fields',
            'schema_name', 'status_label', 'priority_label',
            'created_at', 'updated_at', 'last_ai_update', 'last_human_update'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_schema_name(self, obj):
        return obj.schema.name if obj.schema else None
    
    def get_status_label(self, obj):
        if not obj.schema:
            return obj.status
        
        statuses = obj.schema.get_status_choices()
        for status in statuses:
            if status.get('id') == obj.status:
                return status.get('label', obj.status)
        
        return obj.status
    
    def get_priority_label(self, obj):
        priority_labels = {
            'low': 'Low',
            'medium': 'Medium', 
            'high': 'High',
            'urgent': 'Urgent'
        }
        return priority_labels.get(obj.priority, obj.priority)
    
    def validate_status(self, value):
        """Validate status against schema workflow"""
        schema = self.instance.schema if self.instance else None
        if schema and self.instance:
            current_status = self.instance.status
            if not schema.can_transition_status(current_status, value):
                raise serializers.ValidationError(
                    f"Cannot transition from '{current_status}' to '{value}'"
                )
        return value


class ContextHistorySerializer(serializers.ModelSerializer):
    """Serializer for context history"""
    
    changed_by_name = serializers.SerializerMethodField()
    action_label = serializers.SerializerMethodField()
    
    class Meta:
        model = ContextHistory
        fields = [
            'id', 'context', 'action_type', 'field_name', 'old_value', 
            'new_value', 'changed_by_ai', 'changed_by_user', 'changed_by_name',
            'confidence_score', 'metadata', 'action_label', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_changed_by_name(self, obj):
        if obj.changed_by_ai:
            return "AI Assistant"
        elif obj.changed_by_user:
            return obj.changed_by_user.get_full_name() or obj.changed_by_user.username
        return "System"
    
    def get_action_label(self, obj):
        action_labels = {
            'created': 'Context Created',
            'field_updated': 'Field Updated',
            'status_changed': 'Status Changed',
            'priority_changed': 'Priority Changed',
            'ai_updated': 'AI Updated',
            'schema_changed': 'Schema Changed',
            'bulk_update': 'Bulk Update',
        }
        return action_labels.get(obj.action_type, obj.action_type)


class BusinessRuleConditionSerializer(serializers.Serializer):
    """Serializer for business rule conditions"""
    field = serializers.CharField(max_length=100)
    operator = serializers.ChoiceField(choices=[
        ('equals', 'Equals'),
        ('not_equals', 'Not Equals'),
        ('contains', 'Contains'),
        ('greater_than', 'Greater Than'),
        ('less_than', 'Less Than'),
        ('in', 'In List'),
        ('not_in', 'Not In List'),
        ('is_empty', 'Is Empty'),
        ('is_not_empty', 'Is Not Empty'),
    ])
    value = serializers.JSONField()


class BusinessRuleActionSerializer(serializers.Serializer):
    """Serializer for business rule actions"""
    type = serializers.ChoiceField(choices=[
        ('send_notification', 'Send Notification'),
        ('change_status', 'Change Status'),
        ('change_priority', 'Change Priority'),
        ('assign_tag', 'Assign Tag'),
        ('create_task', 'Create Task'),
        ('send_email', 'Send Email'),
        ('webhook', 'Call Webhook'),
        ('escalate', 'Escalate Conversation'),
    ])
    config = serializers.DictField()


class BusinessRuleSerializer(serializers.ModelSerializer):
    """Serializer for business rules"""
    
    created_by_name = serializers.SerializerMethodField()
    success_rate_percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = BusinessRule
        fields = [
            'id', 'workspace', 'name', 'description', 'trigger_type',
            'trigger_conditions', 'actions', 'is_active', 'priority',
            'execution_count', 'last_executed', 'success_rate', 
            'success_rate_percentage', 'created_at', 'updated_at',
            'created_by', 'created_by_name'
        ]
        read_only_fields = [
            'id', 'execution_count', 'last_executed', 'success_rate',
            'created_at', 'updated_at'
        ]
    
    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None
    
    def get_success_rate_percentage(self, obj):
        return round(obj.success_rate * 100, 1)
    
    def validate_trigger_conditions(self, value):
        """Validate trigger conditions"""
        if not value:
            return value
        
        operator = value.get('operator', 'and')
        if operator not in ['and', 'or']:
            raise serializers.ValidationError("Operator must be 'and' or 'or'")
        
        rules = value.get('rules', [])
        if not isinstance(rules, list):
            raise serializers.ValidationError("Rules must be a list")
        
        for rule in rules:
            condition_serializer = BusinessRuleConditionSerializer(data=rule)
            if not condition_serializer.is_valid():
                raise serializers.ValidationError(f"Invalid condition: {condition_serializer.errors}")
        
        return value
    
    def validate_actions(self, value):
        """Validate actions"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Actions must be a list")
        
        if not value:
            raise serializers.ValidationError("At least one action is required")
        
        for action in value:
            action_serializer = BusinessRuleActionSerializer(data=action)
            if not action_serializer.is_valid():
                raise serializers.ValidationError(f"Invalid action: {action_serializer.errors}")
        
        return value


class RuleExecutionSerializer(serializers.ModelSerializer):
    """Serializer for rule executions"""
    
    rule_name = serializers.SerializerMethodField()
    context_title = serializers.SerializerMethodField()
    
    class Meta:
        model = RuleExecution
        fields = [
            'id', 'rule', 'rule_name', 'context', 'context_title',
            'trigger_type', 'trigger_data', 'execution_result',
            'success', 'error_message', 'execution_time', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_rule_name(self, obj):
        return obj.rule.name if obj.rule else None
    
    def get_context_title(self, obj):
        return obj.context.title if obj.context else None


class ContextExtractionRequestSerializer(serializers.Serializer):
    """Serializer for context extraction requests"""
    message_text = serializers.CharField()
    force_extraction = serializers.BooleanField(default=False)
    fields_to_extract = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Specific fields to extract, if not provided, all extractable fields will be processed"
    )


class ContextUpdateSerializer(serializers.Serializer):
    """Serializer for context field updates"""
    field_updates = serializers.DictField(
        help_text="Dictionary of field_id: value pairs to update"
    )
    title = serializers.CharField(required=False, allow_blank=True)
    tags = serializers.ListField(child=serializers.CharField(), required=False)
    metadata = serializers.DictField(required=False)
    
    def validate_field_updates(self, value):
        """Validate that field updates are valid"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Field updates must be a dictionary")
        
        return value


class SchemaTestSerializer(serializers.Serializer):
    """Serializer for testing schema configurations"""
    test_data = serializers.DictField(
        help_text="Test context data to evaluate against schema"
    )
    test_priority_calculation = serializers.BooleanField(default=True)
    test_status_transitions = serializers.BooleanField(default=True)


class RuleTestSerializer(serializers.Serializer):
    """Serializer for testing business rules"""
    test_context_data = serializers.DictField(
        help_text="Test context data to evaluate rule against"
    )
    test_trigger_data = serializers.DictField(
        required=False,
        help_text="Additional trigger data for testing"
    )


class DynamicFieldSuggestionSerializer(serializers.ModelSerializer):
    """Serializer for AI-discovered field suggestions"""
    
    workspace_name = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()
    target_schema_name = serializers.SerializerMethodField()
    
    class Meta:
        model = 'context_tracking.DynamicFieldSuggestion'  # Use string reference to avoid circular imports
        fields = [
            'id', 'workspace', 'workspace_name', 'suggested_field_name', 'field_type',
            'description', 'frequency_detected', 'sample_values', 'confidence_score',
            'business_value_score', 'detection_pattern', 'related_fields', 'context_examples',
            'is_reviewed', 'is_approved', 'reviewed_by', 'reviewed_by_name', 'reviewed_at',
            'review_notes', 'target_schema', 'target_schema_name', 'implemented_at',
            'implementation_notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_workspace_name(self, obj):
        return obj.workspace.name if obj.workspace else None
    
    def get_reviewed_by_name(self, obj):
        return obj.reviewed_by.get_full_name() if obj.reviewed_by else None
    
    def get_target_schema_name(self, obj):
        return obj.target_schema.name if obj.target_schema else None
    
    def validate_field_type(self, value):
        """Validate field type"""
        valid_types = [
            'text', 'textarea', 'number', 'decimal', 'date', 'datetime',
            'boolean', 'choice', 'multi_choice', 'email', 'phone', 'url',
            'tags', 'priority', 'status'
        ]
        if value not in valid_types:
            raise serializers.ValidationError(f"Invalid field type: {value}")
        return value
    
    def validate_confidence_score(self, value):
        """Validate confidence score is between 0 and 1"""
        if not 0 <= value <= 1:
            raise serializers.ValidationError("Confidence score must be between 0 and 1")
        return value
    
    def validate_business_value_score(self, value):
        """Validate business value score is between 0 and 1"""
        if not 0 <= value <= 1:
            raise serializers.ValidationError("Business value score must be between 0 and 1")
        return value
