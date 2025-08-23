from django.core.management.base import BaseCommand
from core.models import Workspace

class Command(BaseCommand):
    help = 'Enable AI auto-reply mode for all workspaces'

    def handle(self, *args, **options):
        workspaces = Workspace.objects.all()
        enabled_count = 0
        
        for workspace in workspaces:
            if not workspace.auto_reply_mode:
                workspace.auto_reply_mode = True
                workspace.save()
                enabled_count += 1
                self.stdout.write(f'✅ Enabled auto-reply for: {workspace.name}')
            else:
                self.stdout.write(f'☑️ Auto-reply already enabled for: {workspace.name}')
        
        self.stdout.write(
            self.style.SUCCESS(f'\n🎉 Successfully enabled auto-reply for {enabled_count} workspaces!')
        )
