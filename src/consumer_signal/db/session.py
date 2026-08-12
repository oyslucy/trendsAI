"""엔진/세션 생성. `config.db_url`에서 드라이버를 결정한다."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from consumer_signal.config import Settings


def make_engine(settings: Settings) -> Engine:
    if settings.db_url.startswith("sqlite:///"):
        db_path = settings.db_url.removeprefix("sqlite:///")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(settings.db_url)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
