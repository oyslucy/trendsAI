"""추천 신호가 실제로 시장 반응으로 이어졌는지 나중에 확인한다.

매일 파이프라인이 `data/snapshot_<date>.json`을 남기는 것 자체가 이미 로그다
— 새로 뭘 기록할 필요 없이, 과거 스냅샷과 그로부터 N일 뒤 스냅샷을 비교하기만
하면 "이 추천이 맞았는지"를 확인할 수 있다. 이 결과가 쌓여야 나중에(로드맵
6장) 유의성 검증·ML 라벨링이 가능해진다 — 지금은 그 축적을 위한 조회
함수까지만 만든다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date as Date
from datetime import timedelta
from pathlib import Path

from consumer_signal.schema import Node, Snapshot, StockStatus
from consumer_signal.snapshot import load_snapshot


@dataclass
class Outcome:
    """`from_date`에 추천됐던 신호 하나가 `to_date` 시점엔 어땠는지."""

    product: str
    ticker: str | None
    company: str | None
    recommended_score: float
    z_then: float
    z_now: float | None
    status_then: StockStatus | None
    agg_then: float | None
    status_now: StockStatus | None
    agg_now: float | None
    reacted: bool  # then엔 react가 아니었는데 now엔 react가 됐는가
    pending: bool  # to_date 스냅샷이 아직 없어(미래) 판단 불가


def _keyword_nodes(snapshot: Snapshot) -> dict[str, Node]:
    return {n.id: n for n in snapshot.nodes if n.type == "keyword"}


def _stock_nodes_by_ticker(snapshot: Snapshot) -> dict[str, Node]:
    return {n.ticker: n for n in snapshot.nodes if n.type == "stock" and n.ticker is not None}


def _primary_ticker_by_product(snapshot: Snapshot) -> dict[str, str]:
    """product -> 대표 티커. direct 링크가 있으면 direct, 없으면 첫 proxy."""
    proxy: dict[str, str] = {}
    direct: dict[str, str] = {}
    for link in snapshot.links:
        if link.kind == "direct" and link.source not in direct:
            direct[link.source] = link.target
        elif link.kind == "proxy" and link.source not in proxy:
            proxy[link.source] = link.target
    return {**proxy, **direct}


def evaluate_outcomes(from_date: Date, horizon_days: int, data_dir: Path) -> list[Outcome]:
    """`from_date`에 추천 점수>0이었던 신호들이 `from_date+horizon_days` 시점엔
    어떻게 됐는지 비교한다. 그 시점 스냅샷이 아직 없으면 `pending=True`로 반환한다
    (미래를 기다려야 하는 경우와 실제로 반응이 없었던 경우를 구분하기 위함).
    """
    then = load_snapshot(from_date, data_dir)
    if then is None:
        raise ValueError(f"no snapshot for {from_date}")

    to_date = from_date + timedelta(days=horizon_days)
    now = load_snapshot(to_date, data_dir)
    pending = now is None

    then_keywords = _keyword_nodes(then)
    then_stocks = _stock_nodes_by_ticker(then)
    ticker_by_product = _primary_ticker_by_product(then)
    now_keywords = _keyword_nodes(now) if now else {}
    now_stocks = _stock_nodes_by_ticker(now) if now else {}

    outcomes: list[Outcome] = []
    for product, node in then_keywords.items():
        score = node.recommendation_score or 0.0
        if score <= 0:
            continue

        ticker = ticker_by_product.get(product)
        stock_then = then_stocks.get(ticker) if ticker else None
        stock_now = now_stocks.get(ticker) if ticker else None
        keyword_now = now_keywords.get(product)

        reacted = bool(
            not pending
            and stock_now is not None
            and stock_now.status == "react"
            and (stock_then is None or stock_then.status != "react")
        )

        outcomes.append(
            Outcome(
                product=product,
                ticker=ticker,
                company=stock_then.label if stock_then else None,
                recommended_score=round(score, 3),
                z_then=round(node.z or 0.0, 3),
                z_now=(
                    round(keyword_now.z, 3) if keyword_now and keyword_now.z is not None else None
                ),
                status_then=stock_then.status if stock_then else None,
                agg_then=(
                    round(stock_then.agg, 3) if stock_then and stock_then.agg is not None else None
                ),
                status_now=stock_now.status if stock_now else None,
                agg_now=(
                    round(stock_now.agg, 3) if stock_now and stock_now.agg is not None else None
                ),
                reacted=reacted,
                pending=pending,
            )
        )

    outcomes.sort(key=lambda o: o.recommended_score, reverse=True)
    return outcomes
