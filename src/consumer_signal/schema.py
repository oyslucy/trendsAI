"""프론트엔드와 공유하는 스냅샷 계약."""

from __future__ import annotations

from datetime import date as Date
from typing import Literal

from pydantic import BaseModel, Field

NodeType = Literal["keyword", "sector", "stock"]
LinkKind = Literal["direct", "proxy", "sec", "own", "adj", "bad"]
StockStatus = Literal["lead", "react"]
StockSub = Literal["direct", "proxy"]


class Node(BaseModel):
    id: str
    type: NodeType
    label: str

    z: float | None = None
    sentiment: int | None = None
    why: str | None = None

    sub: StockSub | None = None
    ticker: str | None = None
    sector: str | None = None
    agg: float | None = None
    volume_z: float | None = None
    status: StockStatus | None = None


class Link(BaseModel):
    source: str
    target: str
    kind: LinkKind


class Snapshot(BaseModel):
    date: Date
    nodes: list[Node] = Field(default_factory=list)
    links: list[Link] = Field(default_factory=list)
