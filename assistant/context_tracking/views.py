from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from django.db.models import Q, Count, Avg
import time
import logging

from core.models import Workspace, Conversation
from .models import (
    WorkspaceContextSchema, ConversationContext, 
    ContextHistory, BusinessRule, RuleExecution
)
from .serializers import (
    WorkspaceContextSchemaSerializer, ConversationContextSerializer,
    ContextHistorySerializer, BusinessRuleSerializer, RuleExecutionSerializer,
    ContextExtractionRequestSerializer, ContextUpdateSerializer,
    SchemaTestSerializer, RuleTestSerializer
)
from .services import ContextExtractionService, RuleEngineService

logger = logging.getLogger(__name__)


class WorkspaceContextSchemaViewSet(viewsets.ModelViewSet):
    """ViewSet for managing workspace context schemas"""
    
    serializer_class = WorkspaceContextSchemaSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        workspace_id = self.kwargs.get('workspace_pk') or self.request.query_params.get('workspace')
        if workspace_id:
            return WorkspaceContextSchema.objects.filter(workspace_id=workspace_id)
        return WorkspaceContextSchema.objects.none()
    
    def perform_create(self, serializer):
        workspace_id = self.kwargs.get('workspace_pk') or self.request.data.get('workspace')
        workspace = get_object_or_404(Workspace, id=workspace_id)
        
        # If this is marked as default, unset other defaults
        if serializer.validated_data.get('is_default', False):
            WorkspaceContextSchema.objects.filter(
                workspace=workspace, is_default=True
            ).update(is_default=False)
        
        serializer.save(workspace=workspace, created_by=self.request.user)
    
    def perform_update(self, serializer):
        # If this is marked as default, unset other defaults
        if serializer.validated_data.get('is_default', False):
            WorkspaceContextSchema.objects.filter(
                workspace=serializer.instance.workspace, is_default=True
            ).exclude(id=serializer.instance.id).update(is_default=False)
        
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, workspace_pk=None, pk=None):
        """Duplicate a schema with a new name"""
        schema = self.get_object()
        new_name = request.data.get('name', f"{schema.name} (Copy)")
        
        # Create duplicate
        new_schema = WorkspaceContextSchema.objects.create(
            workspace=schema.workspace,
            name=new_name,
            description=schema.description,
            fields=schema.fields.copy(),
            status_workflow=schema.status_workflow.copy(),
            priority_config=schema.priority_config.copy(),
            is_active=True,
            is_default=False,
            created_by=request.user
        )
        
        serializer = self.get_serializer(new_schema)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def test_configuration(self, request, workspace_pk=None, pk=None):
        """Test schema configuration with sample data"""
        schema = self.get_object()
        serializer = SchemaTestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        test_data = serializer.validated_data['test_data']
        results = {}
        
        if serializer.validated_data.get('test_priority_calculation', True):
            results['priority'] = schema.calculate_priority(test_data)
        
        if serializer.validated_data.get('test_status_transitions', True):
            current_status = test_data.get('status', 'new')
            status_choices = schema.get_status_choices()
            
            # Test available transitions
            available_transitions = []
            for status in status_choices:
                if schema.can_transition_status(current_status, status['id']):
                    available_transitions.append(status['id'])
            
            results['status_transitions'] = {
                'current_status': current_status,
                'available_transitions': available_transitions,
                'all_statuses': [s['id'] for s in status_choices]
            }
        
        if serializer.validated_data.get('test_field_validation', True):
            # Test field validation
            field_errors = []
            for field in schema.fields:
                field_id = field.get('id')
                field_value = test_data.get(field_id)
                
                # Check required fields
                if field.get('required', False) and (field_value is None or field_value == ''):
                    field_errors.append(f"Required field '{field['name']}' is missing")
                
                # Check field type validation
                if field_value is not None:
                    type_errors = schema._validate_field_value(field, field_value)
                    field_errors.extend(type_errors)
            
            results['field_validation'] = {
                'valid': len(field_errors) == 0,
                'errors': field_errors
            }
        
        return Response(results)
    
    @action(detail=True, methods=['post'])
    def validate_schema(self, request, workspace_pk=None, pk=None):
        """Validate schema structure and return any errors"""
        schema = self.get_object()
        validation_errors = schema.validate_schema()
        
        return Response({
            'valid': len(validation_errors) == 0,
            'errors': validation_errors,
            'field_count': schema.field_count,
            'required_field_count': schema.required_field_count
        })
    
    @action(detail=True, methods=['post'])
    def export_schema(self, request, workspace_pk=None, pk=None):
        """Export schema as JSON template"""
        schema = self.get_object()
        
        export_data = {
            'name': schema.name,
            'description': schema.description,
            'fields': schema.fields,
            'status_workflow': schema.status_workflow,
            'priority_config': schema.priority_config,
            'exported_at': timezone.now().isoformat(),
            'version': '1.0'
        }
        
        return Response(export_data)
    
    @action(detail=True, methods=['post'])
    def import_schema(self, request, workspace_pk=None, pk=None):
        """Import schema configuration from JSON"""
        schema = self.get_object()
        
        import_data = request.data.get('schema_data', {})
        if not import_data:
            return Response(
                {'error': 'No schema data provided'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate imported data
        try:
            # Update schema fields
            if 'fields' in import_data:
                schema.fields = import_data['fields']
            
            if 'status_workflow' in import_data:
                schema.status_workflow = import_data['status_workflow']
            
            if 'priority_config' in import_data:
                schema.priority_config = import_data['priority_config']
            
            # Validate the updated schema
            validation_errors = schema.validate_schema()
            if validation_errors:
                return Response({
                    'error': 'Invalid schema data',
                    'validation_errors': validation_errors
                }, status=status.HTTP_400_BAD_REQUEST)
            
            schema.save()
            serializer = self.get_serializer(schema)
            return Response(serializer.data)
            
        except Exception as e:
            return Response({
                'error': f'Import failed: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def schema_templates(self, request, workspace_pk=None):
        """Get available schema templates for this workspace"""
        workspace = get_object_or_404(Workspace, id=workspace_pk)
        
        templates = [
            {
                'id': 'customer_service',
                'name': 'Customer Service',
                'description': 'Track customer inquiries, complaints, and support requests',
                'fields': [
                    {'id': 'inquiry_type', 'name': 'Inquiry Type', 'type': 'choice', 'required': True, 'choices': ['General', 'Technical', 'Billing', 'Complaint']},
                    {'id': 'urgency', 'name': 'Urgency Level', 'type': 'choice', 'required': True, 'choices': ['Low', 'Medium', 'High', 'Critical']},
                    {'id': 'customer_tier', 'name': 'Customer Tier', 'type': 'choice', 'required': False, 'choices': ['Bronze', 'Silver', 'Gold', 'Platinum']},
                    {'id': 'assigned_to', 'name': 'Assigned To', 'type': 'text', 'required': False},
                    {'id': 'resolution_time', 'name': 'Expected Resolution Time', 'type': 'number', 'required': False},
                ],
                'status_workflow': {
                    'statuses': [
                        {'id': 'new', 'label': 'New', 'color': 'blue'},
                        {'id': 'assigned', 'label': 'Assigned', 'color': 'yellow'},
                        {'id': 'in_progress', 'label': 'In Progress', 'color': 'orange'},
                        {'id': 'waiting', 'label': 'Waiting for Customer', 'color': 'purple'},
                        {'id': 'resolved', 'label': 'Resolved', 'color': 'green'},
                        {'id': 'closed', 'label': 'Closed', 'color': 'gray'}
                    ],
                    'transitions': {
                        'new': ['assigned', 'in_progress'],
                        'assigned': ['in_progress', 'waiting'],
                        'in_progress': ['waiting', 'resolved'],
                        'waiting': ['in_progress', 'resolved'],
                        'resolved': ['closed'],
                        'closed': []
                    }
                },
                'priority_config': {
                    'default_priority': 'medium',
                    'rules': [
                        {'type': 'equals', 'field_id': 'urgency', 'condition': 'equals', 'value': 'Critical', 'priority': 'high'},
                        {'type': 'equals', 'field_id': 'urgency', 'condition': 'equals', 'value': 'High', 'priority': 'high'},
                        {'type': 'equals', 'field_id': 'customer_tier', 'condition': 'equals', 'value': 'Platinum', 'priority': 'high'}
                    ]
                }
            },
            {
                'id': 'appointment_booking',
                'name': 'Appointment Booking',
                'description': 'Manage appointment scheduling and confirmations',
                'fields': [
                    {'id': 'service_type', 'name': 'Service Type', 'type': 'choice', 'required': True, 'choices': ['Consultation', 'Treatment', 'Follow-up', 'Emergency']},
                    {'id': 'preferred_date', 'name': 'Preferred Date', 'type': 'date', 'required': True},
                    {'id': 'preferred_time', 'name': 'Preferred Time', 'type': 'choice', 'required': True, 'choices': ['Morning', 'Afternoon', 'Evening']},
                    {'id': 'duration', 'name': 'Duration (minutes)', 'type': 'number', 'required': True},
                    {'id': 'special_requirements', 'name': 'Special Requirements', 'type': 'textarea', 'required': False},
                    {'id': 'payment_method', 'name': 'Payment Method', 'type': 'choice', 'required': False, 'choices': ['Cash', 'Card', 'Insurance', 'Other']}
                ],
                'status_workflow': {
                    'statuses': [
                        {'id': 'requested', 'label': 'Requested', 'color': 'blue'},
                        {'id': 'confirmed', 'label': 'Confirmed', 'color': 'green'},
                        {'id': 'rescheduled', 'label': 'Rescheduled', 'color': 'yellow'},
                        {'id': 'cancelled', 'label': 'Cancelled', 'color': 'red'},
                        {'id': 'completed', 'label': 'Completed', 'color': 'gray'}
                    ],
                    'transitions': {
                        'requested': ['confirmed', 'rescheduled', 'cancelled'],
                        'confirmed': ['rescheduled', 'cancelled', 'completed'],
                        'rescheduled': ['confirmed', 'cancelled'],
                        'cancelled': [],
                        'completed': []
                    }
                },
                'priority_config': {
                    'default_priority': 'medium',
                    'rules': [
                        {'type': 'equals', 'field_id': 'service_type', 'condition': 'equals', 'value': 'Emergency', 'priority': 'high'},
                        {'type': 'equals', 'field_id': 'duration', 'condition': 'greater_than', 'value': 60, 'priority': 'high'}
                    ]
                }
            },
            {
                'id': 'sales_inquiry',
                'name': 'Sales Inquiry',
                'description': 'Track sales leads and customer inquiries',
                'fields': [
                    {'id': 'product_interest', 'name': 'Product Interest', 'type': 'choice', 'required': True, 'choices': ['Product A', 'Product B', 'Product C', 'Other']},
                    {'id': 'budget_range', 'name': 'Budget Range', 'type': 'choice', 'required': True, 'choices': ['Under $100', '$100-$500', '$500-$1000', 'Over $1000']},
                    {'id': 'timeline', 'name': 'Purchase Timeline', 'type': 'choice', 'required': True, 'choices': ['Immediate', '1-2 weeks', '1-2 months', '3+ months']},
                    {'id': 'decision_maker', 'name': 'Decision Maker', 'type': 'choice', 'required': False, 'choices': ['Yes', 'No', 'Partially']},
                    {'id': 'competitor_info', 'name': 'Competitor Information', 'type': 'textarea', 'required': False},
                    {'id': 'follow_up_date', 'name': 'Follow-up Date', 'type': 'date', 'required': False}
                ],
                'status_workflow': {
                    'statuses': [
                        {'id': 'new_lead', 'label': 'New Lead', 'color': 'blue'},
                        {'id': 'contacted', 'label': 'Contacted', 'color': 'yellow'},
                        {'id': 'qualified', 'label': 'Qualified', 'color': 'orange'},
                        {'id': 'proposal_sent', 'label': 'Proposal Sent', 'color': 'purple'},
                        {'id': 'negotiating', 'label': 'Negotiating', 'color': 'red'},
                        {'id': 'closed_won', 'label': 'Closed Won', 'color': 'green'},
                        {'id': 'closed_lost', 'label': 'Closed Lost', 'color': 'gray'}
                    ],
                    'transitions': {
                        'new_lead': ['contacted', 'qualified'],
                        'contacted': ['qualified', 'closed_lost'],
                        'qualified': ['proposal_sent', 'closed_lost'],
                        'proposal_sent': ['negotiating', 'closed_lost'],
                        'negotiating': ['closed_won', 'closed_lost'],
                        'closed_won': [],
                        'closed_lost': []
                    }
                },
                'priority_config': {
                    'default_priority': 'medium',
                    'rules': [
                        {'type': 'equals', 'field_id': 'budget_range', 'condition': 'equals', 'value': 'Over $1000', 'priority': 'high'},
                        {'type': 'equals', 'field_id': 'timeline', 'condition': 'equals', 'value': 'Immediate', 'priority': 'high'},
                        {'type': 'equals', 'field_id': 'decision_maker', 'condition': 'equals', 'value': 'Yes', 'priority': 'high'}
                    ]
                }
            }
        ]
        
        return Response(templates)
        
        return Response({
            'test_results': results,
            'schema_validation': 'passed'
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request, workspace_pk=None):
        """Get schema usage statistics"""
        workspace = get_object_or_404(Workspace, id=workspace_pk)
        
        schemas = WorkspaceContextSchema.objects.filter(workspace=workspace)
        schema_stats = []
        
        for schema in schemas:
            contexts = ConversationContext.objects.filter(schema=schema)
            
            stats = {
                'schema_id': schema.id,
                'schema_name': schema.name,
                'total_contexts': contexts.count(),
                'active_contexts': contexts.filter(
                    conversation__status='active'
                ).count(),
                'average_completion': contexts.aggregate(
                    avg_completion=Avg('completion_percentage')
                )['avg_completion'] or 0,
                'field_usage': self._calculate_field_usage(schema, contexts)
            }
            schema_stats.append(stats)
        
        return Response({
            'workspace_id': workspace_pk,
            'schema_statistics': schema_stats,
            'total_schemas': len(schema_stats)
        })
    
    def _calculate_field_usage(self, schema, contexts):
        """Calculate field usage statistics"""
        field_usage = {}
        
        for field in schema.fields:
            field_id = field['id']
            filled_count = 0
            
            for context in contexts:
                if context.context_data.get(field_id):
                    filled_count += 1
            
            field_usage[field_id] = {
                'label': field['label'],
                'filled_count': filled_count,
                'total_contexts': contexts.count(),
                'fill_rate': (filled_count / contexts.count() * 100) if contexts.count() > 0 else 0
            }
        
        return field_usage


class ConversationContextViewSet(viewsets.ModelViewSet):
    """ViewSet for managing conversation contexts"""
    
    serializer_class = ConversationContextSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = ConversationContext.objects.select_related('schema', 'conversation')
        
        # Filter by conversation
        conversation_id = self.kwargs.get('conversation_pk') or self.request.query_params.get('conversation')
        if conversation_id:
            queryset = queryset.filter(conversation_id=conversation_id)
        
        # Filter by workspace
        workspace_id = self.request.query_params.get('workspace')
        if workspace_id:
            queryset = queryset.filter(conversation__workspace_id=workspace_id)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by priority
        priority_filter = self.request.query_params.get('priority')
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)
        
        return queryset.order_by('-updated_at')
    
    @action(detail=True, methods=['post'])
    def extract_context(self, request, conversation_pk=None, pk=None):
        """Extract context from conversation messages using AI"""
        context = self.get_object()
        serializer = ContextExtractionRequestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            extraction_service = ContextExtractionService()
            result = extraction_service.extract_context_from_text(
                context=context,
                text=serializer.validated_data['message_text'],
                force_extraction=serializer.validated_data.get('force_extraction', False),
                fields_to_extract=serializer.validated_data.get('fields_to_extract')
            )
            
            # Refresh context from database
            context.refresh_from_db()
            
            return Response({
                'success': True,
                'extracted_fields': result.get('extracted_fields', {}),
                'confidence_scores': result.get('confidence_scores', {}),
                'updated_context': ConversationContextSerializer(context).data
            })
            
        except Exception as e:
            logger.error(f"Context extraction failed for context {pk}: {str(e)}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['put'])
    def update_fields(self, request, conversation_pk=None, pk=None):
        """Update specific context fields"""
        context = self.get_object()
        serializer = ContextUpdateSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        field_updates = serializer.validated_data.get('field_updates', {})
        
        with transaction.atomic():
            # Update fields and track changes
            for field_id, value in field_updates.items():
                old_value = context.context_data.get(field_id)
                
                if old_value != value:
                    context.set_field_value(field_id, value, is_ai_update=False)
                    
                    # Log the change
                    ContextHistory.objects.create(
                        context=context,
                        action_type='field_updated',
                        field_name=field_id,
                        old_value=old_value,
                        new_value=value,
                        changed_by_user=request.user,
                        changed_by_ai=False
                    )
            
            # Update other fields if provided
            if 'title' in serializer.validated_data:
                context.title = serializer.validated_data['title']
            
            if 'tags' in serializer.validated_data:
                context.tags = serializer.validated_data['tags']
            
            if 'metadata' in serializer.validated_data:
                context.metadata.update(serializer.validated_data['metadata'])
            
            # Recalculate priority based on new data
            context.recalculate_priority()
            context.save()
            
            # Trigger business rules
            try:
                rule_engine = RuleEngineService()
                rule_engine.evaluate_context_change(context, field_updates)
            except Exception as e:
                logger.error(f"Rule evaluation failed after context update: {str(e)}")
        
        return Response(ConversationContextSerializer(context).data)
    
    @action(detail=True, methods=['post'])
    def change_status(self, request, conversation_pk=None, pk=None):
        """Change context status"""
        context = self.get_object()
        new_status = request.data.get('status')
        
        if not new_status:
            return Response(
                {'error': 'Status is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        success = context.update_status(new_status, request.user)
        
        if success:
            context.save()
            
            # Trigger business rules
            try:
                rule_engine = RuleEngineService()
                rule_engine.evaluate_status_change(context, new_status)
            except Exception as e:
                logger.error(f"Rule evaluation failed after status change: {str(e)}")
            
            return Response(ConversationContextSerializer(context).data)
        else:
            available_statuses = context.schema.get_status_choices()
            return Response({
                'error': f'Cannot transition from "{context.status}" to "{new_status}"',
                'available_statuses': available_statuses
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def history(self, request, conversation_pk=None, pk=None):
        """Get context change history"""
        context = self.get_object()
        history = ContextHistory.objects.filter(context=context).order_by('-created_at')
        
        # Pagination
        page_size = int(request.query_params.get('page_size', 50))
        page = int(request.query_params.get('page', 1))
        start = (page - 1) * page_size
        end = start + page_size
        
        paginated_history = history[start:end]
        serializer = ContextHistorySerializer(paginated_history, many=True)
        
        return Response({
            'history': serializer.data,
            'total_count': history.count(),
            'page': page,
            'page_size': page_size,
            'has_next': end < history.count()
        })


class BusinessRuleViewSet(viewsets.ModelViewSet):
    """ViewSet for managing business rules"""
    
    serializer_class = BusinessRuleSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        workspace_id = self.kwargs.get('workspace_pk') or self.request.query_params.get('workspace')
        if workspace_id:
            return BusinessRule.objects.filter(workspace_id=workspace_id).order_by('priority', 'name')
        return BusinessRule.objects.none()
    
    def perform_create(self, serializer):
        workspace_id = self.kwargs.get('workspace_pk') or self.request.data.get('workspace')
        workspace = get_object_or_404(Workspace, id=workspace_id)
        serializer.save(workspace=workspace, created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def test_rule(self, request, workspace_pk=None, pk=None):
        """Test a business rule with sample data"""
        rule = self.get_object()
        serializer = RuleTestSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        test_context_data = serializer.validated_data['test_context_data']
        test_trigger_data = serializer.validated_data.get('test_trigger_data', {})
        
        # Evaluate conditions
        conditions_met = rule.evaluate_conditions(test_context_data)
        
        # If conditions are met, simulate action execution
        execution_result = None
        if conditions_met:
            execution_result = {
                'would_execute': True,
                'actions': rule.actions,
                'simulated': True
            }
        
        return Response({
            'rule_name': rule.name,
            'conditions_met': conditions_met,
            'execution_result': execution_result,
            'test_data': test_context_data
        })
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, workspace_pk=None, pk=None):
        """Toggle rule active status"""
        rule = self.get_object()
        rule.is_active = not rule.is_active
        rule.save()
        
        return Response({
            'id': rule.id,
            'is_active': rule.is_active,
            'message': f"Rule {'activated' if rule.is_active else 'deactivated'} successfully"
        })
    
    @action(detail=False, methods=['get'])
    def execution_statistics(self, request, workspace_pk=None):
        """Get rule execution statistics"""
        workspace = get_object_or_404(Workspace, id=workspace_pk)
        rules = BusinessRule.objects.filter(workspace=workspace)
        
        stats = []
        for rule in rules:
            recent_executions = RuleExecution.objects.filter(
                rule=rule,
                created_at__gte=timezone.now() - timezone.timedelta(days=30)
            )
            
            rule_stats = {
                'rule_id': rule.id,
                'rule_name': rule.name,
                'total_executions': rule.execution_count,
                'recent_executions': recent_executions.count(),
                'success_rate': rule.success_rate,
                'last_executed': rule.last_executed,
                'is_active': rule.is_active,
                'avg_execution_time': recent_executions.aggregate(
                    avg_time=Avg('execution_time')
                )['avg_time'] or 0
            }
            stats.append(rule_stats)
        
        return Response({
            'workspace_id': workspace_pk,
            'rule_statistics': stats,
            'total_rules': len(stats),
            'active_rules': len([r for r in stats if r['is_active']])
        })


class ContextAnalyticsView(APIView):
    """Analytics view for context tracking system"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, workspace_id):
        workspace = get_object_or_404(Workspace, id=workspace_id)
        
        # Time range filter
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timezone.timedelta(days=days)
        
        # Get contexts in time range
        contexts = ConversationContext.objects.filter(
            conversation__workspace=workspace,
            created_at__gte=start_date
        )
        
        # Basic metrics
        metrics = {
            'total_contexts': contexts.count(),
            'active_contexts': contexts.filter(status__in=['new', 'in_progress']).count(),
            'completed_contexts': contexts.filter(status='resolved').count(),
            'average_completion_rate': contexts.aggregate(
                avg_completion=Avg('completion_percentage')
            )['avg_completion'] or 0,
        }
        
        # Status distribution
        status_distribution = {}
        for context in contexts:
            status = context.status
            status_distribution[status] = status_distribution.get(status, 0) + 1
        
        # Priority distribution
        priority_distribution = {}
        for context in contexts:
            priority = context.priority
            priority_distribution[priority] = priority_distribution.get(priority, 0) + 1
        
        # Schema usage
        schema_usage = contexts.values('schema__name').annotate(
            count=Count('schema')
        ).order_by('-count')
        
        # Field completion rates
        schemas = WorkspaceContextSchema.objects.filter(workspace=workspace)
        field_completion = {}
        
        for schema in schemas:
            schema_contexts = contexts.filter(schema=schema)
            if schema_contexts.exists():
                field_stats = {}
                for field in schema.fields:
                    field_id = field['id']
                    filled_count = 0
                    
                    for context in schema_contexts:
                        if context.context_data.get(field_id):
                            filled_count += 1
                    
                    field_stats[field['label']] = {
                        'filled_count': filled_count,
                        'total_contexts': schema_contexts.count(),
                        'completion_rate': (filled_count / schema_contexts.count() * 100) if schema_contexts.count() > 0 else 0
                    }
                
                field_completion[schema.name] = field_stats
        
        # AI extraction performance
        ai_updates = ContextHistory.objects.filter(
            context__conversation__workspace=workspace,
            changed_by_ai=True,
            created_at__gte=start_date
        )
        
        ai_performance = {
            'total_ai_updates': ai_updates.count(),
            'avg_confidence': ai_updates.aggregate(
                avg_conf=Avg('confidence_score')
            )['avg_conf'] or 0,
            'high_confidence_updates': ai_updates.filter(confidence_score__gte=0.8).count()
        }
        
        return Response({
            'workspace_id': workspace_id,
            'time_range_days': days,
            'metrics': metrics,
            'status_distribution': status_distribution,
            'priority_distribution': priority_distribution,
            'schema_usage': list(schema_usage),
            'field_completion_rates': field_completion,
            'ai_performance': ai_performance,
            'generated_at': timezone.now()
        })


class BulkContextOperationsView(APIView):
    """Bulk operations for contexts"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, workspace_id):
        workspace = get_object_or_404(Workspace, id=workspace_id)
        
        operation = request.data.get('operation')
        context_ids = request.data.get('context_ids', [])
        operation_data = request.data.get('data', {})
        
        if not operation or not context_ids:
            return Response({
                'error': 'Operation and context_ids are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        contexts = ConversationContext.objects.filter(
            id__in=context_ids,
            conversation__workspace=workspace
        )
        
        if not contexts.exists():
            return Response({
                'error': 'No valid contexts found'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        results = []
        
        with transaction.atomic():
            for context in contexts:
                try:
                    if operation == 'change_status':
                        new_status = operation_data.get('status')
                        success = context.update_status(new_status, request.user)
                        if success:
                            context.save()
                        results.append({
                            'context_id': context.id,
                            'success': success,
                            'message': 'Status updated' if success else 'Status transition not allowed'
                        })
                    
                    elif operation == 'change_priority':
                        new_priority = operation_data.get('priority')
                        if new_priority in ['low', 'medium', 'high', 'urgent']:
                            context.priority = new_priority
                            context.save()
                            results.append({
                                'context_id': context.id,
                                'success': True,
                                'message': 'Priority updated'
                            })
                        else:
                            results.append({
                                'context_id': context.id,
                                'success': False,
                                'message': 'Invalid priority value'
                            })
                    
                    elif operation == 'add_tags':
                        tags_to_add = operation_data.get('tags', [])
                        for tag in tags_to_add:
                            if tag not in context.tags:
                                context.tags.append(tag)
                        context.save()
                        results.append({
                            'context_id': context.id,
                            'success': True,
                            'message': 'Tags added'
                        })
                    
                    elif operation == 'remove_tags':
                        tags_to_remove = operation_data.get('tags', [])
                        for tag in tags_to_remove:
                            if tag in context.tags:
                                context.tags.remove(tag)
                        context.save()
                        results.append({
                            'context_id': context.id,
                            'success': True,
                            'message': 'Tags removed'
                        })
                    
                    else:
                        results.append({
                            'context_id': context.id,
                            'success': False,
                            'message': f'Unknown operation: {operation}'
                        })
                
                except Exception as e:
                    results.append({
                        'context_id': context.id,
                        'success': False,
                        'message': str(e)
                    })
        
        successful_operations = len([r for r in results if r['success']])
        
        return Response({
            'operation': operation,
            'total_contexts': len(context_ids),
            'successful_operations': successful_operations,
            'failed_operations': len(results) - successful_operations,
            'results': results
        })
