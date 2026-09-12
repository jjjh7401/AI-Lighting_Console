"""t373 — `server/design/override_look.py`: override look 계획기.

`docs/research/ma3-effects/20-mblightarts-end-to-end-showfile-process.md`
§10.1(override look 생성)의 4~14단계를 커맨드 번들로 고정한다. 핀으로 거는
불변식 셋:

1. 안전 답(``stop_ifx``/``stop_pfx``/``move_in_black``) 중 하나라도 빠진 계획은
   거절된다.
2. 점유를 못 잰 슬롯(``occupied_slots=None``)은 절대 비었다고 보고되지 않는다.
3. 번들의 ``Stop IFX``/``Stop PFX`` 원문 줄은 그 답이 True 일 때만 실린다.

순수 함수 검증이다. 콘솔·네트워크 접촉 0.
"""

from __future__ import annotations

import pytest

from server.design.override_look import (
    DEFAULT_OVERRIDE_SLOTS,
    OverrideLookError,
    OverrideSafetyAnswers,
    plan_override_solo_spot,
    recommended_safety_answers,
)
from server.presets.store import preset_store_commands
from server.spatial.pointing import PointingTarget, SpatialPointingError, aim_pan_tilt

_TARGET = PointingTarget(0.0, 0.0, 0.0)
_FRONT_SPOT = (1103, (4.0, 0.0, 6.0))
_ALL_ANSWERS_ON = OverrideSafetyAnswers(stop_ifx=True, stop_pfx=True, move_in_black=True)
_ALL_ANSWERS_OFF = OverrideSafetyAnswers(stop_ifx=False, stop_pfx=False, move_in_black=False)


def _plan(**overrides):
    kwargs = dict(
        fixtures=[_FRONT_SPOT],
        target=_TARGET,
        safety=_ALL_ANSWERS_OFF,
        pool_no=1,
        occupied_slots=frozenset(),
        zoom_degrees=5.0,
        stop_ifx_command=None,
        stop_pfx_command=None,
    )
    kwargs.update(overrides)
    return plan_override_solo_spot(**kwargs)


class TestOverrideSafetyAnswersRequiresExplicitBools:
    def test_all_true_is_accepted(self):
        answers = OverrideSafetyAnswers(stop_ifx=True, stop_pfx=True, move_in_black=True)
        assert answers.to_dict() == {
            "stop_ifx": True,
            "stop_pfx": True,
            "move_in_black": True,
        }

    @pytest.mark.parametrize("field", ["stop_ifx", "stop_pfx", "move_in_black"])
    @pytest.mark.parametrize("bad_value", [None, 1, 0, "yes", "", 1.0])
    def test_a_non_bool_field_is_refused(self, field, bad_value):
        kwargs = {"stop_ifx": True, "stop_pfx": True, "move_in_black": True}
        kwargs[field] = bad_value
        with pytest.raises(OverrideLookError):
            OverrideSafetyAnswers(**kwargs)


class TestAPlanOmittingASafetyAnswerIsRefused:
    """카드 Method 절: "a plan that omits either safety answer must be refused"."""

    def test_a_non_overridesafetyanswers_object_is_refused(self):
        with pytest.raises(OverrideLookError):
            _plan(safety=None)

    def test_a_plain_dict_of_answers_is_refused(self):
        with pytest.raises(OverrideLookError):
            _plan(safety={"stop_ifx": True, "stop_pfx": True, "move_in_black": True})


class TestSlotOccupancy:
    """카드 BUILD 절: "an unestablished slot is not a free slot"."""

    def test_unestablished_occupancy_is_refused(self):
        with pytest.raises(OverrideLookError, match="unestablished"):
            _plan(occupied_slots=None)

    def test_it_auto_picks_the_first_free_slot_in_order(self):
        plan = _plan(occupied_slots=frozenset({1, 2, 3}))
        assert plan.slot == 4

    def test_all_slots_occupied_is_refused(self):
        with pytest.raises(OverrideLookError, match="occupied"):
            _plan(occupied_slots=frozenset(DEFAULT_OVERRIDE_SLOTS))

    def test_a_preferred_free_slot_is_honoured(self):
        plan = _plan(occupied_slots=frozenset({1, 2}), preferred_slot=7)
        assert plan.slot == 7

    def test_a_preferred_occupied_slot_is_refused(self):
        with pytest.raises(OverrideLookError, match="occupied"):
            _plan(occupied_slots=frozenset({7}), preferred_slot=7)

    def test_a_preferred_slot_outside_the_candidate_list_is_refused(self):
        with pytest.raises(OverrideLookError, match="prepared override slots"):
            _plan(occupied_slots=frozenset(), preferred_slot=99)

    def test_a_custom_available_slots_list_is_honoured(self):
        plan = _plan(occupied_slots=frozenset({20}), available_slots=(20, 21, 22))
        assert plan.slot == 21

    def test_no_slots_offered_is_refused(self):
        with pytest.raises(OverrideLookError):
            _plan(occupied_slots=frozenset(), available_slots=())


class TestStopIfxPfxLinesTrackTheAnswer:
    """카드 Method 절: "the emitted bundle must carry the Stop IFX / Stop
    PFX lines only when the answers say so"."""

    def test_both_off_emits_neither_line(self):
        plan = _plan(safety=_ALL_ANSWERS_OFF)
        assert "Call IFX-Off" not in plan.commands
        assert "Call PFX-Off" not in plan.commands
        # 정확히 조준 줄 하나 + Store 줄 하나뿐이어야 한다 — Stop 줄이 섞여
        # 들어가면 이 개수가 늘어난다.
        assert len(plan.commands) == 2

    def test_stop_ifx_true_without_a_command_is_refused(self):
        with pytest.raises(OverrideLookError, match="stop_ifx"):
            _plan(
                safety=OverrideSafetyAnswers(stop_ifx=True, stop_pfx=False, move_in_black=False),
                stop_ifx_command=None,
            )

    def test_stop_pfx_true_without_a_command_is_refused(self):
        with pytest.raises(OverrideLookError, match="stop_pfx"):
            _plan(
                safety=OverrideSafetyAnswers(stop_ifx=False, stop_pfx=True, move_in_black=False),
                stop_pfx_command=None,
            )

    def test_a_command_supplied_while_the_answer_is_false_is_refused(self):
        with pytest.raises(OverrideLookError):
            _plan(safety=_ALL_ANSWERS_OFF, stop_ifx_command="Call IFX-Off")

    def test_both_on_carries_both_lines_in_order_before_store(self):
        plan = _plan(
            safety=_ALL_ANSWERS_ON,
            stop_ifx_command="Call IFX-Off",
            stop_pfx_command="Call PFX-Off",
        )
        assert plan.commands[-3:] == (
            "Call IFX-Off",
            "Call PFX-Off",
            "Store Preset 1.1",
        )

    def test_only_stop_ifx_is_on(self):
        plan = _plan(
            safety=OverrideSafetyAnswers(stop_ifx=True, stop_pfx=False, move_in_black=True),
            stop_ifx_command="Call IFX-Off",
        )
        assert "Call IFX-Off" in plan.commands
        assert "Call PFX-Off" not in plan.commands


class TestTheLookCommandLine:
    def test_it_chains_dimmer_color_pan_tilt_zoom_on_one_line(self):
        plan = _plan(zoom_degrees=5.0)
        pan, tilt = aim_pan_tilt(_FRONT_SPOT[1], _TARGET.as_tuple())
        expected = (
            "Fixture 1103 ; Attribute 'Dimmer' At 100.0 ; "
            "Attribute 'ColorRGB_R' At 100.0 ; Attribute 'ColorRGB_G' At 100.0 ; "
            "Attribute 'ColorRGB_B' At 100.0 ; "
            f"Attribute 'Pan' At {pan:.1f} ; Attribute 'Tilt' At {tilt:.1f} ; "
            "Attribute 'Zoom' At 5.0"
        )
        assert plan.commands[0] == expected

    def test_it_records_the_computed_aim(self):
        plan = _plan()
        pan, tilt = aim_pan_tilt(_FRONT_SPOT[1], _TARGET.as_tuple())
        assert plan.aims == ((1103, pan, tilt),)

    def test_multiple_fixtures_each_get_their_own_line_in_order(self):
        second = (1104, (-4.0, 0.0, 6.0))
        plan = _plan(fixtures=[_FRONT_SPOT, second])
        assert plan.commands[0].startswith("Fixture 1103 ;")
        assert plan.commands[1].startswith("Fixture 1104 ;")
        assert plan.commands[2] == "Store Preset 1.1"

    def test_a_repeated_fixture_id_is_refused(self):
        with pytest.raises(OverrideLookError, match="twice"):
            _plan(fixtures=[_FRONT_SPOT, _FRONT_SPOT])

    def test_no_fixtures_is_refused(self):
        with pytest.raises(OverrideLookError):
            _plan(fixtures=[])

    def test_a_custom_dimmer_and_color_are_honoured(self):
        plan = _plan(dimmer_pct=80.0, color_percents=(10.0, 20.0, 30.0))
        assert "Attribute 'Dimmer' At 80.0" in plan.commands[0]
        assert "Attribute 'ColorRGB_R' At 10.0" in plan.commands[0]
        assert "Attribute 'ColorRGB_G' At 20.0" in plan.commands[0]
        assert "Attribute 'ColorRGB_B' At 30.0" in plan.commands[0]

    @pytest.mark.parametrize("bad_dimmer", [-1.0, 101.0, "80", True])
    def test_an_out_of_range_or_non_numeric_dimmer_is_refused(self, bad_dimmer):
        with pytest.raises(OverrideLookError):
            _plan(dimmer_pct=bad_dimmer)

    def test_an_out_of_range_color_percent_is_refused(self):
        with pytest.raises(OverrideLookError):
            _plan(color_percents=(101.0, 0.0, 0.0))

    def test_a_wrong_length_color_tuple_is_refused(self):
        with pytest.raises(OverrideLookError):
            _plan(color_percents=(0.0, 0.0))

    @pytest.mark.parametrize("bad_zoom", [float("nan"), float("inf"), -1.0, "5", True])
    def test_a_non_finite_or_negative_or_non_numeric_zoom_is_refused(self, bad_zoom):
        with pytest.raises(OverrideLookError):
            _plan(zoom_degrees=bad_zoom)

    def test_a_geometrically_undefined_target_propagates_the_pointing_error(self):
        # 기구 자리와 타겟이 같으면 방향이 없다 — aim_pan_tilt 의 사유가 그대로
        # 올라온다(이 모듈이 감싸지 않는다).
        with pytest.raises(SpatialPointingError):
            _plan(fixtures=[(1103, (0.0, 0.0, 0.0))], target=PointingTarget(0.0, 0.0, 0.0))


class TestStoreLineMatchesTheGenericBuilder:
    """`preset_store_commands` 가 문형의 유일한 자리다 — 여기서 다시 적지 않는다."""

    def test_the_store_line_matches_the_shared_builder_byte_for_byte(self):
        plan = _plan(pool_no=3, occupied_slots=frozenset({1}), label="Piano Solo")
        assert plan.commands[-2:] == preset_store_commands(3, plan.slot, "Piano Solo")

    def test_a_quoted_label_is_refused_by_the_shared_builder(self):
        with pytest.raises(SpatialPointingError):
            _plan(label="bad'name")


class TestRecommendedSafetyAnswers:
    def test_standard_solo_spot_recommends_everything_on(self):
        assert recommended_safety_answers() == OverrideSafetyAnswers(
            stop_ifx=True, stop_pfx=True, move_in_black=True
        )

    def test_show_movement_recommends_everything_off(self):
        assert recommended_safety_answers(show_movement=True) == OverrideSafetyAnswers(
            stop_ifx=False, stop_pfx=False, move_in_black=False
        )


class TestPlanToDict:
    def test_it_serialises_the_store_slot_and_policy(self):
        plan = _plan(pool_no=5, occupied_slots=frozenset())
        payload = plan.to_dict()
        assert payload["store"] == {"pool": 5, "slot": 1, "policy": "override"}
        assert payload["safety"] == _ALL_ANSWERS_OFF.to_dict()
