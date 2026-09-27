"""카드 t476 — 승인한 값 줄이 ``run_commands`` 중복 제거로 조용히 빠지던 결함.

실측(t475, ``.moai/reports/t475/tracking_diff.txt``): Rain 을 대화 길로 반영하면 승인
카드에 뜬 명령은 107줄인데 콘솔로 나간 명령은 75줄이다. 큐 번호는 ``Store`` 줄에만
있고 값 줄에는 없어서, 두 큐가 같은 값을 쓰면 두 번째 큐의 값 줄이
``skipped_already_executed`` 가 된다. 콘솔은 저장되지 않은 값을 앞 큐에서 이어 받으므로
(트래킹) Verse 3·4 의 드롭 앞 어둠 25% 가 100% 로, Chorus 6 의 Ring In 포지션이 앞 큐의
Fan Out 으로 나갔다. 회신은 「모두 실행」, readback 도 통과했다.

중복 제거의 목적은 **저장물**을 두 번 만들지 않는 것이다(``tools.py`` 의 면제 주석).
선택이 붙은 값 줄(``Fixture … ; Attribute … At …`` · ``Fixture … ; At Preset a.b``)은
프로그래머에 값을 올릴 뿐 저장물을 만들지 않는다 — 저장은 뒤따르는 ``Store`` 가 한다.
그래서 면제에 넣는다. ``Store``·``Label``·``Delete``·``Assign`` 의 중복 방지는 그대로다.

세 경로를 못 박는다: 도구 단위, 대화 길(Rain 실측 구간), 큐시트 반영 길(lane-1 판독).
"""

from __future__ import annotations

import copy

import pytest

from server.design.cue_sheet_apply import layer_mapping_from_console_groups, plan_console_apply
from server.design.profile import BpmResolution
from server.design.sugar_timeline import build_sugar_timeline
from server.fx.instantiate import is_programmer_state as fx_is_programmer_state
from server.groupgen.write import is_programmer_state as groupgen_is_programmer_state
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import ToolCall, _is_programmer_state, build_toolset
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.spatial.pointing import BASIC_POSITION_SEQUENCE
from server.tests.test_safety_gate import FakeConsole
from server.tests.test_writegate_song_finalize import _Approval, _Provider, _Questions, _Spatial
from server.web.approval_bridge import ApprovalChannel
from server.web.question import ConfirmedSongAnalysis, ConfirmedSongSection
from server.web.session import ChatSession


class _RecordingPort:
    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, command: str) -> ExecutionResult:
        self.executed.append(command)
        return ExecutionResult(ok=True, detail="OK")


class _StatePort:
    def query_state(self, path: str) -> dict:
        return {}


def _run(commands: list[str]) -> tuple[list[str], list[str]]:
    port = _RecordingPort()
    execution = build_toolset(execution_port=port, state_port=_StatePort()).dispatch(
        ToolCall(id="t476", name="run_commands", arguments={"commands": commands})
    )
    return port.executed, [outcome.status for outcome in execution.command_outcomes]


# -- 도구 단위 -----------------------------------------------------------------------

#: t475 에서 실제로 두 번째부터 빠진 줄들(``tracking_diff.txt``).
_VALUE_LINES = (
    "Fixture 20 + 26 ; Attribute 'Dimmer' At 25",
    "Group 3 ; Attribute 'Dimmer' At 20",
    "Fixture 20 + 26 ; At Preset 2.30",
    "Fixture 20 + 26 ; Attribute 'ColorRGB_R' At 5 ; Attribute 'ColorRGB_G' At 20 ; "
    "Attribute 'ColorRGB_B' At 100",
    "Group 2 + 7 + 9 ; Attribute 'Dimmer' At 55 ; Group 2 ; Attribute 'ColorRGB_R' At 100",
    "Fixture 101 Thru 110 ; Attribute 'Dimmer' At 0",
)


@pytest.mark.parametrize("line", _VALUE_LINES)
def test_a_selected_value_line_reaches_the_console_every_time(line):
    commands = [
        line,
        "Store Sequence 210 Cue 3 'Verse 2' CueFade 2",
        "ClearAll",
        line,
        "Store Sequence 210 Cue 6 'Verse 3' CueFade 2",
        "ClearAll",
    ]
    executed, statuses = _run(commands)
    assert executed == commands
    assert "skipped_already_executed" not in statuses


@pytest.mark.parametrize("line", _VALUE_LINES)
def test_every_exemption_definition_agrees_on_the_value_line(line):
    assert _is_programmer_state(line) is True
    assert fx_is_programmer_state(line) is True
    assert groupgen_is_programmer_state(line) is True


@pytest.mark.parametrize(
    "command",
    [
        "Store Sequence 210 Cue 3 'Verse 2' CueFade 2",
        "Store Preset 4.1",
        "Assign Sequence 210 At Timecode 9",
        "Label Group 7 'Vocals'",
        "Delete Group 3",
        # 선택 없이 값만 있는 줄·선택에 값을 바로 붙인 꼴은 이번 면제 밖이다.
        "Attribute 'Dimmer' At 50",
        "Fixture 1 Thru 10 At 80",
        "Group 3 Full",
        # 값 줄 모양 뒤에 저장 동사를 숨긴 꼴 — 면제가 이것까지 삼키면 안 된다.
        "Fixture 1 ; Attribute 'Dimmer' At 50 ; Store Sequence 1 Cue 1",
        "Fixture 1 ; At Preset 2.30 ; Delete Group 3",
    ],
)
def test_artifact_lines_are_still_deduped(command):
    executed, statuses = _run([command, command])
    assert executed == [command]
    assert statuses == ["executed_ok", "skipped_already_executed"]
    assert _is_programmer_state(command) is False
    assert fx_is_programmer_state(command) is False
    assert groupgen_is_programmer_state(command) is False


# -- 대화 길: Rain 실측 구간 --------------------------------------------------------

#: t475 에서 실제 DSP 가 Rain.mp3 로 잰 구간(``.moai/reports/t475/run3/analysis.json``).
_RAIN_SPANS = (
    (0, 20939, 2),
    (20939, 33568, 3),
    (33568, 49515, 3),
    (49515, 66517, 5),
    (66517, 79595, 5),
    (79595, 106432, 3),
    (106432, 123008, 5),
    (123008, 138581, 5),
    (138581, 166421, 5),
    (166421, 179061, 4),
    (179061, 209141, 5),
    (209141, 222592, 1),
)
_RAIN_BPM = BpmResolution(bpm=76.01351351351367, source="measured", reason="t475", mismatches=())


def _rain_analysis() -> ConfirmedSongAnalysis:
    return ConfirmedSongAnalysis(
        source_sha256="c3b78bbb739f816879a33d508404c137643e01bb77af27b26e6a8514fe085b70",
        source_file_name="Rain.mp3",
        confirmed_at="2026-09-27T00:00:00+00:00",
        bpm=_RAIN_BPM,
        sections=tuple(
            ConfirmedSongSection(
                index=index,
                label=f"{start // 60000}:{start // 1000 % 60:02d} · D{d}",
                start_ms=start,
                end_ms=end,
                d_level=d,
                selected=True,
            )
            for index, (start, end, d) in enumerate(_RAIN_SPANS)
        ),
    )


_T379_GROUPS = ("KEY", "FOH", "BACK", "SIDE-L", "SIDE-R", "BLIND")
_POSITION_POOL = {
    "ok": True,
    "children": [{"i": 21 + i, "name": name} for i, name in enumerate(BASIC_POSITION_SEQUENCE)],
}


class _RainConsole(FakeConsole):
    def query_state(self, path: str) -> dict:
        if path == "DataPool/PresetPools/2":
            return _POSITION_POOL
        if path == "DataPool/Groups":
            return {
                "ok": True,
                "children": [{"i": 1 + i, "name": n} for i, n in enumerate(_T379_GROUPS)],
            }
        raise RuntimeError(f"path segment not found: {path}")


def test_the_whole_approved_rain_bundle_reaches_the_console(tmp_path):
    console = _RainConsole()
    audit = AuditLog(tmp_path / "audit")
    sent: list[dict] = []
    session = ChatSession(
        gate=SafetyGate(console=console, audit=audit, approval_port=_Approval(True)),
        provider=_Provider(),
        system_prefix="PREFIX",
        audit=audit,
        send_event=sent.append,
        approval_channel=ApprovalChannel(timeout_seconds=1.0),
    )
    session._registry = _Spatial(session._registry, [])
    session._question_channel = _Questions(
        (
            "우주",
            "우주 색 조합",
            "",
            "Ring In",
            "우주 컨셉 우선 배치",
            "템포 맞춤 (BPM 기준)",
            "이 매핑 사용",
            "승인",
        )
    )
    session._song_analysis = _rain_analysis()
    session._song_bpm = _RAIN_BPM

    session.run_instruction("디자인 큐 시트, 시퀀스 210, 프리셋 21번부터, 타임코드 9")

    previews = [event for event in sent if event.get("type") == "execution_preview"]
    assert previews, "승인 카드가 뜨지 않았다 — 반영 경로에 닿지 않았다"
    approved = [row["command"] for row in previews[-1]["commands"]]
    # 계기가 공허하지 않다: 승인 카드 안에 같은 값 줄이 실제로 두 번 이상 있다.
    darkness = "Fixture 20 + 26 ; Attribute 'Dimmer' At 25"
    assert approved.count(darkness) >= 2
    assert console.executed == approved


# -- 큐시트 반영 길(lane-1 판독) -----------------------------------------------------

_SUGAR_RIG = (("KEY", 1), ("BACK", 2), ("SIDE-L", 3), ("SIDE-R", 4))


def test_two_cues_with_the_same_value_line_both_reach_the_console():
    baseline = build_sugar_timeline()
    current = copy.deepcopy(baseline)
    current["sequence_number"] = 3
    current["layer_mapping"] = layer_mapping_from_console_groups(
        {"children": [{"name": name, "i": number} for name, number in _SUGAR_RIG]},
        ["KEY", "BACK", "SIDE-L", "SIDE-R"],
    )
    # 큐 20 과 큐 70 은 둘 다 KEY·BACK 을 쓰고 주색이 같다(P2 웜화이트). 같은 밝기로
    # 고치면 두 큐의 값 줄이 글자까지 같아진다.
    for section in current["sections"]:
        if section["cue_number"] in (20, 70):
            section["intensity"] = [
                {"group": "KEY", "level": 80},
                {"group": "BACK", "level": 40},
            ]
            section["palette"] = ["P2 웜화이트"]
            section["palette_primary"] = "P2 웜화이트"
            section.pop("palette_secondary", None)
    plan = plan_console_apply(baseline, current)

    stores = [command for command in plan.commands if command.startswith("Store Sequence 3 Cue")]
    assert len(stores) == 2
    values = [command for command in plan.commands if command.startswith("Group ")]
    # 계기가 공허하지 않다: 두 큐의 값 줄이 실제로 같다.
    assert len(values) == 2
    assert values[0] == values[1]

    executed, statuses = _run(list(plan.commands))
    assert executed == list(plan.commands)
    assert "skipped_already_executed" not in statuses
