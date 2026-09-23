"""카드 t441, SPEC-LDDESIGN-001 REQ-003 — 구간별 주색 결정을 두 곡 조립
경로(웹/채팅 경로 `server/web/session.py` · LLM 도구 경로
`server/orchestrator/tools.py`+`server/looks/songcue.py`)가 **같은 함수**
(`server.design.section_palette._section_palette_choice`)로 정하는지 실제
실행으로 확인한다.

카드 t439(`test_chorus_color_two_paths_t439.py`)와 달리 이번엔 **같은 색이
나와야 한다** — t439 는 "두 경로는 같은 입력을 받을 수 없다"(서로 다른 색
표현 공간)는 것을 실측했지만, 이 카드는 정확히 그 간극을 메운다: 경로 B
(`prepare_songcue`)가 세션의 연출 인터뷰 기록(Q2 팔레트·Q2B 색 운용)을
읽어 경로 A 와 같은 함수로 정한 색을 이미 고른 룩의 ColorRGB 위에 덮는다.

**"메인 컬러 중심" 불변식(카드 t409)이 이 표를 단조롭게 만든다.** `_arc_palette`
/`_per_chorus_palette` 는 역할·회차·색 운용에 무관하게 반환 튜플의 첫 칸(주색)
을 **항상** 감독이 고른 팔레트의 첫 단어로 고정한다(`_arc_palette` 독스트링
"반환 튜플의 첫 칸은 항상 primary"). 이 카드가 옮기는 것은 그 주색 **하나**뿐
이므로(보조색은 옮기지 않는다), 아래 표의 모든 구간·모든 회차·두 색 운용
모드가 **전부 같은 색**으로 나오는 것은 버그가 아니라 그 불변식이 실측으로
드러나는 그대로다. 회차 사다리(모듈레이트 회전·per_chorus 액센트)는 전부
보조색 축에만 산다 — 이 카드 범위 밖이다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.design.interview import Q2_PALETTE, Q2B_COLOR_USAGE, AnswerRecord
from server.design.profile import MusicProfile
from server.design.rig import build_rig_profile
from server.design.section_palette import role_for_songcue_label
from server.design.song_plan import TimingPlan
from server.looks.loader import load_library_from_dir
from server.looks.schema import AttributeValue
from server.looks.songcue import (
    _look_color,
    build_songcue_bundle,
    map_sections_to_looks,
    parse_sections,
    split_selections_for_density,
)
from server.orchestrator.tools import (
    _override_songcue_main_color,
    _songcue_role_occurrences,
    build_toolset,
)
from server.spatial.position_cuesheet import PositionSheetSection
from server.tests.busking_fixtures import FULL_RIG
from server.tests.test_looks_instantiate import _groups
from server.tests.test_songcue_ladder import _sequences
from server.tests.test_songcue_tool import _RecordingPort, _SongCueStatePort, _tree
from server.web.session import _build_unified_song_plan

_REPORT_PATH = Path(".moai/reports/t441/chorus_color_two_paths.md")

_GENRE = "edm"
_PALETTE_ANSWER = "블루"
_BLUE_RGB = (5, 20, 100)  # server/design/color_names.py COLOR_PALETTE_SEQUENCE #8


def _answer_record(step: str, value: object) -> AnswerRecord:
    """실제 ``AnswerRecord`` — 경로 A(``_build_unified_song_plan`` ->
    ``_director_decisions``)와 경로 B(``_interview_record_value``, step/value
    만 duck-typing 으로 읽는다) 양쪽이 "같은 기록" 을 받게 한다. 카드 지시문의
    "same records" 를 문자 그대로 지킨다 — 최소 가짜(step/value 둘만)로도
    경로 B 는 통과하지만, 경로 A 는 ``DirectorDecision.from_audit_record`` 가
    ``confirmed``/``source`` 도 읽으므로 실제 타입이 필요하다."""
    return AnswerRecord(
        step=step,
        proposals=(),
        choice=None,
        free_text=str(value),
        value=value,
        confirmed=True,
        source="standard",
    )


def _records(
    color_usage: str = "modulate", palette: str = _PALETTE_ANSWER
) -> tuple[AnswerRecord, ...]:
    return (
        _answer_record(Q2_PALETTE, palette),
        _answer_record(Q2B_COLOR_USAGE, color_usage),
    )


class _RecordsPort:
    """``InterviewRecordsPort`` 의 가짜 — ``current`` 하나
    (`test_songcue_confirmed_default.py` 의 ``_AnalysisPort`` 와 같은 자리)."""

    def __init__(self, records: tuple[object, ...] | None) -> None:
        self.current = records


# =============================================================================
# 입력 — 같은 곡, 두 경로가 각자 받을 수 있는 형태로
# =============================================================================

#: Intro 1 + (Chorus·Verse·Drop 섞어) 후렴류 3회 — 라벨 문자열이 갈려도
#: (Chorus/Drop 모두 §6 "chorus · drop" 행) 같은 **역할**로 접혀 회차를
#: 공유해야 한다는 것이 `_songcue_role_occurrences` 가 증명하는 것이다.
_RAW_SECTIONS_B = (
    ("Intro", "0:00"),
    ("Chorus", "0:04"),
    ("Verse", "0:08"),
    ("Drop", "0:12"),
    ("Chorus", "0:16"),
)


def _path_a_colors(*, color_usage: str) -> list[tuple[str, str, tuple[str, ...]]]:
    """경로 A — 채팅 연출 인터뷰가 낳는 계획. ``_RAW_SECTIONS_B`` 와 같은
    역할 시퀀스(intro, chorus×3, 사이에 verse 하나)를 role 필드로 직접
    적는다 — 경로 B 의 Chorus/Drop 혼용과 같은 "역할 3회" 를 경로 A 어휘로
    표현한 것(경로 A 에는 Drop 이라는 별도 라벨이 없다, `_section_role` 참고).
    """
    sections = [
        PositionSheetSection(name="Intro", start_ms=0, mood="", d_level=2, role="intro"),
        PositionSheetSection(name="Chorus", start_ms=4000, mood="", d_level=5, role="chorus"),
        PositionSheetSection(name="Verse", start_ms=8000, mood="", d_level=3, role="verse"),
        PositionSheetSection(name="Chorus", start_ms=12000, mood="", d_level=5, role="chorus"),
        PositionSheetSection(name="Chorus", start_ms=16000, mood="", d_level=5, role="chorus"),
    ]
    profile = MusicProfile(palette=(_PALETTE_ANSWER,))
    plan = _build_unified_song_plan(
        sections=sections,
        profile=profile,
        rig=build_rig_profile(patch=[], groups={}, coords=[]),
        records=_records(color_usage),
        timing=TimingPlan.manual_go(),
        sequence_no=441,
    )
    return [
        (decision.section.label, decision.role, tuple(decision.palette.colors))
        for decision in plan.sections
    ]


def _path_b_selections(*, records: tuple[object, ...] | None):
    library = load_library_from_dir()
    sections = parse_sections(_RAW_SECTIONS_B)
    selections = map_sections_to_looks(sections, library, _GENRE)
    selections, _density_notes = split_selections_for_density(selections, bpm=None)
    return _override_songcue_main_color(selections, records=records)


def _path_b_colors(*, color_usage: str) -> list[tuple[str, str, tuple[AttributeValue, ...]]]:
    selections, notes = _path_b_selections(records=_records(color_usage))
    assert not notes, f"기대하지 않은 색 실패 사유: {notes}"
    bundle = build_songcue_bundle(
        "t441 cross-path",
        selections,
        sequences_section=_sequences(),
        groups_section=_groups(*FULL_RIG),
    )
    rows: list[tuple[str, str, tuple[AttributeValue, ...]]] = []
    for section_bundle in bundle.stored_sections:
        look = section_bundle.selection.look
        role = role_for_songcue_label(section_bundle.section.label)
        colors = _look_color(look) if look is not None else ()
        rows.append((section_bundle.section.label, role, colors))
    return rows


def _rgb_tuple(colors: tuple[AttributeValue, ...]) -> tuple[int, int, int] | None:
    by_name = {c.name: c.value for c in colors}
    if not all(name in by_name for name in ("ColorRGB_R", "ColorRGB_G", "ColorRGB_B")):
        return None
    return (by_name["ColorRGB_R"], by_name["ColorRGB_G"], by_name["ColorRGB_B"])


# =============================================================================
# 역할 매핑 + 회차 계산 — 순수 함수 단위
# =============================================================================


class TestRoleForSongcueLabel:
    """`section_palette.role_for_songcue_label` — 카드 지시문이 요구하는
    "모든 매핑을 보고에 적어라" 를 코드로도 고정한다."""

    @pytest.mark.parametrize(
        "label,expected_role",
        [
            ("Intro", "intro"),
            ("인트로", "intro"),
            ("Verse", "verse"),
            ("Chorus", "chorus"),
            ("Chorus 1", "chorus"),
            ("Drop", "chorus"),
            ("Bridge", "bridge"),
            ("Breakdown", "bridge"),
            ("Build-Up", "other"),
            ("Pre-Chorus", "other"),
            ("Post-Chorus", "other"),
            ("Outro", "other"),
            ("Zzyzx (어휘 밖)", "other"),
        ],
    )
    def test_mapping_table(self, label, expected_role):
        assert role_for_songcue_label(label) == expected_role


class TestSongcueRoleOccurrences:
    """``_songcue_role_occurrences`` — 라벨 텍스트가 아니라 **역할**로 회차를
    센다(카드 지시문 "same occurrence counting per role")."""

    def test_mixed_labels_sharing_a_role_share_one_occurrence_stream(self):
        library = load_library_from_dir()
        sections = parse_sections(_RAW_SECTIONS_B)
        selections = map_sections_to_looks(sections, library, _GENRE)
        result = _songcue_role_occurrences(selections)
        labels = [s.section.label for s in selections]
        assert labels == ["Intro", "Chorus", "Verse", "Drop", "Chorus"]
        # Chorus(1) -> chorus occurrence 1, Drop -> chorus occurrence 2(라벨은
        # 다르지만 §6 행이 같다), 두 번째 Chorus -> chorus occurrence 3 —
        # section.instance 만 썼다면 Drop 은 자기 라벨의 1회차로 잘못 셌을
        # 것이다(라벨별 개별 카운터).
        assert result == (
            ("intro", 1),
            ("chorus", 1),
            ("verse", 1),
            ("chorus", 2),
            ("chorus", 3),
        )

    def test_density_split_fragments_of_one_original_section_share_one_occurrence(self):
        library = load_library_from_dir()
        # 첫 구간(0:00~0:32, 32 초 = 2 단위 @120bpm·4/4, 단위는 8마디=16초 —
        # `cue_density.BAR_UNIT_BARS`)만 실제로 쪼개진다. 둘째 구간은
        # `song_end_ms` 없이는 길이를 몰라 통째로 남는다 — 그래도 "쪼개진
        # 조각들이 같은 회차를 공유한다" 를 보이는 데는 첫 구간 하나로 충분하다.
        sections = parse_sections((("Chorus", "0:00"), ("Chorus", "0:32")))
        selections = map_sections_to_looks(sections, library, _GENRE)
        split, notes = split_selections_for_density(selections, bpm=120.0)
        assert len(split) > len(selections), f"쪼개지지 않았다 — 입력 확인: {notes}"
        assert [s.section.instance for s in split] == [1, 1, 2]
        result = _songcue_role_occurrences(split)
        # 첫 원본(회차 1)의 두 조각은 전부 ("chorus", 1), 둘째 원본(회차 2)은
        # ("chorus", 2) — 조각 개수와 무관하게 원본별로 한 값을 공유한다.
        assert result == (("chorus", 1), ("chorus", 1), ("chorus", 2))


# =============================================================================
# 교차 확인 — 같은 곡, 같은 답, 두 경로
# =============================================================================


class TestCrossPathMainColorIdentity:
    """AC-LDDESIGN(REQ-003) — records 가 있으면 두 경로가 같은 주색을 낸다."""

    @pytest.mark.parametrize("color_usage", ["modulate", "per_chorus"])
    def test_every_section_gets_the_directors_blue_on_both_paths(self, color_usage):
        path_a_rows = _path_a_colors(color_usage=color_usage)
        path_b_rows = _path_b_colors(color_usage=color_usage)

        assert len(path_a_rows) == len(path_b_rows) == 5

        # 경로 A — palette.colors[0] (주색) 이 전부 "블루".
        for _label, _role, colors in path_a_rows:
            assert colors[0] == _PALETTE_ANSWER, path_a_rows

        # 경로 B — 덮어쓴 룩의 ColorRGB 가 전부 Blue(5,20,100).
        for label, _role, colors in path_b_rows:
            assert _rgb_tuple(colors) == _BLUE_RGB, (label, path_b_rows)

        # 후렴류(코러스 3회, 라벨은 Chorus/Drop/Chorus)가 전부 같은 색이라는
        # REQ-LDDESIGN-004/030 의 불변식도 두 경로 모두에서 실측.
        path_a_chorus = {colors[0] for _label, role, colors in path_a_rows if role == "chorus"}
        path_b_chorus = {
            _rgb_tuple(colors) for _label, role, colors in path_b_rows if role == "chorus"
        }
        assert path_a_chorus == {_PALETTE_ANSWER}
        assert path_b_chorus == {_BLUE_RGB}


class TestRecordsAbsentIsByteIdenticalToToday:
    """대조군 — 기록이 없거나(``None``) Q2 답이 없으면 경로 B 는 오늘과
    바이트 동일하다(카드 지시문 "records absent -> byte-identical")."""

    def test_none_records_leaves_selections_unchanged(self):
        library = load_library_from_dir()
        sections = parse_sections(_RAW_SECTIONS_B)
        selections = map_sections_to_looks(sections, library, _GENRE)
        selections, _notes = split_selections_for_density(selections, bpm=None)

        overridden, notes = _override_songcue_main_color(selections, records=None)
        assert notes == ()
        assert overridden == tuple(selections)

    def test_empty_records_and_no_palette_answer_also_leave_selections_unchanged(self):
        library = load_library_from_dir()
        sections = parse_sections(_RAW_SECTIONS_B)
        selections = map_sections_to_looks(sections, library, _GENRE)
        selections, _notes = split_selections_for_density(selections, bpm=None)

        empty, empty_notes = _override_songcue_main_color(selections, records=())
        assert empty_notes == ()
        assert empty == tuple(selections)

        # Q2B 만 답하고 Q2(팔레트)는 답하지 않은 기록 — "no palette answer".
        no_palette = (_answer_record(Q2B_COLOR_USAGE, "modulate"),)
        result, result_notes = _override_songcue_main_color(selections, records=no_palette)
        assert result_notes == ()
        assert result == tuple(selections)

    def test_baseline_chorus_look_is_crimson_and_acid_not_blue(self):
        """기록 없이는 오늘 그대로다(SPEC 배경 실측과 동일 — "같은 곡이 경로
        A 에서 블루, 경로 B 에서 crimson"). ``Chorus``/``Drop`` 은 같은
        **역할**(chorus)이지만 라벨 텍스트가 달라 버스킹이 서로 다른 룩을
        고른다(``edm-drop-crimson`` vs ``edm-drop-acid``) — 이 두 값이 바로
        REQ-003 이 고치는 비일관성이고, 오버라이드 없이는 그대로 남는다는
        것을 이 시험이 확인한다."""
        library = load_library_from_dir()
        sections = parse_sections(_RAW_SECTIONS_B)
        selections = map_sections_to_looks(sections, library, _GENRE)
        selections, _notes = split_selections_for_density(selections, bpm=None)
        overridden, _notes2 = _override_songcue_main_color(selections, records=None)
        chorus_colors = {
            _rgb_tuple(_look_color(s.look))
            for s in overridden
            if s.look is not None and role_for_songcue_label(s.section.label) == "chorus"
        }
        assert chorus_colors == {(100, 0, 15), (72, 100, 0)}, chorus_colors
        assert _BLUE_RGB not in chorus_colors


class TestToolsetWiring:
    """ "prepare_songcue 를 툴셋으로 직접 구동" — 세션 뷰 대신 세션 필드
    (``ChatSession._song_interview_records``)의 실제 소비 통로
    (``build_toolset(interview_records=...)``)가 실제로 도구까지 닿는지,
    옵션이 정말 생략 가능한지(카드 지시문)를 콘솔 없이 확인한다."""

    def _library(self):
        return load_library_from_dir()

    def _registry(self, *, interview_records=None):
        return build_toolset(
            execution_port=_RecordingPort(),
            state_port=_SongCueStatePort(_tree()),
            look_library=self._library(),
            **({} if interview_records is None else {"interview_records": interview_records}),
        )

    def _dispatch(self, registry, **arguments):
        import json

        from server.llm.types import ToolCall

        payload = {
            "song_title": "t441 toolset",
            "genre": _GENRE,
            "timecode_number": 7,
            "sections": [{"name": name, "start": start} for name, start in _RAW_SECTIONS_B],
        }
        payload.update(arguments)
        call = ToolCall(id="songcue-t441", name="prepare_songcue", arguments=payload)
        execution = registry.dispatch(call)
        return execution, json.loads(execution.result.content)

    def test_omitting_interview_records_matches_passing_a_none_current_port(self):
        """생략(기본값)과 "포트는 있지만 아직 완료된 인터뷰가 없다"
        (``current is None``)가 같은 결과를 내야 한다 — 둘 다 "오늘과
        바이트 동일" 이라는 같은 약속이다."""
        registry_omitted = self._registry()
        registry_none_current = self._registry(interview_records=_RecordsPort(None))

        execution_a, payload_a = self._dispatch(registry_omitted)
        execution_b, payload_b = self._dispatch(registry_none_current)

        assert execution_a.result.is_error is False
        assert execution_b.result.is_error is False
        assert payload_a["report"] == payload_b["report"]
        assert "director_color_override_notes" not in payload_a
        assert "director_color_override_notes" not in payload_b

    def test_wired_records_reach_the_tool_and_report_no_color_failures(self):
        registry = self._registry(interview_records=_RecordsPort(_records("modulate")))
        execution, payload = self._dispatch(registry)
        assert execution.result.is_error is False
        assert "director_color_override_notes" not in payload


class TestFabricatedControl:
    """날조 대조군 — 위 GREEN 이 공허하지 않다는 것을 보인다. 색 이름 →
    RGB 해소를 끄면(``resolve_color_name`` 을 전부 ``None`` 으로) 덮어쓰기가
    "표준 팔레트에 없다" 갈래로 떨어져 아무것도 안 바뀌고, 그러면 경로 A(여전히
    "블루")와 경로 B(여전히 crimson) 가 갈린다 — 위 교차 확인이 실제로 이
    코드에 의존한다는 증거."""

    def test_disabling_color_resolution_breaks_cross_path_identity(self, monkeypatch):
        import server.orchestrator.tools as tools_module

        monkeypatch.setattr(tools_module._COLOR_NAMES, "resolve_color_name", lambda _name: None)

        selections, notes = _path_b_selections(records=_records("modulate"))
        assert notes, "날조 대조군이 공허하다 — 실패 사유가 하나도 안 남았다"
        bundle = build_songcue_bundle(
            "t441 fabricated control",
            selections,
            sequences_section=_sequences(),
            groups_section=_groups(*FULL_RIG),
        )
        chorus_colors = {
            _rgb_tuple(_look_color(section_bundle.selection.look))
            for section_bundle in bundle.stored_sections
            if section_bundle.selection.look is not None
            and role_for_songcue_label(section_bundle.section.label) == "chorus"
        }
        # 경로 A 는 여전히 블루를 낸다(패치는 tools.py 안에만 걸었다) — 그런데
        # 경로 B 는 바뀌지 않았으므로 여전히 라벨마다 다른 색(crimson/acid)이다.
        # 즉 두 경로가 갈린다 — 위 GREEN(교차 일치)이 우연이 아니라는 증거.
        assert chorus_colors == {(100, 0, 15), (72, 100, 0)}
        assert _BLUE_RGB not in chorus_colors
        assert chorus_colors != {_BLUE_RGB}


# =============================================================================
# 표 — 실행 증거
# =============================================================================


class TestWriteTheCrossPathReport:
    def test_write_the_report(self):
        lines = [
            "# t441 — 구간별 주색 결정, 두 조립 경로 대조 (SPEC-LDDESIGN-001 REQ-003)",
            "",
            "명령: `uv run pytest server/tests/test_chorus_color_two_paths_t441.py -q`",
            "",
            "카드 t439(`chorus_color_two_paths_t439.md`)는 두 경로가 서로 다른 색"
            " 표현 공간(이름 팔레트 vs 룩 라이브러리 RGB)을 쓴다는 것을 실측했다."
            " 이 카드는 그 간극을 메운다 — 경로 B(`prepare_songcue`)가 세션의"
            " Q2(팔레트)·Q2B(색 운용) 답을 `interview_records` 로 받아, 경로 A와"
            " **같은 함수**(`section_palette._section_palette_choice`)로 정한"
            " 주색을 이미 고른 룩의 ColorRGB 위에 덮는다.",
            "",
            "곡: Intro 1 + 후렴류 3회(라벨 Chorus/Verse/Drop/Chorus — Drop 은 §6"
            " 「chorus · drop」 행이라 Chorus 와 같은 **역할**). 팔레트 답: "
            f"`{_PALETTE_ANSWER}` (표준 팔레트 8번 Blue, RGB {_BLUE_RGB}).",
            "",
        ]
        for color_usage in ("modulate", "per_chorus"):
            path_a_rows = _path_a_colors(color_usage=color_usage)
            path_b_rows = _path_b_colors(color_usage=color_usage)
            lines += [
                f"## color_usage = {color_usage}",
                "",
                "| 구간 | 역할 | 경로 A 주색 | 경로 B ColorRGB | 일치 |",
                "|---|---|---|---|---|",
            ]
            for (a_label, a_role, a_colors), (b_label, _b_role, b_colors) in zip(
                path_a_rows, path_b_rows, strict=True
            ):
                a_primary = a_colors[0] if a_colors else None
                b_rgb = _rgb_tuple(b_colors)
                match = "PASS" if b_rgb == _BLUE_RGB and a_primary == _PALETTE_ANSWER else "FAIL"
                lines.append(
                    f"| A:{a_label}/B:{b_label} | {a_role} | {a_primary} | {b_rgb} | {match} |"
                )
            lines.append("")

        lines += [
            "## 대조군",
            "",
            "- 기록 없음(`records=None`) / Q2 미답 → 경로 B 선택 변경 없음 "
            "(`TestRecordsAbsentIsByteIdenticalToToday` — PASS), 후렴 룩은 여전히"
            " `edm-drop-crimson` (100,0,15).",
            "- 날조 대조군(`resolve_color_name` 무력화) → 경로 B 는 crimson 그대로,"
            " 경로 A 는 여전히 블루 — 교차 확인이 실제로 이 코드에 의존함을 보인다"
            " (`TestFabricatedControl` — PASS).",
            "",
            "## 안 잰 것",
            "",
            "- 보조색(`colors[1]`) 은 경로 B 로 옮기지 않는다 — 경로 A 의 콘솔 명령"
            " 생성기(`_song_color_value_lines`)도 주색 한 줄만 내므로 대칭이다."
            " 회차 사다리(모듈레이트 회전·per_chorus 액센트)는 전부 이 축에 살아서"
            ' 이 표에는 드러나지 않는다 — "메인 컬러 중심" 불변식(카드 t409)이'
            " 주색을 역할·회차·색 운용과 무관하게 고정하기 때문이다.",
            "- 실기 콘솔 0회 — 가짜 실행 포트(`_RecordingPort`)·가짜 상태 포트"
            " (`_SongCueStatePort`) 위에서만 돈다(이 SPEC 의 다른 회차들과 같은"
            " 관행).",
        ]
        _REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        _REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
        assert _REPORT_PATH.exists()


class TestToolsetEmitsDirectorColorInCommands:
    """카드 t441 레인 검수 — 위 툴셋 시험은 "실패 메모 없음"만 봐서, 실제
    호출 자리(``prepare_songcue`` 안 ``_override_songcue_main_color``)를
    빼도 통과했다(변이 시험). 여기서는 도구가 **실제로 내보내는 명령**의
    색 값을 본다."""

    _BLUE = (
        "Attribute 'ColorRGB_R' At 5 ; Attribute 'ColorRGB_G' At 20 ; Attribute 'ColorRGB_B' At 100"
    )
    _CRIMSON = (
        "Attribute 'ColorRGB_R' At 100 ; Attribute 'ColorRGB_G' At 0 ; Attribute 'ColorRGB_B' At 15"
    )

    def _commands(self, port) -> list[str]:
        wiring = TestToolsetWiring()
        registry = wiring._registry(interview_records=port) if port else wiring._registry()
        _execution, payload = wiring._dispatch(registry)
        return [entry["command"] for entry in payload["commands"]]

    def test_records_present_chorus_commands_carry_director_blue(self):
        commands = self._commands(_RecordsPort(_records("modulate")))
        assert any(self._BLUE in command for command in commands)
        assert not any(self._CRIMSON in command for command in commands)

    def test_records_absent_commands_keep_the_look_library_colour(self):
        """대조군 — 인터뷰 기록이 없으면 오늘처럼 룩 라이브러리 색(crimson)."""
        commands = self._commands(None)
        assert any(self._CRIMSON in command for command in commands)
