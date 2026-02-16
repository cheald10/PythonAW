"""
Low Balance Alert Management Command
Save to: core/management/commands/check_low_balances.py
"""

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from core.models import UserProfile
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check for users with low balance and send email alerts'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without sending emails (test mode)',
        )
        parser.add_argument(
            '--threshold',
            type=float,
            default=30.00,
            help='Balance threshold for alerts (default: $30)',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        threshold = Decimal(str(options['threshold']))
        
        self.stdout.write(self.style.WARNING(
            f"Checking for low balances (threshold: ${threshold})"
        ))
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No emails will be sent"))
        
        # Find users with auto-pay enabled and low balance
        low_balance_users = UserProfile.objects.filter(
            auto_pay_enabled=True,
            account_balance__lt=threshold,
            account_balance__gt=0,
            low_balance_alert_sent=False  # Only send once until they add funds
        ).select_related('user')
        
        count = low_balance_users.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS("No users with low balance found."))
            return
        
        self.stdout.write(
            self.style.WARNING(f"Found {count} user(s) with low balance")
        )
        
        sent_count = 0
        
        for profile in low_balance_users:
            user = profile.user
            balance = profile.account_balance
            weeks_remaining = int(balance / 10) if balance > 0 else 0
            
            self.stdout.write(
                f"  • {user.username} ({user.email}): ${balance} "
                f"(~{weeks_remaining} weeks remaining)"
            )
            
            if not dry_run:
                try:
                    # Send email alert
                    send_mail(
                        subject='⚾ Low Balance Alert - Baseball Pick 4',
                        message=f'''
Hi {user.first_name or user.username},

Your Baseball Pick 4 account balance is running low: ${balance}

This will cover approximately {weeks_remaining} more week(s).

To avoid missing future weeks, please add funds to your account:
https://cheald10.pythonanywhere.com/payments/

Current Balance: ${balance}
Suggested Deposit: ${30 - balance + 10} (to cover at least 4 more weeks)

You can add any amount you're comfortable with - we just wanted to give you a heads up!

Questions? Reply to this email or contact us at support@baseballpick4.com

Thanks for playing!
The Baseball Pick 4 Team
                        ''',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                    
                    # Mark alert as sent
                    profile.low_balance_alert_sent = True
                    profile.save(update_fields=['low_balance_alert_sent'])
                    
                    sent_count += 1
                    
                    self.stdout.write(
                        self.style.SUCCESS(f"    ✓ Email sent to {user.email}")
                    )
                    
                except Exception as e:
                    logger.error(f"Failed to send email to {user.email}: {str(e)}")
                    self.stdout.write(
                        self.style.ERROR(f"    ✗ Failed to send email: {str(e)}")
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(f"    [DRY RUN] Would send email to {user.email}")
                )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"\n[DRY RUN] Would have sent {count} email(s)")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"\n✓ Successfully sent {sent_count} low balance alert(s)")
            )