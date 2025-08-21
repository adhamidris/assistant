from django.db import models
from core.models import Conversation
import uuid


class Message(models.Model):
    """Individual message model"""
    SENDER_CHOICES = [
        ('client', 'Client'),
        ('assistant', 'AI Assistant'),
        ('owner', 'Business Owner'),
    ]
    
    TYPE_CHOICES = [
        ('text', 'Text Message'),
        ('audio', 'Audio Message'),
        ('file', 'File Attachment'),
        ('system', 'System Message'),
    ]
    
    STATUS_CHOICES = [
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('processing', 'Processing'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    
    sender = models.CharField(max_length=20, choices=SENDER_CHOICES)
    message_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='text')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
    
    # Message content
    text = models.TextField(blank=True, null=True)
    media_url = models.URLField(blank=True, null=True)
    media_filename = models.CharField(max_length=255, blank=True, null=True)
    media_size = models.PositiveIntegerField(blank=True, null=True)  # Size in bytes
    
    # AI analysis
    intent_classification = models.CharField(max_length=50, blank=True, null=True)
    confidence_score = models.FloatField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'messages'
        ordering = ['created_at']
        
    def __str__(self):
        content_preview = (self.text[:50] + '...') if self.text and len(self.text) > 50 else self.text or f'[{self.message_type}]'
        return f"{self.sender}: {content_preview}"


class AudioTranscription(models.Model):
    """Audio transcription results"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.OneToOneField(Message, on_delete=models.CASCADE, related_name='transcription')
    
    transcribed_text = models.TextField()
    language = models.CharField(max_length=10, blank=True, null=True)
    confidence = models.FloatField(blank=True, null=True)
    
    # OpenAI Whisper specific fields
    duration = models.FloatField(blank=True, null=True)  # Duration in seconds
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'audio_transcriptions'
        
    def __str__(self):
        return f"Transcription for {self.message.id}"


class MessageDraft(models.Model):
    """Draft responses for manual approval mode"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='draft_messages')
    
    # Draft content
    suggested_text = models.TextField()
    confidence_score = models.FloatField(blank=True, null=True)
    
    # Context used for generation
    context_sources = models.JSONField(default=list, blank=True)  # List of KB chunk IDs used
    
    # Approval status
    is_approved = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    approved_at = models.DateTimeField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'message_drafts'
        ordering = ['-created_at']
        
    def __str__(self):
        preview = (self.suggested_text[:50] + '...') if len(self.suggested_text) > 50 else self.suggested_text
        return f"Draft: {preview}"
