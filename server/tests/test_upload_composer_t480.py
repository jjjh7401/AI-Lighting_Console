"""카드 t480 — 업로드 길(``prepare_songcue``)이 대화 길 조립기로 큐를 만든다.

SPEC-LDDESIGN-001 REQ-003 · AC-017 「큐 생성 경로가 하나다」. 감독 결정(2026-09-28):

* D1 — 업로드 길의 장르 룩 라이브러리·곡 사이 룩 기억은 사라진다.
* D2 — 선택 인자 ``preset_start`` 가 있으면 포지션 라벨로 슬롯을 찾고, 없으면 포지션
  축을 끄고 사유를 회신에 적는다. 번호를 지어내지 않는다.
* D4 — 인터뷰가 없으면 대화 길 Q2 카드 추천 1순위를 팔레트로 쓰고 회신에 적는다.
  영어 장르 다섯 단어는 §7 표의 한국어 키로 바꾼다.

콘솔 접촉 0건 — 가짜 실행 포트·가짜 상태 포트만 쓴다.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from server.design.rig import build_rig_profile
from server.design.song_cue_render import _build_unified_song_plan
from server.design.song_plan import TimingPlan
from server.design.upload_song_plan import (
    UPLOAD_GENRE_KEYS,
    build_upload_song_plan,
    upload_genre_key,
    upload_plan_sections,
    upload_profile,
)
from server.llm.types import ToolCall
from server.looks.songcue import parse_sections
from server.orchestrator.tools import build_toolset
from server.tests.test_chorus_color_two_paths_t441 import _records, _RecordsPort
from server.tests.test_looks_tool import _RecordingPort
from server.tests.test_songcue_tool import _SongCueStatePort, _tree
from server.tests.upload_console_fixture import POSITION_START

_TOOLS = Path("server/orchestrator/tools.py")
_SECTIONS = (("Intro", "0:00"), ("Verse", "0:20"), ("Chorus", "0:40"), ("Outro", "1:00"))


def _handler() -> ast.FunctionDef:
    tree = ast.parse(_TOOLS.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "prepare_songcue":
            return node
    raise AssertionError("prepare_songcue handler not found")


def _called(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            func = sub.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                names.add(func.attr)
    return names


def _dispatch(**arguments):
    port = _RecordingPort()
    records = arguments.pop("records", None)
    registry = build_toolset(
        execution_port=port,
        state_port=_SongCueStatePort(_tree()),
        **({} if records is None else {"interview_records": _RecordsPort(records)}),
    )
    payload = {
        "song_title": "Upload Composer",
        "genre": "rock",
        "timecode_number": 7,
        "sections": [{"name": name, "start": start} for name, start in _SECTIONS],
    }
    payload.update(arguments)
    execution = registry.dispatch(ToolCall(id="t480", name="prepare_songcue", arguments=payload))
    return port, execution, json.loads(execution.result.content)


class TestOneComposer:
    """AC-017 — 업로드 입구가 대화 길과 같은 조립기와 같은 명령 생성기를 부른다."""

    def test_the_upload_handler_calls_the_composer_and_the_shared_renderer(self):
        called = _called(_handler())
        assert "compose_song_cue_bundle" in called
        assert "reviewed_song_commands" in called
        assert "build_upload_song_plan" in called

    def test_the_upload_handler_no_longer_calls_the_look_library_assembler(self):
        called = _called(_handler())
        assert "build_songcue_bundle" not in called
        assert "map_sections_to_looks" not in called

    def test_the_upload_plan_is_the_chat_paths_plan_for_the_same_input(self):
        """같은 구간·같은 프로필·같은 기록이면 두 길이 **같은 계획**을 짓는다.

        업로드 어댑터는 계획 조립(``_build_unified_song_plan`` — 대화 길이 부르는 그
        함수)에 입력 모양만 바꿔 넘긴다. 곡 제목·시퀀스 이름만 업로드 길 값으로 바뀐다.
        """
        sections = upload_plan_sections(
            parse_sections(_SECTIONS), explicit_dynamics=None, confirmed_default=False
        )
        rig = build_rig_profile(patch=[], groups={}, coords=[])
        records = _records("modulate")
        plan, _notes, _palette = build_upload_song_plan(
            song_title="X",
            sections=sections,
            bpm=None,
            genre="rock",
            records=records,
            rig=rig,
            sequence_no=9,
            timing=TimingPlan.timecode(7),
        )
        profile, _source = upload_profile(bpm=None, genre="rock", records=records)
        chat = _build_unified_song_plan(
            sections=sections,
            profile=profile,
            rig=rig,
            records=records,
            timing=TimingPlan.timecode(7),
            sequence_no=9,
        )
        assert plan.sections == chat.sections
        assert plan.music_profile == chat.music_profile


class TestPositionAxis:
    """D2 — 번호를 지어내지 않는다."""

    def test_without_preset_start_no_position_is_recalled_and_the_reply_says_why(self):
        port, execution, payload = _dispatch()
        assert execution.result.is_error is False
        assert not any("At Preset 2." in command for command in port.executed)
        assert any("preset_start" in note for note in payload["report"]["notes"])

    def test_with_preset_start_positions_are_recalled_from_that_pool_by_label(self):
        port, execution, _payload = _dispatch(preset_start=POSITION_START)
        assert execution.result.is_error is False
        assert any(f"At Preset 2.{POSITION_START}" in command for command in port.executed)

    @pytest.mark.parametrize("bad", [0, -3, True, "21", 2.5])
    def test_a_bad_preset_start_is_refused_before_any_write(self, bad):
        port, execution, payload = _dispatch(preset_start=bad)
        assert execution.result.is_error is True
        assert "'preset_start'" in payload["error"]
        assert port.executed == []

    def test_the_schema_advertises_preset_start_as_optional(self):
        registry = build_toolset(execution_port=_RecordingPort(), state_port=None)
        definition = next(d for d in registry.definitions() if d.name == "prepare_songcue")
        assert "preset_start" in definition.parameters["properties"]
        assert "preset_start" not in definition.parameters["required"]


class TestPaletteSource:
    """D4 — 인터뷰가 없으면 Q2 추천 1순위, 있으면 인터뷰 답. 회신이 출처를 말한다."""

    def test_no_interview_uses_the_q2_recommendation_and_says_so(self):
        _port, _execution, payload = _dispatch()
        assert payload["palette"]["source"] == "q2_default"
        assert payload["palette"]["label"] == "록 느낌 색 조합"
        assert any("인터뷰 없음" in note for note in payload["report"]["notes"])

    def test_the_interview_answer_wins_when_it_exists(self):
        _port, _execution, payload = _dispatch(records=_records("modulate"))
        assert payload["palette"]["source"] == "interview"

    def test_a_genre_outside_the_table_falls_to_the_mood_table_and_says_why(self):
        _port, _execution, payload = _dispatch(genre="jazz")
        assert payload["palette"]["source"] == "q2_default"
        assert payload["palette"]["genre_in_table"] is False
        assert any("장르 표에 없어" in note for note in payload["report"]["notes"])


class TestGenreKeys:
    @pytest.mark.parametrize(("word", "key"), sorted(UPLOAD_GENRE_KEYS.items()))
    def test_the_five_english_words_map_to_the_table_keys(self, word, key):
        assert upload_genre_key(word) == key
        assert upload_genre_key(word.upper()) == key

    def test_other_words_pass_through_unchanged(self):
        assert upload_genre_key("워십") == "워십"
        assert upload_genre_key(None) is None


class TestSequenceName:
    """옛 업로드 길과 같은 시퀀스 이름 — 콘솔 라벨과 타임코드 이름이 같은 값을 쓴다."""

    def test_the_sequence_is_labelled_once_after_the_first_store(self):
        port, _execution, _payload = _dispatch()
        labels = [c for c in port.executed if c.startswith("Label Sequence ")]
        assert labels == ["Label Sequence 3 'Upload Composer'"]
        first_store = next(i for i, c in enumerate(port.executed) if c.startswith("Store Sequence"))
        assert port.executed[first_store + 1] == labels[0]

    def test_the_timecode_name_uses_the_same_sequence_name(self):
        _port, _execution, payload = _dispatch()
        assert (
            "Set Timecode 7 Property 'Name' 'Upload Composer Timecode'"
            in (payload["timing"]["timecode_commands"])
        )
