"""
NHL Sentiment Analysis Dashboard

A Streamlit dashboard displaying sentiment analysis of NHL players 
based on Reddit discussions from r/hockey and team subreddits.

This is a portfolio project demonstrating:
- Web scraping and data collection pipelines
- LLM integration for text sentiment analysis (Claude API)
- Interactive data visualization with Streamlit/Plotly
- Sports analytics methodology

Data: Historical snapshot from May 2026 (243 players analyzed)
Note: Reddit API changes now require OAuth for live data collection.

Features:
- Player sentiment leaderboard
- Team-level sentiment aggregation  
- Player detail cards with analysis summaries
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime
from pathlib import Path
import re
import plotly.express as px

from data_loader import load_players, load_teams, get_player, NHL_TEAMS

# Page config
st.set_page_config(
    page_title="NHL Sentiment Dashboard",
    page_icon="🏒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Clean, minimal CSS
st.markdown("""
<style>
    .stApp {
        background: #f8fafc;
    }
    
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        text-align: center;
        color: #1e293b;
        margin-bottom: 0.25rem;
    }
    
    .sub-header {
        text-align: center;
        color: #64748b;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    [data-testid="stMetricValue"] {
        font-size: 1.8rem;
        color: #1e293b;
    }
    
    [data-testid="stMetricLabel"] {
        color: #64748b;
    }
    
    [data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid #e2e8f0;
    }
    
    .stButton > button {
        background: #3b82f6;
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
    
    .stButton > button:hover {
        background: #2563eb;
    }
    
    .highlight-card {
        background: white;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid #3b82f6;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    .positive-card {
        border-left-color: #22c55e;
    }
    
    .negative-card {
        border-left-color: #ef4444;
    }
</style>
""", unsafe_allow_html=True)


def get_sentiment_emoji(score):
    """Get emoji based on sentiment score."""
    if score > 0.5:
        return "🔥"
    elif score > 0.2:
        return "😊"
    elif score > -0.2:
        return "😐"
    elif score > -0.5:
        return "😟"
    else:
        return "💀"


def get_sentiment_color(score):
    """Get color based on sentiment score."""
    if score > 0.3:
        return "#22c55e"
    elif score < -0.3:
        return "#ef4444"
    else:
        return "#eab308"


def calculate_team_sentiment(results, players):
    """Aggregate player sentiment by team."""
    team_data = {}
    
    for player_key, analysis in results.items():
        player = players.get(player_key, {})
        team_abbr = player.get('team_abbr')
        
        if not team_abbr:
            continue
        
        if team_abbr not in team_data:
            team_data[team_abbr] = {
                'scores': [],
                'comments': 0,
                'players': []
            }
        
        team_data[team_abbr]['scores'].append(analysis['sentiment_score'])
        team_data[team_abbr]['comments'] += analysis['comments_analyzed']
        team_data[team_abbr]['players'].append(analysis['player_name'])
    
    # Calculate averages
    team_results = []
    for team_abbr, data in team_data.items():
        if data['scores']:
            team_info = NHL_TEAMS.get(team_abbr, {})
            team_results.append({
                'team_abbr': team_abbr,
                'team_name': team_info.get('name', team_abbr),
                'avg_sentiment': sum(data['scores']) / len(data['scores']),
                'total_comments': data['comments'],
                'player_count': len(data['players']),
                'players': data['players'],
                'conference': team_info.get('conference', ''),
                'division': team_info.get('division', '')
            })
    
    return sorted(team_results, key=lambda x: x['avg_sentiment'], reverse=True)


def get_comment_highlights(comments, top_n=5):
    """Get most upvoted positive and negative comments."""
    sorted_by_score = sorted(comments, key=lambda x: x.get('score', 0), reverse=True)
    
    highlights = {
        'top_comments': sorted_by_score[:top_n],
        'controversial': sorted([c for c in comments if c.get('score', 0) < 0], 
                                key=lambda x: x.get('score', 0))[:top_n]
    }
    
    return highlights


def render_player_card(analysis, player_info):
    """Render a player sentiment card."""
    score = analysis['sentiment_score']
    emoji = get_sentiment_emoji(score)
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        headshot_url = player_info.get('headshot_url')
        if headshot_url:
            st.image(headshot_url, width=150)
        else:
            st.markdown("🏒")
    
    with col2:
        st.markdown(f"### {emoji} {analysis['player_name']}")
        st.markdown(f"**{analysis['player_team']}** · {player_info.get('position', 'Unknown')}")
        
        normalized_score = (score + 1) / 2
        st.progress(normalized_score)
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            if score > 0:
                st.success(f"Score: **{score:+.2f}**")
            elif score < 0:
                st.error(f"Score: **{score:+.2f}**")
            else:
                st.warning(f"Score: **{score:+.2f}**")
        
        with col_b:
            st.metric("Comments", analysis['comments_analyzed'])
        
        with col_c:
            st.metric("Confidence", f"{analysis.get('confidence', 0.5):.0%}")
        
        st.markdown(f"*{analysis['summary']}*")
        
        themes_html = " ".join([f"`{theme}`" for theme in analysis.get('themes', [])])
        st.markdown(f"**Themes:** {themes_html}")
        
        quotes = analysis.get('notable_quotes', [])
        if quotes:
            st.markdown(f"> \"{quotes[0][:150]}{'...' if len(quotes[0]) > 150 else ''}\"")


def main():
    st.markdown('<h1 class="main-header">🏒 NHL Sentiment Dashboard</h1>', unsafe_allow_html=True)
    st.markdown("<p class='sub-header'>Real-time sentiment analysis from Reddit</p>", unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.markdown("## 🏒 NHL Sentiment")
    st.sidebar.caption("Portfolio Project")
    
    players = load_players()
    teams = load_teams()
    
    # Team filter at top
    st.sidebar.markdown("### 🎯 Filter")
    team_options = ["All Teams"] + sorted([f"{info['name']} ({abbr})" for abbr, info in teams.items()])
    selected_team_display = st.sidebar.selectbox("Team", team_options)
    
    selected_team_abbr = None
    if selected_team_display != "All Teams":
        selected_team_abbr = selected_team_display.split("(")[-1].replace(")", "")
    
    # Auto-load saved data on first run
    if 'results' not in st.session_state:
        # Try multiple possible paths
        possible_paths = [
            Path("data/latest_results.json"),
            Path(__file__).parent / "data" / "latest_results.json",
            Path("./data/latest_results.json"),
        ]
        
        data_file = None
        for p in possible_paths:
            if p.exists():
                data_file = p
                break
        
        if data_file:
            try:
                with open(data_file, 'r', encoding='utf-8') as f:
                    saved_data = json.load(f)
                
                results = saved_data.get('results', {})
                if results:
                    st.session_state['results'] = results
                    st.session_state['comments'] = saved_data.get('comments', [])
                    st.session_state['by_player'] = saved_data.get('by_player', {})
                    st.session_state['last_fetch'] = saved_data.get('timestamp', 'Unknown')
                    st.session_state['from_saved'] = True
            except Exception as e:
                st.sidebar.error(f"Error loading data: {e}")
    
    # About section in sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("### About")
    st.sidebar.markdown("""
    **Live Sentiment Analysis System**
    
    This dashboard was built to **live-scrape** 
    Reddit discussions from r/hockey and all 32 
    team subreddits, then analyze sentiment using 
    Claude AI in real-time.
    
    **Tech Stack:**
    - Python / Streamlit
    - Claude API (sentiment analysis)
    - Reddit live scraping pipeline
    - Plotly visualizations
    """)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Data Note")
    st.sidebar.info("""
    **Snapshot from May 2026 Playoffs**
    
    This data was collected during the playoffs, 
    so some teams may have limited coverage.
    
    Reddit's API now requires OAuth authentication, 
    which blocks the live scraping. The full 
    scraping pipeline is included in the codebase.
    """)
    
    
    # Display results
    if 'results' in st.session_state and st.session_state['results']:
        results = st.session_state['results']
        by_player = st.session_state.get('by_player', {})
        all_comments = st.session_state.get('comments', [])
        
        # Summary stats
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        
        scores = [r['sentiment_score'] for r in results.values()]
        
        with col1:
            st.metric("Players", len(results))
        with col2:
            avg_score = sum(scores) / len(scores) if scores else 0
            st.metric("Avg Sentiment", f"{avg_score:+.2f}")
        with col3:
            positive = sum(1 for s in scores if s > 0.2)
            st.metric("Positive", f"{positive} 🟢")
        with col4:
            negative = sum(1 for s in scores if s < -0.2)
            st.metric("Negative", f"{negative} 🔴")
        
        # Tabs
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 Leaderboard", 
            "🏒 Teams", 
            "💬 Highlights",
            "🔍 Player Details"
        ])
        
        # TAB 1: Leaderboard
        with tab1:
            col_a, col_b = st.columns([2, 1])
            with col_a:
                st.markdown("### Sentiment Leaderboard")
            with col_b:
                sort_option = st.selectbox(
                    "Sort by",
                    ["Most Positive", "Most Negative", "Most Discussed"],
                    label_visibility="collapsed",
                    key="leaderboard_sort"
                )
            
            # Filter by team if selected
            filtered_results = results
            if selected_team_abbr:
                filtered_results = {k: v for k, v in results.items() 
                                   if players.get(k, {}).get('team_abbr') == selected_team_abbr}
                st.caption(f"Showing {len(filtered_results)} players from {selected_team_display}")
            
            if sort_option == "Most Positive":
                sorted_results = sorted(filtered_results.items(), key=lambda x: x[1]['sentiment_score'], reverse=True)
            elif sort_option == "Most Negative":
                sorted_results = sorted(filtered_results.items(), key=lambda x: x[1]['sentiment_score'])
            else:
                sorted_results = sorted(filtered_results.items(), key=lambda x: x[1]['comments_analyzed'], reverse=True)
            
            leaderboard_data = []
            for player_key, analysis in sorted_results:
                player = players.get(player_key, {})
                score = analysis['sentiment_score']
                leaderboard_data.append({
                    "#": len(leaderboard_data) + 1,
                    "Player": analysis['player_name'],
                    "Team": player.get('team_abbr', ''),
                    "Pos": player.get('position', ''),
                    "Score": f"{score:+.2f}",
                    "": get_sentiment_emoji(score),
                    "Comments": analysis['comments_analyzed'],
                    "Summary": analysis['summary'][:50] + "..."
                })
            
            df = pd.DataFrame(leaderboard_data)
            st.dataframe(df, use_container_width=True, hide_index=True, height=400)
        
        # TAB 2: Team Sentiment
        with tab2:
            st.markdown("### Team Sentiment Rankings")
            
            team_sentiment = calculate_team_sentiment(results, players)
            
            if team_sentiment:
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    team_df = pd.DataFrame([{
                        "#": i + 1,
                        "Team": t['team_name'],
                        "Abbr": t['team_abbr'],
                        "Sentiment": f"{t['avg_sentiment']:+.2f}",
                        "": get_sentiment_emoji(t['avg_sentiment']),
                        "Players": t['player_count'],
                        "Comments": t['total_comments'],
                        "Conference": t['conference']
                    } for i, t in enumerate(team_sentiment)])
                    
                    st.dataframe(team_df, use_container_width=True, hide_index=True, height=400)
                
                with col2:
                    fig = px.bar(
                        team_sentiment[:10],
                        x='avg_sentiment',
                        y='team_abbr',
                        orientation='h',
                        color='avg_sentiment',
                        color_continuous_scale=['#ef4444', '#eab308', '#22c55e'],
                        title='Top 10 Teams by Sentiment'
                    )
                    fig.update_layout(height=400, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Not enough data to calculate team sentiment.")
        
        # TAB 3: Comment Highlights
        with tab3:
            st.markdown("### Comment Highlights")
            
            if not all_comments:
                st.info("📊 Comment highlights not available for this historical dataset. This tab displays top comments when collecting live data.")
            else:
                highlights = get_comment_highlights(all_comments, top_n=5)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### 🔥 Most Upvoted Comments")
                    if highlights['top_comments']:
                        for comment in highlights['top_comments']:
                            with st.container():
                                st.markdown(f"""
                                <div class="highlight-card positive-card">
                                    <strong>⬆️ {comment.get('score', 0)} points</strong> · r/{comment.get('subreddit', 'hockey')}<br>
                                    <p style="margin: 8px 0;">{comment.get('body', '')[:300]}{'...' if len(comment.get('body', '')) > 300 else ''}</p>
                                </div>
                                """, unsafe_allow_html=True)
                    else:
                        st.info("No comments to display.")
                
                with col2:
                    st.markdown("#### 💀 Most Controversial Comments")
                    if highlights['controversial']:
                        for comment in highlights['controversial']:
                            with st.container():
                                st.markdown(f"""
                                <div class="highlight-card negative-card">
                                    <strong>⬇️ {comment.get('score', 0)} points</strong> · r/{comment.get('subreddit', 'hockey')}<br>
                                    <p style="margin: 8px 0;">{comment.get('body', '')[:300]}{'...' if len(comment.get('body', '')) > 300 else ''}</p>
                                </div>
                                """, unsafe_allow_html=True)
                    else:
                        st.info("No controversial comments found.")
        
        # TAB 4: Player Details
        with tab4:
            st.markdown("### Player Details")
            
            # Team filter for player selection
            col1, col2 = st.columns([1, 2])
            with col1:
                detail_teams = ["All Teams"] + sorted(set(
                    players.get(k, {}).get('team_abbr', '') 
                    for k in results.keys() 
                    if players.get(k, {}).get('team_abbr')
                ))
                detail_team = st.selectbox("Filter by Team", detail_teams, key="details_team")
            
            # Filter players by selected team
            if detail_team == "All Teams":
                filtered_player_names = {analysis['player_name']: key for key, analysis in results.items()}
            else:
                filtered_player_names = {
                    analysis['player_name']: key 
                    for key, analysis in results.items() 
                    if players.get(key, {}).get('team_abbr') == detail_team
                }
            
            with col2:
                if filtered_player_names:
                    selected_player = st.selectbox(
                        "Select a player", 
                        sorted(filtered_player_names.keys()), 
                        key="details_player"
                    )
                else:
                    selected_player = None
                    st.info("No players found for this team.")
            
            if selected_player:
                player_key = filtered_player_names[selected_player]
                analysis = results[player_key]
                player_info = players.get(player_key, {})
                
                render_player_card(analysis, player_info)
    
    else:
        # Welcome screen when no data loaded
        st.markdown("---")
        st.warning("No data loaded. Please ensure the data files are in the correct location.")
        st.markdown("""
        ### Expected file structure:
        ```
        nhl_sentiment_dashboard/
        └── data/
            └── latest_results.json
        ```
        """)


if __name__ == "__main__":
    main()
