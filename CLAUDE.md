# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run agent (dry-run mode - no actual posting)
python -m agent.main --platform twitter --dry-run

# Run agent for real posting
python -m agent.main --platform twitter

# Custom task
python -m agent.main --task "Post a bullish play for NVDA to twitter"

# Run evaluation (score agent output quality)
python -m agent.main --eval --runs 5

# Run tests
pytest
```

## Error Handling Policy

**No silent fallbacks. Use exceptions that are gracefully caught.**

- Do NOT use fallback behavior that silently degrades functionality
- Raise exceptions when features are unavailable or misconfigured
- Catch exceptions at appropriate boundaries and log clearly
- Let failures surface to the caller so they can be addressed

Example - WRONG:
```python
try:
    enable_grounding()
except Exception:
    # Silent fallback - BAD
    pass
```

Example - RIGHT:
```python
try:
    enable_grounding()
except GroundingError as e:
    logger.error(f"Grounding failed: {e}")
    raise  # Let caller handle it
```

## Architecture

This is an **idea-driven ReAct agent** with Google Search grounding that:
1. Researches market trends via web search
2. Forms an investment thesis
3. Finds options via Alpha Copilot
4. Posts story-driven content

### Agent Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT LOOP (with Grounding)                  │
│                                                                 │
│   LLM (Gemini + Google Search Grounding)                        │
│   ├── Researches web automatically while reasoning              │
│   ├── Forms thesis from findings                                │
│   └── Calls tools to execute                                    │
│                                                                 │
│   Iteration 1-2: Research & Ideate (grounding active)           │
│     "What's moving today? → NVDA up 5% on AI news"              │
│     "Thesis: NVDA momentum likely to continue"                  │
│                                                                 │
│   Iteration 3: query_alpha_copilot("bullish NVDA options")      │
│   Iteration 4: compose_post(thesis + options)                   │
│   Iteration 5: publish()                                        │
│   Iteration 6: done()                                           │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

**Agent Layer** (`agent/`)
- `main.py` - CLI entry point with `--eval` mode
- `loop.py` - ReAct loop implementation
- `llm.py` - Gemini client using `google-genai` package with Google Search grounding
- `eval.py` - Evaluation layer for scoring output quality
- `config.py` - Environment-based configuration

**LLM Package**: Uses `google-genai` (NOT deprecated `google-generativeai`)

**Tools** (`tools/`)
- Extend `BaseTool` abstract class
- Tools: `query_alpha_copilot`, `compose_post` (with thesis), `publish`, `check_recent_posts`, `get_platform_status`, `done`

**Platforms** (`platforms/`)
- Extend `BasePlatform`
- Currently Twitter implemented

**Prompts** (`prompts/system.py`)
- Research-first flow prompting
- Guides agent to form thesis before finding options

### Evaluation Layer

Run `--eval` to score agent output quality:
- Runs agent N times
- LLM judge scores each tweet on 5 criteria (50 points max):
  - Thesis Clarity (1-10)
  - News-Driven (1-10)
  - Actionable (1-10)
  - Engagement (1-10)
  - Originality (1-10)
- Generates report with averages and best/worst runs

## Configuration

Environment variables (`.env` file):
- `GEMINI_API_KEY` - Required for LLM
- `ALPHA_COPILOT_API_URL` - Backend API (default: localhost:8002)
- `TWITTER_*` - Twitter API credentials
- `DRY_RUN` - Set to `true` to skip posting (default: true)

## Troubleshooting

### Common Errors

**Supabase auth failure (`Invalid credentials`)**
- Check `SUPABASE_EMAIL` and `SUPABASE_PASSWORD` in `.env`
- Verify user exists in Supabase dashboard → Authentication → Users
- Reset password if needed and update `.env`

**Twitter 401 Unauthorized**
- Twitter API credentials expired or revoked
- Regenerate tokens in Twitter Developer Portal
- Update `TWITTER_*` values in `.env`

### Validating Credentials

Test Supabase auth:
```bash
curl -X POST "$SUPABASE_URL/auth/v1/token?grant_type=password" \
  -H "apikey: $SUPABASE_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email": "'"$SUPABASE_EMAIL"'", "password": "'"$SUPABASE_PASSWORD"'"}'
```

## Content Guidelines

### Tone: Suggestive, Not Certain

Posts should use cautious language to avoid sounding like financial advice.

**Use:** "Could", "Might", "Possible", "Potential", "Worth watching", "Interesting setup"

**Avoid:** "Will", "Definitely", "Guaranteed", "Buy this", "You should"

### Specificity

Theses should include concrete details from research:
- Numbers, dates, names, or events when available
- Avoid generic phrases like "sector strength" or "analyst upgrades"

### Variety

Vary phrasing across posts - don't use the same structure every time.

## Post Format

Posts lead with thesis and include `#NFA` disclaimer:

```
Trade Idea

NVDA +5% ahead of earnings - could extend if results beat.

$NVDA Call Option
$145 | Exp: Jan 17
Premium: $3.20 | POP: 45%

#NVDA #options #NFA
```
