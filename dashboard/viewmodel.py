"""인사이트 대시보드 뷰모델 투영.

파이프라인이 이미 계산해서 저장해둔 산출물(snapshot.json의 z/agg/status,
debug/series_<date>.json의 트레일링 시계열, keyword_map.yaml의 엔티티 메타데이터)을
그대로 읽어 프론트가 바로 렌더할 수 있는 JSON 하나로 조립한다. z-score나 agg를
여기서 다시 계산하지 않는다 — 순수 조인/투영 레이어다.
"""

from __future__ import annotations

from consumer_signal.dictionary.loader import KeywordEntry, UniverseEntry
from consumer_signal.schema import Snapshot

# 파이프라인 sector 코드 -> 대시보드 표기용 한글 라벨. 표시 전용이며 데이터 의미는 바꾸지 않는다.
SECTOR_LABELS: dict[str, str] = {
    "ramen_snack": "식품·과자",
    "dairy_beverage": "유제품·음료",
    "alcohol_beverage": "주류",
    "bakery": "베이커리",
    "retail": "유통",
    "cosmetics": "화장품",
}

SERIES_POINTS = 30  # 스파크라인에 쓸 트레일링 포인트 수
FEED_TOP_N = 3  # 리더보드 각 종목의 "← 이 제품들 때문" 표기 상위 개수


def _sector_label(sector: str) -> str:
    return SECTOR_LABELS.get(sector, sector)


def _kind_and_tickers(entry: KeywordEntry) -> tuple[str, list[str]]:
    """(kind, 대표+팬아웃 티커 목록). direct가 있으면 direct, 없으면 proxy 전체."""
    if entry.direct:
        return "direct", entry.direct
    if entry.proxy:
        return "proxy", entry.proxy
    return "direct", []


def build_dashboard_viewmodel(
    target_date: str,
    generated_at: str,
    snapshot: Snapshot,
    series_debug: dict[str, dict[str, list]],
    keywords: list[KeywordEntry],
    universe: list[UniverseEntry],
    *,
    min_recommendation_score: float = 0.3,
) -> dict:
    """Signal/flat/stocks 뷰모델을 조립한다. 계약은 세션 노트의 §2 참고.

    signals/flat 분할은 raw z가 아니라 `recommend.py`가 계산한
    recommendation_score(z×지속성×엔티티가중치, 절대검색량 미달이면 0)로 한다 —
    raw z만 보면 "후 비첩"처럼 절대 검색량이 0~4인 노이즈가 z=3.8로 최상단에
    뜨는 문제가 생긴다.
    """
    universe_by_ticker = {u.ticker: u for u in universe}
    keyword_node_by_id = {n.id: n for n in snapshot.nodes if n.type == "keyword"}
    stock_node_by_ticker = {
        n.ticker: n for n in snapshot.nodes if n.type == "stock" and n.ticker is not None
    }
    score_by_product = {n.id: (n.recommendation_score or 0.0) for n in keyword_node_by_id.values()}

    signals: list[dict] = []
    flat: list[dict] = []

    for entry in keywords:
        node = keyword_node_by_id.get(entry.product)
        if node is None:
            continue

        z = node.z or 0.0
        score = node.recommendation_score or 0.0
        kind, tickers = _kind_and_tickers(entry)
        ticker = tickers[0] if tickers else None
        company = (
            universe_by_ticker[ticker].name if ticker and ticker in universe_by_ticker else None
        )

        if score >= min_recommendation_score:
            stock_node = stock_node_by_ticker.get(ticker) if ticker else None
            # 거래량(KRX) 미배선/전부 0이면 stock.status가 None으로 나온다 —
            # 검색은 떴지만 시장 반응은 아직 미확인이라는 뜻이므로 lead로 폴백한다.
            status = (stock_node.status if stock_node else None) or "lead"
            series = series_debug.get(entry.product, {}).get("raw", [])[-SERIES_POINTS:]
            signals.append(
                {
                    "product": entry.product,
                    "brand": entry.brand,
                    "company": company,
                    "ticker": ticker,
                    "z": round(z, 3),
                    "recommendation_score": round(score, 3),
                    "status": status,
                    "kind": kind,
                    "proxy_tickers": tickers if kind == "proxy" else [],
                    "sector": _sector_label(entry.sector),
                    "sentiment": None,  # sentiment.py가 아직 stub(항상 중립)이라 가짜값 대신 null
                    "why": node.why,  # narrator 미구현 — 항상 None
                    "series": series,
                }
            )
        else:
            flat.append(
                {
                    "product": entry.product,
                    "brand": entry.brand,
                    "company": company,
                    "ticker": ticker,
                    "z": round(z, 3),
                    "low_confidence": bool(node.low_confidence),
                    "sentiment": None,
                }
            )

    signals.sort(key=lambda s: s["recommendation_score"], reverse=True)
    flat.sort(key=lambda s: s["z"], reverse=True)

    # 리더보드 feed: 그 종목으로 이어지는 direct/proxy 링크 소스(product)를
    # recommendation_score 내림차순 상위 N개 — 노이즈성 기여보다 신뢰할 만한
    # 기여를 먼저 보여준다.
    feed_by_ticker: dict[str, list[str]] = {}
    for link in snapshot.links:
        if link.kind not in ("direct", "proxy"):
            continue
        feed_by_ticker.setdefault(link.target, []).append(link.source)

    stocks: list[dict] = []
    for node in snapshot.nodes:
        if node.type != "stock" or node.ticker is None or not node.agg or node.agg <= 0:
            continue
        products = sorted(
            feed_by_ticker.get(node.ticker, []),
            key=lambda p: score_by_product.get(p, 0.0),
            reverse=True,
        )[:FEED_TOP_N]
        stocks.append(
            {
                "company": node.label,
                "ticker": node.ticker,
                "agg": round(node.agg, 3),
                "status": node.status or "lead",
                "feed": products,
            }
        )
    stocks.sort(key=lambda s: s["agg"], reverse=True)

    return {
        "date": target_date,
        "generated_at": generated_at,
        "signals": signals,
        "flat": flat,
        "stocks": stocks,
    }
