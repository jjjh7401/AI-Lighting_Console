"""안전 큐 시험 — SPEC-LDDESIGN-001 M5 (REQ-LDDESIGN-068~069, 070, 카드 t438).

description.describe() 는 M2 에서 이미 만들어졌다(수정하지 않는다,
REQ-070) — 이 파일은 M5 안전 큐 상태에 대해 그것이 동작함을 증명하는
시험만 추가한다.
"""

from __future__ import annotations

from server.concept.cue_model import CueState
from server.concept.description import describe
from server.concept.resolver import apply, compute_headroom
from server.concept.safety import first_safety_cue, last_safety_cue

ALL_GROUPS = (
    "KEY",
    "FOH",
    "BACK",
    "SIDE-L",
    "SIDE-R",
    "WASH-U",
    "WASH-D",
    "MOVER-U",
    "MOVER-D",
)


class TestFirstSafetyCue:
    """REQ-LDDESIGN-068 — Q0.5, Block, 최소 조명, 기본 색, 포지션 홈."""

    def test_tracking_is_block(self):
        cue = first_safety_cue(default_color="Blue")
        assert cue["tracking"] == "block"

    def test_resolves_to_minimum_light_default_color_and_home(self):
        cue = first_safety_cue(default_color="Blue", min_dimmer=10, min_group="KEY")
        state = apply(CueState(dim={}, color=None, pos="front", motion=2), cue["ops"], {})
        assert state.dim == {"KEY": 10}
        assert state.color == "Blue"
        assert state.pos == "home"
        assert state.motion == 0

    def test_min_dimmer_and_group_are_overridable(self):
        cue = first_safety_cue(default_color="Red", min_dimmer=15, min_group="FOH")
        state = apply(CueState(dim={}, color=None, pos="home", motion=0), cue["ops"], {})
        assert state.dim == {"FOH": 15}

    def test_description_reports_minimum_brightness(self):
        """REQ-070 — description 이 M5 안전 큐에서도 동작한다."""
        cue = first_safety_cue(default_color="Blue", min_dimmer=10, min_group="KEY")
        prev = CueState(dim={}, color=None, pos="home", motion=0)
        state = apply(prev, cue["ops"], {})
        headroom = compute_headroom(
            state, all_groups=ALL_GROUPS, reserved_colors_remaining=[], reserved_effects=[]
        )
        description = describe(prev, state, cue["ops"], headroom)
        assert description != ""
        assert "최대 10%" in description


class TestLastSafetyCue:
    """REQ-LDDESIGN-069 — 모든 그룹을 끄고(reduce factor=0) Release."""

    def test_tracking_is_release(self):
        cue = last_safety_cue(ref="ALL_GROUPS_BASE")
        assert cue["tracking"] == "release"

    def test_ops_use_reduce_factor_zero(self):
        cue = last_safety_cue(ref="ALL_GROUPS_BASE")
        assert cue["ops"] == [{"op": "reduce", "factor": 0.0, "ref": "ALL_GROUPS_BASE"}]

    def test_resolves_all_groups_to_zero_via_apply(self):
        """제약 6 — reduce factor=0 은 기존 apply() 를 통해 해석돼야 한다
        (유효한 ref/구간 기준을 골라서 시험한다)."""
        base = CueState(
            dim={group: 60 for group in ALL_GROUPS}, color="White", pos="front", motion=2
        )
        prev = CueState(
            dim={group: 60 for group in ALL_GROUPS}, color="White", pos="front", motion=2
        )
        cue = last_safety_cue(ref="ALL_GROUPS_BASE")
        state = apply(prev, cue["ops"], {"ALL_GROUPS_BASE": base})
        assert set(state.dim) == set(ALL_GROUPS)
        assert all(value == 0 for value in state.dim.values())

    def test_description_reports_all_off(self):
        """REQ-070 — description 이 M5 안전 큐(마지막)에서도 동작한다."""
        base = CueState(
            dim={group: 60 for group in ALL_GROUPS}, color="White", pos="front", motion=2
        )
        prev = CueState(
            dim={group: 60 for group in ALL_GROUPS}, color="White", pos="front", motion=2
        )
        cue = last_safety_cue(ref="ALL_GROUPS_BASE")
        state = apply(prev, cue["ops"], {"ALL_GROUPS_BASE": base})
        headroom = compute_headroom(
            state, all_groups=ALL_GROUPS, reserved_colors_remaining=[], reserved_effects=[]
        )
        description = describe(prev, state, cue["ops"], headroom)
        assert "최대 0%" in description
