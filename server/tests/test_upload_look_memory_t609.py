"""카드 t609 — 업로드 길(``prepare_songcue``)도 한 쇼 안 연속 곡을 앞 곡과 다르게 연다.

t491 은 대화 길(``run_instruction`` → ``_song_compose``)만 배선했다. 같은 조립 함수를
부르는 업로드 길(``upload_song_plan.py`` → ``_build_unified_song_plan``)은 오프셋을 안
넘겨 효과가 0 이었다. 여기 고정하는 것:

- 기억 창을 받은 업로드 길은 둘째 곡을 첫 곡과 다른 첫 큐 룩으로 연다.
- 창이 없으면 오늘과 같다(오프셋 0).
- 「앞 곡 룩 허용」에 해당하는 ``avoid_previous_looks=false`` 면 감독 답 그대로.
- 콘솔 저장에 실패한 곡은 기억에 안 들어간다.
- 세션은 대화 길과 **같은 목록**을 업로드 길에 넘긴다(죽은 배선이 아니다).

콘솔 접촉 0건 — 가짜 실행 포트·가짜 상태 포트만 쓴다(t480 업로드 시험과 같은 하네스).
"""

from __future__ import annotations

import json

from server.llm.types import ToolCall
from server.orchestrator.tools import build_toolset
from server.tests.test_chorus_color_two_paths_t441 import _records, _RecordsPort
from server.tests.test_looks_tool import _RecordingPort
from server.tests.test_songcue_tool import _SongCueStatePort, _tree
from server.tests.upload_console_fixture import POSITION_START
from server.web.session import ChatSession, _SongLookMemoryView

_SECTIONS = (("Intro", "0:00"), ("Verse", "0:20"), ("Chorus", "0:40"), ("Outro", "1:00"))


class _Memory:
    def __init__(self):
        self.history: list = []


class _StoreFailingPort(_RecordingPort):
    """``Store Sequence`` 로 시작하는 명령을 콘솔이 거부한다(저장 실패)."""

    def execute(self, command: str):
        if command.startswith("Store Sequence"):
            self.failures.add(command)
        return super().execute(command)


def _registry(memory, port=None):
    return build_toolset(
        execution_port=port or _RecordingPort(),
        state_port=_SongCueStatePort(_tree()),
        interview_records=_RecordsPort(_records("modulate")),
        **({} if memory is None else {"song_look_memory": memory}),
    )


def _song(registry, **extra):
    payload = {
        "song_title": "Upload Look Memory",
        "genre": "rock",
        "timecode_number": 7,
        "preset_start": POSITION_START,
        "sections": [{"name": name, "start": start} for name, start in _SECTIONS],
    }
    payload.update(extra)
    execution = registry.dispatch(ToolCall(id="t609", name="prepare_songcue", arguments=payload))
    return execution, json.loads(execution.result.content)


class TestUploadPath:
    def test_the_second_song_in_one_show_opens_with_a_different_look(self):
        memory = _Memory()
        registry = _registry(memory)

        _song(registry)
        first = memory.history[0][0]
        _, payload = _song(registry)

        assert len(memory.history) == 2, "저장된 두 곡이 모두 기억돼야 한다"
        assert payload["look_offset"] > 0
        assert memory.history[1][0] != first, f"둘째 곡이 첫 곡과 같은 룩으로 열렸다: {first}"
        assert "앞 곡 룩 허용" in payload["look_note_ko"]

    def test_without_the_memory_window_the_upload_path_is_today(self):
        registry = _registry(None)

        _, first = _song(registry)
        _, second = _song(registry)

        assert first["look_offset"] == 0
        assert second["look_offset"] == 0
        assert "look_note_ko" not in second

    def test_the_operator_can_keep_the_previous_look_for_one_song(self):
        memory = _Memory()
        registry = _registry(memory)
        _song(registry)

        _, payload = _song(registry, avoid_previous_looks=False)

        assert payload["look_offset"] == 0
        assert len(memory.history) == 2, "끈 곡도 저장됐으니 기억에 들어간다"
        assert memory.history[1][0] == memory.history[0][0]

    def test_a_non_boolean_switch_is_refused(self):
        execution, _ = _song(_registry(_Memory()), avoid_previous_looks="no")
        assert execution.result.is_error

    def test_a_song_the_console_refused_to_store_is_not_remembered(self):
        memory = _Memory()

        _song(_registry(memory, port=_StoreFailingPort()))

        assert memory.history == []


class TestSessionWiring:
    def test_the_session_hands_its_own_list_to_the_upload_path(self, monkeypatch, tmp_path):
        """t486 이 지운 ``SongLookMemory`` 는 넘겨도 아무도 안 읽었다. 이번 창은 세션이
        ``build_toolset`` 에 실제로 넘기고, 그 ``history`` 는 대화 길이 쓰는 목록 자체다."""
        import server.web.session as session_module
        from server.tests.test_runner_self_correction import ScriptedProvider
        from server.tests.test_web_session import _session

        seen: dict = {}
        original = session_module.build_toolset

        def capture(**kwargs):
            seen.update(kwargs)
            return original(**kwargs)

        monkeypatch.setattr(session_module, "build_toolset", capture)
        session, *_ = _session(tmp_path, ScriptedProvider([]))

        assert isinstance(session, ChatSession)
        window = seen.get("song_look_memory")
        assert isinstance(window, _SongLookMemoryView)
        assert window.history is session._song_look_history
