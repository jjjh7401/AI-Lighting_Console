"""카드 t482 — 컨셉 패널 원천 데이터(SPEC-LDDESIGN-001 AC-018 일부·AC-049).

두 가지를 고정한다.

1. ``concept_report.rows[].description`` — 이미 구현된 ``describe()``(REQ-023/070)를
   런북 경로에 연결한다. 값은 해석된 큐 상태에서만 나온다(지어낸 문장 0).
2. ``concept_report.glance`` — "한눈에" 5단계에 어느 화면 구간이 드는지만 정한다.
   규칙은 리드 제안(2026-09-28, 감독 확인 전)이라 ``rule`` 표식을 단다. 카드 수치는
   UI 가 CUE SHEET 와 같은 구간 데이터에서 계산한다(REQ-097 — 원천을 둘로 나누지
   않는다).
"""

from __future__ import annotations

import dataclasses

from server.concept.cue_model import CueState
from server.concept.description import describe
from server.concept.headroom import compute_cue_headroom
from server.concept.session_bridge import (
    GLANCE_RULE,
    GLANCE_STAGES,
    build_concept_report,
    build_concept_report_from_songcue_sections,
    glance_stages,
)
from server.tests.test_song_timeline_concept_report_wiring import _plan, _section

LABELS = (
    "Intro",
    "Verse 1",
    "Pre-Chorus 1",
    "Chorus 1",
    "Verse 2",
    "Chorus 2",
    "Bridge",
    "Chorus 3",
    "Outro",
)
ROLES = ("intro", "verse", "verse", "chorus", "verse", "chorus", "bridge", "chorus", "finale")


def _positions(result: dict[str, object]) -> dict[str, list[int]]:
    return {stage["stage"]: stage["positions"] for stage in result["stages"]}  # type: ignore[index]


def _reasons(result: dict[str, object]) -> dict[str, str | None]:
    return {stage["stage"]: stage["reason"] for stage in result["stages"]}  # type: ignore[index]


class TestGlanceStages:
    def test_stage_names_and_rule_marker_are_fixed(self) -> None:
        assert GLANCE_STAGES == ("시작", "쌓기", "강조", "예고", "정점→마무리")
        assert GLANCE_RULE == "lead-proposed-2026-09-28"
        result = glance_stages(list(ROLES))
        assert result["available"] is True
        assert result["rule"] == GLANCE_RULE
        assert [stage["stage"] for stage in result["stages"]] == list(GLANCE_STAGES)  # type: ignore[index]

    def test_lead_rule_on_a_three_chorus_song(self) -> None:
        # 시작=intro · 쌓기=첫 후렴 앞 · 강조=첫 후렴~끝에서 둘째 후렴(사이 verse 포함)
        # · 예고=끝에서 둘째 후렴과 마지막 후렴 사이 · 정점→마무리=마지막 후렴부터 끝까지
        assert _positions(glance_stages(list(ROLES))) == {
            "시작": [0],
            "쌓기": [1, 2],
            "강조": [3, 4, 5],
            "예고": [6],
            "정점→마무리": [7, 8],
        }

    def test_every_section_lands_in_exactly_one_stage(self) -> None:
        placed = sorted(
            p for positions in _positions(glance_stages(list(ROLES))).values() for p in positions
        )
        assert placed == list(range(len(ROLES)))

    def test_single_chorus_leaves_emphasis_and_preview_empty_with_reasons(self) -> None:
        result = glance_stages(["intro", "verse", "chorus", "finale"])
        assert _positions(result) == {
            "시작": [0],
            "쌓기": [1],
            "강조": [],
            "예고": [],
            "정점→마무리": [2, 3],
        }
        reasons = _reasons(result)
        assert reasons["강조"] and reasons["예고"]
        assert reasons["시작"] is None and reasons["정점→마무리"] is None

    def test_back_to_back_final_choruses_leave_preview_empty(self) -> None:
        result = glance_stages(["intro", "chorus", "chorus"])
        assert _positions(result)["예고"] == []
        assert _reasons(result)["예고"]

    def test_no_chorus_puts_trailing_finale_at_the_peak_and_explains_the_gaps(self) -> None:
        result = glance_stages(["intro", "verse", "bridge", "finale"])
        assert _positions(result) == {
            "시작": [0],
            "쌓기": [1, 2],
            "강조": [],
            "예고": [],
            "정점→마무리": [3],
        }
        assert _reasons(result)["강조"] and _reasons(result)["예고"]

    def test_missing_role_anywhere_makes_the_whole_glance_unavailable(self) -> None:
        result = glance_stages(["intro", None, "chorus"])
        assert result["available"] is False
        assert result["reason"]
        assert result["stages"] == []


class TestConceptReportWiring:
    def _plan_with_roles(self):  # noqa: ANN202
        sections = tuple(
            dataclasses.replace(_section(i + 1, label, i * 10_000), role=role)
            for i, (label, role) in enumerate(zip(LABELS, ROLES, strict=True))
        )
        return _plan(bpm=120.0, sections=sections)

    def test_glance_is_attached_on_the_plan_path(self) -> None:
        report = build_concept_report(self._plan_with_roles())
        assert report["available"] is True
        assert _positions(report["glance"])["정점→마무리"] == [7, 8]  # type: ignore[arg-type]

    def test_plan_without_roles_reports_why_there_is_no_glance(self) -> None:
        sections = tuple(_section(i + 1, label, i * 10_000) for i, label in enumerate(LABELS))
        glance = build_concept_report(_plan(bpm=120.0, sections=sections))["glance"]
        assert glance["available"] is False  # type: ignore[index]
        assert "role" in glance["reason"]  # type: ignore[index]

    def test_songcue_path_has_no_role_source(self) -> None:
        report = build_concept_report_from_songcue_sections(
            "Rain", 120.0, [("Intro", 0), ("Verse", 10_000), ("Chorus", 20_000)]
        )
        glance = report["glance"]
        assert glance["available"] is False  # type: ignore[index]
        assert glance["reason"]  # type: ignore[index]

    def test_every_row_carries_a_non_empty_description(self) -> None:
        rows = build_concept_report(self._plan_with_roles())["rows"]
        assert rows  # type: ignore[truthy-bool]
        assert all(isinstance(row["description"], str) and row["description"] for row in rows)  # type: ignore[index,union-attr]

    def test_description_is_exactly_describe_over_the_resolved_states(self) -> None:
        # 지어낸 문장이 아니다: 같은 입력으로 describe() 를 직접 불러 한 행씩 대조한다.
        from server.concept.gates import build_song
        from server.concept.session_bridge import _raw_sections

        plan = self._plan_with_roles()
        raw_song = {
            "song": plan.song_title,
            "bpm": plan.music_profile.bpm,
            "sections": _raw_sections(plan),
        }
        build = build_song(raw_song)
        rows = build_concept_report(plan)["rows"]
        prev = CueState(dim={}, color=None, pos="home", motion=0)
        for row, raw, state in zip(rows, build.rows, build.states, strict=True):  # type: ignore[arg-type]
            ops = raw.get("ops", ())
            assert row["description"] == describe(prev, state, ops, compute_cue_headroom(state))  # type: ignore[index]
            prev = state
