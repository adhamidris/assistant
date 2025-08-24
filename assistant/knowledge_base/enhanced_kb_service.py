import logging
import time
from typing import Dict, Any, List, Optional, Callable
from django.db.models import Q
from .models import KBDocument, KBChunk
from .utils import search_knowledge_base

logger = logging.getLogger(__name__)

class EnhancedKnowledgeBaseService:
    """Enhanced knowledge base service with progressive feedback"""
    
    def __init__(self, workspace):
        self.workspace = workspace
        self.search_strategies = ["embeddings", "fulltext", "keyword"]
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
        
    def search_with_progressive_feedback(self, query: str, callback: Optional[Callable] = None) -> Optional[str]:
        """Search knowledge base with progressive feedback"""
        
        if callback:
            callback("Searching our knowledge base...")
        
        # Strategy 1: Embeddings search (if available)
        try:
            results = self._search_with_embeddings(query)
            if results and callback:
                callback("Found relevant information, analyzing...")
            if results:
                return self._format_search_results(results, "embeddings")
        except Exception as e:
            logger.warning(f"Embeddings search failed: {e}")
        
        if callback:
            callback("Performing comprehensive search...")
        
        # Strategy 2: Full-text search
        try:
            results = self._search_with_fulltext(query)
            if results:
                return self._format_search_results(results, "fulltext")
        except Exception as e:
            logger.warning(f"Full-text search failed: {e}")
        
        # Strategy 3: Keyword search
        results = self._search_with_keywords(query)
        return self._format_search_results(results, "keywords") if results else None
    
    def _search_with_embeddings(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Search using embeddings (if available)"""
        try:
            # Check cache first
            cache_key = f"embeddings_{hash(query)}"
            if cache_key in self._cache:
                cache_entry = self._cache[cache_key]
                if time.time() - cache_entry["timestamp"] < self._cache_ttl:
                    return cache_entry["results"]
            
            # Try to use embeddings search
            results = search_knowledge_base(query, str(self.workspace.id), limit=5)
            
            # Cache results
            self._cache[cache_key] = {
                "results": results,
                "timestamp": time.time()
            }
            
            return results
            
        except Exception as e:
            logger.warning(f"Embeddings search failed: {e}")
            return None
    
    def _search_with_fulltext(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Search using PostgreSQL full-text search"""
        try:
            # Check cache
            cache_key = f"fulltext_{hash(query)}"
            if cache_key in self._cache:
                cache_entry = self._cache[cache_key]
                if time.time() - cache_entry["timestamp"] < self._cache_ttl:
                    return cache_entry["results"]
            
            # Perform full-text search
            search_terms = query.split()
            q_objects = Q()
            
            for term in search_terms:
                q_objects |= Q(content__icontains=term)
            
            chunks = KBChunk.objects.filter(
                document__workspace=self.workspace,
                q_objects
            ).select_related("document")[:5]
            
            results = []
            for chunk in chunks:
                results.append({
                    "text": chunk.content,
                    "document_title": chunk.document.title,
                    "document_type": chunk.document.document_type,
                    "relevance_score": self._calculate_relevance_score(query, chunk.content),
                    "source": "fulltext"
                })
            
            # Sort by relevance
            results.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            # Cache results
            self._cache[cache_key] = {
                "results": results,
                "timestamp": time.time()
            }
            
            return results
            
        except Exception as e:
            logger.warning(f"Full-text search failed: {e}")
            return None
    
    def _search_with_keywords(self, query: str) -> List[Dict[str, Any]]:
        """Fallback keyword-based search"""
        try:
            # Check cache
            cache_key = f"keywords_{hash(query)}"
            if cache_key in self._cache:
                cache_entry = self._cache[cache_key]
                if time.time() - cache_entry["timestamp"] < self._cache_ttl:
                    return cache_entry["results"]
            
            # Simple keyword matching
            search_terms = query.lower().split()
            chunks = KBChunk.objects.filter(
                document__workspace=self.workspace
            ).select_related("document")
            
            results = []
            for chunk in chunks:
                content_lower = chunk.content.lower()
                matches = sum(1 for term in search_terms if term in content_lower)
                
                if matches > 0:
                    relevance_score = matches / len(search_terms)
                    results.append({
                        "text": chunk.content,
                        "document_title": chunk.document.title,
                        "document_type": chunk.document.document_type,
                        "relevance_score": relevance_score,
                        "source": "keywords"
                    })
            
            # Sort by relevance and limit results
            results.sort(key=lambda x: x["relevance_score"], reverse=True)
            results = results[:5]
            
            # Cache results
            self._cache[cache_key] = {
                "results": results,
                "timestamp": time.time()
            }
            
            return results
            
        except Exception as e:
            logger.warning(f"Keyword search failed: {e}")
            return []
    
    def _calculate_relevance_score(self, query: str, content: str) -> float:
        """Calculate relevance score between query and content"""
        try:
            query_terms = set(query.lower().split())
            content_terms = set(content.lower().split())
            
            if not query_terms:
                return 0.0
            
            # Calculate Jaccard similarity
            intersection = len(query_terms & content_terms)
            union = len(query_terms | content_terms)
            
            if union == 0:
                return 0.0
            
            base_score = intersection / union
            
            # Boost score for exact phrase matches
            if query.lower() in content.lower():
                base_score += 0.3
            
            # Boost score for longer content (more comprehensive)
            content_length_factor = min(len(content) / 1000, 0.2)
            base_score += content_length_factor
            
            return min(base_score, 1.0)
            
        except Exception as e:
            logger.warning(f"Relevance score calculation failed: {e}")
            return 0.0
    
    def _format_search_results(self, results: List[Dict[str, Any]], source: str) -> str:
        """Format search results for inclusion in AI response"""
        if not results:
            return ""
        
        formatted_results = f"Relevant information from our knowledge base ({source} search):

"
        
        for i, result in enumerate(results[:3], 1):  # Limit to top 3 results
            formatted_results += f"{i}. {result[document_title]} ({result[document_type]}):
"
            formatted_results += f"   {result[text][:200]}...

"
        
        return formatted_results
    
    def _estimate_processing_time(self, query: str) -> str:
        """Estimate processing time based on query complexity"""
        word_count = len(query.split())
        if word_count > 20:
            return "complex"  # 3-5 seconds
        elif word_count > 10:
            return "moderate"  # 1-3 seconds
        else:
            return "simple"  # < 1 second
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """Get statistics about knowledge base usage"""
        try:
            total_documents = KBDocument.objects.filter(workspace=self.workspace).count()
            total_chunks = KBChunk.objects.filter(document__workspace=self.workspace).count()
            
            # Get document type distribution
            doc_types = KBDocument.objects.filter(
                workspace=self.workspace
            ).values_list("document_type", flat=True).distinct()
            
            type_distribution = {}
            for doc_type in doc_types:
                type_distribution[doc_type] = KBDocument.objects.filter(
                    workspace=self.workspace,
                    document_type=doc_type
                ).count()
            
            return {
                "total_documents": total_documents,
                "total_chunks": total_chunks,
                "type_distribution": type_distribution,
                "cache_size": len(self._cache),
                "cache_hit_rate": "N/A"  # Could implement actual hit rate tracking
            }
            
        except Exception as e:
            logger.error(f"Failed to get search statistics: {str(e)}")
            return {}
    
    def clear_cache(self):
        """Clear the search cache"""
        self._cache.clear()
        logger.info("Knowledge base cache cleared")
    
    def optimize_search_performance(self) -> Dict[str, Any]:
        """Optimize search performance and return recommendations"""
        try:
            recommendations = []
            
            # Check cache size
            if len(self._cache) > 1000:
                recommendations.append("Cache size is large. Consider implementing cache expiration.")
            
            # Check document count
            doc_count = KBDocument.objects.filter(workspace=self.workspace).count()
            if doc_count > 1000:
                recommendations.append("Large number of documents. Consider implementing document indexing.")
            
            # Check chunk size
            chunk_count = KBChunk.objects.filter(document__workspace=self.workspace).count()
            if chunk_count > 10000:
                recommendations.append("Large number of chunks. Consider optimizing chunk size.")
            
            return {
                "recommendations": recommendations,
                "cache_size": len(self._cache),
                "document_count": doc_count,
                "chunk_count": chunk_count
            }
            
        except Exception as e:
            logger.error(f"Performance optimization analysis failed: {str(e)}")
            return {"recommendations": [], "error": str(e)}
