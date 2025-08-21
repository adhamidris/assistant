from rest_framework import serializers
from django.core.files.uploadedfile import UploadedFile
from .models import Message, AudioTranscription, MessageDraft
from core.models import Conversation


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model"""
    sender_display = serializers.CharField(source='get_sender_display', read_only=True)
    type_display = serializers.CharField(source='get_message_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    # Include transcription if available
    transcription = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'sender_display', 
            'message_type', 'type_display', 'status', 'status_display',
            'text', 'media_url', 'media_filename', 'media_size',
            'intent_classification', 'confidence_score', 'transcription',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'sender_display', 
            'type_display', 'status_display', 'transcription'
        ]
    
    def get_transcription(self, obj):
        """Include transcription text if available"""
        if hasattr(obj, 'transcription'):
            return {
                'text': obj.transcription.transcribed_text,
                'language': obj.transcription.language,
                'confidence': obj.transcription.confidence,
                'duration': obj.transcription.duration
            }
        return None


class CreateTextMessageSerializer(serializers.Serializer):
    """Serializer for creating text messages"""
    text = serializers.CharField(max_length=5000)
    sender = serializers.ChoiceField(choices=['client', 'owner'], default='client')
    
    def validate_text(self, value):
        """Validate message text"""
        if not value or not value.strip():
            raise serializers.ValidationError("Message text cannot be empty")
        
        # Basic content filtering
        if len(value) > 5000:
            raise serializers.ValidationError("Message too long (max 5000 characters)")
        
        return value.strip()


class FileUploadSerializer(serializers.Serializer):
    """Serializer for file uploads"""
    file = serializers.FileField()
    sender = serializers.ChoiceField(choices=['client', 'owner'], default='client')
    
    def validate_file(self, value):
        """Validate uploaded file"""
        if not value:
            raise serializers.ValidationError("No file provided")
        
        # Check file size (10MB limit)
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError("File too large (max 10MB)")
        
        # Check file type
        allowed_types = [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'application/pdf', 'text/plain', 'text/csv',
            'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ]
        
        if hasattr(value, 'content_type') and value.content_type not in allowed_types:
            raise serializers.ValidationError(f"File type not allowed: {value.content_type}")
        
        return value


class AudioUploadSerializer(serializers.Serializer):
    """Serializer for audio uploads"""
    audio_file = serializers.FileField()
    sender = serializers.ChoiceField(choices=['client', 'owner'], default='client')
    
    def validate_audio_file(self, value):
        """Validate uploaded audio file"""
        if not value:
            raise serializers.ValidationError("No audio file provided")
        
        # Check file size (50MB limit for audio)
        max_size = 50 * 1024 * 1024  # 50MB
        if value.size > max_size:
            raise serializers.ValidationError("Audio file too large (max 50MB)")
        
        # Check audio file type
        allowed_audio_types = [
            'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/ogg', 
            'audio/m4a', 'audio/webm', 'audio/flac'
        ]
        
        if hasattr(value, 'content_type') and value.content_type not in allowed_audio_types:
            raise serializers.ValidationError(f"Audio file type not allowed: {value.content_type}")
        
        return value


class AudioTranscriptionSerializer(serializers.ModelSerializer):
    """Serializer for AudioTranscription model"""
    message_id = serializers.UUIDField(source='message.id', read_only=True)
    
    class Meta:
        model = AudioTranscription
        fields = [
            'id', 'message_id', 'transcribed_text', 'language', 
            'confidence', 'duration', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'message_id']


class MessageDraftSerializer(serializers.ModelSerializer):
    """Serializer for MessageDraft model"""
    conversation_id = serializers.UUIDField(source='conversation.id', read_only=True)
    
    class Meta:
        model = MessageDraft
        fields = [
            'id', 'conversation_id', 'suggested_text', 'confidence_score',
            'context_sources', 'is_approved', 'is_rejected', 
            'approved_at', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'conversation_id']


class ApproveDraftSerializer(serializers.Serializer):
    """Serializer for approving/rejecting draft messages"""
    draft_id = serializers.UUIDField()
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    modified_text = serializers.CharField(max_length=5000, required=False, allow_blank=True)
    
    def validate_draft_id(self, value):
        """Validate draft exists"""
        try:
            draft = MessageDraft.objects.get(id=value)
            if draft.is_approved or draft.is_rejected:
                raise serializers.ValidationError("Draft has already been processed")
            return value
        except MessageDraft.DoesNotExist:
            raise serializers.ValidationError("Draft not found")


class GenerateResponseSerializer(serializers.Serializer):
    """Serializer for generating AI responses"""
    message_text = serializers.CharField(max_length=5000)
    conversation_id = serializers.UUIDField(required=False)
    force_generation = serializers.BooleanField(default=False)
    
    def validate_message_text(self, value):
        """Validate message text for response generation"""
        if not value or not value.strip():
            raise serializers.ValidationError("Message text cannot be empty")
        return value.strip()


class MessageStatusSerializer(serializers.Serializer):
    """Serializer for updating message status"""
    status = serializers.ChoiceField(choices=Message.STATUS_CHOICES)
    error_message = serializers.CharField(max_length=500, required=False, allow_blank=True)


class ConversationMessagesSerializer(serializers.Serializer):
    """Serializer for retrieving conversation messages"""
    conversation_id = serializers.UUIDField()
    limit = serializers.IntegerField(default=50, min_value=1, max_value=200)
    offset = serializers.IntegerField(default=0, min_value=0)
    message_type = serializers.ChoiceField(
        choices=[('all', 'All')] + Message.TYPE_CHOICES, 
        default='all',
        required=False
    )
    
    def validate_conversation_id(self, value):
        """Validate conversation exists and user has access"""
        try:
            conversation = Conversation.objects.get(id=value)
            return value
        except Conversation.DoesNotExist:
            raise serializers.ValidationError("Conversation not found")


class MessageSearchSerializer(serializers.Serializer):
    """Serializer for searching messages"""
    query = serializers.CharField(max_length=200)
    conversation_id = serializers.UUIDField(required=False)
    sender = serializers.ChoiceField(
        choices=[('all', 'All')] + Message.SENDER_CHOICES,
        default='all',
        required=False
    )
    message_type = serializers.ChoiceField(
        choices=[('all', 'All')] + Message.TYPE_CHOICES,
        default='all',
        required=False
    )
    date_from = serializers.DateTimeField(required=False)
    date_to = serializers.DateTimeField(required=False)
    
    def validate(self, attrs):
        """Validate date range"""
        date_from = attrs.get('date_from')
        date_to = attrs.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise serializers.ValidationError("date_from must be before date_to")
        
        return attrs

