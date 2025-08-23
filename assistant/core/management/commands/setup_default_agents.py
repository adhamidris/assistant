from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Workspace, AIAgent


class Command(BaseCommand):
    help = 'Create default AI agents for existing workspaces'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Create default agents for all workspaces',
        )
        parser.add_argument(
            '--workspace-id',
            type=str,
            help='Create default agent for specific workspace ID',
        )

    def handle(self, *args, **options):
        if options['workspace_id']:
            # Create for specific workspace
            try:
                workspace = Workspace.objects.get(id=options['workspace_id'])
                self.create_default_agent(workspace)
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created default agent for workspace: {workspace.name}')
                )
            except Workspace.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Workspace with ID {options["workspace_id"]} not found')
                )
        elif options['all']:
            # Create for all workspaces
            workspaces = Workspace.objects.all()
            created_count = 0
            
            for workspace in workspaces:
                if self.create_default_agent(workspace):
                    created_count += 1
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created default agents for {created_count} workspaces')
            )
        else:
            # Create for workspaces without agents
            workspaces_without_agents = Workspace.objects.filter(ai_agents__isnull=True)
            created_count = 0
            
            for workspace in workspaces_without_agents:
                if self.create_default_agent(workspace):
                    created_count += 1
            
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created default agents for {created_count} workspaces')
            )

    def create_default_agent(self, workspace):
        """Create a default AI agent for a workspace"""
        try:
            # Check if workspace already has a default agent
            if workspace.ai_agents.filter(is_default=True).exists():
                self.stdout.write(
                    f'Workspace {workspace.name} already has a default agent, skipping...'
                )
                return False
            
            # Create default agent
            default_agent = AIAgent.objects.create(
                workspace=workspace,
                name=f"{workspace.assistant_name or 'Assistant'}",
                slug="default",
                description=f"Default AI assistant for {workspace.name}",
                channel_type="website",
                is_active=True,
                is_default=True,
                generated_prompt=self.generate_default_prompt(workspace),
                business_context={
                    'workspace_name': workspace.name,
                    'assistant_name': workspace.assistant_name or 'Assistant',
                    'ai_role': getattr(workspace, 'ai_role', 'general'),
                    'ai_personality': getattr(workspace, 'ai_personality', 'professional'),
                    'custom_instructions': getattr(workspace, 'custom_instructions', ''),
                },
                personality_config={
                    'role': getattr(workspace, 'ai_role', 'general'),
                    'personality': getattr(workspace, 'ai_personality', 'professional'),
                    'tone': 'professional',
                    'communication_style': 'helpful_and_informative',
                }
            )
            
            self.stdout.write(
                f'Created default agent "{default_agent.name}" for workspace "{workspace.name}"'
            )
            return True
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to create default agent for workspace {workspace.name}: {str(e)}')
            )
            return False

    def generate_default_prompt(self, workspace):
        """Generate a default AI prompt based on workspace configuration"""
        role = getattr(workspace, 'ai_role', 'general')
        personality = getattr(workspace, 'ai_personality', 'professional')
        custom_instructions = getattr(workspace, 'custom_instructions', '')
        
        # Base prompt template
        base_prompt = f"""You are an AI assistant for {workspace.name}. 

Your role is to help customers with their inquiries and provide excellent service.

Role: {role.replace('_', ' ').title()}
Personality: {personality.title()}
Workspace: {workspace.name}

Please be helpful, professional, and provide accurate information to customers.

{custom_instructions if custom_instructions else ''}

Remember to:
- Be polite and professional
- Ask clarifying questions when needed
- Provide accurate and helpful responses
- Escalate complex issues when appropriate"""
        
        return base_prompt
