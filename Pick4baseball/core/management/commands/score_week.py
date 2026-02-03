# core/management/commands/score_week.py
"""
Score Week Management Command
Fetches MLB results, scores picks, and determines winners

Usage:
    python manage.py score_week <week_id>
    python manage.py score_week 1 --fetch-results
    python manage.py score_week 1 --determine-winners
    python manage.py score_week 1 --fetch-results --determine-winners (full flow)
    python manage.py score_week 1 --dry-run
"""

from django.core.management.base import BaseCommand, CommandError
from core.models import Week
from core.services.scoring_service import ScoringService
from core.services.winner_service import WinnerService
from core.services.mlb_results_service import MLBResultsService
from core.services.standings_service import update_standings_for_week  # Import once at top


class Command(BaseCommand):
    help = 'Score a week: fetch MLB results, score picks, and determine winners'

    def add_arguments(self, parser):
        parser.add_argument('week_id', type=int, help='Week ID to score')
        parser.add_argument(
            '--fetch-results',
            action='store_true',
            help='Fetch MLB results before scoring',
        )
        parser.add_argument(
            '--determine-winners',
            action='store_true',
            help='Determine winners after scoring',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate without making changes',
        )

    def handle(self, *args, **options):
        week_id = options['week_id']
        fetch_results = options.get('fetch_results', False)
        determine_winners = options.get('determine_winners', False)
        dry_run = options.get('dry_run', False)

        # Verify week exists
        try:
            week = Week.objects.get(id=week_id)
        except Week.DoesNotExist:
            raise CommandError(f'Week with ID {week_id} does not exist')

        self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
        self.stdout.write(self.style.SUCCESS(f'SCORING WEEK {week.week_number} - {week.saturday_date}'))
        self.stdout.write(self.style.SUCCESS(f'{"="*60}\n'))

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be saved\n'))

        # Step 1: Fetch results if requested
        if fetch_results:
            self.stdout.write(self.style.NOTICE(f'\n{"="*60}'))
            self.stdout.write(self.style.NOTICE('STEP 1: Fetching MLB Results'))
            self.stdout.write(self.style.NOTICE(f'{"="*60}\n'))

            mlb_service = MLBResultsService()

            if dry_run:
                self.stdout.write(self.style.WARNING('Skipping actual fetch (dry run)'))
            else:
                try:
                    player_stats = mlb_service.fetch_saturday_results(week.saturday_date)
                    results_saved = mlb_service.save_results_to_database(
                        player_stats, 
                        week,
                        week.prize_pools.first().team if week.prize_pools.exists() else None
                    )
                    self.stdout.write(self.style.SUCCESS(f'\n✅ Fetched and saved {results_saved} results'))
                except Exception as e:
                    raise CommandError(f'Failed to fetch results: {str(e)}')

        # Step 2: Score picks
        self.stdout.write(self.style.NOTICE(f'\n{"="*60}'))
        self.stdout.write(self.style.NOTICE('STEP 2: Scoring Picks'))
        self.stdout.write(self.style.NOTICE(f'{"="*60}\n'))

        scoring_service = ScoringService()

        if dry_run:
            self.stdout.write(self.style.WARNING('Skipping actual scoring (dry run)'))
            scoring_response = {
                'success': True,
                'picks_scored': 0,
                'hits': 0,
                'misses': 0,
                'accuracy': '0%',
                'errors': []
            }
        else:
            scoring_response = scoring_service.score_week(week_id, fetch_results=False)

        if not scoring_response['success']:
            raise CommandError(f'Scoring failed: {scoring_response.get("error")}')

        self.stdout.write(f'\nPicks Scored: {scoring_response["picks_scored"]}')
        self.stdout.write(self.style.SUCCESS(f'Hits: {scoring_response["hits"]}'))
        self.stdout.write(self.style.ERROR(f'Misses: {scoring_response["misses"]}'))
        self.stdout.write(f'Accuracy: {scoring_response["accuracy"]}')

        if scoring_response.get('errors'):
            self.stdout.write(self.style.WARNING(f'\nErrors: {len(scoring_response["errors"])}'))
            for error in scoring_response['errors']:
                self.stdout.write(self.style.ERROR(f'  - {error}'))

        # Step 3: Determine winners if requested
        if determine_winners:
            self.stdout.write(self.style.NOTICE(f'\n{"="*60}'))
            self.stdout.write(self.style.NOTICE('STEP 3: Determining Winners'))
            self.stdout.write(self.style.NOTICE(f'{"="*60}\n'))

            winner_service = WinnerService()

            if dry_run:
                self.stdout.write(self.style.WARNING('Skipping winner determination (dry run)'))
            else:
                winner_response = winner_service.determine_weekly_winners(week_id)

                if not winner_response['success']:
                    raise CommandError(f'Winner determination failed: {winner_response.get("error")}')

                self.stdout.write(f'\nWinners Found: {winner_response["num_winners"]}')

                if winner_response['num_winners'] > 0:
                    self.stdout.write(f'Payout per Winner: ${winner_response["payout_per_winner"]:.2f}')
                    self.stdout.write(f'Total Paid Out: ${winner_response["total_paid_out"]:.2f}')

                    self.stdout.write(self.style.SUCCESS('\n🎉 Winners:'))
                    for winner in winner_response['winners']:
                        self.stdout.write(
                            f'  💰 {winner["username"]} ({winner["team_name"]}): ${winner["amount"]:.2f}'
                        )
                else:
                    self.stdout.write(self.style.WARNING('No winners - prize pool rolled over'))
                    if 'rollover_amount' in winner_response:
                        self.stdout.write(f'Rollover Amount: ${winner_response["rollover_amount"]:.2f}')

                if winner_response.get('errors'):
                    self.stdout.write(self.style.WARNING(f'\nErrors: {len(winner_response["errors"])}'))
                    for error in winner_response['errors']:
                        self.stdout.write(self.style.ERROR(f'  - {error}'))

                # Step 4: Update standings (FIXED - no duplicate import)
                self.stdout.write(self.style.NOTICE(f'\n{"="*60}'))
                self.stdout.write(self.style.NOTICE('STEP 4: Updating Standings'))
                self.stdout.write(self.style.NOTICE(f'{"="*60}\n'))

                try:
                    results = update_standings_for_week(week)  # Use the import from line 18
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ Standings updated: {results['users_updated']} users, "
                            f"{results['teams_updated']} teams"
                        )
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠️  Standings update failed: {str(e)}"
                        )
                    )

        # Final summary
        self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
        self.stdout.write(self.style.SUCCESS('SCORING COMPLETE'))
        self.stdout.write(self.style.SUCCESS(f'{"="*60}\n'))

        if not dry_run:
            # Mark week as completed
            week.is_completed = True
            week.save()
            self.stdout.write(self.style.SUCCESS(f'✅ Week {week.week_number} marked as completed'))
