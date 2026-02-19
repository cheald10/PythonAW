from django.db import migrations, models
import django.db.models.deletion
import secrets
import string


def generate_referral_codes(apps, schema_editor):
    UserProfile = apps.get_model('core', 'UserProfile')
    
    def make_code():
        chars = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(chars) for _ in range(8))
    
    existing_codes = set()
    for profile in UserProfile.objects.all():
        code = make_code()
        while code in existing_codes:
            code = make_code()
        profile.referral_code = code
        existing_codes.add(code)
        profile.save()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_alter_userprofile_preferred_payout_method'),
    ]

    operations = [
        # Tell Django these fields exist in the DB already - don't touch the DB
        migrations.SeparateDatabaseAndState(
            database_operations=[],  # Do nothing in DB - columns already there
            state_operations=[
                migrations.AddField(
                    model_name='userprofile',
                    name='referral_code',
                    field=models.CharField(blank=True, default='', max_length=10),
                ),
                migrations.AddField(
                    model_name='userprofile',
                    name='referred_by',
                    field=models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='referrals',
                        to='core.userprofile',
                    ),
                ),
                migrations.AddField(
                    model_name='userprofile',
                    name='referral_bonus_earned',
                    field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
                ),
                migrations.AddField(
                    model_name='userprofile',
                    name='referral_bonus_paid',
                    field=models.BooleanField(default=False),
                ),
            ]
        ),
        # Now backfill codes (Django state knows about the field now)
        migrations.RunPython(generate_referral_codes, migrations.RunPython.noop),
        # Now enforce unique constraint in the actual DB
        migrations.AlterField(
            model_name='userprofile',
            name='referral_code',
            field=models.CharField(
                blank=True, max_length=10, unique=True,
                help_text='Unique code to share with friends'
            ),
        ),
    ]