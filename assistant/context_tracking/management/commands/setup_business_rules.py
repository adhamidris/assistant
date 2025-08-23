from django.core.management.base import BaseCommand
from core.models import Workspace
from context_tracking.services import RuleEngineService


class Command(BaseCommand):
    help = 'Set up default business rules for existing workspaces'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workspace-id',
            type=str,
            help='Specific workspace ID to set up rules for'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Set up rules for all workspaces'
        )

    def handle(self, *args, **options):
        rule_engine = RuleEngineService()
        
        if options['workspace_id']:
            # Set up rules for specific workspace
            try:
                workspace = Workspace.objects.get(id=options['workspace_id'])
                self.stdout.write(f"Setting up business rules for workspace: {workspace.name}")
                rule_engine.create_default_rules_for_workspace(str(workspace.id))
                self.stdout.write(
                    self.style.SUCCESS(f"Successfully set up business rules for {workspace.name}")
                )
            except Workspace.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Workspace with ID {options['workspace_id']} not found")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error setting up rules: {str(e)}")
                )
        
        elif options['all']:
            # Set up rules for all workspaces
            workspaces = Workspace.objects.all()
            self.stdout.write(f"Setting up business rules for {workspaces.count()} workspaces...")
            
            success_count = 0
            for workspace in workspaces:
                try:
                    self.stdout.write(f"  Setting up rules for: {workspace.name}")
                    rule_engine.create_default_rules_for_workspace(str(workspace.id))
                    success_count += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"  Failed to set up rules for {workspace.name}: {str(e)}")
                    )
            
            self.stdout.write(
                self.style.SUCCESS(f"Successfully set up business rules for {success_count}/{workspaces.count()} workspaces")
            )
        
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Please specify either --workspace-id <id> or --all to set up business rules"
                )
            )
