"""t476 — upload_path_bytes.py 의 대조군: 바꿔 끼운 판정이 업로드 길에서 실제로 불리는가.

두 판정의 결과가 같다는 사실만으로는 「판정을 안 탔다」와 「탔지만 결과가 같다」가
갈리지 않는다. 여기서는 (1) 한 번들 조립 동안 판정이 몇 번 불리는지 세고,
(2) 업로드 번들 안에 새 면제 꼴(선택 + 값)과 맞는 줄이 몇 개인지 센다.

실행: uv run python .moai/reports/t476/upload_path_control.py
"""

from __future__ import annotations

from server.tests.test_songcue_t429_repeat_chorus_collision import (
    _ICE_CREAM_SECTIONS,
    _RAIN_SECTIONS,
)

import server.looks.songcue as songcue
from server.fx.instantiate import is_programmer_state
from server.looks.loader import load_library_from_dir
from server.looks.songcue import build_songcue_bundle, map_sections_to_looks, parse_sections
from server.tests.test_looks_instantiate import FULL_RIG, _groups

calls: list[str] = []


def _spy(command: str) -> bool:
    calls.append(command)
    return is_programmer_state(command)


songcue.is_programmer_state = _spy
library = load_library_from_dir()
selected_value_lines = 0
bundles = 0
for raw, bpm in ((_ICE_CREAM_SECTIONS, 100.4), (_RAIN_SECTIONS, 76.0)):
    for genre in ("rock", "edm", "pop", "ballad"):
        for tempo in (bpm, None):
            bundle = build_songcue_bundle(
                "song",
                map_sections_to_looks(parse_sections(raw), library, genre),
                sequences_section={"objects": [], "truncated": False, "total": 0},
                groups_section=_groups(*FULL_RIG),
                bpm=tempo,
            )
            bundles += 1
            selected_value_lines += sum(
                1 for c in bundle.commands if ";" in c and is_programmer_state(c)
            )
print(f"bundles={bundles} predicate_calls={len(calls)}")
print(f"selected_value_lines_in_upload_bundles={selected_value_lines}")
