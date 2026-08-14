"""`keyword_map.yaml` / `universe.csv` 로더."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

Ownership = Literal["direct", "equity_method", "distribution"]


class KeywordEntry(BaseModel):
    """제품(SKU) 레벨 검색어 한 건 — 브랜드 → 상장사로 이어지는 귀속 체인.

    신호는 product_to_brand × brand_to_company(`weight` 참고)로 감쇠된다 —
    니치 제품의 바이럴이 회사 전체 신호로 과대평가되는 것을 막기 위함.
    두 비율 모두 사업보고서·IR 자료 기반 근사치이며 기본값 1.0(전량 귀속)은
    "아직 리서치 전"이라는 뜻이지 실제 비중이 100%라는 뜻이 아니다 — 다중
    브랜드/사업부 보유 기업은 사람이 리서치해서 채워야 한다.
    """

    product: str
    brand: str
    sector: str
    direct: list[str] = Field(default_factory=list)
    proxy: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(
        default_factory=list,
        description="구글 트렌드 term에 OR(+)로 묶을 기본(geo 미지정) 동의어/변형어.",
    )
    geo_keywords: dict[str, list[str]] = Field(
        default_factory=dict,
        description=(
            "geo별 검색어 override. 예: {'US': ['medicube booster pro']}. "
            "해당 geo 항목이 없으면 aliases → product 순으로 fallback."
        ),
    )
    product_to_brand: float = Field(
        default=1.0, ge=0.0, le=1.0, description="제품이 브랜드 매출에서 차지하는 비중 근사치"
    )
    brand_to_company: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="브랜드가 상장사 전사 매출에서 차지하는 비중 근사치",
    )
    ownership: Ownership = Field(
        default="direct", description="브랜드-상장사 관계: 완전자회사/지분법/단순유통"
    )

    @property
    def weight(self) -> float:
        """product_to_brand × brand_to_company — 종목 신호 집계에 쓰는 유효 가중치."""
        return self.product_to_brand * self.brand_to_company


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
