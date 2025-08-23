from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils.text import slugify
from core.models import Workspace, AIAgent
from context_tracking.models import WorkspaceContextSchema
import uuid


class Command(BaseCommand):
    help = 'Set up a test workspace and AI agent for portal testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workspace-name',
            type=str,
            default='Test Business',
            help='Name for the test workspace'
        )
        parser.add_argument(
            '--agent-name',
            type=str,
            default='Customer Support Bot',
            help='Name for the test AI agent'
        )
        parser.add_argument(
            '--username',
            type=str,
            default='testuser',
            help='Username for the test user'
        )

    def handle(self, *args, **options):
        workspace_name = options['workspace_name']
        agent_name = options['agent_name']
        username = options['username']

        self.stdout.write(f'Setting up test portal for workspace: {workspace_name}')

        # Create or get test user
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@test.com',
                'first_name': 'Test',
                'last_name': 'User',
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
                'assistant_name': 'AI Assistant',
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

        # Create or get test AI agent
        agent, created = AIAgent.objects.get_or_create(
            name=agent_name,
            workspace=workspace,
            defaults={
                'slug': slugify(agent_name),
                'description': 'A helpful AI assistant for customer support',
                'channel_type': 'website',
                'business_context': {
                    'business_type': 'technology',
                    'industry': 'software',
                    'customer_type': 'business',
                    'service_areas': ['support', 'sales', 'general']
                },
                'personality_config': {
                    'tone': 'friendly',
                    'style': 'professional',
                    'empathy_level': 'high',
                    'response_length': 'medium'
                },
                'generated_prompt': f'You are {agent_name}, a helpful AI assistant for {workspace_name}. You help customers with their inquiries in a friendly and professional manner.',
                'custom_instructions': 'Always be helpful, professional, and friendly. If you don\'t know something, say so and offer to connect them with a human.',
                'is_active': True,
                'is_default': True
            }
        )

        if created:
            self.stdout.write(f'✅ Created test AI agent: {agent_name}')
        else:
            self.stdout.write(f'✅ Using existing AI agent: {agent_name}')

        # Create a simple context schema for the workspace
        schema, created = WorkspaceContextSchema.objects.get_or_create(
            name='Customer Support Schema',
            workspace=workspace,
            defaults={
                'description': 'Basic schema for customer support conversations',
                'fields': [
                    {
                        'id': str(uuid.uuid4()),
                        'name': 'customer_issue',
                        'type': 'text',
                        'label': 'Customer Issue',
                        'description': 'Description of the customer\'s problem',
                        'required': True
                    },
                    {
                        'id': str(uuid.uuid4()),
                        'name': 'priority',
                        'type': 'choice',
                        'label': 'Priority Level',
                        'description': 'How urgent this issue is',
                        'required': True,
                        'choices': ['low', 'medium', 'high', 'urgent']
                    },
                    {
                        'id': str(uuid.uuid4()),
                        'name': 'status',
                        'type': 'choice',
                        'label': 'Status',
                        'description': 'Current status of the issue',
                        'required': True,
                        'choices': ['open', 'in_progress', 'resolved', 'closed']
                    }
                ],
                'is_active': True
            }
        )

        if created:
            self.stdout.write(f'✅ Created test context schema: Customer Support Schema')
        else:
            self.stdout.write(f'✅ Using existing context schema: Customer Support Schema')

        # Display portal information
        try:
            portal_slug = workspace.portal_slug
            simple_slug = workspace.get_simple_slug()
            
            self.stdout.write('\n🎉 Test Portal Setup Complete!')
            self.stdout.write('=' * 50)
            self.stdout.write(f'Workspace: {workspace.name}')
            self.stdout.write(f'Workspace ID: {workspace.id}')
            self.stdout.write(f'Portal Slug: {portal_slug}')
            self.stdout.write(f'Simple Slug: {simple_slug}')
            self.stdout.write(f'AI Agent: {agent.name}')
            self.stdout.write(f'Agent Slug: {agent.slug}')
            self.stdout.write('')
            self.stdout.write('🌐 Test URLs:')
            self.stdout.write(f'  - Portal: http://localhost:3000/portal/{simple_slug}/')
            self.stdout.write(f'  - Agent: http://localhost:3000/portal/{simple_slug}/{agent.slug}/')
            self.stdout.write('')
            self.stdout.write('🔧 Backend Test Endpoints:')
            self.stdout.write(f'  - Portal Resolve: http://localhost:8000/api/v1/core/portal-resolve/{simple_slug}/')
            self.stdout.write(f'  - Test Debug: http://localhost:8000/api/v1/core/test-portal/')
            self.stdout.write(f'  - Agents: http://localhost:8000/api/v1/core/workspaces/{workspace.id}/agents/')
            
        except Exception as e:
            self.stdout.write(f'⚠️  Warning: Could not generate portal slug: {e}')
            self.stdout.write(f'   Simple slug fallback: {workspace.get_simple_slug()}')

        self.stdout.write('\n✅ Test portal setup complete!')
