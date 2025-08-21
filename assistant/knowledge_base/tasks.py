from celery import shared_task
from django.utils import timezone
import logging

from .models import KBDocument, KBChunk
from .utils import process_uploaded_document

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_document(self, document_id):
    """
    Background task to process uploaded documents
    
    Args:
        document_id: UUID of the KBDocument to process
    """
    try:
        logger.info(f"Starting document processing for {document_id}")
        
        # Process the document
        success = process_uploaded_document(document_id)
        
        if success:
            logger.info(f"Successfully processed document {document_id}")
            return {
                'status': 'success',
                'document_id': document_id,
                'message': 'Document processed successfully'
            }
        else:
            logger.error(f"Failed to process document {document_id}")
            return {
                'status': 'error',
                'document_id': document_id,
                'message': 'Document processing failed'
            }
            
    except Exception as exc:
        logger.error(f"Error processing document {document_id}: {str(exc)}")
        
        # Update document with error status
        try:
            document = KBDocument.objects.get(id=document_id)
            document.processing_error = str(exc)
            document.save()
        except KBDocument.DoesNotExist:
            pass
        
        # Retry task
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        
        raise exc


@shared_task
def reindex_document_embeddings(document_id):
    """
    Regenerate embeddings for all chunks of a document
    
    Args:
        document_id: UUID of the KBDocument to reindex
    """
    try:
        document = KBDocument.objects.get(id=document_id)
        
        # Get all chunks for this document
        chunks = KBChunk.objects.filter(document=document)
        
        from messaging.ai_utils import openai_client
        
        updated_count = 0
        failed_count = 0
        
        for chunk in chunks:
            try:
                # Generate new embedding
                embedding = openai_client.generate_embeddings(chunk.text)
                
                if embedding:
                    chunk.embedding_vector = embedding
                    chunk.save()
                    updated_count += 1
                else:
                    failed_count += 1
                    logger.warning(f"Failed to generate embedding for chunk {chunk.id}")
                    
            except Exception as e:
                failed_count += 1
                logger.error(f"Error processing chunk {chunk.id}: {str(e)}")
        
        logger.info(f"Reindexed document {document_id}: {updated_count} updated, {failed_count} failed")
        
        return {
            'document_id': document_id,
            'updated_count': updated_count,
            'failed_count': failed_count
        }
        
    except KBDocument.DoesNotExist:
        logger.error(f"Document {document_id} not found for reindexing")
        return {'error': 'Document not found'}
    
    except Exception as e:
        logger.error(f"Error reindexing document {document_id}: {str(e)}")
        return {'error': str(e)}


@shared_task
def cleanup_orphaned_chunks():
    """
    Clean up chunks that belong to deleted documents
    """
    try:
        # Find chunks with no corresponding document
        orphaned_chunks = KBChunk.objects.filter(document__isnull=True)
        count = orphaned_chunks.count()
        
        if count > 0:
            orphaned_chunks.delete()
            logger.info(f"Cleaned up {count} orphaned chunks")
        
        return {'cleaned_chunks': count}
        
    except Exception as e:
        logger.error(f"Error cleaning up orphaned chunks: {str(e)}")
        return {'error': str(e)}


@shared_task
def update_document_stats():
    """
    Update document processing statistics (runs hourly)
    """
    try:
        from django.core.cache import cache
        from django.db.models import Count, Sum
        
        # Calculate global stats
        total_docs = KBDocument.objects.count()
        processed_docs = KBDocument.objects.filter(
            is_processed=True, 
            processing_error__isnull=True
        ).count()
        failed_docs = KBDocument.objects.filter(
            processing_error__isnull=False
        ).count()
        total_chunks = KBChunk.objects.count()
        
        # Cache stats for 1 hour
        stats = {
            'total_documents': total_docs,
            'processed_documents': processed_docs,
            'failed_documents': failed_docs,
            'total_chunks': total_chunks,
            'last_updated': timezone.now().isoformat()
        }
        
        cache.set('kb_global_stats', stats, 3600)
        
        logger.info(f"Updated document stats: {total_docs} total, {processed_docs} processed")
        
        return stats
        
    except Exception as e:
        logger.error(f"Error updating document stats: {str(e)}")
        return {'error': str(e)}


@shared_task
def batch_process_documents(document_ids):
    """
    Process multiple documents in batch
    
    Args:
        document_ids: List of document IDs to process
    """
    results = {
        'successful': [],
        'failed': [],
        'total': len(document_ids)
    }
    
    for document_id in document_ids:
        try:
            success = process_uploaded_document(document_id)
            
            if success:
                results['successful'].append(document_id)
            else:
                results['failed'].append(document_id)
                
        except Exception as e:
            logger.error(f"Error processing document {document_id} in batch: {str(e)}")
            results['failed'].append(document_id)
    
    logger.info(f"Batch processing completed: {len(results['successful'])} successful, {len(results['failed'])} failed")
    
    return results


@shared_task
def optimize_vector_index():
    """
    Optimize the vector index for better search performance
    This is a placeholder for future vector index optimization
    """
    try:
        # For now, just log that optimization would happen here
        # In a production system, this might:
        # - Rebuild vector indices
        # - Optimize database tables
        # - Clean up unused embeddings
        
        logger.info("Vector index optimization completed (placeholder)")
        
        return {'status': 'completed', 'optimized_vectors': 0}
        
    except Exception as e:
        logger.error(f"Error optimizing vector index: {str(e)}")
        return {'error': str(e)}


@shared_task
def generate_search_analytics():
    """
    Generate analytics from search queries (runs daily)
    """
    try:
        from datetime import timedelta
        from collections import Counter
        
        # Get queries from last 7 days
        week_ago = timezone.now() - timedelta(days=7)
        recent_queries = SearchQuery.objects.filter(created_at__gte=week_ago)
        
        # Analyze query patterns
        total_queries = recent_queries.count()
        
        # Most common query terms
        query_terms = []
        for query in recent_queries.values_list('query_text', flat=True):
            query_terms.extend(query.lower().split())
        
        common_terms = Counter(query_terms).most_common(20)
        
        # Average results per query
        avg_results = recent_queries.aggregate(
            avg_results=Sum('results_count')
        )['avg_results'] or 0
        
        if total_queries > 0:
            avg_results = avg_results / total_queries
        
        analytics = {
            'total_queries_week': total_queries,
            'average_results_per_query': round(avg_results, 2),
            'common_terms': dict(common_terms),
            'generated_at': timezone.now().isoformat()
        }
        
        # Cache analytics for 24 hours
        from django.core.cache import cache
        cache.set('search_analytics', analytics, 86400)
        
        logger.info(f"Generated search analytics: {total_queries} queries analyzed")
        
        return analytics
        
    except Exception as e:
        logger.error(f"Error generating search analytics: {str(e)}")
        return {'error': str(e)}

