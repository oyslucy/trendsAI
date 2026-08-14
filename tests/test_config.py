from __future__ import annotations

import pytest

from consumer_signal.config import Settings, get_settings


def test_missing_secrets_raises_clear_error() -> None:
    with pytest.raises(RuntimeError, match="llm_api_key"):
        get_settings()


def test_settings_loads_from_env_with_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "key")

    settings = get_settings()

    assert isinstance(settings, Settings)
    assert settings.google_trends_geo == "KR"
    assert settings.db_url == "sqlite:///./data/signal.db"
    assert settings.z_window == 30
    assert settings.z_threshold == 2.0
    assert settings.log_level == "INFO"
