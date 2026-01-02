#!/usr/bin/env python3
"""CLI entry point for the Alpha Copilot Social Agent."""

import argparse
import logging
import sys

from .config import Config
from .loop import create_agent
from prompts.system import get_task_prompt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Alpha Copilot Social Agent - Post options insights to social media',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m agent.main --post morning --platform twitter
  python -m agent.main --post eod --platform twitter
  python -m agent.main --post volatility --platform twitter
  python -m agent.main --post sector --sector XLF --platform twitter
  python -m agent.main --task "Post a covered call opportunity for AAPL to twitter"
        """
    )

    parser.add_argument(
        '--post',
        choices=['morning', 'eod', 'volatility', 'sector'],
        help='Type of post to create'
    )
    parser.add_argument(
        '--platform',
        choices=['twitter', 'threads', 'discord'],
        default='twitter',
        help='Platform to post to (default: twitter)'
    )
    parser.add_argument(
        '--sector',
        type=str,
        help='Sector ETF for sector posts (e.g., XLF, XLK, XLE)'
    )
    parser.add_argument(
        '--task',
        type=str,
        help='Custom task description (overrides --post)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without actually posting (overrides DRY_RUN env var)'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.post and not args.task:
        parser.print_help()
        sys.exit(1)

    if args.post == 'sector' and not args.sector:
        print("ERROR: --sector is required for sector posts")
        sys.exit(1)

    # Apply dry run override
    if args.dry_run:
        Config.DRY_RUN = True

    # Print configuration
    print("=" * 50)
    print("Alpha Copilot Social Agent")
    print("=" * 50)
    print(f"Platform: {args.platform}")
    print(f"DRY_RUN: {Config.DRY_RUN}")
    print(f"Backend: {Config.ALPHA_COPILOT_API_URL}")
    print(f"LLM Model: {Config.LLM_MODEL}")
    print("=" * 50)

    # Validate configuration
    if not Config.validate_llm():
        print("ERROR: GEMINI_API_KEY not configured")
        sys.exit(1)

    if not Config.DRY_RUN and not Config.validate_twitter() and args.platform == 'twitter':
        print("ERROR: Twitter credentials not configured. Use --dry-run or set credentials.")
        sys.exit(1)

    # Generate task
    if args.task:
        task = args.task
    else:
        task = get_task_prompt(args.post, args.platform, args.sector)

    print(f"Task: {task}")
    print("=" * 50)

    # Create and run agent
    try:
        agent = create_agent()
        result = agent.run(task)

        print("=" * 50)
        print("Result:")
        print(result)
        print("=" * 50)

        # Exit with appropriate code
        if "TASK_COMPLETE" in result or "SUCCESS" in result:
            sys.exit(0)
        else:
            sys.exit(1)

    except Exception as e:
        logger.exception("Agent failed")
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
