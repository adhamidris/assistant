from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.core.files.storage import default_storage
from django.utils import timezone
from django.db.models import Count, Sum, Q
import uuid
import os
import time

from .models import KBDocument, KBChunk, SearchQuery
from .serializers import (
    KBDocumentSerializer, KBChunkSerializer, DocumentUploadSerializer,
    SearchKnowledgeBaseSerializer, SearchResultSerializer, ProcessDocumentSerializer
)
from .utils import search_knowledge_base, process_uploaded_document
from core.models import Workspace


class KBDocumentViewSet(viewsets.ModelViewSet):
    """Knowledge base document management"""
    queryset = KBDocument.objects.all()
    serializer_class = KBDocumentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter documents by workspace"""
        queryset = KBDocument.objects.select_related('workspace').prefetch_related('chunks')
        
        # Filter by workspace
        workspace_id = self.request.query_params.get('workspace', None)
        if workspace_id:
            queryset = queryset.filter(workspace_id=workspace_id)
        
        return queryset.order_by('-uploaded_at')


class KBChunkViewSet(viewsets.ReadOnlyModelViewSet):
    """Knowledge base chunk viewing (read-only)"""
    queryset = KBChunk.objects.all()
    serializer_class = KBChunkSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter chunks by document or workspace"""
        queryset = KBChunk.objects.select_related('document')
        
        # Filter by document
        document_id = self.request.query_params.get('document', None)
        if document_id:
            queryset = queryset.filter(document_id=document_id)
        
        return queryset.order_by('document', 'chunk_index')


class UploadDocumentView(APIView):
    """Handle document uploads"""
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = DocumentUploadSerializer(data=request.data)
        if serializer.is_valid():
            uploaded_file = serializer.validated_data['file']
            title = serializer.validated_data['title']
            workspace_id = serializer.validated_data['workspace_id']
            
            try:
                workspace = Workspace.objects.get(id=workspace_id)
                
                # Generate unique filename
                file_extension = os.path.splitext(uploaded_file.name)[1]
                unique_filename = f"{uuid.uuid4()}{file_extension}"
                
                # Save file to storage
                file_path = f"knowledge-base/{workspace_id}/{unique_filename}"
                saved_path = default_storage.save(file_path, uploaded_file)
                file_url = default_storage.url(saved_path)
                
                # Create document record
                document = KBDocument.objects.create(
                    workspace=workspace,
                    title=title,
                    file_url=file_url,
                    file_size=uploaded_file.size,
                    file_type=uploaded_file.content_type
                )
                
                # Trigger background processing
                from .tasks import process_document
                task = process_document.delay(str(document.id))
                
                return Response({
                    'document': KBDocumentSerializer(document).data,
                    'message': 'Document uploaded successfully, processing started',
                    'task_id': task.id
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                return Response(
                    {'error': f'Document upload failed: {str(e)}'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SearchKnowledgeBaseView(APIView):
    """Search knowledge base using vector similarity"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = SearchKnowledgeBaseSerializer(data=request.data)
        if serializer.is_valid():
            query = serializer.validated_data['query']
            workspace_id = serializer.validated_data.get('workspace_id')
            limit = serializer.validated_data['limit']
            
            # Use workspace from request if not provided
            if not workspace_id:
                workspace_id = getattr(request, 'workspace', None)
                if hasattr(workspace_id, 'id'):
                    workspace_id = workspace_id.id
                else:
                    return Response(
                        {'error': 'Workspace context required'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            try:
                start_time = time.time()
                
                # Perform search
                results = search_knowledge_base(query, str(workspace_id), limit)
                
                search_time_ms = int((time.time() - start_time) * 1000)
                
                response_data = {
                    'chunks': results,
                    'query': query,
                    'total_results': len(results),
                    'search_time_ms': search_time_ms
                }
                
                return Response(response_data)
                
            except Exception as e:
                return Response(
                    {'error': f'Search failed: {str(e)}'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProcessDocumentView(APIView):
    """Manually trigger document processing"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, document_id):
        try:
            document = KBDocument.objects.get(id=document_id)
            
            # Trigger processing
            from .tasks import process_document
            task = process_document.delay(str(document.id))
            
            return Response({
                'message': 'Document processing started',
                'task_id': task.id,
                'document_id': document_id
            })
            
        except KBDocument.DoesNotExist:
            return Response(
                {'error': 'Document not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
