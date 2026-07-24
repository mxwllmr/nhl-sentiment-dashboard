"""
Convert old data format to new dashboard format.
Run this once to make your May 16 data work with the current dashboard.
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

def convert():
    # Load old sentiment results
    old_results_file = DATA_DIR / "sentiment_results_2026-05-16_14-17-12.json"
    old_comments_file = DATA_DIR / "comments_2026-05-16_14-17-12.json"
    
    print("Loading old data...")
    
    with open(old_results_file, 'r', encoding='utf-8') as f:
        results = json.load(f)
    print(f"  Loaded {len(results)} player results")
    
    comments = []
    if old_comments_file.exists():
        with open(old_comments_file, 'r', encoding='utf-8') as f:
            comments = json.load(f)
        print(f"  Loaded {len(comments)} comments")
    
    # Create new format
    new_data = {
        'timestamp': '2026-05-16',
        'results': results,
        'comments': comments,
        'by_player': {},  # We don't have this but dashboard can work without it
        'comment_count': len(comments),
        'player_count': len(results)
    }
    
    # Save as latest_results.json
    output_file = DATA_DIR / "latest_results.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, indent=2, default=str)
    
    print(f"\n✅ Created {output_file}")
    print(f"   {len(results)} players, {len(comments)} comments")
    print("\nNow refresh your dashboard!")

if __name__ == "__main__":
    convert()
