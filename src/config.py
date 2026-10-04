from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUTPUT = ROOT / "output"

UNIVERSE_CSV = DATA / "universe.csv"
NEWS_CSV = DATA / "news_feed.csv"
SOCIAL_JSON = DATA / "social_posts.json"
PORTFOLIO_CSV = DATA / "portfolio_transactions.csv"

SIGNALS_JSONL = OUTPUT / "signals.jsonl"
WEIGHTS_CSV = OUTPUT / "index_weights_history.csv"
STRESS_JSON = OUTPUT / "stress_results.json"
