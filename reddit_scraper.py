"""
Reddit scraper for NHL player mentions.

Uses Reddit's public JSON endpoints (no authentication required).
Fetches comments from r/hockey and team subreddits.
Includes retry logic for rate limiting.
"""

import requests
import time
import re
import unicodedata
from datetime import datetime
from typing import Optional
from data_loader import load_players, load_teams

# Get NHL_TEAMS from roster_scraper
from roster_scraper import TEAMS_BY_ABBR as NHL_TEAMS


def remove_accents(text):
    """Remove accents/diacritics from text."""
    nfkd_form = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd_form if not unicodedata.combining(c))


class RedditScraper:
    """
    Scraper for fetching NHL-related comments from Reddit.
    Uses public JSON endpoints - no API key required.
    """
    
    BASE_URL = "https://old.reddit.com"  # old.reddit.com often works better
    MAIN_SUB = "hockey"
    
    def __init__(self):
        """Initialize the Reddit scraper."""
        self.session = requests.Session()
        # Use headers that look more like a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.players = load_players()
        self._build_search_index()
        self.last_request_time = 0
        self.min_request_interval = 3  # Increased to 3 seconds
        self.max_retries = 3
        self.retry_delay = 5
    
    def _build_search_index(self):
        """Build an index for fast player name lookups.
        
        IMPORTANT: Only matches on:
        - Full names (e.g., "Connor McDavid")
        - Last names with 5+ characters (e.g., "McDavid", "Crosby")
        - Never matches on common first names alone (e.g., "John", "Connor")
        """
        self.search_index = {}
        
        # Common first names to NEVER match on alone
        common_first_names = {
            'john', 'jack', 'alex', 'alexander', 'connor', 'ryan', 'matt', 'matthew', 
            'mike', 'michael', 'chris', 'christopher', 'james', 'david', 'nick', 
            'nicholas', 'tyler', 'kyle', 'adam', 'jordan', 'jake', 'jacob', 'josh', 
            'joshua', 'justin', 'kevin', 'mark', 'marcus', 'sean', 'sam', 'samuel', 
            'tom', 'thomas', 'will', 'william', 'ben', 'benjamin', 'brandon', 'brian', 
            'bryan', 'chad', 'dan', 'daniel', 'eric', 'erik', 'evan', 'jason', 'jeff', 
            'jeffrey', 'joe', 'joseph', 'lucas', 'luke', 'max', 'nathan', 'patrick', 
            'paul', 'peter', 'phil', 'philip', 'scott', 'steve', 'steven', 'tim', 
            'timothy', 'travis', 'zach', 'zachary', 'drew', 'dylan', 'cole', 'brady',
            'brock', 'blake', 'carey', 'carter', 'casey', 'cody', 'corey', 'craig',
            'derek', 'dustin', 'elias', 'filip', 'gabriel', 'garrett', 'grant', 'greg',
            'ivan', 'jamie', 'jared', 'jesse', 'johnny', 'jonathan', 'josh', 'kris',
            'logan', 'martin', 'mitch', 'mitchell', 'morgan', 'nate', 'noah', 'oliver',
            'owen', 'pierre', 'quinn', 'robert', 'rob', 'roman', 'seth', 'shane', 
            'shea', 'simon', 'spencer', 'taylor', 'timo', 'tomas', 'tony', 'trevor',
            'victor', 'vincent', 'wayne', 'zach'
        }
        
        for key, player in self.players.items():
            # Get player name parts
            full_name = player.get('name', '').lower()
            first_name = player.get('first_name', '').lower()
            last_name = player.get('last_name', '').lower()
            
            # ALWAYS add full name
            if len(full_name) >= 5:
                if full_name not in self.search_index:
                    self.search_index[full_name] = []
                if key not in self.search_index[full_name]:
                    self.search_index[full_name].append(key)
            
            # Add last name ONLY if 5+ characters (avoids "Fox", "Kane", etc. being too generic)
            if len(last_name) >= 5 and last_name not in common_first_names:
                if last_name not in self.search_index:
                    self.search_index[last_name] = []
                if key not in self.search_index[last_name]:
                    self.search_index[last_name].append(key)
            
            # Add normalized versions (no accents) of full name and last name
            normalized_full = remove_accents(full_name)
            normalized_last = remove_accents(last_name)
            
            if normalized_full != full_name and len(normalized_full) >= 5:
                if normalized_full not in self.search_index:
                    self.search_index[normalized_full] = []
                if key not in self.search_index[normalized_full]:
                    self.search_index[normalized_full].append(key)
            
            if normalized_last != last_name and len(normalized_last) >= 5 and normalized_last not in common_first_names:
                if normalized_last not in self.search_index:
                    self.search_index[normalized_last] = []
                if key not in self.search_index[normalized_last]:
                    self.search_index[normalized_last].append(key)
    
    def _rate_limit(self):
        """Ensure we don't hit Reddit too fast."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
        self.last_request_time = time.time()
    
    def _make_request(self, url: str, retries: int = 0) -> Optional[dict]:
        """Make a rate-limited request to Reddit with retry logic."""
        self._rate_limit()
        
        try:
            response = self.session.get(url, timeout=15)
            
            # Handle rate limiting
            if response.status_code == 429:
                if retries < self.max_retries:
                    wait_time = self.retry_delay * (retries + 1)
                    print(f"  Rate limited. Waiting {wait_time}s and retrying...")
                    time.sleep(wait_time)
                    return self._make_request(url, retries + 1)
                else:
                    print(f"  Max retries reached for {url}")
                    return None
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            if retries < self.max_retries:
                print(f"  Timeout. Retrying ({retries + 1}/{self.max_retries})...")
                time.sleep(2)
                return self._make_request(url, retries + 1)
            return None
        except requests.exceptions.RequestException as e:
            print(f"  Request error: {e}")
            return None
        except ValueError as e:
            print(f"  JSON decode error: {e}")
            return None
    
    def find_players_in_text(self, text: str) -> list[str]:
        """Find all player mentions in a piece of text."""
        text_lower = text.lower()
        found_players = set()
        
        for term, player_keys in self.search_index.items():
            pattern = r'\b' + re.escape(term) + r'\b'
            if re.search(pattern, text_lower):
                for key in player_keys:
                    found_players.add(key)
        
        return list(found_players)
    
    def fetch_recent_comments(
        self,
        subreddit: str = "hockey",
        limit: int = 100,
        min_length: int = 20
    ) -> list[dict]:
        """Fetch recent comments from a subreddit."""
        comments = []
        url = f"{self.BASE_URL}/r/{subreddit}/comments.json?limit={min(limit, 100)}"
        
        data = self._make_request(url)
        if not data:
            return []
        
        try:
            children = data['data']['children']
        except (KeyError, TypeError):
            return []
        
        for item in children:
            comment_data = item['data']
            body = comment_data.get('body', '')
            
            if len(body) < min_length:
                continue
            
            if body in ['[deleted]', '[removed]']:
                continue
            
            mentioned_players = self.find_players_in_text(body)
            
            if mentioned_players:
                comments.append({
                    'id': comment_data.get('id'),
                    'body': body,
                    'author': comment_data.get('author', '[deleted]'),
                    'score': comment_data.get('score', 0),
                    'created_utc': datetime.fromtimestamp(comment_data.get('created_utc', 0)),
                    'subreddit': subreddit,
                    'permalink': f"https://reddit.com{comment_data.get('permalink', '')}",
                    'mentioned_players': mentioned_players
                })
        
        return comments
    
    def fetch_hot_posts_comments(
        self,
        subreddit: str = "hockey",
        num_posts: int = 10,
        comments_per_post: int = 50,
        min_length: int = 20
    ) -> list[dict]:
        """Fetch comments from hot posts in a subreddit."""
        all_comments = []
        
        url = f"{self.BASE_URL}/r/{subreddit}/hot.json?limit={num_posts}"
        data = self._make_request(url)
        
        if not data:
            return []
        
        try:
            posts = data['data']['children']
        except (KeyError, TypeError):
            return []
        
        for post in posts:
            post_data = post['data']
            post_id = post_data.get('id')
            post_title = post_data.get('title', '')
            
            comments_url = f"{self.BASE_URL}/r/{subreddit}/comments/{post_id}.json?limit={comments_per_post}&sort=top"
            comments_data = self._make_request(comments_url)
            
            if not comments_data or len(comments_data) < 2:
                continue
            
            try:
                comment_children = comments_data[1]['data']['children']
            except (KeyError, TypeError, IndexError):
                continue
            
            for item in comment_children:
                if item['kind'] != 't1':
                    continue
                
                comment_data = item['data']
                body = comment_data.get('body', '')
                
                if len(body) < min_length or body in ['[deleted]', '[removed]']:
                    continue
                
                mentioned_players = self.find_players_in_text(body)
                if not mentioned_players:
                    mentioned_players = self.find_players_in_text(post_title)
                
                if mentioned_players:
                    all_comments.append({
                        'id': comment_data.get('id'),
                        'body': body,
                        'author': comment_data.get('author', '[deleted]'),
                        'score': comment_data.get('score', 0),
                        'created_utc': datetime.fromtimestamp(comment_data.get('created_utc', 0)),
                        'subreddit': subreddit,
                        'permalink': f"https://reddit.com{comment_data.get('permalink', '')}",
                        'post_title': post_title,
                        'mentioned_players': mentioned_players
                    })
        
        return all_comments
    
    def fetch_top_posts_comments(
        self,
        subreddit: str = "hockey",
        time_filter: str = "week",
        num_posts: int = 10,
        comments_per_post: int = 50,
        min_length: int = 20
    ) -> list[dict]:
        """Fetch comments from top posts in a subreddit."""
        all_comments = []
        
        url = f"{self.BASE_URL}/r/{subreddit}/top.json?t={time_filter}&limit={num_posts}"
        data = self._make_request(url)
        
        if not data:
            return []
        
        try:
            posts = data['data']['children']
        except (KeyError, TypeError):
            return []
        
        for post in posts:
            post_data = post['data']
            post_id = post_data.get('id')
            post_title = post_data.get('title', '')
            
            comments_url = f"{self.BASE_URL}/r/{subreddit}/comments/{post_id}.json?limit={comments_per_post}&sort=top"
            comments_data = self._make_request(comments_url)
            
            if not comments_data or len(comments_data) < 2:
                continue
            
            try:
                comment_children = comments_data[1]['data']['children']
            except (KeyError, TypeError, IndexError):
                continue
            
            for item in comment_children:
                if item['kind'] != 't1':
                    continue
                
                comment_data = item['data']
                body = comment_data.get('body', '')
                
                if len(body) < min_length or body in ['[deleted]', '[removed]']:
                    continue
                
                mentioned_players = self.find_players_in_text(body)
                if not mentioned_players:
                    mentioned_players = self.find_players_in_text(post_title)
                
                if mentioned_players:
                    all_comments.append({
                        'id': comment_data.get('id'),
                        'body': body,
                        'author': comment_data.get('author', '[deleted]'),
                        'score': comment_data.get('score', 0),
                        'created_utc': datetime.fromtimestamp(comment_data.get('created_utc', 0)),
                        'subreddit': subreddit,
                        'permalink': f"https://reddit.com{comment_data.get('permalink', '')}",
                        'post_title': post_title,
                        'mentioned_players': mentioned_players
                    })
        
        return all_comments
    
    def fetch_from_all_sources(
        self,
        include_team_subs: bool = True,
        progress_callback=None
    ) -> list[dict]:
        """
        Fetch comments from r/hockey and optionally all team subreddits.
        
        Args:
            include_team_subs: Whether to also fetch from team subreddits
            progress_callback: Optional function to call with progress updates
            
        Returns:
            Combined list of comments with duplicates removed
        """
        all_comments = []
        seen_ids = set()
        
        def add_comments(comments):
            nonlocal all_comments, seen_ids
            for c in comments:
                if c['id'] not in seen_ids:
                    seen_ids.add(c['id'])
                    all_comments.append(c)
        
        # Fetch from main hockey subreddit
        if progress_callback:
            progress_callback(f"Fetching from r/{self.MAIN_SUB}...")
        
        print(f"Fetching from r/{self.MAIN_SUB}...")
        add_comments(self.fetch_recent_comments(self.MAIN_SUB, limit=100))
        add_comments(self.fetch_hot_posts_comments(self.MAIN_SUB, num_posts=15, comments_per_post=50))
        add_comments(self.fetch_top_posts_comments(self.MAIN_SUB, time_filter="week", num_posts=10, comments_per_post=40))
        print(f"  Found {len(all_comments)} comments so far")
        
        # Fetch from team subreddits
        if include_team_subs:
            team_subs = [(abbr, info['subreddit']) for abbr, info in NHL_TEAMS.items()]
            
            for i, (team_abbr, sub_name) in enumerate(team_subs):
                if progress_callback:
                    progress_callback(f"Fetching from r/{sub_name} ({i+1}/{len(team_subs)})...")
                
                print(f"Fetching from r/{sub_name}...")
                
                # Hot posts from team sub
                add_comments(self.fetch_hot_posts_comments(sub_name, num_posts=5, comments_per_post=30))
                
                print(f"  Total comments: {len(all_comments)}")
        
        return all_comments
    
    def group_comments_by_player(self, comments: list[dict]) -> dict[str, list[dict]]:
        """Group comments by the players they mention."""
        by_player = {}
        
        for comment in comments:
            for player_key in comment['mentioned_players']:
                if player_key not in by_player:
                    by_player[player_key] = []
                by_player[player_key].append(comment)
        
        return by_player
    
    def get_player_info(self, player_key: str) -> Optional[dict]:
        """Get player info by key."""
        return self.players.get(player_key)


# Quick test
if __name__ == '__main__':
    print("Initializing NHL Reddit scraper...")
    scraper = RedditScraper()
    
    print(f"Search index built with {len(scraper.search_index)} terms")
    print(f"Loaded {len(scraper.players)} players")
    
    # Test: Fetch from main subreddit only (quick test)
    print("\n" + "="*50)
    print("TEST: Fetching from r/hockey...")
    print("="*50)
    
    comments = scraper.fetch_recent_comments(limit=100)
    print(f"Found {len(comments)} comments mentioning players")
    
    hot_comments = scraper.fetch_hot_posts_comments(num_posts=5, comments_per_post=30)
    print(f"Found {len(hot_comments)} comments from hot posts")
    
    all_comments = comments + hot_comments
    
    # Group by player
    by_player = scraper.group_comments_by_player(all_comments)
    
    print(f"\n" + "="*50)
    print("PLAYERS MENTIONED (top 15):")
    print("="*50)
    for player_key, player_comments in sorted(by_player.items(), key=lambda x: -len(x[1]))[:15]:
        player = scraper.get_player_info(player_key)
        if player:
            print(f"  {player['name']:25} ({player['team_abbr']}): {len(player_comments)} mentions")
    
    # Show sample comment
    if all_comments:
        print(f"\n" + "="*50)
        print("SAMPLE COMMENT:")
        print("="*50)
        sample = all_comments[0]
        players_mentioned = [scraper.get_player_info(p)['name'] for p in sample['mentioned_players']]
        print(f"Players: {', '.join(players_mentioned)}")
        print(f"Score: {sample['score']}")
        print(f"Subreddit: r/{sample['subreddit']}")
        print(f"Text: {sample['body'][:300]}...")
