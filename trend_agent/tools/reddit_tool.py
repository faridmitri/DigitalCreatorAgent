"""Reddit Rising Posts tool — no API key required.

Fetches the 'rising' feed from a given subreddit using Reddit's
public JSON endpoint. Used by the researcher's discoverer agents.
"""

import logging
from typing import Any

import requests

_REDDIT_BASE = "https://www.reddit.com/r"
_TIMEOUT_SECONDS = 30
_HEADERS = {"User-Agent": "trend-bot/1.0"}

logger = logging.getLogger(__name__)


def fetch_rising_posts(subreddit: str, max_results: int = 5) -> dict[str, Any]:
    """Fetch the top rising posts from a subreddit.

    Uses Reddit's public /rising.json endpoint — no API key required.
    Call this ONCE per discoverer invocation with the subreddit assigned
    to your category.

    Args:
        subreddit:   Subreddit name without the r/ prefix (e.g. "artificial").
        max_results: How many posts to return (default 5).

    Returns:
        On success:
            {
                "subreddit": "<echoed>",
                "posts": [
                    {
                        "title": "<post title>",
                        "score": <int upvotes>,
                        "upvote_ratio": <float>,
                        "url": "<external link the post points to>",
                        "permalink": "https://www.reddit.com<reddit permalink>",
                        "num_comments": <int>,
                        "created_utc": <float>
                    },
                    ...
                ],
                "count": <int>
            }
        On error: {"error": "<message>"}
    """
    url = f"{_REDDIT_BASE}/{subreddit}/rising.json?limit={max_results}"
    try:
        response = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as exc:
        return {"error": f"Reddit request failed: {exc}"}
    except ValueError as exc:
        return {"error": f"Reddit returned non-JSON response: {exc}"}

    try:
        children = data["data"]["children"]
    except (KeyError, TypeError) as exc:
        return {"error": f"Unexpected Reddit response shape: {exc}"}

    posts = []
    for child in children[:max_results]:
        try:
            d = child["data"]
            posts.append(
                {
                    "title": d.get("title", ""),
                    "score": int(d.get("score", 0)),
                    "upvote_ratio": float(d.get("upvote_ratio", 0.0)),
                    "url": d.get("url", ""),
                    "permalink": f"https://www.reddit.com{d.get('permalink', '')}",
                    "num_comments": int(d.get("num_comments", 0)),
                    "created_utc": float(d.get("created_utc", 0.0)),
                }
            )
        except (KeyError, TypeError, ValueError):
            # skip malformed post; never raise
            continue

    return {"subreddit": subreddit, "posts": posts, "count": len(posts)}
