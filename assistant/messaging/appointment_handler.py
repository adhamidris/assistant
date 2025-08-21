"""
Appointment booking handler for AI responses
"""
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from django.utils import timezone
from calendar_integration.models import Appointment
from core.models import Contact, Workspace

logger = logging.getLogger(__name__)

class AppointmentBookingHandler:
    """Handle appointment booking from AI conversations"""
    
    def __init__(self):
        self.appointment_keywords = [
            'appointment', 'booking', 'schedule', 'meeting', 'consultation',
            'visit', 'session', 'checkup', 'check-up'
        ]
        
    def extract_appointment_intent(self, message_text: str) -> Dict:
        """Extract appointment booking intent from message"""
        message_lower = message_text.lower()
        
        # Check if message contains appointment keywords
        has_appointment_keyword = any(keyword in message_lower for keyword in self.appointment_keywords)
        
        if not has_appointment_keyword:
            return {'is_appointment_request': False}
        
        # Extract date/time information
        date_info = self._extract_date_time(message_text)
        
        return {
            'is_appointment_request': True,
            'extracted_datetime': date_info.get('datetime'),
            'date_text': date_info.get('text'),
            'confidence': 0.8 if date_info.get('datetime') else 0.6
        }
    
    def _extract_date_time(self, text: str) -> Dict:
        """Extract date and time from text"""
        # Simple patterns for common date/time expressions
        patterns = [
            r'(?:tomorrow|tmrw)\s*(?:at\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)',
            r'(?:next|this)\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)',
            r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})',
            r'(\d{1,2})\s*(?:am|pm)',
            r'in\s+(\d+)\s+(hour|day|week)s?',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                # For now, return a placeholder datetime
                # In production, you'd want proper date parsing
                suggested_time = timezone.now() + timedelta(days=1)
                return {
                    'datetime': suggested_time,
                    'text': match.group(0),
                    'parsed': True
                }
        
        return {'parsed': False}
    
    def create_appointment_from_ai_response(
        self, 
        conversation, 
        ai_response_text: str,
        original_message: str
    ) -> Optional[Appointment]:
        """Create appointment if AI response indicates booking confirmation"""
        
        # Check if AI response indicates appointment was booked
        booking_indicators = [
            'booked', 'scheduled', 'confirmed', 'appointment set',
            'reserved', 'i have scheduled', 'i have booked'
        ]
        
        ai_response_lower = ai_response_text.lower()
        indicates_booking = any(indicator in ai_response_lower for indicator in booking_indicators)
        
        if not indicates_booking:
            return None
        
        try:
            # Extract appointment details from AI response
            appointment_details = self._parse_appointment_from_ai_response(ai_response_text)
            
            # Create appointment
            appointment = Appointment.objects.create(
                workspace=conversation.workspace,
                contact=conversation.contact,
                title=appointment_details.get('title', 'Appointment'),
                description=appointment_details.get('description', f"Booked via AI: {original_message[:100]}"),
                start_time=appointment_details.get('start_time', timezone.now() + timedelta(days=1)),
                end_time=appointment_details.get('end_time', timezone.now() + timedelta(days=1, hours=1)),
                status='confirmed',
                customer_notes=f"Original request: {original_message}\nAI Response: {ai_response_text[:200]}"
            )
            
            logger.info(f"Created appointment {appointment.id} from AI conversation")
            return appointment
            
        except Exception as e:
            logger.error(f"Failed to create appointment from AI response: {str(e)}")
            return None
    
    def _parse_appointment_from_ai_response(self, ai_response: str) -> Dict:
        """Parse appointment details from AI response"""
        # Default appointment details
        details = {
            'title': 'Appointment',
            'description': 'Appointment booked via AI assistant',
            'start_time': timezone.now() + timedelta(days=1),  # Tomorrow
            'end_time': timezone.now() + timedelta(days=1, hours=1)  # Tomorrow + 1 hour
        }
        
        # Try to extract specific appointment type
        appointment_types = {
            'consultation': 'Consultation',
            'checkup': 'Health Checkup',
            'check-up': 'Health Checkup',
            'meeting': 'Business Meeting',
            'session': 'Session',
            'visit': 'Visit'
        }
        
        for keyword, title in appointment_types.items():
            if keyword in ai_response.lower():
                details['title'] = title
                break
        
        # Try to extract time information from AI response
        time_patterns = [
            r'(?:at|for)\s*(\d{1,2}(?::\d{2})?\s*(?:am|pm))',
            r'(?:tomorrow|next day)\s*(?:at\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)',
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, ai_response.lower())
            if match:
                # For now, just use default times
                # In production, you'd parse the actual time
                break
        
        return details
    
    def get_available_slots(self, workspace: Workspace, days_ahead: int = 7) -> List[Dict]:
        """Get available appointment slots for the next few days"""
        available_slots = []
        start_date = timezone.now().date()
        
        for i in range(days_ahead):
            date = start_date + timedelta(days=i)
            
            # Skip weekends for business appointments
            if date.weekday() >= 5:  # Saturday = 5, Sunday = 6
                continue
            
            # Generate time slots (9 AM to 5 PM)
            for hour in range(9, 17):
                slot_time = timezone.make_aware(
                    datetime.combine(date, datetime.min.time().replace(hour=hour))
                )
                
                # Check if slot is available (not booked)
                existing_appointment = Appointment.objects.filter(
                    workspace=workspace,
                    start_time__date=date,
                    start_time__hour=hour,
                    status__in=['confirmed', 'pending']
                ).exists()
                
                if not existing_appointment:
                    available_slots.append({
                        'datetime': slot_time,
                        'display': slot_time.strftime('%A, %B %d at %I:%M %p'),
                        'available': True
                    })
        
        return available_slots[:10]  # Return first 10 available slots

# Global instance
appointment_handler = AppointmentBookingHandler()
