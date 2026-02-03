"""
Baseball Pick 4 - Update MLB Players Command
Updates existing player data and handles roster changes

Usage:
    python manage.py update_mlb_players
    python manage.py update_mlb_players --full  # Re-sync all teams
    python manage.py update_mlb_players --inactive  # Mark inactive players

Created: January 22, 2026
Sprint: Sprint 2, Days 6-8
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
from core.mlb_api_service import MLBAPIService
from core.models import MLBPlayer


class Command(BaseCommand):
    help = 'Update MLB player data (injuries, trades, roster changes)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--full',
            action='store_true',
            help='Full re-sync of all players',
        )
        parser.add_argument(
            '--inactive',
            action='store_true',
            help='Mark players not on active rosters as inactive',
        )
        parser.add_argument(
            '--season',
            type=int,
            default=None,
            help='Season year (default: current year)',
        )

    def handle(self, *args, **options):
        season = options['season'] or datetime.now().year
        full_sync = options['full']
        check_inactive = options['inactive']
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('MLB Player Update'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Season: {season}')
        self.stdout.write(f'Full Sync: {full_sync}')
        self.stdout.write(f'Check Inactive: {check_inactive}')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        
        service = MLBAPIService()
        
        if full_sync:
            # Full re-sync
            self.stdout.write('Performing full re-sync...\n')
            stats = service.sync_all_players(season=season)
            
            self.stdout.write(self.style.SUCCESS('✓ Full sync complete!'))
            self.stdout.write(f'Teams: {stats["teams_processed"]}')
            self.stdout.write(f'Players: {stats["players_updated"]}')
            
        else:
            # Quick update - only update players that exist in DB
            self.stdout.write('Performing quick update...\n')
            self.quick_update(service, season)
        
        if check_inactive:
            # Mark inactive players
            self.stdout.write('\nChecking for inactive players...')
            self.mark_inactive_players(service, season)
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('✓ Update Complete!'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
    
    def quick_update(self, service, season):
        """
        Quick update of existing players in database
        Updates team assignments, jersey numbers, active status
        """
        players = MLBPlayer.objects.filter(is_active=True)
        total = players.count()
        updated = 0
        
        self.stdout.write(f'Updating {total} active players...\n')
        
        # Group players by team to reduce API calls
        teams_to_check = set(players.values_list('mlb_team_id', flat=True))
        teams_to_check.discard(None)
        
        for team_id in teams_to_check:
            team_players = players.filter(mlb_team_id=team_id)
            self.stdout.write(f'Checking team {team_id} ({team_players.count()} players)...')
            
            # Get current roster
            roster = service.get_team_roster(team_id, season)
            roster_ids = {p['person']['id'] for p in roster}
            
            for player in team_players:
                if player.mlb_player_id in roster_ids:
                    # Player still on roster, update details
                    player_entry = next(
                        (p for p in roster if p['person']['id'] == player.mlb_player_id),
                        None
                    )
                    if player_entry:
                        service.sync_player_to_db(player_entry)
                        updated += 1
                else:
                    # Player not on roster anymore
                    self.stdout.write(
                        self.style.WARNING(f'  ⚠ {player.full_name} not on roster')
                    )
        
        self.stdout.write(self.style.SUCCESS(f'\n✓ Updated {updated} players'))
    
    def mark_inactive_players(self, service, season):
        """
        Mark players not on any active roster as inactive
        """
        # Get all active rosters
        teams = service.get_all_teams(season)
        all_active_ids = set()
        
        self.stdout.write(f'Checking {len(teams)} teams...\n')
        
        for team in teams:
            team_id = team.get('id')
            roster = service.get_team_roster(team_id, season)
            roster_ids = {p['person']['id'] for p in roster}
            all_active_ids.update(roster_ids)
        
        self.stdout.write(f'Found {len(all_active_ids)} active players across MLB')
        
        # Mark players not in active rosters as inactive
        inactive_count = MLBPlayer.objects.filter(
            is_active=True
        ).exclude(
            mlb_player_id__in=all_active_ids
        ).update(is_active=False)
        
        self.stdout.write(
            self.style.WARNING(f'✓ Marked {inactive_count} players as inactive')
        )
