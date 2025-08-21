"""
AI Analysis API views for conversation insights
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
import logging

from core.models import Conversation
from .models import Message
from .ai_utils import conversation_analyzer
from .tasks import (
    analyze_conversation_sentiment, 
    generate_conversation_summary,
    extract_conversation_entities,
    generate_comprehensive_insights
)

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_conversation_sentiment_view(request, conversation_id):
    """
    Trigger sentiment analysis for a conversation
    """
    try:
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        # Check if user has access to this workspace
        if not hasattr(request, 'workspace') or conversation.workspace != request.workspace:
            return Response(
                {'error': 'Access denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Trigger background task
        task = analyze_conversation_sentiment.delay(str(conversation_id))
        
        return Response({
            'message': 'Sentiment analysis started',
            'task_id': task.id,
            'conversation_id': str(conversation_id)
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        logger.error(f"Error starting sentiment analysis: {str(e)}")
        return Response(
            {'error': 'Failed to start sentiment analysis'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_summary_view(request, conversation_id):
    """
    Trigger conversation summarization
    """
    try:
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        # Check if user has access to this workspace
        if not hasattr(request, 'workspace') or conversation.workspace != request.workspace:
            return Response(
                {'error': 'Access denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Trigger background task
        task = generate_conversation_summary.delay(str(conversation_id))
        
        return Response({
            'message': 'Summary generation started',
            'task_id': task.id,
            'conversation_id': str(conversation_id)
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        logger.error(f"Error starting summary generation: {str(e)}")
        return Response(
            {'error': 'Failed to start summary generation'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def extract_entities_view(request, conversation_id):
    """
    Trigger entity extraction for a conversation
    """
    try:
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        # Check if user has access to this workspace
        if not hasattr(request, 'workspace') or conversation.workspace != request.workspace:
            return Response(
                {'error': 'Access denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Trigger background task
        task = extract_conversation_entities.delay(str(conversation_id))
        
        return Response({
            'message': 'Entity extraction started',
            'task_id': task.id,
            'conversation_id': str(conversation_id)
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        logger.error(f"Error starting entity extraction: {str(e)}")
        return Response(
            {'error': 'Failed to start entity extraction'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_insights_view(request, conversation_id):
    """
    Trigger comprehensive insights generation for a conversation
    """
    try:
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        # Check if user has access to this workspace
        if not hasattr(request, 'workspace') or conversation.workspace != request.workspace:
            return Response(
                {'error': 'Access denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Trigger background task
        task = generate_comprehensive_insights.delay(str(conversation_id))
        
        return Response({
            'message': 'Comprehensive insights generation started',
            'task_id': task.id,
            'conversation_id': str(conversation_id)
        }, status=status.HTTP_202_ACCEPTED)
        
    except Exception as e:
        logger.error(f"Error starting insights generation: {str(e)}")
        return Response(
            {'error': 'Failed to start insights generation'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_conversation_insights(request, conversation_id):
    """
    Get the current AI insights for a conversation
    """
    try:
        conversation = get_object_or_404(Conversation, id=conversation_id)
        
        # Check if user has access to this workspace
        if not hasattr(request, 'workspace') or conversation.workspace != request.workspace:
            return Response(
                {'error': 'Access denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Prepare insights data
        insights_data = {
            'conversation_id': str(conversation_id),
            'has_insights': conversation.has_ai_insights,
            'insights_generated_at': conversation.insights_generated_at,
            'summary': conversation.summary,
            'key_points': conversation.key_points,
            'resolution_status': conversation.resolution_status,
            'action_items': conversation.action_items,
            'sentiment_score': conversation.sentiment_score,
            'sentiment_label': conversation.sentiment_label,
            'sentiment_data': conversation.sentiment_data,
            'extracted_entities': conversation.extracted_entities,
            'conversation_metrics': conversation.conversation_metrics,
            'status': conversation.status,
            'last_intent': conversation.last_intent
        }
        
        return Response(insights_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error retrieving conversation insights: {str(e)}")
        return Response(
            {'error': 'Failed to retrieve insights'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_message_text(request):
    """
    Analyze a single message or text snippet for sentiment and entities
    """
    try:
        text = request.data.get('text', '')
        if not text:
            return Response(
                {'error': 'Text is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Analyze sentiment
        sentiment_result = conversation_analyzer.analyze_sentiment(text)
        
        # Extract entities
        entities_result = conversation_analyzer.extract_entities(text)
        
        response_data = {
            'text': text,
            'sentiment': sentiment_result,
            'entities': entities_result,
            'analyzed_at': timezone.now().isoformat()
        }
        
        return Response(response_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error analyzing message text: {str(e)}")
        return Response(
            {'error': 'Failed to analyze text'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_workspace_analytics(request):
    """
    Get analytics and insights for the entire workspace
    """
    try:
        workspace = getattr(request, 'workspace', None)
        if not workspace:
            return Response(
                {'error': 'Workspace context required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get conversations for this workspace
        conversations = Conversation.objects.filter(workspace=workspace)
        
        # Calculate analytics
        total_conversations = conversations.count()
        active_conversations = conversations.filter(status='active').count()
        resolved_conversations = conversations.filter(status='resolved').count()
        
        # Sentiment distribution
        sentiment_distribution = {
            'very_positive': 0,
            'positive': 0,
            'neutral': 0,
            'negative': 0,
            'very_negative': 0
        }
        
        avg_sentiment_score = 0
        conversations_with_insights = conversations.filter(insights_generated_at__isnull=False)
        
        if conversations_with_insights.exists():
            for conv in conversations_with_insights:
                if conv.sentiment_data and conv.sentiment_data.get('overall_sentiment'):
                    sentiment = conv.sentiment_data['overall_sentiment']
                    if sentiment in sentiment_distribution:
                        sentiment_distribution[sentiment] += 1
            
            # Calculate average sentiment score
            sentiment_scores = [c.sentiment_score for c in conversations_with_insights if c.sentiment_score]
            if sentiment_scores:
                avg_sentiment_score = sum(sentiment_scores) / len(sentiment_scores)
        
        # Resolution status distribution
        resolution_distribution = {
            'resolved': conversations.filter(resolution_status='resolved').count(),
            'pending': conversations.filter(resolution_status='pending').count(),
            'escalated': conversations.filter(resolution_status='escalated').count()
        }
        
        # Common entities across conversations
        all_entities = {}
        for conv in conversations_with_insights:
            if conv.extracted_entities:
                for entity_type, entities in conv.extracted_entities.items():
                    if entity_type not in all_entities:
                        all_entities[entity_type] = {}
                    for entity in entities:
                        if entity not in all_entities[entity_type]:
                            all_entities[entity_type][entity] = 0
                        all_entities[entity_type][entity] += 1
        
        # Get top entities for each type
        top_entities = {}
        for entity_type, entities in all_entities.items():
            sorted_entities = sorted(entities.items(), key=lambda x: x[1], reverse=True)
            top_entities[entity_type] = sorted_entities[:5]  # Top 5 for each type
        
        analytics_data = {
            'workspace_id': str(workspace.id),
            'total_conversations': total_conversations,
            'active_conversations': active_conversations,
            'resolved_conversations': resolved_conversations,
            'conversations_with_insights': conversations_with_insights.count(),
            'avg_sentiment_score': round(avg_sentiment_score, 2),
            'sentiment_distribution': sentiment_distribution,
            'resolution_distribution': resolution_distribution,
            'top_entities': top_entities,
            'generated_at': timezone.now().isoformat()
        }
        
        return Response(analytics_data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error generating workspace analytics: {str(e)}")
        return Response(
            {'error': 'Failed to generate analytics'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
