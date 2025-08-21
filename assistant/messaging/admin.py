from django.contrib import admin
from .models import Message, AudioTranscription, MessageDraft


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id_short', 'conversation', 'sender', 'message_type', 'status', 'text_preview', 'created_at']
    list_filter = ['sender', 'message_type', 'status', 'created_at', 'conversation__workspace']
    search_fields = ['text', 'conversation__contact__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    def id_short(self, obj):
        return str(obj.id)[:8]
    id_short.short_description = 'ID'
    
    def text_preview(self, obj):
        if obj.text:
            return (obj.text[:50] + '...') if len(obj.text) > 50 else obj.text
        return f'[{obj.message_type}]'
    text_preview.short_description = 'Content'


@admin.register(AudioTranscription)
class AudioTranscriptionAdmin(admin.ModelAdmin):
    list_display = ['id_short', 'message', 'language', 'confidence', 'duration', 'text_preview', 'created_at']
    list_filter = ['language', 'created_at']
    search_fields = ['transcribed_text', 'message__conversation__contact__name']
    readonly_fields = ['id', 'created_at']
    
    def id_short(self, obj):
        return str(obj.id)[:8]
    id_short.short_description = 'ID'
    
    def text_preview(self, obj):
        return (obj.transcribed_text[:50] + '...') if len(obj.transcribed_text) > 50 else obj.transcribed_text
    text_preview.short_description = 'Transcription'


@admin.register(MessageDraft)
class MessageDraftAdmin(admin.ModelAdmin):
    list_display = ['id_short', 'conversation', 'is_approved', 'is_rejected', 'confidence_score', 'text_preview', 'created_at']
    list_filter = ['is_approved', 'is_rejected', 'created_at', 'conversation__workspace']
    search_fields = ['suggested_text', 'conversation__contact__name']
    readonly_fields = ['id', 'created_at']
    
    def id_short(self, obj):
        return str(obj.id)[:8]
    id_short.short_description = 'ID'
    
    def text_preview(self, obj):
        return (obj.suggested_text[:50] + '...') if len(obj.suggested_text) > 50 else obj.suggested_text
    text_preview.short_description = 'Suggested Text'
