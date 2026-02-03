"""
MLB Results Service
Fetches and stores MLB game results from the MLB Stats API.

This service is responsible for:
1. Fetching Saturday game results
2. Extracting player statistics (hits, HR, pitcher decisions, saves)
3. Creating WeeklyResult records for scoring
"""

import statsapi
from decimal import Decimal
from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone

from core.models import Week, MLBPlayer, PickCategory, WeeklyResult


class MLBResultsService:
    """Service for fetching MLB game results and creating WeeklyResult records"""

    def __init__(self):
        self.results_created = []
        self.errors = []

    def fetch_saturday_results(self, week):
        """
        Fetch all MLB game results for a week's Saturday games.

        Args:
            week: Week object

        Returns:
            dict: {
                'results_created': int,
                'errors': list,
                'players_processed': int
            }
        """
        saturday_date = week.saturday_date  # Get the Saturday date

        print(f"Fetching MLB results for Saturday {saturday_date}...")

        # Get all games for Saturday
        try:
            games = statsapi.schedule(date=saturday_date.strftime('%Y-%m-%d'))
        except Exception as e:
            self.errors.append(f"Failed to fetch games: {str(e)}")
            return self._build_response()

        if not games:
            self.errors.append(f"No games found for {saturday_date}")
            return self._build_response()

        print(f"Found {len(games)} games on {saturday_date}")

        # Process each game
        for game in games:
            self._process_game(week, game)

        return self._build_response()

    def _process_game(self, week, game):
        """Process a single game and extract statistics"""

        game_id = game.get('game_id')
        game_date = game.get('game_date')

        # Only process completed games
        if game.get('status') != 'Final':
            print(f"Skipping game {game_id} - Status: {game.get('status')}")
            return

        print(f"Processing game {game_id}: {game.get('summary')}")

        try:
            # Get detailed game data including box score
            boxscore = statsapi.boxscore_data(game_id)

            # Process batting statistics
            self._process_batting_stats(week, game_id, game_date, boxscore)

            # Process pitching statistics
            self._process_pitching_stats(week, game_id, game_date, boxscore)

        except Exception as e:
            self.errors.append(f"Error processing game {game_id}: {str(e)}")

    def _process_batting_stats(self, week, game_id, game_date, boxscore):
        """Process batting statistics from a game"""

        # Get 2H and HR categories
        cat_2h = PickCategory.objects.get(code='2H')
        cat_hr = PickCategory.objects.get(code='HR')

        # Process both teams
        for team_side in ['home', 'away']:
            batting = boxscore.get(team_side + 'Batting', [])

            for player_stats in batting:
                mlb_player_id = player_stats.get('personId')

                if not mlb_player_id:
                    continue

                # Try to find player in our database
                try:
                    player = MLBPlayer.objects.get(mlb_player_id=mlb_player_id)
                except MLBPlayer.DoesNotExist:
                    # Player not in our system, skip
                    continue

                # Get stats
                hits = int(player_stats.get('h', 0))
                home_runs = int(player_stats.get('hr', 0))

                # Create/update WeeklyResult for 2H
                if hits > 0:  # Only create if player had at-bats
                    self._create_or_update_result(
                        week=week,
                        player=player,
                        category=cat_2h,
                        achieved=(hits >= 2),
                        stat_value=Decimal(str(hits)),
                        game_date=game_date,
                        game_id=game_id
                    )

                # Create/update WeeklyResult for HR
                if hits > 0:  # Only if player had at-bats
                    self._create_or_update_result(
                        week=week,
                        player=player,
                        category=cat_hr,
                        achieved=(home_runs >= 1),
                        stat_value=Decimal(str(home_runs)),
                        game_date=game_date,
                        game_id=game_id
                    )

    def _process_pitching_stats(self, week, game_id, game_date, boxscore):
        """Process pitching statistics from a game"""

        # Get SWP and S categories
        cat_swp = PickCategory.objects.get(code='SWP')
        cat_s = PickCategory.objects.get(code='S')

        # Process both teams
        for team_side in ['home', 'away']:
            pitching = boxscore.get(team_side + 'Pitchers', [])

            for pitcher_stats in pitching:
                mlb_player_id = pitcher_stats.get('personId')

                if not mlb_player_id:
                    continue

                # Try to find pitcher in our database
                try:
                    pitcher = MLBPlayer.objects.get(mlb_player_id=mlb_player_id)
                except MLBPlayer.DoesNotExist:
                    continue

                # Get pitcher decision and saves
                decision = pitcher_stats.get('note', '')  # "W", "L", "S", "H", etc.
                saves = int(pitcher_stats.get('sv', 0))

                # Check if starting pitcher
                batting_order = pitcher_stats.get('battingOrder', '')
                is_starter = (batting_order == '1')

                # Create/update WeeklyResult for SWP (Starting Winning Pitcher)
                got_win = ('W' in decision)
                self._create_or_update_result(
                    week=week,
                    player=pitcher,
                    category=cat_swp,
                    achieved=(is_starter and got_win),
                    stat_value=Decimal('1.0' if (is_starter and got_win) else '0.0'),
                    game_date=game_date,
                    game_id=game_id
                )

                # Create/update WeeklyResult for S (Save)
                self._create_or_update_result(
                    week=week,
                    player=pitcher,
                    category=cat_s,
                    achieved=(saves >= 1),
                    stat_value=Decimal(str(saves)),
                    game_date=game_date,
                    game_id=game_id
                )

    @transaction.atomic
    def _create_or_update_result(self, week, player, category, achieved, stat_value, game_date, game_id):
        """
        Create or update a WeeklyResult record.
        If multiple games on same day, aggregate the stats.
        """

        result, created = WeeklyResult.objects.get_or_create(
            week=week,
            player=player,
            category=category,
            defaults={
                'achieved': achieved,
                'stat_value': stat_value,
                'game_date': game_date,
                'game_id': game_id,
                'verified_at': timezone.now()
            }
        )

        if not created:
            # Update existing result - aggregate stats if multiple games
            result.stat_value = result.stat_value + stat_value
            result.achieved = self._check_achievement(category, result.stat_value)
            result.game_id = f"{result.game_id},{game_id}"  # Track multiple games
            result.verified_at = timezone.now()
            result.save()

        self.results_created.append(result)

        action = "Created" if created else "Updated"
        print(f"  {action} result: {player.full_name} - {category.code} - Achieved: {result.achieved} (Value: {result.stat_value})")

    def _check_achievement(self, category, stat_value):
        """Check if a stat value achieves the category requirement"""

        if category.code == '2H':
            return stat_value >= 2
        elif category.code == 'HR':
            return stat_value >= 1
        elif category.code in ['SWP', 'S']:
            return stat_value >= 1

        return False

    def _build_response(self):
        """Build response dictionary"""

        unique_players = set()
        for result in self.results_created:
            unique_players.add(result.player.id)

        return {
            'results_created': len(self.results_created),
            'players_processed': len(unique_players),
            'errors': self.errors
        }

    def get_player_results(self, week, player):
        """
        Get all WeeklyResults for a player in a week.

        Returns: QuerySet of WeeklyResult
        """
        return WeeklyResult.objects.filter(
            week=week,
            player=player
        )

    def verify_result_exists(self, week, player, category):
        """
        Check if a result exists for a player/category/week.

        Returns: WeeklyResult or None
        """
        try:
            return WeeklyResult.objects.get(
                week=week,
                player=player,
                category=category
            )
        except WeeklyResult.DoesNotExist:
            return None

    def get_week_summary(self, week):
        """
        Get summary of results for a week.

        Returns: dict with stats
        """
        results = WeeklyResult.objects.filter(week=week)

        return {
            'total_results': results.count(),
            'achieved_count': results.filter(achieved=True).count(),
            'missed_count': results.filter(achieved=False).count(),
            'by_category': {
                '2H': results.filter(category__code='2H').count(),
                'HR': results.filter(category__code='HR').count(),
                'SWP': results.filter(category__code='SWP').count(),
                'S': results.filter(category__code='S').count(),
            }
        }
