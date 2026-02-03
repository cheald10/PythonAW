# core/services/standings_service.py
"""
Standings Service
Updates UserStanding and TeamStanding after weekly scoring

Created: January 30, 2026
"""

from django.db.models import Sum, Count, Q, Avg
from decimal import Decimal
from core.models import (
    UserStanding, TeamStanding, Pick, Week, 
    WeeklyPrizePool, WeeklyPayout, TeamMember
)


class StandingsService:
    """
    Service to calculate and update leaderboard standings
    """
    
    def update_all_standings_for_week(self, week):
        """
        Update all user and team standings after a week is scored
        
        Args:
            week: Week object that was just scored
            
        Returns:
            Dict with update counts
        """
        print(f"\n{'=' * 80}")
        print(f"UPDATING STANDINGS FOR WEEK {week.week_number}")
        print(f"{'=' * 80}\n")
        
        users_updated = 0
        teams_updated = 0
        
        # Get all teams that have prize pools for this week
        prize_pools = WeeklyPrizePool.objects.filter(week=week)
        
        for prize_pool in prize_pools:
            team = prize_pool.team
            
            # Update all user standings for this team
            team_users = self._update_team_user_standings(week, team)
            users_updated += team_users
            
            # Update team standing
            self._update_team_standing(week.season_year, team)
            teams_updated += 1
        
        # Calculate rankings
        self._calculate_rankings(week.season_year)
        
        print(f"\n{'=' * 80}")
        print(f"STANDINGS UPDATE COMPLETE")
        print(f"{'=' * 80}")
        print(f"✅ Users updated: {users_updated}")
        print(f"✅ Teams updated: {teams_updated}\n")
        
        return {
            'users_updated': users_updated,
            'teams_updated': teams_updated
        }
    
    def _update_team_user_standings(self, week, team):
        """Update standings for all users in a team"""
        
        # Get all team members
        members = TeamMember.objects.filter(
            team=team,
            status='active'
        )
        
        users_updated = 0
        
        for member in members:
            user = member.user
            
            # Get or create standing for this user/team/season
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
                }
            )
            
            # Calculate stats from all their picks this season
            picks = Pick.objects.filter(
                user=user,
                team=team,
                week__season_year=week.season_year
            )
            
            total_picks = picks.count()
            hit_picks = picks.filter(result_status='hit').count()
            
            # Calculate weeks participated (weeks with at least 1 pick)
            weeks_participated = picks.values('week').distinct().count()
            
            # Calculate perfect weeks (4/4 picks hit in a week)
            perfect_weeks = 0
            for week_data in picks.values('week').annotate(
                hits=Count('id', filter=Q(result_status='hit')),
                total=Count('id')
            ):
                if week_data['hits'] == 4 and week_data['total'] == 4:
                    perfect_weeks += 1
            
            # Calculate highest weekly score
            highest_weekly = 0
            for week_data in picks.values('week').annotate(
                hits=Count('id', filter=Q(result_status='hit'))
            ):
                if week_data['hits'] > highest_weekly:
                    highest_weekly = week_data['hits']
            
            # Calculate current streak (consecutive weeks with at least 1 hit)
            current_streak = self._calculate_current_streak(user, team, week.season_year)
            
            # Calculate longest streak
            longest_streak = self._calculate_longest_streak(user, team, week.season_year)
            
            # Calculate financial stats
            total_winnings = WeeklyPayout.objects.filter(
                user=user,
                team=team,
                week__season_year=week.season_year,
                payout_status='paid'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            # Total paid (weekly payments)
            from core.models import WeeklyPayment
            total_paid = WeeklyPayment.objects.filter(
                user=user,
                team=team,
                week__season_year=week.season_year,
                payment_status='paid'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            
            # Update the standing
            standing.total_points = hit_picks  # 1 point per hit pick
            standing.total_picks_made = total_picks
            standing.total_picks_hit = hit_picks
            standing.weeks_participated = weeks_participated
            standing.perfect_weeks = perfect_weeks
            standing.highest_weekly_score = highest_weekly
            standing.current_streak = current_streak
            standing.longest_streak = longest_streak
            standing.total_winnings = total_winnings
            standing.total_paid = total_paid
            standing.update_accuracy()  # Calculates accuracy and net profit
            
            standing.save()
            users_updated += 1
            
            print(f"✅ Updated: {user.username} - {hit_picks} pts, {perfect_weeks} perfect weeks")
        
        return users_updated
    
    def _calculate_current_streak(self, user, team, season_year):
        """Calculate consecutive weeks with at least 1 hit"""
        
        # Get all weeks in order
        weeks = Week.objects.filter(
            season_year=season_year,
            is_completed=True
        ).order_by('-week_number')
        
        streak = 0
        for week in weeks:
            picks = Pick.objects.filter(
                user=user,
                team=team,
                week=week
            )
            
            if not picks.exists():
                break  # No picks this week, streak ends
            
            hits = picks.filter(result_status='hit').count()
            
            if hits > 0:
                streak += 1
            else:
                break  # No hits this week, streak ends
        
        return streak
    
    def _calculate_longest_streak(self, user, team, season_year):
        """Calculate longest streak of consecutive weeks with at least 1 hit"""
        
        weeks = Week.objects.filter(
            season_year=season_year,
            is_completed=True
        ).order_by('week_number')
        
        longest = 0
        current = 0
        
        for week in weeks:
            picks = Pick.objects.filter(
                user=user,
                team=team,
                week=week
            )
            
            if not picks.exists():
                current = 0
                continue
            
            hits = picks.filter(result_status='hit').count()
            
            if hits > 0:
                current += 1
                if current > longest:
                    longest = current
            else:
                current = 0
        
        return longest
    
    def _update_team_standing(self, season_year, team):
        """Update team-level standing"""
        
        # Get or create team standing
        standing, created = TeamStanding.objects.get_or_create(
            team=team,
            season_year=season_year,
            defaults={
                'total_members': 0,
                'active_members': 0,
                'total_team_points': 0,
            }
        )
        
        # Count members
        total_members = TeamMember.objects.filter(team=team).count()
        active_members = TeamMember.objects.filter(
            team=team,
            status='active'
        ).count()
        
        # Get user standings for this team
        user_standings = UserStanding.objects.filter(
            team=team,
            season_year=season_year
        )
        
        # Calculate team stats
        total_points = user_standings.aggregate(
            total=Sum('total_points')
        )['total'] or 0
        
        total_perfect_weeks = user_standings.aggregate(
            total=Sum('perfect_weeks')
        )['total'] or 0
        
        avg_points = user_standings.aggregate(
            avg=Avg('total_points')
        )['avg'] or Decimal('0.00')
        
        # Calculate participation rate
        # (How many members play each week on average)
        weeks = Week.objects.filter(
            season_year=season_year,
            is_completed=True
        ).count()
        
        if weeks > 0 and active_members > 0:
            total_participations = user_standings.aggregate(
                total=Sum('weeks_participated')
            )['total'] or 0
            
            max_possible = weeks * active_members
            participation_rate = (Decimal(total_participations) / Decimal(max_possible)) * Decimal('100.00')
        else:
            participation_rate = Decimal('0.00')
        
        # Update team standing
        standing.total_members = total_members
        standing.active_members = active_members
        standing.total_team_points = total_points
        standing.average_points_per_member = avg_points
        standing.total_perfect_weeks = total_perfect_weeks
        standing.participation_rate = participation_rate
        standing.save()
        
        print(f"✅ Updated team: {team.name} - {total_points} pts, {active_members} active members")
    
    def _calculate_rankings(self, season_year):
        """Calculate rankings for all users and teams"""
        
        # Rank users within each team
        teams = TeamStanding.objects.filter(season_year=season_year)
        
        for team_standing in teams:
            team = team_standing.team
            
            # Get all user standings for this team, ordered by points
            standings = UserStanding.objects.filter(
                team=team,
                season_year=season_year
            ).order_by('-total_points', '-accuracy_percentage', '-perfect_weeks')
            
            # Assign ranks
            for rank, standing in enumerate(standings, start=1):
                standing.team_rank = rank
                standing.save(update_fields=['team_rank'])
        
        # Rank teams globally
        team_standings = TeamStanding.objects.filter(
            season_year=season_year
        ).order_by('-total_team_points', '-average_points_per_member')
        
        for rank, standing in enumerate(team_standings, start=1):
            standing.rank = rank
            standing.save(update_fields=['rank'])
        
        print("✅ Rankings calculated")


# Convenience function
def update_standings_for_week(week):
    """
    Shortcut function to update standings after scoring a week
    
    Usage:
        from core.services.standings_service import update_standings_for_week
        update_standings_for_week(week)
    """
    service = StandingsService()
    return service.update_all_standings_for_week(week)
