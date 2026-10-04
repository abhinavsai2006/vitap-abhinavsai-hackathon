"""End-to-end batch run: ingest -> analyse -> publish -> downstream modules."""
from __future__ import annotations

import csv
import json

from . import config
from .modules import IndexRebalancer, StressTester, load_portfolio
from .riskengine import NewsCsvSource, RiskEngine, SocialJsonSource, load_all


def build_engine() -> RiskEngine:
    return RiskEngine(config.UNIVERSE_CSV)


def run(rss_url: str | None = None, verbose: bool = True) -> dict:
    sources = [NewsCsvSource(config.NEWS_CSV), SocialJsonSource(config.SOCIAL_JSON)]
    if rss_url:
        from .riskengine import RssSource
        sources.append(RssSource(rss_url))
    docs = load_all(sources)

    engine = build_engine()
    rebalancer = IndexRebalancer.from_universe(config.UNIVERSE_CSV)
    tester = StressTester(load_portfolio(config.PORTFOLIO_CSV))

    # downstream modules subscribe to the live signal stream
    engine.subscribe(lambda s: rebalancer.on_signal(s.to_dict()))
    engine.subscribe(lambda s: tester.on_signal(s.to_dict()))
    engine.process(docs)

    engine.write_jsonl(config.SIGNALS_JSONL)

    with config.WEIGHTS_CSV.open("w", newline="", encoding="utf-8") as fh:
        if rebalancer.history:
            w = csv.DictWriter(fh, fieldnames=list(rebalancer.history[0]))
            w.writeheader()
            w.writerows(rebalancer.history)

    config.STRESS_JSON.write_text(json.dumps(tester.triggered, indent=2, default=float),
                                  encoding="utf-8")

    if verbose:
        _print_report(docs, engine, rebalancer, tester)
    return {"docs": len(docs), "signals": len(engine.signals),
            "stress_tests": len(tester.triggered)}


def _print_report(docs, engine, rebalancer, tester) -> None:
    print(f"\nIngested {len(docs)} documents "
          f"({sum(d.source == 'news' for d in docs)} news, "
          f"{sum(d.source == 'social' for d in docs)} social)")
    print(f"Published {len(engine.signals)} risk signals -> {config.SIGNALS_JSONL}\n")

    print(f"{'time':<17} {'src':<6} {'entity':<7} {'sent':>6} {'event':<19} {'imp':>4}  headline")
    for s in engine.signals[:12]:
        print(f"{s.timestamp[:16]:<17} {s.source:<6} {s.entity:<7} {s.sentiment_score:>6.2f} "
              f"{s.event_type:<19} {s.impact_score:>4.1f}  {s.headline[:48]}")
    print("  ...\n")

    print("Module A - final index weights (top movers)")
    snap = sorted(rebalancer.snapshot(), key=lambda r: -abs(r["active_weight"]))[:6]
    for r in snap:
        print(f"  {r['ticker']:<6} base {r['base_weight']:.2%} -> {r['current_weight']:.2%} "
              f"({r['active_weight']:+.2%})  sentiment {r['smoothed_sentiment']:+.2f}")

    print(f"\nModule B - {len(tester.triggered)} stress tests triggered "
          f"(impact > {tester.impact_threshold})")
    for t in tester.triggered:
        print(f"  {t['timestamp'][:16]}  {t['event_type']:<14} impact {t['impact_score']:.1f}  "
              f"P&L {t['pnl'] / 1e6:+.2f}m ({t['pnl_pct']:+.2%})  {t['headline'][:45]}")
    print()
