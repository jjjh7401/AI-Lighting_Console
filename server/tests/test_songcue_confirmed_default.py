"""SPEC-COPILOT-SONGCONFIRM-001 M2 — 도달: 도구 · 모델 · 운영자.

AC-SONGCONFIRM-007 ~ 014. 콘솔 접촉 0건 — 가짜 실행 포트(``_RecordingPort``)와 가짜
상태 포트(``_SongCueStatePort``), 대화를 붙잡는 ``ScriptedProvider`` 위에서만 돈다.
AC-010·011 의 번들도 ``run_commands`` 경로로 그 가짜 포트에 머문다(실기 0).

층 경계: 이 SPEC 은 ``server.orchestrator.tools`` 에 ``server.web`` import 를 **더하지
않는다**(BASE 에 이미 있던 ``server.web.question`` 한 줄만 그대로다 — 아래
``test_tools_adds_no_server_web_import`` 참조). 도구가 세션의 확정 기록에 닿는 통로는
``build_toolset(song_analysis=<읽기 투과 뷰>)`` 하나이고, 여기서는 실제
:class:`ConfirmedSongAnalysis` 를 ``current`` 로 내주는 가짜 뷰를 넘긴다.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from server.design.profile import DEFAULT_BPM, BpmResolution
from server.llm.types import ToolCall, UserMessage
from server.looks.songcue import parse_sections
from server.orchestrator.tools import build_toolset
from server.web.question import (
    UNANSWERED,
    ConfirmedSongAnalysis,
    ConfirmedSongSection,
    SongSectionProposal,
    section_label,
)

from .test_looks_tool import _RecordingPort
from .test_runner_self_correction import ScriptedProvider, _final
from .test_song_confirm_sections import _LABELS, _analysed, _joined
from .test_songcue_tool import _library, _look, _SongCueStatePort, _tree
from .test_web_session import _session as _model_session
from .test_web_song_audio import _session as _plain_session

_TOOL = "prepare_songcue"
_TODAY_SECTIONS_ERROR = "'sections' must be a non-empty array of song sections"
_SERVER = Path("server")
_TOOLS_MODULE = _SERVER / "orchestrator" / "tools.py"
_SESSION_MODULE = _SERVER / "web" / "session.py"

# AC-008 · AC-010 의 기록: 채택 3(start_ms 0 / 15952 / 32020, D1 / D3 / D5) · 제외 1.
_ACCEPTED = ((0, 15_952, 1), (15_952, 32_020, 3), (32_020, 36_000, 5))
_DROPPED = (36_000, 40_000, 2)
_SHA = "373351cd" + "0" * 56


def _section(index: int, start_ms: int, end_ms: int, d_level: int, selected: bool):
    proposal = SongSectionProposal(start_ms=start_ms, end_ms=end_ms, d_level=d_level)
    return ConfirmedSongSection(
        index=index,
        label=section_label(proposal),
        start_ms=start_ms,
        end_ms=end_ms,
        d_level=d_level,
        selected=selected,
    )


def _record(accepted=_ACCEPTED, dropped=(_DROPPED,)) -> ConfirmedSongAnalysis:
    sections = [_section(i, *spec, True) for i, spec in enumerate(accepted)]
    sections += [_section(len(accepted) + i, *spec, False) for i, spec in enumerate(dropped)]
    return ConfirmedSongAnalysis(
        source_sha256=_SHA,
        source_file_name="track.wav",
        confirmed_at="2026-09-06T12:00:00+00:00",
        bpm=BpmResolution(bpm=129.199, source="measured", reason="채택 우선순위."),
        sections=tuple(sections),
    )


class _AnalysisPort:
    """``SongAnalysisPort`` 의 가짜 — ``current`` 하나."""

    def __init__(self, record: ConfirmedSongAnalysis | None) -> None:
        self.current = record


def _hold(session, record: ConfirmedSongAnalysis) -> None:
    """세션에 기록을 직접 심는다 — REQ-006 불변식(``record.bpm is song_bpm``)까지 같이.

    ``analyse_song_audio`` 를 지나면 두 필드가 같은 객체를 들게 되므로, 지름길로
    심을 때도 그 형상을 지킨다. 기록만 심으면 ``song_bpm`` 이 ``None`` 인 세션이 되고,
    그것은 생산에서 생길 수 없는 상태다.
    """
    session._song_analysis = record
    session._song_bpm = record.bpm


def _five_dynamics_library():
    # dynamics 1..5 마다 룩 하나, Dimmer 값을 다르게 — 어느 룩이 골라졌는지 명령의
    # ``Attribute 'Dimmer' At <값>`` 줄로 읽는다(값이 같으면 value-line 충돌로 접힌다).
    return _library(*(_look(f"d{n}", dynamics=n, value=n * 10) for n in range(1, 6)))


def _registry(*, song_analysis=None, port=None, library=None):
    port = port or _RecordingPort()
    registry = build_toolset(
        execution_port=port,
        state_port=_SongCueStatePort(_tree()),
        look_library=library if library is not None else _five_dynamics_library(),
        **({} if song_analysis is None else {"song_analysis": song_analysis}),
    )
    return registry, port


def _call(registry, **arguments):
    import json

    payload = {"song_title": "테스트 곡", "genre": "록", "timecode_number": 7}
    payload.update(arguments)
    execution = registry.dispatch(ToolCall(id="songcue-1", name=_TOOL, arguments=payload))
    return execution, json.loads(execution.result.content)


def _dimmer_values(payload) -> list[int]:
    values = []
    for entry in payload["commands"]:
        match = re.fullmatch(r"Attribute 'Dimmer' At (\d+)", entry["command"])
        if match:
            values.append(int(match.group(1)))
    return values


# =============================================================================
# 도구 — prepare_songcue 기본값 · 명시 우선 · 오늘 오류 · 스키마
# =============================================================================


class TestConfirmedSectionsAreTheDefault:
    """AC-SONGCONFIRM-010 ↔ REQ-009 (B2 · B3 포함)."""

    def test_omitting_sections_uses_the_confirmed_sections(self):
        registry, port = _registry(song_analysis=_AnalysisPort(_record()))
        execution, payload = _call(registry)
        assert execution.result.is_error is False
        assert payload["sections_source"] == "confirmed_analysis"
        assert len(payload["report"]["sections"]) == 3
        # 손실 0 — start_ms 가 정확히 옮겨진다(B2). ``report.sections`` 는 server/looks
        # 소유라 키를 더할 수 없어(REQ-014 보존 경계) 도구 페이로드에 싣는다.
        used = payload["confirmed_sections"]
        assert [s["start_ms"] for s in used] == [0, 15_952, 32_020]
        assert [s["dynamics"] for s in used] == [1, 3, 5]
        names = [s["name"] for s in payload["report"]["sections"]]
        assert names == ["S1", "S2", "S3"]
        assert all(name.isascii() for name in names)
        # 같은 raw 구간을 오늘의 파서로 다시 넣어도 손실 0 이고, 중립 이름은 라이브러리
        # 어휘 밖이다(B3) — dynamics 는 d_level 에서 명시 경로로 온다.
        parsed = parse_sections([{"name": s["name"], "start": s["start"]} for s in used])
        assert [p.start_ms for p in parsed] == [0, 15_952, 32_020]
        assert all(p.requires_explicit_dynamics is True for p in parsed)
        # 골라진 룩의 dynamics 가 1 / 3 / 5 다.
        assert _dimmer_values(payload) == [10, 30, 50]
        # 번들은 오늘 ``TestPayload`` 와 같은 경로(run_commands → 가짜 실행 포트)로 갔다.
        assert any(command.startswith("Store Timecode 7") for command in port.executed)
        assert any(command.startswith("Store Sequence") for command in port.executed)

    @pytest.mark.parametrize("start_ms", [0, 7, 999, 59_999, 60_000, 61_001, 3_599_999, 3_600_000])
    def test_start_ms_round_trips_without_loss(self, start_ms):
        # B2 — ``normalise_start_ms`` 는 bare int 를 초로 읽으므로 그 갈래를 타면 안 된다.
        record = _record(accepted=((start_ms, start_ms + 1000, 3),), dropped=())
        registry, _port = _registry(song_analysis=_AnalysisPort(record))
        _execution, payload = _call(registry)
        assert payload["sections_source"] == "confirmed_analysis"
        assert payload["confirmed_sections"][0]["start_ms"] == start_ms
        parsed = parse_sections(
            [{"name": s["name"], "start": s["start"]} for s in payload["confirmed_sections"]]
        )
        assert parsed[0].start_ms == start_ms


class TestExplicitSectionsWinAndMismatchIsReported:
    """AC-SONGCONFIRM-011 ↔ REQ-010."""

    def test_explicit_sections_are_used_and_the_mismatch_is_side_by_side(self):
        registry, _port = _registry(song_analysis=_AnalysisPort(_record()))
        _execution, payload = _call(
            registry,
            sections=[{"name": "Intro", "start": "0:00"}, {"name": "Chorus", "start": "0:20"}],
        )
        assert payload["sections_source"] == "explicit"
        assert [s["name"] for s in payload["report"]["sections"]] == ["Intro", "Chorus"]
        mismatch = payload["confirmed_analysis_mismatch"]
        assert mismatch["matches"] is False
        assert mismatch["explicit_count"] == 2
        assert mismatch["confirmed_count"] == 3
        assert mismatch["start_pairs"][1] == [20_000, 15_952]
        assert mismatch["start_pairs"][2] == [None, 32_020]
        assert "confirmed_sections" not in payload

    def test_matching_explicit_sections_report_a_match(self):
        # 대조군 — 시작·개수가 전부 같으면 matches True.
        registry, _port = _registry(song_analysis=_AnalysisPort(_record()))
        _execution, payload = _call(
            registry,
            sections=[
                {"name": "Intro", "start": "0:00"},
                {"name": "Verse", "start": "0:15.952"},
                {"name": "Chorus", "start": "0:32.020"},
            ],
        )
        assert payload["sections_source"] == "explicit"
        assert payload["confirmed_analysis_mismatch"]["matches"] is True
        assert payload["confirmed_analysis_mismatch"]["start_pairs"] == [
            [0, 0],
            [15_952, 15_952],
            [32_020, 32_020],
        ]


class TestNoRecordMeansTodaysError:
    """AC-SONGCONFIRM-012 [부정 대조군] ↔ REQ-011 · 015."""

    def test_without_a_port_the_error_is_byte_identical(self):
        registry, _port = _registry()
        execution, payload = _call(registry)
        assert execution.result.is_error is True
        assert payload["error"] == _TODAY_SECTIONS_ERROR

    def test_with_an_empty_port_the_error_is_byte_identical(self):
        registry, _port = _registry(song_analysis=_AnalysisPort(None))
        execution, payload = _call(registry)
        assert execution.result.is_error is True
        assert payload["error"] == _TODAY_SECTIONS_ERROR

    def test_without_a_record_explicit_sections_carry_no_mismatch_report(self):
        registry, _port = _registry()
        _execution, payload = _call(
            registry,
            sections=[{"name": "Intro", "start": "0:00"}, {"name": "Chorus", "start": "0:20"}],
        )
        assert payload["sections_source"] == "explicit"
        assert "confirmed_analysis_mismatch" not in payload


class TestTheSchemaMakesSectionsOptional:
    """AC-SONGCONFIRM-013 ↔ REQ-011 · 012."""

    def test_required_keeps_the_three_and_sections_describes_the_default(self):
        registry, _port = _registry()
        definition = next(d for d in registry.definitions() if d.name == _TOOL)
        assert set(definition.parameters["required"]) == {"song_title", "genre", "timecode_number"}
        properties = definition.parameters["properties"]
        assert "confirmed" in properties["sections"]["description"]
        assert properties["timecode_number"]["description"] == (
            "Positive Timecode object number to create for this draft."
        )


# =============================================================================
# 세션 — 확정 고지 · 세션 노트 · 모델 도달
# =============================================================================


class TestTheConfirmationNoticeNamesSectionsAndTheNextStep:
    """AC-SONGCONFIRM-007 ↔ REQ-013."""

    def test_two_accepted_two_dropped(self, tmp_path, monkeypatch):
        events: list[dict] = []
        _analysed(tmp_path, monkeypatch, _joined(_LABELS[0], _LABELS[2]), events)
        message = events[-1]["message"]
        assert "BPM 129.199 로 확정했습니다 (measured)." in message
        assert "구간 2건 채택" in message
        assert "2건 제외" in message
        assert "큐 리스트" in message
        assert "말씀해 주세요" in message

    def test_an_unanswered_card_keeps_todays_notice(self, tmp_path, monkeypatch):
        # 대조군 — 기록이 안 생긴 갈래의 고지는 오늘 문면과 문자열 동일하다.
        events: list[dict] = []
        session, _channel = _analysed(tmp_path, monkeypatch, UNANSWERED, events)
        assert session.song_analysis is None
        assert events[-1]["message"] == (
            f"BPM 은 확정되지 않았습니다 — 기본값 {DEFAULT_BPM:g} 로 남습니다. "
            "채택 우선순위: 측정 > 시트 HEAD.BPM > 기본값 120."
        )


class TestTheSessionNoteCarriesTheRecord:
    """AC-SONGCONFIRM-008 ↔ REQ-007 · 008."""

    def test_the_note_names_everything_the_model_needs(self, tmp_path):
        session = _plain_session(tmp_path)
        _hold(session, _record())
        note = session._session_context_note()
        assert note is not None
        for needle in (
            "Session context —",
            "track.wav",
            "373351cd",
            "129.199",
            "measured",
            "0:00–0:15",
            "D1",
            "0:15–0:32",
            "D3",
            "0:32–0:36",
            "D5",
            "dropped 1",
            "prepare_songcue",
            "sections",
            "timecode_number",
        ):
            assert needle in note, needle
        assert "0:36–0:40" not in note  # 제외된 구간은 채택 목록에 없다

    def test_without_a_record_the_note_is_none(self, tmp_path):
        # 대조군 — test_web_session.py 의 ``_session_context_note() is None`` 과 같다.
        assert _plain_session(tmp_path)._session_context_note() is None


class TestTheNoteReachesTheModel:
    """AC-SONGCONFIRM-009 ↔ REQ-007 — 기존 통로(handle_instruction session_context)."""

    def test_the_synthetic_user_message_precedes_the_instruction(self, tmp_path):
        provider = ScriptedProvider([_final("ok")])
        session, _console, _audit, _sent, _channel = _model_session(tmp_path, provider)
        _hold(session, _record())
        session.run_instruction("안녕")
        conversation = provider.calls[0]
        assert isinstance(conversation[-1], UserMessage)
        assert conversation[-1].text == "안녕"
        note = conversation[-2]
        assert isinstance(note, UserMessage)
        assert "prepare_songcue" in note.text
        for label in ("0:00–0:15 · D1", "0:15–0:32 · D3", "0:32–0:36 · D5"):
            assert label in note.text

    def test_without_a_record_the_instruction_stands_alone(self, tmp_path):
        provider = ScriptedProvider([_final("ok")])
        session, _console, _audit, _sent, _channel = _model_session(tmp_path, provider)
        session.run_instruction("안녕")
        conversation = provider.calls[0]
        assert len(conversation) == 1
        assert conversation[0].text == "안녕"


# =============================================================================
# 횡단 — 생산 호출자(AC-014) · 층 경계
# =============================================================================


def _production_lines(pattern: str, *paths: Path) -> list[str]:
    hits = []
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            if pattern in line and not line.lstrip().startswith("#"):
                hits.append(f"{path}: {line.strip()}")
    return hits


def _production_modules() -> list[Path]:
    return [p for p in _SERVER.rglob("*.py") if "tests" not in p.parts]


class TestEveryNewEntryPointHasAProductionCaller:
    """AC-SONGCONFIRM-014 ↔ REQ-016 — acceptance.md 의 다섯 grep 을 파일 판독으로 옮겼다."""

    def test_the_section_parser_is_called_from_production(self):
        hits = _production_lines("parse_confirmed_sections(", *_production_modules())
        hits = [h for h in hits if "def parse_confirmed_sections" not in h]
        assert hits, "①"

    def test_the_record_is_built_in_production(self):
        hits = _production_lines("ConfirmedSongAnalysis(", *_production_modules())
        hits = [h for h in hits if "class ConfirmedSongAnalysis" not in h]
        assert hits, "②"

    def test_the_session_passes_the_port_to_build_toolset(self):
        assert _production_lines("song_analysis=", _SESSION_MODULE), "③"

    def test_the_handler_reads_the_port_and_the_keyword_is_declared_once(self):
        assert _production_lines("song_analysis.current", _TOOLS_MODULE), "④"
        text = _TOOLS_MODULE.read_text(encoding="utf-8")
        assert text.count("song_analysis: SongAnalysisPort") == 1, "④ 키워드 인자 1건"

    def test_song_bpm_has_a_production_reader(self):
        excluded = (
            "self._song_bpm: BpmResolution",
            "self._song_bpm = resolution",
            "return self._song_bpm",
        )
        hits = []
        for line in _production_lines(".song_bpm", *_production_modules()) + _production_lines(
            "_song_bpm", *_production_modules()
        ):
            if not any(marker in line for marker in excluded):
                hits.append(line)
        assert hits, "⑤"

    def test_tools_adds_no_server_web_import(self):
        # 층 경계(spec.md §E). 실측: BASE fc65860 의 tools.py:234 는 이미
        # ``from server.web.question import UNANSWERED, QuestionOption, QuestionRequest``
        # 를 갖고 있다 — 그 한 줄은 이 SPEC 이전의 것이다. 이 SPEC 이 지키는 것은
        # 「새 import 를 더하지 않는다」다: 기록은 ``Protocol`` 로 받고, 세션 모듈이나
        # ``ConfirmedSongAnalysis`` 를 tools.py 가 import 하는 일은 없다.
        text = _TOOLS_MODULE.read_text(encoding="utf-8")
        web_imports = re.findall(r"^\s*(?:from|import)\s+server\.web\S*.*$", text, re.MULTILINE)
        assert web_imports == [
            "from server.web.question import UNANSWERED, QuestionOption, QuestionRequest"
        ]
        assert "server.web.session" not in text
        assert not re.search(r"^\s*(?:from|import)\s.*\bConfirmedSongAnalysis\b", text, re.M)
