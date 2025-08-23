from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count, Avg, F, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import logging

from .models import BusinessRule, ConversationContext, RuleExecution, WorkspaceContextSchema
from .advanced_rule_engine import AdvancedRuleEngine, RuleTemplateManager
from .serializers import BusinessRuleSerializer, ConversationContextSerializer
from core.models import Workspace, Conversation

logger = logging.getLogger(__name__)


class AdvancedBusinessRuleViewSet(ViewSet):
    """Advanced business rule management with workflows and analytics"""
    
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rule_engine = AdvancedRuleEngine()
        self.template_manager = RuleTemplateManager()
    
    @action(detail=False, methods=['get'])
    def analytics_dashboard(self, request):
        """Get comprehensive analytics dashboard for business rules"""
        try:
            workspace_id = request.query_params.get('workspace_id')
            if not workspace_id:
                return Response({'error': 'workspace_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            workspace = Workspace.objects.get(id=workspace_id)
            
            # Get rule performance metrics
            rule_metrics = self._get_rule_performance_metrics(workspace)
            
            # Get execution trends
            execution_trends = self._get_execution_trends(workspace)
            
            # Get workflow analytics
            workflow_analytics = self._get_workflow_analytics(workspace)
            
            # Get top performing rules
            top_rules = self._get_top_performing_rules(workspace)
            
            # Get rule health status
            rule_health = self._get_rule_health_status(workspace)
            
            return Response({
                'rule_metrics': rule_metrics,
                'execution_trends': execution_trends,
                'workflow_analytics': workflow_analytics,
                'top_rules': top_rules,
                'rule_health': rule_health
            })
            
        except Workspace.DoesNotExist:
            return Response({'error': 'Workspace not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Analytics dashboard error: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _get_rule_performance_metrics(self, workspace: Workspace) -> Dict[str, Any]:
        """Get rule performance metrics for a workspace"""
        try:
            # Get all rules for the workspace
            rules = BusinessRule.objects.filter(workspace=workspace)
            
            total_rules = rules.count()
            active_rules = rules.filter(is_active=True).count()
            template_rules = rules.filter(is_template=True).count()
            
            # Calculate average success rate
            avg_success_rate = rules.aggregate(avg_success=Avg('success_rate'))['avg_success'] or 0
            
            # Calculate average execution time
            avg_execution_time = rules.aggregate(avg_time=Avg('average_execution_time'))['avg_time'] or 0
            
            # Get execution count distribution
            execution_distribution = rules.aggregate(
                low_execution=Count('id', filter=Q(execution_count__lt=10)),
                medium_execution=Count('id', filter=Q(execution_count__gte=10, execution_count__lt=50)),
                high_execution=Count('id', filter=Q(execution_count__gte=50))
            )
            
            return {
                'total_rules': total_rules,
                'active_rules': active_rules,
                'template_rules': template_rules,
                'inactive_rules': total_rules - active_rules,
                'avg_success_rate': round(avg_success_rate * 100, 2),
                'avg_execution_time': round(avg_execution_time, 3),
                'execution_distribution': execution_distribution
            }
            
        except Exception as e:
            logger.error(f"Error getting rule performance metrics: {str(e)}")
            return {}
    
    def _get_execution_trends(self, workspace: Workspace) -> Dict[str, Any]:
        """Get rule execution trends over time"""
        try:
            # Get executions for the last 30 days
            thirty_days_ago = timezone.now() - timedelta(days=30)
            
            executions = RuleExecution.objects.filter(
                rule__workspace=workspace,
                created_at__gte=thirty_days_ago
            ).extra(
                select={'date': 'DATE(rule_executions.created_at)'}
            ).values('date').annotate(
                total_executions=Count('id'),
                successful_executions=Count('id', filter=Q(success=True)),
                failed_executions=Count('id', filter=Q(success=False)),
                avg_execution_time=Avg('execution_time')
            ).order_by('date')
            
            # Format data for charts
            dates = []
            total_counts = []
            success_counts = []
            failure_counts = []
            avg_times = []
            
            for execution in executions:
                dates.append(execution['date'].strftime('%Y-%m-%d'))
                total_counts.append(execution['total_executions'])
                success_counts.append(execution['successful_executions'])
                failure_counts.append(execution['failed_executions'])
                avg_times.append(round(execution['avg_execution_time'] or 0, 3))
            
            return {
                'dates': dates,
                'total_executions': total_counts,
                'successful_executions': success_counts,
                'failed_executions': failure_counts,
                'avg_execution_times': avg_times
            }
            
        except Exception as e:
            logger.error(f"Error getting execution trends: {str(e)}")
            return {}
    
    def _get_workflow_analytics(self, workspace: Workspace) -> Dict[str, Any]:
        """Get workflow-specific analytics"""
        try:
            # Get rules with workflows
            workflow_rules = BusinessRule.objects.filter(
                workspace=workspace,
                workflow_steps__isnull=False
            ).exclude(workflow_steps=[])
            
            workflow_stats = []
            
            for rule in workflow_rules:
                # Get workflow executions
                workflow_executions = RuleExecution.objects.filter(
                    rule=rule,
                    success=True
                )
                
                if workflow_executions.exists():
                    # Calculate workflow completion rates
                    total_workflows = workflow_executions.count()
                    completed_workflows = sum(
                        1 for execution in workflow_executions
                        if execution.execution_result.get('completed', False)
                    )
                    
                    completion_rate = (completed_workflows / total_workflows * 100) if total_workflows > 0 else 0
                    
                    # Get average steps completed
                    avg_steps = workflow_executions.aggregate(
                        avg_steps=Avg('execution_result__current_step')
                    )['avg_steps'] or 0
                    
                    workflow_stats.append({
                        'rule_name': rule.name,
                        'total_workflows': total_workflows,
                        'completed_workflows': completed_workflows,
                        'completion_rate': round(completion_rate, 2),
                        'avg_steps_completed': round(avg_steps, 1),
                        'total_steps': len(rule.workflow_steps)
                    })
            
            return {
                'total_workflow_rules': len(workflow_stats),
                'workflow_details': workflow_stats
            }
            
        except Exception as e:
            logger.error(f"Error getting workflow analytics: {str(e)}")
            return {}
    
    def _get_top_performing_rules(self, workspace: Workspace) -> List[Dict[str, Any]]:
        """Get top performing rules by success rate and execution count"""
        try:
            top_rules = BusinessRule.objects.filter(
                workspace=workspace,
                execution_count__gte=5  # Only rules with significant execution history
            ).order_by('-success_rate', '-execution_count')[:10]
            
            top_performers = []
            for rule in top_rules:
                top_performers.append({
                    'name': rule.name,
                    'success_rate': round(rule.success_rate * 100, 2),
                    'execution_count': rule.execution_count,
                    'avg_execution_time': round(rule.average_execution_time, 3),
                    'last_executed': rule.last_executed.isoformat() if rule.last_executed else None
                })
            
            return top_performers
            
        except Exception as e:
            logger.error(f"Error getting top performing rules: {str(e)}")
            return []
    
    def _get_rule_health_status(self, workspace: Workspace) -> Dict[str, Any]:
        """Get overall rule health status"""
        try:
            rules = BusinessRule.objects.filter(workspace=workspace)
            
            # Categorize rules by health
            healthy_rules = rules.filter(
                success_rate__gte=0.8,
                execution_count__gte=5
            ).count()
            
            warning_rules = rules.filter(
                Q(success_rate__lt=0.8, success_rate__gte=0.5) |
                Q(execution_count__lt=5)
            ).count()
            
            critical_rules = rules.filter(
                success_rate__lt=0.5,
                execution_count__gte=10
            ).count()
            
            inactive_rules = rules.filter(is_active=False).count()
            
            total_rules = rules.count()
            
            return {
                'total_rules': total_rules,
                'healthy_rules': healthy_rules,
                'warning_rules': warning_rules,
                'critical_rules': critical_rules,
                'inactive_rules': inactive_rules,
                'health_score': round((healthy_rules / total_rules * 100) if total_rules > 0 else 0, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting rule health status: {str(e)}")
            return {}
    
    @action(detail=False, methods=['get'])
    def rule_templates(self, request):
        """Get available rule templates by industry"""
        try:
            industry = request.query_params.get('industry', 'banking')
            templates = self.template_manager.get_industry_templates(industry)
            
            return Response({
                'industry': industry,
                'templates': templates,
                'total_templates': len(templates)
            })
            
        except Exception as e:
            logger.error(f"Error getting rule templates: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def create_from_template(self, request):
        """Create a business rule from a template"""
        try:
            workspace_id = request.data.get('workspace_id')
            template_name = request.data.get('template_name')
            customizations = request.data.get('customizations', {})
            
            if not all([workspace_id, template_name]):
                return Response(
                    {'error': 'workspace_id and template_name are required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            workspace = Workspace.objects.get(id=workspace_id)
            
            # Get the template
            industry = request.data.get('industry', 'banking')
            templates = self.template_manager.get_industry_templates(industry)
            
            template = next((t for t in templates if t['name'] == template_name), None)
            if not template:
                return Response(
                    {'error': f'Template {template_name} not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Create rule from template
            rule = self.template_manager.create_rule_from_template(workspace, template, customizations)
            
            serializer = BusinessRuleSerializer(rule)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Workspace.DoesNotExist:
            return Response({'error': 'Workspace not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error creating rule from template: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def test_rule(self, request, pk=None):
        """Test a business rule with sample data"""
        try:
            rule = BusinessRule.objects.get(id=pk)
            
            # Get test data from request
            test_context_data = request.data.get('test_context_data', {})
            test_trigger_data = request.data.get('test_trigger_data', {})
            
            # Create a mock context for testing
            mock_context = type('MockContext', (), {
                'context_data': test_context_data,
                'status': test_context_data.get('status', 'new'),
                'priority': test_context_data.get('priority', 'medium'),
                'completion_percentage': test_context_data.get('completion_percentage', 0),
                'tags': test_context_data.get('tags', []),
                'created_at': timezone.now(),
                'updated_at': timezone.now()
            })()
            
            # Test rule evaluation
            conditions_met = rule.evaluate_conditions({
                'context_data': test_context_data,
                'status': test_context_data.get('status', 'new'),
                'priority': test_context_data.get('priority', 'medium'),
                'completion_percentage': test_context_data.get('completion_percentage', 0),
                'tags': test_context_data.get('tags', [])
            })
            
            # Test time conditions
            time_conditions_met = rule.evaluate_time_conditions({
                'context_data': test_context_data,
                'status': test_context_data.get('status', 'new'),
                'priority': test_context_data.get('priority', 'medium'),
                'completion_percentage': test_context_data.get('completion_percentage', 0),
                'tags': test_context_data.get('tags', [])
            })
            
            # Test field dependencies
            field_dependencies_met = rule.evaluate_field_dependencies({
                'context_data': test_context_data,
                'status': test_context_data.get('status', 'new'),
                'priority': test_context_data.get('priority', 'medium'),
                'completion_percentage': test_context_data.get('completion_percentage', 0),
                'tags': test_context_data.get('tags', [])
            })
            
            # Check if rule can execute
            can_execute, reason = rule.can_execute({
                'context_data': test_context_data,
                'status': test_context_data.get('status', 'new'),
                'priority': test_context_data.get('priority', 'medium'),
                'completion_percentage': test_context_data.get('completion_percentage', 0),
                'tags': test_context_data.get('tags', [])
            })
            
            return Response({
                'rule_name': rule.name,
                'test_results': {
                    'conditions_met': conditions_met,
                    'time_conditions_met': time_conditions_met,
                    'field_dependencies_met': field_dependencies_met,
                    'can_execute': can_execute,
                    'execution_reason': reason
                },
                'test_data': {
                    'context_data': test_context_data,
                    'trigger_data': test_trigger_data
                }
            })
            
        except BusinessRule.DoesNotExist:
            return Response({'error': 'Rule not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error testing rule: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def execute_workflow(self, request, pk=None):
        """Manually execute a workflow rule"""
        try:
            rule = BusinessRule.objects.get(id=pk)
            
            if not rule.workflow_steps:
                return Response(
                    {'error': 'This rule does not have workflow steps'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get conversation context
            conversation_id = request.data.get('conversation_id')
            if not conversation_id:
                return Response(
                    {'error': 'conversation_id is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            conversation = Conversation.objects.get(id=conversation_id)
            context = ConversationContext.objects.filter(conversation=conversation).first()
            
            if not context:
                return Response(
                    {'error': 'No context found for conversation'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Execute workflow
            trigger_data = {
                'trigger_type': 'manual_execution',
                'triggered_by': request.user.id if hasattr(request, 'user') else None,
                'triggered_at': timezone.now().isoformat()
            }
            
            result = self.rule_engine._execute_workflow_rule(rule, context, trigger_data)
            
            return Response({
                'rule_name': rule.name,
                'workflow_result': result,
                'conversation_id': str(conversation_id)
            })
            
        except BusinessRule.DoesNotExist:
            return Response({'error': 'Rule not found'}, status=status.HTTP_404_NOT_FOUND)
        except Conversation.DoesNotExist:
            return Response({'error': 'Conversation not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error executing workflow: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def rule_insights(self, request):
        """Get intelligent insights about business rules"""
        try:
            workspace_id = request.query_params.get('workspace_id')
            if not workspace_id:
                return Response({'error': 'workspace_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            workspace = Workspace.objects.get(id=workspace_id)
            
            insights = []
            
            # Analyze rule performance
            rules = BusinessRule.objects.filter(workspace=workspace)
            
            # Find underperforming rules
            underperforming_rules = rules.filter(
                success_rate__lt=0.5,
                execution_count__gte=10
            )
            
            if underperforming_rules.exists():
                insights.append({
                    'type': 'warning',
                    'title': 'Underperforming Rules Detected',
                    'message': f'{underperforming_rules.count()} rules have success rates below 50%',
                    'recommendation': 'Review and optimize these rules or consider deactivating them',
                    'rules': list(underperforming_rules.values('name', 'success_rate', 'execution_count'))
                })
            
            # Find rules with high execution times
            slow_rules = rules.filter(
                average_execution_time__gt=5.0,
                execution_count__gte=5
            )
            
            if slow_rules.exists():
                insights.append({
                    'type': 'warning',
                    'title': 'Slow Executing Rules',
                    'message': f'{slow_rules.count()} rules take more than 5 seconds to execute',
                    'recommendation': 'Optimize these rules or consider breaking them into smaller steps',
                    'rules': list(slow_rules.values('name', 'average_execution_time', 'execution_count'))
                })
            
            # Find inactive rules
            inactive_rules = rules.filter(is_active=False)
            
            if inactive_rules.count() > rules.count() * 0.3:
                insights.append({
                    'type': 'info',
                    'title': 'High Number of Inactive Rules',
                    'message': f'{inactive_rules.count()} out of {rules.count()} rules are inactive',
                    'recommendation': 'Consider cleaning up inactive rules to improve maintainability'
                })
            
            # Find rules without recent executions
            thirty_days_ago = timezone.now() - timedelta(days=30)
            unused_rules = rules.filter(
                Q(last_executed__lt=thirty_days_ago) | Q(last_executed__isnull=True),
                is_active=True
            )
            
            if unused_rules.exists():
                insights.append({
                    'type': 'info',
                    'title': 'Unused Active Rules',
                    'message': f'{unused_rules.count()} active rules have not been executed in 30 days',
                    'recommendation': 'Review if these rules are still needed or consider deactivating them'
                })
            
            return Response({
                'insights': insights,
                'total_insights': len(insights)
            })
            
        except Workspace.DoesNotExist:
            return Response({'error': 'Workspace not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error getting rule insights: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WorkflowManagementViewSet(ViewSet):
    """Manage multi-step workflows and their execution"""
    
    permission_classes = [IsAuthenticated]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.rule_engine = AdvancedRuleEngine()
    
    @action(detail=False, methods=['get'])
    def active_workflows(self, request):
        """Get all active workflows across conversations"""
        try:
            workspace_id = request.query_params.get('workspace_id')
            if not workspace_id:
                return Response({'error': 'workspace_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Get all contexts with active workflows
            contexts = ConversationContext.objects.filter(
                conversation__workspace_id=workspace_id,
                context_data__active_workflows__isnull=False
            ).exclude(context_data__active_workflows={})
            
            active_workflows = []
            
            for context in contexts:
                workflows = context.context_data.get('active_workflows', {})
                
                for workflow_name, workflow_state in workflows.items():
                    if not workflow_state.get('completed', False):
                        active_workflows.append({
                            'conversation_id': str(context.conversation.id),
                            'workflow_name': workflow_name,
                            'current_step': workflow_state.get('current_step', 0),
                            'total_steps': workflow_state.get('total_steps', 0),
                            'started_at': workflow_state.get('triggered_at'),
                            'last_updated': workflow_state.get('last_step_completed'),
                            'status': 'paused' if workflow_state.get('paused') else 'active',
                            'context_id': str(context.id)
                        })
            
            return Response({
                'active_workflows': active_workflows,
                'total_active': len(active_workflows)
            })
            
        except Exception as e:
            logger.error(f"Error getting active workflows: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def resume_workflow(self, request):
        """Resume a paused workflow"""
        try:
            context_id = request.data.get('context_id')
            workflow_name = request.data.get('workflow_name')
            
            if not all([context_id, workflow_name]):
                return Response(
                    {'error': 'context_id and workflow_name are required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            context = ConversationContext.objects.get(id=context_id)
            workflow_state = context.context_data.get('active_workflows', {}).get(workflow_name, {})
            
            if not workflow_state:
                return Response(
                    {'error': 'Workflow not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            if not workflow_state.get('paused'):
                return Response(
                    {'error': 'Workflow is not paused'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Resume workflow
            workflow_state['paused'] = False
            workflow_state['resumed_at'] = timezone.now().isoformat()
            
            # Update context
            if 'active_workflows' not in context.context_data:
                context.context_data['active_workflows'] = {}
            context.context_data['active_workflows'][workflow_name] = workflow_state
            context.save()
            
            return Response({
                'message': f'Workflow {workflow_name} resumed successfully',
                'workflow_state': workflow_state
            })
            
        except ConversationContext.DoesNotExist:
            return Response({'error': 'Context not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error resuming workflow: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def reset_workflow(self, request):
        """Reset a workflow to start from beginning"""
        try:
            context_id = request.data.get('context_id')
            workflow_name = request.data.get('workflow_name')
            
            if not all([context_id, workflow_name]):
                return Response(
                    {'error': 'context_id and workflow_name are required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            context = ConversationContext.objects.get(id=context_id)
            
            if 'active_workflows' not in context.context_data:
                context.context_data['active_workflows'] = {}
            
            # Reset workflow state
            context.context_data['active_workflows'][workflow_name] = {
                'triggered_at': timezone.now().isoformat(),
                'current_step': 0,
                'reset_at': timezone.now().isoformat(),
                'reset_count': context.context_data['active_workflows'].get(workflow_name, {}).get('reset_count', 0) + 1
            }
            
            context.save()
            
            return Response({
                'message': f'Workflow {workflow_name} reset successfully',
                'workflow_state': context.context_data['active_workflows'][workflow_name]
            })
            
        except ConversationContext.DoesNotExist:
            return Response({'error': 'Context not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error resetting workflow: {str(e)}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
