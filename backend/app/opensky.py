from __future__ import annotations

import dataclasses
import time
from typing import Any, Callable, Optional

import httpx


class OpenSkyError(RuntimeError):
    """Raised when the OpenSky client cannot obtain data after retries."""


TimeFn = Callable[[], float]
SleepFn = Callable[[float], None]


@dataclasses.dataclass
class OpenSkyClient:
    """Thin client for the OpenSky Network REST API with OAuth2 and simple backoff."""

    base_url: str
    auth_url: str
    client_id: str
    client_secret: str
    min_interval_seconds: float = 10.0
    max_backoff_seconds: float = 60.0
    max_retries: int = 3
    _time_fn: TimeFn = time.time
    _sleep_fn: SleepFn = time.sleep

    _access_token: Optional[str] = dataclasses.field(default=None, init=False)
    _token_expiry_ts: Optional[float] = dataclasses.field(default=None, init=False)

    def _token_valid(self) -> bool:
        if not self._access_token or self._token_expiry_ts is None:
            return False
        # Refresh a bit before actual expiry (60s safety margin)
        return self._time_fn() < (self._token_expiry_ts - 60)

    def _obtain_token(self) -> None:
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        try:
            response = httpx.post(
                self.auth_url,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=10.0,
            )
        except Exception as exc:  # network/timeout etc.
            raise OpenSkyError(f"Failed to obtain OpenSky access token: {exc!r}") from exc

        if response.status_code != 200:
            raise OpenSkyError(
                f"Failed to obtain OpenSky access token: {response.status_code} {response.text}"
            )

        body = response.json()
        token = body.get("access_token")
        expires_in = body.get("expires_in", 1800)
        if not token:
            raise OpenSkyError("OpenSky auth response missing access_token")

        self._access_token = token
        self._token_expiry_ts = self._time_fn() + float(expires_in)

    def _get_bearer_headers(self) -> dict[str, str]:
        if not self._token_valid():
            self._obtain_token()
        assert self._access_token is not None  # for type checkers
        return {"Authorization": f"Bearer {self._access_token}"}

    def fetch_states(self, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Fetch the current states from OpenSky with OAuth2 and simple exponential backoff."""
        url = f"{self.base_url.rstrip('/')}/states/all"
        backoff = self.min_interval_seconds

        last_exc: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                headers = self._get_bearer_headers()
                response = httpx.get(url, params=params or {}, headers=headers, timeout=10.0)
            except Exception as exc:  # network/timeout etc.
                last_exc = exc
            else:
                if response.status_code == 200:
                    return response.json()
                if response.status_code == 401:
                    # Token likely expired or invalid; force refresh and retry
                    self._access_token = None
                    self._token_expiry_ts = None
                    if attempt == self.max_retries:
                        raise OpenSkyError("Unauthorized from OpenSky after token refresh attempt")
                elif response.status_code not in (429, 503):
                    # non-retryable error
                    raise OpenSkyError(
                        f"Unexpected OpenSky status {response.status_code}: {response.text}"
                    )

            if attempt == self.max_retries:
                break

            self._sleep_fn(backoff)
            backoff = min(backoff * 2, self.max_backoff_seconds)

        raise OpenSkyError(f"Failed to fetch OpenSky states after max retries; last error: {last_exc!r}")


