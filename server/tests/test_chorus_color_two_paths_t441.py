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
from server.orchestrator.tools import (
    build_toolset,
)
from server.spatial.position_cuesheet import PositionSheetSection
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


# =============================================================================
# 교차 확인 — 같은 곡, 같은 답, 두 경로
# =============================================================================


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


# =============================================================================
# 표 — 실행 증거
# =============================================================================


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

    def test_records_absent_uses_the_q2_default_palette_not_a_look_colour(self):
        """대조군 — 인터뷰 기록이 없으면 대화 길 Q2 카드의 추천 1순위 팔레트를 쓴다
        (카드 t480, 감독 결정 D4). 업로드 길이 조립기로 합쳐져 룩 라이브러리 색
        (crimson)은 더 이상 나가지 않는다(D1).

        이 시험의 장르(``edm``)는 추천 팔레트 첫 토큰이 색 이름이 아니라서('단색')
        색 줄이 0 이 된다 — 카드 t483 이 따로 고친다. 여기서는 출처만 잰다."""
        wiring = TestToolsetWiring()
        _execution, payload = wiring._dispatch(wiring._registry())
        commands = [entry["command"] for entry in payload["commands"]]
        assert payload["palette"]["source"] == "q2_default"
        assert "edm" in payload["palette"]["label"]
        assert not any(self._CRIMSON in command for command in commands)
