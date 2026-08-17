from __future__ import annotations

from datetime import date

import pytest

from consumer_signal.backtest import evaluate_outcomes
from consumer_signal.schema import Link, Node, Snapshot
from consumer_signal.snapshot import dump_snapshot

FROM_DATE = date(2026, 1, 1)
TO_DATE = date(2026, 1, 4)  # horizon_days=3


def _dump(tmp_path, target_date, nodes, links):
    snapshot = Snapshot(date=target_date, nodes=nodes, links=links)
    dump_snapshot(snapshot, tmp_path)


def test_raises_when_from_date_snapshot_missing(tmp_path) -> None:
    with pytest.raises(ValueError, match=str(FROM_DATE)):
        evaluate_outcomes(FROM_DATE, 3, tmp_path)


def test_pending_when_to_date_snapshot_missing(tmp_path) -> None:
    _dump(
        tmp_path,
        FROM_DATE,
        nodes=[
            Node(
                id="불닭볶음면", type="keyword", label="불닭볶음면", z=3.0, recommendation_score=1.2
            ),
            Node(
                id="003230", type="stock", label="삼양식품", ticker="003230", agg=1.2, status="lead"
            ),
        ],
        links=[Link(source="불닭볶음면", target="003230", kind="direct")],
    )
    outcomes = evaluate_outcomes(FROM_DATE, 3, tmp_path)

    assert len(outcomes) == 1
    assert outcomes[0].pending is True
    assert outcomes[0].reacted is False
    assert outcomes[0].status_now is None


def test_reacted_true_when_status_moves_to_react(tmp_path) -> None:
    _dump(
        tmp_path,
        FROM_DATE,
        nodes=[
            Node(id="동원참치", type="keyword", label="동원참치", z=3.0, recommendation_score=1.5),
            Node(
                id="049770", type="stock", label="동원F&B", ticker="049770", agg=1.5, status="lead"
            ),
        ],
        links=[Link(source="동원참치", target="049770", kind="direct")],
    )
    _dump(
        tmp_path,
        TO_DATE,
        nodes=[
            Node(id="동원참치", type="keyword", label="동원참치", z=1.0, recommendation_score=0.0),
            Node(
                id="049770", type="stock", label="동원F&B", ticker="049770", agg=2.5, status="react"
            ),
        ],
        links=[Link(source="동원참치", target="049770", kind="direct")],
    )

    outcomes = evaluate_outcomes(FROM_DATE, 3, tmp_path)

    assert len(outcomes) == 1
    o = outcomes[0]
    assert o.pending is False
    assert o.reacted is True
    assert o.status_then == "lead"
    assert o.status_now == "react"
    assert o.agg_now == 2.5
    assert o.z_now == 1.0


def test_reacted_false_when_already_react_before(tmp_path) -> None:
    """이미 react였으면 나중에도 react라고 '새로 반응했다'고 치지 않는다."""
    _dump(
        tmp_path,
        FROM_DATE,
        nodes=[
            Node(id="참이슬", type="keyword", label="참이슬", z=2.0, recommendation_score=1.0),
            Node(
                id="000080",
                type="stock",
                label="하이트진로",
                ticker="000080",
                agg=2.0,
                status="react",
            ),
        ],
        links=[Link(source="참이슬", target="000080", kind="direct")],
    )
    _dump(
        tmp_path,
        TO_DATE,
        nodes=[
            Node(id="참이슬", type="keyword", label="참이슬", z=2.0, recommendation_score=1.0),
            Node(
                id="000080",
                type="stock",
                label="하이트진로",
                ticker="000080",
                agg=2.0,
                status="react",
            ),
        ],
        links=[Link(source="참이슬", target="000080", kind="direct")],
    )

    outcomes = evaluate_outcomes(FROM_DATE, 3, tmp_path)
    assert outcomes[0].reacted is False


def test_excludes_zero_score_entries(tmp_path) -> None:
    _dump(
        tmp_path,
        FROM_DATE,
        nodes=[
            Node(id="후 비첩", type="keyword", label="후 비첩", z=3.8, recommendation_score=0.0),
        ],
        links=[],
    )
    outcomes = evaluate_outcomes(FROM_DATE, 3, tmp_path)
    assert outcomes == []


def test_sorted_by_recommended_score_desc(tmp_path) -> None:
    _dump(
        tmp_path,
        FROM_DATE,
        nodes=[
            Node(id="약한신호", type="keyword", label="약한신호", z=1.0, recommendation_score=0.3),
            Node(id="강한신호", type="keyword", label="강한신호", z=3.0, recommendation_score=1.8),
        ],
        links=[],
    )
    outcomes = evaluate_outcomes(FROM_DATE, 3, tmp_path)
    assert [o.product for o in outcomes] == ["강한신호", "약한신호"]
