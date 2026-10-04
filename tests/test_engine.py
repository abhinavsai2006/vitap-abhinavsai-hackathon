from datetime import datetime, timezone

import pytest

from src import config
from src.modules import IndexRebalancer, StressTester, load_portfolio
from src.modules.stress_test import scenario_key
from src.riskengine import Document, NewsCsvSource, RiskEngine, SocialJsonSource, load_all
from src.riskengine.nlp import EventClassifier, LexiconSentiment, impact_score


@pytest.fixture(scope="module")
def engine():
    return RiskEngine(config.UNIVERSE_CSV)


def doc(text, source="news", reach=0):
    return Document("T", source, datetime(2026, 9, 1, tzinfo=timezone.utc), text, reach=reach)


# --- ingestion ---------------------------------------------------------------

def test_both_sources_load_and_sort():
    docs = load_all([NewsCsvSource(config.NEWS_CSV), SocialJsonSource(config.SOCIAL_JSON)])
    assert {d.source for d in docs} == {"news", "social"}
    assert docs == sorted(docs, key=lambda d: d.published_at)


# --- sentiment ---------------------------------------------------------------

@pytest.mark.parametrize("text,sign", [
    ("Apple beats estimates and raises its dividend", 1),
    ("Boeing halts deliveries after a new defect", -1),
    ("The company reported results", 0),
])
def test_sentiment_direction(text, sign):
    score, _ = LexiconSentiment().score(text)
    assert -1 <= score <= 1
    if sign == 0:
        assert abs(score) < 0.15
    else:
        assert score * sign > 0.15


def test_negation_flips_sentiment():
    pos, _ = LexiconSentiment().score("results were good")
    neg, _ = LexiconSentiment().score("results were not good")
    assert pos > 0 > neg


def test_finance_phrases():
    assert LexiconSentiment().score("$AAPL crushed it")[0] > 0.3
    assert LexiconSentiment().score("rates higher for longer")[0] < 0


# --- events ------------------------------------------------------------------

@pytest.mark.parametrize("text,label", [
    ("Missile strikes reported as the conflict escalates", "Geopolitical"),
    ("CPI inflation surprises, Fed signals rate hike", "Macroeconomic"),
    ("Issuer files for Chapter 11 after defaulting on its loan", "Credit Event"),
    ("Microsoft to acquire rival in $10 billion merger", "Merger/Acquisition"),
    ("Nvidia unveils next-generation GPU", "Product Launch"),
])
def test_event_classification(text, label):
    assert EventClassifier().classify(text)[0] == label


def test_unknown_text_falls_back():
    assert EventClassifier().classify("lunch was nice")[0] == "General News"


# --- impact ------------------------------------------------------------------

def test_impact_bounds_and_ordering():
    big = impact_score("Credit Event", -0.95, "sovereign default, downgraded two notches", "news")
    small = impact_score("Product Launch", 0.3, "new flavour launched", "news")
    assert 1 <= small < big <= 10


def test_social_is_discounted_vs_news():
    text = "Bank downgraded to junk on deposit outflows"
    assert impact_score("Credit Event", -0.9, text, "social", reach=500) < \
        impact_score("Credit Event", -0.9, text, "news")


# --- engine ------------------------------------------------------------------

def test_engine_links_cashtags_and_aliases(engine):
    out = engine.analyze(doc("$NVDA and Apple hit by new export controls"))
    assert {s.entity for s in out} == {"NVDA", "AAPL"}
    s = out[0]
    assert s.event_type == "Geopolitical" and s.sentiment_score < 0 and 1 <= s.impact_score <= 10


def test_unlinked_text_goes_to_market(engine):
    assert engine.analyze(doc("Unemployment jumps as recession fears grow"))[0].entity == "MARKET"


def test_subscribers_receive_signals():
    e = RiskEngine(config.UNIVERSE_CSV)
    got = []
    e.subscribe(got.append)
    e.process([doc("Tesla recalls cars after safety probe")])
    assert len(got) == 1 and got[0].entity == "TSLA"


# --- module A ----------------------------------------------------------------

def _sig(entity, s, impact=7.0, ts="2026-09-01T00:00:00+00:00"):
    return {"entity": entity, "sentiment_score": s, "impact_score": impact,
            "timestamp": ts, "signal_id": f"x-{entity}"}


def test_rebalancer_moves_weights_with_sentiment():
    reb = IndexRebalancer({"A": 0.5, "B": 0.5})
    reb.on_signal(_sig("A", 0.9))
    assert reb.weights["A"] > 0.5 > reb.weights["B"]
    assert sum(reb.weights.values()) == pytest.approx(1.0)


def test_rebalancer_respects_turnover_limit():
    reb = IndexRebalancer({"A": 0.5, "B": 0.5})
    reb.config.max_turnover = 0.02
    reb.on_signal(_sig("A", -1.0, impact=10))
    assert reb.history[-1]["turnover"] <= 0.02 + 1e-9


def test_rebalancer_ignores_low_impact():
    reb = IndexRebalancer({"A": 0.5, "B": 0.5})
    reb.on_signal(_sig("A", 1.0, impact=1.0))
    assert reb.weights == {"A": 0.5, "B": 0.5}


# --- module B ----------------------------------------------------------------

def test_stress_triggers_only_above_threshold():
    t = StressTester(load_portfolio(config.PORTFOLIO_CSV), impact_threshold=7)
    base = {"doc_id": "D1", "entity": "MARKET", "event_type": "Geopolitical", "sentiment_score": -0.9,
            "timestamp": "2026-09-01T00:00:00+00:00", "headline": "war", "source": "news"}
    assert t.on_signal({**base, "impact_score": 6.5}) is None
    res = t.on_signal({**base, "impact_score": 8.5})
    assert res and res["pnl"] < 0
    # same story again two hours later is not stressed twice
    assert t.on_signal({**base, "doc_id": "D2", "impact_score": 9,
                        "timestamp": "2026-09-01T02:00:00+00:00"}) is None


def test_higher_impact_means_bigger_loss():
    t = StressTester(load_portfolio(config.PORTFOLIO_CSV))
    assert t.run_scenario("Credit Event", 9.5)["pnl"] < t.run_scenario("Credit Event", 7.0)["pnl"]


def test_pay_fixed_swap_gains_when_rates_rise():
    t = StressTester(load_portfolio(config.PORTFOLIO_CSV))
    swap = next(r for r in t.run_scenario("Macroeconomic", 8)["positions"] if r["trade_id"] == "T1013")
    assert swap["rates"] > 0


def test_macro_scenario_direction():
    assert scenario_key("Macroeconomic", "ECB unexpectedly cuts rates") == "Macroeconomic/Growth"
    assert scenario_key("Macroeconomic", "Fed signals no rate cuts this year") == "Macroeconomic"
