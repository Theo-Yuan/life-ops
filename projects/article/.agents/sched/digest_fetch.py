#!/usr/bin/env python3
"""Fetch candidate articles from Google News RSS for configured topics."""
import html
import os
import re
import subprocess
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TOPICS_FILE = os.path.join(SCRIPT_DIR, "topics.txt")
HL = "en-US"
GL = "US"


def fetch_rss(url: str, attempts: int = 5) -> list[dict]:
    last_err = None
    for i in range(attempts):
        try:
            out = subprocess.run(
                ["curl", "-sS", "--max-time", "20", "-A", "Mozilla/5.0", url],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if out.returncode != 0 or not out.stdout.strip():
                raise RuntimeError(out.stderr.strip() or "empty response")
            root = ET.fromstring(out.stdout)
            items = []
            for item in root.findall("./channel/item"):
                title = html.unescape(item.findtext("title", "")).strip()
                link = html.unescape(item.findtext("link", "")).strip()
                pub = item.findtext("pubDate", "").strip()
                desc = html.unescape(item.findtext("description", "")).strip()
                desc = re.sub(r"<[^>]+>", "", desc)
                source = item.findtext("source", "").strip()
                if source and title.endswith(" - " + source):
                    title = title[: -(len(source) + 3)]
                items.append({"title": title, "link": link, "source": source, "date": pub, "snippet": desc})
            return items
        except Exception as e:
            last_err = e
            time.sleep(5 * (2 ** i))
    sys.stderr.write(f"fetch failed after {attempts} attempts: {last_err}\n")
    return []


def main():
    out_path = sys.argv[1]
    topics = []
    with open(TOPICS_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            label, _, query = line.partition("|")
            topics.append((label.strip(), query.strip()))

    seen = set()
    with open(out_path, "w", encoding="utf-8") as out:
        for label, query in topics:
            url = ("https://news.google.com/rss/search?q="
                   + urllib.parse.quote(query)
                   + f"&hl={HL}&gl={GL}&ceid={GL}:{HL[:2]}")
            items = fetch_rss(url)[:8]
            for it in items:
                if it["link"] in seen:
                    continue
                seen.add(it["link"])
                out.write(f"{label} | {it['title']} | {it['source']} | {it['date']} | {it['link']} | {it['snippet']}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
