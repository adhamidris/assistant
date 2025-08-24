"""
Authentication views for APP users
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from .models import AppUser, Workspace
from .serializers import WorkspaceSerializer
import uuid
import qrcode
import io
import base64
import logging
logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_user(request):
    """Register a new APP user with workspace"""
    try:
        data = request.data
        
        # Validate required fields
        required_fields = ['username', 'email', 'password', 'business_name', 'full_name']
        for field in required_fields:
            if not data.get(field):
                return Response({
                    'error': f'{field} is required'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if username or email already exists
        if User.objects.filter(username=data['username']).exists():
            return Response({
                'error': 'Username already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(email=data['email']).exists():
            return Response({
                'error': 'Email already exists'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate password
        try:
            validate_password(data['password'])
        except ValidationError as e:
            return Response({
                'error': 'Password validation failed',
                'details': list(e.messages)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create user and workspace in transaction
        with transaction.atomic():
            # Create Django User
            django_user = User.objects.create_user(
                username=data['username'],
                email=data['email'],
                password=data['password'],
                first_name=data['full_name'].split()[0] if data['full_name'] else '',
                last_name=' '.join(data['full_name'].split()[1:]) if data['full_name'] and len(data['full_name'].split()) > 1 else ''
            )
            
            # Create APP user profile
            app_user = AppUser.objects.create(
                user=django_user,
                full_name=data['full_name'],
                business_name=data['business_name'],
                business_type=data.get('business_type', ''),
                phone_number=data.get('phone_number', ''),
                occupation=data.get('occupation', ''),
                industry=data.get('industry', ''),
            )
            
            # Create workspace for the user
            workspace = Workspace.objects.create(
                owner=django_user,
                name=data['business_name'],
                assistant_name=data.get('assistant_name', 'Assistant'),
                timezone=data.get('timezone', 'UTC'),
                auto_reply_mode=True,
                profile_completed=False
            )
            
            # Create auth token
            token, created = Token.objects.get_or_create(user=django_user)
            
            # Send welcome email
            try:
                from notifications.services import NotificationService
                NotificationService.send_welcome_email(django_user)
            except Exception as e:
                logger.error(f"Failed to send welcome email: {str(e)}")
            
            return Response({
                'message': 'User registered successfully',
                'user_id': str(django_user.id),
                'workspace_id': str(workspace.id),
                'token': token.key,
                'user': {
                    'username': django_user.username,
                    'email': django_user.email,
                    'full_name': app_user.full_name,
                    'business_name': app_user.business_name,
                },
                'workspace': WorkspaceSerializer(workspace).data
            }, status=status.HTTP_201_CREATED)
            
    except Exception as e:
        return Response({
            'error': 'Registration failed',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def login_user(request):
    """Login APP user"""
    try:
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response({
                'error': 'Username and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Authenticate user
        user = authenticate(username=username, password=password)
        if not user:
            return Response({
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Get or create token
        token, created = Token.objects.get_or_create(user=user)
        
        # Get user's workspace and app profile
        workspace = user.workspaces.first()
        app_profile = getattr(user, 'app_profile', None)
        
        return Response({
            'message': 'Login successful',
            'token': token.key,
            'user_id': str(user.id),
            'workspace_id': str(workspace.id) if workspace else None,
            'user': {
                'username': user.username,
                'email': user.email,
                'full_name': app_profile.full_name if app_profile else '',
                'business_name': app_profile.business_name if app_profile else '',
                'subscription_status': app_profile.subscription_status if app_profile else 'trial',
            },
            'workspace': WorkspaceSerializer(workspace).data if workspace else None,
            'profile_completed': workspace.profile_completed if workspace else False
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': 'Login failed',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    """Logout APP user"""
    try:
        # Delete the user's token
        request.user.auth_token.delete()
        return Response({
            'message': 'Logout successful'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'error': 'Logout failed',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request):
    """Get current user profile and workspace"""
    try:
        user = request.user
        workspace = user.workspaces.first()
        app_profile = getattr(user, 'app_profile', None)
        
        return Response({
            'user': {
                'id': str(user.id),
                'username': user.username,
                'email': user.email,
                'full_name': app_profile.full_name if app_profile else '',
                'business_name': app_profile.business_name if app_profile else '',
                'business_type': app_profile.business_type if app_profile else '',
                'phone_number': app_profile.phone_number if app_profile else '',
                'occupation': app_profile.occupation if app_profile else '',
                'industry': app_profile.industry if app_profile else '',
                'subscription_status': app_profile.subscription_status if app_profile else 'trial',
                'is_verified': app_profile.is_verified if app_profile else False,
            },
            'workspace': WorkspaceSerializer(workspace).data if workspace else None,
            'profile_completed': workspace.profile_completed if workspace else False
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': 'Failed to get user profile',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_portal_link(request):
    """Generate personalized portal links for the user's AI agents"""
    try:
        user = request.user
        workspace = user.workspaces.first()
        
        if not workspace:
            return Response({
                'error': 'No workspace found for user'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Get all agents for this workspace
        from .models import AIAgent
        agents = AIAgent.objects.filter(workspace=workspace)
        default_agent = agents.filter(is_default=True).first()
        active_agents = agents.filter(is_active=True)
        
        # Get the app user profile for business info
        app_profile = getattr(user, 'app_profile', None)
        is_business_user = bool(app_profile and app_profile.business_name)
        
        # Generate agent-specific URLs
        from django.conf import settings
        base_url = getattr(settings, 'FRONTEND_BASE_URL', 'http://localhost:3000')
        workspace_slug = workspace.get_simple_slug()
        
        agent_links = []
        for agent in agents:
            agent_links.append({
                'id': str(agent.id),
                'name': agent.name,
                'description': agent.description,
                'slug': agent.slug,
                'is_active': agent.is_active,
                'is_default': agent.is_default,
                'channel_type': agent.channel_type,
                'portal_url': f"{base_url}/portal/{workspace_slug}/{agent.slug}/",
                'qr_code_url': f"{request.build_absolute_uri('/')[:-1]}/api/v1/auth/qr-code/{workspace.id}/{agent.slug}/"
            })
        
        # Main portal URL (only if there's a default agent)
        main_portal_url = None
        if default_agent:
            main_portal_url = f"{base_url}/portal/{workspace_slug}/{default_agent.slug}/"
        
        return Response({
            'workspace_id': str(workspace.id),
            'workspace_name': workspace.name,
            'workspace_slug': workspace_slug,
            'main_portal_url': main_portal_url,
            'default_agent': {
                'id': str(default_agent.id),
                'name': default_agent.name,
                'slug': default_agent.slug
            } if default_agent else None,
            'agent_links': agent_links,
            'active_agents_count': active_agents.count(),
            'total_agents_count': agents.count(),
            'instructions': f"Share these links with your clients to start conversations with your AI agents",
            'is_business_user': is_business_user,
            'user_info': {
                'business_name': app_profile.business_name if app_profile else None,
                'full_name': app_profile.full_name if app_profile else user.username,
                'assistant_name': workspace.assistant_name
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': 'Failed to generate portal link',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def generate_qr_code(request, workspace_id):
    """Generate QR code for portal link"""
    try:
        # Get workspace
        workspace = get_object_or_404(Workspace, id=workspace_id)
        
        # Use the custom portal URL
        portal_url = workspace.portal_url
        
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(portal_url)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Return image response
        response = HttpResponse(buffer.getvalue(), content_type='image/png')
        response['Content-Disposition'] = f'attachment; filename="portal-qr-{workspace.portal_slug.replace('/', '-')}.png"'
        return response
        
    except Exception as e:
        return Response({
            'error': 'Failed to generate QR code',
            'details': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
