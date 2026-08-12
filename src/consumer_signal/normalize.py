"""이동창 z-score 정규화."""

from __future__ import annotations

import pandas as pd


def rolling_zscore(series: pd.Series, window: int) -> pd.Series:
    """`series`의 마지막 값을 기준으로 이동창 z-score를 계산한다.

    표준편차가 0이면(데이터 부족·무변동) 0.0을 반환한다.
    """
    rolling = series.rolling(window=window, min_periods=1)
    mean = rolling.mean()
    std = rolling.std(ddof=0)
    z = (series - mean) / std
    return z.fillna(0.0)
