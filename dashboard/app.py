"""소비재 검색 신호 대시보드.

`/`는 인사이트 중심 브리핑(제품 카드/밸류체인 흐름/리더보드), `/legacy`는
파이프라인 산출물을 표로 그대로 확인하는 예전 검증 대시보드다. 둘 다
파이프라인이 이미 계산해둔 snapshot/series 산출물만 읽는다 — 여기서는
아무것도 다시 계산하지 않는다.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from consumer_signal.dictionary.loader import load_keyword_map, load_universe
from consumer_signal.schema import Snapshot
from dashboard.viewmodel import build_dashboard_viewmodel

DATA_DIR = Path("data")
DEBUG_DIR = Path("debug")
STATIC_DIR = Path(__file__).parent / "static"
INDEX_HTML = STATIC_DIR / "index.html"
LEGACY_HTML = STATIC_DIR / "legacy.html"

KST = timezone(timedelta(hours=9))

app = FastAPI(title="consumer-signal dashboard")


def _available_dates() -> list[str]:
    return sorted(p.stem.removeprefix("snapshot_") for p in DATA_DIR.glob("snapshot_*.json"))


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX_HTML.read_text(encoding="utf-8")


@app.get("/legacy", response_class=HTMLResponse)
def legacy() -> str:
    return LEGACY_HTML.read_text(encoding="utf-8")


@app.get("/api/dates")
def list_dates() -> JSONResponse:
    """`data/snapshot_<date>.json`이 존재하는 날짜 목록(오름차순)."""
    return JSONResponse(_available_dates())


@app.get("/api/snapshot/{target_date}")
def get_snapshot(target_date: str) -> JSONResponse:
    path = DATA_DIR / f"snapshot_{target_date}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"no snapshot for {target_date}")
    return JSONResponse(json.loads(path.read_text(encoding="utf-8")))


@app.get("/api/series/{target_date}")
def get_series(target_date: str) -> JSONResponse:
    """디버그 시계열. 없으면 404가 아니라 빈 객체 — 아직 스냅샷만 있고

    디버그 산출물은 안 남긴 실행일 수 있어 없는 게 정상적인 상태다.
    """
    path = DEBUG_DIR / f"series_{target_date}.json"
    if not path.exists():
        return JSONResponse({})
    return JSONResponse(json.loads(path.read_text(encoding="utf-8")))


@app.get("/api/dashboard/dates")
def list_dashboard_dates() -> JSONResponse:
    return JSONResponse(_available_dates())


@app.get("/api/dashboard/{target_date}")
def get_dashboard(target_date: str) -> JSONResponse:
    snapshot_path = DATA_DIR / f"snapshot_{target_date}.json"
    if not snapshot_path.exists():
        raise HTTPException(status_code=404, detail=f"no snapshot for {target_date}")

    snapshot = Snapshot.model_validate(json.loads(snapshot_path.read_text(encoding="utf-8")))

    series_path = DEBUG_DIR / f"series_{target_date}.json"
    series_debug = (
        json.loads(series_path.read_text(encoding="utf-8")) if series_path.exists() else {}
    )

    keywords = load_keyword_map(DATA_DIR / "keyword_map.yaml")
    universe = load_universe(DATA_DIR / "universe.csv")
    generated_at = datetime.fromtimestamp(snapshot_path.stat().st_mtime, tz=KST).isoformat()

    viewmodel = build_dashboard_viewmodel(
        target_date, generated_at, snapshot, series_debug, keywords, universe
    )
    return JSONResponse(viewmodel)
