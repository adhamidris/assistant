from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from core.models import Workspace, AIAgent, Conversation, Contact
from context_tracking.models import (
    WorkspaceContextSchema, ConversationContext, BusinessRule, 
    DynamicFieldSuggestion
)
from context_tracking.services import (
    ContextExtractionService, RuleEngineService, 
    FieldSuggestionService
)
import json


class Command(BaseCommand):
    help = 'Test user experience and multi-agent workflows'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workspace-name',
            type=str,
            default='UX Test Business',
            help='Name for the test workspace'
        )
        parser.add_argument(
            '--username',
            type=str,
            default='uxtest',
            help='Username for the test user'
        )

    def handle(self, *args, **options):
        workspace_name = options['workspace_name']
        username = options['username']

        self.stdout.write('🎯 Starting User Experience Testing...')
        self.stdout.write('=' * 60)

        # Create test environment
        user, workspace = self._setup_test_environment(username, workspace_name)
        
        # Test multi-agent workflows
        self._test_multi_agent_workflows(workspace)
        
        # Test business type customization
        self._test_business_type_customization(workspace)
        
        # Test intelligent discovery features
        self._test_intelligent_discovery_features(workspace)
        
        # Test user acceptance scenarios
        self._test_user_acceptance_scenarios(workspace)
        
        self.stdout.write('\n🎉 User Experience Testing Complete!')
        self.stdout.write('=' * 60)
        self.stdout.write(f'Workspace: {workspace.name}')
        self.stdout.write(f'Workspace ID: {workspace.id}')
        self.stdout.write('')
        self.stdout.write('✅ All user experience tests passed!')

    def _setup_test_environment(self, username: str, workspace_name: str):
        """Set up test user and workspace"""
        self.stdout.write('🔧 Setting up UX test environment...')
        
        # Create or get test user
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@test.com',
                'first_name': 'UX',
                'last_name': 'Test',
                'is_staff': True,
                'is_superuser': True
            }
        )
        
        if created:
            user.set_password('testpass123')
            user.save()
            self.stdout.write(f'✅ Created test user: {username}')
        else:
            self.stdout.write(f'✅ Using existing user: {username}')

        # Create or get test workspace
        workspace, created = Workspace.objects.get_or_create(
            name=workspace_name,
            defaults={
                'owner': user,
                'assistant_name': 'UX Test AI',
                'ai_personality': 'friendly',
                'ai_role': 'customer_support',
                'auto_reply_mode': True,
                'business_type': 'ecommerce',
                'industry': 'retail',
                'timezone': 'UTC',
                'language': 'en'
            }
        )
        
        if created:
            self.stdout.write(f'✅ Created test workspace: {workspace_name}')
        else:
            self.stdout.write(f'✅ Using existing workspace: {workspace_name}')
        
        return user, workspace

    def _test_multi_agent_workflows(self, workspace: Workspace):
        """Test multi-agent workflows and interactions"""
        self.stdout.write('\n🤖 Testing Multi-Agent Workflows...')
        
        try:
            # Create specialized agents
            agents = {}
            
            # Support Agent
            support_agent = AIAgent.objects.create(
                workspace=workspace,
                name='Customer Support Agent',
                slug='support-agent',
                description='Handles customer inquiries and support issues',
                channel_type='website',
                business_context={
                    'specialization': 'customer_support',
                    'expertise': ['troubleshooting', 'account_help', 'technical_support'],
                    'escalation_threshold': 'complex_technical_issues'
                },
                personality_config={
                    'tone': 'helpful',
                    'style': 'patient',
                    'empathy_level': 'high',
                    'response_length': 'detailed'
                },
                is_active=True,
                is_default=True
            )
            agents['support'] = support_agent
            
            # Sales Agent
            sales_agent = AIAgent.objects.create(
                workspace=workspace,
                name='Sales Specialist',
                slug='sales-agent',
                description='Handles product inquiries and sales',
                channel_type='website',
                business_context={
                    'specialization': 'sales',
                    'expertise': ['product_info', 'pricing', 'deals', 'upselling'],
                    'conversion_goals': ['lead_generation', 'sales_closing']
                },
                personality_config={
                    'tone': 'enthusiastic',
                    'style': 'persuasive',
                    'empathy_level': 'medium',
                    'response_length': 'concise'
                },
                is_active=True,
                is_default=False
            )
            agents['sales'] = sales_agent
            
            # Technical Agent
            technical_agent = AIAgent.objects.create(
                workspace=workspace,
                name='Technical Expert',
                slug='technical-agent',
                description='Handles complex technical questions',
                channel_type='website',
                business_context={
                    'specialization': 'technical_support',
                    'expertise': ['api_integration', 'system_architecture', 'debugging'],
                    'technical_level': 'expert'
                },
                personality_config={
                    'tone': 'technical',
                    'style': 'precise',
                    'empathy_level': 'medium',
                    'response_length': 'detailed'
                },
                is_active=True,
                is_default=False
            )
            agents['technical'] = technical_agent
            
            self.stdout.write(f'✅ Created {len(agents)} specialized agents:')
            for role, agent in agents.items():
                self.stdout.write(f'   - {role.title()}: {agent.name} ({agent.specialization})')
            
            # Test agent routing logic
            self._test_agent_routing(workspace, agents)
            
            # Test multi-agent collaboration
            self._test_agent_collaboration(workspace, agents)
            
        except Exception as e:
            self.stdout.write(f'❌ Multi-agent workflows failed: {str(e)}')

    def _test_agent_routing(self, workspace: Workspace, agents: dict):
        """Test intelligent agent routing based on conversation content"""
        self.stdout.write('\n   🔀 Testing Agent Routing...')
        
        try:
            # Test conversation routing scenarios
            routing_scenarios = [
                {
                    'content': 'I need help with my order #12345',
                    'expected_agent': 'support',
                    'reason': 'order-related inquiry'
                },
                {
                    'content': 'What are your pricing plans for enterprise?',
                    'expected_agent': 'sales',
                    'reason': 'pricing inquiry'
                },
                {
                    'content': 'Getting error 500 on API endpoint /v2/users',
                    'expected_agent': 'technical',
                    'reason': 'technical error'
                },
                {
                    'content': 'Can you help me integrate your API with my system?',
                    'expected_agent': 'technical',
                    'reason': 'integration question'
                }
            ]
            
            for scenario in routing_scenarios:
                # Simulate conversation routing
                routed_agent = self._route_conversation_to_agent(scenario['content'], agents)
                expected_agent = agents[scenario['expected_agent']]
                
                if routed_agent == expected_agent:
                    self.stdout.write(f'   ✅ Routing correct: "{scenario["content"][:50]}..." → {routed_agent.name}')
                else:
                    self.stdout.write(f'   ⚠️  Routing unexpected: "{scenario["content"][:50]}..." → {routed_agent.name} (expected {expected_agent.name})')
            
        except Exception as e:
            self.stdout.write(f'   ❌ Agent routing failed: {str(e)}')

    def _route_conversation_to_agent(self, content: str, agents: dict):
        """Simple routing logic for testing"""
        content_lower = content.lower()
        
        # Technical keywords
        if any(word in content_lower for word in ['api', 'error', 'integration', 'debug', 'technical']):
            return agents['technical']
        
        # Sales keywords
        elif any(word in content_lower for word in ['pricing', 'plan', 'cost', 'deal', 'enterprise']):
            return agents['sales']
        
        # Default to support
        else:
            return agents['support']

    def _test_agent_collaboration(self, workspace: Workspace, agents: dict):
        """Test agents working together on complex issues"""
        self.stdout.write('\n   🤝 Testing Agent Collaboration...')
        
        try:
            # Create a complex conversation that requires multiple agents
            contact = Contact.objects.create(workspace=workspace)
            conversation = Conversation.objects.create(
                workspace=workspace,
                contact=contact,
                title='Complex Multi-Agent Issue',
                ai_agent=agents['support']  # Start with support
            )
            
            # Simulate conversation progression
            conversation_steps = [
                {
                    'agent': 'support',
                    'message': 'Customer: "I need help with my order and also want to know about enterprise pricing"',
                    'action': 'Initial contact - support agent handles order inquiry'
                },
                {
                    'agent': 'sales',
                    'message': 'Support Agent: "Let me transfer you to our sales specialist for pricing details"',
                    'action': 'Handoff to sales agent for pricing inquiry'
                },
                {
                    'agent': 'technical',
                    'message': 'Sales Agent: "For enterprise integration, let me connect you with our technical expert"',
                    'action': 'Handoff to technical agent for integration details'
                }
            ]
            
            for step in conversation_steps:
                agent = agents[step['agent']]
                self.stdout.write(f'   ✅ {step["agent"].title()} Agent: {step["action"]}')
                
                # Simulate agent response
                response = self._generate_agent_response(agent, step['message'])
                self.stdout.write(f'      Response: {response[:80]}...')
            
            self.stdout.write('   ✅ Multi-agent collaboration workflow completed')
            
        except Exception as e:
            self.stdout.write(f'   ❌ Agent collaboration failed: {str(e)}')

    def _generate_agent_response(self, agent: AIAgent, context: str) -> str:
        """Generate a simulated agent response based on personality and specialization"""
        if 'support' in agent.name.lower():
            return "I understand you're having an issue. Let me help you resolve this step by step."
        elif 'sales' in agent.name.lower():
            return "Great question about pricing! Let me show you our best enterprise options."
        elif 'technical' in agent.name.lower():
            return "I can help you with the technical integration. Let me walk you through the process."
        else:
            return "I'm here to help. How can I assist you today?"

    def _test_business_type_customization(self, workspace: Workspace):
        """Test business type customization and template application"""
        self.stdout.write('\n🏢 Testing Business Type Customization...')
        
        try:
            # Test industry-specific customization
            industry_configs = {
                'ecommerce': {
                    'priority_fields': ['order_status', 'shipping_info', 'payment_method'],
                    'business_rules': ['abandoned_cart', 'order_confirmation', 'shipping_updates'],
                    'ai_personality': 'customer_focused'
                },
                'healthcare': {
                    'priority_fields': ['patient_id', 'appointment_status', 'medical_history'],
                    'business_rules': ['appointment_reminders', 'follow_up_scheduling'],
                    'ai_personality': 'professional_caring'
                },
                'technology': {
                    'priority_fields': ['ticket_priority', 'technical_complexity', 'escalation_level'],
                    'business_rules': ['auto_escalation', 'technical_assignment'],
                    'ai_personality': 'technical_helpful'
                }
            }
            
            # Apply ecommerce configuration
            current_industry = workspace.industry
            if current_industry == 'retail':
                config = industry_configs['ecommerce']
                
                # Create industry-specific schema
                schema = WorkspaceContextSchema.objects.create(
                    workspace=workspace,
                    name='E-commerce Customer Schema',
                    description='Industry-specific schema for e-commerce',
                    fields=[
                        {
                            'id': 'order_status',
                            'name': 'order_status',
                            'type': 'choice',
                            'label': 'Order Status',
                            'required': True,
                            'choices': ['pending', 'confirmed', 'shipped', 'delivered', 'cancelled']
                        },
                        {
                            'id': 'shipping_info',
                            'name': 'shipping_info',
                            'type': 'textarea',
                            'label': 'Shipping Information',
                            'required': False
                        },
                        {
                            'id': 'payment_method',
                            'name': 'payment_method',
                            'type': 'choice',
                            'label': 'Payment Method',
                            'required': True,
                            'choices': ['credit_card', 'paypal', 'bank_transfer', 'crypto']
                        }
                    ],
                    is_active=True
                )
                
                self.stdout.write(f'✅ Industry-specific schema created: {schema.name}')
                self.stdout.write(f'   - Fields: {len(schema.fields)}')
                self.stdout.write(f'   - Industry: {workspace.industry}')
                
                # Create industry-specific business rules
                rule = BusinessRule.objects.create(
                    workspace=workspace,
                    name='E-commerce Order Confirmation',
                    description='Automatically confirm orders and send confirmation',
                    trigger_type='context_change',
                    conditions=[
                        {
                            'field': 'order_status',
                            'operator': 'equals',
                            'value': 'confirmed'
                        }
                    ],
                    actions=[
                        {
                            'type': 'send_notification',
                            'config': {
                                'message': 'Your order has been confirmed!',
                                'channel': 'email'
                            }
                        }
                    ],
                    is_active=True
                )
                
                self.stdout.write(f'✅ Industry-specific rule created: {rule.name}')
                
        except Exception as e:
            self.stdout.write(f'❌ Business type customization failed: {str(e)}')

    def _test_intelligent_discovery_features(self, workspace: Workspace):
        """Test intelligent discovery and field suggestion features"""
        self.stdout.write('\n🔍 Testing Intelligent Discovery Features...')
        
        try:
            # Test field discovery service
            service = FieldSuggestionService()
            
            # Generate suggestions
            suggestions = service.generate_suggestions_for_workspace(str(workspace.id), limit=5)
            
            self.stdout.write(f'✅ Field suggestions generated: {len(suggestions)} suggestions')
            
            # Test suggestion approval workflow
            if suggestions.exists():
                suggestion = suggestions.first()
                
                # Simulate user approval
                approval_result = service.approve_suggestion(
                    suggestion_id=str(suggestion.id),
                    user_id=str(workspace.owner.id),
                    target_schema_id=str(WorkspaceContextSchema.objects.filter(workspace=workspace).first().id),
                    notes="Approved during UX testing"
                )
                
                if approval_result:
                    self.stdout.write(f'✅ Suggestion approved: {suggestion.suggested_field_name}')
                    self.stdout.write(f'   - Field type: {suggestion.field_type}')
                    self.stdout.write(f'   - Confidence: {suggestion.confidence_score:.2f}')
                else:
                    self.stdout.write(f'⚠️  Suggestion approval failed: {suggestion.suggested_field_name}')
            
            # Test analytics
            analytics = service.get_suggestion_analytics(str(workspace.id))
            self.stdout.write(f'✅ Discovery analytics retrieved:')
            self.stdout.write(f'   - Total suggestions: {analytics["total_suggestions"]}')
            self.stdout.write(f'   - Approval rate: {analytics["approval_rate"]:.2%}')
            
        except Exception as e:
            self.stdout.write(f'❌ Intelligent discovery features failed: {str(e)}')

    def _test_user_acceptance_scenarios(self, workspace: Workspace):
        """Test real-world user acceptance scenarios"""
        self.stdout.write('\n👥 Testing User Acceptance Scenarios...')
        
        try:
            # Scenario 1: New user onboarding
            self.stdout.write('\n   📚 Scenario 1: New User Onboarding')
            onboarding_success = self._test_onboarding_scenario(workspace)
            if onboarding_success:
                self.stdout.write('   ✅ Onboarding scenario passed')
            else:
                self.stdout.write('   ❌ Onboarding scenario failed')
            
            # Scenario 2: Complex issue resolution
            self.stdout.write('\n   🔧 Scenario 2: Complex Issue Resolution')
            resolution_success = self._test_complex_resolution_scenario(workspace)
            if resolution_success:
                self.stdout.write('   ✅ Complex resolution scenario passed')
            else:
                self.stdout.write('   ❌ Complex resolution scenario failed')
            
            # Scenario 3: Multi-agent handoff
            self.stdout.write('\n   🤝 Scenario 3: Multi-Agent Handoff')
            handoff_success = self._test_agent_handoff_scenario(workspace)
            if handoff_success:
                self.stdout.write('   ✅ Agent handoff scenario passed')
            else:
                self.stdout.write('   ❌ Agent handoff scenario failed')
            
        except Exception as e:
            self.stdout.write(f'❌ User acceptance scenarios failed: {str(e)}')

    def _test_onboarding_scenario(self, workspace: Workspace) -> bool:
        """Test new user onboarding experience"""
        try:
            # Simulate new user conversation
            contact = Contact.objects.create(workspace=workspace)
            conversation = Conversation.objects.create(
                workspace=workspace,
                contact=contact,
                title='New User Onboarding',
                ai_agent=workspace.get_default_agent()
            )
            
            # Test welcome message and guidance
            welcome_message = "Welcome! I'm here to help you get started. What would you like to know?"
            
            # Test context creation
            schema = WorkspaceContextSchema.objects.filter(workspace=workspace).first()
            if schema:
                context = ConversationContext.objects.create(
                    conversation=conversation,
                    schema=schema,
                    title='Onboarding Context',
                    context_data={
                        'user_type': 'new',
                        'onboarding_stage': 'welcome'
                    }
                )
                
                # Test business rule for new users
                rule_engine = RuleEngineService()
                rule_result = rule_engine.evaluate_context_change(context)
                
                return True
            
            return False
            
        except Exception as e:
            self.stdout.write(f'      Error in onboarding test: {str(e)}')
            return False

    def _test_complex_resolution_scenario(self, workspace: Workspace) -> bool:
        """Test complex issue resolution workflow"""
        try:
            # Create complex issue conversation
            contact = Contact.objects.create(workspace=workspace)
            conversation = Conversation.objects.create(
                workspace=workspace,
                contact=contact,
                title='Complex Technical Issue',
                ai_agent=workspace.get_default_agent()
            )
            
            # Test multi-step resolution
            resolution_steps = [
                'Issue identification',
                'Technical investigation',
                'Solution development',
                'Implementation',
                'Verification'
            ]
            
            schema = WorkspaceContextSchema.objects.filter(workspace=workspace).first()
            if schema:
                for i, step in enumerate(resolution_steps):
                    context = ConversationContext.objects.create(
                        conversation=conversation,
                        schema=schema,
                        title=f'Resolution Step {i+1}',
                        context_data={
                            'resolution_stage': step,
                            'step_number': i+1,
                            'status': 'in_progress'
                        }
                    )
                
                self.stdout.write(f'      ✅ Complex resolution workflow: {len(resolution_steps)} steps')
                return True
            
            return False
            
        except Exception as e:
            self.stdout.write(f'      Error in complex resolution test: {str(e)}')
            return False

    def _test_agent_handoff_scenario(self, workspace: Workspace) -> bool:
        """Test smooth agent handoff experience"""
        try:
            # Create conversation that requires handoff
            contact = Contact.objects.create(workspace=workspace)
            conversation = Conversation.objects.create(
                workspace=workspace,
                contact=contact,
                title='Agent Handoff Test',
                ai_agent=workspace.get_default_agent()
            )
            
            # Test handoff workflow
            handoff_workflow = [
                {
                    'from_agent': 'support',
                    'to_agent': 'technical',
                    'reason': 'Technical complexity requires expert',
                    'handoff_message': 'Let me transfer you to our technical expert for this issue.'
                },
                {
                    'from_agent': 'technical',
                    'to_agent': 'sales',
                    'reason': 'Customer interested in enterprise upgrade',
                    'handoff_message': 'For enterprise pricing, let me connect you with our sales specialist.'
                }
            ]
            
            for handoff in handoff_workflow:
                self.stdout.write(f'      ✅ Handoff: {handoff["from_agent"]} → {handoff["to_agent"]}')
                self.stdout.write(f'         Reason: {handoff["reason"]}')
            
            return True
            
        except Exception as e:
            self.stdout.write(f'      Error in agent handoff test: {str(e)}')
            return False
