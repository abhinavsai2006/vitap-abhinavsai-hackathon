"""The three analysers: entity linking, sentiment, event classification, impact.

Everything here is deterministic and explainable on purpose - for a risk desk
it matters more that an analyst can see *why* a headline scored -0.7 than to
squeeze out a few points of accuracy. A transformer backend (FinBERT) can be
switched on for sentiment if `transformers` is installed; see FinBertSentiment.
"""
from __future__ import annotations

import csv
import math
import re
from pathlib import Path

from .lexicon import (DAMPENERS, EMOJI, EVENT_TAXONOMY, FALLBACK_EVENT,
                      INTENSIFIERS, NEGATIVE, NEGATORS, PHRASES, POSITIVE)

TOKEN_RE = re.compile(r"\$?[a-z][a-z0-9&'\-]*|\d+(?:\.\d+)?%?", re.I)


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]


# --- entity linking --------------------------------------------------------

class EntityLinker:
    """Maps cashtags and company aliases to tickers in the tracked universe."""

    def __init__(self, universe_csv: str | Path):
        self.tickers: dict[str, dict] = {}
        self._patterns: list[tuple[re.Pattern, str]] = []
        with Path(universe_csv).open(encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                t = row["ticker"].upper()
                self.tickers[t] = row
                for alias in row["aliases"].split("|"):
                    pat = re.compile(r"(?<![\w$])" + re.escape(alias) + r"(?!\w)", re.I)
                    self._patterns.append((pat, t))

    def link(self, text: str) -> list[str]:
        found: list[str] = []
        for tag in re.findall(r"\$([A-Za-z]{1,5})\b", text):
            if tag.upper() in self.tickers and tag.upper() not in found:
                found.append(tag.upper())
        for pat, ticker in self._patterns:
            if ticker not in found and pat.search(text):
                found.append(ticker)
        return found


# --- sentiment -------------------------------------------------------------

class LexiconSentiment:
    """Lexicon scorer with phrase matching, negation and intensity handling."""

    NEGATION_WINDOW = 3

    def score(self, text: str) -> tuple[float, list[str]]:
        lowered = text.lower()
        total, hits = 0.0, []

        # phrases first; blank them out so their words aren't double counted
        for phrase, w in sorted(PHRASES.items(), key=lambda kv: -len(kv[0])):
            if phrase in lowered:
                total += w
                hits.append(phrase)
                lowered = lowered.replace(phrase, " ")

        tokens = tokenize(lowered)
        for i, tok in enumerate(tokens):
            word = tok.lstrip("$")
            w = POSITIVE.get(word) or NEGATIVE.get(word)
            if not w:
                continue
            window = tokens[max(0, i - self.NEGATION_WINDOW):i]
            if any(t in NEGATORS for t in window):
                w *= -0.6          # "not good" is weaker than "bad"
            if i and tokens[i - 1] in INTENSIFIERS:
                w *= INTENSIFIERS[tokens[i - 1]]
            if i and tokens[i - 1] in DAMPENERS:
                w *= DAMPENERS[tokens[i - 1]]
            total += w
            hits.append(word)

        for emo, w in EMOJI.items():
            n = text.count(emo)
            if n:
                total += w * n
                hits.append(emo)

        if text.count("!") >= 1 and total:
            total *= 1.1

        # squash into (-1, 1); alpha controls how fast long texts saturate
        score = total / math.sqrt(total * total + 15)
        return round(score, 3), hits


class FinBertSentiment:
    """Optional transformer backend. Only used when explicitly requested."""

    def __init__(self, model_name: str = "ProsusAI/finbert"):
        from transformers import pipeline  # imported lazily: heavy dependency
        self._clf = pipeline("text-classification", model=model_name, top_k=None)

    def score(self, text: str) -> tuple[float, list[str]]:
        probs = {d["label"].lower(): d["score"] for d in self._clf(text[:512])[0]}
        return round(probs.get("positive", 0) - probs.get("negative", 0), 3), []


def sentiment_label(score: float, band: float = 0.15) -> str:
    if score > band:
        return "positive"
    if score < -band:
        return "negative"
    return "neutral"


# --- event classification --------------------------------------------------

class EventClassifier:
    """Weighted keyword voting over the taxonomy in lexicon.py."""

    def classify(self, text: str) -> tuple[str, float, list[str]]:
        lowered = f" {text.lower()} "
        scores: dict[str, float] = {}
        matched: dict[str, list[str]] = {}
        for label, spec in EVENT_TAXONOMY.items():
            s = 0.0
            for trig, w in spec["triggers"].items():
                if re.search(r"(?<![a-z])" + re.escape(trig) + r"(?![a-z])", lowered):
                    s += w
                    matched.setdefault(label, []).append(trig)
            if s:
                scores[label] = s
        if not scores:
            return FALLBACK_EVENT, 0.0, []
        best = max(scores, key=scores.get)
        confidence = scores[best] / sum(scores.values())
        return best, round(confidence, 2), matched[best]


# --- impact ----------------------------------------------------------------

MAGNITUDE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(%|percent|billion|bn|basis points|million)", re.I)
SHOCK_WORDS = {"record", "surprise", "unexpected", "unexpectedly", "sharply", "collapse",
               "collapsed", "escalation", "contagion", "two notches", "two notch",
               "sweeping", "halt", "halts", "junk", "chapter 11", "default"}


def impact_score(event_type: str, sentiment: float, text: str, source: str,
                 reach: int = 0, n_entities: int = 1) -> float:
    """Severity on a 1-10 scale.

    Starts from the event class's base severity and adjusts for: how strongly
    the text leans either way, quantitative magnitude cues ("7%", "$16 billion"),
    shock vocabulary, breadth (how many names are hit) and source credibility.
    Negative news is weighted ~25% heavier than positive - markets react
    asymmetrically and this is a *risk* engine.
    """
    base = EVENT_TAXONOMY.get(event_type, {}).get("base_severity", 3.5)
    lowered = text.lower()

    tone = abs(sentiment) * (2.5 if sentiment < 0 else 2.0)

    magnitude = 0.0
    for num, unit in MAGNITUDE_RE.findall(text):
        v = float(num)
        unit = unit.lower()
        if unit in ("%", "percent"):
            magnitude = max(magnitude, min(v / 3, 1.5))
        elif unit in ("billion", "bn"):
            magnitude = max(magnitude, min(math.log10(v + 1), 1.5))
        elif unit == "basis points":
            magnitude = max(magnitude, min(v / 50, 1.0))

    shock = min(sum(1 for w in SHOCK_WORDS if w in lowered) * 0.5, 1.5)
    breadth = min((n_entities - 1) * 0.3, 0.9) if n_entities > 1 else 0.0

    if source == "social":
        # unverified chatter is discounted, unless the account has real reach
        credibility = -1.5 + min(math.log10(reach + 1) / 5.5, 1.0)
    else:
        credibility = 0.0

    raw = base - 2.0 + tone + magnitude + shock + breadth + credibility
    return round(max(1.0, min(10.0, raw)), 1)
