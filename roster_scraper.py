"""
NHL Wikipedia Roster Scraper

Scrapes current NHL rosters from Wikipedia every time it runs.
This ensures player data is always up-to-date with trades, signings, etc.

Sources:
- https://en.wikipedia.org/wiki/List_of_current_NHL_Western_Conference_team_rosters
- https://en.wikipedia.org/wiki/List_of_current_NHL_Eastern_Conference_team_rosters
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import unicodedata
from pathlib import Path
import time


# NHL Teams with their info
NHL_TEAMS = {
    # Western Conference - Pacific
    "Anaheim Ducks": {"abbr": "ANA", "subreddit": "AnaheimDucks", "conference": "Western", "division": "Pacific"},
    "Calgary Flames": {"abbr": "CGY", "subreddit": "CalgaryFlames", "conference": "Western", "division": "Pacific"},
    "Edmonton Oilers": {"abbr": "EDM", "subreddit": "EdmontonOilers", "conference": "Western", "division": "Pacific"},
    "Los Angeles Kings": {"abbr": "LAK", "subreddit": "losangeleskings", "conference": "Western", "division": "Pacific"},
    "San Jose Sharks": {"abbr": "SJS", "subreddit": "SanJoseSharks", "conference": "Western", "division": "Pacific"},
    "Seattle Kraken": {"abbr": "SEA", "subreddit": "SeattleKraken", "conference": "Western", "division": "Pacific"},
    "Vancouver Canucks": {"abbr": "VAN", "subreddit": "canucks", "conference": "Western", "division": "Pacific"},
    "Vegas Golden Knights": {"abbr": "VGK", "subreddit": "goldenknights", "conference": "Western", "division": "Pacific"},
    
    # Western Conference - Central
    "Chicago Blackhawks": {"abbr": "CHI", "subreddit": "hawks", "conference": "Western", "division": "Central"},
    "Colorado Avalanche": {"abbr": "COL", "subreddit": "ColoradoAvalanche", "conference": "Western", "division": "Central"},
    "Dallas Stars": {"abbr": "DAL", "subreddit": "DallasStars", "conference": "Western", "division": "Central"},
    "Minnesota Wild": {"abbr": "MIN", "subreddit": "wildhockey", "conference": "Western", "division": "Central"},
    "Nashville Predators": {"abbr": "NSH", "subreddit": "Predators", "conference": "Western", "division": "Central"},
    "St. Louis Blues": {"abbr": "STL", "subreddit": "stlouisblues", "conference": "Western", "division": "Central"},
    "Utah Hockey Club": {"abbr": "UTA", "subreddit": "UtahHockeyClub", "conference": "Western", "division": "Central"},
    "Winnipeg Jets": {"abbr": "WPG", "subreddit": "winnipegjets", "conference": "Western", "division": "Central"},
    
    # Eastern Conference - Atlantic
    "Boston Bruins": {"abbr": "BOS", "subreddit": "BostonBruins", "conference": "Eastern", "division": "Atlantic"},
    "Buffalo Sabres": {"abbr": "BUF", "subreddit": "sabres", "conference": "Eastern", "division": "Atlantic"},
    "Detroit Red Wings": {"abbr": "DET", "subreddit": "DetroitRedWings", "conference": "Eastern", "division": "Atlantic"},
    "Florida Panthers": {"abbr": "FLA", "subreddit": "FloridaPanthers", "conference": "Eastern", "division": "Atlantic"},
    "Montreal Canadiens": {"abbr": "MTL", "subreddit": "Habs", "conference": "Eastern", "division": "Atlantic"},
    "Montréal Canadiens": {"abbr": "MTL", "subreddit": "Habs", "conference": "Eastern", "division": "Atlantic"},
    "Ottawa Senators": {"abbr": "OTT", "subreddit": "OttawaSenators", "conference": "Eastern", "division": "Atlantic"},
    "Tampa Bay Lightning": {"abbr": "TBL", "subreddit": "TampaBayLightning", "conference": "Eastern", "division": "Atlantic"},
    "Toronto Maple Leafs": {"abbr": "TOR", "subreddit": "leafs", "conference": "Eastern", "division": "Atlantic"},
    
    # Eastern Conference - Metropolitan  
    "Carolina Hurricanes": {"abbr": "CAR", "subreddit": "canes", "conference": "Eastern", "division": "Metropolitan"},
    "Columbus Blue Jackets": {"abbr": "CBJ", "subreddit": "BlueJackets", "conference": "Eastern", "division": "Metropolitan"},
    "New Jersey Devils": {"abbr": "NJD", "subreddit": "devils", "conference": "Eastern", "division": "Metropolitan"},
    "New York Islanders": {"abbr": "NYI", "subreddit": "NewYorkIslanders", "conference": "Eastern", "division": "Metropolitan"},
    "New York Rangers": {"abbr": "NYR", "subreddit": "rangers", "conference": "Eastern", "division": "Metropolitan"},
    "Philadelphia Flyers": {"abbr": "PHI", "subreddit": "Flyers", "conference": "Eastern", "division": "Metropolitan"},
    "Pittsburgh Penguins": {"abbr": "PIT", "subreddit": "penguins", "conference": "Eastern", "division": "Metropolitan"},
    "Washington Capitals": {"abbr": "WSH", "subreddit": "caps", "conference": "Eastern", "division": "Metropolitan"},
}

# Reverse lookup: abbr -> team info
TEAMS_BY_ABBR = {}
for team_name, info in NHL_TEAMS.items():
    abbr = info['abbr']
    if abbr not in TEAMS_BY_ABBR:
        TEAMS_BY_ABBR[abbr] = {
            'name': team_name,
            'full_name': team_name,
            **info
        }


def remove_accents(text):
    """Remove accents/diacritics from text."""
    nfkd_form = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd_form if not unicodedata.combining(c))


def create_player_key(name):
    """Create a URL-safe key from player name."""
    key = name.lower().strip()
    key = remove_accents(key)
    key = re.sub(r'[^a-z0-9\s]', '', key)
    key = re.sub(r'\s+', '_', key)
    return key


def scrape_wikipedia_rosters():
    """
    Scrape NHL rosters from Wikipedia.
    Returns a dictionary of all players with their team assignments.
    """
    players = {}
    
    urls = [
        ("Western", "https://en.wikipedia.org/wiki/List_of_current_NHL_Western_Conference_team_rosters"),
        ("Eastern", "https://en.wikipedia.org/wiki/List_of_current_NHL_Eastern_Conference_team_rosters")
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    for conference, url in urls:
        print(f"  Fetching {conference} Conference rosters...")
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all tables with class 'wikitable'
            tables = soup.find_all('table', class_='wikitable')
            
            current_team = None
            current_team_info = None
            
            for table in tables:
                # Look for team name in the preceding h3 element
                prev = table.find_previous(['h3', 'h2'])
                if prev:
                    # Extract team name from the header
                    span = prev.find('span', class_='mw-headline')
                    if span:
                        header_text = span.get_text().strip()
                    else:
                        header_text = prev.get_text().strip()
                    
                    # Remove [edit] links
                    header_text = re.sub(r'\[edit\]', '', header_text).strip()
                    
                    # Match to our team list
                    for team_name, team_info in NHL_TEAMS.items():
                        if team_name.lower() in header_text.lower():
                            current_team = team_name
                            current_team_info = team_info
                            break
                
                if not current_team or not current_team_info:
                    continue
                
                # Parse the table rows
                rows = table.find_all('tr')
                
                for row in rows[1:]:  # Skip header row
                    cells = row.find_all(['td', 'th'])
                    
                    if len(cells) < 3:
                        continue
                    
                    # Find the player name - look for the cell with a player link
                    player_name = None
                    position = None
                    
                    for i, cell in enumerate(cells):
                        # Check for player link
                        links = cell.find_all('a')
                        for link in links:
                            href = link.get('href', '')
                            title = link.get('title', '')
                            text = link.get_text().strip()
                            
                            # Skip flags, nationalities, etc
                            if '/wiki/File:' in href or '/wiki/Template:' in href:
                                continue
                            if len(text) <= 2:  # Skip country codes
                                continue
                            if text.isupper() and len(text) <= 3:  # Skip abbreviations
                                continue
                            
                            # This looks like a player name
                            if ' ' in text or len(text) > 6:
                                # Remove captain designations
                                text = re.sub(r'\s*\([CAca]+\)\s*', '', text).strip()
                                if text and len(text) > 3:
                                    player_name = text
                                    break
                        
                        if player_name:
                            break
                    
                    # Find position (usually C, LW, RW, D, G)
                    for cell in cells:
                        cell_text = cell.get_text().strip()
                        if cell_text in ['C', 'LW', 'RW', 'D', 'G', 'F', 'W', 'C/LW', 'C/RW', 'LW/RW']:
                            position = cell_text
                            break
                    
                    if player_name:
                        key = create_player_key(player_name)
                        
                        # Parse first/last name
                        name_parts = player_name.split()
                        first_name = name_parts[0] if name_parts else player_name
                        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
                        
                        players[key] = {
                            "name": player_name,
                            "first_name": first_name,
                            "last_name": last_name,
                            "team": current_team,
                            "team_abbr": current_team_info['abbr'],
                            "position": position or "",
                            "conference": current_team_info['conference'],
                            "division": current_team_info['division'],
                            "headshot_url": None  # Will be filled in later if needed
                        }
            
            time.sleep(0.5)  # Be nice to Wikipedia
            
        except Exception as e:
            print(f"  Error fetching {conference}: {e}")
    
    return players


def save_players(players, output_dir=None):
    """Save players to JSON file."""
    if output_dir is None:
        try:
            output_dir = Path(__file__).parent
        except NameError:
            output_dir = Path.cwd()
    else:
        output_dir = Path(output_dir)
    
    output_file = output_dir / 'players.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(players, f, indent=2, ensure_ascii=False)
    
    return output_file


def save_teams(output_dir=None):
    """Save teams to JSON file."""
    if output_dir is None:
        try:
            output_dir = Path(__file__).parent
        except NameError:
            output_dir = Path.cwd()
    else:
        output_dir = Path(output_dir)
    
    output_file = output_dir / 'teams.json'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(TEAMS_BY_ABBR, f, indent=2, ensure_ascii=False)
    
    return output_file


def update_rosters(output_dir=None, verbose=True):
    """
    Main function to update NHL rosters from Wikipedia.
    Call this at dashboard startup to ensure fresh data.
    
    Returns: (players_dict, success_bool)
    """
    if verbose:
        print("Updating NHL rosters from Wikipedia...")
    
    players = scrape_wikipedia_rosters()
    
    if not players:
        print("WARNING: No players scraped from Wikipedia!")
        return {}, False
    
    # Count by team
    teams_count = {}
    for player in players.values():
        team = player.get('team_abbr', 'Unknown')
        teams_count[team] = teams_count.get(team, 0) + 1
    
    if verbose:
        print(f"  Found {len(players)} players across {len(teams_count)} teams")
    
    # Save files
    save_players(players, output_dir)
    save_teams(output_dir)
    
    return players, True


if __name__ == '__main__':
    # Run standalone to test
    print("=" * 50)
    print("NHL ROSTER SCRAPER TEST")
    print("=" * 50)
    
    players, success = update_rosters(verbose=True)
    
    if success:
        print(f"\n✅ Successfully scraped {len(players)} players!")
        
        # Show sample
        print("\nSample players:")
        for i, (key, player) in enumerate(list(players.items())[:10]):
            print(f"  {player['name']} ({player['team_abbr']}) - {player['position']}")
    else:
        print("\n❌ Failed to scrape rosters")
