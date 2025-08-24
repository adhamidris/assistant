from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, agent_views

router = DefaultRouter()
router.register(r'workspaces', views.WorkspaceViewSet)
router.register(r'contacts', views.ContactViewSet)
router.register(r'sessions', views.SessionViewSet)
router.register(r'conversations', views.ConversationViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('session/create/', views.CreateSessionView.as_view(), name='create-session'),
    path('session/validate/', views.ValidateSessionView.as_view(), name='validate-session'),
    path('portal-resolve/<path:slug_path>/', views.resolve_portal_slug, name='resolve-portal-slug'),
    path('test-portal/', views.test_portal_resolution, name='test-portal-resolution'),
    path('workspace/<uuid:workspace_id>/portal-status/', views.check_portal_status, name='portal-status'),
    path('workspace/<uuid:workspace_id>/agents/', 
         agent_views.AIAgentViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='workspace-agents-by-id'),
    path('workspace/<uuid:workspace_id>/agents/<uuid:pk>/', 
         agent_views.AIAgentViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), 
         name='workspace-agent-detail-by-id'),
    path('workspace/<uuid:workspace_id>/agents/<uuid:pk>/toggle-active/', 
         agent_views.AIAgentViewSet.as_view({'post': 'toggle_active'}), 
         name='workspace-agent-toggle-active-by-id'),
    path('workspace/<uuid:workspace_id>/agents/<uuid:pk>/set-default/', 
         agent_views.AIAgentViewSet.as_view({'post': 'set_default'}), 
         name='workspace-agent-set-default-by-id'),
    
    # 🆕 ADD: AI Agent Management URLs
    path('workspaces/<slug:workspace_slug>/agents/', 
         agent_views.AIAgentViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='workspace-agents'),
    path('workspaces/<slug:workspace_slug>/agents/active/', 
         agent_views.AIAgentViewSet.as_view({'get': 'active_agent'}), 
         name='workspace-active-agent'),
    path('workspaces/<slug:workspace_slug>/agents/<uuid:pk>/', 
         agent_views.AIAgentViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), 
         name='workspace-agent-detail'),
    
    # Agent Actions
    path('workspaces/<slug:workspace_slug>/agents/<uuid:pk>/generate-prompt/', 
         agent_views.AIAgentViewSet.as_view({'post': 'generate_prompt'}), 
         name='agent-generate-prompt'),
    path('workspaces/<slug:workspace_slug>/agents/<uuid:pk>/portal-url/', 
         agent_views.AIAgentViewSet.as_view({'get': 'portal_url'}), 
         name='agent-portal-url'),
    path('workspaces/<slug:workspace_slug>/agents/<uuid:pk>/toggle-active/', 
         agent_views.AIAgentViewSet.as_view({'post': 'toggle_active'}), 
         name='agent-toggle-active'),
    path('workspaces/<slug:workspace_slug>/agents/<uuid:pk>/set-default/', 
         agent_views.AIAgentViewSet.as_view({'post': 'set_default'}), 
         name='agent-set-default'),
    path('workspaces/<slug:workspace_slug>/agents/<uuid:pk>/performance-metrics/', 
         agent_views.AIAgentViewSet.as_view({'get': 'performance_metrics'}), 
         name='agent-performance-metrics'),
    path('workspaces/<slug:workspace_slug>/agents/<uuid:pk>/assign-schema/', 
         agent_views.AIAgentViewSet.as_view({'post': 'assign_schema'}), 
         name='agent-assign-schema'),
    
    # Business Type Templates
    path('business-templates/', 
         agent_views.BusinessTypeTemplateViewSet.as_view({'get': 'list'}), 
         name='business-templates'),
    path('business-templates/<uuid:pk>/', 
         agent_views.BusinessTypeTemplateViewSet.as_view({'get': 'retrieve'}), 
         name='business-template-detail'),
    path('business-templates/<uuid:pk>/apply-to-workspace/', 
         agent_views.BusinessTypeTemplateViewSet.as_view({'post': 'apply_to_workspace'}), 
         name='business-template-apply'),
]

