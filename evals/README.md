# Evaluation System

**`agent/eval.py`** - Unified evaluation system used in production agent loop
- Combines hookiness (engagement) + quality (content) metrics
- Gates posts before publishing - low scores → abort
- Configurable thresholds via environment variables

## Scoring Criteria

### Hookiness (Engagement) - 25 points max

Measures how likely a post is to stop someone mid-scroll:

1. **News Hook (1-5):** Timely news or generic?
   - 1: No news, just data dump
   - 5: Leads with breaking news, price action, or event

2. **Specificity (1-5):** Specific numbers or vague?
   - 1: Vague ("good premium")
   - 5: Specific prices, %, dates, metrics

3. **Urgency (1-5):** FOMO/time-pressure or evergreen?
   - 1: Could post any day
   - 5: "Act now" feeling, expiring soon

4. **Human Voice (1-5):** Conversational or robotic?
   - 1: Template-heavy, no personality
   - 5: Sounds like a real person

5. **Scroll Stop (1-5):** Would this stop your scroll?
   - 1: Easy to ignore
   - 5: Definitely would stop and read

### Quality (Content) - 50 points max

Measures the substance and value of the content:

1. **Thesis Clarity (1-10):** Clear directional view?
   - Does it have a clear investment thesis?
   - Bullish/bearish stance articulated?

2. **News Driven (1-10):** Tied to current events?
   - Connected to today's news?
   - References specific catalysts?

3. **Actionable (1-10):** Specific trade details?
   - Includes strike, expiration, premium?
   - Probability of profit mentioned?

4. **Engagement (1-10):** Interesting/compelling?
   - Would you keep reading?
   - Compelling narrative?

5. **Originality (1-10):** Fresh angle vs template?
   - Unique perspective?
   - Avoids generic phrasing?

### Total: 75 points max

**Default Thresholds:**
- Hookiness minimum: 15/25 (60%)
- Quality minimum: 30/50 (60%)
- Total minimum: 45/75 (60%)

**Target for consistent quality:** 55+ (73%)
**Excellent posts:** 65+ (87%)

## Configuration

Set thresholds in `.env`:

```bash
EVAL_HOOKINESS_MIN=15  # Minimum hookiness score (1-25)
EVAL_QUALITY_MIN=30    # Minimum quality score (1-50)
EVAL_TOTAL_MIN=45      # Minimum total score (1-75)
EVAL_MODE=both         # hookiness, quality, or both
```

## How It Works

1. **Agent writes post** using `write_post` tool
2. **Evaluation runs automatically** before publishing
3. **If score < threshold:** Post is rejected, agent aborts with feedback
4. **If score >= threshold:** Post proceeds to `cross_post`
5. **Eval report logged** with full breakdown

## Example Scores

### Bad Post (Score: ~20/75)
```
AAPL Covered Call | $180 Strike | $3.50 Premium | 72% POP #options
```
- Hookiness: 8/25 (no news, template, generic)
- Quality: 12/50 (no thesis, not news-driven, unoriginal)
- **FAILS** - Would be rejected

### Good Post (Score: ~55/75)
```
NVDA just hit all-time highs on AI chip demand 📈

Here's how to profit if you own shares:
→ Sell the $950 call (Jan 17)
→ Collect $12 premium
→ 75% probability of profit

This is free income if the stock stays below $950. #NFA
```
- Hookiness: 20/25 (news hook, specific, conversational)
- Quality: 35/50 (actionable, news-driven, decent engagement)
- **PASSES** - Would be published

### Excellent Post (Score: ~67/75)
```
Everyone's bearish on TSLA after the delivery miss (-12% today).

That's exactly why I'm selling puts.

$240 put, Jan 17 expiry:
→ $8.50 premium (3.5% return in 2 weeks)
→ 78% win rate
→ I'm happy buying TSLA at $231 if assigned

Fear = premium. I'll take it. #NFA
```
- Hookiness: 23/25 (strong news hook, urgent, very human)
- Quality: 44/50 (clear thesis, news-driven, original angle)
- **PASSES EASILY** - High-quality content
