from __future__ import annotations

from datetime import date

from consumer_signal.dictionary.loader import KeywordEntry, UniverseEntry
from consumer_signal.snapshot import build_snapshot


def _keyword(ticker: str = "003230") -> KeywordEntry:
    return KeywordEntry(
        product="불닭볶음면",
        brand="삼양식품",
        sector="ramen_snack",
        direct=[ticker],
        proxy=[],
    )


def _universe(ticker: str = "003230") -> list[UniverseEntry]:
    return [UniverseEntry(ticker=ticker, name="삼양식품", sector="ramen_snack")]


def test_lead_status_when_search_up_and_volume_still_low() -> None:
    snapshot = build_snapshot(
        date(2026, 1, 1),
        [_keyword()],
        _universe(),
        keyword_z={"불닭볶음면": 3.0},
        keyword_sentiment={"불닭볶음면": 0},
        keyword_no_signal={"불닭볶음면": False},
        volume_z={"003230": 0.5},
        threshold=2.0,
    )
    stock = next(n for n in snapshot.nodes if n.type == "stock")
    assert stock.status == "lead"
    assert stock.agg == 3.0
    assert stock.volume_z == 0.5


def test_react_status_when_search_and_volume_both_up() -> None:
    snapshot = build_snapshot(
        date(2026, 1, 1),
        [_keyword()],
        _universe(),
        keyword_z={"불닭볶음면": 3.0},
        keyword_sentiment={"불닭볶음면": 0},
        keyword_no_signal={"불닭볶음면": False},
        volume_z={"003230": 2.5},
        threshold=2.0,
    )
    stock = next(n for n in snapshot.nodes if n.type == "stock")
    assert stock.status == "react"


def test_no_status_when_search_below_threshold() -> None:
    snapshot = build_snapshot(
        date(2026, 1, 1),
        [_keyword()],
        _universe(),
        keyword_z={"불닭볶음면": 0.1},
        keyword_sentiment={"불닭볶음면": 0},
        keyword_no_signal={"불닭볶음면": False},
        volume_z={"003230": 5.0},
        threshold=2.0,
    )
    stock = next(n for n in snapshot.nodes if n.type == "stock")
    assert stock.status is None


def test_no_signal_keyword_is_zeroed_in_node_and_agg() -> None:
    snapshot = build_snapshot(
        date(2026, 1, 1),
        [_keyword()],
        _universe(),
        keyword_z={"불닭볶음면": 999.0},
        keyword_sentiment={"불닭볶음면": 0},
        keyword_no_signal={"불닭볶음면": True},
        volume_z={},
        threshold=2.0,
    )
    keyword_node = next(n for n in snapshot.nodes if n.type == "keyword")
    stock_node = next(n for n in snapshot.nodes if n.type == "stock")
    assert keyword_node.z == 0.0
    assert stock_node.agg == 0.0


def test_links_cover_direct_sec_own_kinds() -> None:
    snapshot = build_snapshot(
        date(2026, 1, 1),
        [_keyword()],
        _universe(),
        keyword_z={"불닭볶음면": 1.0},
        keyword_sentiment={"불닭볶음면": 0},
        keyword_no_signal={"불닭볶음면": False},
        volume_z={"003230": 0.0},
        threshold=2.0,
    )
    kinds = {link.kind for link in snapshot.links}
    assert {"direct", "sec", "own"} <= kinds


def test_proxy_only_ticker_gets_proxy_sub() -> None:
    keyword = KeywordEntry(
        product="편의점 신상",
        brand="",
        sector="retail",
        direct=[],
        proxy=["007070"],
        brand_to_company=0.5,
    )
    universe = [UniverseEntry(ticker="007070", name="GS리테일", sector="retail")]
    snapshot = build_snapshot(
        date(2026, 1, 1),
        [keyword],
        universe,
        keyword_z={"편의점 신상": 3.0},
        keyword_sentiment={"편의점 신상": 0},
        keyword_no_signal={"편의점 신상": False},
        volume_z={"007070": 0.0},
        threshold=2.0,
    )
    stock = next(n for n in snapshot.nodes if n.type == "stock")
    assert stock.sub == "proxy"
