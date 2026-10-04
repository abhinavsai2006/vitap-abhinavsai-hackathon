"""RiskEngine: wires ingestion and the analysers together and publishes signals."""
from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable

from .models import Document, RiskSignal
from .nlp import (EntityLinker, EventClassifier, LexiconSentiment, impact_score,
                  sentiment_label)

MARKET = "MARKET"


class RiskEngine:
    def __init__(self, universe_csv: str | Path, sentiment_backend=None):
        self.linker = EntityLinker(universe_csv)
        self.sentiment = sentiment_backend or LexiconSentiment()
        self.events = EventClassifier()
        self.signals: list[RiskSignal] = []
        self._subscribers: list[Callable[[RiskSignal], None]] = []

    # simple in-process pub/sub - downstream modules register a callback
    def subscribe(self, fn: Callable[[RiskSignal], None]) -> None:
        self._subscribers.append(fn)

    def analyze(self, doc: Document) -> list[RiskSignal]:
        text = doc.full_text
        score, sent_hits = self.sentiment.score(text)
        event, conf, ev_hits = self.events.classify(text)
        entities = self.linker.link(text) or [MARKET]
        impact = impact_score(event, score, text, doc.source, doc.reach, len(entities))

        headline = doc.title or (doc.text[:110] + ("..." if len(doc.text) > 110 else ""))
        out = []
        for ent in entities:
            out.append(RiskSignal(
                signal_id=f"{doc.doc_id}-{ent}",
                doc_id=doc.doc_id,
                source=doc.source,
                timestamp=doc.published_at.isoformat(),
                entity=ent,
                sentiment_score=score,
                sentiment_label=sentiment_label(score),
                event_type=event,
                event_confidence=conf,
                impact_score=impact,
                headline=headline,
                keywords=sorted(set(sent_hits + ev_hits))[:10],
            ))
        return out

    def process(self, docs: Iterable[Document]) -> list[RiskSignal]:
        new = []
        for doc in docs:
            for sig in self.analyze(doc):
                self.signals.append(sig)
                new.append(sig)
                for fn in self._subscribers:
                    fn(sig)
        return new

    # --- outputs ------------------------------------------------------------

    def write_jsonl(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            for s in self.signals:
                fh.write(json.dumps(s.to_dict(), ensure_ascii=False) + "\n")
        return path

    def entity_summary(self, as_of: datetime | None = None, half_life_h: float = 24.0) -> dict:
        """Impact-weighted, time-decayed sentiment per entity.

        A strongly negative 9/10 event should outweigh a mildly positive tweet,
        and yesterday's news should matter less than this morning's.
        """
        if not self.signals:
            return {}
        as_of = as_of or max(datetime.fromisoformat(s.timestamp) for s in self.signals)
        acc = defaultdict(lambda: [0.0, 0.0, 0, 0.0])  # num, den, count, max impact
        for s in self.signals:
            age_h = (as_of - datetime.fromisoformat(s.timestamp)).total_seconds() / 3600
            if age_h < 0:
                continue
            w = s.impact_score * 0.5 ** (age_h / half_life_h)
            a = acc[s.entity]
            a[0] += w * s.sentiment_score
            a[1] += w
            a[2] += 1
            a[3] = max(a[3], s.impact_score)
        return {
            e: {"sentiment": round(n / d, 3) if d else 0.0, "mentions": c, "max_impact": m}
            for e, (n, d, c, m) in sorted(acc.items())
        }


def load_signals(path: str | Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]
