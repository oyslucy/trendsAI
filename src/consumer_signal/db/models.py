"""스냅샷 저장 테이블 정의."""

from __future__ import annotations

from datetime import date as Date
from datetime import datetime

from sqlalchemy import JSON, DateTime, func
from sqlalchemy import Date as SADate
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class SnapshotRow(Base):
    __tablename__ = "snapshot"

    date: Mapped[Date] = mapped_column(SADate, primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


def upsert_snapshot(session: Session, date: Date, payload: dict) -> SnapshotRow:
    """같은 날짜의 스냅샷이 있으면 payload를 덮어쓰고, 없으면 새로 만든다."""
    row = session.get(SnapshotRow, date)
    if row is None:
        row = SnapshotRow(date=date, payload=payload)
        session.add(row)
    else:
        row.payload = payload
    session.commit()
    return row
