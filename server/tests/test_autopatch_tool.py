"""M7 — `apply_vectorworks_patch` 툴 배선 (AC-AUTOPATCH-023).

`server/tests/test_vwx_tool.py`·`test_prechk_tool.py`의 확립된 패턴을 따른다 —
등록은 **디스패치로** 확인하고(dict 조회 금지), 스키마에 리그 식별자가 없음을 검증한다.

**이 툴이 다른 점**: 콘솔에 쓰지 않는다. 그래서 실행 포트는 **호출되면 즉시 실패하는 대역**을
꽂아 둔다 — 배선 계층에서도 "서버가 패치를 실행하지 않는다"가 지켜지는지가 여기서 걸린다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from server.llm.types import ToolCall
from server.orchestrator.tools import TOOL_NAMES, build_toolset
from server.prechk.inventory import FIXTURE_ROOT
from server.vwx.typemap import FIXTURE_TYPE_LIBRARY_ROOT
from server.vwx.verdicts import ALREADY_PATCHED_IDENTICAL

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TOOL = "apply_vectorworks_patch"

LED = "Robin LEDBeam 350"


class _NeverCalledExecutionPort:
    """이 툴은 콘솔에 발화하지 않는다 — 호출되면 즉시 실패한다."""

    def execute(self, command: str):
        raise AssertionError(f"{TOOL} must never call execution_port: {command}")


class RigPort:
    """픽스처 인벤토리 + FixtureType 라이브러리를 함께 내는 대역."""

    def __init__(self, fixtures: dict[int, dict[str, str]] | None = None):
        self.fixtures = {} if fixtures is None else fixtures
        self.state_calls: list[str] = []

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
        if path == FIXTURE_TYPE_LIBRARY_ROOT:
            return {
                "ok": True,
                "path": path,
                "node": {"childCount": 1},
                "children": [{"i": 3, "name": LED}],
                "truncated": False,
            }
        if path == f"{FIXTURE_TYPE_LIBRARY_ROOT}/3/DMXModes":
            return {
                "ok": True,
                "path": path,
                "node": {"childCount": 1},
                "children": [{"i": 1, "name": "Mode 1"}],
                "truncated": False,
            }
        return {"ok": False, "path": path, "error": "not readable"}

    def query_property(self, path: str, property_name: str) -> dict:
        if path.startswith(FIXTURE_TYPE_LIBRARY_ROOT):
            if property_name == "Name":
                return {"ok": True, "path": path, "property": property_name, "value": "Mode 1"}
            return {"ok": False, "path": path, "property": property_name, "error": "not readable"}
        slot = int(path.rsplit("/", 1)[1])
        value = self.fixtures.get(slot, {}).get(property_name)
        if value is None:
            return {"ok": False, "path": path, "property": property_name, "error": "not readable"}
        return {"ok": True, "path": path, "property": property_name, "value": value}


def _registry(*, rig: RigPort | None = None):
    rig = rig or RigPort()
    return build_toolset(
        execution_port=_NeverCalledExecutionPort(), state_port=rig, property_port=rig
    )


def _report(*, footprint: int | None = 16, universe: int = 1, address: int = 1) -> dict:
    """1단계 payload의 최소 형태 — 후보 1건 + 그 후보의 도면 값."""
    fixture = {
        "unit_number": "1",
        "instrument_type": LED,
        "gdtf_fixture": None,
        "mode": "Mode 1",
        "footprint": footprint,
        "system": None,
        "universe": universe,
        "address": address,
        "classification": "patched",
        "address_basis": "universe_address_direct",
    }
    return {
        "designed_rig": {"fixture_count": 1, "fixtures": [fixture]},
        "diffs": {
            "performed": True,
            "missing_in_console": [
                {
                    "unit_number": "1",
                    "instrument_type": LED,
                    "universe": universe,
                    "address": address,
                    "detail": "",
                }
            ],
            "address_collision": [],
            "quantity_mismatch": [],
        },
        "skipped_checks": [],
    }


def _dispatch(registry, **arguments):
    return registry.dispatch(ToolCall(id="p1", name=TOOL, arguments=arguments))


def _payload(execution) -> dict:
    return json.loads(execution.result.content)


def _candidate_id(payload: dict) -> str:
    return payload["plan"]["candidates"][0]["id"]


def _full_call(registry, *, rig_report=None, dry_run=True, **overrides):
    """후보 1건을 실제로 통과시키는 호출 — 두 단계(식별자 확보 → 선택)."""
    report = rig_report if rig_report is not None else _report()
    first = _payload(_dispatch(registry, report=report))
    candidate = _candidate_id(first)
    arguments = {
        "report": report,
        "selected": [candidate],
        "fid_range": {"start": 501, "end": 599},
        "names": {candidate: "LEDBeam 501"},
        # 타입 매칭은 **사용자 확인 없이 확정되지 않는다**(M3 · 위험 R2) — 확인된 별칭이
        # 없으면 모든 항목이 `type_confirmation_pending`으로 빠진다. 그것이 설계된 기본값이고,
        # 아래 `test_an_unconfirmed_type_match_never_reaches_the_lua`가 그 기본값을 지킨다.
        "type_aliases": {LED: {"type": LED, "mode": "Mode 1"}},
        "dry_run": dry_run,
    }
    arguments.update(overrides)
    return _payload(_dispatch(registry, **arguments)), candidate


# --------------------------------------------------------------------------
# AC-AUTOPATCH-023① ② — 5지점 등록을 dispatch로 확인
# --------------------------------------------------------------------------


class TestRegistrationByDispatch:
    def test_the_name_is_in_the_closed_tool_name_tuple(self):
        assert TOOL in TOOL_NAMES

    def test_the_definition_is_advertised(self):
        assert TOOL in {definition.name for definition in _registry().definitions()}

    def test_dispatch_reaches_a_handler_and_not_the_unknown_tool_path(self):
        execution = _dispatch(_registry(), report=_report())
        assert execution.result.name == TOOL
        assert execution.result.is_error is False
        assert "unknown tool" not in execution.result.content

    def test_every_advertised_name_is_dispatchable(self):
        """AC-023② — `advertised == set(TOOL_NAMES)`."""
        advertised = {definition.name for definition in _registry().definitions()}
        assert advertised == set(TOOL_NAMES)

    def test_the_handler_is_reachable_through_the_handlers_dict_entry(self):
        """5지점 중 마지막 — 이름이 등재됐어도 dict에 없으면 여기서 걸린다."""
        execution = _registry().dispatch(ToolCall(id="p2", name=TOOL, arguments={}))
        assert execution.result.name == TOOL
        assert "unknown tool" not in execution.result.content


# --------------------------------------------------------------------------
# AC-AUTOPATCH-023③ — 스키마에 리그 식별자가 없다
# --------------------------------------------------------------------------


def _schema() -> dict:
    for definition in _registry().definitions():
        if definition.name == TOOL:
            return definition.parameters
    raise AssertionError(f"{TOOL} is not advertised")


# `fid_range`는 리그 식별자가 **아니다** — 기존 객체를 가리키는 번호가 아니라
# 사용자가 "비었다"고 확인해 준 **배정 대상 범위**이고, REQ-AUTOPATCH-007이 그것을
# 생략하면 실행을 거부하라고 요구한다. 금지 대상은 콘솔의 기존 객체를 지목하는 식별자다.
_RIG_IDENTIFIER_WORDS = ("group", "pool", "slot", "fixture_id", "fixture_index", "cid")


def test_no_rig_identifier_parameter():
    schema = _schema()
    properties = schema.get("properties", {})
    assert properties, "schema has no properties — the check would be vacuous"
    for name in properties:
        lowered = name.lower()
        assert not any(word in lowered for word in _RIG_IDENTIFIER_WORDS), (
            f"{TOOL} takes a rig identifier: {name}"
        )


def test_rig_identifier_control_is_caught():
    """AC-023③ 비공허성 — 리그 식별자를 심은 스키마 사본에서 위 단정이 실제로 실패한다."""
    planted = {**_schema().get("properties", {}), "slot": {"type": "integer"}}
    offenders = [
        name for name in planted if any(word in name.lower() for word in _RIG_IDENTIFIER_WORDS)
    ]
    assert offenders == ["slot"]


def test_the_schema_is_a_closed_object():
    schema = _schema()
    assert schema.get("type") == "object"
    assert schema.get("additionalProperties") is False
    assert schema.get("required") == ["report"]


def test_the_schema_declares_the_semi_automatic_model():
    """모델이 읽는 유일한 안내면이다 — 서버가 실행하지 않는다는 사실이 여기 있어야 한다."""
    (definition,) = [d for d in _registry().definitions() if d.name == TOOL]
    assert "NEVER EXECUTES" in definition.description
    assert "dry_run defaults to TRUE" in definition.description


# --------------------------------------------------------------------------
# 배선이 실제로 동작하는가 — 종단 디스패치
# --------------------------------------------------------------------------


class TestTheWiredPipelineActuallyRuns:
    def test_a_bare_call_lists_candidates_and_selects_none(self):
        """기본 선택 0건 — 후보를 보여줄 뿐 아무것도 만들지 않는다."""
        payload = _payload(_dispatch(_registry(), report=_report()))
        assert len(payload["plan"]["candidates"]) == 1
        assert payload["plan"]["selected"] == []
        assert payload["plan"]["targets"] == []
        assert "handoff" not in payload  # 대상이 0건이면 Lua도 절차도 없다

    def test_selecting_without_a_fid_range_is_refused(self):
        """REQ-AUTOPATCH-007 — 빈 FID 범위를 주지 않으면 배정하지 않는다."""
        registry = _registry()
        report = _report()
        candidate = _candidate_id(_payload(_dispatch(registry, report=report)))
        payload = _payload(_dispatch(registry, report=report, selected=[candidate]))
        assert payload["plan"]["ok"] is False
        assert payload["plan"]["rejection"]["code"] == "fid_range_required"

    def test_an_unconfirmed_type_match_never_reaches_the_lua(self):
        """위험 R2 — 사용자가 확인하지 않은 타입 매칭으로는 아무것도 전달하지 않는다."""
        registry = _registry()
        report = _report()
        candidate = _candidate_id(_payload(_dispatch(registry, report=report)))
        payload = _payload(
            _dispatch(
                registry,
                report=report,
                selected=[candidate],
                fid_range={"start": 501, "end": 599},
                names={candidate: "LEDBeam 501"},
                dry_run=False,
            )
        )
        assert payload["handoff"]["lua_source"] is None
        assert [x["code"] for x in payload["handoff"]["exclusions"]] == [
            "type_confirmation_pending"
        ]

    def test_a_selected_candidate_reaches_the_rendered_lua(self):
        payload, _ = _full_call(_registry())
        assert "AddFixtures({" in payload["handoff"]["lua_source"]
        assert payload["handoff"]["dry_run"] is True
        assert payload["handoff"]["delivered"] is False

    def test_the_designed_footprint_comes_from_the_report_not_the_console(self):
        """§0 항목 2a③ — 도면이 폭을 주지 않으면 추측하지 않고 제외된다."""
        payload, _ = _full_call(_registry(), rig_report=_report(footprint=None))
        assert payload["handoff"]["lua_source"] is None
        assert [x["code"] for x in payload["handoff"]["exclusions"]] == ["footprint_unknown"]

    def test_dry_run_is_true_when_the_argument_is_omitted(self):
        registry = _registry()
        report = _report()
        candidate = _candidate_id(_payload(_dispatch(registry, report=report)))
        payload = _payload(
            _dispatch(
                registry,
                report=report,
                selected=[candidate],
                fid_range={"start": 501, "end": 599},
                names={candidate: "LEDBeam 501"},
            )
        )
        assert payload["handoff"]["dry_run"] is True
        assert payload["handoff"]["procedure"] == []

    def test_delivery_adds_the_procedure_and_the_verification_handoff(self):
        payload, _ = _full_call(_registry(), dry_run=False)
        assert payload["handoff"]["delivered"] is True
        assert payload["handoff"]["procedure"]
        assert payload["verification"]["results"]

    def test_the_second_pass_skips_a_fixture_that_now_exists(self):
        """멱등이 배선을 통해서도 성립한다 — 사람이 실행한 뒤의 재호출."""
        after_execution = RigPort(
            fixtures={
                1: {
                    "Patch": "1.001",
                    "FixtureType": "FixtureType 3",
                    "Mode": "1 Mode 1",
                    "Name": "LEDBeam 501",
                }
            }
        )
        payload, _ = _full_call(_registry(rig=after_execution), dry_run=False)
        assert payload["handoff"]["lua_source"] is None
        assert [x["code"] for x in payload["handoff"]["exclusions"]] == [ALREADY_PATCHED_IDENTICAL]
        assert payload["verification"]["results"] == []

    def test_the_verification_section_says_a_pre_execution_read_is_not_a_failure(self):
        payload, _ = _full_call(_registry(), dry_run=False)
        assert "아직 사람이 플러그인을 실행하지 않았다면" in payload["verification"]["note"]

    def test_a_missing_name_is_reported_rather_than_invented(self):
        payload, _ = _full_call(_registry(), names={}, dry_run=False)
        assert [x["code"] for x in payload["handoff"]["exclusions"]] == ["fixture_name_missing"]


class TestTheWiringRefusesRatherThanGuesses:
    def test_a_missing_report_is_an_error_not_an_empty_plan(self):
        execution = _dispatch(_registry(), report="not-an-object")
        assert execution.result.is_error is True
        assert "report" in execution.result.content

    def test_a_non_boolean_dry_run_is_rejected(self):
        execution = _dispatch(_registry(), report=_report(), dry_run="false")
        assert execution.result.is_error is True
        assert "dry_run" in execution.result.content

    def test_a_non_object_names_argument_is_rejected(self):
        execution = _dispatch(_registry(), report=_report(), names=["LEDBeam"])
        assert execution.result.is_error is True
        assert "names" in execution.result.content

    def test_an_unwired_property_port_says_so_instead_of_reporting_zero(self):
        class StateOnly:
            def query_state(self, path: str) -> dict:
                return {"ok": False, "path": path}

        registry = build_toolset(execution_port=_NeverCalledExecutionPort(), state_port=StateOnly())
        execution = _dispatch(registry, report=_report())
        assert execution.result.is_error is True
        assert "property_port" in execution.result.content


@pytest.mark.parametrize("dry_run", [True, False])
def test_no_console_write_leaves_the_wired_tool(dry_run):
    """배선 계층에서도 발화 0건 — 실행 포트 대역은 호출되면 AssertionError를 던진다."""
    payload, _ = _full_call(_registry(), dry_run=dry_run)
    assert payload["handoff"]["execution_performed_by"] == "human"


# --------------------------------------------------------------------------
# 재조회 절단 — 배선 계층에서 막히는가
# --------------------------------------------------------------------------


class _TruncatingRigPort(RigPort):
    """`childCount`는 진짜 총계인데 자식 목록이 짧게 오는 콘솔 — 이 빌드의 **기본 경로**."""

    def query_state(self, path: str) -> dict:
        payload = super().query_state(path)
        if path == FIXTURE_ROOT:
            payload["node"]["childCount"] = 5  # 5대 선언, 목록은 0대
            payload["truncated"] = True
        return payload


def test_a_truncated_console_read_blocks_creation_and_says_why():
    payload, _ = _full_call(_registry(rig=_TruncatingRigPort()), dry_run=False)
    assert payload["console_read"]["complete_enough_to_judge_absence"] is False
    assert payload["console_read"]["caveat"]["kind"] == "console_read_incomplete"
    assert payload["handoff"]["lua_source"] is None
    assert [x["code"] for x in payload["handoff"]["exclusions"]] == ["console_read_incomplete"]


def test_the_truncation_block_control_a_complete_read_still_delivers():
    """비공허성 — 완전한 재조회에서는 같은 경로가 Lua를 실제로 낸다."""
    payload, _ = _full_call(_registry(), dry_run=False)
    assert payload["console_read"]["complete_enough_to_judge_absence"] is True
    assert "AddFixtures({" in payload["handoff"]["lua_source"]
