from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
import json

from .models import (
    WorkspaceContextSchema, ConversationContext, 
    ContextHistory, BusinessRule, RuleExecution, DynamicFieldSuggestion
)


@admin.register(WorkspaceContextSchema)
class WorkspaceContextSchemaAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'workspace', 'field_count', 'is_active', 
        'is_default', 'created_at', 'created_by'
    ]
    list_filter = ['is_active', 'is_default', 'created_at', 'workspace']
    search_fields = ['name', 'description', 'workspace__name']
    readonly_fields = ['field_count', 'required_field_count', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('workspace', 'name', 'description', 'is_active', 'is_default')
        }),
        ('Schema Configuration', {
            'fields': ('fields_display', 'status_workflow_display', 'priority_config_display'),
            'classes': ('wide',)
        }),
        ('Metadata', {
            'fields': ('field_count', 'required_field_count', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def field_count(self, obj):
        return obj.field_count
    field_count.short_description = 'Fields'
    
    def fields_display(self, obj):
        if not obj.fields:
            return "No fields defined"
        
        html = "<table style='width:100%'>"
        html += "<tr><th>ID</th><th>Label</th><th>Type</th><th>Required</th><th>AI Extractable</th></tr>"
        
        for field in obj.fields:
            html += f"""
            <tr>
                <td>{field.get('id', '')}</td>
                <td>{field.get('label', '')}</td>
                <td>{field.get('type', '')}</td>
                <td>{'Yes' if field.get('required', False) else 'No'}</td>
                <td>{'Yes' if field.get('ai_extractable', True) else 'No'}</td>
            </tr>
            """
        
        html += "</table>"
        return mark_safe(html)
    fields_display.short_description = 'Field Definitions'
    
    def status_workflow_display(self, obj):
        if not obj.status_workflow:
            return "No workflow defined"
        
        workflow = obj.status_workflow
        statuses = workflow.get('statuses', [])
        transitions = workflow.get('transitions', {})
        
        html = "<div style='margin-bottom: 10px;'><strong>Statuses:</strong><br>"
        for status in statuses:
            html += f"• {status.get('label', '')} ({status.get('id', '')})<br>"
        html += "</div>"
        
        if transitions:
            html += "<div><strong>Transitions:</strong><br>"
            for from_status, to_statuses in transitions.items():
                html += f"• {from_status} → {', '.join(to_statuses)}<br>"
            html += "</div>"
        
        return mark_safe(html)
    status_workflow_display.short_description = 'Status Workflow'
    
    def priority_config_display(self, obj):
        if not obj.priority_config:
            return "No priority configuration"
        
        config = obj.priority_config
        html = f"<div><strong>Default Priority:</strong> {config.get('default_priority', 'medium')}</div>"
        
        rules = config.get('rules', [])
        if rules:
            html += "<div style='margin-top: 10px;'><strong>Priority Rules:</strong><br>"
            for i, rule in enumerate(rules):
                html += f"Rule {i+1}: Priority {rule.get('priority', '')} if conditions met<br>"
            html += "</div>"
        
        return mark_safe(html)
    priority_config_display.short_description = 'Priority Configuration'


@admin.register(ConversationContext)
class ConversationContextAdmin(admin.ModelAdmin):
    list_display = [
        'title_display', 'conversation', 'schema', 'status', 
        'priority', 'completion_percentage', 'updated_at'
    ]
    list_filter = ['status', 'priority', 'schema', 'created_at', 'updated_at']
    search_fields = ['title', 'conversation__id', 'tags']
    readonly_fields = [
        'completion_percentage', 'field_count', 'high_confidence_fields',
        'created_at', 'updated_at', 'last_ai_update', 'last_human_update'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('conversation', 'schema', 'title', 'status', 'priority')
        }),
        ('Context Data', {
            'fields': ('context_data_display', 'ai_confidence_display', 'tags'),
            'classes': ('wide',)
        }),
        ('Statistics', {
            'fields': ('completion_percentage', 'field_count', 'high_confidence_fields'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata_display', 'created_at', 'updated_at', 'last_ai_update', 'last_human_update'),
            'classes': ('collapse',)
        }),
    )
    
    def title_display(self, obj):
        return obj.title or f"Context for {obj.conversation}"
    title_display.short_description = 'Title'
    
    def context_data_display(self, obj):
        if not obj.context_data:
            return "No data"
        
        html = "<table style='width:100%'>"
        html += "<tr><th>Field</th><th>Value</th></tr>"
        
        for field_id, value in obj.context_data.items():
            # Try to get field label from schema
            field_label = field_id
            if obj.schema:
                field_def = obj.schema.get_field_by_id(field_id)
                if field_def:
                    field_label = field_def.get('label', field_id)
            
            # Format value
            if isinstance(value, (list, dict)):
                display_value = json.dumps(value)
            else:
                display_value = str(value)
            
            # Truncate long values
            if len(display_value) > 100:
                display_value = display_value[:97] + "..."
            
            html += f"<tr><td><strong>{field_label}</strong></td><td>{display_value}</td></tr>"
        
        html += "</table>"
        return mark_safe(html)
    context_data_display.short_description = 'Context Data'
    
    def ai_confidence_display(self, obj):
        if not obj.ai_confidence_scores:
            return "No confidence data"
        
        html = "<table style='width:100%'>"
        html += "<tr><th>Field</th><th>Confidence</th></tr>"
        
        for field_id, confidence in obj.ai_confidence_scores.items():
            # Color code confidence
            if confidence >= 0.8:
                color = "green"
            elif confidence >= 0.6:
                color = "orange"
            else:
                color = "red"
            
            field_label = field_id
            if obj.schema:
                field_def = obj.schema.get_field_by_id(field_id)
                if field_def:
                    field_label = field_def.get('label', field_id)
            
            html += f"""
            <tr>
                <td>{field_label}</td>
                <td style='color: {color}; font-weight: bold;'>{confidence:.2f}</td>
            </tr>
            """
        
        html += "</table>"
        return mark_safe(html)
    ai_confidence_display.short_description = 'AI Confidence Scores'
    
    def metadata_display(self, obj):
        if not obj.metadata:
            return "No metadata"
        
        return format_html("<pre>{}</pre>", json.dumps(obj.metadata, indent=2))
    metadata_display.short_description = 'Metadata'


@admin.register(ContextHistory)
class ContextHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'context', 'action_type', 'field_name', 'changed_by_display', 
        'confidence_score', 'created_at'
    ]
    list_filter = ['action_type', 'changed_by_ai', 'created_at']
    search_fields = ['context__title', 'field_name', 'changed_by_user__username']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Change Information', {
            'fields': ('context', 'action_type', 'field_name')
        }),
        ('Values', {
            'fields': ('old_value_display', 'new_value_display')
        }),
        ('Source', {
            'fields': ('changed_by_ai', 'changed_by_user', 'confidence_score')
        }),
        ('Metadata', {
            'fields': ('metadata_display', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def changed_by_display(self, obj):
        if obj.changed_by_ai:
            return format_html('<span style="color: blue;">🤖 AI</span>')
        elif obj.changed_by_user:
            return format_html('<span style="color: green;">👤 {}</span>', obj.changed_by_user.username)
        else:
            return format_html('<span style="color: gray;">⚙️ System</span>')
    changed_by_display.short_description = 'Changed By'
    
    def old_value_display(self, obj):
        if obj.old_value is None:
            return "None"
        return format_html("<pre>{}</pre>", json.dumps(obj.old_value, indent=2))
    old_value_display.short_description = 'Old Value'
    
    def new_value_display(self, obj):
        if obj.new_value is None:
            return "None"
        return format_html("<pre>{}</pre>", json.dumps(obj.new_value, indent=2))
    new_value_display.short_description = 'New Value'
    
    def metadata_display(self, obj):
        if not obj.metadata:
            return "No metadata"
        return format_html("<pre>{}</pre>", json.dumps(obj.metadata, indent=2))
    metadata_display.short_description = 'Metadata'


@admin.register(BusinessRule)
class BusinessRuleAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'workspace', 'trigger_type', 'is_active', 
        'execution_count', 'success_rate_display', 'last_executed'
    ]
    list_filter = ['trigger_type', 'is_active', 'created_at', 'workspace']
    search_fields = ['name', 'description', 'workspace__name']
    readonly_fields = [
        'execution_count', 'last_executed', 'success_rate', 
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('workspace', 'name', 'description', 'is_active', 'priority')
        }),
        ('Trigger Configuration', {
            'fields': ('trigger_type', 'trigger_conditions_display'),
            'classes': ('wide',)
        }),
        ('Actions', {
            'fields': ('actions_display',),
            'classes': ('wide',)
        }),
        ('Execution Statistics', {
            'fields': ('execution_count', 'last_executed', 'success_rate'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def success_rate_display(self, obj):
        rate = obj.success_rate * 100
        if rate >= 90:
            color = "green"
        elif rate >= 70:
            color = "orange"
        else:
            color = "red"
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color, rate
        )
    success_rate_display.short_description = 'Success Rate'
    
    def trigger_conditions_display(self, obj):
        if not obj.trigger_conditions:
            return "No conditions"
        
        conditions = obj.trigger_conditions
        operator = conditions.get('operator', 'and')
        rules = conditions.get('rules', [])
        
        html = f"<div><strong>Operator:</strong> {operator.upper()}</div>"
        html += "<div style='margin-top: 10px;'><strong>Conditions:</strong><br>"
        
        for i, rule in enumerate(rules):
            field = rule.get('field', '')
            op = rule.get('operator', '')
            value = rule.get('value', '')
            html += f"{i+1}. {field} {op} {value}<br>"
        
        html += "</div>"
        return mark_safe(html)
    trigger_conditions_display.short_description = 'Trigger Conditions'
    
    def actions_display(self, obj):
        if not obj.actions:
            return "No actions"
        
        html = "<ol>"
        for action in obj.actions:
            action_type = action.get('type', '')
            config = action.get('config', {})
            html += f"<li><strong>{action_type}</strong><br>"
            
            if config:
                for key, value in config.items():
                    html += f"&nbsp;&nbsp;{key}: {value}<br>"
            
            html += "</li>"
        
        html += "</ol>"
        return mark_safe(html)
    actions_display.short_description = 'Actions'


@admin.register(RuleExecution)
class RuleExecutionAdmin(admin.ModelAdmin):
    list_display = [
        'rule', 'context', 'trigger_type', 'success', 
        'execution_time_display', 'created_at'
    ]
    list_filter = ['trigger_type', 'success', 'created_at']
    search_fields = ['rule__name', 'context__title']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Execution Information', {
            'fields': ('rule', 'context', 'trigger_type', 'success', 'execution_time')
        }),
        ('Data', {
            'fields': ('trigger_data_display', 'execution_result_display'),
            'classes': ('wide',)
        }),
        ('Error Information', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def execution_time_display(self, obj):
        if obj.execution_time < 1:
            return f"{obj.execution_time * 1000:.0f}ms"
        else:
            return f"{obj.execution_time:.2f}s"
    execution_time_display.short_description = 'Execution Time'
    
    def trigger_data_display(self, obj):
        if not obj.trigger_data:
            return "No trigger data"
        return format_html("<pre>{}</pre>", json.dumps(obj.trigger_data, indent=2))
    trigger_data_display.short_description = 'Trigger Data'
    
    def execution_result_display(self, obj):
        if not obj.execution_result:
            return "No execution result"
        return format_html("<pre>{}</pre>", json.dumps(obj.execution_result, indent=2))
    execution_result_display.short_description = 'Execution Result'


@admin.register(DynamicFieldSuggestion)
class DynamicFieldSuggestionAdmin(admin.ModelAdmin):
    list_display = [
        'suggested_field_name', 'workspace', 'field_type', 'confidence_score', 
        'business_value_score', 'is_reviewed', 'is_approved', 'created_at'
    ]
    list_filter = [
        'field_type', 'is_reviewed', 'is_approved', 'workspace', 'created_at'
    ]
    search_fields = [
        'suggested_field_name', 'description', 'workspace__name'
    ]
    readonly_fields = [
        'id', 'frequency_detected', 'sample_values', 'confidence_score', 
        'business_value_score', 'detection_pattern', 'related_fields', 
        'context_examples', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Field Suggestion', {
            'fields': ('workspace', 'suggested_field_name', 'field_type', 'description')
        }),
        ('AI Analysis', {
            'fields': ('frequency_detected', 'sample_values', 'confidence_score', 'business_value_score'),
            'classes': ('collapse',)
        }),
        ('Pattern Analysis', {
            'fields': ('detection_pattern', 'related_fields', 'context_examples'),
            'classes': ('collapse',)
        }),
        ('Review Workflow', {
            'fields': ('is_reviewed', 'is_approved', 'reviewed_by', 'reviewed_at', 'review_notes')
        }),
        ('Implementation', {
            'fields': ('target_schema', 'implemented_at', 'implementation_notes'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = ['approve_suggestions', 'reject_suggestions']
    
    def approve_suggestions(self, request, queryset):
        """Approve selected field suggestions"""
        approved_count = 0
        for suggestion in queryset.filter(is_reviewed=False):
            suggestion.approve(request.user)
            approved_count += 1
        
        self.message_user(
            request, 
            f'Successfully approved {approved_count} field suggestions.'
        )
    approve_suggestions.short_description = 'Approve selected suggestions'
    
    def reject_suggestions(self, request, queryset):
        """Reject selected field suggestions"""
        rejected_count = 0
        for suggestion in queryset.filter(is_reviewed=False):
            suggestion.reject(request.user, 'Bulk rejected via admin')
            rejected_count += 1
        
        self.message_user(
            request, 
            f'Successfully rejected {rejected_count} field suggestions.'
        )
    reject_suggestions.short_description = 'Reject selected suggestions'
