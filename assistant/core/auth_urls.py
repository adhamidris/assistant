"""
Authentication URLs for APP users
"""
from django.urls import path
from . import auth_views

urlpatterns = [
    path('register/', auth_views.register_user, name='register'),
    path('login/', auth_views.login_user, name='login'),
    path('logout/', auth_views.logout_user, name='logout'),
    path('profile/', auth_views.get_user_profile, name='profile'),
    path('portal-link/', auth_views.get_portal_link, name='portal-link'),
    path('qr-code/<uuid:workspace_id>/', auth_views.generate_qr_code, name='qr-code'),
]
