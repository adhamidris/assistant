from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'documents', views.KBDocumentViewSet)
router.register(r'chunks', views.KBChunkViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('upload/', views.UploadDocumentView.as_view(), name='upload-document'),
    path('search/', views.SearchKnowledgeBaseView.as_view(), name='search-kb'),
    path('process-document/<uuid:document_id>/', views.ProcessDocumentView.as_view(), name='process-document'),
]

