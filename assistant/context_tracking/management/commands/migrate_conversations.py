"""
Management command to migrate existing conversations to dynamic context system
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from core.models import Workspace, Conversation
from context_tracking.models import WorkspaceContextSchema, ConversationContext
from context_tracking.services import ContextMigrationService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Migrate existing conversations to dynamic context system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workspace-id',
            type=str,
            help='Specific workspace ID to migrate conversations for',
        )
        parser.add_argument(
            '--schema-id',
            type=str,
            help='Specific schema ID to use for migration (requires workspace-id)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of conversations to process in each batch',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually migrating',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force migration even if conversations already have context',
        )
        parser.add_argument(
            '--extract-context',
            action='store_true',
            help='Attempt to extract context from existing message content',
        )

    def handle(self, *args, **options):
        workspace_id = options['workspace_id']
        schema_id = options['schema_id']
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        force = options['force']
        extract_context = options['extract_context']

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )

        try:
            if workspace_id:
                if schema_id:
                    # Migrate specific workspace with specific schema
                    self._migrate_workspace_with_schema(
                        workspace_id, schema_id, batch_size, dry_run, force, extract_context
                    )
                else:
                    # Migrate specific workspace with default schema
                    self._migrate_workspace(
                        workspace_id, batch_size, dry_run, force, extract_context
                    )
            else:
                # Migrate all workspaces
                self._migrate_all_workspaces(
                    batch_size, dry_run, force, extract_context
                )

        except Exception as e:
            raise CommandError(f'Migration failed: {str(e)}')

    def _migrate_workspace_with_schema(
        self, workspace_id, schema_id, batch_size, dry_run, force, extract_context
    ):
        """Migrate conversations for a specific workspace with a specific schema"""
        try:
            workspace = Workspace.objects.get(id=workspace_id)
            schema = WorkspaceContextSchema.objects.get(id=schema_id, workspace=workspace)
        except Workspace.DoesNotExist:
            raise CommandError(f'Workspace {workspace_id} not found')
        except WorkspaceContextSchema.DoesNotExist:
            raise CommandError(f'Schema {schema_id} not found in workspace {workspace_id}')

        self.stdout.write(f'Migrating workspace: {workspace.name}')
        self.stdout.write(f'Using schema: {schema.name}')

        conversations = self._get_conversations_to_migrate(workspace, force)
        
        if not conversations.exists():
            self.stdout.write(
                self.style.SUCCESS('No conversations to migrate')
            )
            return

        self.stdout.write(f'Found {conversations.count()} conversations to migrate')

        if dry_run:
            self._preview_migration(conversations[:10])  # Preview first 10
            return

        # Process in batches
        migrated_count = 0
        failed_count = 0

        for i in range(0, conversations.count(), batch_size):
            batch = conversations[i:i + batch_size]
            
            self.stdout.write(f'Processing batch {i//batch_size + 1}...')
            
            for conversation in batch:
                try:
                    with transaction.atomic():
                        self._migrate_single_conversation(
                            conversation, schema, extract_context
                        )
                        migrated_count += 1
                        
                        if migrated_count % 10 == 0:
                            self.stdout.write(f'Migrated {migrated_count} conversations')
                
                except Exception as e:
                    failed_count += 1
                    self.stdout.write(
                        self.style.ERROR(
                            f'Failed to migrate conversation {conversation.id}: {str(e)}'
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f'Migration completed: {migrated_count} migrated, {failed_count} failed'
            )
        )

    def _migrate_workspace(
        self, workspace_id, batch_size, dry_run, force, extract_context
    ):
        """Migrate conversations for a specific workspace using default schema"""
        try:
            workspace = Workspace.objects.get(id=workspace_id)
        except Workspace.DoesNotExist:
            raise CommandError(f'Workspace {workspace_id} not found')

        # Get or create default schema
        schema = WorkspaceContextSchema.objects.filter(
            workspace=workspace, is_default=True, is_active=True
        ).first()

        if not schema:
            self.stdout.write(
                self.style.WARNING(
                    f'No default schema found for workspace {workspace.name}. Creating one...'
                )
            )
            
            if not dry_run:
                # Create default schema
                from context_tracking.ai_integration import _get_default_schema_for_industry
                schema_config = _get_default_schema_for_industry(workspace.industry)
                
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
                    self.style.SUCCESS(f'Created default schema: {schema.name}')
                )
            else:
                self.stdout.write('Would create default schema')
                return

        self._migrate_workspace_with_schema(
            workspace_id, str(schema.id), batch_size, dry_run, force, extract_context
        )

    def _migrate_all_workspaces(
        self, batch_size, dry_run, force, extract_context
    ):
        """Migrate conversations for all workspaces"""
        
        if force:
            workspaces = Workspace.objects.all()
        else:
            # Only workspaces with conversations that don't have context
            workspaces = Workspace.objects.filter(
                conversations__dynamic_context__isnull=True
            ).distinct()

        if not workspaces.exists():
            self.stdout.write(
                self.style.SUCCESS('All conversations already have context')
            )
            return

        self.stdout.write(f'Found {workspaces.count()} workspace(s) with conversations to migrate')

        total_migrated = 0
        total_failed = 0

        for workspace in workspaces:
            self.stdout.write(f'\n--- Processing workspace: {workspace.name} ---')
            
            try:
                # Get conversations to migrate for this workspace
                conversations = self._get_conversations_to_migrate(workspace, force)
                
                if not conversations.exists():
                    self.stdout.write('No conversations to migrate in this workspace')
                    continue

                self.stdout.write(f'Found {conversations.count()} conversations to migrate')

                if dry_run:
                    self._preview_migration(conversations[:3])  # Preview first 3
                    continue

                # Get or create default schema
                schema = self._get_or_create_default_schema(workspace)
                
                if not schema:
                    self.stdout.write(
                        self.style.ERROR(f'Could not get/create schema for {workspace.name}')
                    )
                    continue

                # Migrate conversations
                migration_service = ContextMigrationService()
                result = migration_service.migrate_workspace_conversations(
                    str(workspace.id), str(schema.id)
                )

                migrated = result['migrated_count']
                failed = result['failed_count']
                
                total_migrated += migrated
                total_failed += failed

                self.stdout.write(
                    f'Workspace {workspace.name}: {migrated} migrated, {failed} failed'
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'Failed to process workspace {workspace.name}: {str(e)}'
                    )
                )

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nTotal migration completed: {total_migrated} migrated, {total_failed} failed'
                )
            )

    def _get_conversations_to_migrate(self, workspace, force):
        """Get conversations that need to be migrated"""
        conversations = Conversation.objects.filter(workspace=workspace)
        
        if not force:
            # Only conversations without context
            conversations = conversations.filter(dynamic_context__isnull=True)
        
        return conversations.order_by('created_at')

    def _preview_migration(self, conversations):
        """Preview what would be migrated"""
        self.stdout.write('\nPREVIEW of conversations to migrate:')
        
        for conversation in conversations:
            message_count = conversation.messages.count()
            latest_message = conversation.messages.order_by('-created_at').first()
            
            preview_text = ""
            if latest_message and latest_message.text:
                preview_text = latest_message.text[:100] + "..." if len(latest_message.text) > 100 else latest_message.text
            
            self.stdout.write(
                f'  - {conversation.id}: {message_count} messages, '
                f'created: {conversation.created_at.strftime("%Y-%m-%d %H:%M")}'
            )
            if preview_text:
                self.stdout.write(f'    Latest: "{preview_text}"')

    def _migrate_single_conversation(self, conversation, schema, extract_context):
        """Migrate a single conversation"""
        
        # Check if context already exists
        existing_context = ConversationContext.objects.filter(
            conversation=conversation
        ).first()

        if existing_context:
            # Update schema if different
            if existing_context.schema != schema:
                existing_context.schema = schema
                existing_context.save()
            return existing_context

        # Create new context
        context = ConversationContext.objects.create(
            conversation=conversation,
            schema=schema,
            title=self._generate_title_from_conversation(conversation),
            context_data={},
            status='new',
            priority='medium',
            metadata={
                'migrated_from_legacy': True,
                'migration_date': timezone.now().isoformat(),
                'original_summary': conversation.summary,
                'original_key_points': conversation.key_points,
                'original_action_items': conversation.action_items
            }
        )

        # Map existing conversation data
        self._map_legacy_data(context, conversation)

        # Extract context from messages if requested
        if extract_context:
            self._extract_context_from_messages(context, conversation)

        context.save()
        return context

    def _generate_title_from_conversation(self, conversation):
        """Generate a title from conversation data"""
        
        # Use existing summary if available
        if conversation.summary:
            title = conversation.summary[:100]
            if len(conversation.summary) > 100:
                title += "..."
            return title

        # Use contact information
        if conversation.contact:
            return f"Conversation with {conversation.contact.phone_number}"

        # Use first message
        first_message = conversation.messages.filter(
            sender='client', message_type='text'
        ).first()
        
        if first_message and first_message.text:
            title = first_message.text[:50]
            if len(first_message.text) > 50:
                title += "..."
            return title

        return f"Conversation {str(conversation.id)[:8]}"

    def _map_legacy_data(self, context, conversation):
        """Map legacy conversation data to context"""
        
        # Map sentiment score to priority
        sentiment_score = conversation.sentiment_score
        if sentiment_score <= 2:
            context.priority = 'high'  # Low satisfaction = high priority
        elif sentiment_score >= 4:
            context.priority = 'low'   # High satisfaction = low priority
        else:
            context.priority = 'medium'

        # Map resolution status
        if hasattr(conversation, 'resolution_status'):
            if conversation.resolution_status == 'resolved':
                context.status = 'resolved'
            elif conversation.action_items:
                context.status = 'in_progress'
            else:
                context.status = 'new'

        # Add entities as tags
        if conversation.extracted_entities:
            tags = []
            for entity_type, entity_values in conversation.extracted_entities.items():
                if isinstance(entity_values, list):
                    tags.extend(entity_values[:3])  # Limit to avoid too many tags
                elif isinstance(entity_values, str):
                    tags.append(entity_values)
            
            context.tags = tags[:10]  # Limit to 10 tags

    def _extract_context_from_messages(self, context, conversation):
        """Extract context from conversation messages"""
        try:
            from context_tracking.services import ContextExtractionService
            
            # Get recent messages
            messages = conversation.messages.filter(
                sender='client', message_type='text'
            ).order_by('-created_at')[:5]

            if not messages:
                return

            # Combine message texts
            combined_text = "\n".join([msg.text for msg in messages if msg.text])
            
            if len(combined_text) > 50:  # Only extract if there's meaningful content
                extraction_service = ContextExtractionService()
                extraction_service.extract_context_from_text(
                    context=context,
                    text=combined_text,
                    force_extraction=True
                )

        except Exception as e:
            logger.error(f"Context extraction failed during migration: {str(e)}")

    def _get_or_create_default_schema(self, workspace):
        """Get or create default schema for workspace"""
        
        # Try to get existing default schema
        schema = WorkspaceContextSchema.objects.filter(
            workspace=workspace, is_default=True, is_active=True
        ).first()

        if schema:
            return schema

        # Create default schema
        try:
            from context_tracking.ai_integration import _get_default_schema_for_industry
            schema_config = _get_default_schema_for_industry(workspace.industry)
            
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
                f'Created default schema "{schema.name}" for {workspace.name}'
            )
            return schema

        except Exception as e:
            logger.error(f"Failed to create default schema for {workspace.name}: {str(e)}")
            return None
