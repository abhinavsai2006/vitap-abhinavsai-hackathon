from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime


@dataclass
class Document:
    """A single piece of raw text, normalised across sources."""
    doc_id: str
    source: str            # "news" | "social" | "rss" | "api"
    published_at: datetime
    text: str
    title: str = ""
    author: str = ""
    reach: int = 0         # followers / readership proxy, 0 if unknown

    @property
    def full_text(self) -> str:
        return f"{self.title}. {self.text}" if self.title else self.text


@dataclass
class RiskSignal:
    """The structured output of the engine - one per (document, entity)."""
    signal_id: str
    doc_id: str
    source: str
    timestamp: str
    entity: str            # ticker, or "MARKET" for macro / unattributed news
    sentiment_score: float  # -1.0 .. 1.0
    sentiment_label: str
    event_type: str
    event_confidence: float
    impact_score: float     # 1 .. 10
    headline: str
    keywords: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
