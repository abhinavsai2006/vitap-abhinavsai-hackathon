"""Module B - event-driven stress testing of a synthetic wholesale banking book.

Valuation is first-order sensitivity based (duration / spread duration / delta),
which is the standard "quick" approach a risk desk uses for intraday what-ifs:

    rates     dV = -mod_duration    * dr  * exposure
    credit    dV = -spread_duration * ds  * exposure      (ds depends on rating)
    equity    dV =  equity_delta    * dE  * exposure
    fx        dV =  fx_delta        * dFX * exposure
    default   dV = -EAD * LGD * PD * (pd_multiplier - 1)  (loans: extra expected loss)

Exposure is market value for cash instruments and notional for derivatives,
because a swap's sensitivity scales with notional, not with its (small) MTM.

Scenarios are keyed by event type and scaled by the engine's impact score, so a
9.5/10 geopolitical shock hurts more than a 7.2/10 one.
"""
from __future__ import annotations

import csv
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path

RATING_BUCKET = {
    "AAA": "IG", "AA+": "IG", "AA": "IG", "AA-": "IG", "A+": "IG", "A": "IG",
    "A-": "IG", "BBB+": "IG", "BBB": "IG", "BBB-": "IG",
    "BB+": "HY", "BB": "HY", "BB-": "HY", "B+": "HY", "B": "HY", "B-": "HY",
    "CCC+": "DISTRESSED", "CCC": "DISTRESSED", "CCC-": "DISTRESSED",
}


@dataclass
class Scenario:
    name: str
    description: str
    rates_bp: float                 # parallel shift in rates
    spread_bp: dict[str, float]     # by rating bucket
    equity_pct: float
    fx_pct: float                   # move in EUR/USD (negative = USD strengthens)
    oil_pct: float
    pd_multiplier: float
    sector_equity: dict[str, float] = field(default_factory=dict)  # overrides
    sector_spread_bp: dict[str, float] = field(default_factory=dict)  # add-ons
    region_spread_bp: dict[str, float] = field(default_factory=dict)

    def scaled(self, k: float) -> "Scenario":
        return Scenario(
            name=self.name, description=self.description,
            rates_bp=self.rates_bp * k,
            spread_bp={b: v * k for b, v in self.spread_bp.items()},
            equity_pct=self.equity_pct * k, fx_pct=self.fx_pct * k,
            oil_pct=self.oil_pct * k,
            pd_multiplier=1 + (self.pd_multiplier - 1) * k,
            sector_equity={s: v * k for s, v in self.sector_equity.items()},
            sector_spread_bp={s: v * k for s, v in self.sector_spread_bp.items()},
            region_spread_bp={r: v * k for r, v in self.region_spread_bp.items()},
        )


SCENARIOS: dict[str, Scenario] = {
    "Geopolitical": Scenario(
        "Geopolitical escalation",
        "Risk-off: equities sell off, flight to quality pulls yields down, "
        "credit spreads widen, oil spikes, USD strengthens.",
        rates_bp=-25, spread_bp={"IG": 40, "HY": 150, "DISTRESSED": 400},
        equity_pct=-0.10, fx_pct=-0.04, oil_pct=0.20, pd_multiplier=1.35,
        sector_equity={"Information Technology": -0.15},
        region_spread_bp={"APAC": 60, "EMEA": 30},
    ),
    "Macroeconomic": Scenario(
        "Hawkish rates shock",
        "Hot inflation / hawkish central bank: +100bp parallel rates shift, "
        "equities de-rate, spreads widen moderately.",
        rates_bp=100, spread_bp={"IG": 25, "HY": 90, "DISTRESSED": 250},
        equity_pct=-0.08, fx_pct=0.0, oil_pct=0.0, pd_multiplier=1.20,
        sector_spread_bp={"Real Estate": 60},
    ),
    "Macroeconomic/Growth": Scenario(
        "Growth scare",
        "Weak data or a surprise easing: yields fall, equities and cyclical "
        "credit sell off, defaults pick up.",
        rates_bp=-60, spread_bp={"IG": 30, "HY": 120, "DISTRESSED": 300},
        equity_pct=-0.07, fx_pct=-0.02, oil_pct=-0.10, pd_multiplier=1.30,
        sector_equity={"Financials": -0.10},
    ),
    "Credit Event": Scenario(
        "Credit contagion",
        "A major default or downgrade spills over: spreads gap wider, bank and "
        "property names hit hardest, defaults double.",
        rates_bp=-15, spread_bp={"IG": 60, "HY": 250, "DISTRESSED": 800},
        equity_pct=-0.07, fx_pct=-0.02, oil_pct=-0.05, pd_multiplier=2.0,
        sector_equity={"Financials": -0.18},
        sector_spread_bp={"Financials": 50, "Real Estate": 150},
        region_spread_bp={"LATAM": 120, "APAC": 50},
    ),
}


GROWTH_WORDS = ("unemployment", "payrolls", "recession", "cuts", "cut its", "rate cut",
                "growth stalls", "slows", "gdp contracts")


def scenario_key(event_type: str, text: str) -> str:
    """Macro news can go either way for rates - pick the right variant."""
    if event_type == "Macroeconomic":
        lowered = text.lower()
        if any(w in lowered for w in GROWTH_WORDS) and "no rate cuts" not in lowered:
            return "Macroeconomic/Growth"
    return event_type


@dataclass
class Position:
    trade_id: str
    counterparty: str
    asset_class: str
    instrument: str
    sector: str
    region: str
    notional: float
    market_value: float
    rating: str
    mod_duration: float
    spread_duration: float
    equity_delta: float
    fx_delta: float
    pd: float
    lgd: float

    @property
    def exposure(self) -> float:
        return self.notional if self.asset_class == "Derivative" else self.market_value


def load_portfolio(path: str | Path) -> list[Position]:
    out = []
    with Path(path).open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out.append(Position(
                trade_id=r["trade_id"], counterparty=r["counterparty"],
                asset_class=r["asset_class"], instrument=r["instrument"],
                sector=r["sector"], region=r["region"],
                notional=float(r["notional"]), market_value=float(r["market_value"]),
                rating=r["rating"], mod_duration=float(r["mod_duration"]),
                spread_duration=float(r["spread_duration"]),
                equity_delta=float(r["equity_delta"]), fx_delta=float(r["fx_delta"]),
                pd=float(r["pd"]), lgd=float(r["lgd"]),
            ))
    return out


def shock_position(p: Position, sc: Scenario) -> dict:
    exp = p.exposure
    bucket = RATING_BUCKET.get(p.rating, "IG")

    d_rates = -p.mod_duration * (sc.rates_bp / 1e4) * exp

    ds = sc.spread_bp.get(bucket, 0) + sc.sector_spread_bp.get(p.sector, 0) \
        + sc.region_spread_bp.get(p.region, 0)
    d_credit = -p.spread_duration * (ds / 1e4) * exp

    eq = sc.sector_equity.get(p.sector, sc.equity_pct)
    d_equity = p.equity_delta * eq * exp
    d_fx = p.fx_delta * sc.fx_pct * exp

    # jet fuel swap: the bank receives floating, so it gains when oil rises
    d_commodity = 0.5 * sc.oil_pct * exp if p.sector == "Commodities" else 0.0

    d_default = 0.0
    if p.asset_class == "Loan":
        d_default = -exp * p.lgd * p.pd * (sc.pd_multiplier - 1)

    pnl = d_rates + d_credit + d_equity + d_fx + d_commodity + d_default
    return {
        "trade_id": p.trade_id, "counterparty": p.counterparty,
        "asset_class": p.asset_class, "instrument": p.instrument,
        "sector": p.sector, "region": p.region, "rating": p.rating,
        "value_before": p.market_value, "value_after": p.market_value + pnl,
        "pnl": pnl, "rates": d_rates, "credit_spread": d_credit,
        "equity": d_equity, "fx": d_fx, "commodity": d_commodity,
        "default_loss": d_default,
    }


@dataclass
class StressTester:
    portfolio: list[Position]
    impact_threshold: float = 7.0
    cooldown_hours: float = 12.0   # same event type within this window = same story
    scenarios: dict[str, Scenario] = field(default_factory=lambda: dict(SCENARIOS))
    triggered: list[dict] = field(default_factory=list)

    @property
    def base_value(self) -> float:
        return sum(p.market_value for p in self.portfolio)

    def run_scenario(self, event_type: str, impact: float = 8.0) -> dict:
        # impact 8 = scenario as written; 10 = 1.25x; 7 = 0.875x
        k = max(0.75, min(impact / 8.0, 1.3))
        sc = self.scenarios[event_type].scaled(k)
        event_type = event_type.split("/")[0]
        rows = [shock_position(p, sc) for p in self.portfolio]
        before = self.base_value
        after = sum(r["value_after"] for r in rows)
        return {
            "event_type": event_type, "scenario": sc.name,
            "description": sc.description, "impact_score": impact, "scale": round(k, 3),
            "shocks": {"rates_bp": round(sc.rates_bp, 1),
                       "spread_bp": {b: round(v, 1) for b, v in sc.spread_bp.items()},
                       "equity_pct": round(sc.equity_pct, 4), "fx_pct": round(sc.fx_pct, 4),
                       "oil_pct": round(sc.oil_pct, 4),
                       "pd_multiplier": round(sc.pd_multiplier, 3)},
            "value_before": before, "value_after": after,
            "pnl": after - before, "pnl_pct": (after - before) / before,
            "positions": rows,
        }

    def on_signal(self, sig: dict) -> dict | None:
        if sig["impact_score"] <= self.impact_threshold:
            return None
        key = scenario_key(sig["event_type"], sig["headline"])
        if key not in self.scenarios:
            return None
        # several tickers share one document, and the same story shows up in
        # news and then social - only stress it once per cooldown window
        ts = datetime.fromisoformat(sig["timestamp"])
        for t in self.triggered:
            if t["doc_id"] == sig["doc_id"]:
                return None
            if t["scenario_key"] == key and                     abs((ts - datetime.fromisoformat(t["timestamp"])).total_seconds()) < self.cooldown_hours * 3600:
                return None
        result = self.run_scenario(key, sig["impact_score"])
        result["scenario_key"] = key
        result.update({"doc_id": sig["doc_id"], "timestamp": sig["timestamp"],
                       "headline": sig["headline"], "source": sig["source"]})
        self.triggered.append(result)
        return result

    def run(self, signals: list[dict]) -> list[dict]:
        for s in sorted(signals, key=lambda x: x["timestamp"]):
            self.on_signal(s)
        return self.triggered
