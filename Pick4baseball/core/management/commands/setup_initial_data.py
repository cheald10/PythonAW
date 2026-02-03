"""
Baseball Pick 4 - Initial Data Setup Script
Creates essential data for testing and development

Usage:
    python manage.py setup_initial_data

Created: January 22, 2026
Sprint: Sprint 2, Days 6-8
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
User = get_user_model()
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from core.models import (
    UserProfile,
    Team,
    TeamMember,
    Week,
    PickCategory,
    MLBPlayer,
)


class Command(BaseCommand):
    help = 'Set up initial data for Baseball Pick 4'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-categories',
            action='store_true',
            help='Skip creating pick categories',
        )
        parser.add_argument(
            '--skip-week',
            action='store_true',
            help='Skip creating sample week',
        )
        parser.add_argument(
            '--skip-team',
            action='store_true',
            help='Skip creating sample team',
        )
        parser.add_argument(
            '--skip-players',
            action='store_true',
            help='Skip creating sample players',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('Baseball Pick 4 - Initial Data Setup'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')

        # Create Pick Categories
        if not options['skip_categories']:
            self.create_pick_categories()

        # Create Sample Week
        if not options['skip_week']:
            self.create_sample_week()

        # Create Sample Players
        if not options['skip_players']:
            self.create_sample_players()

        # Create Sample Team
        if not options['skip_team']:
            self.create_sample_team()

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('✓ Initial data setup complete!'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('Next steps:'))
        self.stdout.write('  1. Login to admin: /admin/')
        self.stdout.write('  2. Check the Pick Categories')
        self.stdout.write('  3. Review the sample week')
        self.stdout.write('  4. Test making picks!')
        self.stdout.write('')

    def create_pick_categories(self):
        """Create the 4 pick categories"""
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('Creating Pick Categories...'))

        categories = [
            {
                'code': '2H',
                'name': '2 Hits',
                'description': 'Player gets 2 or more hits in any Saturday game',
                'requires_pitcher': False,
                'display_order': 1,
                'icon': 'fa-baseball-ball',
                'color': '#0051BA',
            },
            {
                'code': 'HR',
                'name': 'Home Run',
                'description': 'Player hits a home run in any Saturday game',
                'requires_pitcher': False,
                'display_order': 2,
                'icon': 'fa-rocket',
                'color': '#C8102E',
            },
            {
                'code': 'SWP',
                'name': 'Starting Winning Pitcher',
                'description': 'Starting pitcher gets the win on Saturday',
                'requires_pitcher': True,
                'display_order': 3,
                'icon': 'fa-trophy',
                'color': '#00843D',
            },
            {
                'code': 'S',
                'name': 'Save',
                'description': 'Pitcher records a save in any Saturday game',
                'requires_pitcher': True,
                'display_order': 4,
                'icon': 'fa-shield-alt',
                'color': '#FFB81C',
            },
        ]

        created_count = 0
        for cat_data in categories:
            category, created = PickCategory.objects.get_or_create(
                code=cat_data['code'],
                defaults=cat_data
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Created: {category.code} - {category.name}')
                )
                created_count += 1
            else:
                self.stdout.write(
                    self.style.WARNING(f'  • Already exists: {category.code} - {category.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\n  Total: {created_count} categories created')
        )

    def create_sample_week(self):
        """Create a sample week for testing"""
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('Creating Sample Week...'))

        # Get next Saturday
        today = timezone.now().date()
        days_until_saturday = (5 - today.weekday()) % 7
        if days_until_saturday == 0:
            days_until_saturday = 7  # Next Saturday if today is Saturday

        saturday = today + timedelta(days=days_until_saturday)

        # Deadline: Saturday at 11 AM CST (5 PM UTC)
        deadline = timezone.datetime.combine(
            saturday,
            timezone.datetime.min.time()
        ).replace(hour=17, minute=0, second=0, microsecond=0)
        deadline = timezone.make_aware(deadline, timezone.utc)

        week_data = {
            'week_number': 1,
            'season_year': 2026,
            'saturday_date': saturday,
            'deadline_utc': deadline,
            'is_active': True,
            'is_completed': False,
        }

        week, created = Week.objects.get_or_create(
            week_number=week_data['week_number'],
            season_year=week_data['season_year'],
            defaults=week_data
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'  ✓ Created: Week {week.week_number}, {week.season_year}')
            )
            self.stdout.write(f'    Saturday: {week.saturday_date}')
            self.stdout.write(f'    Deadline: {week.deadline_utc} UTC')
        else:
            self.stdout.write(
                self.style.WARNING(f'  • Already exists: Week {week.week_number}, {week.season_year}')
            )

    def create_sample_players(self):
        """Create sample MLB players for testing"""
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('Creating Sample Players...'))

        players = [
            # Batters
            {
                'mlb_player_id': 660271,
                'first_name': 'Aaron',
                'last_name': 'Judge',
                'full_name': 'Aaron Judge',
                'team_name': 'New York Yankees',
                'team_abbreviation': 'NYY',
                'position': 'OF',
                'is_pitcher': False,
                'is_two_way_player': False,
                'jersey_number': 99,
            },
            {
                'mlb_player_id': 592450,
                'first_name': 'Mookie',
                'last_name': 'Betts',
                'full_name': 'Mookie Betts',
                'team_name': 'Los Angeles Dodgers',
                'team_abbreviation': 'LAD',
                'position': 'OF',
                'is_pitcher': False,
                'is_two_way_player': False,
                'jersey_number': 50,
            },
            {
                'mlb_player_id': 665487,
                'first_name': 'Shohei',
                'last_name': 'Ohtani',
                'full_name': 'Shohei Ohtani',
                'team_name': 'Los Angeles Dodgers',
                'team_abbreviation': 'LAD',
                'position': 'DH',
                'is_pitcher': False,
                'is_two_way_player': True,
                'jersey_number': 17,
            },
            {
                'mlb_player_id': 608070,
                'first_name': 'Freddie',
                'last_name': 'Freeman',
                'full_name': 'Freddie Freeman',
                'team_name': 'Los Angeles Dodgers',
                'team_abbreviation': 'LAD',
                'position': '1B',
                'is_pitcher': False,
                'is_two_way_player': False,
                'jersey_number': 5,
            },
            # Pitchers
            {
                'mlb_player_id': 605483,
                'first_name': 'Gerrit',
                'last_name': 'Cole',
                'full_name': 'Gerrit Cole',
                'team_name': 'New York Yankees',
                'team_abbreviation': 'NYY',
                'position': 'SP',
                'is_pitcher': True,
                'is_two_way_player': False,
                'jersey_number': 45,
            },
            {
                'mlb_player_id': 545333,
                'first_name': 'Clayton',
                'last_name': 'Kershaw',
                'full_name': 'Clayton Kershaw',
                'team_name': 'Los Angeles Dodgers',
                'team_abbreviation': 'LAD',
                'position': 'SP',
                'is_pitcher': True,
                'is_two_way_player': False,
                'jersey_number': 22,
            },
            {
                'mlb_player_id': 621107,
                'first_name': 'Josh',
                'last_name': 'Hader',
                'full_name': 'Josh Hader',
                'team_name': 'Houston Astros',
                'team_abbreviation': 'HOU',
                'position': 'RP',
                'is_pitcher': True,
                'is_two_way_player': False,
                'jersey_number': 71,
            },
            {
                'mlb_player_id': 663776,
                'first_name': 'Emmanuel',
                'last_name': 'Clase',
                'full_name': 'Emmanuel Clase',
                'team_name': 'Cleveland Guardians',
                'team_abbreviation': 'CLE',
                'position': 'RP',
                'is_pitcher': True,
                'is_two_way_player': False,
                'jersey_number': 48,
            },
        ]

        created_count = 0
        for player_data in players:
            player, created = MLBPlayer.objects.get_or_create(
                mlb_player_id=player_data['mlb_player_id'],
                defaults=player_data
            )

            if created:
                icon = '⚾' if not player.is_pitcher else '🎯'
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ Created: {icon} {player.full_name} ({player.team_abbreviation})')
                )
                created_count += 1
            else:
                self.stdout.write(
                    self.style.WARNING(f'  • Already exists: {player.full_name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\n  Total: {created_count} players created')
        )

    def create_sample_team(self):
        """Create a sample team for testing"""
        self.stdout.write('')
        self.stdout.write(self.style.HTTP_INFO('Creating Sample Team...'))

        # Get or create a test user to be captain
        captain, created = User.objects.get_or_create(
            username='teamcaptain',
            defaults={
                'email': 'captain@example.com',
                'first_name': 'Team',
                'last_name': 'Captain',
                'is_staff': False,
            }
        )

        if created:
            captain.set_password('TestPass123!')
            captain.save()
            self.stdout.write(
                self.style.SUCCESS('  ✓ Created test captain user: teamcaptain')
            )
            self.stdout.write('    Password: TestPass123!')

        # Create or get UserProfile for captain
        profile, created = UserProfile.objects.get_or_create(
            user=captain,
            defaults={
                'timezone': 'America/Chicago',
                'preferred_payout_method': 'manual',
            }
        )

        # Create sample team
        team_data = {
            'name': 'Test Team 2026',
            'description': 'Sample team for testing Baseball Pick 4',
            'captain': captain,
            'weekly_fee': Decimal('5.00'),
            'season_year': 2026,
            'is_public': True,
            'is_active': True,
            'min_members': 3,
            'auto_payout_enabled': False,
        }

        team, created = Team.objects.get_or_create(
            name=team_data['name'],
            defaults=team_data
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'  ✓ Created: {team.name}')
            )
            self.stdout.write(f'    Captain: {team.captain.username}')
            self.stdout.write(f'    Weekly Fee: ${team.weekly_fee}')
            self.stdout.write(f'    Join Code: {team.join_code}')

            # Create captain as team member
            TeamMember.objects.get_or_create(
                team=team,
                user=captain,
                defaults={
                    'role': 'captain',
                    'status': 'active',
                }
            )
            self.stdout.write('    ✓ Captain added as member')
        else:
            self.stdout.write(
                self.style.WARNING(f'  • Already exists: {team.name}')
            )
            self.stdout.write(f'    Join Code: {team.join_code}')
