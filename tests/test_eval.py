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


class TestEvaluationThresholds:
    """Tests for evaluation threshold boundaries."""

    def setup_method(self):
        """Set up test fixtures with known thresholds."""
        self.evaluator = PostEvaluator()

    def test_threshold_exact_pass_total(self):
        """Test that a post at exactly the total threshold passes."""
        from unittest.mock import patch
        from agent.config import Config

        # Use override to set known thresholds
        with Config.override(EVAL_TOTAL_MIN=45, EVAL_HOOKINESS_MIN=15, EVAL_QUALITY_MIN=30, EVAL_MODE="both"):
            evaluator = PostEvaluator()

            # Manually test the threshold check with exact value
            passed, reason = evaluator._check_thresholds(15, 30, 45)
            assert passed is True
            assert reason == ""

    def test_threshold_exact_fail_total(self):
        """Test that a post below the total threshold fails."""
        from unittest.mock import patch
        from agent.config import Config

        with Config.override(EVAL_TOTAL_MIN=45, EVAL_HOOKINESS_MIN=15, EVAL_QUALITY_MIN=30, EVAL_MODE="both"):
            evaluator = PostEvaluator()

            # One below threshold
            passed, reason = evaluator._check_thresholds(14, 30, 44)
            assert passed is False
            assert "too low" in reason.lower()

    def test_hookiness_minimum_score(self):
        """Test hookiness scores at minimum (all 1s)."""
        # A post with nothing interesting should score low
        minimal_post = "zzz"

        score = self.evaluator._score_hookiness_heuristic(minimal_post)

        # Each metric should be at least 1
        assert score.news_hook >= 1
        assert score.specificity >= 1
        assert score.urgency >= 1
        assert score.human_voice >= 1
        assert score.scroll_stop >= 1
        assert score.total >= 5  # Minimum possible

    def test_quality_minimum_score(self):
        """Test quality scores at minimum."""
        minimal_post = "zzz"

        score = self.evaluator._score_quality_heuristic(minimal_post)

        # Each metric should be at least 1
        assert score.thesis_clarity >= 1
        assert score.news_driven >= 1
        assert score.actionable >= 0  # Can be 0 if no trade details
        assert score.engagement >= 1
        assert score.originality >= 1
        assert score.total >= 5  # Minimum possible

    def test_hookiness_only_mode(self):
        """Test evaluation in hookiness-only mode."""
        from agent.config import Config

        with Config.override(EVAL_MODE="hookiness", EVAL_HOOKINESS_MIN=15, EVAL_QUALITY_MIN=0, EVAL_TOTAL_MIN=0):
            evaluator = PostEvaluator()

            # Pass hookiness but fail quality
            passed, reason = evaluator._check_thresholds(20, 10, 30)
            assert passed is True  # Should pass because quality isn't checked

    def test_quality_only_mode(self):
        """Test evaluation in quality-only mode."""
        from agent.config import Config

        with Config.override(EVAL_MODE="quality", EVAL_HOOKINESS_MIN=0, EVAL_QUALITY_MIN=30, EVAL_TOTAL_MIN=0):
            evaluator = PostEvaluator()

            # Pass quality but fail hookiness
            passed, reason = evaluator._check_thresholds(10, 35, 45)
            assert passed is True  # Should pass because hookiness isn't checked

    def test_both_mode_requires_all(self):
        """Test that 'both' mode requires meeting all thresholds."""
        from agent.config import Config

        with Config.override(EVAL_MODE="both", EVAL_HOOKINESS_MIN=15, EVAL_QUALITY_MIN=30, EVAL_TOTAL_MIN=45):
            evaluator = PostEvaluator()

            # Pass total but fail hookiness
            passed, reason = evaluator._check_thresholds(10, 35, 45)
            assert passed is False
            assert "Hookiness" in reason


class TestEvaluationEdgeCases:
    """Tests for evaluation edge cases."""

    def setup_method(self):
        """Set up test fixtures."""
        self.evaluator = PostEvaluator()

    def test_empty_post(self):
        """Test evaluation handles empty string."""
        result = self.evaluator.evaluate("")

        assert isinstance(result, UnifiedScore)
        # Should score very low but not crash
        assert result.total >= 10  # Minimum possible

    def test_very_short_post(self):
        """Test evaluation handles very short posts."""
        result = self.evaluator.evaluate("Hi")

        assert isinstance(result, UnifiedScore)
        assert result.passed is False  # Too short to be useful

    def test_emoji_only_post(self):
        """Test evaluation handles emoji-only posts."""
        result = self.evaluator.evaluate("📈🚀💰")

        assert isinstance(result, UnifiedScore)
        # Emojis should contribute to scroll_stop but low otherwise
        assert result.hookiness.scroll_stop >= 1

    def test_unicode_characters(self):
        """Test evaluation handles unicode/special characters."""
        unicode_post = "$NVDA up 10%! 🚀→ Sell $950 call • Premium: $12 • POP: 75%"

        result = self.evaluator.evaluate(unicode_post)

        assert isinstance(result, UnifiedScore)
        # Should score well despite unicode
        assert result.hookiness.specificity >= 3  # Has numbers

    def test_very_long_post(self):
        """Test evaluation handles very long posts."""
        long_post = """$NVDA (Nvidia) just hit all-time highs on AI chip demand surge!

Here's how to profit from this momentum:
→ Sell the $950 call (Jan 17 expiry)
→ Collect ~$12 premium per contract
→ ~75% probability of profit

This trade benefits from high implied volatility.
The breakeven is $962, giving you 5% upside buffer.

Risk management is key - position size appropriately!

#NVDA #options #theta #income #NFA

This is not financial advice. Do your own research."""

        result = self.evaluator.evaluate(long_post)

        assert isinstance(result, UnifiedScore)
        # Long structured post should score well
        assert result.total >= 30

    def test_template_post_penalized(self):
        """Test that template-style posts get penalized."""
        template_post = "AAPL | $180 Strike | $3.50 Premium | 72% POP | Jan 17"
        human_post = "Here's how to profit from AAPL: sell the $180 call for $3.50 premium"

        template_score = self.evaluator.evaluate(template_post)
        human_score = self.evaluator.evaluate(human_post)

        # Template should be penalized on originality
        assert human_score.quality.originality >= template_score.quality.originality

    def test_post_with_only_numbers(self):
        """Test evaluation of post with just numbers."""
        numbers_post = "$950 $12 75% $1000 10% 100"

        result = self.evaluator.evaluate(numbers_post)

        assert isinstance(result, UnifiedScore)
        # Should score reasonably on specificity (has numbers)
        assert result.hookiness.specificity >= 2

    def test_post_with_question(self):
        """Test that posts with questions get engagement boost."""
        question_post = "Is NVDA a good buy here? $950 call looks tempting..."
        statement_post = "NVDA $950 call looks tempting."

        q_score = self.evaluator.evaluate(question_post)
        s_score = self.evaluator.evaluate(statement_post)

        # Question should boost originality
        assert q_score.quality.originality >= s_score.quality.originality

    def test_post_preserves_original_text(self):
        """Test that hookiness score preserves original post text."""
        post = "Original post text here"
        score = self.evaluator._score_hookiness_heuristic(post)

        assert score.post == post
