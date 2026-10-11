"""카드 t595 하네스 캡처 — 가짜 콘솔(t577/t590 FakeConsole)로 「⇪ 콘솔에 반영」을
한 번 돌리고, 서버가 UI 로 보낸 격자 이벤트에 빈 프리셋 표식이 실렸는지 출력한다.
콘솔 접촉 0건(가짜 콘솔만).

    python .moai/reports/t595/capture_harness.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from server.tests.test_apply_time_approval_t577 import (  # noqa: E402
    _new_session,
    _state_tree,
    _timeline,
)
from server.web.session import SongTimelineStore  # noqa: E402

_APPROVED = {
    "grade": None,
    "approval": {"by": "supervisor", "date": "2026-10-11", "source": "harness"},
}


def _pool(path: str, slots: list[int]) -> dict:
    return {
        "v": 1,
        "kind": "state",
        "path": path,
        "children": [{"i": s, "name": f"P{s}"} for s in slots],
    }


def main() -> None:
    tree = _state_tree()
    tree["DataPool/PresetPools/4"] = _pool("DataPool/PresetPools/4", [21])
    timeline = _timeline()
    timeline["beat_grid"]["tracks"][0]["cues"] = [
        # 승인 대기 + 빈 번호(4.99) → 보류 칸
        {"bar": 1, "effect_preset_no": "4.99", "effect_kind": "position", "evidence": None},
        # 이미 승인된 칸 + 빈 번호(4.98) → t590 보류 대상 아님
        {"bar": 2, "color_preset_no": "4.98", "evidence": dict(_APPROVED)},
        # 승인 대기 + 있는 번호(4.21) → 표식 없음(대조군)
        {"bar": 3, "effect_preset_no": "4.21", "effect_kind": "position", "evidence": None},
    ]
    store = SongTimelineStore()
    store.latest = timeline
    sent: list[dict] = []
    with tempfile.TemporaryDirectory() as tmp:
        session, _console, _approval, _audit = _new_session(
            Path(tmp), store=store, state_tree=tree, sent=sent
        )
        status = session.beat_grid_apply()
    grids = [e["timeline"]["beat_grid"] for e in sent if e.get("type") == "song_timeline"]
    print("apply ok:", status.get("ok"), "| reason:", status.get("reason"))
    print("events:", [e.get("type") for e in sent])
    print("song_timeline events:", len(grids))
    for i, grid in enumerate(grids):
        value = grid.get("empty_preset_cells", "<필드 없음>")
        print(f"  [{i}] empty_preset_cells =", json.dumps(value, ensure_ascii=False))


if __name__ == "__main__":
    main()
