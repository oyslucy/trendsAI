"""추천 점수 — z-score만으로는 "볼만한 신호"를 못 거른다.

절대 검색량이 작은 키워드는 raw가 0→4처럼만 움직여도 z가 3~5까지 튀는데,
이건 신호가 아니라 노이즈다(구글 트렌드가 그 정도 표본으로는 안정적인 평균·
표준편차를 못 준다). 반대로 하루만 튀고 마는 것도 지속되는 관심이 아니라
일회성 이벤트일 가능성이 높다.

이 모듈은 세 가지를 곱해서 하나의 점수로 합친다:
  z-score(평소 대비 튀었나) × 지속성(며칠째 튀고 있나) × 엔티티 가중치(회사
  신호로서 얼마나 무게 있나). 절대 검색량이 최소 기준 밑이면 점수를 아예
  0으로 만든다(low_confidence) — 대신 곱하지 않는 이유는 "덜 신뢰"가 아니라
  "신뢰할 근거 자체가 없음"이기 때문이다.
"""

from __future__ import annotations

import pandas as pd

PERSISTENCE_WINDOW = 5  # 최근 며칠을 볼지
PERSISTENCE_Z_THRESHOLD = 1.0  # 이 z 이상인 날만 "튄 날"로 센다
MIN_PEAK_VOLUME = 10.0  # 최근 구간 raw 최댓값이 이 밑이면 신뢰 안 함 (0~100 척도)


def compute_persistence(
    z_series: pd.Series,
    *,
    window: int = PERSISTENCE_WINDOW,
    threshold: float = PERSISTENCE_Z_THRESHOLD,
) -> float:
    """최근 `window`일 중 z가 `threshold` 이상인 날의 비율 (0~1).

    하루만 튀면 1/window로 크게 할인되고, window일 내내 튀면 1.0이 된다.
    """
    if z_series.empty:
        return 0.0
    recent = z_series.tail(window)
    return float((recent >= threshold).sum()) / len(recent)


def has_enough_volume(raw_series: pd.Series, *, min_peak: float = MIN_PEAK_VOLUME) -> bool:
    """최근 구간에 절대 검색량이 신뢰할 만큼 있었는지."""
    if raw_series.empty:
        return False
    return float(raw_series.max()) >= min_peak


def recommendation_score(
    latest_z: float,
    weight: float,
    persistence: float,
    *,
    enough_volume: bool,
) -> float:
    """z × weight × persistence. 절대 검색량 기준 미달이거나 z가 음수면 0."""
    if not enough_volume or latest_z <= 0:
        return 0.0
    return latest_z * weight * persistence
