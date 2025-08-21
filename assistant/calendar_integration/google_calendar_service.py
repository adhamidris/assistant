"""
Google Calendar API integration service
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from django.conf import settings
from django.utils import timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json

from .models import GoogleCalendarSync, Appointment

logger = logging.getLogger(__name__)


class GoogleCalendarService:
    """Service for managing Google Calendar integration"""
    
    SCOPES = [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/calendar.events'
    ]
    
    def __init__(self):
        self.client_config = {
            'web': {
                'client_id': settings.GOOGLE_OAUTH_CLIENT_ID,
                'client_secret': settings.GOOGLE_OAUTH_CLIENT_SECRET,
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'redirect_uris': [f"{settings.ALLOWED_HOSTS[0]}/api/v1/calendar/oauth/callback/"]
            }
        }
    
    def get_authorization_url(self, workspace_id: str) -> str:
        """
        Generate Google OAuth authorization URL
        
        Args:
            workspace_id: Workspace ID for state parameter
            
        Returns:
            Authorization URL
        """
        try:
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.SCOPES,
                redirect_uri=self.client_config['web']['redirect_uris'][0]
            )
            
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                state=workspace_id,
                prompt='consent'  # Force consent to get refresh token
            )
            
            return auth_url
            
        except Exception as e:
            logger.error(f"Error generating authorization URL: {str(e)}")
            raise
    
    def handle_oauth_callback(self, code: str, state: str) -> Tuple[bool, str]:
        """
        Handle OAuth callback and save credentials
        
        Args:
            code: Authorization code from Google
            state: Workspace ID
            
        Returns:
            Tuple of (success, message)
        """
        try:
            from core.models import Workspace
            
            workspace = Workspace.objects.get(id=state)
            
            # Exchange code for tokens
            flow = Flow.from_client_config(
                self.client_config,
                scopes=self.SCOPES,
                redirect_uri=self.client_config['web']['redirect_uris'][0]
            )
            
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Build calendar service to get calendar info
            service = build('calendar', 'v3', credentials=credentials)
            
            # Get primary calendar
            calendar_list = service.calendarList().list().execute()
            primary_calendar = None
            
            for calendar_item in calendar_list.get('items', []):
                if calendar_item.get('primary', False):
                    primary_calendar = calendar_item
                    break
            
            if not primary_calendar:
                return False, "No primary calendar found"
            
            # Save or update sync configuration
            sync_config, created = GoogleCalendarSync.objects.update_or_create(
                workspace=workspace,
                defaults={
                    'google_calendar_id': primary_calendar['id'],
                    'access_token': credentials.token,
                    'refresh_token': credentials.refresh_token,
                    'token_expires_at': credentials.expiry,
                    'calendar_name': primary_calendar.get('summary', 'Primary'),
                    'calendar_description': primary_calendar.get('description', ''),
                    'sync_status': 'active',
                    'is_successful': True,
                    'error_message': None,
                    'error_count': 0
                }
            )
            
            action = "created" if created else "updated"
            logger.info(f"Google Calendar sync {action} for workspace {workspace.name}")
            
            return True, f"Google Calendar successfully connected for {workspace.name}"
            
        except Exception as e:
            logger.error(f"Error handling OAuth callback: {str(e)}")
            return False, f"Error connecting to Google Calendar: {str(e)}"
    
    def get_service(self, sync_config: GoogleCalendarSync):
        """
        Get authenticated Google Calendar service
        
        Args:
            sync_config: GoogleCalendarSync instance
            
        Returns:
            Google Calendar service instance
        """
        try:
            credentials = Credentials(
                token=sync_config.access_token,
                refresh_token=sync_config.refresh_token,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
                client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET
            )
            
            # Refresh token if needed
            if sync_config.needs_refresh:
                credentials.refresh(Request())
                
                # Update stored tokens
                sync_config.access_token = credentials.token
                sync_config.token_expires_at = credentials.expiry
                sync_config.save()
            
            return build('calendar', 'v3', credentials=credentials)
            
        except Exception as e:
            logger.error(f"Error getting Calendar service: {str(e)}")
            sync_config.sync_status = 'error'
            sync_config.error_message = str(e)
            sync_config.error_count += 1
            sync_config.save()
            raise
    
    def create_event(self, appointment: Appointment) -> bool:
        """
        Create Google Calendar event from appointment
        
        Args:
            appointment: Appointment instance
            
        Returns:
            Success status
        """
        try:
            sync_config = appointment.workspace.google_calendar_sync
            if not sync_config or sync_config.sync_status != 'active':
                return False
            
            service = self.get_service(sync_config)
            
            # Prepare event data
            event_data = {
                'summary': appointment.title,
                'description': self._build_event_description(appointment),
                'start': {
                    'dateTime': appointment.start_time.isoformat(),
                    'timeZone': str(timezone.get_current_timezone()),
                },
                'end': {
                    'dateTime': appointment.end_time.isoformat(),
                    'timeZone': str(timezone.get_current_timezone()),
                },
                'attendees': [],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': appointment.reminder_minutes_before},
                    ],
                },
            }
            
            # Add customer email if available
            if appointment.customer_email:
                event_data['attendees'].append({
                    'email': appointment.customer_email,
                    'displayName': appointment.contact.name or 'Customer'
                })
            
            # Add location based on type
            if appointment.location_type == 'video_call':
                event_data['conferenceData'] = {
                    'createRequest': {
                        'requestId': str(appointment.id),
                        'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                    }
                }
            elif appointment.location_details:
                event_data['location'] = appointment.location_details
            
            # Create event
            event = service.events().insert(
                calendarId=sync_config.google_calendar_id,
                body=event_data,
                conferenceDataVersion=1 if appointment.location_type == 'video_call' else 0
            ).execute()
            
            # Update appointment with Google event details
            appointment.google_event_id = event['id']
            appointment.google_calendar_id = sync_config.google_calendar_id
            
            # Extract Google Meet link if available
            if event.get('conferenceData') and event['conferenceData'].get('entryPoints'):
                for entry_point in event['conferenceData']['entryPoints']:
                    if entry_point.get('entryPointType') == 'video':
                        appointment.google_meet_link = entry_point.get('uri')
                        break
            
            appointment.save()
            
            logger.info(f"Created Google Calendar event for appointment {appointment.id}")
            return True
            
        except HttpError as e:
            logger.error(f"Google Calendar API error creating event: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error creating Google Calendar event: {str(e)}")
            return False
    
    def update_event(self, appointment: Appointment) -> bool:
        """
        Update Google Calendar event from appointment
        
        Args:
            appointment: Appointment instance
            
        Returns:
            Success status
        """
        try:
            if not appointment.google_event_id:
                return self.create_event(appointment)
            
            sync_config = appointment.workspace.google_calendar_sync
            if not sync_config or sync_config.sync_status != 'active':
                return False
            
            service = self.get_service(sync_config)
            
            # Get existing event
            event = service.events().get(
                calendarId=sync_config.google_calendar_id,
                eventId=appointment.google_event_id
            ).execute()
            
            # Update event data
            event.update({
                'summary': appointment.title,
                'description': self._build_event_description(appointment),
                'start': {
                    'dateTime': appointment.start_time.isoformat(),
                    'timeZone': str(timezone.get_current_timezone()),
                },
                'end': {
                    'dateTime': appointment.end_time.isoformat(),
                    'timeZone': str(timezone.get_current_timezone()),
                },
            })
            
            # Update event
            service.events().update(
                calendarId=sync_config.google_calendar_id,
                eventId=appointment.google_event_id,
                body=event
            ).execute()
            
            logger.info(f"Updated Google Calendar event for appointment {appointment.id}")
            return True
            
        except HttpError as e:
            logger.error(f"Google Calendar API error updating event: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error updating Google Calendar event: {str(e)}")
            return False
    
    def delete_event(self, appointment: Appointment) -> bool:
        """
        Delete Google Calendar event
        
        Args:
            appointment: Appointment instance
            
        Returns:
            Success status
        """
        try:
            if not appointment.google_event_id:
                return True  # Already deleted or never created
            
            sync_config = appointment.workspace.google_calendar_sync
            if not sync_config:
                return True
            
            service = self.get_service(sync_config)
            
            # Delete event
            service.events().delete(
                calendarId=sync_config.google_calendar_id,
                eventId=appointment.google_event_id
            ).execute()
            
            # Clear Google event details from appointment
            appointment.google_event_id = None
            appointment.google_calendar_id = None
            appointment.google_meet_link = None
            appointment.save()
            
            logger.info(f"Deleted Google Calendar event for appointment {appointment.id}")
            return True
            
        except HttpError as e:
            if e.resp.status == 404:
                # Event already deleted
                return True
            logger.error(f"Google Calendar API error deleting event: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error deleting Google Calendar event: {str(e)}")
            return False
    
    def get_available_slots(self, workspace, start_date: datetime, end_date: datetime, duration_minutes: int = 30) -> List[Dict]:
        """
        Get available time slots from Google Calendar
        
        Args:
            workspace: Workspace instance
            start_date: Start date for availability check
            end_date: End date for availability check
            duration_minutes: Required slot duration
            
        Returns:
            List of available time slots
        """
        try:
            sync_config = getattr(workspace, 'google_calendar_sync', None)
            if not sync_config or sync_config.sync_status != 'active':
                return []
            
            service = self.get_service(sync_config)
            
            # Get busy times from Google Calendar
            freebusy_request = {
                'timeMin': start_date.isoformat(),
                'timeMax': end_date.isoformat(),
                'items': [{'id': sync_config.google_calendar_id}]
            }
            
            freebusy_result = service.freebusy().query(body=freebusy_request).execute()
            busy_times = freebusy_result['calendars'][sync_config.google_calendar_id]['busy']
            
            # Convert busy times to datetime objects
            busy_periods = []
            for busy_time in busy_times:
                start = datetime.fromisoformat(busy_time['start'].replace('Z', '+00:00'))
                end = datetime.fromisoformat(busy_time['end'].replace('Z', '+00:00'))
                busy_periods.append((start, end))
            
            # Generate available slots
            available_slots = []
            current_time = start_date
            slot_duration = timedelta(minutes=duration_minutes)
            
            while current_time + slot_duration <= end_date:
                slot_end = current_time + slot_duration
                
                # Check if slot conflicts with busy times
                is_available = True
                for busy_start, busy_end in busy_periods:
                    if (current_time < busy_end and slot_end > busy_start):
                        is_available = False
                        break
                
                if is_available:
                    available_slots.append({
                        'start_time': current_time,
                        'end_time': slot_end,
                        'duration_minutes': duration_minutes
                    })
                
                current_time += timedelta(minutes=15)  # 15-minute increments
            
            return available_slots
            
        except Exception as e:
            logger.error(f"Error getting available slots: {str(e)}")
            return []
    
    def _build_event_description(self, appointment: Appointment) -> str:
        """Build event description from appointment details"""
        description_parts = []
        
        if appointment.description:
            description_parts.append(appointment.description)
        
        description_parts.append(f"Customer: {appointment.contact.name or 'Unknown'}")
        
        if appointment.contact.phone_e164:
            description_parts.append(f"Phone: {appointment.contact.phone_e164}")
        
        if appointment.customer_email:
            description_parts.append(f"Email: {appointment.customer_email}")
        
        if appointment.customer_notes:
            description_parts.append(f"Notes: {appointment.customer_notes}")
        
        if appointment.location_type != 'video_call' and appointment.location_details:
            description_parts.append(f"Location: {appointment.location_details}")
        
        return "\n\n".join(description_parts)


# Global service instance
google_calendar_service = GoogleCalendarService()

