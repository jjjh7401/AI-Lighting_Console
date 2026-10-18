"""서브 지오메트리 밝기 — 기종 판독으로 본 「서브 광원에 밝기가 있는 줄」의 선택 꼴(1018 aura 기록).

본체 그룹 선택(``Group 4``)은 서브 광원의 밝기를 열지 못했다(t520 실기). 서브 광원에 밝기가 실린
기종의 줄만 뒤 점 범위(``Fixture 201 Thru 212.``)로 고른다 — 본체와 서브를 함께 고른다.
"""

from __future__ import annotations

from server.design.beat_grid_emit import SongTiming, _cue_attribute_commands
from server.design.beat_grid_stage import mark_sub_selection_tracks
from server.design.capability_join import FixtureCapability
from server.design.preset_plan import LoveAttackPlan, PlanPreset, save_commands
from server.prechk.capability_read import AxisRange


def _cap(fid: int, channels: tuple[tuple[str, str], ...]) -> FixtureCapability:
    """``(채널 이름, 속성)`` 목록으로 만든 능력 — 채널 이름이 지오메트리 접두를 싣는다."""
    axes = tuple(AxisRange(attribute=attr, channel_name=name) for name, attr in channels)
    return FixtureCapability(
        fid=fid,
        type_slot=8,
        type_name="T",
        mode_slot=1,
        mode_name="M",
        mode_width=None,
        channel_count=len(axes),
        axes=axes,
    )


_AURA = (
    ("Main Module_Pan", "Pan"),
    ("Main Module_Tilt", "Tilt"),
    ("Main Module_Dimmer", "Dimmer"),
    ("Aura_Dimmer", "Dimmer"),
    ("Aura_ColorRGB_R", "ColorRGB_R"),
)
_BODY_ONLY = (("Main Module_Pan", "Pan"), ("Main Module_Dimmer", "Dimmer"))


def test_a_dimmer_on_a_sub_geometry_is_a_sub_geometry_dimmer() -> None:
    assert _cap(201, _AURA).sub_geometry_dimmer is True


def test_a_dimmer_only_on_the_body_is_not_a_sub_geometry_dimmer() -> None:
    assert _cap(201, _BODY_ONLY).sub_geometry_dimmer is False


def test_without_a_pan_or_tilt_body_no_sub_geometry_dimmer_is_claimed() -> None:
    # 본체를 가릴 수 없으면 「서브에 밝기가 있다」고 단정하지 않는다.
    assert _cap(201, (("Aura_Dimmer", "Dimmer"),)).sub_geometry_dimmer is False


def test_a_contiguous_line_with_a_sub_dimmer_gets_the_dot_range() -> None:
    tracks = [{"group_name": "BACK"}]
    members = {"BACK": list(range(201, 213))}
    capabilities = {fid: _cap(fid, _AURA) for fid in range(201, 213)}
    marked = mark_sub_selection_tracks(tracks, members, capabilities)
    assert marked[0]["sub_selection"] == "Fixture 201 Thru 212."


def test_a_line_without_a_sub_dimmer_or_a_contiguous_run_keeps_the_group_form() -> None:
    tracks = [{"group_name": "FOH"}, {"group_name": "SIDE-ALL"}, {"group_name": "ONE"}]
    members = {"FOH": [101, 102], "SIDE-ALL": [301, 303], "ONE": [501]}
    capabilities = {
        101: _cap(101, _BODY_ONLY),
        102: _cap(102, _BODY_ONLY),
        301: _cap(301, _AURA),
        303: _cap(303, _AURA),
        501: _cap(501, _AURA),
    }
    marked = mark_sub_selection_tracks(tracks, members, capabilities)
    assert ["sub_selection" in track for track in marked] == [False, False, False]


def test_the_input_tracks_are_not_changed_by_the_sub_selection_mark() -> None:
    tracks = [{"group_name": "BACK"}]
    mark_sub_selection_tracks(
        tracks, {"BACK": [201, 202]}, {201: _cap(201, _AURA), 202: _cap(202, _AURA)}
    )
    assert tracks == [{"group_name": "BACK"}]


_TIMING = SongTiming(bpm=120.0, beats_per_bar=4, downbeat_bar1_seconds=0.0)
_CUE = {"bar": 1, "brightness": {"mode": "value", "value_percent": 60}}


def test_a_dimmer_value_line_uses_the_sub_selection_when_given() -> None:
    commands, reason = _cue_attribute_commands(
        _CUE,
        group_name="BACK",
        group_no=4,
        timing=_TIMING,
        dimmer_attributes={"BACK": ("Dimmer",)},
        brightness_selection="Fixture 201 Thru 212.",
    )
    assert reason is None
    assert commands == ("Fixture 201 Thru 212. ; Attribute 'Dimmer' At 60",)


def test_a_dimmer_value_line_keeps_the_group_form_without_a_sub_selection() -> None:
    commands, reason = _cue_attribute_commands(
        _CUE,
        group_name="BACK",
        group_no=4,
        timing=_TIMING,
        dimmer_attributes={"BACK": ("Dimmer",)},
    )
    assert reason is None
    assert commands == ("Group 4 ; Attribute 'Dimmer' At 60",)


def test_channels_without_a_geometry_prefix_never_make_a_sub_geometry_dimmer() -> None:
    # 채널 이름이 속성 이름뿐이면 지오메트리를 모른다 — 「Pan」과 「Dimmer」를 서로 다른
    # 지오메트리로 읽어 서브 밝기를 지어내면 안 된다.
    assert _cap(201, (("Pan", "Pan"), ("Dimmer", "Dimmer"))).sub_geometry_dimmer is False


def _dimmer_store(selection: str | None) -> PlanPreset:
    return PlanPreset(
        kind="dimmer",
        value="60%",
        name="BACK 60",
        slot="2.5",
        cells=(),
        groups=("BACK",),
        ready=True,
        hold=None,
        value_percent=60,
        group_no=4,
        attributes=("Dimmer",),
        group_nos=(4,),
        selection=selection,
    )


def test_a_single_group_dimmer_store_selects_the_dot_range_when_it_has_one() -> None:
    plan = LoveAttackPlan(presets=(_dimmer_store("Fixture 201 Thru 212."),), unresolved=(), kept=())
    lines = save_commands(plan)
    assert "Fixture 201 Thru 212. ; Attribute 'Dimmer' At 60" in lines
    assert not any(line.startswith("Group 4 ; Attribute") for line in lines)


def test_a_single_group_dimmer_store_keeps_the_group_form_without_a_selection() -> None:
    plan = LoveAttackPlan(presets=(_dimmer_store(None),), unresolved=(), kept=())
    assert "Group 4 ; Attribute 'Dimmer' At 60" in save_commands(plan)
