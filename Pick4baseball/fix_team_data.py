"""Quick fix to populate team data for all players"""
from core.mlb_api_service import MLBAPIService
from core.models import MLBPlayer

service = MLBAPIService()
teams = service.get_all_teams(2026)

print(f"\nFixing team data for {len(teams)} teams...\n")

for team in teams:
    team_id = team.get('id')
    team_name = team.get('name')
    team_abbr = team.get('abbreviation')
    
    print(f"Processing: {team_name} ({team_abbr})")
    
    # Get roster
    roster = service.get_team_roster(team_id, 2026)
    player_ids = [p['person']['id'] for p in roster]
    
    # Update all players on this team
    count = MLBPlayer.objects.filter(
        mlb_player_id__in=player_ids
    ).update(
        team_name=team_name,
        team_abbreviation=team_abbr,
        mlb_team_id=team_id
    )
    
    print(f"  Updated {count} players\n")

print("✓ Done!")
