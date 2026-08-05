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


class TestRealWorldNegativeSampleEndToEndThroughDispatch:
    """결함 1·2(P0) 회귀 — 실물 음성 사례가 dispatch 경계를 넘어 예외를 던지지 않고,
    "이상 없음"으로 위장하지도 않는다. server/tests/test_vwx_reader.py의 단위
    수준 회귀와 달리 이 클래스는 **툴 dispatch 전체 경로**(base64 디코드 →
    reader → columns → address → rig → diff → report → JSON 직렬화)를
    통과시킨다 — reader.py 수정만으로는 잡히지 않는 상위 계층 회귀를 방어한다.
    """

    _FIXTURE_PATH = (
        Path(__file__).parent / "fixtures" / "vwx" / "drop_dk_rigging_not_a_vectorworks_export.csv"
    )

    @staticmethod
    def _b64_bytes(data: bytes) -> str:
        return base64.b64encode(data).decode("ascii")

    def test_cr_only_real_sample_never_raises_through_dispatch(self):
        """결함 1 — CR 전용 실물 파일이 dispatch까지 예외 없이 도달한다."""
        data = self._FIXTURE_PATH.read_bytes()
        execution = _dispatch(_registry(), file_content_base64=self._b64_bytes(data))
        # 예외가 dispatch()를 뚫고 나오면 이 호출 자체가 pytest 에러가 된다.
        assert execution.result is not None

    def test_real_sample_is_not_reported_as_a_clean_zero_diff_match(self):
        """결함 2(잔존 교정) — "설계 0대 · 차이 0건"이 정상 결과로 위장하지 않는다.

        1차 수정에서는 ``read_failures``만 채워졌을 뿐, ``diffs``가 여전히
        빈 배열 3종으로 남아 있어 "찾아봤는데 없다"로 오독될 여지가 있었다.
        이 교정은 ``diffs.performed: False`` + ``summary_ko``가 "차이 없음"을
        절대 말하지 않고 거부 사유로 시작함을 검증한다.
        """
        data = self._FIXTURE_PATH.read_bytes()
        execution = _dispatch(_registry(), file_content_base64=self._b64_bytes(data))
        payload = json.loads(execution.result.content)

        assert payload["designed_rig"]["fixture_count"] == 0

        # diffs가 "찾아봤는데 없다"(빈 배열 3종)가 아니라 "애초에 수행하지
        # 않았다"로 구조화돼야 한다 — 빈 배열 키 자체가 없어야 한다.
        assert payload["diffs"]["performed"] is False
        assert "missing_in_console" not in payload["diffs"]
        assert "address_collision" not in payload["diffs"]
        assert "quantity_mismatch" not in payload["diffs"]

        # 핵심 assert — 판독 실패가 반드시 동반돼 "정상 일치"로 읽히지 않는다.
        # 120개의 개별 실패가 아니라 소수의 구조화된 거부다.
        assert len(payload["read_failures"]) >= 1
        assert len(payload["read_failures"]) < 10  # 수정 전엔 120개였다(비공허성).

        # 사용자가 실제로 읽는 단 하나의 한국어 문장 — "차이 없음"이 절대
        # 등장하지 않고, 거부 사유로 시작해야 한다.
        assert "차이 없음" not in payload["summary_ko"]
        assert payload["summary_ko"].startswith("패치 출처로 성립하지 않는다")
        assert "대조를 수행하지 않았다" in payload["summary_ko"]


class TestRealWorldPositiveSampleEndToEndThroughDispatch:
    """M0 실물 컬럼 계약 검증 — 실물 양성 샘플이 dispatch 전체 경로를 정상 통과한다.

    ``vectorworks_export_sample_with_data.csv``(25컬럼×10행, UTF-8 BOM·CRLF·
    쉼표)를 그대로 base64 인코딩해 툴 dispatch에 넣는다. 10 픽스처 · 주소
    교차검증 통과(경고 없음) · 구간 겹침 0 · fixture_name/gdtf_fixture가
    extra가 아니라 정규 필드로 해석됨을 종단으로 확인한다.
    """

    _FIXTURE_PATH = (
        Path(__file__).parent / "fixtures" / "vwx" / "vectorworks_export_sample_with_data.csv"
    )

    @staticmethod
    def _b64_bytes(data: bytes) -> str:
        return base64.b64encode(data).decode("ascii")

    def test_ten_fixtures_resolved_with_no_exception(self):
        data = self._FIXTURE_PATH.read_bytes()
        execution = _dispatch(_registry(), file_content_base64=self._b64_bytes(data))
        payload = json.loads(execution.result.content)
        assert payload["designed_rig"]["fixture_count"] == 10
        assert payload["diffs"]["performed"] is True

    def test_address_triple_cross_check_passes_with_no_warning(self):
        """비공허성 — 이 파일의 절반(주소 정합성)이 실제로 검증됐음을 확인한다.
        (양성 불일치 케이스는 test_vwx_address.py의 합성 픽스처가 별도로 증명한다.)"""
        data = self._FIXTURE_PATH.read_bytes()
        execution = _dispatch(_registry(), file_content_base64=self._b64_bytes(data))
        payload = json.loads(execution.result.content)
        warning_kinds = {f["kind"] for f in payload["read_failures"]}
        assert "address_triple_mismatch" not in warning_kinds

    def test_zero_design_overlaps_reported_not_omitted(self):
        """stride(38) == footprint(38) — 완벽 패킹, 겹침 0이 정답이다. 빈 목록이
        실제로 계산된 결과임을(생략이 아님을) 필드 존재로 확인한다."""
        data = self._FIXTURE_PATH.read_bytes()
        execution = _dispatch(_registry(), file_content_base64=self._b64_bytes(data))
        payload = json.loads(execution.result.content)
        assert payload["designed_rig"]["footprint_data_present"] is True
        assert payload["designed_rig"]["design_overlaps"] == []

    def test_fixture_name_and_gdtf_fixture_reach_the_dispatch_boundary(self):
        """extra가 아니라 정규 필드로 해석됐음을 종단에서 간접 확인 — quantity_mismatch의
        instrument_type이 gdtf_fixture 값(더 정규화된 소스)을 우선 사용한다."""
        data = self._FIXTURE_PATH.read_bytes()
        execution = _dispatch(_registry(), file_content_base64=self._b64_bytes(data))
        payload = json.loads(execution.result.content)
        mismatches = payload["diffs"]["quantity_mismatch"]
        assert len(mismatches) == 1
        assert mismatches[0]["instrument_type"] == "Martin Professional@MAC Encore Performance CLD"

    def test_console_footprint_width_injection_is_reported_as_deferred_not_silent(self):
        data = self._FIXTURE_PATH.read_bytes()
        execution = _dispatch(_registry(), file_content_base64=self._b64_bytes(data))
        payload = json.loads(execution.result.content)
        skipped_kinds = {entry["kind"] for entry in payload["skipped_checks"]}
        assert "console_footprint_width_injection_deferred" in skipped_kinds


class TestUnitNumberScopeFixEndToEndThroughDispatch:
    """v0.1.5 회귀(코디네이터 정확 재현) — 서로 다른 포지션의 동명 Unit Number가
    dispatch 전체 경로에서 더 이상 전멸하지 않는다."""

    @staticmethod
    def _b64(text: str) -> str:
        return base64.b64encode(text.encode("utf-8")).decode("ascii")

    def test_two_different_positions_with_the_same_unit_number_both_survive(self):
        """코디네이터 재현 A — 수정 전에는 fixture_count 0, join_key_conflicts 1건이었다."""
        header = "Fixture Type,Universe,DMX Address,Unit Number,Position"
        rows = [
            "MAC Encore,1,1,1,Upstage Truss",
            "Source Four,2,1,1,FOH",
        ]
        data = "\n".join([header, *rows])
        execution = _dispatch(_registry(), file_content_base64=self._b64(data))
        payload = json.loads(execution.result.content)
        assert payload["designed_rig"]["fixture_count"] == 2
        assert payload["designed_rig"]["join_key_conflicts"] == []
        assert payload["diffs"]["performed"] is True

    def test_same_position_same_unit_number_still_conflicts(self):
        """대조군 — 같은 포지션 안에서는 여전히 충돌로 잡힌다(스코프가 살아있음을 증명)."""
        header = "Fixture Type,Universe,DMX Address,Unit Number,Position"
        rows = [
            "MAC Encore,1,1,1,FOH",
            "Source Four,1,2,1,FOH",
        ]
        data = "\n".join([header, *rows])
        execution = _dispatch(_registry(), file_content_base64=self._b64(data))
        payload = json.loads(execution.result.content)
        assert payload["designed_rig"]["fixture_count"] == 0
        assert len(payload["designed_rig"]["join_key_conflicts"]) == 1
        assert payload["diffs"]["performed"] is False


class TestSyntheticPathBGridEndToEndThroughDispatch:
    """경로 B(워크시트 그리드) 휴리스틱이 최초로 실행됨을 확인 — ⚠ 합성물, 실물 아님.

    `synthetic_path_b_worksheet_grid.csv`는 손으로 만든 합성 워크시트 그리드다
    (제목행+DB헤더행+데이터4행+소계행). M0가 확보한 실물 샘플은 path_kind=A라
    이 경로를 한 번도 타지 않았다 — 이 테스트는 코드 경로가 실제로 동작함만
    증명하며, ASSUMPTION-70(실물 워크시트에서도 그런가)은 미해소로 남는다.
    """

    _FIXTURE_PATH = (
        Path(__file__).parent / "fixtures" / "vwx" / "synthetic_path_b_worksheet_grid.csv"
    )

    @staticmethod
    def _b64_bytes(data: bytes) -> str:
        return base64.b64encode(data).decode("ascii")

    def test_title_row_and_subtotal_row_are_structurally_excluded_data_rows_survive(self):
        data = self._FIXTURE_PATH.read_bytes()
        execution = _dispatch(_registry(), file_content_base64=self._b64_bytes(data))
        payload = json.loads(execution.result.content)
        # 4개 데이터 행이 전량 판독되고(제목행·소계행은 데이터로 세지 않음),
        # 포지션별 조인 키 스코프가 이 파일 안에서도 정상 동작한다(2 포지션 × 2 유닛 = 4).
        assert payload["designed_rig"]["fixture_count"] == 4
        assert payload["designed_rig"]["join_key_conflicts"] == []
        assert payload["diffs"]["performed"] is True
