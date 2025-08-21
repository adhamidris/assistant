from rest_framework import serializers
from django.core.files.uploadedfile import UploadedFile
from .models import KBDocument, KBChunk, SearchQuery
from core.models import Workspace


class KBDocumentSerializer(serializers.ModelSerializer):
    """Serializer for KBDocument model"""
    file_size_mb = serializers.SerializerMethodField()
    chunk_count = serializers.SerializerMethodField()
    processing_status = serializers.SerializerMethodField()
    
    class Meta:
        model = KBDocument
        fields = [
            'id', 'workspace', 'title', 'file_url', 'file_type', 
            'file_size', 'file_size_mb', 'chunk_count',
            'is_processed', 'processing_status', 'processing_error',
            'uploaded_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'file_url', 'file_type', 'file_size', 'is_processed',
            'processing_error', 'uploaded_at', 'updated_at', 'file_size_mb',
            'chunk_count', 'processing_status'
        ]
    
    def get_file_size_mb(self, obj):
        """Convert file size to MB"""
        if obj.file_size:
            return round(obj.file_size / (1024 * 1024), 2)
        return 0
    
    def get_chunk_count(self, obj):
        """Get number of chunks for this document"""
        return obj.chunks.count()
    
    def get_processing_status(self, obj):
        """Get human-readable processing status"""
        if obj.processing_error:
            return 'failed'
        elif obj.is_processed:
            return 'completed'
        else:
            return 'pending'


class KBChunkSerializer(serializers.ModelSerializer):
    """Serializer for KBChunk model"""
    document_title = serializers.CharField(source='document.title', read_only=True)
    similarity_score = serializers.FloatField(read_only=True)  # For search results
    
    class Meta:
        model = KBChunk
        fields = [
            'id', 'document', 'document_title', 'text', 'chunk_index',
            'word_count', 'char_count', 'similarity_score', 'created_at'
        ]
        read_only_fields = [
            'id', 'document_title', 'word_count', 'char_count',
            'similarity_score', 'created_at'
        ]


class DocumentUploadSerializer(serializers.Serializer):
    """Serializer for document uploads"""
    file = serializers.FileField()
    title = serializers.CharField(max_length=255)
    workspace_id = serializers.UUIDField()
    
    def validate_file(self, value):
        """Validate uploaded document"""
        if not value:
            raise serializers.ValidationError("No file provided")
        
        # Check file size (50MB limit)
        max_size = 50 * 1024 * 1024  # 50MB
        if value.size > max_size:
            raise serializers.ValidationError("File too large (max 50MB)")
        
        # Check file type
        allowed_types = [
            'application/pdf', 'text/plain', 'text/csv',
            'application/msword', 
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ]
        
        if hasattr(value, 'content_type') and value.content_type not in allowed_types:
            raise serializers.ValidationError(f"File type not allowed: {value.content_type}")
        
        return value
    
    def validate_workspace_id(self, value):
        """Validate workspace exists"""
        try:
            Workspace.objects.get(id=value)
            return value
        except Workspace.DoesNotExist:
            raise serializers.ValidationError("Workspace not found")


class SearchKnowledgeBaseSerializer(serializers.Serializer):
    """Serializer for knowledge base search"""
    query = serializers.CharField(max_length=500)
    workspace_id = serializers.UUIDField(required=False)
    limit = serializers.IntegerField(default=5, min_value=1, max_value=20)
    threshold = serializers.FloatField(default=0.7, min_value=0.0, max_value=1.0)
    
    def validate_query(self, value):
        """Validate search query"""
        if not value or not value.strip():
            raise serializers.ValidationError("Query cannot be empty")
        
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Query too short (minimum 3 characters)")
        
        return value.strip()
    
    def validate_workspace_id(self, value):
        """Validate workspace exists if provided"""
        if value:
            try:
                Workspace.objects.get(id=value)
                return value
            except Workspace.DoesNotExist:
                raise serializers.ValidationError("Workspace not found")
        return value


class SearchResultSerializer(serializers.Serializer):
    """Serializer for search results"""
    chunks = KBChunkSerializer(many=True)
    query = serializers.CharField()
    total_results = serializers.IntegerField()
    search_time_ms = serializers.IntegerField()


class ProcessDocumentSerializer(serializers.Serializer):
    """Serializer for triggering document processing"""
    force_reprocess = serializers.BooleanField(default=False)


class DocumentStatsSerializer(serializers.Serializer):
    """Serializer for document statistics"""
    total_documents = serializers.IntegerField()
    processed_documents = serializers.IntegerField()
    failed_documents = serializers.IntegerField()
    total_chunks = serializers.IntegerField()
    total_size_mb = serializers.FloatField()
    
    # File type breakdown
    file_types = serializers.DictField()
    
    # Recent activity
    documents_this_week = serializers.IntegerField()
    documents_this_month = serializers.IntegerField()


class SearchQuerySerializer(serializers.ModelSerializer):
    """Serializer for SearchQuery model"""
    workspace_name = serializers.CharField(source='workspace.name', read_only=True)
    
    class Meta:
        model = SearchQuery
        fields = [
            'id', 'workspace', 'workspace_name', 'query_text', 
            'results_count', 'created_at'
        ]
        read_only_fields = ['id', 'workspace_name', 'created_at']


class BulkDeleteSerializer(serializers.Serializer):
    """Serializer for bulk document deletion"""
    document_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=1,
        max_length=50
    )
    
    def validate_document_ids(self, value):
        """Validate all documents exist and belong to the same workspace"""
        if not value:
            raise serializers.ValidationError("No document IDs provided")
        
        # Check if all documents exist
        existing_docs = KBDocument.objects.filter(id__in=value)
        existing_ids = set(existing_docs.values_list('id', flat=True))
        provided_ids = set(value)
        
        missing_ids = provided_ids - existing_ids
        if missing_ids:
            raise serializers.ValidationError(f"Documents not found: {list(missing_ids)}")
        
        # Check if all documents belong to the same workspace
        workspaces = existing_docs.values_list('workspace_id', flat=True).distinct()
        if len(workspaces) > 1:
            raise serializers.ValidationError("All documents must belong to the same workspace")
        
        return value


class DocumentContentSerializer(serializers.Serializer):
    """Serializer for viewing document content"""
    include_chunks = serializers.BooleanField(default=False)
    chunk_limit = serializers.IntegerField(default=10, min_value=1, max_value=100)


class ReindexDocumentSerializer(serializers.Serializer):
    """Serializer for reindexing documents"""
    document_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="Specific document IDs to reindex. If empty, reindex all documents."
    )
    workspace_id = serializers.UUIDField(
        required=False,
        help_text="Workspace ID to reindex all documents for a workspace"
    )
    
    def validate(self, attrs):
        """Validate that either document_ids or workspace_id is provided"""
        document_ids = attrs.get('document_ids')
        workspace_id = attrs.get('workspace_id')
        
        if not document_ids and not workspace_id:
            raise serializers.ValidationError(
                "Either document_ids or workspace_id must be provided"
            )
        
        if workspace_id:
            try:
                Workspace.objects.get(id=workspace_id)
            except Workspace.DoesNotExist:
                raise serializers.ValidationError("Workspace not found")
        
        return attrs

