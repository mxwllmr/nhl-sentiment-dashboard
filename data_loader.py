"""
NHL Data Loader

Loads NHL player and team data from JSON files.
"""

import json
from pathlib import Path
import unicodedata
import re

# Get the directory where this file lives
try:
    DATA_DIR = Path(__file__).parent
except NameError:
    DATA_DIR = Path.cwd()


# NHL Teams (built-in, no external dependency)
NHL_TEAMS = {
    "ANA": {"name": "Anaheim Ducks", "subreddit": "AnaheimDucks", "conference": "Western", "division": "Pacific"},
    "CGY": {"name": "Calgary Flames", "subreddit": "CalgaryFlames", "conference": "Western", "division": "Pacific"},
    "EDM": {"name": "Edmonton Oilers", "subreddit": "EdmontonOilers", "conference": "Western", "division": "Pacific"},
    "LAK": {"name": "Los Angeles Kings", "subreddit": "losangeleskings", "conference": "Western", "division": "Pacific"},
    "SJS": {"name": "San Jose Sharks", "subreddit": "SanJoseSharks", "conference": "Western", "division": "Pacific"},
    "SEA": {"name": "Seattle Kraken", "subreddit": "SeattleKraken", "conference": "Western", "division": "Pacific"},
    "VAN": {"name": "Vancouver Canucks", "subreddit": "canucks", "conference": "Western", "division": "Pacific"},
    "VGK": {"name": "Vegas Golden Knights", "subreddit": "goldenknights", "conference": "Western", "division": "Pacific"},
    "CHI": {"name": "Chicago Blackhawks", "subreddit": "hawks", "conference": "Western", "division": "Central"},
    "COL": {"name": "Colorado Avalanche", "subreddit": "ColoradoAvalanche", "conference": "Western", "division": "Central"},
    "DAL": {"name": "Dallas Stars", "subreddit": "DallasStars", "conference": "Western", "division": "Central"},
    "MIN": {"name": "Minnesota Wild", "subreddit": "wildhockey", "conference": "Western", "division": "Central"},
    "NSH": {"name": "Nashville Predators", "subreddit": "Predators", "conference": "Western", "division": "Central"},
    "STL": {"name": "St. Louis Blues", "subreddit": "stlouisblues", "conference": "Western", "division": "Central"},
    "UTA": {"name": "Utah Hockey Club", "subreddit": "UtahHockeyClub", "conference": "Western", "division": "Central"},
    "WPG": {"name": "Winnipeg Jets", "subreddit": "winnipegjets", "conference": "Western", "division": "Central"},
    "BOS": {"name": "Boston Bruins", "subreddit": "BostonBruins", "conference": "Eastern", "division": "Atlantic"},
    "BUF": {"name": "Buffalo Sabres", "subreddit": "sabres", "conference": "Eastern", "division": "Atlantic"},
    "DET": {"name": "Detroit Red Wings", "subreddit": "DetroitRedWings", "conference": "Eastern", "division": "Atlantic"},
    "FLA": {"name": "Florida Panthers", "subreddit": "FloridaPanthers", "conference": "Eastern", "division": "Atlantic"},
    "MTL": {"name": "Montreal Canadiens", "subreddit": "Habs", "conference": "Eastern", "division": "Atlantic"},
    "OTT": {"name": "Ottawa Senators", "subreddit": "OttawaSenators", "conference": "Eastern", "division": "Atlantic"},
    "TBL": {"name": "Tampa Bay Lightning", "subreddit": "TampaBayLightning", "conference": "Eastern", "division": "Atlantic"},
    "TOR": {"name": "Toronto Maple Leafs", "subreddit": "leafs", "conference": "Eastern", "division": "Atlantic"},
    "CAR": {"name": "Carolina Hurricanes", "subreddit": "canes", "conference": "Eastern", "division": "Metropolitan"},
    "CBJ": {"name": "Columbus Blue Jackets", "subreddit": "BlueJackets", "conference": "Eastern", "division": "Metropolitan"},
    "NJD": {"name": "New Jersey Devils", "subreddit": "devils", "conference": "Eastern", "division": "Metropolitan"},
    "NYI": {"name": "New York Islanders", "subreddit": "NewYorkIslanders", "conference": "Eastern", "division": "Metropolitan"},
    "NYR": {"name": "New York Rangers", "subreddit": "rangers", "conference": "Eastern", "division": "Metropolitan"},
    "PHI": {"name": "Philadelphia Flyers", "subreddit": "Flyers", "conference": "Eastern", "division": "Metropolitan"},
    "PIT": {"name": "Pittsburgh Penguins", "subreddit": "penguins", "conference": "Eastern", "division": "Metropolitan"},
    "WSH": {"name": "Washington Capitals", "subreddit": "caps", "conference": "Eastern", "division": "Metropolitan"},
}


def remove_accents(text):
    """Remove accents/diacritics from text for search purposes."""
    nfkd_form = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd_form if not unicodedata.combining(c))


def load_players(data_dir=None, force_refresh=False):
    """Load all players from players.json."""
    dir_path = Path(data_dir) if data_dir else DATA_DIR
    players_file = dir_path / 'players.json'
    
    try:
        with open(players_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("ERROR: players.json not found!")
        return {}
    except json.JSONDecodeError:
        print("ERROR: players.json is corrupted!")
        return {}


def load_teams(data_dir=None):
    """Load all teams."""
    return NHL_TEAMS


def get_player(name_or_key, players=None):
    """Find a player by name or key."""
    if players is None:
        players = load_players()
    
    search = name_or_key.lower().strip()
    search_normalized = remove_accents(search)
    
    key_version = search.replace(' ', '_')
    if key_version in players:
        return players[key_version]
    
    for key, player in players.items():
        if search == player.get('name', '').lower():
            return player
        if search_normalized == remove_accents(player.get('name', '')).lower():
            return player
    
    return None
