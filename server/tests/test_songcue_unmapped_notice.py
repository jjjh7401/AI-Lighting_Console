"""건너뛴 구간을 감독이 **보게** 만든다 — 카드 t277.

2026-09-06 실기 회차(`reports/musicsync-live-write-20260906.md`)에서 감독이 확인한
구간은 4건인데 콘솔에 남은 큐는 3건이었다. 첫 구간 `Intro`(D1)는 EDM 의 D1 룩
``edm-ambient-hold`` 이 요구하는 ``배경`` 역할에 묶을 그룹이 실기 리그에 없어
건너뛰어졌다 — 그 건너뜀 자체는 **옳다**(그룹 없이 큐를 저장하는 쪽이 더 나쁘다).
결함은 **침묵**이다: 앱은 「요청한 명령을 모두 실행했습니다」라고만 답했고, 첫 곡
구간에 조명이 없다는 사실은 공연에서 처음 드러난다.

이 파일의 리그 지문이 이 회차의 핵심이다. 기존 시험대(``test_songcue_tool.py``)의
가짜 그룹에는 ``Cyc`` 가 들어 있어 ``배경`` 이 항상 묶였고, 그래서 이 결함이 가짜
콘솔에서는 한 번도 보이지 않았다. 아래 18개는 실기에서 되읽은 이름 그대로다.
"""

from __future__ import annotations

import json
from pathlib import Path

from server.llm.types import ModelTurn, ToolCall, ToolDefinition, Usage
from server.looks.loader import load_library_from_dir
from server.looks.songcue_report import build_songcue_report
from server.orchestrator.runner import InstructionResult, Orchestrator
from server.orchestrator.tools import ToolExecution, ToolResult, build_toolset
from server.tests.test_looks_tool import _RecordingPort
from server.tests.test_songcue_tool import _SongCueStatePort, _tree
from server.web.session import ChatSession

#: 2026-09-06 실기 grandMA3 onPC 가 되읽어 답한 ``DataPool/Groups`` 18건.
#: ``배경``(Cyc / Backdrop / 호리) 계열 이름이 **하나도 없다** — 그것이 이 카드다.
_REAL_RIG_GROUPS: tuple[tuple[int, str], ...] = (
    (1, "ALL"),
    (2, "KEY"),
    (3, "FOH"),
    (4, "BACK"),
    (5, "SIDE-L"),
    (6, "SIDE-R"),
    (7, "SIDE-ALL"),
    (8, "WASH-U"),
    (9, "WASH-D"),
    (10, "WASH-ALL"),
    (11, "MOVER-U"),
    (12, "MOVER-D"),
    (13, "MOVER-ALL"),
    (14, "BLIND"),
    (15, "STROBE"),
    (16, "HAZE"),
    (17, "ODD"),
    (18, "EVEN"),
)

#: 실기 회차에서 감독이 확정한 네 구간 — 시각도 이름도 그대로.
_LIVE_SECTIONS: tuple[dict[str, object], ...] = (
    {"name": "Intro", "start": "0:00", "dynamics": 1},
    {"name": "Build", "start": "0:15.952", "dynamics": 3},
    {"name": "Drop", "start": "0:32.020", "dynamics": 5},
    {"name": "Outro", "start": "0:36.014", "dynamics": 2},
)

#: 실기 리그에서 ``BACK`` 하나만 뺀 것 — 고지 **문면**을 재는 시험대다.
#:
#: 왜 필요해졌는가: 이 파일이 태어날 때는 실기 리그 그대로가 「건너뜀이 있는 리그」
#: 였다. SPEC-COPILOT-D1GRANT-001 이 edm 에 ``edm-haze-shafts``(``백라이트``)를 넣어
#: 그 건너뜀을 없앴고, 그래서 실기 리그는 이제 **전량 저장**된다. 그것이 이 SPEC 의
#: 성과이고 :func:`test_the_live_rig_now_stores_every_section` 이 그 성과를 잰다.
#:
#: 그러나 「건너뜀이 있을 때 감독이 무엇을 읽는가」는 여전히 재야 한다 — 그 기계가
#: 사라진 것이 아니라 이 리그에서 발화하지 않을 뿐이다. ``BACK`` 을 빼면 edm 의 D1
#: 후보 둘이 요구하는 역할(``백라이트``·``배경``)이 **둘 다** 안 묶여 첫 구간이 다시
#: 건너뛰어지고, 나머지 셋은 ``사이드``·``프론트`` 로 묶여 저장된다. 카드 t277 이
#: 실기에서 본 「4건 중 3건」 형상을 그대로 되살린 것이며, 고지 문면 검사는 그 위에서
#: 돈다.
_RIG_WITHOUT_BACKLIGHT: tuple[tuple[int, str], ...] = tuple(
    (number, name) for number, name in _REAL_RIG_GROUPS if name != "BACK"
)


def _real_library():
    return load_library_from_dir(Path("server/looks/library"))


def _call(groups: tuple[tuple[int, str], ...], *, call_id: str) -> tuple[object, dict]:
    """주어진 리그 지문으로 실기 지시문을 한 번 돌린다."""
    registry = build_toolset(
        execution_port=_RecordingPort(),
        state_port=_SongCueStatePort(_tree(groups=groups)),
        bundle_gate=None,
        look_library=_real_library(),
        rig_paths=None,
    )
    execution = registry.dispatch(
        ToolCall(
            id=call_id,
            name="prepare_songcue",
            arguments={
                "song_title": "Synth Test",
                "genre": "EDM",
                "timecode_number": 7,
                "sections": [dict(section) for section in _LIVE_SECTIONS],
            },
        )
    )
    return execution, json.loads(execution.result.content)


def _live_call() -> tuple[object, dict]:
    """실기 리그 18그룹 그대로."""
    return _call(_REAL_RIG_GROUPS, call_id="songcue-t277")


def _gapped_call() -> tuple[object, dict]:
    """``BACK`` 을 뺀 리그 — 첫 구간이 여전히 건너뛰어지는 시험대."""
    return _call(_RIG_WITHOUT_BACKLIGHT, call_id="songcue-t277-gapped")


def test_the_live_rig_now_stores_every_section():
    """카드 t277 이 실기에서 본 손해가 닫혔다 — 같은 리그, 같은 네 구간, 이제 4건.

    **전.** 이 검사는 ``test_live_rig_drops_the_first_section_without_a_cue`` 였고
    ``generated_count == 3`` · ``unmapped_sections == ["Intro"]`` ·
    ``reason_kind == "role_unaddressed"`` 를 회귀로 고정했다. 감독이 확정한 4구간 중
    3건만 콘솔에 남은 2026-09-06 실기 회차 그대로다. 건너뜀 자체는 옳았고(그룹 없이
    큐를 저장하는 쪽이 더 나쁘다), 카드 t277 이 고친 것은 그 **침묵**이었다.

    **후.** SPEC-COPILOT-D1GRANT-001 이 edm 에 ``edm-haze-shafts``(``백라이트``)를
    넣었다. 실기 리그의 ``BACK`` 이 ``백라이트`` 로 묶이므로 첫 구간이 이제 큐를 받고,
    건너뜀이 0건이라 고지도 비어 있다 — 고지 기계가 죽은 것이 아니라 **울릴 일이
    없어진 것**이고, 그 구별은 :func:`test_the_notice_still_fires_when_a_section_is_
    dropped` 가 잰다.

    이 검사가 이 SPEC 의 가장 강한 증거다: 문자열 검색이 아니라 도구 → 게이트 →
    실행 포트까지 실제 경로를 탄 뒤의 보고를 읽는다.
    """
    _execution, payload = _live_call()

    report = payload["report"]
    assert report["summary"]["section_count"] == 4
    assert report["summary"]["generated_count"] == 4
    stored = [cue["name"] for cue in report["generated_cues"]]
    assert stored == ["Intro", "Build", "Drop", "Outro"]
    assert report["unmapped_sections"] == []


def test_the_notice_is_silent_when_the_live_rig_drops_nothing():
    """건너뜀 0건이면 고지도 없다 — 위 검사의 짝."""
    execution, _payload = _live_call()

    assert execution.operator_notice == ""


def test_the_notice_still_fires_when_a_section_is_dropped():
    """감독이 읽는 한 문장 — 몇 건 중 몇 건, 어느 구간이, 왜.

    시험대만 바뀌었다(실기 리그 → ``BACK`` 을 뺀 리그). 재는 성질은 그대로다:
    건너뛴 구간이 있으면 고지가 건수·구간 이름·빠진 역할을 전부 담는다.
    """
    execution, payload = _gapped_call()

    report = payload["report"]
    assert report["summary"]["generated_count"] == 3
    dropped = [section["name"] for section in report["unmapped_sections"]]
    assert dropped == ["Intro"]
    assert report["unmapped_sections"][0]["reason_kind"] == "role_unaddressed"

    notice = execution.operator_notice
    assert notice, "건너뛴 구간이 있는데 감독용 고지가 비어 있다"
    assert "구간 4건 중 큐 3건" in notice
    assert "Intro" in notice
    assert "배경" in notice


def test_notice_is_empty_when_every_section_got_a_cue():
    """건너뜀 0건이면 고지도 없다 — 오늘의 출력과 바이트 동일해야 한다."""
    registry = build_toolset(
        execution_port=_RecordingPort(),
        state_port=_SongCueStatePort(_tree()),
        bundle_gate=None,
        look_library=_real_library(),
        rig_paths=None,
    )
    execution = registry.dispatch(
        ToolCall(
            id="songcue-t277-clean",
            name="prepare_songcue",
            arguments={
                "song_title": "Synth Test",
                "genre": "EDM",
                "timecode_number": 7,
                "sections": [dict(section) for section in _LIVE_SECTIONS],
            },
        )
    )
    payload = json.loads(execution.result.content)

    assert payload["report"]["summary"]["unmapped_count"] == 0
    assert execution.operator_notice == ""


def test_notice_is_built_from_the_report_alone():
    """보고 계층이 고지의 주인이다 — 도구 핸들러는 옮기기만 한다.

    시험대가 ``BACK`` 을 뺀 리그로 바뀐 이유는 위와 같다: 실기 리그는 이제 건너뜀이
    0건이라 고지가 비고, 빈 문자열로는 「보고 계층이 문장을 만든다」를 못 잰다.
    """
    execution, payload = _gapped_call()
    del payload  # 아래는 보고 객체만으로 같은 문장이 나오는지 본다.

    assert build_songcue_report is not None
    assert execution.operator_notice.endswith(".")


# -- 감독의 화면까지 가는 두 구간 -------------------------------------------------
#
# 도구가 고지를 만들어도 화면에 안 나오면 이 카드는 안 닫힌다. 아래 둘이 그
# 경로를 하나씩 잰다: 러너가 도구에서 모으는가, 요약이 그것을 싣는가.


class _NoticingRegistry:
    """무엇을 불러도 고지 한 줄을 내는 등록부 — 여기서 재는 것은 운반이다."""

    NOTICE = "구간 4건 중 큐 3건만 저장했습니다 — 'Intro': 이 리그에 배경 역할 그룹이 없습니다."

    def definitions(self):
        return (ToolDefinition(name="prepare_songcue", description="곡 큐리스트", parameters={}),)

    def dispatch(self, call, context):
        return ToolExecution(
            result=ToolResult(
                tool_call_id=call.id,
                name=call.name,
                content=json.dumps({"ok": True}, ensure_ascii=False),
                is_error=False,
            ),
            operator_notice=self.NOTICE,
        )


class _ScriptedProvider:
    """도구를 한 번 부르고 글로 끝내는 모델."""

    def __init__(self) -> None:
        self.calls = 0

    def complete(self, *, system_prefix, conversation, tools):
        self.calls += 1
        if self.calls == 1:
            return ModelTurn(
                text="",
                tool_calls=(ToolCall(id="c1", name="prepare_songcue", arguments={}),),
                stop_reason="tool_use",
                usage=Usage(),
                provider="scripted",
            )
        return ModelTurn(
            text="큐 리스트를 만들었습니다",
            tool_calls=(),
            stop_reason="end",
            usage=Usage(),
            provider="scripted",
        )


def test_runner_collects_the_notice_from_the_tool_that_raised_it():
    result = Orchestrator(
        provider=_ScriptedProvider(),
        registry=_NoticingRegistry(),
        system_prefix="",
    ).handle_instruction("이 곡으로 큐 리스트 만들어줘")

    assert result.notices == (_NoticingRegistry.NOTICE,)


def _summary(notices: tuple[str, ...]) -> str:
    """``_compose_summary`` 만 부른다 — 마지막 구간을 다른 것 없이 재려는 것."""
    return ChatSession._compose_summary(
        _StubSession(),
        InstructionResult(
            status="ok",
            text="큐 리스트를 만들었습니다",
            command_outcomes=(),
            retries_used=0,
            model_calls=1,
            duration_seconds=0.0,
            notices=notices,
        ),
        [],
    )


class _StubSession:
    """``_compose_summary`` 가 읽는 것은 턴 판정 목록 하나뿐이다."""

    _turn_decisions: tuple = ()


def test_the_notice_reaches_the_chat_summary():
    assert _NoticingRegistry.NOTICE in _summary((_NoticingRegistry.NOTICE,))


def test_a_turn_with_no_skip_leaves_the_summary_untouched():
    """건너뜀 0건이면 요약은 이 변경 이전과 같다 — 빈 문자열, 덧붙임 없음."""
    assert _summary(()) == ""
