"""카드 t444 — 컨셉 게이트의 색 판정은 입력 색으로만 한다 (SPEC-LDDESIGN-001
REQ-026·027·029·030, 브리지 충족).

배경(실측, ``origin/main@f5283ea4``): ``pilot_baseline.json`` 에는 색이 없고
게이트의 색은 전부 ``gates.py`` 의 프로토타입 상수 4개에서 나왔다. 운영
경로는 구간마다 주색·보조색을 내는데(``SectionDecision.palette.colors``),
``session_bridge`` 가 그 색을 버리고 구간 이름·시각만 넘겼다. 그래서 운영
경로의 G6 도 상수 한 색으로 판정됐다.

이 파일이 고정하는 것:

1. 입력에 색이 없으면 G2·G6·G7 은 n/a(사유 문자열까지), G5 는 흰색 조건만
   빼고 판정한다.
2. 입력 색이 있으면 그 색(주색+보조색)으로 판정한다 — 보조색이 공통색이면
   브리지가 통과하고(보조색이 실제로 실려야만 통과하는 입력), 공통색이
   없으면 실패한다(양팔 대조).
3. ``restore`` 로 1회차를 복원하는 후렴 행도 자기 입력 색을 띤다.
4. 두 운영 어댑터가 실제 팔레트를 원시 구간에 싣는다.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from server.concept.gates import (
    GATE_NAMES,
    NO_INPUT_COLOR_REASON,
    _concept_cues,
    build_song,
    evaluate_song,
)
from server.concept.session_bridge import (
    _raw_sections,
    build_concept_report,
    build_concept_report_from_songcue_sections,
)
from server.orchestrator.tools import _songcue_concept_palettes
from server.tests.test_chorus_color_two_paths_t441 import (
    _path_b_selections,
    _records,
)
from server.tests.test_concept_session_bridge import _plan

_FIXTURE = Path(__file__).parent / "fixtures" / "pilot_baseline.json"
_SONGS = {
    s["song"]: s for s in json.loads(_FIXTURE.read_text(encoding="utf-8")) if "error" not in s
}

_G2, _G5, _G6, _G7 = (
    next(name for name in GATE_NAMES if name.startswith(prefix))
    for prefix in ("G2", "G5", "G6", "G7")
)


def _colored(song: dict[str, Any], palette_for) -> dict[str, Any]:
    """원시 구간마다 ``palette_for(baseline_name)`` 을 실은 사본."""
    colored = copy.deepcopy(song)
    for section in colored["sections"]:
        section["palette"] = list(palette_for(str(section["baseline_name"])))
    return colored


def _is_chorus(name: str) -> bool:
    return name.startswith("Chorus")


# Cut and Run — 후렴 3회 이상(Final Chorus 승급), 절과 후렴이 그룹을 공유해
# t439 가 상수 팔레트로 브리지 위반 12건을 셌던 곡.
_SONG = _SONGS["Cut and Run.mp3"]


class TestNoInputColorIsNotApplicable:
    def test_fixture_songs_have_no_color_keys(self) -> None:
        """전제 실측 — 입력에 색이 정말 없다(있으면 이 카드의 n/a 가 틀린다)."""
        for song in _SONGS.values():
            assert not {"palette", "colors", "color"} & set(song)
            for section in song["sections"]:
                assert "palette" not in section

    @pytest.mark.parametrize("song_name", sorted(_SONGS))
    def test_color_gates_are_na_with_reason(self, song_name: str) -> None:
        result = evaluate_song(_SONGS[song_name])
        for gate in (_G6, _G7):
            assert result[gate].passed is None
            assert result[gate].detail == NO_INPUT_COLOR_REASON
        g2 = result[_G2]
        assert g2.passed is None
        assert g2.detail in (NO_INPUT_COLOR_REASON, "후렴 쌍 없음(구조상 n/a)")
        assert NO_INPUT_COLOR_REASON in result[_G5].detail

    def test_constant_palette_still_fills_states(self) -> None:
        """색 입력이 없어도 큐 상태의 색은 오늘처럼 상수 팔레트로 채운다
        (컴파일·에너지 경로 바이트 동일) — 판정에만 쓰지 않는다."""
        build = build_song(_SONG)
        assert build.color_source == "constant"
        assert {row.color for row in build.table if row.kind == "section"} >= {"파랑", "노랑"}


class TestInputColorsAreJudged:
    def test_shared_secondary_color_passes_bridge(self) -> None:
        """절=파랑+흰색, 후렴=노랑+흰색 — 주색은 서로 다르고 보조색(흰색)이
        공통이다. 보조색이 실제로 큐까지 실려야만 통과하는 입력이다."""
        song = _colored(
            _SONG, lambda name: ("yellow", "white") if _is_chorus(name) else ("blue", "white")
        )
        result = evaluate_song(song)
        assert result[_G6].passed is True, result[_G6].detail
        assert "브리지 pass" in result[_G6].detail
        assert "유보색 n/a(입력에 유보색 없음)" in result[_G6].detail

    def test_disjoint_colors_fail_bridge(self) -> None:
        """대조군 — 같은 곡, 보조색 없이 주색만 서로 다르면 브리지 위반."""
        song = _colored(_SONG, lambda name: ("yellow",) if _is_chorus(name) else ("blue",))
        result = evaluate_song(song)
        assert result[_G6].passed is False
        assert "브리지 fail" in result[_G6].detail

    def test_secondary_reaches_the_concept_cues(self) -> None:
        song = _colored(_SONG, lambda name: ("blue", "white"))
        cues = _concept_cues(build_song(song).table)
        section_cues = [cue for cue in cues if cue.layer == "section"]
        assert section_cues
        assert all(cue.colors == ("blue", "white") for cue in section_cues)

    def test_restored_chorus_rows_carry_their_own_input_color(self) -> None:
        """후렴 2회차 이후는 "Chorus 1" 을 restore 한다 — 입력 색은 그 뒤에
        얹혀야 한다(앞에 두면 restore 가 1회차 색으로 덮는다)."""
        counter = {"n": 0}

        def palette_for(name: str) -> tuple[str, ...]:
            if _is_chorus(name):
                counter["n"] += 1
                return ("red",) if counter["n"] == 1 else ("green",)
            return ("blue",)

        song = _colored(_SONG, palette_for)  # 색은 여기서 한 번, 구간 순서대로 정해진다
        build = build_song(song)
        chorus_rows = [
            row
            for row in build.table
            if row.kind == "section" and row.section in ("Chorus", "Final Chorus")
        ]
        assert [row.color for row in chorus_rows][:2] == ["red", "green"]
        # 입력 색이 회차마다 달라졌으니 G7 은 실패, G2 도 1→2 쌍에서 실패.
        result = evaluate_song(song)
        assert result[_G7].passed is False
        assert result[_G2].passed is False

    def test_uniform_input_passes_identity_gates(self) -> None:
        result = evaluate_song(_colored(_SONG, lambda name: ("blue", "warm white")))
        assert result[_G2].passed is True
        assert result[_G7].passed is True

    def test_declared_reserved_color_is_checked(self) -> None:
        """유보색을 입력이 선언하면 판정한다 — 해제(Final Chorus) 전에
        흰색을 쓰면 실패, 해제 구간에서만 쓰면 통과."""
        early = _colored(_SONG, lambda name: ("blue", "white"))
        early["reserved"] = ["white"]
        assert evaluate_song(early)[_G6].passed is False

        build_names = [s.section for s in build_song(_SONG).table if s.kind == "section"]
        assert "Final Chorus" in build_names
        late = _colored(_SONG, lambda name: ("blue",))
        late["sections"][_last_chorus_index(late)]["palette"] = ["blue", "white"]
        late["reserved"] = ["white"]
        result = evaluate_song(late)
        assert "유보색 pass" in result[_G6].detail

    def test_white_chorus1_triggers_g5_only_with_input(self) -> None:
        white_chorus = _colored(_SONG, lambda name: (" White ",) if _is_chorus(name) else ("blue",))
        assert evaluate_song(white_chorus)[_G5].passed is False
        assert "흰색" in evaluate_song(white_chorus)[_G5].detail
        blue_chorus = _colored(_SONG, lambda name: ("blue",))
        assert evaluate_song(blue_chorus)[_G5].passed is True


def _last_chorus_index(song: dict[str, Any]) -> int:
    return max(i for i, s in enumerate(song["sections"]) if _is_chorus(str(s["baseline_name"])))


class TestPathAAdapterCarriesPalette:
    _LABELS = ("Intro", "Verse 1", "Chorus 1", "Verse 2", "Chorus 2", "Outro")

    def test_raw_sections_carry_decision_palette(self) -> None:
        plan = _plan(bpm=120.0, labels=self._LABELS)
        raw = _raw_sections(plan)
        assert [item["palette"] for item in raw] == [
            list(decision.palette.colors) for decision in plan.sections
        ]

    def test_report_judges_g6_with_plan_colors(self) -> None:
        report = build_concept_report(_plan(bpm=120.0, labels=self._LABELS))
        assert report["available"] is True
        g6 = report["gates"][_G6]
        assert g6["passed"] is True  # 모든 구간 blue — 공통색 있음
        assert g6["detail"] != NO_INPUT_COLOR_REASON


class TestPathBAdapterCarriesPalette:
    _PAIRS = [("Intro 1", 0), ("Verse 1", 13_000), ("Chorus 1", 26_000), ("Outro 1", 39_000)]

    def test_without_palettes_color_gates_are_na(self) -> None:
        report = build_concept_report_from_songcue_sections("t444", 120.0, self._PAIRS)
        assert report["gates"][_G6] == {"passed": None, "detail": NO_INPUT_COLOR_REASON}

    def test_with_palettes_g6_is_judged(self) -> None:
        palettes = [("blue",), ("blue",), ("red",), ("red",)]
        report = build_concept_report_from_songcue_sections(
            "t444", 120.0, self._PAIRS, palettes=palettes
        )
        assert report["gates"][_G6]["passed"] is False

    def test_mismatched_palette_count_is_reported_not_raised(self) -> None:
        report = build_concept_report_from_songcue_sections(
            "t444", 120.0, self._PAIRS, palettes=[("blue",)]
        )
        assert report["available"] is False
        assert "짝이 안 맞는다" in report["reason"]

    def test_songcue_concept_palettes_follow_the_director_override(self) -> None:
        selections, _notes = _path_b_selections(records=_records("modulate"))
        palettes = _songcue_concept_palettes(selections, records=_records("modulate"))
        assert palettes is not None
        assert len(palettes) == len(selections)
        # 경로 B 는 주색 한 개만 낸다. 이름은 감독 답(Q2 "블루") 그대로다 —
        # 경로 A 의 ``palette.colors[0]`` 과 같은 문자열(t441 교차 일치).
        assert set(palettes) == {("블루",)}

    def test_songcue_concept_palettes_none_without_records(self) -> None:
        selections, _notes = _path_b_selections(records=None)
        assert _songcue_concept_palettes(selections, records=None) is None
        assert _songcue_concept_palettes(selections, records=()) is None


class TestPrepareSongcueWiresPalettes:
    """호출 자리 배선 — 헬퍼만 시험하면 ``prepare_songcue`` 안에서
    ``palettes=`` 를 빼도 초록이다(t441 변이 교훈). 도구를 실제로 돌려
    결과의 컨셉 리포트를 읽는다."""

    def _report(self, port):
        from server.looks.loader import load_library_from_dir
        from server.orchestrator.tools import build_toolset
        from server.tests.test_chorus_color_two_paths_t441 import TestToolsetWiring
        from server.tests.test_songcue_bpm_production_wiring import _record
        from server.tests.test_songcue_confirmed_default import _AnalysisPort
        from server.tests.test_songcue_tool import _RecordingPort, _SongCueStatePort, _tree

        # BPM 은 확정 분석 기록에서만 온다(``_confirmed_density_bpm``) — 없으면
        # 컨셉 리포트가 아예 안 돈다. t439 배선 시험과 같은 가짜 분석 포트.
        registry = build_toolset(
            execution_port=_RecordingPort(),
            state_port=_SongCueStatePort(_tree()),
            look_library=load_library_from_dir(),
            song_analysis=_AnalysisPort(_record(bpm=120.0)),
            **({} if port is None else {"interview_records": port}),
        )
        # 구간 간격 16초(120 BPM 8마디) + Outro — t441 의 4초 간격 5구간은
        # 색과 무관하게 컨셉 파이프라인이 ``reduce: ref 'song_release_reference'``
        # 로 실패해(기록 유무 둘 다) 색 게이트까지 가지 못한다.
        sections = [
            {"name": name, "start": start}
            for name, start in (
                ("Intro", "0:00"),
                ("Verse", "0:16"),
                ("Chorus", "0:32"),
                ("Verse", "0:48"),
                ("Chorus", "1:04"),
                ("Outro", "1:20"),
            )
        ]
        execution, payload = TestToolsetWiring()._dispatch(registry, sections=sections)
        assert execution.result.is_error is False, execution.result.content
        return payload["concept_report"]

    def test_records_present_color_gates_are_judged(self) -> None:
        from server.tests.test_chorus_color_two_paths_t441 import _RecordsPort

        report = self._report(_RecordsPort(_records("modulate")))
        assert report["available"] is True, report
        assert report["gates"][_G6]["detail"] != NO_INPUT_COLOR_REASON
        assert report["gates"][_G6]["passed"] is True  # 전 구간 감독 주색 하나

    def test_records_absent_color_gates_are_na(self) -> None:
        report = self._report(None)
        assert report["available"] is True, report
        assert report["gates"][_G6] == {"passed": None, "detail": NO_INPUT_COLOR_REASON}
