"""스냅샷 빌드 및 저장."""

from __future__ import annotations

import json
from datetime import date as Date
from pathlib import Path

from consumer_signal.schema import Snapshot


def build_empty_snapshot(target_date: Date) -> Snapshot:
    """빈 스냅샷을 만든다. 파이프라인 각 단계가 구현되면 nodes/links로 채워진다."""
    return Snapshot(date=target_date, nodes=[], links=[])


def dump_snapshot(snapshot: Snapshot, out_dir: Path) -> Path:
    """`data/snapshot_<date>.json`으로 스냅샷을 덤프한다."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"snapshot_{snapshot.date.isoformat()}.json"
    out_path.write_text(
        json.dumps(snapshot.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out_path
