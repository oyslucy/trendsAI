from __future__ import annotations

import pandas as pd

from consumer_signal.recommend import (
    compute_persistence,
    has_enough_volume,
    recommendation_score,
)


def test_persistence_empty_series_is_zero() -> None:
    assert compute_persistence(pd.Series(dtype=float)) == 0.0


def test_persistence_all_days_above_threshold_is_one() -> None:
    series = pd.Series([2.0, 2.0, 2.0, 2.0, 2.0])
    assert compute_persistence(series, window=5, threshold=1.0) == 1.0


def test_persistence_single_day_blip_is_heavily_discounted() -> None:
    series = pd.Series([0.0, 0.0, 0.0, 0.0, 3.0])
    assert compute_persistence(series, window=5, threshold=1.0) == 0.2


def test_persistence_uses_only_trailing_window() -> None:
    series = pd.Series([5.0, 5.0, 0.0, 0.0, 0.0])  # 오래된 스파이크는 최근 창 밖
    assert compute_persistence(series, window=3, threshold=1.0) == 0.0


def test_has_enough_volume_false_for_empty_series() -> None:
    assert has_enough_volume(pd.Series(dtype=float)) is False


def test_has_enough_volume_false_below_floor() -> None:
    """후 비첩 실사례: raw가 0~4 사이만 움직이면 z가 커도 신뢰하면 안 된다."""
    series = pd.Series([0.0, 1.0, 2.0, 0.0, 4.0])
    assert has_enough_volume(series, min_peak=10.0) is False


def test_has_enough_volume_true_above_floor() -> None:
    series = pd.Series([15.0, 22.0, 89.0, 16.0, 78.0])
    assert has_enough_volume(series, min_peak=10.0) is True


def test_recommendation_score_zero_when_volume_insufficient() -> None:
    assert recommendation_score(3.0, 1.0, 1.0, enough_volume=False) == 0.0


def test_recommendation_score_zero_when_z_non_positive() -> None:
    assert recommendation_score(0.0, 1.0, 1.0, enough_volume=True) == 0.0
    assert recommendation_score(-2.0, 1.0, 1.0, enough_volume=True) == 0.0


def test_recommendation_score_multiplies_three_factors() -> None:
    score = recommendation_score(3.0, 0.5, 0.6, enough_volume=True)
    assert score == 3.0 * 0.5 * 0.6
