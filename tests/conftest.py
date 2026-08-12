from __future__ import annotations

from pathlib import Path

import pytest

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture
def data_dir() -> Path:
    return DATA_DIR


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """실제 셸 환경변수·`.env`가 테스트에 새어들지 않도록 격리한다."""
    for key in ("NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET", "LLM_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)
