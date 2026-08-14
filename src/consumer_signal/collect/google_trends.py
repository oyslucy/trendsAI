"""구글 트렌드 검색어트렌드 수집기.

⚠ 정규화 불변 규칙
구글 트렌드 지수는 한 요청(payload)에 담긴 검색어들 중 최댓값을 100으로 잡는
상대지수다 (절대 검색량이 아니다). z-score는 양의 상수배에 불변이므로, 한
엔트리의 전체 트레일링 구간을 "한 번의 payload" 안에서 받으면 그 시계열 안에서
계산한 z는 유효하다.
날짜별로 따로 요청해서 받은 지수를 이어붙이는(stitch) 것은 절대 금지 —
요청마다 정규화 기준(그 요청 구간의 최댓값)이 달라져 z가 깨진다.
이 모듈은 항상 `[start_date, end_date]` 전체 구간을 배치당 한 번의 payload로
요청하도록 설계되어, 구조적으로 stitching이 불가능하다.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import date as Date
from pathlib import Path

import pandas as pd
from loguru import logger
from pytrends.exceptions import ResponseError, TooManyRequestsError
from pytrends.request import TrendReq

from consumer_signal.config import Settings
from consumer_signal.dictionary.loader import KeywordEntry

MAX_KEYWORDS_PER_REQUEST = 5  # 구글 트렌드 payload 한 번에 비교 가능한 term 수 상한
MAX_ALIASES_PER_TERM = 5  # "a + b + c" OR 결합에 넣을 동의어 수 상한 (쿼리 길이 보호)
MAX_RETRIES = 5
BACKOFF_BASE_SECONDS = 2.0

DEFAULT_CACHE_DIR = Path("cache/google_trends")


class GoogleTrendsError(RuntimeError):
    """구글 트렌드 요청이 재시도 후에도 실패했을 때."""


def _term_for(entry: KeywordEntry) -> str:
    """엔트리를 구글 트렌드 검색어 term으로 변환한다.

    구글 트렌드는 term 안에서 `+`를 OR로 해석하므로, 네이버 데이터랩의
    keywordGroups처럼 동의어/변형어를 하나의 term으로 묶을 수 있다.
    """
    aliases = entry.aliases or [entry.keyword]
    return " + ".join(aliases[:MAX_ALIASES_PER_TERM])


def _batches(entries: list[KeywordEntry]) -> list[list[KeywordEntry]]:
    return [
        entries[i : i + MAX_KEYWORDS_PER_REQUEST]
        for i in range(0, len(entries), MAX_KEYWORDS_PER_REQUEST)
    ]


def _batch_key(terms: list[str], start_date: Date, end_date: Date, geo: str) -> str:
    canonical = json.dumps(
        {"terms": terms, "start": start_date.isoformat(), "end": end_date.isoformat(), "geo": geo},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


def _fetch_with_backoff(
    pytrends: TrendReq, terms: list[str], start_date: Date, end_date: Date, geo: str
) -> pd.DataFrame:
    timeframe = f"{start_date.isoformat()} {end_date.isoformat()}"
    last_exc: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            pytrends.build_payload(terms, timeframe=timeframe, geo=geo)
            return pytrends.interest_over_time()
        except TooManyRequestsError as exc:
            last_exc = exc
            wait = BACKOFF_BASE_SECONDS * (2**attempt)
            logger.warning("google trends 429 rate limited, backing off {}s", wait)
            time.sleep(wait)
        except ResponseError as exc:
            last_exc = exc
            wait = BACKOFF_BASE_SECONDS * (2**attempt)
            logger.warning("google trends response error, retry in {}s: {}", wait, exc)
            time.sleep(wait)

    raise GoogleTrendsError(
        f"google trends request failed after {MAX_RETRIES} retries"
    ) from last_exc


def _request_with_cache(
    pytrends: TrendReq,
    terms: list[str],
    start_date: Date,
    end_date: Date,
    geo: str,
    cache_dir: Path,
) -> pd.DataFrame:
    cache_dir.mkdir(parents=True, exist_ok=True)
    batch_key = _batch_key(terms, start_date, end_date, geo)
    cache_path = cache_dir / f"{end_date.isoformat()}_{batch_key}.json"
    if cache_path.exists():
        logger.debug("google trends cache hit: {}", cache_path)
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        df = pd.DataFrame(cached["values"], index=pd.to_datetime(cached["dates"]))
        return df

    df = _fetch_with_backoff(pytrends, terms, start_date, end_date, geo)
    payload = {
        "dates": [ts.date().isoformat() for ts in df.index],
        "values": {term: [float(v) for v in df[term]] for term in terms if term in df.columns},
    }
    cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return df


def _series_from_df(df: pd.DataFrame, term: str, start_date: Date, end_date: Date) -> pd.Series:
    full_index = pd.date_range(start_date, end_date, freq="D")
    if df.empty or term not in df.columns:
        return pd.Series(0.0, index=full_index)
    series = df[term].astype(float)
    return series.reindex(full_index, fill_value=0.0)


def fetch_search_trend_series(
    entries: list[KeywordEntry],
    start_date: Date,
    end_date: Date,
    settings: Settings,
    *,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    pytrends: TrendReq | None = None,
) -> dict[str, pd.Series]:
    """엔트리별 `[start_date, end_date]` 트레일링 구글 트렌드 시계열을 가져온다.

    반환값은 `entry.keyword` → `pd.Series(index=date, value=index)`. 요청당
    5개 term 제한에 맞춰 배치로 나눠 요청하고, 배치 결과는
    `cache_dir/<end_date>_<batchhash>.json`에 캐시한다.
    """
    if not entries:
        return {}

    active = pytrends or TrendReq(hl="ko-KR", tz=540)
    series: dict[str, pd.Series] = {}
    for batch in _batches(entries):
        terms = [_term_for(entry) for entry in batch]
        df = _request_with_cache(
            active, terms, start_date, end_date, settings.google_trends_geo, cache_dir
        )
        for entry, term in zip(batch, terms, strict=True):
            series[entry.keyword] = _series_from_df(df, term, start_date, end_date)
    return series


def probe(keyword: str, settings: Settings, *, days: int = 30) -> None:
    """단일 키워드로 실제 응답 shape를 확인하는 스파이크 헬퍼."""
    from datetime import timedelta

    end_date = Date.today()
    start_date = end_date - timedelta(days=days)
    entry = KeywordEntry(keyword=keyword, brand="", sector="", direct=[], proxy=[], weight=1.0)
    series_map = fetch_search_trend_series([entry], start_date, end_date, settings)
    series = series_map.get(keyword)
    if series is None:
        logger.error("probe: no result for keyword={}", keyword)
        return
    logger.info("probe: keyword={} points={}", keyword, len(series))
    logger.info("probe: tail=\n{}", series.tail(10))


if __name__ == "__main__":
    import argparse

    from consumer_signal.config import get_settings

    parser = argparse.ArgumentParser(description="구글 트렌드 응답 shape를 키워드 1개로 확인한다.")
    parser.add_argument("keyword", help="조회할 키워드")
    parser.add_argument("--days", type=int, default=30, help="조회 기간(일)")
    args = parser.parse_args()

    probe(args.keyword, get_settings(), days=args.days)
