"""
Management command to set up default context schemas for workspaces
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from core.models import Workspace
from context_tracking.models import WorkspaceContextSchema
from context_tracking.ai_integration import create_default_schemas_for_existing_workspaces


class Command(BaseCommand):
    help = 'Set up default context schemas for existing workspaces'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workspace-id',
            type=str,
            help='Specific workspace ID to set up schema for',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force create schemas even if they already exist',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating',
        )

    def handle(self, *args, **options):
        workspace_id = options['workspace_id']
        force = options['force']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )

        try:
            if workspace_id:
                # Set up schema for specific workspace
                self._setup_workspace_schema(workspace_id, force, dry_run)
            else:
                # Set up schemas for all workspaces
                self._setup_all_workspace_schemas(force, dry_run)

        except Exception as e:
            raise CommandError(f'Command failed: {str(e)}')

    def _setup_workspace_schema(self, workspace_id, force, dry_run):
        """Set up schema for a specific workspace"""
        try:
            workspace = Workspace.objects.get(id=workspace_id)
        except Workspace.DoesNotExist:
            raise CommandError(f'Workspace {workspace_id} not found')

        existing_schemas = WorkspaceContextSchema.objects.filter(workspace=workspace)
        
        if existing_schemas.exists() and not force:
            self.stdout.write(
                self.style.WARNING(
                    f'Workspace {workspace.name} already has {existing_schemas.count()} schema(s). '
                    'Use --force to recreate.'
                )
            )
            return

        if dry_run:
            self.stdout.write(
                f'Would create default schema for workspace: {workspace.name} '
                f'(Industry: {workspace.industry or "Not specified"})'
            )
            return

        with transaction.atomic():
            if force and existing_schemas.exists():
                # Delete existing schemas
                deleted_count = existing_schemas.count()
                existing_schemas.delete()
                self.stdout.write(
                    self.style.WARNING(f'Deleted {deleted_count} existing schema(s)')
                )

            # Create default schema
            schema_config = self._get_schema_config_for_workspace(workspace)
            
            schema = WorkspaceContextSchema.objects.create(
                workspace=workspace,
                name=schema_config['name'],
                description=schema_config['description'],
                fields=schema_config['fields'],
                status_workflow=schema_config['status_workflow'],
                priority_config=schema_config['priority_config'],
                is_default=True,
                is_active=True
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f'Created schema "{schema.name}" for workspace {workspace.name}'
                )
            )

    def _setup_all_workspace_schemas(self, force, dry_run):
        """Set up schemas for all workspaces"""
        
        if force:
            workspaces = Workspace.objects.all()
        else:
            workspaces = Workspace.objects.filter(context_schemas__isnull=True).distinct()

        if not workspaces.exists():
            self.stdout.write(
                self.style.SUCCESS('All workspaces already have schemas')
            )
            return

        self.stdout.write(f'Found {workspaces.count()} workspace(s) to process')

        created_count = 0
        updated_count = 0

        for workspace in workspaces:
            existing_schemas = WorkspaceContextSchema.objects.filter(workspace=workspace)
            
            if existing_schemas.exists() and not force:
                self.stdout.write(
                    f'Skipping {workspace.name} (already has {existing_schemas.count()} schema(s))'
                )
                continue

            if dry_run:
                self.stdout.write(
                    f'Would process workspace: {workspace.name} '
                    f'(Industry: {workspace.industry or "Not specified"})'
                )
                continue

            try:
                with transaction.atomic():
                    if force and existing_schemas.exists():
                        existing_schemas.delete()
                        updated_count += 1
                        action = "Updated"
                    else:
                        created_count += 1
                        action = "Created"

                    # Create default schema
                    schema_config = self._get_schema_config_for_workspace(workspace)
                    
                    schema = WorkspaceContextSchema.objects.create(
                        workspace=workspace,
                        name=schema_config['name'],
                        description=schema_config['description'],
                        fields=schema_config['fields'],
                        status_workflow=schema_config['status_workflow'],
                        priority_config=schema_config['priority_config'],
                        is_default=True,
                        is_active=True
                    )

                    self.stdout.write(
                        f'{action} schema "{schema.name}" for {workspace.name}'
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Failed to create schema for {workspace.name}: {str(e)}'
                    )
                )

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Completed: {created_count} created, {updated_count} updated'
                )
            )

    def _get_schema_config_for_workspace(self, workspace):
        """Get schema configuration based on workspace industry"""
        
        from context_tracking.ai_integration import _get_default_schema_for_industry
        
        # Map AI roles to industries for better schema selection
        role_to_industry_map = {
            'banker': 'financial',
            'medical': 'medical',
            'legal': 'legal',
            'real_estate': 'real_estate',
            'restaurant': 'restaurant',
            'retail': 'retail',
            'tech_support': 'technology',
            'consultant': 'consulting',
            'educator': 'education'
        }
        
        # Use AI role if industry is not set
        industry = workspace.industry
        if not industry and hasattr(workspace, 'ai_role'):
            industry = role_to_industry_map.get(workspace.ai_role)
        
        return _get_default_schema_for_industry(industry)

    def _display_schema_preview(self, schema_config):
        """Display a preview of what schema would be created"""
        self.stdout.write(f"  Name: {schema_config['name']}")
        self.stdout.write(f"  Description: {schema_config['description']}")
        self.stdout.write(f"  Fields: {len(schema_config['fields'])}")
        
        for field in schema_config['fields'][:3]:  # Show first 3 fields
            self.stdout.write(f"    - {field['label']} ({field['type']})")
        
        if len(schema_config['fields']) > 3:
            self.stdout.write(f"    ... and {len(schema_config['fields']) - 3} more")
        
        statuses = schema_config['status_workflow'].get('statuses', [])
        self.stdout.write(f"  Statuses: {', '.join([s['label'] for s in statuses])}")
