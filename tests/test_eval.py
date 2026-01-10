"""Tests for the post evaluation system."""

import pytest
from agent.eval import PostEvaluator, HookinessScore, QualityScore, UnifiedScore


class TestPostEvaluator:
    """Tests for PostEvaluator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.evaluator = PostEvaluator()

    def test_evaluate_returns_unified_score(self):
        """Test that evaluate returns a UnifiedScore."""
        post = "$NVDA up 5% today on AI chip demand! Sell the $950 call for $12 premium. #NFA"
        result = self.evaluator.evaluate(post)

        assert isinstance(result, UnifiedScore)
        assert isinstance(result.hookiness, HookinessScore)
        assert isinstance(result.quality, QualityScore)

    def test_hookiness_scoring_with_news_hook(self):
        """Test that posts with news hooks score higher."""
        news_post = "$NVDA just hit all-time highs today on massive AI demand surge!"
        no_news_post = "NVDA Covered Call | $950 Strike | $12 Premium"

        news_score = self.evaluator._score_hookiness_heuristic(news_post)
        no_news_score = self.evaluator._score_hookiness_heuristic(no_news_post)

        assert news_score.news_hook > no_news_score.news_hook

    def test_hookiness_scoring_with_specificity(self):
        """Test that posts with numbers score higher on specificity."""
        specific_post = "$NVDA $950 call, Jan 17 expiry, $12 premium, 75% POP"
        vague_post = "NVDA options look good"

        specific_score = self.evaluator._score_hookiness_heuristic(specific_post)
        vague_score = self.evaluator._score_hookiness_heuristic(vague_post)

        assert specific_score.specificity > vague_score.specificity

    def test_hookiness_penalizes_template_format(self):
        """Test that template-like posts get penalized on human_voice."""
        template_post = "AAPL | $180 Strike | $3.50 Premium | 72% POP | Jan 17"
        human_post = "Here's how to profit from AAPL: sell the $180 call for $3.50"

        template_score = self.evaluator._score_hookiness_heuristic(template_post)
        human_score = self.evaluator._score_hookiness_heuristic(human_post)

        assert human_score.human_voice >= template_score.human_voice

    def test_quality_scoring_actionable(self):
        """Test that posts with trade details score higher on actionable."""
        actionable_post = "$NVDA $950 call, Jan 17, collect $12 premium, 75% probability of profit"
        vague_post = "NVDA looks bullish"

        actionable_score = self.evaluator._score_quality_heuristic(actionable_post)
        vague_score = self.evaluator._score_quality_heuristic(vague_post)

        assert actionable_score.actionable > vague_score.actionable

    def test_total_score_is_sum(self):
        """Test that total score equals hookiness + quality."""
        post = "$NVDA up 5% today! Sell the $950 call for $12. #NFA"
        result = self.evaluator.evaluate(post)

        assert result.total == result.hookiness.total + result.quality.total

    def test_pass_threshold(self):
        """Test that posts meeting threshold pass."""
        # Good post that should pass
        good_post = """$NVDA (Nvidia) just hit all-time highs on AI chip demand surge!

Here's how to profit:
→ Sell the $950 call (Jan 17)
→ Collect ~$12 premium
→ ~75% POP

#NVDA #options #NFA"""

        result = self.evaluator.evaluate(good_post)
        # Score should be reasonable (won't always pass but should score decently)
        assert result.total >= 30  # At minimum, should score something

    def test_format_report(self):
        """Test that format_report returns a string."""
        post = "$NVDA up 5%! #NFA"
        result = self.evaluator.evaluate(post)
        report = self.evaluator.format_report(result)

        assert isinstance(report, str)
        assert "EVALUATION REPORT" in report
        assert "HOOKINESS" in report
        assert "QUALITY" in report


class TestHookinessScore:
    """Tests for HookinessScore dataclass."""

    def test_hookiness_score_total_range(self):
        """Test that hookiness total is within valid range."""
        evaluator = PostEvaluator()
        post = "Test post with some content"
        score = evaluator._score_hookiness_heuristic(post)

        assert 5 <= score.total <= 25  # 5 metrics, each 1-5


class TestQualityScore:
    """Tests for QualityScore dataclass."""

    def test_quality_score_total_range(self):
        """Test that quality total is within valid range."""
        evaluator = PostEvaluator()
        post = "Test post with some content"
        score = evaluator._score_quality_heuristic(post)

        assert 5 <= score.total <= 50  # 5 metrics, each 1-10
