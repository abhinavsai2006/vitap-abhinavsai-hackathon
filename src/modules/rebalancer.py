"""Module A - tactical, sentiment-driven index rebalancer.

The mock index starts from the base weights in data/universe.csv. Each stock
keeps an exponentially smoothed sentiment state that is updated every time the
engine publishes a signal about it. At every rebalance the target weight is

    w_i  ∝  base_i * exp(k * s_i)

then clipped to [floor, cap] x base, re-normalised, and blended with the
previous weights so a single tweet can't swing the book (turnover control).

Market-wide signals (entity == "MARKET") are ignored by default: a fully
invested index can't express a view on "the market", and shifting every name
by the same amount only distorts relative weights through the clipping.
Set market_beta > 0 to let them through anyway.
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RebalancerConfig:
    tilt: float = 1.2              # k - how aggressively sentiment moves weights
    smoothing: float = 0.5         # weight given to a new signal in the EWMA
    min_mult: float = 0.4          # weight floor as a multiple of base weight
    max_mult: float = 2.0          # weight cap as a multiple of base weight
    max_single_weight: float = 0.15
    max_turnover: float = 0.10     # max one-way turnover per rebalance
    market_beta: float = 0.0       # how much MARKET signals bleed into every name
    min_impact: float = 3.0        # ignore low-impact noise


@dataclass
class IndexRebalancer:
    base_weights: dict[str, float]
    config: RebalancerConfig = field(default_factory=RebalancerConfig)

    def __post_init__(self):
        total = sum(self.base_weights.values())
        self.base_weights = {t: w / total for t, w in self.base_weights.items()}
        self.weights = dict(self.base_weights)
        self.sentiment = {t: 0.0 for t in self.base_weights}
        self.history: list[dict] = []
        self.trades: list[dict] = []

    @classmethod
    def from_universe(cls, path: str | Path, config: RebalancerConfig | None = None):
        with Path(path).open(encoding="utf-8") as fh:
            base = {r["ticker"]: float(r["base_weight"]) for r in csv.DictReader(fh)}
        return cls(base, config or RebalancerConfig())

    # --- signal handling -----------------------------------------------------

    def on_signal(self, sig: dict) -> None:
        """Consume one engine signal (dict form) and rebalance."""
        if sig["impact_score"] < self.config.min_impact:
            return
        # stronger events update the state more
        alpha = self.config.smoothing * min(sig["impact_score"] / 7.0, 1.3)
        alpha = min(alpha, 0.9)
        s = sig["sentiment_score"]
        if sig["entity"] in self.sentiment:
            targets = {sig["entity"]: alpha}
        elif sig["entity"] == "MARKET" and self.config.market_beta > 0:
            targets = {t: alpha * self.config.market_beta for t in self.sentiment}
        else:
            return
        for t, a in targets.items():
            self.sentiment[t] = (1 - a) * self.sentiment[t] + a * s
        self._rebalance(sig)

    def _target(self) -> dict[str, float]:
        c = self.config
        raw = {}
        for t, base in self.base_weights.items():
            mult = math.exp(c.tilt * self.sentiment[t])
            raw[t] = base * min(max(mult, c.min_mult), c.max_mult)
        total = sum(raw.values())
        tgt = {t: w / total for t, w in raw.items()}
        # enforce single-name cap, redistributing the excess pro rata; the cap
        # has to stay feasible for small universes (n * cap must exceed 100%)
        cap = max(c.max_single_weight, 1.5 / len(tgt))
        for _ in range(5):
            over = {t: w - cap for t, w in tgt.items() if w > cap}
            if not over:
                break
            excess = sum(over.values())
            under = {t: w for t, w in tgt.items() if t not in over}
            u_total = sum(under.values())
            for t in over:
                tgt[t] = cap
            for t, w in under.items():
                tgt[t] = w + excess * w / u_total
        return tgt

    def _rebalance(self, sig: dict) -> None:
        target = self._target()
        turnover = 0.5 * sum(abs(target[t] - self.weights[t]) for t in target)
        step = 1.0 if turnover <= self.config.max_turnover else self.config.max_turnover / turnover
        new = {t: self.weights[t] + step * (target[t] - self.weights[t]) for t in target}

        for t in new:
            delta = new[t] - self.weights[t]
            if abs(delta) > 0.001:
                self.trades.append({"timestamp": sig["timestamp"], "ticker": t,
                                    "delta_weight": round(delta, 5),
                                    "trigger": sig["signal_id"]})
        self.weights = new
        self.history.append({"timestamp": sig["timestamp"], "trigger": sig["signal_id"],
                             "turnover": round(turnover * step, 5),
                             **{t: round(w, 5) for t, w in new.items()}})

    def run(self, signals: list[dict]) -> "IndexRebalancer":
        for s in sorted(signals, key=lambda x: x["timestamp"]):
            self.on_signal(s)
        return self

    def snapshot(self) -> list[dict]:
        return [{"ticker": t, "base_weight": round(self.base_weights[t], 4),
                 "current_weight": round(self.weights[t], 4),
                 "active_weight": round(self.weights[t] - self.base_weights[t], 4),
                 "smoothed_sentiment": round(self.sentiment[t], 3)}
                for t in sorted(self.weights, key=lambda x: -self.weights[x])]
