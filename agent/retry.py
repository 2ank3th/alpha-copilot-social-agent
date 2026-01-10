"""Retry utilities for handling transient failures."""

import logging
import time
from typing import TypeVar, Callable, Tuple, Type, Union

logger = logging.getLogger(__name__)

# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_DELAY_SECONDS = 2.0
DEFAULT_BACKOFF_MULTIPLIER = 2.0

T = TypeVar('T')


def retry_with_backoff(
    func: Callable[[], T],
    retryable_exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]],
    max_retries: int = DEFAULT_MAX_RETRIES,
    initial_delay: float = DEFAULT_DELAY_SECONDS,
    backoff_multiplier: float = DEFAULT_BACKOFF_MULTIPLIER,
    operation_name: str = "operation",
) -> T:
    """
    Retry a function with exponential backoff on specific exceptions.

    Args:
        func: The function to call (should take no arguments)
        retryable_exceptions: Exception type(s) to retry on
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        backoff_multiplier: Multiplier for delay after each retry
        operation_name: Name for logging purposes

    Returns:
        The return value of func

    Raises:
        The last exception if all retries fail
    """
    last_error: Exception = None
    delay = initial_delay

    for attempt in range(1, max_retries + 1):
        try:
            return func()
        except retryable_exceptions as e:
            last_error = e
            if attempt < max_retries:
                logger.warning(
                    f"{operation_name} failed (attempt {attempt}/{max_retries}): {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                time.sleep(delay)
                delay *= backoff_multiplier
            else:
                logger.error(f"{operation_name} failed after {max_retries} attempts: {e}")
                raise
        except Exception:
            # Don't retry on non-retryable exceptions
            raise

    # Should not reach here, but just in case
    if last_error:
        raise last_error
