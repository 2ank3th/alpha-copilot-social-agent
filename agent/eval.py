"""Unified evaluation system for post quality."""

import re
import logging
from dataclasses import dataclass
from typing import Tuple

from agent.config import Config

logger = logging.getLogger(__name__)


@dataclass
class HookinessScore:
    """Hookiness scores for engagement potential."""
    post: str
    news_hook: int  # 1-5: Does it lead with news/timely info?
    specificity: int  # 1-5: Does it have specific numbers (%, $, dates)?
    urgency: int  # 1-5: Does it create FOMO/urgency?
    human_voice: int  # 1-5: Does it sound human vs robotic?
    scroll_stop: int  # 1-5: Would this stop someone scrolling?
    total: int  # Sum of all scores (max 25)
    reasoning: str  # Why the scores were given


@dataclass
class QualityScore:
    """Content quality scores (thesis-driven analysis)."""
    thesis_clarity: int  # 1-10: Clear investment thesis?
    news_driven: int  # 1-10: Tied to news/events?
    actionable: int  # 1-10: Specific trade details?
    engagement: int  # 1-10: Compelling/interesting?
    originality: int  # 1-10: Fresh angle vs generic?
    total: int  # Sum (max 50)
    reasoning: str


@dataclass
class UnifiedScore:
    """Combined hookiness + quality evaluation."""
    hookiness: HookinessScore
    quality: QualityScore
    total: int  # hookiness.total + quality.total (max 75)
    passed: bool
    failure_reason: str = ""


class PostEvaluator:
    """Evaluates post quality using hookiness + content quality metrics."""

    def __init__(self):
        self.hookiness_min = Config.EVAL_HOOKINESS_MIN
        self.quality_min = Config.EVAL_QUALITY_MIN
        self.total_min = Config.EVAL_TOTAL_MIN
        self.eval_mode = Config.EVAL_MODE

    def evaluate(self, post_text: str) -> UnifiedScore:
        """
        Evaluate a post using both hookiness and quality metrics.

        Args:
            post_text: The complete post text

        Returns:
            UnifiedScore with pass/fail and detailed breakdown
        """
        # 1. Score hookiness (engagement metrics)
        hookiness = self._score_hookiness_heuristic(post_text)

        # 2. Score quality (content metrics)
        quality = self._score_quality_heuristic(post_text)

        # 3. Determine pass/fail
        total = hookiness.total + quality.total
        passed, reason = self._check_thresholds(hookiness.total, quality.total, total)

        return UnifiedScore(
            hookiness=hookiness,
            quality=quality,
            total=total,
            passed=passed,
            failure_reason=reason
        )

    def _score_hookiness_heuristic(self, post: str) -> HookinessScore:
        """Score post hookiness using heuristic rules (from hookiness_eval.py)."""

        # NEWS_HOOK: Check for news indicators
        news_patterns = [
            r'\bjust\b', r'\bbreaking\b', r'\btoday\b', r'\bthis morning\b',
            r'\bhit\b.*\bhigh', r'\bup\b.*%', r'\bdown\b.*%', r'\brally\b',
            r'\breports?\b', r'\bearnings\b', r'\bafter\b.*\bmiss\b',
            r'\bdemand\b', r'\bsurge\b', r'\bbroke\b.*resistance'
        ]
        news_hook = 1
        news_matches = sum(1 for p in news_patterns if re.search(p, post, re.IGNORECASE))
        if news_matches >= 3:
            news_hook = 5
        elif news_matches >= 2:
            news_hook = 4
        elif news_matches >= 1:
            news_hook = 3

        # SPECIFICITY: Check for specific numbers
        number_patterns = [
            r'\$\d+', r'\d+%', r'\d+\.\d+', r'Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec',
            r'\d+/\d+', r'\d+ (days?|weeks?)'
        ]
        specificity = 1
        num_matches = sum(1 for p in number_patterns if re.search(p, post, re.IGNORECASE))
        if num_matches >= 5:
            specificity = 5
        elif num_matches >= 3:
            specificity = 4
        elif num_matches >= 2:
            specificity = 3
        elif num_matches >= 1:
            specificity = 2

        # URGENCY: Check for urgency indicators
        urgency_patterns = [
            r'\bjust\b', r'\bnow\b', r'\btoday\b', r'\bthis week\b',
            r'\bexpir', r'\bweekly\b', r'\bbefore\b', r"I'll take it"
        ]
        urgency = 1
        urgency_matches = sum(1 for p in urgency_patterns if re.search(p, post, re.IGNORECASE))
        if urgency_matches >= 3:
            urgency = 5
        elif urgency_matches >= 2:
            urgency = 4
        elif urgency_matches >= 1:
            urgency = 3

        # HUMAN_VOICE: Check for conversational elements
        human_patterns = [
            r'\bhere\'s\b', r'\bhow to\b', r'\bif you\b', r'\bI\'m\b',
            r'\beveryone\b', r'\bthat\'s\b', r'\blet\'s\b', r'\bfree\b',
            r'→', r'📈|🚀', r'\?', r'\bexactly\b'
        ]
        human_voice = 1
        human_matches = sum(1 for p in human_patterns if re.search(p, post, re.IGNORECASE))
        # Also penalize template-like structure
        template_penalty = 1 if '|' in post and post.count('|') >= 3 else 0
        human_voice = min(5, max(1, human_matches - template_penalty))
        if human_matches >= 4:
            human_voice = 5
        elif human_matches >= 2:
            human_voice = 4
        elif human_matches >= 1:
            human_voice = 3
        if template_penalty:
            human_voice = max(1, human_voice - 2)

        # SCROLL_STOP: Combination of above + length and structure
        has_line_breaks = '\n' in post
        has_emoji = bool(re.search(r'[📈🚀📊💰]', post))

        scroll_stop = 1
        scroll_factors = sum([
            news_hook >= 3,
            specificity >= 3,
            urgency >= 3,
            human_voice >= 3,
            has_line_breaks,
            has_emoji,
            len(post) > 100,
        ])
        if scroll_factors >= 5:
            scroll_stop = 5
        elif scroll_factors >= 4:
            scroll_stop = 4
        elif scroll_factors >= 3:
            scroll_stop = 3
        elif scroll_factors >= 2:
            scroll_stop = 2

        total = news_hook + specificity + urgency + human_voice + scroll_stop

        reasoning = f"Heuristic scoring: news_matches={news_matches}, numbers={num_matches}, urgency_cues={urgency_matches}, human_cues={human_matches}"

        return HookinessScore(
            post=post,
            news_hook=news_hook,
            specificity=specificity,
            urgency=urgency,
            human_voice=human_voice,
            scroll_stop=scroll_stop,
            total=total,
            reasoning=reasoning
        )

    def _score_quality_heuristic(self, post: str) -> QualityScore:
        """Score post quality using heuristic rules."""

        # THESIS_CLARITY: Check for clear directional view
        thesis_indicators = [
            r'\b(bullish|bearish|neutral)\b',
            r'\b(buy|sell|hold)\b',
            r'\b(up|down|higher|lower)\b',
            r'\b(rally|drop|surge|decline)\b'
        ]
        thesis_clarity = self._pattern_score(post, thesis_indicators, scale=10)

        # NEWS_DRIVEN: Check for news/event references
        news_indicators = [
            r'\bjust\b', r'\btoday\b', r'\breport(s|ed)?\b',
            r'\bearnings\b', r'\bbeat\b', r'\bmiss\b',
            r'\bannounced?\b', r'\d+%', r'all-time high'
        ]
        news_driven = self._pattern_score(post, news_indicators, scale=10)

        # ACTIONABLE: Check for specific trade details
        has_strike = bool(re.search(r'\$\d+', post))
        has_date = bool(re.search(r'Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec', post))
        has_premium = bool(re.search(r'premium|credit|collect', post, re.I))
        has_pop = bool(re.search(r'\d+%.*prob', post, re.I))

        actionable = sum([has_strike * 3, has_date * 3, has_premium * 2, has_pop * 2])
        actionable = min(10, actionable)

        # ENGAGEMENT: Similar to hookiness scroll_stop
        # Use scroll_stop as base and scale
        scroll_stop_score = self._get_scroll_stop_estimate(post)
        engagement = min(10, scroll_stop_score * 2)  # Scale from 5 to 10

        # ORIGINALITY: Penalty for templates, reward for unique phrasing
        has_template = '|' in post and post.count('|') >= 3
        has_emoji = bool(re.search(r'[📈🚀📊💰→]', post))
        has_question = '?' in post
        has_story = any(w in post.lower() for w in ['here\'s', 'everyone', 'that\'s'])

        originality = 5  # baseline
        if has_template:
            originality -= 3
        if has_emoji:
            originality += 2
        if has_question or has_story:
            originality += 2
        originality = max(1, min(10, originality))

        total = thesis_clarity + news_driven + actionable + engagement + originality

        return QualityScore(
            thesis_clarity=thesis_clarity,
            news_driven=news_driven,
            actionable=actionable,
            engagement=engagement,
            originality=originality,
            total=total,
            reasoning=f"Quality heuristic: thesis={thesis_clarity}, news={news_driven}, actionable={actionable}"
        )

    def _pattern_score(self, text: str, patterns: list, scale: int = 10) -> int:
        """Score based on pattern matches."""
        matches = sum(1 for p in patterns if re.search(p, text, re.I))
        # Scale linearly: 0 matches=1, max matches=scale
        if not matches:
            return 1
        max_expected = len(patterns) // 2  # Expect ~half
        score = 1 + min(matches, max_expected) * (scale - 1) // max_expected
        return min(scale, score)

    def _get_scroll_stop_estimate(self, post: str) -> int:
        """Estimate scroll-stop score (1-5) for quality scoring."""
        has_line_breaks = '\n' in post
        has_emoji = bool(re.search(r'[📈🚀📊💰]', post))
        has_news = bool(re.search(r'\bjust\b|\btoday\b|\breport', post, re.I))
        has_numbers = bool(re.search(r'\d+%|\$\d+', post))

        scroll_factors = sum([
            has_news,
            has_numbers,
            has_line_breaks,
            has_emoji,
            len(post) > 100,
        ])

        if scroll_factors >= 4:
            return 5
        elif scroll_factors >= 3:
            return 4
        elif scroll_factors >= 2:
            return 3
        elif scroll_factors >= 1:
            return 2
        else:
            return 1

    def _check_thresholds(
        self, hookiness_score: int, quality_score: int, total_score: int
    ) -> Tuple[bool, str]:
        """Check if scores meet thresholds."""
        failures = []

        if self.eval_mode in ["hookiness", "both"]:
            if hookiness_score < self.hookiness_min:
                failures.append(
                    f"Hookiness too low: {hookiness_score}/{self.hookiness_min} required"
                )

        if self.eval_mode in ["quality", "both"]:
            if quality_score < self.quality_min:
                failures.append(
                    f"Quality too low: {quality_score}/{self.quality_min} required"
                )

        if total_score < self.total_min:
            failures.append(
                f"Total score too low: {total_score}/{self.total_min} required"
            )

        if failures:
            return False, " | ".join(failures)

        return True, ""

    def format_report(self, score: UnifiedScore) -> str:
        """Format evaluation report for logging."""
        lines = [
            "=" * 50,
            "POST EVALUATION REPORT",
            "=" * 50,
            f"OVERALL: {'✓ PASS' if score.passed else '✗ FAIL'}",
            f"Total Score: {score.total}/75 (min {self.total_min})",
            "",
            f"HOOKINESS (Engagement): {score.hookiness.total}/25 (min {self.hookiness_min})",
            f"  - News Hook: {score.hookiness.news_hook}/5",
            f"  - Specificity: {score.hookiness.specificity}/5",
            f"  - Urgency: {score.hookiness.urgency}/5",
            f"  - Human Voice: {score.hookiness.human_voice}/5",
            f"  - Scroll Stop: {score.hookiness.scroll_stop}/5",
            "",
            f"QUALITY (Content): {score.quality.total}/50 (min {self.quality_min})",
            f"  - Thesis Clarity: {score.quality.thesis_clarity}/10",
            f"  - News Driven: {score.quality.news_driven}/10",
            f"  - Actionable: {score.quality.actionable}/10",
            f"  - Engagement: {score.quality.engagement}/10",
            f"  - Originality: {score.quality.originality}/10",
        ]

        if not score.passed:
            lines.extend([
                "",
                f"FAILURE REASON: {score.failure_reason}",
            ])

        lines.append("=" * 50)
        return "\n".join(lines)
