"""M7 — `apply_vectorworks_patch` 툴 배선 (AC-AUTOPATCH-023).

`server/tests/test_vwx_tool.py`·`test_prechk_tool.py`의 확립된 패턴을 따른다 —
등록은 **디스패치로** 확인하고(dict 조회 금지), 스키마에 리그 식별자가 없음을 검증한다.

**이 툴이 다른 점**: 콘솔에 쓰지 않는다. 그래서 실행 포트는 **호출되면 즉시 실패하는 대역**을
꽂아 둔다 — 배선 계층에서도 "서버가 패치를 실행하지 않는다"가 지켜지는지가 여기서 걸린다.
"""

from __future__ import annotations

import json
import sys
from functools import cache
from pathlib import Path
from types import ModuleType

import pytest

from server.llm.types import ToolCall
from server.orchestrator.tools import TOOL_NAMES, build_toolset
from server.prechk.inventory import FIXTURE_ROOT
from server.vwx.patchplan import (
    ASSUMPTION_71_GO,
    ASSUMPTION_71_INCONCLUSIVE,
    ASSUMPTION_71_NEGATIVE,
    ASSUMPTION_71_VALUES,
    validate_assumption_71,
)
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
        # 실측: FID는 이 콘솔에서 읽힌다(`ASSUMPTION-71` GO) — 슬롯≠FID 조건도 재현한다.
        if property_name == "FID":
            return {"ok": True, "path": path, "property": property_name, "value": 19 + slot}
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


# **PRECHK 원본 목록 그대로**다(`test_prechk_tool.py` · `test_vwx_tool.py`와 동일) —
# design.md §2.3의 "PRECHK 관례 계승"이 요구하는 것이 이것이다. [round11 M7 N04] 이전 판은
# `fid` 하나를 정당화하면서 `address`·`universe`·`fixture`까지 함께 지웠다. 그 셋은 통과에
# 필요하지도 않았고(현 스키마에 그 이름이 없다) 이유도 적히지 않았다 — 미래에 정확히
# SPEC이 금하는 유형의 파라미터가 들어와도 이 게이트만 통과하게 되는 조용한 약화였다.
_RIG_IDENTIFIER_WORDS = ("group", "pool", "slot", "fixture", "address", "universe", "fid")

# 예외는 **이름 완전 일치로만** 둔다. `fid_range`는 콘솔의 기존 객체를 가리키는 번호가 아니라
# 사용자가 "비었다"고 확인해 준 **배정 대상 범위**이고, REQ-AUTOPATCH-007이 그것을 생략하면
# 거부하라고 요구한다. 완전 일치라서 `fid`·`fixture_id`는 여전히 걸린다.
_RIG_IDENTIFIER_EXCEPTIONS = frozenset({"fid_range", "fid_range_visually_confirmed_empty"})


def _offending_names(properties) -> list[str]:
    return sorted(
        name
        for name in properties
        if name not in _RIG_IDENTIFIER_EXCEPTIONS
        and any(word in name.lower() for word in _RIG_IDENTIFIER_WORDS)
    )


def test_no_rig_identifier_parameter():
    properties = _schema().get("properties", {})
    assert properties, "schema has no properties — the check would be vacuous"
    assert _offending_names(properties) == []


@pytest.mark.parametrize("planted", ["slot", "universe", "address", "fixture_id", "group_id"])
def test_rig_identifier_control_is_caught(planted):
    """AC-023③ 비공허성 — 같은 헬퍼를 타고, 심은 이름에서 **실제로 실패한다**.

    [round11 M7 N05] 이전 판은 본 테스트의 단정을 부르지 않고 같은 내포 표현을 새로 썼다 —
    본 테스트가 엉뚱한 대상을 순회하도록 깨져도 대조군은 그대로 통과했다.
    """
    properties = {**_schema().get("properties", {}), planted: {"type": "integer"}}
    assert _offending_names(properties) == [planted]


def test_the_fid_range_exception_is_name_exact_not_substring():
    """예외가 `fid`를 통째로 열어주지 않는다."""
    assert _offending_names({"fid": {}, "fixture_id": {}}) == ["fid", "fixture_id"]


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
        # 검증은 전달분이 아니라 **승인 항목 전체**를 본다 — 2회차에서 결과가 비면
        # AC-021①("승인 항목마다 확인 결과")이 성립하지 않는다(round11 M6 N04).
        assert [r["outcome"] for r in payload["verification"]["results"]] == ["observed"]

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


def test_a_truncated_console_read_refuses_before_anything_is_planned():
    """절단된 콘솔에서는 FID 사전검사가 먼저 거부한다 — 배정도 전달도 없다.

    두 가드가 같은 루트를 읽으므로 절단이면 FID 쪽이 먼저 걸린다. 그래도 `console_read`는
    **모든 분기에서** 실린다 — 사용자가 거부 이유를 payload에서 바로 볼 수 있어야 한다.
    """
    payload, _ = _full_call(_registry(rig=_TruncatingRigPort()), dry_run=False)
    assert payload["console_read"]["complete_enough_to_judge_absence"] is False
    assert payload["console_read"]["caveat"]["kind"] == "console_read_incomplete"
    assert payload["plan"]["ok"] is False
    assert payload["plan"]["rejection"]["code"] == "fid_precheck_read_incomplete"
    assert "handoff" not in payload


def test_an_unreadable_patch_property_also_counts_as_unread():
    """열거는 됐는데 주소를 못 읽은 픽스처도 미판독이다(round11 M6 N02).

    `missing_count`는 열거·복구 축만 센다 — 주소 판독 실패는 그 축에 잡히지 않는데,
    그 픽스처는 점유·멱등·검증 어디에서도 보이지 않으므로 '없음'을 단정할 수 없다.
    """
    blind = RigPort(
        fixtures={
            1: {"Patch": None, "FixtureType": "FixtureType 3", "Mode": "1 Mode 1", "Name": "x"}
        }
    )
    payload, _ = _full_call(_registry(rig=blind), dry_run=False)
    caveat = payload["console_read"]["caveat"]
    assert caveat["kind"] == "console_read_incomplete"
    assert caveat["unreadable_address_count"] == 1
    assert caveat["missing_count"] == 0  # 열거 축은 깨끗하다 — 그래서 이전 판이 놓쳤다
    assert payload["handoff"]["lua_source"] is None
    assert [x["code"] for x in payload["handoff"]["exclusions"]] == ["console_read_incomplete"]


def test_the_truncation_block_control_a_complete_read_still_delivers():
    """비공허성 — 완전한 재조회에서는 같은 경로가 Lua를 실제로 낸다."""
    payload, _ = _full_call(_registry(), dry_run=False)
    assert payload["console_read"]["complete_enough_to_judge_absence"] is True
    assert "AddFixtures({" in payload["handoff"]["lua_source"]


# --------------------------------------------------------------------------
# round11 회귀 — 무관한 후보 하나가 겹침 가드를 없애지 못한다
# --------------------------------------------------------------------------


def _multi_report(rows):
    fixtures = [
        {
            "unit_number": str(i + 1),
            "instrument_type": LED,
            "gdtf_fixture": None,
            "mode": "Mode 1",
            "footprint": 16,
            "system": None,
            "universe": u,
            "address": a,
            "classification": "patched",
            "address_basis": "universe_address_direct",
        }
        for i, (u, a) in enumerate(rows)
    ]
    return {
        "designed_rig": {"fixture_count": len(fixtures), "fixtures": fixtures},
        "diffs": {
            "performed": True,
            "missing_in_console": [
                {
                    "unit_number": str(i + 1),
                    "instrument_type": LED,
                    "universe": u,
                    "address": a,
                    "detail": "",
                }
                for i, (u, a) in enumerate(rows)
            ],
            "address_collision": [],
            "quantity_mismatch": [],
        },
        "skipped_checks": [],
    }


def _deliver(rig, rows):
    registry = _registry(rig=rig)
    report = _multi_report(rows)
    candidates = [
        c["id"] for c in _payload(_dispatch(registry, report=report))["plan"]["candidates"]
    ]
    return _payload(
        _dispatch(
            registry,
            report=report,
            selected=candidates,
            fid_range={"start": 501, "end": 599},
            names={c: f"LEDBeam {i}" for i, c in enumerate(candidates)},
            type_aliases={LED: {"type": LED, "mode": "Mode 1"}},
            dry_run=False,
        )
    )


_INTRUDER = {
    1: {"Patch": "1.005", "FixtureType": "FixtureType 3", "Mode": "1 Mode 1", "Name": "existing"}
}


def test_an_unrelated_second_candidate_does_not_disable_the_overlap_guard():
    """[round11 M7 N01] 계획 구간(1..16) 안에 기존 픽스처(1.5)가 있으면 A는 나가지 못한다.

    이전 판은 면제 집합을 **모든 대상 주소**로 잡아서, B(1.5)를 함께 고르는 것만으로
    그 픽스처가 occupied에서 사라지고 A가 점유된 구간으로 전달됐다(재현 확인).
    """
    payload = _deliver(RigPort(fixtures=_INTRUDER), [(1, 1), (1, 5)])
    codes = sorted(x["code"] for x in payload["handoff"]["exclusions"])
    assert "address_already_occupied" in codes
    assert payload["handoff"]["lua_source"] is None


def test_the_overlap_guard_control_a_clear_span_still_delivers():
    """비공허성 — 같은 두 후보라도 콘솔이 비어 있으면 겹치는 B만 빠지고 A는 나간다."""
    payload = _deliver(RigPort(), [(1, 1), (1, 5)])
    assert [x["code"] for x in payload["handoff"]["exclusions"]] == ["address_overlap_in_plan"]
    assert "AddFixtures({" in payload["handoff"]["lua_source"]


def test_the_single_candidate_case_still_reports_occupancy():
    payload = _deliver(RigPort(fixtures=_INTRUDER), [(1, 1)])
    assert [x["code"] for x in payload["handoff"]["exclusions"]] == ["address_already_occupied"]


def test_the_payload_discloses_that_tail_overlap_is_undetectable():
    """[round11 N04] 기존 픽스처 폭을 못 읽는다는 사실과 그 결과를 구조화해 싣는다."""
    payload = _deliver(RigPort(), [(1, 1)])
    kinds = [c["kind"] for c in payload["plan"]["skipped_checks"]]
    assert "existing_footprint_unreadable" in kinds


def _fixture(patch: str, name: str) -> dict:
    return {"Patch": patch, "FixtureType": "FixtureType 3", "Mode": "1 Mode 1", "Name": name}


def test_a_re_call_reads_as_already_patched_even_with_an_intruder_in_the_span():
    """[round12 R05] 멱등이 점유보다 **먼저** 판정돼야 2회차가 '이미 했음'으로 읽힌다.

    우리 자리(1.1)에 우리와 동일한 픽스처가 있고 구간 안(1.5)에 무관한 픽스처가 하나 더
    있으면, 점유 선별이 앞서면 항목이 `address_already_occupied`로 먼저 빠져
    `already_patched_identical`이 영영 나오지 않는다 — REQ-AUTOPATCH-022가 금지하는 뭉갬이다.
    """
    rig = RigPort(fixtures={1: _fixture("1.001", "ours"), 2: _fixture("1.005", "other")})
    payload = _deliver(rig, [(1, 1)])
    assert [x["code"] for x in payload["handoff"]["exclusions"]] == [ALREADY_PATCHED_IDENTICAL]


def test_a_call_that_delivered_nothing_does_not_ask_about_plugin_execution():
    """[round12 R04] 전달분 0건인 거부 분기에서 실행 재확인 안내가 나가면 거짓말이다."""
    payload = _deliver(RigPort(fixtures=_INTRUDER), [(1, 1)])
    assert payload["handoff"]["lua_source"] is None
    guidance = " ".join(payload["verification"]["guidance"])
    assert "플러그인을 실제로 실행했는지" not in guidance


def test_a_call_that_delivered_nothing_reports_zero_created():
    """[round12 R06] Lua를 한 줄도 내지 않은 호출이 '1건 생성'을 보고하면 거짓 성공이다."""
    rig = RigPort(fixtures={1: _fixture("1.001", "ours")})
    payload = _deliver(rig, [(1, 1)])
    assert payload["handoff"]["lua_source"] is None
    assert payload["verification"]["created_count"] == 0
    assert payload["verification"]["observed_count"] == 1  # 있긴 하다 — 우리가 만든 게 아닐 뿐


def test_an_unpatched_console_fixture_does_not_halt_the_tool():
    """[round12 R08] 미패치 예비 픽스처 1대가 리그에 있다고 툴이 멈추면 안 된다."""
    rig = RigPort(fixtures={1: _fixture("0.0", "spare")})
    payload = _deliver(rig, [(1, 1)])
    assert payload["console_read"]["complete_enough_to_judge_absence"] is True
    assert "AddFixtures({" in payload["handoff"]["lua_source"]


def test_a_dry_run_reports_zero_delivered_and_does_not_ask_about_execution():
    """[round13 S03] 드라이런은 전달분 0건이다 — `delivered`가 두 계층에서 같은 것을 뜻해야 한다.

    이전 판은 같은 payload에 `handoff.delivered=false`와 `delivered_count=1`을 함께 싣고,
    기본 경로인 드라이런에서 "플러그인을 실제로 실행했는지 확인하라"를 냈다 —
    검토만 받으려던 Lua를 라이브 콘솔에서 실행하게 만드는 안내다.
    """
    payload, _ = _full_call(_registry(), dry_run=True)
    assert payload["handoff"]["delivered"] is False
    assert payload["verification"]["delivered_count"] == 0
    assert [r["delivered"] for r in payload["verification"]["results"]] == [False]
    assert "플러그인을 실제로 실행했는지" not in " ".join(payload["verification"]["guidance"])


def test_the_dry_run_control_a_delivery_does_report_delivered():
    """비공허성 — 전달 요청에서는 같은 필드가 참이 된다."""
    payload, _ = _full_call(_registry(), dry_run=False)
    assert payload["handoff"]["delivered"] is True
    assert payload["verification"]["delivered_count"] == 1
    assert "플러그인을 실제로 실행했는지" in " ".join(payload["verification"]["guidance"])


def test_a_fixture_whose_patch_value_is_unparsable_blocks_the_tool():
    """[round13 S01] 읽히긴 했으나 주소가 아닌 값이 있으면 '비어 있다'고 판단하지 않는다."""
    rig = RigPort(fixtures={1: _fixture("1-5", "weird")})
    payload = _deliver(rig, [(1, 1)])
    assert payload["console_read"]["complete_enough_to_judge_absence"] is False
    assert payload["handoff"]["lua_source"] is None


def test_the_payload_discloses_that_the_negative_assumption_branch_is_unreachable():
    """[round13 S04] 도달 불가 분기를 숨기지 않는다."""
    payload, _ = _full_call(_registry(), dry_run=True)
    reach = payload["assumption_71_reachability"]
    assert reach["injected"] == "go"
    assert reach["negative_branch_reachable"] is False


# --------------------------------------------------------------------------
# --- round15 T08 대조군 (ASSUMPTION-71 도달성 표기) ---
#
# round14 T08은 `assumption_71_reachability`를 (a) 닫힌 어휘 검증을 거치게 하고
# (b) 하드코딩 자기주장이 아니라 **주입값에서 파생**하게 고쳤다. 그런데 저장소 전체
# 테스트에서 `validate_assumption_71` 참조가 **0건**이었다 — 그 수정을 되돌리는 뮤테이션이
# 전부 통과한다는 뜻이다. 여기서 그 구멍을 닫는다.
#
# 방법은 이 저장소의 선례를 따른다(`test_autopatch_verify.py` 약 463행 · `APPLY_SOURCE`):
# **프로덕션 소스의 사본에 주입 한 줄만 바꿔 심고, 그 사본을 적재해 실제로 디스패치**한 뒤
# payload를 본다. `_INJECTED_ASSUMPTION_71`은 `build_toolset` 안의 지역 이름이라
# monkeypatch로 닿지 않는다 — 사본 적재가 유일하게 정직한 경로다.
# --------------------------------------------------------------------------

TOOLS_PATH = PROJECT_ROOT / "server" / "orchestrator" / "tools.py"
TOOLS_SOURCE = TOOLS_PATH.read_text(encoding="utf-8")

#: 사본에서 갈아끼울 **주입 한 줄**. 이 앵커가 사라지면 아래 대조군이 전부 즉시 실패한다.
INJECTION_LINE = "    _INJECTED_ASSUMPTION_71 = ASSUMPTION_71_GO"

_TOOLS_UNDER_TEST = "server.orchestrator._tools_under_test"


def _load_tools(source: str) -> dict[str, object]:
    """`tools.py` 소스를 **진짜 모듈로** 적재한다 — `test_autopatch_execute._load` 관례."""
    module = ModuleType(_TOOLS_UNDER_TEST)
    module.__file__ = str(TOOLS_PATH)
    saved = sys.modules.get(_TOOLS_UNDER_TEST)
    sys.modules[_TOOLS_UNDER_TEST] = module
    try:
        exec(compile(source, str(TOOLS_PATH), "exec"), module.__dict__)
    finally:
        if saved is None:
            del sys.modules[_TOOLS_UNDER_TEST]
        else:
            sys.modules[_TOOLS_UNDER_TEST] = saved
    return module.__dict__


@cache
def _tools_with_injection(value: str) -> dict[str, object]:
    """주입값만 `value`로 바꾼 `tools.py` 사본을 적재해 돌려준다.

    상수 이름이 아니라 **값 리터럴**로 심는다 — `ASSUMPTION_71_INCONCLUSIVE`는 `tools.py`가
    import하지 않으므로 이름으로 심으면 `NameError`가 나고, 그러면 대조군이 "도달성 파생"이
    아니라 "이름 존재"를 시험하게 된다. 값은 프로덕션 상수에서 가져온다(복사 금지).
    """
    assert TOOLS_SOURCE.count(INJECTION_LINE) == 1, "주입 앵커가 유일하지 않다"
    return _load_tools(
        TOOLS_SOURCE.replace(INJECTION_LINE, f"    _INJECTED_ASSUMPTION_71 = {value!r}", 1)
    )


def _reachability(value: str) -> dict:
    """`value`를 주입한 사본을 **실제로 디스패치**해 도달성 payload를 돌려준다."""
    rig = RigPort()
    registry = _tools_with_injection(value)["build_toolset"](
        execution_port=_NeverCalledExecutionPort(), state_port=rig, property_port=rig
    )
    return _payload(_dispatch(registry, report=_report()))["assumption_71_reachability"]


# ---- ① 닫힌 어휘 검증 자체에 대조군 -------------------------------------------


def test_the_registered_vocabulary_is_exactly_the_three_named_constants():
    """[round15 C1] `ASSUMPTION_71_VALUES`에 값을 더하거나 빼면 이 단정이 깨진다."""
    assert (
        frozenset({ASSUMPTION_71_GO, ASSUMPTION_71_NEGATIVE, ASSUMPTION_71_INCONCLUSIVE})
        == ASSUMPTION_71_VALUES
    )


@pytest.mark.parametrize("value", sorted(ASSUMPTION_71_VALUES))
def test_validate_assumption_71_passes_every_registered_value_through_unchanged(value: str):
    """등재된 3값은 그대로 통과한다 — 목록은 **프로덕션 상수에서** 받는다(복사 금지)."""
    assert validate_assumption_71(value) == value


# 미등재 표본 — 등재 3값의 형제 축을 표로 연다: 대소문자 변형 · 공백 · 그럴듯한 유의어 ·
# 빈 문자열 · 실측 판정처럼 보이는 문자열.
_UNREGISTERED_ASSUMPTION_71_VALUES = (
    "GO",
    " go",
    "go ",
    "yes",
    "positive",
    "unknown",
    "",
    "maybe",
)


@pytest.mark.parametrize("value", _UNREGISTERED_ASSUMPTION_71_VALUES)
def test_validate_assumption_71_refuses_every_unregistered_value(value: str):
    """[round15 C1] `validate_assumption_71` 본문을 `return value`로 바꾸면 전부 실패한다.

    payload로 나가는 판정 문자열은 닫힌 어휘여야 한다 — 오타 하나가 도달성 표기를
    조용히 뒤집으면 사람은 되돌릴 수 없는 생성을 잘못된 전제로 승인한다.
    """
    with pytest.raises(ValueError, match="assumption_71 must be one of"):
        validate_assumption_71(value)


# ---- ② payload가 주입값에서 파생된다 -------------------------------------------

# 세 값 전부에 대한 **기대 표**. 두 열이 `inconclusive`에서 갈린다 — 이전 판은 둘을
# 한 술어(`!= go`)로 묶어 "NEGATIVE 분기 도달 가능"이라는 거짓을 참으로 만들었다.
#
#   주입값          negative_branch_reachable   confirmation_branch_reachable
#   go              False                       False
#   negative        True                        True
#   inconclusive    False                       True     <- 여기서 갈린다
_REACHABILITY_TABLE = (
    (ASSUMPTION_71_GO, False, False),
    (ASSUMPTION_71_NEGATIVE, True, True),
    (ASSUMPTION_71_INCONCLUSIVE, False, True),
)


@pytest.mark.parametrize(
    "value,negative_reachable,confirmation_reachable",
    _REACHABILITY_TABLE,
    ids=[value for value, _, _ in _REACHABILITY_TABLE],
)
def test_the_reachability_payload_follows_the_injected_value(
    value: str, negative_reachable: bool, confirmation_reachable: bool
):
    """[round14 T08 · round15 C2] 도달성은 **주입값에서 파생**한다 — 자기주장이 아니다.

    어느 필드든 상수로 되돌리는 뮤테이션(예: `"negative_branch_reachable": False`)은
    이 표의 한 행 이상에서 실패한다. 사본에 심은 주입 한 줄만 다르고 나머지는
    프로덕션 소스 그대로이며, payload는 **실제 디스패치**로 얻는다.
    """
    reach = _reachability(value)
    assert reach["injected"] == value
    assert reach["negative_branch_reachable"] is negative_reachable
    assert reach["confirmation_branch_reachable"] is confirmation_reachable


def test_the_two_reachability_fields_are_not_the_same_proposition():
    """[round15 C3] 두 필드를 한 술어로 다시 묶으면 이 단정이 깨진다.

    `inconclusive` 주입에서 "NEGATIVE 값이 주입됐는가"(거짓)와 "확인 요구 분기가 열리는가"
    (참)가 갈린다. 필드 이름이 주장하는 것보다 넓은 술어를 쓰지 않는다는 규율의 본체다.
    """
    observed = {
        value: (reach["negative_branch_reachable"], reach["confirmation_branch_reachable"])
        for value, reach in ((v, _reachability(v)) for v, _, _ in _REACHABILITY_TABLE)
    }
    assert observed[ASSUMPTION_71_INCONCLUSIVE][0] != observed[ASSUMPTION_71_INCONCLUSIVE][1]
    assert [pair[0] for pair in observed.values()] != [pair[1] for pair in observed.values()]


def test_the_injected_value_reaches_the_payload_through_the_closed_vocabulary_validator():
    """[round15 C2] `"injected": validate_assumption_71(...)`에서 검증 호출을 빼면 실패한다.

    사본의 모듈 전역 `validate_assumption_71`을 감시자로 갈아끼운다 — `build_toolset`은
    그 이름을 **호출 시점에 모듈 전역에서** 찾으므로, payload가 검증을 거치지 않으면
    감시자가 호출되지 않고 표식도 실리지 않는다.
    """
    namespace = _tools_with_injection(ASSUMPTION_71_GO)
    original = namespace["validate_assumption_71"]
    seen: list[str] = []

    def _spy(value: str) -> str:
        seen.append(value)
        return f"{original(value)}/검증됨"

    namespace["validate_assumption_71"] = _spy
    try:
        rig = RigPort()
        registry = namespace["build_toolset"](
            execution_port=_NeverCalledExecutionPort(), state_port=rig, property_port=rig
        )
        reach = _payload(_dispatch(registry, report=_report()))["assumption_71_reachability"]
    finally:
        namespace["validate_assumption_71"] = original

    assert seen == [ASSUMPTION_71_GO]
    assert reach["injected"] == f"{ASSUMPTION_71_GO}/검증됨"


def test_an_unregistered_injection_never_reaches_the_payload():
    """[round15 C1] 툴 경계에서도 닫힌 어휘가 강제된다 — 미등재 주입은 payload를 못 만든다.

    `validate_assumption_71`과 `build_patch_plan`의 어휘 검증 **둘 다** 무력화해야만
    미등재 값이 payload로 나간다. 어느 하나만 되돌려도 이 단정은 여전히 통과하지만,
    위 `test_validate_assumption_71_refuses_every_unregistered_value`가 전자를 따로 잡는다.
    """
    with pytest.raises(ValueError, match="assumption_71 must be one of"):
        _reachability("maybe")


# --- round16 표 전단사·문장 전문 고정 (TableBijection) ---
#
# `_UNREGISTERED_ASSUMPTION_71_VALUES`는 자유 표본 목록이라 프로덕션에서 파생할 기준
# 집합이 없다. 그래서 두 겹으로 막는다:
#   ① 축소 트립와이어 — 표본을 하나 지우면 어긋나는 동결 집합,
#   ② **프로덕션에서 파생한** 근사 오타 표 — 등재 어휘 전부 × 정규화 변형 전부를
#      `itertools.product`로 만들어 프로덕션이 **하나도 받아들이지 않음**을 본다.
#      ②는 표를 지워서 줄일 수 없다 — 행이 `ASSUMPTION_71_VALUES`에서 나오기 때문이다.

#: 자유 표본의 동결 집합. 값을 더하거나 빼면 아래 단정이 깨진다.
_ROUND16_UNREGISTERED_SAMPLE = frozenset(
    {"GO", " go", "go ", "yes", "positive", "unknown", "", "maybe"}
)

#: 프로덕션이 **적용해서는 안 되는** 정규화. 이름은 실패 메시지에서 무엇이 새는지 읽히도록 둔다.
_ROUND16_FORBIDDEN_NORMALISATIONS = (
    ("upper", str.upper),
    ("title", str.title),
    ("leading_space", lambda value: f" {value}"),
    ("trailing_space", lambda value: f"{value} "),
    ("inner_space", lambda value: f"{value[:1]} {value[1:]}"),
)


def test_the_unregistered_assumption_71_sample_cannot_shrink_silently():
    """[round16 A1] 미등재 표본에서 행을 하나 지우면 이 단정이 깨진다.

    파라미터화 대조군은 목록에서 행을 만들기 때문에 **축소를 원리적으로 감지하지 못한다** —
    round16 A1이 `test_autopatch_verify.py`에서 삭제한 항진명제 20건이 같은 구조였다.
    """
    assert len(_UNREGISTERED_ASSUMPTION_71_VALUES) == len(set(_UNREGISTERED_ASSUMPTION_71_VALUES))
    assert set(_UNREGISTERED_ASSUMPTION_71_VALUES) == _ROUND16_UNREGISTERED_SAMPLE
    # 표본은 등재 어휘와 **겹치지 않아야** 한다 — 겹치면 그 행은 공허하다.
    assert set(_UNREGISTERED_ASSUMPTION_71_VALUES).isdisjoint(ASSUMPTION_71_VALUES)
    assert len(_UNREGISTERED_ASSUMPTION_71_VALUES) >= 2 * len(ASSUMPTION_71_VALUES)


def _round16_near_miss_probes() -> tuple[tuple[str, str, str], ...]:
    """등재 어휘 × 금지 정규화의 **전수 곱** — 행 목록이 프로덕션 상수에서 나온다."""
    import itertools

    probes = []
    for value, (label, transform) in itertools.product(
        sorted(ASSUMPTION_71_VALUES), _ROUND16_FORBIDDEN_NORMALISATIONS
    ):
        probes.append((value, label, transform(value)))
    return tuple(probes)


_ROUND16_NEAR_MISS_PROBES = _round16_near_miss_probes()


def test_the_near_miss_probe_table_is_the_full_product_of_production_vocabulary():
    """[round16 A1] 이 표는 지워서 줄일 수 없다 — 행이 `ASSUMPTION_71_VALUES`에서 나온다.

    등재 어휘가 하나 늘면 행도 함께 늘고, 금지 정규화를 하나 더 정의하면 그 축도 곧바로
    전수에 들어온다. 만들어진 변형이 실수로 등재 어휘가 되어 공허해지지도 않는다.
    """
    assert len(_ROUND16_NEAR_MISS_PROBES) == len(ASSUMPTION_71_VALUES) * len(
        _ROUND16_FORBIDDEN_NORMALISATIONS
    )
    variants = [variant for _, _, variant in _ROUND16_NEAR_MISS_PROBES]
    assert len(set(variants)) == len(variants), variants
    assert set(variants).isdisjoint(ASSUMPTION_71_VALUES)


@pytest.mark.parametrize(
    "variant",
    [variant for _, _, variant in _ROUND16_NEAR_MISS_PROBES],
    ids=[f"{value}__{label}" for value, label, _ in _ROUND16_NEAR_MISS_PROBES],
)
def test_validate_assumption_71_refuses_every_near_miss_of_a_registered_value(variant: str):
    """[round16 A1] `validate_assumption_71`이 어떤 정규화도 하지 않음을 전수로 고정한다.

    본문에 `value = value.strip()`이나 `value.lower()`를 끼우면 해당 변형 행이 실패한다 —
    도달성 표기가 조용히 뒤집히면 사람은 되돌릴 수 없는 생성을 잘못된 전제로 승인한다.
    """
    with pytest.raises(ValueError, match="assumption_71 must be one of"):
        validate_assumption_71(variant)


# --- round16 형제 필드·형제 사이트 (SiblingFields) ---
#
# S16-07 — `assignment_requested=bool(selected)`가 **무게이트**였다.
#
# round11 M7 N03은 "실측 판정(`assumption_71`)을 요청 신호로 겸용하지 않는다"를 위해
# 배정 분기 개방을 `assignment_requested`로 분리했다. 그런데 툴 경계에서 그 분리를 지키는
# 대조군이 없어 `assignment_requested=True` 상수로 바꿔도 전부 통과했다. 그러면
# **선택 없는 열람 호출**이 `fid_range_required` 거부로 돌아온다 — 조작자는 아직 아무것도
# 고르지 않았는데 "FID 범위를 내놓으라"는 말을 듣고, 1단계 대조 결과를 볼 수 없다.
#
# 대조군은 이 파일의 확립된 방식을 그대로 쓴다: 한 줄만 갈아끼운 `tools.py` **사본을
# 적재해 실제로 디스패치**한다(`_load_tools` · `TOOLS_SOURCE`).

#: 사본에서 갈아끼울 **배정 신호 한 줄**. 앵커가 사라지면 아래 비공허성 대조군이 즉시 실패한다.
ASSIGNMENT_SIGNAL_LINE = "            assignment_requested=bool(selected),"

# (행 이름, `selected` 인자, 배정 분기가 열리는가)
# 세 모양이 서로 다른 뮤테이션을 잡는다:
#   `None`  — `assignment_requested=True` 상수화를 잡는다(열람 호출이 거부로 돌아온다).
#   `[]`    — `assignment_requested=selected is not None`으로 바꾸는 것을 잡는다.
#   `[cid]` — 신호를 `False`로 죽이는 것을 잡는다(선택했는데 배정 분기가 안 열린다).
_R16_ASSIGNMENT_SIGNAL_ROWS = (
    ("no_selected", None, False),
    ("empty_selected", [], False),
    ("one_selected", "candidate", True),
)


def test_the_assignment_signal_table_matches_the_production_expression():
    """[round16 S16-07] 표의 세 모양이 프로덕션 식 `bool(selected)`를 **전부 가른다**.

    앵커가 유일해야 아래 사본 심기가 정확히 그 한 줄만 바꾼다. 그리고 표의 기대값은
    프로덕션 식을 그대로 적용한 결과와 같아야 한다 — 행을 지우면 `bool()`이 가르는 세
    모양 중 하나가 표에서 사라져 이 단정이 실패한다.
    """
    assert TOOLS_SOURCE.count(ASSIGNMENT_SIGNAL_LINE) == 1, "배정 신호 앵커가 유일하지 않다"

    shapes = {name: selected for name, selected, _ in _R16_ASSIGNMENT_SIGNAL_ROWS}
    assert shapes == {"no_selected": None, "empty_selected": [], "one_selected": "candidate"}
    for name, selected, opens in _R16_ASSIGNMENT_SIGNAL_ROWS:
        probe = ["c"] if selected == "candidate" else selected
        assert bool(probe) is opens, name


def _r16_assignment_payload(registry, *, selected):
    """`selected` 모양만 바꿔 툴을 부른다 — `fid_range`는 **주지 않는다**."""
    report = _report()
    first = _payload(_dispatch(registry, report=report))
    if selected == "candidate":
        selected = [_candidate_id(first)]
    arguments = {"report": report}
    if selected is not None:
        arguments["selected"] = selected
    return _payload(_dispatch(registry, **arguments))


@pytest.mark.parametrize(
    "name,selected,opens_assignment",
    _R16_ASSIGNMENT_SIGNAL_ROWS,
    ids=[row[0] for row in _R16_ASSIGNMENT_SIGNAL_ROWS],
)
def test_only_a_nonempty_selection_opens_the_fid_assignment_branch(
    name, selected, opens_assignment
):
    """[round16 S16-07] 선택이 있어야만 배정 분기가 열린다 — 열람 호출은 거부되지 않는다.

    `tools.py`의 `assignment_requested=bool(selected)`를 `True` 상수로 바꾸면
    'no_selected'·'empty_selected' 두 행이 실패한다(둘 다 `fid_range_required`로 돌아온다).
    `False` 상수로 바꾸면 'one_selected' 행이 실패한다.
    """
    payload = _r16_assignment_payload(_registry(), selected=selected)
    plan = payload["plan"]

    if opens_assignment:
        assert plan["ok"] is False
        assert plan["rejection"]["code"] == "fid_range_required"
    else:
        # 열람 호출 — 계획은 서고, FID 범위를 내놓으라는 요구는 나오지 않는다.
        assert plan["ok"] is True
        assert plan["status"] == "planned"
        assert "rejection" not in plan
        assert plan["candidates"], "열람 호출은 후보 목록을 그대로 보여준다"
        # 배정 분기를 열지 않았으므로 FID 안전 payload 자체가 없다.
        assert "fid_safety" not in plan


@pytest.mark.parametrize(
    "name,selected",
    [(name, selected) for name, selected, opens in _R16_ASSIGNMENT_SIGNAL_ROWS if not opens],
    ids=[name for name, _, opens in _R16_ASSIGNMENT_SIGNAL_ROWS if not opens],
)
def test_the_read_only_rows_actually_flip_when_the_signal_is_constant_true(name, selected):
    """[round16 S16-07] 비공허성 — 프로덕션 **사본**에 상수를 심으면 그 행이 실제로 뒤집힌다.

    이 대조군이 없으면 위 단정은 "지금도 그렇다"만 말하고, `bool(selected)`가 실제로
    그 결과를 만든 것인지는 말하지 못한다. 여기서는 `assignment_requested=True`를 심은
    사본을 적재해 **실제로 디스패치**하고, 두 열람 행이 `fid_range_required`로 돌아오는
    것을 확인한다 — 그것이 이 한 줄이 지키고 있는 것이다.
    """
    planted = TOOLS_SOURCE.replace(
        ASSIGNMENT_SIGNAL_LINE, "            assignment_requested=True,", 1
    )
    assert planted != TOOLS_SOURCE

    rig = RigPort()
    registry = _load_tools(planted)["build_toolset"](
        execution_port=_NeverCalledExecutionPort(), state_port=rig, property_port=rig
    )
    payload = _r16_assignment_payload(registry, selected=selected)

    assert payload["plan"]["ok"] is False
    assert payload["plan"]["rejection"]["code"] == "fid_range_required"


def test_a_selection_without_a_fid_range_stays_one_rejection_not_scattered_rows():
    """[round16 S16-07 형제 축] 분리의 **다른 쪽 절반** — 선택이 있으면 거부가 하나로 올라온다.

    `assignment_requested`를 떼면(`build_patch_plan`의 기본 추론에 맡기면) `fid_range`가
    `None`이라 배정 분기가 열리지 않고, 누락이 항목별 `fid_not_assigned`로 흩어져
    조작자가 원인을 한눈에 보지 못한다(REQ-AUTOPATCH-007).
    """
    payload = _r16_assignment_payload(_registry(), selected="candidate")
    plan = payload["plan"]

    assert plan["rejection"]["code"] == "fid_range_required"
    assert plan["rejection"]["reason"]
    assert [row["fid"] for row in plan["target_table"]["rows"]] == [None]
