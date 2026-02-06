"""
Account Balance Service
Handles all balance operations with proper transaction handling and audit trails.
"""
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from core.models import UserProfile, AccountTransaction, WeeklyPayment
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
    def get_balance(user):
        """Get user's current account balance"""
        return user.profile.account_balance
    
    @staticmethod
    def has_sufficient_balance(user, amount):
        """Check if user has sufficient balance"""
        return user.profile.account_balance >= Decimal(str(amount))