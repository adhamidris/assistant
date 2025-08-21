"""
Notification services for sending emails and managing notifications
"""
import logging
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Notification, EmailTemplate, NotificationPreference
from core.models import AppUser

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for managing notifications and sending emails"""
    
    @staticmethod
    def create_notification(user, notification_type, title, message, **kwargs):
        """Create a new notification"""
        try:
            notification = Notification.objects.create(
                user=user,
                notification_type=notification_type,
                title=title,
                message=message,
                related_conversation=kwargs.get('conversation'),
                related_appointment=kwargs.get('appointment')
            )
            
            # Check if user wants immediate email notifications
            preferences = NotificationPreference.objects.filter(user=user).first()
            if preferences and getattr(preferences, f'email_{notification_type}', True):
                NotificationService.send_email_notification(notification)
            
            return notification
        except Exception as e:
            logger.error(f"Failed to create notification: {e}")
            return None
    
    @staticmethod
    def send_email_notification(notification):
        """Send email notification"""
        try:
            # Get user's app profile for personalization
            app_profile = getattr(notification.user, 'app_profile', None)
            business_name = app_profile.business_name if app_profile else "Your Business"
            
            # Get email template
            template = EmailTemplate.objects.filter(
                template_type=notification.notification_type,
                is_active=True
            ).first()
            
            if not template:
                # Use default template
                subject = f"{business_name} - {notification.title}"
                html_content = f"""
                <html>
                <body>
                    <h2>{notification.title}</h2>
                    <p>{notification.message}</p>
                    <hr>
                    <p><small>This is an automated notification from {business_name}</small></p>
                </body>
                </html>
                """
                text_content = f"{notification.title}\n\n{notification.message}\n\nThis is an automated notification from {business_name}"
            else:
                # Use custom template
                subject = template.subject.replace('{business_name}', business_name)
                html_content = template.html_content.replace('{business_name}', business_name)
                html_content = html_content.replace('{title}', notification.title)
                html_content = html_content.replace('{message}', notification.message)
                text_content = template.text_content.replace('{business_name}', business_name)
                text_content = text_content.replace('{title}', notification.title)
                text_content = text_content.replace('{message}', notification.message)
            
            # Send email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[notification.user.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
            # Mark notification as sent
            notification.is_sent = True
            notification.sent_at = timezone.now()
            notification.save()
            
            logger.info(f"Email notification sent to {notification.user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    @staticmethod
    def send_welcome_email(user):
        """Send welcome email to new user"""
        try:
            app_profile = getattr(user, 'app_profile', None)
            business_name = app_profile.business_name if app_profile else "Your Business"
            
            subject = f"Welcome to {business_name} - AI Personal Business Assistant"
            html_content = f"""
            <html>
            <body>
                <h2>Welcome to {business_name}!</h2>
                <p>Thank you for joining our AI Personal Business Assistant platform.</p>
                <p>Here's what you can do:</p>
                <ul>
                    <li>Set up your business profile and AI preferences</li>
                    <li>Generate personalized portal links for your clients</li>
                    <li>Manage conversations and appointments</li>
                    <li>Upload knowledge base documents</li>
                </ul>
                <p>Get started by completing your profile setup!</p>
                <hr>
                <p><small>This is an automated welcome email from {business_name}</small></p>
            </body>
            </html>
            """
            text_content = f"Welcome to {business_name}!\n\nThank you for joining our AI Personal Business Assistant platform.\n\nGet started by completing your profile setup!"
            
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            
            logger.info(f"Welcome email sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send welcome email: {e}")
            return False
    
    @staticmethod
    def send_new_message_notification(user, conversation, message):
        """Send notification for new message"""
        try:
            contact_name = conversation.contact.name or "A client"
            title = f"New message from {contact_name}"
            message_text = f"You have received a new message from {contact_name} in conversation #{conversation.id}."
            
            return NotificationService.create_notification(
                user=user,
                notification_type='new_message',
                title=title,
                message=message_text,
                conversation=conversation
            )
        except Exception as e:
            logger.error(f"Failed to create new message notification: {e}")
            return None
    
    @staticmethod
    def send_appointment_booking_notification(user, appointment):
        """Send notification for appointment booking"""
        try:
            contact_name = appointment.contact.name or "A client"
            title = f"New appointment booking from {contact_name}"
            message_text = f"{contact_name} has booked an appointment for {appointment.start_time.strftime('%B %d, %Y at %I:%M %p')}."
            
            return NotificationService.create_notification(
                user=user,
                notification_type='appointment_booking',
                title=title,
                message=message_text,
                appointment=appointment
            )
        except Exception as e:
            logger.error(f"Failed to create appointment booking notification: {e}")
            return None
    
    @staticmethod
    def send_appointment_reminder_notification(user, appointment):
        """Send appointment reminder notification"""
        try:
            contact_name = appointment.contact.name or "A client"
            title = f"Appointment reminder"
            message_text = f"Reminder: You have an appointment with {contact_name} tomorrow at {appointment.start_time.strftime('%I:%M %p')}."
            
            return NotificationService.create_notification(
                user=user,
                notification_type='appointment_reminder',
                title=title,
                message=message_text,
                appointment=appointment
            )
        except Exception as e:
            logger.error(f"Failed to create appointment reminder notification: {e}")
            return None
    
    @staticmethod
    def mark_notification_as_read(notification_id, user):
        """Mark notification as read"""
        try:
            notification = Notification.objects.get(id=notification_id, user=user)
            notification.is_read = True
            notification.save()
            return True
        except Notification.DoesNotExist:
            return False
    
    @staticmethod
    def get_unread_notifications(user):
        """Get unread notifications for user"""
        return Notification.objects.filter(user=user, is_read=False)
    
    @staticmethod
    def create_default_email_templates():
        """Create default email templates"""
        templates_data = [
            {
                'template_type': 'new_message',
                'subject': '{business_name} - New Message Received',
                'html_content': '''
                <html>
                <body>
                    <h2>New Message Received</h2>
                    <p>You have received a new message from {contact_name}.</p>
                    <p><strong>Message:</strong> {message_preview}</p>
                    <p><a href="{dashboard_url}">View in Dashboard</a></p>
                    <hr>
                    <p><small>This is an automated notification from {business_name}</small></p>
                </body>
                </html>
                ''',
                'text_content': 'New Message Received\n\nYou have received a new message from {contact_name}.\n\nMessage: {message_preview}\n\nView in Dashboard: {dashboard_url}\n\nThis is an automated notification from {business_name}'
            },
            {
                'template_type': 'appointment_booking',
                'subject': '{business_name} - New Appointment Booking',
                'html_content': '''
                <html>
                <body>
                    <h2>New Appointment Booking</h2>
                    <p>{contact_name} has booked an appointment with you.</p>
                    <p><strong>Date:</strong> {appointment_date}</p>
                    <p><strong>Time:</strong> {appointment_time}</p>
                    <p><strong>Notes:</strong> {appointment_notes}</p>
                    <p><a href="{dashboard_url}">View in Dashboard</a></p>
                    <hr>
                    <p><small>This is an automated notification from {business_name}</small></p>
                </body>
                </html>
                ''',
                'text_content': 'New Appointment Booking\n\n{contact_name} has booked an appointment with you.\n\nDate: {appointment_date}\nTime: {appointment_time}\nNotes: {appointment_notes}\n\nView in Dashboard: {dashboard_url}\n\nThis is an automated notification from {business_name}'
            },
            {
                'template_type': 'welcome',
                'subject': 'Welcome to {business_name} - AI Personal Business Assistant',
                'html_content': '''
                <html>
                <body>
                    <h2>Welcome to {business_name}!</h2>
                    <p>Thank you for joining our AI Personal Business Assistant platform.</p>
                    <p>Here's what you can do:</p>
                    <ul>
                        <li>Set up your business profile and AI preferences</li>
                        <li>Generate personalized portal links for your clients</li>
                        <li>Manage conversations and appointments</li>
                        <li>Upload knowledge base documents</li>
                    </ul>
                    <p>Get started by completing your profile setup!</p>
                    <hr>
                    <p><small>This is an automated welcome email from {business_name}</small></p>
                </body>
                </html>
                ''',
                'text_content': 'Welcome to {business_name}!\n\nThank you for joining our AI Personal Business Assistant platform.\n\nGet started by completing your profile setup!\n\nThis is an automated welcome email from {business_name}'
            }
        ]
        
        for template_data in templates_data:
            EmailTemplate.objects.get_or_create(
                template_type=template_data['template_type'],
                defaults=template_data
            )
