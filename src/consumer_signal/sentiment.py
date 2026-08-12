"""감성 게이트 (stub). 검색량 급증이 긍정/부정 뉴스에서 온 것인지 구분."""

from __future__ import annotations

from loguru import logger


def gate_sentiment(keyword: str) -> int:
    """키워드에 대한 감성 점수를 반환한다: -1(부정), 0(중립), 1(긍정).

    아직 실제 감성 분석은 구현하지 않았다 — 항상 중립을 반환.
    """
    logger.info("sentiment stub: keyword={}", keyword)
    return 0
