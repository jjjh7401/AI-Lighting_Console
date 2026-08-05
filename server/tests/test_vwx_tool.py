"""precheck_vectorworks_diff 툴 배선 테스트 (M6 — AC-VWX-024). 문서 근거 · 실물 미검증.

``server/tests/test_prechk_tool.py``의 확립된 패턴을 따른다 — 등록은 dict
조회가 아니라 **디스패치**로 확인하고, 파라미터 스키마에 리그 식별자가
없음을 검증하며, 콘솔 실측은 기존 ``read_inventory`` 경로만 경유함을 대역
모킹으로 확인한다.
"""

from __future__ import annotations

import ast
import base64
import json
from pathlib import Path

from server.llm.types import ToolCall
from server.orchestrator.tools import TOOL_NAMES, build_toolset
from server.prechk.inventory import FIXTURE_ROOT

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOOLS_SOURCE = PROJECT_ROOT / "server" / "orchestrator" / "tools.py"

TOOL = "precheck_vectorworks_diff"

_FIXTURES = {
    1: {"Patch": "1.001", "FixtureType": "Robin MMX Spot", "Mode": "Mode 1", "Name": "MMX 1"},
}


class RigPort:
    """state_port + property_port 대역 — precheck_patch 테스트의 축소판."""

    def __init__(self, fixtures=None):
        self.fixtures = _FIXTURES if fixtures is None else fixtures
        self.state_calls: list[str] = []
        self.property_calls: list[tuple[str, str]] = []

    def query_state(self, path: str) -> dict:
        self.state_calls.append(path)
        if path == FIXTURE_ROOT:
            children = [
                {"i": slot, "name": self.fixtures[slot]["Name"], "class": "Fixture"}
                for slot in sorted(self.fixtures)
            ]
            return {
                "ok": True,
                "path": path,
                "node": {"name": "Fixtures", "class": "Fixtures", "childCount": len(children)},
                "children": children,
                "truncated": False,
            }
        raise RuntimeError(f"unexpected state path: {path}")

    def query_property(self, path: str, property_name: str) -> dict:
        self.property_calls.append((path, property_name))
        slot = int(path.rsplit("/", 1)[1])
        value = self.fixtures[slot].get(property_name)
        if value is None:
            return {"ok": False, "path": path, "property": property_name, "error": "not readable"}
        return {"ok": True, "path": path, "property": property_name, "value": value}


def _registry(*, rig=None):
    rig = rig or RigPort()
    return build_toolset(
        execution_port=_NeverCalledExecutionPort(), state_port=rig, property_port=rig
    )


class _NeverCalledExecutionPort:
    """이 툴은 콘솔에 발화하지 않는다 — 호출되면 즉시 실패한다."""

    def execute(self, command: str):
        raise AssertionError(f"precheck_vectorworks_diff must never call execution_port: {command}")


def _b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _sample_export() -> str:
    header = "Instrument Type\tUnit Number\tUniverse\tDMX Address"
    row = "Robin MMX Spot\t1\t1\t1"
    return f"{header}\n{row}"


def _dispatch(registry, **arguments):
    return registry.dispatch(ToolCall(id="v1", name=TOOL, arguments=arguments))


class TestRegistrationByDispatch:
    """AC-VWX-024 ① — 툴 등록 4지점, 디스패치로 확인(dict 조회만으로 확인 안 함)."""

    def test_the_name_is_in_the_closed_tool_name_tuple(self):
        assert TOOL in TOOL_NAMES

    def test_the_definition_is_advertised(self):
        names = {definition.name for definition in _registry().definitions()}
        assert TOOL in names

    def test_dispatch_reaches_a_handler(self):
        execution = _dispatch(_registry(), file_content_base64=_b64(_sample_export()))
        assert execution.result.name == TOOL
        assert execution.result.is_error is False

    def test_every_advertised_name_is_dispatchable(self):
        registry = _registry()
        advertised = {definition.name for definition in registry.definitions()}
        assert advertised == set(TOOL_NAMES)


class TestParameterSchemaCarriesNoRigIdentifiers:
    """AC-VWX-024 (mirrors AC-PRECHK-014 ③) — 스키마에 리그 식별자가 없다."""

    def _schema(self):
        for definition in _registry().definitions():
            if definition.name == TOOL:
                return definition.parameters
        raise AssertionError(f"{TOOL} is not advertised")

    def test_no_group_pool_slot_fixture_or_address_parameter(self):
        schema = self._schema()
        properties = schema.get("properties", {})
        assert properties, "schema has no properties — the check would be vacuous"
        banned = ("group", "pool", "slot", "fixture", "address", "universe", "fid")
        for name in properties:
            lowered = name.lower()
            has_banned_word = any(word in lowered for word in banned)
            assert not has_banned_word, f"{TOOL} takes a rig identifier: {name}"

    def test_the_schema_is_a_closed_object(self):
        schema = self._schema()
        assert schema.get("type") == "object"
        assert schema.get("additionalProperties") is False


class TestConsoleReadRoutesThroughReadInventoryOnly:
    """AC-VWX-024 ③ — 콘솔 실측이 read_inventory를 경유함을 대역으로 확인."""

    def test_query_state_is_called_against_the_fixture_root(self):
        rig = RigPort()
        _dispatch(_registry(rig=rig), file_content_base64=_b64(_sample_export()))
        assert FIXTURE_ROOT in rig.state_calls

    def test_the_response_carries_the_console_side_inventory_verbatim(self):
        rig = RigPort()
        execution = _dispatch(_registry(rig=rig), file_content_base64=_b64(_sample_export()))
        payload = json.loads(execution.result.content)
        assert payload["console_rig"]["inventory"]["observed_count"] == 1


class TestNoNewTransportSurface:
    """AC-VWX-024 ④ — 신규 REST 라우트·웹소켓·execution_port 직접 접근 0건."""

    def test_the_handler_never_calls_execution_port(self):
        # _NeverCalledExecutionPort raises on any .execute() call — a clean
        # dispatch with no exception is the proof.
        rig = RigPort()
        execution = _dispatch(_registry(rig=rig), file_content_base64=_b64(_sample_export()))
        assert execution.result.is_error is False

    def test_the_handler_source_never_references_execution_port_directly(self):
        tree = ast.parse(TOOLS_SOURCE.read_text(encoding="utf-8"))
        target = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "precheck_vectorworks_diff":
                target = node
                break
        assert target is not None, "precheck_vectorworks_diff handler not found in source"
        for inner in ast.walk(target):
            if isinstance(inner, ast.Name) and inner.id == "execution_port":
                raise AssertionError("precheck_vectorworks_diff references execution_port directly")


class TestPayloadShape:
    """대조 결과가 report.py 페이로드 형태로 되돌아온다(스모크)."""

    def test_missing_and_matched_fixtures_report_correctly(self):
        rig = RigPort(fixtures={})  # console has nothing patched
        execution = _dispatch(_registry(rig=rig), file_content_base64=_b64(_sample_export()))
        payload = json.loads(execution.result.content)
        assert len(payload["diffs"]["missing_in_console"]) == 1
        assert payload["diffs"]["missing_in_console"][0]["instrument_type"] == "Robin MMX Spot"
        skipped_kinds = {entry["kind"] for entry in payload["skipped_checks"]}
        assert "fid_cid_identity_unreachable" in skipped_kinds

    def test_a_matching_console_fixture_produces_no_missing_entry(self):
        execution = _dispatch(_registry(), file_content_base64=_b64(_sample_export()))
        payload = json.loads(execution.result.content)
        assert payload["diffs"]["missing_in_console"] == []

    def test_missing_file_content_argument_is_a_structured_error_not_a_crash(self):
        execution = _dispatch(_registry())
        assert execution.result.is_error is True

    def test_invalid_base64_is_a_structured_error_not_a_crash(self):
        execution = _dispatch(_registry(), file_content_base64="not-valid-base64!!!")
        assert execution.result.is_error is True
