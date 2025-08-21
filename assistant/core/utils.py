import secrets
import string
import hashlib
import phonenumbers
from phonenumbers import NumberParseException
from django.core.cache import cache
from django.conf import settings
from typing import Optional, Tuple
from .models import Session, Contact, Workspace


def generate_session_token(length: int = 32) -> str:
    """Generate a cryptographically secure session token"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def normalize_phone_number(phone_number: str, default_region: str = 'US') -> Optional[str]:
    """
    Normalize phone number to E.164 format
    
    Args:
        phone_number: Raw phone number string
        default_region: Default country code if not provided
        
    Returns:
        Normalized phone number in E.164 format or None if invalid
    """
    try:
        # Parse the phone number
        parsed_number = phonenumbers.parse(phone_number, default_region)
        
        # Check if it's valid
        if not phonenumbers.is_valid_number(parsed_number):
            return None
        
        # Format to E.164
        return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)
        
    except NumberParseException:
        return None


def create_customer_session(phone_number: str, workspace_id: str) -> Tuple[Optional[Session], bool, str]:
    """
    Create a new customer session
    
    Args:
        phone_number: Customer's phone number
        workspace_id: Workspace UUID
        
    Returns:
        Tuple of (Session object, is_new_contact, error_message)
    """
    try:
        # Normalize phone number
        normalized_phone = normalize_phone_number(phone_number)
        if not normalized_phone:
            return None, False, "Invalid phone number format"
        
        # Get workspace
        try:
            workspace = Workspace.objects.get(id=workspace_id)
        except Workspace.DoesNotExist:
            return None, False, "Workspace not found"
        
        # Get or create contact
        contact, is_new_contact = Contact.objects.get_or_create(
            workspace=workspace,
            phone_e164=normalized_phone,
            defaults={'name': ''}
        )
        
        # Deactivate existing sessions for this contact
        Session.objects.filter(contact=contact, is_active=True).update(is_active=False)
        
        # Create new session
        session_token = generate_session_token()
        session = Session.objects.create(
            contact=contact,
            session_token=session_token,
            is_active=True
        )
        
        return session, is_new_contact, ""
        
    except Exception as e:
        return None, False, str(e)


def validate_session_token(session_token: str) -> Optional[Session]:
    """
    Validate a session token and return the session if valid
    
    Args:
        session_token: Session token to validate
        
    Returns:
        Session object if valid, None otherwise
    """
    try:
        session = Session.objects.select_related(
            'contact', 'contact__workspace'
        ).get(
            session_token=session_token,
            is_active=True
        )
        
        # Update last seen timestamp
        session.save()
        
        return session
        
    except Session.DoesNotExist:
        return None


def get_session_cache_key(session_token: str) -> str:
    """Generate cache key for session data"""
    return f"session:{hashlib.md5(session_token.encode()).hexdigest()}"


def cache_session_data(session: Session, timeout: int = 3600) -> None:
    """Cache session data for faster lookups"""
    cache_key = get_session_cache_key(session.session_token)
    session_data = {
        'session_id': str(session.id),
        'contact_id': str(session.contact.id),
        'contact_name': session.contact.name,
        'workspace_id': str(session.contact.workspace.id),
        'workspace_name': session.contact.workspace.name,
        'assistant_name': session.contact.workspace.assistant_name,
        'auto_reply_mode': session.contact.workspace.auto_reply_mode,
    }
    cache.set(cache_key, session_data, timeout)


def get_cached_session_data(session_token: str) -> Optional[dict]:
    """Retrieve cached session data"""
    cache_key = get_session_cache_key(session_token)
    return cache.get(cache_key)


def invalidate_session_cache(session_token: str) -> None:
    """Invalidate cached session data"""
    cache_key = get_session_cache_key(session_token)
    cache.delete(cache_key)


def mask_phone_number(phone_number: str, visible_digits: int = 2) -> str:
    """
    Mask phone number for privacy
    
    Args:
        phone_number: Phone number to mask
        visible_digits: Number of digits to show at the end
        
    Returns:
        Masked phone number
    """
    if len(phone_number) <= visible_digits:
        return phone_number
    
    mask_length = len(phone_number) - visible_digits
    return '*' * mask_length + phone_number[-visible_digits:]


def is_business_hours(workspace: Workspace) -> bool:
    """
    Check if current time is within business hours for the workspace
    
    Args:
        workspace: Workspace object
        
    Returns:
        True if within business hours, False otherwise
    """
    from datetime import datetime
    import pytz
    
    try:
        # Get current time in workspace timezone
        tz = pytz.timezone(workspace.timezone)
        now = datetime.now(tz)
        
        # Get day of week (Monday = 0)
        day_name = now.strftime('%A').lower()
        
        # Check business hours
        business_hours = workspace.business_hours or {}
        day_config = business_hours.get(day_name, {})
        
        # If day is marked as closed
        if day_config.get('closed', False):
            return False
        
        # Check time range
        start_time = day_config.get('start')
        end_time = day_config.get('end')
        
        if not start_time or not end_time:
            return True  # Default to always open if not configured
        
        # Parse times
        start_hour, start_min = map(int, start_time.split(':'))
        end_hour, end_min = map(int, end_time.split(':'))
        
        current_minutes = now.hour * 60 + now.minute
        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min
        
        return start_minutes <= current_minutes <= end_minutes
        
    except Exception:
        # Default to open if there's any error
        return True


def get_rate_limit_key(identifier: str, action: str) -> str:
    """Generate rate limiting cache key"""
    return f"rate_limit:{action}:{hashlib.md5(identifier.encode()).hexdigest()}"


def check_rate_limit(identifier: str, action: str, limit: int, window: int = 3600) -> Tuple[bool, int]:
    """
    Check if action is rate limited
    
    Args:
        identifier: Unique identifier (IP, session token, etc.)
        action: Action being rate limited
        limit: Maximum number of actions allowed
        window: Time window in seconds
        
    Returns:
        Tuple of (is_allowed, remaining_attempts)
    """
    cache_key = get_rate_limit_key(identifier, action)
    
    try:
        current_count = cache.get(cache_key, 0)
        
        if current_count >= limit:
            return False, 0
        
        # Increment counter
        cache.set(cache_key, current_count + 1, window)
        
        return True, limit - current_count - 1
        
    except Exception:
        # Allow action if cache fails
        return True, limit - 1

