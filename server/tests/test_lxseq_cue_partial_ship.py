"""t228 — 부분 출하는 **큐 단위**이고, 그 사실이 산출물에 남는다.

## 재현 우선 — 이 카드가 존재한 이유

t207 이 「전부 아니면 아무것도」를 **배치** 층에 놓았다. 그래서 시트 어디든 참조
하나가 안 풀리면 성한 큐 전부가 멈췄다. t225 실측: 여덟 큐 중 전 행이 해결된
것이 다섯인데 툴이 계획한 큐는 **0개**였고, 프리셋을 다 채워 열여섯이 해결돼도
`FX.04`(Hue)·`FX.06`(Shutter) 두 종 때문에 여전히 0개였다.

감독 판정(2026-09-01 2차)은 **입도**만 옮긴다. 큐 **안**에서는 그대로 전부
아니면 아무것도다 — 한 그룹이 빠진 큐는 MA3 트래킹 때문에 큐 리스트에서 정상으로
보이고 발사할 때에야 어긋난다. 큐 **사이**는 서로 독립이다.

## 이 파일이 지키는 것 — 값이 아니라 **기록**

부분 출하는 콘솔이 시트의 일부만 든 상태를 만든다. 되읽기 채널은 큐 내용을
안 주므로(AC-LXSEQ4-013) 콘솔을 되읽어 「무엇이 안 올라갔나」를 알 수단이 없다 —
**툴 산출물이 유일한 기록이다.** 그래서 여기서 재는 것은 계획 수만이 아니라
`cues_held` 가 어느 큐를 · 몇 행을 · 왜 세웠는지까지 말하는가다.

어휘는 t225 의 `unresolved_preset_refs`(ref/kind/cause/expected_console_name)를
그대로 쓴다 — 병렬 어휘를 만들면 같은 실패가 자리마다 다른 이름으로 불린다.

콘솔 접촉 0 — 상태 포트는 경로별로 답하는 가짜다.
"""

from __future__ import annotations

import base64
import json

from server.llm.types import ToolCall
from server.lxseq.cue_mapper import UNRESOLVED_CONSOLE_LACKS_NAME
from server.lxseq.cue_parser import CANONICAL_CUE_COLUMNS
from server.orchestrator.tools import build_toolset

COLOR_POOL_NO = 4


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
    """경로별로 답하는 상태 포트. Color 풀에 COL.01 의 이름만 있다."""

    def __init__(self, *, sequence_children: list | None = None) -> None:
        self.sequence_children = list(sequence_children or [])

    def query_state(self, path: str, offset: int = 0) -> dict:
        if path == "DataPool/PresetPools":
            return _reply([_obj(COLOR_POOL_NO, "Color")])
        if path == "DataPool/PresetPools/" + str(COLOR_POOL_NO):
            return _reply([_obj(1, "따뜻한 앰버")])
        if path == "DataPool/Groups":
            return _reply([_obj(4, "BACK")])
        if path == "DataPool/Sequences":
            return _reply(self.sequence_children)
        return _reply([])


class _RecordingExec:
    def __init__(self) -> None:
        self.sent: list[str] = []

    def execute(self, command):
        self.sent.append(command)
        return type("R", (), dict(command=command, ok=True, detail="OK"))()


class _AcceptAll:
    def __init__(self) -> None:
        self.asked: list[tuple[str, ...]] = []
        self.reasons: list[str] = []

    def request_approval(self, request) -> bool:
        self.asked.append(tuple(item.command for item in request.items))
        for item in request.items:
            self.reasons.extend(item.risk_reasons)
        return True


COL_SHEET = "ID,Name,Value,Purpose\nCOL.01,따뜻한 앰버,#FFAA55,키\nCOL.02,웜 화이트,~3200K,백\n"


def _sheet(*rows: tuple[str, str]) -> bytes:
    """(Q#, COL 참조) 쌍으로 CUE-EX 한 장을 짓는다. 그룹은 BACK 하나다."""
    header = ",".join(CANONICAL_CUE_COLUMNS)
    body = "\n".join(
        ",".join([cue, "BACK", "55", col, ""] + [""] * 10 + ["", ""]) for cue, col in rows
    )
    return (header + "\n" + body + "\n").encode("utf-8")


def _run(rows, *, action: str = "preview", state: _FakeState | None = None):
    exec_port = _RecordingExec()
    approval = _AcceptAll()
    fake = state or _FakeState()
    registry = build_toolset(
        execution_port=exec_port,
        state_port=fake,
        property_port=fake,
        group_approval_port=approval,
    )
    execution = registry.dispatch(
        ToolCall(
            id="t228",
            name="import_lxseq_cues",
            arguments=dict(
                file_content_base64=base64.b64encode(_sheet(*rows)).decode("ascii"),
                preset_col_content_base64=base64.b64encode(COL_SHEET.encode("utf-8")).decode(
                    "ascii"
                ),
                sequence_name="t228 Sugar",
                action=action,
            ),
        )
    )
    assert execution.result.is_error is False
    return json.loads(execution.result.content), exec_port, approval


MIXED = (("Q010", "COL.01"), ("Q020", "COL.02"))


class TestPartialShip:
    """재현 — 성한 큐가 나가고 보류된 큐만 빠진다."""

    def test_a_held_cue_does_not_stop_the_healthy_one(self):
        """고치기 전: `refusal=rows_held` · `planned_cues=[]`. 두 큐 다 안 갔다."""
        payload, _exec, _appr = _run(MIXED)
        assert payload["refusal"] is None
        assert [c["cue_no"] for c in payload["planned_cues"]] == ["Q010"]
        assert payload["partial_ship"] is True

    def test_the_output_names_the_held_cue_its_rows_and_its_refs(self):
        """콘솔 상태를 되읽을 수 없으므로 이 칸이 유일한 기록이다."""
        payload, _exec, _appr = _run(MIXED)
        held = payload["cues_held"]
        assert len(held) == 1
        assert held[0]["cue_no"] == "Q020"
        assert held[0]["held_rows"] == 1
        assert held[0]["withheld_rows"] == 0
        assert held[0]["preset_refs"] == ["COL.02"]
        assert payload["cues_held_count"] == 1

    def test_the_held_refs_join_to_the_cause_table(self):
        """t225 의 어휘를 그대로 쓴다 -- `ref` 로 조인하면 원인과 기대 이름이 나온다."""
        payload, _exec, _appr = _run(MIXED)
        by_ref = dict((row["ref"], row) for row in payload["unresolved_preset_refs"])
        for ref in payload["cues_held"][0]["preset_refs"]:
            assert ref in by_ref, ref
        assert by_ref["COL.02"]["cause"] == UNRESOLVED_CONSOLE_LACKS_NAME
        assert by_ref["COL.02"]["expected_console_name"] == "웜 화이트"

    def test_the_notice_says_the_console_holds_only_part_of_the_sheet(self):
        payload, _exec, _appr = _run(MIXED)
        notice = payload["notice_partial_ship"]
        assert "일부만" in notice
        assert "AC-LXSEQ4-013" in notice

    def test_apply_sends_the_healthy_cue_and_not_the_held_one(self):
        payload, exec_port, approval = _run(MIXED, action="apply")
        assert payload["approval"] == "granted"
        assert any("Store Cue 10 " in command for command in exec_port.sent)
        assert not any("Store Cue 20 " in command for command in exec_port.sent)
        # 승인 화면이 부분 출하임을 말한다 -- 사람이 모르고 승인하지 않게
        assert any("부분 출하" in reason for reason in approval.reasons)


class TestPartialShipControls:
    """팔 2 — 기존 상태에서는 이 계약이 무엇을 **안** 말하는가."""

    def test_every_cue_healthy_is_not_a_partial_ship(self):
        payload, _exec, _appr = _run((("Q010", "COL.01"), ("Q020", "COL.01")))
        assert payload["refusal"] is None
        assert payload["cues_held"] == []
        assert payload["partial_ship"] is False
        assert "notice_partial_ship" not in payload

    def test_every_cue_held_is_a_batch_refusal_not_a_partial_ship(self):
        """입도를 옮긴 것이지 거절을 없앤 것이 아니다."""
        payload, exec_port, _appr = _run((("Q010", "COL.02"), ("Q020", "COL.02")), action="apply")
        assert payload["refusal"] == "rows_held"
        assert payload["planned_cues"] == []
        assert payload["partial_ship"] is False
        assert [c["cue_no"] for c in payload["cues_held"]] == ["Q010", "Q020"]
        assert exec_port.sent == []


class TestRerunAfterAPartialShip:
    """부분 출하 뒤 같은 시트를 다시 부르는 자리 -- 멱등성이 여기서 깨지면
    재시도가 콘솔에 중복을 얹는다."""

    def test_the_landed_cue_is_not_replanned(self):
        # 1회차가 만든 시퀀스가 슬롯 1 에 있고 그 안에 Q010(cueNo=10)이 있다.
        state = _FakeState(sequence_children=[_obj(1, "t228 Sugar")])
        payload, exec_port, _appr = _run(MIXED, action="apply", state=state)
        assert payload["already_present"] is True
        assert payload["cues_already_present"] == []
        # 이 가짜는 큐 목록을 안 답한다(응답기 1.5.0 미만과 같은 상태) --
        # 그래서 큐 층 판단을 못 하고 Q010 을 다시 계획한다. 그 갈래도 부분
        # 출하 기록은 그대로다.
        assert [c["cue_no"] for c in payload["planned_cues"]] == ["Q010"]
        assert [c["cue_no"] for c in payload["cues_held"]] == ["Q020"]
        # 시퀀스는 이미 있으므로 다시 만들지 않는다
        assert not any("Store Sequence" in command for command in exec_port.sent)
