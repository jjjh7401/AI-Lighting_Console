"""t51 — 시트 종류 레지스트리와 **함께 자라는** 소비 지점 검사.

시트 종류는 `server/sheets/registry.py`의 :data:`REGISTRY`에서 한 번 선언되지만
소비는 네 곳에서 더 일어난다. 종류를 더하는 사람이 다섯 자리를 모두 만져야
하는데, 기존 검사는 **이미 고친 자리**(레지스트리 행 수)에서만 빨개지고 안 고친
자리에서는 침묵했다. 엉뚱한 자리에서만 울리는 그물은 없느니만 못하다 — 빨간불이
거짓 안심을 사기 때문이다.

그래서 여기 있는 검사는 종류 이름을 **하나도 적지 않는다**. 전부 :data:`REGISTRY`
자체를 돌며, 새 행이 생기면 사례가 저절로 늘어난다.

소비 지점과 이 파일이 그것을 재는 방식:

===  ====================================================  ==========================
#    자리                                                   여기서 재는 것
===  ====================================================  ==========================
1    ``server/sheets/registry.py`` ``REGISTRY``             정본 — 사례의 출처
2    ``server/orchestrator/tools.py`` ``SHEET_KIND_ACTIONS``  종류별 유효 ``action``
3    ``server/web/session.py`` ``_SHEET_ROW_COUNTERS``      종류별 행 수 판독기
4    ``server/web/session.py`` 첨부 이음매                    ``session_method`` 배선
5    ``server/orchestrator/tools.py`` 래퍼 스키마             ``action`` enum · 인자명
===  ====================================================  ==========================

**2·3번은 전 종류가 아니라 ``tool`` 종 행에만 걸린다** — 이것을 실측으로 확인하고
검사를 그렇게 짰다. ``session_method`` 종(오늘은 ``vectorworks``)은 첨부 이음매에서
자기 슬롯으로 갈라져 나가므로 래퍼에도, ``_store_uploaded_sheet``에도 닿지 않는다
(``_sheet_row_counts``의 호출 지점은 ``_store_uploaded_sheet`` 하나뿐이다). 전
종류를 두 표에 요구하는 검사는 **오늘 당장 빨간불**이며, 그것이야말로 이 카드가
없애려는 "엉뚱한 자리에서 우는 그물"이다.
"""

from __future__ import annotations

import pytest

from server.orchestrator.tools import SHEET_KIND_ACTIONS, build_toolset
from server.sheets.registry import (
    HANDLER_TAG_SESSION_METHOD,
    HANDLER_TAG_TOOL,
    REGISTRY,
)
from server.web.session import (
    _ATTACH_ROUTED_SESSION_METHODS,
    _SHEET_ROW_COUNTERS,
    ChatSession,
)

WRAPPER = "import_uploaded_sheet"

#: 태그별로 가른 행 목록. 모듈 수준에서 계산하므로 ``REGISTRY``에 행이 하나 더
#: 생기면 아래 파라미터화 사례도 하나 더 생긴다 — 손으로 더할 것이 없다.
TOOL_ROWS = [row for row in REGISTRY if row.handler.kind_tag == HANDLER_TAG_TOOL]
SESSION_METHOD_ROWS = [
    row for row in REGISTRY if row.handler.kind_tag == HANDLER_TAG_SESSION_METHOD
]


def _kind_id(row) -> str:
    return row.kind


class _NeverCalledPort:
    """스키마만 읽는다 — 콘솔에 한 마디도 발화하지 않는다."""

    def execute(self, command: str):
        raise AssertionError("스키마 판독은 콘솔에 발화하지 않는다: " + command)

    def query_state(self, probe: str):
        raise AssertionError("스키마 판독은 콘솔 상태를 읽지 않는다: " + probe)


def _wrapper_schema() -> dict:
    """래퍼 툴이 모델에게 **실제로** 내보이는 스키마.

    문자열을 훑지 않고 ``build_toolset``이 조립한 정의를 그대로 읽는다 — 문면이
    아니라 구조를 재기 위해서다.
    """
    port = _NeverCalledPort()
    registry = build_toolset(execution_port=port, state_port=port)
    definition = next(item for item in registry.definitions() if item.name == WRAPPER)
    return definition.parameters


def _wrapper_properties() -> dict:
    properties = _wrapper_schema().get("properties")
    assert isinstance(properties, dict), "래퍼 스키마에 properties가 없다"
    return properties


# -- 0. 그물이 비어 있지 않은가 --------------------------------------------------
#
# 파라미터화 목록이 비면 pytest는 사례를 0개 수집하고도 초록이다. 아래 검사들이
# 공허해지는 유일한 경로가 그것이므로 먼저 막는다.


class TestPartitionsAreNotVacuous:
    def test_registry_is_not_empty(self):
        assert REGISTRY, "REGISTRY가 비었다 — 아래 검사가 전부 공허해진다"

    def test_both_partitions_carry_at_least_one_row(self):
        assert TOOL_ROWS, (
            "tool 종 행이 하나도 없다 — SHEET_KIND_ACTIONS·_SHEET_ROW_COUNTERS "
            "검사가 사례 0개로 조용히 통과한다"
        )
        assert SESSION_METHOD_ROWS, (
            "session_method 종 행이 하나도 없다 — 첨부 이음매 배선 검사가 사례 "
            "0개로 조용히 통과한다"
        )

    def test_every_row_falls_into_a_checked_partition(self):
        """태그가 오타 나면 두 목록 어디에도 안 들어가 **아무도 안 잰다**."""
        covered = [row.kind for row in TOOL_ROWS + SESSION_METHOD_ROWS]
        for row in REGISTRY:
            assert row.kind in covered, (
                f"시트 종류 '{row.kind}'의 handler.kind_tag가 "
                f"'{row.handler.kind_tag}'라 tool·session_method 어느 쪽에도 "
                f"들지 않는다 — 이 종류는 t51 검사 전부를 조용히 빠져나간다. "
                f"server/sheets/registry.py의 HANDLER_TAGS 중 하나를 쓰라."
            )


# -- 2. SHEET_KIND_ACTIONS (server/orchestrator/tools.py) ------------------------


class TestActionTable:
    @pytest.mark.parametrize("row", TOOL_ROWS, ids=_kind_id)
    def test_tool_row_has_supported_actions(self, row):
        actions = SHEET_KIND_ACTIONS.get(row.kind)
        assert actions, (
            f"[소비 지점 2/5] 시트 종류 '{row.kind}'가 "
            f"server/orchestrator/tools.py의 SHEET_KIND_ACTIONS에 없거나 비었다 "
            f"— 이 종류가 지원하는 action 튜플을 그 표에 더하라. 비어 있으면 "
            f"래퍼의 kind_action_mismatch 가드가 판별력을 잃는다."
        )
        for action in actions:
            assert isinstance(action, str) and action, (
                f"[소비 지점 2/5] '{row.kind}'의 SHEET_KIND_ACTIONS 항목에 "
                f"빈 값 또는 문자열이 아닌 값이 있다: {action!r}"
            )


# -- 3. _SHEET_ROW_COUNTERS (server/web/session.py) ------------------------------


class TestRowCounterTable:
    @pytest.mark.parametrize("row", TOOL_ROWS, ids=_kind_id)
    def test_tool_row_has_a_row_counter(self, row):
        counter = _SHEET_ROW_COUNTERS.get(row.kind)
        assert callable(counter), (
            f"[소비 지점 3/5] 시트 종류 '{row.kind}'의 행 수 판독기가 "
            f"server/web/session.py의 _SHEET_ROW_COUNTERS에 없다 — 첨부 안내가 "
            f"'행 수 미상'으로 나가고, 운영자는 몇 행이 담겼는지 모른 채 계획을 "
            f"승인하게 된다."
        )


# -- 4. 첨부 이음매의 session_method 배선 (server/web/session.py) ----------------


class TestAttachSeamWiring:
    @pytest.mark.parametrize("row", SESSION_METHOD_ROWS, ids=_kind_id)
    def test_session_method_row_is_routed_not_refused(self, row):
        name = row.handler.name
        assert name in _ATTACH_ROUTED_SESSION_METHODS, (
            f"[소비 지점 4/5] 시트 종류 '{row.kind}'의 세션 메서드 '{name}'이 "
            f"첨부 이음매에 배선돼 있지 않다 — upload_vectorworks_export가 이 "
            f"종류를 받으면 '배선돼 있지 않습니다'로 거절한다. "
            f"server/web/session.py의 _ATTACH_ROUTED_SESSION_METHODS에 더하고 "
            f"이음매가 그 이름을 어디로 보낼지 정하라."
        )

    @pytest.mark.parametrize("row", SESSION_METHOD_ROWS, ids=_kind_id)
    def test_session_method_row_names_a_real_method(self, row):
        name = row.handler.name
        assert callable(getattr(ChatSession, name, None)), (
            f"[소비 지점 4/5] 시트 종류 '{row.kind}'가 이름 붙인 세션 메서드 "
            f"'{name}'이 ChatSession에 없다 — 행은 존재하지 않는 자리를 가리킨다."
        )


# -- 5. 래퍼의 닫힌 JSON 스키마 (server/orchestrator/tools.py) -------------------
#
# 스키마는 ``additionalProperties: False``다. 여기 없는 이름은 모델이 **보낼 수
# 없으므로**, 행의 passthrough_args에만 적고 스키마에 안 적으면 그 인자는 영영
# 전달되지 않는다 — 오류 없이 조용히.


class TestWrapperSchema:
    def test_wrapper_schema_is_closed(self):
        """닫혀 있어야 아래 두 검사가 의미를 가진다."""
        assert _wrapper_schema().get("additionalProperties") is False, (
            "래퍼 스키마가 더 이상 닫혀 있지 않다 — passthrough_args 검사의 "
            "전제가 무너졌으니 이 검사군을 다시 설계하라"
        )

    @pytest.mark.parametrize("row", REGISTRY, ids=_kind_id)
    def test_passthrough_args_are_declared_in_the_schema(self, row):
        properties = _wrapper_properties()
        missing = [name for name in row.passthrough_args if name not in properties]
        assert not missing, (
            f"[소비 지점 5/5] 시트 종류 '{row.kind}'의 passthrough_args "
            f"{missing}가 래퍼 스키마에 없다 — 스키마가 "
            f"additionalProperties: False라 모델은 이 인자를 보낼 수 없고, "
            f"거절도 없이 조용히 누락된다. "
            f"server/orchestrator/tools.py의 import_uploaded_sheet 정의에 "
            f"properties 항목을 더하라."
        )

    @pytest.mark.parametrize("row", TOOL_ROWS, ids=_kind_id)
    def test_every_supported_action_is_offerable(self, row):
        if "action" not in row.passthrough_args:
            pytest.skip("이 종류는 action을 대상 툴로 전달하지 않는다")
        properties = _wrapper_properties()
        declared = properties.get("action", dict()).get("enum")
        assert declared, "래퍼 스키마의 action에 enum이 없다"
        unofferable = [a for a in SHEET_KIND_ACTIONS.get(row.kind, ()) if a not in declared]
        assert not unofferable, (
            f"[소비 지점 5/5] 시트 종류 '{row.kind}'가 지원한다고 적힌 action "
            f"{unofferable}를 래퍼 스키마의 enum {list(declared)}이 내보이지 "
            f"않는다 — 모델은 그 값을 보낼 수 없으므로 SHEET_KIND_ACTIONS의 "
            f"그 항목은 도달 불가능하다. "
            f"server/orchestrator/tools.py의 import_uploaded_sheet 정의에서 "
            f"action enum을 넓히라."
        )
