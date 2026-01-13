"""Tests for retry utilities."""

import pytest
import time
from unittest.mock import Mock, patch

from agent.retry import (
    retry_with_backoff,
    DEFAULT_MAX_RETRIES,
    DEFAULT_DELAY_SECONDS,
    DEFAULT_BACKOFF_MULTIPLIER,
)


class TestRetryWithBackoff:
    """Tests for retry_with_backoff function."""

    def test_success_on_first_try(self):
        """Function succeeds on first call, no retry needed."""
        func = Mock(return_value="success")

        result = retry_with_backoff(
            func=func,
            retryable_exceptions=ValueError,
            operation_name="test_op"
        )

        assert result == "success"
        assert func.call_count == 1

    def test_retry_on_transient_exception(self):
        """Retries when retryable exception is raised, then succeeds."""
        func = Mock(side_effect=[ValueError("fail"), ValueError("fail"), "success"])

        with patch("agent.retry.time.sleep"):  # Don't actually sleep in tests
            result = retry_with_backoff(
                func=func,
                retryable_exceptions=ValueError,
                max_retries=3,
                operation_name="test_op"
            )

        assert result == "success"
        assert func.call_count == 3

    def test_max_retries_exhausted(self):
        """Raises exception after max retries are exhausted."""
        error = ValueError("persistent failure")
        func = Mock(side_effect=error)

        with patch("agent.retry.time.sleep"):
            with pytest.raises(ValueError) as exc_info:
                retry_with_backoff(
                    func=func,
                    retryable_exceptions=ValueError,
                    max_retries=3,
                    operation_name="test_op"
                )

        assert str(exc_info.value) == "persistent failure"
        assert func.call_count == 3

    def test_non_retryable_exception_propagates(self):
        """Non-retryable exceptions propagate immediately without retry."""
        func = Mock(side_effect=TypeError("not retryable"))

        with pytest.raises(TypeError) as exc_info:
            retry_with_backoff(
                func=func,
                retryable_exceptions=ValueError,  # Only retry ValueError
                max_retries=3,
                operation_name="test_op"
            )

        assert str(exc_info.value) == "not retryable"
        assert func.call_count == 1  # No retry attempted

    def test_exponential_backoff_timing(self):
        """Verify delays increase exponentially between retries."""
        func = Mock(side_effect=[ValueError("fail")] * 3)
        sleep_calls = []

        with patch("agent.retry.time.sleep", side_effect=lambda x: sleep_calls.append(x)):
            with pytest.raises(ValueError):
                retry_with_backoff(
                    func=func,
                    retryable_exceptions=ValueError,
                    max_retries=3,
                    initial_delay=1.0,
                    backoff_multiplier=2.0,
                    operation_name="test_op"
                )

        # Should have 2 sleeps (after attempt 1 and 2, not after final attempt)
        assert len(sleep_calls) == 2
        assert sleep_calls[0] == 1.0  # Initial delay
        assert sleep_calls[1] == 2.0  # 1.0 * 2.0

    def test_custom_backoff_multiplier(self):
        """Test with custom backoff multiplier."""
        func = Mock(side_effect=[ValueError("fail")] * 4)
        sleep_calls = []

        with patch("agent.retry.time.sleep", side_effect=lambda x: sleep_calls.append(x)):
            with pytest.raises(ValueError):
                retry_with_backoff(
                    func=func,
                    retryable_exceptions=ValueError,
                    max_retries=4,
                    initial_delay=0.5,
                    backoff_multiplier=3.0,
                    operation_name="test_op"
                )

        assert len(sleep_calls) == 3
        assert sleep_calls[0] == 0.5
        assert sleep_calls[1] == 1.5  # 0.5 * 3.0
        assert sleep_calls[2] == 4.5  # 1.5 * 3.0

    def test_multiple_retryable_exception_types(self):
        """Retries on multiple exception types."""
        func = Mock(side_effect=[
            ValueError("val error"),
            TypeError("type error"),
            "success"
        ])

        with patch("agent.retry.time.sleep"):
            result = retry_with_backoff(
                func=func,
                retryable_exceptions=(ValueError, TypeError),
                max_retries=3,
                operation_name="test_op"
            )

        assert result == "success"
        assert func.call_count == 3

    def test_logging_on_retry(self, caplog):
        """Verify warning is logged on retry."""
        func = Mock(side_effect=[ValueError("temp fail"), "success"])

        with patch("agent.retry.time.sleep"):
            import logging
            with caplog.at_level(logging.WARNING):
                retry_with_backoff(
                    func=func,
                    retryable_exceptions=ValueError,
                    max_retries=3,
                    operation_name="Custom Operation"
                )

        assert "Custom Operation failed (attempt 1/3)" in caplog.text

    def test_logging_on_final_failure(self, caplog):
        """Verify error is logged on final failure."""
        func = Mock(side_effect=ValueError("persistent"))

        with patch("agent.retry.time.sleep"):
            import logging
            with caplog.at_level(logging.ERROR):
                with pytest.raises(ValueError):
                    retry_with_backoff(
                        func=func,
                        retryable_exceptions=ValueError,
                        max_retries=2,
                        operation_name="My Operation"
                    )

        assert "My Operation failed after 2 attempts" in caplog.text


class TestRetryDefaults:
    """Tests for default configuration values."""

    def test_default_max_retries(self):
        """Verify default max retries value."""
        assert DEFAULT_MAX_RETRIES == 3

    def test_default_delay(self):
        """Verify default delay value."""
        assert DEFAULT_DELAY_SECONDS == 2.0

    def test_default_backoff_multiplier(self):
        """Verify default backoff multiplier value."""
        assert DEFAULT_BACKOFF_MULTIPLIER == 2.0
