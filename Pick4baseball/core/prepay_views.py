"""
Season Prepay & Payment Preference Views
Handles onboarding, season prepay, and custom amount deposits

Created: February 16, 2026
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from decimal import Decimal
from core.models import UserProfile, Week, Team
from core.services.balance_service import complete_season_prepay, complete_custom_prepay
import stripe
import logging

logger = logging.getLogger(__name__)

# Set Stripe API key
stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
def payment_preference_onboarding(request):
    """
    Show payment preference options during onboarding
    First-time users choose how they want to pay
    """
    profile = request.user.profile

    # Skip if already completed onboarding
    if profile.onboarding_completed:
        messages.info(request, "You've already completed onboarding.")
        return redirect('home')

    # Get user's active team
    team_membership = request.user.team_memberships.filter(status='active').first()
    if not team_membership:
        messages.warning(request, "Please join a team first.")
        return redirect('home')

    team = team_membership.team

    # Calculate season info
    current_week = Week.objects.filter(is_active=True, season_year=2026).first()
    if current_week:
        weeks_remaining = 26 - current_week.week_number + 1
    else:
        weeks_remaining = 26

    season_cost = team.weekly_fee * weeks_remaining

    # Calculate savings
    stripe_fee_per_week = Decimal('0.30') + (team.weekly_fee * Decimal('0.029'))
    total_stripe_fees_weekly = stripe_fee_per_week * weeks_remaining

    stripe_fee_season = Decimal('0.30') + (season_cost * Decimal('0.029'))
    fee_savings = total_stripe_fees_weekly - stripe_fee_season

    if request.method == 'POST':
        preference = request.POST.get('payment_preference')

        if preference not in ['weekly', 'season', 'custom']:
            messages.error(request, "Invalid payment preference selected.")
            return redirect('payment_preference_onboarding')

        # Save preference
        profile.payment_preference = preference
        profile.save()

        if preference == 'weekly':
            # Mark onboarding complete, go to dashboard
            profile.onboarding_completed = True
            profile.save()
            messages.success(request,
                f"You're all set! You'll pay ${team.weekly_fee} each week before making picks."
            )
            return redirect('home')

        elif preference == 'season':
            # Redirect to season prepay payment
            return redirect('season_prepay_payment')

        elif preference == 'custom':
            # Redirect to custom amount payment
            return redirect('custom_amount_payment')

    context = {
        'team': team,
        'weekly_fee': team.weekly_fee,
        'weeks_remaining': weeks_remaining,
        'season_cost': season_cost,
        'fee_savings': fee_savings,
        'profile': profile,
        'current_week': current_week,
    }

    return render(request, 'onboarding/payment_preference.html', context)


@login_required
def season_prepay_payment(request):
    """
    Handle full season prepayment with Stripe
    """
    profile = request.user.profile
    team_membership = request.user.team_memberships.filter(status='active').first()

    if not team_membership:
        messages.warning(request, "Please join a team first.")
        return redirect('home')

    team = team_membership.team

    # Calculate season cost (prorate if mid-season)
    current_week = Week.objects.filter(is_active=True, season_year=2026).first()
    if current_week:
        weeks_remaining = 26 - current_week.week_number + 1
    else:
        weeks_remaining = 26

    season_cost = team.weekly_fee * weeks_remaining

    if request.method == 'POST':
        try:
            # Create Stripe Checkout Session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'unit_amount': int(season_cost * 100),  # Convert to cents
                        'product_data': {
                            'name': f'Season Prepay - {team.name}',
                            'description': f'{weeks_remaining} weeks @ ${team.weekly_fee}/week',
                        },
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=request.build_absolute_uri('/payments/season-prepay-success/'),
                cancel_url=request.build_absolute_uri('/onboarding/season-prepay/'),
                client_reference_id=str(request.user.id),
                metadata={
                    'payment_type': 'season_prepay',
                    'user_id': request.user.id,
                    'team_id': team.id,
                    'weeks_covered': weeks_remaining,
                    'amount': str(season_cost),
                }
            )

            # Store info in session for callback
            request.session['prepay_amount'] = float(season_cost)
            request.session['prepay_weeks'] = weeks_remaining
            request.session['prepay_team_id'] = team.id

            return redirect(checkout_session.url)

        except Exception as e:
            logger.error(f"Stripe error for {request.user.username}: {str(e)}")
            messages.error(request, "Payment processing error. Please try again.")
            return redirect('season_prepay_payment')

    context = {
        'team': team,
        'weeks_remaining': weeks_remaining,
        'weekly_fee': team.weekly_fee,
        'season_cost': season_cost,
        'profile': profile,
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    }

    return render(request, 'onboarding/season_prepay.html', context)


@login_required
def season_prepay_success(request):
    """
    Handle successful season prepay payment
    Called after Stripe redirect
    """
    # Get session data
    prepay_amount = request.session.get('prepay_amount')
    prepay_weeks = request.session.get('prepay_weeks')
    prepay_team_id = request.session.get('prepay_team_id')

    if not all([prepay_amount, prepay_weeks, prepay_team_id]):
        messages.error(request, "Payment session expired. Please try again.")
        return redirect('payment_preference_onboarding')

    try:
        team = Team.objects.get(id=prepay_team_id)

        # Complete the prepay
        success = complete_season_prepay(
            user=request.user,
            amount_paid=prepay_amount,
            weeks_covered=prepay_weeks,
            team=team
        )

        if success:
            # Clear session
            del request.session['prepay_amount']
            del request.session['prepay_weeks']
            del request.session['prepay_team_id']

            messages.success(request,
                f"Success! ${prepay_amount} added to your account. "
                f"You're covered for {prepay_weeks} weeks with auto-pay enabled!"
            )
            return redirect('home')
        else:
            messages.error(request, "Error processing payment. Please contact support.")
            return redirect('payment_preference_onboarding')

    except Team.DoesNotExist:
        messages.error(request, "Team not found. Please contact support.")
        return redirect('home')

    # Check if this was an upgrade
    is_upgrade = profile.payment_preference == 'weekly'

    if success:
        # Clear session
        del request.session['prepay_amount']
        del request.session['prepay_weeks']
        del request.session['prepay_team_id']

        if is_upgrade:
            messages.success(request,
                f"🎉 Successfully upgraded to season prepay! "
                f"${prepay_amount} added to your account. "
                f"You're now set for {prepay_weeks} weeks with auto-pay!"
            )
        else:
            messages.success(request,
                f"Success! ${prepay_amount} added to your account. "
                f"You're covered for {prepay_weeks} weeks with auto-pay enabled!"
            )

        return redirect('home')


@login_required
def custom_amount_payment(request):
    """
    Handle custom amount deposit with Stripe
    """
    profile = request.user.profile
    team_membership = request.user.team_memberships.filter(status='active').first()

    if not team_membership:
        messages.warning(request, "Please join a team first.")
        return redirect('home')

    team = team_membership.team

    # Suggested amounts based on weeks of coverage
    suggested_amounts = [
        {'amount': 50, 'weeks': 5},
        {'amount': 100, 'weeks': 10},
        {'amount': 150, 'weeks': 15},
        {'amount': 260, 'weeks': 26},  # Full season
    ]

    if request.method == 'POST':
        try:
            # Get amount (either from quick button or custom input)
            amount_str = request.POST.get('amount')

            if not amount_str:
                messages.error(request, "Please enter an amount.")
                return redirect('custom_amount_payment')

            amount = Decimal(amount_str)

            # Validate amount
            if amount < 10:
                messages.error(request, "Minimum deposit is $10.")
                return redirect('custom_amount_payment')

            if amount > 1000:
                messages.error(request, "Maximum deposit is $1,000.")
                return redirect('custom_amount_payment')

            # Create Stripe Checkout Session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'unit_amount': int(amount * 100),  # Convert to cents
                        'product_data': {
                            'name': f'Account Deposit - {team.name}',
                            'description': f'Add ${amount} to your account balance',
                        },
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=request.build_absolute_uri('/payments/custom-prepay-success/'),
                cancel_url=request.build_absolute_uri('/onboarding/custom-amount/'),
                client_reference_id=str(request.user.id),
                metadata={
                    'payment_type': 'custom_prepay',
                    'user_id': request.user.id,
                    'team_id': team.id,
                    'amount': str(amount),
                }
            )

            # Store info in session for callback
            request.session['custom_prepay_amount'] = float(amount)
            request.session['custom_prepay_team_id'] = team.id

            return redirect(checkout_session.url)

        except ValueError:
            messages.error(request, "Invalid amount entered.")
            return redirect('custom_amount_payment')
        except Exception as e:
            logger.error(f"Stripe error for {request.user.username}: {str(e)}")
            messages.error(request, "Payment processing error. Please try again.")
            return redirect('custom_amount_payment')

    context = {
        'team': team,
        'weekly_fee': team.weekly_fee,
        'suggested_amounts': suggested_amounts,
        'profile': profile,
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    }

    return render(request, 'onboarding/custom_amount.html', context)


@login_required
def custom_prepay_success(request):
    """
    Handle successful custom prepay payment
    Called after Stripe redirect
    """
    # Get session data
    custom_prepay_amount = request.session.get('custom_prepay_amount')
    custom_prepay_team_id = request.session.get('custom_prepay_team_id')

    if not all([custom_prepay_amount, custom_prepay_team_id]):
        messages.error(request, "Payment session expired. Please try again.")
        return redirect('payment_preference_onboarding')

    try:
        team = Team.objects.get(id=custom_prepay_team_id)

        # Complete the prepay
        success = complete_custom_prepay(
            user=request.user,
            amount_paid=custom_prepay_amount,
            team=team
        )

        if success:
            # Clear session
            del request.session['custom_prepay_amount']
            del request.session['custom_prepay_team_id']

            profile = request.user.profile
            weeks_covered = int(Decimal(str(custom_prepay_amount)) / team.weekly_fee)

            messages.success(request,
                f"Success! ${custom_prepay_amount} added to your account. "
                f"You're covered for approximately {weeks_covered} weeks with auto-pay enabled!"
            )
            return redirect('home')
        else:
            messages.error(request, "Error processing payment. Please contact support.")
            return redirect('payment_preference_onboarding')

    except Team.DoesNotExist:
        messages.error(request, "Team not found. Please contact support.")
        return redirect('home')

@login_required
def season_prepay_payment(request):
    """
    Handle full season prepayment
    Now also handles upgrades from week-to-week
    """
    profile = request.user.profile
    team_membership = request.user.team_memberships.filter(status='active').first()

    if not team_membership:
        messages.warning(request, "Please join a team first.")
        return redirect('home')

    team = team_membership.team

    # Calculate season cost (prorate if mid-season)
    current_week = Week.objects.filter(is_active=True, season_year=2026).first()
    if current_week:
        weeks_remaining = 26 - current_week.week_number + 1
    else:
        weeks_remaining = 26

    season_cost = team.weekly_fee * weeks_remaining

    # Check if upgrading from week-to-week
    is_upgrade = profile.payment_preference == 'weekly'

    if request.method == 'POST':
        try:
            # Create Stripe Checkout Session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'unit_amount': int(season_cost * 100),
                        'product_data': {
                            'name': f'Season Prepay - {team.name}',
                            'description': f'{weeks_remaining} weeks @ ${team.weekly_fee}/week',
                        },
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=request.build_absolute_uri('/payments/season-prepay-success/'),
                cancel_url=request.build_absolute_uri('/account/settings/'),  # Changed from onboarding
                client_reference_id=str(request.user.id),
                metadata={
                    'payment_type': 'season_prepay',
                    'user_id': request.user.id,
                    'team_id': team.id,
                    'weeks_covered': weeks_remaining,
                    'amount': str(season_cost),
                    'is_upgrade': str(is_upgrade),  # Track if this is an upgrade
                }
            )

            # Store info in session for callback
            request.session['prepay_amount'] = float(season_cost)
            request.session['prepay_weeks'] = weeks_remaining
            request.session['prepay_team_id'] = team.id

            return redirect(checkout_session.url)

        except Exception as e:
            logger.error(f"Stripe error for {request.user.username}: {str(e)}")
            messages.error(request, "Payment processing error. Please try again.")
            return redirect('season_prepay_payment')

    context = {
        'team': team,
        'weeks_remaining': weeks_remaining,
        'weekly_fee': team.weekly_fee,
        'season_cost': season_cost,
        'profile': profile,
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
        'is_upgrade': is_upgrade,  # Pass to template
    }

    return render(request, 'onboarding/season_prepay.html', context)