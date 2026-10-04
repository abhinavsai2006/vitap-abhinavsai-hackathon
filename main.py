"""RiskPulse command line.

    python main.py run                  # batch pipeline, writes output/
    python main.py analyze "text..."    # score a single piece of text
    python main.py api                  # start the REST API on :8000
    python main.py dashboard            # launch the Streamlit dashboard
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone

from src.pipeline import build_engine, run
from src.riskengine import Document


def main() -> None:
    parser = argparse.ArgumentParser(description="RiskPulse - AI/NLP risk engine")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="run the full pipeline on the sample data")
    p_run.add_argument("--rss", help="optional live RSS feed URL to ingest as a third source")

    p_an = sub.add_parser("analyze", help="analyse a single piece of text")
    p_an.add_argument("text")
    p_an.add_argument("--source", default="news", choices=["news", "social"])

    p_api = sub.add_parser("api", help="serve signals over HTTP")
    p_api.add_argument("--port", type=int, default=8000)

    sub.add_parser("dashboard", help="open the Streamlit dashboard")

    args = parser.parse_args()

    if args.cmd == "run":
        run(rss_url=args.rss)
    elif args.cmd == "analyze":
        doc = Document("CLI", args.source, datetime.now(timezone.utc), args.text)
        for s in build_engine().analyze(doc):
            print(json.dumps(s.to_dict(), indent=2, ensure_ascii=False))
    elif args.cmd == "api":
        import uvicorn
        uvicorn.run("src.api:app", host="127.0.0.1", port=args.port)
    elif args.cmd == "dashboard":
        subprocess.run([sys.executable, "-m", "streamlit", "run", "src/dashboard.py"])


if __name__ == "__main__":
    main()
