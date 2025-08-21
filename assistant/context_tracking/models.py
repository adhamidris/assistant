from django.db import models
from django.contrib.auth.models import User
from core.models import Workspace, Conversation, Contact
import uuid
import json


class WorkspaceContextSchema(models.Model):
    """Defines the context structure for a workspace"""
    
    FIELD_TYPES = [
        ('text', 'Text Field'),
        ('textarea', 'Text Area'),
        ('choice', 'Choice Dropdown'),
        ('multi_choice', 'Multi-Select'),
        ('date', 'Date'),
        ('datetime', 'Date & Time'),
        ('number', 'Number'),
        ('decimal', 'Decimal'),
        ('boolean', 'Yes/No'),
        ('tags', 'Tags'),
        ('email', 'Email'),
        ('phone', 'Phone Number'),
        ('url', 'URL'),
        ('priority', 'Priority Level'),
        ('status', 'Status'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='context_schemas')
    
    name = models.CharField(max_length=255, help_text="Schema name (e.g., 'Real Estate Inquiries')")
    description = models.TextField(blank=True, help_text="What this schema tracks")
    
    # Schema definition stored as JSON
    fields = models.JSONField(default=list, help_text="Array of field definitions")
    status_workflow = models.JSONField(default=dict, help_text="Custom status definitions and transitions")
    priority_config = models.JSONField(default=dict, help_text="Priority calculation configuration")
    
    # Schema state
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False, help_text="Default schema for new conversations")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_schemas')
    
    class Meta:
        db_table = 'workspace_context_schemas'
        unique_together = ['workspace', 'name']
        ordering = ['-is_default', 'name']
        indexes = [
            models.Index(fields=['workspace', 'is_active']),
            models.Index(fields=['workspace', 'is_default']),
        ]
    
    def __str__(self):
        return f"{self.workspace.name} - {self.name}"
    
    @property
    def field_count(self):
        """Get number of fields in this schema"""
        return len(self.fields)
    
    @property
    def required_field_count(self):
        """Get number of required fields"""
        return len([f for f in self.fields if f.get('required', False)])
    
    def get_field_by_id(self, field_id):
        """Get field definition by ID"""
        for field in self.fields:
            if field.get('id') == field_id:
                return field
        return None
    
    def get_status_choices(self):
        """Get available status choices from workflow"""
        workflow = self.status_workflow or {}
        return workflow.get('statuses', [
            {'id': 'new', 'label': 'New', 'color': 'blue'},
            {'id': 'in_progress', 'label': 'In Progress', 'color': 'yellow'},
            {'id': 'resolved', 'label': 'Resolved', 'color': 'green'},
        ])
    
    def can_transition_status(self, from_status, to_status):
        """Check if status transition is allowed"""
        workflow = self.status_workflow or {}
        transitions = workflow.get('transitions', {})
        allowed_transitions = transitions.get(from_status, [])
        return to_status in allowed_transitions or from_status == to_status
    
    def calculate_priority(self, context_data):
        """Calculate priority based on context data and configuration"""
        priority_config = self.priority_config or {}
        rules = priority_config.get('rules', [])
        
        # Default priority
        priority = priority_config.get('default_priority', 'medium')
        
        for rule in rules:
            if self._evaluate_priority_rule(rule, context_data):
                priority = rule.get('priority', priority)
                break  # Use first matching rule
        
        return priority
    
    def _evaluate_priority_rule(self, rule, context_data):
        """Evaluate a single priority rule against context data"""
        conditions = rule.get('conditions', [])
        operator = rule.get('operator', 'and')  # 'and' or 'or'
        
        if operator == 'and':
            return all(self._evaluate_condition(cond, context_data) for cond in conditions)
        else:
            return any(self._evaluate_condition(cond, context_data) for cond in conditions)
    
    def _evaluate_condition(self, condition, context_data):
        """Evaluate a single condition"""
        field_id = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value')
        
        field_value = context_data.get(field_id)
        
        if operator == 'equals':
            return field_value == value
        elif operator == 'not_equals':
            return field_value != value
        elif operator == 'contains':
            return value in str(field_value or '')
        elif operator == 'greater_than':
            return (field_value or 0) > value
        elif operator == 'less_than':
            return (field_value or 0) < value
        elif operator == 'is_empty':
            return not field_value
        elif operator == 'is_not_empty':
            return bool(field_value)
        
        return False


class ConversationContext(models.Model):
    """Enhanced conversation context with dynamic fields"""
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.OneToOneField(Conversation, on_delete=models.CASCADE, related_name='dynamic_context')
    schema = models.ForeignKey(WorkspaceContextSchema, on_delete=models.CASCADE, related_name='contexts')
    
    # Context data
    title = models.CharField(max_length=255, blank=True, help_text="Auto-generated or manual title")
    context_data = models.JSONField(default=dict, help_text="Field values based on schema")
    ai_confidence_scores = models.JSONField(default=dict, help_text="AI confidence per field")
    
    # Status and priority
    status = models.CharField(max_length=50, default='new', help_text="Current status from schema")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    
    # Tags and metadata
    tags = models.JSONField(default=list, help_text="Array of tags")
    metadata = models.JSONField(default=dict, help_text="Additional metadata")
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_ai_update = models.DateTimeField(null=True, blank=True)
    last_human_update = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'conversation_contexts'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['schema', 'status']),
            models.Index(fields=['schema', 'priority']),
            models.Index(fields=['conversation']),
            models.Index(fields=['-updated_at']),
        ]
    
    def __str__(self):
        return f"Context for {self.conversation} - {self.title or 'Untitled'}"
    
    @property
    def completion_percentage(self):
        """Calculate how much of the schema is filled"""
        if not self.schema.fields:
            return 100
        
        required_fields = [f for f in self.schema.fields if f.get('required', False)]
        if not required_fields:
            return 100
        
        filled_required = 0
        for field in required_fields:
            field_id = field.get('id')
            if self.context_data.get(field_id):
                filled_required += 1
        
        return int((filled_required / len(required_fields)) * 100)
    
    @property
    def field_count(self):
        """Get total number of fields with data"""
        return len([k for k, v in self.context_data.items() if v])
    
    @property
    def high_confidence_fields(self):
        """Get fields with high AI confidence (>0.8)"""
        return [
            field_id for field_id, confidence 
            in self.ai_confidence_scores.items() 
            if confidence > 0.8
        ]
    
    def get_field_value(self, field_id, default=None):
        """Get value for a specific field"""
        return self.context_data.get(field_id, default)
    
    def set_field_value(self, field_id, value, confidence=None, is_ai_update=False):
        """Set value for a specific field"""
        self.context_data[field_id] = value
        
        if confidence is not None:
            self.ai_confidence_scores[field_id] = confidence
        
        if is_ai_update:
            from django.utils import timezone
            self.last_ai_update = timezone.now()
        else:
            from django.utils import timezone
            self.last_human_update = timezone.now()
    
    def update_status(self, new_status, user=None):
        """Update status with validation"""
        if self.schema.can_transition_status(self.status, new_status):
            old_status = self.status
            self.status = new_status
            
            # Log the change
            ContextHistory.objects.create(
                context=self,
                action_type='status_changed',
                field_name='status',
                old_value=old_status,
                new_value=new_status,
                changed_by_user=user,
                changed_by_ai=user is None
            )
            return True
        return False
    
    def recalculate_priority(self):
        """Recalculate priority based on current context data"""
        new_priority = self.schema.calculate_priority(self.context_data)
        if new_priority != self.priority:
            old_priority = self.priority
            self.priority = new_priority
            
            # Log the change
            ContextHistory.objects.create(
                context=self,
                action_type='priority_changed',
                field_name='priority',
                old_value=old_priority,
                new_value=new_priority,
                changed_by_ai=True
            )


class ContextHistory(models.Model):
    """Tracks all context changes for audit trail"""
    
    ACTION_TYPES = [
        ('created', 'Context Created'),
        ('field_updated', 'Field Updated'),
        ('status_changed', 'Status Changed'),
        ('priority_changed', 'Priority Changed'),
        ('ai_updated', 'AI Updated'),
        ('schema_changed', 'Schema Changed'),
        ('bulk_update', 'Bulk Update'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    context = models.ForeignKey(ConversationContext, on_delete=models.CASCADE, related_name='history')
    
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    field_name = models.CharField(max_length=100, blank=True, help_text="Which field changed")
    
    # Change details
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    
    # Source of change
    changed_by_ai = models.BooleanField(default=False)
    changed_by_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    confidence_score = models.FloatField(null=True, blank=True, help_text="AI confidence if AI change")
    
    # Additional metadata
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'context_history'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['context', '-created_at']),
            models.Index(fields=['action_type', '-created_at']),
            models.Index(fields=['changed_by_ai', '-created_at']),
        ]
    
    def __str__(self):
        source = "AI" if self.changed_by_ai else f"User {self.changed_by_user}"
        return f"{self.action_type} by {source} at {self.created_at}"


class BusinessRule(models.Model):
    """Defines workspace-specific automation rules"""
    
    TRIGGER_TYPES = [
        ('context_change', 'Context Field Changed'),
        ('new_message', 'New Message Received'),
        ('status_change', 'Status Changed'),
        ('priority_change', 'Priority Changed'),
        ('time_elapsed', 'Time Elapsed'),
        ('completion_rate', 'Completion Rate Changed'),
        ('sentiment_change', 'Sentiment Changed'),
    ]
    
    ACTION_TYPES = [
        ('send_notification', 'Send Notification'),
        ('change_status', 'Change Status'),
        ('change_priority', 'Change Priority'),
        ('assign_tag', 'Assign Tag'),
        ('create_task', 'Create Task'),
        ('send_email', 'Send Email'),
        ('webhook', 'Call Webhook'),
        ('escalate', 'Escalate Conversation'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='business_rules')
    
    # Rule definition
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Trigger configuration
    trigger_type = models.CharField(max_length=30, choices=TRIGGER_TYPES)
    trigger_conditions = models.JSONField(default=dict, help_text="Conditions that must be met")
    
    # Action configuration
    actions = models.JSONField(default=list, help_text="Actions to execute when triggered")
    
    # Rule state
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=100, help_text="Lower numbers = higher priority")
    
    # Execution tracking
    execution_count = models.IntegerField(default=0)
    last_executed = models.DateTimeField(null=True, blank=True)
    success_rate = models.FloatField(default=1.0, help_text="Percentage of successful executions")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_rules')
    
    class Meta:
        db_table = 'business_rules'
        ordering = ['priority', 'name']
        indexes = [
            models.Index(fields=['workspace', 'is_active']),
            models.Index(fields=['trigger_type', 'is_active']),
            models.Index(fields=['priority']),
        ]
    
    def __str__(self):
        return f"{self.workspace.name} - {self.name}"
    
    def evaluate_conditions(self, context_data):
        """Evaluate if this rule's conditions are met"""
        conditions = self.trigger_conditions or {}
        
        # If no conditions, rule is triggered
        if not conditions:
            return True
        
        operator = conditions.get('operator', 'and')
        rules = conditions.get('rules', [])
        
        if operator == 'and':
            return all(self._evaluate_single_condition(rule, context_data) for rule in rules)
        else:
            return any(self._evaluate_single_condition(rule, context_data) for rule in rules)
    
    def _evaluate_single_condition(self, condition, context_data):
        """Evaluate a single condition"""
        field = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value')
        
        if field == 'priority':
            field_value = context_data.get('priority')
        elif field == 'status':
            field_value = context_data.get('status')
        elif field == 'completion_rate':
            field_value = context_data.get('completion_percentage', 0)
        else:
            field_value = context_data.get('context_data', {}).get(field)
        
        return self._compare_values(field_value, operator, value)
    
    def _compare_values(self, field_value, operator, expected_value):
        """Compare values based on operator"""
        if operator == 'equals':
            return field_value == expected_value
        elif operator == 'not_equals':
            return field_value != expected_value
        elif operator == 'contains':
            return expected_value in str(field_value or '')
        elif operator == 'greater_than':
            return (field_value or 0) > expected_value
        elif operator == 'less_than':
            return (field_value or 0) < expected_value
        elif operator == 'in':
            return field_value in expected_value
        elif operator == 'not_in':
            return field_value not in expected_value
        elif operator == 'is_empty':
            return not field_value
        elif operator == 'is_not_empty':
            return bool(field_value)
        
        return False
    
    def execute_actions(self, context, trigger_data=None):
        """Execute the rule's actions"""
        from django.utils import timezone
        
        executed_actions = []
        
        for action in self.actions:
            try:
                result = self._execute_single_action(action, context, trigger_data)
                executed_actions.append({
                    'action': action,
                    'result': result,
                    'success': True
                })
            except Exception as e:
                executed_actions.append({
                    'action': action,
                    'error': str(e),
                    'success': False
                })
        
        # Update execution tracking
        self.execution_count += 1
        self.last_executed = timezone.now()
        
        # Update success rate
        successful_actions = len([a for a in executed_actions if a['success']])
        total_actions = len(executed_actions)
        current_success_rate = successful_actions / total_actions if total_actions > 0 else 1.0
        
        # Weighted average with previous success rate
        self.success_rate = (self.success_rate * (self.execution_count - 1) + current_success_rate) / self.execution_count
        
        self.save(update_fields=['execution_count', 'last_executed', 'success_rate'])
        
        return executed_actions
    
    def _execute_single_action(self, action, context, trigger_data):
        """Execute a single action"""
        action_type = action.get('type')
        action_config = action.get('config', {})
        
        if action_type == 'change_status':
            new_status = action_config.get('status')
            return context.update_status(new_status)
        
        elif action_type == 'change_priority':
            new_priority = action_config.get('priority')
            context.priority = new_priority
            context.save()
            return True
        
        elif action_type == 'assign_tag':
            tag = action_config.get('tag')
            if tag and tag not in context.tags:
                context.tags.append(tag)
                context.save()
            return True
        
        elif action_type == 'send_notification':
            # Import here to avoid circular imports
            from notifications.models import Notification
            message = action_config.get('message', 'Rule triggered')
            Notification.objects.create(
                workspace=context.conversation.workspace,
                title=f"Rule: {self.name}",
                message=message,
                notification_type='rule_triggered',
                related_conversation=context.conversation
            )
            return True
        
        elif action_type == 'webhook':
            # Implement webhook calling
            import requests
            url = action_config.get('url')
            payload = {
                'rule_name': self.name,
                'context_id': str(context.id),
                'conversation_id': str(context.conversation.id),
                'trigger_data': trigger_data,
                'context_data': context.context_data
            }
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        
        # Default: action not implemented
        return False


class RuleExecution(models.Model):
    """Log of rule executions for debugging and analytics"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rule = models.ForeignKey(BusinessRule, on_delete=models.CASCADE, related_name='executions')
    context = models.ForeignKey(ConversationContext, on_delete=models.CASCADE, related_name='rule_executions')
    
    # Execution details
    trigger_type = models.CharField(max_length=30)
    trigger_data = models.JSONField(default=dict)
    execution_result = models.JSONField(default=dict)
    
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    execution_time = models.FloatField(help_text="Execution time in seconds")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'rule_executions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['rule', '-created_at']),
            models.Index(fields=['context', '-created_at']),
            models.Index(fields=['success', '-created_at']),
        ]
    
    def __str__(self):
        return f"Execution of {self.rule.name} at {self.created_at}"
