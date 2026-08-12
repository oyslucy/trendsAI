from __future__ import annotations

import pandas as pd

from consumer_signal.normalize import rolling_zscore


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
