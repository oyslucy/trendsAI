"""CLI 엔트리포인트. `consumer-signal --date YYYY-MM-DD`."""

from __future__ import annotations

import sys
from datetime import date as Date
from datetime import timedelta
from pathlib import Path

import pandas as pd
import typer
from loguru import logger

from consumer_signal.collect import google_trends, krx
from consumer_signal.config import Settings, get_settings
from consumer_signal.db.models import Base, upsert_snapshot
from consumer_signal.db.session import make_engine, make_session_factory
from consumer_signal.dictionary.loader import KeywordEntry, load_keyword_map, load_universe
from consumer_signal.dictionary.validator import validate_keyword_map
from consumer_signal.normalize import is_no_signal, latest_zscore, rolling_zscore, winsorize
from consumer_signal.recommend import compute_persistence, has_enough_volume, recommendation_score
from consumer_signal.sentiment import gate_sentiment
from consumer_signal.snapshot import build_snapshot, dump_debug_series, dump_snapshot

app = typer.Typer(help="소비재 검색 신호 스크리너")

DATA_DIR = Path("data")
DEBUG_DIR = Path("debug")


def _configure_logging(settings: Settings) -> None:
    logger.remove()
    logger.add(sys.stderr, level=settings.log_level)


def _score_keywords(
    keywords: list[KeywordEntry], raw_search: dict[str, pd.Series], z_window: int
) -> tuple[dict[str, float], dict[str, bool], dict[str, int], dict[str, pd.Series]]:
    """키워드별 z, no_signal, sentiment(stub), 디버그용 z 시계열을 계산한다."""
    keyword_z: dict[str, float] = {}
    keyword_no_signal: dict[str, bool] = {}
    keyword_sentiment: dict[str, int] = {}
    z_series: dict[str, pd.Series] = {}

    for entry in keywords:
        series = raw_search.get(entry.product, pd.Series(dtype=float))
        no_signal = is_no_signal(series)
        keyword_no_signal[entry.product] = no_signal
        keyword_z[entry.product] = 0.0 if no_signal else latest_zscore(series, z_window)
        z_series[entry.product] = winsorize(rolling_zscore(series, z_window))
        keyword_sentiment[entry.product] = gate_sentiment(entry.product)

    return keyword_z, keyword_no_signal, keyword_sentiment, z_series


def _recommend_keywords(
    keywords: list[KeywordEntry],
    raw_search: dict[str, pd.Series],
    keyword_z: dict[str, float],
    z_series: dict[str, pd.Series],
) -> tuple[dict[str, float], dict[str, bool]]:
    """키워드별 추천 점수(z×지속성×엔티티 가중치)와 저신뢰 여부를 계산한다."""
    keyword_recommendation: dict[str, float] = {}
    keyword_low_confidence: dict[str, bool] = {}

    for entry in keywords:
        raw = raw_search.get(entry.product, pd.Series(dtype=float))
        enough_volume = has_enough_volume(raw)
        keyword_low_confidence[entry.product] = not enough_volume
        persistence = compute_persistence(z_series.get(entry.product, pd.Series(dtype=float)))
        keyword_recommendation[entry.product] = recommendation_score(
            keyword_z.get(entry.product, 0.0),
            entry.weight,
            persistence,
            enough_volume=enough_volume,
        )

    return keyword_recommendation, keyword_low_confidence


def run_pipeline(target_date: Date, settings: Settings) -> Path:
    """collect → normalize → sentiment(stub) → narrate(stub) → snapshot 순으로 실행한다."""
    keywords = load_keyword_map(DATA_DIR / "keyword_map.yaml")
    universe = load_universe(DATA_DIR / "universe.csv")
    warnings = validate_keyword_map(keywords, universe)
    for w in warnings:
        logger.warning(w)

    start_date = target_date - timedelta(days=settings.z_window + settings.window_buffer_days)
    end_date = target_date
    logger.info(
        "collect: {} keywords, {} tickers, window {}..{}",
        len(keywords),
        len(universe),
        start_date,
        end_date,
    )

    raw_search = google_trends.fetch_search_trend_series(keywords, start_date, end_date, settings)
    keyword_z, keyword_no_signal, keyword_sentiment, z_series = _score_keywords(
        keywords, raw_search, settings.z_window
    )
    logger.info("normalize: {} keyword entries scored", len(keyword_z))

    keyword_recommendation, keyword_low_confidence = _recommend_keywords(
        keywords, raw_search, keyword_z, z_series
    )
    n_recommended = sum(1 for score in keyword_recommendation.values() if score > 0)
    logger.info("recommend: {} keywords pass the watchlist bar", n_recommended)

    tickers = [u.ticker for u in universe]
    raw_volume = krx.fetch_volume_series(tickers, start_date, end_date)
    volume_z = {
        ticker: (0.0 if is_no_signal(series) else latest_zscore(series, settings.z_window))
        for ticker, series in raw_volume.items()
    }
    logger.info("collect.krx: {} tickers scored", len(volume_z))

    logger.info("sentiment: stub (always neutral)")
    logger.info("narrate: stub (always empty)")

    snapshot = build_snapshot(
        target_date,
        keywords,
        universe,
        keyword_z,
        keyword_sentiment,
        keyword_no_signal,
        volume_z,
        threshold=settings.z_threshold,
        keyword_recommendation=keyword_recommendation,
        keyword_low_confidence=keyword_low_confidence,
    )

    dump_debug_series(target_date, raw_search, z_series, DEBUG_DIR)

    engine = make_engine(settings)
    Base.metadata.create_all(engine)
    session_factory = make_session_factory(engine)
    with session_factory() as session:
        upsert_snapshot(session, snapshot.date, snapshot.model_dump(mode="json"))

    out_path = dump_snapshot(snapshot, DATA_DIR)
    logger.info("snapshot written: {}", out_path)
    return out_path


@app.command()
def run(
    date: str = typer.Option(..., "--date", help="처리할 날짜 (YYYY-MM-DD)"),
) -> None:
    """지정한 날짜의 신호 스냅샷을 생성한다."""
    target_date = Date.fromisoformat(date)
    settings = get_settings()
    _configure_logging(settings)
    run_pipeline(target_date, settings)


if __name__ == "__main__":
    app()
