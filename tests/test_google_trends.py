from __future__ import annotations

from datetime import date

import pandas as pd
import pytest
from pytrends.exceptions import ResponseError, TooManyRequestsError

from consumer_signal.collect.google_trends import (
    GoogleTrendsError,
    _batches,
    _term_for,
    fetch_search_trend_series,
)
from consumer_signal.config import Settings
from consumer_signal.dictionary.loader import KeywordEntry


def _settings() -> Settings:
    return Settings(llm_api_key="key")  # type: ignore[call-arg]


def _entry(
    product: str,
    aliases: list[str] | None = None,
    geo_keywords: dict[str, list[str]] | None = None,
) -> KeywordEntry:
    return KeywordEntry(
        product=product,
        brand="",
        sector="s",
        direct=[],
        proxy=[],
        aliases=aliases or [],
        geo_keywords=geo_keywords or {},
    )


class _FakeTrendReq:
    """`build_payload` + `interest_over_time`만 흉내내는 pytrends 대역."""

    def __init__(self, respond, *, fail_times: int = 0, error: type[Exception] = ResponseError):
        self._respond = respond
        self._fail_times = fail_times
        self._error = error
        self.calls = 0
        self._terms: list[str] = []

    def build_payload(
        self, terms: list[str], timeframe: str | None = None, geo: str | None = None
    ) -> None:
        self.calls += 1
        self._terms = list(terms)
        if self.calls <= self._fail_times:
            raise self._error("simulated failure", None)

    def interest_over_time(self) -> pd.DataFrame:
        return self._respond(self._terms)


def _df(terms: list[str], dates: list[str], value: float = 10.0) -> pd.DataFrame:
    idx = pd.to_datetime(dates)
    data = {term: [value] * len(dates) for term in terms}
    data["isPartial"] = [False] * len(dates)
    return pd.DataFrame(data, index=idx)


def test_batches_respect_group_limit() -> None:
    entries = [_entry(f"kw{i}") for i in range(12)]
    batches = _batches(entries)
    assert [len(b) for b in batches] == [5, 5, 2]


def test_term_for_uses_aliases_when_present() -> None:
    entry = _entry("k", aliases=["a", "b"])
    assert _term_for(entry, "KR") == "a + b"


def test_term_for_falls_back_to_product() -> None:
    assert _term_for(_entry("k"), "KR") == "k"


def test_term_for_prefers_geo_keywords_over_aliases() -> None:
    entry = _entry("부스터프로", aliases=["부스터 프로"], geo_keywords={"US": ["booster pro"]})
    assert _term_for(entry, "US") == "booster pro"
    assert _term_for(entry, "KR") == "부스터 프로"


def test_fetch_search_trend_series_parses_and_reindexes(tmp_path) -> None:
    start, end = date(2026, 1, 1), date(2026, 1, 5)

    def respond(terms: list[str]) -> pd.DataFrame:
        return _df(terms, ["2026-01-02", "2026-01-04"])

    fake = _FakeTrendReq(respond)
    series = fetch_search_trend_series(
        [_entry("불닭볶음면")], start, end, _settings(), cache_dir=tmp_path / "cache", pytrends=fake
    )

    s = series["불닭볶음면"]
    assert len(s) == 5
    assert s.loc["2026-01-02"] == 10.0
    assert s.loc["2026-01-01"] == 0.0


def test_fetch_search_trend_series_uses_cache_on_second_call(tmp_path) -> None:
    start, end = date(2026, 1, 1), date(2026, 1, 3)

    def respond(terms: list[str]) -> pd.DataFrame:
        return _df(terms, ["2026-01-02"])

    cache_dir = tmp_path / "cache"
    entries = [_entry("k")]

    fetch_search_trend_series(
        entries, start, end, _settings(), cache_dir=cache_dir, pytrends=_FakeTrendReq(respond)
    )
    second = _FakeTrendReq(respond)
    fetch_search_trend_series(
        entries, start, end, _settings(), cache_dir=cache_dir, pytrends=second
    )

    assert second.calls == 0


def test_fetch_retries_on_429_then_succeeds(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("consumer_signal.collect.google_trends.time.sleep", lambda _: None)
    start, end = date(2026, 1, 1), date(2026, 1, 3)

    def respond(terms: list[str]) -> pd.DataFrame:
        return _df(terms, ["2026-01-02"])

    fake = _FakeTrendReq(respond, fail_times=2, error=TooManyRequestsError)
    series = fetch_search_trend_series(
        [_entry("k")], start, end, _settings(), cache_dir=tmp_path / "cache", pytrends=fake
    )

    assert fake.calls == 3
    assert "k" in series


def test_fetch_raises_after_max_retries(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("consumer_signal.collect.google_trends.time.sleep", lambda _: None)
    start, end = date(2026, 1, 1), date(2026, 1, 3)

    fake = _FakeTrendReq(lambda terms: _df(terms, ["2026-01-02"]), fail_times=999)
    with pytest.raises(GoogleTrendsError):
        fetch_search_trend_series(
            [_entry("k")], start, end, _settings(), cache_dir=tmp_path / "cache", pytrends=fake
        )
