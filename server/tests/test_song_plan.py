from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, dataclass

import pytest

from server.design.profile import MusicProfile
from server.design.rig import build_rig_profile
from server.design.song_plan import (
    ACCENT_AXIS,
    APPROVAL_APPROVED,
    D_AXIS,
    MANUAL_GO,
    PALETTE_AXIS,
    POSITION_AXIS,
    TIMECODE,
    TRIG_TIME,
    AccentDecision,
    ApprovalState,
    CueTimingPayload,
    DirectorDecision,
    DLevelDecision,
    FxDecision,
    PaletteDecision,
    PositionDecision,
    SectionDecision,
    SongPlanError,
    TextureDecision,
    TimestampedSection,
    TimingPlan,
    UnifiedSongLightingPlan,
    UnresolvedNote,
)


@dataclass(frozen=True)
class FakeChoice:
    label: str


@dataclass(frozen=True)
class FakeAnswerRecord:
    step: str
    choice: FakeChoice | None
    free_text: str | None
    value: object
    confirmed: bool
    source: str


def _section_decision(
    index: int,
    label: str,
    start_ms: int,
    *,
    cue_number: int | None = None,
) -> SectionDecision:
    return SectionDecision(
        section=TimestampedSection(index=index, label=label, start_ms=start_ms),
        d=DLevelDecision(level=index + 2, source="section_mood"),
        palette=PaletteDecision(colors=("blue", "warm white"), source="director"),
        position=PositionDecision(
            preset="Center",
            source="director",
            candidates=("Center", "Vocal DSC"),
        ),
        texture=TextureDecision(label="long fade", source="genre"),
        fx=FxDecision(allowed=("dimmer chase",), disabled=("strobe",), density=1),
        accent=AccentDecision(
            accents=("snare hit",),
            hits=({"at_ms": start_ms + 500, "label": "snare"},),
        ),
        cue_number=cue_number,
    )


def _plan(
    *,
    timing: TimingPlan | None = None,
    approval: ApprovalState | None = None,
    director_decisions: tuple[DirectorDecision, ...] = (),
    unresolved: tuple[UnresolvedNote, ...] = (),
) -> UnifiedSongLightingPlan:
    return UnifiedSongLightingPlan(
        song_title="Test Song",
        sequence_name="Test Song Unified",
        sections=(
            _section_decision(1, "Verse", 0, cue_number=11),
            _section_decision(2, "Chorus", 64321, cue_number=12),
        ),
        timing=timing or TimingPlan.timecode(901),
        music_profile=MusicProfile(bpm=128, genre="rock", concept="neon"),
        rig_profile=build_rig_profile((), {}, ()),
        approval=approval or ApprovalState.draft(),
        director_decisions=director_decisions,
        unresolved=unresolved,
    )


def test_decisions_are_frozen_and_nested_sequences_are_tuples() -> None:
    decision = _section_decision(1, "Verse", 0)

    assert decision.palette.colors == ("blue", "warm white")
    assert decision.position.candidates == ("Center", "Vocal DSC")
    assert decision.accent.hits[0]["label"] == "snare"

    with pytest.raises(FrozenInstanceError):
        decision.d.level = 4

    with pytest.raises(TypeError):
        decision.accent.hits[0]["label"] = "kick"


def test_timecode_mode_projects_absolute_trigtime_and_timecode_without_commands() -> None:
    plan = _plan(timing=TimingPlan.timecode(901), approval=ApprovalState.approved(reviewer="LD"))
    payloads = plan.cue_payloads()

    assert plan.ready_for_commit is True
    assert payloads[0].cue_number == 11
    assert payloads[1].to_dict()["timing"] == {
        "mode": TIMECODE,
        "start_ms": 64321,
        "manual_go": False,
        "trig_time_seconds": 64.321,
        "timecode_number": 901,
    }
    for payload in payloads:
        rendered = payload.to_dict()
        assert "commands" not in rendered
        assert "command" not in json.dumps(rendered)


def test_manual_go_mode_keeps_timestamps_for_review_without_auto_timing() -> None:
    plan = _plan(timing=TimingPlan.manual_go())
    timing = plan.cue_payloads()[1].timing

    assert timing.mode == MANUAL_GO
    assert timing.start_ms == 64321
    assert timing.manual_go is True
    assert timing.trig_time_seconds is None
    assert timing.timecode_number is None


def test_trigtime_mode_is_distinct_from_timecode_mode() -> None:
    plan = _plan(timing=TimingPlan.trig_time())
    timing = plan.cue_payloads()[1].timing

    assert timing.mode == TRIG_TIME
    assert timing.manual_go is False
    assert timing.trig_time_seconds == pytest.approx(64.321)
    assert timing.timecode_number is None


def test_timing_contract_rejects_mixed_modes() -> None:
    with pytest.raises(SongPlanError):
        TimingPlan(mode=TRIG_TIME, timecode_number=7)

    with pytest.raises(SongPlanError):
        TimingPlan.timecode(0)

    with pytest.raises(SongPlanError):
        CueTimingPayload(mode=MANUAL_GO, start_ms=0, manual_go=False)

    with pytest.raises(SongPlanError):
        CueTimingPayload(mode=MANUAL_GO, start_ms=0, manual_go=True, trig_time_seconds=1.0)


def test_director_audit_projection_keeps_confirmed_and_draft_decisions_separate() -> None:
    confirmed = DirectorDecision(
        step="Q2_PALETTE",
        axis=PALETTE_AXIS,
        value=("blue", "white"),
        confirmed=True,
        source="option",
        choice_label="blue and white",
    )
    draft = DirectorDecision(
        step="Q5_TEXTURE",
        axis=ACCENT_AXIS,
        value="recommended hit pattern",
        confirmed=False,
        source="auto_draft",
        section_index=2,
    )
    plan = _plan(
        approval=ApprovalState.approved(reviewer="LD"),
        director_decisions=(confirmed, draft),
    )
    projection = plan.director_review_projection()

    assert plan.has_unconfirmed_director_decisions is True
    assert plan.ready_for_review is True
    assert plan.ready_for_commit is False
    assert projection["approval"]["status"] == APPROVAL_APPROVED
    assert projection["director_decisions"][0]["confirmed"] is True
    assert projection["director_decisions"][1]["confirmed"] is False


def test_unresolved_notes_block_review_and_commit_even_when_approved() -> None:
    unresolved = UnresolvedNote(
        axis=POSITION_AXIS,
        section_index=2,
        reason="free text did not match a position preset",
        prompt="Ask Q4 again",
    )
    plan = _plan(approval=ApprovalState.approved(reviewer="LD"), unresolved=(unresolved,))
    projection = plan.director_review_projection()

    assert plan.has_unresolved is True
    assert plan.ready_for_review is False
    assert plan.ready_for_commit is False
    assert projection["unresolved"] == [unresolved.to_dict()]


def test_projecting_from_answer_record_does_not_import_session_or_interview_code() -> None:
    record = FakeAnswerRecord(
        step="Q3_CLIMAX",
        choice=FakeChoice(label="Ring In peak"),
        free_text=None,
        value={"d_level": 5, "positions": ("Ring In",)},
        confirmed=True,
        source="option",
    )

    decision = DirectorDecision.from_audit_record(record, axis=D_AXIS, section_index=2)

    assert decision.to_dict() == {
        "step": "Q3_CLIMAX",
        "axis": D_AXIS,
        "section_index": 2,
        "value": {"d_level": 5, "positions": ["Ring In"]},
        "confirmed": True,
        "source": "option",
        "free_text": None,
        "choice_label": "Ring In peak",
    }


def test_plan_validation_requires_typed_sections_unique_cues_and_ordered_timestamps() -> None:
    with pytest.raises(SongPlanError):
        DLevelDecision(level=6, source="section_mood")

    with pytest.raises(SongPlanError):
        PaletteDecision(colors=(), source="director")

    with pytest.raises(SongPlanError):
        SectionDecision(
            section=TimestampedSection(index=1, label="Verse", start_ms=0),
            d=object(),
            palette=PaletteDecision(colors=("blue",), source="director"),
            position=PositionDecision(preset="Center", source="director"),
            texture=TextureDecision(label="long fade", source="genre"),
            fx=FxDecision(),
            accent=AccentDecision(),
        )

    with pytest.raises(SongPlanError):
        UnifiedSongLightingPlan(
            song_title="Out of Order",
            sections=(
                _section_decision(1, "Chorus", 1000),
                _section_decision(2, "Verse", 0),
            ),
            timing=TimingPlan.manual_go(),
            music_profile=MusicProfile(),
            rig_profile=build_rig_profile((), {}, ()),
        )

    with pytest.raises(SongPlanError):
        UnifiedSongLightingPlan(
            song_title="Duplicate Cue",
            sections=(
                _section_decision(1, "Verse", 0, cue_number=1),
                _section_decision(2, "Chorus", 1000, cue_number=1),
            ),
            timing=TimingPlan.manual_go(),
            music_profile=MusicProfile(),
            rig_profile=build_rig_profile((), {}, ()),
        )
