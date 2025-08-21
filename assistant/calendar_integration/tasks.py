"""
Celery tasks for calendar integration
"""

from celery import shared_task
from django.utils import timezone
from datetime import datetime, timedelta
import logging

from core.models import Workspace
from .models import Appointment, GoogleCalendarSync
from .google_calendar_service import google_calendar_service

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def sync_appointment_with_google(self, appointment_id, action='create'):
    """
    Sync appointment with Google Calendar
    
    Args:
        appointment_id: UUID of the appointment
        action: 'create', 'update', or 'delete'
    """
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        
        # Check if workspace has Google Calendar integration
        sync_config = getattr(appointment.workspace, 'google_calendar_sync', None)
        if not sync_config or sync_config.sync_status != 'active':
            logger.info(f"No active Google Calendar sync for workspace {appointment.workspace.name}")
            return
        
        success = False
        
        if action == 'create':
            success = google_calendar_service.create_event(appointment)
        elif action == 'update':
            success = google_calendar_service.update_event(appointment)
        elif action == 'delete':
            success = google_calendar_service.delete_event(appointment)
        
        if success:
            logger.info(f"Successfully {action}d appointment {appointment_id} in Google Calendar")
        else:
            logger.warning(f"Failed to {action} appointment {appointment_id} in Google Calendar")
            
    except Appointment.DoesNotExist:
        logger.error(f"Appointment {appointment_id} not found")
    except Exception as e:
        logger.error(f"Error syncing appointment {appointment_id} with Google Calendar: {str(e)}")
        
        # Retry task
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=2)
def sync_calendar_events(self, workspace_id):
    """
    Sync all calendar events for a workspace (bidirectional sync)
    
    Args:
        workspace_id: UUID of the workspace
    """
    try:
        workspace = Workspace.objects.get(id=workspace_id)
        sync_config = getattr(workspace, 'google_calendar_sync', None)
        
        if not sync_config or sync_config.sync_status != 'active':
            logger.info(f"No active Google Calendar sync for workspace {workspace.name}")
            return
        
        # Get Google Calendar service
        service = google_calendar_service.get_service(sync_config)
        
        # Sync appointments to Google Calendar
        appointments_to_sync = Appointment.objects.filter(
            workspace=workspace,
            status__in=['scheduled', 'confirmed'],
            start_time__gte=timezone.now() - timedelta(days=1),  # Past day and future
            google_event_id__isnull=True  # Not yet synced
        )
        
        synced_count = 0
        for appointment in appointments_to_sync:
            if google_calendar_service.create_event(appointment):
                synced_count += 1
        
        # Update sync statistics
        sync_config.last_sync_at = timezone.now()
        sync_config.events_synced += synced_count
        sync_config.is_successful = True
        sync_config.error_message = None
        sync_config.save()
        
        logger.info(f"Synced {synced_count} appointments for workspace {workspace.name}")
        
    except Workspace.DoesNotExist:
        logger.error(f"Workspace {workspace_id} not found")
    except Exception as e:
        logger.error(f"Error syncing calendar events for workspace {workspace_id}: {str(e)}")
        
        # Update sync config with error
        try:
            workspace = Workspace.objects.get(id=workspace_id)
            sync_config = getattr(workspace, 'google_calendar_sync', None)
            if sync_config:
                sync_config.is_successful = False
                sync_config.error_message = str(e)
                sync_config.error_count += 1
                sync_config.save()
        except:
            pass
        
        # Retry task
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (self.request.retries + 1))


@shared_task
def send_appointment_reminders():
    """
    Send appointment reminders via email/SMS
    """
    try:
        # Get appointments that need reminders
        reminder_time = timezone.now() + timedelta(minutes=15)  # 15 minutes from now
        
        appointments_needing_reminders = Appointment.objects.filter(
            start_time__lte=reminder_time,
            start_time__gte=timezone.now(),
            status__in=['scheduled', 'confirmed'],
            email_reminder=True
        ).select_related('contact', 'workspace')
        
        reminder_count = 0
        
        for appointment in appointments_needing_reminders:
            # Send email reminder (implement email service)
            if appointment.customer_email:
                # TODO: Implement email reminder service
                logger.info(f"Would send email reminder for appointment {appointment.id}")
                reminder_count += 1
            
            # Send SMS reminder if phone number available
            if appointment.contact.phone_e164:
                # TODO: Implement SMS reminder service
                logger.info(f"Would send SMS reminder for appointment {appointment.id}")
        
        logger.info(f"Processed {reminder_count} appointment reminders")
        
    except Exception as e:
        logger.error(f"Error sending appointment reminders: {str(e)}")


@shared_task
def cleanup_old_appointments():
    """
    Clean up old completed/cancelled appointments
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=90)  # 3 months old
        
        # Archive old completed appointments
        old_appointments = Appointment.objects.filter(
            end_time__lt=cutoff_date,
            status__in=['completed', 'cancelled', 'no_show']
        )
        
        count = old_appointments.count()
        
        # Instead of deleting, we could archive them
        # For now, we'll just log what would be cleaned up
        logger.info(f"Found {count} old appointments that could be archived")
        
        return count
        
    except Exception as e:
        logger.error(f"Error cleaning up old appointments: {str(e)}")
        return 0


@shared_task(bind=True, max_retries=2)
def refresh_google_calendar_token(self, workspace_id):
    """
    Refresh Google Calendar access token for a workspace
    
    Args:
        workspace_id: UUID of the workspace
    """
    try:
        workspace = Workspace.objects.get(id=workspace_id)
        sync_config = getattr(workspace, 'google_calendar_sync', None)
        
        if not sync_config:
            logger.info(f"No Google Calendar sync config for workspace {workspace.name}")
            return
        
        if not sync_config.needs_refresh:
            logger.info(f"Token for workspace {workspace.name} does not need refresh yet")
            return
        
        # Refresh token using Google Calendar service
        try:
            service = google_calendar_service.get_service(sync_config)
            logger.info(f"Successfully refreshed token for workspace {workspace.name}")
            
        except Exception as refresh_error:
            logger.error(f"Failed to refresh token for workspace {workspace.name}: {str(refresh_error)}")
            
            # Mark sync as having error
            sync_config.sync_status = 'error'
            sync_config.error_message = f"Token refresh failed: {str(refresh_error)}"
            sync_config.error_count += 1
            sync_config.save()
            
    except Workspace.DoesNotExist:
        logger.error(f"Workspace {workspace_id} not found for token refresh")
    except Exception as e:
        logger.error(f"Error refreshing Google Calendar token for workspace {workspace_id}: {str(e)}")
        
        # Retry task
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=300)  # 5 minutes


@shared_task
def periodic_calendar_sync():
    """
    Periodic task to sync all active Google Calendar integrations
    """
    try:
        # Get all workspaces with active Google Calendar sync
        active_syncs = GoogleCalendarSync.objects.filter(
            sync_status='active'
        ).select_related('workspace')
        
        for sync_config in active_syncs:
            # Check if token needs refresh
            if sync_config.needs_refresh:
                refresh_google_calendar_token.delay(str(sync_config.workspace.id))
            
            # Trigger calendar sync
            sync_calendar_events.delay(str(sync_config.workspace.id))
        
        logger.info(f"Triggered periodic sync for {active_syncs.count()} workspaces")
        
    except Exception as e:
        logger.error(f"Error in periodic calendar sync: {str(e)}")

