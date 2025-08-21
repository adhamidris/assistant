from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.urls import reverse
from .models import Session
import json


class SessionValidationMiddleware(MiddlewareMixin):
    """Middleware to validate session tokens for customer portal endpoints"""
    
    # Endpoints that require session validation (portal clients only)
    PROTECTED_ENDPOINTS = [
        '/api/v1/messaging/session-messages/',
        '/api/v1/knowledge-base/search/',
        '/api/v1/calendar/available-slots/',
        '/api/v1/calendar/book-appointment/',
    ]
    
    # Endpoints that are excluded from session validation
    EXCLUDED_ENDPOINTS = [
        '/api/v1/core/session/create/',
        '/api/v1/core/session/validate/',
        '/admin/',
        '/api/v1/core/workspaces/',  # Admin endpoints
        '/api/v1/core/contacts/',    # Admin endpoints
        '/api/v1/messaging/drafts/', # Admin endpoints (owner dashboard)
    ]
    
    def process_request(self, request):
        # Skip validation for excluded endpoints
        if any(request.path.startswith(endpoint) for endpoint in self.EXCLUDED_ENDPOINTS):
            return None
        
        # Skip validation for non-protected endpoints
        if not any(request.path.startswith(endpoint) for endpoint in self.PROTECTED_ENDPOINTS):
            return None
        
        # Skip validation for OPTIONS requests (CORS preflight)
        if request.method == 'OPTIONS':
            return None
        
        # Get session token from headers or request data
        session_token = self._get_session_token(request)
        
        if not session_token:
            return JsonResponse({
                'error': 'Session token required',
                'code': 'SESSION_TOKEN_MISSING'
            }, status=401)
        
        try:
            session = Session.objects.select_related('contact', 'contact__workspace').get(
                session_token=session_token,
                is_active=True
            )
            
            # Attach session and related objects to request
            request.session_obj = session
            request.contact = session.contact
            request.workspace = session.contact.workspace
            
            # Update last seen
            session.save()  # Triggers auto_now=True on last_seen_at
            
            return None
            
        except Session.DoesNotExist:
            return JsonResponse({
                'error': 'Invalid or expired session token',
                'code': 'SESSION_TOKEN_INVALID'
            }, status=401)
    
    def _get_session_token(self, request):
        """Extract session token from request"""
        # Try Authorization header first
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            return auth_header[7:]  # Remove 'Bearer ' prefix
        
        # Try X-Session-Token header
        session_header = request.META.get('HTTP_X_SESSION_TOKEN')
        if session_header:
            return session_header
        
        # Try request data for POST requests
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                if request.content_type == 'application/json':
                    data = json.loads(request.body)
                    return data.get('session_token')
                else:
                    return request.POST.get('session_token')
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        
        # Try query parameters
        return request.GET.get('session_token')


class ConversationContextMiddleware(MiddlewareMixin):
    """Middleware to automatically create or get conversation context"""
    
    def process_request(self, request):
        # Only process if we have a session (after SessionValidationMiddleware)
        if not hasattr(request, 'session_obj'):
            return None
        
        # Skip for non-messaging endpoints
        if not request.path.startswith('/api/v1/messaging/'):
            return None
        
        # Get or create active conversation for this session
        from .models import Conversation
        
        conversation, created = Conversation.objects.get_or_create(
            session=request.session_obj,
            status='active',
            defaults={
                'workspace': request.workspace,
                'contact': request.contact,
            }
        )
        
        # Attach conversation to request
        request.conversation = conversation
        
        return None

