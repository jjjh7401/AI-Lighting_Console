"""t558 거절 재현 — 앱 드롭다운이 보내는 모양(승인 없음) 그대로 새 효과 번호를 넣는다.

실행: uv run python .moai/reports/t557/t558_reject_repro.py
"""

from server.design.beat_grid import attach_beat_grid_default
from server.design.beat_grid_edit import BeatGridEditError, apply_beat_grid_edit

timeline = attach_beat_grid_default({"song_title": "LOVE ATTACK", "sequence_number": 210})
grid = timeline["beat_grid"]
CASES = (
    # 움직임 효과 드롭다운이 보내는 모양
    {"effect_preset_no": "2.63", "effect_kind": "position"},
    # 밝기 → 디머 효과 드롭다운이 보내는 모양
    {"brightness": {"mode": "dimmer_effect", "value_percent": None, "preset_no": "1.21"}},
)
for changes in CASES:
    try:
        apply_beat_grid_edit(grid, bar=11, target="MOVER-U", changes=changes)
        print("ACCEPTED", changes)
    except BeatGridEditError as error:
        print("REJECTED", changes, "->", error)
