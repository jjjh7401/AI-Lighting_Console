"""M7 — 1단계 공개 계약 무변경 (AC-AUTOPATCH-025).

**무엇을 고정하고 무엇을 고정하지 않는가.** 고정하는 것은 `precheck_vectorworks_diff`
payload의 **최상위 키 집합과 키별 타입 시그니처**다. 값은 고정하지 않는다 — 값 고정은
무관한 변경에도 깨져 곧 무의미해지고, 그러면 스냅샷은 지워지거나 기계적으로 갱신된다
(AC-AUTOPATCH-025①).

키 **내부**의 의미는 여기서 다시 확인하지 않는다 — 1단계 자신의 구조 assert
(`test_vwx_report.py`·`test_vwx_multisystem_real_samples.py` 계열)에 위임한다(AC-025③).
이 파일은 "2단계가 1단계 출력의 **형상**을 바꾸지 않았다"만 본다.

**2단계가 실제로 건드린 것 하나**: `designed_rig.fixtures[*]`에
`gdtf_fixture`·`mode`·`footprint` 열이 **추가**됐다(M7). 패치 계층은 이 payload만 입력으로
받으므로 도면 점유폭이 없으면 주소 계획이 전부 `footprint_unknown`으로 제외되기 때문이다.
그것은 **중첩 키 추가**이고 최상위 계약은 불변이다 — 아래 스냅샷이 그 사실을 강제한다.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

from server.llm.types import ToolCall
from server.orchestrator.tools import build_toolset
from server.prechk.inventory import FIXTURE_ROOT

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = PROJECT_ROOT / "server" / "tests" / "fixtures" / "vwx"
EXPORT = FIXTURE_DIR / "vectorworks_worksheet_multisystem_full.csv"
SNAPSHOT = FIXTURE_DIR / "stage1_contract_snapshot.json"

TOOL = "precheck_vectorworks_diff"


class _NeverCalledExecutionPort:
    def execute(self, command: str):
        raise AssertionError(f"{TOOL} must never call execution_port: {command}")


class _RigPort:
    """빈 콘솔 — 계약 형상은 콘솔 내용과 무관해야 한다."""

    def query_state(self, path: str) -> dict:
        if path == FIXTURE_ROOT:
            return {
                "ok": True,
                "path": path,
                "node": {"name": "Fixtures", "class": "Fixtures", "childCount": 0},
                "children": [],
                "truncated": False,
            }
        return {"ok": False, "path": path, "error": "not readable"}

    def query_property(self, path: str, property_name: str) -> dict:
        return {"ok": False, "path": path, "property": property_name, "error": "not readable"}


def _stage1_payload() -> dict:
    rig = _RigPort()
    registry = build_toolset(
        execution_port=_NeverCalledExecutionPort(), state_port=rig, property_port=rig
    )
    execution = registry.dispatch(
        ToolCall(
            id="c1",
            name=TOOL,
            arguments={
                "file_content_base64": base64.b64encode(EXPORT.read_bytes()).decode("ascii")
            },
        )
    )
    assert execution.result.is_error is False, execution.result.content
    return json.loads(execution.result.content)


def type_signature(value: object) -> object:
    """값이 아니라 **모양**만 남긴다 — AC-AUTOPATCH-025①이 정한 깊이 그대로.

    최상위 값의 타입(dict/list/str/int/bool)과, 리스트면 **원소 타입의 집합**까지다.
    더 깊이 들어가지 않는 것은 의도다: 중첩 구조까지 고정하면 1단계 내부의 정당한
    확장(실제로 M7이 `designed_rig.fixtures[*]`에 열 셋을 더했다)마다 깨지고, 그러면
    스냅샷은 기계적으로 갱신되어 아무것도 막지 못하게 된다. 중첩 의미는 1단계 자신의
    구조 assert가 지킨다(AC-025③) — 여기서 사본을 만들지 않는다.
    """
    if isinstance(value, list):
        return {"list": sorted({type(item).__name__ for item in value})}
    return type(value).__name__


def _top_level_signature(payload: dict) -> dict:
    return {key: type_signature(value) for key, value in sorted(payload.items())}


def test_the_top_level_contract_matches_the_snapshot():
    """AC-025② — 최상위 키 집합과 키별 타입 시그니처가 동일하다."""
    recorded = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    observed = _top_level_signature(_stage1_payload())
    assert set(observed) == set(recorded), "1단계 payload의 최상위 키 집합이 바뀌었다"
    assert observed == recorded


def test_an_added_top_level_key_control_is_caught():
    """AC-025④ 비공허성 — 최상위 키를 하나 추가한 사본에서 위 단정이 실제로 실패한다."""
    recorded = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    planted = {**_stage1_payload(), "patch_result": {"ok": True}}
    observed = _top_level_signature(planted)
    assert set(observed) != set(recorded)
    assert observed != recorded


def test_a_changed_type_signature_control_is_caught():
    """AC-025④ 비공허성 — 키를 남긴 채 타입만 바꿔도 잡힌다(키 집합 비교만으로는 못 잡는다)."""
    recorded = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    planted = {**_stage1_payload(), "summary_ko": ["문자열이 아니라 리스트"]}
    observed = _top_level_signature(planted)
    assert set(observed) == set(recorded), "이 대조군은 키 집합은 그대로여야 의미가 있다"
    assert observed != recorded


def test_the_designed_fixture_rows_carry_the_patch_layer_columns():
    """M7이 **추가**한 중첩 열 — 없으면 패치 계층이 전부 `footprint_unknown`이 된다."""
    payload = _stage1_payload()
    rows = payload["designed_rig"]["fixtures"]
    assert rows, "픽스처가 0대면 이 확인은 공허하다"
    for row in rows:
        assert {"gdtf_fixture", "mode", "footprint"} <= set(row)


def test_the_added_columns_did_not_displace_the_stage_one_columns():
    """추가지 교체가 아니다 — 1단계가 쓰던 열이 그대로 있다."""
    (row, *_) = _stage1_payload()["designed_rig"]["fixtures"]
    assert {
        "unit_number",
        "instrument_type",
        "system",
        "universe",
        "address",
        "classification",
        "address_basis",
    } <= set(row)
