"""키워드 맵의 티커가 유니버스에 실재하는지 검증."""

from __future__ import annotations

from consumer_signal.dictionary.loader import KeywordEntry, UniverseEntry


class DictionaryValidationError(Exception):
    pass


def validate_keyword_map(keywords: list[KeywordEntry], universe: list[UniverseEntry]) -> list[str]:
    """검증하고 경고 목록(예: unmapped 키워드)을 반환한다.

    실재하지 않는 티커를 참조하면 즉시 raise한다.
    """
    known_tickers = {u.ticker for u in universe}
    warnings: list[str] = []

    for entry in keywords:
        if not entry.direct and not entry.proxy:
            warnings.append(f"unmapped: '{entry.product}' has no direct/proxy tickers")
            continue

        for ticker in [*entry.direct, *entry.proxy]:
            if ticker not in known_tickers:
                raise DictionaryValidationError(
                    f"'{entry.product}' references unknown ticker '{ticker}' "
                    "not present in universe.csv"
                )

    return warnings
