# core/email_views.py
"""
Email sending views and utilities for Baseball Pick 4 application.
Handles all transactional emails: weekly results, picks confirmation,
withdrawal confirmation, and welcome emails.

This file is separated from views.py to keep the main views file manageable.
"""

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from .models import Pick, UserProfile, WeeklyPayout, Team
import logging

logger = logging.getLogger(__name__)


def send_weekly_results_email(user, week, user_picks, team):
    """
    Send weekly results email to user after week is scored.
    Simple version - just notifies results are in, links to leaderboard.

    Args:
        user: User object
        week: Week object
        user_picks: QuerySet of user's picks for the week
        team: Team object

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Calculate user's score
        correct_picks = sum(1 for pick in user_picks if pick.result_status == 'hit')
        total_games = user_picks.count()

        # Build URLs
        domain = settings.SITE_DOMAIN
        leaderboard_url = f"https://{domain}{reverse('leaderboard')}"
        account_url = f"https://{domain}{reverse('account_settings')}"
        support_url = f"https://{domain}/contact/"

        # Simple context
        context = {
            'user': user,
            'week_number': week.week_number,
            'correct_picks': correct_picks,
            'total_games': total_games,
            'leaderboard_url': leaderboard_url,
            'account_url': account_url,
            'support_url': support_url,
        }

        # Render templates
        html_content = render_to_string('emails/weekly_results.html', context)
        text_content = render_to_string('emails/weekly_results.txt', context)

        # Create subject line
        subject = f"Week {week.week_number} Results: You got {correct_picks}/{total_games} correct!"
        if correct_picks == 4:
            subject += " 🎉"

        # Create email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach_alternative(html_content, "text/html")

        # Send email
        email.send()
        logger.info(f"Weekly results email sent to {user.email} for week {week.week_number}")
        return True

    except Exception as e:
        logger.error(f"Error sending weekly results email to {user.email}: {e}", exc_info=True)
        return False

def send_picks_submitted_email(user, week, picks):
    """
    Send confirmation email after user submits picks.

    Args:
        user: User object
        week: Week object
        picks: QuerySet or list of Pick objects

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Build URLs
        domain = settings.SITE_DOMAIN
        edit_picks_url = f"https://{domain}{reverse('make_picks')}"
        account_url = f"https://{domain}{reverse('account_settings')}"
        support_url = f"https://{domain}/contact/"

        # Format deadline
        if week.deadline_utc:
            deadline = week.deadline_utc.strftime('%A, %B %d at %I:%M %p ET')
        else:
            deadline = "TBD"

        # Context
        context = {
            'user': user,
            'week_number': week.week_number,
            'picks': picks,
            'deadline': deadline,
            'edit_picks_url': edit_picks_url,
            'account_url': account_url,
            'support_url': support_url,
        }

        # Render templates
        html_content = render_to_string('emails/picks_submitted.html', context)
        text_content = render_to_string('emails/picks_submitted.txt', context)

        # Create and send email
        subject = f"Picks Received for Week {week.week_number} ✅"

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach_alternative(html_content, "text/html")

        email.send()
        logger.info(f"Picks confirmation email sent to {user.email} for week {week.week_number}")
        return True

    except Exception as e:
        logger.error(f"Error sending picks confirmation to {user.email}: {e}", exc_info=True)
        return False


def send_withdrawal_confirmation_email(user, withdrawal):
    """
    Send confirmation email after withdrawal is processed.

    Args:
        user: User object
        withdrawal: AccountTransaction object with withdrawal details

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Build URLs
        domain = settings.SITE_DOMAIN
        transaction_history_url = f"https://{domain}{reverse('transaction_history')}"
        account_url = f"https://{domain}{reverse('account_settings')}"
        support_url = f"https://{domain}/contact/"

        # Format payout method display
        payout_methods = {
            'paypal': 'PayPal',
            'venmo': 'Venmo',
            'stripe': 'Bank Transfer (Stripe)',
            'balance': 'Account Balance',
            'manual': 'Manual Processing',
        }

        # Get payout method from withdrawal or user profile
        if hasattr(withdrawal, 'method'):
            method = withdrawal.method
        else:
            # Get from user profile
            profile = UserProfile.objects.get(user=user)
            method = profile.preferred_payout_method or 'manual'

        payout_method = payout_methods.get(method, method.title())

        # Get destination (email for PayPal, username for Venmo, etc.)
        if hasattr(withdrawal, 'destination') and withdrawal.destination:
            destination = withdrawal.destination
        else:
            profile = UserProfile.objects.get(user=user)
            if method == 'paypal':
                destination = profile.paypal_email or 'Account on file'
            elif method == 'venmo':
                destination = profile.venmo_username or 'Account on file'
            else:
                destination = 'Account on file'

        # Format date
        if hasattr(withdrawal, 'created_at'):
            date_formatted = withdrawal.created_at.strftime('%B %d, %Y at %I:%M %p')
        else:
            from django.utils import timezone
            date_formatted = timezone.now().strftime('%B %d, %Y at %I:%M %p')

        # Get transaction ID
        transaction_id = getattr(withdrawal, 'transaction_id', None) or f"WD-{withdrawal.id}"

        # Context
        context = {
            'user': user,
            'amount': f"{withdrawal.amount:.2f}",
            'payout_method': payout_method,
            'destination': destination,
            'transaction_id': transaction_id,
            'date': date_formatted,
            'transaction_history_url': transaction_history_url,
            'account_url': account_url,
            'support_url': support_url,
        }

        # Render templates
        html_content = render_to_string('emails/withdrawal_confirmation.html', context)
        text_content = render_to_string('emails/withdrawal_confirmation.txt', context)

        # Create and send email
        subject = f"Withdrawal Processed: ${withdrawal.amount:.2f} to {payout_method}"

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach_alternative(html_content, "text/html")

        email.send()
        logger.info(f"Withdrawal confirmation email sent to {user.email} for ${withdrawal.amount}")
        return True

    except Exception as e:
        logger.error(f"Error sending withdrawal confirmation to {user.email}: {e}", exc_info=True)
        return False


def send_welcome_email(user):
    """
    Send welcome email to new users after registration.

    Args:
        user: Newly registered User object

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Build URLs
        domain = settings.SITE_DOMAIN
        team_url = f"https://{domain}{reverse('my_teams')}"
        picks_url = f"https://{domain}{reverse('make_picks')}"
        payment_url = f"https://{domain}{reverse('payment_portal')}"
        rules_url = f"https://{domain}{reverse('rules')}"
        account_url = f"https://{domain}{reverse('account_settings')}"
        support_url = f"https://{domain}/contact/"
        get_started_url = f"https://{domain}{reverse('home')}"

        # Context
        context = {
            'user': user,
            'team_url': team_url,
            'picks_url': picks_url,
            'payment_url': payment_url,
            'rules_url': rules_url,
            'account_url': account_url,
            'support_url': support_url,
            'get_started_url': get_started_url,
        }

        # Render templates
        html_content = render_to_string('emails/welcome.html', context)
        text_content = render_to_string('emails/welcome.txt', context)

        # Create and send email
        subject = "Welcome to Baseball Pick 4! ⚾"

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email],
        )
        email.attach_alternative(html_content, "text/html")

        email.send()
        logger.info(f"Welcome email sent to {user.email}")
        return True

    except Exception as e:
        logger.error(f"Error sending welcome email to {user.email}: {e}", exc_info=True)
        return False


# Helper functions for email context

def _calculate_season_rank(user, team):
    """
    Calculate user's rank within their team for the season.

    Args:
        user: User object
        team: Team object

    Returns:
        int: User's rank (1 = first place)
    """
    try:
        from django.db.models import Count, Q

        # Get all team members with their correct pick counts
        rankings = Pick.objects.filter(
            team_member__team=team,
            result_status='hit'
        ).values('user').annotate(
            correct_count=Count('id')
        ).order_by('-correct_count')

        # Find user's rank
        for idx, ranking in enumerate(rankings, start=1):
            if ranking['user'] == user.id:
                return idx

        return '-'  # User not found in rankings

    except Exception as e:
        logger.error(f"Error calculating season rank for {user.username}: {e}")
        return '-'


def _calculate_points_behind_leader(user, team, season):
    """
    Calculate how many points user is behind the team leader.

    Args:
        user: User object
        team: Team object
        season: Season object

    Returns:
        int: Points behind leader (0 if user is leader)
    """
    try:
        from django.db.models import Count, Q

        # Get leader's correct pick count
        leader_picks = Pick.objects.filter(
            team_member__team=team,
            week__season=season,
            result_status='hit'
        ).values('user').annotate(
            correct_count=Count('id')
        ).order_by('-correct_count').first()

        if not leader_picks:
            return 0

        # Get user's correct pick count
        user_picks = Pick.objects.filter(
            user=user,
            week__season=season,
            result_status='hit'
        ).count()

        return max(0, leader_picks['correct_count'] - user_picks)

    except Exception as e:
        logger.error(f"Error calculating points behind leader for {user.username}: {e}")
        return 0


# Batch email sending for admin functions

def send_weekly_results_to_all_users(week):
    """
    Send weekly results email to all users who made picks for the week.
    Called by admin after scoring a week.

    Args:
        week: Week object that was just scored

    Returns:
        dict: {'sent': int, 'failed': int, 'total': int}
    """
    from .models import TeamMember, Team

    stats = {'sent': 0, 'failed': 0, 'total': 0}

    try:
        # Get all teams that have picks for this week
        teams = Team.objects.filter(picks__week=week).distinct()

        for team in teams:
            # Get all team members
            members = TeamMember.objects.filter(team=team).select_related('user')

            for member in members:
                user = member.user

                # Get user's picks for this week
                user_picks = Pick.objects.filter(
                    user=user,
                    week=week
                ).select_related('player', 'category')

                # Only send email if user made picks
                if user_picks.exists():
                    stats['total'] += 1

                    if send_weekly_results_email(user, week, user_picks, team):
                        stats['sent'] += 1
                    else:
                        stats['failed'] += 1

        logger.info(f"Weekly results emails sent for week {week.week_number}: "
                   f"{stats['sent']} sent, {stats['failed']} failed, {stats['total']} total")

    except Exception as e:
        logger.error(f"Error sending batch weekly results emails: {e}", exc_info=True)

    return stats
