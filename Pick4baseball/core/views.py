# core/views.py - UPDATED FOR SPRINT 3 - BP4A-8 Payment Integration
"""
Views for Baseball Pick 4 application.
Includes registration, email verification, picks functionality, and payment processing.
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_decode
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.mail import send_mail
from django.contrib import messages
from .forms import ContactForm
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db import models, transaction
from datetime import timedelta
from decimal import Decimal
from .email_utils import send_verification_email
from .models import (
    Week, MLBPlayer, Pick, PickCategory, Team, TeamMember, UserProfile,
    WeeklyPayment, WeeklyPrizePool
)
from .forms import RegistrationForm, TeamCreationForm, JoinTeamForm

import secrets
import stripe
import json
from django.shortcuts import get_object_or_404

from django.core.mail import send_mail
from django.http import HttpResponse

import logging
logger = logging.getLogger(__name__)

User = get_user_model()

def about(request):
    return render(request, 'about.html')

def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            subject = form.cleaned_data["subject"]
            priority = form.cleaned_data["priority"]
            message = form.cleaned_data["message"]

            full_subject = f"{subject} (Priority: {priority})"

            send_mail(
                full_subject,
                message,
                "claytonheald@gmail.com",      # FROM (must match verified sender)
                ["claytonheald@gmail.com"],    # TO (send to yourself for now)
            )

            messages.success(request, "Your message has been sent successfully.")
            return redirect("contact")
    else:
        form = ContactForm()

    return render(request, "contact.html", {"form": form})

    """temporary email test"""
def test_email(request):
    send_mail(
        "Test Email from Pick 4",
        "If you received this, your email system works!",
        "claytonheald@gmail.com",
        ["claytonheald@gmail.com"],
    )
    return HttpResponse("Email sent!")


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

def verify_email(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, "Your email has been verified. You can now log in.")
        return redirect('login')
    else:
        messages.error(request, "The verification link is invalid or has expired.")
        return render(request, 'verification_failed.html')

@login_required
def resend_verification(request):
    user = request.user

    if user.is_active:
        messages.info(request, "Your email is already verified.")
        return redirect("home")  # or wherever you want

    # Re-send the verification email
    send_verification_email(user)

    messages.success(request, "A new verification email has been sent to your inbox.")
    return redirect("home")  # or a dedicated "check your email" page

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            next_url = request.POST.get('next') or 'home'
            return redirect(next_url)
    else:
        form = AuthenticationForm()

    return render(request, 'login.html', {'form': form})

@login_required
def home(request):
    """
    Dashboard homepage.
    Shows current week status, user stats, and quick actions.
    """
    # Get current active week
    current_week = Week.objects.filter(is_active=True).first()

    if not current_week:
        # No active week - show message
        context = {
            'current_week': None,
            'picks_made': 0,
            'season_points': 0,
            'season_rank': '-',
            'week_points': 0,
            'time_remaining': None,
        }
        return render(request, 'home.html', context)

    # Get user's picks for current week
    user_picks = Pick.objects.filter(
        user=request.user,
        week=current_week
    )
    picks_made = user_picks.count()

    # Get user's teams
    user_teams = TeamMember.objects.filter(
        user=request.user
    ).select_related('team')

    # Calculate time remaining
    now = timezone.now()
    if current_week.deadline_utc > now:
        time_diff = current_week.deadline_utc - now
        days = time_diff.days
        hours = time_diff.seconds // 3600
        minutes = (time_diff.seconds % 3600) // 60

        if days > 0:
            time_remaining = f"{days}d {hours}h {minutes}m"
        else:
            time_remaining = f"{hours}h {minutes}m"
    else:
        time_remaining = None

    # Get user stats (basic implementation)
    season_points = Pick.objects.filter(
        user=request.user,
        week__season_year=current_week.season_year,
        result_status='hit'
    ).count()

    week_points = user_picks.filter(result_status='hit').count()

    # Calculate rank (placeholder for now)
    season_rank = '-'  # TODO: Implement ranking logic in Sprint 4

    context = {
        'current_week': current_week,
        'picks_made': picks_made,
        'season_points': season_points,
        'season_rank': season_rank,
        'week_points': week_points,
        'time_remaining': time_remaining,
        'user_teams': user_teams,
    }

    return render(request, 'home.html', context)

@login_required
def team_detail(request, team_id):
    from core.models import Team, TeamMember

    team = get_object_or_404(Team, id=team_id)
    members = TeamMember.objects.filter(team=team, status='active').select_related('user')

    context = {'team': team, 'members': members}
    return render(request, 'team_detail.html', context)

# Add to core/views.py

@login_required
def my_teams(request):
    """Display all teams the user is a member of"""
    from core.models import TeamMember

    # Get all team memberships for the user
    memberships = TeamMember.objects.filter(
        user=request.user,
        status='active'
    ).select_related('team').order_by('-joined_at')

    context = {
        'memberships': memberships,
    }

    return render(request, 'my_teams.html', context)

@login_required
def make_picks(request):
    """
    Make/edit weekly picks view.
    Allows users to select their 4 weekly picks.
    """
    # Get current active week
    current_week = Week.objects.filter(is_active=True).first()

    if not current_week:
        messages.error(request, "No active week available.")
        return redirect('home')

    # Check if deadline has passed
    if timezone.now() > current_week.deadline_utc:
        messages.error(request, "The deadline for this week has passed.")
        return redirect('home')

    # Get existing picks for user (for editing)
    existing_picks = {}
    for category_code in ['2B', 'HR', 'SWP', 'S']:
        pick = Pick.objects.filter(
            user=request.user,
            week=current_week,
            category__code=category_code
        ).first()
        if pick:
            existing_picks[f'pick_{category_code.lower()}'] = pick.player.id

    if request.method == 'POST':
        # Get user's team
        from core.models import TeamMember
        team_membership = TeamMember.objects.filter(user=request.user).first()

        if not team_membership:
            messages.error(request, "You must be on a team to make picks.")
            return redirect('home')

        user_team = team_membership.team

        # Get form data
        pick_2b_id = request.POST.get('pick_2b')
        pick_hr_id = request.POST.get('pick_hr')
        pick_swp_id = request.POST.get('pick_swp')
        pick_s_id = request.POST.get('pick_s')

        # Validate all picks selected
        if not all([pick_2b_id, pick_hr_id, pick_swp_id, pick_s_id]):
            messages.error(request, "Please select all 4 picks.")
            return redirect('make_picks')

        # Optional: Validate no duplicates (uncomment if needed)
        # player_ids = [pick_2b_id, pick_hr_id, pick_swp_id, pick_s_id]
        # if len(player_ids) != len(set(player_ids)):
        #     messages.error(request, "You cannot select the same player for multiple categories.")
        #     return redirect('make_picks')

        try:
            # Get categories
            cat_2b = PickCategory.objects.get(code='2B')
            cat_hr = PickCategory.objects.get(code='HR')
            cat_swp = PickCategory.objects.get(code='SWP')
            cat_s = PickCategory.objects.get(code='S')

            # Create or update picks (including team_id)
            Pick.objects.update_or_create(
                user=request.user,
                week=current_week,
                category=cat_2b,
                defaults={
                    'player_id': pick_2b_id,
                    'team': user_team,
                    'submitted_at': timezone.now()
                }
            )

            Pick.objects.update_or_create(
                user=request.user,
                week=current_week,
                category=cat_hr,
                defaults={
                    'player_id': pick_hr_id,
                    'team': user_team,
                    'submitted_at': timezone.now()
                }
            )

            Pick.objects.update_or_create(
                user=request.user,
                week=current_week,
                category=cat_swp,
                defaults={
                    'player_id': pick_swp_id,
                    'team': user_team,
                    'submitted_at': timezone.now()
                }
            )

            Pick.objects.update_or_create(
                user=request.user,
                week=current_week,
                category=cat_s,
                defaults={
                    'player_id': pick_s_id,
                    'team': user_team,
                    'submitted_at': timezone.now()
                }
            )

            messages.success(request, "Your picks have been saved successfully!")
            logger.info(f"User {request.user.username} saved picks for Week {current_week.week_number}")
            return redirect('home')

        except PickCategory.DoesNotExist:
            messages.error(request, "Pick categories not found. Please contact support.")
            logger.error("Pick categories missing in database")
            return redirect('home')
        except Exception as e:
            messages.error(request, "An error occurred while saving your picks. Please try again.")
            logger.error(f"Error saving picks for {request.user.username}: {str(e)}")
            return redirect('make_picks')

    # GET request - show form
    # Get available players
    batters = MLBPlayer.objects.filter(
        is_active=True,
        is_pitcher=False
    ).order_by('full_name')

    pitchers = MLBPlayer.objects.filter(
        is_active=True,
        is_pitcher=True
    ).order_by('full_name')

    context = {
        'week': current_week,
        'batters': batters,
        'pitchers': pitchers,
        'existing_picks': existing_picks,
    }

    return render(request, 'make_picks.html', context)


@login_required
def view_picks(request):
    """
    View submitted picks for current week.
    Displays all 4 picks with status and results.
    """
    # Get current active week
    current_week = Week.objects.filter(is_active=True).first()

    if not current_week:
        messages.info(request, "No active week available.")
        return redirect('home')

    # Get user's picks for current week
    picks = Pick.objects.filter(
        user=request.user,
        week=current_week
    ).select_related('player', 'category').order_by('category__display_order')

    context = {
        'week': current_week,
        'picks': picks,
    }

    return render(request, 'view_picks.html', context)


@login_required
def leaderboard(request):
    """Leaderboard placeholder"""
    return render(request, 'leaderboard.html')


@login_required
def weekly_results(request):
    """Weekly results placeholder"""
    return render(request, 'weekly_results.html')


@login_required
def terms(request):
    """Terms and conditions placeholder"""
    return render(request, 'terms.html')


@login_required
def rules(request):
    """Game rules placeholder"""
    return render(request, 'rules.html')


@login_required
def account_settings(request):
    """Account settings placeholder"""
    return render(request, 'account_settings.html')


@login_required
def privacy(request):
    """Privacy policy placeholder"""
    return render(request, 'privacy.html')


def how_to_play(request):
    """How to Play / Rules page"""
    return render(request, 'how_to_play.html')

@login_required
def create_team(request):
    """
    Create a new team
    User becomes the captain
    """
    if request.method == 'POST':
        form = TeamCreationForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create team
                    team = form.save(commit=False)
                    team.captain = request.user
                    team.season_year = 2026  # TODO: Get current season

                    # Generate unique join code
                    team.join_code = secrets.token_urlsafe(8)[:8].upper()

                    # Ensure join code is unique
                    while Team.objects.filter(join_code=team.join_code).exists():
                        team.join_code = secrets.token_urlsafe(8)[:8].upper()

                    team.save()

                    # Create UserProfile if doesn't exist
                    user_profile, created = UserProfile.objects.get_or_create(
                        user=request.user
                    )

                    # Add creator as team member (captain)
                    TeamMember.objects.create(
                        team=team,
                        user=request.user,
                        role='captain'
                    )

                    messages.success(
                        request,
                        f'Team "{team.name}" created successfully! '
                        f'Your join code is: {team.join_code}'
                    )

                    return redirect('team_detail', team_id=team.id)

            except Exception as e:
                messages.error(request, f'Error creating team: {str(e)}')
                return redirect('create_team')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = TeamCreationForm()

    context = {
        'form': form,
    }

    return render(request, 'create_team.html', context)


@login_required
def team_detail(request, team_id):
    """
    View team details
    """
    team = get_object_or_404(Team, id=team_id)

    # Check if user is a member
    is_member = TeamMember.objects.filter(
        team=team,
        user=request.user
    ).exists()

    # Get user's membership info
    membership = None
    if is_member:
        membership = TeamMember.objects.get(team=team, user=request.user)

    # Get all team members
    members = TeamMember.objects.filter(team=team).select_related('user')

    # Check if user is captain
    is_captain = team.captain == request.user

    context = {
        'team': team,
        'is_member': is_member,
        'is_captain': is_captain,
        'membership': membership,
        'members': members,
    }

    return render(request, 'team_detail.html', context)


@login_required
def my_teams(request):
    """
    List all teams user is a member of
    """
    memberships = TeamMember.objects.filter(
        user=request.user
    ).select_related('team').order_by('-joined_at')

    context = {
        'memberships': memberships,
    }

    return render(request, 'my_teams.html', context)

    # ADD THIS TO core/views.py (after my_teams view)

@login_required
def join_team(request):
    """
    Join an existing team using a join code
    """
    if request.method == 'POST':
        form = JoinTeamForm(request.POST)

        if form.is_valid():
            join_code = form.cleaned_data['join_code']
            team = form.cleaned_data['team']

            # Check if user is already a member
            existing_membership = TeamMember.objects.filter(
                team=team,
                user=request.user
            ).first()

            if existing_membership:
                messages.warning(
                    request,
                    f'You are already a member of "{team.name}"!'
                )
                return redirect('team_detail', team_id=team.id)

            # Add user to team
            try:
                TeamMember.objects.create(
                    team=team,
                    user=request.user,
                    role='member'
                )

                messages.success(
                    request,
                    f'Successfully joined "{team.name}"! Welcome to the team.'
                )

                return redirect('team_detail', team_id=team.id)

            except Exception as e:
                messages.error(
                    request,
                    f'Error joining team: {str(e)}'
                )
                return redirect('join_team')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = JoinTeamForm()

    context = {
        'form': form,
    }

    return render(request, 'join_team.html', context)

@login_required
def dashboard(request):
    context = {
        'current_week': 1,
        'deadline': 'Sat 11:00 AM',
        'picks_count': 0,
        'total_points': 0,
        'correct_picks': 0,
        'streak': 0,
        'rank': '-',
        'teams': [],
    }
    return render(request, 'dashboard.html', context)


# ==============================================================================
# PAYMENT VIEWS - BP4A-8: Secure Payment Submission
# ==============================================================================

@login_required
def payment_portal(request):
    """
    Main payment portal view.
    Shows payment status, outstanding fees, and payment options.
    """
    # Get user's team memberships
    memberships = TeamMember.objects.filter(
        user=request.user,
        status='active'
    ).select_related('team')

    # Get current week
    current_week = Week.objects.filter(is_active=True).first()

    payment_data = []
    total_outstanding = Decimal('0.00')

    for membership in memberships:
        team = membership.team

        # Check if user has paid for current week
        if current_week:
            payment_exists = WeeklyPayment.objects.filter(
                user=request.user,
                team=team,
                week=current_week,
                payment_status__in=['completed', 'pending']
            ).exists()

            payment_status = 'paid' if payment_exists else 'outstanding'
            amount_due = Decimal('0.00') if payment_exists else team.weekly_fee

            if not payment_exists:
                total_outstanding += team.weekly_fee
        else:
            payment_status = 'no_active_week'
            amount_due = Decimal('0.00')

        payment_data.append({
            'team': team,
            'week': current_week,
            'status': payment_status,
            'amount_due': amount_due,
        })

    context = {
        'payment_data': payment_data,
        'total_outstanding': total_outstanding,
        'current_week': current_week,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
    }

    return render(request, 'payments/payment_portal.html', context)


@login_required
def create_payment_intent(request, team_id):
    """
    Create a Stripe Payment Intent for a team payment.
    Returns client secret for frontend to complete payment.
    """
    # Initialize Stripe with the API key
    stripe.api_key = settings.STRIPE_SECRET_KEY

    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        team = get_object_or_404(Team, id=team_id)

        # Verify user is a team member
        membership = TeamMember.objects.filter(
            user=request.user,
            team=team,
            status='active'
        ).first()

        if not membership:
            return JsonResponse({'error': 'Not a team member'}, status=403)

        # Get current week
        current_week = Week.objects.filter(is_active=True).first()
        if not current_week:
            return JsonResponse({'error': 'No active week'}, status=400)

        # Check if already paid
        existing_payment = WeeklyPayment.objects.filter(
            user=request.user,
            team=team,
            week=current_week,
            payment_status__in=['completed', 'pending']
        ).first()

        if existing_payment:
            return JsonResponse({'error': 'Already paid for this week'}, status=400)

        # Get or create Stripe customer
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)

        if not user_profile.stripe_customer_id:
            customer = stripe.Customer.create(
                email=request.user.email,
                name=request.user.get_full_name() or request.user.username,
                metadata={
                    'user_id': request.user.id,
                    'username': request.user.username,
                }
            )
            user_profile.stripe_customer_id = customer.id
            user_profile.save()

        # Create Payment Intent
        amount_cents = int(team.weekly_fee * 100)  # Convert to cents

        payment_intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency='usd',
            customer=user_profile.stripe_customer_id,
            metadata={
                'user_id': request.user.id,
                'username': request.user.username,
                'team_id': team.id,
                'team_name': team.name,
                'week_id': current_week.id,
                'week_number': current_week.week_number,
                'season_year': current_week.season_year,
            },
            description=f'{team.name} - Week {current_week.week_number} Entry Fee',
        )

        # Create pending payment record
        payment = WeeklyPayment.objects.create(
            user=request.user,
            team=team,
            week=current_week,
            amount=team.weekly_fee,
            payment_method='stripe',
            payment_status='pending',
            stripe_payment_intent_id=payment_intent.id,
        )

        logger.info(
            f"Payment intent created: {payment_intent.id} for "
            f"{request.user.username} - {team.name} - Week {current_week.week_number}"
        )

        return JsonResponse({
            'clientSecret': payment_intent.client_secret,
            'payment_id': payment.id,
        })

    except Team.DoesNotExist:
        return JsonResponse({'error': 'Team not found'}, status=404)
    except Exception as e:
        logger.error(f"Error creating payment intent: {str(e)}")
        return JsonResponse({'error': 'Payment processing error'}, status=500)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """
    Handle Stripe webhook events.
    Processes payment confirmations and updates payment status.
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        logger.error("Invalid webhook payload")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid webhook signature")
        return HttpResponse(status=400)

    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        handle_payment_success(payment_intent)

    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        handle_payment_failure(payment_intent)

    else:
        logger.info(f"Unhandled webhook event type: {event['type']}")

    return HttpResponse(status=200)


def handle_payment_success(payment_intent):
    """
    Handle successful payment and update prize pools with 80/10/10 split

    Payment Breakdown:
    - 80% → weekly_pool_amount (for picks payout)
    - 10% → season_pot_contribution (end of season)
    - 10% → company_fee (application cost)
    """
    try:
        # Get payment intent metadata
        metadata = payment_intent.get('metadata', {})
        user_id = metadata.get('user_id')
        team_id = metadata.get('team_id')
        week_id = metadata.get('week_id')

        if not all([user_id, team_id, week_id]):
            print(f"Missing metadata in payment intent: {payment_intent.id}")
            return False

        # Use database transaction to ensure data consistency
        with transaction.atomic():
            # 1. Update or create the WeeklyPayment record
            payment, created = WeeklyPayment.objects.get_or_create(
                user_id=user_id,
                team_id=team_id,
                week_id=week_id,
                defaults={
                    'amount': Decimal(str(payment_intent['amount'])) / 100,  # Stripe uses cents
                    'payment_status': 'completed',
                    'payment_method': 'stripe',
                    'stripe_payment_intent_id': payment_intent['id'],
                    'stripe_charge_id': payment_intent.get('latest_charge'),
                    'stripe_customer_id': payment_intent.get('customer'),
                    'payment_date': timezone.now(),
                }
            )

            # If payment already existed, update it
            if not created:
                payment.payment_status = 'completed'
                payment.stripe_payment_intent_id = payment_intent['id']
                payment.stripe_charge_id = payment_intent.get('latest_charge')
                payment.payment_date = timezone.now()
                payment.save()

            # 2. Calculate the 80/10/10 split
            payment_amount = payment.amount

            weekly_pool = payment_amount * Decimal('0.80')      # 80% for picks
            season_pot = payment_amount * Decimal('0.10')       # 10% for season
            company_fee = payment_amount * Decimal('0.10')      # 10% for app

            # Calculate per-pick value based on payment amount
            # $5 payment = $1 per pick, $10 payment = $2 per pick
            per_pick_value = weekly_pool / Decimal('4.00')  # 4 picks per entry

            # 3. Get or create the WeeklyPrizePool for this team/week
            prize_pool, pool_created = WeeklyPrizePool.objects.get_or_create(
                team_id=team_id,
                week_id=week_id,
                defaults={
                    'total_collected': Decimal('0.00'),
                    'weekly_pool_amount': Decimal('0.00'),
                    'season_pot_contribution': Decimal('0.00'),
                    'company_fee': Decimal('0.00'),
                    'per_pick_value': per_pick_value,
                }
            )

            # 4. Update the prize pool amounts (add to existing amounts)
            prize_pool.total_collected += payment_amount
            prize_pool.weekly_pool_amount += weekly_pool
            prize_pool.season_pot_contribution += season_pot
            prize_pool.company_fee += company_fee

            # Update per_pick_value (recalculate based on pool)
            # This handles mixed $5 and $10 payments
            if prize_pool.total_collected > 0:
                prize_pool.per_pick_value = prize_pool.weekly_pool_amount / (Decimal('4.00') * prize_pool.payment_count)

            prize_pool.save()

            # 5. Update user's lifetime payment total
            user_profile, profile_created = UserProfile.objects.get_or_create(
                user_id=user_id,
                defaults={'total_lifetime_paid': Decimal('0.00')}
            )
            user_profile.total_lifetime_paid += payment_amount
            user_profile.save()

            # 6. Log success
            print(f"✅ Payment processed successfully:")
            print(f"   User: {user_id}, Team: {team_id}, Week: {week_id}")
            print(f"   Amount: ${payment_amount}")
            print(f"   Split: Pool=${weekly_pool}, Season=${season_pot}, Fee=${company_fee}")
            print(f"   Prize Pool ID: {prize_pool.id}")

            return True

    except Exception as e:
        print(f"❌ Error in handle_payment_success: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


# HELPER PROPERTY FOR PRIZE POOL MODEL
# Add this to your WeeklyPrizePool model in models.py:

"""
@property
def payment_count(self):
    '''Count of completed payments for this team/week'''
    return self.team.weekly_payments.filter(
        week=self.week,
        payment_status='completed'
    ).count()
"""

def handle_payment_failure(payment_intent):
    """
    Process failed payment.
    Update payment status and log failure.
    """
    try:
        payment_intent_id = payment_intent['id']

        payment = WeeklyPayment.objects.filter(
            stripe_payment_intent_id=payment_intent_id
        ).first()

        if not payment:
            logger.error(f"Payment record not found for failed intent: {payment_intent_id}")
            return

        payment.payment_status = 'failed'
        payment.notes = f"Payment failed: {payment_intent.get('last_payment_error', {}).get('message', 'Unknown error')}"
        payment.save()

        logger.warning(
            f"Payment failed: {payment.id} - "
            f"{payment.user.username} - Reason: {payment.notes}"
        )

        # TODO: Send failure notification email (Sprint 3 Day 2)

    except Exception as e:
        logger.error(f"Error processing payment failure: {str(e)}")


@login_required
def payment_history(request):
    """
    View payment history for user.
    Shows all past payments across all teams.
    """
    payments = WeeklyPayment.objects.filter(
        user=request.user
    ).select_related('team', 'week').order_by('-created_at')

    # Calculate totals
    total_paid = payments.filter(payment_status='completed').aggregate(
        total=models.Sum('amount')
    )['total'] or Decimal('0.00')

    context = {
        'payments': payments,
        'total_paid': total_paid,
    }

    return render(request, 'payments/payment_history.html', context)


@login_required
def payment_confirmation(request, payment_id):
    """
    Payment confirmation page.
    Shows details of a completed payment.
    """
    payment = get_object_or_404(
        WeeklyPayment,
        id=payment_id,
        user=request.user
    )

    context = {
        'payment': payment,
    }

    return render(request, 'payments/payment_confirmation.html', context)
