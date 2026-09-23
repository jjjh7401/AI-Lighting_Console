"""카드 t445 — 후렴 색 운용을 곡별 선택으로(감독 결정 2026-09-23).

「음악 스타일마다 다르니 하나로 고정은 무리」 → 기본은 후렴 주색 고정,
곡마다 Q2B(``color_usage``)로 고른다. 선택지 넷:

* ``modulate``(기본)·``single`` — 후렴(chorus/finale)을 마디 분할한 큐도
  주색이 고정된다. 보조색만 돌고, 돌릴 보조색이 없으면(2색 팔레트) 쪼개지
  않는다 — 같은 큐 둘을 내지 않는다는 카드 t305 원칙 그대로.
* ``per_chorus`` — 후렴 회차마다 색을 바꾼다(t439 에서 살려 둔 것).
* ``split_swap`` — 한 후렴의 분할 큐 안에서 주·보조색을 맞바꾼다(t305
  현행 동작). 이 선택지를 고른 곡은 고치기 전 기본 동작과 바이트 동일하다.
  카드는 표준 §2d 「제안 3개」를 지키므로 이 선택지는 자유 입력(「맞바꾸기」)
  으로 고른다.

RED 재현 — 고치기 전(``origin/main@db601e8a``)에는 기본 모드에서
32초(16마디 @120bpm) 후렴 3회가 'Chorus (1/2)' ('blue','warm white') /
'Chorus (2/2)' ('warm white','blue') 로 주색이 뒤집혀 G7 이 FAIL(위반 5건)
했다(``.moai/reports/t445/probe.py``).
"""

from __future__ import annotations

import itertools

import pytest

from server.concept.gates import evaluate_song
from server.concept.session_bridge import build_concept_report
from server.design.interview import Q2_PALETTE, Q2B_COLOR_USAGE, AnswerRecord, build_question
from server.design.profile import MusicProfile
from server.design.rig import build_rig_profile
from server.design.song_plan import TimingPlan
from server.spatial.position_cuesheet import PositionSheetSection
from server.tests.test_concept_color_input_t444 import _SONG as _T444_SONG
from server.tests.test_concept_color_input_t444 import _colored, _is_chorus
from server.web.session import _build_unified_song_plan, _split_sections_for_density

_G7 = "G7 후렴 주색 동일"


def _record(step: str, value: object) -> AnswerRecord:
    return AnswerRecord(
        step=step,
        proposals=(),
        choice=None,
        free_text=str(value),
        value=value,
        confirmed=True,
        source="standard",
    )


def _records(color_usage: str | None) -> tuple[AnswerRecord, ...]:
    if color_usage is None:
        return ()
    return (_record(Q2_PALETTE, "blue"), _record(Q2B_COLOR_USAGE, color_usage))


def _long_chorus_sections() -> list[PositionSheetSection]:
    """Intro + (Verse 16초 + Chorus 32초)×3 + Outro. 32초 = 16마디 @120bpm
    = 분할 단위(8마디) 2개 — 고치기 전에는 후렴마다 두 큐로 갈렸다."""
    sections = [PositionSheetSection(name="Intro", start_ms=0, mood="", d_level=2, role="intro")]
    start = 8000
    for _ in range(3):
        sections.append(
            PositionSheetSection(name="Verse", start_ms=start, mood="", d_level=3, role="verse")
        )
        start += 16000
        sections.append(
            PositionSheetSection(name="Chorus", start_ms=start, mood="", d_level=5, role="chorus")
        )
        start += 32000
    sections.append(
        PositionSheetSection(name="Outro", start_ms=start, mood="", d_level=2, role="outro")
    )
    return sections


def _plan(color_usage: str | None):
    profile = MusicProfile(bpm=120.0, palette=("blue", "white"))
    expanded, origin, _notes = _split_sections_for_density(
        _long_chorus_sections(),
        profile=profile,
        color_usage=color_usage or "modulate",
    )
    plan = _build_unified_song_plan(
        sections=expanded,
        profile=profile,
        rig=build_rig_profile(patch=[], groups={}, coords=[]),
        records=_records(color_usage),
        timing=TimingPlan.manual_go(),
        sequence_no=445,
        section_origin=origin,
    )
    return plan


def _chorus_rows(plan) -> list[tuple[str, tuple[str, ...]]]:
    return [
        (decision.section.label, tuple(decision.palette.colors))
        for decision in plan.sections
        if decision.role == "chorus"
    ]


class TestDefaultPinsChorusPrimaryAcrossSplitCues:
    """기본(무응답·modulate)·single — 후렴 분할 큐 주색 고정, G7 pass."""

    @pytest.mark.parametrize("color_usage", [None, "modulate", "single"])
    def test_every_chorus_cue_shares_one_primary(self, color_usage):
        rows = _chorus_rows(_plan(color_usage))
        primaries = {colors[0] for _label, colors in rows}
        assert len(primaries) == 1, f"후렴 주색이 갈렸다 — {rows}"

    @pytest.mark.parametrize("color_usage", [None, "modulate"])
    def test_g7_passes_on_the_session_path(self, color_usage):
        plan = _plan(color_usage)
        report = build_concept_report(plan, color_usage=color_usage or "modulate")
        assert report["gates"][_G7]["passed"] is True, report["gates"][_G7]

    @pytest.mark.parametrize("color_usage", [None, "modulate"])
    def test_no_two_adjacent_cues_are_identical_copies(self, color_usage):
        """회전을 끈 자리에서 분할을 그대로 두면 색까지 같은 복제 큐가 나온다
        — 같은 큐 둘보다 안 쪼갠다(카드 t305)."""
        decisions = _plan(color_usage).sections
        for prev, curr in zip(decisions, decisions[1:], strict=False):
            same = (
                prev.role == curr.role
                and prev.palette.colors == curr.palette.colors
                and prev.d == curr.d
                and prev.position == curr.position
            )
            assert not same, f"복제 큐: {prev.section.label} / {curr.section.label}"

    def test_verse_split_rotation_is_unchanged(self):
        """verse 등 후렴이 아닌 역할의 분할 회전은 이 카드 범위 밖 — 기본에서도
        split_swap 과 같은 산출이어야 한다."""
        default = [
            (d.section.label, tuple(d.palette.colors))
            for d in _plan(None).sections
            if d.role not in ("chorus", "finale")
        ]
        swap = [
            (d.section.label, tuple(d.palette.colors))
            for d in _plan("split_swap").sections
            if d.role not in ("chorus", "finale")
        ]
        assert default == swap


class TestSplitSwapKeepsThePreviousBehaviour:
    """split_swap — 고치기 전 기본 동작과 바이트 동일(probe 실측값 고정)."""

    def test_split_swap_swaps_primary_inside_each_chorus(self):
        rows = _chorus_rows(_plan("split_swap"))
        assert (
            rows
            == [
                ("Chorus (1/2)", ("blue", "warm white")),
                ("Chorus (2/2)", ("warm white", "blue")),
            ]
            * 3
        )

    def test_split_swap_cue_count_matches_previous_default(self):
        assert len(_plan("split_swap").sections) == 11

    def test_g7_is_not_judged_for_split_swap(self):
        plan = _plan("split_swap")
        report = build_concept_report(plan, color_usage="split_swap")
        assert report["gates"][_G7]["passed"] is None


class TestGateRespectsPerSongChoice:
    """게이트 층 — 후렴 회차마다 주색이 다른 입력(카드 t444 픽스처 곡)."""

    @staticmethod
    def _song_with_changing_chorus_color():
        colors = itertools.cycle(("red", "yellow", "green"))
        return _colored(
            _T444_SONG,
            lambda name: (next(colors), "white") if _is_chorus(name) else ("blue", "white"),
        )

    def test_control_modulate_still_fails_g7(self):
        """대조군 — 기본이면 같은 입력이 G7 FAIL 이어야 n/a 가 의미를 갖는다."""
        results = evaluate_song(self._song_with_changing_chorus_color())
        assert results[_G7].passed is False, results[_G7].detail

    @pytest.mark.parametrize("color_usage", ["per_chorus", "split_swap"])
    def test_evaluate_song_marks_g7_na(self, color_usage):
        results = evaluate_song(self._song_with_changing_chorus_color(), color_usage=color_usage)
        assert results[_G7].passed is None, results[_G7].detail


class TestInterviewOffersSplitSwap:
    def test_q2b_card_keeps_three_options_and_names_split_swap_as_free_text(self):
        """표준 §2d 「제안 3개」는 카드가 기계적으로 강제한다(QuestionCard).
        넷째 선택지는 1급인 자유 입력(DI3)으로 받고, 카드가 그 말을 알려 준다."""
        card = build_question(
            Q2B_COLOR_USAGE, MusicProfile(), build_rig_profile(patch=[], groups={}, coords=[])
        )
        assert [option.value for option in card.options] == ["modulate", "single", "per_chorus"]
        assert "맞바꾸기" in card.why

    @pytest.mark.parametrize("text", ["후렴 안에서 맞바꾸기", "분할 큐 색 교대", "swap"])
    def test_free_text_resolves_to_split_swap(self, text):
        from server.design.interview import _parse_free_text

        assert _parse_free_text(Q2B_COLOR_USAGE, text, MusicProfile()) == "split_swap"


class TestTwoEntrancesAgreeOnSplitChorusPrimary:
    """두 입구(경로 A 인터뷰 · 경로 B 곡 업로드, 카드 t441) — 같은 답이면 후렴
    분할 조각의 주색 순서가 같다. 기본은 조각 모두 주색, split_swap 은
    조각마다 주·보조색 교대."""

    _BLUE = (5, 20, 100)
    _WARM_WHITE = (100, 75, 40)

    @staticmethod
    def _path_b_primaries(color_usage: str) -> list[tuple[int, int, int] | None]:
        from server.design.section_palette import role_for_songcue_label
        from server.looks.loader import load_library_from_dir
        from server.looks.songcue import (
            _look_color,
            map_sections_to_looks,
            parse_sections,
            split_selections_for_density,
        )
        from server.orchestrator.tools import _override_songcue_main_color

        raw = (
            ("Intro", "0:00"),
            ("Verse", "0:08"),
            ("Chorus", "0:24"),
            ("Verse", "0:56"),
            ("Chorus", "1:12"),
            ("Outro", "1:44"),
        )
        selections = map_sections_to_looks(parse_sections(raw), load_library_from_dir(), "edm")
        selections, _ = split_selections_for_density(selections, bpm=120.0, song_end_ms=120_000)
        records = (_record(Q2_PALETTE, "블루"), _record(Q2B_COLOR_USAGE, color_usage))
        overridden, notes = _override_songcue_main_color(selections, records=records)
        assert not notes
        primaries = []
        for selection in overridden:
            if role_for_songcue_label(selection.section.label) != "chorus":
                continue
            rgb = {value.name: value.value for value in _look_color(selection.look)}
            primaries.append((rgb["ColorRGB_R"], rgb["ColorRGB_G"], rgb["ColorRGB_B"]))
        return primaries

    def test_default_path_b_split_fragments_share_the_primary(self):
        assert self._path_b_primaries("modulate") == [self._BLUE] * 4

    def test_split_swap_path_b_alternates_like_path_a(self):
        assert self._path_b_primaries("split_swap") == [self._BLUE, self._WARM_WHITE] * 2
