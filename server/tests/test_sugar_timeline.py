"""정본 Sugar 큐시트가 모델을 통과하고, 라이브러리 시드로 앱에 실리는지."""

from __future__ import annotations

import json

from server.design.song_plan import (
    apply_cue_sheet_section,
    apply_cue_sheet_view,
    extract_cue_sheet_section,
    extract_cue_sheet_view,
)
from server.design.sugar_timeline import (
    SUGAR_ENTRY_ID,
    SUGAR_TIMELINE_NAME,
    build_sugar_timeline,
    sugar_library_entry,
)
from server.web.timeline_library import SongTimelineLibrary, timeline_entry_summary


def test_eighteen_cues_q010_to_q180() -> None:
    sections = build_sugar_timeline()["sections"]
    assert len(sections) == 18
    assert [section["cue_number"] for section in sections] == list(range(10, 190, 10))
    assert [section["label"] for section in sections][:2] == ["INTRO", "VERSE1"]
    assert sections[-1]["label"] == "OUTRO"


def test_header_meta_matches_the_source_document() -> None:
    timeline = build_sugar_timeline()
    assert timeline["bpm"] == 120
    assert timeline["time_signature"] == "4/4"
    assert timeline["musical_key"] == "D♭ major"
    assert timeline["total_duration_ms"] == 236_000  # 03:56.0
    assert timeline["bar_count"] == 118
    assert timeline["seconds_per_bar"] == 2.0
    assert timeline["tc_source"] == "LTC"
    assert timeline["tc_origin"] == "00:00.0 = 곡 첫 음 (카운트인 없음)"


def test_tc_method_is_derived_with_its_warning() -> None:
    """계산으로 얻은 타임코드를 실측처럼 보여선 안 된다."""
    timeline = build_sugar_timeline()
    assert timeline["tc_method"] == "DERIVED"
    assert "마디 연산" in str(timeline["tc_method_warning"])
    assert "LTC 대조" in str(timeline["tc_method_warning"])


def test_manual_rows_are_the_two_the_document_marks() -> None:
    sections = build_sugar_timeline()["sections"]
    manual = [section["cue_number"] for section in sections if section["manual"]]
    assert manual == [10, 180]
    for section in sections:
        if section["manual"]:
            assert str(section["note"]).startswith("[MANUAL]")


def test_last_cue_leaves_the_blank_columns_absent() -> None:
    """정본 표에서 Q180 의 TC Out / Dur 은 `—` 다 — 값을 만들지 않는다."""
    last = build_sugar_timeline()["sections"][-1]
    assert last["cue_number"] == 180
    assert "end_ms" not in last
    assert "duration_ms" not in last
    assert "bar_count" not in last


def test_sections_are_contiguous_on_two_second_bars() -> None:
    sections = build_sugar_timeline()["sections"]
    for section, following in zip(sections, sections[1:], strict=False):
        assert section["end_ms"] == following["start_ms"]
        assert section["bar_start"] + section["bar_count"] == following["bar_start"]


def test_every_section_round_trips_through_the_cue_sheet_model() -> None:
    """t279 모델이 18행을 손실 없이 싣는다 (모든 확장 필드 왕복)."""
    for section in build_sugar_timeline()["sections"]:
        fields = extract_cue_sheet_section(section)
        assert apply_cue_sheet_section(section, fields) == section


def test_view_fields_round_trip_through_the_model() -> None:
    timeline = build_sugar_timeline()
    fields = extract_cue_sheet_view(timeline)
    assert fields.tc_method == "DERIVED"
    assert len(fields.palette_legend) == 7
    assert apply_cue_sheet_view(timeline, fields) == timeline


def test_payload_is_json_serialisable() -> None:
    """라이브러리는 JSON 파일에 그대로 얹힌다 — 직렬화 왕복이 동일해야 한다."""
    entry = sugar_library_entry()
    assert json.loads(json.dumps(entry, ensure_ascii=False)) == entry


def test_library_seeds_the_entry_when_the_file_is_missing(tmp_path) -> None:
    library = SongTimelineLibrary(tmp_path / "absent.json", seed=(sugar_library_entry(),))
    items = library.items()
    assert [item["id"] for item in items] == [SUGAR_ENTRY_ID]
    assert timeline_entry_summary(items[0]) == {
        "id": SUGAR_ENTRY_ID,
        "name": SUGAR_TIMELINE_NAME,
        "saved_at": items[0]["saved_at"],
        "song_title": SUGAR_TIMELINE_NAME,
        "sequence_number": 0,
        "lifecycle": "pending_approval",
        "section_count": 18,
    }


def test_library_seed_survives_a_corrupt_file(tmp_path) -> None:
    """읽기 경로의 fail-open 은 그대로 — 깨진 파일도 예외 없이 시드만 남는다."""
    path = tmp_path / "library.json"
    path.write_text("{ not json", encoding="utf-8")
    library = SongTimelineLibrary(path, seed=(sugar_library_entry(),))
    assert [item["id"] for item in library.items()] == [SUGAR_ENTRY_ID]


def test_a_saved_entry_with_the_same_id_wins_over_the_seed(tmp_path) -> None:
    path = tmp_path / "library.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "entries": [
                    {"id": SUGAR_ENTRY_ID, "name": "감독이 고친 판", "timeline": {"sections": []}}
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    library = SongTimelineLibrary(path, seed=(sugar_library_entry(),))
    entries = library.items()
    assert len(entries) == 1
    assert entries[0]["name"] == "감독이 고친 판"


def test_seed_is_oldest_so_saved_versions_list_first(tmp_path) -> None:
    library = SongTimelineLibrary(tmp_path / "library.json", seed=(sugar_library_entry(),))
    library.save("나중 판", {"sections": []})
    assert [item["name"] for item in library.items()] == ["나중 판", SUGAR_TIMELINE_NAME]


def test_library_without_seed_is_unchanged(tmp_path) -> None:
    assert SongTimelineLibrary(tmp_path / "library.json").items() == []
    assert SongTimelineLibrary().items() == []
