"""
Scoring Service
Scores user picks against actual MLB results.

This service is responsible for:
1. Scoring individual picks
2. Scoring all picks for a user
3. Scoring all picks for a week
4. Updating pick status and points
"""

from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from core.models import Week, Pick, WeeklyResult, PickCategory


class ScoringService:
    """Service for scoring user picks against MLB results"""
    
    def __init__(self):
        self.picks_scored = 0
        self.hits = 0
        self.misses = 0
        self.errors = []
    
    def score_week(self, week_id, fetch_results=False):
        """
        Score all picks for a week.
        
        Args:
            week_id: ID of Week to score
            fetch_results: If True, fetch MLB results first
            
        Returns:
            dict with scoring results
        """
        try:
            week = Week.objects.get(id=week_id)
        except Week.DoesNotExist:
            return {
                'success': False,
                'error': f'Week {week_id} not found'
            }
        
        print(f"\n{'='*60}")
        print(f"Scoring Week {week.week_number} ({week.season_year})")
        print(f"{'='*60}\n")
        
        # Fetch results if requested
        if fetch_results:
            from core.services.mlb_results_service import MLBResultsService
            results_service = MLBResultsService()
            fetch_response = results_service.fetch_saturday_results(week)
            print(f"Fetched {fetch_response['results_created']} results")
            
            if fetch_response['errors']:
                print("Errors during fetch:")
                for error in fetch_response['errors']:
                    print(f"  - {error}")
        
        # Get all picks for this week
        picks = Pick.objects.filter(week=week).select_related('user', 'player', 'category')
        
        if not picks.exists():
            return {
                'success': False,
                'error': 'No picks found for this week'
            }
        
        print(f"Found {picks.count()} picks to score\n")
        
        # Score each pick
        for pick in picks:
            self.score_single_pick(pick)
        
        # Build response
        return {
            'success': True,
            'week_id': week_id,
            'picks_scored': self.picks_scored,
            'hits': self.hits,
            'misses': self.misses,
            'errors': self.errors,
            'accuracy': f"{(self.hits / self.picks_scored * 100):.1f}%" if self.picks_scored > 0 else "0%"
        }
    
    def score_user_picks(self, user, week):
        """
        Score all 4 picks for a specific user in a week.
        
        Args:
            user: User object
            week: Week object
            
        Returns:
            dict with user's score
        """
        picks = Pick.objects.filter(
            user=user,
            week=week
        ).select_related('player', 'category')
        
        if picks.count() != 4:
            return {
                'success': False,
                'error': f'User has {picks.count()} picks, expected 4'
            }
        
        user_hits = 0
        user_misses = 0
        
        for pick in picks:
            result = self.score_single_pick(pick)
            if result['result_status'] == 'hit':
                user_hits += 1
            else:
                user_misses += 1
        
        return {
            'success': True,
            'user': user.username,
            'total_points': user_hits,
            'hits': user_hits,
            'misses': user_misses,
            'is_perfect': (user_hits == 4)
        }
    
    @transaction.atomic
    def score_single_pick(self, pick):
        """
        Score a single pick against WeeklyResult.
        
        Args:
            pick: Pick object
            
        Returns:
            dict with scoring result
        """
        # Look up the WeeklyResult for this pick
        try:
            result = WeeklyResult.objects.get(
                week=pick.week,
                player=pick.player,
                category=pick.category
            )
        except WeeklyResult.DoesNotExist:
            # No result found - mark as miss
            pick.result_status = 'miss'
            pick.points_earned = 0
            pick.scored_at = timezone.now()
            pick.notes = "No result data available (player may not have played)"
            pick.save()
            
            self.picks_scored += 1
            self.misses += 1
            
            print(f"❌ {pick.user.username} - {pick.category.code} - {pick.player.full_name}: MISS (no data)")
            
            return {
                'pick_id': pick.id,
                'result_status': 'miss',
                'points_earned': 0,
                'reason': 'No result data'
            }
        
        # Verify the pick based on category
        is_hit = self._verify_pick(pick, result)
        
        # Update pick
        pick.result_status = 'hit' if is_hit else 'miss'
        pick.points_earned = 1 if is_hit else 0
        pick.scored_at = timezone.now()
        pick.notes = f"Actual: {result.stat_value} | Achieved: {result.achieved}"
        pick.save()
        
        # Update counters
        self.picks_scored += 1
        if is_hit:
            self.hits += 1
        else:
            self.misses += 1
        
        # Log result
        status_icon = "✅" if is_hit else "❌"
        print(f"{status_icon} {pick.user.username} - {pick.category.code} - {pick.player.full_name}: {pick.result_status.upper()} (Value: {result.stat_value})")
        
        return {
            'pick_id': pick.id,
            'result_status': pick.result_status,
            'points_earned': pick.points_earned,
            'stat_value': result.stat_value
        }
    
    def _verify_pick(self, pick, result):
        """
        Verify if a pick is a hit or miss based on category rules.
        
        Args:
            pick: Pick object
            result: WeeklyResult object
            
        Returns:
            bool: True if hit, False if miss
        """
        category_code = pick.category.code
        
        if category_code == '2H':
            return self._verify_2h(result)
        elif category_code == 'HR':
            return self._verify_hr(result)
        elif category_code == 'SWP':
            return self._verify_swp(result)
        elif category_code == 'S':
            return self._verify_save(result)
        else:
            self.errors.append(f"Unknown category: {category_code}")
            return False
    
    def _verify_2h(self, result):
        """
        Verify 2H pick: Player must get 2+ hits in Saturday games.
        
        Args:
            result: WeeklyResult object
            
        Returns:
            bool: True if player got 2+ hits
        """
        return result.achieved and result.stat_value >= 2
    
    def _verify_hr(self, result):
        """
        Verify HR pick: Player must hit 1+ home run in Saturday games.
        
        Args:
            result: WeeklyResult object
            
        Returns:
            bool: True if player hit 1+ HR
        """
        return result.achieved and result.stat_value >= 1
    
    def _verify_swp(self, result):
        """
        Verify SWP pick: Pitcher must be starting pitcher AND get the win.
        
        Args:
            result: WeeklyResult object
            
        Returns:
            bool: True if starting pitcher got win
        """
        return result.achieved
    
    def _verify_save(self, result):
        """
        Verify S pick: Pitcher must record 1+ save in Saturday games.
        
        Args:
            result: WeeklyResult object
            
        Returns:
            bool: True if pitcher got save
        """
        return result.achieved and result.stat_value >= 1
    
    def get_scoring_summary(self, week):
        """
        Get summary of scoring for a week.
        
        Args:
            week: Week object
            
        Returns:
            dict with summary stats
        """
        picks = Pick.objects.filter(week=week)
        
        total = picks.count()
        hits = picks.filter(result_status='hit').count()
        misses = picks.filter(result_status='miss').count()
        pending = picks.filter(result_status='pending').count()
        
        return {
            'total_picks': total,
            'hits': hits,
            'misses': misses,
            'pending': pending,
            'accuracy': f"{(hits / total * 100):.1f}%" if total > 0 else "0%",
            'by_category': {
                '2H': self._get_category_stats(week, '2H'),
                'HR': self._get_category_stats(week, 'HR'),
                'SWP': self._get_category_stats(week, 'SWP'),
                'S': self._get_category_stats(week, 'S'),
            }
        }
    
    def _get_category_stats(self, week, category_code):
        """Get stats for a specific category"""
        picks = Pick.objects.filter(week=week, category__code=category_code)
        
        total = picks.count()
        hits = picks.filter(result_status='hit').count()
        
        return {
            'total': total,
            'hits': hits,
            'accuracy': f"{(hits / total * 100):.1f}%" if total > 0 else "0%"
        }
    
    def rescore_pick(self, pick_id):
        """
        Re-score a single pick (useful for corrections).
        
        Args:
            pick_id: ID of Pick to re-score
            
        Returns:
            dict with result
        """
        try:
            pick = Pick.objects.get(id=pick_id)
            return self.score_single_pick(pick)
        except Pick.DoesNotExist:
            return {
                'success': False,
                'error': f'Pick {pick_id} not found'
            }
    
    def reset_week_scoring(self, week_id):
        """
        Reset all scoring for a week (marks all picks as pending).
        Useful before re-scoring.
        
        Args:
            week_id: ID of Week to reset
            
        Returns:
            int: Number of picks reset
        """
        picks = Pick.objects.filter(week_id=week_id)
        count = picks.update(
            result_status='pending',
            points_earned=0,
            scored_at=None,
            notes=''
        )
        
        print(f"Reset {count} picks for week {week_id}")
        return count
