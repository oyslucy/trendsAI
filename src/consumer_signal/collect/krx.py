"""KRX 거래량 수집기 (stub). dstask에서 재활용 예정."""

from __future__ import annotations

from datetime import date as Date

from loguru import logger


def fetch_volume(tickers: list[str], target_date: Date) -> dict[str, float]:
    """티커별 거래량을 가져온다.

    dstask의 기존 수집 로직을 재활용할 예정 — 아직 stub.
    """
    logger.info("collect.krx stub: {} tickers for {}", len(tickers), target_date)
    return {ticker: 0.0 for ticker in tickers}
