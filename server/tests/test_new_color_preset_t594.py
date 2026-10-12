"""카드 t594(REQ-LDBEAT-015(i-5)) — 「＋ 새 프리셋 만들기」의 "색" 필드.

t589 이 "색"을 base 풀(효과 번호대 없음)이라는 이유로 거절했다
(`server.web.session.ChatSession._NEW_PRESET_NO_BAND_FIELDS`). 이 카드는
그 거절을 풀고 색이 되게 한다 — 목표 RGB(r·g·b, 0~100%)와 영문 콘솔 이름을
받아, 콘솔이 실제로 쥔 첫 빈 번호를 `first_free_base_color_number`(새
순수 함수, `server.design.beat_grid_presets`)로 고르고 **일반 편집과
같은 길**(`apply_beat_grid_edit`)로 씌운다 — 번호는 다른 신규 번호와
똑같이 「⇪ 콘솔에 반영」 승인 전까지 승인 대기로 남고, 목표 RGB는 카드
t589의 ``record_app_preset_label``과 같은 저장 모양인
``record_color_preset_rgb``로 남아 반영 때
`server.design.beat_grid_color_presets.color_preset_outcomes`가 선택+값
줄로 환산한다. dimmer_preset은 그대로 거절한다(회귀 없음).

네 층: ① 순수 번호 배정 함수 ② 순수 판정 모듈(`beat_grid_color_presets`)
③ 프로토콜 파서(rgb 모양 검증) ④ 서버 핸들러(세션 종단간, 다이얼로그 +
반영). 콘솔 접촉: 0건(쓰기) — `FakeConsole.executed`로 직접 잰다.
"""

from __future__ import annotations

import json
import math

import pytest

from server.design.beat_grid import (
    EMPTY_PRESET_HOLD,
    POOL_UNREAD_HOLD,
    empty_preset_cells,
)
from server.design.beat_grid_color_presets import (
    COLOR_ATTRS_MISSING,
    COLOR_CHANNELS_UNREAD,
    COLOR_CREATE_ON_APPLY,
    COLOR_GROUP_UNCONFIRMED,
    COLOR_LABEL_INVALID,
    COLOR_LABEL_MISSING,
    COLOR_MEMBERS_UNREAD,
    COLOR_MULTI_GROUP,
    COLOR_RGB_MISSING,
    color_grid_blocker,
    color_preset_outcomes,
    color_preset_rgb,
    record_color_preset_rgb,
)
from server.design.beat_grid_position_presets import plan_cells
from server.design.beat_grid_presets import (
    app_preset_description,
    app_preset_label,
    first_free_base_color_number,
)
from server.web.messages import ProtocolError, parse_client_message
from server.web.session import SongTimelineStore

from .test_new_preset_dialog_t589 import (
    PROTOCOL_VERSION,
    _cue_of,
    _new_session,
    _pool_children_payload,
    _pool_list_payload,
    _state_tree,
    _timeline,
    _timeline_for_apply,
)

_CREATED = "박자 격자 새 프리셋"
_REJECTED = "박자 격자 수정 거절"

_RGB_RED = {"r": 50.0, "g": 0.0, "b": 0.0}
_CHANNELS_OK = ["Main Module#2_ColorRGB_R", "Main Module#2_ColorRGB_G", "Main Module#2_ColorRGB_B"]
_CHANNELS_CMY = ["Cyan", "Magenta", "Yellow"]


# == ① 순수 번호 배정 함수 ====================================================


class TestFirstFreeBaseColorNumber:
    def test_capture_harness_fake_pool_example(self) -> None:
        policy = {
            "confirmed": False,
            "pools": {"color_effect": {"start": "4.41", "end": "4.99"}},
        }
        grid = {"tracks": []}
        console_children = (4, {21: "LA Red", 41: None})
        preset_no, reason = first_free_base_color_number(
            policy=policy, grid=grid, console_children=console_children
        )
        assert reason is None
        assert preset_no == "4.22"

    def test_band_slots_are_skipped_even_when_occupied(self) -> None:
        policy = {
            "confirmed": False,
            "pools": {"color_effect": {"start": "4.41", "end": "4.99"}},
        }
        grid = {"tracks": []}
        console_children = (4, {21: "LA Red", **{slot: "X" for slot in range(41, 100)}})
        preset_no, reason = first_free_base_color_number(
            policy=policy, grid=grid, console_children=console_children
        )
        assert reason is None
        assert preset_no == "4.22"

    def test_grid_referenced_number_is_skipped(self) -> None:
        policy = {"confirmed": False, "pools": {}}
        grid = {
            "tracks": [
                {"group_name": "BACK", "cues": [{"bar": 1, "color_preset_no": "4.1"}]},
            ]
        }
        console_children = (4, {})
        preset_no, reason = first_free_base_color_number(
            policy=policy, grid=grid, console_children=console_children
        )
        assert reason is None
        assert preset_no == "4.2"

    def test_no_base_slots_at_all_starts_at_dot_one(self) -> None:
        policy = {
            "confirmed": False,
            "pools": {"color_effect": {"start": "4.41", "end": "4.99"}},
        }
        grid = {"tracks": []}
        console_children = (4, {})
        preset_no, reason = first_free_base_color_number(
            policy=policy, grid=grid, console_children=console_children
        )
        assert reason is None
        assert preset_no == "4.1"

    def test_unread_pool_is_rejected_not_guessed(self) -> None:
        policy = {"confirmed": False, "pools": {}}
        grid = {"tracks": []}
        preset_no, reason = first_free_base_color_number(
            policy=policy, grid=grid, console_children=None
        )
        assert preset_no is None
        assert reason is not None
        assert "Color" in reason and "콘솔" in reason

    def test_pool_number_comes_from_the_console_read_not_a_literal_four(self) -> None:
        policy = {"confirmed": False, "pools": {}}
        grid = {"tracks": []}
        console_children = (9, {})
        preset_no, reason = first_free_base_color_number(
            policy=policy, grid=grid, console_children=console_children
        )
        assert reason is None
        assert preset_no == "9.1"

    def test_position_message_is_untouched(self) -> None:
        # 공유 몸체(`_first_free_base_pool_number`)를 쪼갠 뒤에도 위치 쪽
        # 거절 문구는 바이트 동일해야 한다(회귀 없음).
        from server.design.beat_grid_presets import first_free_base_position_number

        preset_no, reason = first_free_base_position_number(
            policy={"confirmed": False, "pools": {}}, grid={"tracks": []}, console_children=None
        )
        assert preset_no is None
        assert reason == (
            "콘솔에서 Position 풀을 읽지 못해 빈 슬롯을 알 수 없습니다 — "
            "번호대 보호가 없는 기본 풀이라 추측해 배정하지 않습니다."
        )


# == ② 순수 판정 모듈 =========================================================


def _grid(cues: list[dict], *, confirmed: bool = True, **extra: object) -> dict:
    grid: dict = {
        "tracks": [
            {
                "group_name": "BACK",
                "group_no": 7,
                "group_no_confirmed": confirmed,
                "cues": cues,
            }
        ]
    }
    grid.update(extra)
    return grid


_RECIPE = {
    "preset_colors": {"4.41": _RGB_RED},
    "preset_labels": {"4.41": "LA Red"},
}
_MEMBERS = {"BACK": [101, 102]}
_CHANNELS = {101: _CHANNELS_OK, 102: _CHANNELS_OK}


class TestStorage:
    def test_records_a_copy_keyed_by_pool_slot(self) -> None:
        grid = _grid([])
        updated = record_color_preset_rgb(grid, "4.41", (50, 0, 0))
        assert "preset_colors" not in grid, "원본을 바꿨다"
        assert updated["preset_colors"] == {"4.41": {"r": 50.0, "g": 0.0, "b": 0.0}}
        assert color_preset_rgb(updated, "4.41") == (50.0, 0.0, 0.0)

    @pytest.mark.parametrize("value", ["abc", "4", "4.x"])
    def test_refuses_non_pool_slot_numbers(self, value) -> None:
        with pytest.raises(ValueError):
            record_color_preset_rgb(_grid([]), value, (0, 0, 0))

    @pytest.mark.parametrize("bad", [math.nan, math.inf, -1, 101, "1"])
    def test_refuses_out_of_range_or_non_finite_channels(self, bad) -> None:
        with pytest.raises(ValueError):
            record_color_preset_rgb(_grid([]), "4.41", (bad, 0, 0))

    def test_missing_or_malformed_rgb_reads_as_none(self) -> None:
        assert color_preset_rgb(_grid([]), "4.41") is None
        assert color_preset_rgb({"preset_colors": {"4.41": {"r": 1}}}, "4.41") is None
        bad_grid = {"preset_colors": {"4.41": {"r": 1, "g": -1, "b": 0}}}
        assert color_preset_rgb(bad_grid, "4.41") is None


class TestColorGridBlocker:
    def test_none_when_all_grid_conditions_are_present(self) -> None:
        cue = {"bar": 1, "color_preset_no": "4.41", "evidence": None}
        assert color_grid_blocker(_grid([cue], **_RECIPE), "4.41") is None

    def test_rgb_missing(self) -> None:
        cue = {"bar": 1, "color_preset_no": "4.41", "evidence": None}
        grid = _grid([cue], preset_labels={"4.41": "LA Red"})
        assert color_grid_blocker(grid, "4.41") == COLOR_RGB_MISSING

    def test_label_missing(self) -> None:
        cue = {"bar": 1, "color_preset_no": "4.41", "evidence": None}
        grid = _grid([cue], preset_colors=_RECIPE["preset_colors"])
        assert color_grid_blocker(grid, "4.41") == COLOR_LABEL_MISSING

    def test_label_invalid(self) -> None:
        cue = {"bar": 1, "color_preset_no": "4.41", "evidence": None}
        grid = _grid([cue], **{**_RECIPE, "preset_labels": {"4.41": "라 레드"}})
        assert color_grid_blocker(grid, "4.41") == COLOR_LABEL_INVALID

    def test_group_unconfirmed(self) -> None:
        cue = {"bar": 1, "color_preset_no": "4.41", "evidence": None}
        grid = _grid([cue], confirmed=False, **_RECIPE)
        assert color_grid_blocker(grid, "4.41") == COLOR_GROUP_UNCONFIRMED

    def test_multi_group(self) -> None:
        grid = {
            "tracks": [
                {
                    "group_name": "BACK",
                    "group_no": 7,
                    "group_no_confirmed": True,
                    "cues": [{"bar": 1, "color_preset_no": "4.41"}],
                },
                {
                    "group_name": "SIDE",
                    "group_no": 8,
                    "group_no_confirmed": True,
                    "cues": [{"bar": 2, "color_preset_no": "4.41"}],
                },
            ],
            **_RECIPE,
        }
        assert color_grid_blocker(grid, "4.41") == COLOR_MULTI_GROUP


class TestColorPresetOutcomes:
    def test_bundle_shape_is_clear_select_value_store_label_clear(self) -> None:
        cue = {"bar": 1, "color_preset_no": "4.41", "evidence": None}
        outcomes = color_preset_outcomes(
            _grid([cue], **_RECIPE), ["4.41"], members=_MEMBERS, channel_names=_CHANNELS
        )
        lines, reason = outcomes["4.41"]
        assert reason is None
        assert lines == (
            "ClearAll",
            "Group 7 ; Attribute 'ColorRGB_R' At 50 ; Attribute 'ColorRGB_G' At 0"
            " ; Attribute 'ColorRGB_B' At 0",
            "Store Preset 4.41",
            "Label Preset 4.41 'LA Red'",
            "ClearAll",
        )

    def test_integer_percent_values_are_rendered_without_decimals(self) -> None:
        cue = {"bar": 1, "color_preset_no": "4.41", "evidence": None}
        recipe = {**_RECIPE, "preset_colors": {"4.41": {"r": 12.5, "g": 0, "b": 100}}}
        outcomes = color_preset_outcomes(
            _grid([cue], **recipe), ["4.41"], members=_MEMBERS, channel_names=_CHANNELS
        )
        lines, _reason = outcomes["4.41"]
        assert "At 12.5" in lines[1]
        assert "At 0 " in lines[1] or lines[1].endswith("At 0")
        assert "At 100" in lines[1]

    @pytest.mark.parametrize(
        ("grid_extra", "confirmed", "members", "channels", "reason"),
        [
            ({"preset_labels": {"4.41": "LA Red"}}, True, _MEMBERS, _CHANNELS, COLOR_RGB_MISSING),
            (
                {"preset_colors": _RECIPE["preset_colors"]},
                True,
                _MEMBERS,
                _CHANNELS,
                COLOR_LABEL_MISSING,
            ),
            (_RECIPE, False, _MEMBERS, _CHANNELS, COLOR_GROUP_UNCONFIRMED),
            (_RECIPE, True, {}, _CHANNELS, COLOR_MEMBERS_UNREAD),
        ],
    )
    def test_missing_piece_holds_with_its_reason(
        self, grid_extra, confirmed, members, channels, reason
    ) -> None:
        cue = {"bar": 1, "color_preset_no": "4.41", "evidence": None}
        grid = _grid([cue], confirmed=confirmed, **grid_extra)
        outcomes = color_preset_outcomes(grid, ["4.41"], members=members, channel_names=channels)
        lines, held_reason = outcomes["4.41"]
        assert lines is None
        assert held_reason == reason

    def test_channels_unread_holds_with_fid(self) -> None:
        cue = {"bar": 1, "color_preset_no": "4.41", "evidence": None}
        outcomes = color_preset_outcomes(
            _grid([cue], **_RECIPE),
            ["4.41"],
            members=_MEMBERS,
            channel_names={101: None, 102: _CHANNELS_OK},
        )
        lines, reason = outcomes["4.41"]
        assert lines is None
        assert reason is not None
        assert reason.startswith(COLOR_CHANNELS_UNREAD)
        assert "101" in reason

    def test_cmy_only_rig_holds_with_attrs_missing_and_fid(self) -> None:
        # CMY 만 있는 리그 — RGB 세 속성이 없다(보류, 지어내지 않는다).
        cue = {"bar": 1, "color_preset_no": "4.41", "evidence": None}
        outcomes = color_preset_outcomes(
            _grid([cue], **_RECIPE),
            ["4.41"],
            members=_MEMBERS,
            channel_names={101: _CHANNELS_CMY, 102: _CHANNELS_CMY},
        )
        lines, reason = outcomes["4.41"]
        assert lines is None
        assert reason is not None
        assert reason.startswith(COLOR_ATTRS_MISSING)
        assert "101" in reason and "102" in reason

    def test_partial_rgb_capable_rig_holds_the_non_capable_fid(self) -> None:
        cue = {"bar": 1, "color_preset_no": "4.41", "evidence": None}
        outcomes = color_preset_outcomes(
            _grid([cue], **_RECIPE),
            ["4.41"],
            members=_MEMBERS,
            channel_names={101: _CHANNELS_OK, 102: _CHANNELS_CMY},
        )
        lines, reason = outcomes["4.41"]
        assert lines is None
        assert reason is not None
        assert reason.startswith(COLOR_ATTRS_MISSING)
        assert "102" in reason
        assert "101" not in reason.split("FID")[-1]

    def test_module_prefix_is_stripped_before_matching(self) -> None:
        cue = {"bar": 1, "color_preset_no": "4.41", "evidence": None}
        outcomes = color_preset_outcomes(
            _grid([cue], **_RECIPE),
            ["4.41"],
            members={"BACK": [101]},
            channel_names={
                101: [
                    "Main Module#2_ColorRGB_R",
                    "Main Module#2_ColorRGB_G",
                    "Main Module#2_ColorRGB_B",
                ]
            },
        )
        lines, reason = outcomes["4.41"]
        assert reason is None
        assert lines is not None


class TestPlanCellsReusesTheSharedEntry:
    def test_color_number_is_created_through_the_shared_plan_cells_entry(self) -> None:
        cue = {"bar": 1, "color_preset_no": "4.41", "evidence": None}
        held = [
            {
                "group_name": "BACK",
                "bar": 1,
                "field": "color_preset_no",
                "field_label": "색 프리셋",
                "value": "4.41",
                "hold_reason": EMPTY_PRESET_HOLD,
            }
        ]
        outcomes = color_preset_outcomes(
            _grid([cue], **_RECIPE), ["4.41"], members=_MEMBERS, channel_names=_CHANNELS
        )
        outcome_map = {("color_preset_no", number): outcome for number, outcome in outcomes.items()}
        plan = plan_cells(held, outcome_map)
        assert list(plan.creations) == ["4.41"]
        assert plan.creation_fields["4.41"] == "color_preset_no"
        assert plan.held == []


# == ③ 프로토콜 파서 =========================================================


class TestParseClientMessageRgb:
    def _valid_payload(self, **overrides: object) -> dict:
        payload = {
            "v": PROTOCOL_VERSION,
            "type": "beat_grid_new_preset",
            "bar": 1,
            "target": "BACK",
            "field": "color",
            "label": "LA Red",
            "description": "따뜻한 빨강",
            "rgb": {"r": 50.0, "g": 0.0, "b": 0.0},
        }
        payload.update(overrides)
        return payload

    def _parse(self, payload: dict) -> dict:
        return parse_client_message(json.dumps(payload))

    def test_color_with_valid_rgb_parses_and_carries_rgb(self) -> None:
        parsed = self._parse(self._valid_payload())
        assert parsed["field"] == "color"
        assert parsed["rgb"] == {"r": 50.0, "g": 0.0, "b": 0.0}

    def test_color_without_rgb_is_rejected(self) -> None:
        payload = self._valid_payload()
        del payload["rgb"]
        with pytest.raises(ProtocolError):
            self._parse(payload)

    @pytest.mark.parametrize("channel", ["r", "g", "b"])
    def test_color_with_missing_channel_is_rejected(self, channel) -> None:
        payload = self._valid_payload()
        del payload["rgb"][channel]
        with pytest.raises(ProtocolError):
            self._parse(payload)

    @pytest.mark.parametrize("bad", ["1", True, None, [1]])
    def test_color_with_non_numeric_channel_is_rejected(self, bad) -> None:
        payload = self._valid_payload()
        payload["rgb"]["r"] = bad
        with pytest.raises(ProtocolError):
            self._parse(payload)

    @pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf, -1, 101])
    def test_color_with_out_of_range_channel_is_rejected(self, bad) -> None:
        payload = self._valid_payload()
        payload["rgb"]["b"] = bad
        with pytest.raises(ProtocolError):
            self._parse(payload)

    @pytest.mark.parametrize("field", ["dimmer_preset", "dimmer_effect", "position", "effect"])
    def test_rgb_present_on_a_non_color_field_is_rejected(self, field) -> None:
        payload = self._valid_payload(field=field)
        with pytest.raises(ProtocolError):
            self._parse(payload)

    def test_non_color_fields_without_rgb_still_parse(self) -> None:
        payload = self._valid_payload(field="effect")
        del payload["rgb"]
        payload["fx"] = {"fx_id": "sweep-soft-wide", "period_unit": "beat", "period_value": 2}
        parsed = self._parse(payload)
        assert parsed["field"] == "effect"
        assert "rgb" not in parsed


# == ④ 서버 핸들러(세션 종단간) ===============================================


def _color_state_tree(*, pool_no: int = 4, children: dict | None = None) -> dict:
    return _state_tree(
        **{
            "DataPool/PresetPools": _pool_list_payload({"Color": pool_no}),
            f"DataPool/PresetPools/{pool_no}": _pool_children_payload(children or {}),
        }
    )


class TestBeatGridNewPresetColorField:
    def test_color_is_no_longer_rejected_as_a_no_band_field(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, _approval, _audit = _new_session(
            tmp_path, store=store, state_tree=_color_state_tree()
        )
        event = session.beat_grid_new_preset(
            1, "BACK", "color", "LA Red", "따뜻한 빨강", None, None, _RGB_RED
        )
        assert "번호대를 지어내지 않습니다" not in event["text"], event["text"]
        assert event["summary"] == _CREATED, event["text"]
        assert console.executed == []  # 읽기만 — 쓰기 0건

    def test_assigns_the_console_empty_slot_outside_the_effect_band(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, _approval, _audit = _new_session(
            tmp_path, store=store, state_tree=_color_state_tree(children={21: "LA Red"})
        )
        event = session.beat_grid_new_preset(
            1, "BACK", "color", "New Red", "새 빨강", None, None, _RGB_RED
        )
        assert "4.22" in event["text"], event["text"]
        cue = _cue_of(store.latest["beat_grid"], "BACK", 1)
        assert cue["color_preset_no"] == "4.22"
        assert console.executed == []

    def test_label_description_and_rgb_are_all_recorded(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, _console, _approval, _audit = _new_session(
            tmp_path, store=store, state_tree=_color_state_tree()
        )
        session.beat_grid_new_preset(
            1,
            "BACK",
            "color",
            "New Red",
            "새 빨강",
            None,
            None,
            {"r": 12.0, "g": 34.0, "b": 56.0},
        )
        grid = store.latest["beat_grid"]
        assert app_preset_label(grid, "4.1") == "New Red"
        assert app_preset_description(grid, "4.1") == "새 빨강"
        assert color_preset_rgb(grid, "4.1") == (12.0, 34.0, 56.0)

    def test_missing_rgb_is_rejected_without_console_contact(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, _approval, _audit = _new_session(
            tmp_path, store=store, state_tree=_color_state_tree()
        )
        event = session.beat_grid_new_preset(1, "BACK", "color", "LA Red", "따뜻한 빨강")
        assert "목표 RGB" in event["text"]
        assert console.executed == []

    def test_out_of_range_rgb_channel_is_rejected(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, _approval, _audit = _new_session(
            tmp_path, store=store, state_tree=_color_state_tree()
        )
        event = session.beat_grid_new_preset(
            1,
            "BACK",
            "color",
            "LA Red",
            "따뜻한 빨강",
            None,
            None,
            {"r": 101.0, "g": 0.0, "b": 0.0},
        )
        assert "목표 RGB" in event["text"] or "범위" in event["text"]
        assert console.executed == []

    def test_non_finite_rgb_channel_is_rejected(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, _approval, _audit = _new_session(
            tmp_path, store=store, state_tree=_color_state_tree()
        )
        event = session.beat_grid_new_preset(
            1,
            "BACK",
            "color",
            "LA Red",
            "따뜻한 빨강",
            None,
            None,
            {"r": math.nan, "g": 0.0, "b": 0.0},
        )
        assert "색 채널" in event["text"]
        assert console.executed == []

    def test_unread_color_pool_is_rejected(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, _approval, _audit = _new_session(
            tmp_path, store=store, state_tree=_state_tree()
        )
        event = session.beat_grid_new_preset(
            1, "BACK", "color", "LA Red", "따뜻한 빨강", None, None, _RGB_RED
        )
        assert "콘솔" in event["text"]
        assert console.executed == []

    def test_dimmer_preset_is_still_rejected(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, _approval, _audit = _new_session(tmp_path, store=store)
        event = session.beat_grid_new_preset(1, "BACK", "dimmer_preset", "LA Wave", "따뜻한 흰색")
        assert "번호대를 지어내지 않습니다" in event["text"]
        assert console.executed == []

    def test_rgb_on_a_non_color_field_is_rejected(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _timeline()
        session, console, _approval, _audit = _new_session(tmp_path, store=store)
        fx = {"fx_id": "sweep-soft-wide", "period_unit": "beat", "period_value": 2}
        event = session.beat_grid_new_preset(
            1, "BACK", "effect", "LA Wave", "따뜻한 흰색", None, fx, _RGB_RED
        )
        assert "rgb" in event["text"] or "목표 RGB" in event["text"]
        assert console.executed == []


# == ④b 반영(승인=송신) ======================================================


def _grid_with_color_cell(*, bar: int = 1, group_name: str = "BACK", group_no: int = 7) -> dict:
    return {
        "tracks": [
            {
                "group_name": group_name,
                "group_no": group_no,
                "group_no_confirmed": True,
                "cues": [{"bar": bar, "color_preset_no": "4.41", "evidence": None}],
            }
        ],
        "preset_colors": {"4.41": _RGB_RED},
        "preset_labels": {"4.41": "LA Red"},
        "probe_results": {},
    }


def _apply_session(
    tmp_path,
    grid: dict,
    *,
    pool4: list[int] | None,
    members=_MEMBERS,
    channels=_CHANNELS,
):
    timeline = _timeline_for_apply(beat_grid=grid)
    tree = _state_tree()
    if pool4 is not None:
        tree["DataPool/PresetPools/4"] = {
            "children": [{"i": slot, "name": f"P{slot}"} for slot in pool4]
        }
    store = SongTimelineStore()
    store.latest = timeline
    session, console, approval, _audit = _new_session(tmp_path, store=store, state_tree=tree)
    session._beat_grid_group_members = lambda names: {n: members[n] for n in names if n in members}
    session._beat_grid_color_channel_names = lambda fids: dict(channels)
    status = session.beat_grid_apply()
    return status, store, approval, console


def _sent(approval) -> list[str]:
    return [item.command for request in approval.requests for item in request.items]


class TestApplyCreatesTheColorPreset:
    def test_bundle_rides_the_batch_before_cue_lines_and_cell_is_approved(self, tmp_path) -> None:
        status, store, approval, _console = _apply_session(
            tmp_path, _grid_with_color_cell(), pool4=[1]
        )
        assert status["ok"] is True, status
        sent = _sent(approval)
        clear_at = sent.index("ClearAll")
        assert sent[clear_at + 1].startswith("Group 7 ; Attribute 'ColorRGB_R' At 50")
        assert sent[clear_at + 2] == "Store Preset 4.41"
        assert sent[clear_at + 3] == "Label Preset 4.41 'LA Red'"
        assert sent[clear_at + 4] == "ClearAll"
        risk = " ".join(approval.requests[0].items[0].risk_reasons)
        assert "새로 만드는 색 프리셋 1개" in risk
        assert "4.41 'LA Red'" in risk

    def test_occupied_slot_is_never_stored(self, tmp_path) -> None:
        # 4.41 이 이미 있다 → split 이 held 로 보내지 않음 → Store 0줄.
        status, _store, approval, _console = _apply_session(
            tmp_path, _grid_with_color_cell(), pool4=[41]
        )
        assert status["ok"] is True
        assert not [c for c in _sent(approval) if c.startswith("Store Preset")]

    def test_unreadable_pool_is_never_stored(self, tmp_path) -> None:
        status, _store, approval, _console = _apply_session(
            tmp_path, _grid_with_color_cell(), pool4=None
        )
        assert status["ok"] is False
        assert approval.requests == []
        assert not [c for c in _sent(approval) if "4.41" in c]
        assert POOL_UNREAD_HOLD in status["reason"]

    # COLOR_GROUP_UNCONFIRMED 는 순수 판정 층(`TestColorPresetOutcomes.
    # test_missing_piece_holds_with_its_reason`)에서 전수로 잠근다. 반영
    # 세션 레벨에서는 그 트랙의 `group_no_confirmed` 가 큐 송신 자체의
    # 전제라 — 꺼면 그 트랙이 통째로 "콘솔에 반영할 내용이 없습니다"로
    # 떨어진다(실측) — 색 전용 보류가 아니라 다른 관문과 섞여 이 칸에서는
    # 잠글 수 없다.

    def test_multi_group_holds(self, tmp_path) -> None:
        grid = {
            "tracks": [
                {
                    "group_name": "BACK",
                    "group_no": 7,
                    "group_no_confirmed": True,
                    "cues": [{"bar": 1, "color_preset_no": "4.41"}],
                },
                {
                    "group_name": "SIDE",
                    "group_no": 8,
                    "group_no_confirmed": True,
                    "cues": [{"bar": 2, "color_preset_no": "4.41"}],
                },
            ],
            "preset_colors": {"4.41": _RGB_RED},
            "preset_labels": {"4.41": "LA Red"},
            "probe_results": {},
        }
        status, _store, approval, _console = _apply_session(
            tmp_path,
            grid,
            pool4=[1],
            members={"BACK": [101], "SIDE": [201]},
            channels={101: _CHANNELS_OK, 201: _CHANNELS_OK},
        )
        assert status["ok"] is False
        assert approval.requests == []
        assert not [c for c in _sent(approval) if "4.41" in c]
        assert COLOR_MULTI_GROUP in status["reason"]

    def test_members_unread_holds(self, tmp_path) -> None:
        status, _store, approval, _console = _apply_session(
            tmp_path, _grid_with_color_cell(), pool4=[1], members={}
        )
        assert status["ok"] is False
        assert approval.requests == []
        assert not [c for c in _sent(approval) if "4.41" in c]
        assert COLOR_MEMBERS_UNREAD in status["reason"]

    def test_channels_unread_holds(self, tmp_path) -> None:
        status, _store, approval, _console = _apply_session(
            tmp_path, _grid_with_color_cell(), pool4=[1], channels={101: None, 102: _CHANNELS_OK}
        )
        assert status["ok"] is False
        assert approval.requests == []
        assert not [c for c in _sent(approval) if "4.41" in c]
        assert COLOR_CHANNELS_UNREAD in status["reason"]

    def test_cmy_only_rig_holds_with_attrs_missing(self, tmp_path) -> None:
        status, _store, approval, _console = _apply_session(
            tmp_path,
            _grid_with_color_cell(),
            pool4=[1],
            channels={101: _CHANNELS_CMY, 102: _CHANNELS_CMY},
        )
        assert status["ok"] is False
        assert approval.requests == []
        assert not [c for c in _sent(approval) if "4.41" in c]
        assert COLOR_ATTRS_MISSING in status["reason"]

    def test_rgb_missing_holds(self, tmp_path) -> None:
        grid = _grid_with_color_cell()
        del grid["preset_colors"]
        status, _store, approval, _console = _apply_session(tmp_path, grid, pool4=[1])
        assert status["ok"] is False
        assert approval.requests == []
        assert not [c for c in _sent(approval) if "4.41" in c]
        assert COLOR_RGB_MISSING in status["reason"]


class TestTwoColorPresetsSurviveTheSendDedupe:
    """카드 t601 결함류 — 같은 그룹·같은 RGB 를 쓰는 색 프리셋 둘이 한 반영
    묶음에 있어도 선택+값 한 줄(``is_programmer_state`` 면제)이라 둘 다
    살아 나간다(실제 송신 경로, ``run_commands`` 중복 제거 경유)."""

    def test_both_selection_value_lines_are_sent_not_deduped(self, tmp_path) -> None:
        grid = {
            "tracks": [
                {
                    "group_name": "BACK",
                    "group_no": 7,
                    "group_no_confirmed": True,
                    "cues": [
                        {"bar": 1, "color_preset_no": "4.41", "evidence": None},
                        {"bar": 2, "color_preset_no": "4.42", "evidence": None},
                    ],
                }
            ],
            "preset_colors": {"4.41": _RGB_RED, "4.42": _RGB_RED},
            "preset_labels": {"4.41": "LA Red", "4.42": "LA Red 2"},
            "probe_results": {},
        }
        status, _store, approval, _console = _apply_session(tmp_path, grid, pool4=[1])
        assert status["ok"] is True, status
        sent = _sent(approval)
        selection_line = (
            "Group 7 ; Attribute 'ColorRGB_R' At 50"
            " ; Attribute 'ColorRGB_G' At 0 ; Attribute 'ColorRGB_B' At 0"
        )
        assert sent.count(selection_line) == 2, sent
        assert "Store Preset 4.41" in sent
        assert "Store Preset 4.42" in sent


class TestColorCreateOnApply:
    """카드 t595 넓힘 — 빈 색 번호도 반영 때 그룹·RGB 로 만들어질 수 있다
    (``empty_preset_cells``의 「빈 프리셋」 표식이 ``create_on_apply``로 간다)."""

    def _color_grid(self, cue: dict, **extra: object) -> dict:
        track = {"group_name": "BACK", "group_no": 7, "group_no_confirmed": True, "cues": [cue]}
        grid: dict = {"tracks": [track]}
        grid.update(extra)
        return grid

    def test_pending_empty_color_with_rgb_and_label_is_create(self) -> None:
        grid = self._color_grid({"bar": 1, "color_preset_no": "4.41", "evidence": None}, **_RECIPE)
        (cell,) = empty_preset_cells(grid, {4: {1: "P1"}})
        assert cell["state"] == "create"
        assert cell["fields"][0]["kind"] == "create_on_apply"
        assert cell["fields"][0]["reason"] == COLOR_CREATE_ON_APPLY

    def test_missing_rgb_stays_held_with_t594_reason(self) -> None:
        grid = self._color_grid({"bar": 1, "color_preset_no": "4.41", "evidence": None})
        (cell,) = empty_preset_cells(grid, {4: {1: "P1"}})
        assert cell["state"] == "held"
        assert cell["fields"][0]["kind"] == "empty"
        assert COLOR_RGB_MISSING in cell["fields"][0]["reason"]

    def test_approved_only_reference_is_created(self) -> None:
        """카드 t600 — 승인된 칸만 가리켜도 t594 후보다(반영이 같은 규칙으로 만든다)."""
        approved = {"by": "supervisor", "date": "2026-10-11", "source": "t594"}
        cue = {
            "bar": 1,
            "color_preset_no": "4.41",
            "evidence": {"grade": None, "approval": approved},
        }
        (cell,) = empty_preset_cells(self._color_grid(cue, **_RECIPE), {4: {1: "P1"}})
        assert cell["state"] == "create"
        assert cell["fields"][0]["kind"] == "create_on_apply"


class TestPresendRereadCoversColor:
    def test_filled_during_approval_window_blocks_the_whole_send(self, tmp_path) -> None:
        timeline = _timeline_for_apply(beat_grid=_grid_with_color_cell())
        tree = _state_tree()
        tree["DataPool/PresetPools/4"] = {"children": [{"i": 1, "name": "P1"}]}
        store = SongTimelineStore()
        store.latest = timeline

        def _on_request(_request):
            # 승인 창이 떠 있는 사이 콘솔에서 4.41 이 채워진다.
            tree["DataPool/PresetPools/4"] = {
                "children": [{"i": 1, "name": "P1"}, {"i": 41, "name": "Filled"}]
            }

        from server.safety.audit import AuditLog
        from server.safety.gate import SafetyGate
        from server.web.approval_bridge import ApprovalChannel
        from server.web.session import ChatSession
        from server.web.timeline_library import SongTimelineLibrary

        from .test_new_preset_dialog_t589 import RefusingProvider
        from .test_safety_gate import FakeConsole, ScriptedApproval

        console = FakeConsole(state_tree=tree)
        audit = AuditLog(tmp_path / "audit")
        approval = ScriptedApproval(decisions=(True,), on_request=_on_request)
        gate = SafetyGate(console=console, audit=audit, approval_port=approval)
        channel = ApprovalChannel(timeout_seconds=1.0)
        session = ChatSession(
            gate=gate,
            provider=RefusingProvider(),
            system_prefix="PREFIX",
            audit=audit,
            send_event=lambda event: None,
            approval_channel=channel,
            timeline_store=store,
            timeline_library=SongTimelineLibrary(tmp_path / "library.json"),
        )
        session._beat_grid_group_members = lambda names: {
            n: _MEMBERS[n] for n in names if n in _MEMBERS
        }
        session._beat_grid_color_channel_names = lambda fids: dict(_CHANNELS)
        status = session.beat_grid_apply()
        assert status["ok"] is False
        assert not [c for c in console.executed if "Preset" in c and "4.41" in c]
