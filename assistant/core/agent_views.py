from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import Workspace, AIAgent, AgentSchemaAssignment, BusinessTypeTemplate
from .serializers import AIAgentSerializer, AgentSchemaAssignmentSerializer, BusinessTypeTemplateSerializer


class AIAgentViewSet(viewsets.ModelViewSet):
    """API viewset for managing AI agents"""
    serializer_class = AIAgentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get agents for the specified workspace"""
        workspace_slug = self.kwargs.get('workspace_slug')
        if workspace_slug:
            return AIAgent.objects.filter(workspace__slug=workspace_slug)
        return AIAgent.objects.none()
    
    def perform_create(self, serializer):
        """Create agent with workspace assignment"""
        workspace_slug = self.kwargs.get('workspace_slug')
        workspace = get_object_or_404(Workspace, slug=workspace_slug)
        
        # Ensure slug uniqueness within workspace
        slug = serializer.validated_data.get('slug')
        if AIAgent.objects.filter(workspace=workspace, slug=slug).exists():
            raise serializers.ValidationError(f"Agent with slug '{slug}' already exists in this workspace")
        
        serializer.save(workspace=workspace, created_by=self.request.user)
    
    def perform_update(self, serializer):
        """Update agent with validation"""
        # Ensure slug uniqueness within workspace
        workspace = serializer.instance.workspace
        slug = serializer.validated_data.get('slug')
        if slug != serializer.instance.slug:
            if AIAgent.objects.filter(workspace=workspace, slug=slug).exists():
                raise serializers.ValidationError(f"Agent with slug '{slug}' already exists in this workspace")
        
        serializer.save()
    
    @action(detail=True, methods=['post'])
    def generate_prompt(self, request, pk=None, workspace_slug=None):
        """Generate optimized prompt for agent"""
        agent = self.get_object()
        
        try:
            # This will be implemented when we create the EnhancedDeepSeekClient
            # For now, return a basic prompt
            basic_prompt = f"""You are an AI assistant for {agent.workspace.name}.

Your name is {agent.name}.
Channel: {agent.get_channel_type_display()}
Description: {agent.description}

Please be helpful and professional in your responses.

{agent.custom_instructions or ''}"""
            
            agent.generated_prompt = basic_prompt
            agent.save()
            
            return Response({
                'prompt': basic_prompt,
                'message': 'Prompt generated successfully'
            })
            
        except Exception as e:
            return Response({
                'error': f'Failed to generate prompt: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['get'])
    def portal_url(self, request, pk=None, workspace_slug=None):
        """Get agent portal URL"""
        agent = self.get_object()
        return Response({
            'url': agent.get_portal_url(),
            'deployment_url': agent.get_deployment_url()
        })
    
    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None, workspace_slug=None):
        """Toggle agent active status"""
        agent = self.get_object()
        agent.is_active = not agent.is_active
        agent.save()
        
        return Response({
            'id': agent.id,
            'is_active': agent.is_active,
            'message': f'Agent {"activated" if agent.is_active else "deactivated"} successfully'
        })
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None, workspace_slug=None):
        """Set this agent as the default for the workspace"""
        agent = self.get_object()
        
        with transaction.atomic():
            # Remove default status from other agents in the workspace
            AIAgent.objects.filter(workspace=agent.workspace, is_default=True).update(is_default=False)
            
            # Set this agent as default
            agent.is_default = True
            agent.save()
        
        return Response({
            'id': agent.id,
            'is_default': True,
            'message': f'Agent "{agent.name}" is now the default for workspace "{agent.workspace.name}"'
        })
    
    @action(detail=True, methods=['get'])
    def performance_metrics(self, request, pk=None, workspace_slug=None):
        """Get agent performance metrics"""
        agent = self.get_object()
        
        metrics = {
            'conversation_count': agent.conversation_count,
            'average_response_time': agent.average_response_time,
            'customer_satisfaction_score': agent.customer_satisfaction_score,
            'performance_metrics': agent.performance_metrics,
            'created_at': agent.created_at,
            'last_activity': agent.updated_at,
        }
        
        return Response(metrics)
    
    @action(detail=True, methods=['post'])
    def assign_schema(self, request, pk=None, workspace_slug=None):
        """Assign a schema to this agent"""
        agent = self.get_object()
        schema_id = request.data.get('schema_id')
        priority = request.data.get('priority', 1)
        is_primary = request.data.get('is_primary', False)
        
        if not schema_id:
            return Response({
                'error': 'schema_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            from context_tracking.models import WorkspaceContextSchema
            schema = WorkspaceContextSchema.objects.get(id=schema_id, workspace=agent.workspace)
            
            # Create or update assignment
            assignment, created = AgentSchemaAssignment.objects.get_or_create(
                agent=agent,
                schema=schema,
                defaults={
                    'priority': priority,
                    'is_primary': is_primary
                }
            )
            
            if not created:
                assignment.priority = priority
                assignment.is_primary = is_primary
                assignment.save()
            
            return Response({
                'message': f'Schema "{schema.name}" {"assigned" if created else "updated"} successfully',
                'assignment': AgentSchemaAssignmentSerializer(assignment).data
            })
            
        except WorkspaceContextSchema.DoesNotExist:
            return Response({
                'error': 'Schema not found or does not belong to this workspace'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Failed to assign schema: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class BusinessTypeTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """API viewset for business type templates"""
    serializer_class = BusinessTypeTemplateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get active business type templates"""
        return BusinessTypeTemplate.objects.filter(is_active=True)
    
    @action(detail=True, methods=['post'])
    def apply_to_workspace(self, request, pk=None):
        """Apply this template to a workspace"""
        template = self.get_object()
        workspace_slug = request.data.get('workspace_slug')
        
        if not workspace_slug:
            return Response({
                'error': 'workspace_slug is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            workspace = Workspace.objects.get(slug=workspace_slug)
            
            # This will be implemented when we create the template application logic
            # For now, return success message
            return Response({
                'message': f'Template "{template.name}" applied to workspace "{workspace.name}" successfully',
                'template': template.name,
                'workspace': workspace.name
            })
            
        except Workspace.DoesNotExist:
            return Response({
                'error': 'Workspace not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'error': f'Failed to apply template: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
