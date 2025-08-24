from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils.text import slugify
import secrets
import string

from .models import Workspace, Contact, Session, Conversation, AIAgent
from .serializers import (
    WorkspaceSerializer, ContactSerializer, SessionSerializer, 
    ConversationSerializer, CreateSessionSerializer, ValidateSessionSerializer
)
from .profile_serializers import ProfileSetupSerializer, ProfileStatusSerializer


class WorkspaceViewSet(viewsets.ModelViewSet):
    """Workspace management viewset"""
    queryset = Workspace.objects.all()
    serializer_class = WorkspaceSerializer
    permission_classes = [AllowAny]  # Temporary for development
    
    @action(detail=True, methods=['get'], url_path='profile-status')
    def profile_status(self, request, pk=None):
        """Check profile completion status"""
        workspace = self.get_object()
        serializer = ProfileStatusSerializer(workspace)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post', 'put'], url_path='setup-profile')
    def setup_profile(self, request, pk=None):
        """Setup or update workspace profile"""
        workspace = self.get_object()
        serializer = ProfileSetupSerializer(workspace, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Profile updated successfully',
                'profile_completed': workspace.profile_completed,
                'data': serializer.data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ContactViewSet(viewsets.ModelViewSet):
    """Contact management viewset"""
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter contacts by workspace if provided"""
        queryset = Contact.objects.all()
        workspace_id = self.request.query_params.get('workspace', None)
        if workspace_id:
            queryset = queryset.filter(workspace_id=workspace_id)
        return queryset.order_by('-created_at')


class SessionViewSet(viewsets.ModelViewSet):
    """Session management viewset"""
    queryset = Session.objects.all()
    serializer_class = SessionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter sessions by contact or active status"""
        queryset = Session.objects.all()
        contact_id = self.request.query_params.get('contact', None)
        is_active = self.request.query_params.get('active', None)
        
        if contact_id:
            queryset = queryset.filter(contact_id=contact_id)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
            
        return queryset.order_by('-created_at')


class ConversationViewSet(viewsets.ModelViewSet):
    """Conversation management viewset"""
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter conversations by workspace, status, or contact"""
        queryset = Conversation.objects.all()
        workspace_id = self.request.query_params.get('workspace', None)
        status_filter = self.request.query_params.get('status', None)
        contact_id = self.request.query_params.get('contact', None)
        
        if workspace_id:
            queryset = queryset.filter(workspace_id=workspace_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if contact_id:
            queryset = queryset.filter(contact_id=contact_id)
            
        return queryset.order_by('-updated_at')
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update conversation status"""
        conversation = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in ['active', 'resolved', 'archived']:
            return Response(
                {'error': 'Invalid status'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        conversation.status = new_status
        conversation.save()
        
        return Response({'status': 'Status updated successfully'})


class CreateSessionView(APIView):
    """Create a new session for a customer"""
    permission_classes = [AllowAny]  # Allow anonymous access for customer portal
    
    def post(self, request):
        serializer = CreateSessionSerializer(data=request.data)
        if serializer.is_valid():
            phone_number = serializer.validated_data['phone_number']
            workspace_id = serializer.validated_data['workspace_id']
            
            try:
                with transaction.atomic():
                    # Get or create workspace
                    workspace = get_object_or_404(Workspace, id=workspace_id)
                    
                    # Get or create contact
                    contact, created = Contact.objects.get_or_create(
                        workspace=workspace,
                        phone_e164=phone_number,
                        defaults={'name': ''}
                    )
                    
                    # Generate session token
                    session_token = ''.join(secrets.choice(
                        string.ascii_letters + string.digits
                    ) for _ in range(32))
                    
                    # Create session
                    session = Session.objects.create(
                        contact=contact,
                        session_token=session_token
                    )
                    
                    return Response({
                        'session_token': session_token,
                        'contact_id': contact.id,
                        'contact_name': contact.name,
                        'workspace_name': contact.workspace.name,
                        'assistant_name': contact.workspace.assistant_name,
                        'is_new_contact': created
                    }, status=status.HTTP_201_CREATED)
                    
            except Exception as e:
                return Response(
                    {'error': str(e)}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ValidateSessionView(APIView):
    """Validate an existing session token"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = ValidateSessionSerializer(data=request.data)
        if serializer.is_valid():
            session_token = serializer.validated_data['session_token']
            
            try:
                session = Session.objects.select_related('contact', 'contact__workspace').get(
                    session_token=session_token,
                    is_active=True
                )
                
                # Update last seen
                session.save()  # This triggers auto_now=True on last_seen_at
                
                return Response({
                    'valid': True,
                    'contact_id': session.contact.id,
                    'contact_name': session.contact.name,
                    'workspace_name': session.contact.workspace.name,
                    'assistant_name': session.contact.workspace.assistant_name
                })
                
            except Session.DoesNotExist:
                return Response(
                    {'valid': False, 'error': 'Invalid session token'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def resolve_portal_slug(request, slug_path):
    """Resolve custom portal slug to workspace information"""
    try:
        # Parse the slug path - it could be "company-name/employee-name" or "user-name"
        slug_parts = slug_path.split('/')
        
        # First, try to find workspace by exact portal slug match
        workspaces = Workspace.objects.select_related('owner').all()
        
        for workspace in workspaces:
            try:
                # Try to get the computed portal slug
                computed_slug = workspace.portal_slug
                if computed_slug == slug_path:
                    return Response({
                        'workspace_id': str(workspace.id),
                        'workspace_name': workspace.name,
                        'assistant_name': workspace.assistant_name,
                        'portal_slug': computed_slug,
                        'found': True
                    })
            except Exception:
                # Skip workspaces with missing app_profile
                continue
        
        # If no exact match found, try to find by workspace name or ID
        # This provides a fallback for testing and development
        for workspace in workspaces:
            # Try matching by workspace name (case-insensitive)
            if workspace.name.lower() == slug_path.lower():
                try:
                    computed_slug = workspace.portal_slug
                    return Response({
                        'workspace_id': str(workspace.id),
                        'workspace_name': workspace.name,
                        'assistant_name': workspace.assistant_name,
                        'portal_slug': computed_slug,
                        'found': True
                    })
                except Exception:
                    # If portal_slug fails, use a fallback
                    fallback_slug = workspace.get_simple_slug()
                    return Response({
                        'workspace_id': str(workspace.id),
                        'workspace_name': workspace.name,
                        'assistant_name': workspace.assistant_name,
                        'portal_slug': fallback_slug,
                        'found': True
                    })
            
            # Try matching by workspace ID
            if str(workspace.id) == slug_path:
                try:
                    computed_slug = workspace.portal_slug
                    return Response({
                        'workspace_id': str(workspace.id),
                        'workspace_name': workspace.name,
                        'assistant_name': workspace.assistant_name,
                        'portal_slug': computed_slug,
                        'found': True
                    })
                except Exception:
                    # If portal_slug fails, use a fallback
                    fallback_slug = workspace.get_simple_slug()
                    return Response({
                        'workspace_id': str(workspace.id),
                        'workspace_name': workspace.name,
                        'assistant_name': workspace.assistant_name,
                        'portal_slug': fallback_slug,
                        'found': True
                    })
        
        # If no match found, return not found
        return Response({
            'found': False,
            'error': 'Portal not found'
        }, status=status.HTTP_404_NOT_FOUND)
        
    except Exception as e:
        return Response({
            'found': False,
            'error': f'Failed to resolve portal: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def test_portal_resolution(request):
    """Test endpoint to debug portal resolution"""
    try:
        workspaces = Workspace.objects.all()
        workspace_data = []
        
        for workspace in workspaces:
            try:
                portal_slug = workspace.portal_slug
                simple_slug = workspace.get_simple_slug()
                workspace_data.append({
                    'id': str(workspace.id),
                    'name': workspace.name,
                    'portal_slug': portal_slug,
                    'simple_slug': simple_slug,
                    'has_owner': hasattr(workspace, 'owner'),
                    'owner_username': workspace.owner.username if hasattr(workspace, 'owner') else None,
                })
            except Exception as e:
                workspace_data.append({
                    'id': str(workspace.id),
                    'name': workspace.name,
                    'error': str(e),
                    'portal_slug': 'ERROR',
                    'simple_slug': workspace.get_simple_slug(),
                })
        
        return Response({
            'workspaces': workspace_data,
            'total': len(workspaces)
        })
        
    except Exception as e:
        return Response({
            'error': f'Failed to get workspace data: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def check_portal_status(request, workspace_id):
    """Check portal status for a workspace - used by portal to determine what to show"""
    try:
        workspace = get_object_or_404(Workspace, id=workspace_id)
        
        # Check if a specific agent is requested
        agent_slug = request.GET.get('agent_slug')
        
        # Get active agent
        active_agent = AIAgent.objects.filter(workspace=workspace, is_active=True).first()
        
        # Get all agents count
        total_agents = AIAgent.objects.filter(workspace=workspace).count()
        inactive_agents = AIAgent.objects.filter(workspace=workspace, is_active=False)
        
        # If checking for a specific agent
        if agent_slug:
            requested_agent = AIAgent.objects.filter(workspace=workspace, slug=agent_slug).first()
            if requested_agent and requested_agent.is_active:
                return Response({
                    'status': 'active',
                    'active_agent': {
                        'id': str(requested_agent.id),
                        'name': requested_agent.name,
                        'slug': requested_agent.slug,
                        'description': requested_agent.description,
                        'channel_type': requested_agent.channel_type
                    },
                    'workspace_name': workspace.name,
                    'assistant_name': workspace.assistant_name,
                    'total_agents': total_agents
                })
            else:
                return Response({
                    'status': 'agent_not_found',
                    'message': f'Agent "{agent_slug}" not found or inactive',
                    'workspace_name': workspace.name,
                    'total_agents': total_agents
                })
        
        # Default behavior for general portal status
        if active_agent:
            return Response({
                'status': 'active',
                'active_agent': {
                    'id': str(active_agent.id),
                    'name': active_agent.name,
                    'slug': active_agent.slug,
                    'description': active_agent.description,
                    'channel_type': active_agent.channel_type
                },
                'workspace_name': workspace.name,
                'assistant_name': workspace.assistant_name,
                'total_agents': total_agents
            })
        elif total_agents > 0:
            return Response({
                'status': 'no_active_agent',
                'message': 'AI assistant is not available at the moment',
                'workspace_name': workspace.name,
                'total_agents': total_agents,
                'inactive_agents': [
                    {
                        'id': str(agent.id),
                        'name': agent.name,
                        'slug': agent.slug,
                        'description': agent.description
                    }
                    for agent in inactive_agents
                ]
            })
        else:
            return Response({
                'status': 'no_agents',
                'message': 'No AI agents configured',
                'workspace_name': workspace.name,
                'total_agents': 0
            })
            
    except Exception as e:
        return Response({
            'error': f'Failed to check portal status: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
