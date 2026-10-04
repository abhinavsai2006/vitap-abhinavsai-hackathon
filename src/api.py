"""REST API exposing the engine's signals to downstream consumers.

    uvicorn src.api:app --reload      (or: python main.py api)
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from . import config
from .modules import SCENARIOS, StressTester, load_portfolio
from .pipeline import build_engine, run
from .riskengine import Document, load_signals

app = FastAPI(title="RiskPulse - AI/NLP Risk Engine",
              description="Structured risk signals from unstructured news and social text.",
              version="1.0.0")

engine = build_engine()


def _signals() -> list[dict]:
    if not config.SIGNALS_JSONL.exists():
        run(verbose=False)
    return load_signals(config.SIGNALS_JSONL)


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=3, examples=["$NVDA slumps after export controls cut China revenue"])
    source: str = Field("api", examples=["news", "social"])
    followers: int = 0


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/signals")
def signals(entity: str | None = None, event_type: str | None = None,
            min_impact: float = Query(0, ge=0, le=10), limit: int = Query(200, le=1000)):
    out = _signals()
    if entity:
        out = [s for s in out if s["entity"] == entity.upper()]
    if event_type:
        out = [s for s in out if s["event_type"].lower() == event_type.lower()]
    out = [s for s in out if s["impact_score"] >= min_impact]
    return out[-limit:]


@app.get("/signals/summary")
def summary():
    e = build_engine()
    from .riskengine.models import RiskSignal
    e.signals = [RiskSignal(**s) for s in _signals()]
    return e.entity_summary()


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    doc = Document(doc_id="ADHOC", source=req.source, published_at=datetime.now(timezone.utc),
                   text=req.text, reach=req.followers)
    return [s.to_dict() for s in engine.analyze(doc)]


@app.get("/stress/{event_type}")
def stress(event_type: str, impact: float = Query(8.0, ge=1, le=10)):
    match = next((k for k in SCENARIOS if k.lower() == event_type.lower()), None)
    if not match:
        raise HTTPException(404, f"No scenario for '{event_type}'. Options: {list(SCENARIOS)}")
    res = StressTester(load_portfolio(config.PORTFOLIO_CSV)).run_scenario(match, impact)
    res.pop("positions")
    return res


@app.post("/refresh")
def refresh():
    return run(verbose=False)
