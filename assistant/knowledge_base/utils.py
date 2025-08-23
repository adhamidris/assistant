"""
Knowledge base utilities for document processing and vector search
"""

import os
import re
import logging
import hashlib
from typing import List, Dict, Optional, Tuple
from django.conf import settings
from django.core.cache import cache
from django.db import connection
import PyPDF2
# import magic  # Temporarily disabled for Windows compatibility
from io import BytesIO
import requests

from .models import KBDocument, KBChunk, SearchQuery
from messaging.deepseek_client import DeepSeekClient

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Process and extract text from various document types"""
    
    def __init__(self):
        self.supported_types = {
            'application/pdf': self.extract_pdf_text,
            'text/plain': self.extract_text_file,
            'text/csv': self.extract_text_file,
            'application/msword': self.extract_doc_text,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': self.extract_docx_text,
        }
    
    def detect_file_type(self, file_path: str) -> str:
        """Detect file type using python-magic"""
        try:
            mime = magic.Magic(mime=True)
            return mime.from_file(file_path)
        except Exception as e:
            logger.warning(f"Could not detect file type for {file_path}: {e}")
            # Fallback to extension-based detection
            ext = os.path.splitext(file_path)[1].lower()
            ext_to_mime = {
                '.pdf': 'application/pdf',
                '.txt': 'text/plain',
                '.csv': 'text/csv',
                '.doc': 'application/msword',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            }
            return ext_to_mime.get(ext, 'application/octet-stream')
    
    def extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"PDF extraction failed for {file_path}: {e}")
            return ""
    
    def extract_text_file(self, file_path: str) -> str:
        """Extract text from plain text files"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                return file.read().strip()
        except Exception as e:
            logger.error(f"Text extraction failed for {file_path}: {e}")
            return ""
    
    def extract_doc_text(self, file_path: str) -> str:
        """Extract text from DOC files (placeholder - requires additional libraries)"""
        logger.warning("DOC file processing not fully implemented")
        return ""
    
    def extract_docx_text(self, file_path: str) -> str:
        """Extract text from DOCX files (placeholder - requires additional libraries)"""
        logger.warning("DOCX file processing not fully implemented")
        return ""
    
    def process_document(self, file_path: str) -> Tuple[str, str]:
        """
        Process document and extract text
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Tuple of (extracted_text, file_type)
        """
        file_type = self.detect_file_type(file_path)
        
        if file_type not in self.supported_types:
            logger.warning(f"Unsupported file type: {file_type}")
            return "", file_type
        
        text = self.supported_types[file_type](file_path)
        return text, file_type
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove special characters but keep basic punctuation
        text = re.sub(r'[^\w\s\.\,\?\!\;\:\-\(\)]', ' ', text)
        
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text


class TextChunker:
    """Split text into chunks for vector embedding"""
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk_by_sentences(self, text: str) -> List[str]:
        """Split text into chunks by sentences, respecting chunk size"""
        sentences = re.split(r'[.!?]+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check if adding this sentence would exceed chunk size
            if len(current_chunk) + len(sentence) > self.chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                
                # Start new chunk with overlap
                if self.overlap > 0:
                    overlap_text = current_chunk[-self.overlap:] if len(current_chunk) > self.overlap else current_chunk
                    current_chunk = overlap_text + " " + sentence
                else:
                    current_chunk = sentence
            else:
                current_chunk += " " + sentence if current_chunk else sentence
        
        # Add the last chunk
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def chunk_by_paragraphs(self, text: str) -> List[str]:
        """Split text into chunks by paragraphs"""
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            if len(current_chunk) + len(paragraph) > self.chunk_size and current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                current_chunk += "\n\n" + paragraph if current_chunk else paragraph
        
        if current_chunk.strip():
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def chunk_text(self, text: str, method: str = 'sentences') -> List[str]:
        """
        Chunk text using specified method
        
        Args:
            text: Text to chunk
            method: Chunking method ('sentences' or 'paragraphs')
            
        Returns:
            List of text chunks
        """
        if method == 'paragraphs':
            return self.chunk_by_paragraphs(text)
        else:
            return self.chunk_by_sentences(text)


class VectorSearch:
    """Vector similarity search using pgvector"""
    
    def __init__(self):
        self.embedding_dim = 1536  # OpenAI text-embedding-ada-002 dimension
    
    def cosine_similarity_search(
        self, 
        query_embedding: List[float], 
        workspace_id: str,
        limit: int = 5,
        threshold: float = 0.7
    ) -> List[Dict]:
        """
        Perform cosine similarity search using raw SQL
        
        Args:
            query_embedding: Query vector embedding
            workspace_id: Workspace ID to filter results
            limit: Maximum number of results
            threshold: Minimum similarity threshold
            
        Returns:
            List of similar chunks with metadata
        """
        try:
            with connection.cursor() as cursor:
                # Use pgvector cosine similarity operator
                sql = """
                SELECT 
                    kc.id,
                    kc.text,
                    kc.chunk_index,
                    kd.title,
                    kd.id as document_id,
                    1 - (kc.embedding_vector <=> %s) as similarity
                FROM kb_chunks kc
                JOIN kb_documents kd ON kc.document_id = kd.id
                WHERE kd.workspace_id = %s 
                    AND kc.embedding_vector IS NOT NULL
                    AND 1 - (kc.embedding_vector <=> %s) > %s
                ORDER BY kc.embedding_vector <=> %s
                LIMIT %s
                """
                
                cursor.execute(sql, [
                    query_embedding, workspace_id, query_embedding, 
                    threshold, query_embedding, limit
                ])
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'id': row[0],
                        'text': row[1],
                        'chunk_index': row[2],
                        'document_title': row[3],
                        'document_id': row[4],
                        'similarity': float(row[5])
                    })
                
                return results
                
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []
    
    def search_knowledge_base(
        self, 
        query: str, 
        workspace_id: str, 
        limit: int = 5
    ) -> List[Dict]:
        """
        Search knowledge base using semantic similarity
        
        Args:
            query: Search query text
            workspace_id: Workspace ID
            limit: Maximum number of results
            
        Returns:
            List of relevant chunks
        """
        try:
            # Generate query embedding using DeepSeek
            deepseek_client = DeepSeekClient()
            # Note: DeepSeek doesn't have embeddings yet, so we'll skip for now
            query_embedding = None
            logger.warning("Embeddings not available with DeepSeek - using fallback search")
            if not query_embedding:
                logger.error("Failed to generate query embedding")
                return []
            
            # Perform similarity search
            results = self.cosine_similarity_search(
                query_embedding, workspace_id, limit
            )
            
            # Log search query for analytics
            SearchQuery.objects.create(
                workspace_id=workspace_id,
                query_text=query,
                results_count=len(results),
                query_embedding=query_embedding
            )
            
            return results
            
        except Exception as e:
            logger.error(f"Knowledge base search failed: {e}")
            return []


# Global instances
document_processor = DocumentProcessor()
text_chunker = TextChunker()
vector_search = VectorSearch()


def search_knowledge_base(query: str, workspace_id: str, limit: int = 5) -> List[Dict]:
    """
    Convenience function for searching knowledge base
    
    Args:
        query: Search query
        workspace_id: Workspace ID
        limit: Maximum results
        
    Returns:
        List of relevant chunks
    """
    return vector_search.search_knowledge_base(query, workspace_id, limit)


def process_uploaded_document(document_id: str) -> bool:
    """
    Process an uploaded document: extract text, chunk, and generate embeddings
    
    Args:
        document_id: KBDocument ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        document = KBDocument.objects.get(id=document_id)
        
        # Download file if it's a URL
        if document.file_url:
            response = requests.get(document.file_url)
            response.raise_for_status()
            
            # Save to temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(response.content)
                temp_file_path = temp_file.name
        else:
            logger.error(f"No file URL for document {document_id}")
            return False
        
        try:
            # Extract text
            extracted_text, file_type = document_processor.process_document(temp_file_path)
            
            if not extracted_text:
                document.processing_error = "Failed to extract text from document"
                document.save()
                return False
            
            # Clean text
            clean_text = document_processor.clean_text(extracted_text)
            
            # Update document with extracted content
            document.content = clean_text
            document.file_type = file_type
            document.save()
            
            # Chunk text
            chunks = text_chunker.chunk_text(clean_text)
            
            # Generate embeddings and save chunks
            for i, chunk_text in enumerate(chunks):
                # Note: DeepSeek doesn't have embeddings yet, so we'll skip for now
                embedding = None
                logger.warning("Embeddings not available with DeepSeek - skipping chunk embedding")
                
                # Create chunk without embedding for now
                KBChunk.objects.create(
                    document=document,
                    text=chunk_text,
                    chunk_index=i,
                    embedding_vector=embedding,
                    word_count=len(chunk_text.split()),
                    char_count=len(chunk_text)
                )
            
            # Mark as processed
            document.is_processed = True
            document.save()
            
            logger.info(f"Successfully processed document {document_id} into {len(chunks)} chunks")
            return True
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    except KBDocument.DoesNotExist:
        logger.error(f"Document {document_id} not found")
        return False
    
    except Exception as e:
        logger.error(f"Document processing failed for {document_id}: {e}")
        
        # Update document with error
        try:
            document = KBDocument.objects.get(id=document_id)
            document.processing_error = str(e)
            document.save()
        except KBDocument.DoesNotExist:
            pass
        
        return False

