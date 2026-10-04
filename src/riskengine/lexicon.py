"""Domain lexicons used by the rule-based NLP layer.

General-purpose sentiment models (VADER, TextBlob) read "liability", "cut" or
"exposure" as neutral and "crushed it" as negative. Finance text needs its own
vocabulary, so the word lists below are hand-curated, loosely in the spirit of
the Loughran-McDonald dictionary, and tuned on the sample feed.
Weights are in roughly [-3, 3]; the scorer normalises the sum later.
"""

# --- sentiment -------------------------------------------------------------

POSITIVE = {
    "beat": 2.0, "beats": 2.0, "beating": 1.8, "record": 1.2, "strong": 1.5,
    "stronger": 1.5, "growth": 1.2, "raise": 1.2, "raised": 1.4, "raises": 1.4,
    "raising": 1.4, "rally": 1.8, "rallied": 1.8, "surge": 1.5, "jumped": 0.8,
    "rose": 1.0, "gain": 1.2, "gains": 1.2, "upgrade": 2.0, "upgraded": 2.0,
    "bullish": 2.5, "outperform": 2.0, "resilient": 1.4, "win": 1.8, "wins": 1.8,
    "settlement": 0.8, "resolve": 1.0, "resolved": 1.0, "positive": 1.5,
    "launch": 0.8, "launched": 0.8, "unveils": 1.0, "impressive": 2.0,
    "monster": 1.5, "synergies": 1.5, "solid": 1.4, "steady": 0.8,
    "stable": 0.8, "smart": 1.2, "love": 1.8, "good": 1.2, "great": 1.8,
    "huge": 1.0, "goat": 1.5, "printing": 1.0, "buy": 1.0, "dismissed": 1.2,
    "expand": 0.8, "boost": 1.4, "lift": 1.0, "adopt": 0.8, "demand": 0.4,
    "removed": 0.6, "approval": 0.8, "completes": 0.8, "completed": 0.8,
    "soar": 2.0, "soars": 2.0, "soared": 2.0, "climbs": 1.2, "rebound": 1.4,
    "upbeat": 1.6, "optimistic": 1.4, "profit": 0.8, "profitable": 1.2,
}

NEGATIVE = {
    "miss": -2.0, "misses": -2.0, "missed": -2.0, "fail": -2.2, "fails": -2.2,
    "failed": -2.2, "failure": -2.4, "halt": -2.0, "halts": -2.0,
    "halted": -2.0, "defect": -2.0, "investigation": -1.4, "probe": -1.4,
    "delay": -1.4, "delayed": -1.6, "delays": -1.4, "warned": -1.2,
    "warn": -1.2, "downgrade": -2.4, "downgraded": -2.4, "junk": -2.5,
    "outflows": -1.8, "losses": -1.8, "loss": -1.6, "fell": -1.4, "fall": -1.2,
    "slumped": -2.0, "slump": -2.0, "sharply": -0.4, "impairment": -2.0,
    "recall": -2.0, "recalling": -2.0, "fine": -1.2, "fined": -2.0,
    "violating": -1.8, "lawsuit": -1.5, "lawsuits": -1.2, "sanctions": -2.0,
    "restrictions": -1.6, "controls": -0.8, "default": -2.6,
    "defaulting": -2.6, "bankruptcy": -3.0, "restructuring": -1.8,
    "contagion": -2.5, "recession": -2.5, "inflation": -1.0, "sticky": -1.0,
    "hike": -1.2, "hotter": -1.2, "ugly": -2.0, "brutal": -2.4,
    "terrible": -2.5, "disappointing": -2.2, "trouble": -2.0, "exposed": -1.2,
    "escalate": -2.0, "escalates": -2.0, "escalating": -2.0,
    "escalation": -2.2, "conflict": -1.8, "war": -2.5, "missile": -2.2,
    "strikes": -1.8, "collapse": -2.6, "collapsed": -2.6, "blockade": -2.4,
    "disruption": -1.8, "sell-off": -2.0, "selloff": -2.0, "killed": -1.8,
    "weak": -1.6, "weakened": -1.6, "stalls": -1.6, "slows": -1.2,
    "cut": -0.8, "cuts": -0.8, "deficit": -1.2, "risk": -0.6, "fears": -1.6,
    "dumping": -1.6, "mistake": -1.8, "tailed": -1.4, "spiking": -1.2,
    "spike": -1.2, "problems": -1.6, "expensive": -1.0, "worse": -1.8,
    "suspend": -1.4, "overhang": -0.8, "concerns": -1.2, "tightened": -1.0,
    "tighten": -1.0, "risk-off": -2.0, "volatile": -1.0,
    "plunge": -2.4, "plunges": -2.4, "plunged": -2.4, "tumble": -2.0,
    "tumbles": -2.0, "tumbled": -2.0, "crash": -2.2, "crashes": -2.2,
    "rout": -2.2, "slides": -1.4, "sinks": -1.8, "layoffs": -1.6,
    "fraud": -3.0, "scandal": -2.4, "lawsuit": -1.5, "warning": -1.4,
}

# Multi-word phrases are matched before single tokens and override them.
PHRASES = {
    "crushed it": 2.5, "higher for longer": -1.8, "no rate cuts": -1.5,
    "no cuts": -1.5, "rate cut": 0.6, "surprise cut": 0.2, "output cut": -0.4,
    "raised guidance": 2.0, "raised its full-year outlook": 2.2,
    "raised full-year guidance": 2.2, "cut revenue guidance": -2.5,
    "cut guidance": -2.5, "beat estimates": 2.2, "above estimates": 2.0,
    "below expectations": -2.0, "beating analyst expectations": 2.2,
    "not a good look": -2.0, "not even close": 1.2, "not trivial": -1.4,
    "not a tail risk anymore": -2.4, "at a loss": -1.8, "chapter 11": -3.0,
    "to the moon": 2.5, "risk off": -2.0, "not bad": 1.2,
    "removing a long-running legal overhang": 1.8, "overhang removed": 1.8,
    "record high": 1.8, "16-year high": -0.6, "primary endpoint": -0.2,
    "safety concerns": -2.0, "quality issue": -2.0,
}

NEGATORS = {"not", "no", "never", "nor", "without", "hardly", "isn't",
            "wasn't", "aren't", "don't", "doesn't", "didn't", "won't", "cannot"}

INTENSIFIERS = {"very": 1.3, "extremely": 1.6, "sharply": 1.3, "significantly": 1.3,
                "absolute": 1.4, "absolutely": 1.4, "huge": 1.3, "massive": 1.5,
                "record": 1.2, "serious": 1.3, "major": 1.3, "honestly": 1.1,
                "really": 1.2, "sweeping": 1.3}

DAMPENERS = {"slightly": 0.6, "somewhat": 0.7, "maybe": 0.7, "possible": 0.8,
             "could": 0.85, "might": 0.8}

EMOJI = {"🚀": 1.5, "🔥": 1.2, "📈": 1.2, "💎": 0.8, "📉": -1.2, "💀": -1.5,
         "😱": -1.2, "🤡": -1.0}

# --- event taxonomy --------------------------------------------------------
# Each class gets weighted triggers; the classifier sums the matches and
# picks the best one. "base_severity" feeds the impact model.

EVENT_TAXONOMY = {
    "Geopolitical": {
        "base_severity": 7.0,
        "triggers": {"geopolitical": 2, "military": 2, "naval": 2, "drills": 1.5,
                     "war": 3, "conflict": 2.5, "ceasefire": 2.5, "missile": 3,
                     "strikes": 1.5, "sanctions": 2.5, "export controls": 3,
                     "blockade": 3, "strait": 1.5, "tensions": 2, "diplomatic": 1.5,
                     "escalation": 1.5, "escalated": 1.5, "escalates": 1.5,
                     "tariff": 2, "tariffs": 2, "embargo": 3, "invasion": 3},
    },
    "Macroeconomic": {
        "base_severity": 6.0,
        "triggers": {"fed": 2.5, "federal reserve": 3, "ecb": 3, "central bank": 3,
                     "inflation": 2.5, "cpi": 3, "interest rate": 2, "rate hike": 2.5,
                     "hike": 1.2, "rate cut": 2, "cuts its deposit rate": 3,
                     "yields": 1.5, "treasury": 1.5, "gdp": 2.5, "unemployment": 3,
                     "payrolls": 3, "recession": 2.5, "growth stalls": 2,
                     "opec": 2.5, "crude": 1.5, "oil": 1, "auction": 1.5,
                     "basis points": 1.5, "financial conditions": 2},
    },
    "Credit Event": {
        "base_severity": 7.5,
        "triggers": {"default": 3, "defaulting": 3, "bankruptcy": 3.5,
                     "chapter 11": 3.5, "downgrade": 2.5, "downgraded": 2.5,
                     "junk": 2.5, "coupon": 2, "missed a coupon": 3.5,
                     "grace period": 2.5, "restructuring": 2, "creditors": 2,
                     "lenders": 1.5, "loan losses": 2.5, "deposit outflows": 2.5,
                     "contagion": 2, "notches": 2, "rating agency": 2.5,
                     "leveraged loan": 2, "distressed": 2},
    },
    "Merger/Acquisition": {
        "base_severity": 5.0,
        "triggers": {"acquire": 3, "acquisition": 3, "merger": 3, "takeover": 3,
                     "buyout": 3, "definitive agreement": 2.5, "deal": 1.2,
                     "divestiture": 2.5, "sell its": 1.5, "to sell": 1.5,
                     "synergies": 2, "all-stock": 2.5, "buying": 1, "dumping": 1},
    },
    "Product Launch": {
        "base_severity": 4.0,
        "triggers": {"launch": 3, "launched": 3, "launches": 3, "unveils": 3,
                     "unveiled": 3, "rolled out": 2.5, "new product": 2.5,
                     "next-generation": 2, "gpu": 1.5, "chip": 0.8, "assistant": 1.2,
                     "product line": 2},
    },
    "Earnings": {
        "base_severity": 5.0,
        "triggers": {"earnings": 3, "quarterly": 2, "revenue": 1.5, "guidance": 2,
                     "estimates": 2, "outlook": 2, "eps": 3, "same-store sales": 2.5,
                     "trading revenue": 2, "beat": 1.5, "quarter": 1.5,
                     "dividend": 1.5},
    },
    "Regulatory/Legal": {
        "base_severity": 5.5,
        "triggers": {"regulator": 2.5, "regulators": 2.5, "fined": 3, "fine": 1,
                     "antitrust": 3, "lawsuit": 2.5, "lawsuits": 2.5, "litigation": 3,
                     "settlement": 2, "settles": 2.5, "recall": 2.5, "recalling": 2.5,
                     "probe": 2, "investigation": 2, "judge": 2.5, "appeal": 1.5,
                     "privacy": 1.5, "safety regulator": 3},
    },
    "Operational": {
        "base_severity": 5.5,
        "triggers": {"defect": 3, "halt": 2, "halts": 2, "deliveries": 1.5,
                     "quality": 1.5, "outage": 3, "cyberattack": 3, "breach": 2.5,
                     "production targets": 2, "manufacturing": 1.5, "yield problems": 2.5,
                     "delayed": 1.5, "phase 3": 2.5, "trial": 2, "endpoint": 2},
    },
}

FALLBACK_EVENT = "General News"
