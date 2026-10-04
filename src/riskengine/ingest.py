"""Source adapters. Each one turns a raw feed into a list of Documents.

Two offline sources ship with the repo (news CSV + social JSON) so the demo
runs without network access. RssSource can pull a live public feed when one
is available; it uses only the standard library.
"""
from __future__ import annotations

import csv
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from .models import Document


def _parse_ts(value: str) -> datetime:
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    ts = datetime.fromisoformat(value)
    return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)


class NewsCsvSource:
    name = "news"

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> list[Document]:
        with self.path.open(encoding="utf-8") as fh:
            return [
                Document(
                    doc_id=row["id"],
                    source=self.name,
                    published_at=_parse_ts(row["published_at"]),
                    title=row["headline"].strip(),
                    text=row["body"].strip(),
                    author=row.get("outlet", ""),
                )
                for row in csv.DictReader(fh)
            ]


class SocialJsonSource:
    name = "social"

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def load(self) -> list[Document]:
        posts = json.loads(self.path.read_text(encoding="utf-8"))
        return [
            Document(
                doc_id=p["id"],
                source=self.name,
                published_at=_parse_ts(p["created_at"]),
                text=p["text"],
                author=p.get("user", ""),
                reach=int(p.get("followers", 0)),
            )
            for p in posts
        ]


class RssSource:
    """Minimal RSS 2.0 reader, e.g. a Yahoo Finance or Google News feed URL."""
    name = "rss"
    _tag_re = re.compile(r"<[^>]+>")

    def __init__(self, url: str, timeout: int = 10):
        self.url = url
        self.timeout = timeout

    def load(self) -> list[Document]:
        req = urllib.request.Request(self.url, headers={"User-Agent": "riskpulse/1.0"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            root = ET.fromstring(resp.read())
        docs = []
        for i, item in enumerate(root.iter("item")):
            title = (item.findtext("title") or "").strip()
            desc = self._tag_re.sub(" ", item.findtext("description") or "").strip()
            pub = item.findtext("pubDate")
            try:
                ts = parsedate_to_datetime(pub) if pub else datetime.now(timezone.utc)
            except (TypeError, ValueError):
                ts = datetime.now(timezone.utc)
            docs.append(Document(doc_id=f"R{i:04d}", source=self.name,
                                 published_at=ts, title=title, text=desc))
        return docs


def load_all(sources) -> list[Document]:
    docs: list[Document] = []
    for src in sources:
        docs.extend(src.load())
    docs.sort(key=lambda d: d.published_at)
    return docs
