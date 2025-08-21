from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

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
]

