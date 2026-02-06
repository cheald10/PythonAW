import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Pick4baseball.settings')
django.setup()

from core.models import User, Team, TeamMember, Week
from django.utils import timezone
from datetime import timedelta

user = User.objects.get(username='Real_cheald10')

team, team_created = Team.objects.get_or_create(
    name='Test Balance Team',
    defaults={
        'captain': user,
        'weekly_fee': 10.00,
        'season_year': 2026,
        'join_code': 'TEST123',
        'is_active': True
    }
)

member, member_created = TeamMember.objects.get_or_create(
    user=user,
    team=team,
    defaults={'status': 'active'}
)

week, week_created = Week.objects.get_or_create(
    week_number=1,
    season_year=2026,
    defaults={
        'saturday_date': timezone.now().date(),
        'deadline_utc': timezone.now() + timedelta(days=2),
        'is_active': True
    }
)

print(f"✅ Team: {team.name} ({'created' if team_created else 'exists'})")
print(f"✅ Member: {member.status} ({'added' if member_created else 'exists'})")
print(f"✅ Week: {week.week_number} ({'created' if week_created else 'exists'})")
print(f"\n🎯 Visit /payments/ to test Pay with Balance!")