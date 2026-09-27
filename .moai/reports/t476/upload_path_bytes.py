"""t476 — 업로드 길(build_songcue_bundle) 명령이 면제 확장 전후로 바이트 동일한가.

업로드 길은 면제 판정(`is_programmer_state`)을 번들 조립 안에서 두 번 쓴다
(`songcue.py` 충돌 회수·충돌 그물). 확장 전 판정(선택 없는 값 줄은 면제 아님, 선택+값
줄도 면제 아님)으로 갈아 끼운 조립과 지금 판정의 조립을 한 프로세스에서 비교한다.
범위는 t462 dump_b 와 같다: 2곡(Ice cream·Rain) × 4장르 × BPM 있음/없음 = 16조합.

실행: uv run python .moai/reports/t476/upload_path_bytes.py
"""

from __future__ import annotations

import hashlib
import re

import server.looks.songcue as songcue
from server.looks.loader import load_library_from_dir
from server.looks.songcue import build_songcue_bundle, map_sections_to_looks, parse_sections
from server.tests.test_looks_instantiate import FULL_RIG, _groups
from server.tests.test_songcue_t429_repeat_chorus_collision import (
    _ICE_CREAM_SECTIONS,
    _RAIN_SECTIONS,
)

_OPERAND = r"\d+(?:\s*[-+]\s*\d+|\s+Thru(?:\s+\d+)?)*"
_BEFORE = (
    re.compile(r"Clear", re.IGNORECASE),
    re.compile(r"ClearAll", re.IGNORECASE),
    re.compile(rf"(?:Fixture|Group)\s+{_OPERAND}", re.IGNORECASE),
)


def _before(command: str) -> bool:
    text = command.strip()
    return any(pattern.fullmatch(text) is not None for pattern in _BEFORE)


def _dump() -> tuple[str, list[str]]:
    library = load_library_from_dir()
    total = hashlib.sha256()
    rows = []
    for song, raw, bpm in (
        ("Ice cream", _ICE_CREAM_SECTIONS, 100.4),
        ("Rain", _RAIN_SECTIONS, 76.0),
    ):
        for genre in ("rock", "edm", "pop", "ballad"):
            for tempo in (bpm, None):
                selections = map_sections_to_looks(parse_sections(raw), library, genre)
                try:
                    bundle = build_songcue_bundle(
                        song,
                        selections,
                        sequences_section={"objects": [], "truncated": False, "total": 0},
                        groups_section=_groups(*FULL_RIG),
                        bpm=tempo,
                    )
                    body = "\n".join(bundle.commands)
                except Exception as error:  # noqa: BLE001 — 실패 모양도 비교 대상이다
                    body = f"ERROR {type(error).__name__}: {error}"
                total.update(body.encode())
                rows.append(f"{song} {genre} bpm={tempo} lines={body.count(chr(10)) + 1}")
    return total.hexdigest(), rows


after_sha, after_rows = _dump()
current = songcue.is_programmer_state
songcue.is_programmer_state = _before
try:
    before_sha, before_rows = _dump()
finally:
    songcue.is_programmer_state = current

for row in after_rows:
    print(row)
print(f"before sha256={before_sha}")
print(f"after  sha256={after_sha}")
print("BYTE-IDENTICAL" if before_sha == after_sha else "DIFFERENT")
