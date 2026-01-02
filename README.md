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
│  query_alpha_copilot | compose_post | publish   │
│  check_recent_posts | get_platform_status | done │
└─────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│             PLATFORM ADAPTERS                    │
│        Twitter | Threads | Discord              │
└─────────────────────────────────────────────────┘
```

## Key Features

- **Uses Alpha Copilot Backend**: Same API as the web app for consistent analysis
- **Platform Agnostic**: Easy to add new platforms (Threads, Discord, LinkedIn)
- **Autonomous**: LLM decides what to query, how to compose, when to post
- **Duplicate Prevention**: Checks recent posts before creating new content

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys

# Run with dry-run mode
python -m agent.main --post morning --platform twitter --dry-run

# Run for real
python -m agent.main --post morning --platform twitter
```

## Usage

```bash
# Morning options alert (covered calls, CSPs)
python -m agent.main --post morning --platform twitter

# End-of-day directional play
python -m agent.main --post eod --platform twitter

# High IV opportunity
python -m agent.main --post volatility --platform twitter

# Sector focus
python -m agent.main --post sector --sector XLF --platform twitter

# Custom task
python -m agent.main --task "Post a bullish play for NVDA to twitter"
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
| `DRY_RUN` | Set to `true` to skip actual posting | No |

## Deployment

### Railway (Recommended)

1. Create a new project on Railway
2. Connect your GitHub repo
3. Add environment variables
4. Set up a cron job to trigger the agent:

```bash
# Morning alert at 9:35 AM ET
python -m agent.main --post morning --platform twitter
```

### GitHub Actions

Create `.github/workflows/post.yml`:

```yaml
name: Post to Twitter
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
      - run: python -m agent.main --post morning --platform twitter
        env:
          ALPHA_COPILOT_API_URL: ${{ secrets.ALPHA_COPILOT_API_URL }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          TWITTER_API_KEY: ${{ secrets.TWITTER_API_KEY }}
          TWITTER_API_SECRET: ${{ secrets.TWITTER_API_SECRET }}
          TWITTER_ACCESS_TOKEN: ${{ secrets.TWITTER_ACCESS_TOKEN }}
          TWITTER_ACCESS_SECRET: ${{ secrets.TWITTER_ACCESS_SECRET }}
```

## Adding New Platforms

1. Create `platforms/threads.py`:

```python
from .base import BasePlatform

class ThreadsPlatform(BasePlatform):
    name = "threads"
    max_length = 500

    def publish(self, content: str) -> dict:
        # Implementation
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

## License

MIT
