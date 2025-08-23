from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.conf import settings
from django.utils.text import slugify
import uuid
from datetime import datetime, timezone
import re


class AppUser(models.Model):
    """
    Extended user model for APP users (business owners)
    These are the main users of the application who have their own workspaces
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link to Django's built-in User model
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='app_profile')
    
    # Business Information
    business_name = models.CharField(max_length=255, blank=True, null=True)
    business_type = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    
    # Profile Information
    full_name = models.CharField(max_length=255, blank=True, null=True)
    occupation = models.CharField(max_length=255, blank=True, null=True)
    industry = models.CharField(max_length=255, blank=True, null=True)
    
    # Account Status
    is_verified = models.BooleanField(default=False)
    subscription_status = models.CharField(max_length=20, choices=[
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ], default='trial')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'app_users'
        verbose_name = 'App User'
        verbose_name_plural = 'App Users'
    
    def __str__(self):
        return f"{self.full_name or self.user.username} ({self.business_name or 'No Business'})"
    
    @property
    def display_name(self):
        return self.full_name or self.user.username
    
    @property
    def username(self):
        return self.user.username
    
    @property
    def email(self):
        return self.user.email
    
    @property
    def workspace(self):
        """Get the user's primary workspace"""
        return self.user.workspaces.first()  # Each user has one primary workspace


class Workspace(models.Model):
    """Business account/workspace model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link to the APP user (business owner)
    owner = models.ForeignKey(
        'auth.User', 
        on_delete=models.CASCADE, 
        related_name='workspaces',
        null=True, blank=True  # Temporary for migration
    )
    
    name = models.CharField(max_length=255)
    timezone = models.CharField(max_length=50, default='UTC')
    auto_reply_mode = models.BooleanField(default=True)
    assistant_name = models.CharField(max_length=100, default='Assistant')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Google Calendar Integration
    google_calendar_connected = models.BooleanField(default=False)
    google_refresh_token = models.TextField(blank=True, null=True)
    google_calendar_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Business Hours (stored as JSON or separate model if complex)
    business_hours = models.JSONField(default=dict, blank=True)
    
    # Owner Profile for AI Personalization
    owner_name = models.CharField(max_length=255, blank=True, null=True)
    owner_occupation = models.CharField(max_length=255, blank=True, null=True)
    industry = models.CharField(max_length=255, blank=True, null=True)
    ai_role = models.CharField(max_length=100, choices=[
        ('general', 'General Assistant'),
        ('banker', 'Banking Assistant'),
        ('medical', 'Medical Assistant'),
        ('legal', 'Legal Assistant'),
        ('real_estate', 'Real Estate Assistant'),
        ('restaurant', 'Restaurant Assistant'),
        ('retail', 'Retail Assistant'),
        ('tech_support', 'Technical Support'),
        ('secretary', 'Personal Secretary'),
        ('customer_service', 'Customer Service'),
        ('consultant', 'Business Consultant'),
        ('educator', 'Educational Assistant'),
    ], default='general')
    ai_personality = models.CharField(max_length=100, choices=[
        ('professional', 'Professional'),
        ('friendly', 'Friendly'),
        ('formal', 'Formal'),
        ('casual', 'Casual'),
        ('empathetic', 'Empathetic'),
        ('direct', 'Direct'),
    ], default='professional')
    custom_instructions = models.TextField(blank=True, null=True, help_text="Custom instructions for AI behavior")
    profile_completed = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'workspaces'
        
    def __str__(self):
        return self.name
    
    @property
    def portal_slug(self):
        """Generate a user-friendly portal URL slug"""
        try:
            # Get the AppUser profile
            app_user = self.owner.app_profile
            
            # If it's a business user (has business_name), use: company-name/employee-name
            if app_user.business_name and app_user.business_name.strip():
                company_slug = slugify(app_user.business_name)
                employee_slug = slugify(app_user.full_name or self.owner.username)
                return f"{company_slug}/{employee_slug}"
            
            # If it's a personal user (no business_name), use: user-name
            else:
                user_slug = slugify(app_user.full_name or self.owner.username)
                return user_slug
                
        except Exception:
            # Fallback to workspace name if anything goes wrong
            return slugify(self.name) or str(self.id)
    
    def get_simple_slug(self):
        """Get a simple, reliable slug for the workspace"""
        try:
            return slugify(self.name) or str(self.id)
        except Exception:
            return str(self.id)
    
    @property
    def portal_url(self):
        """Get the full portal URL"""
        from django.conf import settings
        base_url = getattr(settings, 'FRONTEND_BASE_URL', 'http://localhost:3000')
        return f"{base_url}/portal/{self.portal_slug}"
    
    def ensure_unique_portal_slug(self):
        """Ensure the portal slug is unique by adding a number suffix if needed"""
        base_slug = self.portal_slug
        
        # Check if this slug is already taken by another workspace
        counter = 1
        test_slug = base_slug
        
        while Workspace.objects.exclude(id=self.id).filter(
            owner__app_profile__business_name__isnull=False
        ).annotate(
            computed_slug=models.Case(
                models.When(
                    owner__app_profile__business_name__isnull=False,
                    then=models.Concat(
                        models.F('owner__app_profile__business_name'),
                        models.Value('/'),
                        models.Coalesce(
                            models.F('owner__app_profile__full_name'),
                            models.F('owner__username')
                        )
                    )
                ),
                default=models.Coalesce(
                    models.F('owner__app_profile__full_name'),
                    models.F('owner__username')
                )
            )
        ).filter(computed_slug=test_slug).exists():
            counter += 1
            test_slug = f"{base_slug}-{counter}"
        
        return test_slug
    
    def get_default_agent(self):
        """Get the default AI agent for this workspace"""
        return self.ai_agents.filter(is_default=True).first()
    
    def get_active_agents(self):
        """Get all active AI agents for this workspace"""
        return self.ai_agents.filter(is_active=True).order_by('-is_default', 'name')


class Contact(models.Model):
    """Customer identity model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='contacts')
    
    # Phone number in E.164 format
    phone_validator = RegexValidator(
        regex=r'^\+[1-9]\d{1,14}$',
        message='Phone number must be in E.164 format (e.g., +1234567890)'
    )
    phone_e164 = models.CharField(max_length=16, validators=[phone_validator])
    
    name = models.CharField(max_length=255, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'contacts'
        unique_together = ['workspace', 'phone_e164']
        
    def __str__(self):
        return f"{self.name or 'Unknown'} ({self.phone_e164[-4:]})"  # Mask phone number
    
    @property
    def masked_phone(self):
        """Return masked phone number showing only last 2 digits"""
        return f"***{self.phone_e164[-2:]}"


class Session(models.Model):
    """Chat session tracking model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='sessions')
    session_token = models.CharField(max_length=255, unique=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'sessions'
        
    def __str__(self):
        return f"Session {self.session_token[:8]}... for {self.contact}"


class Conversation(models.Model):
    """Conversation thread model"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('resolved', 'Resolved'),
        ('archived', 'Archived'),
    ]
    
    INTENT_CHOICES = [
        ('inquiry', 'General Inquiry'),
        ('request', 'Service Request'),
        ('complaint', 'Complaint'),
        ('appointment', 'Appointment Request'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='conversations')
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='conversations')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='conversations')
    
    # 🆕 ADD: Agent reference (nullable for backward compatibility)
    ai_agent = models.ForeignKey('AIAgent', on_delete=models.CASCADE, 
                                null=True, blank=True, 
                                help_text="Agent handling this conversation")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    last_intent = models.CharField(max_length=20, choices=INTENT_CHOICES, default='other')
    
    # AI Analysis Fields
    summary = models.TextField(blank=True, null=True, help_text="AI-generated conversation summary")
    key_points = models.JSONField(default=list, blank=True, help_text="Key points extracted from conversation")
    resolution_status = models.CharField(max_length=20, blank=True, null=True, help_text="AI-determined resolution status")
    action_items = models.JSONField(default=list, blank=True, help_text="Action items identified by AI")
    sentiment_score = models.IntegerField(default=3, help_text="Customer satisfaction score (1-5)")
    sentiment_data = models.JSONField(default=dict, blank=True, help_text="Detailed sentiment analysis results")
    extracted_entities = models.JSONField(default=dict, blank=True, help_text="Entities extracted from conversation")
    conversation_metrics = models.JSONField(default=dict, blank=True, help_text="Conversation metrics and statistics")
    insights_generated_at = models.DateTimeField(blank=True, null=True, help_text="When AI insights were last generated")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'conversations'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['workspace', '-updated_at']),
            models.Index(fields=['status', '-updated_at']),
            models.Index(fields=['sentiment_score', '-updated_at']),
            models.Index(fields=['resolution_status', '-updated_at']),
        ]
    
    @property
    def has_ai_insights(self):
        """Check if AI insights have been generated"""
        return self.insights_generated_at is not None
    
    @property
    def sentiment_label(self):
        """Get human-readable sentiment label"""
        if not self.sentiment_data:
            return 'Unknown'
        return self.sentiment_data.get('overall_sentiment', 'neutral').replace('_', ' ').title()
    
    @property
    def message_count(self):
        """Get the number of messages in this conversation"""
        return self.messages.count()
    
    def get_active_agent(self):
        """Get agent for this conversation or workspace default"""
        return self.ai_agent or self.workspace.get_default_agent()
        
    def __str__(self):
        return f"Conversation {str(self.id)[:8]}... with {self.contact}"


class AIAgent(models.Model):
    """AI Agent model for multi-agent support per workspace"""
    CHANNEL_TYPE_CHOICES = [
        ('instagram', 'Instagram'),
        ('whatsapp', 'WhatsApp'), 
        ('facebook', 'Facebook Messenger'),
        ('telegram', 'Telegram'),
        ('website', 'Website Chat'),
        ('sms', 'SMS'),
        ('email', 'Email'),
        ('phone', 'Phone Call'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='ai_agents')
    
    # Basic Information
    name = models.CharField(max_length=100, help_text="Agent name (e.g., 'Customer Support Bot', 'Sales Assistant')")
    slug = models.SlugField(max_length=120, help_text="URL-friendly identifier for the agent")
    description = models.TextField(blank=True, help_text="Description of the agent's purpose and capabilities")
    
    # Channel Configuration
    channel_type = models.CharField(max_length=20, choices=CHANNEL_TYPE_CHOICES, default='website')
    channel_specific_config = models.JSONField(default=dict, blank=True, help_text="Channel-specific configuration settings")
    
    # Business Customization
    business_context = models.JSONField(default=dict, blank=True, help_text="Business-specific context and parameters")
    personality_config = models.JSONField(default=dict, blank=True, help_text="AI personality and communication style")
    
    # AI Prompt Configuration
    generated_prompt = models.TextField(blank=True, help_text="AI-generated prompt based on configuration")
    custom_instructions = models.TextField(blank=True, help_text="Custom instructions for the AI agent")
    prompt_version = models.CharField(max_length=20, default='1.0', help_text="Version of the current prompt")
    
    # Deployment Status
    is_active = models.BooleanField(default=True, help_text="Whether this agent is currently active")
    is_default = models.BooleanField(default=False, help_text="Whether this is the default agent for the workspace")
    deployment_url = models.URLField(blank=True, help_text="Deployment URL for this agent")
    
    # Performance Metrics
    performance_metrics = models.JSONField(default=dict, blank=True, help_text="Performance metrics and analytics")
    conversation_count = models.IntegerField(default=0, help_text="Total conversations handled by this agent")
    average_response_time = models.FloatField(default=0.0, help_text="Average response time in seconds")
    customer_satisfaction_score = models.FloatField(default=0.0, help_text="Average customer satisfaction (1-5)")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_agents')
    
    class Meta:
        db_table = 'ai_agents'
        unique_together = ['workspace', 'slug']
        ordering = ['-is_default', 'name']
        indexes = [
            models.Index(fields=['workspace', 'is_active']),
            models.Index(fields=['workspace', 'is_default']),
            models.Index(fields=['channel_type', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.workspace.name} - {self.name}"
    
    def get_portal_url(self):
        """Generate agent-specific portal URL"""
        return f"/portal/{self.workspace.slug}/{self.slug}/"
    
    def get_deployment_url(self):
        """Get the deployment URL for this agent"""
        if self.deployment_url:
            return self.deployment_url
        return self.get_portal_url()
    
    def update_performance_metrics(self, conversation_data):
        """Update performance metrics based on conversation data"""
        # Update conversation count
        self.conversation_count += 1
        
        # Update average response time
        if 'response_time' in conversation_data:
            current_avg = self.average_response_time
            new_time = conversation_data['response_time']
            self.average_response_time = ((current_avg * (self.conversation_count - 1)) + new_time) / self.conversation_count
        
        # Update customer satisfaction
        if 'satisfaction_score' in conversation_data:
            current_avg = self.customer_satisfaction_score
            new_score = conversation_data['satisfaction_score']
            self.customer_satisfaction_score = ((current_avg * (self.conversation_count - 1)) + new_score) / self.conversation_count
        
        self.save()


class AgentSchemaAssignment(models.Model):
    """Links agents to existing schemas with priority and configuration"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(AIAgent, on_delete=models.CASCADE, related_name='schema_assignments')
    schema = models.ForeignKey('context_tracking.WorkspaceContextSchema', on_delete=models.CASCADE, related_name='agent_assignments')
    
    # Assignment Configuration
    priority = models.IntegerField(default=1, help_text="Priority order for this schema (lower = higher priority)")
    is_primary = models.BooleanField(default=False, help_text="Whether this is the primary schema for the agent")
    is_required = models.BooleanField(default=True, help_text="Whether this schema is required for the agent")
    
    # Customization
    custom_config = models.JSONField(default=dict, blank=True, help_text="Agent-specific customization for this schema")
    field_mapping = models.JSONField(default=dict, blank=True, help_text="Custom field mappings for this agent-schema combination")
    
    # Usage Tracking
    usage_count = models.IntegerField(default=0, help_text="Number of times this schema was used by the agent")
    last_used = models.DateTimeField(null=True, blank=True, help_text="When this schema was last used")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'agent_schema_assignments'
        unique_together = ['agent', 'schema']
        ordering = ['priority', 'schema__name']
        indexes = [
            models.Index(fields=['agent', 'priority']),
            models.Index(fields=['agent', 'is_primary']),
        ]
    
    def __str__(self):
        return f"{self.agent.name} - {self.schema.name} (Priority: {self.priority})"
    
    def mark_used(self):
        """Mark this schema as used by the agent"""
        self.usage_count += 1
        self.last_used = timezone.now()
        self.save()


class BusinessTypeTemplate(models.Model):
    """Industry-specific templates that leverage existing schema system"""
    INDUSTRY_CHOICES = [
        ('healthcare', 'Healthcare/Medical'),
        ('restaurant', 'Restaurant/Food Service'),
        ('finance', 'Financial Services'),
        ('ecommerce', 'E-commerce/Retail'),
        ('realestate', 'Real Estate'),
        ('professional', 'Professional Services'),
        ('education', 'Education/Training'),
        ('consulting', 'Consulting/Advisory'),
        ('manufacturing', 'Manufacturing/Industrial'),
        ('technology', 'Technology/SaaS'),
        ('hospitality', 'Hospitality/Tourism'),
        ('legal', 'Legal Services'),
        ('creative', 'Creative/Media'),
        ('nonprofit', 'Non-Profit/Charity'),
        ('other', 'Other/General'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic Information
    name = models.CharField(max_length=100, help_text="Template name (e.g., 'Medical Practice Assistant', 'Restaurant Order Bot')")
    industry = models.CharField(max_length=50, choices=INDUSTRY_CHOICES, help_text="Industry category for this template")
    description = models.TextField(help_text="Detailed description of what this template provides")
    
    # Template Content
    default_schema_templates = models.JSONField(default=dict, help_text="Templates for creating WorkspaceContextSchemas")
    default_rule_templates = models.JSONField(default=dict, help_text="Templates for creating BusinessRules")
    
    # AI Configuration
    base_prompt_template = models.TextField(help_text="Base AI prompt template for this business type")
    personality_defaults = models.JSONField(default=dict, help_text="Default personality and communication style")
    conversation_flow = models.JSONField(default=dict, help_text="Suggested conversation flow patterns")
    
    # Integration Suggestions
    recommended_integrations = models.JSONField(default=dict, help_text="Recommended third-party integrations")
    compliance_requirements = models.JSONField(default=dict, help_text="Industry compliance and regulatory requirements")
    best_practices = models.JSONField(default=dict, help_text="Industry best practices and guidelines")
    
    # Template Metadata
    is_active = models.BooleanField(default=True, help_text="Whether this template is available for use")
    is_featured = models.BooleanField(default=False, help_text="Whether this template is featured/recommended")
    version = models.CharField(max_length=20, default='1.0', help_text="Template version")
    usage_count = models.IntegerField(default=0, help_text="Number of times this template has been applied")
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_templates')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'business_type_templates'
        ordering = ['-is_featured', 'industry', 'name']
        indexes = [
            models.Index(fields=['industry', 'is_active']),
            models.Index(fields=['is_featured', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.get_industry_display()} - {self.name}"
    
    def get_schema_template(self, template_name):
        """Get a specific schema template by name"""
        return self.default_schema_templates.get(template_name, {})
    
    def get_rule_template(self, template_name):
        """Get a specific business rule template by name"""
        return self.default_rule_templates.get(template_name, {})
    
    def apply_to_workspace(self, workspace):
        """Apply this template to a workspace, creating schemas and rules"""
        from context_tracking.models import WorkspaceContextSchema, BusinessRule
        from django.utils import timezone
        import uuid
        
        created_items = {
            'schemas': [],
            'rules': [],
            'agents': []
        }
        
        try:
            # Create schemas from template
            for schema_name, schema_data in self.default_schema_templates.items():
                schema, created = WorkspaceContextSchema.objects.get_or_create(
                    name=schema_data.get('name', schema_name),
                    workspace=workspace,
                    defaults={
                        'description': schema_data.get('description', f'Auto-generated {schema_name} schema'),
                        'fields': schema_data.get('fields', []),
                        'status_workflow': schema_data.get('status_workflow', {}),
                        'is_active': True,
                        'is_default': schema_data.get('is_default', False),
                        'source': 'template',
                        'template_source': str(self.id)
                    }
                )
                
                if created:
                    created_items['schemas'].append(schema)
            
            # Create business rules from template
            for rule_name, rule_data in self.default_rule_templates.items():
                rule, created = BusinessRule.objects.get_or_create(
                    name=rule_data.get('name', rule_name),
                    workspace=workspace,
                    defaults={
                        'description': rule_data.get('description', f'Auto-generated {rule_name} rule'),
                        'trigger_type': rule_data.get('trigger_type', 'context_change'),
                        'conditions': rule_data.get('conditions', []),
                        'actions': rule_data.get('actions', []),
                        'is_active': True,
                        'is_default': rule_data.get('is_default', False),
                        'source': 'template',
                        'template_source': str(self.id)
                    }
                )
                
                if created:
                    created_items['rules'].append(rule)
            
            # Create default AI agent if specified in template
            if self.personality_defaults and self.base_prompt_template:
                from django.utils.text import slugify
                
                agent_name = f"{workspace.name} {self.name}"
                agent, created = AIAgent.objects.get_or_create(
                    name=agent_name,
                    workspace=workspace,
                    defaults={
                        'slug': slugify(agent_name),
                        'description': self.description,
                        'channel_type': 'website',
                        'business_context': {
                            'business_type': workspace.business_type,
                            'industry': workspace.industry,
                            'template_source': str(self.id)
                        },
                        'personality_config': self.personality_defaults,
                        'generated_prompt': self.base_prompt_template.format(
                            workspace_name=workspace.name,
                            business_type=workspace.business_type,
                            industry=workspace.industry
                        ),
                        'is_active': True,
                        'is_default': True
                    }
                )
                
                if created:
                    created_items['agents'].append(agent)
            
            # Update template usage
            self.usage_count += 1
            self.save()
            
            return created_items
            
        except Exception as e:
            # Log the error and return what was created
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to apply template {self.name} to workspace {workspace.name}: {str(e)}")
            return created_items
    
    def get_template_preview(self):
        """Get a preview of what this template will create"""
        preview = {
            'schemas': [],
            'rules': [],
            'agent_info': None
        }
        
        # Preview schemas
        for schema_name, schema_data in self.default_schema_templates.items():
            preview['schemas'].append({
                'name': schema_data.get('name', schema_name),
                'description': schema_data.get('description', ''),
                'field_count': len(schema_data.get('fields', [])),
                'has_status_workflow': bool(schema_data.get('status_workflow', {}))
            })
        
        # Preview rules
        for rule_name, rule_data in self.default_rule_templates.items():
            preview['rules'].append({
                'name': rule_data.get('name', rule_name),
                'description': rule_data.get('description', ''),
                'trigger_type': rule_data.get('trigger_type', 'context_change'),
                'action_count': len(rule_data.get('actions', []))
            })
        
        # Preview agent info
        if self.personality_defaults and self.base_prompt_template:
            preview['agent_info'] = {
                'name': f"AI {self.name}",
                'description': self.description,
                'personality': self.personality_defaults.get('tone', 'professional'),
                'channel_type': 'website'
            }
        
        return preview
    
    def clone_template(self, new_name=None, new_industry=None):
        """Create a copy of this template with modifications"""
        new_template = BusinessTypeTemplate.objects.create(
            name=new_name or f"{self.name} (Copy)",
            industry=new_industry or self.industry,
            description=self.description,
            default_schema_templates=self.default_schema_templates,
            default_rule_templates=self.default_rule_templates,
            base_prompt_template=self.base_prompt_template,
            personality_defaults=self.personality_defaults,
            conversation_flow=self.conversation_flow,
            recommended_integrations=self.recommended_integrations,
            compliance_requirements=self.compliance_requirements,
            best_practices=self.best_practices,
            is_active=False,  # Cloned templates start as inactive
            is_featured=False,
            version='1.0'
        )
        
        return new_template
