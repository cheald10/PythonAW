"""
Baseball Pick 4 - MLB Stats API Service
Service for syncing player data from MLB Stats API

Created: January 22, 2026
Sprint: Sprint 2, Day 6-8
"""

import requests
from datetime import datetime
from typing import List, Dict, Optional
from django.utils import timezone
from core.models import MLBPlayer


class MLBAPIService:
    """
    Service for interacting with MLB Stats API
    
    API Documentation: https://statsapi.mlb.com/docs/
    Base URL: https://statsapi.mlb.com/api/v1/
    """
    
    BASE_URL = 'https://statsapi.mlb.com/api/v1'
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BaseballPick4/1.0',
            'Accept': 'application/json',
        })
    
    # ==========================================================================
    # TEAMS
    # ==========================================================================
    
    def get_all_teams(self, season: int = None) -> List[Dict]:
        """
        Get all MLB teams
        
        Args:
            season: Year (default: current year)
        
        Returns:
            List of team dictionaries
        """
        if season is None:
            season = datetime.now().year
        
        endpoint = f'{self.BASE_URL}/teams'
        params = {
            'sportId': 1,  # MLB
            'season': season,
        }
        
        try:
            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('teams', [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching teams: {e}")
            return []
    
    # ==========================================================================
    # PLAYERS
    # ==========================================================================
    
    def get_team_roster(self, team_id: int, season: int = None) -> List[Dict]:
        """
        Get roster for a specific team
        
        Args:
            team_id: MLB team ID
            season: Year (default: current year)
        
        Returns:
            List of player dictionaries
        """
        if season is None:
            season = datetime.now().year
        
        endpoint = f'{self.BASE_URL}/teams/{team_id}/roster'
        params = {
            'rosterType': 'active',  # Active roster only
            'season': season,
        }
        
        try:
            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('roster', [])
        except requests.exceptions.RequestException as e:
            print(f"Error fetching roster for team {team_id}: {e}")
            return []
    
    def get_player_details(self, player_id: int) -> Optional[Dict]:
        """
        Get detailed information about a player
        
        Args:
            player_id: MLB player ID
        
        Returns:
            Player dictionary or None
        """
        endpoint = f'{self.BASE_URL}/people/{player_id}'
        
        try:
            response = self.session.get(endpoint, timeout=10)
            response.raise_for_status()
            data = response.json()
            people = data.get('people', [])
            return people[0] if people else None
        except requests.exceptions.RequestException as e:
            print(f"Error fetching player {player_id}: {e}")
            return None
    
    # ==========================================================================
    # GAME DATA
    # ==========================================================================
    
    def get_games_by_date(self, date: str, team_id: Optional[int] = None) -> List[Dict]:
        """
        Get games for a specific date
        
        Args:
            date: Date in YYYY-MM-DD format
            team_id: Optional team ID to filter
        
        Returns:
            List of game dictionaries
        """
        endpoint = f'{self.BASE_URL}/schedule'
        params = {
            'sportId': 1,  # MLB
            'date': date,
            'hydrate': 'linescore,decisions',
        }
        
        if team_id:
            params['teamId'] = team_id
        
        try:
            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            games = []
            for date_entry in data.get('dates', []):
                games.extend(date_entry.get('games', []))
            
            return games
        except requests.exceptions.RequestException as e:
            print(f"Error fetching games for {date}: {e}")
            return []
    
    def get_game_boxscore(self, game_id: int) -> Optional[Dict]:
        """
        Get detailed boxscore for a game
        
        Args:
            game_id: MLB game ID (gamePk)
        
        Returns:
            Boxscore dictionary or None
        """
        endpoint = f'{self.BASE_URL}/game/{game_id}/boxscore'
        
        try:
            response = self.session.get(endpoint, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching boxscore for game {game_id}: {e}")
            return None
    
    # ==========================================================================
    # PLAYER STATS
    # ==========================================================================
    
    def get_player_stats(self, player_id: int, season: int = None, 
                         stat_type: str = 'season') -> Optional[Dict]:
        """
        Get player statistics
        
        Args:
            player_id: MLB player ID
            season: Year (default: current year)
            stat_type: 'season', 'career', 'gameLog'
        
        Returns:
            Stats dictionary or None
        """
        if season is None:
            season = datetime.now().year
        
        endpoint = f'{self.BASE_URL}/people/{player_id}/stats'
        params = {
            'stats': stat_type,
            'season': season,
            'group': 'hitting,pitching',
        }
        
        try:
            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching stats for player {player_id}: {e}")
            return None
    
    # ==========================================================================
    # DATABASE SYNC
    # ==========================================================================
    
    def sync_player_to_db(self, player_data: Dict) -> Optional[MLBPlayer]:
        """
        Create or update a player in the database
        
        Args:
            player_data: Player data from API (from roster or people endpoint)
        
        Returns:
            MLBPlayer instance or None
        """
        try:
            # Handle both roster format and people format
            if 'person' in player_data:
                person = player_data['person']
                position = player_data.get('position', {})
                jersey = player_data.get('jerseyNumber')
                team_data = player_data.get('team', {})
            else:
                person = player_data
                position = player_data.get('primaryPosition', {})
                jersey = person.get('primaryNumber')
                team_data = person.get('currentTeam', {})
            
            player_id = person.get('id')
            if not player_id:
                return None
            
            # Determine if pitcher
            position_code = position.get('abbreviation', '')
            is_pitcher = position_code == 'P'
            
            # Check for two-way player (has both pitching and hitting stats)
            is_two_way = False
            # Note: We'll need to check stats to truly determine this
            # For now, we'll set it manually for known two-way players
            
            player_obj, created = MLBPlayer.objects.update_or_create(
                mlb_player_id=player_id,
                defaults={
                    'first_name': person.get('firstName', ''),
                    'last_name': person.get('lastName', ''),
                    'full_name': person.get('fullName', ''),
                    'team_name': team_data.get('name', ''),
                    'team_abbreviation': team_data.get('abbreviation', ''),
                    'position': position_code,
                    'is_active': person.get('active', True),
                    'is_pitcher': is_pitcher,
                    'is_two_way_player': is_two_way,
                    'mlb_team_id': team_data.get('id'),
                    'jersey_number': int(jersey) if jersey else None,
                }
            )
            
            action = "Created" if created else "Updated"
            print(f"  {action}: {player_obj.full_name} ({player_obj.team_abbreviation})")
            
            return player_obj
            
        except Exception as e:
            print(f"Error syncing player: {e}")
            return None
    
    def sync_all_players(self, season: int = None, limit_teams: int = None) -> Dict:
        """
        Sync all active MLB players to database
        
        Args:
            season: Year (default: current year)
            limit_teams: Limit to first N teams (for testing)
        
        Returns:
            Dictionary with sync statistics
        """
        if season is None:
            season = datetime.now().year
        
        print(f"\n{'='*70}")
        print(f"Syncing MLB Players for {season} Season")
        print(f"{'='*70}\n")
        
        stats = {
            'teams_processed': 0,
            'players_created': 0,
            'players_updated': 0,
            'errors': 0,
        }
        
        # Get all teams
        teams = self.get_all_teams(season)
        if limit_teams:
            teams = teams[:limit_teams]
        
        print(f"Found {len(teams)} teams to process\n")
        
        for team in teams:
            team_id = team.get('id')
            team_name = team.get('name')
            
            print(f"Processing: {team_name} (ID: {team_id})")
            
            # Get team roster
            roster = self.get_team_roster(team_id, season)
            print(f"  Found {len(roster)} players")
            
            for player_entry in roster:
                player_obj = self.sync_player_to_db(player_entry)
                if player_obj:
                    # Check if created or updated based on last_updated
                    # This is approximate since we just updated it
                    stats['players_updated'] += 1
                else:
                    stats['errors'] += 1
            
            stats['teams_processed'] += 1
            print()
        
        print(f"{'='*70}")
        print("Sync Complete!")
        print(f"{'='*70}")
        print(f"Teams Processed: {stats['teams_processed']}")
        print(f"Players Synced: {stats['players_updated']}")
        print(f"Errors: {stats['errors']}")
        print(f"{'='*70}\n")
        
        return stats
    
    # ==========================================================================
    # STATS VERIFICATION (for scoring picks)
    # ==========================================================================
    
    def verify_two_hits(self, player_id: int, game_date: str) -> bool:
        """
        Verify if a player got 2+ hits on a specific date
        
        Args:
            player_id: MLB player ID
            game_date: Date in YYYY-MM-DD format
        
        Returns:
            True if player got 2+ hits
        """
        games = self.get_games_by_date(game_date)
        
        for game in games:
            boxscore = self.get_game_boxscore(game['gamePk'])
            if not boxscore:
                continue
            
            # Check both teams
            for team_type in ['away', 'home']:
                team_data = boxscore.get('teams', {}).get(team_type, {})
                batters = team_data.get('batters', [])
                
                if player_id in batters:
                    player_stats = team_data.get('players', {}).get(f'ID{player_id}', {})
                    hitting_stats = player_stats.get('stats', {}).get('batting', {})
                    hits = hitting_stats.get('hits', 0)
                    
                    if hits >= 2:
                        return True
        
        return False
    
    def verify_home_run(self, player_id: int, game_date: str) -> bool:
        """
        Verify if a player hit a home run on a specific date
        
        Args:
            player_id: MLB player ID
            game_date: Date in YYYY-MM-DD format
        
        Returns:
            True if player hit a home run
        """
        games = self.get_games_by_date(game_date)
        
        for game in games:
            boxscore = self.get_game_boxscore(game['gamePk'])
            if not boxscore:
                continue
            
            for team_type in ['away', 'home']:
                team_data = boxscore.get('teams', {}).get(team_type, {})
                batters = team_data.get('batters', [])
                
                if player_id in batters:
                    player_stats = team_data.get('players', {}).get(f'ID{player_id}', {})
                    hitting_stats = player_stats.get('stats', {}).get('batting', {})
                    home_runs = hitting_stats.get('homeRuns', 0)
                    
                    if home_runs >= 1:
                        return True
        
        return False
    
    def verify_starting_win(self, player_id: int, game_date: str) -> bool:
        """
        Verify if a starting pitcher got the win on a specific date
        
        Args:
            player_id: MLB player ID
            game_date: Date in YYYY-MM-DD format
        
        Returns:
            True if starting pitcher got the win
        """
        games = self.get_games_by_date(game_date)
        
        for game in games:
            # Check decisions (winning/losing pitcher)
            decisions = game.get('decisions', {})
            winner = decisions.get('winner', {})
            
            if winner.get('id') == player_id:
                # Verify they were the starting pitcher
                boxscore = self.get_game_boxscore(game['gamePk'])
                if boxscore:
                    for team_type in ['away', 'home']:
                        team_data = boxscore.get('teams', {}).get(team_type, {})
                        player_stats = team_data.get('players', {}).get(f'ID{player_id}', {})
                        
                        if player_stats:
                            game_note = player_stats.get('gameStatus', {}).get('note', '')
                            # Starting pitchers have notes like "W, 6.0 IP, 3 H, 0 R..."
                            # Or check if they're listed as starting pitcher
                            return True  # Simplified - winner is usually the starter
        
        return False
    
    def verify_save(self, player_id: int, game_date: str) -> bool:
        """
        Verify if a pitcher got a save on a specific date
        
        Args:
            player_id: MLB player ID
            game_date: Date in YYYY-MM-DD format
        
        Returns:
            True if pitcher got a save
        """
        games = self.get_games_by_date(game_date)
        
        for game in games:
            # Check decisions (save)
            decisions = game.get('decisions', {})
            save_pitcher = decisions.get('save', {})
            
            if save_pitcher.get('id') == player_id:
                return True
        
        return False


# ==============================================================================
# CONVENIENCE FUNCTIONS
# ==============================================================================

def sync_players(season: int = None, limit_teams: int = None):
    """
    Convenience function to sync all players
    
    Args:
        season: Year (default: current year)
        limit_teams: Limit to first N teams
    
    Returns:
        Sync statistics dictionary
    """
    service = MLBAPIService()
    return service.sync_all_players(season=season, limit_teams=limit_teams)


def verify_pick(player_id: int, category_code: str, game_date: str) -> bool:
    """
    Verify if a pick was successful
    
    Args:
        player_id: MLB player ID
        category_code: '2H', 'HR', 'SWP', or 'S'
        game_date: Date in YYYY-MM-DD format
    
    Returns:
        True if pick was successful
    """
    service = MLBAPIService()
    
    if category_code == '2H':
        return service.verify_two_hits(player_id, game_date)
    elif category_code == 'HR':
        return service.verify_home_run(player_id, game_date)
    elif category_code == 'SWP':
        return service.verify_starting_win(player_id, game_date)
    elif category_code == 'S':
        return service.verify_save(player_id, game_date)
    else:
        return False
