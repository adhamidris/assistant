from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from .models import ContextCase, CaseUpdate, CaseTypeConfiguration, CaseMatchingRule
from .case_service import CaseManagementService
from core.models import Workspace

class ContextCaseViewSet(viewsets.ModelViewSet):
    """API viewset for context case management"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        workspace_id = self.kwargs.get("workspace_pk")
        queryset = ContextCase.objects.filter(workspace_id=workspace_id)
        
        # Filter by status if provided
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            
        # Filter by case type if provided
        case_type = self.request.query_params.get("case_type")
        if case_type:
            queryset = queryset.filter(case_type=case_type)
            
        # Filter by priority if provided
        priority = self.request.query_params.get("priority")
        if priority:
            queryset = queryset.filter(priority=priority)
            
        return queryset.order_by("-updated_at")
    
    @action(detail=False, methods=["get"])
    def summary(self, request, workspace_pk=None):
        """Get summary statistics for cases"""
        try:
            case_service = CaseManagementService(get_object_or_404(Workspace, pk=workspace_pk))
            summary = case_service.get_case_statistics()
            return Response(summary)
        except Exception as e:
            return Response(
                {"error": f"Failed to get summary: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=["post"])
    def close_case(self, request, pk=None, workspace_pk=None):
        """Manually close a case"""
        try:
            case = self.get_object()
            reason = request.data.get("reason", "Manually closed")
            
            case.update_status("closed", reason, manual=True)
            
            return Response({
                "message": "Case closed successfully",
                "case_id": case.case_id,
                "new_status": "closed"
            })
        except Exception as e:
            return Response(
                {"error": f"Failed to close case: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=["post"])
    def update_status(self, request, pk=None, workspace_pk=None):
        """Update case status"""
        try:
            case = self.get_object()
            new_status = request.data.get("status")
            reason = request.data.get("reason", "")
            
            if not new_status:
                return Response(
                    {"error": "Status is required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            case.update_status(new_status, reason, manual=True)
            
            return Response({
                "message": "Case status updated successfully",
                "case_id": case.case_id,
                "new_status": new_status
            })
        except Exception as e:
            return Response(
                {"error": f"Failed to update status: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=["get"])
    def updates(self, request, pk=None, workspace_pk=None):
        """Get update history for a case"""
        try:
            case = self.get_object()
            updates = CaseUpdate.objects.filter(case=case).order_by("-timestamp")
            
            update_data = []
            for update in updates:
                update_data.append({
                    "update_type": update.update_type,
                    "previous_data": update.previous_data,
                    "new_data": update.new_data,
                    "update_source": update.update_source,
                    "confidence_score": update.confidence_score,
                    "ai_reasoning": update.ai_reasoning,
                    "timestamp": update.timestamp.isoformat(),
                    "notes": update.notes
                })
            
            return Response({"updates": update_data})
        except Exception as e:
            return Response(
                {"error": f"Failed to get updates: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=["post"])
    def bulk_update(self, request, workspace_pk=None):
        """Bulk update multiple cases"""
        try:
            case_ids = request.data.get("case_ids", [])
            updates = request.data.get("updates", {})
            
            if not case_ids:
                return Response(
                    {"error": "Case IDs are required"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            updated_count = 0
            failed_updates = []
            
            with transaction.atomic():
                for case_id in case_ids:
                    try:
                        case = ContextCase.objects.get(
                            id=case_id,
                            workspace_id=workspace_pk
                        )
                        
                        # Update case fields
                        for field, value in updates.items():
                            if hasattr(case, field):
                                setattr(case, field, value)
                        
                        case.save()
                        updated_count += 1
                        
                    except ContextCase.DoesNotExist:
                        failed_updates.append({"case_id": case_id, "error": "Case not found"})
                    except Exception as e:
                        failed_updates.append({"case_id": case_id, "error": str(e)})
            
            return Response({
                "message": f"Successfully updated {updated_count} cases",
                "updated_count": updated_count,
                "failed_updates": failed_updates
            })
            
        except Exception as e:
            return Response(
                {"error": f"Bulk update failed: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=["get"])
    def search(self, request, workspace_pk=None):
        """Search cases based on query and filters"""
        try:
            query = request.query_params.get("q", "")
            filters = {
                "status": request.query_params.get("status"),
                "case_type": request.query_params.get("case_type"),
                "priority": request.query_params.get("priority"),
                "date_from": request.query_params.get("date_from"),
                "date_to": request.query_params.get("date_to")
            }
            
            # Remove None values
            filters = {k: v for k, v in filters.items() if v is not None}
            
            case_service = CaseManagementService(get_object_or_404(Workspace, pk=workspace_pk))
            results = case_service.search_cases(query, filters)
            
            return Response({"results": results, "query": query, "filters": filters})
            
        except Exception as e:
            return Response(
                {"error": f"Search failed: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CaseTypeConfigurationViewSet(viewsets.ModelViewSet):
    """API viewset for case type configuration"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        workspace_id = self.kwargs.get("workspace_pk")
        return CaseTypeConfiguration.objects.filter(workspace_id=workspace_id, is_active=True)
    
    @action(detail=True, methods=["post"])
    def test_configuration(self, request, pk=None, workspace_pk=None):
        """Test case type configuration with sample data"""
        try:
            config = self.get_object()
            sample_data = request.data.get("sample_data", {})
            
            # Validate sample data against configuration
            validation_result = config.validate_data(sample_data)
            
            return Response({
                "validation_result": validation_result,
                "configuration": {
                    "case_type": config.case_type,
                    "required_fields": config.required_fields,
                    "data_schema": config.data_schema
                }
            })
            
        except Exception as e:
            return Response(
                {"error": f"Configuration test failed: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CaseMatchingRuleViewSet(viewsets.ModelViewSet):
    """API viewset for case matching rules"""
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        workspace_id = self.kwargs.get("workspace_pk")
        return CaseMatchingRule.objects.filter(workspace_id=workspace_id, is_active=True)
    
    @action(detail=True, methods=["post"])
    def test_matching(self, request, pk=None, workspace_pk=None):
        """Test matching rule with sample data"""
        try:
            rule = self.get_object()
            sample_data = request.data.get("sample_data", {})
            
            # Get existing cases to test against
            existing_cases = ContextCase.objects.filter(
                workspace_id=workspace_pk,
                case_type=rule.case_type
            )[:5]
            
            test_results = []
            for case in existing_cases:
                score = rule.get_matching_score(sample_data, case)
                test_results.append({
                    "case_id": case.case_id,
                    "similarity_score": score,
                    "would_match": score >= rule.similarity_threshold
                })
            
            return Response({
                "rule_name": rule.rule_name,
                "matching_fields": rule.matching_fields,
                "similarity_threshold": rule.similarity_threshold,
                "test_results": test_results
            })
            
        except Exception as e:
            return Response(
                {"error": f"Matching test failed: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
