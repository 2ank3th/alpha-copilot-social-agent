#!/usr/bin/env python3
"""Railway entrypoint - determines post type based on current UTC hour and day of week.

Schedule (UTC → EST):
  14:00 (9 AM EST)  — Morning post: trade Mon/Thu, question Tue/Fri, contrarian Wed
  15:00 (10 AM EST) — Engage: reply to popular FinTwit tweets
  17:00 (12 PM EST) — Midday post: commentary Mon/Thu, thread_starter Tue/Fri, volatility Wed
  20:00 (3 PM EST)  — EOD trade post
  22:00 (5 PM EST)  — Engage: reply to popular FinTwit tweets
"""

import subprocess
import sys
from datetime import datetime, timezone


def get_post_args():
    """Return CLI args based on current UTC hour and day of week."""
    now = datetime.now(timezone.utc)
    hour = now.hour
    dow = now.isoweekday()  # 1=Mon ... 5=Fri

    if hour == 14:
        # 9 AM EST — morning slot, rotate by day
        if dow in (1, 4):
            return ["--post", "morning"]
        elif dow in (2, 5):
            return ["--post", "question"]
        else:
            return ["--post", "contrarian"]

    elif hour in (15, 22):
        # 10 AM / 5 PM EST — engage slots
        return ["--engage"]

    elif hour == 17:
        # 12 PM EST — midday slot, rotate by day
        if dow in (1, 4):
            return ["--post", "commentary"]
        elif dow in (2, 5):
            return ["--post", "thread_starter"]
        else:
            return ["--post", "volatility"]

    elif hour == 20:
        # 3 PM EST — power hour / EOD
        return ["--post", "eod"]

    else:
        # Fallback for manual/unexpected runs
        return ["--post", "morning"]


def main():
    args = get_post_args()
    cmd = [sys.executable, "-m", "agent.main"] + args
    print(f"Entrypoint: running {' '.join(cmd)}")
    result = subprocess.run(cmd)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
