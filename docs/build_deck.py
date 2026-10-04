"""Builds docs/presentation.pptx (and the chart images it uses) from the latest pipeline output.

    python main.py run
    python docs/build_deck.py

Design matches the demo film: ink navy field, ivory type, one amber accent, the hand-drawn
pulse mark. Fonts are Segoe UI + Consolas so the deck renders the same on any Windows laptop.
"""
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src import config  # noqa: E402
from src.modules import IndexRebalancer  # noqa: E402
from src.riskengine import load_signals  # noqa: E402

NAME = "Madapati Naga Durga Abhinav Sai"
COLLEGE = "VIT-AP University"
EVENT = "S&P Global & Crisil Campus Hackathon 2026"

DOCS = ROOT / "docs"
SHOTS = DOCS / "screenshots"

INK, PANEL, RULE = "0D1321", "16233A", "2C4260"
MUTED, IVORY, AMBER = "9DB0C8", "F0EBD8", "FCA311"
LOSS, GAIN = "E8645A", "4FC08D"
DISPLAY, BODY, MONO = "Segoe UI Black", "Segoe UI", "Consolas"


def rgb(h):
    return RGBColor.from_string(h)


# --- data ------------------------------------------------------------------------

signals = load_signals(config.SIGNALS_JSONL)
stress = json.loads(config.STRESS_JSON.read_text(encoding="utf-8"))
reb = IndexRebalancer.from_universe(config.UNIVERSE_CSV).run(signals)
snap = pd.DataFrame(reb.snapshot()).sort_values("active_weight")
n_docs = len({s["doc_id"] for s in signals})
worst = min(stress, key=lambda s: s["pnl"])

# --- charts, dark to match the deck ------------------------------------------------

plt.rcParams.update({"font.family": "Segoe UI", "text.color": f"#{IVORY}", "axes.labelcolor": f"#{MUTED}",
                     "xtick.color": f"#{MUTED}", "ytick.color": f"#{IVORY}", "axes.edgecolor": f"#{RULE}"})


def dark_ax(ax):
    ax.set_facecolor("none")
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(f"#{RULE}")
    ax.grid(axis="x", color=f"#{RULE}", linewidth=.8, alpha=.7)
    ax.set_axisbelow(True)


fig, ax = plt.subplots(figsize=(6.2, 4.6), dpi=200)
fig.patch.set_alpha(0)
dark_ax(ax)
ax.barh(snap["ticker"], snap["active_weight"] * 100, height=.68,
        color=[f"#{GAIN}" if v > 0 else f"#{LOSS}" for v in snap["active_weight"]])
ax.axvline(0, color=f"#{MUTED}", linewidth=1)
ax.set_xlabel("active weight vs base (percentage points)", fontsize=10)
ax.tick_params(labelsize=10)
fig.tight_layout()
fig.savefig(DOCS / "chart_weights.png", transparent=True)
plt.close(fig)

st = pd.DataFrame([{"label": f"{s['timestamp'][5:10]}  {s['event_type'].split('/')[0]}",
                    "pnl": s["pnl"] / 1e6} for s in stress])
fig, ax = plt.subplots(figsize=(6.2, 4.6), dpi=200)
fig.patch.set_alpha(0)
dark_ax(ax)
ax.barh(st["label"], st["pnl"], height=.62,
        color=[f"#{AMBER}" if v == st["pnl"].min() else f"#{LOSS}" for v in st["pnl"]])
ax.invert_yaxis()
ax.set_xlabel("stress P&L ($m)", fontsize=10)
ax.tick_params(labelsize=10)
fig.tight_layout()
fig.savefig(DOCS / "chart_stress.png", transparent=True)
plt.close(fig)

# --- deck primitives ----------------------------------------------------------------

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
W, H = 13.333, 7.5


def rect(sl, x, y, w, h, fill=None, line=None, lw=1.5, radius=None):
    shp = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
                              Inches(x), Inches(y), Inches(w), Inches(h))
    if radius:
        shp.adjustments[0] = radius
    if fill:
        shp.fill.solid()
        shp.fill.fore_color.rgb = rgb(fill)
    else:
        shp.fill.background()
    if line:
        shp.line.color.rgb = rgb(line)
        shp.line.width = Pt(lw)
    else:
        shp.line.fill.background()
    shp.shadow.inherit = False
    return shp


def text(sl, x, y, w, h, runs, size=18, font=BODY, color=IVORY, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, spacing=None, line_spacing=None):
    """runs: str, or list of paragraphs; a paragraph is a str or a list of (text, overrides) tuples."""
    tb = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    paras = runs if isinstance(runs, list) else [runs]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if line_spacing:
            p.line_spacing = line_spacing
        if spacing is not None:
            p.space_after = Pt(spacing)
        for t, o in ([(para, {})] if isinstance(para, str) else para):
            r = p.add_run()
            r.text = t
            f = r.font
            f.size = Pt(o.get("size", size))
            f.name = o.get("font", font)
            f.bold = o.get("bold", False)
            f.color.rgb = rgb(o.get("color", color))
    return tb


def line(sl, x1, y1, x2, y2, color=RULE, w=1.5):
    c = sl.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = rgb(color)
    c.line.width = Pt(w)
    return c


def pulse(sl, x, y, w, h, color=AMBER, weight=3):
    """The RiskPulse mark: flat line, soft bump, sharp spike, settle (same path as the film)."""
    pts = [(0, 70), (760, 70), (822, 62), (872, 70), (930, 70), (962, 14), (994, 126),
           (1022, 40), (1046, 70), (1920, 70)]
    sx, sy = w / 1920, h / 140
    fb = sl.shapes.build_freeform(Inches(x + pts[0][0] * sx), Inches(y + pts[0][1] * sy), scale=1.0)
    fb.add_line_segments([(Inches(x + px * sx), Inches(y + py * sy)) for px, py in pts[1:]], close=False)
    shp = fb.convert_to_shape()
    shp.fill.background()
    shp.line.color.rgb = rgb(color)
    shp.line.width = Pt(weight)
    return shp


def base(title=None, num=None, label=None):
    sl = prs.slides.add_slide(BLANK)
    rect(sl, 0, 0, W, H, fill=INK)
    # faint 1-inch grid, like the film's 120px grid
    for gx in range(1, 14):
        line(sl, gx, 0, gx, H, color="172238", w=.75)
    for gy in range(1, 8):
        line(sl, 0, gy, W, gy, color="172238", w=.75)
    if num:
        text(sl, .7, .42, 8, .3, [[("RP", {"color": AMBER, "bold": True}), (f"  ·  {num} / {label.upper()}", {})]],
             size=11, font=MONO, color=MUTED)
        text(sl, W - 4.7, .42, 4, .3, "RISKPULSE — AI/NLP RISK ENGINE", size=11, font=MONO, color=MUTED, align=PP_ALIGN.RIGHT)
    if title:
        text(sl, .7, .8, 12, .9, title, size=34, font=DISPLAY)
    return sl


def card(sl, x, y, w, h, border=RULE):
    return rect(sl, x, y, w, h, fill=PANEL, line=border, lw=1.5, radius=.06)


def label(sl, x, y, w, t, color=MUTED, size=11):
    text(sl, x, y, w, .3, t.upper(), size=size, font=MONO, color=color, line_spacing=1.0)


# --- 1. title -----------------------------------------------------------------------

sl = base()
text(sl, .7, .42, 8, .3, [[("RP", {"color": AMBER, "bold": True}), ("  ·  " + EVENT.upper(), {})]],
     size=11, font=MONO, color=MUTED)
pulse(sl, 0, 1.55, W, 1.0)
text(sl, .65, 2.75, 12, 1.5, [[("Risk", {}), ("Pulse", {"color": AMBER})]], size=88, font=DISPLAY)
text(sl, .7, 4.25, 10.5, 1.1, "An AI/NLP risk engine that turns financial news and social chatter into "
     "structured, machine-readable risk signals — and acts on them.", size=20, color=MUTED, line_spacing=1.1)
rect(sl, .7, 5.75, .06, .85, fill=AMBER)
text(sl, .95, 5.72, 9, .5, NAME, size=20, font="Segoe UI Semibold")
text(sl, .95, 6.18, 9, .4, f"{COLLEGE}  ·  Individual submission", size=14, color=MUTED)

# --- 2. problem & approach ---------------------------------------------------------

sl = base("Risk lives in words. Systems can't read them.", "02", "Problem & approach")
pains = [("VOLUME", "Thousands of headlines and posts an hour — far beyond what an analyst desk can read."),
         ("STRUCTURE", "Raw text can't feed a model, a limit system or a portfolio revaluation."),
         ("LATENCY", "Risk teams learn about the shock after the P&L does — at the overnight run.")]
for i, (k, v) in enumerate(pains):
    y = 1.95 + i * 1.6
    card(sl, .7, y, 5.6, 1.4)
    label(sl, 1.0, y + .25, 4, k, color=LOSS)
    text(sl, 1.0, y + .58, 5.0, .8, v, size=15, line_spacing=1.05)
label(sl, 6.9, 1.95, 5, "My approach", color=AMBER)
steps = [("01", "Ingest", "News CSV, social JSON and any live RSS feed → one Document format."),
         ("02", "Understand", "Link companies, score sentiment, classify the event, predict impact."),
         ("03", "Publish", "Signals to a JSONL file, a REST API and a live pub/sub stream."),
         ("04", "Act", "Module A tilts an index · Module B stress-tests a banking book.")]
for i, (n, h_, b) in enumerate(steps):
    y = 2.4 + i * 1.12
    text(sl, 6.9, y, .8, .6, n, size=26, font=DISPLAY, color=AMBER)
    text(sl, 7.8, y + .02, 4.9, .4, h_, size=18, font="Segoe UI Semibold")
    text(sl, 7.8, y + .42, 4.9, .6, b, size=13.5, color=MUTED, line_spacing=1.05)
    if i < 3:
        line(sl, 7.8, y + 1.0, 12.6, y + 1.0, color=RULE, w=1)

# --- 3. system design -----------------------------------------------------------------

sl = base("One engine. Two consumers. Three ways out.", "03", "System design")


def node(x, y, w, h, small, big, border=RULE, big_size=16, big_color=IVORY):
    card(sl, x, y, w, h, border=border)
    label(sl, x + .2, y + .16, w - .3, small, size=9.5)
    text(sl, x + .2, y + .42, w - .3, h - .5, big, size=big_size, font="Segoe UI Semibold", color=big_color)


srcs = [("SOURCE", "Financial news"), ("SOURCE", "Social media (X)"), ("SOURCE · OPTIONAL", "Live RSS feed")]
for i, (s_, b) in enumerate(srcs):
    node(.7, 2.0 + i * 1.35, 2.5, .95, s_, b)
    line(sl, 3.2, 2.48 + i * 1.35, 3.9, 3.83, color=RULE, w=1.75)
node(3.9, 2.0, 3.0, 3.65, "RISKPULSE ENGINE", "NLP risk engine", border=AMBER, big_size=20)
for i, (k, v) in enumerate([("Entity linker", "cashtags + alias table"), ("Sentiment", "finance lexicon · −1 … +1"),
                            ("Event classifier", "8-class taxonomy"), ("Impact model", "severity 1 … 10")]):
    y = 2.95 + i * .64
    rect(sl, 4.1, y, 2.6, .54, fill=INK, line=RULE, lw=1, radius=.12)
    text(sl, 4.22, y + .05, 2.4, .25, k, size=11.5, font="Segoe UI Semibold")
    text(sl, 4.22, y + .28, 2.4, .25, v, size=9.5, font=MONO, color=MUTED)
outs = [("FILE", "signals.jsonl"), ("REST API", "/signals · /analyze · /stress"), ("LIVE STREAM", "pub / sub bus")]
for i, (s_, b) in enumerate(outs):
    y = 2.0 + i * 1.35
    line(sl, 6.9, 3.83, 7.6, y + .48, color=AMBER, w=1.75)
    node(7.6, y, 2.55, .95, s_, b, big_size=13)
line(sl, 10.15, 5.18, 10.55, 2.85, color=AMBER, w=1.75)
line(sl, 10.15, 5.18, 10.55, 4.75, color=AMBER, w=1.75)
node(10.55, 2.2, 2.1, 1.35, "MODULE A · TACTICAL", "Index rebalancer", big_size=15)
node(10.55, 4.1, 2.1, 1.35, "MODULE B · STRATEGIC", "Stress tester", big_size=15)
card(sl, .7, 6.15, 11.95, .7)
text(sl, .95, 6.3, 11.5, .45, [[("Dashboard  ", {"bold": True, "font": "Segoe UI Semibold"}),
                                ("Streamlit + Plotly — signal feed · weights over time · portfolio before/after · live headline scoring",
                                 {"color": MUTED})]], size=13)

# --- 4. implementation ------------------------------------------------------------------

sl = base("One headline in. One signal out.", "04", "Implementation highlights")
card(sl, .7, 1.85, 11.95, .78)
label(sl, .95, 1.95, 4, "Incoming · news wire")
text(sl, .95, 2.22, 11.5, .4, [[("Rating agency", {"color": AMBER}), (" downgrades ", {}), ("Goldman Sachs", {"color": AMBER}),
                               (" after surprise trading ", {}), ("losses", {"color": AMBER}), ("; ", {}),
                               ("contagion fears", {"color": AMBER}), (" hit bank stocks", {})]], size=13.5, font=MONO)
outs4 = [("ENTITY", "GS", IVORY, "alias → ticker"), ("SENTIMENT", "−0.84", LOSS, "lexicon, negation-aware"),
         ("EVENT", "Credit Event", IVORY, "confidence 100%"), ("IMPACT", "8.6 / 10", AMBER, "triggers a stress test")]
for i, (k, v, c, sub) in enumerate(outs4):
    x = .7 + i * 3.02
    card(sl, x, 2.85, 2.85, 1.55)
    label(sl, x + .22, 3.0, 2.5, k)
    text(sl, x + .22, 3.3, 2.5, .6, v, size=26 if len(v) < 8 else 21, font=DISPLAY, color=c)
    text(sl, x + .22, 3.95, 2.5, .3, sub, size=11, font=MONO, color=MUTED)
choices = [("Explainable lexicon, not a black box",
            "~250 finance terms + phrases. 'Crushed it' is positive, 'higher for longer' negative. Every score ships with the words behind it — auditable for model risk."),
           ("Impact is a model, not a guess",
            "Event base severity + tone (negative ×1.25) + magnitude cues (7%, $16bn, 25bp) + shock words + breadth + source credibility by follower reach."),
           ("Modules built like desk tools",
            "A: w ∝ base·e^(k·s) with floors, a 15% cap and 10% turnover limit.  B: duration / spread / delta / FX / PD×LGD revaluation; scenario by event, scaled by impact.")]
for i, (h_, b) in enumerate(choices):
    x = .7 + i * 4.03
    rect(sl, x, 4.78, .05, 1.45, fill=AMBER)
    text(sl, x + .25, 4.7, 3.6, .4, h_, size=15, font="Segoe UI Semibold")
    text(sl, x + .25, 5.12, 3.6, 1.6, b, size=12, color=MUTED, line_spacing=1.08)
text(sl, .7, 6.88, 12, .3, "Python 3 · pandas · FastAPI · Streamlit · Plotly · pytest (24 tests) — core engine uses only the standard library",
     size=11, font=MONO, color=MUTED)

# --- 5. results ------------------------------------------------------------------------

sl = base("One sample week, end to end.", "05", "Key results")
kpis = [(str(n_docs), "documents", IVORY), (str(len(signals)), "risk signals", IVORY),
        (str(len(reb.history)), "rebalances", IVORY), (str(len(stress)), "stress tests", AMBER)]
for i, (n, l_, c) in enumerate(kpis):
    x = .7 + i * 1.62
    text(sl, x, 1.75, 1.6, .8, n, size=40, font=DISPLAY, color=c)
    label(sl, x + .03, 2.55, 1.6, l_, size=9.5)
card(sl, 7.4, 1.75, 5.25, 1.15, border=LOSS)
label(sl, 7.62, 1.88, 5, "Worst case · sovereign downgrade · impact 9.4", size=9.5)
text(sl, 7.62, 2.12, 2.6, .7, f"−${abs(worst['pnl']) / 1e6:.1f}M", size=30, font=DISPLAY, color=LOSS)
text(sl, 10.05, 2.25, 2.5, .6, f"{worst['pnl_pct']:+.1%} of a ${worst['value_before'] / 1e6:.0f}m book, valued the moment it landed",
     size=11, color=MUTED, line_spacing=1.0)
for i, (img, cap) in enumerate([("chart_weights.png", "Module A — AAPL, NVDA cut ~4.6pp; MSFT, GOOGL, JPM up"),
                                ("chart_stress.png", "Module B — 10 auto-triggered stress tests (amber = worst)")]):
    x = .7 + i * 6.05
    card(sl, x, 3.15, 5.9, 3.55)
    sl.shapes.add_picture(str(DOCS / img), Inches(x + .3), Inches(3.3), height=Inches(2.95))
    text(sl, x + .25, 6.3, 5.5, .3, cap, size=11, font=MONO, color=MUTED)
text(sl, .7, 6.92, 12, .3, "News and social agree on sentiment direction in 29 of 30 stories — the miss (OPEC+ cut) is genuinely mixed news.",
     size=12, color=IVORY)

# --- 6. domain impact -------------------------------------------------------------------

sl = base("Why it matters to a bank or an index provider.", "06", "Domain impact")
impacts = [("EARLY WARNING", "Seconds, not overnight",
            "A credit event in the news revalues the book as it lands — instead of at the next daily risk run."),
           ("EXPLAINABILITY", "Every number has a reason",
            "Scores trace back to the words that produced them, so model validation and regulators can audit them."),
           ("ONE SIGNAL, MANY USES", "Build once, consume everywhere",
            "The same feed drives trading tilts, scenario analysis and — next — limit monitoring and alerts."),
           ("ANALYST LEVERAGE", "One ranked feed",
            "A desk watching 18 names and 60 stories sees what matters first, instead of dozens of tabs.")]
for i, (k, h_, b) in enumerate(impacts):
    x = .7 + (i % 2) * 6.05
    y = 1.95 + (i // 2) * 2.3
    card(sl, x, y, 5.9, 1.95)
    label(sl, x + .3, y + .28, 5, k, color=AMBER)
    text(sl, x + .3, y + .62, 5.3, .5, h_, size=21, font="Segoe UI Semibold")
    text(sl, x + .3, y + 1.15, 5.3, 1.0, b, size=13.5, color=MUTED, line_spacing=1.08)
# --- 7. limitations & next steps ---------------------------------------------------------

sl = base("Honest limits, clear next steps.", "07", "Limitations & next steps")
cols = [("ASSUMPTIONS & GAPS", LOSS, ["Lexicon tuned on a small synthetic sample",
                                      "First-order (linear) revaluation — no convexity or optionality",
                                      "Scenario shocks hand-calibrated, not fitted to history",
                                      "Entity linking limited to an alias table"]),
        ("NEXT STEPS", GAIN, ["Fine-tune FinBERT on labelled headlines; ensemble with the lexicon",
                              "Calibrate impact against realised abnormal returns",
                              "Historical scenario library — 2008, 2020, 2022 rates shock",
                              "Streaming ingestion (Kafka) with alerting; backtest Module A vs equal weight"])]
for i, (k, c, items) in enumerate(cols):
    x = .7 + i * 6.05
    card(sl, x, 1.85, 5.9, 4.3)
    label(sl, x + .3, 2.1, 5, k, color=c)
    for j, it in enumerate(items):
        y = 2.6 + j * .85
        rect(sl, x + .32, y + .12, .1, .1, fill=c)
        text(sl, x + .6, y, 5.0, .8, it, size=14.5, line_spacing=1.05)
pulse(sl, 0, 6.2, W, .62, weight=2.5)
text(sl, .7, 7.0, 12, .3, f"{NAME}  ·  {COLLEGE}  ·  Thank you", size=12, font=MONO, color=MUTED)

out = DOCS / "presentation.pptx"
prs.save(out)
print(f"wrote {out} ({len(prs.slides)} slides)")
