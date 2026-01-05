"""Eval to measure the hookiness/engagement potential of generated posts."""

import json
import os
import logging
from dataclasses import dataclass
from typing import Dict, Any

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load API key from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"


@dataclass
class HookinessScore:
    """Scores for a single post's hookiness."""
    post: str
    news_hook: int  # 1-5: Does it lead with news/timely info?
    specificity: int  # 1-5: Does it have specific numbers (%, $, dates)?
    urgency: int  # 1-5: Does it create FOMO/urgency?
    human_voice: int  # 1-5: Does it sound human vs robotic?
    scroll_stop: int  # 1-5: Would this stop someone scrolling?
    total: int  # Sum of all scores (max 25)
    reasoning: str  # Why the scores were given


# Sample posts to evaluate - mix of old style and new style
SAMPLE_POSTS = [
    # OLD STYLE (generic, boring)
    {
        "type": "old_style",
        "post": "AAPL Covered Call | Strike $180 | Premium $3.50 | POP 72% | Exp Jan 17 #options #trading"
    },
    {
        "type": "old_style",
        "post": "📊 MSFT Put Credit Spread | $400/$395 | $1.20 credit | 75% POP | Good risk/reward #stocks"
    },
    {
        "type": "old_style",
        "post": "GOOGL Iron Condor opportunity | Strikes 140/145/160/165 | Premium $2.50 | Neutral outlook #options"
    },
    # NEW STYLE (news-driven, hooky)
    {
        "type": "new_style",
        "post": "NVDA just hit all-time highs on AI chip demand 📈\n\nHere's how to profit:\n→ Sell the $950 call (Jan 17)\n→ Collect $12 premium\n→ 75% probability of profit\n\nIf you own shares, this is free income."
    },
    {
        "type": "new_style",
        "post": "Everyone's bearish on TSLA after the delivery miss.\n\nThat's exactly why I'm selling puts.\n\n$240 put, Jan 17 expiry\n→ $8.50 premium (3.5% return in 2 weeks)\n→ 78% win rate\n\nFear = premium. I'll take it."
    },
    {
        "type": "new_style",
        "post": "META reports earnings Thursday after close.\n\nIV is at 65% - here's how to profit from the crush:\n\n→ Iron Condor: $550/$560/$610/$620\n→ Collect $4.20\n→ Max profit if META stays in range\n\nWin rate: 72%"
    },
    {
        "type": "new_style",
        "post": "AAPL broke $182 resistance this morning 🚀\n\nSelling the $190 weekly call:\n→ $2.40 credit (1.3% in 4 days)\n→ 78% probability of profit\n→ Earnings not until Jan 30\n\nBreakout = cushion. Let's collect premium."
    },
]


SCORING_PROMPT = """You are evaluating social media posts for their "hookiness" - how likely they are to stop someone scrolling and engage them.

Score this post on 5 criteria (1-5 scale each, where 5 is best):

1. NEWS_HOOK (1-5): Does it lead with timely news or just generic info?
   - 1: No news, just data dump
   - 3: Mentions a stock but no catalyst
   - 5: Leads with breaking news, price action, or event

2. SPECIFICITY (1-5): Does it have specific numbers?
   - 1: Vague ("good premium", "solid play")
   - 3: Some numbers but generic
   - 5: Specific prices, percentages, dates, metrics

3. URGENCY (1-5): Does it create FOMO or urgency?
   - 1: Could post this any day
   - 3: Somewhat time-relevant
   - 5: "Act now" feeling, expiring soon, just happened

4. HUMAN_VOICE (1-5): Does it sound like a human or a bot?
   - 1: Robotic template, no personality
   - 3: Functional but bland
   - 5: Conversational, personality, relatable

5. SCROLL_STOP (1-5): Would this stop someone mid-scroll?
   - 1: Easy to ignore
   - 3: Might glance at it
   - 5: Would definitely stop and read

POST TO EVALUATE:
\"\"\"
{post}
\"\"\"

Respond in this exact JSON format only, no other text:
{{
    "news_hook": <1-5>,
    "specificity": <1-5>,
    "urgency": <1-5>,
    "human_voice": <1-5>,
    "scroll_stop": <1-5>,
    "reasoning": "<brief explanation of scores>"
}}
"""


def score_post(post: str) -> HookinessScore:
    """Score a single post for hookiness using Gemini REST API."""
    prompt = SCORING_PROMPT.format(post=post)

    if not GEMINI_API_KEY:
        return HookinessScore(
            post=post,
            news_hook=0, specificity=0, urgency=0,
            human_voice=0, scroll_stop=0, total=0,
            reasoning="Error: GEMINI_API_KEY not set"
        )

    try:
        with httpx.Client(timeout=60) as client:
            response = client.post(
                f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": 500,
                    }
                }
            )
            response.raise_for_status()
            data = response.json()

        # Extract text from response
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()

        # Parse JSON from response
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]

        scores = json.loads(text.strip())

        return HookinessScore(
            post=post,
            news_hook=scores["news_hook"],
            specificity=scores["specificity"],
            urgency=scores["urgency"],
            human_voice=scores["human_voice"],
            scroll_stop=scores["scroll_stop"],
            total=sum([
                scores["news_hook"],
                scores["specificity"],
                scores["urgency"],
                scores["human_voice"],
                scores["scroll_stop"],
            ]),
            reasoning=scores["reasoning"]
        )
    except Exception as e:
        logger.error(f"Failed to score post: {e}")
        return HookinessScore(
            post=post,
            news_hook=0, specificity=0, urgency=0,
            human_voice=0, scroll_stop=0, total=0,
            reasoning=f"Error: {e}"
        )


def run_eval() -> Dict[str, Any]:
    """Run the hookiness eval on all sample posts."""
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY environment variable not set")
        print("Run: export GEMINI_API_KEY=your_api_key")
        return {}

    results = {
        "old_style": [],
        "new_style": [],
    }

    print("=" * 60)
    print("HOOKINESS EVAL - Measuring Post Engagement Potential")
    print("=" * 60)
    print()

    for sample in SAMPLE_POSTS:
        post_type = sample["type"]
        post = sample["post"]

        print(f"Scoring {post_type} post...")
        score = score_post(post)
        results[post_type].append(score)

        print(f"  Total: {score.total}/25")
        print(f"  - News Hook: {score.news_hook}/5")
        print(f"  - Specificity: {score.specificity}/5")
        print(f"  - Urgency: {score.urgency}/5")
        print(f"  - Human Voice: {score.human_voice}/5")
        print(f"  - Scroll Stop: {score.scroll_stop}/5")
        print(f"  Reasoning: {score.reasoning[:100]}...")
        print()

    # Calculate averages
    old_avg = sum(s.total for s in results["old_style"]) / len(results["old_style"])
    new_avg = sum(s.total for s in results["new_style"]) / len(results["new_style"])

    print("=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    print(f"Old Style Average: {old_avg:.1f}/25")
    print(f"New Style Average: {new_avg:.1f}/25")
    if old_avg > 0:
        print(f"Improvement: {((new_avg - old_avg) / old_avg * 100):.1f}%")
    else:
        print("Improvement: N/A (could not score posts - check API key)")
    print()

    # Breakdown by criteria
    print("Average by Criteria:")
    for criteria in ["news_hook", "specificity", "urgency", "human_voice", "scroll_stop"]:
        old_crit = sum(getattr(s, criteria) for s in results["old_style"]) / len(results["old_style"])
        new_crit = sum(getattr(s, criteria) for s in results["new_style"]) / len(results["new_style"])
        print(f"  {criteria}: Old={old_crit:.1f} → New={new_crit:.1f} ({new_crit - old_crit:+.1f})")

    print("=" * 60)

    return {
        "old_style_avg": old_avg,
        "new_style_avg": new_avg,
        "improvement_pct": ((new_avg - old_avg) / old_avg * 100) if old_avg > 0 else 0,
        "results": results,
    }


if __name__ == "__main__":
    run_eval()
