# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run agent (dry-run mode - no actual posting)
python -m agent.main --post morning --platform twitter --dry-run

# Run agent for real posting
python -m agent.main --post morning --platform twitter

# Custom task
python -m agent.main --task "Post a bullish play for NVDA to twitter"

# Run tests
pytest

# Run single test
pytest tests/test_file.py::test_name
```

## Architecture

This is a **ReAct (Reason + Act) pattern** agent that autonomously posts options trading insights to social media.

### Core Loop (`agent/loop.py`)

The agent runs in a while loop where the LLM:
1. Reasons about current state
2. Selects a tool to call (via JSON in text response)
3. Tool executes and returns result
4. Result added to context
5. Repeats until `done` tool called or max iterations (default: 10)

### Key Components

**Agent Layer** (`agent/`)
- `main.py` - CLI entry point, handles args and configuration
- `loop.py` - ReAct loop implementation, creates agent with registered tools
- `llm.py` - Gemini client with text-based tool calling (parses JSON from responses)
- `config.py` - Environment-based configuration via `Config` class

**Tools** (`tools/`)
- Extend `BaseTool` abstract class with `name`, `description`, `get_schema()`, `execute()`
- Registered via `ToolRegistry` in `agent/loop.py:create_agent()`
- Available tools: `query_alpha_copilot`, `compose_post`, `publish`, `check_recent_posts`, `get_platform_status`, `done`

**Platforms** (`platforms/`)
- Extend `BasePlatform` with `name`, `max_length`, `publish()`, `get_recent_posts()`, `health_check()`
- Currently only Twitter implemented

**Prompts** (`prompts/system.py`)
- `SYSTEM_PROMPT` - Agent instructions and guidelines
- `TASK_TEMPLATES` - Templates for different post types (morning, eod, volatility, sector)

### Data Flow

1. CLI parses args, generates task from template or custom input
2. Agent queries Alpha Copilot backend API for options analysis
3. LLM composes post content based on recommendations
4. Post published to target platform (or logged in dry-run mode)

## Configuration

Set via environment variables (`.env` file):
- `GEMINI_API_KEY` - Required for LLM
- `ALPHA_COPILOT_API_URL` - Backend API (default: localhost:8002)
- `TWITTER_*` - Twitter API credentials (required for real posting)
- `DRY_RUN` - Set to `true` to skip actual posting (default: true)

## Adding New Platforms

1. Create `platforms/<name>.py` extending `BasePlatform`
2. Implement `publish()`, `get_recent_posts()`, `health_check()`
3. Register in `platforms/__init__.py`
4. Add to `PLATFORMS` dict in `tools/publish.py`
