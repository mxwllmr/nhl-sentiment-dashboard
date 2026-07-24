"""
Sentiment analyzer for NHL player comments.

Uses Claude API to analyze Reddit comments and extract:
- Sentiment score
- Summary of discourse
- Key themes
- Notable quotes
"""

import anthropic
import json
from datetime import datetime
from typing import Optional


# Your Anthropic API key
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


class SentimentAnalyzer:
    """
    Analyzes sentiment of Reddit comments about NHL players using Claude.
    """
    
    def __init__(self, api_key: str = ANTHROPIC_API_KEY):
        """Initialize the sentiment analyzer with Anthropic API key."""
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"
    
    def analyze_player_sentiment(
        self,
        player_name: str,
        player_team: str,
        comments: list[dict],
        max_comments: int = 30
    ) -> Optional[dict]:
        """
        Analyze sentiment for a single player based on their comments.
        """
        if not comments:
            return None
        
        selected_comments = comments[:max_comments]
        
        comments_text = "\n\n".join([
            f"[Score: {c['score']}] {c['body'][:500]}"
            for c in selected_comments
        ])
        
        prompt = f"""Analyze the following Reddit comments about NHL player {player_name} ({player_team}).

COMMENTS:
{comments_text}

Analyze the overall sentiment and discourse about this player. Return your analysis as JSON with this exact structure:
{{
    "sentiment_score": <float from -1.0 (very negative) to 1.0 (very positive)>,
    "confidence": <float from 0.0 to 1.0 indicating how confident you are>,
    "summary": "<one sentence summarizing what fans are saying>",
    "themes": ["<theme 1>", "<theme 2>", "<theme 3>"],
    "notable_quotes": ["<quote 1>", "<quote 2>"],
    "sentiment_breakdown": {{
        "positive_percentage": <int 0-100>,
        "negative_percentage": <int 0-100>,
        "neutral_percentage": <int 0-100>
    }}
}}

Guidelines:
- sentiment_score: -1.0 = extremely negative, 0 = neutral, 1.0 = extremely positive
- themes: 2-4 main topics being discussed (e.g., "performance", "contract", "trade rumors", "playoffs", "injury")
- notable_quotes: Pick 2 representative quotes that capture the overall sentiment (keep them short)
- Be objective and base your analysis only on the comments provided

Return ONLY the JSON object, no other text."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            response_text = response.content[0].text.strip()
            
            try:
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0]
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0]
                
                analysis = json.loads(response_text)
                
                analysis['player_name'] = player_name
                analysis['player_team'] = player_team
                analysis['comments_analyzed'] = len(selected_comments)
                analysis['analyzed_at'] = datetime.now().isoformat()
                
                return analysis
                
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON response for {player_name}: {e}")
                return None
                
        except anthropic.APIError as e:
            print(f"API error analyzing {player_name}: {e}")
            return None
        except Exception as e:
            print(f"Error analyzing {player_name}: {e}")
            return None
    
    def analyze_multiple_players(
        self,
        comments_by_player: dict[str, list[dict]],
        player_info: dict[str, dict],
        min_comments: int = 3,
        progress_callback=None
    ) -> dict[str, dict]:
        """
        Analyze sentiment for multiple players.
        """
        results = {}
        
        eligible_players = {
            k: v for k, v in comments_by_player.items()
            if len(v) >= min_comments and k in player_info
        }
        
        total = len(eligible_players)
        print(f"Analyzing sentiment for {total} players...")
        
        for i, (player_key, comments) in enumerate(eligible_players.items()):
            player = player_info[player_key]
            player_name = player['name']
            player_team = player.get('team', 'Unknown')
            
            if progress_callback:
                progress_callback(i + 1, total, player_name)
            
            print(f"  [{i+1}/{total}] {player_name} ({len(comments)} comments)...")
            
            analysis = self.analyze_player_sentiment(
                player_name=player_name,
                player_team=player_team,
                comments=comments
            )
            
            if analysis:
                results[player_key] = analysis
                print(f"    → Sentiment: {analysis['sentiment_score']:.2f}")
            else:
                print(f"    → Failed to analyze")
        
        return results


def test_api_connection(api_key: str = ANTHROPIC_API_KEY) -> bool:
    """Test if the Anthropic API key is working."""
    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=50,
            messages=[
                {"role": "user", "content": "Say 'API working!' and nothing else."}
            ]
        )
        print(f"✓ API connection successful: {response.content[0].text}")
        return True
    except anthropic.AuthenticationError:
        print("✗ API authentication failed - check your API key")
        return False
    except Exception as e:
        print(f"✗ API connection failed: {e}")
        return False


if __name__ == '__main__':
    print("Testing Anthropic API connection...")
    if not test_api_connection():
        print("\nPlease check your API key.")
        exit(1)
    
    print("\n" + "="*50)
    print("Running test with Reddit data...")
    print("="*50)
    
    from reddit_scraper import RedditScraper
    
    scraper = RedditScraper()
    
    print("\nFetching comments from Reddit...")
    comments = scraper.fetch_recent_comments(limit=100)
    hot_comments = scraper.fetch_hot_posts_comments(num_posts=5, comments_per_post=30)
    all_comments = comments + hot_comments
    
    print(f"Total comments: {len(all_comments)}")
    
    by_player = scraper.group_comments_by_player(all_comments)
    player_info = {k: scraper.get_player_info(k) for k in by_player.keys()}
    player_info = {k: v for k, v in player_info.items() if v is not None}
    
    analyzer = SentimentAnalyzer()
    results = analyzer.analyze_multiple_players(by_player, player_info, min_comments=2)
    
    print("\n" + "="*50)
    print("SENTIMENT ANALYSIS RESULTS")
    print("="*50)
    
    sorted_results = sorted(results.items(), key=lambda x: x[1]['sentiment_score'], reverse=True)
    
    for player_key, analysis in sorted_results:
        score = analysis['sentiment_score']
        
        if score > 0.3:
            indicator = "🟢"
        elif score < -0.3:
            indicator = "🔴"
        else:
            indicator = "🟡"
        
        print(f"\n{indicator} {analysis['player_name']} ({analysis['player_team']})")
        print(f"   Score: {score:+.2f}")
        print(f"   Summary: {analysis['summary']}")
        print(f"   Themes: {', '.join(analysis['themes'])}")
