"""M4 — 툴 배선 · 실행 경로 · LiveLock.

SPEC-COPILOT-BUSKWIZ-001 AC-BUSKWIZ-009 / -010 / -011.

이 마일스톤이 지키는 것은 **경계**다: 신규 툴은 `run_commands` → `gate.screen()`
경로의 **호출자**이지 제2 실행 표면이 아니며, 리그는 모델이 타이핑해 주는 것이
아니라 핸들러가 직접 읽는다.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from server.llm.types import ToolCall
from server.orchestrator.tools import TOOL_NAMES, build_toolset
from server.safety.gate import SafetyGate
from server.safety.lock import LiveLock
from server.tests.test_looks_tool import (
    _RecordingGate,
    _RecordingPort,
    _RigStatePort,
    _tree,
)

_TOOL = "prepare_busking"
_TOOLS_MODULE = Path("server/orchestrator/tools.py")
_SPEC_MODULES = (
    Path("server/looks/busking.py"),
    Path("server/looks/report.py"),
)

# 역할 6종과 in-scope 풀 4종을 모두 주소하는 리그. 픽스처는
# ``test_looks_tool``의 것을 그대로 쓴다 — 리그 트리 조립을 다시 구현하면
# 두 테스트가 서로 다른 리그를 검증하게 된다.
FULL_GROUPS = (
    (11, "Back Wash"),
    (12, "FOH Wash"),
    (13, "Side L"),
    (14, "Top"),
    (15, "Cyc"),
    (16, "Special"),
)


def _rig(**kwargs):
    kwargs.setdefault("groups", FULL_GROUPS)
    return _RigStatePort(_tree(**kwargs))


def _registry(*, port=None, state=None, gate=None):
    return build_toolset(
        execution_port=port or _RecordingPort(),
        state_port=state if state is not None else _rig(),
        bundle_gate=gate,
    )


def _call(registry, **arguments):
    execution = registry.dispatch(ToolCall(id="t1", name=_TOOL, arguments=arguments))
    return execution, json.loads(execution.result.content)


def _handler_node() -> ast.FunctionDef:
    tree = ast.parse(_TOOLS_MODULE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == _TOOL:
            return node
    raise AssertionError(f"{_TOOL} 핸들러를 tools.py에서 찾지 못했다")


def _identifiers(node: ast.AST) -> set[str]:
    return (
        {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
        | {n.attr for n in ast.walk(node) if isinstance(n, ast.Attribute)}
        | {
            alias.asname or alias.name
            for n in ast.walk(node)
            if isinstance(n, ast.ImportFrom | ast.Import)
            for alias in n.names
        }
    )


# -- AC-BUSKWIZ-011 — 툴 등록 관례 ----------------------------------------------


class TestRegistrationConvention:
    def test_the_tool_is_in_all_three_places(self):
        """`TOOL_NAMES` · `definitions` · `handlers` — 하나라도 빠지면 실패다.

        핸들러 등재는 dict를 들여다보지 않고 **디스패치로** 확인한다: 모델이
        닿는 경로가 그것이고, 등록만 되고 부를 수 없는 상태를 그래야 잡는다.
        """
        registry = _registry()
        assert _TOOL in TOOL_NAMES
        assert _TOOL in {d.name for d in registry.definitions()}
        execution = registry.dispatch(ToolCall(id="probe", name=_TOOL, arguments={}))
        assert "unknown tool" not in execution.result.content

    def test_every_registered_name_is_dispatchable(self):
        # 비공허성 — 이름만 넣고 핸들러를 빠뜨린 상태를 잡는다.
        registry = _registry()
        assert {d.name for d in registry.definitions()} == set(TOOL_NAMES)
        for name in TOOL_NAMES:
            execution = registry.dispatch(ToolCall(id="probe", name=name, arguments={}))
            assert "unknown tool" not in execution.result.content, name

    def test_the_schema_has_no_rig_fields(self):
        """리그 데이터를 모델 인자로 받지 않는다 (REQ-BUSKWIZ-020).

        모델이 리그 섹션을 다시 타이핑하면 이름을 바꿔 적거나 절단 신호를
        떨어뜨리거나 콘솔이 준 적 없는 번호를 넣을 수 있다
        (`server/orchestrator/tools.py:735-738`가 같은 이유를 적어 두었다).
        """
        registry = _registry()
        definition = next(d for d in registry.definitions() if d.name == _TOOL)
        properties = definition.parameters["properties"]
        assert properties, "파라미터가 하나도 없으면 이 검사는 공허하다"
        forbidden = {"group", "pool", "slot", "fixture", "executor", "page", "fid"}
        for name in properties:
            assert not (forbidden & set(name.casefold().split("_"))), name
        blob = json.dumps(definition.parameters, ensure_ascii=False).casefold()
        for word in ("groups", "preset_pool", "fixture", "executor"):
            assert word not in blob, f"스키마가 리그 어휘 {word!r}를 노출한다"

    def test_the_handler_reads_the_rig_itself(self):
        # 리그를 인자로 주지 않아도 동작한다 = 핸들러가 직접 읽었다는 뜻.
        registry = _registry()
        _execution, payload = _call(registry, genre="록")
        assert payload["report"]["created"], "핸들러가 스스로 리그를 읽어 저장을 세웠다"


# -- AC-BUSKWIZ-011 구간 2 — is_error 규약 --------------------------------------


class TestIsErrorContract:
    def test_an_unknown_genre_is_a_correctable_mistake(self):
        execution, payload = _call(_registry(), genre="뽕짝")
        assert execution.result.is_error is True
        assert payload["candidates"], "고칠 수 있도록 실재하는 장르를 돌려준다"

    def test_a_missing_genre_argument_is_an_error(self):
        execution, _payload = _call(_registry())
        assert execution.result.is_error is True

    def test_storing_nothing_is_an_answer_not_a_failure(self):
        """저장 0건은 **답변**이다 — 재시도해도 같은 리그는 같은 답을 준다."""
        port = _RecordingPort()
        registry = _registry(port=port, state=_rig(groups=((99, "관계 없는 그룹"),)))
        execution, payload = _call(registry, genre="록")
        assert execution.result.is_error is False
        assert payload["executed"] is False
        assert port.executed == []
        assert payload["report"]["looks"], "무엇이 왜 비었는지는 보고에 남는다"

    def test_an_unavailable_rig_section_is_an_error(self):
        class _Dead:
            def query_state(self, path: str) -> dict:
                raise LookupError("console unreachable")

        execution, payload = _call(_registry(state=_Dead()), genre="록")
        assert execution.result.is_error is True
        assert "rig_unavailable" in payload


# -- AC-BUSKWIZ-010 — LiveLock 강등 ---------------------------------------------


class TestLiveLockDemotion:
    @staticmethod
    def _locked_gate(tmp_path):
        """실물 `SafetyGate` + 활성 `LiveLock`.

        목 게이트로 `status="locked"` 문자열만 흉내내면 "우리가 그 문자열을
        읽는가"만 검증된다. 잠금 의미론 자체는 게이트가 소유하므로 실물을 쓴다.
        """
        from server.safety.audit import AuditLog

        class _Console:
            def send_command(self, command: str):
                raise AssertionError("LiveLock 중 콘솔 송신이 시도됐다")

        lock = LiveLock()
        lock.activate()
        return SafetyGate(console=_Console(), audit=AuditLog(tmp_path / "audit"), lock=lock)

    def test_nothing_reaches_the_console(self, tmp_path):
        port = _RecordingPort()
        registry = _registry(port=port, gate=self._locked_gate(tmp_path))
        _execution, _payload = _call(registry, genre="록")
        assert port.executed == [], "LiveLock 중에는 한 줄도 나가지 않는다"

    def test_the_demotion_is_an_answer_not_a_technical_failure(self, tmp_path):
        execution, payload = _call(_registry(gate=self._locked_gate(tmp_path)), genre="록")
        assert execution.result.is_error is False, (
            "제안으로의 강등은 답변이다 — is_error=True는 자기수정 루프를 돌려 "
            "같은 잠금에 다시 부딪히게 만든다"
        )
        assert payload["executed"] is False
        assert payload["gate_status"] == "locked"

    def test_the_proposal_carries_the_commands_it_did_not_send(self, tmp_path):
        _execution, payload = _call(_registry(gate=self._locked_gate(tmp_path)), genre="록")
        proposed = [entry["command"] for entry in payload["commands"]]
        assert proposed, "제안이 비어 있으면 사용자가 검토할 것이 없다"
        assert {entry["status"] for entry in payload["commands"]} == {"proposal"}


# -- AC-BUSKWIZ-009 — 단일 실행 경로 --------------------------------------------


class TestSingleExecutionPath:
    def test_a_held_gate_sends_nothing(self):
        gate = _RecordingGate(cleared=False, status="held")
        port = _RecordingPort()
        execution, _payload = _call(_registry(port=port, gate=gate), genre="록")
        assert gate.screened, "비공허성: 게이트가 실제로 상담됐다"
        assert port.executed == []
        assert execution.result.is_error is True, "보류는 LiveLock 강등과 다른 사건이다"

    def test_the_handler_never_touches_the_execution_port(self):
        """AST 스캔 — 핸들러 서브트리에 실행 포트 직접 접근 0건.

        raw 텍스트 grep은 "호출"과 "호출을 설명하는 독스트링"을 구분하지 못한다.
        """
        identifiers = _identifiers(_handler_node())
        assert identifiers, "AST에서 식별자를 하나도 모으지 못했다"
        assert "run_commands" in identifiers, "비공허성: 실제로 쓰는 이름이 보여야 한다"
        assert {"execution_port", "ConsoleLink", "OscBridge", "send_command"} & identifiers == set()

    @pytest.mark.parametrize("module", _SPEC_MODULES, ids=lambda p: p.name)
    def test_spec_modules_hold_no_execution_surface(self, module: Path):
        identifiers = _identifiers(ast.parse(module.read_text(encoding="utf-8")))
        assert identifiers
        forbidden = {
            "execution_port",
            "ConsoleLink",
            "OscBridge",
            "APIRouter",
            "FastAPI",
            "websocket",
        }
        assert forbidden & identifiers == set()

    def test_the_bundle_goes_through_run_commands_verbatim(self):
        port = _RecordingPort()
        registry = _registry(port=port)
        _execution, payload = _call(registry, genre="록")
        assert payload["executed"] is True
        assert port.executed, "번들이 실제로 실행됐다"
        assert [o["command"] for o in payload["commands"]] == port.executed

    def test_no_command_is_lost_to_dedupe_on_the_real_path(self):
        _execution, payload = _call(_registry(), genre="발라드")
        statuses = {o["status"] for o in payload["commands"]}
        assert statuses, "per-command status가 비어 있으면 공허하다"
        assert "skipped_already_executed" not in statuses


# -- 보고 부착 ------------------------------------------------------------------


class TestReportIsAttached:
    def test_the_payload_carries_the_two_tier_report(self):
        _execution, payload = _call(_registry(), genre="록")
        report = payload["report"]
        assert report["created"], "(a) 생성"
        assert "skipped" in report, "(c) 건너뜀"
        assert "unmapped" in report, "(b) 미매핑"
        assert report["looks"], "(d) 룩별 판정"
        assert "not_executed" in report, "(e) 미실행"

    def test_the_summary_is_korean(self):
        _execution, payload = _call(_registry(), genre="록")
        summary = payload["summary_ko"]
        assert any("\uac00" <= ch <= "\ud7a3" for ch in summary)
        assert "생성" in summary and "건너뜀" in summary

    def test_every_look_of_the_genre_appears_once(self):
        from server.looks.busking import looks_for_genre
        from server.looks.loader import load_library_from_dir

        _execution, payload = _call(_registry(), genre="EDM")
        expected = [look.look_id for look in looks_for_genre(load_library_from_dir(), "edm")]
        assert [entry["look_id"] for entry in payload["report"]["looks"]] == expected
