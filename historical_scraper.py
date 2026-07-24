"""
NHL Historical Scraper

One-time script to scrape top posts from the entire season.
Run this ONCE to build your baseline historical data.
Then use daily_update.py to add new data incrementally.

This will take 30-60 minutes due to Reddit rate limits.
"""

import json
import time
from datetime import datetime
from pathlib import Path

from data_loader import load_players
from roster_scraper import TEAMS_BY_ABBR as NHL_TEAMS
from reddit_scraper import RedditScraper
from sentiment_analyzer import SentimentAnalyzer

# Output directory
OUTPUT_DIR = Path(__file__).parent / "data"
OUTPUT_DIR.mkdir(exist_ok=True)


def fetch_historical_comments(scraper, time_filter="year"):
    """
    Fetch comments from top posts across the season.
    
    time_filter options: "year", "month", "week", "all"
    """
    all_comments = []
    seen_ids = set()
    
    def add_comments(comments):
        for c in comments:
            if c['id'] not in seen_ids:
                seen_ids.add(c['id'])
                all_comments.append(c)
    
    # 1. Fetch from r/hockey - top posts from the year
    print("\n" + "="*50)
    print("FETCHING FROM r/hockey")
    print("="*50)
    
    print(f"\nFetching top posts ({time_filter})...")
    add_comments(scraper.fetch_top_posts_comments("hockey", time_filter=time_filter, num_posts=50, comments_per_post=100))
    print(f"  Total comments so far: {len(all_comments)}")
    
    print("\nFetching hot posts...")
    add_comments(scraper.fetch_hot_posts_comments("hockey", num_posts=25, comments_per_post=75))
    print(f"  Total comments so far: {len(all_comments)}")
    
    print("\nFetching recent comments...")
    add_comments(scraper.fetch_recent_comments("hockey", limit=100))
    print(f"  Total comments so far: {len(all_comments)}")
    
    # 2. Fetch from each team subreddit
    print("\n" + "="*50)
    print("FETCHING FROM TEAM SUBREDDITS")
    print("="*50)
    
    team_subs = [(abbr, info['subreddit']) for abbr, info in NHL_TEAMS.items()]
    
    for i, (team_abbr, sub_name) in enumerate(team_subs):
        print(f"\n[{i+1}/{len(team_subs)}] r/{sub_name}...")
        
        # Top posts from the season
        add_comments(scraper.fetch_top_posts_comments(sub_name, time_filter=time_filter, num_posts=15, comments_per_post=50))
        
        # Hot posts
        add_comments(scraper.fetch_hot_posts_comments(sub_name, num_posts=10, comments_per_post=40))
        
        print(f"  Total comments: {len(all_comments)}")
    
    return all_comments


def analyze_and_save(comments, scraper, analyzer, players):
    """Analyze comments and save results."""
    
    # Group by player
    by_player = scraper.group_comments_by_player(comments)
    
    print(f"\n" + "="*50)
    print(f"ANALYZING {len(by_player)} PLAYERS")
    print("="*50)
    
    # Analyze each player with enough comments
    results = {}
    min_comments = 3
    
    eligible = {k: v for k, v in by_player.items() if len(v) >= min_comments and k in players}
    
    for i, (player_key, player_comments) in enumerate(eligible.items()):
        player = players.get(player_key)
        if not player:
            continue
        
        print(f"[{i+1}/{len(eligible)}] {player['name']} ({len(player_comments)} comments)...")
        
        analysis = analyzer.analyze_player_sentiment(
            player_name=player['name'],
            player_team=player.get('team', 'Unknown'),
            comments=player_comments
        )
        
        if analysis:
            results[player_key] = analysis
            print(f"  → Sentiment: {analysis['sentiment_score']:+.2f}")
    
    return results, by_player


def save_historical_data(results, by_player, comments):
    """Save all data to files."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    # Save sentiment results
    results_file = OUTPUT_DIR / f"sentiment_results_{timestamp}.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nSaved results to {results_file}")
    
    # Save raw comments (for future analysis)
    comments_file = OUTPUT_DIR / f"comments_{timestamp}.json"
    with open(comments_file, 'w', encoding='utf-8') as f:
        json.dump(comments, f, indent=2, default=str)
    print(f"Saved {len(comments)} comments to {comments_file}")
    
    # Save current snapshot as "latest"
    latest_file = OUTPUT_DIR / "latest_results.json"
    with open(latest_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': timestamp,
            'results': results,
            'comment_count': len(comments),
            'player_count': len(results)
        }, f, indent=2, default=str)
    print(f"Saved latest snapshot to {latest_file}")
    
    # Save history log
    history_file = OUTPUT_DIR / "history.json"
    history = []
    if history_file.exists():
        with open(history_file, 'r') as f:
            history = json.load(f)
    
    history.append({
        'timestamp': timestamp,
        'comment_count': len(comments),
        'player_count': len(results),
        'avg_sentiment': sum(r['sentiment_score'] for r in results.values()) / len(results) if results else 0
    })
    
    with open(history_file, 'w') as f:
        json.dump(history, f, indent=2)
    print(f"Updated history log")
    
    return results_file, comments_file


def main():
    print("="*60)
    print("NHL HISTORICAL SENTIMENT SCRAPER")
    print("="*60)
    print("\nThis will scrape top posts from the entire season.")
    print("Expected time: 30-60 minutes (Reddit rate limits)")
    print("\nPress Ctrl+C to cancel, or wait 5 seconds to continue...")
    
    try:
        time.sleep(5)
    except KeyboardInterrupt:
        print("\nCancelled.")
        return
    
    # Initialize
    print("\nLoading players from Wikipedia...")
    players = load_players(force_refresh=True)
    print(f"Loaded {len(players)} players")
    
    print("\nInitializing scraper...")
    scraper = RedditScraper()
    
    print("\nInitializing sentiment analyzer...")
    analyzer = SentimentAnalyzer()
    
    # Fetch historical comments
    start_time = time.time()
    comments = fetch_historical_comments(scraper, time_filter="year")
    fetch_time = time.time() - start_time
    
    print(f"\n✅ Fetched {len(comments)} comments in {fetch_time/60:.1f} minutes")
    
    # Analyze
    start_time = time.time()
    results, by_player = analyze_and_save(comments, scraper, analyzer, players)
    analyze_time = time.time() - start_time
    
    print(f"\n✅ Analyzed {len(results)} players in {analyze_time/60:.1f} minutes")
    
    # Save
    save_historical_data(results, by_player, comments)
    
    # Summary
    print("\n" + "="*60)
    print("COMPLETE!")
    print("="*60)
    print(f"Total comments: {len(comments)}")
    print(f"Players analyzed: {len(results)}")
    print(f"Total time: {(fetch_time + analyze_time)/60:.1f} minutes")
    
    # Top/bottom players
    sorted_results = sorted(results.items(), key=lambda x: x[1]['sentiment_score'], reverse=True)
    
    print("\n🔥 Most Loved Players:")
    for key, analysis in sorted_results[:5]:
        print(f"  {analysis['player_name']}: {analysis['sentiment_score']:+.2f}")
    
    print("\n💀 Most Hated Players:")
    for key, analysis in sorted_results[-5:]:
        print(f"  {analysis['player_name']}: {analysis['sentiment_score']:+.2f}")


if __name__ == "__main__":
    main()
