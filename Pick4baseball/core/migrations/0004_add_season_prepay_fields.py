# Generated migration for Season Prepay & Auto-Pay feature
# To be placed in: core/migrations/

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_add_account_transaction_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='payment_preference',
            field=models.CharField(
                choices=[
                    ('weekly', 'Pay Week-to-Week'),
                    ('season', 'Full Season Prepay'),
                    ('custom', 'Custom Amount'),
                ],
                default='weekly',
                help_text='How user prefers to pay for weekly picks',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='auto_pay_enabled',
            field=models.BooleanField(
                default=False,
                help_text='Automatically deduct weekly fee from balance',
            ),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='onboarding_completed',
            field=models.BooleanField(
                default=False,
                help_text='Has user completed payment preference onboarding',
            ),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='prepay_weeks_remaining',
            field=models.IntegerField(
                default=0,
                help_text='Number of weeks covered by prepayment',
            ),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='last_auto_payment_week',
            field=models.ForeignKey(
                blank=True,
                help_text='Last week auto-payment was processed',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='auto_paid_users',
                to='core.week',
            ),
        ),
    ]