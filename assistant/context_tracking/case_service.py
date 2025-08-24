import logging
import json
from typing import Dict, Any, List, Optional
from django.db import transaction, models
from django.utils import timezone
from .models import ContextCase, CaseUpdate, CaseTypeConfiguration
from .case_analyzer import CaseAnalyzer
from .duplicate_detector import DuplicateDetector

logger = logging.getLogger(__name__)

class CaseManagementService:
    """Main service for case management operations"""
    
    def __init__(self, workspace):
        self.workspace = workspace
        self.analyzer = None  # Will be set when AI service is available
        self.duplicate_detector = DuplicateDetector(workspace)
        
    def set_ai_service(self, ai_service):
        """Set the AI service for case analysis"""
        self.analyzer = CaseAnalyzer(self.workspace, ai_service)
        
    def process_message_for_cases(self, message: str, conversation_context: List[Dict], agent) -> Dict[str, Any]:
        """Main entry point for case processing"""
        try:
            if not self.analyzer:
                return {"action": "error", "message": "AI service not available"}
            
            # Analyze message for case actions
            analysis = self.analyzer.analyze_message_for_cases(message, conversation_context, agent)
            
            if analysis["action"] == "create":
                return self._create_new_case(analysis["case_data"], message, conversation_context)
            elif analysis["action"] == "update":
                return self._update_existing_cases(analysis["matching_cases"], analysis["case_data"], message)
            
            return {"action": "none", "case_id": None, "message": "No case action required"}
            
        except Exception as e:
            logger.error(f"Case processing failed: {str(e)}")
            return {"action": "error", "message": f"Processing error: {str(e)}"}
    
    def _create_new_case(self, case_data: Dict[str, Any], message: str, conversation_context: List[Dict]) -> Dict[str, Any]:
        """Create a new context case with duplicate prevention"""
        try:
            with transaction.atomic():
                # Check for duplicates
                duplicate_check = self.duplicate_detector.detect_duplicates(case_data, case_data["case_type"])
                
                if duplicate_check["is_duplicate"]:
                    if duplicate_check["action"] == "merge_or_update":
                        # Update existing case instead of creating new one
                        existing_case = ContextCase.objects.get(id=duplicate_check["similar_cases"][0]["id"])
                        return self._update_case(existing_case, case_data, message, "duplicate_merge")
                    else:
                        # Flag for manual review
                        return {
                            "action": "duplicate_detected",
                            "similar_cases": duplicate_check["similar_cases"],
                            "message": "Similar cases found - manual review required"
                        }
                
                # Create new case
                case = ContextCase.objects.create(
                    workspace=self.workspace,
                    case_type=case_data["case_type"],
                    extracted_data=case_data,
                    business_parameters=self._get_business_parameters(case_data["case_type"]),
                    matching_criteria=case_data,
                    related_messages=[message],
                    hash_signature=self.duplicate_detector._generate_case_hash(case_data),
                    confidence_score=case_data.get("confidence", 0.8),
                    source_channel=conversation_context[0].get("channel", "website") if conversation_context else "website"
                )
                
                # Add message to case
                case.add_message({
                    "timestamp": timezone.now().isoformat(),
                    "content": message,
                    "sender": "client",
                    "message_type": "text"
                })
                
                logger.info(f"Created new case: {case.case_id} for {case_data[case_type]}")
                
                return {
                    "action": "case_created",
                    "case_id": case.case_id,
                    "case_data": case.extracted_data,
                    "message": f"New {case_data[case_type]} case created: {case.case_id}"
                }
                
        except Exception as e:
            logger.error(f"Case creation failed: {str(e)}")
            return {"action": "error", "message": f"Creation failed: {str(e)}"}
    
    def _update_existing_cases(self, matching_cases: List[Dict], updates: Dict[str, Any], message: str) -> Dict[str, Any]:
        """Update existing cases with new information"""
        try:
            updated_cases = []
            
            for match in matching_cases:
                case = match["case"]
                update_result = self._update_case(case, updates, message, "ai_analysis")
                if update_result["success"]:
                    updated_cases.append(case.case_id)
            
            if updated_cases:
                return {
                    "action": "cases_updated",
                    "updated_case_ids": updated_cases,
                    "message": f"Updated {len(updated_cases)} existing cases"
                }
            else:
                return {"action": "update_failed", "message": "Failed to update any cases"}
                
        except Exception as e:
            logger.error(f"Case update failed: {str(e)}")
            return {"action": "error", "message": f"Update failed: {str(e)}"}
    
    def _update_case(self, case: ContextCase, new_data: Dict[str, Any], message: str, update_source: str) -> Dict[str, Any]:
        """Update a specific case with new data"""
        try:
            with transaction.atomic():
                # Store previous data
                previous_data = case.extracted_data.copy()
                
                # Merge new data
                for key, value in new_data.items():
                    if key not in case.extracted_data:
                        case.extracted_data[key] = value
                    elif isinstance(value, dict) and isinstance(case.extracted_data.get(key), dict):
                        # Merge dictionaries
                        case.extracted_data[key].update(value)
                    elif isinstance(value, list) and isinstance(case.extracted_data.get(key), list):
                        # Merge lists
                        case.extracted_data[key].extend(value)
                    else:
                        case.extracted_data[key] = value
                
                # Update case
                case.save()
                
                # Add message to case
                case.add_message({
                    "timestamp": timezone.now().isoformat(),
                    "content": message,
                    "sender": "client",
                    "message_type": "text"
                })
                
                # Create update record
                CaseUpdate.objects.create(
                    case=case,
                    update_type="data_update",
                    previous_data=previous_data,
                    new_data=new_data,
                    update_source=update_source,
                    confidence_score=case.confidence_score,
                    ai_reasoning="Case updated with new information from message"
                )
                
                logger.info(f"Updated case: {case.case_id}")
                
                return {
                    "success": True,
                    "case_id": case.case_id,
                    "updated_data": new_data
                }
                
        except Exception as e:
            logger.error(f"Case update failed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_cases_summary(self, status_filter: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get summary of cases for display in frontend"""
        try:
            query = ContextCase.objects.filter(workspace=self.workspace)
            
            if status_filter:
                query = query.filter(status=status_filter)
                
            cases = query.order_by("-updated_at")[:limit]
            
            return [{
                "case_id": case.case_id,
                "case_type": case.case_type,
                "status": case.status,
                "priority": case.priority,
                "extracted_data": case.get_extracted_data_summary(),
                "last_updated": case.updated_at.isoformat(),
                "confidence_score": case.confidence_score,
                "message_count": len(case.related_messages),
                "source_channel": case.source_channel,
                "assigned_agent": case.assigned_agent.name if case.assigned_agent else None
            } for case in cases]
            
        except Exception as e:
            logger.error(f"Failed to get cases summary: {str(e)}")
            return []
    
    def get_case_details(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific case"""
        try:
            case = ContextCase.objects.get(
                workspace=self.workspace,
                case_id=case_id
            )
            
            # Get case updates
            updates = CaseUpdate.objects.filter(case=case).order_by("-timestamp")
            
            return {
                "case_id": case.case_id,
                "case_type": case.case_type,
                "status": case.status,
                "priority": case.priority,
                "extracted_data": case.extracted_data,
                "business_parameters": case.business_parameters,
                "matching_criteria": case.matching_criteria,
                "confidence_score": case.confidence_score,
                "related_messages": case.related_messages,
                "source_channel": case.source_channel,
                "assigned_agent": case.assigned_agent.name if case.assigned_agent else None,
                "created_at": case.created_at.isoformat(),
                "updated_at": case.updated_at.isoformat(),
                "created_by_ai": case.created_by_ai,
                "manual_override": case.manual_override,
                "updates": [{
                    "update_type": update.update_type,
                    "previous_data": update.previous_data,
                    "new_data": update.new_data,
                    "update_source": update.update_source,
                    "confidence_score": update.confidence_score,
                    "ai_reasoning": update.ai_reasoning,
                    "timestamp": update.timestamp.isoformat()
                } for update in updates]
            }
            
        except ContextCase.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Failed to get case details: {str(e)}")
            return None
    
    def update_case_status(self, case_id: str, new_status: str, reason: str = "", manual: bool = False) -> Dict[str, Any]:
        """Update case status with audit trail"""
        try:
            case = ContextCase.objects.get(
                workspace=self.workspace,
                case_id=case_id
            )
            
            case.update_status(new_status, reason, manual)
            
            return {
                "success": True,
                "case_id": case.case_id,
                "new_status": new_status,
                "message": f"Case status updated to {new_status}"
            }
            
        except ContextCase.DoesNotExist:
            return {"success": False, "error": "Case not found"}
        except Exception as e:
            logger.error(f"Failed to update case status: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _get_business_parameters(self, case_type: str) -> Dict[str, Any]:
        """Get business parameters for a case type"""
        try:
            config = CaseTypeConfiguration.objects.get(
                workspace=self.workspace,
                case_type=case_type
            )
            return config.data_schema
        except CaseTypeConfiguration.DoesNotExist:
            return {}
    
    def get_case_statistics(self) -> Dict[str, Any]:
        """Get statistics about cases in the workspace"""
        try:
            total_cases = ContextCase.objects.filter(workspace=self.workspace).count()
            
            status_counts = {}
            for status, _ in ContextCase.STATUS_CHOICES:
                status_counts[status] = ContextCase.objects.filter(
                    workspace=self.workspace,
                    status=status
                ).count()
            
            type_counts = {}
            case_types = ContextCase.objects.filter(
                workspace=self.workspace
            ).values_list("case_type", flat=True).distinct()
            
            for case_type in case_types:
                type_counts[case_type] = ContextCase.objects.filter(
                    workspace=self.workspace,
                    case_type=case_type
                ).count()
            
            return {
                "total_cases": total_cases,
                "status_distribution": status_counts,
                "type_distribution": type_counts,
                "average_confidence": ContextCase.objects.filter(
                    workspace=self.workspace
                ).aggregate(avg_confidence=models.Avg("confidence_score"))["avg_confidence"] or 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get case statistics: {str(e)}")
            return {}
    
    def search_cases(self, query: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search cases based on query and filters"""
        try:
            queryset = ContextCase.objects.filter(workspace=self.workspace)
            
            # Apply filters
            if filters:
                if filters.get("status"):
                    queryset = queryset.filter(status=filters["status"])
                if filters.get("case_type"):
                    queryset = queryset.filter(case_type=filters["case_type"])
                if filters.get("priority"):
                    queryset = queryset.filter(priority=filters["priority"])
                if filters.get("date_from"):
                    queryset = queryset.filter(created_at__gte=filters["date_from"])
                if filters.get("date_to"):
                    queryset = queryset.filter(created_at__lte=filters["date_to"])
            
            # Text search in extracted data
            if query:
                queryset = queryset.filter(
                    extracted_data__icontains=query
                )
            
            cases = queryset.order_by("-updated_at")[:100]  # Limit results
            
            return [{
                "case_id": case.case_id,
                "case_type": case.case_type,
                "status": case.status,
                "priority": case.priority,
                "extracted_data": case.get_extracted_data_summary(),
                "last_updated": case.updated_at.isoformat(),
                "confidence_score": case.confidence_score
            } for case in cases]
            
        except Exception as e:
            logger.error(f"Case search failed: {str(e)}")
            return []
