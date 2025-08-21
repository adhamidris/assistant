from django.apps import AppConfig


class ContextTrackingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'context_tracking'
    verbose_name = 'Context Tracking'
    
    def ready(self):
        # Import signals
        try:
            import context_tracking.signals
        except ImportError:
            pass
