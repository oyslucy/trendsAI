"""애플리케이션 설정. `.env`에서 로드하고 검증한다."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """환경 변수 기반 설정.

    필수 시크릿이 비어 있으면 pydantic이 `.env`에 무엇을 채워야 하는지
    필드명과 함께 검증 에러를 던진다.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    naver_client_id: str = Field(..., description="네이버 데이터랩 API client id")
    naver_client_secret: str = Field(..., description="네이버 데이터랩 API client secret")
    llm_api_key: str = Field(..., description="'왜' 요약에 쓰는 LLM API key")

    db_url: str = Field(
        default="sqlite:///./data/signal.db",
        description="SQLAlchemy 연결 문자열. Postgres 등으로 교체 가능.",
    )
    z_window: int = Field(default=30, description="z-score 이동창 길이(일)")
    z_threshold: float = Field(default=2.0, description="신호로 간주할 z-score 임계값")
    log_level: str = Field(default="INFO", description="로그 레벨")


def get_settings() -> Settings:
    """`.env` 누락 시 명확한 에러 메시지와 함께 Settings를 생성한다."""
    try:
        return Settings()  # type: ignore[call-arg]
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "필수 설정이 누락되었습니다. `.env.example`을 `.env`로 복사한 뒤 "
            "naver_client_id, naver_client_secret, llm_api_key 를 채워주세요.\n"
            f"원본 에러: {exc}"
        ) from exc
