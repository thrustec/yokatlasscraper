"""Polite HTTP client with request pacing, timeout handling, and bounded retries."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import time
from typing import Any

import requests


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 5
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.base_delay_seconds < 0 or self.max_delay_seconds < 0:
            raise ValueError("retry delays cannot be negative")


class HttpClient:
    """A small reusable client; every attempt observes the configured rate limit."""

    def __init__(
        self,
        *,
        minimum_interval_seconds: float = 1.0,
        timeout_seconds: float = 30.0,
        retry_policy: RetryPolicy | None = None,
        user_agent: str = "HigherEducationDataResearch/0.1 (read-only collector)",
    ) -> None:
        if minimum_interval_seconds < 1.0:
            raise ValueError("minimum_interval_seconds must be at least 1 second")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.minimum_interval_seconds = minimum_interval_seconds
        self.timeout_seconds = timeout_seconds
        self.retry_policy = retry_policy or RetryPolicy()
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json", "User-Agent": user_agent})
        self._last_request_started = 0.0
        self.requests_made = 0
        self.last_attempt_count = 0

    def _pace(self) -> None:
        remaining = self.minimum_interval_seconds - (time.monotonic() - self._last_request_started)
        if remaining > 0:
            time.sleep(remaining)
        self._last_request_started = time.monotonic()

    def _retry_after(self, response: requests.Response) -> float | None:
        value = response.headers.get("Retry-After")
        if not value:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                return None

    def request(
        self,
        method: str,
        url: str,
        *,
        json_body: Any = None,
        max_attempts: int | None = None,
    ) -> requests.Response:
        policy = self.retry_policy
        attempts_allowed = max_attempts or policy.max_attempts
        if not 1 <= attempts_allowed <= policy.max_attempts:
            raise ValueError("max_attempts must be between 1 and the configured retry limit")
        last_error: Exception | None = None
        self.last_attempt_count = 0

        for attempt in range(1, attempts_allowed + 1):
            self._pace()
            self.requests_made += 1
            self.last_attempt_count = attempt
            try:
                response = self.session.request(
                    method,
                    url,
                    json=json_body,
                    timeout=self.timeout_seconds,
                )
            except requests.RequestException as exc:
                last_error = exc
                if attempt == attempts_allowed:
                    raise
                wait = min(policy.max_delay_seconds, policy.base_delay_seconds * (2 ** (attempt - 1)))
                time.sleep(wait)
                continue

            if response.status_code == 429 or 500 <= response.status_code <= 599:
                if attempt == attempts_allowed:
                    response.raise_for_status()
                backoff = min(policy.max_delay_seconds, policy.base_delay_seconds * (2 ** (attempt - 1)))
                wait = self._retry_after(response)
                time.sleep(max(backoff, wait or 0.0))
                continue

            # Authentication, CAPTCHA, and other access restrictions are not retried or bypassed.
            response.raise_for_status()
            response._codex_attempt_count = attempt
            return response

        if last_error is not None:
            raise last_error
        raise RuntimeError("HTTP request ended without a response")

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> "HttpClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

