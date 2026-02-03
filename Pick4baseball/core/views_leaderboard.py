# core/views_leaderboard.py
"""
Leaderboard Views
Display user standings, team standings, and weekly results

Created: January 30, 2026
"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from core.models import (
    UserStanding, TeamStanding, Week, Pick,
    Team, TeamMember, WeeklyPrizePool, WeeklyPayout
)


@login_required
def leaderboard(request):
    """
    Main leaderboard view showing user's team standings
    """
    # Get user's teams
    user_teams = TeamMember.objects.filter(
        user=request.user,
        status='active'
    ).select_related('team')

    # Default to first team if user has multiple
    selected_team = None
    if user_teams.exists():
        # Check if team_id in query params
        team_id = request.GET.get('team')
        if team_id:
            selected_team = Team.objects.filter(id=team_id).first()

        if not selected_team:
            selected_team = user_teams.first().team

    # Get current season year
    current_week = Week.objects.filter(is_active=True).first()
    season_year = current_week.season_year if current_week else 2026

    # Get standings for selected team
    standings = []
    user_standing = None

    if selected_team:
        standings = UserStanding.objects.filter(
            team=selected_team,
            season_year=season_year
        ).select_related('user').order_by('team_rank')

        # Get current user's standing
        user_standing = standings.filter(user=request.user).first()

    context = {
        'user_teams': user_teams,
        'selected_team': selected_team,
        'season_year': season_year,
        'standings': standings,
        'user_standing': user_standing,
        'current_week': current_week,
    }

    return render(request, 'leaderboard.html', context)


@login_required
def weekly_results(request, week_number=None):
    """
    Show results for a specific week
    """
    # Get user's first active team
    team_member = TeamMember.objects.filter(
        user=request.user,
        status='active'
    ).first()

    if not team_member:
        return render(request, 'weekly_results.html', {
            'error': 'You are not a member of any team'
        })

    team = team_member.team

    # Get season year
    current_week = Week.objects.filter(is_active=True).first()
    season_year = current_week.season_year if current_week else 2026

    # Get specific week or most recent completed week
    if week_number:
        week = get_object_or_404(
            Week,
            week_number=week_number,
            season_year=season_year
        )
    else:
        week = Week.objects.filter(
            season_year=season_year,
            is_completed=True
        ).order_by('-week_number').first()

    if not week:
        return render(request, 'weekly_results.html', {
            'error': 'No completed weeks found'
        })

    # Get prize pool for this week/team
    prize_pool = WeeklyPrizePool.objects.filter(
        week=week,
        team=team
    ).first()

    # Get all users' picks for this week
    team_members = TeamMember.objects.filter(
        team=team,
        status='active'
    ).select_related('user')

    results = []
    for member in team_members:
        picks = Pick.objects.filter(
            user=member.user,
            team=team,
            week=week
        ).select_related('player', 'category')

        hits = picks.filter(result_status='hit').count()
        total = picks.count()

        # Check if user won this week
        payout = WeeklyPayout.objects.filter(
            user=member.user,
            team=team,
            week=week
        ).first()

        results.append({
            'user': member.user,
            'picks': picks,
            'hits': hits,
            'total': total,
            'is_perfect': hits == 4 and total == 4,
            'payout': payout
        })

    # Sort by hits (descending)
    results.sort(key=lambda x: x['hits'], reverse=True)

    # Get all weeks for navigation
    all_weeks = Week.objects.filter(
        season_year=season_year,
        is_completed=True
    ).order_by('-week_number')

    context = {
        'week': week,
        'team': team,
        'prize_pool': prize_pool,
        'results': results,
        'all_weeks': all_weeks,
        'season_year': season_year,
    }

    return render(request, 'weekly_results.html', context)


@login_required
def team_leaderboard(request):
    """
    Show global leaderboard of all teams
    """
    # Get current season
    current_week = Week.objects.filter(is_active=True).first()
    season_year = current_week.season_year if current_week else 2026

    # Get all team standings
    team_standings = TeamStanding.objects.filter(
        season_year=season_year,
        is_public=True  # Only show public teams
    ).select_related('team').order_by('rank')

    # Get user's teams
    user_teams = TeamMember.objects.filter(
        user=request.user,
        status='active'
    ).values_list('team_id', flat=True)

    context = {
        'team_standings': team_standings,
        'season_year': season_year,
        'user_teams': user_teams,
        'current_week': current_week,
    }

    return render(request, 'team_leaderboard.html', context)


@login_required
def user_profile(request, username=None):
    """
    Show detailed profile/stats for a user
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()


    if username:
        profile_user = get_object_or_404(User, username=username)
    else:
        profile_user = request.user

    # Get current season
    current_week = Week.objects.filter(is_active=True).first()
    season_year = current_week.season_year if current_week else 2026

    # Get all standings for this user
    standings = UserStanding.objects.filter(
        user=profile_user,
        season_year=season_year
    ).select_related('team')

    # Get recent picks
    recent_picks = Pick.objects.filter(
        user=profile_user,
        week__season_year=season_year
    ).select_related(
        'week', 'player', 'category', 'team'
    ).order_by('-week__week_number')[:20]

    context = {
        'profile_user': profile_user,
        'standings': standings,
        'recent_picks': recent_picks,
        'season_year': season_year,
        'is_own_profile': profile_user == request.user,
    }

    return render(request, 'user_profile.html', context)
