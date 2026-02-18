"""
Low Balance Alert Management Command
Checks for users with auto-pay enabled and low balances, sends email alerts
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
            '--threshold',
            type=float,
            default=30.00,
            help='Balance threshold for alerts (default: $30)',
        )

    def handle(self, *args, **options):
        threshold = Decimal(str(options['threshold']))

        self.stdout.write(
            f"Checking for low balances (threshold: ${threshold})..."
        )

        # Find users with auto-pay enabled and low balance
        low_balance_users = UserProfile.objects.filter(
            auto_pay_enabled=True,
            account_balance__lt=threshold,
            account_balance__gt=0,
            low_balance_alert_sent=False
        ).select_related('user')

        count = low_balance_users.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("✓ No users with low balance found."))
            return

        self.stdout.write(f"Found {count} user(s) with low balance:\n")

        sent_count = 0
        failed_count = 0

        for profile in low_balance_users:
            user = profile.user
            balance = profile.account_balance
            weekly_fee = Decimal('10.00')
            weeks_remaining = int(balance / weekly_fee) if balance > 0 else 0

            self.stdout.write(f"  • {user.username} ({user.email}): ${balance} (~{weeks_remaining} weeks)")

            # Send email
            if self.send_low_balance_email(user, balance, weeks_remaining):
                # Mark alert as sent
                profile.low_balance_alert_sent = True
                profile.save(update_fields=['low_balance_alert_sent'])
                sent_count += 1
                self.stdout.write(self.style.SUCCESS(f"    ✓ Email sent"))
            else:
                failed_count += 1
                self.stdout.write(self.style.ERROR(f"    ✗ Email failed"))

        # Summary
        self.stdout.write("")
        if sent_count > 0:
            self.stdout.write(self.style.SUCCESS(f"✓ Sent {sent_count} alert(s)"))
        if failed_count > 0:
            self.stdout.write(self.style.ERROR(f"✗ Failed {failed_count} alert(s)"))

    def send_low_balance_email(self, user, balance, weeks_remaining):
        """Send low balance alert via Django email system"""
        try:
            site_url = getattr(settings, 'SITE_URL', 'https://cheald10.pythonanywhere.com')
            
            subject = f'⚠️ Low Balance Alert - {weeks_remaining} Week{"s" if weeks_remaining != 1 else ""} Remaining'
            
            message = f"""Hi {user.first_name or user.username},

Your Baseball Pick 4 account balance is running low!

Current Balance: ${balance}
Weeks Remaining: ~{weeks_remaining}

To avoid missing future weeks, please add funds to your account:
{site_url}/onboarding/custom-amount/

Suggested Amount: ${max(40 - float(balance), 10)}

You can manage your payment preferences in Account Settings:
{site_url}/account/settings/

Thanks for playing!
Baseball Pick 4 Team
"""
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            logger.info(f"Low balance alert sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Email error for {user.email}: {e}")
            return False
