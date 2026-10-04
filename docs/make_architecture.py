"""Renders docs/architecture.png. Run: python docs/make_architecture.py"""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).with_name("architecture.png")

fig, ax = plt.subplots(figsize=(16, 9), dpi=150)
ax.set_xlim(0, 16)
ax.set_ylim(0, 9)
ax.axis("off")

INK, MUTED = "#1c2833", "#566573"
SRC, ENG, OUTC, MOD = "#d6eaf8", "#fdebd0", "#e8f8f5", "#f5eef8"


def box(x, y, w, h, title, lines=(), color="#fff", size=12):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.15",
                                fc=color, ec=INK, lw=1.3))
    ax.text(x + w / 2, y + h - 0.3, title, ha="center", va="top", fontsize=size,
            fontweight="bold", color=INK)
    for i, ln in enumerate(lines):
        ax.text(x + w / 2, y + h - 0.75 - i * 0.33, ln, ha="center", va="top", fontsize=9, color=MUTED)


def arrow(x1, y1, x2, y2, label=""):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=16,
                                 lw=1.4, color=INK))
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.15, label, ha="center", fontsize=8.5,
                color=MUTED, style="italic")


ax.text(8, 8.65, "RiskPulse - AI/NLP Risk Engine architecture", ha="center",
        fontsize=17, fontweight="bold", color=INK)

# sources
box(0.3, 5.9, 2.8, 1.6, "Financial news", ["news_feed.csv", "headline + body"], SRC)
box(0.3, 3.9, 2.8, 1.6, "Social media (X)", ["social_posts.json", "cashtags, followers"], SRC)
box(0.3, 1.9, 2.8, 1.6, "Live RSS (optional)", ["any public feed URL", "stdlib parser"], SRC)

# ingestion
box(3.8, 3.4, 2.4, 2.6, "Ingestion", ["source adapters", "-> Document", "UTC timestamps", "time-ordered stream"], ENG)
for y in (6.7, 4.7, 2.7):
    arrow(3.1, y, 3.8, 4.7)

# engine
box(6.9, 2.0, 4.0, 5.8, "NLP Risk Engine", [], ENG, size=13)
steps = [("Entity linker", "cashtags + company aliases"),
         ("Sentiment scorer", "finance lexicon, negation, phrases"),
         ("Event classifier", "8-class weighted taxonomy"),
         ("Impact model", "severity, magnitude, credibility")]
for i, (t, d) in enumerate(steps):
    y = 6.5 - i * 1.25
    ax.add_patch(FancyBboxPatch((7.2, y - 0.2), 3.4, 0.95, boxstyle="round,pad=0.02",
                                fc="white", ec=MUTED, lw=1))
    ax.text(8.9, y + 0.5, t, ha="center", fontsize=10.5, fontweight="bold", color=INK)
    ax.text(8.9, y + 0.12, d, ha="center", fontsize=8.5, color=MUTED)
    if i < 3:
        arrow(8.9, y - 0.2, 8.9, y - 0.5)
arrow(6.2, 4.7, 6.9, 4.7, "Documents")

# outputs
box(11.6, 5.6, 4.1, 2.2, "Signal bus / outputs",
    ["RiskSignal {entity, sentiment,", "event_type, impact, ...}", "signals.jsonl  |  REST API (FastAPI)",
     "in-process pub/sub"], OUTC)
arrow(10.9, 6.2, 11.6, 6.6, "publish")

box(11.6, 2.9, 4.1, 2.2, "Module A - Index rebalancer",
    ["subscribes: sentiment", "w ~ base * exp(k * s)", "caps, floors, turnover limit"], MOD)
box(11.6, 0.3, 4.1, 2.2, "Module B - Stress tester",
    ["subscribes: event + impact", "impact > 7 -> scenario shocks", "rates / spread / equity / FX / PD"], MOD)
arrow(13.65, 5.6, 13.65, 5.1)
# bus -> module B, routed around module A
ax.plot([11.6, 11.3, 11.3], [5.9, 5.9, 1.4], color=INK, lw=1.4)
arrow(11.3, 1.4, 11.6, 1.4)

box(6.9, 0.1, 4.0, 1.1, "Streamlit dashboard", ["feed  |  weights over time  |  before/after"], OUTC, size=11)
arrow(11.6, 0.65, 10.9, 0.65)

fig.savefig(OUT, bbox_inches="tight", facecolor="white")
print(f"wrote {OUT}")
