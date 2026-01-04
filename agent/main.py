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
  python -m agent.main --post morning              # Cross-post to Twitter + Threads
  python -m agent.main --post eod                  # Cross-post to Twitter + Threads
  python -m agent.main --post morning --no-promo   # Skip promotional follow-up
  python -m agent.main --post sector --sector XLF  # Sector-focused cross-post
  python -m agent.main --post morning --dry-run    # Test without posting
  python -m agent.main --task "Post a bullish play for NVDA"
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
    parser.add_argument(
        '--no-promo',
        action='store_true',
        help='Skip promotional follow-up post'
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

    # Apply promo override
    if args.no_promo:
        Config.ENABLE_PROMO_POST = False

    # Print configuration
    print("=" * 50)
    print("Alpha Copilot Social Agent")
    print("=" * 50)
    print(f"Platform: {args.platform} (cross-post to Twitter + Threads by default)")
    print(f"DRY_RUN: {Config.DRY_RUN}")
    print(f"Promo posts: {Config.ENABLE_PROMO_POST}")
    print(f"Backend: {Config.ALPHA_COPILOT_API_URL}")
    print(f"LLM Model: {Config.LLM_MODEL}")
    print(f"Twitter configured: {Config.validate_twitter()}")
    print(f"Threads configured: {Config.validate_threads()}")
    print("=" * 50)

    # Validate configuration
    if not Config.validate_llm():
        print("ERROR: GEMINI_API_KEY not configured")
        sys.exit(1)

    if not Config.DRY_RUN:
        if not Config.validate_twitter():
            print("WARNING: Twitter credentials not configured. Twitter posts will be skipped.")
        if not Config.validate_threads():
            print("WARNING: Threads credentials not configured. Threads posts will be skipped.")

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
