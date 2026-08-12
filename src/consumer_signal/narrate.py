"""LLM 기반 '왜' 요약 생성 (stub)."""

from __future__ import annotations

from loguru import logger

from consumer_signal.config import Settings


def narrate_why(keyword: str, z: float, settings: Settings) -> str:
    """키워드의 z-score 급등에 대한 한 줄 설명을 생성한다.

    실제 LLM 호출은 아직 구현하지 않았다 — 인터페이스만 정의.
    """
    logger.info("narrate stub: keyword={} z={}", keyword, z)
    _ = settings
    return ""
