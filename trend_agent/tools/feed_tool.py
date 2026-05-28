"""RSS/Atom feed source tool — no API key required.

Fetches recent entries from a curated set of official Google Cloud feeds.
This is the on-topic alternative to Reddit for a Google Cloud-focused blog:
Reddit gives velocity (what is gaining attention), whereas these feeds give
authoritative freshness (what Google actually shipped or announced).

Why a feed *registry* instead of a free-form URL argument:
    LLMs frequently mangle long URLs. Each discoverer passes a short, fixed
    ``feed_key`` (e.g. ``"gcp_blog"``) and the URL is resolved here, so a typo
    in the model's output can never point the fetcher at the wrong endpoint.

Feeds (verified May 2026):
    gcp_blog      Google Cloud blog — official product news & announcements.
    gcp_releases  Google Cloud release notes — all-product changelog feed.
    gcp_learning  Training & Certifications topic feed — courses, exams,
                  learning paths, and new credentials.
"""

from __future__ import annotations

import calendar
import logging
import re
import time
from typing import Any

import feedparser

logger = logging.getLogger(__name__)

# Short, fixed keys → canonical feed URLs. The LLM only ever sees the keys.
_FEEDS: dict[str, str] = {
    "gcp_blog": "https://cloudblog.withgoogle.com/rss",
    "gcp_releases": "https://cloud.google.com/feeds/gcp-release-notes.xml",
    "gcp_learning": "https://cloudblog.withgoogle.com/topics/training-certifications/rss/",
}

# A descriptive User-Agent is polite and avoids some bot filters.
_USER_AGENT = "trend-bot/1.0 (+https://blog.cloud-edify.com)"

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _strip_html(text: str, limit: int = 400) -> str:
    """Reduce a feed's HTML summary to a short plain-text snippet."""
    if not text:
        return ""
    plain = _TAG_RE.sub(" ", text)
    plain = _WS_RE.sub(" ", plain).strip()
    return plain[:limit]


def _entry_age_hours(entry: Any, now_utc: float) -> float | None:
    """Age of an entry in hours, or None if it has no usable timestamp."""
    struct = entry.get("published_parsed") or entry.get("updated_parsed")
    if not struct:
        return None
    # feedparser returns a UTC time.struct_time; calendar.timegm reads it as UTC.
    published_utc = calendar.timegm(struct)
    return (now_utc - published_utc) / 3600.0


def fetch_feed_items(
    feed_key: str,
    max_results: int = 5,
    max_age_hours: int = 72,
) -> dict[str, Any]:
    """Fetch recent entries from one curated Google Cloud feed.

    Call this EXACTLY ONCE per discoverer invocation, with the ``feed_key``
    assigned to your category. Only entries newer than ``max_age_hours`` are
    returned, so a daily run never re-surfaces stale items.

    Args:
        feed_key: One of ``"gcp_blog"``, ``"gcp_releases"``, ``"gcp_learning"``.
        max_results: How many of the most recent items to return (1..15).
        max_age_hours: Drop entries older than this. Release-note and blog
            feeds carry weeks of history; this keeps the run focused on what
            is genuinely new.

    Returns:
        On success::

            {
                "feed": "<echoed feed_key>",
                "items": [
                    {
                        "title": "<entry title>",
                        "url": "<entry link>",
                        "summary": "<plain-text snippet, <=400 chars>",
                        "published": "<ISO 8601 string or ''>",
                        "age_hours": <float, rounded to 1 dp>,
                    },
                    ...
                ],
                "count": <int>,
            }

        On error: ``{"error": "<message>"}``.
    """
    if feed_key not in _FEEDS:
        return {
            "error": (
                f"Unknown feed_key {feed_key!r}. "
                f"Valid keys: {', '.join(sorted(_FEEDS))}."
            )
        }

    max_results = max(1, min(int(max_results), 15))
    url = _FEEDS[feed_key]

    try:
        parsed = feedparser.parse(url, agent=_USER_AGENT)
    except Exception as exc:  # feedparser is defensive, but never let it raise
        logger.exception("feed_tool: parse failed for %s", feed_key)
        return {"error": f"Feed parse failed for {feed_key}: {exc}"}

    # feedparser sets `bozo` on malformed feeds but still returns whatever it
    # could parse. Only treat it as fatal when no entries came back at all.
    if getattr(parsed, "bozo", 0) and not parsed.entries:
        reason = getattr(parsed, "bozo_exception", "unknown parse error")
        return {"error": f"Malformed feed for {feed_key}: {reason}"}

    now_utc = time.time()
    items: list[dict[str, Any]] = []

    for entry in parsed.entries:
        age = _entry_age_hours(entry, now_utc)
        # Keep undated entries (age is None) rather than silently dropping them;
        # only filter out entries we can confirm are too old.
        if age is not None and age > max_age_hours:
            continue

        struct = entry.get("published_parsed") or entry.get("updated_parsed")
        published_iso = (
            time.strftime("%Y-%m-%dT%H:%M:%SZ", struct) if struct else ""
        )

        items.append(
            {
                "title": entry.get("title", "").strip(),
                "url": entry.get("link", "").strip(),
                "summary": _strip_html(entry.get("summary", "")),
                "published": published_iso,
                "age_hours": round(age, 1) if age is not None else None,
            }
        )
        if len(items) >= max_results:
            break

    return {"feed": feed_key, "items": items, "count": len(items)}