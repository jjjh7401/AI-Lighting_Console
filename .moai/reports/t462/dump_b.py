"""t462 완료 조건 ② — 업로드 길(B) 콘솔 명령 바이트 동일 확인용 덤프.

실제 입구(``build_songcue_bundle``) + 실제 룩 라이브러리로 두 곡 × 네 장르 × (bpm 있음/없음)
을 만들어 명령을 전부 이어 붙이고 sha256 과 함께 출력한다. 변경 전후에 같은 명령으로
돌려 파일을 diff 한다.

실행: uv run python .moai/reports/t462/dump_b.py > .moai/reports/t462/dump_b.<before|after>.txt
"""

import hashlib

from server.looks.loader import load_library_from_dir
from server.looks.songcue import build_songcue_bundle, map_sections_to_looks, parse_sections
from server.tests.test_looks_instantiate import FULL_RIG, _groups
from server.tests.test_songcue_t429_repeat_chorus_collision import (
    _ICE_CREAM_SECTIONS,
    _RAIN_SECTIONS,
)

library = load_library_from_dir()
total = hashlib.sha256()
for song, raw, bpm in (("Ice cream", _ICE_CREAM_SECTIONS, 100.4), ("Rain", _RAIN_SECTIONS, 76.0)):
    for genre in ("rock", "edm", "pop", "ballad"):
        for tempo in (bpm, None):
            sections = parse_sections(raw)
            selections = map_sections_to_looks(sections, library, genre)
            try:
                bundle = build_songcue_bundle(
                    song,
                    selections,
                    sequences_section={"objects": [], "truncated": False, "total": 0},
                    groups_section=_groups(*FULL_RIG),
                    bpm=tempo,
                )
                body = "\n".join(bundle.commands)
                extra = (
                    f"returns={[(r.source_cue_number, r.inserted_cue_number, r.inserted_start_ms, r.cap_beats) for r in bundle.climax_returns]} "
                    f"withheld={len(bundle.withheld_climax_returns)}"
                )
            except Exception as error:  # noqa: BLE001 — 실패 모양도 바이트 비교 대상이다
                body = f"ERROR {type(error).__name__}: {error}"
                extra = ""
            digest = hashlib.sha256(body.encode()).hexdigest()
            total.update(body.encode())
            print(f"## {song} {genre} bpm={tempo} lines={body.count(chr(10)) + 1} sha={digest[:16]} {extra}")
            print(body)
print(f"TOTAL sha256={total.hexdigest()}")
