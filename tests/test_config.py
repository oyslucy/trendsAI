from __future__ import annotations

import pytest

from consumer_signal.config import Settings, get_settings


def test_missing_secrets_raises_clear_error() -> None:
    with pytest.raises(RuntimeError, match="naver_client_id"):
        get_settings()


def test_settings_loads_from_env_with_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NAVER_CLIENT_ID", "id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "secret")
    monkeypatch.setenv("LLM_API_KEY", "key")

    settings = get_settings()

    assert isinstance(settings, Settings)
    assert settings.db_url == "sqlite:///./data/signal.db"
    assert settings.z_window == 30
    assert settings.z_threshold == 2.0
    assert settings.log_level == "INFO"
