"""
Django management command to set up demo data for the AI Personal Business Assistant.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Workspace, Contact, Session, Conversation
import uuid


class Command(BaseCommand):
    help = 'Set up demo data for testing the application'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--workspace-id',
            type=str,
            default='demo-workspace-123',
            help='Demo workspace ID to create (default: demo-workspace-123)',
        )
    
    def handle(self, *args, **options):
        workspace_id = options['workspace_id']
        
        self.stdout.write(
            self.style.SUCCESS(f'Setting up demo data with workspace ID: {workspace_id}')
        )
        
        # Create demo workspace (convert string to UUID if needed)
        try:
            workspace_uuid = uuid.UUID(workspace_id)
        except ValueError:
            # If not a valid UUID, create one
            workspace_uuid = uuid.uuid4()
            self.stdout.write(
                self.style.WARNING(f'Invalid UUID provided, using generated UUID: {workspace_uuid}')
            )
        
        workspace, created = Workspace.objects.get_or_create(
            id=workspace_uuid,
            defaults={
                'name': 'Demo Business',
                'business_hours': {
                    'monday': {'open': '09:00', 'close': '17:00', 'closed': False},
                    'tuesday': {'open': '09:00', 'close': '17:00', 'closed': False},
                    'wednesday': {'open': '09:00', 'close': '17:00', 'closed': False},
                    'thursday': {'open': '09:00', 'close': '17:00', 'closed': False},
                    'friday': {'open': '09:00', 'close': '17:00', 'closed': False},
                    'saturday': {'open': '10:00', 'close': '14:00', 'closed': False},
                    'sunday': {'open': '10:00', 'close': '14:00', 'closed': True}
                },
                'auto_reply_mode': True,
                'assistant_name': 'Demo Assistant',
                'timezone': 'UTC'
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'✓ Created demo workspace: {workspace.name}')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'✓ Demo workspace already exists: {workspace.name}')
            )
        
        # Create some demo contacts
        demo_contacts = [
            {
                'phone_e164': '+201234567890',
                'name': 'Ahmed Mohamed',
                'email': 'ahmed@example.com'
            },
            {
                'phone_e164': '+201987654321',
                'name': 'Fatma Hassan',
                'email': 'fatma@example.com'
            },
            {
                'phone_e164': '+12345678901',
                'name': 'John Smith',
                'email': 'john@example.com'
            }
        ]
        
        contacts_created = 0
        for contact_data in demo_contacts:
            contact, created = Contact.objects.get_or_create(
                workspace=workspace,
                phone_e164=contact_data['phone_e164'],
                defaults={
                    'name': contact_data['name'],
                    'email': contact_data['email']
                }
            )
            if created:
                contacts_created += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'✓ Created {contacts_created} demo contacts')
        )
        
        # Create demo conversations (need sessions first)
        conversations_created = 0
        for contact in Contact.objects.filter(workspace=workspace)[:2]:
            # Create a session for each contact first
            from core.models import Session
            session, _ = Session.objects.get_or_create(
                contact=contact,
                defaults={
                    'session_token': f'demo_session_{contact.id}',
                    'is_active': True
                }
            )
            
            conversation, created = Conversation.objects.get_or_create(
                workspace=workspace,
                contact=contact,
                session=session,
                defaults={
                    'status': 'active'
                }
            )
            if created:
                conversations_created += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'✓ Created {conversations_created} demo conversations')
        )
        
        self.stdout.write(
            self.style.SUCCESS('🎉 Demo data setup complete!')
        )
        self.stdout.write('')
        self.stdout.write('You can now:')
        self.stdout.write(f'• Use workspace ID: {workspace_id}')
        self.stdout.write('• Test with Egyptian phone numbers like: 01234567890')
        self.stdout.write('• Test with US phone numbers like: (555) 123-4567')
        self.stdout.write('• Access the customer portal at: http://localhost:3000/portal')
        self.stdout.write('• Access the business dashboard at: http://localhost:3000/dashboard')