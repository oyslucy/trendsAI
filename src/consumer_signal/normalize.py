"""이동창 z-score 정규화."""

from __future__ import annotations

import pandas as pd

WINSOR_LIMIT = 5.0


def rolling_zscore(series: pd.Series, window: int) -> pd.Series:
    """`series`의 마지막 값을 기준으로 이동창 z-score를 계산한다.

    표준편차가 0이면(데이터 부족·무변동) 0.0을 반환한다.
    """
    rolling = series.rolling(window=window, min_periods=1)
    mean = rolling.mean()
    std = rolling.std(ddof=0)
    z = (series - mean) / std
    return z.fillna(0.0)


def winsorize(series: pd.Series, limit: float = WINSOR_LIMIT) -> pd.Series:
    """`series`를 [-limit, limit] 범위로 클립한다."""
    return series.clip(lower=-limit, upper=limit)


def is_no_signal(series: pd.Series) -> bool:
    """시계열이 비어있거나 전부 0이면 저검색 키워드로 간주한다."""
    return series.empty or bool((series == 0).all())


def latest_zscore(series: pd.Series, window: int, *, limit: float = WINSOR_LIMIT) -> float:
    """`series`의 마지막 값 기준 이동창 z-score를 winsorize해서 반환한다."""
    if series.empty:
        return 0.0
    z = winsorize(rolling_zscore(series, window), limit=limit)
    return float(z.iloc[-1])


def stock_aggregate(entry_z: dict[str, float], links: list[tuple[str, float]]) -> float:
    """연결된 키워드 z × weight 합.

    `links`는 `[(keyword, weight), ...]`. `entry_z`에 없는 키워드는 0으로 취급한다.
    """
    return sum(entry_z.get(keyword, 0.0) * weight for keyword, weight in links)
