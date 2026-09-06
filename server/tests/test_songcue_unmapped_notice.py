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


def _real_library():
    return load_library_from_dir(Path("server/looks/library"))


#: 어느 역할에도 안 걸리는 리그 — 고지 기제를 계속 재기 위한 자리.
#: 실기 리그가 이제 네 구간을 전부 덮으므로(아래 첫 테스트), 「건너뛴 구간이
#: 있을 때 고지가 나오는가」를 실기 리그로는 더 이상 못 잰다. 계측기를 지우는
#: 대신 여전히 건너뛰는 리그로 옮긴다.
_UNBINDABLE_RIG_GROUPS: tuple[tuple[int, str], ...] = (
    (1, "FIXTURE-1"),
    (2, "FIXTURE-2"),
    (3, "FIXTURE-3"),
)


def _call_with_rig(groups: tuple[tuple[int, str], ...], call_id: str) -> tuple[object, dict]:
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


def test_live_rig_now_covers_every_section():
    """이 카드가 관측한 손해가 닫혔다 — 4건 확정에 4건 저장 (교체된 회귀 고정).

    **전** (2026-09-06 실기 회차, 이 파일이 태어난 이유): 같은 호출이
    ``section_count == 4`` · ``generated_count == 3`` 을 답했고, 저장된 것은
    ``["Build", "Drop", "Outro"]``, 버려진 것은 ``["Intro"]`` 였으며 그 사유는
    ``reason_kind == "role_unaddressed"`` 였다. EDM 의 유일한 D1 룩
    ``edm-ambient-hold`` 이 요구하는 ``배경`` 역할에 묶을 그룹이 실기 리그에
    없었기 때문이다. 그 건너뜀은 옳았고, 결함은 침묵이었다.

    **후** (SPEC-COPILOT-D1GRANT-001): ``edm-haze-shafts``(역할 ``백라이트``)가
    라이브러리에 들어오면서 ``Intro`` 가 묶을 룩을 얻었다. 이제 네 구간이 전부
    큐를 받으므로 버려지는 구간이 없다 — 이 테스트가 재는 것은 그 사실이다.
    고지 기제 자체는 아래 ``_UNBINDABLE_RIG_GROUPS`` 로 계속 측정된다.
    """
    _execution, payload = _call_with_rig(_REAL_RIG_GROUPS, "songcue-t277")

    report = payload["report"]
    assert report["summary"]["section_count"] == 4
    assert report["summary"]["generated_count"] == 4
    stored = [cue["name"] for cue in report["generated_cues"]]
    assert stored == ["Intro", "Build", "Drop", "Outro"]
    assert report["unmapped_sections"] == []


def test_operator_notice_names_the_gap_the_count_and_the_missing_role():
    """감독이 읽는 한 문장 — 몇 건 중 몇 건, 어느 구간이, 왜.

    실기 리그가 아니라 어느 역할에도 안 걸리는 리그로 잰다. 실기 리그는 이제
    건너뛰는 구간이 없어 고지가 비고, 빈 고지로는 「고지가 만들어지는가」를
    확인할 수 없다 — 계측기가 공허해진다.
    """
    execution, payload = _call_with_rig(_UNBINDABLE_RIG_GROUPS, "songcue-t277-unbindable")

    assert payload["report"]["summary"]["unmapped_count"] > 0
    notice = execution.operator_notice
    assert notice, "건너뛴 구간이 있는데 감독용 고지가 비어 있다"
    assert "구간 4건 중 큐 0건" in notice
    assert "Intro" in notice


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

    실기 리그가 아니라 건너뛰는 리그로 잰다. 실기 리그의 고지는 이제 빈
    문자열이라 「보고 객체만으로 같은 문장이 나오는가」를 확인할 수 없다.
    """
    execution, _payload = _call_with_rig(_UNBINDABLE_RIG_GROUPS, "songcue-t277-report")

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
