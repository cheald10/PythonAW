"""
Simple command to mark weeks past deadline as completed
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Week

class Command(BaseCommand):
    help = 'Mark weeks past deadline as completed'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be completed without actually doing it',
        )

    def handle(self, *args, **options):
        now = timezone.now()
        dry_run = options.get('dry_run', False)
        
        # Find weeks past deadline that aren't completed
        weeks_to_complete = Week.objects.filter(
            deadline_utc__lt=now,
            is_completed=False
        )
        
        if not weeks_to_complete.exists():
            self.stdout.write(
                self.style.WARNING('✓ No weeks need to be completed')
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Found {weeks_to_complete.count()} week(s) past deadline:'
            )
        )
        
        for week in weeks_to_complete:
            self.stdout.write(
                f'  Week {week.week_number} ({week.season_year}) - '
                f'Deadline: {week.deadline_utc}'
            )
            
            if not dry_run:
                week.is_completed = True
                week.is_active = False
                week.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  ✅ Marked as complete'
                    )
                )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    '\n⚠️  DRY RUN - No changes made'
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✅ Successfully completed {weeks_to_complete.count()} week(s)'
                )
            )