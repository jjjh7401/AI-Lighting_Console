"""t111 — 이름 **안**의 제어문자가 계획에 실렸다가 발사 직전에 거절된다.

t97(#155)이 세운 원칙은 「못 보내는 이름을 계획에 싣지 않는다 — 검증을 배정
전으로」였다. 그 원칙이 **따옴표에만** 걸렸다. `preset_label_refusal` 은 빈
라벨과 홑·겹따옴표만 보고, `strip` 은 앞뒤만 걷어내므로 이름 **안**의 개행·탭은
그대로 통과한다.

착수 전 실측(2026-08-26, 수정 전 트리):

    predicate  preset_label_refusal("쇼\\n하이") -> None   (보낼 수 있다고 답한다)
               preset_label_refusal("쇼\\t하이") -> None
    builder    preset_store_commands(1, 7, "쇼\\n하이")
                 -> ("Store Preset 1.7", "Label Preset 1.7 '쇼\\n하이'")
                    터지지 않는다 — 따옴표와 달리 빌더까지 통과한다
    CSV        탭은 맨몸 필드로, 개행은 따옴표 친 필드로 파서를 통과한다
    preview    planned 에 실린다 · held []
    apply      기형 명령이 approval 요청까지 올라가 승인을 받는다

즉 따옴표보다 **더 멀리** 간다. 따옴표는 빌더에서 터졌지만(t97) 제어문자는
빌더·계획·승인을 전부 통과한다.

2차 방어는 살아 있다 — 실측:

    validate("Label Preset 1.2 '탭\\t이름'") -> ok=False, control character
    validate("Label Preset 1.2 '탭\\n이름'") -> ok=False, must be a single line
    validate("Label Preset 1.2 '쓰지'")      -> ok=True          (양성 대조군)

그래서 무대에 기형 명령이 닿지는 않는다. 고칠 값은 **계획-발사 불일치**다:
사용자는 「보낼 수 있다」고 본 이름을 승인했는데 그 런이 통째로 멈춘다.

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
from server.safety.grammar import validate
from server.spatial.pointing import SpatialPointingError

_CLEAN = "쓰지"
_TAB = "탭\t이름"
_NEWLINE = "개행\n이름"

# 이름 안에 하나씩 든 제어문자. 개행·탭이 카드가 지목한 둘이고, 나머지는
# 같은 술어가 같은 이유로 놓치는 형제들이다 — 전부 strip 이 안 걷어낸다.
_C0_NAMES = (
    ("newline", _NEWLINE),
    ("tab", _TAB),
    ("carriage-return", "복귀" + chr(0x0D) + "이름"),
    ("nul", "널" + chr(0x00) + "이름"),
    ("escape", "이스케이프" + chr(0x1B) + "이름"),
)

# 이 셋은 C0 밖이라 안전 문법층의 ord(ch) < 32 검사에 **안 걸린다** — 실측(t111).
# 개행·탭과 달리 2차 방어가 없어서 이 술어가 유일한 방어다. 문법층을 넓히는
# 것은 이 카드 범위가 아니다(별도 자리 · 후속 카드).
_BEYOND_C0_NAMES = (
    ("delete", "삭제" + chr(0x7F) + "이름"),
    ("next-line", "다음줄" + chr(0x85) + "이름"),
    ("line-separator", "줄분리" + chr(0x2028) + "이름"),
)

_CONTROL_NAMES = _C0_NAMES + _BEYOND_C0_NAMES

# 양성 대조군 — 「무조건 거부」와 구분하는 자리. 안쪽 공백은 제어문자가 아니고
# 문형도 안 깨므로 통과해야 한다. 이게 없으면 술어를 「글자만 허용」으로 넓혀도
# 검사가 초록이다.
_SENDABLE_NAMES = (
    ("plain", _CLEAN),
    ("inner-space", "안 쪽 공백"),
    ("punctuation", "R1-DIM.50"),
    ("outer-whitespace", "\n\t 쓰지 \t\n"),
)


def _csv(*names: str) -> str:
    # 이름을 따옴표 친 CSV 필드로 싣는다 — 개행이 든 이름은 맨몸 필드로는
    # 행이 쪼개져 파서에 닿지 않는다(탭은 맨몸으로도 닿는다, 실측).
    rows = "".join(
        "DIM.R" + str(i) + ',"' + name + '",' + str(10 * (i + 1)) + "%,t111\n"
        for i, name in enumerate(names)
    )
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
            id="t111",
            name="import_lxseq_presets",
            arguments=dict(
                file_content_base64=base64.b64encode(csv_text.encode("utf-8")).decode("ascii"),
                action=action,
            ),
        )
    )
    return json.loads(execution.result.content), port, approval


class TestTheSecondDefenceReallyRefusesThese:
    """이 카드가 고치는 것이 무대 위험이 아님을 먼저 못박는다.

    이 검사가 빨개지면 축이 바뀐 것이다 — 그때는 계획-발사 불일치가 아니라
    기형 명령이 콘솔에 닿는 문제이고, 우선순위가 달라진다.
    """

    def test_the_grammar_layer_refuses_a_control_char_command(self):
        for tag, name in _C0_NAMES:
            line = "Label Preset 1.2 '" + name + "'"
            assert validate(line).ok is False, tag

    def test_the_grammar_layer_lets_a_clean_command_through(self):
        """양성 대조군 — 없으면 「문법기가 전부 거부」와 구분되지 않는다."""
        assert validate("Label Preset 1.2 '" + _CLEAN + "'").ok is True


class TestThePredicateNamesControlChars:
    """술어 하나가 판정한다 — 사본을 만들면 판정기와 발사기가 갈라진다(t97)."""

    def test_the_predicate_refuses_an_inner_control_char(self):
        for tag, name in _CONTROL_NAMES:
            assert preset_label_refusal(name) is not None, tag

    def test_the_builder_refuses_exactly_what_the_predicate_names(self):
        """판정기와 발사기가 같은 답을 내야 한다 — 갈라지면 t97 이 되풀이된다."""
        for tag, name in _CONTROL_NAMES:
            try:
                preset_store_commands(1, 1, name)
            except SpatialPointingError:
                continue
            raise AssertionError("builder accepted " + tag)

    def test_a_sendable_name_still_goes_through(self):
        """양성 대조군 — 안쪽 공백·문장부호·바깥 공백은 문형을 안 깬다."""
        for tag, name in _SENDABLE_NAMES:
            assert preset_label_refusal(name) is None, tag
            assert preset_store_commands(1, 1, name)[0] == "Store Preset 1.1"

    def test_outer_whitespace_is_stripped_not_refused(self):
        """판별력 있는 자리 — 「제어문자를 담고 있으면 거부」로 넓히면 빨개진다.

        strip 이 앞뒤를 걷어낸 뒤에 판정하므로 바깥 개행·탭은 이름의 일부가
        아니다. 판정을 strip 전 문자열로 옮기면 이 검사가 죽는다.
        """
        assert preset_label_refusal("\n\t 쓰지 \t\n") is None
        assert preset_store_commands(1, 1, "\n\t 쓰지 \t\n") == (
            "Store Preset 1.1",
            "Label Preset 1.1 '" + _CLEAN + "'",
        )

    def test_the_refusal_says_which_character(self):
        """문면이 거짓말을 하면 사용자가 시트에서 그 글자를 못 찾는다."""
        reason = preset_label_refusal(_TAB)
        assert reason is not None
        assert "제어문자" in reason, reason

    def test_the_builder_error_names_the_real_reason(self):
        """수정 전 문면은 empty or carries a quote 였다 — 제어문자엔 거짓이다."""
        with pytest.raises(SpatialPointingError) as caught:
            preset_store_commands(1, 1, _TAB)
        assert "quote" not in str(caught.value), str(caught.value)


class TestTheMapperHoldsWhatItCannotSend:
    def test_a_control_char_name_is_held_not_planned(self):
        result = map_presets(_records(_CLEAN, _TAB), pool_section=_pool())
        assert [p.name for p in result.planned] == [_CLEAN]
        assert [h.preset_id for h in result.held] == ["DIM.R1"]
        assert NAME_UNSENDABLE in result.held[0].hold_classes

    def test_a_newline_name_is_held_too(self):
        result = map_presets(_records(_NEWLINE), pool_section=_pool())
        assert result.planned == ()
        assert NAME_UNSENDABLE in result.held[0].hold_classes

    def test_holding_happens_before_slot_assignment(self):
        """배정 후에 거르면 쓰지도 않을 슬롯을 예약해 없는 부족분이 생긴다."""
        result = map_presets(_records(_TAB, _CLEAN), pool_section=_pool())
        assert [(p.name, p.slot) for p in result.planned] == [(_CLEAN, 1)]

    def test_the_three_baskets_still_sum_to_what_was_read(self):
        """REQ-IDEM-004 — 합이 깨지면 세 번째 바구니를 안 읽는 소비자가 생긴다."""
        names = (_CLEAN, _TAB, _NEWLINE)
        result = map_presets(_records(*names), pool_section=_pool())
        total = len(result.planned) + len(result.held) + len(result.already_present)
        assert total == len(names)


class TestTheRunNoLongerStopsOnOneBadName:
    def test_preview_stops_calling_it_sendable(self):
        """사용자가 승인하는 화면이 여기다 — 여기서 거짓말하면 승인이 무의미하다."""
        payload, port, _approval = _dispatch(_csv(_CLEAN, _TAB), action="preview")
        assert [p["name"] for p in payload["planned"]] == [_CLEAN]
        assert payload["held_by_class"].get(NAME_UNSENDABLE) == 1
        assert port.executed == []

    def test_apply_fires_the_clean_row_and_holds_the_other(self):
        """수정 전에는 기형 명령이 승인 요청까지 올라갔다(실측)."""
        _payload, port, approval = _dispatch(_csv(_CLEAN, _TAB), action="apply")
        assert [c for c in port.executed if c.startswith("Store Preset ")] == ["Store Preset 1.1"]
        assert not any("\t" in c for c in port.executed), port.executed
        assert not any("\t" in c for asked in approval.asked for c in asked), approval.asked

    def test_a_clean_sheet_still_fires(self):
        """양성 대조군 — 없으면 위 검사가 「툴이 그냥 고장 남」과 구분되지 않는다."""
        _payload, port, approval = _dispatch(_csv(_CLEAN), action="apply")
        assert approval.asked
        assert any(c.startswith("Store Preset ") for c in port.executed), port.executed
