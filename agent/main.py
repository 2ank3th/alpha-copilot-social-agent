#!/usr/bin/env python3
"""CLI entry point for the Alpha Copilot Social Agent."""

import argparse
import json
import logging
import sys
from datetime import datetime
from typing import List, Dict, Any

from .config import Config
from .loop import create_agent
from .eval import PostEvaluator
from prompts.system import get_task_prompt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def run_eval_mode(args) -> None:
    """Run evaluation mode - generate N posts and score them."""
    print("=" * 70)
    print(f"EVALUATION MODE - Running {args.runs} iterations")
    print("=" * 70)

    # Force dry run
    original_dry_run = Config.DRY_RUN
    Config.DRY_RUN = True

    # Generate task
    if args.task:
        task = args.task
    else:
        task = get_task_prompt(args.post or 'morning', args.platform)

    print(f"Task: {task}\n")

    evaluator = PostEvaluator()
    results: List[Dict[str, Any]] = []

    # Run agent N times
    for run_num in range(1, args.runs + 1):
        print(f"\n{'='*70}")
        print(f"RUN {run_num}/{args.runs}")
        print('='*70)

        try:
            agent = create_agent()
            result = agent.run(task)

            # Get post text from agent's pending_post (stored during write_post evaluation)
            post_text = agent._pending_post

            # Evaluate the post
            if post_text:
                eval_result = evaluator.evaluate(post_text)

                results.append({
                    'run': run_num,
                    'success': True,
                    'post_text': post_text,
                    'hookiness': eval_result.hookiness.total,
                    'quality': eval_result.quality.total,
                    'total': eval_result.total,
                    'passed': eval_result.passed,
                    'failure_reason': eval_result.failure_reason
                })

                print(f"\n✓ Post generated and evaluated")
                print(f"  Score: {eval_result.total}/75 ({'PASS' if eval_result.passed else 'FAIL'})")
                print(f"  Hookiness: {eval_result.hookiness.total}/25")
                print(f"  Quality: {eval_result.quality.total}/50")
            else:
                results.append({
                    'run': run_num,
                    'success': False,
                    'error': 'Could not extract post text from result'
                })
                print(f"\n✗ Failed to extract post text")

        except Exception as e:
            results.append({
                'run': run_num,
                'success': False,
                'error': str(e)
            })
            print(f"\n✗ Run failed: {e}")

    # Generate summary report
    print("\n\n")
    print("=" * 70)
    print("EVALUATION REPORT")
    print("=" * 70)

    successful_runs = [r for r in results if r.get('success', False)]
    passed_runs = [r for r in successful_runs if r.get('passed', False)]

    print(f"\nSuccessful Runs: {len(successful_runs)}/{args.runs}")

    avg_total = 0
    avg_hookiness = 0
    avg_quality = 0

    if successful_runs:
        print(f"Pass Rate: {len(passed_runs)/len(successful_runs)*100:.1f}% ({len(passed_runs)}/{len(successful_runs)} passed)")

        avg_total = sum(r['total'] for r in successful_runs) / len(successful_runs)
        avg_hookiness = sum(r['hookiness'] for r in successful_runs) / len(successful_runs)
        avg_quality = sum(r['quality'] for r in successful_runs) / len(successful_runs)

        print(f"\nAVERAGE SCORES:")
        print(f"  Total: {avg_total:.1f}/75")
        print(f"  Hookiness: {avg_hookiness:.1f}/25")
        print(f"  Quality: {avg_quality:.1f}/50")

        # Best post
        best = max(successful_runs, key=lambda r: r['total'])
        print(f"\n{'='*70}")
        print(f"BEST POST (Run {best['run']}, Score: {best['total']}/75)")
        print(f"{'='*70}")
        print(best['post_text'])

        # Worst post
        worst = min(successful_runs, key=lambda r: r['total'])
        print(f"\n{'='*70}")
        print(f"WORST POST (Run {worst['run']}, Score: {worst['total']}/75)")
        print(f"{'='*70}")
        print(worst['post_text'])

        # Failed posts
        failed_runs = [r for r in successful_runs if not r.get('passed', False)]
        if failed_runs:
            print(f"\n{'='*70}")
            print(f"FAILED POSTS ({len(failed_runs)} total)")
            print(f"{'='*70}")
            for r in failed_runs:
                print(f"\nRun {r['run']} - Score: {r['total']}/75")
                print(f"Reason: {r['failure_reason']}")

    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"eval_results_{timestamp}.json"
    with open(filename, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'task': task,
            'runs': args.runs,
            'results': results,
            'summary': {
                'successful_runs': len(successful_runs),
                'passed_runs': len(passed_runs),
                'pass_rate': len(passed_runs)/len(successful_runs) if successful_runs else 0,
                'avg_total': avg_total if successful_runs else 0,
                'avg_hookiness': avg_hookiness if successful_runs else 0,
                'avg_quality': avg_quality if successful_runs else 0
            }
        }, f, indent=2)

    print(f"\n{'='*70}")
    print(f"Detailed results saved to: {filename}")
    print('='*70)

    # Restore original dry run setting
    Config.DRY_RUN = original_dry_run


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
  python -m agent.main --eval --runs 5             # Evaluation mode
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
    parser.add_argument(
        '--eval',
        action='store_true',
        help='Run in evaluation mode - generate N posts and score them'
    )
    parser.add_argument(
        '--runs',
        type=int,
        default=5,
        help='Number of posts to generate in eval mode (default: 5)'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.eval and not args.post and not args.task:
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
    if Config.validate_supabase():
        print(f"Backend Auth: Supabase ({Config.SUPABASE_EMAIL})")
    elif Config.ALPHA_COPILOT_API_KEY:
        print(f"Backend Auth: Static API Key")
    else:
        print(f"Backend Auth: NOT CONFIGURED")
    print(f"LLM Model: {Config.LLM_MODEL}")
    print(f"Twitter configured: {Config.validate_twitter()}")
    print(f"Threads configured: {Config.validate_threads()}")
    print("=" * 50)

    # Validate configuration
    if not Config.validate_alpha_copilot():
        print("ERROR: ALPHA_COPILOT_API_KEY not configured")
        sys.exit(1)

    if not Config.validate_llm():
        print("ERROR: GEMINI_API_KEY not configured")
        sys.exit(1)

    if not Config.DRY_RUN:
        if not Config.validate_twitter():
            print("WARNING: Twitter credentials not configured. Twitter posts will be skipped.")
        if not Config.validate_threads():
            print("WARNING: Threads credentials not configured. Threads posts will be skipped.")

    # Run evaluation mode if requested
    if args.eval:
        run_eval_mode(args)
        return

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
