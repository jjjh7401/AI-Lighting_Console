"""t108 C1 — 프리셋 값이 콘솔에 도달하는지 (LXSEQ-003 후속).

🔴 **이 파일은 결함 뒤에 쓰였다.** import_lxseq_presets 의 apply 경로가
preset_store_commands 만 불렀다 — 즉 Store Preset / Label Preset 만 나가고,
**저장될 값을 프로그래머에 싣는 줄이 한 줄도 없었다.** 그래서 콘솔은 그 순간의
프로그래머 상태(감독이 손으로 만들어 둔 것, 또는 앞 프리셋의 잔여)를 저장했고,
미리보기가 약속한 value 와 무관한 것이 영속했다.

형제 _store_position_preset_looks(server/web/session.py:5342-5346)는 룩마다
적용 -> Store -> Label -> ClearAll 을 **별개 번들**로 쏜다. 이 경로는 가운데
하나만 불렀다.

결함이 둘이고 **결합돼 있다**:

1. 값 미도달 — 적용 줄이 없다
2. ClearAll 부재 — 연속 저장에서 앞 저장의 프로그래머 상태가 뒤에 실린다

둘은 짝으로만 고칠 수 있다. ClearAll 만 먼저 넣으면 1번은 감독의 프로그래머를
저장하고 2번부터는 **빈 프리셋**이 된다 — 지금(누적)보다 조용히 더 틀리다.

셋째로, 번들을 가르지 않으면 run_commands 의 접힘이 값을 지운다. ClearAll 과
**맨몸** 선택은 접힘 면제지만(tools.py:809-819), 값을 실은
Group 1 ; Attribute 'Dimmer' At 50 은 면제가 **아니다** — 같은 레벨이 두 행 있는
시트에서 뒤 적용이 접히고, 앞에서 ClearAll 이 돌았으므로 빈 프로그래머가
저장된다. TestTwoRowsAtTheSameLevel 이 그 자리를 잡는다.

순수 검증이다. 콘솔·네트워크 접촉 0.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

from server.llm.types import ToolCall
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import build_toolset

RIG = Path("src/Lighting_Designer/02_RIG팩")
DIM = RIG / "LXSEQ_RIG_01_ShowBase_r3.preset-dim.csv"
TOOL = "import_lxseq_presets"

#: 정본 dim 시트의 Level 열 전수 (파일을 열어 확인한 값 — 요약이 아니다).
DIM_LEVELS = (100, 85, 60, 30, 15, 0)


class _RecordingPort:
    """발화를 기록만 한다 — test_lxseq_preset_safety.py 의 포트와 같은 이유로
    예외를 던지지 않는다(발화와 「발화하려다 막힘」이 구분돼야 한다)."""

    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, command: str) -> ExecutionResult:
        self.executed.append(command)
        return ExecutionResult(ok=True, detail="OK")

    def query_state(self, path: str) -> dict:
        if path.endswith("PresetPools"):
            return dict(children=[dict(i=1, name="Dimmer")], node=dict(childCount=1))
        return dict(children=[], node=dict(childCount=0), truncated=False)

    def query_property(self, path: str, name: str) -> dict:
        return dict(ok=False, error="not readable")


class _Approval:
    def __init__(self, *, approve: bool = True) -> None:
        self.approve = approve
        self.asked: list[tuple[str, ...]] = []

    def request_approval(self, request) -> bool:
        self.asked.append(tuple(item.command for item in request.items))
        return self.approve


def _dispatch(sheet_bytes: bytes, *, approve: bool = True, action: str = "apply"):
    port = _RecordingPort()
    approval = _Approval(approve=approve)
    registry = build_toolset(
        execution_port=port,
        state_port=port,
        property_port=port,
        group_approval_port=approval,
    )
    execution = registry.dispatch(
        ToolCall(
            id="t108",
            name=TOOL,
            arguments=dict(
                file_content_base64=base64.b64encode(sheet_bytes).decode("ascii"),
                action=action,
            ),
        )
    )
    return json.loads(execution.result.content), port, approval


class TestTheValueReachesTheConsole:
    """미리보기가 약속한 값이 실제 명령에 실리는가."""

    def test_every_planned_level_is_applied(self):
        """🔴 결함이 난 자리다 — 적용 줄이 하나도 없었다."""
        _payload, port, _approval = _dispatch(DIM.read_bytes())
        for level in DIM_LEVELS:
            expected = "Group 1 ; Attribute 'Dimmer' At " + str(level)
            assert expected in port.executed, (
                "레벨 " + str(level) + "% 를 싣는 줄이 없다 — 저장된 것은 시트 값이 "
                "아니다. " + repr(port.executed)
            )

    def test_the_applied_value_matches_what_the_preview_promised(self):
        """페이로드의 planned[].value 와 발화한 값이 같은 원천에서 와야 한다.

        미리보기와 발화가 갈라지면 사람이 승인한 것과 콘솔이 받은 것이 달라진다.
        """
        payload, port, _approval = _dispatch(DIM.read_bytes())
        promised = [row["value"] for row in payload["planned"]]
        assert promised, payload
        for value_raw in promised:
            level = value_raw.strip().rstrip("%").strip()
            assert "Group 1 ; Attribute 'Dimmer' At " + level in port.executed, value_raw


class TestTheProgrammerIsClearedBetweenPresets:
    def test_each_stored_preset_is_closed_with_clearall(self):
        """ClearAll 이 없으면 앞 저장의 프로그래머 상태가 뒤 프리셋에 그대로 실린다."""
        _payload, port, _approval = _dispatch(DIM.read_bytes())
        stores = [c for c in port.executed if c.startswith("Store Preset ")]
        clears = [c for c in port.executed if c == "ClearAll"]
        assert len(stores) == len(DIM_LEVELS), port.executed
        assert len(clears) == len(stores), (
            "Store "
            + str(len(stores))
            + "건에 ClearAll "
            + str(len(clears))
            + "건 — 짝이 안 맞는다. "
            + repr(port.executed)
        )

    def test_the_order_is_apply_then_store_then_clear(self):
        """순서가 계약이다. ClearAll 이 적용보다 앞서면 빈 프리셋이 저장된다."""
        _payload, port, _approval = _dispatch(DIM.read_bytes())
        for level in DIM_LEVELS:
            apply_at = port.executed.index("Group 1 ; Attribute 'Dimmer' At " + str(level))
            store_at = next(
                i
                for i, c in enumerate(port.executed)
                if i > apply_at and c.startswith("Store Preset ")
            )
            clear_at = next(
                i for i, c in enumerate(port.executed) if i > store_at and c == "ClearAll"
            )
            assert apply_at < store_at < clear_at, (level, port.executed)


class TestTwoRowsAtTheSameLevel:
    """접힘 위험 — 값이 같은 두 행이 한 번들에 있으면 뒤 적용이 지워진다.

    정본 시트는 6행의 값이 전부 달라 이 자리를 **못 잡는다.** 그래서 합성 시트로
    잡는다. 이게 없으면 「번들을 가른다」는 규율이 검사 없이 남는다.
    """

    SHEET = ("ID,Name,Level,Purpose\nDIM.A,에이,50%,첫째\nDIM.B,비,50%,둘째 — 값이 같다\n").encode()

    def test_both_applies_reach_the_console(self):
        _payload, port, _approval = _dispatch(self.SHEET)
        applies = [c for c in port.executed if c == "Group 1 ; Attribute 'Dimmer' At 50"]
        assert len(applies) == 2, (
            "값이 같은 두 행 중 하나의 적용이 접혔다 — 그 프리셋은 빈 프로그래머로 "
            "저장된다. " + repr(port.executed)
        )

    def test_both_presets_are_still_stored(self):
        _payload, port, _approval = _dispatch(self.SHEET)
        stores = [c for c in port.executed if c.startswith("Store Preset ")]
        assert len(stores) == 2, port.executed


class TestAKindWithoutATranslationIsNotStored:
    """fail-closed — 적용 줄을 만들 수 없는 종류는 **저장하지 않는다.**

    오늘 계획에 오르는 종류는 dim 하나뿐이지만, 나중에 col·bm 이 열릴 때 번역이
    빠진 채 저장 줄만 나가면 결함이 그대로 되돌아온다. 그 자리를 미리 막는다.
    """

    def test_nothing_fires_when_the_attribute_table_has_no_entry(self, monkeypatch):
        from server.orchestrator import tools as tools_module

        monkeypatch.setattr(tools_module, "LXSEQ_PRESET_APPLY_ATTRIBUTE", {})
        payload, port, _approval = _dispatch(DIM.read_bytes())
        assert port.executed == [], "번역이 없는데 발화했다: " + repr(port.executed)
        assert payload.get("refusal") == "apply_untranslatable", payload.get("refusal")

    def test_the_control_probe_fires_with_the_table_intact(self):
        """대조군 — 표가 그대로면 나간다. 없으면 위 검사가 「무조건 안 나간다」와
        구분되지 않는다."""
        _payload, port, _approval = _dispatch(DIM.read_bytes())
        assert any(c.startswith("Store Preset ") for c in port.executed), port.executed
