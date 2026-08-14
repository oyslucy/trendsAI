from __future__ import annotations

from datetime import date

from dashboard.viewmodel import build_dashboard_viewmodel

from consumer_signal.dictionary.loader import KeywordEntry, UniverseEntry
from consumer_signal.schema import Link, Node, Snapshot


def _entry(
    product: str, direct: list[str] | None = None, proxy: list[str] | None = None
) -> KeywordEntry:
    return KeywordEntry(
        product=product,
        brand=f"{product}브랜드",
        sector="ramen_snack",
        direct=direct or [],
        proxy=proxy or [],
    )


def _universe(ticker: str, name: str) -> UniverseEntry:
    return UniverseEntry(ticker=ticker, name=name, sector="ramen_snack")


def test_signal_above_threshold_has_full_fields() -> None:
    entries = [_entry("불닭볶음면", direct=["003230"])]
    universe = [_universe("003230", "삼양식품")]
    snapshot = Snapshot(
        date=date(2026, 1, 1),
        nodes=[
            Node(
                id="불닭볶음면",
                type="keyword",
                label="불닭볶음면",
                z=3.0,
                sentiment=0,
                recommendation_score=1.5,
            ),
            Node(
                id="003230",
                type="stock",
                label="삼양식품",
                ticker="003230",
                agg=3.0,
                status="react",
            ),
        ],
        links=[Link(source="불닭볶음면", target="003230", kind="direct")],
    )
    vm = build_dashboard_viewmodel(
        "2026-01-01",
        "2026-01-01T00:00:00",
        snapshot,
        {},
        entries,
        universe,
        min_recommendation_score=0.3,
    )

    assert len(vm["signals"]) == 1
    assert vm["flat"] == []
    signal = vm["signals"][0]
    assert signal["product"] == "불닭볶음면"
    assert signal["company"] == "삼양식품"
    assert signal["ticker"] == "003230"
    assert signal["kind"] == "direct"
    assert signal["proxy_tickers"] == []
    assert signal["status"] == "react"
    assert signal["recommendation_score"] == 1.5
    assert signal["sentiment"] is None  # sentiment stub -> always null regardless of node value
    assert signal["sector"] == "식품·과자"


def test_below_threshold_goes_to_flat_with_reduced_shape() -> None:
    """z는 높아도 recommendation_score가 낮으면(절대 검색량 미달 등) flat으로 간다."""
    entries = [_entry("신라면", direct=["004370"])]
    universe = [_universe("004370", "농심")]
    snapshot = Snapshot(
        date=date(2026, 1, 1),
        nodes=[
            Node(
                id="신라면",
                type="keyword",
                label="신라면",
                z=3.8,
                sentiment=0,
                recommendation_score=0.0,
                low_confidence=True,
            )
        ],
        links=[Link(source="신라면", target="004370", kind="direct")],
    )
    vm = build_dashboard_viewmodel(
        "2026-01-01",
        "2026-01-01T00:00:00",
        snapshot,
        {},
        entries,
        universe,
        min_recommendation_score=0.3,
    )

    assert vm["signals"] == []
    assert len(vm["flat"]) == 1
    flat = vm["flat"][0]
    assert set(flat) == {
        "product",
        "brand",
        "company",
        "ticker",
        "z",
        "low_confidence",
        "sentiment",
    }
    assert flat["low_confidence"] is True


def test_proxy_only_entry_reports_full_fanout() -> None:
    entries = [_entry("PDRN", proxy=["192820", "161890", "257720"])]
    universe = [
        _universe("192820", "코스맥스"),
        _universe("161890", "한국콜마"),
        _universe("257720", "실리콘투"),
    ]
    snapshot = Snapshot(
        date=date(2026, 1, 1),
        nodes=[
            Node(
                id="PDRN",
                type="keyword",
                label="PDRN",
                z=2.0,
                sentiment=0,
                recommendation_score=0.8,
            ),
            Node(
                id="192820", type="stock", label="코스맥스", ticker="192820", agg=2.0, status=None
            ),
        ],
        links=[Link(source="PDRN", target="192820", kind="proxy")],
    )
    vm = build_dashboard_viewmodel(
        "2026-01-01",
        "2026-01-01T00:00:00",
        snapshot,
        {},
        entries,
        universe,
        min_recommendation_score=0.3,
    )

    signal = vm["signals"][0]
    assert signal["kind"] == "proxy"
    assert signal["ticker"] == "192820"
    assert signal["proxy_tickers"] == ["192820", "161890", "257720"]
    assert signal["company"] == "코스맥스"


def test_missing_stock_status_falls_back_to_lead() -> None:
    """KRX 거래량이 미배선/전부 0이면 stock.status가 None으로 나온다 — lead로 폴백해야 함."""
    entries = [_entry("초코파이", direct=["271560"])]
    universe = [_universe("271560", "오리온")]
    snapshot = Snapshot(
        date=date(2026, 1, 1),
        nodes=[
            Node(
                id="초코파이",
                type="keyword",
                label="초코파이",
                z=1.5,
                sentiment=0,
                recommendation_score=0.6,
            ),
            Node(id="271560", type="stock", label="오리온", ticker="271560", agg=1.5, status=None),
        ],
        links=[Link(source="초코파이", target="271560", kind="direct")],
    )
    vm = build_dashboard_viewmodel(
        "2026-01-01",
        "2026-01-01T00:00:00",
        snapshot,
        {},
        entries,
        universe,
        min_recommendation_score=0.3,
    )

    assert vm["signals"][0]["status"] == "lead"


def test_series_is_trailing_slice_from_debug_dump() -> None:
    entries = [_entry("동원참치", direct=["049770"])]
    universe = [_universe("049770", "동원F&B")]
    snapshot = Snapshot(
        date=date(2026, 1, 1),
        nodes=[
            Node(
                id="동원참치",
                type="keyword",
                label="동원참치",
                z=3.0,
                sentiment=0,
                recommendation_score=1.2,
            )
        ],
        links=[Link(source="동원참치", target="049770", kind="direct")],
    )
    long_series = list(range(50))
    series_debug = {"동원참치": {"dates": [], "raw": long_series, "z": []}}
    vm = build_dashboard_viewmodel(
        "2026-01-01",
        "2026-01-01T00:00:00",
        snapshot,
        series_debug,
        entries,
        universe,
        min_recommendation_score=0.3,
    )

    assert vm["signals"][0]["series"] == long_series[-30:]


def test_stocks_excludes_non_positive_agg_and_sorts_desc() -> None:
    entries = [
        _entry("A", direct=["111"]),
        _entry("B", direct=["222"]),
        _entry("C", direct=["333"]),
    ]
    universe = [_universe("111", "회사A"), _universe("222", "회사B"), _universe("333", "회사C")]
    snapshot = Snapshot(
        date=date(2026, 1, 1),
        nodes=[
            Node(id="A", type="keyword", label="A", z=1.0, recommendation_score=0.4),
            Node(id="B", type="keyword", label="B", z=2.0, recommendation_score=0.9),
            Node(id="C", type="keyword", label="C", z=-1.0, recommendation_score=0.0),
            Node(id="111", type="stock", label="회사A", ticker="111", agg=1.0, status="lead"),
            Node(id="222", type="stock", label="회사B", ticker="222", agg=2.0, status="react"),
            Node(id="333", type="stock", label="회사C", ticker="333", agg=-1.0, status=None),
        ],
        links=[
            Link(source="A", target="111", kind="direct"),
            Link(source="B", target="222", kind="direct"),
            Link(source="C", target="333", kind="direct"),
        ],
    )
    vm = build_dashboard_viewmodel(
        "2026-01-01",
        "2026-01-01T00:00:00",
        snapshot,
        {},
        entries,
        universe,
        min_recommendation_score=0.3,
    )

    tickers = [s["ticker"] for s in vm["stocks"]]
    assert tickers == ["222", "111"]  # 333 excluded (agg <= 0), sorted by agg desc
    assert vm["stocks"][0]["feed"] == ["B"]


def test_signals_sorted_by_recommendation_score_not_raw_z() -> None:
    """z가 더 높아도 recommendation_score가 낮으면 순위에서 밀려야 한다."""
    entries = [
        _entry("노이즈", direct=["111"]),
        _entry("진짜신호", direct=["222"]),
    ]
    universe = [_universe("111", "회사A"), _universe("222", "회사B")]
    snapshot = Snapshot(
        date=date(2026, 1, 1),
        nodes=[
            # z는 더 크지만(절대 검색량 미달 등으로) 추천 점수는 낮음
            Node(
                id="노이즈",
                type="keyword",
                label="노이즈",
                z=3.8,
                recommendation_score=0.4,
            ),
            Node(
                id="진짜신호",
                type="keyword",
                label="진짜신호",
                z=2.0,
                recommendation_score=1.2,
            ),
        ],
        links=[
            Link(source="노이즈", target="111", kind="direct"),
            Link(source="진짜신호", target="222", kind="direct"),
        ],
    )
    vm = build_dashboard_viewmodel(
        "2026-01-01",
        "2026-01-01T00:00:00",
        snapshot,
        {},
        entries,
        universe,
        min_recommendation_score=0.3,
    )

    assert [s["product"] for s in vm["signals"]] == ["진짜신호", "노이즈"]
