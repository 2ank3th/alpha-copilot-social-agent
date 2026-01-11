# E2E CI/CD Test Design

## Overview

Add end-to-end testing to CI/CD pipeline to verify the complete agent flow works before merging PRs.

## Decision Summary

| Aspect | Decision |
|--------|----------|
| CI Platform | GitHub Actions |
| Trigger | PRs to `main` only |
| Mode | Full integration with real services, dry-run enabled |
| Pass Criteria | Agent completes + post passes evaluation (≥45/75) |
| Missing Secrets | Fail test (not skip) |

## Architecture

### Workflow Flow

```
PR to main
    ↓
GitHub Actions triggered
    ↓
Install dependencies
    ↓
Run E2E test (pytest -m e2e)
    ↓
Agent runs with real LLM + Alpha Copilot API
    ↓
Dry-run mode prevents actual posting
    ↓
Verify: TASK_COMPLETE + EVAL_PASSED
    ↓
PR status updated (pass/fail)
```

### Files to Create

1. `.github/workflows/e2e-test.yml` - GitHub Actions workflow
2. `tests/test_e2e.py` - E2E test implementation
3. `pytest.ini` - Pytest configuration with markers

## Implementation Details

### 1. GitHub Actions Workflow

**File**: `.github/workflows/e2e-test.yml`

- Trigger on PRs to `main` only
- Ubuntu latest, Python 3.9
- Install dependencies from `requirements.txt`
- Run `pytest -m e2e` with secrets as env vars
- 5-minute timeout
- Concurrency: cancel in-progress runs on same PR

**Required Secrets**:
- `GEMINI_API_KEY`
- One of:
  - `ALPHA_COPILOT_API_KEY`, OR
  - `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_EMAIL`, `SUPABASE_PASSWORD`

### 2. E2E Test

**File**: `tests/test_e2e.py`

```python
@pytest.mark.e2e
def test_e2e_agent_completes_and_passes_evaluation():
    # 1. Validate required env vars - FAIL if missing
    # 2. Force DRY_RUN=true
    # 3. Run agent with morning post task
    # 4. Assert TASK_COMPLETE or SUCCESS in result
    # 5. Assert EVAL_FAILED not in result
    # 6. Assert agent._pending_post is not None
```

### 3. Pytest Configuration

**File**: `pytest.ini`

```ini
[pytest]
markers =
    e2e: End-to-end tests requiring API keys (GEMINI_API_KEY, ALPHA_COPILOT credentials)

# By default, skip e2e tests
addopts = -m "not e2e"
```

This allows:
- `pytest` - runs unit tests only (default)
- `pytest -m e2e` - runs E2E tests only
- `pytest -m ""` - runs all tests

### 4. Error Handling

| Scenario | Behavior |
|----------|----------|
| Missing secrets | Test fails with clear error listing missing vars |
| API rate limit | Fail (no retry in v1) |
| LLM timeout | Fail with timeout error |
| Evaluation fails | Fail with score details |
| Agent completes but no post | Fail |

### 5. Safeguards

- `DRY_RUN=true` hardcoded in test (cannot post accidentally)
- Pytest timeout: 3 minutes per test
- Workflow timeout: 5 minutes total

## Success Criteria

1. PR to `main` triggers E2E test
2. Test runs full agent loop with real APIs
3. Test passes only if:
   - Agent returns success status
   - Generated post scores ≥45/75
4. Test fails clearly if secrets missing
5. Failed test blocks PR merge

## Future Enhancements (Out of Scope)

- Retry logic for flaky LLM responses
- Parallel test runs for different post types
- Test result caching
- Slack notifications on failure
