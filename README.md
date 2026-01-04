# Alpha Copilot Social Agent

An autonomous AI agent that posts options trading insights to social media platforms.

## Architecture

This agent follows the **ReAct (Reason + Act) pattern** - a simple while loop where the LLM:
1. Reasons about the current state
2. Selects a tool to call
3. Executes the tool
4. Observes the result
5. Repeats until task complete

```
┌─────────────────────────────────────────────────┐
│              AGENT MAIN LOOP                     │
│                                                  │
│   while not done:                                │
│       reasoning = llm.think(context)             │
│       tool, args = llm.select_tool()             │
│       result = tools.execute(tool, args)         │
│       context.append(result)                     │
└─────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│                   TOOLS                          │
│  query_alpha_copilot | compose_post | cross_post│
│  publish | check_recent_posts | done            │
└─────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│             PLATFORM ADAPTERS                    │
│          Twitter (X) | Threads (Meta)           │
└─────────────────────────────────────────────────┘
```

## Key Features

- **Uses Alpha Copilot Backend**: Same API as the web app for consistent analysis
- **Cross-Posting**: Posts to both Twitter and Threads simultaneously for maximum reach
- **Promotional Follow-ups**: Automatically adds Alpha Copilot promo posts after insights
- **Platform Agnostic**: Easy to add new platforms (Discord, LinkedIn, etc.)
- **Autonomous**: LLM decides what to query, how to compose, when to post
- **Duplicate Prevention**: Checks recent posts before creating new content

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys (Twitter + Threads)

# Run with dry-run mode (no actual posts)
python -m agent.main --post morning --dry-run

# Run for real (cross-posts to Twitter + Threads)
python -m agent.main --post morning
```

## Usage

```bash
# Morning options alert - posts to Twitter + Threads with promo follow-up
python -m agent.main --post morning

# End-of-day directional play
python -m agent.main --post eod

# High IV opportunity
python -m agent.main --post volatility

# Sector focus (e.g., Financials)
python -m agent.main --post sector --sector XLF

# Skip promotional follow-up post
python -m agent.main --post morning --no-promo

# Custom task
python -m agent.main --task "Post a bullish play for NVDA"
```

## Configuration

| Variable | Description | Required |
|----------|-------------|----------|
| `ALPHA_COPILOT_API_URL` | Backend API URL | Yes |
| `GEMINI_API_KEY` | Google Gemini API key | Yes |
| `TWITTER_API_KEY` | Twitter API key | For Twitter |
| `TWITTER_API_SECRET` | Twitter API secret | For Twitter |
| `TWITTER_ACCESS_TOKEN` | Twitter access token | For Twitter |
| `TWITTER_ACCESS_SECRET` | Twitter access secret | For Twitter |
| `THREADS_ACCESS_TOKEN` | Meta Threads access token | For Threads |
| `THREADS_USER_ID` | Meta Threads user ID | For Threads |
| `ALPHA_COPILOT_URL` | URL for promo posts | No (default: alphacopilot.ai) |
| `ENABLE_PROMO_POST` | Enable promo follow-ups | No (default: true) |
| `DRY_RUN` | Set to `true` to skip actual posting | No |

### Getting Threads Credentials

1. Go to [Meta Developer Portal](https://developers.facebook.com/)
2. Create a new app with Threads API access
3. Generate a long-lived access token
4. Get your Threads User ID from the API

## Deployment

### Railway (Recommended)

1. Create a new project on Railway
2. Connect your GitHub repo
3. Add environment variables (Twitter + Threads credentials)
4. Set up a cron job to trigger the agent:

```bash
# Morning alert at 9:35 AM ET (cross-posts to Twitter + Threads)
python -m agent.main --post morning
```

### GitHub Actions

Create `.github/workflows/post.yml`:

```yaml
name: Post to Social Media
on:
  schedule:
    - cron: '35 14 * * 1-5'  # 9:35 AM ET (14:35 UTC)
jobs:
  post:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python -m agent.main --post morning
        env:
          ALPHA_COPILOT_API_URL: ${{ secrets.ALPHA_COPILOT_API_URL }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          TWITTER_API_KEY: ${{ secrets.TWITTER_API_KEY }}
          TWITTER_API_SECRET: ${{ secrets.TWITTER_API_SECRET }}
          TWITTER_ACCESS_TOKEN: ${{ secrets.TWITTER_ACCESS_TOKEN }}
          TWITTER_ACCESS_SECRET: ${{ secrets.TWITTER_ACCESS_SECRET }}
          THREADS_ACCESS_TOKEN: ${{ secrets.THREADS_ACCESS_TOKEN }}
          THREADS_USER_ID: ${{ secrets.THREADS_USER_ID }}
          ENABLE_PROMO_POST: 'true'
```

## Adding New Platforms

To add a new platform (e.g., Discord):

1. Create `platforms/discord.py`:

```python
from .base import BasePlatform

class DiscordPlatform(BasePlatform):
    name = "discord"
    max_length = 2000

    def publish(self, content: str) -> dict:
        # Implementation using Discord webhook or bot
        pass

    def get_recent_posts(self, hours: int) -> list:
        # Implementation
        pass

    def health_check(self) -> bool:
        # Implementation
        pass
```

2. Register in `platforms/__init__.py`
3. Add to `tools/publish.py` PLATFORMS dict
4. Add credentials to `agent/config.py`

## How Cross-Posting Works

When you run the agent, the `cross_post` tool:

1. Posts the main content to **Twitter** (280 char limit)
2. Posts the same content to **Threads** (500 char limit)
3. Follows up with a **promotional post** for Alpha Copilot on each platform
4. Returns a summary of all posts made

The promotional messages are platform-optimized:
- **Twitter**: Concise with hashtags
- **Threads**: More detailed with bullet points and emojis

## License

MIT
