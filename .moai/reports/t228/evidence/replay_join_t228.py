"""t225 -- 콘솔 실측 슬롯표로 map_cues 를 오프라인 재현한다.

콘솔 쓰기 0. 슬롯표는 `t95_state_dump` 로 **실측한 값**을 그대로 적었다
(같은 회차 evidence/pool_*.json). 여기서 다시 조회하지 않는 이유는 셋이다:
이 재현이 콘솔 가용성에 걸리지 않게 하고, 반사실(FX 를 채웠다면)을 콘솔을
건드리지 않고 돌리고, 응답기 침묵이 관측된 경로(`Patch/Stages/1/Fixtures`)를
안 밟기 위해서다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from server.lxseq.cue_mapper import map_cues
from server.lxseq.cue_parser import parse_cue_csv

ROOT = Path(__file__).resolve().parents[4]
CUE_REL = "src/Lighting_Designer/03_곡파일_Sugar/LXSEQ_SAMPLE_01_Sugar_r3.cue-ex.csv"
CUE_CSV = ROOT / CUE_REL

# 실측 -- DataPool/Groups, childCount 18, truncated false
GROUP_SLOTS = dict(
    [
        ("ALL", 1),
        ("KEY", 2),
        ("FOH", 3),
        ("BACK", 4),
        ("SIDE-L", 5),
        ("SIDE-R", 6),
        ("SIDE-ALL", 7),
        ("WASH-U", 8),
        ("WASH-D", 9),
        ("WASH-ALL", 10),
        ("MOVER-U", 11),
        ("MOVER-D", 12),
        ("MOVER-ALL", 13),
        ("BLIND", 14),
        ("STROBE", 15),
        ("HAZE", 16),
        ("ODD", 17),
        ("EVEN", 18),
    ]
)

# 실측 -- PresetPools/1 Dimmer(7) · /2 Position(6) · /4 Color(7) ·
# /5 Beam(0) · /21 All 1(2). ID 는 시트 Name 조인(POS 는 라벨 첫 어절).
PRESET_SLOTS_NOW = dict(
    [
        ("DIM.FULL", 1),
        ("DIM.MID", 3),
        ("DIM.LOW", 4),
        ("DIM.GLOW", 5),
        ("DIM.OUT", 6),
        ("DIM.SHOW", 7),
        ("POS.01", 1),
        ("POS.02", 2),
        ("POS.03", 3),
        ("POS.04", 4),
        ("POS.05", 5),
        ("POS.06", 6),
        ("COL.01", 1),
        ("COL.04", 2),
        ("COL.05", 3),
        ("COL.06", 4),
        ("COL.07", 5),
        ("COL.08", 6),
        ("FX.02", 1),
        ("FX.08", 2),
    ]
)

# 반사실 A -- FX.01/03/05/07 을 All 1 의 빈 슬롯에 채웠다면.
PRESET_SLOTS_WITH_FX = dict(PRESET_SLOTS_NOW)
PRESET_SLOTS_WITH_FX["FX.01"] = 3
PRESET_SLOTS_WITH_FX["FX.03"] = 4
PRESET_SLOTS_WITH_FX["FX.05"] = 5
PRESET_SLOTS_WITH_FX["FX.07"] = 6

# 반사실 B -- 위에 더해 BM 넷과 COL.02 까지 채웠다면.
PRESET_SLOTS_ALL = dict(PRESET_SLOTS_WITH_FX)
PRESET_SLOTS_ALL["BM.01"] = 1
PRESET_SLOTS_ALL["BM.02"] = 2
PRESET_SLOTS_ALL["BM.03"] = 3
PRESET_SLOTS_ALL["BM.04"] = 4
PRESET_SLOTS_ALL["COL.02"] = 7

EMPTY_SEQUENCE_SECTION = dict([("ok", True), ("objects", [])])


def _run(records, cue_numbers, preset_slots):
    result = map_cues(
        records,
        declared_cues=cue_numbers,
        sequence_name="t225-replay",
        sequence_section=EMPTY_SEQUENCE_SECTION,
        group_slots=GROUP_SLOTS,
        preset_slots=preset_slots,
        existing_cue_numbers=(),
    )
    planned = [b.cue_no for b in result.planned]
    held = dict()
    for hold in result.held:
        row = dict([("group", hold.group), ("classes", list(hold.hold_classes))])
        held.setdefault(hold.cue_no, []).append(row)
    return dict(
        [
            ("planned", planned),
            ("planned_count", len(planned)),
            ("held_cues", sorted(held)),
            ("held", held),
            ("refusal", result.refusal),
        ]
    )


def main() -> int:
    parsed = parse_cue_csv(CUE_CSV.read_text(encoding="utf-8-sig"))
    out = dict(
        [
            ("cue_csv", str(CUE_CSV)),
            ("read", len(parsed.records)),
            ("declared_cues", list(parsed.cue_numbers)),
            ("preset_slots_resolved_now", len(PRESET_SLOTS_NOW)),
            ("now", _run(parsed.records, parsed.cue_numbers, PRESET_SLOTS_NOW)),
            ("with_fx", _run(parsed.records, parsed.cue_numbers, PRESET_SLOTS_WITH_FX)),
            ("all_filled", _run(parsed.records, parsed.cue_numbers, PRESET_SLOTS_ALL)),
        ]
    )
    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
