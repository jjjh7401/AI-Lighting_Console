"""카드 t439 — AC-LDDESIGN-017 방향의 교차 확인: 같은 후렴 반복(코러스 6회
+ Final Chorus)이 두 곡 조립 경로(웹/채팅 경로 `server/web/session.py` ·
LLM 툴 경로 `server/looks/songcue.py`+`server/orchestrator/tools.py`) 양쪽
모두에서 회차 간 색 항등을 만족하는지 실제 실행으로 확인한다.

**두 경로는 같은 입력을 받을 수 없다** — Path A 는 역할(role)·D-레벨·감독이
고른 팔레트(이름 문자열, 예: "블루")를 입력으로 받아 `_ARC_PALETTE` 아크에서
보조색을 고르고, Path B 는 구간 라벨·다이내믹스 요청을 입력으로 받아
버스킹 룩 라이브러리(`server/looks/busking/`)에서 이미 RGB 값이 박힌 Look
을 고른다. 색의 출처 자체가 다르므로(이름 팔레트 vs 라이브러리 룩) **값을
곧이곧대로 비교하는 것은 의미가 없다** — 이 파일은 대신 "가장 가까운
등가물"(같은 구간 어휘, 같은 반복 횟수, 같은 다이내믹스/세기)을 만들어 두
경로 각각이 **자기 색 표현 안에서** REQ-LDDESIGN-004/030 의 불변식(후렴
반복 전체가 동일한 색을 유지한다)을 실제로 지키는지 재고, 그 결과를
표로 남긴다.
"""

from __future__ import annotations

from pathlib import Path

from server.design.profile import MusicProfile
from server.design.rig import build_rig_profile
from server.design.song_plan import TimingPlan
from server.spatial.position_cuesheet import PositionSheetSection
from server.web.session import _build_unified_song_plan

_REPORT_PATH = Path(".moai/reports/t439/chorus_color_two_paths.md")

_CHORUS_OCCURRENCES = 6


def _path_a_chorus_colors() -> list[tuple[str, tuple[str, ...]]]:
    """Path A — 확정 구간(role 명시) 경로. intro 1 + chorus 6회 + finale 1."""
    sections = [
        PositionSheetSection(name="Intro", start_ms=0, mood="", d_level=2, role="intro"),
    ]
    start_ms = 4000
    for _ in range(_CHORUS_OCCURRENCES):
        sections.append(
            PositionSheetSection(
                name="Chorus", start_ms=start_ms, mood="", d_level=5, role="chorus"
            )
        )
        start_ms += 4000
    sections.append(
        PositionSheetSection(
            name="Final Chorus", start_ms=start_ms, mood="", d_level=5, role="finale"
        )
    )
    profile = MusicProfile(palette=("블루",))
    plan = _build_unified_song_plan(
        sections=sections,
        profile=profile,
        rig=build_rig_profile(patch=[], groups={}, coords=[]),
        records=(),
        timing=TimingPlan.manual_go(),
        sequence_no=139,
    )
    rows: list[tuple[str, tuple[str, ...]]] = []
    n = 0
    for decision in plan.sections:
        if decision.role == "chorus":
            n += 1
            rows.append((f"Chorus {n}", tuple(decision.palette.colors)))
        elif decision.role == "finale":
            rows.append(("Final Chorus", tuple(decision.palette.colors)))
    return rows


class TestBothPathsSatisfyChorusColorIdentityInTheirOwnRepresentation:
    def test_path_a_all_chorus_occurrences_share_one_palette_final_excluded(self):
        rows = _path_a_chorus_colors()
        chorus_rows = [colors for label, colors in rows if label != "Final Chorus"]
        assert len(chorus_rows) == _CHORUS_OCCURRENCES
        assert len(set(chorus_rows)) == 1, f"Path A 후렴 색이 갈렸다: {rows}"
