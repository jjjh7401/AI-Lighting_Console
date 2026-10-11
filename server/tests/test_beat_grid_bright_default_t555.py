"""카드 t555 — 박자 격자 밝기 기본값 100% (감독 결정 2026-10-11).

감독 원문: 「밝기 값이 명확하지 않으면 우선 100% 진행해」.
- 밝기가 비어 있던 25칸 중, §4(`reports/effect-arrangement-rules-20261007.md:98-110`)가
  밝기를 정하지 않은 16칸만 100% 로 채운다.
- 「—」 칸 7개는 §4:100 「「—」는 그 시퀀스가 쉰다는 뜻」 — 값이 명확(쉼)하므로 비운다.
- BACK 0·3 은 §4 SCENE 열 「BACK 차가운 실루엣 30%」(0~2)·「그대로」(3~6) — 값이 명확(30)
  하므로 100 을 넣지 않는다. 30 을 칸에 옮길지는 감독 결정 대기.
- 100 은 코드 상수가 아니라 데이터(`love_attack.yaml`)에만 있다.
- 근거: 기존 승인이 없던 10칸은 evidence.approval {supervisor, 2026-10-11, 카드 t555},
  이미 2026-10-10 프리셋 승인이 있던 6칸은 그 승인을 그대로 둔다(칸당 승인 필드가 하나라
  밝기 근거는 YAML 주석·증거표에만 — 기계 필드 없음은 알려진 갭).
"""

from __future__ import annotations

import pytest

from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid
from server.design.beat_grid_edit import BeatGridEditError, apply_beat_grid_edit

FILLED = {
    ("SIDE-ALL", 11),
    ("SIDE-ALL", 14),
    *(("MOVER-U", b) for b in (0, 3, 7, 11, 14, 18, 22)),
    *(("MOVER-D", b) for b in (0, 3, 7, 11, 14, 18, 22)),
}
KEPT_PRIOR_APPROVAL = {
    ("SIDE-ALL", 11),
    ("SIDE-ALL", 14),
    ("MOVER-U", 14),
    ("MOVER-U", 18),
    ("MOVER-D", 14),
    ("MOVER-D", 18),
}
REST_CELLS = {
    ("BACK", 11),
    ("BACK", 14),
    *(("SIDE-ALL", b) for b in (0, 3, 7, 18, 22)),
}
AWAITING_DIRECTOR = {("BACK", 0), ("BACK", 3)}


def _cells() -> dict[tuple[str, int], dict]:
    grid = default_beat_grid(LOVE_ATTACK_TITLE)
    return {(t["group_name"], c["bar"]): c for t in grid["tracks"] for c in t["cues"]}


def test_sixteen_unclear_cells_get_value_100() -> None:
    cells = _cells()
    for key in FILLED:
        assert cells[key]["brightness"] == {
            "mode": "value",
            "value_percent": 100,
            "preset_no": None,
        }, key


def test_rest_and_awaiting_cells_stay_empty() -> None:
    cells = _cells()
    for key in REST_CELLS | AWAITING_DIRECTOR:
        assert cells[key]["brightness"] == {
            "mode": None,
            "value_percent": None,
            "preset_no": None,
        }, key


def test_new_approvals_name_this_card_and_prior_approvals_are_untouched() -> None:
    cells = _cells()
    for key in FILLED - KEPT_PRIOR_APPROVAL:
        approval = cells[key]["evidence"]["approval"]
        assert approval["by"] == "supervisor", key
        assert approval["date"] == "2026-10-11", key
        assert "t555" in approval["source"], key
    for key in KEPT_PRIOR_APPROVAL:
        approval = cells[key]["evidence"]["approval"]
        assert approval["date"] == "2026-10-10", key
        assert "proposal-table.md" in approval["source"], key


def test_no_other_brightness_changed() -> None:
    # §4 숫자가 있던 칸·디머 프리셋 칸은 그대로다.
    cells = _cells()
    assert cells[("BACK", 7)]["brightness"]["value_percent"] == 60
    assert cells[("WASH-ALL", 14)]["brightness"]["value_percent"] == 25
    assert cells[("FOH", 7)]["brightness"]["preset_no"] == "1.1"
    assert cells[("BLIND", 17)]["brightness"]["preset_no"] == "1.6"
    changed = {
        key
        for key, cue in cells.items()
        if cue["brightness"]["value_percent"] == 100 and key not in FILLED
    }
    assert changed == {("BACK", 18), ("BACK", 22), ("BLIND", 18)}


# -- 밝기 승인이 새 프리셋 번호를 통과시키지 않는다 (REQ-LDBEAT-015(f)(g)) ------
# 합친 CI 빨강(run 38112994889) 재현 — t555 가 MOVER-U·MOVER-D 칸에 붙인
# 밝기 승인이, 같은 칸에 새 효과/디머 프리셋 번호를 넣을 때 재사용됐다.
# 감독 선택 2026-10-11: 새 번호는 이번 changes 에 함께 온 evidence.approval 만
# 인정한다. MOVER-U 3·MOVER-D 3 은 app_movement 가 없어 축 겹침(vi-7)과 섞이지
# 않는다.

_FRESH_APPROVAL = {
    "grade": "name_only",
    "approval": {
        "by": "supervisor",
        "date": "2026-10-11",
        "source": ".moai/reports/t555/run-verdict.md",
    },
}


def _cue_of(grid, group_name: str, bar: int) -> dict:
    track = next(t for t in grid["tracks"] if t["group_name"] == group_name)
    return next(c for c in track["cues"] if c["bar"] == bar)


def test_cell_brightness_approval_does_not_admit_new_effect_number() -> None:
    assert _cells()[("MOVER-U", 3)]["evidence"]["approval"] is not None
    with pytest.raises(BeatGridEditError) as excinfo:
        apply_beat_grid_edit(
            default_beat_grid(LOVE_ATTACK_TITLE),
            bar=3,
            target="MOVER-U",
            changes={"effect_preset_no": "2.65", "effect_kind": "position"},
        )
    assert "REQ-LDBEAT-015" in str(excinfo.value)


def test_cell_brightness_approval_does_not_admit_new_dimmer_number() -> None:
    assert _cells()[("MOVER-D", 3)]["evidence"]["approval"] is not None
    with pytest.raises(BeatGridEditError) as excinfo:
        apply_beat_grid_edit(
            default_beat_grid(LOVE_ATTACK_TITLE),
            bar=3,
            target="MOVER-D",
            changes={
                "brightness": {
                    "mode": "dimmer_effect",
                    "value_percent": None,
                    "preset_no": "1.22",
                }
            },
        )
    assert "REQ-LDBEAT-015" in str(excinfo.value)


def test_approval_sent_with_the_change_admits_new_effect_number() -> None:
    updated, _report = apply_beat_grid_edit(
        default_beat_grid(LOVE_ATTACK_TITLE),
        bar=3,
        target="MOVER-U",
        changes={
            "effect_preset_no": "2.65",
            "effect_kind": "position",
            "evidence": _FRESH_APPROVAL,
        },
    )
    cue = _cue_of(updated, "MOVER-U", 3)
    assert cue["effect_preset_no"] == "2.65"
    assert cue["evidence"]["approval"]["source"] == ".moai/reports/t555/run-verdict.md"
