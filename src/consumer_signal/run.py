"""CLI 엔트리포인트. `consumer-signal run --date YYYY-MM-DD`."""

from __future__ import annotations

import sys
from datetime import date as Date
from pathlib import Path

import typer
from loguru import logger

from consumer_signal.config import Settings, get_settings
from consumer_signal.db.models import Base, upsert_snapshot
from consumer_signal.db.session import make_engine, make_session_factory
from consumer_signal.dictionary.loader import load_keyword_map, load_universe
from consumer_signal.dictionary.validator import validate_keyword_map
from consumer_signal.snapshot import build_empty_snapshot, dump_snapshot

app = typer.Typer(help="소비재 검색 신호 스크리너")

DATA_DIR = Path("data")


def _configure_logging(settings: Settings) -> None:
    logger.remove()
    logger.add(sys.stderr, level=settings.log_level)


def run_pipeline(target_date: Date, settings: Settings) -> Path:
    """collect → normalize → sentiment → narrate → snapshot 순으로 실행한다.

    각 단계는 현재 stub이며 로그만 남긴다.
    """
    keywords = load_keyword_map(DATA_DIR / "keyword_map.yaml")
    universe = load_universe(DATA_DIR / "universe.csv")
    warnings = validate_keyword_map(keywords, universe)
    for w in warnings:
        logger.warning(w)

    logger.info("collect: {} keywords, {} tickers in universe", len(keywords), len(universe))
    logger.info("normalize: stub")
    logger.info("sentiment: stub")
    logger.info("narrate: stub")

    snapshot = build_empty_snapshot(target_date)

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
