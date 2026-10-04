"""Builds docs/demo_video.mp4 - a narrated, captioned walkthrough.

Needs: the dashboard running on :8501 (python main.py dashboard), ffmpeg on PATH,
Chrome installed, `pip install playwright pillow`. Narration uses the Windows
built-in voice; to use your own voice, drop <scene_id>.wav files into
docs/video/voice/ and they'll be used instead.

    python docs/video/make_video.py            # everything
    python docs/video/make_video.py --skip-capture   # reuse captured footage
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
import time
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
BUILD = HERE / "build"
VOICE = HERE / "voice"
OUT = ROOT / "docs" / "demo_video.mp4"
SHOTS = ROOT / "docs" / "screenshots"
URL = "http://localhost:8501"
W, H, FPS = 1920, 1080, 30
LEAD, TAIL = 0.6, 0.9          # silence before / after narration in each scene

sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
from script import SCENES  # noqa: E402

# --- design tokens (shared with the slide deck) -----------------------------
NAVY, PANEL, PANEL2 = (11, 31, 51), (18, 48, 77), (24, 62, 99)
WHITE, MUTED = (255, 255, 255), (159, 179, 200)
TEAL, AMBER, RED, GREEN = (25, 195, 177), (245, 166, 35), (229, 83, 61), (46, 204, 113)
FONTS = Path("C:/Windows/Fonts")


def font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    name = {"light": "segoeuil.ttf", "regular": "segoeui.ttf", "semibold": "seguisb.ttf",
            "bold": "segoeuib.ttf", "black": "seguibl.ttf", "mono": "consola.ttf",
            "monob": "consolab.ttf"}[weight]
    return ImageFont.truetype(str(FONTS / name), size)


def run(cmd, **kw):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, **kw)
    if r.returncode:
        raise RuntimeError(f"{cmd[0]} failed:\n{r.stderr[-2500:]}")
    return r


# --- narration ----------------------------------------------------------------

def narrate(scene) -> Path:
    custom = VOICE / f"{scene['id']}.wav"
    if custom.exists():
        return custom
    wav = BUILD / f"{scene['id']}.wav"
    if wav.exists():
        return wav
    txt = BUILD / f"{scene['id']}.txt"
    txt.write_text(scene["text"], encoding="utf-8")
    ps = ("Add-Type -AssemblyName System.Speech;"
          "$s=New-Object System.Speech.Synthesis.SpeechSynthesizer;"
          "$s.SelectVoice('Microsoft David Desktop');$s.Rate=0;"
          f"$s.SetOutputToWaveFile('{wav}');"
          f"$s.Speak([IO.File]::ReadAllText('{txt}'));$s.Dispose()")
    run(["powershell", "-NoProfile", "-Command", ps])
    return wav


def wav_seconds(p: Path) -> float:
    with wave.open(str(p)) as w:
        return w.getnframes() / w.getframerate()


# --- designed cards ---------------------------------------------------------------

def canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    # soft glow top-right + thin accent rule
    glow = Image.new("RGB", (W, H), NAVY)
    ImageDraw.Draw(glow).ellipse((1150, -500, 2500, 700), fill=(20, 70, 100))
    img = Image.blend(img, glow.filter(ImageFilter.GaussianBlur(160)), 0.9)
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W, 8), fill=TEAL)
    d.text((120, 1000), "RiskPulse", font=font("semibold", 26), fill=MUTED)
    d.text((W - 120, 1000), "S&P Global & Crisil Campus Hackathon 2026", font=font("regular", 24),
           fill=MUTED, anchor="ra")
    return img, d


def pill(d, xy, text, color, size=26):
    f = font("semibold", size)
    x, y = xy
    w = d.textlength(text, font=f)
    d.rounded_rectangle((x, y, x + w + 44, y + size + 26), radius=(size + 26) // 2, fill=color)
    d.text((x + 22, y + 10), text, font=f, fill=NAVY)
    return x + w + 44


def wrap(d, text, f, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = f"{cur} {w}".strip()
        if d.textlength(t, font=f) > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    return lines + [cur]


def card_title():
    img, d = canvas()
    pill(d, (120, 250), "AI / NLP RISK ENGINE", TEAL)
    d.text((112, 320), "RiskPulse", font=font("black", 170), fill=WHITE)
    for i, ln in enumerate(["From headlines and posts to structured,",
                            "machine-readable financial risk signals"]):
        d.text((120, 540 + i * 62), ln, font=font("light", 48), fill=MUTED)
    d.rectangle((120, 720, 124, 840), fill=AMBER)
    d.text((150, 718), "Madapati Naga Durga Abhinav Sai", font=font("semibold", 40), fill=WHITE)
    d.text((150, 778), "VIT-AP University", font=font("regular", 34), fill=MUTED)
    return img


def card_problem():
    img, d = canvas()
    d.text((120, 120), "The problem", font=font("bold", 72), fill=WHITE)
    d.text((120, 215), "Markets move on text long before it reaches prices, ratings or a risk report.",
           font=font("light", 36), fill=MUTED)
    items = [("Volume", "Thousands of headlines and posts an hour. No team can read them all.", AMBER),
             ("Structure", "Raw text can't feed a model, a limit system or a dashboard.", RED),
             ("Latency", "Risk teams often learn about a shock after the P&L does.", TEAL)]
    for i, (h, body, c) in enumerate(items):
        x = 120 + i * 570
        d.rounded_rectangle((x, 340, x + 530, 700), radius=24, fill=PANEL)
        d.rectangle((x, 340, x + 530, 348), fill=c)
        d.text((x + 40, 390), h, font=font("bold", 44), fill=WHITE)
        for j, ln in enumerate(wrap(d, body, font("regular", 30), 450)):
            d.text((x + 40, 470 + j * 44), ln, font=font("regular", 30), fill=MUTED)
    d.rounded_rectangle((120, 760, 1800, 900), radius=24, fill=PANEL2)
    d.text((170, 795), "Goal:", font=font("bold", 38), fill=TEAL)
    d.text((290, 795), "read every document and turn it into a signal a machine can use.",
           font=font("regular", 38), fill=WHITE)
    return img


def card_results():
    sig = [json.loads(l) for l in (ROOT / "output/signals.jsonl").read_text(encoding="utf-8").splitlines() if l]
    stress = json.loads((ROOT / "output/stress_results.json").read_text(encoding="utf-8"))
    worst = min(stress, key=lambda s: s["pnl"])
    img, d = canvas()
    d.text((120, 120), "Results on the sample feed", font=font("bold", 72), fill=WHITE)
    tiles = [(str(len({s['doc_id'] for s in sig})), "documents", "news + social", WHITE),
             (str(len(sig)), "risk signals", "one per company", TEAL),
             ("46", "rebalances", "turnover-capped", AMBER),
             (str(len(stress)), "stress tests", "auto-triggered", RED)]
    for i, (num, lab, sub, c) in enumerate(tiles):
        x = 120 + i * 430
        d.rounded_rectangle((x, 270, x + 400, 560), radius=24, fill=PANEL)
        d.text((x + 40, 290), num, font=font("black", 130), fill=c)
        d.text((x + 44, 465), lab, font=font("semibold", 36), fill=WHITE)
        d.text((x + 44, 512), sub, font=font("regular", 26), fill=MUTED)
    rows = [("29 / 30", "news and social agree on sentiment direction"),
            (f"{worst['pnl'] / 1e6:+.1f}m", f"worst stress loss ({worst['pnl_pct']:+.1%}): sovereign downgrade"),
            ("24 / 24", "unit tests passing; every score explainable by its keywords")]
    for i, (k, v) in enumerate(rows):
        y = 620 + i * 105
        d.rounded_rectangle((120, y, 1800, y + 88), radius=18, fill=PANEL2)
        d.text((160, y + 18), k, font=font("bold", 40), fill=AMBER)
        d.text((480, y + 22), v, font=font("regular", 36), fill=WHITE)
    return img


def card_close():
    img, d = canvas()
    d.text((120, 140), "What's next", font=font("bold", 72), fill=WHITE)
    nxt = ["Fine-tune FinBERT and ensemble it with the explainable lexicon",
           "Calibrate impact scores against realised market moves",
           "Historical scenario library (2008, 2020, 2022 rates shock)",
           "Streaming ingestion (Kafka) with alerting"]
    for i, t in enumerate(nxt):
        y = 290 + i * 100
        d.ellipse((125, y + 14, 149, y + 38), fill=TEAL)
        d.text((180, y), t, font=font("regular", 40), fill=WHITE)
    d.text((120, 760), "Thank you", font=font("black", 96), fill=WHITE)
    d.text((124, 890), "Madapati Naga Durga Abhinav Sai  ·  VIT-AP University", font=font("regular", 32), fill=MUTED)
    return img


def card_terminal():
    out = run([sys.executable, "main.py", "run"], env={**__import__("os").environ,
                                                       "PYTHONIOENCODING": "utf-8"}).stdout
    lines = ["$ python main.py run"] + out.strip("\n").splitlines()
    img, d = canvas()
    d.text((120, 60), "One command, end to end", font=font("bold", 54), fill=WHITE)
    x0, y0, x1, y1 = 120, 150, 1800, 975
    d.rounded_rectangle((x0, y0, x1, y1), radius=18, fill=(13, 17, 23))
    d.rounded_rectangle((x0, y0, x1, y0 + 48), radius=18, fill=(33, 38, 45))
    d.rectangle((x0, y0 + 30, x1, y0 + 48), fill=(33, 38, 45))
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse((x0 + 22 + i * 30, y0 + 15, x0 + 40 + i * 30, y0 + 33), fill=c)
    d.text(((x0 + x1) // 2, y0 + 12), "PowerShell - Phase3", font=font("regular", 20),
           fill=MUTED, anchor="ma")
    f = font("mono", 19)
    y = y0 + 66
    for ln in lines[:36]:
        col = (201, 209, 217)
        if ln.startswith("$"):
            col = GREEN
        elif ln.startswith("Module"):
            col = AMBER
        elif "Ingested" in ln or "Published" in ln:
            col = TEAL
        elif re.search(r"P&L -", ln):
            col = (255, 140, 120)
        d.text((x0 + 28, y), ln[:150], font=f, fill=col)
        y += 22.5
    return img


CARDS = {"01_title": card_title, "02_problem": card_problem, "09_results": card_results,
         "10_close": card_close, "04_terminal": card_terminal}


def badge(text: str) -> Path:
    """Lower-right chapter label overlaid on live footage."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = font("semibold", 30)
    w = d.textlength(text, font=f)
    x, y = W - w - 110, 960
    d.rounded_rectangle((x - 30, y - 14, x + w + 30, y + 50), radius=32, fill=(11, 31, 51, 235))
    d.ellipse((x - 14, y + 12, x - 2, y + 24), fill=TEAL + (255,))
    d.text((x + 8, y - 2), text, font=f, fill=WHITE)
    p = BUILD / f"badge_{re.sub(r'\\W+', '_', text)}.png"
    img.save(p)
    return p


# --- live capture via Chrome DevTools screencast ------------------------------

CURSOR_JS = """
(() => {
  if (window.__cursor) return;
  const c = document.createElement('div');
  c.style.cssText = 'position:fixed;z-index:2147483647;width:26px;height:26px;margin:-13px 0 0 -13px;'
    + 'border-radius:50%;background:rgba(25,195,177,.35);border:2px solid #19c3b1;pointer-events:none;'
    + 'transition:transform .12s;left:-50px;top:-50px';
  document.documentElement.appendChild(c);
  addEventListener('mousemove', e => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; }, true);
  addEventListener('mousedown', () => c.style.transform = 'scale(.6)', true);
  addEventListener('mouseup', () => c.style.transform = 'scale(1)', true);
  window.__cursor = c;
})();
"""


class Director:
    def __init__(self, page, duration):
        self.page, self.duration, self.t0 = page, duration, time.monotonic()
        self.mx, self.my = 960, 540

    def at(self, frac):
        """Sleep until `frac` of the scene has elapsed."""
        dt = self.t0 + frac * self.duration - time.monotonic()
        if dt > 0:
            self.page.wait_for_timeout(dt * 1000)

    def move(self, x, y, steps=30):
        self.page.mouse.move(x, y, steps=steps)
        self.mx, self.my = x, y

    def click_el(self, loc):
        b = loc.bounding_box()
        self.move(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
        self.page.wait_for_timeout(250)
        self.page.mouse.down()
        self.page.wait_for_timeout(90)
        self.page.mouse.up()

    def scroll(self, dy, secs=1.6):
        n = max(int(secs * 40), 1)
        self.move(1150, 600, steps=15)
        for _ in range(n):
            self.page.mouse.wheel(0, dy / n)
            self.page.wait_for_timeout(secs * 1000 / n)

    def scroll_to(self, loc, offset=110, secs=1.6):
        b = loc.bounding_box()
        if b:
            self.scroll(b["y"] - offset, secs)


def open_tab(dr, name):
    dr.click_el(dr.page.get_by_role("tab", name=name))
    dr.page.wait_for_timeout(1800)


def scene_feed(dr):
    p = dr.page
    dr.at(0.04); dr.move(620, 560, 50)
    dr.at(0.12); dr.move(900, 500, 40)
    dr.at(0.30); dr.scroll_to(p.get_by_text("Impact-weighted sentiment by company").first, 90)
    dr.at(0.40); dr.move(700, 600, 40)
    dr.at(0.66); dr.scroll_to(p.locator('[data-testid="stDataFrame"]').first, 90)
    dr.at(0.80); dr.move(1000, 520, 40)


def scene_module_a(dr):
    p = dr.page
    open_tab(dr, "Module A - Index rebalancer")
    dr.at(0.10); dr.move(1100, 560, 40)
    dr.at(0.30); dr.scroll_to(p.get_by_text("Base vs current weight").first, 120)
    dr.at(0.40); dr.move(1500, 640, 40)
    dr.at(0.66); dr.scroll(-3000, 1.2)
    dr.at(0.72)
    slider = p.get_by_role("slider").first
    dr.click_el(slider)
    for _ in range(12):
        p.keyboard.press("ArrowRight")
        p.wait_for_timeout(120)
    dr.at(0.84); dr.move(1100, 560, 40)


def scene_module_b(dr):
    p = dr.page
    open_tab(dr, "Module B - Stress test")
    dr.at(0.08); dr.move(1100, 620, 40)
    dr.at(0.20); dr.scroll_to(p.get_by_text("Scenario detail").first, 80)
    # the event picker is the first visible selectbox in this tab
    sel = p.locator('[data-testid="stSelectbox"]:visible').first
    dr.click_el(sel)
    p.wait_for_timeout(500)
    p.keyboard.type("Sovereign", delay=60)
    p.wait_for_timeout(400)
    p.keyboard.press("Enter")
    p.get_by_text("-$28.0m").first.wait_for(timeout=8000)
    dr.at(0.48); dr.scroll_to(p.get_by_text("Value before").first, 140)
    dr.at(0.56); dr.move(1450, 650, 40)
    dr.at(0.80); dr.scroll_to(p.get_by_text("Position-level impact").first, 100)


def scene_try(dr):
    p = dr.page
    open_tab(dr, "Try the engine")
    box = p.get_by_label("Text")
    dr.click_el(box)
    p.keyboard.press("Control+A")
    p.keyboard.press("Delete")
    box.fill("Breaking: rating agency downgrades Goldman Sachs after surprise trading losses;")
    box.press_sequentially(" contagion fears hit bank stocks", delay=45)
    dr.at(0.22)
    dr.click_el(p.get_by_role("button", name="Analyze"))
    p.wait_for_timeout(1500)
    dr.at(0.40); dr.move(900, 560, 40)
    dr.at(0.62); dr.move(700, p.get_by_text("This would trigger").first.bounding_box()["y"] + 12, 40)
    dr.at(0.80); dr.click_el(p.get_by_text("Structured output").first.locator("xpath=following::*[@data-testid='stJson'][1]"))


LIVE = {"05_feed": (scene_feed, "Signal feed"),
        "06_module_a": (scene_module_a, "Module A  ·  Index rebalancer"),
        "07_module_b": (scene_module_b, "Module B  ·  Stress test"),
        "08_try": (scene_try, "Live engine")}


def capture(scene_id, duration) -> Path:
    from playwright.sync_api import sync_playwright
    fn, _ = LIVE[scene_id]
    fdir = BUILD / f"{scene_id}_frames"
    fdir.mkdir(parents=True, exist_ok=True)
    for old in fdir.glob("*.jpg"):
        old.unlink()
    frames: list[tuple[float, Path]] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome")
        ctx = browser.new_context(viewport={"width": W, "height": H}, color_scheme="light")
        page = ctx.new_page()
        page.add_init_script(CURSOR_JS)
        page.goto(URL)
        page.wait_for_selector(".js-plotly-plot", timeout=60000)
        page.wait_for_timeout(4000)
        page.evaluate(CURSOR_JS)
        # hide Streamlit's own chrome so the footage looks like an app, not a dev tool
        page.add_style_tag(content='[data-testid="stToolbar"],[data-testid="stDecoration"],'
                                   '[data-testid="stStatusWidget"]{display:none!important}')
        page.mouse.move(960, 540)

        cdp = ctx.new_cdp_session(page)

        def on_frame(ev):
            path = fdir / f"{len(frames):05d}.jpg"
            path.write_bytes(base64.b64decode(ev["data"]))
            frames.append((time.monotonic(), path))
            cdp.send("Page.screencastFrameAck", {"sessionId": ev["sessionId"]})

        cdp.on("Page.screencastFrame", on_frame)
        cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 92,
                                          "maxWidth": W, "maxHeight": H})
        dr = Director(page, duration)
        frames.append((dr.t0, None))   # placeholder start
        fn(dr)
        dr.at(1.0)
        end = time.monotonic()
        cdp.send("Page.stopScreencast")
        if scene_id == "07_module_b":
            page.screenshot(path=str(SHOTS / "module_b_stress_test.png"))
        browser.close()

    # timeline -> ffconcat with per-frame durations
    real = [(t, p) for t, p in frames if p]
    t0 = frames[0][0]
    lst = ["ffconcat version 1.0"]
    for i, (t, p) in enumerate(real):
        nxt = real[i + 1][0] if i + 1 < len(real) else end
        start = t0 if i == 0 else t
        lst += [f"file '{p.name}'", f"duration {max(nxt - start, 1 / FPS):.4f}"]
    lst.append(f"file '{real[-1][1].name}'")
    concat = fdir / "list.txt"
    concat.write_text("\n".join(lst), encoding="utf-8")
    return concat


# --- assembly ------------------------------------------------------------------------

def seg_cmd(video_in: list[str], vf: str, audio: Path, total: float, out: Path) -> list[str]:
    return ["ffmpeg", "-y", "-loglevel", "error", *video_in, "-i", str(audio),
            "-filter_complex",
            f"{vf}[v];[1:a]aresample=48000,adelay={int(LEAD * 1000)}:all=1,apad[a]",
            "-map", "[v]", "-map", "[a]", "-t", f"{total:.3f}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-ar", "48000", str(out)]


def build(skip_capture=False):
    BUILD.mkdir(parents=True, exist_ok=True)
    SHOTS.mkdir(parents=True, exist_ok=True)
    segs, srt, clock = [], [], 0.0
    for i, sc in enumerate(SCENES):
        sid = sc["id"]
        wav = narrate(sc)
        speech = wav_seconds(wav)
        total = LEAD + speech + TAIL
        out = BUILD / f"{sid}.mp4"
        fade = f"fade=t=in:st=0:d=0.35,fade=t=out:st={total - 0.35:.3f}:d=0.35"
        print(f"[{i + 1}/{len(SCENES)}] {sid}  {total:5.1f}s")

        if sid in CARDS:
            png = BUILD / f"{sid}.png"
            CARDS[sid]().save(png)
            frames = int(total * FPS)
            zoom = (f"scale=3840:-1,zoompan=z='1+0.035*on/{frames}':x='iw/2-(iw/zoom/2)':"
                    f"y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS}")
            run(seg_cmd(["-loop", "1", "-i", str(png)], f"[0:v]{zoom},{fade}", wav, total, out))
        elif sc["kind"] == "image":
            src = ROOT / sc["image"]
            img = Image.open(src).convert("RGB")
            bg, _ = canvas()
            img.thumbnail((W - 160, H - 150))
            bg.paste(img, ((W - img.width) // 2, (H - img.height) // 2 - 20))
            png = BUILD / f"{sid}.png"
            bg.save(png)
            frames = int(total * FPS)
            zoom = (f"scale=3840:-1,zoompan=z='1+0.08*on/{frames}':x='iw/2-(iw/zoom/2)':"
                    f"y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS}")
            run(seg_cmd(["-loop", "1", "-i", str(png)], f"[0:v]{zoom},{fade}", wav, total, out))
        else:
            concat = BUILD / f"{sid}_frames" / "list.txt"
            if not (skip_capture and concat.exists()):
                concat = capture(sid, total)
            lbl = badge(LIVE[sid][1])
            vf = (f"[0:v]scale={W}:{H},fps={FPS},format=yuv420p[base];[2:v]format=rgba[lb];"
                  f"[base][lb]overlay=0:0,{fade}")
            cmd = seg_cmd(["-f", "concat", "-safe", "0", "-i", str(concat)], vf, wav, total, out)
            cmd[cmd.index(str(wav)) + 1:cmd.index(str(wav)) + 1] = ["-i", str(lbl)]
            run(cmd)
        segs.append(out)

        # captions: split into short chunks, timed in proportion to their length
        chunks = [c.strip() for c in re.split(r"(?<=[.,:!?])\s+", sc["text"]) if c.strip()]
        merged, cur = [], ""
        for c in chunks:
            if len(cur) + len(c) < 90:
                cur = f"{cur} {c}".strip()
            else:
                merged.append(cur) if cur else None
                cur = c
        merged.append(cur)
        chars = sum(len(c) for c in merged)
        t = clock + LEAD
        for c in merged:
            dt = speech * len(c) / chars
            srt.append((t, t + dt, c))
            t += dt
        clock += total

    lst = BUILD / "segments.txt"
    lst.write_text("\n".join(f"file '{s.name}'" for s in segs), encoding="utf-8")
    joined = BUILD / "joined.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
         "-c", "copy", str(joined)])

    def ts(x):
        return f"{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{int(x % 60):02d},{int(x % 1 * 1000):03d}"
    (BUILD / "captions.srt").write_text(
        "\n".join(f"{i + 1}\n{ts(a)} --> {ts(b)}\n{c}\n" for i, (a, b, c) in enumerate(srt)),
        encoding="utf-8")
    style = ("FontName=Segoe UI,FontSize=12,PrimaryColour=&H00FFFFFF,BackColour=&HB4331F0B,"
             "BorderStyle=4,Outline=0,Shadow=0,MarginV=14,MarginL=40,MarginR=40")
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(joined.relative_to(ROOT)),
         "-vf", f"subtitles=docs/video/build/captions.srt:force_style='{style}'",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
         "-c:a", "copy", "-movflags", "+faststart", str(OUT.relative_to(ROOT))])
    (ROOT / "docs" / "demo_video.srt").write_text(
        (BUILD / "captions.srt").read_text(encoding="utf-8"), encoding="utf-8")
    print(f"wrote {OUT}  ({clock / 60:.1f} min)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-capture", action="store_true")
    build(ap.parse_args().skip_capture)
