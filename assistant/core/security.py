"""
Security utilities and middleware for the AI Personal Business Assistant.
"""
import re
import json
import logging
from typing import Dict, Any, Optional
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.core.cache import cache
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.middleware.csrf import CsrfViewMiddleware
from django.core.exceptions import SuspiciousOperation
from django.utils import timezone
from datetime import timedelta
import bleach
from bleach import clean
from bleach.css_sanitizer import CSSSanitizer

logger = logging.getLogger(__name__)

# Security constants
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
MAX_UPLOAD_SIZE = 50 * 1024 * 1024   # 50MB for file uploads
RATE_LIMIT_REQUESTS_PER_MINUTE = 60
RATE_LIMIT_REQUESTS_PER_HOUR = 1000

# Allowed HTML tags and attributes for user content
ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li', 'blockquote',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'pre', 'code', 'span', 'div'
]

ALLOWED_ATTRIBUTES = {
    '*': ['class'],
    'a': ['href', 'title'],
    'img': ['src', 'alt', 'width', 'height'],
}

# Suspicious patterns to detect in requests
SUSPICIOUS_PATTERNS = [
    r'<script[^>]*>.*?</script>',
    r'javascript:',
    r'vbscript:',
    r'onload\s*=',
    r'onerror\s*=',
    r'onclick\s*=',
    r'eval\s*\(',
    r'exec\s*\(',
    r'import\s+os',
    r'__import__',
    r'\.\./',
    r'\.\.\\',
]

class SecurityMiddleware(MiddlewareMixin):
    """
    Enhanced security middleware that provides:
    - Request size limiting
    - Rate limiting
    - Input sanitization
    - Suspicious pattern detection
    - Security headers
    """
    
    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.suspicious_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in SUSPICIOUS_PATTERNS]
    
    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """Process incoming request for security checks."""
        
        # Check request size
        if hasattr(request, 'META') and 'CONTENT_LENGTH' in request.META:
            try:
                content_length = int(request.META['CONTENT_LENGTH'])
                max_size = MAX_UPLOAD_SIZE if 'upload' in request.path else MAX_REQUEST_SIZE
                
                if content_length > max_size:
                    logger.warning(f"Request size {content_length} exceeds limit {max_size} from {self._get_client_ip(request)}")
                    return JsonResponse({
                        'error': 'Request too large',
                        'max_size': max_size
                    }, status=413)
            except (ValueError, TypeError):
                pass
        
        # Rate limiting
        if self._is_rate_limited(request):
            logger.warning(f"Rate limit exceeded for {self._get_client_ip(request)}")
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'retry_after': 60
            }, status=429)
        
        # Check for suspicious patterns in URL and headers
        if self._contains_suspicious_patterns(request.path + str(request.META.get('HTTP_USER_AGENT', ''))):
            logger.warning(f"Suspicious request detected from {self._get_client_ip(request)}: {request.path}")
            return JsonResponse({'error': 'Request blocked'}, status=403)
        
        return None
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Add security headers to response."""
        
        # Security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        # Content Security Policy (relaxed for development, tighten for production)
        if not settings.DEBUG:
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https://api.openai.com; "
                "media-src 'self'; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "frame-ancestors 'none';"
            )
            response['Content-Security-Policy'] = csp
        
        return response
    
    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')
        return ip
    
    def _is_rate_limited(self, request: HttpRequest) -> bool:
        """Check if request should be rate limited."""
        client_ip = self._get_client_ip(request)
        
        # Different limits for different endpoints
        if '/api/v1/messaging/upload-audio/' in request.path:
            # Stricter limits for audio uploads
            limit_key = f"rate_limit_audio_{client_ip}"
            requests_per_minute = 10
        elif '/api/v1/messaging/' in request.path:
            # Moderate limits for messaging
            limit_key = f"rate_limit_messaging_{client_ip}"
            requests_per_minute = 30
        else:
            # General API limits
            limit_key = f"rate_limit_general_{client_ip}"
            requests_per_minute = RATE_LIMIT_REQUESTS_PER_MINUTE
        
        # Check minute-based rate limit
        current_requests = cache.get(limit_key, 0)
        if current_requests >= requests_per_minute:
            return True
        
        # Increment counter
        cache.set(limit_key, current_requests + 1, 60)  # 60 seconds TTL
        
        # Check hourly limit
        hour_key = f"rate_limit_hour_{client_ip}"
        hourly_requests = cache.get(hour_key, 0)
        if hourly_requests >= RATE_LIMIT_REQUESTS_PER_HOUR:
            return True
        
        cache.set(hour_key, hourly_requests + 1, 3600)  # 1 hour TTL
        
        return False
    
    def _contains_suspicious_patterns(self, text: str) -> bool:
        """Check if text contains suspicious patterns."""
        for pattern in self.suspicious_patterns:
            if pattern.search(text):
                return True
        return False


class InputSanitizationMixin:
    """
    Mixin for views that provides input sanitization methods.
    """
    
    def sanitize_html(self, content: str) -> str:
        """Sanitize HTML content to prevent XSS."""
        if not content:
            return content
        
        css_sanitizer = CSSSanitizer(allowed_css_properties=['color', 'background-color', 'font-weight'])
        
        return clean(
            content,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            css_sanitizer=css_sanitizer,
            strip=True
        )
    
    def sanitize_text(self, text: str) -> str:
        """Sanitize plain text input."""
        if not text:
            return text
        
        # Remove null bytes and control characters
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
        
        # Limit length
        if len(text) > 10000:  # 10k character limit
            text = text[:10000]
        
        return text.strip()
    
    def validate_file_type(self, filename: str, allowed_types: list = None) -> bool:
        """Validate file type based on extension."""
        if not filename:
            return False
        
        if allowed_types is None:
            allowed_types = [
                '.txt', '.pdf', '.doc', '.docx', '.rtf',
                '.jpg', '.jpeg', '.png', '.gif', '.webp',
                '.mp3', '.wav', '.ogg', '.m4a', '.flac'
            ]
        
        ext = filename.lower().split('.')[-1]
        return f'.{ext}' in allowed_types
    
    def sanitize_filename(self, filename: str) -> str:
        """Sanitize filename to prevent directory traversal."""
        if not filename:
            return 'unnamed_file'
        
        # Remove path separators and dangerous characters
        filename = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', filename)
        filename = re.sub(r'\.\.', '_', filename)  # Prevent directory traversal
        filename = filename.strip('. ')  # Remove leading/trailing dots and spaces
        
        # Ensure filename is not empty and has reasonable length
        if not filename or len(filename) > 255:
            filename = f"file_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        
        return filename


class DataEncryption:
    """
    Utility class for data encryption/decryption.
    """
    
    @staticmethod
    def hash_phone_number(phone: str) -> str:
        """Hash phone number for privacy while maintaining searchability."""
        import hashlib
        return hashlib.sha256(f"{phone}{settings.SECRET_KEY}".encode()).hexdigest()[:16]
    
    @staticmethod
    def mask_phone_number(phone: str) -> str:
        """Mask phone number for display purposes."""
        if len(phone) < 4:
            return phone
        return phone[:-4] + '****'
    
    @staticmethod
    def mask_email(email: str) -> str:
        """Mask email for display purposes."""
        if '@' not in email:
            return email
        
        local, domain = email.split('@', 1)
        if len(local) <= 2:
            masked_local = local
        else:
            masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
        
        return f"{masked_local}@{domain}"


class SecurityAudit:
    """
    Security audit and logging utilities.
    """
    
    @staticmethod
    def log_security_event(event_type: str, request: HttpRequest, details: Dict[str, Any] = None):
        """Log security-related events."""
        if details is None:
            details = {}
        
        client_ip = SecurityMiddleware()._get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', 'unknown')
        
        audit_data = {
            'event_type': event_type,
            'timestamp': timezone.now().isoformat(),
            'client_ip': client_ip,
            'user_agent': user_agent,
            'path': request.path,
            'method': request.method,
            'details': details
        }
        
        logger.warning(f"Security Event: {json.dumps(audit_data)}")
    
    @staticmethod
    def log_failed_authentication(request: HttpRequest, reason: str):
        """Log failed authentication attempts."""
        SecurityAudit.log_security_event(
            'failed_authentication',
            request,
            {'reason': reason}
        )
    
    @staticmethod
    def log_suspicious_activity(request: HttpRequest, activity: str):
        """Log suspicious activity."""
        SecurityAudit.log_security_event(
            'suspicious_activity',
            request,
            {'activity': activity}
        )
    
    @staticmethod
    def log_data_access(request: HttpRequest, resource: str, action: str):
        """Log data access for audit trail."""
        SecurityAudit.log_security_event(
            'data_access',
            request,
            {'resource': resource, 'action': action}
        )


def require_workspace_access(view_func):
    """
    Decorator to ensure user has access to the requested workspace.
    """
    def wrapper(request, *args, **kwargs):
        # This would be implemented based on your authentication system
        # For now, we'll just pass through
        return view_func(request, *args, **kwargs)
    return wrapper


def sanitize_request_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize request data recursively.
    """
    sanitizer = InputSanitizationMixin()
    
    def _sanitize_value(value):
        if isinstance(value, str):
            return sanitizer.sanitize_text(value)
        elif isinstance(value, dict):
            return {k: _sanitize_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [_sanitize_value(item) for item in value]
        return value
    
    return _sanitize_value(data)
