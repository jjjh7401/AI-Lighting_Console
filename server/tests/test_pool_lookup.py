"""t231 — 풀 탐색 술어 비대칭: 시트 다섯 자리가 잘림을 부재로 읽고 다중을 안 가른다.

## 무엇을 재는가

t216 이 찾은 것은 비대칭이다 — 대화 쪽(`server/web/session.py`
`_resolve_named_pool_no`)은 완전 일치 + 절단 거부로 **안전한 쪽으로 틀리고**,
시트 쪽은 접두 일치 + 첫 일치로 **위험한 쪽으로 틀린다.**

t231 이 잰 것은 그 **폭**이다: 시트 쪽 자리는 하나가 아니라 다섯이고
(`tools.py` 5015 · 5579 · 5657 · 5718 · 6752), 결함 축이 둘이다.

- **D1 — 접두 일치 + 첫 일치.** 후보가 둘이어도 조용히 첫째를 집는다.
- **D2 — 잘림을 부재로 읽음.** 잘린 목록에 대상이 없으면 「그런 풀이 없다」로
  답한다. 안 보인 것을 부재로 보고하는 것이다.

## 왜 술어를 하나로 통일하지 않는가

`All` 조회는 **다중 일치가 정상**이다 — 이 쇼파일에 `All 1` ~ `All 5` 가 함께
살고, FX 목적지 해석이 그중 첫째를 고르는 것을 의도한다. 한 벌 거절 술어를
넣으면 그 경로가 항상 죽는다. 그래서 술어가 둘이고, 이 파일이 **둘이 다르다는
것 자체를** 고정한다 — 다음 사람이 「여기도 거절로 통일하자」로 안 깨도록.

콘솔 접촉 0. 순수 검증이다.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

from server.llm.types import ToolCall
from server.lxseq.cue_parser import CANONICAL_CUE_COLUMNS
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import build_toolset, rig_object
from server.rig.pool_lookup import (
    POOL_AMBIGUOUS,
    POOL_LIST_TRUNCATED,
    POOL_LIST_UNREAD,
    POOL_NOT_FOUND,
    pool_slot_and_name,
    resolve_all_pool,
    resolve_family_pool,
)

RIG = Path("src/Lighting_Designer/02_RIG팩")
DIM = RIG / "LXSEQ_RIG_01_ShowBase_r3.preset-dim.csv"
POOLS = "DataPool/PresetPools"


def _child(no, name: str) -> dict:
    return dict([("class", "Object"), ("i", no), ("name", name)])


def _window(children: list, *, truncated: bool = False, child_count=None) -> dict:
    count = len(children) if child_count is None else child_count
    return dict(
        ok=True,
        truncated=truncated,
        offset=0,
        node=dict(childCount=count),
        children=list(children),
    )


class _StubPort:
    """풀 목록 한 창만 답하는 최소 포트. 잘림은 **전진 불가**로 만든다.

    truncated=True 를 답하면서 후속 창에 offset 에코를 주지 않으므로
    paged_children 이 무진전으로 읽고 truncated=True 로 강등한다 — 실기의
    낡은 응답기와 같은 갈래다.
    """

    def __init__(self, pools, *, truncated: bool = False, raises: bool = False) -> None:
        self._pools = pools
        self._truncated = truncated
        self._raises = raises

    def query_state(self, path: str, *, offset: int = 0) -> dict:
        if self._raises:
            raise RuntimeError("풀 목록을 못 읽었다")
        if self._truncated:
            return _window(self._pools, truncated=True, child_count=99)
        return _window(self._pools)


class TestThePredicateItself:
    """자리별 검사는 「무언가가 거절한다」를 잰다 — 술어를 직접 재는 반이 따로 있다."""

    def test_a_unique_family_match_resolves(self):
        no, refusal = resolve_family_pool(_StubPort([_child(4, "Color")]), POOLS, "Color")
        assert (no, refusal) == (4, None)

    def test_two_family_matches_are_refused_not_silently_first(self):
        """🔴 D1 — 지금 코드가 조용히 첫째를 집는 자리."""
        no, refusal = resolve_family_pool(
            _StubPort([_child(4, "Color"), _child(9, "ColorFX")]), POOLS, "Color"
        )
        assert no is None
        assert refusal[0] == POOL_AMBIGUOUS
        assert "ColorFX" in refusal[1], refusal[1]

    def test_no_match_in_a_whole_listing_is_the_honest_absence(self):
        no, refusal = resolve_family_pool(_StubPort([_child(1, "Dimmer")]), POOLS, "Color")
        assert no is None
        assert refusal[0] == POOL_NOT_FOUND

    def test_a_truncated_listing_is_not_an_absence(self):
        """🔴 D2 — 안 보인 것을 부재로 보고하지 않는다."""
        no, refusal = resolve_family_pool(
            _StubPort([_child(1, "Dimmer")], truncated=True), POOLS, "Color"
        )
        assert no is None
        assert refusal[0] == POOL_LIST_TRUNCATED, refusal

    def test_an_unread_listing_is_its_own_reason(self):
        no, refusal = resolve_family_pool(_StubPort([], raises=True), POOLS, "Color")
        assert no is None
        assert refusal[0] == POOL_LIST_UNREAD

    def test_the_three_refusals_do_not_collapse_into_one_string(self):
        """사유가 접히면 사람이 무엇을 고쳐야 하는지 갈리지 않는다(규약 §3.6)."""
        whole = resolve_family_pool(_StubPort([_child(1, "Dimmer")]), POOLS, "Color")
        cut = resolve_family_pool(_StubPort([_child(1, "Dimmer")], truncated=True), POOLS, "Color")
        dead = resolve_family_pool(_StubPort([], raises=True), POOLS, "Color")
        reasons = set([whole[1][1], cut[1][1], dead[1][1]])
        assert len(reasons) == 3, reasons


class TestTheAllPredicateIsDeliberatelyDifferent:
    """🔴 이 반이 조건 2 다 — 다중 일치가 **정상**임을 고정한다.

    이 검사가 없으면 다음 회차가 「일관성」을 이유로 All 쪽에도 다중 거절을
    넣고, FX 목적지 해석이 항상 죽는다. 그 회귀는 조용하다 — 거절이므로
    사고처럼 보이지 않는다.
    """

    @staticmethod
    def _five_all_pools():
        return [_child(21 + i, "All " + str(i + 1)) for i in range(5)]

    def test_five_all_pools_are_normal_and_the_first_wins(self):
        pools = [_child(1, "Dimmer")] + self._five_all_pools()
        no, refusal = resolve_all_pool(_StubPort(pools), POOLS)
        assert (no, refusal) == (21, None)

    def test_the_family_predicate_would_refuse_the_very_same_listing(self):
        """두 술어가 같은 입력에 **다르게** 답한다 — 그것이 이 분리의 요점이다."""
        pools = self._five_all_pools()
        assert resolve_all_pool(_StubPort(pools), POOLS)[0] == 21
        assert resolve_family_pool(_StubPort(pools), POOLS, "All")[1][0] == POOL_AMBIGUOUS

    def test_all_lookup_still_refuses_a_truncated_listing(self):
        """다중이 정상인 것과 「모름은 거부」는 다른 축이다."""
        no, refusal = resolve_all_pool(_StubPort([_child(1, "Dimmer")], truncated=True), POOLS)
        assert no is None
        assert refusal[0] == POOL_LIST_TRUNCATED

    def test_all_lookup_names_absence_when_the_listing_is_whole(self):
        no, refusal = resolve_all_pool(_StubPort([_child(1, "Dimmer")]), POOLS)
        assert no is None
        assert refusal[0] == POOL_NOT_FOUND


class TestSlotRuleAgreesWithRigObject:
    """합치기 전후로 슬롯 규율이 갈리지 않는다는 것을 **재서** 고정한다.

    읽어서 「같다」고 하지 않는다(조건 3). 두 자리가 갈리면 풀 번호가 한쪽에서만
    주소가 되고, 그 어긋남은 조용하다.
    """

    CORPUS = (
        dict(i=4, name="Color"),
        dict(i="4", name="Color"),
        dict(i=None, name="Color"),
        dict(i=True, name="Color"),
        dict(i="넷", name="Color"),
        dict(name="Color"),
        dict(i=4),
    )

    def test_every_corpus_row_agrees(self):
        for child in self.CORPUS:
            mine = pool_slot_and_name(child)
            theirs = rig_object(dict(child))
            assert mine[0] == theirs.get("no"), (child, mine, theirs)
            assert mine[1] == str(theirs.get("name") or ""), (child, mine, theirs)


# =============================================================================
# 자리별 재현 — 다섯 자리를 각각 잰다 (조건 1)
# =============================================================================


class _Approval:
    def request_approval(self, request) -> bool:
        return True


class _TreePort:
    """경로별 응답. 풀 목록만 손잡이가 있고 나머지는 빈 창을 답한다."""

    def __init__(self, pools, *, pools_truncated: bool = False, slots=None) -> None:
        self._pools = pools
        self._pools_truncated = pools_truncated
        self._slots = slots or []
        self.executed: list[str] = []

    def execute(self, command: str) -> ExecutionResult:
        self.executed.append(command)
        return ExecutionResult(ok=True, detail="OK")

    def query_state(self, path: str, *, offset: int = 0) -> dict:
        if path == POOLS:
            if self._pools_truncated:
                return _window(self._pools, truncated=True, child_count=99)
            return _window(self._pools)
        if path.startswith(POOLS + "/"):
            return _window(self._slots)
        if path == "DataPool/Groups":
            return _window([_child(4, "BACK")])
        return _window([])

    def query_property(self, path: str, name: str) -> dict:
        return dict(ok=False, error="not readable")


def _import_presets(port) -> dict:
    registry = build_toolset(
        execution_port=port,
        state_port=port,
        property_port=port,
        group_approval_port=_Approval(),
    )
    execution = registry.dispatch(
        ToolCall(
            id="t231",
            name="import_lxseq_presets",
            arguments=dict(
                file_content_base64=base64.b64encode(DIM.read_bytes()).decode("ascii"),
                action="preview",
            ),
        )
    )
    return json.loads(execution.result.content)


class TestSite5015PresetImport:
    """_preset_pool_number — 페이징이 아예 없던 자리."""

    def test_a_truncated_listing_does_not_become_no_such_pool(self):
        payload = _import_presets(_TreePort([_child(4, "Color")], pools_truncated=True))
        assert payload["pool_no"] is None
        assert "잘렸" in str(payload.get("pool_error") or ""), payload.get("pool_error")

    def test_two_matching_pools_are_refused_rather_than_first_won(self):
        payload = _import_presets(_TreePort([_child(1, "Dimmer"), _child(7, "DimmerFX")]))
        assert payload["pool_no"] is None, payload["pool_no"]
        assert "DimmerFX" in str(payload.get("pool_error") or ""), payload.get("pool_error")

    def test_the_control_still_plans_with_one_whole_match(self):
        """대조군이 없으면 위 둘은 「이 툴이 그냥 고장 났다」와 구별되지 않는다."""
        payload = _import_presets(_TreePort([_child(1, "Dimmer")]))
        assert payload["pool_no"] == 1
        assert payload["planned"], payload


def _cue_body(col: str = "", pos: str = "") -> bytes:
    header = ",".join(CANONICAL_CUE_COLUMNS)
    row = ",".join(["Q010", "BACK", "55", col, pos] + [""] * 10 + ["", ""])
    return (header + "\n" + row + "\n").encode("utf-8")


def _col_sheet() -> str:
    body = "ID,Name,Value,Purpose\nCOL.01,웜 화이트,,키\n"
    return base64.b64encode(body.encode("utf-8")).decode("ascii")


def _import_cues(port, *, col: str = "", pos: str = "") -> dict:
    registry = build_toolset(
        execution_port=port,
        state_port=port,
        property_port=port,
        group_approval_port=_Approval(),
    )
    arguments = dict(
        file_content_base64=base64.b64encode(_cue_body(col=col, pos=pos)).decode("ascii"),
        sequence_name="t231",
        action="preview",
    )
    if col:
        arguments["preset_col_content_base64"] = _col_sheet()
    execution = registry.dispatch(
        ToolCall(id="t231", name="import_lxseq_cues", arguments=arguments)
    )
    return json.loads(execution.result.content)


class TestSite5579CueSheetJoin:
    """프리셋 시트 조인 — paged_children 은 부르되 절단 플래그를 버리던 자리."""

    def test_a_truncated_listing_does_not_become_no_such_pool(self):
        payload = _import_cues(_TreePort([_child(1, "Dimmer")], pools_truncated=True), col="COL.01")
        errors = str(payload.get("preset_sheet_errors") or dict())
        assert "잘렸" in errors, errors

    def test_two_matching_pools_are_refused(self):
        payload = _import_cues(_TreePort([_child(4, "Color"), _child(9, "ColorFX")]), col="COL.01")
        errors = str(payload.get("preset_sheet_errors") or dict())
        assert "ColorFX" in errors, errors

    def test_the_control_resolves_with_one_whole_match(self):
        """대조군 — 온전한 목록에 하나만 맞으면 그 시트는 사유 없이 지나간다."""
        pools = [_child(4, "Color"), _child(2, "Position")]
        payload = _import_cues(_TreePort(pools), col="COL.01")
        errors = payload.get("preset_sheet_errors") or dict()
        assert "preset_col_content_base64" not in errors, errors


class TestSite5718PositionPool:
    """POS 풀 조회 — 같은 축, 다른 자리."""

    def test_a_truncated_listing_does_not_become_no_such_pool(self):
        payload = _import_cues(_TreePort([_child(1, "Dimmer")], pools_truncated=True), pos="POS.01")
        errors = str(payload.get("preset_sheet_errors") or dict())
        assert "잘렸" in errors, errors

    def test_two_matching_pools_are_refused(self):
        payload = _import_cues(
            _TreePort([_child(2, "Position"), _child(8, "PositionFX")]), pos="POS.01"
        )
        errors = str(payload.get("preset_sheet_errors") or dict())
        assert "PositionFX" in errors, errors


def _fx_sheet() -> str:
    body = "ID,Name,Attribute,WaveSteps,BaseRate,Width,Phase,Note\nFX.01,DIM-CHASE,Dimmer,2-step,240,50%,0..360,\n"
    return base64.b64encode(body.encode("utf-8")).decode("ascii")


def _import_cues_with_fx(port, *, fx: str = "FX.01") -> dict:
    registry = build_toolset(
        execution_port=port,
        state_port=port,
        property_port=port,
        group_approval_port=_Approval(),
    )
    header = ",".join(CANONICAL_CUE_COLUMNS)
    row = ",".join(["Q010", "BACK", "55", "", "", "", fx] + [""] * 8 + ["", ""])
    body = (header + "\n" + row + "\n").encode("utf-8")
    arguments = dict(
        file_content_base64=base64.b64encode(body).decode("ascii"),
        sequence_name="t231",
        action="preview",
        fx_content_base64=_fx_sheet(),
    )
    execution = registry.dispatch(
        ToolCall(id="t231", name="import_lxseq_cues", arguments=arguments)
    )
    return json.loads(execution.result.content)


class TestSite5657CueSheetFxAllPool:
    """FX 풀 조회 — 접두어가 all 이라 다중이 정상인 자리.

    그래서 이 자리에서 재는 것은 **잘림 축 하나**다. 다중을 거절하면 안 되는
    자리이므로 D1 재현은 여기에 없다 — 그 사실 자체가 위 All 술어 반이 고정한다.
    """

    def test_a_truncated_listing_does_not_become_no_such_pool(self):
        payload = _import_cues_with_fx(_TreePort([_child(1, "Dimmer")], pools_truncated=True))
        errors = str(payload.get("preset_sheet_errors") or dict())
        assert "잘렸" in errors, errors

    def test_several_all_pools_still_resolve_to_the_first(self):
        """대조군이자 계약 — 다중이 정상이다."""
        pools = [_child(1, "Dimmer")] + [_child(21 + i, "All " + str(i + 1)) for i in range(5)]
        payload = _import_cues_with_fx(_TreePort(pools))
        errors = payload.get("preset_sheet_errors") or dict()
        assert "fx_content_base64" not in errors, errors
