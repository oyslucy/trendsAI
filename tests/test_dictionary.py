from __future__ import annotations

from pathlib import Path

import pytest

from consumer_signal.dictionary.loader import (
    KeywordEntry,
    UniverseEntry,
    load_keyword_map,
    load_universe,
)
from consumer_signal.dictionary.validator import (
    DictionaryValidationError,
    validate_keyword_map,
)


def test_load_seed_keyword_map(data_dir: Path) -> None:
    keywords = load_keyword_map(data_dir / "keyword_map.yaml")
    assert len(keywords) >= 20
    assert all(isinstance(k, KeywordEntry) for k in keywords)


def test_load_seed_universe(data_dir: Path) -> None:
    universe = load_universe(data_dir / "universe.csv")
    assert len(universe) >= 20
    assert all(isinstance(u, UniverseEntry) for u in universe)


def test_seed_data_validates_without_error(data_dir: Path) -> None:
    keywords = load_keyword_map(data_dir / "keyword_map.yaml")
    universe = load_universe(data_dir / "universe.csv")
    warnings = validate_keyword_map(keywords, universe)
    assert warnings == []


def test_unknown_ticker_raises() -> None:
    keywords = [KeywordEntry(keyword="k", brand="b", sector="s", direct=["999999"], proxy=[])]
    universe = [UniverseEntry(ticker="003230", name="삼양식품", sector="ramen_snack")]
    with pytest.raises(DictionaryValidationError, match="999999"):
        validate_keyword_map(keywords, universe)


def test_unmapped_keyword_warns() -> None:
    keywords = [KeywordEntry(keyword="k", brand="b", sector="s", direct=[], proxy=[])]
    warnings = validate_keyword_map(keywords, universe=[])
    assert any("unmapped" in w for w in warnings)
