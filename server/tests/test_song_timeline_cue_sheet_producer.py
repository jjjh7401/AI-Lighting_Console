"""t283 — 서버가 t279 의 큐시트 필드를 **실제로 채우는지** 재는 시험.

t279 는 모델만 넓혔고 채우는 자리가 없었다(그 회차 보고: "No producer fills
these fields"). 여기서 재는 것은 `server.web.session._song_timeline_payload`
가 내보내는 페이로드 그 자체다 — 모델이 값을 담을 수 **있다**가 아니라, 서버가
값을 담아 **보낸다**.

원칙은 하나다: 없는 것보다 틀린 것이 나쁘다. 그래서 "안 채운 필드는 키가 없다"
쪽도 같은 무게로 잰다.
"""

from __future__ import annotations

import json

from server.design.energy import EFFECT_AXIS_CAPABILITY
from server.design.profile import MusicProfile
from server.design.rig import build_rig_profile
from server.design.song_cue_composer import compose_song_cue_bundle
from server.design.song_plan import (
    AccentDecision,
    ApprovalState,
    CueSheetSectionFields,
    CueSheetViewFields,
    DLevelDecision,
    FxDecision,
    PaletteDecision,
    PositionDecision,
    SectionDecision,
    TextureDecision,
    TimestampedSection,
    TimingPlan,
    UnifiedSongLightingPlan,
    apply_cue_sheet_section,
    apply_cue_sheet_view,
)
from server.web.session import _song_timeline_payload


def _rig():
    patch = [
        {"fid": fid, "type_name": "Fixture", "capabilities": [EFFECT_AXIS_CAPABILITY]}
        for fid in range(1, 41)
    ]
    return build_rig_profile(
        patch=patch,
        groups={},
        coords=[],
        declared_layers={"key": [1, 2], "back": [3, 4]},
    )


def _section(
    index: int,
    label: str,
    start_ms: int,
    *,
    d_level: int,
    colors: tuple[str, ...] = ("hot_pink", "gold_amber"),
    fx_allowed: tuple[str, ...] = (),
    fx_density: int = 0,
    position: str = "Center",
) -> SectionDecision:
    return SectionDecision(
        section=TimestampedSection(
            index=index, label=label, start_ms=start_ms, source="song_design_interview"
        ),
        d=DLevelDecision(level=d_level, source="section_mood"),
        palette=PaletteDecision(colors=colors, source="director"),
        position=PositionDecision(preset=position, source="director"),
        texture=TextureDecision(label="long fade", source="genre"),
        fx=FxDecision(allowed=fx_allowed, density=fx_density),
        accent=AccentDecision(),
        cue_number=index * 10,
    )


def _plan(
    *,
    sections: tuple[SectionDecision, ...] | None = None,
    profile: MusicProfile | None = None,
    timing: TimingPlan | None = None,
) -> UnifiedSongLightingPlan:
    return UnifiedSongLightingPlan(
        song_title="Sugar",
        sequence_name="Sugar Seq",
        sections=sections
        or (
            _section(1, "INTRO", 0, d_level=2),
            _section(2, "VERSE1", 8000, d_level=3),
            _section(
                3,
                "CHORUS1",
                40000,
                d_level=5,
                fx_allowed=("dimmer chase",),
                fx_density=2,
            ),
        ),
        timing=timing or TimingPlan.timecode(77),
        music_profile=profile or MusicProfile(bpm=120.0, meter="4/4", key_mode="D♭ major"),
        rig_profile=_rig(),
        approval=ApprovalState.approved(reviewer="LD"),
    )


_LAYER_MAPPING = ({"role": "back", "group_no": 5, "group_name": "BACK"},)


def _payload(plan: UnifiedSongLightingPlan | None = None, **kwargs) -> dict:
    plan = plan or _plan()
    return _song_timeline_payload(
        plan,
        compose_song_cue_bundle(plan),
        lifecycle=kwargs.pop("lifecycle", "pending_approval"),
        sequence_no=1,
        layer_mapping=kwargs.pop("layer_mapping", _LAYER_MAPPING),
        **kwargs,
    )


class TestEmittedViewFields:
    def test_the_header_carries_the_declared_tempo_meter_and_key(self) -> None:
        payload = _payload()

        assert payload["bpm"] == 120.0
        assert payload["time_signature"] == "4/4"
        assert payload["musical_key"] == "D♭ major"

    def test_seconds_per_bar_is_computed_from_bpm_and_meter(self) -> None:
        payload = _payload()

        # 4박 × 60/120 = 2.000s — 정본 산출물의 "1마디 2.000s" 와 같은 값.
        assert payload["seconds_per_bar"] == 2.0

    def test_an_undeclared_tempo_leaves_tempo_derived_fields_absent(self) -> None:
        payload = _payload(_plan(profile=MusicProfile(meter="4/4")))

        # `effective_bpm` 이 120 을 답하지만 그것은 **기본값**이라 안 싣는다.
        assert "bpm" not in payload
        assert "seconds_per_bar" not in payload
        assert all("bar_start" not in section for section in payload["sections"])

    def test_an_unreadable_meter_leaves_the_bar_math_absent(self) -> None:
        payload = _payload(_plan(profile=MusicProfile(bpm=120.0, meter="free")))

        assert payload["bpm"] == 120.0
        assert "seconds_per_bar" not in payload
        assert all("bar_count" not in section for section in payload["sections"])

    def test_fields_with_no_producer_stay_absent(self) -> None:
        payload = _payload()

        for absent in (
            "total_duration_ms",
            "bar_count",
            "tc_source",
            "tc_origin",
            "palette_legend",
        ):
            assert absent not in payload, absent


class TestTcMethodHonesty:
    def test_interview_sourced_times_report_derived_with_the_warning(self) -> None:
        payload = _payload()

        assert payload["tc_method"] == "DERIVED"
        assert "음원 청취로 검증하지 않았습니다" in payload["tc_method_warning"]

    def test_measured_sources_report_measured_and_carry_no_warning(self) -> None:
        measured = tuple(
            SectionDecision(
                section=TimestampedSection(
                    index=decision.section.index,
                    label=decision.section.label,
                    start_ms=decision.section.start_ms,
                    source="confirmed_song_analysis",
                ),
                d=decision.d,
                palette=decision.palette,
                position=decision.position,
                texture=decision.texture,
                fx=decision.fx,
                accent=decision.accent,
                cue_number=decision.cue_number,
            )
            for decision in _plan().sections
        )

        payload = _payload(_plan(sections=measured))

        assert payload["tc_method"] == "MEASURED"
        assert "tc_method_warning" not in payload

    def test_one_unmeasured_section_makes_the_whole_timeline_derived(self) -> None:
        base = _plan().sections
        mixed = (
            SectionDecision(
                section=TimestampedSection(
                    index=1, label="INTRO", start_ms=0, source="confirmed_song_analysis"
                ),
                d=base[0].d,
                palette=base[0].palette,
                position=base[0].position,
                texture=base[0].texture,
                fx=base[0].fx,
                accent=base[0].accent,
                cue_number=base[0].cue_number,
            ),
            base[1],
        )

        assert _payload(_plan(sections=mixed))["tc_method"] == "DERIVED"


class TestEmittedSectionFields:
    def test_end_and_duration_come_from_the_next_sections_start(self) -> None:
        sections = _payload()["sections"]

        assert sections[0]["end_ms"] == 8000
        assert sections[0]["duration_ms"] == 8000
        assert sections[1]["end_ms"] == 40000
        assert sections[1]["duration_ms"] == 32000

    def test_the_last_section_has_no_end_because_nothing_gives_the_songs_length(
        self,
    ) -> None:
        last = _payload()["sections"][-1]

        assert "end_ms" not in last
        assert "duration_ms" not in last
        assert "bar_count" not in last

    def test_bars_are_counted_from_the_tempo(self) -> None:
        sections = _payload()["sections"]

        # 2.000s/마디: 0s → 1마디째, 8s → 5마디째, 40s → 21마디째.
        assert [section["bar_start"] for section in sections] == [1, 5, 21]
        assert sections[0]["bar_count"] == 4
        assert sections[1]["bar_count"] == 16

    def test_palette_carries_the_colour_values_the_plan_actually_holds(self) -> None:
        first = _payload()["sections"][0]

        assert first["palette_primary"] == "hot_pink"
        assert first["palette_secondary"] == "gold_amber"

    def test_a_single_colour_palette_leaves_the_secondary_absent(self) -> None:
        plan = _plan(sections=(_section(1, "INTRO", 0, d_level=2, colors=("amber",)),))

        first = _payload(plan)["sections"][0]

        assert first["palette_primary"] == "amber"
        assert "palette_secondary" not in first

    def test_intensity_reports_the_composed_key_and_back_levels(self) -> None:
        sections = _payload()["sections"]

        # D2 / D3 / D5 가 각각 만들어 낸 조도. 값을 그대로 박아 두는 이유는,
        # 큐에서 다시 계산해 비교하면 계산이 틀려도 시험이 같이 틀리기 때문이다.
        assert [section["intensity"] for section in sections] == [
            [{"group": "KEY", "level": 50}, {"group": "BACK", "level": 40}],
            [{"group": "KEY", "level": 70}, {"group": "BACK", "level": 56}],
            [{"group": "KEY", "level": 100}, {"group": "BACK", "level": 80}],
        ]

    def test_fixture_groups_name_the_console_group_the_cue_addresses(self) -> None:
        first = _payload()["sections"][0]

        assert first["fixture_groups"] == ["BACK"]

    def test_without_a_confirmed_layer_mapping_no_group_is_claimed(self) -> None:
        first = _payload(layer_mapping=())["sections"][0]

        assert "fixture_groups" not in first

    def test_movement_comes_from_the_composed_position(self) -> None:
        assert [section["movement"] for section in _payload()["sections"]] == [
            "Center",
            "Center",
            "Center",
        ]

    def test_effect_lists_the_permitted_fx_and_is_absent_when_there_are_none(
        self,
    ) -> None:
        sections = _payload()["sections"]

        assert "effect" not in sections[0]
        assert "effect" not in sections[1]
        assert sections[2]["effect"] == "dimmer chase"

    def test_trans_reads_fade_when_the_cue_actually_fades(self) -> None:
        assert [section["trans"] for section in _payload()["sections"]] == [
            "FADE",
            "FADE",
            "FADE",
        ]

    def test_trans_reads_snap_when_the_director_set_the_fade_to_zero(self) -> None:
        base = _section(1, "CHORUS1", 0, d_level=5)
        snap = SectionDecision(
            section=base.section,
            d=base.d,
            palette=base.palette,
            position=base.position,
            texture=base.texture,
            fx=base.fx,
            accent=base.accent,
            cue_number=base.cue_number,
            fade_override=0.0,
        )

        first = _payload(_plan(sections=(snap,)))["sections"][0]

        assert first["fade_seconds"] == 0
        assert first["trans"] == "SNAP"

    def test_manual_is_flagged_only_under_a_manual_go_timing_plan(self) -> None:
        auto = _payload()["sections"][0]
        manual = _payload(_plan(timing=TimingPlan.manual_go()))["sections"][0]

        assert "manual" not in auto
        assert manual["manual"] is True

    def test_fields_with_no_producer_stay_absent(self) -> None:
        for section in _payload()["sections"]:
            assert "mood" not in section
            assert "note" not in section


class TestAbsentPathStaysByteIdentical:
    def test_an_empty_extension_changes_no_byte_of_the_payload(self) -> None:
        payload = _payload()
        sections = payload["sections"]
        before = json.dumps(payload, ensure_ascii=False, sort_keys=True)

        merged = apply_cue_sheet_view(payload, CueSheetViewFields())
        merged["sections"] = [
            apply_cue_sheet_section(section, CueSheetSectionFields()) for section in sections
        ]

        assert json.dumps(merged, ensure_ascii=False, sort_keys=True) == before

    def test_the_legacy_keys_are_untouched_by_the_extension(self) -> None:
        payload = _payload()

        for key in (
            "song_title",
            "sequence_name",
            "sequence_number",
            "timing_mode",
            "lifecycle",
            "approval",
            "lint",
            "unresolved",
            "disabled",
            "readback",
            "console_stored",
            "warnings",
            "layer_mapping",
            "preset_start",
        ):
            assert key in payload, key
        for key in (
            "index",
            "label",
            "start_ms",
            "cue_number",
            "plan_status",
            "d_level",
            "palette",
            "position",
            "texture",
            "fx",
            "accents",
            "mib",
        ):
            assert key in payload["sections"][0], key
