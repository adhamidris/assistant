from django.contrib import admin
from .models import Workspace, Contact, Session, Conversation


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ['name', 'timezone', 'auto_reply_mode', 'assistant_name', 'google_calendar_connected', 'created_at']
    list_filter = ['auto_reply_mode', 'google_calendar_connected', 'created_at']
    search_fields = ['name', 'assistant_name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'masked_phone', 'workspace', 'email', 'created_at']
    list_filter = ['workspace', 'created_at']
    search_fields = ['name', 'email']
    readonly_fields = ['id', 'masked_phone', 'created_at', 'updated_at']
    
    def masked_phone(self, obj):
        return obj.masked_phone
    masked_phone.short_description = 'Phone'


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['session_token_short', 'contact', 'is_active', 'last_seen_at', 'created_at']
    list_filter = ['is_active', 'created_at', 'last_seen_at']
    search_fields = ['session_token', 'contact__name']
    readonly_fields = ['id', 'created_at', 'last_seen_at']
    
    def session_token_short(self, obj):
        return f"{obj.session_token[:8]}..."
    session_token_short.short_description = 'Session Token'


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id_short', 'contact', 'status', 'last_intent', 'updated_at']
    list_filter = ['status', 'last_intent', 'workspace', 'created_at']
    search_fields = ['contact__name', 'contact__phone_e164']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    def id_short(self, obj):
        return str(obj.id)[:8]
    id_short.short_description = 'ID'
