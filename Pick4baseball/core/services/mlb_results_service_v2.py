# core/services/mlb_results_service_v2.py
"""
MLB Results Service - Version 2
Enhanced with Rainout and Doubleheader Handling

Updates from v1:
1. Detects and handles postponed/rained out games
2. Only counts first game of doubleheaders
3. Excludes makeup games from previous weeks
4. Validates games were originally scheduled for Saturday

Created: January 29, 2026
"""

import statsapi
from datetime import datetime, date
from typing import Dict, List, Optional
from core.models import WeeklyResult, MLBPlayer


class MLBResultsService:
    """
    Enhanced service to fetch MLB game results with special handling for:
    - Rainouts and postponements
    - Doubleheaders (first game only)
    - Makeup games (excluded)
    """
    
    def __init__(self):
        self.api = statsapi
    
    def fetch_saturday_results(
        self, 
        saturday_date: date,
        verify_schedule: bool = True
    ) -> Dict[int, Dict]:
        """
        Fetch all valid Saturday game results with enhanced filtering
        
        Args:
            saturday_date: The Saturday to fetch results for
            verify_schedule: If True, verify games were originally scheduled for this date
            
        Returns:
            Dict mapping MLB player ID to their stats for valid Saturday games
        """
        print(f"\n{'=' * 80}")
        print(f"FETCHING MLB RESULTS - {saturday_date}")
        print(f"{'=' * 80}\n")
        
        # Get all games for this date
        date_str = saturday_date.strftime('%Y-%m-%d')
        schedule = self.api.schedule(date=date_str)
        
        print(f"📅 Found {len(schedule)} scheduled games for {saturday_date}\n")
        
        valid_games = []
        postponed_games = []
        
        for game in schedule:
            game_id = game['game_id']
            game_status = game.get('status', '')
            
            # Check if game was postponed/cancelled
            if game_status in ['Postponed', 'Cancelled', 'Suspended']:
                postponed_games.append({
                    'game_id': game_id,
                    'away': game['away_name'],
                    'home': game['home_name'],
                    'status': game_status
                })
                print(f"⚠️  POSTPONED: {game['away_name']} @ {game['home_name']} - {game_status}")
                continue
            
            # Verify game was originally scheduled for this Saturday (not a makeup)
            if verify_schedule:
                if not self._is_originally_scheduled(game, saturday_date):
                    print(f"⏭️  MAKEUP GAME: {game['away_name']} @ {game['home_name']} - Excluded")
                    continue
            
            # Check for doubleheaders
            game_number = game.get('game_number', 1)
            
            if game_number == 1:
                valid_games.append(game)
                dh_marker = " (DH Game 1)" if game.get('doubleheader', '') else ""
                print(f"✅ VALID: {game['away_name']} @ {game['home_name']}{dh_marker}")
            elif game_number == 2:
                print(f"⏭️  DH GAME 2: {game['away_name']} @ {game['home_name']} - Excluded")
        
        print(f"\n📊 GAME SUMMARY:")
        print(f"   Valid games: {len(valid_games)}")
        print(f"   Postponed: {len(postponed_games)}")
        print(f"   Processing {len(valid_games)} games for player stats...\n")
        
        # Fetch player stats from valid games only
        player_stats = {}
        
        for game in valid_games:
            game_stats = self._fetch_game_stats(game['game_id'])
            player_stats.update(game_stats)
        
        print(f"\n✅ Fetched stats for {len(player_stats)} players\n")
        
        return player_stats
    
    def _is_originally_scheduled(self, game: Dict, saturday_date: date) -> bool:
        """
        Verify game was originally scheduled for this Saturday
        (not a makeup game from a previous postponement)
        
        Args:
            game: Game data from statsapi
            saturday_date: The Saturday we're checking
            
        Returns:
            True if originally scheduled for this date, False if makeup
        """
        # Check if game has reschedule data
        if 'rescheduled_from' in game or 'makeup' in game.get('description', '').lower():
            return False
        
        # Additional check: scheduled date matches Saturday
        scheduled_date = game.get('game_date', '')
        if scheduled_date:
            try:
                game_date = datetime.strptime(scheduled_date, '%Y-%m-%d').date()
                return game_date == saturday_date
            except:
                pass
        
        # Default to True if we can't determine
        return True
    
    def _fetch_game_stats(self, game_id: int) -> Dict[int, Dict]:
        """
        Fetch player statistics from a single game
        
        Args:
            game_id: MLB game ID
            
        Returns:
            Dict mapping MLB player ID to stats
        """
        player_stats = {}
        
        try:
            # Get boxscore data
            boxscore = self.api.boxscore_data(game_id)
            
            # Process both teams
            for team_key in ['away', 'home']:
                team_data = boxscore.get(team_key, {})
                
                # Process batters
                for player_id, player_data in team_data.get('batters', {}).items():
                    player_stats[int(player_id)] = {
                        'name': player_data.get('name', ''),
                        'team': player_data.get('team', ''),
                        'position': player_data.get('position', ''),
                        'hits': player_data.get('hits', 0),
                        'home_runs': player_data.get('homeRuns', 0),
                        'at_bats': player_data.get('atBats', 0),
                        'game_id': game_id
                    }
                
                # Process pitchers
                for player_id, player_data in team_data.get('pitchers', {}).items():
                    # Get decision (W/L/S)
                    decision = self._get_pitcher_decision(player_data)
                    
                    player_stats[int(player_id)] = {
                        'name': player_data.get('name', ''),
                        'team': player_data.get('team', ''),
                        'position': 'P',
                        'decision': decision,
                        'saves': 1 if decision == 'S' else 0,
                        'wins': 1 if decision == 'W' else 0,
                        'innings_pitched': player_data.get('inningsPitched', 0),
                        'game_id': game_id
                    }
        
        except Exception as e:
            print(f"⚠️  Error fetching game {game_id}: {str(e)}")
        
        return player_stats
    
    def _get_pitcher_decision(self, pitcher_data: Dict) -> Optional[str]:
        """
        Determine pitcher decision (W/L/S)
        
        Args:
            pitcher_data: Pitcher statistics from boxscore
            
        Returns:
            'W', 'L', 'S', or None
        """
        note = pitcher_data.get('note', '').upper()
        
        if 'W' in note or 'WIN' in note:
            return 'W'
        elif 'L' in note or 'LOSS' in note:
            return 'L'
        elif 'S' in note or 'SAVE' in note:
            return 'S'
        elif 'SV' in note:
            return 'S'
        
        return None
    
    def save_results_to_database(
        self,
        player_stats: Dict[int, Dict],
        week,
        team
    ) -> int:
        """
        Save fetched results to WeeklyResult table
        
        Args:
            player_stats: Dict of player stats from fetch_saturday_results
            week: Week model instance
            team: Team model instance
            
        Returns:
            Number of results saved
        """
        print(f"\n{'=' * 80}")
        print(f"SAVING RESULTS TO DATABASE")
        print(f"{'=' * 80}\n")
        
        results_created = 0
        results_updated = 0
        
        for mlb_player_id, stats in player_stats.items():
            try:
                # Get or create MLB Player
                mlb_player, _ = MLBPlayer.objects.get_or_create(
                    mlb_id=mlb_player_id,
                    defaults={
                        'name': stats['name'],
                        'team': stats['team'],
                        'position': stats['position']
                    }
                )
                
                # Create or update WeeklyResult
                result, created = WeeklyResult.objects.update_or_create(
                    week=week,
                    team=team,
                    mlb_player=mlb_player,
                    defaults={
                        'hits': stats.get('hits', 0),
                        'home_runs': stats.get('home_runs', 0),
                        'wins': stats.get('wins', 0),
                        'saves': stats.get('saves', 0),
                        'pitcher_decision': stats.get('decision', None),
                        'at_bats': stats.get('at_bats', 0),
                        'innings_pitched': stats.get('innings_pitched', 0)
                    }
                )
                
                if created:
                    results_created += 1
                    action = "CREATED"
                else:
                    results_updated += 1
                    action = "UPDATED"
                
                print(f"{action}: {stats['name']} ({stats['team']}) - "
                      f"H: {stats.get('hits', 0)}, HR: {stats.get('home_runs', 0)}")
            
            except Exception as e:
                print(f"❌ ERROR saving {stats.get('name', 'Unknown')}: {str(e)}")
        
        print(f"\n{'=' * 80}")
        print(f"DATABASE SAVE COMPLETE")
        print(f"{'=' * 80}")
        print(f"✅ Created: {results_created}")
        print(f"🔄 Updated: {results_updated}")
        print(f"📊 Total: {results_created + results_updated}\n")
        
        return results_created + results_updated
    
    def get_postponed_games(self, saturday_date: date) -> List[Dict]:
        """
        Get list of postponed games for a Saturday
        Useful for admin notifications
        
        Args:
            saturday_date: The Saturday to check
            
        Returns:
            List of postponed game details
        """
        date_str = saturday_date.strftime('%Y-%m-%d')
        schedule = self.api.schedule(date=date_str)
        
        postponed = []
        for game in schedule:
            if game.get('status', '') in ['Postponed', 'Cancelled', 'Suspended']:
                postponed.append({
                    'game_id': game['game_id'],
                    'away_team': game['away_name'],
                    'home_team': game['home_name'],
                    'status': game['status'],
                    'reason': game.get('status_reason', 'Weather')
                })
        
        return postponed


# Example usage
if __name__ == '__main__':
    service = MLBResultsService()
    
    # Test with a sample date
    test_date = date(2025, 9, 28)
    
    # Fetch results
    results = service.fetch_saturday_results(test_date)
    
    # Check for postponements
    postponed = service.get_postponed_games(test_date)
    
    if postponed:
        print(f"\n⚠️  POSTPONED GAMES:")
        for game in postponed:
            print(f"   {game['away_team']} @ {game['home_team']} - {game['reason']}")
