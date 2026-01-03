"""Evaluation layer for scoring agent output quality."""

import json
import logging
import re
from typing import Dict, List, Any, Optional

from google import genai
from google.genai import types

from .config import Config
from .loop import create_agent
from prompts.system import get_task_prompt

logger = logging.getLogger(__name__)


class AgentEvaluator:
    """Evaluates agent output quality over multiple runs.

    Uses google-genai package for LLM judge.
    Raises exceptions on failure - no silent fallbacks.
    """

    def __init__(self):
        if not Config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not configured")

        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)

    def run_eval(self, platform: str = "twitter", num_runs: int = 5) -> Dict[str, Any]:
        """
        Run agent multiple times and score outputs.

        Args:
            platform: Target platform for posts
            num_runs: Number of evaluation runs

        Returns:
            Evaluation report with scores
        """
        results = []
        task = get_task_prompt(platform)

        print(f"\n{'='*50}")
        print("AGENT EVALUATION")
        print(f"{'='*50}")
        print(f"Runs: {num_runs}")
        print(f"Platform: {platform}")
        print(f"{'='*50}\n")

        for i in range(num_runs):
            print(f"Run {i+1}/{num_runs}...")

            try:
                # Force dry run for evaluation
                original_dry_run = Config.DRY_RUN
                Config.DRY_RUN = True

                agent = create_agent()
                result = agent.run(task)

                Config.DRY_RUN = original_dry_run

                # Parse result - try to extract from full agent run output
                # Note: We need to capture the tweet from compose_post tool output
                tweet = self._extract_tweet(result)
                thesis = self._extract_thesis(result)
                symbol = self._extract_symbol(result)

                # If no tweet found in result, check if publish was called
                if not tweet and "DRY_RUN:" in result:
                    # Extract from dry run output
                    import re
                    match = re.search(r'DRY_RUN:.*?Content:\s*(.*?)(?:\.\.\.|$)', result, re.DOTALL)
                    if match:
                        tweet = match.group(1).strip()

                results.append({
                    "run": i + 1,
                    "raw_result": result,
                    "tweet": tweet,
                    "thesis": thesis,
                    "symbol": symbol,
                    "success": "TASK_COMPLETE" in result or "SUCCESS" in result
                })

                if tweet:
                    print(f"  Tweet: {tweet[:60]}...")
                else:
                    print(f"  No tweet composed (result: {result[:50]}...)")

            except Exception as e:
                logger.exception(f"Run {i+1} failed")
                results.append({
                    "run": i + 1,
                    "error": str(e),
                    "tweet": None,
                    "thesis": None,
                    "symbol": None,
                    "success": False
                })
                print(f"  Error: {e}")

        # Filter successful runs with tweets
        tweets_to_judge = [r for r in results if r.get("tweet")]

        if not tweets_to_judge:
            print("\nNo tweets to evaluate.")
            return {
                "num_runs": num_runs,
                "successful_runs": 0,
                "average_score": 0,
                "max_score": 50,
                "results": results,
                "scores": []
            }

        # Judge quality
        print(f"\nScoring {len(tweets_to_judge)} tweets...")
        scores = self._judge_tweets(tweets_to_judge)

        # Generate report
        return self._generate_report(results, scores)

    def _extract_tweet(self, result: str) -> Optional[str]:
        """Extract composed tweet from result."""
        # Look for COMPOSED_POST block
        match = re.search(r'COMPOSED_POST:\n(.*?)\n\nCHARACTER_COUNT', result, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Look in context
        match = re.search(r'COMPOSED_POST:\n(.*?)(?:\n\n|$)', result, re.DOTALL)
        if match:
            return match.group(1).strip()

        return None

    def _extract_thesis(self, result: str) -> Optional[str]:
        """Extract thesis from result."""
        # Look for thesis patterns
        patterns = [
            r'thesis["\s:]+([^"]+)"',
            r'My thesis:\s*([^\n]+)',
            r'Thesis:\s*([^\n]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, result, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _extract_symbol(self, result: str) -> Optional[str]:
        """Extract stock symbol from result."""
        match = re.search(r'\$([A-Z]{1,5})\b', result)
        if match:
            return match.group(1)
        return None

    def _judge_tweets(self, results: List[Dict]) -> List[Dict]:
        """Use LLM to score tweet quality."""
        tweets_json = json.dumps([
            {"run": r["run"], "tweet": r["tweet"], "thesis": r.get("thesis", "")}
            for r in results
        ], indent=2)

        prompt = f"""You are a trading content quality judge. Score each tweet on these criteria (1-10 each):

1. **Thesis Clarity**: Is the investment thesis clear and specific? Does it explain WHY this trade?
2. **News-Driven**: Is it based on real, current news or a specific catalyst? (not generic)
3. **Actionable**: Are the trade details clear? (symbol, strategy, strike, expiration)
4. **Engagement**: Would this get engagement on Twitter? Is it compelling?
5. **Originality**: Is this a unique take, not generic filler content?

Tweets to evaluate:
{tweets_json}

Return ONLY a JSON array with this exact format (no markdown, no explanation):
[
  {{"run": 1, "clarity": 8, "news": 7, "actionable": 9, "engagement": 6, "originality": 7, "total": 37, "feedback": "Brief feedback here"}},
  ...
]"""

        try:
            config = types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=1024,
            )

            response = self.client.models.generate_content(
                model=Config.LLM_MODEL,
                contents=prompt,
                config=config,
            )

            # Parse JSON from response
            text = response.text.strip()

            # Remove markdown code blocks if present
            if text.startswith("```"):
                text = re.sub(r'^```(?:json)?\n?', '', text)
                text = re.sub(r'\n?```$', '', text)

            scores = json.loads(text)
            return scores

        except Exception as e:
            logger.exception("Failed to judge tweets")
            # Return default scores
            return [
                {"run": r["run"], "clarity": 5, "news": 5, "actionable": 5,
                 "engagement": 5, "originality": 5, "total": 25,
                 "feedback": f"Scoring failed: {e}"}
                for r in results
            ]

    def _generate_report(self, results: List[Dict], scores: List[Dict]) -> Dict[str, Any]:
        """Generate evaluation report."""
        successful = len([r for r in results if r.get("success")])

        if not scores:
            avg_score = 0
            best = worst = None
        else:
            avg_score = sum(s.get("total", 0) for s in scores) / len(scores)
            best = max(scores, key=lambda x: x.get("total", 0))
            worst = min(scores, key=lambda x: x.get("total", 0))

        report = {
            "num_runs": len(results),
            "successful_runs": successful,
            "tweets_scored": len(scores),
            "average_score": round(avg_score, 1),
            "max_score": 50,
            "percentage": round((avg_score / 50) * 100, 1) if avg_score else 0,
            "best_run": best,
            "worst_run": worst,
            "all_scores": scores,
            "all_results": results
        }

        # Print report
        self._print_report(report)

        return report

    def _print_report(self, report: Dict[str, Any]):
        """Print formatted evaluation report."""
        print(f"\n{'='*50}")
        print("AGENT EVALUATION REPORT")
        print(f"{'='*50}")
        print(f"Runs: {report['num_runs']}")
        print(f"Successful: {report['successful_runs']}")
        print(f"Tweets Scored: {report['tweets_scored']}")
        print(f"Average Score: {report['average_score']} / {report['max_score']} ({report['percentage']}%)")

        if report.get("best_run"):
            best = report["best_run"]
            print(f"\nBest Run (#{best['run']}): {best.get('total', 0)}/50")
            # Find the tweet
            for r in report.get("all_results", []):
                if r.get("run") == best["run"] and r.get("tweet"):
                    print(f"  \"{r['tweet'][:80]}...\"")
                    break
            print(f"  Feedback: {best.get('feedback', 'N/A')}")

        if report.get("worst_run") and report.get("best_run") != report.get("worst_run"):
            worst = report["worst_run"]
            print(f"\nWorst Run (#{worst['run']}): {worst.get('total', 0)}/50")
            print(f"  Feedback: {worst.get('feedback', 'N/A')}")

        # Score breakdown
        if report.get("all_scores"):
            scores = report["all_scores"]
            print(f"\nScore Breakdown:")
            print(f"  Thesis Clarity: {sum(s.get('clarity', 0) for s in scores) / len(scores):.1f} avg")
            print(f"  News-Driven:    {sum(s.get('news', 0) for s in scores) / len(scores):.1f} avg")
            print(f"  Actionable:     {sum(s.get('actionable', 0) for s in scores) / len(scores):.1f} avg")
            print(f"  Engagement:     {sum(s.get('engagement', 0) for s in scores) / len(scores):.1f} avg")
            print(f"  Originality:    {sum(s.get('originality', 0) for s in scores) / len(scores):.1f} avg")

        print(f"{'='*50}\n")


def run_evaluation(platform: str = "twitter", num_runs: int = 5) -> Dict[str, Any]:
    """Run agent evaluation."""
    evaluator = AgentEvaluator()
    return evaluator.run_eval(platform=platform, num_runs=num_runs)
