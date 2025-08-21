"""
Calendar integration API views
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
import logging

from core.models import Workspace, Contact
from .models import Appointment, AvailabilitySlot, GoogleCalendarSync
from .serializers import (
    AppointmentSerializer, 
    AvailabilitySlotSerializer,
    AppointmentBookingSerializer,
    AvailableSlotSerializer
)
from .google_calendar_service import google_calendar_service
from .tasks import sync_appointment_with_google, sync_calendar_events

logger = logging.getLogger(__name__)


class AppointmentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing appointments"""
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Appointment.objects.all()
        workspace = getattr(self.request, 'workspace', None)
        
        if workspace:
            queryset = queryset.filter(workspace=workspace)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
                queryset = queryset.filter(start_time__gte=start_dt)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
                queryset = queryset.filter(start_time__lte=end_dt)
            except ValueError:
                pass
        
        return queryset.select_related('workspace', 'contact').order_by('start_time')
    
    def perform_create(self, serializer):
        workspace = getattr(self.request, 'workspace', None)
        appointment = serializer.save(workspace=workspace)
        
        # Trigger Google Calendar sync
        sync_appointment_with_google.delay(str(appointment.id), 'create')
    
    def perform_update(self, serializer):
        appointment = serializer.save()
        
        # Trigger Google Calendar sync
        sync_appointment_with_google.delay(str(appointment.id), 'update')
    
    def perform_destroy(self, instance):
        # Trigger Google Calendar sync for deletion
        sync_appointment_with_google.delay(str(instance.id), 'delete')
        instance.delete()
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Confirm an appointment"""
        appointment = self.get_object()
        appointment.status = 'confirmed'
        appointment.save()
        
        # Sync with Google Calendar
        sync_appointment_with_google.delay(str(appointment.id), 'update')
        
        return Response({'status': 'confirmed'})
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancel an appointment"""
        appointment = self.get_object()
        appointment.status = 'cancelled'
        appointment.save()
        
        # Sync with Google Calendar
        sync_appointment_with_google.delay(str(appointment.id), 'update')
        
        return Response({'status': 'cancelled'})
    
    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming appointments"""
        workspace = getattr(request, 'workspace', None)
        if not workspace:
            return Response({'error': 'Workspace context required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        now = timezone.now()
        upcoming = Appointment.objects.filter(
            workspace=workspace,
            start_time__gte=now,
            status__in=['scheduled', 'confirmed']
        ).select_related('contact').order_by('start_time')[:10]
        
        serializer = self.get_serializer(upcoming, many=True)
        return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_available_slots(request):
    """Get available appointment slots for a workspace"""
    workspace_id = request.query_params.get('workspace_id')
    start_date_str = request.query_params.get('start_date')
    end_date_str = request.query_params.get('end_date')
    duration_minutes = int(request.query_params.get('duration', 30))
    
    if not all([workspace_id, start_date_str, end_date_str]):
        return Response(
            {'error': 'workspace_id, start_date, and end_date are required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        workspace = get_object_or_404(Workspace, id=workspace_id)
        start_date = datetime.fromisoformat(start_date_str)
        end_date = datetime.fromisoformat(end_date_str)
        
        # Get available slots from Google Calendar
        available_slots = google_calendar_service.get_available_slots(
            workspace, start_date, end_date, duration_minutes
        )
        
        return Response({
            'available_slots': available_slots,
            'total_slots': len(available_slots)
        })
        
    except Exception as e:
        logger.error(f"Error getting available slots: {str(e)}")
        return Response(
            {'error': 'Failed to get available slots'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def book_appointment(request):
    """Book an appointment (for customers)"""
    try:
        # Get required data
        workspace_id = request.data.get('workspace_id')
        phone_number = request.data.get('phone_number')
        title = request.data.get('title', 'Customer Appointment')
        start_time_str = request.data.get('start_time')
        end_time_str = request.data.get('end_time')
        
        if not all([workspace_id, phone_number, start_time_str, end_time_str]):
            return Response(
                {'error': 'workspace_id, phone_number, start_time, and end_time are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        workspace = get_object_or_404(Workspace, id=workspace_id)
        contact, created = Contact.objects.get_or_create(
            workspace=workspace,
            phone_e164=phone_number,
            defaults={'name': request.data.get('customer_name', '')}
        )
        
        # Parse times
        start_time = datetime.fromisoformat(start_time_str)
        end_time = datetime.fromisoformat(end_time_str)
        
        # Create appointment
        appointment = Appointment.objects.create(
            workspace=workspace,
            contact=contact,
            title=title,
            description=request.data.get('description', ''),
            start_time=start_time,
            end_time=end_time,
            location_type=request.data.get('location_type', 'video_call'),
            location_details=request.data.get('location_details', ''),
            customer_email=request.data.get('customer_email'),
            customer_notes=request.data.get('customer_notes', ''),
            status='scheduled'
        )
        
        # Trigger Google Calendar sync
        sync_appointment_with_google.delay(str(appointment.id), 'create')
        
        return Response({
            'appointment_id': str(appointment.id),
            'message': 'Appointment booked successfully',
            'appointment': AppointmentSerializer(appointment).data
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error booking appointment: {str(e)}")
        return Response(
            {'error': 'Failed to book appointment'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def google_calendar_auth(request):
    """Start Google Calendar OAuth flow"""
    workspace = getattr(request, 'workspace', None)
    if not workspace:
        return Response(
            {'error': 'Workspace context required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        auth_url = google_calendar_service.get_authorization_url(str(workspace.id))
        return Response({'auth_url': auth_url})
        
    except Exception as e:
        logger.error(f"Error starting Google Calendar auth: {str(e)}")
        return Response(
            {'error': 'Failed to start authorization'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def google_calendar_callback(request):
    """Handle Google Calendar OAuth callback"""
    code = request.query_params.get('code')
    state = request.query_params.get('state')  # workspace_id
    error = request.query_params.get('error')
    
    if error:
        return redirect(f'/dashboard?error=calendar_auth_failed&message={error}')
    
    if not code or not state:
        return redirect('/dashboard?error=calendar_auth_failed&message=Missing_parameters')
    
    try:
        success, message = google_calendar_service.handle_oauth_callback(code, state)
        
        if success:
            return redirect(f'/dashboard?success=calendar_connected&message={message}')
        else:
            return redirect(f'/dashboard?error=calendar_auth_failed&message={message}')
            
    except Exception as e:
        logger.error(f"Error handling Google Calendar callback: {str(e)}")
        return redirect(f'/dashboard?error=calendar_auth_failed&message=Unexpected_error')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def calendar_sync_status(request):
    """Get Google Calendar sync status for workspace"""
    workspace = getattr(request, 'workspace', None)
    if not workspace:
        return Response(
            {'error': 'Workspace context required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        sync_config = getattr(workspace, 'google_calendar_sync', None)
        
        if not sync_config:
            return Response({
                'connected': False,
                'status': 'disconnected',
                'message': 'Google Calendar not connected'
            })
        
        return Response({
            'connected': True,
            'status': sync_config.sync_status,
            'calendar_name': sync_config.calendar_name,
            'last_sync_at': sync_config.last_sync_at,
            'error_message': sync_config.error_message,
            'events_synced': sync_config.events_synced
        })
        
    except Exception as e:
        logger.error(f"Error getting calendar sync status: {str(e)}")
        return Response(
            {'error': 'Failed to get sync status'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )