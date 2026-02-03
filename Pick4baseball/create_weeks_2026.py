"""
2026 MLB Season Week Creation Script
Baseball Pick 4 App

Creates all 26 weeks for the 2026 MLB season
UPDATED: Week 16 (All-Star week) IS INCLUDED - Saturday games occur

Run this script via Django shell:
    python manage.py shell < create_weeks_2026.py

Or manually:
    python manage.py shell
    exec(open('create_weeks_2026.py').read())
"""

from core.models import Week, Team
from datetime import date, datetime
from django.utils import timezone

# 2026 MLB Season Saturdays (ALL 26 weeks - including All-Star week)
saturdays_2026 = [
    date(2026, 3, 28),   # Week 1 - Opening Week
    date(2026, 4, 4),    # Week 2
    date(2026, 4, 11),   # Week 3
    date(2026, 4, 18),   # Week 4
    date(2026, 4, 25),   # Week 5
    date(2026, 5, 2),    # Week 6
    date(2026, 5, 9),    # Week 7
    date(2026, 5, 16),   # Week 8
    date(2026, 5, 23),   # Week 9
    date(2026, 5, 30),   # Week 10
    date(2026, 6, 6),    # Week 11
    date(2026, 6, 13),   # Week 12
    date(2026, 6, 20),   # Week 13
    date(2026, 6, 27),   # Week 14
    date(2026, 7, 4),    # Week 15 - July 4th Weekend
    date(2026, 7, 11),   # Week 16 - All-Star Week (NORMAL - Games occur!)
    date(2026, 7, 18),   # Week 17 - Post All-Star
    date(2026, 7, 25),   # Week 18
    date(2026, 8, 1),    # Week 19
    date(2026, 8, 8),    # Week 20
    date(2026, 8, 15),   # Week 21
    date(2026, 8, 22),   # Week 22
    date(2026, 8, 29),   # Week 23
    date(2026, 9, 5),    # Week 24
    date(2026, 9, 12),   # Week 25
    date(2026, 9, 26),   # Week 26 - Final Regular Season Week
]

print("=" * 80)
print("BASEBALL PICK 4 - 2026 SEASON WEEK CREATION")
print("=" * 80)
print(f"\nTotal weeks to create: {len(saturdays_2026)}")
print(f"Season start: {saturdays_2026[0]}")
print(f"Season end: {saturdays_2026[-1]}")
print(f"\nNote: Week 16 (July 11) IS INCLUDED - All-Star break is Tue-Thu only\n")

# Get all teams (or specify a specific team)
teams = Team.objects.all()

if not teams:
    print("❌ ERROR: No teams found in database!")
    print("   Create at least one team before running this script.")
    exit()

print(f"Creating weeks for {teams.count()} team(s):\n")

for team in teams:
    print(f"\n{'=' * 80}")
    print(f"TEAM: {team.name}")
    print(f"{'=' * 80}\n")
    
    weeks_created = 0
    weeks_existing = 0
    
    for week_num, saturday in enumerate(saturdays_2026, start=1):
        # Deadline is Saturday at 11 AM CST (17:00 UTC in standard time)
        # Note: Adjust for DST if needed
        deadline = timezone.make_aware(datetime(
            saturday.year,
            saturday.month,
            saturday.day,
            17, 0, 0  # 11 AM CST = 5 PM UTC (standard time)
        ))
        
        # Create or get the week
        week, created = Week.objects.get_or_create(
            week_number=week_num,
            season_year=2026,
            team=team,
            defaults={
                'saturday_date': saturday,
                'deadline_utc': deadline,
                'is_active': False,
                'is_completed': False
            }
        )
        
        if created:
            weeks_created += 1
            status = "✅ CREATED"
            
            # Special notes for certain weeks
            note = ""
            if week_num == 1:
                note = " (Opening Week - Early registration allowed)"
            elif week_num == 15:
                note = " (July 4th Weekend)"
            elif week_num == 16:
                note = " (All-Star Week - NORMAL WEEK)"
            elif week_num == 17:
                note = " (Post All-Star)"
            elif week_num == 26:
                note = " (Final Regular Season Week)"
            
            print(f"{status} Week {week_num:2d}: {saturday}{note}")
        else:
            weeks_existing += 1
            print(f"⚠️  EXISTS Week {week_num:2d}: {saturday}")
    
    print(f"\n{'-' * 80}")
    print(f"Summary for {team.name}:")
    print(f"  ✅ Created: {weeks_created} weeks")
    print(f"  ⚠️  Existing: {weeks_existing} weeks")
    print(f"  📊 Total: {weeks_created + weeks_existing} weeks")

# Final summary
print(f"\n{'=' * 80}")
print("CREATION COMPLETE")
print(f"{'=' * 80}\n")

total_weeks = Week.objects.filter(season_year=2026).count()
print(f"Total 2026 weeks in database: {total_weeks}")

# Show active weeks
active_weeks = Week.objects.filter(season_year=2026, is_active=True).count()
print(f"Active weeks: {active_weeks}")

# Show Week 1 details
week_1 = Week.objects.filter(season_year=2026, week_number=1).first()
if week_1:
    print(f"\n📅 WEEK 1 DETAILS:")
    print(f"   Date: {week_1.saturday_date}")
    print(f"   Deadline: {week_1.deadline_utc}")
    print(f"   Active: {week_1.is_active}")
    print(f"   Team: {week_1.team.name}")
    print(f"\n💡 To activate Week 1 for picks:")
    print(f"   Week.objects.filter(season_year=2026, week_number=1).update(is_active=True)")

# Show All-Star week details
week_16 = Week.objects.filter(season_year=2026, week_number=16).first()
if week_16:
    print(f"\n⭐ ALL-STAR WEEK DETAILS:")
    print(f"   Week: 16")
    print(f"   Date: {week_16.saturday_date}")
    print(f"   Status: NORMAL WEEK (not skipped)")
    print(f"   Note: All-Star Game is Tuesday July 15, Saturday games occur")

print(f"\n{'=' * 80}")
print("✅ 2026 SEASON READY!")
print(f"{'=' * 80}")
print("\nNext steps:")
print("1. Activate Week 1 on March 22, 2026 (Sunday before opening day)")
print("2. Set up cron job for automated Sunday scoring")
print("3. Communicate opening date to users")
print("4. Test rainout/doubleheader handling")
print("\n")
