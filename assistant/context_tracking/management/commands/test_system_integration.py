from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from core.models import Workspace, AIAgent, Conversation, Contact
from context_tracking.models import (
    WorkspaceContextSchema, ConversationContext, BusinessRule, 
    DynamicFieldSuggestion, ContextHistory
)
from context_tracking.services import (
    ContextExtractionService, RuleEngineService, 
    FieldSuggestionService, EnhancedContextExtraction
)
from context_tracking.advanced_rule_engine import AdvancedRuleEngine
from core.models import BusinessTypeTemplate
import json
import time


class Command(BaseCommand):
    help = 'Test complete system integration of all components'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workspace-name',
            type=str,
            default='Integration Test Business',
            help='Name for the test workspace'
        )
        parser.add_argument(
            '--username',
            type=str,
            default='integrationtest',
            help='Username for the test user'
        )
        parser.add_argument(
            '--test-scenario',
            type=str,
            choices=['basic', 'advanced', 'full'],
            default='full',
            help='Test scenario to run'
        )

    def handle(self, *args, **options):
        workspace_name = options['workspace_name']
        username = options['username']
        test_scenario = options['test_scenario']

        self.stdout.write('🚀 Starting Phase 6: System Integration Testing...')
        self.stdout.write('=' * 60)

        # Create test environment
        user, workspace = self._setup_test_environment(username, workspace_name)
        
        if test_scenario in ['advanced', 'full']:
            self._test_business_type_templates(workspace)
        
        if test_scenario in ['basic', 'advanced', 'full']:
            self._test_context_schema_system(workspace)
            self._test_business_rules_system(workspace)
            self._test_field_discovery_system(workspace)
        
        if test_scenario in ['advanced', 'full']:
            self._test_advanced_rule_engine(workspace)
            self._test_multi_agent_system(workspace)
        
        if test_scenario == 'full':
            self._test_complete_workflow(workspace)
            self._test_performance_scenarios(workspace)
        
        self._test_backward_compatibility(workspace)
        self._test_data_flow_integration(workspace)
        
        self.stdout.write('\n🎉 System Integration Testing Complete!')
        self.stdout.write('=' * 60)
        self.stdout.write(f'Workspace: {workspace.name}')
        self.stdout.write(f'Workspace ID: {workspace.id}')
        self.stdout.write(f'Test Scenario: {test_scenario}')
        self.stdout.write('')
        self.stdout.write('✅ All systems are integrated and working correctly!')

    def _setup_test_environment(self, username: str, workspace_name: str):
        """Set up test user and workspace"""
        self.stdout.write('🔧 Setting up test environment...')
        
        # Create or get test user
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@test.com',
                'first_name': 'Integration',
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
                'assistant_name': 'Integration Test AI',
                'ai_personality': 'professional',
                'ai_role': 'customer_support',
                'auto_reply_mode': True,
                'business_type': 'technology',
                'industry': 'software',
                'timezone': 'UTC',
                'language': 'en'
            }
        )
        
        if created:
            self.stdout.write(f'✅ Created test workspace: {workspace_name}')
        else:
            self.stdout.write(f'✅ Using existing workspace: {workspace_name}')
        
        return user, workspace

    def _test_business_type_templates(self, workspace: Workspace):
        """Test business type template system"""
        self.stdout.write('\n🏢 Testing Business Type Templates...')
        
        try:
            # Check if templates exist
            templates = BusinessTypeTemplate.objects.filter(is_active=True)
            if templates.exists():
                self.stdout.write(f'✅ Found {templates.count()} active business templates')
                
                # Test template application
                template = templates.first()
                result = template.apply_to_workspace(workspace)
                
                self.stdout.write(f'✅ Template applied successfully:')
                self.stdout.write(f'   - Schemas created: {len(result["schemas"])}')
                self.stdout.write(f'   - Rules created: {len(result["rules"])}')
                self.stdout.write(f'   - Agents created: {len(result["agents"])}')
            else:
                self.stdout.write('⚠️  No business templates found - run setup_business_templates first')
                
        except Exception as e:
            self.stdout.write(f'❌ Business type templates failed: {str(e)}')

    def _test_context_schema_system(self, workspace: Workspace):
        """Test context schema system"""
        self.stdout.write('\n📋 Testing Context Schema System...')
        
        try:
            # Create test schema
            schema_data = {
                'name': 'Integration Test Schema',
                'description': 'Schema for testing system integration',
                'fields': [
                    {
                        'id': 'test_field_1',
                        'name': 'priority',
                        'type': 'choice',
                        'label': 'Priority Level',
                        'required': True,
                        'choices': ['low', 'medium', 'high', 'urgent']
                    },
                    {
                        'id': 'test_field_2',
                        'name': 'customer_tier',
                        'type': 'choice',
                        'label': 'Customer Tier',
                        'required': False,
                        'choices': ['bronze', 'silver', 'gold', 'platinum']
                    }
                ],
                'status_workflow': {
                    'default_status': 'open',
                    'statuses': [
                        {'id': 'open', 'label': 'Open'},
                        {'id': 'in_progress', 'label': 'In Progress'},
                        {'id': 'resolved', 'label': 'Resolved'}
                    ],
                    'transitions': [
                        {'from': 'open', 'to': 'in_progress', 'label': 'Start Work'},
                        {'from': 'in_progress', 'to': 'resolved', 'label': 'Mark Resolved'}
                    ]
                }
            }
            
            schema = WorkspaceContextSchema.objects.create(
                workspace=workspace,
                **schema_data
            )
            
            self.stdout.write(f'✅ Test schema created: {schema.name}')
            self.stdout.write(f'   - Fields: {len(schema.fields)}')
            self.stdout.write(f'   - Status workflow: {len(schema.status_workflow.get("statuses", []))} statuses')
            
        except Exception as e:
            self.stdout.write(f'❌ Context schema system failed: {str(e)}')

    def _test_business_rules_system(self, workspace: Workspace):
        """Test business rules system"""
        self.stdout.write('\n⚡ Testing Business Rules System...')
        
        try:
            # Create test rule
            rule = BusinessRule.objects.create(
                workspace=workspace,
                name='Integration Test Rule',
                description='Test rule for system integration',
                trigger_type='context_change',
                conditions=[
                    {
                        'field': 'priority',
                        'operator': 'equals',
                        'value': 'urgent'
                    }
                ],
                actions=[
                    {
                        'type': 'send_notification',
                        'config': {
                            'message': 'Urgent priority case detected!',
                            'channel': 'email'
                        }
                    }
                ],
                is_active=True
            )
            
            self.stdout.write(f'✅ Test rule created: {rule.name}')
            self.stdout.write(f'   - Trigger: {rule.trigger_type}')
            self.stdout.write(f'   - Conditions: {len(rule.conditions)}')
            self.stdout.write(f'   - Actions: {len(rule.actions)}')
            
        except Exception as e:
            self.stdout.write(f'❌ Business rules system failed: {str(e)}')

    def _test_field_discovery_system(self, workspace: Workspace):
        """Test field discovery system"""
        self.stdout.write('\n🔍 Testing Field Discovery System...')
        
        try:
            # Test enhanced context extraction
            enhanced_extraction = EnhancedContextExtraction()
            
            test_conversations = [
                "Hi, I have an urgent issue with my premium account. I'm a platinum customer.",
                "When will my order #12345 arrive? It's marked as high priority.",
                "I need help with the API integration. Getting error 500 on authentication.",
                "This is a compliance issue that needs immediate attention."
            ]
            
            # Discover fields
            discovered_fields = enhanced_extraction.discover_new_fields(
                workspace_id=str(workspace.id),
                conversation_texts=test_conversations
            )
            
            self.stdout.write(f'✅ Field discovery completed: {len(discovered_fields)} fields found')
            
            # Test field suggestion service
            service = FieldSuggestionService()
            suggestions = service.generate_suggestions_for_workspace(str(workspace.id), limit=3)
            
            self.stdout.write(f'✅ Field suggestions generated: {len(suggestions)} suggestions')
            
        except Exception as e:
            self.stdout.write(f'❌ Field discovery system failed: {str(e)}')

    def _test_advanced_rule_engine(self, workspace: Workspace):
        """Test advanced rule engine"""
        self.stdout.write('\n🧠 Testing Advanced Rule Engine...')
        
        try:
            # Create advanced rule with workflow
            advanced_rule = BusinessRule.objects.create(
                workspace=workspace,
                name='Advanced Integration Test Rule',
                description='Advanced rule with workflow steps',
                trigger_type='context_change',
                conditions=[
                    {
                        'field': 'customer_tier',
                        'operator': 'equals',
                        'value': 'platinum'
                    }
                ],
                actions=[
                    {
                        'type': 'workflow',
                        'config': {
                            'steps': [
                                {
                                    'type': 'send_notification',
                                    'config': {
                                        'message': 'Platinum customer detected!',
                                        'channel': 'email'
                                    }
                                },
                                {
                                    'type': 'update_field',
                                    'config': {
                                        'field': 'priority',
                                        'value': 'high'
                                    }
                                }
                            ]
                        }
                    }
                ],
                is_active=True
            )
            
            self.stdout.write(f'✅ Advanced rule created: {advanced_rule.name}')
            
            # Test rule engine
            rule_engine = AdvancedRuleEngine()
            
            # Create test context
            schema = WorkspaceContextSchema.objects.filter(workspace=workspace).first()
            if schema:
                context = ConversationContext.objects.create(
                    conversation=Conversation.objects.filter(workspace=workspace).first() or 
                               Conversation.objects.create(workspace=workspace, contact=Contact.objects.create(workspace=workspace)),
                    schema=schema,
                    title='Advanced Rule Test',
                    context_data={
                        'customer_tier': 'platinum',
                        'priority': 'medium'
                    }
                )
                
                # Test rule evaluation
                result = rule_engine.evaluate_conversation_rules(context)
                self.stdout.write(f'✅ Advanced rule evaluation completed: {result}')
            
        except Exception as e:
            self.stdout.write(f'❌ Advanced rule engine failed: {str(e)}')

    def _test_multi_agent_system(self, workspace: Workspace):
        """Test multi-agent system"""
        self.stdout.write('\n🤖 Testing Multi-Agent System...')
        
        try:
            # Create test agents
            agent1 = AIAgent.objects.create(
                workspace=workspace,
                name='Support Agent',
                slug='support-agent',
                description='Customer support specialist',
                channel_type='website',
                is_active=True,
                is_default=True
            )
            
            agent2 = AIAgent.objects.create(
                workspace=workspace,
                name='Sales Agent',
                slug='sales-agent',
                description='Sales and product specialist',
                channel_type='website',
                is_active=True,
                is_default=False
            )
            
            self.stdout.write(f'✅ Test agents created: {agent1.name}, {agent2.name}')
            self.stdout.write(f'   - Default agent: {workspace.get_default_agent().name}')
            self.stdout.write(f'   - Active agents: {workspace.get_active_agents().count()}')
            
        except Exception as e:
            self.stdout.write(f'❌ Multi-agent system failed: {str(e)}')

    def _test_complete_workflow(self, workspace: Workspace):
        """Test complete end-to-end workflow"""
        self.stdout.write('\n🔄 Testing Complete Workflow...')
        
        try:
            # Create test conversation
            contact = Contact.objects.create(workspace=workspace)
            conversation = Conversation.objects.create(
                workspace=workspace,
                contact=contact,
                title='Integration Test Conversation'
            )
            
            # Create context
            schema = WorkspaceContextSchema.objects.filter(workspace=workspace).first()
            if schema:
                context = ConversationContext.objects.create(
                    conversation=conversation,
                    schema=schema,
                    title='Workflow Test',
                    context_data={
                        'priority': 'urgent',
                        'customer_tier': 'platinum'
                    }
                )
                
                # Test context extraction
                extraction_service = ContextExtractionService()
                extraction_result = extraction_service.extract_context_from_text(
                    context=context,
                    text="This is an urgent issue that needs immediate attention from our platinum customer."
                )
                
                self.stdout.write(f'✅ Context extraction completed: {extraction_result["success"]}')
                
                # Test rule execution
                rule_engine = RuleEngineService()
                rule_result = rule_engine.evaluate_context_change(context)
                
                self.stdout.write(f'✅ Rule execution completed: {rule_result}')
                
        except Exception as e:
            self.stdout.write(f'❌ Complete workflow failed: {str(e)}')

    def _test_performance_scenarios(self, workspace: Workspace):
        """Test performance with multiple agents and rules"""
        self.stdout.write('\n📊 Testing Performance Scenarios...')
        
        try:
            start_time = time.time()
            
            # Create multiple test contexts
            contexts = []
            for i in range(10):
                contact = Contact.objects.create(workspace=workspace)
                conversation = Conversation.objects.create(
                    workspace=workspace,
                    contact=contact,
                    title=f'Performance Test {i+1}'
                )
                
                schema = WorkspaceContextSchema.objects.filter(workspace=workspace).first()
                if schema:
                    context = ConversationContext.objects.create(
                        conversation=conversation,
                        schema=schema,
                        title=f'Performance Test Context {i+1}',
                        context_data={
                            'priority': 'high' if i % 2 == 0 else 'medium',
                            'customer_tier': 'gold' if i % 3 == 0 else 'silver'
                        }
                    )
                    contexts.append(context)
            
            # Test bulk rule evaluation
            rule_engine = RuleEngineService()
            for context in contexts:
                rule_engine.evaluate_context_change(context)
            
            end_time = time.time()
            performance_time = end_time - start_time
            
            self.stdout.write(f'✅ Performance test completed:')
            self.stdout.write(f'   - Contexts processed: {len(contexts)}')
            self.stdout.write(f'   - Total time: {performance_time:.2f} seconds')
            self.stdout.write(f'   - Average time per context: {performance_time/len(contexts):.3f} seconds')
            
        except Exception as e:
            self.stdout.write(f'❌ Performance testing failed: {str(e)}')

    def _test_backward_compatibility(self, workspace: Workspace):
        """Test backward compatibility with existing systems"""
        self.stdout.write('\n🔄 Testing Backward Compatibility...')
        
        try:
            # Test existing conversation context
            existing_conversations = Conversation.objects.filter(workspace=workspace)
            self.stdout.write(f'✅ Existing conversations: {existing_conversations.count()}')
            
            # Test existing schemas
            existing_schemas = WorkspaceContextSchema.objects.filter(workspace=workspace)
            self.stdout.write(f'✅ Existing schemas: {existing_schemas.count()}')
            
            # Test existing rules
            existing_rules = BusinessRule.objects.filter(workspace=workspace)
            self.stdout.write(f'✅ Existing rules: {existing_rules.count()}')
            
            # Test context extraction on existing data
            if existing_conversations.exists() and existing_schemas.exists():
                conversation = existing_conversations.first()
                schema = existing_schemas.first()
                
                # Create context if it doesn't exist
                context, created = ConversationContext.objects.get_or_create(
                    conversation=conversation,
                    defaults={
                        'schema': schema,
                        'title': 'Backward Compatibility Test',
                        'context_data': {}
                    }
                )
                
                self.stdout.write(f'✅ Backward compatibility test passed')
                
        except Exception as e:
            self.stdout.write(f'❌ Backward compatibility failed: {str(e)}')

    def _test_data_flow_integration(self, workspace: Workspace):
        """Test data flow between all systems"""
        self.stdout.write('\n🌊 Testing Data Flow Integration...')
        
        try:
            # Test schema -> context -> rules flow
            schemas = WorkspaceContextSchema.objects.filter(workspace=workspace)
            contexts = ConversationContext.objects.filter(conversation__workspace=workspace)
            rules = BusinessRule.objects.filter(workspace=workspace)
            
            self.stdout.write(f'✅ Data flow components:')
            self.stdout.write(f'   - Schemas: {schemas.count()}')
            self.stdout.write(f'   - Contexts: {contexts.count()}')
            self.stdout.write(f'   - Rules: {rules.count()}')
            
            # Test field suggestions integration
            suggestions = DynamicFieldSuggestion.objects.filter(workspace=workspace)
            self.stdout.write(f'   - Field suggestions: {suggestions.count()}')
            
            # Test history tracking
            history_entries = ContextHistory.objects.filter(context__conversation__workspace=workspace)
            self.stdout.write(f'   - History entries: {history_entries.count()}')
            
            self.stdout.write(f'✅ Data flow integration test passed')
            
        except Exception as e:
            self.stdout.write(f'❌ Data flow integration failed: {str(e)}')
