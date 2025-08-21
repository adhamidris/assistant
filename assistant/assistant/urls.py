"""
URL configuration for AI Personal Business Assistant project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include([
        path('auth/', include('core.auth_urls')),
        path('core/', include('core.urls')),
        path('messaging/', include('messaging.urls')),
        path('knowledge-base/', include('knowledge_base.urls')),
        path('calendar/', include('calendar_integration.urls')),
        path('notifications/', include('notifications.urls')),
    ])),
]
