"""카드 t599(REQ-LDBEAT-015(i-3)/(h)) — 「＋ 새 프리셋 만들기」의 "위치" 필드.

t589이 "위치"를 base 풀(효과 번호대 없음)이라는 이유로 거절했다
(`server.web.session.ChatSession._NEW_PRESET_NO_BAND_FIELDS`). 이 카드는
그 거절을 풀고 위치가 되게 한다 — 목표 좌표(x·y·z, 미터, `server/spatial/
pointing.py` 틀)와 영문 콘솔 이름을 받아, 콘솔이 실제로 쥔 첫 빈 번호를
`first_free_base_position_number`(새 순수 함수, `server.design.beat_grid_
presets`)로 고르고 **일반 편집과 같은 길**(`apply_beat_grid_edit`)로
씌운다 — 번호는 다른 신규 번호와 똑같이 「⇪ 콘솔에 반영」 승인 전까지
승인 대기로 남고, 목표 좌표는 카드 t592의 `record_position_preset_target`
자리에 남아 반영 때 `plan_position_preset_creation`이 조준 명령으로
환산한다. dimmer_preset·color는 그대로 거절한다(회귀 없음).

세 층: ① 순수 번호 배정 함수 ② 프로토콜 파서(aim 모양 검증) ③ 서버
핸들러(세션 종단간). 콘솔 접촉: 0건(쓰기) — `FakeConsole.executed == []`로
직접 잰다.
"""

from __future__ import annotations

import json
import math

import pytest

from server.design.beat_grid_position_presets import position_preset_target
from server.design.beat_grid_presets import (
    app_preset_description,
    app_preset_label,
    first_free_base_position_number,
)
from server.web.messages import ProtocolError, parse_client_message
from server.web.session import SongTimelineStore

from .test_new_preset_dialog_t589 import (
    _cue_of,
    _new_session,
    _pool_children_payload,
    _pool_list_payload,
    _state_tree,
    _timeline,
)

PROTOCOL_VERSION = 1


# == ① 순수 번호 배정 함수 ====================================================


class TestFirstFreeBasePositionNumber:
    def test_capture_harness_fake_pool_example(self) -> None:
        # 카드 본문 예시 — children {41:'LA Center', 61:None}, 효과 밴드
        # 2.61~2.68 → 2.42(격자가 참조하지 않으면).
        policy = {
            "confirmed": False,
            "pools": {"position_effect": {"start": "2.61", "end": "2.68"}},
        }
        grid = {"tracks": []}
        console_children = (2, {41: "LA Center", 61: None})
        preset_no, reason = first_free_base_position_number(
            policy=policy, grid=grid, console_children=console_children
        )
        assert reason is None
        assert preset_no == "2.42"

    def test_band_slots_are_skipped_even_when_occupied(self) -> None:
        policy = {
            "confirmed": False,
            "pools": {"position_effect": {"start": "2.61", "end": "2.68"}},
        }
        grid = {"tracks": []}
        # 밴드 안 슬롯까지 전부 채워도(occupied 최댓값이 68이어도) base 쪽
        # 시작은 밴드 밖 occupied(41) 기준이어야 한다 — 밴드는 세지 않는다.
        console_children = (2, {41: "LA Center", **{slot: "X" for slot in range(61, 69)}})
        preset_no, reason = first_free_base_position_number(
            policy=policy, grid=grid, console_children=console_children
        )
        assert reason is None
        assert preset_no == "2.42"

    def test_unnamed_occupied_slot_is_still_skipped(self) -> None:
        # paged_pool_children 은 이름 없는 프리셋을 {slot: None} 으로 돌려준다
        # — 키가 있으면 그 번호는 콘솔에 있다(이름 유무와 무관).
        policy = {"confirmed": False, "pools": {}}
        grid = {"tracks": []}
        console_children = (2, {1: "Named", 2: None})
        preset_no, reason = first_free_base_position_number(
            policy=policy, grid=grid, console_children=console_children
        )
        assert reason is None
        assert preset_no == "2.3"

    def test_grid_referenced_number_is_skipped(self) -> None:
        policy = {"confirmed": False, "pools": {}}
        grid = {
            "tracks": [
                {"group_name": "BACK", "cues": [{"bar": 1, "position_preset_no": "2.1"}]},
            ]
        }
        console_children = (2, {})
        preset_no, reason = first_free_base_position_number(
            policy=policy, grid=grid, console_children=console_children
        )
        assert reason is None
        assert preset_no == "2.2"

    def test_no_base_slots_at_all_starts_at_dot_one(self) -> None:
        policy = {
            "confirmed": False,
            "pools": {"position_effect": {"start": "2.61", "end": "2.68"}},
        }
        grid = {"tracks": []}
        console_children = (2, {})
        preset_no, reason = first_free_base_position_number(
            policy=policy, grid=grid, console_children=console_children
        )
        assert reason is None
        assert preset_no == "2.1"

    def test_unread_pool_is_rejected_not_guessed(self) -> None:
        policy = {"confirmed": False, "pools": {}}
        grid = {"tracks": []}
        preset_no, reason = first_free_base_position_number(
            policy=policy, grid=grid, console_children=None
        )
        assert preset_no is None
        assert reason is not None
        assert "콘솔" in reason

    def test_pool_number_comes_from_the_console_read_not_a_literal_two(self) -> None:
        policy = {"confirmed": False, "pools": {}}
        grid = {"tracks": []}
        console_children = (7, {})
        preset_no, reason = first_free_base_position_number(
            policy=policy, grid=grid, console_children=console_children
        )
        assert reason is None
        assert preset_no == "7.1"


# == ② 프로토콜 파서 =========================================================


class TestParseClientMessageAim:
    def _valid_payload(self, **overrides: object) -> dict:
        payload = {
            "v": PROTOCOL_VERSION,
            "type": "beat_grid_new_preset",
            "bar": 1,
            "target": "BACK",
            "field": "position",
            "label": "LA Center",
            "description": "스테이지 중앙",
            "aim": {"x": 0.0, "y": 1.5, "z": 2.0},
        }
        payload.update(overrides)
        return payload

    def _parse(self, payload: dict) -> dict:
        return parse_client_message(json.dumps(payload))

    def test_position_with_valid_aim_parses_and_carries_aim(self) -> None:
        parsed = self._parse(self._valid_payload())
        assert parsed["field"] == "position"
        assert parsed["aim"] == {"x": 0.0, "y": 1.5, "z": 2.0}

    def test_position_without_aim_is_rejected(self) -> None:
        payload = self._valid_payload()
        del payload["aim"]
        with pytest.raises(ProtocolError):
            self._parse(payload)

    @pytest.mark.parametrize("axis", ["x", "y", "z"])
    def test_position_with_missing_axis_is_rejected(self, axis) -> None:
        payload = self._valid_payload()
        del payload["aim"][axis]
        with pytest.raises(ProtocolError):
            self._parse(payload)

    @pytest.mark.parametrize("bad", ["1", True, None, [1]])
    def test_position_with_non_numeric_axis_is_rejected(self, bad) -> None:
        payload = self._valid_payload()
        payload["aim"]["x"] = bad
        with pytest.raises(ProtocolError):
            self._parse(payload)

    @pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
    def test_position_with_non_finite_axis_is_rejected(self, bad) -> None:
        payload = self._valid_payload()
        payload["aim"]["z"] = bad
        with pytest.raises(ProtocolError):
            self._parse(payload)

    @pytest.mark.parametrize("field", ["dimmer_preset", "dimmer_effect", "color", "effect"])
    def test_aim_present_on_a_non_position_field_is_rejected(self, field) -> None:
        payload = self._valid_payload(field=field)
        with pytest.raises(ProtocolError):
            self._parse(payload)

    def test_non_position_fields_without_aim_still_parse(self) -> None:
        payload = self._valid_payload(field="effect")
        del payload["aim"]
        # 카드 t603 — "effect"는 효과 레시피가 필수다(이 시험은 aim 이 없어도 되는지만 본다).
        payload["fx"] = {"fx_id": "sweep-soft-wide", "period_unit": "beat", "period_value": 2}
        parsed = self._parse(payload)
        assert parsed["field"] == "effect"
        assert "aim" not in parsed


# == ③ 서버 핸들러(세션 종단간) ===============================================


def _position_state_tree(*, pool_no: int = 2, children: dict | None = None) -> dict:
    return _state_tree(
        **{
            "DataPool/PresetPools": _pool_list_payload({"Position": pool_no}),
            f"DataPool/PresetPools/{pool_no}": _pool_children_payload(children or {}),
        }
    )


class TestBeatGridNewPresetPositionField:
    def test_position_is_no_longer_rejected_as_a_no_band_field(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, _approval, _audit = _new_session(
            tmp_path, store=store, state_tree=_position_state_tree()
        )
        event = session.beat_grid_new_preset(
            1, "BACK", "position", "LA Center", "스테이지 중앙", {"x": 0.0, "y": 1.0, "z": 2.0}
        )
        assert "번호대를 지어내지 않습니다" not in event["text"], event["text"]
        assert "거절" not in event.get("summary", ""), event["text"]
        assert console.executed == []  # 읽기만 — 쓰기 0건

    def test_assigns_the_console_empty_slot_outside_the_effect_band(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, _approval, _audit = _new_session(
            tmp_path, store=store, state_tree=_position_state_tree(children={41: "LA Center"})
        )
        event = session.beat_grid_new_preset(
            1, "BACK", "position", "New Center", "새 중앙", {"x": 0.0, "y": 1.0, "z": 2.0}
        )
        assert "2.42" in event["text"], event["text"]
        cue = _cue_of(store.latest["beat_grid"], "BACK", 1)
        assert cue["position_preset_no"] == "2.42"
        assert console.executed == []

    def test_label_description_and_target_are_all_recorded(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, _console, _approval, _audit = _new_session(
            tmp_path, store=store, state_tree=_position_state_tree()
        )
        session.beat_grid_new_preset(
            1, "BACK", "position", "New Center", "새 중앙", {"x": 0.5, "y": -1.0, "z": 2.5}
        )
        grid = store.latest["beat_grid"]
        assert app_preset_label(grid, "2.1") == "New Center"
        assert app_preset_description(grid, "2.1") == "새 중앙"
        assert position_preset_target(grid, "2.1") == (0.5, -1.0, 2.5)

    def test_missing_aim_is_rejected_without_console_contact(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, _approval, _audit = _new_session(
            tmp_path, store=store, state_tree=_position_state_tree()
        )
        event = session.beat_grid_new_preset(1, "BACK", "position", "LA Center", "스테이지 중앙")
        assert "목표 좌표" in event["text"]
        assert console.executed == []

    def test_non_finite_aim_axis_is_rejected(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, _approval, _audit = _new_session(
            tmp_path, store=store, state_tree=_position_state_tree()
        )
        event = session.beat_grid_new_preset(
            1, "BACK", "position", "LA Center", "스테이지 중앙", {"x": 0.0, "y": math.nan, "z": 0.0}
        )
        assert "목표 좌표" in event["text"]
        assert console.executed == []

    def test_unread_position_pool_is_rejected(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, _approval, _audit = _new_session(
            tmp_path, store=store, state_tree=_state_tree()
        )
        event = session.beat_grid_new_preset(
            1, "BACK", "position", "LA Center", "스테이지 중앙", {"x": 0.0, "y": 0.0, "z": 0.0}
        )
        assert "콘솔" in event["text"]
        assert console.executed == []

    # 카드 t594(REQ-LDBEAT-015(i-5)) — "color"는 더는 이 거절에 들지 않는다
    # (base 색 풀도 콘솔 빈 슬롯으로 지원한다, `test_new_color_preset_t594.py`
    # 가 전수로 잠근다). dimmer_preset 거절은 회귀 없이 그대로다.
    @pytest.mark.parametrize("field", ["dimmer_preset"])
    def test_dimmer_preset_is_still_rejected(self, tmp_path, field) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, _approval, _audit = _new_session(tmp_path, store=store)
        event = session.beat_grid_new_preset(1, "BACK", field, "LA Wave", "따뜻한 흰색")
        assert "번호대를 지어내지 않습니다" in event["text"]
        assert console.executed == []

    def test_aim_on_a_non_position_field_is_rejected(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, _approval, _audit = _new_session(tmp_path, store=store)
        event = session.beat_grid_new_preset(
            1, "BACK", "effect", "LA Wave", "따뜻한 흰색", {"x": 0.0, "y": 0.0, "z": 0.0}
        )
        assert "aim" in event["text"] or "목표 좌표" in event["text"]
        assert console.executed == []
