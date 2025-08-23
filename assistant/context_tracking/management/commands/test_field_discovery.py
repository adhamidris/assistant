from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Workspace
from context_tracking.services import FieldSuggestionService, EnhancedContextExtraction
from context_tracking.models import DynamicFieldSuggestion


class Command(BaseCommand):
    help = 'Test the field discovery system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workspace-name',
            type=str,
            default='Test Business',
            help='Name for the test workspace'
        )
        parser.add_argument(
            '--username',
            type=str,
            default='testuser',
            help='Username for the test user'
        )

    def handle(self, *args, **options):
        workspace_name = options['workspace_name']
        username = options['username']

        self.stdout.write('Testing field discovery system...')

        # Create or get test user
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@test.com',
                'first_name': 'Test',
                'last_name': 'User',
                'is_staff': True,
                'is_superuser': True
            }
        )

        if created:
            user.set_password('testpass123')
            user.save()
            self.stdout.write(f'✅ Created test user: {username}')
        else:
            self.stdout.write(f'✅ Using existing user: {username}')

        # Create or get test workspace
        workspace, created = Workspace.objects.get_or_create(
            name=workspace_name,
            defaults={
                'owner': user,
                'assistant_name': 'AI Assistant',
                'ai_personality': 'professional',
                'ai_role': 'customer_support',
                'auto_reply_mode': True,
                'business_type': 'technology',
                'industry': 'software',
                'timezone': 'UTC',
                'language': 'en'
            }
        )

        if created:
            self.stdout.write(f'✅ Created test workspace: {workspace_name}')
        else:
            self.stdout.write(f'✅ Using existing workspace: {workspace_name}')

        # Test Enhanced Context Extraction
        self.stdout.write('\n🧠 Testing Enhanced Context Extraction...')
        try:
            enhanced_extraction = EnhancedContextExtraction()
            
            # Test conversation analysis
            test_conversations = [
                "Hi, I need help with my urgent order #12345. It's for 5 units of the premium package.",
                "When will my delivery arrive? I'm a gold tier customer and this is time-sensitive.",
                "I have a compliance question about our enterprise account. We need this resolved ASAP.",
                "Can you help me with the API integration? I'm getting error 404 on the authentication endpoint.",
                "I'm a platinum customer and need priority support for my urgent issue."
            ]
            
            # Analyze patterns
            patterns = enhanced_extraction._analyze_conversation_patterns(test_conversations)
            self.stdout.write(f'✅ Pattern analysis completed:')
            self.stdout.write(f'   - Entities found: {len(patterns["entities"])}')
            self.stdout.write(f'   - Phrases found: {len(patterns["phrases"])}')
            self.stdout.write(f'   - Contextual clues found: {len(patterns["contextual_clues"])}')
            
            # Discover fields
            discovered_fields = enhanced_extraction.discover_new_fields(
                workspace_id=str(workspace.id),
                conversation_texts=test_conversations
            )
            
            self.stdout.write(f'✅ Field discovery completed: {len(discovered_fields)} fields found')
            
            for field in discovered_fields:
                self.stdout.write(f'   - {field["suggested_field_name"]} ({field["field_type"]}) - Confidence: {field["confidence_score"]:.2f}')
                
        except Exception as e:
            self.stdout.write(f'❌ Enhanced Context Extraction failed: {str(e)}')

        # Test Field Suggestion Service
        self.stdout.write('\n🔍 Testing Field Suggestion Service...')
        try:
            service = FieldSuggestionService()
            
            # Generate suggestions
            suggestions = service.generate_suggestions_for_workspace(str(workspace.id), limit=5)
            
            self.stdout.write(f'✅ Field suggestions generated: {len(suggestions)} suggestions')
            
            for suggestion in suggestions:
                self.stdout.write(f'   - {suggestion.suggested_field_name} ({suggestion.field_type})')
                self.stdout.write(f'     Confidence: {suggestion.confidence_score:.2f}, Business Value: {suggestion.business_value_score:.2f}')
            
            # Test analytics
            analytics = service.get_suggestion_analytics(str(workspace.id))
            self.stdout.write(f'✅ Analytics retrieved:')
            self.stdout.write(f'   - Total suggestions: {analytics["total_suggestions"]}')
            self.stdout.write(f'   - Approval rate: {analytics["approval_rate"]:.2%}')
            
        except Exception as e:
            self.stdout.write(f'❌ Field Suggestion Service failed: {str(e)}')

        # Test DynamicFieldSuggestion model
        self.stdout.write('\n📊 Testing DynamicFieldSuggestion Model...')
        try:
            suggestions = DynamicFieldSuggestion.objects.filter(workspace=workspace)
            self.stdout.write(f'✅ Model queries working: {suggestions.count()} suggestions in database')
            
            if suggestions.exists():
                suggestion = suggestions.first()
                self.stdout.write(f'   - Sample suggestion: {suggestion.suggested_field_name}')
                self.stdout.write(f'   - Field type: {suggestion.field_type}')
                self.stdout.write(f'   - Confidence: {suggestion.confidence_score:.2f}')
                
        except Exception as e:
            self.stdout.write(f'❌ Model queries failed: {str(e)}')

        self.stdout.write('\n🎉 Field discovery system test completed!')
        self.stdout.write('=' * 50)
        self.stdout.write(f'Workspace: {workspace.name}')
        self.stdout.write(f'Workspace ID: {workspace.id}')
        self.stdout.write(f'Owner: {workspace.owner.username}')
        self.stdout.write('')
        self.stdout.write('You can now test the field discovery system in the dashboard!')
