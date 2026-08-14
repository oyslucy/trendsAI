"""KRX 거래량 수집기.

data.krx.co.kr의 공개 "전종목시세"(bld=dbms/MDC/STAT/standard/MDCSTAT01501)
엔드포인트를 날짜별로 호출해 유니버스 티커의 거래량을 뽑는다. 이 엔드포인트는
종목 단축코드(ISU_SRT_CD)를 그대로 키로 쓰므로 ISIN 변환이 필요 없다.
"""

from __future__ import annotations

import json
import time
from datetime import date as Date
from datetime import timedelta
from pathlib import Path

import httpx
import pandas as pd
from loguru import logger

KRX_JSON_URL = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
KRX_BLD = "dbms/MDC/STAT/standard/MDCSTAT01501"
KRX_REFERER = "http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201020101"

MAX_RETRIES = 5
BACKOFF_BASE_SECONDS = 1.0

DEFAULT_CACHE_DIR = Path("cache/krx")


class KrxFetchError(RuntimeError):
    """KRX 요청이 재시도 후에도 실패했을 때."""


def _daterange(start_date: Date, end_date: Date) -> list[Date]:
    days = (end_date - start_date).days
    return [start_date + timedelta(days=i) for i in range(days + 1)]


def _post_with_backoff(client: httpx.Client, trade_date: Date) -> list[dict]:
    params = {
        "bld": KRX_BLD,
        "mktId": "ALL",
        "trdDd": trade_date.strftime("%Y%m%d"),
        "share": "1",
        "csvxls_isNo": "false",
    }
    headers = {"Referer": KRX_REFERER}
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            resp = client.post(KRX_JSON_URL, data=params, headers=headers)
            resp.raise_for_status()
            body = resp.json()
            result: list[dict] = body.get("OutBlock_1", [])
            return result
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            last_exc = exc
            wait = BACKOFF_BASE_SECONDS * (2**attempt)
            logger.warning("krx request failed for {}, retry in {}s: {}", trade_date, wait, exc)
            time.sleep(wait)
    raise KrxFetchError(
        f"krx request failed for {trade_date} after {MAX_RETRIES} retries"
    ) from last_exc


def _fetch_day_with_cache(client: httpx.Client, trade_date: Date, cache_dir: Path) -> list[dict]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{trade_date.isoformat()}.json"
    if cache_path.exists():
        logger.debug("krx cache hit: {}", cache_path)
        return json.loads(cache_path.read_text(encoding="utf-8"))

    rows = _post_with_backoff(client, trade_date)
    cache_path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return rows


def fetch_volume_series(
    tickers: list[str],
    start_date: Date,
    end_date: Date,
    *,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    client: httpx.Client | None = None,
) -> dict[str, pd.Series]:
    """티커별 `[start_date, end_date]` 트레일링 거래량 시계열을 가져온다.

    주말·휴장일은 거래 자체가 없으므로 시계열에서 빠진다(0으로 채우지 않는다) —
    거래일 기준 rolling z-score를 위해 인위적인 0 거래량 날짜를 만들지 않는다.
    응답이 비어 있는 휴장일은 오류가 아니라 정상 스킵으로 처리하고, 실제
    네트워크/서버 오류만 백오프 재시도한다.
    """
    if not tickers:
        return {}

    ticker_set = set(tickers)
    owns_client = client is None
    active_client = client or httpx.Client(timeout=15.0)
    points: dict[str, list[tuple[Date, float]]] = {ticker: [] for ticker in tickers}
    try:
        for trade_date in _daterange(start_date, end_date):
            try:
                rows = _fetch_day_with_cache(active_client, trade_date, cache_dir)
            except KrxFetchError as exc:
                logger.warning("krx: skipping {} — {}", trade_date, exc)
                continue
            for row in rows:
                ticker = row.get("ISU_SRT_CD")
                if ticker not in ticker_set:
                    continue
                raw_volume = row.get("ACC_TRDVOL", "0")
                try:
                    volume = float(str(raw_volume).replace(",", ""))
                except ValueError:
                    continue
                points[ticker].append((trade_date, volume))
    finally:
        if owns_client:
            active_client.close()

    series: dict[str, pd.Series] = {}
    for ticker, ticker_points in points.items():
        if not ticker_points:
            series[ticker] = pd.Series(dtype=float)
            continue
        ticker_points.sort(key=lambda pair: pair[0])
        idx = pd.to_datetime([d for d, _ in ticker_points])
        values = [v for _, v in ticker_points]
        series[ticker] = pd.Series(values, index=idx)
    return series
