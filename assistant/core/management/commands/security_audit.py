"""
Django management command for security auditing and monitoring.
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta
import logging
import os
import json

from core.models import Session, Conversation, Contact
from messaging.models import Message

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Perform security audit and generate security reports'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days to analyze (default: 7)',
        )
        parser.add_argument(
            '--output',
            type=str,
            default='security_report.json',
            help='Output file for the security report',
        )
        parser.add_argument(
            '--check-sessions',
            action='store_true',
            help='Check for suspicious session patterns',
        )
        parser.add_argument(
            '--check-uploads',
            action='store_true',
            help='Check for suspicious file uploads',
        )
        parser.add_argument(
            '--check-messages',
            action='store_true',
            help='Check for suspicious message patterns',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Run all security checks',
        )
    
    def handle(self, *args, **options):
        days = options['days']
        output_file = options['output']
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting security audit for the last {days} days...')
        )
        
        # Calculate date range
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Initialize report
        report = {
            'audit_timestamp': end_date.isoformat(),
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days
            },
            'summary': {},
            'findings': [],
            'recommendations': []
        }
        
        # Run security checks
        if options['all'] or options['check_sessions']:
            self.check_session_security(start_date, end_date, report)
        
        if options['all'] or options['check_uploads']:
            self.check_upload_security(start_date, end_date, report)
        
        if options['all'] or options['check_messages']:
            self.check_message_security(start_date, end_date, report)
        
        # Add general statistics
        self.add_general_statistics(start_date, end_date, report)
        
        # Generate recommendations
        self.generate_recommendations(report)
        
        # Save report
        self.save_report(report, output_file)
        
        self.stdout.write(
            self.style.SUCCESS(f'Security audit completed. Report saved to {output_file}')
        )
    
    def check_session_security(self, start_date, end_date, report):
        """Check for suspicious session patterns."""
        self.stdout.write('Checking session security...')
        
        # Get session statistics
        total_sessions = Session.objects.filter(
            created_at__range=[start_date, end_date]
        ).count()
        
        active_sessions = Session.objects.filter(
            created_at__range=[start_date, end_date],
            is_active=True
        ).count()
        
        # Check for sessions with unusual patterns
        suspicious_sessions = []
        
        # Sessions with very high message counts
        high_activity_sessions = Session.objects.filter(
            created_at__range=[start_date, end_date]
        ).annotate(
            message_count=Count('conversation__message')
        ).filter(message_count__gt=1000)
        
        for session in high_activity_sessions:
            suspicious_sessions.append({
                'session_id': str(session.id),
                'issue': 'High message volume',
                'message_count': session.message_count,
                'created_at': session.created_at.isoformat()
            })
        
        # Sessions with rapid creation from same IP (if tracked)
        # This would require IP tracking implementation
        
        report['summary']['sessions'] = {
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'suspicious_sessions': len(suspicious_sessions)
        }
        
        if suspicious_sessions:
            report['findings'].append({
                'category': 'Session Security',
                'severity': 'medium',
                'count': len(suspicious_sessions),
                'description': 'Sessions with suspicious activity patterns detected',
                'details': suspicious_sessions
            })
    
    def check_upload_security(self, start_date, end_date, report):
        """Check for suspicious file upload patterns."""
        self.stdout.write('Checking upload security...')
        
        # Get upload statistics
        total_uploads = Message.objects.filter(
            created_at__range=[start_date, end_date],
            message_type='file'
        ).count()
        
        audio_uploads = Message.objects.filter(
            created_at__range=[start_date, end_date],
            message_type='audio'
        ).count()
        
        # Check for suspicious upload patterns
        suspicious_uploads = []
        
        # Messages with very large files (if size tracking is implemented)
        # This would require file size tracking in the Message model
        
        # Messages with suspicious file types
        suspicious_extensions = ['.exe', '.bat', '.cmd', '.scr', '.php', '.js']
        for ext in suspicious_extensions:
            suspicious_files = Message.objects.filter(
                created_at__range=[start_date, end_date],
                message_type='file',
                media_filename__iendswith=ext
            )
            
            for msg in suspicious_files:
                suspicious_uploads.append({
                    'message_id': str(msg.id),
                    'issue': f'Suspicious file extension: {ext}',
                    'filename': msg.media_filename,
                    'created_at': msg.created_at.isoformat()
                })
        
        report['summary']['uploads'] = {
            'total_uploads': total_uploads,
            'audio_uploads': audio_uploads,
            'suspicious_uploads': len(suspicious_uploads)
        }
        
        if suspicious_uploads:
            report['findings'].append({
                'category': 'Upload Security',
                'severity': 'high',
                'count': len(suspicious_uploads),
                'description': 'Suspicious file uploads detected',
                'details': suspicious_uploads
            })
    
    def check_message_security(self, start_date, end_date, report):
        """Check for suspicious message patterns."""
        self.stdout.write('Checking message security...')
        
        # Get message statistics
        total_messages = Message.objects.filter(
            created_at__range=[start_date, end_date]
        ).count()
        
        # Check for suspicious content patterns
        suspicious_messages = []
        
        # Messages with potential script injection attempts
        script_patterns = ['<script', 'javascript:', 'eval(', 'exec(']
        for pattern in script_patterns:
            suspicious_msgs = Message.objects.filter(
                created_at__range=[start_date, end_date],
                content__icontains=pattern
            )
            
            for msg in suspicious_msgs:
                suspicious_messages.append({
                    'message_id': str(msg.id),
                    'issue': f'Potential script injection: {pattern}',
                    'sender': msg.sender,
                    'created_at': msg.created_at.isoformat()
                })
        
        # Messages with very long content (potential DoS)
        long_messages = Message.objects.filter(
            created_at__range=[start_date, end_date],
            content__isnull=False
        ).extra(where=["LENGTH(content) > %s"], params=[10000])
        
        for msg in long_messages:
            suspicious_messages.append({
                'message_id': str(msg.id),
                'issue': 'Extremely long message content',
                'content_length': len(msg.content or ''),
                'sender': msg.sender,
                'created_at': msg.created_at.isoformat()
            })
        
        report['summary']['messages'] = {
            'total_messages': total_messages,
            'suspicious_messages': len(suspicious_messages)
        }
        
        if suspicious_messages:
            report['findings'].append({
                'category': 'Message Security',
                'severity': 'high',
                'count': len(suspicious_messages),
                'description': 'Suspicious message patterns detected',
                'details': suspicious_messages
            })
    
    def add_general_statistics(self, start_date, end_date, report):
        """Add general security statistics."""
        
        # Count total conversations
        total_conversations = Conversation.objects.filter(
            created_at__range=[start_date, end_date]
        ).count()
        
        # Count unique contacts
        unique_contacts = Contact.objects.filter(
            created_at__range=[start_date, end_date]
        ).count()
        
        report['summary']['general'] = {
            'total_conversations': total_conversations,
            'unique_contacts': unique_contacts,
            'period_days': (end_date - start_date).days
        }
    
    def generate_recommendations(self, report):
        """Generate security recommendations based on findings."""
        
        recommendations = []
        
        # General recommendations
        recommendations.append({
            'priority': 'high',
            'category': 'General Security',
            'recommendation': 'Ensure all security middleware is properly configured and active',
            'action': 'Review Django settings for security headers and middleware'
        })
        
        recommendations.append({
            'priority': 'medium',
            'category': 'Monitoring',
            'recommendation': 'Set up automated security monitoring and alerting',
            'action': 'Configure log monitoring for security events'
        })
        
        # Specific recommendations based on findings
        for finding in report['findings']:
            if finding['category'] == 'Session Security':
                recommendations.append({
                    'priority': 'medium',
                    'category': 'Session Management',
                    'recommendation': 'Review session timeout and cleanup policies',
                    'action': 'Implement automated cleanup of old sessions'
                })
            
            elif finding['category'] == 'Upload Security':
                recommendations.append({
                    'priority': 'high',
                    'category': 'File Security',
                    'recommendation': 'Strengthen file upload validation and scanning',
                    'action': 'Review and update file type restrictions and virus scanning'
                })
            
            elif finding['category'] == 'Message Security':
                recommendations.append({
                    'priority': 'high',
                    'category': 'Input Validation',
                    'recommendation': 'Enhance input sanitization and validation',
                    'action': 'Review and strengthen content filtering rules'
                })
        
        report['recommendations'] = recommendations
    
    def save_report(self, report, output_file):
        """Save the security report to a file."""
        
        # Ensure logs directory exists
        logs_dir = settings.BASE_DIR / 'logs'
        logs_dir.mkdir(exist_ok=True)
        
        # Save to logs directory
        report_path = logs_dir / output_file
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        self.stdout.write(f'Report saved to: {report_path}')
