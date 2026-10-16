"""칸 하나의 왼쪽·오른쪽 따로 색 — UI 사본이 서버 실출력과 어긋나는 걸 막는 대조 시험.

사본: `ui/src/components/beatgrid/cellSplitServerPayload.json`. UI 쪽 왕복 시험
(`cellSplitRoundTrip.test.tsx`)이 이 사본을 읽는다. 사본이 서버가 지금 내는 값과 다르면 UI
시험은 낡은 모양을 믿고 초록이 된다 — 그래서 값까지 똑같은지 본다(런북 사본의 구조 대조보다
엄격하다: 이 사본은 칸 하나의 값이 전부라 값이 곧 계약이다). 다르면 오류 문구에 재생성 명령이
실린다.
"""

from __future__ import annotations

import json

from server.tests.cell_split_payload_fixture import (
    FIXTURE_PATH,
    NEXT_BAR,
    REGEN_COMMAND,
    SPLIT_BAR,
    build_payload,
)


def _cues(payload: dict) -> list[dict]:
    return [cue for track in payload["beat_grid"]["tracks"] for cue in track["cues"]]


def test_fixture_equals_the_server_output() -> None:
    on_disk = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert on_disk == build_payload(), (
        f"{FIXTURE_PATH.name} 가 서버 실출력과 다르다. 다시 뜨기: {REGEN_COMMAND}"
    )


def test_fixture_contains_exactly_one_split_cell_with_both_sides_resolved() -> None:
    on_disk = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    split_cues = [cue for cue in _cues(on_disk) if "split" in cue]
    assert [cue["bar"] for cue in split_cues] == [SPLIT_BAR]
    assert split_cues[0]["split"] == {
        "left": {"color": "Red", "color_rgb": [100, 0, 0]},
        "right": {"color": "Blue", "color_rgb": [5, 20, 100]},
    }


def test_the_other_cells_carry_no_split_key_at_all() -> None:
    on_disk = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    others = [cue for cue in _cues(on_disk) if cue["bar"] != SPLIT_BAR]
    assert NEXT_BAR in {cue["bar"] for cue in others}  # 나뉜 칸 뒤의 보통 칸이 있다
    assert all("split" not in cue for cue in others)
