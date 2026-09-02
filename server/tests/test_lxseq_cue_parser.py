"""SPEC-COPILOT-LXSEQ-004 M1 -- CUE-EX parser tests (t209 · t207).

AC-LXSEQ4-002  헤더는 정규 17열 **정확 집합** (모자람 · 남음 둘 다 거부)
AC-LXSEQ4-012  두 갈래가 서로 다른 사유 문자열을 낸다

Lead's pinned contract requires four assertions:
1) sample CSV -> records 89 / cue_numbers 18
2) blank preservation -- blank dim_raw stays "" not "0"
3) LED-W 6 rows -- is_video_call True, kept in records (not dropped)
4) BOM -- first column name reads as "Q#" (not the BOM-prefixed form)

Pure-function verification only. Zero console/network contact.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from server.lxseq.cue_parser import (
    CANONICAL_CUE_COLUMNS,
    CueColumnSetError,
    MissingCueColumnsError,
    UnexpectedCueColumnsError,
    parse_cue_csv,
)

SAMPLE = next(Path("src/Lighting_Designer").glob("03_*Sugar/LXSEQ_SAMPLE_01_Sugar_r3.cue-ex.csv"))

EXPECTED_RECORD_COUNT = 89
EXPECTED_CUE_COUNT = 18
EXPECTED_LED_W_ROWS = 6
BOM = chr(0xFEFF)


def _raw_bytes() -> bytes:
    return SAMPLE.read_bytes()


def _sample_text() -> str:
    return _raw_bytes().decode("utf-8")


def _parsed():
    return parse_cue_csv(_sample_text())


class TestSampleShape:
    def test_the_sample_file_still_carries_a_bom(self):
        assert _raw_bytes()[:3] == b"\xef\xbb\xbf"

    def test_ninety_rows_parse_to_eighty_nine_records(self):
        result = _parsed()
        assert len(result.records) == EXPECTED_RECORD_COUNT
        assert result.rejections == ()

    def test_eighteen_unique_cue_numbers_in_sheet_order(self):
        result = _parsed()
        assert len(result.cue_numbers) == EXPECTED_CUE_COUNT
        assert result.cue_numbers[0] == "Q010"
        assert list(result.cue_numbers) == sorted(
            result.cue_numbers, key=lambda q: int(q.lstrip("Q"))
        )

    def test_every_record_names_one_of_the_eighteen_cues(self):
        result = _parsed()
        cue_set = set(result.cue_numbers)
        assert all(record.cue_no in cue_set for record in result.records)

    def test_every_cue_has_at_least_one_row(self):
        result = _parsed()
        seen = set(record.cue_no for record in result.records)
        assert seen == set(result.cue_numbers)


class TestBlankPreservation:
    def test_a_blank_dim_row_is_the_empty_string_not_zero(self):
        result = _parsed()
        haze_row = next(r for r in result.records if r.group == "HAZE" and r.cue_no == "Q010")
        assert haze_row.dim_raw == "40"
        assert haze_row.col_raw == ""
        assert haze_row.pos_raw == ""

    def test_a_blank_bm_cell_stays_the_empty_string_not_zero(self):
        result = _parsed()
        haze_row = next(r for r in result.records if r.group == "HAZE" and r.cue_no == "Q010")
        assert haze_row.bm_raw == ""
        blank_bm_rows = [r for r in result.records if r.bm_raw == ""]
        filled_bm_rows = [r for r in result.records if r.bm_raw != ""]
        assert blank_bm_rows, "control is vacuous -- no blank BM rows in the sample"
        assert filled_bm_rows, "control is vacuous -- no filled BM rows in the sample"
        assert not any(r.bm_raw == "0" for r in blank_bm_rows)

    def test_fx_off_is_a_real_value_not_a_blank(self):
        result = _parsed()
        off_rows = [r for r in result.records if r.fx_raw == "OFF"]
        blank_fx_rows = [r for r in result.records if r.fx_raw == ""]
        assert all(row.fx_raw == "OFF" for row in off_rows)
        assert all(row.fx_raw == "" for row in blank_fx_rows)


class TestVideoCallFlag:
    def test_led_w_rows_are_flagged_and_counted(self):
        result = _parsed()
        video_rows = [r for r in result.records if r.is_video_call]
        assert len(video_rows) == EXPECTED_LED_W_ROWS
        assert all(r.group == "LED-W" for r in video_rows)

    def test_led_w_rows_are_not_dropped(self):
        result = _parsed()
        led_w_cues = set(r.cue_no for r in result.records if r.group == "LED-W")
        assert led_w_cues <= set(result.cue_numbers)
        assert led_w_cues, "sample carries no LED-W rows -- control is vacuous"

    def test_a_non_video_group_is_not_flagged(self):
        result = _parsed()
        non_video = [r for r in result.records if r.group != "LED-W"]
        assert non_video, "control is vacuous"
        assert all(not r.is_video_call for r in non_video)


class TestBomHandling:
    def test_the_bom_is_stripped_from_the_first_column_name(self):
        result = parse_cue_csv(_sample_text())
        assert result.records[0].cue_no == "Q010"

    def test_without_the_bom_the_same_text_parses_identically(self):
        with_bom = parse_cue_csv(_sample_text())
        without_bom = parse_cue_csv(_sample_text().lstrip(BOM))
        assert with_bom.records == without_bom.records
        assert with_bom.cue_numbers == without_bom.cue_numbers


class TestHeaderValidation:
    def test_missing_columns_is_refused_not_silently_dropped(self):  # AC-LXSEQ4-002
        header = ",".join(c for c in CANONICAL_CUE_COLUMNS if c != "Snap")
        text = header + "\nQ010,BACK,55,,,,,,,,,,,,,\n"
        with pytest.raises(MissingCueColumnsError) as excinfo:
            parse_cue_csv(text)
        assert "Snap" in str(excinfo.value)

    def test_an_extra_column_is_refused_by_name(self):
        """AC-LXSEQ4-002 -- 헤더는 **정확 집합**이다.

        재현(2026-09-01, t207): 고치기 전에는 이 시트가 그대로 통과했다.
        오타 열은 정규 이름이 사라져 모자람 갈래로 이미 잡히므로, 실제로
        노출돼 있던 것은 **덧붙은 열**이다 -- 작성자가 열을 만들고 파이프라인이
        그것을 읽는다고 믿는 경우다. 조용히 무시하면 그 믿음이 무대까지 간다.
        """
        header = ",".join(CANONICAL_CUE_COLUMNS) + ",EXTRA-JUNK"
        text = header + "\nQ010,BACK,55,,,,,,,,,,,,,,x\n"
        with pytest.raises(UnexpectedCueColumnsError) as excinfo:
            parse_cue_csv(text)
        assert "EXTRA-JUNK" in str(excinfo.value)
        assert excinfo.value.unexpected == ("EXTRA-JUNK",)

    def test_both_column_faults_share_one_ancestor(self):
        """규약 §3.2 -- 부르는 쪽이 한 갈래만 잡으면 다른 갈래가 새어나간다.
        `tools.py` 가 조상을 잡으므로 둘 다 조상이어야 한다."""
        assert issubclass(MissingCueColumnsError, CueColumnSetError)
        assert issubclass(UnexpectedCueColumnsError, CueColumnSetError)

    def test_the_two_column_faults_give_different_reason_strings(self):  # AC-LXSEQ4-012
        """AC-LXSEQ4-012 -- 거짓 사유가 참 사유를 가리지 않게 문자열로 가른다."""
        missing = ",".join(c for c in CANONICAL_CUE_COLUMNS if c != "Snap")
        extra = ",".join(CANONICAL_CUE_COLUMNS) + ",EXTRA-JUNK"
        with pytest.raises(CueColumnSetError) as a:
            parse_cue_csv(missing + "\n")
        with pytest.raises(CueColumnSetError) as b:
            parse_cue_csv(extra + "\n")
        assert str(a.value).startswith("missing_columns:")
        assert str(b.value).startswith("unexpected_columns:")
        assert str(a.value) != str(b.value)

    def test_column_order_does_not_matter(self):
        reversed_columns = tuple(reversed(CANONICAL_CUE_COLUMNS))
        header = ",".join(reversed_columns)
        values = {"Q#": "Q010", "Group": "BACK"}
        row = ",".join(values.get(col, "") for col in reversed_columns)
        text = header + "\n" + row + "\n"
        result = parse_cue_csv(text)
        assert len(result.records) == 1
        assert result.records[0].cue_no == "Q010"
        assert result.records[0].group == "BACK"


class TestRowRejection:
    def test_an_empty_cue_number_is_rejected_not_dropped_silently(self):
        header = ",".join(CANONICAL_CUE_COLUMNS)
        text = header + "\n" + ",".join([""] + ["BACK"] + [""] * 15) + "\n"
        result = parse_cue_csv(text)
        assert result.records == ()
        assert len(result.rejections) == 1
        assert result.rejections[0].reason == "cue_no_empty"

    def test_an_empty_group_is_rejected_not_dropped_silently(self):
        header = ",".join(CANONICAL_CUE_COLUMNS)
        text = header + "\n" + ",".join(["Q010"] + [""] + [""] * 15) + "\n"
        result = parse_cue_csv(text)
        assert result.records == ()
        assert len(result.rejections) == 1
        assert result.rejections[0].reason == "group_empty"
