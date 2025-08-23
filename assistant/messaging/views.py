from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.core.files.storage import default_storage
from django.conf import settings
from django.utils import timezone
from django.utils.decorators import method_decorator
# from django_ratelimit.decorators import ratelimit
import uuid
import os
import mimetypes

from .models import Message, AudioTranscription, MessageDraft
from .serializers import (
    MessageSerializer, CreateTextMessageSerializer, FileUploadSerializer,
    AudioUploadSerializer, MessageDraftSerializer, ApproveDraftSerializer,
    GenerateResponseSerializer, MessageStatusSerializer, ConversationMessagesSerializer
)
from core.models import Conversation
# from core.security import InputSanitizationMixin, SecurityAudit, sanitize_request_data
# from core.file_security import file_validator

# Import context tracking components
try:
    from context_tracking.models import ConversationContext
    from context_tracking.services import ContextExtractionService, RuleEngineService
    from context_tracking.ai_integration import ContextAwareIntentClassifier
    CONTEXT_TRACKING_AVAILABLE = True
except ImportError:
    CONTEXT_TRACKING_AVAILABLE = False


# @method_decorator(ratelimit(key='ip', rate='30/m', method=['POST', 'PUT', 'PATCH']), name='dispatch')
class MessageViewSet(viewsets.ModelViewSet):
    """Message management viewset with security"""
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [AllowAny]  # Session validation handled by middleware
    
    def get_queryset(self):
        """Filter messages by conversation"""
        queryset = Message.objects.select_related('conversation').prefetch_related('transcription')
        
        # Filter by conversation if provided
        conversation_id = self.request.query_params.get('conversation', None)
        if conversation_id:
            queryset = queryset.filter(conversation_id=conversation_id)
        elif hasattr(self.request, 'conversation'):
            # Use conversation from middleware
            queryset = queryset.filter(conversation=self.request.conversation)
        
        # Filter by sender
        sender = self.request.query_params.get('sender', None)
        if sender:
            queryset = queryset.filter(sender=sender)
        
        # Filter by message type
        message_type = self.request.query_params.get('type', None)
        if message_type:
            queryset = queryset.filter(message_type=message_type)
        
        return queryset.order_by('created_at')
    
    def create(self, request, *args, **kwargs):
        """Create a new text message"""
        serializer = CreateTextMessageSerializer(data=request.data)
        if serializer.is_valid():
            # Get conversation from middleware or request
            conversation = getattr(request, 'conversation', None)
            if not conversation:
                conversation_id = request.data.get('conversation_id')
                if conversation_id:
                    conversation = get_object_or_404(Conversation, id=conversation_id)
                else:
                    return Response(
                        {'error': 'Conversation context required'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Create message
            message = Message.objects.create(
                conversation=conversation,
                sender=serializer.validated_data['sender'],
                message_type='text',
                text=serializer.validated_data['text'],
                status='sent'
            )
            
            # Update conversation timestamp
            conversation.save()
            
            # Enhanced context processing for client messages
            try:
                from context_tracking.models import ConversationContext
                CONTEXT_TRACKING_AVAILABLE = True
            except ImportError:
                CONTEXT_TRACKING_AVAILABLE = False
                
            if message.sender == 'client' and CONTEXT_TRACKING_AVAILABLE:
                self._process_message_context(message)
            
            # Trigger AI response if from client and auto-reply is enabled
            if (message.sender == 'client' and 
                conversation.workspace.auto_reply_mode):
                # Import here to avoid circular imports
                from .tasks import generate_ai_response
                try:
                    # Try async first, fallback to sync for development
                    generate_ai_response.delay(str(message.id))
                except Exception as e:
                    # Fallback to synchronous execution for development
                    print(f"Celery not running, executing AI response synchronously: {e}")
                    generate_ai_response(str(message.id))
            
            return Response(
                MessageSerializer(message).data, 
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def extract_context(self, request, pk=None):
        """Manually trigger context extraction for a message"""
        if not CONTEXT_TRACKING_AVAILABLE:
            return Response(
                {'error': 'Context tracking not available'}, 
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
        
        message = self.get_object()
        
        if message.sender != 'client':
            return Response(
                {'error': 'Context extraction only available for client messages'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get conversation context
            conversation_context = self._get_or_create_conversation_context(message.conversation)
            
            if not conversation_context:
                return Response(
                    {'error': 'No context schema available for this conversation'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Force context extraction
            extraction_service = ContextExtractionService()
            result = extraction_service.extract_context_from_text(
                context=conversation_context,
                text=message.text,
                force_extraction=True
            )
            
            if result.get('success'):
                return Response({
                    'success': True,
                    'message': 'Context extraction completed',
                    'extracted_fields': result.get('extracted_fields', {}),
                    'confidence_scores': result.get('confidence_scores', {}),
                    'context_id': str(conversation_context.id)
                })
            else:
                return Response({
                    'success': False,
                    'error': result.get('error', 'Context extraction failed')
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _process_message_context(self, message):
        """Process message for context extraction and business rules"""
        try:
            from context_tracking.models import ConversationContext
            # Get or create conversation context
            conversation_context = self._get_or_create_conversation_context(message.conversation)
            
            if not conversation_context:
                return
            
            # Extract context from message text if it's meaningful
            if message.text and len(message.text.strip()) > 10:
                # Schedule async context extraction
                from django.db import transaction
                
                def extract_context():
                    try:
                        extraction_service = ContextExtractionService()
                        extraction_service.extract_context_from_text(
                            context=conversation_context,
                            text=message.text,
                            force_extraction=False
                        )
                        
                        # Trigger business rules
                        rule_engine = RuleEngineService()
                        rule_engine.evaluate_new_message(
                            context=conversation_context,
                            message_data={
                                'id': str(message.id),
                                'text': message.text,
                                'sender': message.sender,
                                'message_type': message.message_type,
                                'created_at': message.created_at.isoformat()
                            }
                        )
                        
                    except Exception as e:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.error(f"Context processing failed for message {message.id}: {str(e)}")
                
                # Schedule extraction after transaction commits
                transaction.on_commit(extract_context)
            
            # Enhanced intent classification with context
            try:
                from context_tracking.ai_integration import ContextAwareIntentClassifier
                classifier = ContextAwareIntentClassifier()
                intent, confidence, context_updates = classifier.classify_with_context(
                    message.text, conversation_context
                )
                
                # Update message with enhanced intent
                message.intent_classification = intent
                message.confidence_score = confidence
                message.save(update_fields=['intent_classification', 'confidence_score'])
                
                # Apply context updates if any
                if context_updates:
                    for field_id, value in context_updates.items():
                        conversation_context.set_field_value(
                            field_id, value, confidence, is_ai_update=True
                        )
                    conversation_context.save()
                
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Intent classification failed for message {message.id}: {str(e)}")
                # Continue without intent classification
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Message context processing failed for {message.id}: {str(e)}")
    
    def _get_or_create_conversation_context(self, conversation):
        """Get or create conversation context"""
        try:
            from context_tracking.models import ConversationContext
            return ConversationContext.objects.get(conversation=conversation)
        except ConversationContext.DoesNotExist:
            # Should be created by signals, but as fallback
            try:
                from context_tracking.models import WorkspaceContextSchema
                
                default_schema = WorkspaceContextSchema.objects.filter(
                    workspace=conversation.workspace,
                    is_default=True,
                    is_active=True
                ).first()
                
                if default_schema:
                    return ConversationContext.objects.create(
                        conversation=conversation,
                        schema=default_schema,
                        title="",
                        context_data={},
                        status="new",
                        priority="medium"
                    )
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to create conversation context: {str(e)}")
            
            return None


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def session_messages(request):
    """Get messages for a session (GET) or create a new message (POST)"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Get session token from query params or headers
    session_token = (
        request.GET.get('session_token') or 
        request.headers.get('X-Session-Token') or
        request.META.get('HTTP_X_SESSION_TOKEN')
    )
    
    logger.info(f"session_messages: method={request.method}, session_token present: {bool(session_token)}")
    
    if not session_token:
        logger.error("session_messages: No session token provided")
        return Response(
            {
                'error': 'Session token is required in query params or X-Session-Token header',
                'debug': {
                    'query_params': dict(request.GET),
                    'headers_checked': ['X-Session-Token', 'HTTP_X_SESSION_TOKEN'],
                    'headers_available': list(request.headers.keys())
                }
            }, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Handle POST request - create new message
    if request.method == 'POST':
        return _create_session_message(request, session_token, logger)
    
    # Handle GET request - get messages
    else:
        return _get_session_messages(request, session_token, logger)


def _create_session_message(request, session_token, logger):
    """Create a new message for a session"""
    try:
        # Get session
        from core.models import Session
        try:
            session = Session.objects.get(session_token=session_token)
        except Session.DoesNotExist:
            return Response(
                {'error': 'Invalid session token'}, 
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Get or create conversation
        conversation = session.conversations.order_by('-created_at').first()
        if not conversation:
            # Create new conversation
            from core.models import Conversation
            conversation = Conversation.objects.create(
                workspace=session.contact.workspace,
                session=session,
                contact=session.contact,
                status='active'
            )
        
        # Validate request data - accept both 'text' and 'content' fields
        text = request.data.get('text', '') or request.data.get('content', '')
        text = text.strip()
        if not text:
            return Response(
                {'error': 'Message text is required (use "text" or "content" field)'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create message
        message = Message.objects.create(
            conversation=conversation,
            sender='client',
            message_type='text',
            text=text,
            status='sent'
        )
        
        # Update conversation timestamp
        conversation.save()
        
        # Enhanced context processing for client messages
        try:
            from context_tracking.models import ConversationContext
            CONTEXT_TRACKING_AVAILABLE = True
        except ImportError:
            CONTEXT_TRACKING_AVAILABLE = False
            
        if CONTEXT_TRACKING_AVAILABLE:
            try:
                # Get or create conversation context
                conversation_context = ConversationContext.objects.filter(
                    conversation=conversation
                ).first()
                
                if conversation_context and len(text) > 10:
                    # Schedule async context extraction
                    from django.db import transaction
                    
                    def extract_context():
                        try:
                            extraction_service = ContextExtractionService()
                            extraction_service.extract_context_from_text(
                                context=conversation_context,
                                text=text,
                                force_extraction=False
                            )
                        except Exception as e:
                            logger.error(f"Context extraction failed: {str(e)}")
                    
                    transaction.on_commit(extract_context)
            except Exception as e:
                logger.error(f"Context processing failed: {str(e)}")
        
        # Trigger AI response if auto-reply is enabled
        if conversation.workspace.auto_reply_mode:
            from .tasks import generate_ai_response
            try:
                generate_ai_response.delay(str(message.id))
            except Exception as e:
                logger.warning(f"Could not schedule AI response: {str(e)}")
                # Fallback to synchronous execution for development
                try:
                    generate_ai_response(str(message.id))
                except Exception as sync_error:
                    logger.error(f"AI response generation failed: {str(sync_error)}")
        
        # Return created message
        serializer = MessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Failed to create session message: {str(e)}")
        return Response(
            {'error': f'Failed to create message: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def _get_session_messages(request, session_token, logger):
    """Get messages for a session"""
    conversation_id = request.GET.get('conversation_id') or request.GET.get('conversation')
    
    try:
        # Get session from middleware or validate session
        session = getattr(request, 'session_obj', None)
        
        if not session:
            # Try to get session by token
            from core.models import Session
            try:
                session = Session.objects.get(session_token=session_token)
            except Session.DoesNotExist:
                return Response(
                    {'error': 'Invalid session token'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )
        
        # Get conversation
        if conversation_id:
            try:
                conversation = Conversation.objects.get(
                    id=conversation_id, 
                    session=session
                )
            except Conversation.DoesNotExist:
                return Response(
                    {'error': 'Conversation not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Get latest conversation for session
            conversation = session.conversations.order_by('-created_at').first()
            
            if not conversation:
                return Response({
                    'conversation_id': None,
                    'messages': [],
                    'total_messages': 0
                })
        
        # Get messages for conversation
        messages = Message.objects.filter(
            conversation=conversation
        ).order_by('created_at')
        
        # Apply pagination
        page_size = min(int(request.GET.get('page_size', 50)), 100)
        page = int(request.GET.get('page', 1))
        start = (page - 1) * page_size
        end = start + page_size
        
        paginated_messages = messages[start:end]
        serializer = MessageSerializer(paginated_messages, many=True)
        
        return Response({
            'conversation_id': str(conversation.id),
            'messages': serializer.data,
            'total_messages': messages.count(),
            'page': page,
            'page_size': page_size,
            'has_next': end < messages.count(),
            'has_previous': page > 1
        })
        
    except Exception as e:
        logger.error(f"Failed to get session messages: {str(e)}")
        return Response(
            {'error': f'Failed to get session messages: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class MessageDraftViewSet(viewsets.ModelViewSet):
    """Message draft management viewset"""
    queryset = MessageDraft.objects.all()
    serializer_class = MessageDraftSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter drafts by conversation or workspace"""
        queryset = MessageDraft.objects.select_related('conversation')
        
        # Filter by conversation
        conversation_id = self.request.query_params.get('conversation', None)
        if conversation_id:
            queryset = queryset.filter(conversation_id=conversation_id)
        
        # Filter by approval status
        pending_only = self.request.query_params.get('pending', None)
        if pending_only == 'true':
            queryset = queryset.filter(is_approved=False, is_rejected=False)
        
        return queryset.order_by('-created_at')


# @method_decorator(ratelimit(key='ip', rate='10/m', method='POST'), name='post')
class UploadFileView(APIView):
    """Handle file uploads with security validation"""
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [AllowAny]  # Session validation via middleware
    
    def post(self, request):
        # # Sanitize input data
        # sanitized_data = sanitize_request_data(request.data.dict())
        
        serializer = FileUploadSerializer(data=request.data)
        if serializer.is_valid():
            uploaded_file = serializer.validated_data['file']
            sender = serializer.validated_data['sender']
            
            # Get conversation from middleware
            conversation = getattr(request, 'conversation', None)
            if not conversation:
                return Response(
                    {'error': 'Conversation context required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # # Validate file security
            # validation_result = file_validator.validate_file(uploaded_file)
            # if not validation_result['is_valid']:
            #     SecurityAudit.log_suspicious_activity(
            #         request, 
            #         f"Invalid file upload: {', '.join(validation_result['errors'])}"
            #     )
            #     return Response({
            #         'error': 'File validation failed',
            #         'details': validation_result['errors']
            #     }, status=status.HTTP_400_BAD_REQUEST)
            
            # # Log warnings if any
            # if validation_result.get('warnings'):
            #     SecurityAudit.log_security_event(
            #         'file_upload_warning',
            #         request,
            #         {'warnings': validation_result['warnings']}
            #     )
            
            try:
                # Generate unique filename
                file_extension = os.path.splitext(uploaded_file.name)[1]
                unique_filename = f"{uuid.uuid4()}{file_extension}"
                
                # Save file to storage
                file_path = f"uploads/{conversation.workspace.id}/{unique_filename}"
                saved_path = default_storage.save(file_path, uploaded_file)
                file_url = default_storage.url(saved_path)
                
                # Create message record
                message = Message.objects.create(
                    conversation=conversation,
                    sender=sender,
                    message_type='file',
                    media_url=file_url,
                    media_filename=uploaded_file.name,
                    media_size=uploaded_file.size,
                    text=f"Uploaded file: {uploaded_file.name}",
                    status='sent'
                )
                
                # Update conversation timestamp
                conversation.save()
                
                return Response(
                    MessageSerializer(message).data,
                    status=status.HTTP_201_CREATED
                )
                
            except Exception as e:
                return Response(
                    {'error': f'File upload failed: {str(e)}'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# @method_decorator(ratelimit(key='ip', rate='5/m', method='POST'), name='post')
class UploadAudioView(APIView):
    """Handle audio file uploads with security validation and transcription"""
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [AllowAny]  # Session validation via middleware
    
    def post(self, request):
        serializer = AudioUploadSerializer(data=request.data)
        if serializer.is_valid():
            audio_file = serializer.validated_data['audio_file']
            sender = serializer.validated_data['sender']
            
            # Get conversation from middleware
            conversation = getattr(request, 'conversation', None)
            if not conversation:
                return Response(
                    {'error': 'Conversation context required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                # Generate unique filename
                file_extension = os.path.splitext(audio_file.name)[1]
                unique_filename = f"{uuid.uuid4()}{file_extension}"
                
                # Save audio file to storage
                file_path = f"audio/{conversation.workspace.id}/{unique_filename}"
                saved_path = default_storage.save(file_path, audio_file)
                file_url = default_storage.url(saved_path)
                
                # Create message record
                message = Message.objects.create(
                    conversation=conversation,
                    sender=sender,
                    message_type='audio',
                    media_url=file_url,
                    media_filename=audio_file.name,
                    media_size=audio_file.size,
                    text="Audio message",
                    status='processing'
                )
                
                # Update conversation timestamp
                conversation.save()
                
                # Trigger background transcription
                from .tasks import process_audio_message
                process_audio_message.delay(str(message.id))
                
                return Response(
                    MessageSerializer(message).data,
                    status=status.HTTP_201_CREATED
                )
                
            except Exception as e:
                return Response(
                    {'error': f'Audio upload failed: {str(e)}'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GenerateResponseView(APIView):
    """Generate AI response for a message"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = GenerateResponseSerializer(data=request.data)
        if serializer.is_valid():
            message_text = serializer.validated_data['message_text']
            conversation_id = serializer.validated_data.get('conversation_id')
            force_generation = serializer.validated_data.get('force_generation', False)
            
            # Get conversation
            if conversation_id:
                conversation = get_object_or_404(Conversation, id=conversation_id)
            else:
                conversation = getattr(request, 'conversation', None)
                if not conversation:
                    return Response(
                        {'error': 'Conversation context required'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Create a temporary message for processing
            temp_message = Message.objects.create(
                conversation=conversation,
                sender='client',
                message_type='text',
                text=message_text,
                status='processing'
            )
            
            # Trigger AI response generation
            from .tasks import generate_ai_response
            task = generate_ai_response.delay(str(temp_message.id), force_generation)
            
            return Response({
                'message': 'AI response generation started',
                'task_id': task.id,
                'message_id': temp_message.id
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ApproveDraftView(APIView):
    """Approve or reject draft messages"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = ApproveDraftSerializer(data=request.data)
        if serializer.is_valid():
            draft_id = serializer.validated_data['draft_id']
            action = serializer.validated_data['action']
            modified_text = serializer.validated_data.get('modified_text', '')
            
            draft = get_object_or_404(MessageDraft, id=draft_id)
            
            if action == 'approve':
                with transaction.atomic():
                    # Mark draft as approved
                    draft.is_approved = True
                    draft.approved_at = timezone.now()
                    draft.save()
                    
                    # Create actual message
                    message_text = modified_text if modified_text else draft.suggested_text
                    message = Message.objects.create(
                        conversation=draft.conversation,
                        sender='assistant',
                        message_type='text',
                        text=message_text,
                        status='sent'
                    )
                    
                    # Update conversation
                    draft.conversation.save()
                    
                    return Response({
                        'status': 'Draft approved and message sent',
                        'message_id': message.id
                    })
            
            elif action == 'reject':
                draft.is_rejected = True
                draft.save()
                
                return Response({'status': 'Draft rejected'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
