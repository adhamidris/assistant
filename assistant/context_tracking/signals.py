from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
import logging

from core.models import Conversation
from messaging.models import Message
from .models import ConversationContext, WorkspaceContextSchema, ContextHistory
from .services import ContextExtractionService, RuleEngineService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Conversation)
def create_conversation_context(sender, instance, created, **kwargs):
    """
    Automatically create a context for new conversations
    """
    if created and not hasattr(instance, '_skip_context_creation'):
        try:
            workspace = instance.workspace
            
            # Get default schema for this workspace
            default_schema = WorkspaceContextSchema.objects.filter(
                workspace=workspace,
                is_default=True,
                is_active=True
            ).first()
            
            # If no default schema, get the first active schema
            if not default_schema:
                default_schema = WorkspaceContextSchema.objects.filter(
                    workspace=workspace,
                    is_active=True
                ).first()
            
            # If still no schema, create a basic one
            if not default_schema:
                default_schema = WorkspaceContextSchema.objects.create(
                    workspace=workspace,
                    name="Default Schema",
                    description="Auto-created default schema",
                    is_default=True,
                    is_active=True,
                    fields=[
                        {
                            "id": "customer_name",
                            "label": "Customer Name",
                            "type": "text",
                            "required": False,
                            "ai_extractable": True,
                            "display_order": 1
                        },
                        {
                            "id": "inquiry_type",
                            "label": "Inquiry Type",
                            "type": "choice",
                            "choices": ["general", "support", "sales", "complaint"],
                            "required": False,
                            "ai_extractable": True,
                            "display_order": 2
                        },
                        {
                            "id": "urgency",
                            "label": "Urgency Level",
                            "type": "choice",
                            "choices": ["low", "medium", "high", "urgent"],
                            "required": False,
                            "ai_extractable": True,
                            "display_order": 3
                        }
                    ],
                    status_workflow={
                        "statuses": [
                            {"id": "new", "label": "New", "color": "blue"},
                            {"id": "in_progress", "label": "In Progress", "color": "yellow"},
                            {"id": "resolved", "label": "Resolved", "color": "green"},
                            {"id": "closed", "label": "Closed", "color": "gray"}
                        ],
                        "transitions": {
                            "new": ["in_progress", "resolved"],
                            "in_progress": ["resolved", "new"],
                            "resolved": ["closed", "in_progress"],
                            "closed": ["in_progress"]
                        }
                    },
                    priority_config={
                        "default_priority": "medium",
                        "rules": [
                            {
                                "conditions": [
                                    {"field": "urgency", "operator": "equals", "value": "urgent"}
                                ],
                                "priority": "urgent"
                            },
                            {
                                "conditions": [
                                    {"field": "urgency", "operator": "equals", "value": "high"}
                                ],
                                "priority": "high"
                            }
                        ]
                    }
                )
            
            # Create the conversation context
            context = ConversationContext.objects.create(
                conversation=instance,
                schema=default_schema,
                title="",  # Will be generated when first message is processed
                context_data={},
                status="new",
                priority="medium"
            )
            
            # Log the creation
            ContextHistory.objects.create(
                context=context,
                action_type='created',
                changed_by_ai=True,
                metadata={
                    'created_via': 'conversation_signal',
                    'schema_id': str(default_schema.id),
                    'auto_created': True
                }
            )
            
            logger.info(f"Created context {context.id} for conversation {instance.id}")
            
        except Exception as e:
            logger.error(f"Failed to create context for conversation {instance.id}: {str(e)}")


@receiver(post_save, sender=Message)
def process_message_for_context(sender, instance, created, **kwargs):
    """
    Process new messages to extract context and trigger rules
    """
    if created and instance.sender == 'client' and instance.message_type == 'text':
        try:
            conversation = instance.conversation
            
            # Get or create context for this conversation
            try:
                context = ConversationContext.objects.get(conversation=conversation)
            except ConversationContext.DoesNotExist:
                # Create context if it doesn't exist (shouldn't happen due to signal above)
                logger.warning(f"No context found for conversation {conversation.id}, creating one")
                create_conversation_context(Conversation, conversation, True)
                context = ConversationContext.objects.get(conversation=conversation)
            
            # Extract context from the message
            if instance.text and len(instance.text.strip()) > 10:  # Only process meaningful messages
                extraction_service = ContextExtractionService()
                
                # Async context extraction to avoid blocking
                from django.db import transaction
                
                def extract_context():
                    try:
                        extraction_service.extract_context_from_text(
                            context=context,
                            text=instance.text,
                            force_extraction=False
                        )
                        
                        # Trigger business rules
                        rule_engine = RuleEngineService()
                        rule_engine.evaluate_new_message(
                            context=context,
                            message_data={
                                'id': str(instance.id),
                                'text': instance.text,
                                'sender': instance.sender,
                                'message_type': instance.message_type,
                                'created_at': instance.created_at.isoformat()
                            }
                        )
                        
                    except Exception as e:
                        logger.error(f"Context extraction failed for message {instance.id}: {str(e)}")
                
                # Schedule extraction after transaction commits
                transaction.on_commit(extract_context)
            
        except Exception as e:
            logger.error(f"Failed to process message {instance.id} for context: {str(e)}")


@receiver(pre_save, sender=ConversationContext)
def track_context_changes(sender, instance, **kwargs):
    """
    Track changes to context fields for history
    """
    if instance.pk:  # Only for updates, not creation
        try:
            # Get the original instance
            original = ConversationContext.objects.get(pk=instance.pk)
            
            # Track status changes
            if original.status != instance.status:
                ContextHistory.objects.create(
                    context=instance,
                    action_type='status_changed',
                    field_name='status',
                    old_value=original.status,
                    new_value=instance.status,
                    changed_by_ai=True,  # Will be updated by view if it's a user change
                    metadata={
                        'auto_tracked': True,
                        'signal_source': 'pre_save'
                    }
                )
            
            # Track priority changes
            if original.priority != instance.priority:
                ContextHistory.objects.create(
                    context=instance,
                    action_type='priority_changed',
                    field_name='priority',
                    old_value=original.priority,
                    new_value=instance.priority,
                    changed_by_ai=True,
                    metadata={
                        'auto_tracked': True,
                        'signal_source': 'pre_save'
                    }
                )
            
            # Track context data changes
            if original.context_data != instance.context_data:
                # Find specific field changes
                original_data = original.context_data or {}
                new_data = instance.context_data or {}
                
                all_fields = set(original_data.keys()) | set(new_data.keys())
                
                for field_id in all_fields:
                    old_value = original_data.get(field_id)
                    new_value = new_data.get(field_id)
                    
                    if old_value != new_value:
                        ContextHistory.objects.create(
                            context=instance,
                            action_type='field_updated',
                            field_name=field_id,
                            old_value=old_value,
                            new_value=new_value,
                            changed_by_ai=True,  # Will be updated by view if it's a user change
                            metadata={
                                'auto_tracked': True,
                                'signal_source': 'pre_save'
                            }
                        )
            
        except ConversationContext.DoesNotExist:
            # Original doesn't exist, this is creation
            pass
        except Exception as e:
            logger.error(f"Failed to track context changes for {instance.id}: {str(e)}")


@receiver(post_save, sender=ConversationContext)
def trigger_business_rules_on_context_change(sender, instance, created, **kwargs):
    """
    Trigger business rules when context changes
    """
    if not created:  # Only for updates
        try:
            rule_engine = RuleEngineService()
            
            # Get the changes from the update_fields if available
            update_fields = kwargs.get('update_fields', set())
            
            if 'status' in update_fields or not update_fields:
                # Status change might have happened
                rule_engine.evaluate_status_change(instance, instance.status)
            
            if 'context_data' in update_fields or not update_fields:
                # Context data might have changed
                rule_engine.evaluate_context_change(instance, instance.context_data)
            
            if 'priority' in update_fields or not update_fields:
                # Priority might have changed - but we need the old value
                # This would be better handled in the view where we have the old value
                pass
            
        except Exception as e:
            logger.error(f"Failed to trigger business rules for context {instance.id}: {str(e)}")


@receiver(post_delete, sender=ConversationContext)
def cleanup_context_history(sender, instance, **kwargs):
    """
    Clean up context history when context is deleted
    """
    try:
        # The history will be automatically deleted due to CASCADE,
        # but we can log this for audit purposes
        logger.info(f"Context {instance.id} deleted, history will be cleaned up automatically")
        
    except Exception as e:
        logger.error(f"Error during context cleanup for {instance.id}: {str(e)}")


@receiver(post_save, sender=WorkspaceContextSchema)
def handle_default_schema_changes(sender, instance, created, **kwargs):
    """
    Ensure only one default schema per workspace
    """
    if instance.is_default:
        try:
            # Unset other default schemas in the same workspace
            WorkspaceContextSchema.objects.filter(
                workspace=instance.workspace,
                is_default=True
            ).exclude(
                id=instance.id
            ).update(is_default=False)
            
            logger.info(f"Set {instance.name} as default schema for workspace {instance.workspace.id}")
            
        except Exception as e:
            logger.error(f"Failed to handle default schema change: {str(e)}")


# Optional: Add a signal to migrate existing conversations when a new default schema is created
@receiver(post_save, sender=WorkspaceContextSchema)
def migrate_existing_conversations_to_new_schema(sender, instance, created, **kwargs):
    """
    Optionally migrate existing conversations to a new default schema
    """
    if created and instance.is_default:
        try:
            # Count conversations without context in this workspace
            from django.db.models import Q
            conversations_without_context = Conversation.objects.filter(
                workspace=instance.workspace
            ).filter(
                Q(dynamic_context__isnull=True) | Q(dynamic_context__schema__is_active=False)
            )
            
            count = conversations_without_context.count()
            if count > 0:
                logger.info(
                    f"Found {count} conversations without active context in workspace {instance.workspace.id}. "
                    f"Consider running migration to apply new schema {instance.name}"
                )
                
                # Optionally auto-migrate (disabled by default to avoid performance issues)
                # from .services import ContextMigrationService
                # migration_service = ContextMigrationService()
                # migration_service.migrate_workspace_conversations(
                #     str(instance.workspace.id), 
                #     str(instance.id)
                # )
            
        except Exception as e:
            logger.error(f"Failed to check for migration opportunities: {str(e)}")


# Signal to create default business rules for new workspaces
@receiver(post_save, sender='core.Workspace')
def create_default_business_rules(sender, instance, created, **kwargs):
    """
    Create default business rules when a new workspace is created
    """
    if created:
        try:
            from .services import RuleEngineService
            rule_engine = RuleEngineService()
            rule_engine.create_default_rules_for_workspace(str(instance.id))
            logger.info(f"Created default business rules for new workspace: {instance.name}")
        except Exception as e:
            logger.error(f"Failed to create default business rules for workspace {instance.id}: {str(e)}")


# Celery task for background context processing (if needed)
def schedule_context_extraction(context_id, message_text):
    """
    Schedule context extraction as a background task
    This can be used for heavy processing without blocking the request
    """
    try:
        from celery import shared_task
        
        @shared_task
        def extract_context_background(context_id, message_text):
            try:
                context = ConversationContext.objects.get(id=context_id)
                extraction_service = ContextExtractionService()
                extraction_service.extract_context_from_text(
                    context=context,
                    text=message_text,
                    force_extraction=False
                )
                logger.info(f"Background context extraction completed for {context_id}")
            except Exception as e:
                logger.error(f"Background context extraction failed for {context_id}: {str(e)}")
        
        # Schedule the task
        extract_context_background.delay(context_id, message_text)
        
    except ImportError:
        # Celery not available, process synchronously
        logger.warning("Celery not available, processing context extraction synchronously")
        extraction_service = ContextExtractionService()
        context = ConversationContext.objects.get(id=context_id)
        extraction_service.extract_context_from_text(
            context=context,
            text=message_text,
            force_extraction=False
        )
