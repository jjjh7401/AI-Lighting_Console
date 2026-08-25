"""t97 — 이름에 따옴표가 있으면 매퍼가 계획을 낸 뒤에 터진다.

t87 이 발견하고 안 고쳤다. 결함 형태는 **검증 순서**다: `preset_store_commands`
가 이름의 따옴표를 거부하는데, 매퍼는 그보다 **먼저** 계획을 낸다. 사용자는
`preview` 에서 그 이름을 `planned`(보낼 수 있음)로 보고 승인한 뒤에 예외를 본다.

착수 전 실측(2026-08-25, 수정 전 트리, `uv run python` 즉석 재현):

    preview  → planned 에 둘 다 · held []
    apply    → SpatialPointingError 가 `registry.dispatch` **밖으로** 튐
               승인 통로 asked [] · 콘솔 executed []

즉 **부분 실행은 아니다** — 명령을 전부 조립한 뒤에 승인·발사로 가므로 콘솔
발화는 0줄이다. 카드 본문이 걱정한 "절반만 찬 콘솔" 은 이 경로에선 안 생긴다.
대신 사용자는 계획·보류가 담긴 리포트째로 잃는다.

고치는 자리는 매퍼의 **배정 전**이다 — 배정 후에 거르면 쓰지도 않을 슬롯을
예약해 없는 부족분이 생긴다(t87 이 `name_taken` 에서 같은 이유로 같은 자리를
골랐다).

순수 검증이다. 콘솔·네트워크 접촉 0.
"""

from __future__ import annotations

import base64
import json

import pytest

from server.llm.types import ToolCall
from server.lxseq.preset_mapper import NAME_UNSENDABLE, map_presets
from server.lxseq.preset_parser import parse_preset_csv
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import build_toolset
from server.presets.store import preset_label_refusal, preset_store_commands
from server.spatial.pointing import SpatialPointingError

_CLEAN = "쓰지"
_QUOTED = "쇼'하이"
_DQUOTED = '쇼"하이'


def _csv(*names: str) -> str:
    rows = "".join(f"DIM.R{i},{name},{10 * (i + 1)}%,t97\n" for i, name in enumerate(names))
    return "ID,Name,Level,Purpose\n" + rows


def _records(*names: str):
    return parse_preset_csv(_csv(*names)).records


def _pool(occupied=()):
    return dict(objects=[dict(no=n) for n in occupied], truncated=False)


class _RecordingPort:
    """발화를 기록만 한다 — 죽이면 「발화했다」와 「막혔다」가 안 갈린다."""

    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, command: str) -> ExecutionResult:
        self.executed.append(command)
        return ExecutionResult(ok=True, detail="OK")

    def query_state(self, path: str) -> dict:
        if path.endswith("PresetPools"):
            return dict(children=[dict(i=1, name="Dimmer")], node=dict(childCount=1))
        return dict(children=[], node=dict(childCount=0), truncated=False)

    def query_property(self, path: str, name: str) -> dict:
        return dict(ok=False, error="not readable")


class _Approval:
    def __init__(self) -> None:
        self.asked: list[tuple[str, ...]] = []

    def request_approval(self, request) -> bool:
        self.asked.append(tuple(item.command for item in request.items))
        return True


def _dispatch(csv_text: str, *, action: str):
    port = _RecordingPort()
    approval = _Approval()
    registry = build_toolset(
        execution_port=port,
        state_port=port,
        property_port=port,
        group_approval_port=approval,
    )
    execution = registry.dispatch(
        ToolCall(
            id="t97",
            name="import_lxseq_presets",
            arguments=dict(
                file_content_base64=base64.b64encode(csv_text.encode("utf-8")).decode("ascii"),
                action=action,
            ),
        )
    )
    return json.loads(execution.result.content), port, approval


class TestThePredicateHasOneHome:
    """술어를 매퍼에 **다시 적지 않는다**.

    `store.py` 가 스스로 "문형을 아는 유일한 일반형 자리 — 새 자리에 같은 문형을
    적지 마라" 고 못박았다. 사본을 만들면 판정기와 발사기가 갈라져, 한쪽만 바뀐
    날에 매퍼가 「보낼 수 있다」고 답한 이름에서 빌더가 터진다.
    """

    def test_the_builder_refuses_exactly_what_the_predicate_names(self):
        for name in (_QUOTED, _DQUOTED, "", "   "):
            assert preset_label_refusal(name) is not None, name
            with pytest.raises(SpatialPointingError):
                preset_store_commands(1, 1, name)

    def test_the_predicate_lets_a_sendable_name_through(self):
        """양성 대조군 — 없으면 「무조건 거부」와 구분되지 않는다."""
        assert preset_label_refusal(_CLEAN) is None
        assert preset_store_commands(1, 1, _CLEAN) == (
            "Store Preset 1.1",
            f"Label Preset 1.1 '{_CLEAN}'",
        )


class TestTheMapperHoldsWhatItCannotSend:
    def test_a_quoted_name_is_held_not_planned(self):
        result = map_presets(_records(_CLEAN, _QUOTED), pool_section=_pool())
        assert [p.name for p in result.planned] == [_CLEAN]
        assert [h.preset_id for h in result.held] == ["DIM.R1"]
        assert NAME_UNSENDABLE in result.held[0].hold_classes

    def test_a_double_quoted_name_is_held_too(self):
        """빌더는 홑·겹 둘 다 거부한다. 하나만 막으면 나머지가 그대로 터진다."""
        result = map_presets(_records(_DQUOTED), pool_section=_pool())
        assert result.planned == ()
        assert NAME_UNSENDABLE in result.held[0].hold_classes

    def test_the_hold_says_why_in_prose(self):
        result = map_presets(_records(_QUOTED), pool_section=_pool())
        detail = " ".join(result.held[0].details)
        assert _QUOTED in detail, detail
        assert "따옴표" in detail, detail

    def test_holding_happens_before_slot_assignment(self):
        """배정 **후**에 거르면 쓰지도 않을 슬롯을 예약해 없는 부족분이 생긴다.

        보낼 수 없는 이름이 앞에 오는데도 뒤의 성한 이름이 슬롯 1을 받아야 한다.
        슬롯 2를 받으면 배정이 먼저 돌았다는 뜻이다.
        """
        result = map_presets(_records(_QUOTED, _CLEAN), pool_section=_pool())
        assert [(p.name, p.slot) for p in result.planned] == [(_CLEAN, 1)]

    def test_the_three_baskets_still_sum_to_what_was_read(self):
        """REQ-IDEM-004 — 합이 깨지면 세 번째 바구니를 안 읽는 소비자가 생긴다."""
        names = (_CLEAN, _QUOTED, _DQUOTED)
        result = map_presets(_records(*names), pool_section=_pool())
        total = len(result.planned) + len(result.held) + len(result.already_present)
        assert total == len(names)


class TestTheToolNoLongerExplodesAfterPlanning:
    def test_apply_survives_a_quoted_name(self):
        """수정 전에는 여기서 `SpatialPointingError` 가 dispatch 밖으로 튀었다."""
        payload, port, _approval = _dispatch(_csv(_CLEAN, _QUOTED), action="apply")
        assert payload["approval"] == "granted"
        assert [c for c in port.executed if c.startswith("Store Preset ")] == ["Store Preset 1.1"]
        assert not any(_QUOTED in c for c in port.executed), port.executed

    def test_preview_stops_calling_it_sendable(self):
        """사용자가 승인하는 화면이 여기다 — 여기서 거짓말하면 승인이 무의미하다."""
        payload, port, _approval = _dispatch(_csv(_CLEAN, _QUOTED), action="preview")
        assert [p["name"] for p in payload["planned"]] == [_CLEAN]
        assert payload["held_by_class"].get(NAME_UNSENDABLE) == 1
        assert port.executed == []

    def test_a_clean_sheet_still_fires(self):
        """양성 대조군 — 없으면 위 검사가 「툴이 그냥 고장 남」과 구분되지 않는다."""
        _payload, port, approval = _dispatch(_csv(_CLEAN), action="apply")
        assert approval.asked
        assert any(c.startswith("Store Preset ") for c in port.executed), port.executed
