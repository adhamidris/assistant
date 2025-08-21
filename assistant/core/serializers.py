from rest_framework import serializers
from .models import Workspace, Contact, Session, Conversation
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

