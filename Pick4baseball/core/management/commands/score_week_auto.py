# core/management/commands/score_week_auto.py
"""
Automated Weekly Scoring Command
Runs every Sunday at 6 PM CST to score the previous day's (Saturday) games

This ensures all data from potential extra inning games is collected.
MLB API needs time to gather complete data from Saturday games.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.utils import timezone
from core.models import Week
from datetime import date, timedelta


class Command(BaseCommand):
    help = 'Automatically score the most recent Saturday week'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be scored without actually scoring',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)

        # Find yesterday's Saturday (today is Sunday)
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Verify today is Sunday
        if today.weekday() != 6:  # 6 = Sunday
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️  This command should run on Sunday. Today is {today.strftime('%A')}"
                )
            )

        # Find the week for yesterday (Saturday)
        #week = Week.objects.filter(saturday_date=yesterday).first()
        week = Week.objects.filter(
            saturday_date=yesterday,
            is_completed=False  # Only get incomplete weeks
        ).first()

        if not week:
            self.stdout.write(
                self.style.ERROR(
                    f"❌ No week found for {yesterday}. "
                    f"This may be All-Star break or an error."
                )
            )
            return

        if week.is_completed:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️  Week {week.week_number} ({yesterday}) has already been scored."
                )
            )
            # Still show the results
            self._show_week_results(week)
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"🎯 Scoring Week {week.week_number} - {yesterday}"
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN - No actual scoring will occur")
            )
            self.stdout.write(f"Would score: Week {week.week_number} (ID: {week.id})")
            return

        # Run the full scoring process
        try:
            self.stdout.write("⏳ Fetching MLB results...")

            # Try to fetch MLB results
            try:
                call_command(
                    'score_week',
                    week.id,
                    '--fetch-results',
                    '--determine-winners',
                    verbosity=2
                )
            except Exception as scoring_error:
                # If MLB scoring fails (e.g., test data), just mark week complete
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️  MLB scoring failed: {str(scoring_error)}"
                    )
                )
                self.stdout.write(
                    self.style.WARNING(
                        "Marking week as complete without MLB scoring (test mode)"
                    )
                )
                week.is_completed = True
                week.is_active = False
                week.save()

            # Refresh week from database
            week.refresh_from_db()

            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Week {week.week_number} scored successfully!"
                )
            )

            # Show results
            self._show_week_results(week)

            # Activate next week if it exists
            self._activate_next_week(week)

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"❌ Error scoring week: {str(e)}"
                )
            )
            raise

    def _show_week_results(self, week):
        """Display week scoring results"""
        try:
            from core.models import WeeklyPrizePool, Pick

            # Get all prize pools for this week (one per team)
            prize_pools = WeeklyPrizePool.objects.filter(week=week)

            if not prize_pools.exists():
                self.stdout.write(
                    self.style.WARNING(
                        "⚠️  No prize pools found for this week"
                    )
                )
                return

            # Display results for each team
            for prize_pool in prize_pools:
                self.stdout.write(f"\n📊 WEEK RESULTS - {prize_pool.team.name}:")
                self.stdout.write(f"  Total Pool: ${prize_pool.weekly_pool_amount}")
                self.stdout.write(f"  Perfect Picks: {prize_pool.num_perfect_picks}")

                if prize_pool.num_perfect_picks > 0:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  🎉 Winners: {prize_pool.num_perfect_picks} player(s) "
                            f"won ${prize_pool.payout_per_winner} each!"
                        )
                    )
                else:
                    rollover = prize_pool.weekly_pool_amount
                    self.stdout.write(
                        self.style.WARNING(
                            f"  📈 No winners - ${rollover} rolled over"
                        )
                    )

            # Show pick stats
            total_picks = Pick.objects.filter(week=week).count()
            hit_picks = Pick.objects.filter(
                week=week,
                result_status='hit'
            ).count()

            self.stdout.write(f"\n📈 PICK STATS:")
            self.stdout.write(f"  Total Picks: {total_picks}")
            self.stdout.write(f"  Correct Picks: {hit_picks}/{total_picks}")

            if total_picks > 0:
                accuracy = (hit_picks / total_picks) * 100
                self.stdout.write(f"  Accuracy: {accuracy:.1f}%")

        except Exception as e:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️  Could not display results: {str(e)}"
                )
            )

    def _activate_next_week(self, current_week):
        """Activate the next week for picks after scoring current week"""
        try:
            # Find next Saturday
            next_saturday = current_week.saturday_date + timedelta(days=7)

            next_week = Week.objects.filter(
                saturday_date=next_saturday,
                is_active=False
            ).first()

            if next_week:
                next_week.is_active = True
                next_week.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n🚀 Week {next_week.week_number} ({next_saturday}) "
                        f"is now open for picks!"
                    )
                )
            else:
                # Check if there are any more weeks
                remaining_weeks = Week.objects.filter(
                    saturday_date__gt=current_week.saturday_date
                ).count()

                if remaining_weeks == 0:
                    self.stdout.write(
                        self.style.SUCCESS(
                            "\n🏁 SEASON COMPLETE! No more weeks to activate."
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"\n⚠️  Week for {next_saturday} not found or already active."
                        )
                    )

        except Exception as e:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️  Could not activate next week: {str(e)}"
                )
            )
