import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assistant.settings')

app = Celery('assistant')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Configure task routes
app.conf.task_routes = {
    'messaging.tasks.process_audio_message': {'queue': 'audio_processing'},
    'messaging.tasks.generate_ai_response': {'queue': 'ai_processing'},
    'knowledge_base.tasks.process_document': {'queue': 'document_processing'},
    'calendar_integration.tasks.sync_google_calendar': {'queue': 'calendar_sync'},
}

# Configure task priorities
app.conf.task_default_priority = 5
app.conf.worker_prefetch_multiplier = 1
app.conf.task_acks_late = True

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
