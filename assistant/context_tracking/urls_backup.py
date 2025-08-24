from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    WorkspaceContextSchemaViewSet, ConversationContextViewSet, 
    BusinessRuleViewSet, ContextAnalyticsView, BulkContextOperationsView
)
from . import advanced_views, field_suggestion_views, api_views

app_name = 'context_tracking'

urlpatterns = [
    # Schema management
    path('workspaces/<uuid:workspace_pk>/schemas/', 
         WorkspaceContextSchemaViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='workspace-schemas-list'),
    path('workspaces/<uuid:workspace_pk>/schemas/<uuid:pk>/', 
         WorkspaceContextSchemaViewSet.as_view({
             'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'
         }), 
         name='workspace-schemas-detail'),
    path('workspaces/<uuid:workspace_pk>/schemas/<uuid:pk>/duplicate/', 
         WorkspaceContextSchemaViewSet.as_view({'post': 'duplicate'}), 
         name='workspace-schemas-duplicate'),
    path('workspaces/<uuid:workspace_pk>/schemas/<uuid:pk>/test/', 
         WorkspaceContextSchemaViewSet.as_view({'post': 'test_configuration'}), 
         name='workspace-schemas-test'),
    path('workspaces/<uuid:workspace_pk>/schemas/statistics/', 
         WorkspaceContextSchemaViewSet.as_view({'get': 'statistics'}), 
         name='workspace-schemas-statistics'),
    
    # Business rules
    path('workspaces/<uuid:workspace_pk>/rules/', 
         BusinessRuleViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='workspace-rules-list'),
    path('workspaces/<uuid:workspace_pk>/rules/<uuid:pk>/', 
         BusinessRuleViewSet.as_view({
             'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'
         }), 
         name='workspace-rules-detail'),
    path('workspaces/<uuid:workspace_pk>/rules/<uuid:pk>/test/', 
         BusinessRuleViewSet.as_view({'post': 'test_rule'}), 
         name='workspace-rules-test'),
    path('workspaces/<uuid:workspace_pk>/rules/<uuid:pk>/toggle/', 
         BusinessRuleViewSet.as_view({'post': 'toggle_active'}), 
         name='workspace-rules-toggle'),
    path('workspaces/<uuid:workspace_pk>/rules/statistics/', 
         BusinessRuleViewSet.as_view({'get': 'execution_statistics'}), 
         name='workspace-rules-statistics'),
    
    # Conversation contexts
    path('conversations/<uuid:conversation_pk>/contexts/', 
         ConversationContextViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='conversation-contexts-list'),
    path('conversations/<uuid:conversation_pk>/contexts/<uuid:pk>/', 
         ConversationContextViewSet.as_view({
             'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'
         }), 
         name='conversation-contexts-detail'),
    path('conversations/<uuid:conversation_pk>/contexts/<uuid:pk>/extract/', 
         ConversationContextViewSet.as_view({'post': 'extract_context'}), 
         name='conversation-contexts-extract'),
    path('conversations/<uuid:conversation_pk>/contexts/<uuid:pk>/update-fields/', 
         ConversationContextViewSet.as_view({'put': 'update_fields'}), 
         name='conversation-contexts-update-fields'),
    path('conversations/<uuid:conversation_pk>/contexts/<uuid:pk>/change-status/', 
         ConversationContextViewSet.as_view({'post': 'change_status'}), 
         name='conversation-contexts-change-status'),
    path('conversations/<uuid:conversation_pk>/contexts/<uuid:pk>/history/', 
         ConversationContextViewSet.as_view({'get': 'history'}), 
         name='conversation-contexts-history'),
    
    # Context by conversation (simplified access)
    path('conversations/<uuid:conversation_id>/context/', 
         ConversationContextViewSet.as_view({'get': 'retrieve', 'put': 'update'}), 
         name='conversation-context'),
    
    # Workspace-level context operations
    path('workspaces/<uuid:workspace_id>/contexts/', 
         ConversationContextViewSet.as_view({'get': 'list'}), 
         name='workspace-contexts-list'),
    path('workspaces/<uuid:workspace_id>/contexts/bulk/', 
         BulkContextOperationsView.as_view(), 
         name='workspace-contexts-bulk'),
    
    # Analytics
    path('workspaces/<uuid:workspace_id>/analytics/', 
         ContextAnalyticsView.as_view(), 
         name='workspace-analytics'),
    
    # Advanced Business Rules
    path('workspaces/<uuid:workspace_id>/advanced-rules/analytics/', 
         advanced_views.AdvancedBusinessRuleViewSet.as_view({'get': 'analytics_dashboard'}), 
         name='advanced-rules-analytics'),
    path('workspaces/<uuid:workspace_id>/advanced-rules/templates/', 
         advanced_views.AdvancedBusinessRuleViewSet.as_view({'get': 'rule_templates'}), 
         name='advanced-rules-templates'),
    path('workspaces/<uuid:workspace_id>/advanced-rules/create-from-template/', 
         advanced_views.AdvancedBusinessRuleViewSet.as_view({'post': 'create_from_template'}), 
         name='advanced-rules-create-from-template'),
    path('workspaces/<uuid:workspace_id>/advanced-rules/insights/', 
         advanced_views.AdvancedBusinessRuleViewSet.as_view({'get': 'rule_insights'}), 
         name='advanced-rules-insights'),
    
    # Workflow Management
    path('workspaces/<uuid:workspace_id>/workflows/active/', 
         advanced_views.WorkflowManagementViewSet.as_view({'get': 'active_workflows'}), 
         name='workflows-active'),
    path('workspaces/<uuid:workspace_id>/workflows/resume/', 
         advanced_views.WorkflowManagementViewSet.as_view({'post': 'resume_workflow'}), 
         name='workflows-resume'),
    path('workspaces/<uuid:workspace_id>/workflows/reset/', 
         advanced_views.WorkflowManagementViewSet.as_view({'post': 'reset_workflow'}), 
         name='workflows-reset'),
    
    # Rule Testing and Execution
    path('rules/<uuid:pk>/test/', 
         advanced_views.AdvancedBusinessRuleViewSet.as_view({'post': 'test_rule'}), 
         name='rule-test'),
    path('rules/<uuid:pk>/execute-workflow/', 
         advanced_views.AdvancedBusinessRuleViewSet.as_view({'post': 'execute_workflow'}), 
         name='rule-execute-workflow'),
    
    # Field Suggestions and Intelligent Discovery
    path('field-suggestions/', 
         field_suggestion_views.FieldSuggestionViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='field-suggestions-list'),
    path('field-suggestions/<uuid:pk>/', 
         field_suggestion_views.FieldSuggestionViewSet.as_view({
             'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'
         }), 
         name='field-suggestions-detail'),
    path('field-suggestions/generate/', 
         field_suggestion_views.FieldSuggestionViewSet.as_view({'post': 'generate_suggestions'}), 
         name='field-suggestions-generate'),
    path('field-suggestions/<uuid:pk>/approve/', 
         field_suggestion_views.FieldSuggestionViewSet.as_view({'post': 'approve_suggestion'}), 
         name='field-suggestions-approve'),
    path('field-suggestions/<uuid:pk>/reject/', 
         field_suggestion_views.FieldSuggestionViewSet.as_view({'post': 'reject_suggestion'}), 
         name='field-suggestions-reject'),
    path('field-suggestions/analytics/', 
         field_suggestion_views.FieldSuggestionViewSet.as_view({'get': 'get_analytics'}), 
         name='field-suggestions-analytics'),
    path('field-suggestions/pending/', 
         field_suggestion_views.FieldSuggestionViewSet.as_view({'get': 'get_pending_suggestions'}), 
         name='field-suggestions-pending'),
    path('field-suggestions/reviewed/', 
         field_suggestion_views.FieldSuggestionViewSet.as_view({'get': 'get_reviewed_suggestions'}), 
         name='field-suggestions-reviewed'),
    
    # Intelligent Discovery
    path('intelligent-discovery/analyze-conversations/', 
         field_suggestion_views.IntelligentDiscoveryViewSet.as_view({'post': 'analyze_conversations'}), 
         name='intelligent-discovery-analyze'),
    path('intelligent-discovery/discover-fields/', 
         field_suggestion_views.IntelligentDiscoveryViewSet.as_view({'post': 'discover_fields'}), 
         name='intelligent-discovery-discover'),
]
    # Case Management
    path("workspaces/<uuid:workspace_pk>/cases/", 
         api_views.ContextCaseViewSet.as_view({"get": "list", "post": "create"}), 
         name="workspace-cases-list"),
    path("workspaces/<uuid:workspace_pk>/cases/<uuid:pk>/", 
         api_views.ContextCaseViewSet.as_view({
             "get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"
         }), 
         name="workspace-cases-detail"),
    path("workspaces/<uuid:workspace_pk>/cases/summary/", 
         api_views.ContextCaseViewSet.as_view({"get": "summary"}), 
         name="workspace-cases-summary"),
    path("workspaces/<uuid:workspace_pk>/cases/search/", 
         api_views.ContextCaseViewSet.as_view({"get": "search"}), 
         name="workspace-cases-search"),
    path("workspaces/<uuid:workspace_pk>/cases/bulk-update/", 
         api_views.ContextCaseViewSet.as_view({"post": "bulk_update"}), 
         name="workspace-cases-bulk-update"),
    path("workspaces/<uuid:workspace_pk>/cases/<uuid:pk>/close/", 
         api_views.ContextCaseViewSet.as_view({"post": "close_case"}), 
         name="workspace-cases-close"),
    path("workspaces/<uuid:workspace_pk>/cases/<uuid:pk>/update-status/", 
         api_views.ContextCaseViewSet.as_view({"post": "update_status"}), 
         name="workspace-cases-update-status"),
    path("workspaces/<uuid:workspace_pk>/cases/<uuid:pk>/updates/", 
         api_views.ContextCaseViewSet.as_view({"get": "updates"}), 
         name="workspace-cases-updates"),
    
    # Case Type Configuration
    path("workspaces/<uuid:workspace_pk>/case-types/", 
         api_views.CaseTypeConfigurationViewSet.as_view({"get": "list", "post": "create"}), 
         name="workspace-case-types-list"),
    path("workspaces/<uuid:workspace_pk>/case-types/<uuid:pk>/", 
         api_views.CaseTypeConfigurationViewSet.as_view({
             "get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"
         }), 
         name="workspace-case-types-detail"),
    path("workspaces/<uuid:workspace_pk>/case-types/<uuid:pk>/test/", 
         api_views.CaseTypeConfigurationViewSet.as_view({"post": "test_configuration"}), 
         name="workspace-case-types-test"),
    
    # Case Matching Rules
    path("workspaces/<uuid:workspace_pk>/case-matching-rules/", 
         api_views.CaseMatchingRuleViewSet.as_view({"get": "list", "post": "create"}), 
         name="workspace-case-matching-rules-list"),
    path("workspaces/<uuid:workspace_pk>/case-matching-rules/<uuid:pk>/", 
         api_views.CaseMatchingRuleViewSet.as_view({
             "get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"
         }), 
         name="workspace-case-matching-rules-detail"),
    path("workspaces/<uuid:workspace_pk>/case-matching-rules/<uuid:pk>/test/", 
         api_views.CaseMatchingRuleViewSet.as_view({"post": "test_matching"}), 
         name="workspace-case-matching-rules-test"),
]
