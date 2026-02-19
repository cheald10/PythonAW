"""
Account Balance Service
Handles all balance operations with proper transaction handling and audit trails.
"""
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from core.models import UserProfile, AccountTransaction, WeeklyPayment, Week
import logging

logger = logging.getLogger(__name__)


class BalanceService:
    """Service for managing user account balances"""

    @staticmethod
    @transaction.atomic
    def add_to_balance(user, amount, description, related_payout=None, processed_by=None):
        """
        Add funds to user's account balance (e.g., from winnings)

        Args:
            user: User object
            amount: Decimal amount to add
            description: Human-readable description
            related_payout: Optional WeeklyPayout that generated this deposit
            processed_by: Optional User who processed this (admin)

        Returns:
            AccountTransaction object
        """
        profile = user.profile
        balance_before = profile.account_balance
        profile.account_balance += Decimal(str(amount))
        profile.low_balance_alert_sent = False  # Reset alert flag
        profile.save()

        transaction_record = AccountTransaction.objects.create(
            user=user,
            transaction_type='deposit',
            amount=Decimal(str(amount)),
            balance_before=balance_before,
            balance_after=profile.account_balance,
            status='completed',
            description=description,
            related_payout=related_payout,
            processed_by=processed_by
        )

        logger.info(f"Added ${amount} to {user.username}'s balance. New balance: ${profile.account_balance}")
        return transaction_record

    @staticmethod
    @transaction.atomic
    def deduct_from_balance(user, amount, description, related_payment=None):
        """
        Deduct funds from user's account balance (e.g., for weekly payment)

        Args:
            user: User object
            amount: Decimal amount to deduct
            description: Human-readable description
            related_payment: Optional WeeklyPayment being paid

        Returns:
            AccountTransaction object or None if insufficient funds
        """
        profile = user.profile
        amount = Decimal(str(amount))

        if profile.account_balance < amount:
            logger.warning(f"Insufficient balance for {user.username}: ${profile.account_balance} < ${amount}")
            return None

        balance_before = profile.account_balance
        profile.account_balance -= amount
        profile.save()

        # Check if low balance alert should be sent
        if profile.account_balance < profile.low_balance_threshold and not profile.low_balance_alert_sent:
            # TODO: Send low balance alert email
            profile.low_balance_alert_sent = True
            profile.last_low_balance_alert = timezone.now()
            profile.save()
            logger.info(f"Low balance alert triggered for {user.username}")

        transaction_record = AccountTransaction.objects.create(
            user=user,
            transaction_type='payment',
            amount=amount,
            balance_before=balance_before,
            balance_after=profile.account_balance,
            status='completed',
            description=description,
            related_payment=related_payment
        )

        logger.info(f"Deducted ${amount} from {user.username}'s balance. New balance: ${profile.account_balance}")
        return transaction_record

    @staticmethod
    @transaction.atomic
    def process_withdrawal(user, amount, withdrawal_method, notes=''):
        """
        Process withdrawal of funds from account balance

        Args:
            user: User object
            amount: Decimal amount to withdraw
            withdrawal_method: 'stripe', 'paypal', or 'venmo'
            notes: Optional notes

        Returns:
            (success: bool, transaction: AccountTransaction or None, error_message: str)
        """
        profile = user.profile
        amount = Decimal(str(amount))

        if profile.account_balance < amount:
            return (False, None, f"Insufficient funds. Available: ${profile.account_balance}")

        if amount < Decimal('5.00'):
            return (False, None, "Minimum withdrawal amount is $5.00")

        balance_before = profile.account_balance
        profile.account_balance -= amount
        profile.save()

        transaction_record = AccountTransaction.objects.create(
            user=user,
            transaction_type='withdrawal',
            amount=amount,
            balance_before=balance_before,
            balance_after=profile.account_balance,
            status='pending',  # Will be marked 'completed' when processed
            description=f"Withdrawal to {withdrawal_method}",
            notes=notes
        )

        logger.info(f"Withdrawal initiated for {user.username}: ${amount} to {withdrawal_method}")

        # TODO: Integrate with payment processors
        # For now, admin will process manually

        return (True, transaction_record, "Withdrawal request submitted successfully")

    @staticmethod
    @transaction.atomic
    def add_funds(user, amount, description, transaction_type='deposit'):
        """
        Generic helper to credit funds to a user's balance.
        Used internally by credit_referral_bonus and other credit operations.

        Args:
            user: User object
            amount: Decimal amount to add
            description: Human-readable description
            transaction_type: AccountTransaction type string (default 'deposit')

        Returns:
            AccountTransaction object
        """
        profile = user.profile
        amount = Decimal(str(amount))
        balance_before = profile.account_balance
        profile.account_balance += amount
        profile.low_balance_alert_sent = False  # Reset alert — balance is going up
        profile.save()

        transaction_record = AccountTransaction.objects.create(
            user=user,
            transaction_type=transaction_type,
            amount=amount,
            balance_before=balance_before,
            balance_after=profile.account_balance,
            status='completed',
            description=description,
        )

        logger.info(
            f"Added ${amount} ({transaction_type}) to {user.username}'s balance. "
            f"New balance: ${profile.account_balance}"
        )
        return transaction_record

    @staticmethod
    def credit_referral_bonus(new_user, deposit_amount=None):
        """
        Called after every deposit by a referred user.
        Credits $10 to BOTH the new user AND their referrer, but ONLY when
        ALL 3 conditions are met:
          1. new_user was referred (has referred_by set on their profile)
          2. new_user has auto_pay enabled
          3. deposit_amount is $50 or more

        Safe to call multiple times — referral_bonus_paid flag prevents double-crediting.

        Args:
            new_user: User object who just made a deposit
            deposit_amount: Decimal (or numeric) amount of this deposit

        Returns:
            bool: True if bonus was credited, False if skipped or failed
        """
        REFERRAL_BONUS = Decimal('10.00')
        MIN_DEPOSIT = Decimal('50.00')

        try:
            profile = new_user.profile

            # Guard: already paid out — skip silently, never credit twice
            if profile.referral_bonus_paid:
                return False

            # CONDITION 1: Must have been referred via a referral code at registration
            if not profile.referred_by:
                logger.debug(f"Referral bonus skipped for {new_user.username}: no referrer linked")
                return False

            # CONDITION 2: Must have auto-pay enabled (shows genuine commitment to the platform)
            if not profile.auto_pay_enabled:
                logger.debug(
                    f"Referral bonus skipped for {new_user.username}: auto-pay not enabled"
                )
                return False

            # CONDITION 3: This deposit must be $50 or more
            if deposit_amount is None or Decimal(str(deposit_amount)) < MIN_DEPOSIT:
                logger.debug(
                    f"Referral bonus skipped for {new_user.username}: "
                    f"deposit ${deposit_amount} is below ${MIN_DEPOSIT} minimum"
                )
                return False

            # All 3 conditions met — credit both users atomically
            referrer_profile = profile.referred_by

            with transaction.atomic():
                # Credit the NEW USER — welcome bonus
                BalanceService.add_funds(
                    user=new_user,
                    amount=REFERRAL_BONUS,
                    description=f'Welcome referral bonus — referred by {referrer_profile.user.username}',
                    transaction_type='referral_bonus',
                )

                # Credit the REFERRER — their friend qualified
                BalanceService.add_funds(
                    user=referrer_profile.user,
                    amount=REFERRAL_BONUS,
                    description=f'Referral bonus — {new_user.username} qualified!',
                    transaction_type='referral_bonus',
                )

                # Update referrer's running total
                referrer_profile.referral_bonus_earned += REFERRAL_BONUS
                referrer_profile.save()

                # Mark as paid — this flag prevents any future crediting
                profile.referral_bonus_paid = True
                profile.save()

            # Send bonus emails — non-blocking, never fail the payment if email fails
            try:
                from core.email_utils import (
                    send_referral_welcome_bonus_email,
                    send_referral_bonus_earned_email,
                )
                send_referral_welcome_bonus_email(new_user, referrer_profile.user)
                send_referral_bonus_earned_email(referrer_profile.user, new_user)
            except Exception as e:
                logger.error(f"Failed to send referral bonus emails: {e}")

            logger.info(
                f"Referral bonus credited: {new_user.username} and "
                f"{referrer_profile.user.username} each received ${REFERRAL_BONUS}"
            )
            return True

        except Exception as e:
            logger.error(f"Error in credit_referral_bonus for {new_user.username}: {e}")
            return False

    @staticmethod
    def has_sufficient_balance(user, amount):
        """Check if user has sufficient balance for a given amount."""
        return user.profile.account_balance >= Decimal(str(amount))

    @staticmethod
    def get_balance(user):
        """Return user's current account balance."""
        return user.profile.account_balance


# ============================================================================
# SEASON PREPAY & AUTO-PAY FUNCTIONS (Standalone)
# ============================================================================

def auto_deduct_weekly_fee(user, week, team):
    """
    Automatically deduct weekly fee from user's account balance
    Called when user with auto_pay_enabled makes picks

    Args:
        user: User object
        week: Week object
        team: Team object

    Returns:
        tuple: (success: bool, payment: WeeklyPayment or None, message: str)
    """
    try:
        profile = user.profile
        weekly_fee = Decimal(str(team.weekly_fee))

        # Check if auto-pay is enabled
        if not profile.auto_pay_enabled:
            return (False, None, "Auto-pay is not enabled for this account.")

        # Check if already paid for this week
        existing_payment = WeeklyPayment.objects.filter(
            user=user,
            week=week,
            status='completed'
        ).first()

        if existing_payment:
            return (True, existing_payment, "Already paid for this week.")

        # Check if same as last auto-payment week (prevent double charging)
        if profile.last_auto_payment_week == week:
            return (False, None, "Already auto-paid for this week.")

        # Check balance
        if profile.account_balance < weekly_fee:
            return (
                False,
                None,
                f"Insufficient balance (${profile.account_balance}). "
                f"Weekly fee is ${weekly_fee}. Please add funds."
            )

        # Process auto-payment
        with transaction.atomic():
            # Deduct from balance
            balance_before = profile.account_balance
            profile.account_balance -= weekly_fee
            profile.prepay_weeks_remaining = max(0, profile.prepay_weeks_remaining - 1)
            profile.last_auto_payment_week = week

            # Check and update low balance alert
            if profile.account_balance < profile.low_balance_threshold:
                if not profile.low_balance_alert_sent:
                    profile.low_balance_alert_sent = True
                    profile.last_low_balance_alert = timezone.now()
                    # Note: Send email in separate async task
            else:
                # Reset alert if balance is back above threshold
                profile.low_balance_alert_sent = False

            profile.save()

            # Create transaction record
            AccountTransaction.objects.create(
                user=user,
                transaction_type='weekly_payment',
                amount=weekly_fee,
                balance_before=balance_before,
                balance_after=profile.account_balance,
                description=f'Week {week.week_number} auto-payment - {team.name}',
                status='completed',
                week=week
            )

            # Create weekly payment record
            payment = WeeklyPayment.objects.create(
                user=user,
                week=week,
                amount=weekly_fee,
                payment_method='balance',
                status='completed',
                stripe_payment_intent_id=f'auto_pay_{week.id}_{user.id}',
                paid_at=timezone.now()
            )

            logger.info(
                f"Auto-pay successful: {user.username} - Week {week.week_number} - "
                f"${weekly_fee} - New balance: ${profile.account_balance}"
            )

            return (
                True,
                payment,
                f"Auto-payment successful! ${weekly_fee} deducted from your balance. "
                f"New balance: ${profile.account_balance}"
            )

    except UserProfile.DoesNotExist:
        logger.error(f"UserProfile not found for user {user.username}")
        return (False, None, "Account error. Please contact support.")
    except Exception as e:
        logger.error(f"Auto-deduct error for {user.username}: {str(e)}")
        return (False, None, "An error occurred processing your payment. Please try again.")


def complete_season_prepay(user, amount_paid, weeks_covered, team):
    """
    Called after successful season prepayment to set up auto-pay

    Args:
        user: User object
        amount_paid: Decimal amount paid
        weeks_covered: int number of weeks covered
        team: Team object

    Returns:
        bool: Success status
    """
    try:
        profile = user.profile
        amount_decimal = Decimal(str(amount_paid))

        with transaction.atomic():
            # Add to account balance
            balance_before = profile.account_balance
            profile.account_balance += amount_decimal

            # Enable auto-pay
            profile.auto_pay_enabled = True
            profile.payment_preference = 'season'
            profile.prepay_weeks_remaining = weeks_covered
            profile.onboarding_completed = True
            profile.save()

            # Create transaction record
            AccountTransaction.objects.create(
                user=user,
                transaction_type='deposit',
                amount=amount_decimal,
                balance_before=balance_before,
                balance_after=profile.account_balance,
                description=f'Season prepay - {weeks_covered} weeks - {team.name}',
                status='completed',
            )

            logger.info(
                f"Season prepay completed: {user.username} - "
                f"${amount_paid} - {weeks_covered} weeks"
            )

        return True

    except Exception as e:
        logger.error(f"Season prepay error for {user.username}: {str(e)}")
        return False


def complete_custom_prepay(user, amount_paid, team):
    """
    Called after successful custom amount deposit

    Args:
        user: User object
        amount_paid: Decimal amount paid
        team: Team object

    Returns:
        bool: Success status
    """
    try:
        profile = user.profile
        amount_decimal = Decimal(str(amount_paid))

        with transaction.atomic():
            # Add to account balance
            balance_before = profile.account_balance
            profile.account_balance += amount_decimal

            # Enable auto-pay
            profile.auto_pay_enabled = True
            profile.payment_preference = 'custom'
            profile.onboarding_completed = True

            # Calculate weeks covered (approximate)
            weekly_fee = Decimal(str(team.weekly_fee))
            weeks_covered = int(amount_decimal / weekly_fee)
            profile.prepay_weeks_remaining = weeks_covered

            profile.save()

            # Create transaction record
            AccountTransaction.objects.create(
                user=user,
                transaction_type='deposit',
                amount=amount_decimal,
                balance_before=balance_before,
                balance_after=profile.account_balance,
                description=f'Custom prepay - ${amount_paid} - {team.name}',
                status='completed',
            )

            logger.info(
                f"Custom prepay completed: {user.username} - ${amount_paid}"
            )

        return True

    except Exception as e:
        logger.error(f"Custom prepay error for {user.username}: {str(e)}")
        return False


def get_balance_status(user, team):
    """
    Get user's current balance status and payment info

    Args:
        user: User object
        team: Team object

    Returns:
        dict with balance info
    """
    try:
        profile = user.profile
        weekly_fee = Decimal(str(team.weekly_fee))

        weeks_remaining_by_balance = int(profile.account_balance / weekly_fee) if weekly_fee > 0 else 0

        return {
            'balance': profile.account_balance,
            'auto_pay_enabled': profile.auto_pay_enabled,
            'payment_preference': profile.payment_preference,
            'prepay_weeks_remaining': profile.prepay_weeks_remaining,
            'weeks_remaining_by_balance': weeks_remaining_by_balance,
            'has_sufficient_funds': profile.account_balance >= weekly_fee,
            'low_balance_warning': profile.account_balance < profile.low_balance_threshold,
            'weekly_fee': weekly_fee,
        }

    except Exception as e:
        logger.error(f"Balance status error for {user.username}: {str(e)}")
        return None
