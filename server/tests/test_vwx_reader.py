"""server/vwx/reader.py 판독 테스트 (M1 — AC-VWX-002~005). 문서 근거 · 실물 미검증.

fixture 이름은 ``design.md`` §6.1을 따른다.
"""

from __future__ import annotations

from pathlib import Path

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
        column_records, column_failures = resolve_columns(list(result.records))
        resolved_records, address_failures = resolve_all(column_records)
        designed_rig = build_designed_rig(resolved_records)

        all_failures = (*result.read_failures, *column_failures, *address_failures)
        assert len(designed_rig.fixtures) == 0
        # 픽스처 0대 자체는 정상일 수 있으나(빈 도면), 이 경우는 판독 실패가
        # 동반되어야 "차이 없음"으로 오독되지 않는다 — 비공허성 핵심 assert.
        assert len(all_failures) >= 1
