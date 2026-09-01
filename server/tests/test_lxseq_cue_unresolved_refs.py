"""t225 — 미해결 프리셋 참조를 **원인별로** 가른다.

## 재현 우선 — 이 카드가 존재한 이유

t224 는 「미해결 11종」을 세기만 했고, 산출물은 그 열한 종이 **왜** 미해결인지
말하지 않았다. `cue_mapper._HOLD_BLOCK_CLASS[UNRESOLVED_PRESET]` 이 그 한계를
문면으로 적어 뒀다 — 「시트에 정의가 없는 것인지, 정의는 있는데 콘솔 슬롯
조인이 안 선 것인지 **이 층에서는 안 갈린다**」.

그래서 t225 는 콘솔 프리셋 풀 다섯 개를 손으로 떠서 (a) 콘솔에 없다 /
(b) 있는데 이름이 다르다 / (c) 시트가 안 실렸다 를 갈라야 했다. 셋은 처방이
다르다 — 프리셋을 만들어야 하나, 시트를 고쳐야 하나, 호출 인자를 고쳐야 하나.

툴 층은 그 셋을 **가를 수 있다**: 시트(정의)와 콘솔 되읽기(조인)를 둘 다 쥔
자리가 `import_lxseq_cues` 하나뿐이기 때문이다. 이 파일이 그 분류를 고정한다.

콘솔 접촉 0 — 상태 포트는 경로별로 답하는 가짜다.
"""

from __future__ import annotations

import base64
import json

from server.llm.types import ToolCall
from server.lxseq.cue_mapper import (
    UNRESOLVED_CONSOLE_LACKS_NAME,
    UNRESOLVED_POOL_UNREADABLE,
    UNRESOLVED_SHEET_LACKS_ID,
    UNRESOLVED_SHEET_NOT_SUPPLIED,
)
from server.lxseq.cue_parser import CANONICAL_CUE_COLUMNS
from server.orchestrator.tools import build_toolset

COLOR_POOL_NO = 4
POSITION_POOL_NO = 2


def _obj(no: int, name: str) -> dict:
    return dict([("class", "Object"), ("i", no), ("name", name)])


def _reply(children: list) -> dict:
    return dict(
        ok=True,
        truncated=False,
        offset=0,
        node=dict(childCount=len(children)),
        children=list(children),
    )


class _FakeState:
    """경로별로 답하는 상태 포트.

    `position_pool_listed` 를 끄면 풀 목록에 Position 이 없어 툴이
    `preset_sheet_errors["position_pool"]` 을 채운다 — `pool_unreadable`
    갈래를 만드는 유일한 손잡이다.
    """

    def __init__(
        self,
        *,
        color_children: list | None = None,
        position_children: list | None = None,
        position_pool_listed: bool = True,
    ) -> None:
        self.color_children = list(color_children or [])
        self.position_children = list(position_children or [])
        self.position_pool_listed = position_pool_listed

    def query_state(self, path: str, offset: int = 0) -> dict:
        if path == "DataPool/PresetPools":
            pools = [_obj(COLOR_POOL_NO, "Color")]
            if self.position_pool_listed:
                pools.append(_obj(POSITION_POOL_NO, "Position"))
            return _reply(pools)
        if path == "DataPool/PresetPools/" + str(COLOR_POOL_NO):
            return _reply(self.color_children)
        if path == "DataPool/PresetPools/" + str(POSITION_POOL_NO):
            return _reply(self.position_children)
        if path == "DataPool/Groups":
            return _reply([_obj(4, "BACK")])
        return _reply([])


class _RecordingExec:
    def __init__(self) -> None:
        self.sent: list[str] = []

    def execute(self, command):
        self.sent.append(command)
        return type("R", (), dict(command=command, ok=True, detail="OK"))()


class _AcceptAll:
    def request_approval(self, request) -> bool:
        return True


def _cue_body(col: str = "", pos: str = "") -> bytes:
    header = ",".join(CANONICAL_CUE_COLUMNS)
    row = ",".join(["Q010", "BACK", "55", col, pos] + [""] * 10 + ["", ""])
    return (header + "\n" + row + "\n").encode("utf-8")


COL_SHEET_HEADER = "ID,Name,Value,Purpose\n"


def _col_sheet(rows: str) -> str:
    return base64.b64encode((COL_SHEET_HEADER + rows).encode("utf-8")).decode("ascii")


def _run(state: _FakeState, *, col: str = "", pos: str = "", col_sheet: str | None = None):
    registry = build_toolset(
        execution_port=_RecordingExec(),
        state_port=state,
        property_port=state,
        group_approval_port=_AcceptAll(),
    )
    arguments = dict(
        file_content_base64=base64.b64encode(_cue_body(col=col, pos=pos)).decode("ascii"),
        sequence_name="t225 Sugar",
        action="preview",
    )
    if col_sheet is not None:
        arguments["preset_col_content_base64"] = col_sheet
    execution = registry.dispatch(
        ToolCall(id="t225", name="import_lxseq_cues", arguments=arguments)
    )
    assert execution.result.is_error is False
    return json.loads(execution.result.content)


def _only(payload: dict) -> dict:
    refs = payload["unresolved_preset_refs"]
    assert len(refs) == 1, refs
    return refs[0]


class TestUnresolvedRefCauses:
    """네 갈래 — 각각이 다른 처방을 가리킨다."""

    def test_a_kind_with_no_sheet_supplied_says_so(self):
        """(c) 호출이 그 종류의 시트를 아예 안 실었다 — 인자를 고치면 된다."""
        payload = _run(_FakeState(), col="COL.02")
        row = _only(payload)
        assert row["ref"] == "COL.02"
        assert row["kind"] == "COL"
        assert row["cause"] == UNRESOLVED_SHEET_NOT_SUPPLIED
        assert row["expected_console_name"] is None

    def test_a_sheet_without_the_id_says_so(self):
        """(c') 시트는 실렸는데 그 ID 가 없다 — 시트를 고쳐야 한다."""
        payload = _run(
            _FakeState(),
            col="COL.02",
            col_sheet=_col_sheet("COL.01,골드 앰버,R255 G180 B60,기본\n"),
        )
        row = _only(payload)
        assert row["cause"] == UNRESOLVED_SHEET_LACKS_ID
        assert row["expected_console_name"] is None

    def test_a_defined_id_the_console_lacks_names_the_expected_label(self):
        """🔴 하중을 지는 팔 — (a)/(b) 를 사람이 갈라 볼 수 있게 만든다.

        시트는 ID 와 Name 을 둘 다 줬는데 콘솔 풀에 그 이름이 없다. 이 상태는
        **프리셋을 만들어야** 풀린다. `expected_console_name` 이 없으면
        다음 사람은 콘솔 풀을 손으로 떠서 「없는 것인지 이름이 다른 것인지」를
        다시 갈라야 한다 — t225 가 실제로 그렇게 했다.
        """
        payload = _run(
            _FakeState(color_children=[_obj(1, "골드 앰버 (=P1)")]),
            col="COL.02",
            col_sheet=_col_sheet(
                "COL.01,골드 앰버 (=P1),R255 G180 B60,기본\n"
                "COL.02,웜 화이트 (=P2),~3200K,인물 기본\n"
            ),
        )
        row = _only(payload)
        assert row["cause"] == UNRESOLVED_CONSOLE_LACKS_NAME
        assert row["expected_console_name"] == "웜 화이트 (=P2)"

    def test_a_position_ref_the_pool_lacks_is_console_lacks_name(self):
        """POS 는 시트에 Name 열이 없어 시트 갈래 둘이 정의역 밖이다(§10)."""
        payload = _run(_FakeState(), pos="POS.03")
        row = _only(payload)
        assert row["kind"] == "POS"
        assert row["cause"] == UNRESOLVED_CONSOLE_LACKS_NAME
        assert row["expected_console_name"] is None

    def test_an_unlisted_position_pool_is_pool_unreadable_not_missing_preset(self):
        """못 읽은 것을 「프리셋이 없다」로 접지 않는다 — 처방이 다르다."""
        payload = _run(_FakeState(position_pool_listed=False), pos="POS.03")
        row = _only(payload)
        assert row["cause"] == UNRESOLVED_POOL_UNREADABLE


class TestUnresolvedRefControls:
    """팔 2 — 기존 상태에서는 이 표가 무엇을 **안** 말하는가."""

    def test_a_resolved_ref_is_absent_from_the_table(self):
        payload = _run(
            _FakeState(position_children=[_obj(3, "POS03 밴드 라인 백 · 산출값")]),
            pos="POS.03",
        )
        assert payload["unresolved_preset_refs"] == []
        assert payload["refusal"] is None

    def test_a_blank_cell_is_tracking_not_an_unresolved_ref(self):
        """빈칸은 트래킹이다(§11.2 #1). 미해결로 세면 없는 결함이 생긴다."""
        payload = _run(_FakeState())
        assert payload["unresolved_preset_refs"] == []

    def test_the_table_does_not_change_the_plan(self):
        """순수하게 산출물 한 칸이다 — 보류·거절은 그대로다."""
        payload = _run(_FakeState(), col="COL.02")
        assert payload["refusal"] == "rows_held"
        assert payload["planned_cues"] == []
        assert "unresolved_preset" in payload["held"][0]["classes"]


def _cue_body_with_video_call(col: str) -> bytes:
    header = ",".join(CANONICAL_CUE_COLUMNS)
    row = ",".join(["Q010", "LED-W", "55", col, ""] + [""] * 10 + ["", ""])
    return (header + "\n" + row + "\n").encode("utf-8")


class TestVideoCallRowsAreNotOurRefs:
    """영상 콜 행은 콘솔에 안 나간다 — 그 행의 참조는 우리 미해결이 아니다.

    이 팔이 없으면 `is_video_call` 가드가 코퍼스에 안 걸려, 지워도 아무도
    모른다(규약 §3.5 — 초록은 「이 실행에서 빨강이 안 났다」일 뿐이다).
    """

    def test_a_video_call_rows_preset_ref_is_not_counted(self):
        registry = build_toolset(
            execution_port=_RecordingExec(),
            state_port=_FakeState(),
            property_port=_FakeState(),
            group_approval_port=_AcceptAll(),
        )
        body = _cue_body_with_video_call("COL.02")
        execution = registry.dispatch(
            ToolCall(
                id="t225-video",
                name="import_lxseq_cues",
                arguments=dict(
                    file_content_base64=base64.b64encode(body).decode("ascii"),
                    sequence_name="t225 Sugar",
                    action="preview",
                ),
            )
        )
        assert execution.result.is_error is False
        payload = json.loads(execution.result.content)
        assert payload["video_call_rows"] == 1
        assert payload["unresolved_preset_refs"] == []
