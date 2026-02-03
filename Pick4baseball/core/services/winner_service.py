"""
Winner Service
Determines weekly winners and calculates payouts.

This service is responsible for:
1. Finding users with perfect picks (4/4)
2. Calculating payout amounts
3. Handling rollover when no winners
4. Updating user standings
"""

from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Count

from core.models import (
    Week, Pick, WeeklyPrizePool, UserStanding, Team, User
)


class WinnerService:
    """Service for determining winners and calculating payouts"""

    def __init__(self):
        self.winners = []
        self.errors = []

    def determine_weekly_winners(self, week_id):
        """
        Find all users with perfect picks (4/4) and calculate payouts.

        Args:
            week_id: ID of Week to determine winners for

        Returns:
            dict with winner information
        """
        try:
            week = Week.objects.get(id=week_id)
        except Week.DoesNotExist:
            return {
                'success': False,
                'error': f'Week {week_id} not found'
            }

        print(f"\n{'='*60}")
        print(f"Determining Winners for Week {week.week_number} ({week.season_year})")
        print(f"{'='*60}\n")

        # Get all perfect pickers
        perfect_pickers = self.get_perfect_pickers(week)

        if not perfect_pickers:
            print("❌ No perfect pickers this week - rolling over prize pool")
            return self.handle_rollover(week)

        print(f"🎉 Found {len(perfect_pickers)} perfect picker(s)!\n")

        # Calculate and distribute payouts
        payout_results = self.calculate_payouts(week, perfect_pickers)

        return {
            'success': True,
            'week_id': week_id,
            'num_winners': len(perfect_pickers),
            'winners': self.winners,
            'payout_per_winner': payout_results['payout_per_winner'],
            'total_paid_out': payout_results['total_paid_out'],
            'errors': self.errors
        }

    def get_perfect_pickers(self, week):
        """
        Find all users with 4/4 correct picks in a week.

        Args:
            week: Week object

        Returns:
            list of dicts with user and team info
        """
        # Get all picks for the week, grouped by user and team
        user_scores = Pick.objects.filter(
            week=week
        ).values(
            'user', 'user__username', 'team', 'team__name'
        ).annotate(
            total_points=Sum('points_earned'),
            total_picks=Count('id')
        )

        # Filter for perfect scores (4 points, 4 picks)
        perfect_pickers = []

        for score in user_scores:
            if score['total_points'] == 4 and score['total_picks'] == 4:
                perfect_pickers.append({
                    'user_id': score['user'],
                    'username': score['user__username'],
                    'team_id': score['team'],
                    'team_name': score['team__name'],
                    'points': score['total_points']
                })

                print(f"✅ Perfect Pick: {score['user__username']} ({score['team__name']})")

        return perfect_pickers

    @transaction.atomic
    def calculate_payouts(self, week, perfect_pickers):
        """
        Calculate and record payout amounts for winners.

        Args:
            week: Week object
            perfect_pickers: list of winner dicts

        Returns:
            dict with payout information
        """
        # Get all prize pools for this week
        prize_pools = WeeklyPrizePool.objects.filter(week=week)

        if not prize_pools.exists():
            self.errors.append("No prize pools found for this week")
            return {
                'payout_per_winner': Decimal('0.00'),
                'total_paid_out': Decimal('0.00')
            }

        # Calculate total available for weekly payout across all teams
        total_weekly_pool = prize_pools.aggregate(
            total=Sum('weekly_pool_amount')
        )['total'] or Decimal('0.00')

        # Add any rollover from previous weeks
        total_rollover = prize_pools.aggregate(
            total=Sum('rollover_from_previous')
        )['total'] or Decimal('0.00')

        total_available = total_weekly_pool + total_rollover

        print(f"\nPrize Pool Summary:")
        print(f"  Weekly Pool: ${total_weekly_pool:.2f}")
        print(f"  Rollover: ${total_rollover:.2f}")
        print(f"  Total Available: ${total_available:.2f}")
        print(f"  Number of Winners: {len(perfect_pickers)}")

        # Calculate payout per winner
        if len(perfect_pickers) > 0:
            payout_per_winner = total_available / Decimal(len(perfect_pickers))
        else:
            payout_per_winner = Decimal('0.00')

        print(f"  Payout per Winner: ${payout_per_winner:.2f}\n")

        # Update prize pools
        for prize_pool in prize_pools:
            # Calculate how many winners from this team
            team_winners = [p for p in perfect_pickers if p['team_id'] == prize_pool.team_id]

            prize_pool.num_perfect_picks = len(team_winners)
            prize_pool.payout_per_winner = payout_per_winner
            prize_pool.is_scored = True
            prize_pool.scored_at = timezone.now()

            # Reset rollover (it's been distributed)
            prize_pool.rollover_from_previous = Decimal('0.00')

            prize_pool.save()

        # Create winner records (for future payout processing)
        for picker in perfect_pickers:
            self.winners.append({
                'user_id': picker['user_id'],
                'username': picker['username'],
                'team_id': picker['team_id'],
                'team_name': picker['team_name'],
                'amount': payout_per_winner,
                'week': week.week_number
            })

            # Update user standings
            self.update_user_standings(
                user_id=picker['user_id'],
                team_id=picker['team_id'],
                week=week,
                points_earned=4,
                winnings=payout_per_winner
            )

            print(f"💰 {picker['username']} ({picker['team_name']}): ${payout_per_winner:.2f}")

        total_paid_out = payout_per_winner * Decimal(len(perfect_pickers))

        return {
            'payout_per_winner': payout_per_winner,
            'total_paid_out': total_paid_out
        }

    @transaction.atomic
    def handle_rollover(self, week):
        """
        Handle the case when there are no winners - rollover to next week.

        Args:
            week: Week object

        Returns:
            dict with rollover information
        """
        prize_pools = WeeklyPrizePool.objects.filter(week=week)

        total_rolled_over = Decimal('0.00')

        for prize_pool in prize_pools:
            # Add weekly pool to rollover
            rollover_amount = prize_pool.weekly_pool_amount + prize_pool.rollover_from_previous

            # Find next week's prize pool
            try:
                next_week = Week.objects.filter(
                    season_year=week.season_year,
                    week_number=week.week_number + 1
                ).first()

                if next_week:
                    next_prize_pool, created = WeeklyPrizePool.objects.get_or_create(
                        team=prize_pool.team,
                        week=next_week,
                        defaults={
                            'rollover_from_previous': rollover_amount
                        }
                    )

                    if not created:
                        next_prize_pool.rollover_from_previous += rollover_amount
                        next_prize_pool.save()

                    print(f"📦 Rolled over ${rollover_amount:.2f} from {prize_pool.team.name} to Week {next_week.week_number}")
                else:
                    # No next week - add to season pot
                    prize_pool.season_pot_contribution += rollover_amount
                    print(f"📦 Added ${rollover_amount:.2f} from {prize_pool.team.name} to season pot (no more weeks)")

            except Exception as e:
                self.errors.append(f"Error rolling over for {prize_pool.team.name}: {str(e)}")
                continue

            # Mark this week as scored with no winners
            prize_pool.num_perfect_picks = 0
            prize_pool.payout_per_winner = Decimal('0.00')
            prize_pool.is_scored = True
            prize_pool.scored_at = timezone.now()
            prize_pool.rollover_from_previous = Decimal('0.00')  # Moved to next week
            prize_pool.save()

            total_rolled_over += rollover_amount

        return {
            'success': True,
            'week_id': week.id,
            'num_winners': 0,
            'winners': [],
            'rollover_amount': total_rolled_over,
            'message': f'No winners - rolled over ${total_rolled_over:.2f} to next week'
        }

    @transaction.atomic
    def update_user_standings(self, user_id, team_id, week, points_earned, winnings):
        """
        Update user's standing statistics.

        Args:
            user_id: ID of User
            team_id: ID of Team
            week: Week object
            points_earned: Points earned this week
            winnings: Amount won this week
        """
        try:
            user = User.objects.get(id=user_id)
            team = Team.objects.get(id=team_id)
        except (User.DoesNotExist, Team.DoesNotExist):
            self.errors.append(f"User {user_id} or Team {team_id} not found")
            return

        # Get or create standing
        standing, created = UserStanding.objects.get_or_create(
            user=user,
            team=team,
            season_year=week.season_year,
            defaults={
                'total_points': 0,
                'total_picks_made': 0,
                'total_picks_hit': 0,
                'weeks_participated': 0,
                'perfect_weeks': 0,
                'total_winnings': Decimal('0.00')
            }
        )

        # Update stats
        standing.total_points += points_earned
        standing.total_picks_made += 4  # Always 4 picks per week
        standing.total_picks_hit += points_earned  # Points = hits
        standing.weeks_participated += 1

        if points_earned == 4:
            standing.perfect_weeks += 1

        standing.total_winnings += winnings

        # Update accuracy
        standing.update_accuracy()

        # Update streak
        if points_earned > 0:
            standing.current_streak += 1
            if standing.current_streak > standing.longest_streak:
                standing.longest_streak = standing.current_streak
        else:
            standing.current_streak = 0

        # Update highest weekly score
        if points_earned > standing.highest_weekly_score:
            standing.highest_weekly_score = points_earned

        standing.save()

        print(f"📊 Updated standings for {user.username}: {standing.total_points} pts, ${standing.total_winnings:.2f} won")

    def get_week_winners_summary(self, week_id):
        """
        Get summary of winners for a week.

        Args:
            week_id: ID of Week

        Returns:
            dict with winner summary
        """
        try:
            week = Week.objects.get(id=week_id)
        except Week.DoesNotExist:
            return {
                'success': False,
                'error': f'Week {week_id} not found'
            }

        prize_pools = WeeklyPrizePool.objects.filter(week=week)

        total_winners = prize_pools.aggregate(
            total=Sum('num_perfect_picks')
        )['total'] or 0

        payout_per_winner = prize_pools.first().payout_per_winner if prize_pools.exists() else Decimal('0.00')

        return {
            'success': True,
            'week': week.week_number,
            'season': week.season_year,
            'num_winners': total_winners,
            'payout_per_winner': payout_per_winner,
            'is_scored': prize_pools.filter(is_scored=True).exists()
        }

    def get_leaderboard(self, team_id, season_year):
        """
        Get leaderboard for a team's season.

        Args:
            team_id: ID of Team
            season_year: Season year

        Returns:
            QuerySet of UserStanding ordered by points
        """
        return UserStanding.objects.filter(
            team_id=team_id,
            season_year=season_year
        ).order_by('-total_points', '-total_winnings').select_related('user')
