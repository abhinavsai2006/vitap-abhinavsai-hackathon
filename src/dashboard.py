"""Streamlit dashboard: signal feed, Module A (rebalancer), Module B (stress test).

    streamlit run src/dashboard.py
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config  # noqa: E402
from src.modules import (SCENARIOS, IndexRebalancer, RebalancerConfig,  # noqa: E402
                         StressTester, load_portfolio)
from src.pipeline import build_engine, run  # noqa: E402
from src.riskengine import Document, load_signals  # noqa: E402

st.set_page_config(page_title="RiskPulse", layout="wide")

NEG, POS, NEUTRAL = "#c0392b", "#1e8449", "#7f8c8d"


@st.cache_data
def get_signals() -> pd.DataFrame:
    if not config.SIGNALS_JSONL.exists():
        run(verbose=False)
    df = pd.DataFrame(load_signals(config.SIGNALS_JSONL))
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


@st.cache_resource
def get_engine():
    return build_engine()


def money(x: float) -> str:
    return f"{'-' if x < 0 else ''}${abs(x) / 1e6:,.1f}m"


signals = get_signals()
records = signals.assign(timestamp=signals["timestamp"].astype(str)).to_dict("records")

st.title("RiskPulse")
st.caption("AI/NLP risk engine turning news and social chatter into structured risk signals")

with st.sidebar:
    st.header("Settings")
    st.subheader("Index rebalancer")
    tilt = st.slider("Sentiment tilt (k)", 0.0, 3.0, 1.2, 0.1)
    max_turnover = st.slider("Max turnover per rebalance", 0.02, 0.5, 0.10, 0.01)
    max_name = st.slider("Single-name cap", 0.08, 0.30, 0.15, 0.01)
    st.subheader("Stress testing")
    threshold = st.slider("Impact trigger threshold", 5.0, 9.5, 7.0, 0.5)
    if st.button("Re-run pipeline"):
        run(verbose=False)
        st.cache_data.clear()
        st.rerun()

tab_feed, tab_a, tab_b, tab_try = st.tabs(
    ["Signal feed", "Module A - Index rebalancer", "Module B - Stress test", "Try the engine"])

# --- signal feed -------------------------------------------------------------
with tab_feed:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Documents", signals["doc_id"].nunique())
    c2.metric("Signals", len(signals))
    c3.metric("Avg sentiment", f"{signals['sentiment_score'].mean():+.2f}")
    c4.metric("High-impact (>7)", int((signals["impact_score"] > 7).sum()))

    left, right = st.columns([3, 2])
    with left:
        fig = px.scatter(signals, x="timestamp", y="sentiment_score", size="impact_score",
                         color="event_type", hover_data=["entity", "headline", "source"],
                         title="Signals over time (bubble size = impact)")
        fig.add_hline(y=0, line_dash="dot", line_color=NEUTRAL)
        st.plotly_chart(fig, use_container_width=True)
    with right:
        counts = signals.drop_duplicates("doc_id")["event_type"].value_counts().reset_index()
        counts.columns = ["event_type", "count"]
        st.plotly_chart(px.bar(counts, x="count", y="event_type", orientation="h",
                               title="Event classification mix"), use_container_width=True)

    ent = (signals[signals["entity"] != "MARKET"]
           .groupby("entity")
           .apply(lambda g: pd.Series({
               "sentiment": (g["sentiment_score"] * g["impact_score"]).sum() / g["impact_score"].sum(),
               "mentions": len(g), "max_impact": g["impact_score"].max()}), include_groups=False)
           .reset_index().sort_values("sentiment"))
    fig = px.bar(ent, x="sentiment", y="entity", orientation="h", color="sentiment",
                 color_continuous_scale=[NEG, "#f4f6f6", POS], range_color=[-1, 1],
                 title="Impact-weighted sentiment by company")
    st.plotly_chart(fig, use_container_width=True)

    f1, f2, f3 = st.columns(3)
    pick_src = f1.multiselect("Source", sorted(signals["source"].unique()))
    pick_evt = f2.multiselect("Event type", sorted(signals["event_type"].unique()))
    pick_ent = f3.multiselect("Entity", sorted(signals["entity"].unique()))
    view = signals
    if pick_src:
        view = view[view["source"].isin(pick_src)]
    if pick_evt:
        view = view[view["event_type"].isin(pick_evt)]
    if pick_ent:
        view = view[view["entity"].isin(pick_ent)]
    st.dataframe(view[["timestamp", "source", "entity", "sentiment_score", "sentiment_label",
                       "event_type", "event_confidence", "impact_score", "headline"]]
                 .sort_values("timestamp", ascending=False),
                 use_container_width=True, hide_index=True)

# --- module A ----------------------------------------------------------------
with tab_a:
    cfg = RebalancerConfig(tilt=tilt, max_turnover=max_turnover, max_single_weight=max_name)
    reb = IndexRebalancer.from_universe(config.UNIVERSE_CSV, cfg).run(records)
    hist = pd.DataFrame(reb.history)
    tickers = list(reb.base_weights)

    if hist.empty:
        st.info("No signals passed the impact filter.")
    else:
        hist["timestamp"] = pd.to_datetime(hist["timestamp"])
        start = {"timestamp": hist["timestamp"].min() - pd.Timedelta(hours=1), **reb.base_weights}
        hist = pd.concat([pd.DataFrame([start]), hist], ignore_index=True)

        st.markdown("Weights move toward names with positive news flow and away from names "
                    "with negative flow, subject to a floor/cap and a turnover limit.")
        long = hist.melt(id_vars="timestamp", value_vars=tickers, var_name="ticker", value_name="weight")
        fig = px.area(long, x="timestamp", y="weight", color="ticker",
                      title="Index weights over time")
        fig.update_layout(yaxis_tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)

        snap = pd.DataFrame(reb.snapshot())
        l, r = st.columns(2)
        with l:
            fig = go.Figure()
            fig.add_bar(x=snap["ticker"], y=snap["base_weight"], name="Base", marker_color="#aab7b8")
            fig.add_bar(x=snap["ticker"], y=snap["current_weight"], name="Current", marker_color="#2e86c1")
            fig.update_layout(barmode="group", title="Base vs current weight", yaxis_tickformat=".0%")
            st.plotly_chart(fig, use_container_width=True)
        with r:
            snap_sorted = snap.sort_values("active_weight")
            fig = px.bar(snap_sorted, x="active_weight", y="ticker", orientation="h",
                         color=snap_sorted["active_weight"] > 0,
                         color_discrete_map={True: POS, False: NEG}, title="Active weight vs base")
            fig.update_layout(showlegend=False, xaxis_tickformat=".1%")
            st.plotly_chart(fig, use_container_width=True)

        pick = st.multiselect("Drill into tickers", tickers, default=["AAPL", "NVDA", "BA", "INTC"])
        if pick:
            fig = px.line(hist, x="timestamp", y=pick, title="Selected weights", line_shape="hv")
            fig.update_layout(yaxis_tickformat=".1%")
            st.plotly_chart(fig, use_container_width=True)

        st.caption(f"{len(reb.history)} rebalances, total one-way turnover "
                   f"{pd.DataFrame(reb.history)['turnover'].sum():.1%}")
        st.dataframe(snap, use_container_width=True, hide_index=True)

# --- module B ----------------------------------------------------------------
with tab_b:
    portfolio = load_portfolio(config.PORTFOLIO_CSV)
    tester = StressTester(portfolio, impact_threshold=threshold)
    triggered = tester.run(records)

    pf = pd.DataFrame([p.__dict__ for p in portfolio])
    c1, c2, c3 = st.columns(3)
    c1.metric("Portfolio value", money(tester.base_value))
    c2.metric("Positions", len(pf))
    c3.metric("Stress tests triggered", len(triggered))

    with st.expander("Synthetic wholesale banking book"):
        st.plotly_chart(px.sunburst(pf, path=["asset_class", "sector", "counterparty"],
                                    values=pf["market_value"].abs(), title="Composition by market value"),
                        use_container_width=True)
        st.dataframe(pf, use_container_width=True, hide_index=True)

    if not triggered:
        st.info("No event crossed the impact threshold. Lower it in the sidebar or use the manual scenario below.")
        options = []
    else:
        tl = pd.DataFrame([{k: t[k] for k in ("timestamp", "event_type", "impact_score", "pnl",
                                             "headline", "source")} for t in triggered])
        tl["timestamp"] = pd.to_datetime(tl["timestamp"])
        fig = px.scatter(tl, x="timestamp", y="pnl", size="impact_score", color="event_type",
                         hover_data=["headline"], title="Triggered stress tests - P&L impact")
        st.plotly_chart(fig, use_container_width=True)
        options = [f"{t['timestamp'][:16]} | {t['event_type']} | {t['impact_score']} | {t['headline'][:60]}"
                   for t in triggered]

    st.subheader("Scenario detail")
    mode = st.radio("Show", ["Triggered event", "Manual scenario"], horizontal=True,
                    index=0 if options else 1)
    if mode == "Triggered event" and options:
        res = triggered[options.index(st.selectbox("Event", options))]
    else:
        m1, m2 = st.columns(2)
        evt = m1.selectbox("Event type", list(SCENARIOS))
        imp = m2.slider("Impact score", 1.0, 10.0, 8.5, 0.5)
        res = tester.run_scenario(evt, imp)

    st.markdown(f"**{res['scenario']}** - {res['description']}")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Value before", money(res["value_before"]))
    k2.metric("Value after", money(res["value_after"]), f"{res['pnl_pct']:+.2%}")
    k3.metric("Stress P&L", money(res["pnl"]))
    k4.metric("Scale vs base scenario", f"{res['scale']:.2f}x")

    pos = pd.DataFrame(res["positions"])
    l, r = st.columns(2)
    with l:
        fig = go.Figure()
        fig.add_bar(name="Before", x=["Portfolio"], y=[res["value_before"]], marker_color="#aab7b8")
        fig.add_bar(name="After", x=["Portfolio"], y=[res["value_after"]],
                    marker_color=NEG if res["pnl"] < 0 else POS)
        fig.update_layout(barmode="group", title="Portfolio value before vs after",
                          yaxis_range=[res["value_before"] * 0.85, res["value_before"] * 1.02])
        st.plotly_chart(fig, use_container_width=True)
    with r:
        drivers = pos[["rates", "credit_spread", "equity", "fx", "commodity", "default_loss"]].sum()
        fig = go.Figure(go.Waterfall(
            x=["Start"] + [d.replace("_", " ").title() for d in drivers.index] + ["End"],
            measure=["absolute"] + ["relative"] * len(drivers) + ["total"],
            y=[res["value_before"]] + list(drivers.values) + [0],
            decreasing={"marker": {"color": NEG}}, increasing={"marker": {"color": POS}}))
        fig.update_layout(title="P&L attribution by risk factor",
                          yaxis_range=[res["value_before"] * 0.85, res["value_before"] * 1.02])
        st.plotly_chart(fig, use_container_width=True)

    by_class = pos.groupby("asset_class")[["value_before", "value_after", "pnl"]].sum().reset_index()
    fig = px.bar(by_class.melt(id_vars="asset_class", value_vars=["value_before", "value_after"]),
                 x="asset_class", y="value", color="variable", barmode="group",
                 title="Value by asset class", color_discrete_sequence=["#aab7b8", "#2e86c1"])
    st.plotly_chart(fig, use_container_width=True)

    worst = pos.sort_values("pnl")[["trade_id", "counterparty", "instrument", "rating",
                                    "value_before", "value_after", "pnl"]]
    st.markdown("**Position-level impact (worst first)**")
    st.dataframe(worst.style.format({"value_before": "{:,.0f}", "value_after": "{:,.0f}", "pnl": "{:+,.0f}"}),
                 use_container_width=True, hide_index=True)
    st.json(res["shocks"], expanded=False)

# --- try it ------------------------------------------------------------------
with tab_try:
    st.markdown("Paste any headline or post to see the structured signal the engine produces.")
    text = st.text_area("Text", "Breaking: rating agency downgrades Goldman Sachs after surprise "
                                "trading losses; contagion fears hit bank stocks")
    c1, c2 = st.columns(2)
    src = c1.selectbox("Source", ["news", "social"])
    followers = c2.number_input("Followers (social only)", 0, 10_000_000, 50_000, step=1000)
    if st.button("Analyze", type="primary") and text.strip():
        doc = Document("LIVE", src, datetime.now(timezone.utc), text, reach=followers)
        out = get_engine().analyze(doc)
        for s in out:
            a, b, c = st.columns(3)
            a.metric(f"Sentiment - {s.entity}", f"{s.sentiment_score:+.2f}", s.sentiment_label)
            b.metric("Event", s.event_type, f"conf {s.event_confidence:.0%}")
            c.metric("Impact", f"{s.impact_score}/10")
        st.json([s.to_dict() for s in out])
        top = out[0]
        if top.impact_score > threshold and top.event_type in SCENARIOS:
            r = StressTester(load_portfolio(config.PORTFOLIO_CSV)).run_scenario(top.event_type, top.impact_score)
            st.warning(f"This would trigger a **{r['scenario']}** stress test: "
                       f"P&L {money(r['pnl'])} ({r['pnl_pct']:+.2%})")
