"""네이버 데이터랩 검색어트렌드 수집기 (stub)."""

from __future__ import annotations

from datetime import date as Date

import httpx
from loguru import logger

from consumer_signal.config import Settings

NAVER_DATALAB_URL = "https://openapi.naver.com/v1/datalab/search"


def fetch_search_trend(
    keywords: list[str], target_date: Date, settings: Settings
) -> dict[str, float]:
    """키워드별 검색량 지수를 가져온다.

    실제 API 호출은 아직 구현하지 않았다 — 인터페이스만 정의.
    """
    logger.info("collect.naver stub: {} keywords for {}", len(keywords), target_date)
    _ = httpx.Client  # 실제 구현 시 사용할 클라이언트 타입 참조
    _ = settings
    return {kw: 0.0 for kw in keywords}
