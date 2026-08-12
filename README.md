# consumer-signal

네이버 데이터랩 검색어트렌드와 KRX 거래 데이터를 결합해 소비재 종목의 검색 신호 스냅샷을 만드는 파이프라인.

## 시작하기

```bash
uv sync
cp .env.example .env   # 아래 안내대로 값 채우기
uv run pre-commit install
```

### 네이버 API 키 발급

1. [네이버 개발자 센터](https://developers.naver.com)에 로그인 후 애플리케이션을 등록한다.
2. 사용 API에 "데이터랩(검색어트렌드)"를 추가한다.
3. 발급된 Client ID/Secret을 `.env`의 `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`에 넣는다.
4. `LLM_API_KEY`에는 '왜' 요약 생성에 쓸 LLM API 키를 넣는다.

`.env`가 없거나 필수 값이 비어 있으면 실행 시 무엇을 채워야 하는지 알려주는 에러가 뜬다.

## 실행

```bash
uv run consumer-signal --date 2026-08-12
# 또는
make run DATE=2026-08-12
```

`data/snapshot_<date>.json`이 생성되고, 같은 스냅샷이 DB(`data/signal.db` 기본)에 upsert된다.

## 사전(dictionary) 채우기

- `data/keyword_map.yaml`: 검색어 → 브랜드/종목 매핑. `keyword, brand, sector, direct[], proxy[], weight` 스키마.
- `data/universe.csv`: 매핑 대상 종목 유니버스(`ticker,name,sector`).

`keyword_map.yaml`의 모든 `direct`/`proxy` 티커는 `universe.csv`에 존재해야 하며, 없으면 파이프라인 실행 시 에러가 난다. 둘 다 비어 있으면 `unmapped` 경고만 찍힌다. 시드로 20여 행만 채워져 있으니 필요한 섹터/키워드를 이어서 채운다.

## 개발

```bash
make lint   # ruff check + format --check + mypy
make test   # pytest
```

## 모듈 맵

| 경로 | 역할 |
|---|---|
| `src/consumer_signal/config.py` | `.env` 로드/검증 (pydantic-settings) |
| `src/consumer_signal/schema.py` | 프론트와 공유하는 스냅샷 계약 (nodes/links) |
| `src/consumer_signal/run.py` | CLI 오케스트레이션 (typer) |
| `src/consumer_signal/collect/` | 네이버 데이터랩, KRX 수집기 |
| `src/consumer_signal/normalize.py` | 이동창 z-score |
| `src/consumer_signal/sentiment.py` | 감성 게이트 |
| `src/consumer_signal/narrate.py` | LLM 기반 '왜' 요약 |
| `src/consumer_signal/snapshot.py` | 스냅샷 빌드/저장 |
| `src/consumer_signal/dictionary/` | 키워드→종목 사전 로더/검증기 |
| `src/consumer_signal/db/` | SQLAlchemy 모델/세션 |
| `web/` | 프론트엔드 (미착수) |
