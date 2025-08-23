from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from typing import Dict, List, Any

from .models import DynamicFieldSuggestion, WorkspaceContextSchema
from .serializers import DynamicFieldSuggestionSerializer
from .services import FieldSuggestionService
from core.models import Workspace


class FieldSuggestionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing AI-discovered field suggestions"""
    
    serializer_class = DynamicFieldSuggestionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter suggestions by workspace"""
        workspace_id = self.request.query_params.get('workspace')
        if workspace_id:
            return DynamicFieldSuggestion.objects.filter(workspace_id=workspace_id)
        return DynamicFieldSuggestion.objects.none()
    
    @action(detail=False, methods=['post'], url_path='generate')
    def generate_suggestions(self, request):
        """Generate new field suggestions for a workspace"""
        try:
            workspace_id = request.data.get('workspace_id')
            limit = request.data.get('limit', 10)
            
            if not workspace_id:
                return Response(
                    {'error': 'workspace_id is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if user has access to this workspace
            workspace = get_object_or_404(Workspace, id=workspace_id)
            if workspace.owner != request.user:
                return Response(
                    {'error': 'Access denied'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Generate suggestions
            service = FieldSuggestionService()
            suggestions = service.generate_suggestions_for_workspace(workspace_id, limit)
            
            # Serialize suggestions
            serializer = self.get_serializer(suggestions, many=True)
            
            return Response({
                'success': True,
                'suggestions': serializer.data,
                'count': len(suggestions)
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to generate suggestions: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='approve')
    def approve_suggestion(self, request, pk=None):
        """Approve a field suggestion"""
        try:
            suggestion = self.get_object()
            target_schema_id = request.data.get('target_schema_id')
            notes = request.data.get('notes', '')
            
            # Check if user has access to the workspace
            if suggestion.workspace.owner != request.user:
                return Response(
                    {'error': 'Access denied'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Approve the suggestion
            service = FieldSuggestionService()
            success = service.approve_suggestion(
                suggestion_id=str(suggestion.id),
                user_id=str(request.user.id),
                target_schema_id=target_schema_id,
                notes=notes
            )
            
            if success:
                return Response({
                    'success': True,
                    'message': 'Suggestion approved successfully'
                })
            else:
                return Response(
                    {'error': 'Failed to approve suggestion'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            return Response(
                {'error': f'Failed to approve suggestion: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='reject')
    def reject_suggestion(self, request, pk=None):
        """Reject a field suggestion"""
        try:
            suggestion = self.get_object()
            notes = request.data.get('notes', '')
            
            # Check if user has access to the workspace
            if suggestion.workspace.owner != request.user:
                return Response(
                    {'error': 'Access denied'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Reject the suggestion
            service = FieldSuggestionService()
            success = service.reject_suggestion(
                suggestion_id=str(suggestion.id),
                user_id=str(request.user.id),
                notes=notes
            )
            
            if success:
                return Response({
                    'success': True,
                    'message': 'Suggestion rejected successfully'
                })
            else:
                return Response(
                    {'error': 'Failed to reject suggestion'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            return Response(
                {'error': f'Failed to reject suggestion: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='analytics')
    def get_analytics(self, request):
        """Get analytics about field suggestions for a workspace"""
        try:
            workspace_id = request.query_params.get('workspace_id')
            
            if not workspace_id:
                return Response(
                    {'error': 'workspace_id is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if user has access to this workspace
            workspace = get_object_or_404(Workspace, id=workspace_id)
            if workspace.owner != request.user:
                return Response(
                    {'error': 'Access denied'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get analytics
            service = FieldSuggestionService()
            analytics = service.get_suggestion_analytics(workspace_id)
            
            return Response({
                'success': True,
                'analytics': analytics
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to get analytics: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='pending')
    def get_pending_suggestions(self, request):
        """Get pending field suggestions for a workspace"""
        try:
            workspace_id = request.query_params.get('workspace_id')
            
            if not workspace_id:
                return Response(
                    {'error': 'workspace_id is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if user has access to this workspace
            workspace = get_object_or_404(Workspace, id=workspace_id)
            if workspace.owner != request.user:
                return Response(
                    {'error': 'Access denied'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get pending suggestions
            pending_suggestions = DynamicFieldSuggestion.objects.filter(
                workspace_id=workspace_id,
                is_reviewed=False
            ).order_by('-business_value_score', '-confidence_score')
            
            serializer = self.get_serializer(pending_suggestions, many=True)
            
            return Response({
                'success': True,
                'suggestions': serializer.data,
                'count': len(pending_suggestions)
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to get pending suggestions: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='reviewed')
    def get_reviewed_suggestions(self, request):
        """Get reviewed field suggestions for a workspace"""
        try:
            workspace_id = request.query_params.get('workspace_id')
            
            if not workspace_id:
                return Response(
                    {'error': 'workspace_id is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if user has access to this workspace
            workspace = get_object_or_404(Workspace, id=workspace_id)
            if workspace.owner != request.user:
                return Response(
                    {'error': 'Access denied'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get reviewed suggestions
            reviewed_suggestions = DynamicFieldSuggestion.objects.filter(
                workspace_id=workspace_id,
                is_reviewed=True
            ).order_by('-reviewed_at')
            
            serializer = self.get_serializer(reviewed_suggestions, many=True)
            
            return Response({
                'success': True,
                'suggestions': serializer.data,
                'count': len(reviewed_suggestions)
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to get reviewed suggestions: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class IntelligentDiscoveryViewSet(viewsets.ViewSet):
    """ViewSet for intelligent discovery features"""
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'], url_path='analyze-conversations')
    def analyze_conversations(self, request):
        """Analyze conversations for pattern discovery"""
        try:
            workspace_id = request.data.get('workspace_id')
            
            if not workspace_id:
                return Response(
                    {'error': 'workspace_id is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if user has access to this workspace
            workspace = get_object_or_404(Workspace, id=workspace_id)
            if workspace.owner != request.user:
                return Response(
                    {'error': 'Access denied'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get recent conversations for analysis
            from core.models import Conversation
            recent_conversations = Conversation.objects.filter(
                workspace=workspace
            ).order_by('-created_at')[:100]  # Last 100 conversations
            
            # Extract conversation texts
            conversation_texts = []
            for conv in recent_conversations:
                messages = conv.messages.all()
                for msg in messages:
                    if msg.text:
                        conversation_texts.append(msg.text)
            
            if not conversation_texts:
                return Response({
                    'success': True,
                    'message': 'No conversations found for analysis',
                    'patterns': {}
                })
            
            # Analyze patterns using enhanced extraction
            from .services import EnhancedContextExtraction
            enhanced_extraction = EnhancedContextExtraction()
            patterns = enhanced_extraction._analyze_conversation_patterns(conversation_texts)
            
            return Response({
                'success': True,
                'patterns': patterns,
                'conversation_count': len(recent_conversations),
                'text_count': len(conversation_texts)
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to analyze conversations: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='discover-fields')
    def discover_fields(self, request):
        """Discover new fields from conversation analysis"""
        try:
            workspace_id = request.data.get('workspace_id')
            limit = request.data.get('limit', 10)
            
            if not workspace_id:
                return Response(
                    {'error': 'workspace_id is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if user has access to this workspace
            workspace = get_object_or_404(Workspace, id=workspace_id)
            if workspace.owner != request.user:
                return Response(
                    {'error': 'Access denied'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Discover fields using enhanced extraction
            from .services import EnhancedContextExtraction
            enhanced_extraction = EnhancedContextExtraction()
            
            # Get recent conversations
            from core.models import Conversation
            recent_conversations = Conversation.objects.filter(
                workspace=workspace
            ).order_by('-created_at')[:50]
            
            conversation_texts = []
            for conv in recent_conversations:
                messages = conv.messages.all()
                for msg in messages:
                    if msg.text:
                        conversation_texts.append(msg.text)
            
            if not conversation_texts:
                return Response({
                    'success': True,
                    'message': 'No conversations found for analysis',
                    'discovered_fields': []
                })
            
            # Discover fields
            discovered_fields = enhanced_extraction.discover_new_fields(
                workspace_id=workspace_id,
                conversation_texts=conversation_texts
            )
            
            # Limit results
            limited_fields = discovered_fields[:limit]
            
            return Response({
                'success': True,
                'discovered_fields': limited_fields,
                'total_discovered': len(discovered_fields),
                'returned_count': len(limited_fields)
            })
            
        except Exception as e:
            return Response(
                {'error': f'Failed to discover fields: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
