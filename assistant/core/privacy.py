"""
Data privacy and GDPR compliance utilities for the AI Personal Business Assistant.
"""
from typing import Dict, List, Optional, Any
from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


class DataPrivacyManager:
    """
    Handles data privacy operations including GDPR compliance,
    data anonymization, and retention policies.
    """
    
    def __init__(self):
        self.retention_periods = {
            'session': timedelta(days=90),  # 3 months
            'conversation': timedelta(days=365),  # 1 year
            'message': timedelta(days=365),  # 1 year
            'audio_transcription': timedelta(days=180),  # 6 months
            'knowledge_base': timedelta(days=1095),  # 3 years
            'audit_logs': timedelta(days=2555),  # 7 years
        }
    
    def anonymize_personal_data(self, contact_id: str) -> Dict[str, Any]:
        """
        Anonymize personal data for a contact while preserving business value.
        
        Args:
            contact_id: UUID of the contact to anonymize
            
        Returns:
            Dict containing anonymization results
        """
        from core.models import Contact, Session, Conversation
        from messaging.models import Message
        
        try:
            with transaction.atomic():
                # Get the contact
                contact = Contact.objects.get(id=contact_id)
                original_phone = contact.phone_number
                original_email = contact.email
                
                # Create anonymized identifiers
                anon_phone = self._anonymize_phone(contact.phone_number)
                anon_email = self._anonymize_email(contact.email) if contact.email else None
                
                # Update contact record
                contact.phone_number = anon_phone
                contact.email = anon_email
                contact.first_name = "Anonymous"
                contact.last_name = "User"
                contact.save()
                
                # Update related messages
                messages_updated = Message.objects.filter(
                    conversation__contact=contact
                ).update(
                    sender=f"anonymous_{contact.id[:8]}"
                )
                
                # Log the anonymization
                logger.info(f"Anonymized contact {contact_id}: {messages_updated} messages updated")
                
                return {
                    'success': True,
                    'contact_id': contact_id,
                    'messages_anonymized': messages_updated,
                    'anonymized_phone': anon_phone,
                    'anonymized_email': anon_email,
                    'timestamp': timezone.now().isoformat()
                }
                
        except Contact.DoesNotExist:
            return {
                'success': False,
                'error': 'Contact not found',
                'contact_id': contact_id
            }
        except Exception as e:
            logger.error(f"Error anonymizing contact {contact_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'contact_id': contact_id
            }
    
    def delete_personal_data(self, contact_id: str, hard_delete: bool = False) -> Dict[str, Any]:
        """
        Delete or soft-delete personal data for a contact.
        
        Args:
            contact_id: UUID of the contact
            hard_delete: If True, permanently delete; if False, soft delete
            
        Returns:
            Dict containing deletion results
        """
        from core.models import Contact, Session, Conversation
        from messaging.models import Message, AudioTranscription
        
        try:
            with transaction.atomic():
                contact = Contact.objects.get(id=contact_id)
                
                # Get related data counts
                sessions = Session.objects.filter(contact=contact)
                conversations = Conversation.objects.filter(contact=contact)
                messages = Message.objects.filter(conversation__contact=contact)
                transcriptions = AudioTranscription.objects.filter(
                    message__conversation__contact=contact
                )
                
                counts = {
                    'sessions': sessions.count(),
                    'conversations': conversations.count(),
                    'messages': messages.count(),
                    'transcriptions': transcriptions.count()
                }
                
                if hard_delete:
                    # Permanently delete all related data
                    transcriptions.delete()
                    messages.delete()
                    conversations.delete()
                    sessions.delete()
                    contact.delete()
                    
                    logger.warning(f"Hard deleted contact {contact_id} and all related data")
                    
                else:
                    # Soft delete - mark as deleted but keep for audit
                    contact.is_active = False
                    contact.deleted_at = timezone.now()
                    contact.deletion_reason = 'user_request'
                    contact.save()
                    
                    # Mark conversations as deleted
                    conversations.update(
                        status='deleted',
                        updated_at=timezone.now()
                    )
                    
                    logger.info(f"Soft deleted contact {contact_id}")
                
                return {
                    'success': True,
                    'contact_id': contact_id,
                    'deletion_type': 'hard' if hard_delete else 'soft',
                    'deleted_counts': counts,
                    'timestamp': timezone.now().isoformat()
                }
                
        except Contact.DoesNotExist:
            return {
                'success': False,
                'error': 'Contact not found',
                'contact_id': contact_id
            }
        except Exception as e:
            logger.error(f"Error deleting contact {contact_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'contact_id': contact_id
            }
    
    def export_personal_data(self, contact_id: str) -> Dict[str, Any]:
        """
        Export all personal data for a contact (GDPR data portability).
        
        Args:
            contact_id: UUID of the contact
            
        Returns:
            Dict containing exported data
        """
        from core.models import Contact, Session, Conversation
        from messaging.models import Message, AudioTranscription
        
        try:
            contact = Contact.objects.get(id=contact_id)
            
            # Export contact data
            contact_data = {
                'id': str(contact.id),
                'phone_number': contact.phone_number,
                'email': contact.email,
                'first_name': contact.first_name,
                'last_name': contact.last_name,
                'created_at': contact.created_at.isoformat(),
                'updated_at': contact.updated_at.isoformat(),
            }
            
            # Export sessions
            sessions_data = []
            for session in Session.objects.filter(contact=contact):
                sessions_data.append({
                    'id': str(session.id),
                    'token': session.token[:8] + '...',  # Partial token for identification
                    'created_at': session.created_at.isoformat(),
                    'is_active': session.is_active,
                })
            
            # Export conversations and messages
            conversations_data = []
            for conversation in Conversation.objects.filter(contact=contact):
                messages_data = []
                for message in Message.objects.filter(conversation=conversation):
                    message_data = {
                        'id': str(message.id),
                        'sender': message.sender,
                        'content': message.content,
                        'message_type': message.message_type,
                        'created_at': message.created_at.isoformat(),
                    }
                    
                    # Add transcription if available
                    try:
                        transcription = message.transcription
                        message_data['transcription'] = {
                            'text': transcription.transcribed_text,
                            'language': transcription.language,
                            'confidence': transcription.confidence,
                        }
                    except AudioTranscription.DoesNotExist:
                        pass
                    
                    messages_data.append(message_data)
                
                conversations_data.append({
                    'id': str(conversation.id),
                    'title': conversation.title,
                    'status': conversation.status,
                    'created_at': conversation.created_at.isoformat(),
                    'updated_at': conversation.updated_at.isoformat(),
                    'messages': messages_data,
                })
            
            export_data = {
                'export_timestamp': timezone.now().isoformat(),
                'contact': contact_data,
                'sessions': sessions_data,
                'conversations': conversations_data,
                'metadata': {
                    'total_sessions': len(sessions_data),
                    'total_conversations': len(conversations_data),
                    'total_messages': sum(len(conv['messages']) for conv in conversations_data),
                }
            }
            
            logger.info(f"Exported data for contact {contact_id}")
            
            return {
                'success': True,
                'data': export_data
            }
            
        except Contact.DoesNotExist:
            return {
                'success': False,
                'error': 'Contact not found',
                'contact_id': contact_id
            }
        except Exception as e:
            logger.error(f"Error exporting data for contact {contact_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'contact_id': contact_id
            }
    
    def cleanup_expired_data(self) -> Dict[str, Any]:
        """
        Clean up expired data based on retention policies.
        
        Returns:
            Dict containing cleanup results
        """
        from core.models import Session, Conversation
        from messaging.models import Message, AudioTranscription
        
        cleanup_results = {
            'timestamp': timezone.now().isoformat(),
            'cleaned_up': {},
            'errors': []
        }
        
        current_time = timezone.now()
        
        try:
            # Clean up expired sessions
            session_cutoff = current_time - self.retention_periods['session']
            expired_sessions = Session.objects.filter(
                created_at__lt=session_cutoff,
                is_active=False
            )
            session_count = expired_sessions.count()
            expired_sessions.delete()
            cleanup_results['cleaned_up']['sessions'] = session_count
            
            # Clean up expired transcriptions
            transcription_cutoff = current_time - self.retention_periods['audio_transcription']
            expired_transcriptions = AudioTranscription.objects.filter(
                created_at__lt=transcription_cutoff
            )
            transcription_count = expired_transcriptions.count()
            expired_transcriptions.delete()
            cleanup_results['cleaned_up']['transcriptions'] = transcription_count
            
            # Clean up old conversations (soft delete only)
            conversation_cutoff = current_time - self.retention_periods['conversation']
            old_conversations = Conversation.objects.filter(
                created_at__lt=conversation_cutoff,
                status='completed'
            )
            conversation_count = old_conversations.update(
                status='archived',
                updated_at=current_time
            )
            cleanup_results['cleaned_up']['conversations_archived'] = conversation_count
            
            logger.info(f"Data cleanup completed: {cleanup_results['cleaned_up']}")
            
        except Exception as e:
            error_msg = f"Error during data cleanup: {str(e)}"
            logger.error(error_msg)
            cleanup_results['errors'].append(error_msg)
        
        return cleanup_results
    
    def _anonymize_phone(self, phone: str) -> str:
        """Generate anonymized phone number."""
        # Create hash-based anonymized phone
        phone_hash = hashlib.sha256(f"{phone}{settings.SECRET_KEY}".encode()).hexdigest()
        return f"+1555{phone_hash[:7]}"  # Fake US number format
    
    def _anonymize_email(self, email: str) -> str:
        """Generate anonymized email address."""
        if not email:
            return None
        
        email_hash = hashlib.sha256(f"{email}{settings.SECRET_KEY}".encode()).hexdigest()
        return f"anonymous_{email_hash[:8]}@example.com"
    
    def generate_privacy_report(self, workspace_id: str) -> Dict[str, Any]:
        """
        Generate privacy compliance report for a workspace.
        
        Args:
            workspace_id: UUID of the workspace
            
        Returns:
            Dict containing privacy report
        """
        from core.models import Workspace, Contact, Conversation
        from messaging.models import Message
        
        try:
            workspace = Workspace.objects.get(id=workspace_id)
            current_time = timezone.now()
            
            # Count data by age
            data_age_buckets = {
                'last_30_days': current_time - timedelta(days=30),
                'last_90_days': current_time - timedelta(days=90),
                'last_year': current_time - timedelta(days=365),
                'older_than_year': None
            }
            
            report = {
                'workspace_id': workspace_id,
                'workspace_name': workspace.business_name,
                'report_timestamp': current_time.isoformat(),
                'data_summary': {},
                'retention_compliance': {},
                'recommendations': []
            }
            
            # Analyze contact data
            total_contacts = Contact.objects.filter(workspace=workspace).count()
            active_contacts = Contact.objects.filter(
                workspace=workspace,
                is_active=True
            ).count()
            
            # Analyze conversation data by age
            conversations_by_age = {}
            for bucket, cutoff_date in data_age_buckets.items():
                if cutoff_date:
                    count = Conversation.objects.filter(
                        workspace=workspace,
                        created_at__gte=cutoff_date
                    ).count()
                else:
                    count = Conversation.objects.filter(
                        workspace=workspace,
                        created_at__lt=data_age_buckets['last_year']
                    ).count()
                conversations_by_age[bucket] = count
            
            # Analyze message data
            total_messages = Message.objects.filter(
                conversation__workspace=workspace
            ).count()
            
            report['data_summary'] = {
                'total_contacts': total_contacts,
                'active_contacts': active_contacts,
                'total_conversations': sum(conversations_by_age.values()),
                'conversations_by_age': conversations_by_age,
                'total_messages': total_messages
            }
            
            # Check retention compliance
            retention_issues = []
            old_conversations = conversations_by_age.get('older_than_year', 0)
            if old_conversations > 0:
                retention_issues.append(
                    f"{old_conversations} conversations are older than retention policy"
                )
            
            report['retention_compliance'] = {
                'compliant': len(retention_issues) == 0,
                'issues': retention_issues
            }
            
            # Generate recommendations
            recommendations = []
            if old_conversations > 0:
                recommendations.append({
                    'priority': 'medium',
                    'type': 'retention',
                    'message': 'Consider archiving or anonymizing old conversations',
                    'action': f'Review {old_conversations} conversations older than 1 year'
                })
            
            if total_contacts > 1000:
                recommendations.append({
                    'priority': 'low',
                    'type': 'optimization',
                    'message': 'Large contact database - consider data optimization',
                    'action': 'Review contact data cleanup policies'
                })
            
            report['recommendations'] = recommendations
            
            return {
                'success': True,
                'report': report
            }
            
        except Workspace.DoesNotExist:
            return {
                'success': False,
                'error': 'Workspace not found',
                'workspace_id': workspace_id
            }
        except Exception as e:
            logger.error(f"Error generating privacy report for {workspace_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'workspace_id': workspace_id
            }


# Global instance
privacy_manager = DataPrivacyManager()
