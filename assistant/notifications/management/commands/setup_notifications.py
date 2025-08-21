"""
Management command to set up default email templates and notification preferences
"""
from django.core.management.base import BaseCommand
from notifications.services import NotificationService
from notifications.models import EmailTemplate, NotificationPreference
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Set up default email templates and notification preferences'

    def handle(self, *args, **options):
        self.stdout.write('Setting up notification system...')
        
        # Create default email templates
        self.stdout.write('Creating default email templates...')
        NotificationService.create_default_email_templates()
        
        # Create notification preferences for existing users
        self.stdout.write('Creating notification preferences for existing users...')
        users = User.objects.all()
        created_count = 0
        
        for user in users:
            preferences, created = NotificationPreference.objects.get_or_create(
                user=user,
                defaults={
                    'email_new_messages': True,
                    'email_appointment_bookings': True,
                    'email_appointment_reminders': True,
                    'email_system_alerts': True,
                    'email_welcome': True,
                    'email_frequency': 'immediate',
                    'quiet_hours_start': '22:00',
                    'quiet_hours_end': '08:00',
                    'timezone': 'UTC'
                }
            )
            if created:
                created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully set up notification system!\n'
                f'- Created default email templates\n'
                f'- Created notification preferences for {created_count} users'
            )
        )
