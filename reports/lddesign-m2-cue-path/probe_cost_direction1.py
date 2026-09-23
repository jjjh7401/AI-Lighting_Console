"""방향 1 실측 — 길 A 에 색을 붙이면 몇 줄인가. 실제로 붙여서 명령을 낸다.

`_reviewed_song_commands` 를 고치지 않고, 그 함수가 이미 받는
`extra_value_lines` 통로(= `_back_layer_value_lines` 와 같은 자리)에
색 값 라인을 하나 더 얹는 형태를 그대로 재현한다. 여기서 세는 줄 수가
본 구현에서 실제로 추가될 줄 수다.
"""

import sys

sys.path.insert(0, ".")

from server.design.color_names import resolve_color_name
from server.web.session import _color_apply_command


# ---- 여기가 추가될 코드 전부 --------------------------------------------
def _color_value_lines(cue, fids):
    """REQ-012 팔레트 주색을 큐의 값 라인으로 낸다. 모르는 이름은 조용히 건너뛴다."""
    palette = cue.color.palette
    if not palette:
        return ()
    rgb = resolve_color_name(palette[0])
    if rgb is None:
        return ()
    return (_color_apply_command(fids, rgb),)


# ---- 끝 ------------------------------------------------------------------

ADDED_LINES = 10  # 위 블록의 실제 줄 수(독스트링 포함, 주석 제외)

# 길 A 탐침을 그대로 다시 돌리되 extra_value_lines 에 위 함수를 끼운다.
import probe_helper_path_a as H  # noqa: E402

comp = H.build_composition()
fids = [1, 2, 3, 4]

print("=== 붙이기 전 (현재 main)")
before = H.commands(comp, fids, extra=lambda cue: ())
print(f"  명령 {len(before)}줄 · 색 줄 {H.color_hits(before)}")

print()
print("=== 붙인 뒤")
after = H.commands(comp, fids, extra=lambda cue: _color_value_lines(cue, fids))
for c in after[:14]:
    print("   ", c)
print("    ...")
print(f"  명령 {len(after)}줄 · 색 줄 {H.color_hits(after)}")

print()
print(f"=== 추가된 코드: {ADDED_LINES}줄 (새 함수 하나) + 호출부 1줄")
print(f"=== 명령 증가: {len(before)} -> {len(after)}줄")
