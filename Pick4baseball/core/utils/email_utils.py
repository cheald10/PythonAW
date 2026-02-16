from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse

def send_weekly_results_email(user, week, user_picks, team):
    """
    Send weekly results email to user
    
    Args:
        user: User object
        week: Week object (with week_number, season, etc.)
        user_picks: QuerySet of user's picks for the week
        team: Team object
    """
    
    # Calculate results
    correct_picks = sum(1 for pick in user_picks if pick.is_correct)
    total_games = user_picks.count()
    
    # Calculate winnings (your existing logic)
    winnings = 0
    if correct_picks == 4:
        winnings = week.weekly_pot_payout_4  # $120
    elif correct_picks == 3:
        # Split among 3/4 winners
        winners_count = team.get_week_3_correct_count(week)
        if winners_count > 0:
            winnings = week.weekly_pot_payout_3 / winners_count
    
    # Get season rankings
    season_rank = team.get_user_season_rank(user)
    total_correct = team.get_user_total_correct(user)
    points_behind = team.get_points_behind_leader(user)
    
    # Build URLs
    domain = settings.SITE_DOMAIN  # e.g., 'cheald10.pythonanywhere.com'
    leaderboard_url = f"https://{domain}{reverse('leaderboard')}"
    next_week_url = f"https://{domain}{reverse('picks')}"
    account_url = f"https://{domain}{reverse('account_settings')}"
    support_url = f"https://{domain}/support/"
    
    # Context for template
    context = {
        'user': user,
        'week_number': week.week_number,
        'correct_picks': correct_picks,
        'total_games': total_games,
        'winnings': winnings,
        'user_picks': user_picks,
        'season_rank': season_rank,
        'total_correct': total_correct,
        'points_behind': points_behind,
        'leaderboard_url': leaderboard_url,
        'next_week_url': next_week_url,
        'account_url': account_url,
        'support_url': support_url,
    }
    
    # Render templates
    html_content = render_to_string('emails/weekly_results.html', context)
    text_content = render_to_string('emails/weekly_results.txt', context)
    
    # Create email
    subject = f"Week {week.week_number} Results: You got {correct_picks}/4 correct!"
    if correct_picks == 4:
        subject += " 🎉"
    
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )
    email.attach_alternative(html_content, "text/html")
    
    # Send email
    try:
        email.send()
        return True
    except Exception as e:
        print(f"Error sending weekly results email to {user.email}: {e}")
        return False