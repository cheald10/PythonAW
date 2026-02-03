"""
Management command to fetch MLB results for a specific week.

Usage:
    python manage.py fetch_mlb_results <week_id>
    python manage.py fetch_mlb_results 1 --dry-run
"""

from django.core.management.base import BaseCommand, CommandError
from core.models import Week
from core.services.mlb_results_service import MLBResultsService


class Command(BaseCommand):
    help = 'Fetch MLB game results for a week and create WeeklyResult records'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'week_id',
            type=int,
            help='ID of the week to fetch results for'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fetched without saving to database'
        )
    
    def handle(self, *args, **options):
        week_id = options['week_id']
        dry_run = options['dry_run']
        
        # Get the week
        try:
            week = Week.objects.get(id=week_id)
        except Week.DoesNotExist:
            raise CommandError(f'Week {week_id} does not exist')
        
        self.stdout.write(self.style.NOTICE(f'\n{"="*60}'))
        self.stdout.write(self.style.NOTICE(f'Fetching MLB Results'))
        self.stdout.write(self.style.NOTICE(f'{"="*60}'))
        self.stdout.write(f'Week: {week.week_number} ({week.season_year})')
        self.stdout.write(f'Saturday Date: {week.saturday_date}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  DRY RUN MODE - No changes will be saved'))
        
        self.stdout.write('')
        
        # Fetch results
        service = MLBResultsService()
        response = service.fetch_saturday_results(week)
        
        # Display results
        self.stdout.write('')
        self.stdout.write(self.style.NOTICE(f'{"="*60}'))
        self.stdout.write(self.style.NOTICE(f'Results Summary'))
        self.stdout.write(self.style.NOTICE(f'{"="*60}'))
        self.stdout.write(f'Results Created: {response["results_created"]}')
        self.stdout.write(f'Players Processed: {response["players_processed"]}')
        
        if response['errors']:
            self.stdout.write(self.style.WARNING(f'\nErrors: {len(response["errors"])}'))
            for error in response['errors']:
                self.stdout.write(self.style.ERROR(f'  - {error}'))
        else:
            self.stdout.write(self.style.SUCCESS('\n✅ No errors'))
        
        self.stdout.write('')
        
        # Get summary
        summary = service.get_week_summary(week)
        
        self.stdout.write(self.style.NOTICE('Category Breakdown:'))
        for category, count in summary['by_category'].items():
            self.stdout.write(f'  {category}: {count} results')
        
        self.stdout.write(f'\nAchieved: {summary["achieved_count"]}')
        self.stdout.write(f'Missed: {summary["missed_count"]}')
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✅ Results fetch complete!'))