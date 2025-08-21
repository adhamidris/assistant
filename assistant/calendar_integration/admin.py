from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone

from .models import Appointment, AvailabilitySlot, GoogleCalendarSync


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'contact_name', 'workspace_name', 'start_time', 
        'duration_display', 'status', 'location_type', 'is_synced'
    ]
    list_filter = ['status', 'location_type', 'workspace', 'created_at']
    search_fields = ['title', 'contact__name', 'contact__phone_e164', 'customer_email']
    readonly_fields = ['id', 'google_event_id', 'google_meet_link', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'workspace', 'contact', 'title', 'description', 'status')
        }),
        ('Schedule', {
            'fields': ('start_time', 'end_time', 'location_type', 'location_details')
        }),
        ('Customer Details', {
            'fields': ('customer_email', 'customer_notes')
        }),
        ('Notifications', {
            'fields': ('email_reminder', 'reminder_minutes_before')
        }),
        ('Google Calendar', {
            'fields': ('google_event_id', 'google_meet_link'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def contact_name(self, obj):
        return obj.contact.name or 'Unknown'
    contact_name.short_description = 'Contact'
    
    def workspace_name(self, obj):
        return obj.workspace.name
    workspace_name.short_description = 'Workspace'
    
    def duration_display(self, obj):
        return f"{obj.duration_minutes} min"
    duration_display.short_description = 'Duration'
    
    def is_synced(self, obj):
        if obj.google_event_id:
            return format_html('<span style="color: green;">✓ Synced</span>')
        return format_html('<span style="color: red;">✗ Not synced</span>')
    is_synced.short_description = 'Google Calendar'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('workspace', 'contact')


@admin.register(AvailabilitySlot)
class AvailabilitySlotAdmin(admin.ModelAdmin):
    list_display = [
        'workspace_name', 'weekday_display', 'time_range', 
        'is_available', 'booking_info', 'created_at'
    ]
    list_filter = ['is_available', 'workspace', 'created_at']
    search_fields = ['workspace__name']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'workspace', 'is_available')
        }),
        ('Time Settings', {
            'fields': ('start_time', 'end_time')
        }),
        ('Booking Settings', {
            'fields': ('max_bookings', 'current_bookings', 'is_recurring', 'recurrence_rule')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def workspace_name(self, obj):
        return obj.workspace.name
    workspace_name.short_description = 'Workspace'
    
    def weekday_display(self, obj):
        return obj.start_time.strftime('%A')  # Show day name (Monday, Tuesday, etc.)
    weekday_display.short_description = 'Day'
    
    def time_range(self, obj):
        return f"{obj.start_time} - {obj.end_time}"
    time_range.short_description = 'Time Range'
    
    def booking_info(self, obj):
        return f"{obj.current_bookings}/{obj.max_bookings}"
    booking_info.short_description = 'Bookings'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('workspace')


@admin.register(GoogleCalendarSync)
class GoogleCalendarSyncAdmin(admin.ModelAdmin):
    list_display = [
        'workspace_name', 'sync_status', 'calendar_name', 
        'last_sync_at', 'sync_stats', 'token_status'
    ]
    list_filter = ['sync_status', 'sync_direction', 'is_successful', 'created_at']
    search_fields = ['workspace__name', 'calendar_name', 'google_calendar_id']
    readonly_fields = [
        'id', 'google_calendar_id', 'access_token', 'refresh_token', 
        'token_expires_at', 'last_sync_at', 'events_synced', 
        'appointments_created', 'appointments_updated', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'workspace', 'sync_status', 'sync_direction')
        }),
        ('Google Calendar', {
            'fields': ('google_calendar_id', 'calendar_name', 'calendar_description')
        }),
        ('OAuth Credentials', {
            'fields': ('access_token', 'refresh_token', 'token_expires_at'),
            'classes': ('collapse',)
        }),
        ('Sync Status', {
            'fields': ('last_sync_at', 'is_successful', 'error_message', 'error_count')
        }),
        ('Statistics', {
            'fields': ('events_synced', 'appointments_created', 'appointments_updated')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def workspace_name(self, obj):
        return obj.workspace.name
    workspace_name.short_description = 'Workspace'
    
    def sync_stats(self, obj):
        return f"Events: {obj.events_synced}, Created: {obj.appointments_created}, Updated: {obj.appointments_updated}"
    sync_stats.short_description = 'Sync Statistics'
    
    def token_status(self, obj):
        if obj.is_token_expired:
            return format_html('<span style="color: red;">Expired</span>')
        elif obj.needs_refresh:
            return format_html('<span style="color: orange;">Needs Refresh</span>')
        else:
            return format_html('<span style="color: green;">Valid</span>')
    token_status.short_description = 'Token Status'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('workspace')
    
    actions = ['trigger_sync', 'refresh_tokens']
    
    def trigger_sync(self, request, queryset):
        """Trigger manual sync for selected workspaces"""
        from .tasks import sync_calendar_events
        
        count = 0
        for sync_config in queryset:
            if sync_config.sync_status == 'active':
                sync_calendar_events.delay(str(sync_config.workspace.id))
                count += 1
        
        self.message_user(request, f"Triggered sync for {count} workspace(s).")
    trigger_sync.short_description = "Trigger calendar sync"
    
    def refresh_tokens(self, request, queryset):
        """Refresh tokens for selected workspaces"""
        from .tasks import refresh_google_calendar_token
        
        count = 0
        for sync_config in queryset:
            if sync_config.needs_refresh:
                refresh_google_calendar_token.delay(str(sync_config.workspace.id))
                count += 1
        
        self.message_user(request, f"Triggered token refresh for {count} workspace(s).")
    refresh_tokens.short_description = "Refresh Google Calendar tokens"
