import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Count, Avg, F
from datetime import datetime, timedelta

from .models import BusinessRule, ConversationContext, RuleExecution
from core.models import Workspace, Conversation, AppUser

logger = logging.getLogger(__name__)


class AdvancedRuleEngine:
    """Advanced business rule engine with complex workflows and intelligent automation"""
    
    def __init__(self):
        self.logger = logger
        self.execution_cache = {}  # Cache for rule execution results
    
    def evaluate_conversation_rules(self, conversation: Conversation, trigger_type: str, trigger_data: Dict[str, Any] = None):
        """Evaluate all applicable rules for a conversation"""
        try:
            workspace = conversation.workspace
            context = self._get_or_create_context(conversation)
            
            if not context:
                self.logger.warning(f"No context found for conversation {conversation.id}")
                return
            
            # Get all active rules for this workspace and trigger type
            rules = BusinessRule.objects.filter(
                workspace=workspace,
                is_active=True,
                trigger_type=trigger_type
            ).order_by('priority')
            
            self.logger.info(f"Evaluating {rules.count()} rules for {trigger_type} on conversation {conversation.id}")
            
            executed_rules = []
            for rule in rules:
                try:
                    if self._should_execute_rule(rule, context, trigger_data):
                        execution_result = self._execute_rule_with_workflow(rule, context, trigger_data)
                        executed_rules.append({
                            'rule': rule,
                            'result': execution_result
                        })
                        
                        # Check if we should continue with other rules
                        if rule.trigger_type == 'escalate' and execution_result.get('escalated'):
                            self.logger.info(f"Conversation escalated, stopping rule evaluation")
                            break
                            
                except Exception as e:
                    self.logger.error(f"Rule {rule.name} execution failed: {str(e)}")
                    self._log_rule_failure(rule, context, trigger_data, str(e))
            
            # Update conversation metrics
            self._update_conversation_metrics(conversation, executed_rules)
            
            return executed_rules
            
        except Exception as e:
            self.logger.error(f"Advanced rule evaluation failed: {str(e)}")
            return []
    
    def _should_execute_rule(self, rule: BusinessRule, context: ConversationContext, trigger_data: Dict[str, Any]) -> bool:
        """Check if a rule should execute based on advanced conditions"""
        try:
            # Basic execution check
            can_execute, reason = rule.can_execute(self._prepare_context_data(context))
            if not can_execute:
                self.logger.debug(f"Rule {rule.name} cannot execute: {reason}")
                return False
            
            # Check if rule has been executed recently (execution interval)
            if rule.execution_interval > 0 and rule.last_execution_time:
                time_since_last = (timezone.now() - rule.last_execution_time).total_seconds()
                if time_since_last < rule.execution_interval:
                    self.logger.debug(f"Rule {rule.name} execution interval not met")
                    return False
            
            # Check time conditions
            if not rule.evaluate_time_conditions(self._prepare_context_data(context)):
                self.logger.debug(f"Rule {rule.name} time conditions not met")
                return False
            
            # Check field dependencies
            if not rule.evaluate_field_dependencies(self._prepare_context_data(context)):
                self.logger.debug(f"Rule {rule.name} field dependencies not met")
                return False
            
            # Check external conditions
            if not self._evaluate_external_conditions(rule, context, trigger_data):
                self.logger.debug(f"Rule {rule.name} external conditions not met")
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking if rule {rule.name} should execute: {str(e)}")
            return False
    
    def _evaluate_external_conditions(self, rule: BusinessRule, context: ConversationContext, trigger_data: Dict[str, Any]) -> bool:
        """Evaluate external system conditions"""
        external_conditions = rule.external_conditions or {}
        if not external_conditions:
            return True
        
        try:
            for condition_type, condition_config in external_conditions.items():
                if condition_type == 'workload_check':
                    if not self._check_agent_workload(condition_config, context):
                        return False
                
                elif condition_type == 'business_hours':
                    if not self._check_business_hours(condition_config):
                        return False
                
                elif condition_type == 'customer_tier':
                    if not self._check_customer_tier(condition_config, context):
                        return False
                
                elif condition_type == 'conversation_age':
                    if not self._check_conversation_age(condition_config, context):
                        return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"External condition evaluation failed: {str(e)}")
            return False
    
    def _check_agent_workload(self, condition_config: Dict[str, Any], context: ConversationContext) -> bool:
        """Check if agents have capacity for new work"""
        max_workload = condition_config.get('max_conversations', 10)
        agent_type = condition_config.get('agent_type', 'general')
        
        try:
            # Count active conversations per agent
            agent_workloads = ConversationContext.objects.filter(
                conversation__workspace=context.conversation.workspace,
                status__in=['new', 'in_progress']
            ).values('context_data__assigned_agent').annotate(
                count=Count('id')
            )
            
            # Check if any agent has capacity
            for workload in agent_workloads:
                if workload['count'] < max_workload:
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Workload check failed: {str(e)}")
            return True  # Default to allowing execution
    
    def _check_business_hours(self, condition_config: Dict[str, Any]) -> bool:
        """Check if current time is within business hours"""
        try:
            now = timezone.now()
            current_hour = now.hour
            current_weekday = now.weekday()
            
            start_hour = condition_config.get('start_hour', 9)
            end_hour = condition_config.get('end_hour', 17)
            business_days = condition_config.get('business_days', [0, 1, 2, 3, 4])  # Mon-Fri
            
            if current_weekday not in business_days:
                return False
            
            if not (start_hour <= current_hour <= end_hour):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Business hours check failed: {str(e)}")
            return True
    
    def _check_customer_tier(self, condition_config: Dict[str, Any], context: ConversationContext) -> bool:
        """Check if customer meets tier requirements"""
        required_tier = condition_config.get('required_tier', 'bronze')
        customer_tier = context.context_data.get('customer_tier', 'bronze')
        
        tier_hierarchy = ['bronze', 'silver', 'gold', 'platinum']
        
        try:
            required_index = tier_hierarchy.index(required_tier.lower())
            customer_index = tier_hierarchy.index(customer_tier.lower())
            
            return customer_index >= required_index
            
        except ValueError:
            return True  # Default to allowing execution
    
    def _check_conversation_age(self, condition_config: Dict[str, Any], context: ConversationContext) -> bool:
        """Check if conversation meets age requirements"""
        max_age_hours = condition_config.get('max_age_hours', 24)
        
        try:
            conversation_age = (timezone.now() - context.conversation.created_at).total_seconds() / 3600
            return conversation_age <= max_age_hours
            
        except Exception as e:
            self.logger.error(f"Conversation age check failed: {str(e)}")
            return True
    
    def _execute_rule_with_workflow(self, rule: BusinessRule, context: ConversationContext, trigger_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a rule with multi-step workflow support"""
        start_time = time.time()
        
        try:
            # Check if this is a workflow rule
            if rule.workflow_steps:
                return self._execute_workflow_rule(rule, context, trigger_data)
            else:
                # Execute regular rule
                return self._execute_simple_rule(rule, context, trigger_data)
                
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Workflow rule execution failed: {str(e)}")
            
            # Execute rollback actions if defined
            if rule.rollback_actions:
                self._execute_rollback_actions(rule, context, trigger_data)
            
            return {
                'success': False,
                'error': str(e),
                'execution_time': execution_time,
                'workflow_type': 'workflow' if rule.workflow_steps else 'simple'
            }
    
    def _execute_workflow_rule(self, rule: BusinessRule, context: ConversationContext, trigger_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a multi-step workflow rule"""
        workflow_steps = rule.workflow_steps
        current_step = context.context_data.get('active_workflows', {}).get(rule.name, {}).get('current_step', 0)
        
        self.logger.info(f"Executing workflow rule {rule.name} at step {current_step}")
        
        executed_steps = []
        workflow_state = context.context_data.get('active_workflows', {}).get(rule.name, {})
        
        try:
            # Execute current step
            if current_step < len(workflow_steps):
                step = workflow_steps[current_step]
                step_result = self._execute_workflow_step(step, context, trigger_data, workflow_state)
                executed_steps.append(step_result)
                
                if step_result.get('success'):
                    # Move to next step
                    workflow_state['current_step'] = current_step + 1
                    workflow_state['last_step_completed'] = timezone.now().isoformat()
                    
                    # Check if workflow is complete
                    if workflow_state['current_step'] >= len(workflow_steps):
                        workflow_state['completed'] = True
                        workflow_state['completed_at'] = timezone.now().isoformat()
                        self.logger.info(f"Workflow {rule.name} completed successfully")
                    
                    # Update context with workflow state
                    if 'active_workflows' not in context.context_data:
                        context.context_data['active_workflows'] = {}
                    context.context_data['active_workflows'][rule.name] = workflow_state
                    context.save()
                    
                    return {
                        'success': True,
                        'workflow_type': 'workflow',
                        'current_step': workflow_state['current_step'],
                        'total_steps': len(workflow_steps),
                        'completed': workflow_state.get('completed', False),
                        'executed_steps': executed_steps
                    }
                else:
                    # Step failed, workflow paused
                    workflow_state['paused'] = True
                    workflow_state['paused_at'] = timezone.now().isoformat()
                    workflow_state['last_error'] = step_result.get('error', 'Unknown error')
                    
                    if 'active_workflows' not in context.context_data:
                        context.context_data['active_workflows'] = {}
                    context.context_data['active_workflows'][rule.name] = workflow_state
                    context.save()
                    
                    return {
                        'success': False,
                        'workflow_type': 'workflow',
                        'current_step': current_step,
                        'error': step_result.get('error'),
                        'paused': True
                    }
            else:
                # Workflow already completed
                return {
                    'success': True,
                    'workflow_type': 'workflow',
                    'completed': True,
                    'message': 'Workflow already completed'
                }
                
        except Exception as e:
            self.logger.error(f"Workflow execution failed: {str(e)}")
            return {
                'success': False,
                'workflow_type': 'workflow',
                'error': str(e),
                'current_step': current_step
            }
    
    def _execute_workflow_step(self, step: Dict[str, Any], context: ConversationContext, trigger_data: Dict[str, Any], workflow_state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single workflow step"""
        step_type = step.get('type')
        step_config = step.get('config', {})
        
        try:
            if step_type == 'condition':
                # Conditional step - check if we should proceed
                condition_result = self._evaluate_workflow_condition(step_config, context, trigger_data)
                return {
                    'success': condition_result,
                    'type': 'condition',
                    'result': condition_result
                }
            
            elif step_type == 'action':
                # Action step - execute the action
                action_result = self._execute_workflow_action(step_config, context, trigger_data)
                return {
                    'success': action_result,
                    'type': 'action',
                    'result': action_result
                }
            
            elif step_type == 'wait':
                # Wait step - pause workflow for specified time
                wait_hours = step_config.get('hours', 1)
                workflow_state['next_execution'] = (timezone.now() + timedelta(hours=wait_hours)).isoformat()
                
                return {
                    'success': True,
                    'type': 'wait',
                    'wait_hours': wait_hours
                }
            
            elif step_type == 'parallel':
                # Parallel step - execute multiple actions simultaneously
                parallel_actions = step_config.get('actions', [])
                results = []
                
                for action in parallel_actions:
                    try:
                        result = rule._execute_single_action(action, context, trigger_data)
                        results.append({
                            'action': action,
                            'success': result
                        })
                    except Exception as e:
                        results.append({
                            'action': action,
                            'success': False,
                            'error': str(e)
                        })
                
                overall_success = all(r['success'] for r in results)
                return {
                    'success': overall_success,
                    'type': 'parallel',
                    'results': results
                }
            
            else:
                return {
                    'success': False,
                    'type': 'unknown',
                    'error': f"Unknown step type: {step_type}"
                }
                
        except Exception as e:
            return {
                'success': False,
                'type': step_type,
                'error': str(e)
            }
    
    def _evaluate_workflow_condition(self, condition_config: Dict[str, Any], context: ConversationContext, trigger_data: Dict[str, Any]) -> bool:
        """Evaluate a workflow condition"""
        condition_type = condition_config.get('type')
        
        if condition_type == 'field_value':
            field_id = condition_config.get('field_id')
            operator = condition_config.get('operator')
            expected_value = condition_config.get('value')
            
            field_value = context.context_data.get(field_id)
            # We need to create a mock rule object or pass the rule to this method
            # For now, let's implement a simple comparison
            return self._compare_values_simple(field_value, operator, expected_value)
        
        elif condition_type == 'time_elapsed':
            hours_since_trigger = condition_config.get('hours', 24)
            trigger_time = trigger_data.get('triggered_at')
            
            if trigger_time:
                try:
                    trigger_datetime = datetime.fromisoformat(trigger_time.replace('Z', '+00:00'))
                    elapsed_hours = (timezone.now() - trigger_datetime).total_seconds() / 3600
                    return elapsed_hours >= hours_since_trigger
                except:
                    return False
            
            return False
        
        elif condition_type == 'external_check':
            # Implement external system checks
            return True
        
        return True
    
    def _compare_values_simple(self, field_value, operator, expected_value):
        """Simple value comparison for workflow conditions"""
        if operator == 'equals':
            return field_value == expected_value
        elif operator == 'not_equals':
            return field_value != expected_value
        elif operator == 'contains':
            return expected_value in str(field_value or '')
        elif operator == 'greater_than':
            return (field_value or 0) > expected_value
        elif operator == 'less_than':
            return (field_value or 0) < expected_value
        elif operator == 'in':
            return field_value in (expected_value or [])
        elif operator == 'not_in':
            return field_value not in (expected_value or [])
        elif operator == 'is_empty':
            return not field_value
        elif operator == 'is_not_empty':
            return bool(field_value)
        
        return False
    
    def _execute_workflow_action(self, action_config: Dict[str, Any], context: ConversationContext, trigger_data: Dict[str, Any]) -> bool:
        """Execute a workflow action"""
        action_type = action_config.get('type')
        config = action_config.get('config', {})
        
        try:
            if action_type == 'assign_tag':
                tag = config.get('tag')
                if tag:
                    if context.tags is None:
                        context.tags = []
                    if tag not in context.tags:
                        context.tags.append(tag)
                        context.save()
                    return True
                return False
            
            elif action_type == 'send_notification':
                # Import here to avoid circular imports
                from notifications.models import Notification
                message = config.get('message', 'Workflow notification')
                try:
                    # Check what fields the Notification model actually has
                    notification_data = {
                        'title': f"Workflow: {action_config.get('workflow_name', 'Unknown')}",
                        'message': message,
                        'notification_type': 'workflow_notification',
                    }
                    
                    # Add optional fields if they exist
                    if hasattr(Notification, 'workspace'):
                        notification_data['workspace'] = context.conversation.workspace
                    if hasattr(Notification, 'related_conversation'):
                        notification_data['related_conversation'] = context.conversation
                    
                    # Check for required fields
                    if hasattr(Notification, 'user_id') and 'user_id' not in notification_data:
                        # Try to get a default user from the workspace
                        try:
                            default_user = context.conversation.workspace.owner
                            if default_user:
                                notification_data['user_id'] = default_user.id
                        except:
                            pass
                    
                    Notification.objects.create(**notification_data)
                    return True
                except Exception as e:
                    self.logger.error(f"Failed to create notification: {str(e)}")
                    # For now, just log the success without creating the notification
                    self.logger.info(f"Would create notification: {message}")
                    return True  # Return True to continue workflow
            
            elif action_type == 'change_status':
                new_status = config.get('status')
                if new_status:
                    return context.update_status(new_status)
                return False
            
            elif action_type == 'change_priority':
                new_priority = config.get('priority')
                if new_priority:
                    context.priority = new_priority
                    context.save()
                    return True
                return False
            
            else:
                self.logger.warning(f"Unknown workflow action type: {action_type}")
                return False
                
        except Exception as e:
            self.logger.error(f"Workflow action execution failed: {str(e)}")
            return False
    
    def _execute_simple_rule(self, rule: BusinessRule, context: ConversationContext, trigger_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a simple rule without workflow"""
        start_time = time.time()
        
        try:
            # Execute the rule's actions
            execution_result = rule.execute_actions(context, trigger_data)
            
            execution_time = time.time() - start_time
            
            # Update rule performance metrics
            self._update_rule_metrics(rule, execution_time, execution_result)
            
            return {
                'success': True,
                'workflow_type': 'simple',
                'execution_time': execution_time,
                'actions_executed': len(execution_result),
                'successful_actions': len([a for a in execution_result if a.get('success', False)])
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Simple rule execution failed: {str(e)}")
            
            return {
                'success': False,
                'workflow_type': 'simple',
                'error': str(e),
                'execution_time': execution_time
            }
    
    def _execute_rollback_actions(self, rule: BusinessRule, context: ConversationContext, trigger_data: Dict[str, Any]):
        """Execute rollback actions when a rule fails"""
        try:
            rollback_actions = rule.rollback_actions or []
            
            for action in rollback_actions:
                try:
                    rule._execute_single_action(action, context, trigger_data)
                    self.logger.info(f"Rollback action executed: {action.get('type')}")
                except Exception as e:
                    self.logger.error(f"Rollback action failed: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"Rollback execution failed: {str(e)}")
    
    def _update_rule_metrics(self, rule: BusinessRule, execution_time: float, execution_result: List[Dict[str, Any]]):
        """Update rule performance metrics"""
        try:
            # Calculate success rate for this execution
            successful_actions = len([a for a in execution_result if a.get('success', False)])
            total_actions = len(execution_result)
            current_success_rate = successful_actions / total_actions if total_actions > 0 else 1.0
            
            # Update average execution time
            if rule.average_execution_time == 0:
                rule.average_execution_time = execution_time
            else:
                rule.average_execution_time = (rule.average_execution_time + execution_time) / 2
            
            # Update success rate
            if rule.execution_count == 0:
                rule.success_rate = current_success_rate
            else:
                rule.success_rate = (rule.success_rate * (rule.execution_count - 1) + current_success_rate) / rule.execution_count
            
            # Check if rule should be auto-deactivated
            should_deactivate, reason = rule.should_auto_deactivate()
            if should_deactivate:
                rule.is_active = False
                self.logger.warning(f"Auto-deactivating rule {rule.name}: {reason}")
            
            rule.save(update_fields=[
                'average_execution_time', 'success_rate', 'is_active'
            ])
            
        except Exception as e:
            self.logger.error(f"Failed to update rule metrics: {str(e)}")
    
    def _update_conversation_metrics(self, conversation: Conversation, executed_rules: List[Dict[str, Any]]):
        """Update conversation-level metrics after rule execution"""
        try:
            # Count successful rule executions
            successful_rules = len([r for r in executed_rules if r.get('result', {}).get('success', False)])
            total_rules = len(executed_rules)
            
            # Update conversation context with rule execution summary
            context = self._get_or_create_context(conversation)
            if context:
                if 'rule_executions' not in context.context_data:
                    context.context_data['rule_executions'] = []
                
                execution_summary = {
                    'timestamp': timezone.now().isoformat(),
                    'total_rules': total_rules,
                    'successful_rules': successful_rules,
                    'success_rate': successful_rules / total_rules if total_rules > 0 else 0
                }
                
                context.context_data['rule_executions'].append(execution_summary)
                context.save()
                
        except Exception as e:
            self.logger.error(f"Failed to update conversation metrics: {str(e)}")
    
    def _get_or_create_context(self, conversation: Conversation) -> Optional[ConversationContext]:
        """Get or create conversation context"""
        try:
            context = ConversationContext.objects.filter(conversation=conversation).first()
            if not context:
                # Create default context if none exists
                from .models import WorkspaceContextSchema
                default_schema = WorkspaceContextSchema.objects.filter(
                    workspace=conversation.workspace,
                    is_default=True
                ).first()
                
                if default_schema:
                    context = ConversationContext.objects.create(
                        conversation=conversation,
                        schema=default_schema,
                        status='new',
                        priority='medium'
                    )
                    self.logger.info(f"Created default context for conversation {conversation.id}")
            
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to get/create context: {str(e)}")
            return None
    
    def _prepare_context_data(self, context: ConversationContext) -> Dict[str, Any]:
        """Prepare context data for rule evaluation"""
        return {
            'context_data': context.context_data or {},
            'status': context.status,
            'priority': context.priority,
            'completion_percentage': getattr(context, 'completion_percentage', 0),
            'tags': context.tags or [],
            'created_at': context.created_at,
            'updated_at': context.updated_at
        }
    
    def _log_rule_failure(self, rule: BusinessRule, context: ConversationContext, trigger_data: Dict[str, Any], error: str):
        """Log rule execution failure"""
        try:
            RuleExecution.objects.create(
                rule=rule,
                context=context,
                trigger_type=trigger_data.get('trigger_type', 'unknown') if trigger_data else 'unknown',
                trigger_data=trigger_data or {},
                execution_result={},
                success=False,
                error_message=error,
                execution_time=0.0
            )
        except Exception as e:
            self.logger.error(f"Failed to log rule failure: {str(e)}")


class RuleTemplateManager:
    """Manager for business rule templates"""
    
    def __init__(self):
        self.logger = logger
    
    def get_industry_templates(self, industry: str) -> List[Dict[str, Any]]:
        """Get business rule templates for a specific industry"""
        templates = {
            'banking': self._get_banking_templates(),
            'healthcare': self._get_healthcare_templates(),
            'ecommerce': self._get_ecommerce_templates(),
            'support': self._get_support_templates(),
            'sales': self._get_sales_templates()
        }
        
        return templates.get(industry.lower(), [])
    
    def _get_banking_templates(self) -> List[Dict[str, Any]]:
        """Banking industry rule templates"""
        return [
            {
                'name': 'High-Value Customer Escalation',
                'description': 'Automatically escalate high-value customer inquiries',
                'trigger_type': 'context_change',
                'trigger_conditions': {
                    'operator': 'and',
                    'rules': [
                        {'field': 'customer_tier', 'operator': 'in', 'value': ['gold', 'platinum']},
                        {'field': 'inquiry_type', 'operator': 'equals', 'value': 'urgent'}
                    ]
                },
                'actions': [
                    {'type': 'change_priority', 'config': {'priority': 'high'}},
                    {'type': 'assign_tag', 'config': {'tag': 'high_value_customer'}},
                    {'type': 'send_notification', 'config': {'message': 'High-value customer inquiry escalated'}}
                ],
                'time_conditions': {
                    'business_hours': {'start_hour': 9, 'end_hour': 17, 'business_days': [0, 1, 2, 3, 4]}
                }
            },
            {
                'name': 'Compliance Check Workflow',
                'description': 'Multi-step compliance verification workflow',
                'trigger_type': 'new_message',
                'workflow_steps': [
                    {
                        'type': 'condition',
                        'config': {'type': 'field_value', 'field_id': 'compliance_required', 'operator': 'equals', 'value': True}
                    },
                    {
                        'type': 'action',
                        'config': {'type': 'assign_tag', 'config': {'tag': 'compliance_review'}}
                    },
                    {
                        'type': 'wait',
                        'config': {'hours': 2}
                    },
                    {
                        'type': 'action',
                        'config': {'type': 'send_notification', 'config': {'message': 'Compliance review required'}}
                    }
                ]
            }
        ]
    
    def _get_healthcare_templates(self) -> List[Dict[str, Any]]:
        """Healthcare industry rule templates"""
        return [
            {
                'name': 'Emergency Triage',
                'description': 'Automatically triage emergency medical inquiries',
                'trigger_type': 'context_change',
                'trigger_conditions': {
                    'operator': 'or',
                    'rules': [
                        {'field': 'symptom_severity', 'operator': 'equals', 'value': 'critical'},
                        {'field': 'patient_age', 'operator': 'less_than', 'value': 18}
                    ]
                },
                'actions': [
                    {'type': 'change_priority', 'config': {'priority': 'critical'}},
                    {'type': 'assign_tag', 'config': {'tag': 'emergency_triage'}},
                    {'type': 'generate_ai_response', 'config': {}}
                ]
            }
        ]
    
    def _get_ecommerce_templates(self) -> List[Dict[str, Any]]:
        """E-commerce industry rule templates"""
        return [
            {
                'name': 'Order Issue Escalation',
                'description': 'Escalate order-related issues',
                'trigger_type': 'context_change',
                'trigger_conditions': {
                    'operator': 'and',
                    'rules': [
                        {'field': 'issue_type', 'operator': 'equals', 'value': 'order_problem'},
                        {'field': 'customer_satisfaction', 'operator': 'less_than', 'value': 3}
                    ]
                },
                'actions': [
                    {'type': 'change_priority', 'config': {'priority': 'high'}},
                    {'type': 'assign_tag', 'config': {'tag': 'order_issue'}},
                    {'type': 'schedule_followup', 'config': {'delay_hours': 4}}
                ]
            }
        ]
    
    def _get_support_templates(self) -> List[Dict[str, Any]]:
        """Customer support industry rule templates"""
        return [
            {
                'name': 'Response Time SLA',
                'description': 'Ensure response time meets SLA requirements',
                'trigger_type': 'time_elapsed',
                'time_conditions': {
                    'time_window': {'start_time': '09:00', 'end_time': '17:00'}
                },
                'actions': [
                    {'type': 'change_priority', 'config': {'priority': 'high'}},
                    {'type': 'assign_tag', 'config': {'tag': 'sla_breach'}},
                    {'type': 'send_notification', 'config': {'message': 'SLA response time exceeded'}}
                ]
            }
        ]
    
    def _get_sales_templates(self) -> List[Dict[str, Any]]:
        """Sales industry rule templates"""
        return [
            {
                'name': 'Lead Qualification',
                'description': 'Automatically qualify sales leads',
                'trigger_type': 'context_change',
                'trigger_conditions': {
                    'operator': 'and',
                    'rules': [
                        {'field': 'budget_range', 'operator': 'equals', 'value': 'Over $1000'},
                        {'field': 'decision_maker', 'operator': 'equals', 'value': 'Yes'}
                    ]
                },
                'actions': [
                    {'type': 'change_priority', 'config': {'priority': 'high'}},
                    {'type': 'assign_tag', 'config': {'tag': 'qualified_lead'}},
                    {'type': 'assign_agent', 'config': {'agent_id': 'senior_sales'}}
                ]
            }
        ]
    
    def create_rule_from_template(self, workspace: Workspace, template: Dict[str, Any], customizations: Dict[str, Any] = None) -> BusinessRule:
        """Create a business rule from a template"""
        try:
            # Merge template with customizations
            rule_data = template.copy()
            if customizations:
                rule_data.update(customizations)
            
            # Create the rule
            rule = BusinessRule.objects.create(
                workspace=workspace,
                name=rule_data['name'],
                description=rule_data['description'],
                trigger_type=rule_data['trigger_type'],
                trigger_conditions=rule_data.get('trigger_conditions', {}),
                actions=rule_data.get('actions', []),
                workflow_steps=rule_data.get('workflow_steps', []),
                time_conditions=rule_data.get('time_conditions', {}),
                field_dependencies=rule_data.get('field_dependencies', {}),
                is_template=False,
                is_active=True
            )
            
            self.logger.info(f"Created rule from template: {rule.name}")
            return rule
            
        except Exception as e:
            self.logger.error(f"Failed to create rule from template: {str(e)}")
            raise
