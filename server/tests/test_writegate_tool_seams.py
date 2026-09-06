"""카드 t319 — 쇼파일을 고치는 여섯 자리가 **진짜 게이트**를 지나는가.

`test_bulkgate_songcue_seam.py` 가 곡 경로에서 한 일을 나머지 여섯 자리에서
그대로 한다: 게이트 더블이 아니라 실제 `SafetyGate` 를 세우고, 승인 채널만
바꿔 같은 디스패치를 두 번 돌린다. 거절 회차에서 콘솔이 0건을 받는지,
수락 회차에서 카드가 한 장이고 그 카드가 **나갈 명령 전부**를 싣고 있는지,
감사 로그의 `kind` 가 그 자리의 태그인지를 본다.

카드 문면은 `showfile_write_risk` 가 나갈 명령에서 읽어 만든다. 그래서
검사도 문면을 짐작하지 않고 **실제로 관측한 조각**만 단언한다 — 프리셋 풀,
Sequence 큐, Macro 슬롯, 좌표 장비 수처럼 그 자리에서 실제로 나온 말이다.

## 잰 것과 못 잰 것

잰 것 — 여섯 자리 전부(`instantiate_look` · `prepare_busking` ·
`precheck_patch` · `instantiate_fx`(`_deliver_fx_plan`) · `compile_scene` ·
`arrange_fixtures`). 각 자리마다 거절/수락 두 회차, 카드 한 장, 카드의
명령 집합이 콘솔이 받은 줄을 모두 덮는지, 감사 `kind`, 문면 조각.

못 잰 것:

* **DOM 은 안 잰다.** 화면에 카드가 실제로 그려지는지는 브라우저 회차의 몫이다
  (형제 파일 `test_bulkgate_songcue_seam.py` 와 같은 한계).
* **`arrange_fixtures` 는 실행 포트가 게이트 소유가 아니다.** 이 자리는
  저장소의 기존 배선(`test_spatial_arrange.py`)을 그대로 쓴다 — 콘솔이 상태·
  속성·실행 셋을 겸해야 좌표 되읽기가 성립하기 때문이다. 따라서 여기서 재는
  것은 「게이트가 거절하면 쓰기가 0건」이지, 클리어런스 토큰 소비가 아니다.
* **덮어쓰기 문면(`/Merge`·`/Overwrite`)은 이 여섯 자리에서 안 나왔다.** 여섯
  번들 모두 플래그 없는 `Store` 라 문면의 덮어쓰기 절은 미관측이다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import server.tests.test_busking_tool as busking_tests
import server.tests.test_fx_tool as fx_tests
import server.tests.test_looks_tool as look_tests
import server.tests.test_prechk_tool as prechk_tests
import server.tests.test_scene_tool as scene_tests
import server.tests.test_spatial_arrange as spatial_tests
from server.llm.types import ToolCall
from server.orchestrator.tools import build_toolset
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.safety.lock import LiveLock


class _Console:
    """콘솔이 실제로 받은 명령만 센다 — 「0건 나갔다」의 계측기."""

    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, command: str):
        from server.safety.console import ExecOutcome

        self.executed.append(command)
        return ExecOutcome(status="ok", detail="OK")

    def ping(self) -> bool:
        return True

    def query_state(self, path: str) -> dict:
        raise RuntimeError(f"no such path: {path}")


class _Approval:
    def __init__(self, answer: bool) -> None:
        self.answer = answer
        self.requests: list = []

    def request_approval(self, request) -> bool:
        self.requests.append(request)
        return self.answer


def _events(audit: AuditLog, event_type: str) -> list[dict]:
    return [e for e in audit.iter_events() if e["event"] == event_type]


# -- 자리별 배선 ----------------------------------------------------------------
#
# 각 자리의 픽스처(리그 트리·라이브러리·인자)는 그 자리를 이미 성공적으로
# 디스패치하는 기존 검사에서 그대로 들고 온다. 여기서 다시 조립하면 두 검사가
# 서로 다른 리그를 재게 된다.


def _look_registry(gate):
    return build_toolset(
        execution_port=gate.execution_port,
        state_port=look_tests._RigStatePort(look_tests._tree()),
        bundle_gate=gate,
        look_library=look_tests._library(),
    )


def _busking_registry(gate):
    return build_toolset(
        execution_port=gate.execution_port,
        state_port=look_tests._RigStatePort(look_tests._tree(groups=busking_tests.FULL_GROUPS)),
        bundle_gate=gate,
    )


def _prechk_registry(gate):
    rig = prechk_tests.RigPort()
    return build_toolset(
        execution_port=gate.execution_port,
        state_port=rig,
        property_port=rig,
        bundle_gate=gate,
    )


def _fx_registry(gate):
    return build_toolset(
        execution_port=gate.execution_port,
        state_port=fx_tests._RigStatePort(fx_tests._tree()),
        bundle_gate=gate,
        fx_library=fx_tests._library(),
    )


def _scene_registry(gate):
    scene_lib, look_lib, fx_lib = scene_tests._libraries()
    return build_toolset(
        execution_port=gate.execution_port,
        state_port=scene_tests._RigStatePort(scene_tests._tree()),
        bundle_gate=gate,
        look_library=look_lib,
        fx_library=fx_lib,
        scene_library=scene_lib,
    )


#: (표시 이름, 레지스트리 배선, 툴 이름, 인자, 감사 kind, 문면 조각)
_SEAMS = [
    (
        "look_instantiate",
        _look_registry,
        "instantiate_look",
        {"look_id": "test-look"},
        "look_instantiate",
        "프리셋",
    ),
    (
        "busking_bundle",
        _busking_registry,
        "prepare_busking",
        {"genre": "록"},
        "busking_bundle",
        "프리셋",
    ),
    (
        "precheck_macro",
        _prechk_registry,
        "precheck_patch",
        {"create_macro": True},
        "precheck_macro",
        "Macro",
    ),
    (
        "fx_plan",
        _fx_registry,
        "instantiate_fx",
        {"fx_id": "test-fx", "group": 11},
        "fx_plan",
        "Sequence",
    ),
    (
        "scene_compile",
        _scene_registry,
        "compile_scene",
        {"scene_id": "blue-wave", "group": 11},
        "scene_compile",
        "Sequence",
    ),
]

_IDS = [seam[0] for seam in _SEAMS]


def _run(tmp_path: Path, factory, tool: str, arguments: dict, *, approve: bool):
    console = _Console()
    approval = _Approval(approve)
    audit = AuditLog(tmp_path / "audit")
    gate = SafetyGate(console=console, audit=audit, approval_port=approval)
    registry = factory(gate)
    execution = registry.dispatch(ToolCall(id="seam", name=tool, arguments=dict(arguments)))
    return execution, console, approval, audit


@pytest.mark.parametrize(
    ("factory", "tool", "arguments", "kind", "fragment"),
    [seam[1:] for seam in _SEAMS],
    ids=_IDS,
)
class TestTheFiveClosureSeams:
    """`run_commands` 클로저를 지나는 다섯 자리 — 실행 포트가 게이트 소유다."""

    def test_a_refusal_sends_zero_commands(
        self, tmp_path, factory, tool, arguments, kind, fragment
    ):
        # 「0건」의 세 갈래 중 여기서 참이어야 하는 것은 「감독이 거절했다」다.
        # 카드가 정확히 한 장 떴다는 단언이 「선언이 배선을 못 지났다」를 배제한다.
        _execution, console, approval, _audit = _run(
            tmp_path, factory, tool, arguments, approve=False
        )
        assert len(approval.requests) == 1
        assert console.executed == []
        assert not [c for c in console.executed if c.startswith("Store ")]

    def test_the_card_is_one_and_covers_every_line_that_went_out(
        self, tmp_path, factory, tool, arguments, kind, fragment
    ):
        # 카드는 나간 줄의 상위집합이다 — `run_commands` 가 중복을 접기 때문에
        # 「같다」가 아니라 「전부 담겼다」로 잰다.
        _execution, console, approval, _audit = _run(
            tmp_path, factory, tool, arguments, approve=True
        )
        assert len(approval.requests) == 1
        assert console.executed, "비공허성: 수락 회차에는 실제로 명령이 나갔다"
        carried = set(approval.requests[0].commands)
        missing = [c for c in console.executed if c not in carried]
        assert missing == [], missing

    def test_the_audit_tags_this_seam_by_its_own_kind(
        self, tmp_path, factory, tool, arguments, kind, fragment
    ):
        # 자리마다 다른 태그여야 로그에서 어느 통로였는지 되짚을 수 있다.
        _execution, _console, _approval, audit = _run(
            tmp_path, factory, tool, arguments, approve=True
        )
        approved = _events(audit, "approved")
        assert len(approved) == 1
        assert approved[0]["kind"] == kind

    def test_the_reason_names_what_this_bundle_actually_writes(
        self, tmp_path, factory, tool, arguments, kind, fragment
    ):
        # 「위험한 명령입니다」로는 감독이 무엇을 수락하는지 알 수 없다.
        _execution, _console, approval, _audit = _run(
            tmp_path, factory, tool, arguments, approve=True
        )
        reasons = [r for item in approval.requests[0].items for r in item.risk_reasons]
        assert any("쇼파일 쓰기" in r for r in reasons), reasons
        assert any(fragment in r for r in reasons), reasons


class TestTheLookBundleCountsItsPools:
    """룩 하나가 어느 풀을 몇 건 고치는지 — 숫자가 계획이 아니라 명령에서 왔다."""

    def test_the_reason_counts_the_store_preset_lines(self, tmp_path):
        _execution, console, approval, _audit = _run(
            tmp_path, _look_registry, "instantiate_look", {"look_id": "test-look"}, approve=True
        )
        stores = [c for c in console.executed if c.startswith("Store Preset ")]
        assert len(stores) == 2, stores  # 1번(Dimmer) · 4번(Color) 풀
        reason = approval.requests[0].items[0].risk_reasons[0]
        assert "프리셋 2건" in reason, reason
        assert "1번 풀" in reason and "4번 풀" in reason, reason
        assert "되돌리기 명령이 없습니다" in reason, reason


class TestTheMacroBundleNamesItsSlot:
    """자유 슬롯 탐색이 고른 번호가 문면에 그대로 실린다."""

    def test_the_slot_in_the_reason_is_the_slot_on_the_wire(self, tmp_path):
        _execution, console, approval, _audit = _run(
            tmp_path, _prechk_registry, "precheck_patch", {"create_macro": True}, approve=True
        )
        stores = [c for c in console.executed if c.startswith("Store Macro ")]
        assert stores, console.executed
        slot = stores[0].split()[-1].split(".")[0]
        reason = approval.requests[0].items[0].risk_reasons[0]
        assert f"Macro {slot} 슬롯" in reason, (slot, reason)


# =============================================================================
# arrange_fixtures — 실행 포트가 게이트 소유가 아닌 유일한 자리
# =============================================================================


def _arrange_gate(tmp_path: Path, *, approve: bool):
    """`test_spatial_arrange.real_gate` 와 같은 모양이되, 감사 로그를 손에 쥔다.

    콘솔을 게이트에 물리지 않는 것은 이 자리의 기존 배선 그대로다 —
    상태·속성·실행을 한 객체가 겸해야 「쓰기 전에 원좌표를 읽었다」가 순서에
    대한 단언이 된다(`test_spatial_arrange.ArrangeConsole`).
    """
    audit = AuditLog(tmp_path / "audit")
    approval = spatial_tests.ScriptedApprovalPort(approve)
    gate = SafetyGate(
        console=None,
        audit=audit,
        lock=LiveLock(),
        approval_port=approval,
    )
    return gate, approval, audit


def _arrange(tmp_path: Path, *, approve: bool):
    console = spatial_tests.rig()
    gate, approval, audit = _arrange_gate(tmp_path, approve=approve)
    execution = spatial_tests.registry(console, gate=gate).dispatch(
        ToolCall(id="seam", name="arrange_fixtures", arguments={"preset": "row", "fids": [11, 12]})
    )
    writes = [command for kind, command in console.calls if kind == "write"]
    return json.loads(execution.result.content), writes, approval, audit


class TestTheArrangeSeam:
    def test_a_refusal_writes_no_coordinate(self, tmp_path):
        payload, writes, approval, _audit = _arrange(tmp_path, approve=False)
        assert len(approval.requests) == 1
        assert writes == []
        assert not [c for c in writes if " Pos" in c]
        assert payload["executed"] is False

    def test_the_card_is_one_and_carries_every_write(self, tmp_path):
        _payload, writes, approval, _audit = _arrange(tmp_path, approve=True)
        assert len(approval.requests) == 1
        assert writes, "비공허성: 수락 회차에는 좌표가 실제로 나갔다"
        carried = set(approval.requests[0].commands)
        assert [c for c in writes if c not in carried] == []

    def test_the_audit_tags_the_arrange_seam(self, tmp_path):
        _payload, _writes, _approval, audit = _arrange(tmp_path, approve=True)
        approved = _events(audit, "approved")
        assert len(approved) == 1
        assert approved[0]["kind"] == "arrange_fixtures"

    def test_the_reason_says_the_restore_bundle_it_actually_holds(self, tmp_path):
        # 이 자리만 복원 번들을 들고 있다 — 문면이 「되돌리기 없음」이면 거짓이다.
        payload, _writes, approval, _audit = _arrange(tmp_path, approve=True)
        reason = approval.requests[0].items[0].risk_reasons[0]
        assert "패치의 3D 좌표를 장비 2대에 기록" in reason, reason
        assert f"원상 복구 명령 {len(payload['restore_bundle'])}건" in reason, reason
        assert "되돌리기 명령이 없습니다" not in reason, reason
