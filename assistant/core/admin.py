from django.contrib import admin
from .models import Workspace, Contact, Session, Conversation, AIAgent, AgentSchemaAssignment, BusinessTypeTemplate


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


@admin.register(AIAgent)
class AIAgentAdmin(admin.ModelAdmin):
    list_display = ['name', 'workspace', 'channel_type', 'is_active', 'is_default', 'conversation_count', 'created_at']
    list_filter = ['is_active', 'is_default', 'channel_type', 'workspace', 'created_at']
    search_fields = ['name', 'description', 'workspace__name']
    readonly_fields = ['id', 'conversation_count', 'average_response_time', 'customer_satisfaction_score', 'created_at', 'updated_at']
    filter_horizontal = []
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('workspace', 'name', 'slug', 'description')
        }),
        ('Channel Configuration', {
            'fields': ('channel_type', 'channel_specific_config')
        }),
        ('Business Customization', {
            'fields': ('business_context', 'personality_config')
        }),
        ('AI Configuration', {
            'fields': ('generated_prompt', 'custom_instructions', 'prompt_version')
        }),
        ('Deployment', {
            'fields': ('is_active', 'is_default', 'deployment_url')
        }),
        ('Performance Metrics', {
            'fields': ('performance_metrics', 'conversation_count', 'average_response_time', 'customer_satisfaction_score'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(AgentSchemaAssignment)
class AgentSchemaAssignmentAdmin(admin.ModelAdmin):
    list_display = ['agent', 'schema', 'priority', 'is_primary', 'is_required', 'usage_count', 'last_used']
    list_filter = ['is_primary', 'is_required', 'priority', 'agent__workspace', 'created_at']
    search_fields = ['agent__name', 'schema__name', 'agent__workspace__name']
    readonly_fields = ['id', 'usage_count', 'last_used', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Assignment', {
            'fields': ('agent', 'schema', 'priority', 'is_primary', 'is_required')
        }),
        ('Customization', {
            'fields': ('custom_config', 'field_mapping')
        }),
        ('Usage Tracking', {
            'fields': ('usage_count', 'last_used'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(BusinessTypeTemplate)
class BusinessTypeTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'industry', 'is_active', 'is_featured', 'version', 'created_at']
    list_filter = ['industry', 'is_active', 'is_featured', 'created_at']
    search_fields = ['name', 'description', 'industry']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'industry', 'description', 'version')
        }),
        ('Template Content', {
            'fields': ('default_schema_templates', 'default_rule_templates')
        }),
        ('AI Configuration', {
            'fields': ('base_prompt_template', 'personality_defaults', 'conversation_flow')
        }),
        ('Integration & Compliance', {
            'fields': ('recommended_integrations', 'compliance_requirements', 'best_practices'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active', 'is_featured', 'created_by')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
