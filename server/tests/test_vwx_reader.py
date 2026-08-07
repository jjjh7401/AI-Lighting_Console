"""server/vwx/reader.py 판독 테스트 (M1 — AC-VWX-002~005). 문서 근거 · 실물 미검증.

fixture 이름은 ``design.md`` §6.1을 따른다.
"""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

import pytest

from server.vwx import reader
from server.vwx.reader import (
    PATH_A,
    PATH_B,
    READ_FAILURE_BLOCK_UNDETECTED,
    READ_FAILURE_ENCODING,
    READ_FAILURE_MALFORMED_CSV,
    READ_FAILURE_NOT_PATCH_SOURCE,
    READ_FAILURE_UNAPPROVED_DEPENDENCY,
    READ_FAILURE_WORKSHEET_SUBTOTAL,
    _looks_binary,
    read,
)

#: 실물 음성 사례 픽스처 — drop.dk 리깅 하중 CSV. Vectorworks export가 아니다
#: (server/tests/fixtures/vwx/README.md 참조). REQ-VWX-003·결함 1·결함 2 회귀
#: 테스트 전용이며 M0(실물 Vectorworks 샘플 확보)의 산출물이 아니다.
_REAL_NEGATIVE_SAMPLE_PATH = (
    Path(__file__).parent / "fixtures" / "vwx" / "drop_dk_rigging_not_a_vectorworks_export.csv"
)


def _real_negative_sample_bytes() -> bytes:
    return _REAL_NEGATIVE_SAMPLE_PATH.read_bytes()


_HEADER_A = "Instrument Type\tUnit Number\tUniverse\tDMX Address\tUID"
_ROWS_A = [
    "Robe Robin MMX Spot\t1\t1\t1\tA100",
    "Robe Robin MMX Spot\t2\t1\t5\tA101",
    "Martin MAC Aura\t3\t1\t9\tA102",
]


def clean_export_a() -> bytes:
    """경로 A tab-text, 헤더 있음, 정상 3행 (설계 §6.1)."""
    return "\n".join([_HEADER_A, *_ROWS_A]).encode("utf-8")


def worksheet_with_subtotals() -> bytes:
    """제목행 + 헤더행 + 데이터행 + 소계행이 섞인 워크시트 export (경로 B).

    소계행은 헤더 컬럼 수(4)와 다른 필드 수(2)를 가져 구조적으로 감지된다.
    """
    lines = [
        "Instrument Data",  # 제목행 — 별칭 매칭 0
        "Instrument Type,Unit Number,Universe,DMX Address",  # DB 헤더행
        "Robe Robin MMX Spot,1,1,1",
        "Robe Robin MMX Spot,2,1,5",
        "Totals,2",  # 소계행 — 필드 수가 다르다(구조적 감지 대상)
    ]
    return "\n".join(lines).encode("utf-8")


def instrument_summary_only() -> bytes:
    """주소 열이 아예 없는 Instrument Summary류 요약(REQ-VWX-003)."""
    lines = [
        "Instrument Type,Symbol Name,Quantity",
        "Robe Robin MMX Spot,MMX_SPOT,12",
        "Martin MAC Aura,MAC_AURA,8",
    ]
    return "\n".join(lines).encode("utf-8")


class TestPathATabDelimited:
    """AC-VWX-002 — 경로 A(tab-text) 판독."""

    def test_headered_tab_text_is_read_by_tab_delimiter_regardless_of_extension(self):
        result = read(clean_export_a())
        assert result.path_kind == PATH_A
        assert len(result.records) == 3
        assert result.records[0]["Instrument Type"] == "Robe Robin MMX Spot"
        assert not result.read_failures

    def test_headerless_tab_text_is_still_read_structurally(self):
        """헤더 없는(체크박스 미선택) 경로 A 파일도 예외 없이 판독된다."""
        data = "\n".join(_ROWS_A).encode("utf-8")
        result = read(data)
        assert result.path_kind == PATH_A
        assert len(result.records) == 3
        # 위치 기반 "의미" 해석은 하지 않는다 — 자리표시자 키만 부여된다.
        assert set(result.records[0]) == {"col_0", "col_1", "col_2", "col_3", "col_4"}

    def test_comma_inside_a_tab_delimited_value_is_not_mistaken_for_the_delimiter(self):
        """AC-VWX-002 ② — .txt 확장자에 값 안에 comma가 있어도 tab이 구분자다."""
        header = "Instrument Type\tUnit Number\tUniverse\tDMX Address"
        row = "Robe, Robin MMX Spot\t1\t1\t1"
        data = f"{header}\n{row}".encode()
        result = read(data)
        assert result.path_kind == PATH_A
        assert len(result.records) == 1
        # comma가 필드를 쪼개지 않고 온전히 한 필드로 보존됐다(비공허성).
        assert result.records[0]["Instrument Type"] == "Robe, Robin MMX Spot"
        assert "," in result.records[0]["Instrument Type"]

    def test_auto_added_uid_column_is_recognized(self):
        """AC-VWX-002 ③ — 경로 A 자동 추가 UID 컬럼이 uid 별칭으로 인식된다."""
        from server.vwx.columns import resolve_header

        result = read(clean_export_a())
        assert "UID" in result.header
        assert resolve_header("UID") == "uid"
        assert result.records[0]["UID"] == "A100"

    def test_extension_alone_never_decides_the_delimiter(self):
        """뮤테이션 ① 대응 — 확장자를 무시하고 내용 구조로만 구분자를 정한다."""
        # 순수 comma 파일이 tab 없이도 comma 구분자로 정확히 판독된다(경로 B류).
        header = "Instrument Type,Unit Number,Universe,DMX Address"
        row = "Robe Robin MMX Spot,1,1,1"
        data = f"{header}\n{row}".encode()
        result = read(data)
        assert len(result.records) == 1
        assert result.records[0]["Instrument Type"] == "Robe Robin MMX Spot"


class TestPathBWorksheetBlockDetection:
    """AC-VWX-003 — 경로 B(워크시트) 데이터 블록 구조적 식별."""

    def test_title_and_subtotal_rows_are_excluded_from_records(self):
        result = worksheet_with_subtotals_result()
        assert result.path_kind == PATH_B
        assert len(result.records) == 2
        assert all(record["Instrument Type"].startswith("Robe") for record in result.records)

    def test_subtotal_row_is_reported_as_a_structured_failure_not_dropped_silently(self):
        result = worksheet_with_subtotals_result()
        kinds = {failure.kind for failure in result.read_failures}
        assert READ_FAILURE_WORKSHEET_SUBTOTAL in kinds

    def test_undetectable_header_returns_empty_records_with_a_reason_not_a_guess(self):
        """AC-VWX-003 ② — 헤더를 못 찾으면 예외 없이 빈 레코드 + 사유를 반환한다."""
        # 여러 컬럼(tab 구분)이지만 폭이 들쭉날쭉하고 별칭에 전혀 매칭되지
        # 않는다 — 경로 A의 "flat 균일 테이블" 시그니처가 아니므로 headerless
        # 경로 A 폴백도 타지 않고, 진짜 데이터 블록 미탐으로 분류돼야 한다.
        lines = ["random\tjunk\teven more", "whatever\tnoise", "foo\tbar\tbaz\tqux"]
        data = "\n".join(lines).encode()
        result = read(data)
        assert result.records == ()
        assert len(result.read_failures) == 1
        assert result.read_failures[0].kind == READ_FAILURE_BLOCK_UNDETECTED
        # 비공허성 — 임의 추측으로 블록을 자른 지점이 0건임을 레코드 0건으로 확인.
        assert result.records == ()


def worksheet_with_subtotals_result() -> reader.ReadResult:
    return read(worksheet_with_subtotals())


class TestInstrumentSummaryRejection:
    """AC-VWX-004 — Instrument Summary(주소 열 없음) 거부."""

    def test_a_file_with_no_address_family_column_is_rejected_as_not_a_patch_source(self):
        result = read(instrument_summary_only())
        assert result.records == ()
        assert len(result.read_failures) == 1
        failure = result.read_failures[0]
        assert failure.kind == READ_FAILURE_NOT_PATCH_SOURCE
        assert "패치 출처 아님" in failure.detail

    def test_a_normal_file_is_never_misclassified_as_instrument_summary(self):
        """뮤테이션 ② 대응 + 비공허성 — 정상 파일에서 오발동하지 않는다."""
        result = read(clean_export_a())
        kinds = {failure.kind for failure in result.read_failures}
        assert READ_FAILURE_NOT_PATCH_SOURCE not in kinds
        assert len(result.records) > 0


class TestEncodingFallbackChain:
    """AC-VWX-005 — 인코딩 폴백 + 명시적 실패."""

    def test_each_encoding_in_the_chain_round_trips_korean_position_names(self):
        header = "Instrument Type\tUnit Number\tUniverse\tDMX Address\tPosition"
        row = "Robe Robin MMX Spot\t1\t1\t1\t무대 좌측"
        text = f"{header}\n{row}"
        for encoding in ("utf-8-sig", "utf-16", "cp1252", "mac_roman"):
            # cp1252/mac_roman cannot represent Hangul; use utf-8-sig content for
            # those but exercise the BOM/utf-16 paths with real Korean bytes.
            if encoding in ("cp1252", "mac_roman"):
                continue
            data = text.encode(encoding)
            result = read(data)
            assert result.path_kind == PATH_A
            assert result.records[0]["Position"] == "무대 좌측"
            assert result.encoding == encoding

    def test_cp1252_and_mac_roman_are_reachable_fallback_targets(self):
        header = "Instrument Type\tUnit Number\tUniverse\tDMX Address\tPosition"
        row = "Robe Robin MMX Spot\t1\t1\t1\tCafe"
        text = f"{header}\n{row}"
        for encoding in ("cp1252", "mac_roman"):
            data = text.encode(encoding)
            result = read(data)
            assert result.path_kind == PATH_A
            assert result.records[0]["Position"] == "Cafe"

    def test_all_five_encodings_failing_returns_an_explicit_failure_with_byte_offset(self):
        """뮤테이션 ③ 대응 — 모지바케를 조용히 통과시키지 않는다.

        0xFF는 utf-8 계열을 깨고, 홀수 길이는 utf-16을 깨고, 0x81은 cp1252에서
        미정의라 cp1252를 깬다. mac_roman은 모든 바이트를 매핑하므로 성공하지만
        디코딩 결과에 NUL 문자(원본 0x00 바이트, 오프셋 2)가 살아남아
        "이진 내용"으로 거부된다 — 5종 전부 실패.
        """
        data = bytes([0xFF, 0x81, 0x00, 0x02, 0xFE])
        result = read(data)
        assert result.records == ()
        assert len(result.read_failures) == 1
        failure = result.read_failures[0]
        assert failure.kind == READ_FAILURE_ENCODING
        assert "바이트 오프셋 2" in failure.detail


class TestInstrumentSummaryDoesNotBlockNormalXlsx:
    """xlsx 분기 스모크 — openpyxl 승인 반영(§C v0.1.1)."""

    def test_openpyxl_parses_a_real_xlsx_workbook(self):
        openpyxl = __import__("openpyxl")
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(["Instrument Type", "Unit Number", "Universe", "DMX Address"])
        sheet.append(["Robe Robin MMX Spot", 1, 1, 1])
        sheet.append(["Martin MAC Aura", 2, 1, 5])
        import io

        buffer = io.BytesIO()
        workbook.save(buffer)
        result = read(buffer.getvalue())
        assert len(result.records) == 2
        assert result.records[0]["Instrument Type"] == "Robe Robin MMX Spot"

    def test_unapproved_openpyxl_dependency_produces_a_structured_failure(self):
        """§D 퇴화 케이스 — openpyxl 미승인 상태에서 .xlsx 제공."""
        data = b"PK\x03\x04" + b"\x00" * 20
        result = read(data, _openpyxl_available=False)
        assert result.records == ()
        assert result.read_failures[0].kind == READ_FAILURE_UNAPPROVED_DEPENDENCY
        assert "미승인 의존성" in result.read_failures[0].detail


class TestNewlineVariantsNeverEscapeAsExceptions:
    """결함 1(P0) 회귀 — CR 전용/CRLF/LF 전부 예외 없이 구조화된 결과를 낸다.

    수정 전 코드는 CR 전용(classic Mac) 텍스트를 ``io.StringIO``에
    ``newline=''`` 없이 넘겨 ``csv.reader``가 ``_csv.Error: new-line
    character seen in unquoted field``를 던졌다 — 예외가 ``read()`` 호출자
    (툴 핸들러)까지 그대로 탈출했다. 비공허성: 이 테스트들은 수정 전 커밋에서
    반드시 실패했다(``_csv.Error``가 그대로 전파되어 ``pytest``가 테스트
    함수 실행 자체를 에러로 표시함).
    """

    _HEADER = "Instrument Type,Unit Number,Universe,DMX Address"
    _ROW = "Robe Robin MMX Spot,1,1,1"

    def test_cr_only_classic_mac_newlines_never_raise(self):
        data = f"{self._HEADER}\r{self._ROW}".encode()
        result = read(data)  # 예외를 던지면 이 테스트 자체가 실패한다.
        assert len(result.records) == 1
        assert result.records[0]["Instrument Type"] == "Robe Robin MMX Spot"

    def test_crlf_newlines_never_raise(self):
        data = f"{self._HEADER}\r\n{self._ROW}".encode()
        result = read(data)
        assert len(result.records) == 1
        assert result.records[0]["Instrument Type"] == "Robe Robin MMX Spot"

    def test_lf_newlines_never_raise(self):
        data = f"{self._HEADER}\n{self._ROW}".encode()
        result = read(data)
        assert len(result.records) == 1
        assert result.records[0]["Instrument Type"] == "Robe Robin MMX Spot"

    def test_the_three_newline_variants_produce_identical_records(self):
        """비공허성 — 세 변형이 실제로 동일한 판독 산출을 낸다(우연히 통과가 아님)."""
        variants = {
            "CR": f"{self._HEADER}\r{self._ROW}".encode(),
            "CRLF": f"{self._HEADER}\r\n{self._ROW}".encode(),
            "LF": f"{self._HEADER}\n{self._ROW}".encode(),
        }
        results = {name: read(data) for name, data in variants.items()}
        for name, result in results.items():
            assert len(result.records) == 1, name
            assert result.records[0]["Instrument Type"] == "Robe Robin MMX Spot", name

    def test_csv_layer_exception_is_converted_to_a_structured_read_failure(self, monkeypatch):
        """결함 1 ② — 정규화 이후에도 csv가 거부하는 입력은 예외가 아니라 구조화된 실패다.

        정규화만으로는 막을 수 없는 csv 예외(예: 따옴표 불균형)를 강제로
        재현하기 위해 ``csv.reader``를 몽키패치해 ``csv.Error``를 던지게 한다
        — 이 테스트는 "모든 입력이 우연히 정규화로 해결됐다"는 거짓양성을
        배제한다(비공허성).
        """
        import csv as csv_module

        def _always_raises_csv_error(*args, **kwargs):
            raise csv_module.Error("synthetic malformed csv for test")

        monkeypatch.setattr(csv_module, "reader", _always_raises_csv_error)
        data = f"{self._HEADER}\n{self._ROW}".encode()
        result = read(data)  # 예외를 던지면 이 테스트 자체가 실패한다.
        assert result.records == ()
        assert result.read_failures[0].kind == READ_FAILURE_MALFORMED_CSV
        assert "synthetic malformed csv" in result.read_failures[0].detail


class TestDelimiterTieBreakPrefersMultiColumnStructure:
    """결함 2(P0) 부수 결함 회귀 — 별칭 점수 동점 시 다중 컬럼 구조를 우선한다.

    수정 전 코드는 ``("\\t", ",")`` 순회에서 tab을 먼저 시도하고 ``score >
    best[3]``(엄격한 초과)만으로 갱신했다 — 별칭 매칭이 전부 0으로 동점이면
    tab이 최초 채택된 채로 절대 교체되지 않았다. comma로 쪼개면 진짜 다중
    컬럼 구조가 나오는 파일도 tab 순회 우선순위 때문에 단일 컬럼(col_0)
    쓰레기 구조로 오분류됐다.
    """

    def test_real_world_rigging_csv_is_not_misparsed_as_single_column_tab_data(self):
        """실물 픽스처(드롭.dk 리깅 CSV) — 별칭 매칭 0으로 동점이어도 comma의
        5컬럼 구조가 tab의 1컬럼 구조보다 우선 채택된다(비공허성 — 실제로
        구분자가 바뀌었음을 내부 헬퍼로 직접 확인)."""
        text = _real_negative_sample_bytes().decode("utf-8-sig").replace("\r", "\n")
        delimiter, rows, header_index, score = reader._choose_delimiter(text)
        assert delimiter == ","
        assert score == 0  # 별칭 매칭 자체가 없다 — 그래도 comma가 이겨야 한다.
        assert reader._uniform_width(rows)
        assert len(rows[0]) == 5  # Name,PT-NAME,X_Coordinate,Y_Coordinate,LOAD

    def test_tie_break_falls_back_to_widest_consistent_delimiter_when_both_score_zero(self):
        """합성 재현 — tab 없는 순수 comma 다중열 데이터에서 tab이 잘못 채택되지 않는다."""
        text = "aaa,bbb,ccc\nddd,eee,fff\n"  # 별칭 매칭 0, comma로 쪼개야 3컬럼.
        delimiter, rows, header_index, score = reader._choose_delimiter(text)
        assert delimiter == ","
        assert len(rows[0]) == 3


class TestRealWorldNonPatchSourceIsRejectedStructurally:
    """결함 2(P0) 회귀 — 실물 음성 사례가 "정상 결과"로 위장하지 않는다.

    수정 전 코드는 이 파일을 (tie-break 결함으로) 단일 컬럼 ``col_0`` 데이터로
    오판독해 120개의 개별 ``min_record_incomplete`` 실패를 만들면서도,
    ``designed_rig.fixture_count: 0`` + ``diffs`` 전부 빈 배열을 반환해
    "도면과 콘솔이 일치"로 오독될 수 있는 정상-형태 페이로드를 냈다. 수정 후에는
    ① 예외가 없고 ② 단일 구조화된 거부(주소 계열 컬럼 0개)로 명확히 보고된다.
    """

    def test_real_negative_sample_is_rejected_not_silently_accepted(self):
        data = _real_negative_sample_bytes()
        result = read(data)  # 예외를 던지면 이 테스트 자체가 실패한다(결함 1).

        # 비공허성 — 픽스처 자체가 실제로 주소 계열 컬럼을 하나도 갖지 않음을
        # 먼저 확인한다(거부가 우연이 아니라 파일 특성 때문임을 증명).
        header_line = data.decode("utf-8-sig").splitlines()[0]
        from server.vwx.columns import has_address_family

        assert not has_address_family(header_line.split(","))

        assert result.records == ()
        assert len(result.read_failures) == 1  # 120개 개별 실패가 아니라 단일 구조화 거부.
        failure = result.read_failures[0]
        assert failure.kind in {READ_FAILURE_BLOCK_UNDETECTED, READ_FAILURE_NOT_PATCH_SOURCE}
        assert failure.detail  # 사유가 실려 있다 — 빈 문자열이 아니다.

    def test_tool_level_payload_never_reports_zero_diffs_as_a_clean_match(self):
        """R End-to-end에 준하는 검증 — reader→columns→address→rig 파이프라인 전체가
        일관되게 판독 실패를 신호하고, 위장된 "차이 없음" 을 만들지 않는다."""
        from server.vwx.address import resolve_all
        from server.vwx.columns import resolve_columns
        from server.vwx.rig import build_designed_rig

        data = _real_negative_sample_bytes()
        result = read(data)
        column_records, column_failures, _column_excluded = resolve_columns(list(result.records))
        resolved_records, address_failures = resolve_all(column_records)
        designed_rig = build_designed_rig(resolved_records)

        all_failures = (*result.read_failures, *column_failures, *address_failures)
        assert len(designed_rig.fixtures) == 0
        # 픽스처 0대 자체는 정상일 수 있으나(빈 도면), 이 경우는 판독 실패가
        # 동반되어야 "차이 없음"으로 오독되지 않는다 — 비공허성 핵심 assert.
        assert len(all_failures) >= 1


# --- round17 판독 수치 경계 전수 (AddressGates) ---
#
# round17 HARD 규율 1 — 게이트가 모듈 경계에서 멈추지 않게 `server/vwx/` **전 모듈**의
# 수치 경계 자리를 격리 사본 뮤테이션으로 훑었고(레지스트리는
# `test_vwx_address.py::_R17_VWX_BOUNDARY_SITES`), `reader.py`에서 무대조군 3자리가
# 나왔다: `_looks_binary`의 제어문자 임계 `ord(ch) < 32` · 비율 임계 `> 0.1` ·
# `_extract_data_block`의 폭 일치 `len(row) == width`.


class _BinarySniffRow(NamedTuple):
    control_ord: int
    control_count: int
    filler_count: int
    looks_binary: bool
    note: str


#: 제어문자 임계(32)·비율 임계(0.1)·제외 화이트스페이스(`\t\n\r`)·NUL 단락의 **양끝**.
#: 비율은 `control_count / (control_count + filler_count)`로 손계산한 값이다.
_R17_BINARY_SNIFF_ROWS: tuple[_BinarySniffRow, ...] = (
    _BinarySniffRow(0x00, 1, 19, True, "NUL 한 개면 비율과 무관하게 이진(단락 분기)"),
    _BinarySniffRow(0x01, 1, 9, False, "비율 정확히 0.1 — 임계는 초과여야 한다"),
    _BinarySniffRow(0x01, 3, 17, True, "비율 0.15 — 임계 바로 위"),
    _BinarySniffRow(0x09, 10, 10, False, "탭은 제어문자에서 제외된다"),
    _BinarySniffRow(0x0A, 10, 10, False, "LF는 제어문자에서 제외된다"),
    _BinarySniffRow(0x0D, 10, 10, False, "CR은 제어문자에서 제외된다"),
    _BinarySniffRow(0x1F, 1, 9, False, "0x1F는 제어문자지만 비율이 임계 이하"),
    _BinarySniffRow(0x1F, 3, 17, True, "0x1F는 제어문자다 — 임계 32의 바로 아래 칸"),
    _BinarySniffRow(0x1F, 5, 20, True, "0x1F 비율 0.2"),
    _BinarySniffRow(0x20, 10, 10, False, "공백(0x20)은 제어문자가 아니다 — 임계 32의 바로 위 칸"),
)

#: 표에서 파생하지 **않은** 독립 커버리지 요구.
_R17_REQUIRED_SNIFF_ORDS = frozenset({0x00, 0x01, 0x09, 0x0A, 0x0D, 0x1F, 0x20})


def _r17_sniff_text(row: _BinarySniffRow) -> str:
    return chr(row.control_ord) * row.control_count + "A" * row.filler_count


class TestRound17BinarySniffBoundaries:
    """[round17] `_looks_binary`의 두 임계(제어문자 코드 32 · 비율 0.1) 경계 전수."""

    def test_the_table_covers_both_thresholds_at_both_ends(self):
        """[round17 표 전수] 행을 지우면 행수·코드 커버리지·비율 커버리지 중 하나가 깨진다."""
        assert len(_R17_BINARY_SNIFF_ROWS) == 10, "행수 리터럴 — 행 삭제/추가 감지"
        assert {row.control_ord for row in _R17_BINARY_SNIFF_ROWS} == _R17_REQUIRED_SNIFF_ORDS
        # 제어문자 임계의 **양끝**(0x1F·0x20)이 둘 다 있어야 `< 32`가 고정된다.
        assert {0x1F, 0x20} <= {row.control_ord for row in _R17_BINARY_SNIFF_ROWS}
        # 비율 임계의 **양끝**(정확히 0.1 · 0.1 초과)이 둘 다 있어야 `> 0.1`이 고정된다.
        ratios = {
            row.control_count / (row.control_count + row.filler_count)
            for row in _R17_BINARY_SNIFF_ROWS
        }
        assert 0.1 in ratios, "비율 정확히 0.1인 행이 사라졌다 — `>=`로 바꿔도 안 잡힌다"
        assert any(0.1 < ratio < 0.2 for ratio in ratios), "0.1과 0.2 사이 행이 사라졌다"
        # 비공허성 — 두 결론이 모두 표에 있다.
        assert {row.looks_binary for row in _R17_BINARY_SNIFF_ROWS} == {True, False}

    @pytest.mark.parametrize(
        "row", _R17_BINARY_SNIFF_ROWS, ids=lambda r: f"x{r.control_ord:02X}n{r.control_count}"
    )
    def test_each_boundary_decides_as_declared(self, row):
        """[round17] `reader.py`의 `ord(ch) < 32`를 `< 31`로 바꾸면 0x1F 행 둘이 실패한다.
        `< 33`으로 바꾸면 0x20 행이 실패한다. `> 0.1`을 `> 0.2`로 바꾸면 비율 0.15 행
        둘이 실패한다. `>= 0.1`로 바꾸면 비율 0.1 행 둘이 실패한다. 제외 목록
        `"\\t\\n\\r"`에서 한 글자라도 빼면 해당 행이 실패한다. `"\\x00" in text` 단락
        분기를 지우면 NUL 행(비율 0.05)이 실패한다."""
        assert _looks_binary(_r17_sniff_text(row)) is row.looks_binary, row.note

    def test_the_threshold_is_reachable_through_the_public_read_entrypoint(self):
        """[round17 도달성] `_looks_binary`가 죽은 코드가 아님을 공개 진입점에서 보인다.

        길이를 **홀수**로 잡는다 — 짝수 길이면 인코딩 체인의 `utf-16`이 두 바이트씩
        묶어 제어문자 없는 CJK 모지바케를 만들어 이진 판정을 우회한다(그 자체는
        의도된 폴백이다). 홀수 길이에서는 `utf-16`이 탈락해 임계가 실제로 판정한다.
        """
        binary_side = read((chr(0x1F) * 3 + "A" * 18).encode())
        assert [f.kind for f in binary_side.read_failures] == [READ_FAILURE_ENCODING]
        # 비공허성 — 같은 길이에서 비율만 낮추면 정상 판독된다.
        text_side = read((chr(0x1F) * 1 + "A" * 20).encode())
        assert READ_FAILURE_ENCODING not in {f.kind for f in text_side.read_failures}


class _WidthRow(NamedTuple):
    label: str
    field_count: int
    accepted: bool


#: 헤더 폭 대비 데이터 행의 필드 수 — **양쪽 한 칸씩**. `len(row) == width`의 등호를
#: `>=`로 넓히면 넘치는 행이 조용히 레코드가 되고(zip이 잘라내므로 데이터가 사라진다),
#: `<=`로 넓히면 모자란 행이 빈 값으로 채워진 레코드가 된다.
_R17_ROW_WIDTH_ROWS: tuple[_WidthRow, ...] = (
    _WidthRow("헤더보다 한 칸 적다", -1, False),
    _WidthRow("헤더와 같다", 0, True),
    _WidthRow("헤더보다 한 칸 많다", +1, False),
)


class TestRound17DataBlockWidthBoundary:
    """[round17] `_extract_data_block`의 `len(row) == width` 양끝."""

    def test_the_table_covers_both_sides_of_the_exact_width(self):
        """[round17 표 전수] 행을 지우면 실패한다."""
        assert len(_R17_ROW_WIDTH_ROWS) == 3, "행수 리터럴 — 행 삭제/추가 감지"
        assert {row.field_count for row in _R17_ROW_WIDTH_ROWS} == {-1, 0, +1}
        assert {row.accepted for row in _R17_ROW_WIDTH_ROWS} == {True, False}

    @pytest.mark.parametrize("row", _R17_ROW_WIDTH_ROWS, ids=lambda r: r.label)
    def test_only_an_exact_width_row_becomes_a_record(self, row):
        """[round17] `reader.py`의 `len(row) == width`를 `>= width`로 바꾸면 "한 칸 많다"
        행이 레코드가 되어 실패한다. `<= width`로 바꾸면 "한 칸 적다" 행이 레코드가 되어
        실패한다. 채택되지 않은 행은 **조용히 버려지지 않고** 구조화된 판독 실패가 된다.
        """
        header = ["Instrument Type", "Universe", "DMX Address"]
        good = ["Robe Robin MMX Spot", "1", "1"]
        odd = ["Robe Robin MMX Spot", "1", "2"]
        if row.field_count < 0:
            odd = odd[:-1]
        elif row.field_count > 0:
            odd = [*odd, "extra"]
        data = "\n".join(",".join(cells) for cells in (header, good, odd)).encode()

        result = read(data)
        kinds = {failure.kind for failure in result.read_failures}
        if row.accepted:
            assert len(result.records) == 2, row.label
            assert READ_FAILURE_WORKSHEET_SUBTOTAL not in kinds
        else:
            assert len(result.records) == 1, row.label
            assert READ_FAILURE_WORKSHEET_SUBTOTAL in kinds, "버려진 행이 기록되지 않았다"
