"""Narration for the demo video, one entry per scene.

kind = "card"  -> designed slide rendered by make_video.py
kind = "image" -> a static image with a slow zoom
kind = "live"  -> real screen capture of the running dashboard
"""

SCENES = [
    dict(id="01_title", kind="card", text=(
        "Hi, I'm Abhinav Sai from VIT-AP University. This is RiskPulse, an AI and NLP risk engine "
        "that turns financial news and social media chatter into structured risk signals."
    )),
    dict(id="02_problem", kind="card", text=(
        "Markets react to text long before it shows up in prices or in a daily risk report. "
        "A downgrade, a missile strike, or a hot inflation print. "
        "There is far too much of it for analysts to read, and raw text can't feed a model or a limit system. "
        "So the goal is simple: read every document, and turn it into a signal a machine can use."
    )),
    dict(id="03_architecture", kind="image", image="docs/architecture.png", text=(
        "Here's the design. Source adapters ingest financial news, social posts, and optionally any live RSS feed, "
        "and normalise them into one document format. The engine then links each document to the companies it mentions, "
        "scores sentiment from minus one to plus one with a finance specific lexicon, classifies the event into one of eight types, "
        "and predicts an impact score from one to ten. Signals are published to a file, a REST API, and an in-process bus "
        "that both downstream modules subscribe to."
    )),
    dict(id="04_terminal", kind="terminal", text=(
        "Running it is one command. Python main dot py run. "
        "Sixty documents from two sources become sixty eight signals, because a story about Apple and Nvidia produces one signal per company. "
        "You can already see both modules reacting: the index weights shift, and ten stress tests fire automatically."
    )),
    dict(id="05_feed", kind="live", text=(
        "This is the dashboard. The signal feed shows every signal over time. Bubble size is impact, colour is event type. "
        "Below that is impact weighted sentiment for each company, so Boeing, Pfizer and Intel stand out as the most negative names this week. "
        "And the table at the bottom is the raw structured output, with sentiment, event type, confidence and impact for every document."
    )),
    dict(id="06_module_a", kind="live", text=(
        "Module A is the tactical index rebalancer. Each stock's weight is its base weight times the exponential of its smoothed sentiment, "
        "with floors, a fifteen percent single name cap, and a ten percent turnover limit, so a single tweet can't swing the index. "
        "After the Strait tensions and the chip export controls, Apple and Nvidia are cut by around four and a half points, "
        "while Microsoft, Alphabet and JP Morgan gain on deal, legal and earnings news. "
        "If I raise the sentiment tilt in the sidebar, the index reacts more aggressively."
    )),
    dict(id="07_module_b", kind="live", text=(
        "Module B is the strategic stress tester. The portfolio is a synthetic two hundred and eighty three million dollar wholesale banking book "
        "of loans, bonds, swaps, credit default swaps and equity. "
        "Whenever an event scores above seven, the matching scenario is applied automatically, scaled by the impact score. "
        "For the sovereign downgrade, the book loses about twenty eight million, close to ten percent. "
        "The waterfall shows where the loss comes from. About two thirds is credit spread widening, led by the commercial real estate loan, "
        "and most of the rest is the equity sell off. "
        "Rate cuts are mapped to a growth scare scenario, not a hawkish one."
    )),
    dict(id="08_try", kind="live", text=(
        "Finally, you can paste any headline and score it live. This is the same engine the API exposes on the analyze endpoint. "
        "Here, a downgrade of Goldman Sachs with contagion fears is linked to Goldman, scored strongly negative, classified as a credit event, "
        "with an impact of eight point six out of ten. "
        "That is high enough to trigger a credit contagion stress test straight away, and the dashboard shows the projected loss."
    )),
    dict(id="09_results", kind="card", text=(
        "To sum up. Sixty documents, sixty eight signals, forty six rebalances, and ten automatic stress tests. "
        "News and social posts agree on sentiment direction in twenty nine of thirty stories. "
        "Every score is explainable down to the words that produced it, which matters for model risk review, "
        "and the engine is covered by twenty four unit tests."
    )),
    dict(id="10_close", kind="card", text=(
        "Next, I'd fine tune Fin BERT and ensemble it with the lexicon, calibrate impact against real market moves, "
        "and move ingestion to streaming. Thank you for watching."
    )),
]
