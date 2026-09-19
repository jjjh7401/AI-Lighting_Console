from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, fields

import pytest

from server.design.energy import EFFECT_AXIS_CAPABILITY
from server.design.profile import MusicProfile
from server.design.rig import build_rig_profile
from server.design.song_cue_composer import (
    SongCueBundle,
    compose_song_cue_bundle,
)
from server.design.song_plan import (
    ACCENT_AXIS,
    COLOR_USAGE_AXIS,
    POSITION_AXIS,
    AccentDecision,
    ApprovalState,
    DirectorDecision,
    DLevelDecision,
    FxDecision,
    PaletteDecision,
    PositionDecision,
    SectionDecision,
    TextureDecision,
    TimestampedSection,
    TimingPlan,
    UnifiedSongLightingPlan,
    UnresolvedNote,
)


def _rig(*, effect_count: int = 40, layers: bool = True):
    patch = [
        {
            "fid": fid,
            "type_name": "Fixture",
            "capabilities": [EFFECT_AXIS_CAPABILITY],
        }
        for fid in range(1, effect_count + 1)
    ]
    declared_layers = {"key": [1, 2], "back": [3, 4]} if layers else None
    return build_rig_profile(
        patch=patch,
        groups={},
        coords=[],
        declared_layers=declared_layers,
    )


def _section(
    index: int,
    label: str,
    start_ms: int,
    *,
    d_level: int,
    position: str = "Center",
    colors: tuple[str, ...] = ("blue", "white"),
    fx_allowed: tuple[str, ...] = (),
    fx_disabled: tuple[str, ...] = (),
    fx_density: int = 0,
    accents: tuple[str, ...] = (),
    texture: str = "long fade",
    cue_number: int | None = None,
) -> SectionDecision:
    return SectionDecision(
        section=TimestampedSection(index=index, label=label, start_ms=start_ms),
        d=DLevelDecision(level=d_level, source="section_mood"),
        palette=PaletteDecision(colors=colors, source="director"),
        position=PositionDecision(preset=position, source="director"),
        texture=TextureDecision(label=texture, source="genre"),
        fx=FxDecision(
            allowed=fx_allowed,
            disabled=fx_disabled,
            density=fx_density,
        ),
        accent=AccentDecision(accents=accents),
        cue_number=cue_number,
    )


def _plan(
    *,
    sections: tuple[SectionDecision, ...],
    profile: MusicProfile | None = None,
    timing: TimingPlan | None = None,
    rig=None,
    director_decisions: tuple[DirectorDecision, ...] = (),
    unresolved: tuple[UnresolvedNote, ...] = (),
) -> UnifiedSongLightingPlan:
    return UnifiedSongLightingPlan(
        song_title="Composer Test",
        sequence_name="Composer Test Seq",
        sections=sections,
        timing=timing or TimingPlan.timecode(77),
        music_profile=profile or MusicProfile(bpm=120.0, palette=("blue", "white")),
        rig_profile=rig or _rig(),
        approval=ApprovalState.approved(reviewer="LD"),
        director_decisions=director_decisions,
        unresolved=unresolved,
    )


def test_complete_bundle_contains_section_axis_data_and_structured_timing() -> None:
    plan = _plan(
        sections=(
            _section(
                1,
                "Verse",
                0,
                d_level=4,
                position="Center",
                fx_allowed=("dimmer chase", "pan sweep", "color chase"),
                fx_disabled=("strobe",),
                fx_density=3,
                cue_number=101,
            ),
            _section(
                2,
                "Chorus",
                32_100,
                d_level=5,
                position="Center",
                fx_allowed=("dimmer chase", "pan sweep"),
                fx_density=2,
                cue_number=102,
            ),
        )
    )

    result = compose_song_cue_bundle(plan)

    assert result.complete is True
    assert result.bundle is not None
    first, second = result.bundle.cues
    assert first.position.to_dict() == {
        "requested": "Center",
        "stored": "Center",
        "width_tier": "wide",
        "source": "director",
        "mib_premoved_by": None,
    }
    assert first.dimmer.key_pct == pytest.approx(90.0)
    assert first.dimmer.back_pct == pytest.approx(72.0)
    assert first.color.palette == ("blue", "white")
    assert first.color.saturation == "높음"
    assert first.fx.permitted == ("dimmer chase", "pan sweep")
    assert first.fx.disabled == ("strobe", "color chase")
    assert first.fade_seconds == pytest.approx(0.75)
    assert second.timing.to_dict() == {
        "mode": "timecode",
        "trigger": "timecode",
        "start_ms": 32_100,
        "trig_time_seconds": 32.1,
        "timecode_number": 77,
        "follows_cue_number": None,
    }
    assert result.lint_findings == ()
    assert result.disabled_rule_notes == ()


def test_unresolved_and_unconfirmed_director_inputs_return_card_requeries_only() -> None:
    unresolved = UnresolvedNote(
        axis=POSITION_AXIS,
        section_index=1,
        reason="position free text did not match a preset",
        prompt="Ask Q4 again.",
    )
    unconfirmed = DirectorDecision(
        step="Q5_ACCENTS",
        axis=ACCENT_AXIS,
        value=("snare hit",),
        confirmed=False,
        source="auto_draft",
        section_index=1,
        choice_label="snare hit",
    )
    plan = _plan(
        sections=(_section(1, "Verse", 0, d_level=3),),
        unresolved=(unresolved,),
        director_decisions=(unconfirmed,),
    )

    result = compose_song_cue_bundle(plan)

    assert result.complete is False
    assert result.bundle is None
    assert [requirement.axis for requirement in result.requery_requirements] == [
        POSITION_AXIS,
        ACCENT_AXIS,
    ]
    assert result.requery_requirements[0].prompt == "Ask Q4 again."
    assert result.requery_requirements[1].step == "Q5_ACCENTS"
    assert result.lint_findings == ()


def test_color_usage_default_accepted_decision_never_generates_a_requery() -> None:
    """AC-COLORMODE-003 (REQ-010) — a confirmed=True Q2B_COLOR_USAGE decision
    (default-accepted or otherwise) never appears in requery_requirements —
    `_requery_requirements`'s ``if decision.confirmed: continue`` already
    works axis-agnostically (research.md §4)."""
    color_usage = DirectorDecision(
        step="Q2B_COLOR_USAGE",
        axis=COLOR_USAGE_AXIS,
        value="modulate",
        confirmed=True,
        source="default_accepted",
    )
    plan = _plan(
        sections=(_section(1, "Verse", 0, d_level=3),),
        director_decisions=(color_usage,),
    )

    result = compose_song_cue_bundle(plan)

    assert COLOR_USAGE_AXIS not in [requirement.axis for requirement in result.requery_requirements]


def test_lint_findings_and_disabled_rule_notes_are_returned_with_bundle() -> None:
    plan = _plan(
        sections=(_section(1, "Verse", 0, d_level=2, colors=("red",), cue_number=1),),
        profile=MusicProfile(palette=("blue",)),
        rig=_rig(layers=False),
    )

    result = compose_song_cue_bundle(plan)

    assert result.bundle is not None
    assert {finding.rule_id for finding in result.lint_findings} == {"L5"}
    assert {note.rule_id for note in result.disabled_rule_notes} == {"L6", "L7", "L11"}
    assert result.bundle.lint_findings == result.lint_findings
    assert result.bundle.disabled_rule_notes == result.disabled_rule_notes


@pytest.mark.parametrize(
    ("timing", "expected"),
    (
        (
            TimingPlan.manual_go(),
            {
                "mode": "manual_go",
                "trigger": "manual_go",
                "start_ms": 12_500,
                "trig_time_seconds": None,
                "timecode_number": None,
                "follows_cue_number": None,
            },
        ),
        (
            TimingPlan.trig_time(),
            {
                "mode": "trig_time",
                "trigger": "trig_time",
                "start_ms": 12_500,
                "trig_time_seconds": 12.5,
                "timecode_number": None,
                "follows_cue_number": None,
            },
        ),
    ),
)
def test_timing_consumes_plan_payload_semantics_without_rendering(timing, expected) -> None:
    plan = _plan(
        sections=(_section(1, "Drop", 12_500, d_level=4, cue_number=9),),
        timing=timing,
    )

    result = compose_song_cue_bundle(plan)

    assert result.bundle is not None
    assert result.bundle.cues[0].timing.to_dict() == expected


def test_mib_is_modeled_as_inserted_position_only_data_not_console_text() -> None:
    plan = _plan(
        sections=(
            _section(
                1,
                "Blackout",
                0,
                d_level=1,
                position="Center",
                accents=("blackout",),
                cue_number=1,
            ),
            _section(
                2,
                "Reveal",
                10_000,
                d_level=3,
                position="Cross",
                cue_number=2,
            ),
        ),
        timing=TimingPlan.trig_time(),
    )

    result = compose_song_cue_bundle(plan)

    assert result.bundle is not None
    blackout, premove, reveal = result.bundle.cues
    assert blackout.dimmer.blackout is True
    assert [cue.kind for cue in result.bundle.cues] == ["section", "mib_premove", "section"]
    assert premove.cue_number == 1.5
    assert premove.position.stored == "Cross"
    assert premove.dimmer.key_pct is None
    assert premove.fx.permitted == ()
    assert premove.mib.premove is True
    assert premove.timing.to_dict() == {
        "mode": "trig_time",
        "trigger": "follow_previous",
        "start_ms": None,
        "trig_time_seconds": None,
        "timecode_number": None,
        "follows_cue_number": 1.0,
    }
    assert reveal.position.requested == "Cross"
    assert reveal.position.stored is None
    assert reveal.position.mib_premoved_by == 1.5


def test_bundle_is_immutable_and_has_no_console_text_surface() -> None:
    plan = _plan(sections=(_section(1, "Verse", 0, d_level=3, cue_number=1),))
    result = compose_song_cue_bundle(plan)
    assert result.bundle is not None
    payload = json.dumps(result.bundle.to_dict(), ensure_ascii=False, sort_keys=True)

    with pytest.raises(FrozenInstanceError):
        result.bundle.cues[0].dimmer.key_pct = 100.0

    assert "command" not in payload.casefold()
    assert "/" + "merge" not in payload.casefold()
    assert "commands" not in {field.name for field in fields(SongCueBundle)}
