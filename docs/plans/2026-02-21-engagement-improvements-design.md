# Engagement Improvements Design

## Problem

225 posts, 3 followers. Content quality is decent (avg 52/75) but:
1. All posts follow the same trade-idea template regardless of content type
2. The agent only broadcasts — no community engagement
3. Eval scorer biases toward trade posts, discouraging variety

## Changes

### 1. System Prompt: Content-Type-Specific Guidelines

Add distinct formatting rules and examples for each content type:
- **Trade Idea**: Current format (news hook + options trade)
- **Market Question**: Short, provocative question + context. No trade details. End with "What's your read?"
- **Contrarian Take**: Open with "Everyone thinks X. Here's why Y." Bold, opinion-first.
- **Commentary**: Quick sector/macro observation. 1-2 sentences. Punchy.
- **Thread Starter**: Hot take designed to provoke replies. No trade, no data.

Remove universal "REQUIRED Elements" that force trade-post format on non-trade types.

### 2. Eval Scorer: Remove Trade-Post Bias

Current "actionable" score (1-10) awards up to 10 for strike/date/premium/POP. Non-trade posts max ~6 on engagement driver strength.

Fix: Score non-trade posts on engagement metrics instead:
- Strong question / provocative opinion: up to 10
- Specificity of the take: up to 10
- Conversation-starting power: up to 10

### 3. Schedule: Aggressive Content Rotation

Target mix per week (15 posts):
- Trade ideas: 5 (33%) — morning + EOD on select days
- Questions: 4 (27%) — high-engagement time slots
- Commentary/Contrarian: 3 (20%) — midday slots
- Thread starters: 3 (20%) — pre-market for engagement

Rotate deterministically by day-of-week to ensure coverage.

### 4. Engage Mode: Reply to Popular FinTwit Tweets

New `--engage` CLI mode. Uses Gemini + Google Search grounding to:
1. Find popular recent tweets about trending stocks
2. Extract tweet IDs from x.com URLs
3. Compose a helpful, non-spammy reply (with optional alphacopilot.app link)
4. Post reply via Twitter API (free tier supports create_tweet with in_reply_to_tweet_id)

Guardrails:
- Max 3 replies per run
- Must add genuine value (not just promotion)
- Link only when naturally relevant
- Track reply history to avoid replying to same account twice in 24h

Schedule: 2 engage slots per weekday in GitHub Actions.

## Files Modified

- `prompts/system.py` — content-type-specific guidelines and examples
- `agent/eval.py` — equal scoring for non-trade posts
- `agent/main.py` — add `--engage` CLI mode
- `tools/engage.py` — new: search_tweets and reply_to_tweet tools
- `platforms/twitter.py` — add reply method
- `.github/workflows/scheduled-posts.yml` — updated rotation + engage slots
