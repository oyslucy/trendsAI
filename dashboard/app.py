"""검증용 대시보드 (개발 도구).

폴리시된 제품이 아니라 파이프라인 산출물(스냅샷/시계열)이 멀쩡한지 눈으로
확인하기 위한 것 — 검증 테이블이 주인공이고 장식은 최소화한다.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

DATA_DIR = Path("data")
DEBUG_DIR = Path("debug")
INDEX_HTML = Path(__file__).parent / "static" / "index.html"

app = FastAPI(title="consumer-signal dashboard")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return INDEX_HTML.read_text(encoding="utf-8")


@app.get("/api/dates")
def list_dates() -> JSONResponse:
    """`data/snapshot_<date>.json`이 존재하는 날짜 목록(오름차순)."""
    dates = sorted(p.stem.removeprefix("snapshot_") for p in DATA_DIR.glob("snapshot_*.json"))
    return JSONResponse(dates)


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
