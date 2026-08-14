from __future__ import annotations

from datetime import date
from urllib.parse import parse_qs

import httpx
import pytest

from consumer_signal.collect.krx import fetch_volume_series


def _krx_response(rows: list[dict]) -> dict:
    return {"OutBlock_1": rows}


def _trd_dd(request: httpx.Request) -> str:
    params = parse_qs(request.content.decode())
    return params["trdDd"][0]


def test_fetch_volume_series_filters_to_universe_and_skips_holidays(tmp_path) -> None:
    start, end = date(2026, 1, 1), date(2026, 1, 3)

    def handler(request: httpx.Request) -> httpx.Response:
        if _trd_dd(request) == "20260102":
            return httpx.Response(
                200,
                json=_krx_response(
                    [
                        {"ISU_SRT_CD": "003230", "ACC_TRDVOL": "1,234"},
                        {"ISU_SRT_CD": "999999", "ACC_TRDVOL": "500"},
                    ]
                ),
            )
        return httpx.Response(200, json=_krx_response([]))

    client = httpx.Client(transport=httpx.MockTransport(handler))
    series = fetch_volume_series(
        ["003230"], start, end, cache_dir=tmp_path / "cache", client=client
    )

    s = series["003230"]
    assert len(s) == 1
    assert s.iloc[0] == 1234.0


def test_fetch_volume_series_uses_cache_on_second_call(tmp_path) -> None:
    start, end = date(2026, 1, 1), date(2026, 1, 1)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(
            200, json=_krx_response([{"ISU_SRT_CD": "003230", "ACC_TRDVOL": "10"}])
        )

    cache_dir = tmp_path / "cache"
    fetch_volume_series(
        ["003230"],
        start,
        end,
        cache_dir=cache_dir,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    fetch_volume_series(
        ["003230"],
        start,
        end,
        cache_dir=cache_dir,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )

    assert calls["n"] == 1


def test_fetch_volume_series_skips_failed_day_without_raising(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("consumer_signal.collect.krx.time.sleep", lambda _: None)
    start, end = date(2026, 1, 1), date(2026, 1, 2)

    def handler(request: httpx.Request) -> httpx.Response:
        if _trd_dd(request) == "20260101":
            return httpx.Response(500)
        return httpx.Response(
            200, json=_krx_response([{"ISU_SRT_CD": "003230", "ACC_TRDVOL": "10"}])
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    series = fetch_volume_series(
        ["003230"], start, end, cache_dir=tmp_path / "cache", client=client
    )

    assert len(series["003230"]) == 1
