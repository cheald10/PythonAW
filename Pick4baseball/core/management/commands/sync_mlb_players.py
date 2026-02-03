"""
Baseball Pick 4 - Sync MLB Players Command
Management command to sync player data from MLB Stats API

Usage:
    python manage.py sync_mlb_players
    python manage.py sync_mlb_players --season 2026
    python manage.py sync_mlb_players --limit 3  # First 3 teams only

Created: January 22, 2026
Sprint: Sprint 2, Days 6-8
"""

from django.core.management.base import BaseCommand
from datetime import datetime
from core.mlb_api_service import MLBAPIService


class Command(BaseCommand):
    help = 'Sync MLB player data from MLB Stats API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--season',
            type=int,
            default=None,
            help='Season year (default: current year)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit to first N teams (for testing)',
        )
        parser.add_argument(
            '--team',
            type=int,
            default=None,
            help='Sync single team by ID',
        )

    def handle(self, *args, **options):
        season = options['season'] or datetime.now().year
        limit = options['limit']
        team_id = options['team']
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(self.style.SUCCESS('MLB Player Sync'))
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write(f'Season: {season}')
        
        if limit:
            self.stdout.write(f'Limiting to first {limit} teams')
        if team_id:
            self.stdout.write(f'Syncing single team: {team_id}')
        
        self.stdout.write(self.style.SUCCESS('=' * 70))
        self.stdout.write('')
        
        # Initialize service
        service = MLBAPIService()
        
        # Sync players
        if team_id:
            # Sync single team
            self.stdout.write(f"Syncing team ID: {team_id}")
            roster = service.get_team_roster(team_id, season)
            self.stdout.write(f"Found {len(roster)} players")
            
            for player_entry in roster:
                service.sync_player_to_db(player_entry)
            
            self.stdout.write(self.style.SUCCESS(f'\n✓ Team {team_id} synced!'))
        else:
            # Sync all teams
            stats = service.sync_all_players(season=season, limit_teams=limit)
            
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('=' * 70))
            self.stdout.write(self.style.SUCCESS('✓ Sync Complete!'))
            self.stdout.write(self.style.SUCCESS('=' * 70))
            self.stdout.write(f'Teams: {stats["teams_processed"]}')
            self.stdout.write(f'Players: {stats["players_updated"]}')
            self.stdout.write(f'Errors: {stats["errors"]}')
            self.stdout.write(self.style.SUCCESS('=' * 70))
        
        self.stdout.write('')
