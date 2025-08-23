from rest_framework import serializers
from .models import Workspace, Contact, Session, Conversation, AIAgent, AgentSchemaAssignment, BusinessTypeTemplate
import phonenumbers
from phonenumbers import NumberParseException


class WorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        fields = [
            'id', 'name', 'timezone', 'auto_reply_mode', 'assistant_name',
            'google_calendar_connected', 'business_hours', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'google_calendar_connected']


class ContactSerializer(serializers.ModelSerializer):
    masked_phone = serializers.ReadOnlyField()
    
    class Meta:
        model = Contact
        fields = [
            'id', 'workspace', 'phone_e164', 'masked_phone', 'name', 'email', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'masked_phone']
    
    def validate_phone_e164(self, value):
        """Validate and format phone number to E.164 format"""
        try:
            # Parse the phone number
            parsed_number = phonenumbers.parse(value, None)
            
            # Check if it's valid
            if not phonenumbers.is_valid_number(parsed_number):
                raise serializers.ValidationError("Invalid phone number")
            
            # Format to E.164
            formatted_number = phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
            return formatted_number
            
        except NumberParseException as e:
            raise serializers.ValidationError(f"Invalid phone number format: {e}")


class SessionSerializer(serializers.ModelSerializer):
    contact = ContactSerializer(read_only=True)
    
    class Meta:
        model = Session
        fields = [
            'id', 'contact', 'session_token', 'last_seen_at', 
            'created_at', 'is_active'
        ]
        read_only_fields = ['id', 'created_at', 'last_seen_at']


class ConversationSerializer(serializers.ModelSerializer):
    contact = ContactSerializer(read_only=True)
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'workspace', 'session', 'contact', 'status', 'last_intent',
            'message_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'message_count']
    
    def get_message_count(self, obj):
        return obj.messages.count()


class CreateSessionSerializer(serializers.Serializer):
    """Serializer for creating a new session"""
    phone_number = serializers.CharField(max_length=16)
    workspace_id = serializers.UUIDField()
    
    def validate_phone_number(self, value):
        """Validate and format phone number"""
        try:
            parsed_number = phonenumbers.parse(value, None)
            if not phonenumbers.is_valid_number(parsed_number):
                raise serializers.ValidationError("Invalid phone number")
            return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
        except NumberParseException as e:
            raise serializers.ValidationError(f"Invalid phone number format: {e}")
    
    def validate_workspace_id(self, value):
        """Validate workspace exists"""
        try:
            Workspace.objects.get(id=value)
            return value
        except Workspace.DoesNotExist:
            raise serializers.ValidationError("Workspace not found")


class ValidateSessionSerializer(serializers.Serializer):
    """Serializer for validating an existing session"""
    session_token = serializers.CharField(max_length=255)


class AIAgentSerializer(serializers.ModelSerializer):
    """Serializer for AI Agent model"""
    workspace_name = serializers.ReadOnlyField(source='workspace.name')
    channel_type_display = serializers.ReadOnlyField(source='get_channel_type_display')
    portal_url = serializers.ReadOnlyField(source='get_portal_url')
    deployment_url = serializers.ReadOnlyField(source='get_deployment_url')
    
    class Meta:
        model = AIAgent
        fields = [
            'id', 'workspace', 'workspace_name', 'name', 'slug', 'description',
            'channel_type', 'channel_type_display', 'channel_specific_config',
            'business_context', 'personality_config', 'generated_prompt',
            'custom_instructions', 'prompt_version', 'is_active', 'is_default',
            'deployment_url', 'performance_metrics', 'conversation_count',
            'average_response_time', 'customer_satisfaction_score',
            'portal_url', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'workspace_name', 'generated_prompt', 'performance_metrics',
            'conversation_count', 'average_response_time', 'customer_satisfaction_score',
            'portal_url', 'deployment_url', 'created_at', 'updated_at'
        ]
    
    def validate_slug(self, value):
        """Validate slug format and uniqueness within workspace"""
        if not value:
            raise serializers.ValidationError("Slug is required")
        
        # Check if slug contains only valid characters
        import re
        if not re.match(r'^[a-z0-9-]+$', value):
            raise serializers.ValidationError("Slug can only contain lowercase letters, numbers, and hyphens")
        
        return value
    
    def validate(self, data):
        """Validate agent configuration"""
        # Ensure only one default agent per workspace
        if data.get('is_default', False):
            workspace = data.get('workspace') or self.instance.workspace if self.instance else None
            if workspace:
                existing_default = AIAgent.objects.filter(workspace=workspace, is_default=True)
                if self.instance:
                    existing_default = existing_default.exclude(id=self.instance.id)
                
                if existing_default.exists():
                    raise serializers.ValidationError("Only one agent can be the default per workspace")
        
        return data


class AgentSchemaAssignmentSerializer(serializers.ModelSerializer):
    """Serializer for Agent Schema Assignment model"""
    agent_name = serializers.ReadOnlyField(source='agent.name')
    schema_name = serializers.ReadOnlyField(source='schema.name')
    
    class Meta:
        model = AgentSchemaAssignment
        fields = [
            'id', 'agent', 'agent_name', 'schema', 'schema_name', 'priority',
            'is_primary', 'is_required', 'custom_config', 'field_mapping',
            'usage_count', 'last_used', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'agent_name', 'schema_name', 'usage_count', 'last_used',
            'created_at', 'updated_at'
        ]


class BusinessTypeTemplateSerializer(serializers.ModelSerializer):
    """Serializer for Business Type Template model"""
    industry_display = serializers.ReadOnlyField(source='get_industry_display')
    
    class Meta:
        model = BusinessTypeTemplate
        fields = [
            'id', 'name', 'industry', 'industry_display', 'description',
            'default_schema_templates', 'default_rule_templates',
            'base_prompt_template', 'personality_defaults', 'conversation_flow',
            'recommended_integrations', 'compliance_requirements', 'best_practices',
            'is_active', 'is_featured', 'version', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at'
        ]

