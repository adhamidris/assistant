from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import views_ai

router = DefaultRouter()
router.register(r'messages', views.MessageViewSet)
router.register(r'drafts', views.MessageDraftViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('upload-audio/', views.UploadAudioView.as_view(), name='upload-audio'),
    path('upload-file/', views.UploadFileView.as_view(), name='upload-file'),
    path('generate-response/', views.GenerateResponseView.as_view(), name='generate-response'),
    path('approve-draft/', views.ApproveDraftView.as_view(), name='approve-draft'),
    
    # AI Analysis endpoints
    path('conversations/<uuid:conversation_id>/analyze-sentiment/', 
         views_ai.analyze_conversation_sentiment_view, name='analyze-sentiment'),
    path('conversations/<uuid:conversation_id>/generate-summary/', 
         views_ai.generate_summary_view, name='generate-summary'),
    path('conversations/<uuid:conversation_id>/extract-entities/', 
         views_ai.extract_entities_view, name='extract-entities'),
    path('conversations/<uuid:conversation_id>/generate-insights/', 
         views_ai.generate_insights_view, name='generate-insights'),
    path('conversations/<uuid:conversation_id>/insights/', 
         views_ai.get_conversation_insights, name='get-insights'),
    path('analyze-text/', views_ai.analyze_message_text, name='analyze-text'),
    path('analytics/', views_ai.get_workspace_analytics, name='workspace-analytics'),
    path('session-messages/', views.session_messages, name='session-messages'),
]
