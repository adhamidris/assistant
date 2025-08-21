from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    WorkspaceContextSchemaViewSet, ConversationContextViewSet, 
    BusinessRuleViewSet, ContextAnalyticsView, BulkContextOperationsView
)

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
]
