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
        # Ensure context_data is a dict
        if not isinstance(context_data, dict):
            context_data = {}
        
        priority_config = self.priority_config or {}
        rules = priority_config.get('rules', [])
        
        # Ensure rules is a list
        if not isinstance(rules, list):
            rules = []
        
        # Default priority
        priority = priority_config.get('default_priority', 'medium')
        
        # Apply priority rules
        for rule in rules:
            if self._evaluate_priority_rule(rule, context_data):
                priority = rule.get('priority', priority)
                break
        
        return priority
    
    def _evaluate_priority_rule(self, rule, context_data):
        """Evaluate a single priority rule"""
        # Ensure context_data is a dict
        if not isinstance(context_data, dict):
            context_data = {}
        
        rule_type = rule.get('type')
        field_id = rule.get('field_id')
        condition = rule.get('condition')
        value = rule.get('value')
        
        if not all([rule_type, field_id, condition, value]):
            return False
        
        field_value = context_data.get(field_id)
        
        if rule_type == 'equals':
            return field_value == value
        elif rule_type == 'contains':
            return isinstance(field_value, str) and value in field_value
        elif rule_type == 'greater_than':
            return isinstance(field_value, (int, float)) and field_value > value
        elif rule_type == 'less_than':
            return isinstance(field_value, (int, float)) and field_value < value
        elif rule_type == 'is_set':
            return field_value is not None and field_value != ''
        elif rule_type == 'is_empty':
            return field_value is None or field_value == ''
        
        return False
    
    def validate_schema(self):
        """Validate schema structure and return any errors"""
        errors = []
        
        # Check if fields exist
        if not self.fields:
            errors.append("Schema must have at least one field")
            return errors
        
        # Ensure fields is a list
        if not isinstance(self.fields, list):
            errors.append("Fields must be a list")
            return errors
        
        # Validate each field
        field_ids = set()
        for i, field in enumerate(self.fields):
            field_errors = self._validate_field(field, i)
            errors.extend(field_errors)
            
            # Check for duplicate field IDs
            field_id = field.get('id')
            if field_id:
                if field_id in field_ids:
                    errors.append(f"Duplicate field ID: {field_id}")
                field_ids.add(field_id)
        
        # Validate status workflow
        workflow_errors = self._validate_status_workflow()
        errors.extend(workflow_errors)
        
        return errors
    
    def _validate_field(self, field, index):
        """Validate a single field definition"""
        errors = []
        
        # Ensure field is a dict
        if not isinstance(field, dict):
            errors.append(f"Field {index}: Must be a dictionary")
            return errors
        
        # Required fields
        required_fields = ['id', 'name', 'type']
        for req_field in required_fields:
            if req_field not in field:
                errors.append(f"Field {index}: Missing required field '{req_field}'")
        
        # Validate field type
        field_type = field.get('type')
        if field_type and field_type not in [f[0] for f in self.FIELD_TYPES]:
            errors.append(f"Field {index}: Invalid field type '{field_type}'")
        
        # Validate choice fields
        if field_type in ['choice', 'multi_choice']:
            choices = field.get('choices', [])
            if not isinstance(choices, list):
                errors.append(f"Field {index}: Choices must be a list")
            elif not choices:
                errors.append(f"Field {index}: Choice fields must have options")
        
        # Validate dependencies
        dependencies = field.get('dependencies', {})
        if dependencies:
            if not isinstance(dependencies, dict):
                errors.append(f"Field {index}: Dependencies must be a dictionary")
            else:
                for dep_field, dep_condition in dependencies.items():
                    if dep_field not in [f.get('id') for f in self.fields]:
                        errors.append(f"Field {index}: Invalid dependency field '{dep_field}'")
        
        return errors
    
    def _validate_status_workflow(self):
        """Validate status workflow configuration"""
        errors = []
        workflow = self.status_workflow or {}
        
        # Ensure workflow is a dict
        if not isinstance(workflow, dict):
            errors.append("Status workflow must be a dictionary")
            return errors
        
        statuses = workflow.get('statuses', [])
        transitions = workflow.get('transitions', {})
        
        # Ensure statuses is a list
        if not isinstance(statuses, list):
            errors.append("Statuses must be a list")
            return errors
        
        # Ensure transitions is a dict
        if not isinstance(transitions, dict):
            errors.append("Transitions must be a dictionary")
            return errors
        
        # Check if statuses exist
        if not statuses:
            errors.append("Status workflow must have at least one status")
            return errors
        
        # Validate status structure
        status_ids = set()
        for status in statuses:
            if not isinstance(status, dict):
                errors.append("Status must be a dictionary")
                continue
            status_id = status.get('id')
            if not status_id:
                errors.append("Status must have an ID")
            elif status_id in status_ids:
                errors.append(f"Duplicate status ID: {status_id}")
            else:
                status_ids.add(status_id)
        
        # Validate transitions
        for from_status, to_statuses in transitions.items():
            if from_status not in status_ids:
                errors.append(f"Invalid transition from status: {from_status}")
            if not isinstance(to_statuses, list):
                errors.append(f"Transitions to status must be a list for: {from_status}")
            else:
                for to_status in to_statuses:
                    if to_status not in status_ids:
                        errors.append(f"Invalid transition to status: {to_status}")
        
        return errors
    
    def _validate_field_value(self, field, value):
        """Validate a field value based on its type"""
        errors = []
        
        # Ensure field is a dict
        if not isinstance(field, dict):
            errors.append("Field must be a dictionary")
            return errors
        
        field_type = field.get('type')
        
        if value is None:
            return errors
        
        if field_type == 'number' or field_type == 'decimal':
            try:
                float(value)
            except (ValueError, TypeError):
                errors.append(f"Value must be a number")
        
        elif field_type == 'date':
            try:
                from django.utils.dateparse import parse_date
                parsed_date = parse_date(value)
                if not parsed_date:
                    errors.append(f"Invalid date format")
            except:
                errors.append(f"Invalid date format")
        
        elif field_type == 'datetime':
            try:
                from django.utils.dateparse import parse_datetime
                parsed_datetime = parse_datetime(value)
                if not parsed_datetime:
                    errors.append(f"Invalid datetime format")
            except:
                errors.append(f"Invalid datetime format")
        
        elif field_type == 'email':
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, str(value)):
                errors.append(f"Invalid email format")
        
        elif field_type == 'phone':
            import re
            phone_pattern = r'^\+?1?\d{9,15}$'
            if not re.match(phone_pattern, str(value)):
                errors.append(f"Invalid phone number format")
        
        elif field_type == 'url':
            import re
            url_pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
            if not re.match(url_pattern, str(value)):
                errors.append(f"Invalid URL format")
        
        elif field_type == 'choice':
            choices = field.get('choices', [])
            if not isinstance(choices, list):
                errors.append("Field choices must be a list")
            elif choices and value not in choices:
                errors.append(f"Value must be one of: {', '.join(choices)}")
        
        elif field_type == 'multi_choice':
            choices = field.get('choices', [])
            if not isinstance(choices, list):
                errors.append("Field choices must be a list")
            elif choices:
                if not isinstance(value, list):
                    errors.append(f"Value must be a list")
                else:
                    invalid_choices = [v for v in value if v not in choices]
                    if invalid_choices:
                        errors.append(f"Invalid choices: {', '.join(invalid_choices)}")
        
        elif field_type == 'boolean':
            if not isinstance(value, bool) and value not in ['true', 'false', '1', '0', 1, 0]:
                errors.append(f"Value must be true or false")
        
        return errors
    
    def get_schema_template(self):
        """Get a template for this schema type"""
        return {
            'fields': self.fields,
            'status_workflow': self.status_workflow,
            'priority_config': self.priority_config
        }
        
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
        
        # Ensure context_data is a dict
        context_data = self.context_data or {}
        
        filled_required = 0
        for field in required_fields:
            field_id = field.get('id')
            if context_data.get(field_id):
                filled_required += 1
        
        return int((filled_required / len(required_fields)) * 100)
    
    @property
    def field_count(self):
        """Get total number of fields with data"""
        context_data = self.context_data or {}
        return len([k for k, v in context_data.items() if v])
    
    @property
    def high_confidence_fields(self):
        """Get fields with high AI confidence (>0.8)"""
        ai_confidence_scores = self.ai_confidence_scores or {}
        return [
            field_id for field_id, confidence 
            in ai_confidence_scores.items() 
            if confidence > 0.8
        ]
    
    def get_field_value(self, field_id, default=None):
        """Get value for a specific field"""
        context_data = self.context_data or {}
        return context_data.get(field_id, default)
    
    def set_field_value(self, field_id, value, confidence=None, is_ai_update=False):
        """Set value for a specific field"""
        # Ensure context_data is a dict
        if self.context_data is None:
            self.context_data = {}
        
        self.context_data[field_id] = value
        
        # Ensure ai_confidence_scores is a dict
        if self.ai_confidence_scores is None:
            self.ai_confidence_scores = {}
        
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
        context_data = self.context_data or {}
        new_priority = self.schema.calculate_priority(context_data)
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
        ('field_dependency', 'Field Dependency Met'),
        ('schedule', 'Scheduled Trigger'),
        ('external_webhook', 'External Webhook Trigger'),
        ('conversation_age', 'Conversation Age Threshold'),
        ('response_time', 'Response Time Threshold'),
        ('customer_satisfaction', 'Customer Satisfaction Score'),
        ('business_hours', 'Business Hours Check'),
        ('workload_balance', 'Workload Distribution'),
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
        ('generate_ai_response', 'Generate AI Response'),
        ('schedule_followup', 'Schedule Follow-up'),
        ('assign_agent', 'Assign to Agent'),
        ('create_reminder', 'Create Reminder'),
        ('update_metrics', 'Update Analytics Metrics'),
        ('trigger_workflow', 'Trigger Multi-Step Workflow'),
        ('conditional_action', 'Execute Conditional Action'),
        ('batch_operation', 'Perform Batch Operation'),
        ('integration_sync', 'Sync with External System'),
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
    is_default = models.BooleanField(default=False, help_text="Whether this is a default system rule")
    priority = models.IntegerField(default=100, help_text="Lower numbers = higher priority")
    
    # Advanced rule configuration
    is_template = models.BooleanField(default=False, help_text="Whether this rule can be used as a template")
    template_category = models.CharField(max_length=100, blank=True, help_text="Category for rule templates")
    rule_version = models.CharField(max_length=20, default='1.0', help_text="Version of the rule")
    
    # Execution control
    max_executions = models.IntegerField(default=0, help_text="Maximum executions (0 = unlimited)")
    execution_interval = models.IntegerField(default=0, help_text="Minimum seconds between executions")
    last_execution_time = models.DateTimeField(null=True, blank=True)
    
    # Advanced conditions
    time_conditions = models.JSONField(default=dict, help_text="Time-based conditions (business hours, etc.)")
    field_dependencies = models.JSONField(default=dict, help_text="Field dependency rules")
    external_conditions = models.JSONField(default=dict, help_text="External system conditions")
    
    # Workflow configuration
    workflow_steps = models.JSONField(default=list, help_text="Multi-step workflow configuration")
    rollback_actions = models.JSONField(default=list, help_text="Actions to execute on failure")
    
    # Performance tracking
    average_execution_time = models.FloatField(default=0.0, help_text="Average execution time in seconds")
    success_threshold = models.FloatField(default=0.8, help_text="Minimum success rate to keep rule active")
    
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
        
        # Ensure conditions is a dict
        if not isinstance(conditions, dict):
            return True
        
        # Check execution limits first
        can_execute, reason = self.can_execute(context_data)
        if not can_execute:
            return False
        
        # Check time conditions
        if not self.evaluate_time_conditions(context_data):
            return False
        
        # Check field dependencies
        if not self.evaluate_field_dependencies(context_data):
            return False
        
        # Check trigger conditions
        operator = conditions.get('operator', 'and')
        rules = conditions.get('rules', [])
        
        # Ensure rules is a list
        if not isinstance(rules, list):
            return False
        
        if operator == 'and':
            return all(self._evaluate_single_condition(rule, context_data) for rule in rules)
        else:
            return any(self._evaluate_single_condition(rule, context_data) for rule in rules)
    
    def _evaluate_single_condition(self, condition, context_data):
        """Evaluate a single condition"""
        # Ensure condition is a dict
        if not isinstance(condition, dict):
            return False
        
        field = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value')
        
        # Ensure required fields exist
        if not field or not operator:
            return False
        
        if field == 'priority':
            field_value = context_data.get('priority')
        elif field == 'status':
            field_value = context_data.get('status')
        elif field == 'completion_rate':
            field_value = context_data.get('completion_percentage', 0)
        else:
            # Safely get context_data field
            context_data_dict = context_data.get('context_data', {})
            if context_data_dict is None:
                context_data_dict = {}
            field_value = context_data_dict.get(field)
        
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
            if expected_value is None:
                return False
            if not isinstance(expected_value, (list, tuple)):
                expected_value = [expected_value]
            return field_value in expected_value
        elif operator == 'not_in':
            if expected_value is None:
                return True
            if not isinstance(expected_value, (list, tuple)):
                expected_value = [expected_value]
            return field_value not in expected_value
        elif operator == 'is_empty':
            return not field_value
        elif operator == 'is_not_empty':
            return bool(field_value)
        elif operator == 'regex_match':
            import re
            try:
                if expected_value is None:
                    return False
                return bool(re.search(expected_value, str(field_value or '')))
            except:
                return False
        elif operator == 'starts_with':
            if expected_value is None:
                return False
            return str(field_value or '').startswith(str(expected_value))
        elif operator == 'ends_with':
            if expected_value is None:
                return False
            return str(field_value or '').endswith(str(expected_value))
        elif operator == 'between':
            if isinstance(expected_value, (list, tuple)) and len(expected_value) == 2:
                return (expected_value[0] <= (field_value or 0) <= expected_value[1])
            return False
        elif operator == 'percentage_of':
            if isinstance(field_value, (int, float)) and isinstance(expected_value, (int, float)):
                if expected_value == 0:  # Avoid division by zero
                    return False
                return (field_value / expected_value * 100) >= 80  # 80% threshold
            return False
        
        return False
    
    def evaluate_time_conditions(self, context_data):
        """Evaluate time-based conditions"""
        time_conditions = self.time_conditions or {}
        if not time_conditions:
            return True
        
        # Ensure time_conditions is a dict
        if not isinstance(time_conditions, dict):
            return True
        
        from django.utils import timezone
        now = timezone.now()
        
        # Business hours check
        if 'business_hours' in time_conditions:
            business_hours = time_conditions['business_hours']
            current_hour = now.hour
            current_weekday = now.weekday()  # 0 = Monday, 6 = Sunday
            
            # Check if current time is within business hours
            if 'start_hour' in business_hours and 'end_hour' in business_hours:
                if not (business_hours['start_hour'] <= current_hour <= business_hours['end_hour']):
                    return False
            
            # Check if current day is a business day
            if 'business_days' in business_hours:
                if current_weekday not in business_hours['business_days']:
                    return False
        
        # Time window check
        if 'time_window' in time_conditions:
            time_window = time_conditions['time_window']
            if 'start_time' in time_window and 'end_time' in time_window:
                start_time = time_window['start_time']
                end_time = time_window['end_time']
                current_time = now.time()
                
                if not (start_time <= current_time <= end_time):
                    return False
        
        # Day of week check
        if 'days_of_week' in time_conditions:
            if now.weekday() not in time_conditions['days_of_week']:
                return False
        
        # Month check
        if 'months' in time_conditions:
            if now.month not in time_conditions['months']:
                return False
        
        return True
    
    def evaluate_field_dependencies(self, context_data):
        """Evaluate field dependency conditions"""
        field_dependencies = self.field_dependencies or {}
        if not field_dependencies:
            return True
        
        for field_id, dependency_config in field_dependencies.items():
            # Safely get context_data field
            context_data_dict = context_data.get('context_data', {})
            if context_data_dict is None:
                context_data_dict = {}
            field_value = context_data_dict.get(field_id)
            dependency_type = dependency_config.get('type')
            required_value = dependency_config.get('value')
            
            if dependency_type == 'required':
                if not field_value:
                    return False
            elif dependency_type == 'equals':
                if field_value != required_value:
                    return False
            elif dependency_type == 'not_equals':
                if field_value == required_value:
                    return False
            elif dependency_type == 'greater_than':
                if not (field_value and field_value > required_value):
                    return False
            elif dependency_type == 'less_than':
                if not (field_value and field_value < required_value):
                    return False
        
        return True
    
    def can_execute(self, context_data):
        """Check if rule can execute based on execution limits"""
        # Check execution count limit
        if self.max_executions > 0 and self.execution_count >= self.max_executions:
            return False, "Maximum executions reached"
        
        # Check execution interval
        if self.execution_interval > 0 and self.last_executed:
            from django.utils import timezone
            time_since_last = (timezone.now() - self.last_executed).total_seconds()
            if time_since_last < self.execution_interval:
                return False, f"Execution interval not met ({time_since_last:.1f}s < {self.execution_interval}s)"
        
        # Check success rate threshold
        if self.success_rate < self.success_threshold:
            return False, "Success rate below threshold"
        
        return True, "Rule can execute"
    
    def should_auto_deactivate(self):
        """Check if rule should be automatically deactivated"""
        if self.execution_count >= 10 and self.success_rate < 0.3:
            return True, "Low success rate after multiple executions"
        
        if self.execution_count >= 50 and self.success_rate < 0.5:
            return True, "Poor performance after many executions"
        
        return False, "Rule performing adequately"
    
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
            if tag:
                # Ensure tags is a list
                if context.tags is None:
                    context.tags = []
                if not isinstance(context.tags, list):
                    context.tags = []
                if tag not in context.tags:
                    context.tags.append(tag)
                    context.save()
            return True
        
        elif action_type == 'send_notification':
            # Import here to avoid circular imports
            from notifications.models import Notification
            message = action_config.get('message', 'Rule triggered')
            
            # Safely get context data
            context_data = context.context_data or {}
            
            try:
                notification_data = {
                    'title': f"Rule: {self.name}",
                    'message': message,
                    'notification_type': 'rule_triggered'
                }
                
                # Check if Notification model has workspace field
                if hasattr(Notification, 'workspace'):
                    notification_data['workspace'] = context.conversation.workspace
                
                # Check if Notification model has related_conversation field
                if hasattr(Notification, 'related_conversation'):
                    notification_data['related_conversation'] = context.conversation
                
                # Check if Notification model has user_id field
                if hasattr(Notification, 'user_id') and not notification_data.get('user_id'):
                    # Try to get user from workspace owner
                    if hasattr(context.conversation.workspace, 'owner'):
                        notification_data['user_id'] = context.conversation.workspace.owner.id
                
                Notification.objects.create(**notification_data)
                return True
                
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to create notification: {str(e)}")
                return False
        
        elif action_type == 'webhook':
            # Implement webhook calling
            import requests
            url = action_config.get('url')
            
            # Safely get context data
            context_data = context.context_data or {}
            
            payload = {
                'rule_name': self.name,
                'context_id': str(context.id),
                'conversation_id': str(context.conversation.id),
                'trigger_data': trigger_data or {},
                'context_data': context_data
            }
            
            try:
                response = requests.post(url, json=payload, timeout=10)
                return response.status_code == 200
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Webhook call failed: {str(e)}")
                return False
        
        elif action_type == 'generate_ai_response':
            # Generate AI response for the conversation
            try:
                from messaging.tasks import generate_ai_response
                from messaging.models import Message
                
                # Get the latest client message in this conversation
                latest_message = Message.objects.filter(
                    conversation=context.conversation,
                    sender='client'
                ).order_by('-created_at').first()
                
                if latest_message:
                    # Schedule AI response generation
                    generate_ai_response.delay(str(latest_message.id))
                    return True
                else:
                    return False
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to generate AI response: {str(e)}")
                return False
        
        elif action_type == 'schedule_followup':
            # Schedule a follow-up task
            try:
                from django.utils import timezone
                from datetime import timedelta
                
                delay_hours = action_config.get('delay_hours', 24)
                followup_time = timezone.now() + timedelta(hours=delay_hours)
                
                # Create a scheduled task (you can implement this with Celery Beat)
                # For now, we'll just log it
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Scheduling follow-up for {delay_hours} hours from now")
                
                return True
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to schedule follow-up: {str(e)}")
                return False
        
        elif action_type == 'assign_agent':
            # Assign conversation to a specific agent
            agent_id = action_config.get('agent_id')
            if agent_id:
                try:
                    from core.models import AppUser
                    agent = AppUser.objects.get(id=agent_id)
                    # You can implement agent assignment logic here
                    context.context_data['assigned_agent'] = str(agent_id)
                    context.save()
                    return True
                except AppUser.DoesNotExist:
                    return False
            return False
        
        elif action_type == 'create_reminder':
            # Create a reminder for the conversation
            reminder_text = action_config.get('text', 'Follow up needed')
            reminder_time = action_config.get('reminder_time')
            
            try:
                # Store reminder in context data
                if 'reminders' not in context.context_data:
                    context.context_data['reminders'] = []
                
                reminder = {
                    'text': reminder_text,
                    'created_at': timezone.now().isoformat(),
                    'reminder_time': reminder_time
                }
                context.context_data['reminders'].append(reminder)
                context.save()
                return True
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to create reminder: {str(e)}")
                return False
        
        elif action_type == 'update_metrics':
            # Update analytics metrics
            metric_name = action_config.get('metric_name')
            metric_value = action_config.get('metric_value', 1)
            
            try:
                # You can implement metrics tracking here
                # For now, we'll just log it
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Updating metric: {metric_name} = {metric_value}")
                return True
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to update metrics: {str(e)}")
                return False
        
        elif action_type == 'trigger_workflow':
            # Trigger a multi-step workflow
            workflow_name = action_config.get('workflow_name')
            workflow_config = action_config.get('workflow_config', {})
            
            try:
                # Store workflow state in context
                if 'active_workflows' not in context.context_data:
                    context.context_data['active_workflows'] = {}
                
                context.context_data['active_workflows'][workflow_name] = {
                    'triggered_at': timezone.now().isoformat(),
                    'config': workflow_config,
                    'current_step': 0
                }
                context.save()
                return True
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to trigger workflow: {str(e)}")
                return False
        
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


class DynamicFieldSuggestion(models.Model):
    """AI-discovered fields to enhance existing schemas"""
    
    FIELD_TYPE_CHOICES = [
        ('text', 'Text'),
        ('textarea', 'Text Area'),
        ('number', 'Number'), 
        ('decimal', 'Decimal'),
        ('date', 'Date'),
        ('datetime', 'Date & Time'),
        ('boolean', 'Yes/No'),
        ('choice', 'Choice Dropdown'),
        ('multi_choice', 'Multi-Select'),
        ('email', 'Email'),
        ('phone', 'Phone Number'),
        ('url', 'URL'),
        ('tags', 'Tags'),
        ('priority', 'Priority Level'),
        ('status', 'Status'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey('core.Workspace', on_delete=models.CASCADE, related_name='field_suggestions')
    
    # Suggested field details
    suggested_field_name = models.CharField(max_length=100, help_text="Name of the suggested field")
    field_type = models.CharField(max_length=50, choices=FIELD_TYPE_CHOICES, help_text="Data type for the field")
    description = models.TextField(blank=True, help_text="Description of what this field captures")
    
    # AI analysis results
    frequency_detected = models.IntegerField(default=1, help_text="How many times this pattern was detected")
    sample_values = models.JSONField(default=list, help_text="Sample values found for this field")
    confidence_score = models.FloatField(help_text="AI confidence in this suggestion (0.0-1.0)")
    business_value_score = models.FloatField(default=0.0, help_text="Estimated business value of this field (0.0-1.0)")
    
    # Pattern analysis
    detection_pattern = models.TextField(blank=True, help_text="Pattern or context where this field was detected")
    related_fields = models.JSONField(default=list, help_text="Other fields that often appear with this one")
    context_examples = models.JSONField(default=list, help_text="Example conversation contexts where this field appears")
    
    # User review workflow
    is_reviewed = models.BooleanField(default=False, help_text="Whether user has reviewed this suggestion")
    is_approved = models.BooleanField(default=False, help_text="Whether user approved this suggestion")
    reviewed_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_suggestions')
    reviewed_at = models.DateTimeField(null=True, blank=True, help_text="When the suggestion was reviewed")
    review_notes = models.TextField(blank=True, help_text="User notes about this suggestion")
    
    # Implementation tracking
    target_schema = models.ForeignKey(WorkspaceContextSchema, on_delete=models.SET_NULL, null=True, blank=True, related_name='implemented_suggestions')
    implemented_at = models.DateTimeField(null=True, blank=True, help_text="When this suggestion was implemented")
    implementation_notes = models.TextField(blank=True, help_text="Notes about how this field was implemented")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'dynamic_field_suggestions'
        ordering = ['-confidence_score', '-business_value_score', '-frequency_detected']
        indexes = [
            models.Index(fields=['workspace', 'is_reviewed']),
            models.Index(fields=['workspace', 'is_approved']),
            models.Index(fields=['confidence_score', '-created_at']),
            models.Index(fields=['business_value_score', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.suggested_field_name} ({self.get_field_type_display()}) - {self.workspace.name}"
    
    def approve(self, user, target_schema=None, notes=""):
        """Approve this field suggestion"""
        self.is_reviewed = True
        self.is_approved = True
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        
        if target_schema:
            self.target_schema = target_schema
            
        self.save()
        
        # If target schema is specified, implement the field
        if target_schema:
            self.implement_in_schema(target_schema)
    
    def reject(self, user, notes=""):
        """Reject this field suggestion"""
        self.is_reviewed = True
        self.is_approved = False
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.review_notes = notes
        self.save()
    
    def implement_in_schema(self, schema):
        """Add this field to the specified schema"""
        try:
            # Get current schema fields
            schema_fields = schema.fields or []
            
            # Create new field definition
            new_field = {
                'id': str(uuid.uuid4()),
                'name': self.suggested_field_name,
                'type': self.field_type,
                'label': self.suggested_field_name.replace('_', ' ').title(),
                'description': self.description,
                'required': False,  # New fields are optional by default
                'source': 'ai_discovery',
                'discovered_at': timezone.now().isoformat(),
                'confidence_score': self.confidence_score,
                'business_value_score': self.business_value_score,
            }
            
            # Add field type specific configuration
            if self.field_type in ['choice', 'multi_choice']:
                new_field['choices'] = list(set(self.sample_values))  # Use unique sample values as choices
            
            # Add to schema fields
            schema_fields.append(new_field)
            schema.fields = schema_fields
            schema.save()
            
            # Update suggestion tracking
            self.target_schema = schema
            self.implemented_at = timezone.now()
            self.save()
            
            return True
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to implement field {self.suggested_field_name} in schema: {str(e)}")
            return False
    
    def get_business_value_label(self):
        """Get human-readable business value label"""
        if self.business_value_score >= 0.8:
            return "High Value"
        elif self.business_value_score >= 0.6:
            return "Medium Value"
        elif self.business_value_score >= 0.4:
            return "Low Value"
        else:
            return "Unknown Value"
    
    def get_confidence_label(self):
        """Get human-readable confidence label"""
        if self.confidence_score >= 0.9:
            return "Very High"
        elif self.confidence_score >= 0.7:
            return "High"
        elif self.confidence_score >= 0.5:
            return "Medium"
        elif self.confidence_score >= 0.3:
            return "Low"
        else:
            return "Very Low"
