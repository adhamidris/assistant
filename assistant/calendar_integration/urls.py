from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'appointments', views.AppointmentViewSet, basename='appointment')

urlpatterns = [
    path('', include(router.urls)),
    
    # Appointment booking
    path('available-slots/', views.get_available_slots, name='available-slots'),
    path('book-appointment/', views.book_appointment, name='book-appointment'),
    
    # Google Calendar integration
    path('google/auth/', views.google_calendar_auth, name='google-calendar-auth'),
    path('google/callback/', views.google_calendar_callback, name='google-calendar-callback'),
    path('google/status/', views.calendar_sync_status, name='calendar-sync-status'),
]
