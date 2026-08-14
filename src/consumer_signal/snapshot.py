"""스냅샷 빌드 및 저장."""

from __future__ import annotations

import json
from datetime import date as Date
from pathlib import Path

import pandas as pd

from consumer_signal.dictionary.loader import KeywordEntry, UniverseEntry
from consumer_signal.schema import Link, Node, Snapshot, StockStatus, StockSub

# 섹터 간 인접(참고용) 관계. static — 리서치로 필요시 확장.
SECTOR_ADJACENCY: list[tuple[str, str]] = [
    ("ramen_snack", "bakery"),
    ("ramen_snack", "retail"),
    ("dairy_beverage", "alcohol_beverage"),
    ("dairy_beverage", "bakery"),
    ("retail", "cosmetics"),
]


def _stock_status(agg: float, volume_z: float, threshold: float) -> StockStatus | None:
    """검색 관심도(agg)가 임계 이상일 때만 lead/react를 판정한다.

    거래량 z가 아직 낮으면 선행(lead), 이미 같이 튀었으면 반응(react).
    """
    if agg < threshold:
        return None
    return "react" if volume_z >= threshold else "lead"


def build_empty_snapshot(target_date: Date) -> Snapshot:
    """빈 스냅샷을 만든다 (사전이 비어있거나 데이터 수집 전 fallback)."""
    return Snapshot(date=target_date, nodes=[], links=[])


def build_snapshot(
    target_date: Date,
    keywords: list[KeywordEntry],
    universe: list[UniverseEntry],
    keyword_z: dict[str, float],
    keyword_sentiment: dict[str, int],
    keyword_no_signal: dict[str, bool],
    volume_z: dict[str, float],
    threshold: float,
) -> Snapshot:
    """실제 검색/거래량 z-score로 nodes/links를 조립한다."""
    nodes: list[Node] = []
    links: list[Link] = []

    sectors_seen: set[str] = set()
    universe_by_ticker = {u.ticker: u for u in universe}
    # ticker -> [(product, weight, "direct"|"proxy"), ...]
    ticker_links: dict[str, list[tuple[str, float, str]]] = {}

    for entry in keywords:
        z = 0.0 if keyword_no_signal.get(entry.product, True) else keyword_z.get(entry.product, 0.0)
        nodes.append(
            Node(
                id=entry.product,
                type="keyword",
                label=entry.product,
                z=z,
                sentiment=keyword_sentiment.get(entry.product, 0),
            )
        )

        sectors_seen.add(entry.sector)
        links.append(Link(source=entry.product, target=entry.sector, kind="sec"))

        for ticker in entry.direct:
            links.append(Link(source=entry.product, target=ticker, kind="direct"))
            ticker_links.setdefault(ticker, []).append((entry.product, entry.weight, "direct"))
        for ticker in entry.proxy:
            links.append(Link(source=entry.product, target=ticker, kind="proxy"))
            ticker_links.setdefault(ticker, []).append((entry.product, entry.weight, "proxy"))

    for sector in sorted(sectors_seen):
        nodes.append(Node(id=sector, type="sector", label=sector))

    for ticker, links_for_ticker in ticker_links.items():
        universe_entry = universe_by_ticker.get(ticker)
        if universe_entry is None:
            continue

        agg = sum(
            (0.0 if keyword_no_signal.get(kw, True) else keyword_z.get(kw, 0.0)) * weight
            for kw, weight, _sub in links_for_ticker
        )
        sub: StockSub = "direct" if any(s == "direct" for _, _, s in links_for_ticker) else "proxy"
        vz = volume_z.get(ticker, 0.0)
        status = _stock_status(agg, vz, threshold)

        nodes.append(
            Node(
                id=ticker,
                type="stock",
                label=universe_entry.name,
                sub=sub,
                ticker=ticker,
                sector=universe_entry.sector,
                agg=agg,
                volume_z=vz,
                status=status,
            )
        )
        links.append(Link(source=ticker, target=universe_entry.sector, kind="own"))

    for sector_a, sector_b in SECTOR_ADJACENCY:
        if sector_a in sectors_seen and sector_b in sectors_seen:
            links.append(Link(source=sector_a, target=sector_b, kind="adj"))

    return Snapshot(date=target_date, nodes=nodes, links=links)


def dump_snapshot(snapshot: Snapshot, out_dir: Path) -> Path:
    """`data/snapshot_<date>.json`으로 스냅샷을 덤프한다."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"snapshot_{snapshot.date.isoformat()}.json"
    out_path.write_text(
        json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out_path


def dump_debug_series(
    target_date: Date,
    raw_series: dict[str, pd.Series],
    z_series: dict[str, pd.Series],
    out_dir: Path,
) -> Path:
    """`debug/series_<date>.json`으로 키워드별 raw/z 시계열을 덤프한다.

    대시보드 Signals 탭 스파크라인 전용 산출물이라 `schema.Snapshot` 계약과는
    분리한다.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"series_{target_date.isoformat()}.json"

    payload: dict[str, dict[str, list]] = {}
    for keyword, raw in raw_series.items():
        z = z_series.get(keyword)
        payload[keyword] = {
            "dates": [ts.date().isoformat() for ts in raw.index],
            "raw": [float(v) for v in raw.to_numpy()],
            "z": [float(v) for v in z.to_numpy()] if z is not None else [],
        }

    out_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return out_path
