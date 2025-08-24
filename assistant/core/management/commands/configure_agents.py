"""
Management command for configuring AI agents
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from core.models import AIAgent, Workspace
from messaging.agent_configurator import AgentConfigurator


class Command(BaseCommand):
    help = 'Configure AI agents with enhanced customization'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workspace',
            type=str,
            help='Workspace name or ID to configure agents for'
        )
        
        parser.add_argument(
            '--agent',
            type=str,
            help='Agent name or ID to configure'
        )
        
        parser.add_argument(
            '--create-preset',
            type=str,
            choices=['customer_support', 'sales', 'appointment', 'technical', 'general'],
            help='Create a new agent with preset configuration'
        )
        
        parser.add_argument(
            '--agent-name',
            type=str,
            help='Name for new agent (required with --create-preset)'
        )
        
        parser.add_argument(
            '--channel',
            type=str,
            default='website',
            choices=['instagram', 'whatsapp', 'facebook', 'telegram', 'website', 'sms', 'email', 'phone'],
            help='Channel type for agent'
        )
        
        parser.add_argument(
            '--tone',
            type=str,
            choices=['professional', 'friendly', 'casual', 'formal', 'empathetic'],
            help='Agent communication tone'
        )
        
        parser.add_argument(
            '--formality',
            type=str,
            choices=['formal', 'balanced', 'casual'],
            help='Agent formality level'
        )
        
        parser.add_argument(
            '--regenerate-prompt',
            action='store_true',
            help='Regenerate agent prompt based on current configuration'
        )
        
        parser.add_argument(
            '--list-agents',
            action='store_true',
            help='List all agents in workspace'
        )
        
        parser.add_argument(
            '--show-config',
            action='store_true',
            help='Show current agent configuration'
        )

    def handle(self, *args, **options):
        # Get workspace
        workspace = self.get_workspace(options.get('workspace'))
        
        if options.get('list_agents'):
            self.list_agents(workspace)
            return
        
        if options.get('create_preset'):
            self.create_preset_agent(workspace, options)
            return
        
        # Get agent
        agent = self.get_agent(workspace, options.get('agent'))
        
        if options.get('show_config'):
            self.show_agent_config(agent)
            return
        
        # Configure agent
        self.configure_agent(agent, options)

    def get_workspace(self, workspace_identifier):
        """Get workspace by name or ID"""
        if not workspace_identifier:
            workspaces = Workspace.objects.all()
            if workspaces.count() == 1:
                return workspaces.first()
            elif workspaces.count() == 0:
                raise CommandError("No workspaces found")
            else:
                self.stdout.write("Available workspaces:")
                for ws in workspaces:
                    self.stdout.write(f"  - {ws.name} (ID: {ws.id})")
                raise CommandError("Multiple workspaces found. Please specify --workspace")
        
        # Try by name first
        try:
            return Workspace.objects.get(name__iexact=workspace_identifier)
        except Workspace.DoesNotExist:
            pass
        
        # Try by ID
        try:
            return Workspace.objects.get(id=workspace_identifier)
        except Workspace.DoesNotExist:
            raise CommandError(f"Workspace '{workspace_identifier}' not found")

    def get_agent(self, workspace, agent_identifier):
        """Get agent by name or ID"""
        if not agent_identifier:
            agents = AIAgent.objects.filter(workspace=workspace)
            if agents.count() == 0:
                raise CommandError(f"No agents found in workspace '{workspace.name}'")
            elif agents.count() == 1:
                return agents.first()
            else:
                self.stdout.write(f"Available agents in '{workspace.name}':")
                for agent in agents:
                    status = "✅ Active" if agent.is_active else "❌ Inactive"
                    default = " (Default)" if agent.is_default else ""
                    self.stdout.write(f"  - {agent.name} - {status}{default}")
                raise CommandError("Multiple agents found. Please specify --agent")
        
        # Try by name first
        try:
            return AIAgent.objects.get(workspace=workspace, name__iexact=agent_identifier)
        except AIAgent.DoesNotExist:
            pass
        
        # Try by ID
        try:
            return AIAgent.objects.get(workspace=workspace, id=agent_identifier)
        except AIAgent.DoesNotExist:
            raise CommandError(f"Agent '{agent_identifier}' not found in workspace '{workspace.name}'")

    def list_agents(self, workspace):
        """List all agents in workspace"""
        agents = AIAgent.objects.filter(workspace=workspace)
        
        if not agents:
            self.stdout.write(f"No agents found in workspace '{workspace.name}'")
            return
        
        self.stdout.write(self.style.SUCCESS(f"\nAgents in '{workspace.name}':"))
        self.stdout.write("=" * 50)
        
        for agent in agents:
            status = "✅ Active" if agent.is_active else "❌ Inactive"
            default = " (Default)" if agent.is_default else ""
            
            self.stdout.write(f"\n📱 {agent.name} - {status}{default}")
            self.stdout.write(f"   Channel: {agent.get_channel_type_display()}")
            self.stdout.write(f"   ID: {agent.id}")
            
            if agent.description:
                self.stdout.write(f"   Description: {agent.description}")
            
            # Show personality if configured
            personality = agent.personality_config or {}
            if personality:
                self.stdout.write(f"   Personality: {personality.get('tone', 'default')} tone, {personality.get('formality', 'balanced')} formality")

    def create_preset_agent(self, workspace, options):
        """Create agent with preset configuration"""
        preset_type = options['create_preset']
        agent_name = options.get('agent_name')
        
        if not agent_name:
            raise CommandError("--agent-name is required when using --create-preset")
        
        channel = options.get('channel', 'website')
        
        try:
            agent = AgentConfigurator.create_agent_preset(
                workspace=workspace,
                preset_type=preset_type,
                name=agent_name,
                channel_type=channel
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Created {preset_type} agent '{agent_name}' for {channel} channel"
                )
            )
            self.stdout.write(f"   Agent ID: {agent.id}")
            self.stdout.write(f"   Description: {agent.description}")
            
        except Exception as e:
            raise CommandError(f"Failed to create agent: {str(e)}")

    def configure_agent(self, agent, options):
        """Configure existing agent"""
        changes_made = False
        
        # Configure personality
        personality_changes = {}
        if options.get('tone'):
            personality_changes['tone'] = options['tone']
        if options.get('formality'):
            personality_changes['formality'] = options['formality']
        
        if personality_changes:
            current_personality = agent.personality_config or {}
            new_personality = {**current_personality, **personality_changes}
            agent.personality_config = new_personality
            agent.save()
            changes_made = True
            self.stdout.write(f"✅ Updated personality: {personality_changes}")
        
        # Regenerate prompt if requested or if changes were made
        if options.get('regenerate_prompt') or changes_made:
            prompt = AgentConfigurator.generate_custom_prompt(agent, regenerate=True)
            self.stdout.write("✅ Regenerated agent prompt")
            
            if options.get('regenerate_prompt'):
                self.stdout.write("\n📝 Generated Prompt:")
                self.stdout.write("-" * 50)
                self.stdout.write(prompt)
        
        if not changes_made and not options.get('regenerate_prompt'):
            self.stdout.write("No configuration changes specified.")
            self.stdout.write("Use --help to see available options.")

    def show_agent_config(self, agent):
        """Show current agent configuration"""
        self.stdout.write(self.style.SUCCESS(f"\n🤖 Configuration for '{agent.name}':"))
        self.stdout.write("=" * 50)
        
        # Basic info
        self.stdout.write(f"ID: {agent.id}")
        self.stdout.write(f"Workspace: {agent.workspace.name}")
        self.stdout.write(f"Channel: {agent.get_channel_type_display()}")
        self.stdout.write(f"Status: {'✅ Active' if agent.is_active else '❌ Inactive'}")
        self.stdout.write(f"Default: {'Yes' if agent.is_default else 'No'}")
        
        if agent.description:
            self.stdout.write(f"Description: {agent.description}")
        
        # Personality configuration
        personality = agent.personality_config or {}
        if personality:
            self.stdout.write("\n📋 Personality Configuration:")
            for key, value in personality.items():
                self.stdout.write(f"  - {key.replace('_', ' ').title()}: {value}")
        
        # Business context
        business_context = agent.business_context or {}
        if business_context:
            self.stdout.write("\n🏢 Business Context:")
            for key, value in business_context.items():
                if isinstance(value, list):
                    value = ', '.join(value)
                self.stdout.write(f"  - {key.replace('_', ' ').title()}: {value}")
        
        # Channel configuration
        channel_config = agent.channel_specific_config or {}
        if channel_config:
            self.stdout.write("\n📱 Channel Configuration:")
            for key, value in channel_config.items():
                self.stdout.write(f"  - {key.replace('_', ' ').title()}: {value}")
        
        # Custom instructions
        if agent.custom_instructions:
            self.stdout.write(f"\n📝 Custom Instructions:")
            self.stdout.write(agent.custom_instructions)
        
        # Generated prompt
        if agent.generated_prompt:
            self.stdout.write(f"\n🎯 Generated Prompt (v{agent.prompt_version}):")
            self.stdout.write("-" * 50)
            self.stdout.write(agent.generated_prompt)
