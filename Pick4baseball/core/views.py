# core/views.py - COMPLETE CLEAN VERSION (FIXED)
"""
Views for Baseball Pick 4 application.
Includes registration, email verification, and picks functionality.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import RegistrationForm
from .email_utils import send_verification_email
import logging

logger = logging.getLogger(__name__)

def register(request):
    """
    User registration view with email verification.

    GET: Display registration form
    POST: Process registration and send verification email
    """
    if request.method == 'POST':
        form = RegistrationForm(request.POST)

        if form.is_valid():
            # Save user but don't activate yet
            user = form.save(commit=False)
            user.is_active = False  # User must verify email first
            user.save()

            username = form.cleaned_data.get('username')
            logger.info(f"New user registered: {username} ({user.email})")

            # Send verification email
            email_sent = send_verification_email(request, user)

            if email_sent:
                messages.success(
                    request,
                    f'Account created for {username}! Please check your email to verify your account.'
                )
                logger.info(f"Verification email sent to {user.email}")
                return redirect('verification_sent')
            else:
                # Email failed to send, but account was created
                messages.warning(
                    request,
                    f'Account created for {username}, but there was an issue sending the verification email. '
                    f'Please use the "Resend Verification" option.'
                )
                logger.error(f"Failed to send verification email to {user.email}")
                return redirect('resend_verification')
        else:
            messages.error(request, 'Please correct the errors below.')
            logger.warning(f"Registration form validation failed: {form.errors}")
    else:
        form = RegistrationForm()

    return render(request, 'register.html', {'form': form})

@login_required
def home(request):
    """
    Dashboard homepage.
    Shows current week status, user stats, and quick actions.
    """
    context = {
        'current_week': None,
        'picks_made': 0,
        'season_points': 0,
        'season_rank': '-',
        'week_points': 0,
        'time_remaining': None,
    }
    return render(request, 'home.html', context)


@login_required
def make_picks(request):
    """
    Form to make weekly picks.
    Shows player selection form for 4 categories.
    """
    context = {
        'week': None,
        'batters': [],
        'pitchers': [],
        'current_picks': {},
    }
    return render(request, 'make_picks.html', context)


@login_required
def view_picks(request):
    """
    View submitted picks for current week.
    Displays all 4 picks with status and results.
    """
    return render(request, 'view_picks.html')


@login_required
def leaderboard(request):
    """Leaderboard placeholder"""
    return render(request, 'leaderboard.html')


@login_required
def weekly_results(request):
    """Weekly results placeholder"""
    return render(request, 'weekly_results.html')


@login_required
def rules(request):
    """Game rules placeholder"""
    return render(request, 'rules.html')


@login_required
def account_settings(request):
    """Account settings placeholder"""
    return render(request, 'account_settings.html')