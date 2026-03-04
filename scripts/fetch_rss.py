#!/usr/bin/env python3
"""
fetch_rss.py

Fetches the latest post from each RSS feed listed in feeds.json.
Sends new (unseen) posts to a Discord webhook as rich embeds.
Tracks seen post IDs in state/seen_posts.json to avoid duplicates.
"""

import json
import os
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
FEEDS_FILE = ROOT / "feeds.json"
STATE_FILE = ROOT / "state" / "seen_posts.json"

# ── Discord config ────────────────────────────────────────────────────────────
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

# Brand colours per source (Discord embed colour, decimal)
SOURCE_COLORS = {
    "Netflix Tech Blog":    16711680,   # Netflix red
    "Uber Engineering":     2067276,    # Uber dark green
    "Meta Engineering":     1054256,    # Meta blue
    "LinkedIn Engineering": 40941,      # LinkedIn blue
    "Cloudflare Blog":      16742144,   # Cloudflare orange
    "GitHub Engineering":   2236962,    # GitHub dark
    "Etsy Code as Craft":   16753920,   # Etsy orange
    "Medium Engineering":   2302755,    # Medium dark
    "Stripe Engineering":   6840569,    # Stripe purple
}
DEFAULT_COLOR = 5793266  # Neutral blue-grey


def load_json(path: Path, default):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def entry_id(entry) -> str:
    """Return a stable unique identifier for a feed entry."""
    return entry.get("id") or entry.get("link") or entry.get("title", "")


def format_date(entry) -> str:
    """Return a human-readable published date, or empty string."""
    for attr in ("published_parsed", "updated_parsed"):
        t = entry.get(attr)
        if t:
            try:
                dt = datetime(*t[:6], tzinfo=timezone.utc)
                return dt.strftime("%B %d, %Y")
            except Exception:
                pass
    return ""


def build_embed(feed_name: str, entry) -> dict:
    """Build a Discord embed dict for a single feed entry."""
    title = entry.get("title", "New Post").strip()
    link = entry.get("link", "")

    # Summary / description — strip HTML tags roughly
    summary_raw = entry.get("summary", "") or entry.get("content", [{}])[0].get("value", "")
    # Very simple HTML tag removal
    import re
    summary_clean = re.sub(r"<[^>]+>", "", summary_raw).strip()
    summary_clean = re.sub(r"\s+", " ", summary_clean)
    description = textwrap.shorten(summary_clean, width=300, placeholder="…") if summary_clean else ""

    date_str = format_date(entry)
    footer_text = f"{feed_name}"
    if date_str:
        footer_text += f"  •  {date_str}"

    color = SOURCE_COLORS.get(feed_name, DEFAULT_COLOR)

    embed = {
        "title": title,
        "url": link,
        "color": color,
        "footer": {"text": footer_text},
    }
    if description:
        embed["description"] = description

    # Author thumbnail from media or image if available
    author_name = None
    for author in entry.get("authors", []):
        author_name = author.get("name")
        break
    if author_name:
        embed["author"] = {"name": author_name}

    return embed


def send_to_discord(feed_name: str, embed: dict) -> bool:
    """POST the embed to the Discord webhook. Returns True on success."""
    if not DISCORD_WEBHOOK_URL:
        print("  ✗  DISCORD_WEBHOOK_URL is not set. Skipping send.", file=sys.stderr)
        return False

    payload = {
        "username": "RSS Tech Feeds",
        "avatar_url": "https://www.svgrepo.com/show/452163/rss.svg",
        "embeds": [embed],
    }

    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=15)
        if resp.status_code in (200, 204):
            return True
        else:
            print(f"  ✗  Discord returned {resp.status_code}: {resp.text[:200]}", file=sys.stderr)
            return False
    except requests.RequestException as exc:
        print(f"  ✗  Request error: {exc}", file=sys.stderr)
        return False


def process_feed(feed_cfg: dict, seen: dict) -> bool:
    """
    Fetch a feed, find the latest unseen entry, post it to Discord.
    Returns True if state was modified.
    """
    name = feed_cfg["name"]
    url = feed_cfg["url"]

    print(f"\n[{name}]")
    print(f"  Fetching: {url}")

    # Some feeds (e.g. Uber) require browser-like headers to avoid 406/404 responses
    parsed = feedparser.parse(
        url,
        request_headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.5",
        },
    )

    if parsed.bozo and not parsed.entries:
        print(f"  ⚠  Feed error or empty: {parsed.bozo_exception}", file=sys.stderr)
        return False

    if not parsed.entries:
        print("  ⚠  No entries found.")
        return False

    # feedparser returns entries newest-first for most feeds
    latest = parsed.entries[0]
    eid = entry_id(latest)

    seen_for_feed = seen.get(name, "")
    if seen_for_feed == eid:
        print(f"  ⏭  Already seen: {eid!r}")
        return False

    title = latest.get("title", "(no title)").strip()
    print(f"  📨  Sending: {title!r}")

    embed = build_embed(name, latest)
    success = send_to_discord(name, embed)

    if success:
        seen[name] = eid
        print(f"  ✅  Sent successfully.")
        return True
    else:
        print(f"  ✗  Failed to send.")
        return False


def main():
    if not DISCORD_WEBHOOK_URL:
        print("ERROR: DISCORD_WEBHOOK_URL environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    feeds = load_json(FEEDS_FILE, [])
    seen = load_json(STATE_FILE, {})

    if not feeds:
        print("No feeds configured in feeds.json", file=sys.stderr)
        sys.exit(1)

    state_changed = False
    for feed_cfg in feeds:
        changed = process_feed(feed_cfg, seen)
        if changed:
            state_changed = True

    if state_changed:
        save_json(STATE_FILE, seen)
        print("\n✅ State file updated.")
    else:
        print("\n⏭  No new posts. State unchanged.")


if __name__ == "__main__":
    main()
