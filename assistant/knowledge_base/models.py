from django.db import models
from django.contrib.postgres.fields import ArrayField
from core.models import Workspace
import uuid


class KBDocument(models.Model):
    """Knowledge base document model"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='kb_documents')
    
    title = models.CharField(max_length=255)
    content = models.TextField()
    file_url = models.URLField(blank=True, null=True)  # Original file location
    file_type = models.CharField(max_length=50, blank=True, null=True)  # pdf, txt, docx, etc.
    file_size = models.PositiveIntegerField(blank=True, null=True)  # Size in bytes
    
    # Processing status
    is_processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True, null=True)
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'kb_documents'
        ordering = ['-uploaded_at']
        
    def __str__(self):
        return f"{self.title} ({self.workspace.name})"


class KBChunk(models.Model):
    """Searchable text chunks with embeddings"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(KBDocument, on_delete=models.CASCADE, related_name='chunks')
    
    text = models.TextField()
    chunk_index = models.PositiveIntegerField()  # Order within document
    
    # Vector embeddings - using pgvector extension
    # This will store OpenAI text-embedding-ada-002 vectors (1536 dimensions)
    embedding_vector = ArrayField(
        models.FloatField(),
        size=1536,
        blank=True,
        null=True,
        help_text="1536-dimensional embedding vector"
    )
    
    # Metadata
    word_count = models.PositiveIntegerField(blank=True, null=True)
    char_count = models.PositiveIntegerField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'kb_chunks'
        ordering = ['document', 'chunk_index']
        indexes = [
            models.Index(fields=['document', 'chunk_index']),
        ]
        
    def __str__(self):
        preview = (self.text[:100] + '...') if len(self.text) > 100 else self.text
        return f"Chunk {self.chunk_index} of {self.document.title}: {preview}"


class SearchQuery(models.Model):
    """Track search queries for analytics"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(Workspace, on_delete=models.CASCADE, related_name='search_queries')
    
    query_text = models.TextField()
    results_count = models.PositiveIntegerField(default=0)
    
    # Query embedding for similarity analysis
    query_embedding = ArrayField(
        models.FloatField(),
        size=1536,
        blank=True,
        null=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'search_queries'
        ordering = ['-created_at']
        
    def __str__(self):
        preview = (self.query_text[:50] + '...') if len(self.query_text) > 50 else self.query_text
        return f"Query: {preview} ({self.results_count} results)"
