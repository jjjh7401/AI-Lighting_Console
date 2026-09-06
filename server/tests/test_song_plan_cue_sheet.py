"""LX-SEQ 큐시트 모델 확장 (t279 M1).

두 축을 잰다:

1. **추가만, 변형 없음** -- 새 필드를 하나도 담지 않은 기존 페이로드는
   확장분을 떼었다 다시 붙여도 JSON 바이트가 같아야 한다. 이게 깨지면
   저장된 타임라인과 기존 테스트가 조용히 달라진다.
2. **정본 산출물을 실을 수 있다** -- `LXSEQ_SAMPLE_01_Sugar_r3.timeline.html`
   의 Q050(CHORUS1) 한 행을 그대로 채워 왕복시킨다.
"""

from __future__ import annotations

import json

import pytest

from server.design.song_plan import (
    CueSheetSectionFields,
    CueSheetViewFields,
    GroupIntensity,
    PaletteEntry,
    SongPlanError,
    apply_cue_sheet_section,
    apply_cue_sheet_view,
    extract_cue_sheet_section,
    extract_cue_sheet_view,
)

# 확장 이전에 서버가 내보내던 모양 그대로 (server/web/session.py _song_timeline_payload).
LEGACY_SECTION: dict[str, object] = {
    "index": 5,
    "label": "CHORUS1",
    "start_ms": 56000,
    "cue_number": 50,
    "plan_status": "draft",
    "d_level": 5,
    "palette": ["hot_pink", "gold_amber"],
    "position": "front_wash",
    "texture": "open",
    "fx": ["chase"],
    "fade_seconds": None,
    "accents": [],
    "mib": False,
    "trig_time_seconds": None,
}

LEGACY_VIEW: dict[str, object] = {
    "song_title": "Sugar",
    "sequence_name": None,
    "sequence_number": 1,
    "timing_mode": "manual_go",
    "timecode_number": None,
    "lifecycle": "draft",
    "approval": "draft",
    "sections": [LEGACY_SECTION],
    "lint": [],
    "unresolved": [],
    "disabled": [],
}


class TestLegacyPayloadRoundTrip:
    """새 필드가 하나도 없는 페이로드는 왕복해도 바이트가 같다."""

    def test_a_section_without_new_fields_round_trips_byte_identically(self):
        before = json.dumps(LEGACY_SECTION, ensure_ascii=False, sort_keys=True)

        extracted = extract_cue_sheet_section(LEGACY_SECTION)
        restored = apply_cue_sheet_section(LEGACY_SECTION, extracted)

        assert extracted.is_empty
        assert json.dumps(restored, ensure_ascii=False, sort_keys=True) == before

    def test_a_view_without_new_fields_round_trips_byte_identically(self):
        before = json.dumps(LEGACY_VIEW, ensure_ascii=False, sort_keys=True)

        extracted = extract_cue_sheet_view(LEGACY_VIEW)
        restored = apply_cue_sheet_view(LEGACY_VIEW, extracted)

        assert extracted.is_empty
        assert json.dumps(restored, ensure_ascii=False, sort_keys=True) == before

    def test_an_empty_extension_adds_no_keys(self):
        assert CueSheetSectionFields().to_dict() == {}
        assert CueSheetViewFields().to_dict() == {}
        # 확장분이 비면 원본 키 집합이 그대로다 (덧붙지도, 지워지지도 않는다).
        assert set(apply_cue_sheet_section(LEGACY_SECTION, CueSheetSectionFields())) == set(
            LEGACY_SECTION
        )


class TestFullyPopulatedSection:
    """정본 산출물 Q050 (CHORUS1, 00:56.0 -> 01:12.0) 한 행."""

    @staticmethod
    def q050() -> CueSheetSectionFields:
        return CueSheetSectionFields(
            end_ms=72000,
            duration_ms=16000,
            bar_start=29,
            bar_count=16,
            mood="개방, 축제",
            palette_primary="P4 핫핑크",
            palette_secondary="P1 골드앰버",
            intensity=(GroupIntensity(group="ALL", level=90),),
            fixture_groups=("MOVER-U", "MOVER-D", "BACK", "WASH-D"),
            movement="FAN-OUT @mid",
            effect="CHASE @1/8",
            trans="SNAP",
            fade_seconds=0.0,
            note="후렴 첫 박 정확히 · 1차 웨이브 정점",
            manual=False,
        )

    def test_it_carries_every_cue_sheet_column(self):
        merged = apply_cue_sheet_section(LEGACY_SECTION, self.q050())

        assert merged["end_ms"] == 72000
        assert merged["duration_ms"] == 16000
        assert merged["bar_count"] == 16
        assert merged["mood"] == "개방, 축제"
        assert merged["palette_primary"] == "P4 핫핑크"
        assert merged["palette_secondary"] == "P1 골드앰버"
        assert merged["intensity"] == [{"group": "ALL", "level": 90}]
        assert merged["fixture_groups"] == ["MOVER-U", "MOVER-D", "BACK", "WASH-D"]
        assert merged["movement"] == "FAN-OUT @mid"
        assert merged["effect"] == "CHASE @1/8"
        assert merged["trans"] == "SNAP"
        assert merged["fade_seconds"] == 0.0
        assert merged["manual"] is False
        # 기존 필드는 그대로 남는다.
        assert merged["label"] == "CHORUS1"
        assert merged["d_level"] == 5

    def test_it_survives_a_json_round_trip(self):
        merged = apply_cue_sheet_section(LEGACY_SECTION, self.q050())
        decoded = json.loads(json.dumps(merged, ensure_ascii=False))

        assert extract_cue_sheet_section(decoded) == self.q050()

    def test_per_group_intensity_reads_the_q020_shape(self):
        # Q020 은 그룹별로 갈린다: KEY 70 / BACK 35.
        fields = CueSheetSectionFields(
            intensity=(
                GroupIntensity(group="KEY", level=70),
                GroupIntensity(group="BACK", level=35),
            )
        )
        assert fields.to_dict()["intensity"] == [
            {"group": "KEY", "level": 70},
            {"group": "BACK", "level": 35},
        ]


class TestViewHeaderMeta:
    def test_it_carries_the_header_and_the_provenance_banner(self):
        fields = CueSheetViewFields(
            bpm=120,
            time_signature="4/4",
            musical_key="D♭ major",
            total_duration_ms=236000,
            bar_count=118,
            seconds_per_bar=2.0,
            tc_source="LTC",
            tc_origin="00:00.0 = 곡 첫 음 (카운트인 없음)",
            tc_method="DERIVED",
            tc_method_warning="마디 연산으로 도출한 값입니다. 음원 청취로 검증하지 않았습니다.",
            palette_legend=(
                PaletteEntry(id="P1", name="골드 앰버", color="#FFB43C"),
                PaletteEntry(id="P4", name="핫 핑크", color="#FF3C9E"),
            ),
        )
        merged = apply_cue_sheet_view(LEGACY_VIEW, fields)

        assert merged["bpm"] == 120
        assert merged["tc_method"] == "DERIVED"
        assert merged["tc_source"] == "LTC"
        assert merged["seconds_per_bar"] == 2.0
        assert merged["palette_legend"][0] == {
            "id": "P1",
            "name": "골드 앰버",
            "color": "#FFB43C",
        }
        assert extract_cue_sheet_view(json.loads(json.dumps(merged, ensure_ascii=False))) == fields


class TestValidation:
    def test_it_rejects_an_out_of_range_group_level(self):
        with pytest.raises(SongPlanError):
            GroupIntensity(group="KEY", level=101)

    def test_it_rejects_a_blank_palette_name(self):
        with pytest.raises(SongPlanError):
            PaletteEntry(id="P1", name="  ", color="#FFB43C")

    def test_it_rejects_a_negative_duration(self):
        with pytest.raises(SongPlanError):
            CueSheetSectionFields(duration_ms=-1)

    def test_it_rejects_a_non_string_mood(self):
        with pytest.raises(SongPlanError):
            CueSheetSectionFields(mood=42)  # type: ignore[arg-type]
