import time
from unittest import mock

import httpx

from backend.app.opensky import OpenSkyClient, OpenSkyError


class DummyTime:
    """Deterministic time/ sleep helper."""

    def __init__(self) -> None:
        self._now = 0.0
        self.sleeps = []

    def time(self) -> float:
        return self._now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self._now += seconds


def make_client(dummy_time: DummyTime) -> OpenSkyClient:
    return OpenSkyClient(
        base_url="https://opensky-network.org/api",
        username=None,
        password=None,
        min_interval_seconds=10,
        max_backoff_seconds=60,
        _time_fn=dummy_time.time,
        _sleep_fn=dummy_time.sleep,
    )


def test_backoff_increases_on_rate_limit():
    dummy_time = DummyTime()
    client = make_client(dummy_time)

    responses = [
        httpx.Response(429, request=httpx.Request("GET", "https://opensky-network.org/api/states/all")),
        httpx.Response(200, json={"states": []}, request=httpx.Request("GET", "https://opensky-network.org/api/states/all")),
    ]

    with mock.patch("backend.app.opensky.httpx.get", side_effect=responses) as get_mock:
        result = client.fetch_states()

    assert result == {"states": []}
    # should have called underlying HTTP twice
    assert get_mock.call_count == 2
    # should have slept at least once with some positive backoff
    assert dummy_time.sleeps
    assert dummy_time.sleeps[0] > 0


def test_eventual_failure_raises_error():
    dummy_time = DummyTime()
    client = make_client(dummy_time)

    # Always returning 503 should eventually raise
    responses = [
        httpx.Response(503, request=httpx.Request("GET", "https://opensky-network.org/api/states/all"))
        for _ in range(5)
    ]

    with mock.patch("backend.app.opensky.httpx.get", side_effect=responses):
        try:
            client.fetch_states()
        except OpenSkyError as exc:
            assert "max retries" in str(exc).lower()
        else:
            raise AssertionError("Expected OpenSkyError on repeated failures")

