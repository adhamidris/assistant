import hashlib
import logging
from typing import Dict, Any, List, Optional
from django.db.models import Q
from .models import ContextCase, CaseMatchingRule

logger = logging.getLogger(__name__)

class DuplicateDetector:
    """Intelligent duplicate detection and prevention system"""
    
    def __init__(self, workspace):
        self.workspace = workspace
        
    def detect_duplicates(self, case_data: Dict[str, Any], case_type: str) -> Dict[str, Any]:
        """
        Detect potential duplicates for new case data
        
        Returns:
            {
                "is_duplicate": bool,
                "similar_cases": List[Dict],
                "action": "merge_or_update" | "flag_duplicate" | "allow_creation",
                "confidence": float
            }
        """
        try:
            # Generate hash signature for the case data
            case_hash = self._generate_case_hash(case_data)
            
            # Check for exact hash matches
            exact_matches = ContextCase.objects.filter(
                workspace=self.workspace,
                hash_signature=case_hash,
                case_type=case_type
            )
            
            if exact_matches.exists():
                return {
                    "is_duplicate": True,
                    "similar_cases": [{"id": case.id, "case_id": case.case_id, "status": case.status} for case in exact_matches],
                    "action": "merge_or_update",
                    "confidence": 1.0
                }
            
            # Check for similar cases using matching rules
            similar_cases = self._find_similar_cases(case_data, case_type)
            
            if similar_cases:
                # Determine action based on similarity and business rules
                action = self._determine_duplicate_action(similar_cases, case_data)
                
                return {
                    "is_duplicate": True,
                    "similar_cases": similar_cases,
                    "action": action,
                    "confidence": max(case["similarity"] for case in similar_cases)
                }
            
            return {
                "is_duplicate": False,
                "similar_cases": [],
                "action": "allow_creation",
                "confidence": 1.0
            }
            
        except Exception as e:
            logger.error(f"Duplicate detection failed: {str(e)}")
            return {
                "is_duplicate": False,
                "similar_cases": [],
                "action": "allow_creation",
                "confidence": 0.0
            }
    
    def _generate_case_hash(self, case_data: Dict[str, Any]) -> str:
        """Generate hash signature for case data"""
        # Create normalized string representation
        normalized_data = {}
        
        for key, value in sorted(case_data.items()):
            if isinstance(value, str):
                normalized_data[key] = value.lower().strip()
            elif isinstance(value, (int, float, bool)):
                normalized_data[key] = str(value)
            elif isinstance(value, dict):
                normalized_data[key] = self._generate_case_hash(value)
            elif isinstance(value, list):
                normalized_data[key] = sorted([str(item) for item in value])
        
        # Create hash from normalized data
        hash_string = json.dumps(normalized_data, sort_keys=True)
        return hashlib.sha256(hash_string.encode()).hexdigest()
    
    def _find_similar_cases(self, case_data: Dict[str, Any], case_type: str) -> List[Dict]:
        """Find cases with high similarity scores"""
        try:
            # Get matching rules for this case type
            matching_rules = CaseMatchingRule.objects.filter(
                workspace=self.workspace,
                case_type=case_type,
                is_active=True
            ).order_by("-priority")
            
            if not matching_rules:
                return []
            
            # Get existing cases of this type
            existing_cases = ContextCase.objects.filter(
                workspace=self.workspace,
                case_type=case_type,
                status__in=["open", "in_progress", "pending"]
            )
            
            similar_cases = []
            
            for case in existing_cases:
                for rule in matching_rules:
                    similarity_score = rule.get_matching_score(case_data, case)
                    
                    if similarity_score >= rule.similarity_threshold:
                        similar_cases.append({
                            "id": case.id,
                            "case_id": case.case_id,
                            "status": case.status,
                            "similarity": similarity_score,
                            "rule": rule.rule_name
                        })
                        break  # Use highest priority rule only
            
            # Sort by similarity score
            similar_cases.sort(key=lambda x: x["similarity"], reverse=True)
            return similar_cases[:5]  # Return top 5 matches
            
        except Exception as e:
            logger.error(f"Error finding similar cases: {str(e)}")
            return []
    
    def _determine_duplicate_action(self, similar_cases: List[Dict], case_data: Dict[str, Any]) -> str:
        """Determine what action to take for duplicate cases"""
        try:
            # Get the highest similarity case
            best_match = similar_cases[0]
            similarity_score = best_match["similarity"]
            
            # If very high similarity, merge or update
            if similarity_score >= 0.9:
                return "merge_or_update"
            
            # If high similarity, flag for review
            elif similarity_score >= 0.7:
                return "flag_duplicate"
            
            # If moderate similarity, allow creation but flag
            else:
                return "allow_creation"
                
        except Exception as e:
            logger.error(f"Error determining duplicate action: {str(e)}")
            return "allow_creation"
    
    def merge_cases(self, target_case: ContextCase, source_data: Dict[str, Any]) -> Dict[str, Any]:
        """Merge source data into target case"""
        try:
            with transaction.atomic():
                # Update target case with new data
                for key, value in source_data.items():
                    if key not in target_case.extracted_data:
                        target_case.extracted_data[key] = value
                    elif isinstance(value, dict) and isinstance(target_case.extracted_data.get(key), dict):
                        # Merge dictionaries
                        target_case.extracted_data[key].update(value)
                    elif isinstance(value, list) and isinstance(target_case.extracted_data.get(key), list):
                        # Merge lists
                        target_case.extracted_data[key].extend(value)
                
                # Update case
                target_case.save()
                
                # Create update record
                from .case_models import CaseUpdate
                CaseUpdate.objects.create(
                    case=target_case,
                    update_type="case_merge",
                    previous_data={},
                    new_data=source_data,
                    update_source="duplicate_detector",
                    confidence_score=0.9,
                    ai_reasoning="Case merged due to duplicate detection"
                )
                
                return {
                    "success": True,
                    "merged_case_id": target_case.case_id,
                    "merged_data": source_data
                }
                
        except Exception as e:
            logger.error(f"Case merge failed: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_duplicate_prevention_stats(self) -> Dict[str, Any]:
        """Get statistics about duplicate prevention"""
        try:
            total_cases = ContextCase.objects.filter(workspace=self.workspace).count()
            duplicate_cases = ContextCase.objects.filter(
                workspace=self.workspace,
                extracted_data__has_key="duplicate_flag"
            ).count()
            
            return {
                "total_cases": total_cases,
                "duplicate_cases": duplicate_cases,
                "duplicate_rate": duplicate_cases / total_cases if total_cases > 0 else 0,
                "prevention_effectiveness": "high" if duplicate_cases / total_cases < 0.1 else "medium"
            }
            
        except Exception as e:
            logger.error(f"Error getting duplicate prevention stats: {str(e)}")
            return {}

