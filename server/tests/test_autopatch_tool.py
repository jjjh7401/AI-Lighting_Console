"""M7 — `apply_vectorworks_patch` 툴 배선 (AC-AUTOPATCH-023).

`server/tests/test_vwx_tool.py`·`test_prechk_tool.py`의 확립된 패턴을 따른다 —
등록은 **디스패치로** 확인하고(dict 조회 금지), 스키마에 리그 식별자가 없음을 검증한다.

**이 툴이 다른 점**: 콘솔에 쓰지 않는다. 그래서 실행 포트는 **호출되면 즉시 실패하는 대역**을
꽂아 둔다 — 배선 계층에서도 "서버가 패치를 실행하지 않는다"가 지켜지는지가 여기서 걸린다.
"""

from __future__ import annotations

import base64
import json
import re
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


class _UploadedExport:
    def __init__(self, content_base64: str | None = None, report: dict | None = None):
        self.content_base64 = content_base64
        self.report = report


def _registry(*, rig: RigPort | None = None, upload: _UploadedExport | None = None):
    rig = rig or RigPort()
    return build_toolset(
        execution_port=_NeverCalledExecutionPort(),
        state_port=rig,
        property_port=rig,
        vectorworks_upload=upload,
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


class TestUploadedVectorworksAutopatch:
    def test_analyse_decodes_and_caches_the_session_export(self):
        content_base64 = base64.b64encode(
            b"Fixture Type,Universe,DMX Address,Unit Number,Fixture Name\n"
            b"Robin LEDBeam 350,1,1,1,VWX Beam 01\n"
        ).decode("ascii")
        upload = _UploadedExport(content_base64)
        execution = _registry(upload=upload).dispatch(
            ToolCall(id="uploaded-0", name="vectorworks_autopatch", arguments={"action": "analyse"})
        )

        payload = _payload(execution)
        assert execution.result.is_error is False
        assert payload["designed_rig"]["fixture_count"] == 1
        assert upload.report == payload

    def test_analyse_decodes_and_caches_the_session_mvr_export(self):
        source = PROJECT_ROOT / "server" / "tests" / "fixtures" / "vwx" / "demoshow_grandma3.mvr"
        upload = _UploadedExport(
            content_base64=base64.b64encode(source.read_bytes()).decode("ascii")
        )
        execution = _registry(upload=upload).dispatch(
            ToolCall(
                id="uploaded-mvr",
                name="vectorworks_autopatch",
                arguments={"action": "analyse"},
            )
        )

        payload = _payload(execution)
        assert execution.result.is_error is False
        assert payload["designed_rig"]["fixture_count"] == 176
        assert payload["read_failures"] == []
        assert upload.report == payload

    def test_prepare_uses_the_cached_report_and_the_drawing_fixture_name(self):
        report = _report()
        report["designed_rig"]["fixtures"][0]["fixture_name"] = "VWX Beam 01"
        preview = _payload(_dispatch(_registry(), report=report))
        candidate = _candidate_id(preview)
        registry = _registry(upload=_UploadedExport(content_base64="c2FmZQ==", report=report))

        execution = registry.dispatch(
            ToolCall(
                id="uploaded-1",
                name="vectorworks_autopatch",
                arguments={
                    "action": "prepare",
                    "selected": [candidate],
                    "fid_range": {"start": 101, "end": 101},
                    "type_aliases": {LED: {"type": LED, "mode": "Mode 1"}},
                },
            )
        )

        payload = _payload(execution)
        assert execution.result.is_error is False
        assert execution.result.name == "vectorworks_autopatch"
        assert payload["handoff"]["entries"][0]["name"] == "VWX Beam 01"

    def test_prepare_refuses_without_a_session_report(self):
        execution = _registry().dispatch(
            ToolCall(id="uploaded-2", name="vectorworks_autopatch", arguments={"action": "prepare"})
        )
        assert execution.result.is_error is True
        assert "대조 결과" in execution.result.content


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


# --- round17 항진식 전단사·payload CD 표면 (ScopeAndTables) ---
#
# 이 절이 닫는 두 구멍:
#   [round17 #8] `_ROUND16_FORBIDDEN_NORMALISATIONS`의 "전수 곱" 게이트가 **항진식**이었다.
#     `len(probes) == len(ASSUMPTION_71_VALUES) * len(_ROUND16_FORBIDDEN_NORMALISATIONS)`에서
#     `probes`가 바로 그 두 목록의 `itertools.product`이므로 좌변과 우변이 같은 것을 두 번
#     세고 있었다. 정규화 축을 한 행 지우면 **양변이 함께 줄어** 아무것도 실패하지 않는다.
#     같은 60줄 블록 안 형제(`_ROUND16_UNREGISTERED_SAMPLE`)에는 동결집합+하한 2겹이 이미
#     있었다 — 한 커밋이 형제 둘에 서로 다른 등급을 준 전형이다.
#   [round17 S17-02] 계약 2b④의 **다섯째 사이트**. `typemap.py`가 콘솔 판독 이름을 사유
#     문장에 f-string 보간했고 그 문장은 `payload["types"]["hard_stops"][].reason` ·
#     `payload["types"]["type_table"]["rows"][].reason`으로 나갔다. 기존 CD 게이트는
#     `PatchHandoff`·`verification` 두 블록만 훑었으므로 **`types` 블록은 전부 게이트 밖**이었다.
#     여기서 payload의 **여섯 블록 전부**를 표로 열거하고, 문장 칸과 구조화 칸을 전수 분류한 뒤
#     문장 칸 전체에 CD 게이트를 건다.

#: 금지 정규화 축의 **동결 집합** — 축을 지우거나 더하면 아래 단정이 깨진다.
#: 형제 `_ROUND16_UNREGISTERED_SAMPLE`이 이미 쓰던 방식이고, 항진식이 아닌 이유는
#: 이 집합이 `_ROUND16_FORBIDDEN_NORMALISATIONS`에서 **파생되지 않기 때문**이다.
_R17_FORBIDDEN_NORMALISATION_LABELS = frozenset(
    {"upper", "title", "leading_space", "trailing_space", "inner_space"}
)


def test_the_forbidden_normalisation_axis_table_cannot_shrink_silently():
    """[round17 #8] 정규화 축을 하나 지우면 여기서 깨진다.

    round16의 `test_the_near_miss_probe_table_is_the_full_product_of_production_vocabulary`는
    `len(probes) == len(어휘) * len(정규화)`를 단정했는데 `probes`가 그 곱 자체라 **항진식**이었다.
    축 목록은 프로덕션에서 파생할 수 없는 **자유 목록**이므로 동결집합으로 고정하고,
    하한을 함께 둔다 — 그래야 "동결집합도 같이 줄이는" 편집이 하한에서 걸린다.

    [round17 #8] `_ROUND16_FORBIDDEN_NORMALISATIONS`에서 어느 행이든 지우면 실패한다.
    """
    labels = [label for label, _ in _ROUND16_FORBIDDEN_NORMALISATIONS]
    assert len(labels) == len(set(labels)) == len(_R17_FORBIDDEN_NORMALISATION_LABELS)
    assert set(labels) == _R17_FORBIDDEN_NORMALISATION_LABELS
    # 하한 — 대소문자 축 2 · 공백 축 3. 동결집합째 줄이는 편집을 여기서 막는다.
    assert len(_ROUND16_FORBIDDEN_NORMALISATIONS) >= 5


def test_every_forbidden_normalisation_actually_changes_every_registered_value():
    """[round17 #8] 축 하나를 항등 함수로 바꿔치면 여기서 깨진다 — 비공허성.

    변형이 원값과 같으면 그 행의 근사 오타 대조군은 "등재 값이 거부되는가"를 묻게 되어
    **의미가 뒤집힌다**. 등재 어휘와의 비교만으로는 그 상태를 잡지 못한다.
    """
    for label, transform in _ROUND16_FORBIDDEN_NORMALISATIONS:
        for value in sorted(ASSUMPTION_71_VALUES):
            assert transform(value) != value, (label, value)


# ---- S17-02 · payload 블록 전수와 CD 게이트 표면 -----------------------------------

#: `test_autopatch_execute.py`·`test_autopatch_lua.py`와 **같은 토큰**. 콘솔에서 `CD`는
#: `ChangeDestination`이고, 그 한 토큰이 사람이 따라 치는 문장에 섞이면 목적지가 바뀐다.
_R17_CD_TOKEN = re.compile(r"ChangeDestination|(?<![A-Za-z])CD(?![A-Za-z])")

#: payload로 나가는 **최상위 블록 전수**와 CD 게이트 등급.
#: `console_bound` — 사람이 콘솔에서 실행하는 텍스트를 품는다. 문장이든 칸이든 CD 금지.
#: `sentence_gated` — 진단·표 블록. **문장 칸**에만 CD 금지, 구조화 관측 칸은 면제(round15 D).
_R17_PAYLOAD_BLOCKS = (
    ("plan", "sentence_gated"),
    ("console_read", "sentence_gated"),
    ("assumption_71_reachability", "sentence_gated"),
    ("types", "sentence_gated"),
    ("handoff", "console_bound"),
    ("verification", "sentence_gated"),
)

#: 사람이 읽는 **문장**을 담는 잎 키 전수. 여기에 콘솔 판독 원문이 보간되면 §0 2b④ 위반이다.
_R17_SENTENCE_LEAF_KEYS = frozenset(
    {
        "reason",
        "detail",
        "note",
        "scope",
        "as_of",
        "label",
        "status_label",
        "warnings",
        "procedure",
        "guidance",
        "next_step",
        "execution_performed_by",
        "lua_source_unresolved_reason",
        "source",
        "columns",
    }
)

#: 구조화 관측·식별 칸 전수 — 콘솔 원문이 **여기로** 간다(§0 2c①). CD 게이트 면제.
_R17_STRUCTURED_LEAF_KEYS = frozenset(
    {
        "active_safety",
        "address_basis",
        "alias_key",
        "assumption_71",
        "assumption_72",
        "candidate_id",
        "code",
        "completeness",
        "confirmation_source",
        "console_channel_count",
        "console_mode",
        "console_type",
        "designed_footprint",
        "designed_mode",
        "designed_type",
        "expected_mode",
        "expected_type",
        "field",
        "footprint",
        "footprint_unverified",
        "id",
        "injected",
        "instrument_type",
        "kind",
        "lua_source",
        "mode",
        # [round21 R20-B] 목록 완전성 칸 — `column_labels`의 키로 잎에 나타난다
        # (`footprint_unverified`·`console_channel_count`와 같은 기제). 콘솔 판독 원문을
        # 담지 않는 구조화 칸이므로 형제 열 이름들과 같은 분류다.
        "mode_options_completeness",
        "mode_candidates",
        "name",
        "outcome",
        "path",
        "presented_console_type",
        "property",
        "searched_mode_key",
        "searched_type_key",
        "selected",
        "source_path",
        "status",
        "type",
        "type_candidates",
        "type_candidates_completeness",
        "unit_number",
    }
)

_R17_CD_LIBRARY_TYPE = "CD 5"


class _R17CdLibraryPort(RigPort):
    """콘솔 FixtureType 라이브러리에 `'CD 5'`가 있고 도면이 요구한 모드는 **없는** 콘솔.

    이 구성이 `typemap._resolve_one`의 `DMX_MODE_NOT_IN_LIBRARY` 갈래에 도달한다 —
    round17 S17-02가 실증한 바로 그 자리다.
    """

    def query_state(self, path: str) -> dict:
        state = super().query_state(path)
        if path == FIXTURE_TYPE_LIBRARY_ROOT:
            return {**state, "children": [{"i": 3, "name": _R17_CD_LIBRARY_TYPE}]}
        if path == f"{FIXTURE_TYPE_LIBRARY_ROOT}/3/DMXModes":
            return {**state, "children": [{"i": 1, "name": "Mode 9"}]}
        return state

    def query_property(self, path: str, property_name: str) -> dict:
        result = super().query_property(path, property_name)
        if path.startswith(FIXTURE_TYPE_LIBRARY_ROOT) and property_name == "Name":
            return {**result, "value": "Mode 9"}
        return result


def _r17_cd_library_payload() -> dict:
    """콘솔 라이브러리 타입 이름이 `'CD 5'`인 상태에서 만든 **전체 payload**."""
    report = _report()
    report["designed_rig"]["fixtures"][0]["instrument_type"] = _R17_CD_LIBRARY_TYPE
    report["diffs"]["missing_in_console"][0]["instrument_type"] = _R17_CD_LIBRARY_TYPE
    payload, _ = _full_call(_registry(rig=_R17CdLibraryPort()), rig_report=report)
    return payload


def _r17_cd_alias_payload() -> dict:
    """저장된 **별칭 값**이 `'CD 5'`인데 콘솔 라이브러리에 그 타입이 없는 payload.

    `typemap._resolve_one`의 `TYPE_LIBRARY_ABSENT` 갈래에 도달한다 — 위 시나리오가
    닿지 못하는 형제 갈래이고, 그 사유가 `alias_type`을 문장에 보간하던 자리다.
    """
    payload, _ = _full_call(
        _registry(), type_aliases={LED: {"type": _R17_CD_LIBRARY_TYPE, "mode": "Mode 1"}}
    )
    return payload


def _r17_delivered_payload() -> dict:
    """정상 전달 payload — `handoff.lua_source`·`procedure`·`verification.guidance`가 있는 쪽."""
    payload, _ = _full_call(
        _registry(),
        dry_run=False,
        type_aliases={LED: {"type": LED, "mode": "Mode 1"}},
    )
    return payload


def _r17_string_leaves(node, path: str = ""):
    """payload의 문자열 잎을 `(경로, 잎 키, 값)`으로 전수 산출한다."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _r17_string_leaves(value, f"{path}.{key}" if path else str(key))
    elif isinstance(node, (list, tuple)):
        for value in node:
            yield from _r17_string_leaves(value, f"{path}[]")
    elif isinstance(node, str):
        yield path, path.rsplit(".", 1)[-1].replace("[]", ""), node


def _r17_leaf_keys(*payloads) -> frozenset[str]:
    return frozenset(key for payload in payloads for _, key, _ in _r17_string_leaves(payload))


def test_the_payload_block_table_is_a_bijection_onto_the_produced_payload():
    """[round17 S17-02] payload 최상위 블록 표가 실제 payload와 1:1이다.

    표에서 블록 행을 지우면 실패하고, 프로덕션이 블록을 하나 더 실으면 행 없이는 통과하지
    못한다 — round16까지 `types` 블록은 어떤 CD 게이트에도 등재되지 않은 채 payload로 나갔다.
    두 시나리오 **모두**에서 같은 여섯 블록이 나오는 것까지 본다.
    """
    declared = tuple(sorted(block for block, _ in _R17_PAYLOAD_BLOCKS))
    assert declared == tuple(sorted(_r17_delivered_payload()))
    assert declared == tuple(sorted(_r17_cd_library_payload()))
    assert declared == tuple(sorted(_r17_cd_alias_payload()))
    classes = {gate for _, gate in _R17_PAYLOAD_BLOCKS}
    assert classes == {"sentence_gated", "console_bound"}


def test_the_payload_leaf_key_partition_is_total_and_disjoint():
    """[round17 S17-02] 문자열 잎 키가 **전부** 문장/구조화 중 하나로 분류돼 있다.

    프로덕션이 문자열 키를 하나 더 실으면 여기서 먼저 실패한다 — 분류되지 않은 키는
    CD 게이트의 사각이 된다. 두 표 어느 쪽에서 행을 지워도 실패한다.
    """
    observed = _r17_leaf_keys(
        _r17_cd_library_payload(), _r17_cd_alias_payload(), _r17_delivered_payload()
    )
    assert _R17_SENTENCE_LEAF_KEYS.isdisjoint(_R17_STRUCTURED_LEAF_KEYS)
    unclassified = observed - _R17_SENTENCE_LEAF_KEYS - _R17_STRUCTURED_LEAF_KEYS
    assert unclassified == frozenset(), sorted(unclassified)
    stale = (_R17_SENTENCE_LEAF_KEYS | _R17_STRUCTURED_LEAF_KEYS) - observed
    assert stale == frozenset(), sorted(stale)


def test_the_cd_library_scenario_actually_reaches_the_typemap_hard_stop():
    """재현 구성이 겨냥한 갈래에 실제로 도달한다 — 아니면 아래 게이트가 공허하다."""
    payload = _r17_cd_library_payload()
    (hard_stop,) = payload["types"]["hard_stops"]
    assert hard_stop["code"] == "dmx_mode_not_in_library"
    (row,) = payload["types"]["type_table"]["rows"]
    # 콘솔 판독 원문은 **구조화 칸**으로 나간다(§0 2c①) — 값이 버려지지 않았다.
    assert row["presented_console_type"] == _R17_CD_LIBRARY_TYPE
    assert row["type_candidates"] == [_R17_CD_LIBRARY_TYPE]


#: CD 게이트를 거는 **시나리오 전수**. 두 시나리오가 `typemap._resolve_one`의 **서로 다른**
#: 하드 스톱 갈래에 도달한다 — 한 갈래만 재현하면 형제 갈래의 보간이 무게이트로 남는다.
#: round17 실측: `_r17_cd_library_payload` 하나만으로는 `TYPE_LIBRARY_ABSENT` 사유의
#: `'{alias_type or designed_type}'` 재보간이 **SURVIVED**였다.
_R17_CD_SCENARIOS = (
    ("dmx_mode_not_in_library", lambda: _r17_cd_library_payload()),
    ("fixture_type_not_in_library", lambda: _r17_cd_alias_payload()),
)


def test_the_cd_scenario_table_covers_every_typemap_hard_stop_branch():
    """[round17 S17-02] 시나리오 표가 `typemap`의 하드 스톱 코드 **전수**와 1:1이다.

    [round17 S17-02] 시나리오 행을 지우면 실패한다 — 그 갈래의 사유가 무게이트로 돌아간다.
    [round17 S17-02] `typemap.py`에 하드 스톱 코드를 더하면 시나리오 없이는 통과하지 못한다.
    """
    from server.vwx.verdicts import DMX_MODE_NOT_IN_LIBRARY, FIXTURE_TYPE_NOT_IN_LIBRARY

    declared = tuple(sorted(code for code, _ in _R17_CD_SCENARIOS))
    assert declared == tuple(sorted({DMX_MODE_NOT_IN_LIBRARY, FIXTURE_TYPE_NOT_IN_LIBRARY}))
    for code, build in _R17_CD_SCENARIOS:
        payload = build()
        assert [stop["code"] for stop in payload["types"]["hard_stops"]] == [code], code


@pytest.mark.parametrize(
    "scenario,build", _R17_CD_SCENARIOS, ids=[code for code, _ in _R17_CD_SCENARIOS]
)
def test_no_sentence_anywhere_in_the_payload_echoes_the_console_read_name(scenario, build):
    """[round17 S17-02] payload **전 블록**의 문장 칸에 콘솔 판독 원문이 없다.

    [round17 S17-02] `typemap.py`의 `DMX_MODE_NOT_IN_LIBRARY` 사유를
      `f"콘솔 FixtureType '{presented_type.name}'에 …"`으로 되돌리면
      `types.hard_stops[].reason`과 `types.type_table.rows[].reason` 두 경로가 잡힌다.
    [round17 S17-02] `TYPE_LIBRARY_ABSENT` 사유를
      `f"콘솔 라이브러리에 '{alias_type or request.designed_type}'에 …"`으로 되돌리면
      `fixture_type_not_in_library` 행이 잡힌다 — 별칭 값은 사람이 콘솔에서 확인해 저장한
      **콘솔 쪽 이름**이라 도면 값과 같은 등급이 아니다.
    round16까지 이 두 경로는 **어떤 CD 게이트에도 닿지 않았다**.
    """
    payload = build()
    offenders = [
        (path, value)
        for path, key, value in _r17_string_leaves(payload)
        if key in _R17_SENTENCE_LEAF_KEYS and _R17_CD_TOKEN.search(value)
    ]
    assert offenders == [], (scenario, offenders)


def test_the_payload_cd_gate_is_not_vacuous():
    """대조의 대조 — 같은 payload의 **구조화 칸**에는 그 원문이 실제로 들어 있다.

    이것이 없으면 위 게이트는 "CD가 애초에 아무 데도 없었다"로 공허해질 수 있다.
    """
    payload = _r17_cd_library_payload()
    carriers = sorted(
        {
            path
            for path, key, value in _r17_string_leaves(payload)
            if key in _R17_STRUCTURED_LEAF_KEYS and _R17_CD_TOKEN.search(value)
        }
    )
    assert "types.type_table.rows[].presented_console_type" in carriers
    assert "types.library.types[].name" in carriers


def test_the_delivered_payload_carries_no_cd_token_at_all():
    """[round17 S17-02 형제 축] `console_bound` 블록은 문장·칸을 가리지 않고 CD가 0건이다.

    `handoff`는 `lua_source`·`procedure`가 들어 있는 블록이라 구조화 칸 면제가 없다 —
    그 텍스트는 사람이 콘솔에 그대로 친다.
    """
    payload = _r17_delivered_payload()
    console_bound = [block for block, gate in _R17_PAYLOAD_BLOCKS if gate == "console_bound"]
    assert console_bound == ["handoff"]
    for block in console_bound:
        hits = [
            (path, value)
            for path, _, value in _r17_string_leaves(payload[block])
            if _R17_CD_TOKEN.search(value)
        ]
        assert hits == [], hits


# --- round18 전달물 도달성 감지기 (VacuityAndData) ---
#
# [round18 R18-G · R18-H · R18-E · R18-J] 앞선 섹션들의 판정이 **배선 끝까지** 살아 있는지를
# 툴 dispatch로 확인한다. 단위 대조군만 있으면 "그 판정이 전달물에 영향을 주는가"가 열려
# 있고, 여덟 라운드째 지적된 "규율이 모듈 경계에서 멈춘다"가 정확히 그 형태다.

_R18_TYPE_A = "MegaPointe"
_R18_TYPE_B = "LEDWash 600"
_R18_MODE = "Mode 1"


class _R18TwoTypeRigPort(RigPort):
    """FixtureType 라이브러리에 **두 이름**을 담은 대역 — 어느 쪽이 확정되는지가 관측점이다."""

    _LIBRARY = ((7, _R18_TYPE_A), (8, _R18_TYPE_B))

    def query_state(self, path: str) -> dict:
        self.state_calls.append(path)
        if path == FIXTURE_TYPE_LIBRARY_ROOT:
            return {
                "ok": True,
                "path": path,
                "node": {"childCount": len(self._LIBRARY)},
                "children": [{"i": index, "name": name} for index, name in self._LIBRARY],
                "truncated": False,
            }
        for index, _name in self._LIBRARY:
            if path == f"{FIXTURE_TYPE_LIBRARY_ROOT}/{index}/DMXModes":
                return {
                    "ok": True,
                    "path": path,
                    "node": {"childCount": 1},
                    "children": [{"i": 1, "name": _R18_MODE}],
                    "truncated": False,
                }
        return super().query_state(path)


def _r18_report(instrument_type: str, *, universe: int = 1, address: int = 1) -> dict:
    """`_report()`와 같은 최소 형태 — 타입 이름만 파라미터로 뺀다."""
    fixture = {
        "unit_number": "1",
        "instrument_type": instrument_type,
        "gdtf_fixture": None,
        "mode": _R18_MODE,
        "footprint": 16,
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
                    "instrument_type": instrument_type,
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


def _r18_call(registry, report, *, names=None, aliases=None, dry_run=False) -> dict:
    first = _payload(_dispatch(registry, report=report))
    candidate = _candidate_id(first)
    return _payload(
        _dispatch(
            registry,
            report=report,
            selected=[candidate],
            fid_range={"start": 501, "end": 599},
            names={candidate: "LEDBeam 501"} if names is None else {candidate: names},
            type_aliases=aliases if aliases is not None else {},
            dry_run=dry_run,
        )
    )


class TestRound18DeliverableReachability:
    """[round18] 판정이 전달물(`handoff.lua_source`)까지 도달하는지 — 툴 dispatch 전 구간."""

    def test_the_confirmed_type_name_that_reaches_the_lua_is_the_one_the_report_carried(self):
        """[round18 R18-G 도달성] 1단계 리포트의 `instrument_type`이 그대로
        `Patch().FixtureTypes[...]`가 된다 — `columns.py`의 우선순위 규약이 이 값을 정하므로
        `fields.setdefault`를 대입으로 바꾸면 여기 박히는 이름이 바뀐다.

        라이브러리에 **두 이름이 모두** 있으므로 확정 결과는 리포트 값의 함수다.
        """
        rig = _R18TwoTypeRigPort()
        for designed in (_R18_TYPE_A, _R18_TYPE_B):
            other = _R18_TYPE_B if designed == _R18_TYPE_A else _R18_TYPE_A
            payload = _r18_call(
                _registry(rig=rig),
                _r18_report(designed),
                aliases={designed: {"type": designed, "mode": _R18_MODE}},
            )
            rendered = payload["handoff"]["lua_source"] or ""
            assert f'Patch().FixtureTypes["{designed}"]' in rendered, designed
            assert other not in rendered, designed
            assert payload["handoff"]["entries"], designed

    def test_a_blank_fixture_name_never_reaches_the_lua_through_the_wired_tool(self):
        """[round18 R18-H 도달성] 배선 끝까지 — 공백만 이름은 `AddFixtures({`를 만들지 않고
        `fixture_name_missing`으로 제외된다. `apply.py`의 `.strip()`을 떼면 실패한다.
        """
        rig = _R18TwoTypeRigPort()
        for blank in ("   ", "\t\n", "\u00a0"):
            payload = _r18_call(
                _registry(rig=rig),
                _r18_report(_R18_TYPE_A),
                names=blank,
                aliases={_R18_TYPE_A: {"type": _R18_TYPE_A, "mode": _R18_MODE}},
            )
            handoff = payload["handoff"]
            assert handoff["lua_source"] is None, repr(blank)
            assert [entry["code"] for entry in handoff["exclusions"]] == ["fixture_name_missing"], (
                repr(blank)
            )
            # `delivered`는 "인계가 나갔는가"라 항목 0건에서도 True다
            # (`test_an_empty_delivery_reports_no_lua_source` 관례) — 관측점은 항목 수다.
            assert handoff["entries"] == [], repr(blank)

    def test_a_vacuous_designed_type_hard_stops_and_delivers_nothing(self):
        """[round18 R18-E 도달성] 공허명 후보는 배선 끝에서 **하드 스톱으로 보고되고**
        아무것도 전달되지 않는다.

        `typemap.py`의 하드스톱을 `None`으로 되돌리면 `types.hard_stops`가 비어 실패한다 —
        전달물은 어느 쪽이든 비므로(`status != resolved`는 fail-closed) 깨진 것은
        **조작자에게 가는 신호**다. 그 신호가 여기서 관측된다.
        """
        rig = _R18TwoTypeRigPort()
        payload = _r18_call(_registry(rig=rig), _r18_report("---"))
        hard_stops = payload["types"]["hard_stops"]

        assert [stop["code"] for stop in hard_stops] == ["fixture_type_name_unusable"]
        assert payload["types"]["type_table"]["rows"][0]["status"] == (
            "designed_type_name_unusable"
        )
        assert payload["types"]["type_table"]["rows"][0]["confirmation_required"] is False
        # fail-closed 확인 — 잘못된 Lua는 애초에 나가지 않는다.
        assert payload["handoff"]["lua_source"] is None
        assert payload["handoff"]["entries"] == []

    def test_the_vacuous_type_disclosure_rides_the_wired_payload(self):
        """[round18 R18-J 도달성] 1단계 대조가 삼켰을 수 있다는 고지가 **툴 payload**에
        실린다 — `plan.skipped_checks`에 등재 어휘로 나간다.
        """
        report = _r18_report(_R18_TYPE_A)
        report["designed_rig"]["fixture_count"] = 2
        report["designed_rig"]["fixtures"].append(
            {
                "unit_number": "2",
                "instrument_type": "---",
                "gdtf_fixture": None,
                "mode": _R18_MODE,
                "footprint": 16,
                "system": None,
                "universe": 1,
                "address": 40,
                "classification": "patched",
                "address_basis": "universe_address_direct",
            }
        )
        payload = _payload(_dispatch(_registry(rig=_R18TwoTypeRigPort()), report=report))
        kinds = {check["kind"] for check in payload["plan"]["skipped_checks"]}
        assert "designed_type_name_vacuous" in kinds
        (check,) = [
            check
            for check in payload["plan"]["skipped_checks"]
            if check["kind"] == "designed_type_name_vacuous"
        ]
        assert tuple(check["affected_designed_addresses"]) == ("1.40",)
        assert "---" not in check["reason"]

    def test_the_disclosure_control_a_clean_report_carries_no_vacuity_notice(self):
        """비공허성 — 정상 리포트에서는 고지가 나오지 않는다(항상 켜져 있으면 무시된다)."""
        payload = _payload(
            _dispatch(_registry(rig=_R18TwoTypeRigPort()), report=_r18_report(_R18_TYPE_A))
        )
        kinds = {check["kind"] for check in payload["plan"]["skipped_checks"]}
        assert "designed_type_name_vacuous" not in kinds


# --------------------------------------------------------------------------
# [round23 R21-A] 2회차 재호출이 "이미 했음"을 말하는가 — 실물 M8 세션 재현
#
# 2026-08-08 세션: ZZAP1~3을 FID 501~503으로 만든 뒤 **같은 인자로 재호출**하면
#   targets 0 · exclusions 3 · fid_already_in_use ×3
#   최상위 키에 handoff·types·verification 자체가 없다
# 가 나왔다. FID 배정이 `screen_idempotent`보다 위에 있어 배제해버리므로 멱등 판정에
# 도달하지 못한다 — round12 R05가 닫은 뭉갬과 **같은 것**이고, 그때 고친 순서보다
# 한 층 위에서 다시 났다.
#
# **기존 멱등 대조군을 대체하지 않는다.** round11 M7 N01
# (`test_an_unrelated_second_candidate_does_not_disable_the_overlap_guard`)과 round12 R05
# (`test_a_re_call_reads_as_already_patched_even_with_an_intruder_in_the_span`)는 FID가
# 충돌하지 않는 리그를 쓰므로 이 절과 서로 다른 축을 지킨다. 둘 다 살아 있어야 한다.
# --------------------------------------------------------------------------

_R21_FID = 501  # `_deliver`·`_r18_call`이 쓰는 fid_range의 첫 값 — 1회차가 배정한 그 FID다.
_ADDRESS_CONFLICT = "address_conflicts_with_existing_fixture"
_FID_ALREADY_IN_USE = "fid_already_in_use"


class _R21FidRigPort(RigPort):
    """슬롯별 FID를 지정하는 대역 — 1회차가 만든 픽스처가 **그 FID를 들고 있는** 상태.

    기본 `RigPort`는 FID를 `19 + slot`으로 내므로 501~599 대역과 절대 겹치지 않는다.
    그래서 기존 멱등 대조군은 FID 충돌을 **한 번도 겪지 않은 채** 통과해 왔고, 실물
    세션의 결함이 스위트에 보이지 않았다. 이 대역이 그 사각을 연다.
    """

    def __init__(self, fixtures: dict[int, dict[str, str]], *, fids: dict[int, int]):
        super().__init__(fixtures)
        self.fids = fids
        self.patch_probes: list[str] = []

    def query_property(self, path: str, property_name: str) -> dict:
        if not path.startswith(FIXTURE_TYPE_LIBRARY_ROOT):
            slot = int(path.rsplit("/", 1)[1])
            if property_name == "FID":
                return {
                    "ok": True,
                    "path": path,
                    "property": property_name,
                    "value": self.fids.get(slot, 19 + slot),
                }
            if property_name == "Patch":
                self.patch_probes.append(path)
        return super().query_property(path, property_name)


class _R21TwoTypeFidRigPort(_R21FidRigPort, _R18TwoTypeRigPort):
    """위 대역 + 라이브러리에 타입 **둘** — 부분 일치(좌표는 같고 타입이 다름)를 만든다."""


def _r21_ours(slot_fid: int = _R21_FID) -> _R21FidRigPort:
    """1회차가 우리 도면 자리(1.1)에 만들어 둔 픽스처가 그 FID를 든 리그."""
    return _R21FidRigPort(fixtures={1: _fixture("1.001", "ZZAP1")}, fids={1: slot_fid})


def _r21_partial_match() -> _R21TwoTypeFidRigPort:
    """좌표는 우리 자리, **타입은 다른** 픽스처가 그 FID를 든 리그."""
    return _R21TwoTypeFidRigPort(
        fixtures={
            1: {
                "Patch": "1.001",
                "FixtureType": _R18_TYPE_B,
                "Mode": f"1 {_R18_MODE}",
                "Name": "other",
            }
        },
        fids={1: _R21_FID},
    )


def _r21_partial_match_call(rig) -> dict:
    return _r18_call(
        _registry(rig=rig),
        _r18_report(_R18_TYPE_A),
        aliases={_R18_TYPE_A: {"type": _R18_TYPE_A, "mode": _R18_MODE}},
    )


def test_r21_a_second_pass_with_the_same_arguments_says_already_patched():
    """세션 실증 재현 — 우리가 만든 픽스처가 그 FID를 들고 있어도 "이미 했음"이 나온다.

    죽이는 뮤테이션:
      · `_fid_holder_is_this_target`을 `return False`로(= 재분류 전으로 되돌리기) →
        `fid_already_in_use`가 돌아오고 `handoff` 키가 사라져 실패한다.
      · `_assign_fids`의 승격 갈래를 지워도 같다.
      · `_slot_address`가 좌표 대신 `None`을 돌려주게 해도 승격이 죽어 실패한다.
    """
    payload = _deliver(_r21_ours(), [(1, 1)])

    assert [x["code"] for x in payload["plan"]["target_exclusions"]] == []
    assert [x["code"] for x in payload["handoff"]["exclusions"]] == [ALREADY_PATCHED_IDENTICAL]
    # 재실행이 사실을 말한다 — 배정된 FID는 콘솔에 실재하는 그 FID다.
    assert [row["fid"] for row in payload["plan"]["targets"]] == [_R21_FID]


def test_r21_the_second_pass_produces_the_verification_block():
    """세션에서 AC-026③ 검증을 가로막은 것은 **키 자체의 부재**였다.

    `handoff`·`types`·`verification`이 최상위에 없으면 조작자는 "만들어졌는가"를 물을
    수단이 없다. 승격이 죽으면 대상이 0건이 되어 툴이 그 세 키 앞에서 반환하므로,
    이 단정은 승격 규칙이 살아 있을 때만 성립한다.
    """
    payload = _deliver(_r21_ours(), [(1, 1)])

    assert {"types", "handoff", "verification"} <= set(payload)
    # 승인 항목 전체가 검증 대상이다 — 2회차라고 결과가 비지 않는다(round11 M6 N04).
    assert len(payload["verification"]["results"]) == 1
    assert payload["verification"]["observed_count"] == 1
    assert payload["verification"]["created_count"] == 0


def test_r21_a_foreign_fixture_holding_that_fid_is_still_a_real_conflict():
    """**둘을 가르는 것이 핵심이다.** 남의 픽스처가 그 FID를 쓰면 여전히 점유 보고다.

    같은 FID·같은 대역·같은 호출인데 점유자가 **다른 자리**(1.100)에 있다는 것만 다르다.
    승격 규칙을 "FID가 겹치면 통과"로 넓히면 이 행이 통과해버려 실패한다 — 그러면
    남이 쓰는 FID로 픽스처를 만드는 Lua가 나가고, 이 앱에는 실행 취소가 없다.
    """
    rig = _R21FidRigPort(fixtures={1: _fixture("1.100", "someone else")}, fids={1: _R21_FID})
    payload = _deliver(rig, [(1, 1)])

    exclusions = payload["plan"]["target_exclusions"]
    assert [x["code"] for x in exclusions] == [_FID_ALREADY_IN_USE]
    assert [x["proposed_fid"] for x in exclusions] == [_R21_FID]


def test_r21_a_partial_match_is_not_promoted_to_idempotent():
    """부분 일치 — 좌표는 같고 **타입이 다르다**. `already_patched_identical`이 아니다.

    승격은 FID 배제만 면제할 뿐 멱등을 단정하지 않는다. 정체 판정은 `screen_idempotent`
    한 곳에만 있고(기존 규율 재사용), 그것이 여기서 충돌로 답해야 한다. 승격 규칙에
    타입 비교를 복제해 넣고 "일치하면 멱등"이라 쓰면 두 규약이 갈라진다.
    """
    payload = _r21_partial_match_call(_r21_partial_match())
    codes = [x["code"] for x in payload["handoff"]["exclusions"]]

    assert codes == [_ADDRESS_CONFLICT]
    assert ALREADY_PATCHED_IDENTICAL not in codes


#: (라벨, 대역, 호출, 승격 뒤 주소 계층이 내는 배제 코드) — 승격이 **실제로 일어나는**
#: 갈래 전수다. 좌표가 우리 자리가 아니면 승격 자체가 없으므로 이 표에 없고, 우리
#: 자리이면 `screen_idempotent`가 정체 일치(멱등)나 불일치(충돌) 중 하나로 답한다.
_R21_PROMOTION_CASES = (
    (
        "identical",
        _r21_ours,
        lambda rig: _deliver(rig, [(1, 1)]),
        ALREADY_PATCHED_IDENTICAL,
    ),
    ("type_differs", _r21_partial_match, _r21_partial_match_call, _ADDRESS_CONFLICT),
)


def test_r21_the_promotion_case_table_covers_both_downstream_verdicts():
    """**표 행삭제 프로브** — 두 행이 서로 다른 하류 판정을 덮어야 한다.

    한 행을 지우면 남은 코드 집합이 둘을 채우지 못해 실패한다. 두 행을 같은 판정으로
    바꿔도 같다 — 그러면 아래 안전 조건이 갈래 하나에서만 확인된 것이 된다.
    """
    codes = [expected for _label, _rig, _call, expected in _R21_PROMOTION_CASES]

    assert set(codes) == {ALREADY_PATCHED_IDENTICAL, _ADDRESS_CONFLICT}
    assert len(codes) == len(set(codes))


@pytest.mark.parametrize("label, build_rig, call, expected_code", _R21_PROMOTION_CASES)
def test_r21_a_promoted_target_never_reaches_the_lua(label, build_rig, call, expected_code):
    """**승격의 안전 조건** — FID 배제를 면제받은 대상은 전달물에 실리지 않는다.

    승격이 안전한 이유는 그 대상의 도면 자리에 픽스처가 실재해 `screen_idempotent`의
    갈래가 **전부 배제**이기 때문이다. 그 성질이 깨지면 이미 쓰이는 FID로 `AddFixtures`가
    나간다 — 승격 규칙을 넓히는 어떤 수정도 여기서 먼저 걸린다.

    승격이 정말 일어났는지도 함께 본다: FID 계층이 배제했다면 대상이 0건이 되어
    `handoff` 키가 없고, 그때는 아래 첫 단정이 `KeyError`로 죽는다.
    """
    payload = call(build_rig())

    assert [x["code"] for x in payload["plan"]["target_exclusions"]] == [], label
    assert [x["code"] for x in payload["handoff"]["exclusions"]] == [expected_code], label
    assert payload["handoff"]["lua_source"] is None, label
    assert payload["handoff"]["entries"] == [], label
    assert payload["verification"]["created_count"] == 0, label
