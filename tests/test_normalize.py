from __future__ import annotations

import pandas as pd

from consumer_signal.normalize import (
    is_no_signal,
    latest_zscore,
    rolling_zscore,
    stock_aggregate,
    winsorize,
)


def test_constant_series_has_zero_zscore() -> None:
    series = pd.Series([5.0] * 10)
    z = rolling_zscore(series, window=5)
    assert (z == 0.0).all()


def test_spike_produces_positive_zscore() -> None:
    series = pd.Series([1.0] * 29 + [100.0])
    z = rolling_zscore(series, window=30)
    assert z.iloc[-1] > 2.0


def test_output_length_matches_input() -> None:
    series = pd.Series(range(50), dtype=float)
    z = rolling_zscore(series, window=10)
    assert len(z) == len(series)


def test_zscore_invariant_to_positive_scaling() -> None:
    """데이터랩 ratio는 상대지수라 요청마다 스케일이 다를 수 있다.

    전 구간이 같은 양의 상수로 스케일되면(같은 요청 안에서는 항상 그렇다)
    평균·표준편차도 같은 비율로 스케일되어 z는 상쇄되어 동일해야 한다.
    이 회귀 테스트가 깨지면 collect/google_trends.py의 "요청당 한 번" 규칙이
    무의미해진다.
    """
    series = pd.Series([1.0, 2.0, 1.0, 3.0, 1.0, 1.0, 50.0])
    scaled = series * 4.2

    z = rolling_zscore(series, window=5)
    z_scaled = rolling_zscore(scaled, window=5)

    pd.testing.assert_series_equal(z, z_scaled, check_exact=False, atol=1e-9)


def test_winsorize_clips_extremes() -> None:
    series = pd.Series([-100.0, -1.0, 0.0, 1.0, 100.0])
    clipped = winsorize(series, limit=5.0)
    assert clipped.min() == -5.0
    assert clipped.max() == 5.0


def test_latest_zscore_winsorized() -> None:
    series = pd.Series([1.0] * 29 + [10_000.0])
    z = latest_zscore(series, window=30)
    assert z == 5.0


def test_latest_zscore_empty_series_is_zero() -> None:
    assert latest_zscore(pd.Series(dtype=float), window=30) == 0.0


def test_is_no_signal_for_all_zero_series() -> None:
    assert is_no_signal(pd.Series([0.0, 0.0, 0.0]))
    assert is_no_signal(pd.Series(dtype=float))
    assert not is_no_signal(pd.Series([0.0, 1.0, 0.0]))


def test_stock_aggregate_sums_weighted_z() -> None:
    entry_z = {"불닭볶음면": 2.0, "신라면": -1.0}
    links = [("불닭볶음면", 1.0), ("신라면", 0.5), ("모르는키워드", 3.0)]
    assert stock_aggregate(entry_z, links) == 2.0 * 1.0 + -1.0 * 0.5 + 0.0 * 3.0
