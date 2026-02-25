"""Tools for community engagement - finding and replying to popular FinTwit tweets."""

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, List

from google import genai
from google.genai import types
from google.genai.errors import ServerError

from .base import BaseTool
from agent.config import Config
from agent.retry import retry_with_backoff

logger = logging.getLogger(__name__)

# Max replies per engage run to avoid looking spammy
MAX_REPLIES_PER_RUN = 3

# Reply history file to track who we've replied to
REPLY_HISTORY_PATH = ".data/reply_history.json"


def _load_reply_history() -> List[Dict[str, Any]]:
    """Load reply history from local cache."""
    path = Path(REPLY_HISTORY_PATH)
    if not path.exists():
        return []
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_reply_history(history: List[Dict[str, Any]]) -> None:
    """Save reply history to local cache."""
    path = Path(REPLY_HISTORY_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep last 200 entries
    history = history[-200:]
    with open(path, "w") as f:
        json.dump(history, f, indent=2)


def _get_recent_reply_authors(hours: int = 24) -> set:
    """Get authors we've replied to in the last N hours."""
    history = _load_reply_history()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    recent_authors = set()
    for entry in history:
        try:
            created = datetime.fromisoformat(entry["created_at"])
            if created > cutoff:
                recent_authors.add(entry.get("author", "").lower())
        except (KeyError, ValueError):
            continue
    return recent_authors


def _get_recent_reply_tweet_ids(hours: int = 24) -> set:
    """Get tweet IDs we've replied to in the last N hours."""
    history = _load_reply_history()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    recent_ids = set()
    for entry in history:
        try:
            created = datetime.fromisoformat(entry["created_at"])
            if created > cutoff:
                tid = entry.get("tweet_id", "")
                if tid:
                    recent_ids.add(tid)
        except (KeyError, ValueError):
            continue
    return recent_ids


def _record_reply(tweet_id: str, author: str, reply_text: str) -> None:
    """Record a reply in the history."""
    history = _load_reply_history()
    history.append({
        "tweet_id": tweet_id,
        "author": author.lower(),
        "reply_text": reply_text,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    _save_reply_history(history)


class SearchTweetsTool(BaseTool):
    """Find popular tweets about trending stocks using Google Search."""

    name = "search_tweets"
    description = (
        "Search for popular recent tweets about a stock or market topic. "
        "Returns tweet URLs and summaries. Use this to find tweets to reply to."
    )

    def __init__(self):
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)
        self.model_name = Config.LLM_MODEL
        self.grounding_enabled = Config.ENABLE_GROUNDING

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "What to search for. Example: 'popular tweets about NVDA earnings today' "
                            "or 'FinTwit discussion about Tesla stock drop'"
                        ),
                    },
                },
                "required": ["query"],
            },
        }

    def execute(self, query: str = "", **kwargs) -> str:
        """Search for popular tweets about a topic using Google Search grounding."""
        if not query:
            return "ERROR: query is required."

        logger.info(f"Searching for tweets about: {query}")

        search_prompt = (
            f"Find 3-5 popular recent tweets (from x.com or twitter.com) about: {query}\n\n"
            "CRITICAL: Each tweet MUST be from a DIFFERENT author with a DIFFERENT tweet URL. "
            "Do NOT return the same tweet URL twice. If you cannot find 3+ DISTINCT real tweet URLs, "
            "return only the ones you can verify.\n\n"
            "For each tweet, provide:\n"
            "1. The EXACT tweet URL (must be a real x.com/username/status/ID URL)\n"
            "2. The author's @handle\n"
            "3. A brief summary of what they said\n"
            "4. Approximate engagement (likes/retweets if visible)\n\n"
            "Focus on tweets from accounts with significant followings (finance, "
            "options trading, market analysis accounts). Prefer tweets from the "
            "last 24 hours.\n\n"
            "Format each as:\n"
            "TWEET: [url]\n"
            "AUTHOR: @[handle]\n"
            "SUMMARY: [what they said]\n"
            "ENGAGEMENT: [likes/retweets estimate]\n"
        )

        tools = []
        if self.grounding_enabled:
            tools.append(types.Tool(google_search=types.GoogleSearch()))

        config = types.GenerateContentConfig(temperature=0.3)
        if tools:
            config.tools = tools

        def _do_search():
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=search_prompt,
                config=config,
            )
            if not response.text:
                raise ValueError("No search results from Gemini")
            return response.text

        result = retry_with_backoff(
            func=_do_search,
            retryable_exceptions=ServerError,
            operation_name="Tweet search",
        )

        # Extract tweet IDs from URLs in the response
        raw_tweet_ids = re.findall(
            r'https?://(?:x\.com|twitter\.com)/\w+/status/(\d+)', result
        )

        # Deduplicate preserving order
        seen = set()
        unique_tweet_ids = []
        for tid in raw_tweet_ids:
            if tid not in seen:
                seen.add(tid)
                unique_tweet_ids.append(tid)

        if len(unique_tweet_ids) < len(raw_tweet_ids):
            dupe_count = len(raw_tweet_ids) - len(unique_tweet_ids)
            logger.warning(f"Removed {dupe_count} duplicate tweet IDs from search results")

        # Filter out tweet IDs we've already replied to
        recent_tweet_ids = _get_recent_reply_tweet_ids(hours=24)
        fresh_tweet_ids = [tid for tid in unique_tweet_ids if tid not in recent_tweet_ids]

        if len(fresh_tweet_ids) < len(unique_tweet_ids):
            skipped = len(unique_tweet_ids) - len(fresh_tweet_ids)
            logger.info(f"Filtered out {skipped} tweet IDs already replied to")

        if len(fresh_tweet_ids) < 2:
            logger.warning(f"Only {len(fresh_tweet_ids)} fresh unique tweets found — consider broadening search")

        # Check reply history to filter out authors we've already replied to
        recent_authors = _get_recent_reply_authors(hours=24)

        lines = [
            "TWEET SEARCH RESULTS:",
            "=" * 40,
            "",
            result.strip(),
            "",
            "=" * 40,
            f"Found {len(fresh_tweet_ids)} fresh unique tweet IDs: {', '.join(fresh_tweet_ids[:5])}",
        ]

        if recent_tweet_ids & seen:
            lines.append(f"\nALREADY REPLIED TO TWEETS (filtered out): {', '.join(recent_tweet_ids & seen)}")

        if recent_authors:
            lines.append(f"\nALREADY REPLIED TO AUTHORS (skip these): {', '.join(recent_authors)}")

        lines.extend([
            "",
            "NEXT: Pick the best tweets to reply to. Each reply MUST be to a DIFFERENT tweet ID.",
            "Compose replies that:",
            "- Reference options data (IV rank, unusual flow, POP, premium levels)",
            "- Make readers curious enough to check your profile",
            "- Sound like a sharp options trader, not a generic commentator",
            f"- Maximum {MAX_REPLIES_PER_RUN} replies per session, each to a DIFFERENT tweet",
        ])

        return "\n".join(lines)


class ReplyToTweetTool(BaseTool):
    """Reply to a specific tweet with helpful commentary."""

    name = "reply_to_tweet"
    description = (
        "Reply to a specific tweet by ID. Compose a helpful, non-spammy reply "
        "that adds value to the conversation. Optionally include a link to "
        "alphacopilot.app if naturally relevant."
    )

    def __init__(self):
        self._reply_count = 0
        self._replied_tweet_ids = set()

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "tweet_id": {
                        "type": "string",
                        "description": "The tweet ID to reply to (numeric string from the tweet URL)",
                    },
                    "author": {
                        "type": "string",
                        "description": "The @handle of the tweet author (for tracking, without @)",
                    },
                    "reply_text": {
                        "type": "string",
                        "description": "Your reply text. Must add value. Max 280 characters.",
                    },
                },
                "required": ["tweet_id", "author", "reply_text"],
            },
        }

    def execute(self, tweet_id: str = "", author: str = "", reply_text: str = "", **kwargs) -> str:
        """Reply to a tweet."""
        if not tweet_id or not reply_text:
            return "ERROR: tweet_id and reply_text are required."

        if not author:
            return "ERROR: author handle is required for reply tracking."

        # Check reply limit
        if self._reply_count >= MAX_REPLIES_PER_RUN:
            return f"REPLY_LIMIT: Already sent {MAX_REPLIES_PER_RUN} replies this session. Call done."

        # Check if we already replied to this author recently
        recent_authors = _get_recent_reply_authors(hours=24)
        if author.lower().lstrip("@") in recent_authors:
            return f"SKIP: Already replied to @{author} in the last 24 hours. Pick a different tweet."

        # In-session tweet_id dedup
        if tweet_id in self._replied_tweet_ids:
            return f"DUPLICATE_TWEET: Already replied to tweet {tweet_id} this session. Pick a DIFFERENT tweet."

        # Cross-session tweet_id dedup
        recent_tweet_ids = _get_recent_reply_tweet_ids(hours=24)
        if tweet_id in recent_tweet_ids:
            return f"DUPLICATE_TWEET: Already replied to tweet {tweet_id} in last 24h. Pick a DIFFERENT tweet."

        # Validate reply length
        if len(reply_text) > 280:
            return f"TOO_LONG: Reply is {len(reply_text)} chars. Max 280. Shorten it."

        # Check for spam signals
        link_count = reply_text.lower().count("http") + reply_text.lower().count("alphacopilot")
        if link_count > 1:
            return "TOO_PROMOTIONAL: Reply has too many links. Keep it to 0-1 links max."

        if Config.DRY_RUN:
            logger.info(f"[DRY RUN] Would reply to tweet {tweet_id} by @{author}: {reply_text[:50]}...")
            self._reply_count += 1
            self._replied_tweet_ids.add(tweet_id)
            return (
                f"[DRY RUN] Reply composed for tweet {tweet_id} by @{author}:\n"
                f"{reply_text}\n\n"
                f"Replies sent this session: {self._reply_count}/{MAX_REPLIES_PER_RUN}"
            )

        # Post the reply via Twitter API
        from platforms.twitter import TwitterPlatform

        twitter = TwitterPlatform()
        result = twitter.publish(content=reply_text, reply_to_id=tweet_id)

        if result.get("success"):
            self._reply_count += 1
            self._replied_tweet_ids.add(tweet_id)
            # Record in history
            _record_reply(tweet_id, author, reply_text)

            return (
                f"REPLY_SENT to @{author} (tweet {tweet_id}):\n"
                f"{reply_text}\n\n"
                f"Reply URL: {result.get('url', 'N/A')}\n"
                f"Replies sent this session: {self._reply_count}/{MAX_REPLIES_PER_RUN}"
            )
        else:
            error = result.get("error", "Unknown error")
            return f"REPLY_FAILED: {error}"


class EngageDoneTool(BaseTool):
    """Signal completion of engagement session."""

    name = "engage_done"
    description = "Signal that the engagement session is complete. Call this when done replying."

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "Brief summary of what was accomplished (replies sent, topics engaged on)",
                    },
                },
                "required": ["summary"],
            },
        }

    def execute(self, summary: str = "", **kwargs) -> str:
        return f"ENGAGE_COMPLETE: {summary}"
