"""
API views for notification management
"""
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer
from django.shortcuts import get_object_or_404
from .models import Notification, NotificationPreference, EmailTemplate
from .services import NotificationService

class NotificationSerializer(ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'title', 'message', 
            'is_read', 'is_sent', 'sent_at', 'created_at',
            'related_conversation', 'related_appointment'
        ]

class NotificationPreferenceSerializer(ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            'email_new_messages', 'email_appointment_bookings', 
            'email_appointment_reminders', 'email_system_alerts',
            'email_welcome', 'email_frequency', 'quiet_hours_start',
            'quiet_hours_end', 'timezone'
        ]

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for notification management"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        success = NotificationService.mark_notification_as_read(notification.id, request.user)
        
        if success:
            return Response({'status': 'Notification marked as read'})
        else:
            return Response(
                {'error': 'Failed to mark notification as read'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Mark all notifications as read"""
        unread_notifications = Notification.objects.filter(
            user=request.user, 
            is_read=False
        )
        unread_notifications.update(is_read=True)
        
        return Response({
            'status': f'Marked {unread_notifications.count()} notifications as read'
        })
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get count of unread notifications"""
        count = Notification.objects.filter(
            user=request.user, 
            is_read=False
        ).count()
        
        return Response({'unread_count': count})

@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def notification_preferences(request):
    """Get or update notification preferences"""
    if request.method == 'GET':
        preferences, created = NotificationPreference.objects.get_or_create(
            user=request.user
        )
        serializer = NotificationPreferenceSerializer(preferences)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        preferences, created = NotificationPreference.objects.get_or_create(
            user=request.user
        )
        serializer = NotificationPreferenceSerializer(
            preferences, 
            data=request.data, 
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(
                serializer.errors, 
                status=status.HTTP_400_BAD_REQUEST
            )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_notification(request):
    """Send a test notification"""
    try:
        notification_type = request.data.get('type', 'system_alert')
        title = request.data.get('title', 'Test Notification')
        message = request.data.get('message', 'This is a test notification.')
        
        notification = NotificationService.create_notification(
            user=request.user,
            notification_type=notification_type,
            title=title,
            message=message
        )
        
        if notification:
            return Response({
                'status': 'Test notification sent successfully',
                'notification_id': str(notification.id)
            })
        else:
            return Response(
                {'error': 'Failed to send test notification'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    except Exception as e:
        return Response(
            {'error': f'Failed to send test notification: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def email_templates(request):
    """Get email templates"""
    templates = EmailTemplate.objects.filter(is_active=True)
    data = []
    
    for template in templates:
        data.append({
            'template_type': template.template_type,
            'subject': template.subject,
            'html_content': template.html_content,
            'text_content': template.text_content
        })
    
    return Response(data)
