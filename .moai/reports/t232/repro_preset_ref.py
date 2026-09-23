"""t232 재현 — 같은 입력을 가짜 쇼파일 두 상태에 올린다. 콘솔 접촉 0.

사용: .venv/bin/python .moai/reports/t232/repro_preset_ref.py

(1) 시트 경로: map_presets 가 같은 CSV 프리셋을 상태마다 다른 슬롯에 앉힌다.
    큐 참조는 쓰는 순간 풀의 이름->슬롯 표로 푼다(tools.py 가 하는 방식) —
    그래서 번호는 달라도 각 상태 안에서는 같은 이름을 가리키는지 본다.
(2) 대화 경로: _position_preset_ready_starts 는 「연속 10칸 점유」만 본다.
    그 10칸이 기본 포지션 10종이 아니어도 시작점으로 제안되고, 곡 큐는
    preset_start + BASIC_POSITION_SEQUENCE.index(...) 로 번호를 짓는다.
"""

from __future__ import annotations

from server.lxseq.cue_mapper import resolve_preset_ref
from server.lxseq.preset_mapper import map_presets
from server.lxseq.preset_parser import LxseqPresetRecord
from server.spatial.pointing import BASIC_POSITION_SEQUENCE
from server.web.session import ChatSession


def pool(objects):
    return {
        "ok": True,
        "objects": [{"no": no, "name": name} for no, name in objects],
        "truncated": False,
        "total": len(objects),
        "capacity": 100,
    }


def rec(pid, name, row):
    return LxseqPresetRecord(
        kind="POS", preset_id=pid, name=name, value_raw="-", row=row, storable=True
    )


records = [rec("POS.01", "POS01 보컬 센터", 1), rec("POS.02", "POS02 드럼", 2)]

# 상태 A: 빈 풀 / 상태 B: 1~6 번이 다른 프리셋으로 차 있음
state_a = pool([])
state_b = pool([(n, f"OTHER{n}") for n in range(1, 7)])

print("(1) 시트 경로 — 같은 CSV, 두 쇼파일 상태")
for label, section in (("A 빈 풀", state_a), ("B 1~6 점유", state_b)):
    result = map_presets(records, pool_section=section)
    placed = [(p.preset_id, p.slot) for p in result.planned]
    print(f"  {label}: 배정 {placed}  refusal={result.refusal}")
    # 쓴 뒤의 풀을 tools.py 처럼 읽어 ID -> 슬롯 표를 만든다(첫 어절 = ID)
    after = [(o["no"], o["name"]) for o in section["objects"]] + [
        (p.slot, p.name) for p in result.planned
    ]
    slots = {}
    for no, name in after:
        head = name.split(" ")[0]
        if head.startswith("POS") and head[3:].isdigit():
            slots[f"POS.{head[3:]}"] = no
    ref, reason = resolve_preset_ref("POS.01", preset_slots=slots)
    target = dict(after).get(ref.slot) if ref else None
    slot_text = ref.slot if ref else "?"
    print(f"      큐의 POS.01 참조 -> At Preset 2.{slot_text} (그 슬롯의 이름: {target!r})")

print()
print("(2) 대화 경로 — 연속 10칸 점유만 보는 시작점 제안")
cases = {
    "C 기본 10종이 1~10": {n: BASIC_POSITION_SEQUENCE[n - 1] for n in range(1, 11)},
    "D 시트 프리셋 10개가 1~10": {n: f"POS{n:02d} 시트" for n in range(1, 11)},
}
for label, names in cases.items():
    starts = ChatSession._position_preset_ready_starts(None, slots=set(names))
    start = starts[0]
    center_no = start + BASIC_POSITION_SEQUENCE.index("Center")
    print(
        f"  {label}: 제안 시작점 {starts} -> 'Center' 큐는 At Preset 2.{center_no} "
        f"= 실제 이름 {names[center_no]!r}"
    )
