"""
URL patterns for notification management
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'notifications', views.NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
    path('preferences/', views.notification_preferences, name='notification-preferences'),
    path('test/', views.test_notification, name='test-notification'),
    path('templates/', views.email_templates, name='email-templates'),
]
