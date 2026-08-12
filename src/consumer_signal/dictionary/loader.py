"""`keyword_map.yaml` / `universe.csv` 로더."""

from __future__ import annotations

import csv
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class KeywordEntry(BaseModel):
    keyword: str
    brand: str
    sector: str
    direct: list[str] = Field(default_factory=list)
    proxy: list[str] = Field(default_factory=list)
    weight: float = 1.0


class UniverseEntry(BaseModel):
    ticker: str
    name: str
    sector: str


def load_keyword_map(path: Path) -> list[KeywordEntry]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return [KeywordEntry.model_validate(row) for row in raw]


def load_universe(path: Path) -> list[UniverseEntry]:
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [UniverseEntry.model_validate(row) for row in reader]
