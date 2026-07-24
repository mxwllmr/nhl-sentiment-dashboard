"""
NHL Data Loader

Loads NHL player and team data.
Automatically scrapes Wikipedia for fresh rosters on first load.
"""

import json
from pathlib import Path
import unicodedata
import re
from datetime import datetime, timedelta

# Get the directory where this file lives
try:
    DATA_DIR = Path(__file__).parent
except NameError:
    DATA_DIR = Path.cwd()


# Import teams from roster_scraper
from roster_scraper import TEAMS_BY_ABBR as NHL_TEAMS, update_rosters


def remove_accents(text):
    """Remove accents/diacritics from text for search purposes."""
    nfkd_form = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd_form if not unicodedata.combining(c))


def create_player_key(name):
    """Create a URL-safe key from player name."""
    key = name.lower().strip()
    key = remove_accents(key)
    key = re.sub(r'[^a-z0-9\s]', '', key)
    key = re.sub(r'\s+', '_', key)
    return key


def should_refresh_rosters(max_age_hours=24):
    """Check if we should refresh rosters from Wikipedia."""
    players_file = DATA_DIR / 'players.json'
    
    if not players_file.exists():
        return True
    
    # Check file age
    file_time = datetime.fromtimestamp(players_file.stat().st_mtime)
    age = datetime.now() - file_time
    
    return age > timedelta(hours=max_age_hours)


def load_players(data_dir=None, force_refresh=False):
    """
    Load all players from players.json.
    Will scrape Wikipedia if file doesn't exist or is stale.
    """
    dir_path = Path(data_dir) if data_dir else DATA_DIR
    players_file = dir_path / 'players.json'
    
    # Check if we need to refresh from Wikipedia
    if force_refresh or not players_file.exists():
        print("Scraping fresh rosters from Wikipedia...")
        players, success = update_rosters(dir_path, verbose=True)
        if success:
            return players
        # If scrape failed, try to use cached file
    
    # Load from file
    try:
        with open(players_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("ERROR: players.json not found and Wikipedia scrape failed!")
        return {}
    except json.JSONDecodeError:
        print("ERROR: players.json is corrupted!")
        return {}


def load_teams(data_dir=None):
    """Load all teams."""
    return NHL_TEAMS


def get_player(name_or_key, players=None):
    """
    Find a player by name or key.
    """
    if players is None:
        players = load_players()
    
    search = name_or_key.lower().strip()
    search_normalized = remove_accents(search)
    
    # Direct key match
    key_version = search.replace(' ', '_')
    if key_version in players:
        return players[key_version]
    
    # Search by name
    for key, player in players.items():
        if search == player.get('name', '').lower():
            return player
        if search_normalized == remove_accents(player.get('name', '')).lower():
            return player
    
    # Partial last name match
    for key, player in players.items():
        last_name = player.get('last_name', '').lower()
        if search == remove_accents(last_name):
            return player
    
    return None


def get_players_by_team(team_abbr, players=None):
    """Get all players for a specific team."""
    if players is None:
        players = load_players()
    return {k: v for k, v in players.items() if v.get('team_abbr') == team_abbr}


def get_team_subreddits():
    """Get list of all team subreddits."""
    return [team['subreddit'] for team in NHL_TEAMS.values()]


# Quick test
if __name__ == '__main__':
    print("Testing data loader...")
    
    players = load_players(force_refresh=True)
    teams = load_teams()
    
    print(f"\nLoaded {len(players)} players")
    print(f"Loaded {len(teams)} teams")
    
    # Test player lookup
    print("\n--- Testing player lookup ---")
    for search in ["Connor McDavid", "mcdavid", "crosby", "ovechkin"]:
        player = get_player(search, players)
        if player:
            print(f"'{search}' -> {player['name']} ({player.get('team_abbr', 'Unknown')})")
        else:
            print(f"'{search}' -> Not found")
