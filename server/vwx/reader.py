"""Vectorworks Instrument Data export 파일 판독 (REQ-VWX-001~004). 문서 근거 · 실물 미검증.

경로 A(``Export Instrument Data`` — tab-delimited text 전용)와 경로 B
(``Export Worksheet`` — 워크시트 그리드: 제목행 + DB 헤더행 + 데이터행 +
소계행이 한 파일에 섞임)를 **확장자가 아니라 내용 구조**로 판별한다
(``research.md`` §2). 인코딩은 BOM 스니프 -> ``utf-8-sig`` -> ``utf-16`` ->
``cp1252`` -> ``mac_roman`` 순으로 폴백하며, 전부 실패하면 조용히 통과시키지
않고 바이트 오프셋과 함께 구조화된 판독 실패를 반환한다(REQ-VWX-004).

이 모듈은 예외를 던지지 않는다 — 모든 실패는 :class:`ReadResult`의
``read_failures``에 담긴 구조화된 항목이다(HARD 제약: 구조화 페이로드,
예외 산문 금지).
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass

from server.vwx.columns import has_address_family, match_count

try:
    import openpyxl

    OPENPYXL_AVAILABLE = True
except ImportError:  # pragma: no cover — openpyxl은 승인된 런타임 의존성이다
    openpyxl = None  # type: ignore[assignment]
    OPENPYXL_AVAILABLE = False

PATH_A = "A"
PATH_B = "B"

READ_FAILURE_ENCODING = "encoding_undetermined"
READ_FAILURE_NOT_PATCH_SOURCE = "not_patch_source"
READ_FAILURE_BLOCK_UNDETECTED = "worksheet_block_undetected"
READ_FAILURE_UNAPPROVED_DEPENDENCY = "unapproved_dependency"
READ_FAILURE_WORKSHEET_SUBTOTAL = "worksheet_subtotal_row"

_ENCODING_CHAIN = ("utf-8-sig", "utf-16", "cp1252", "mac_roman")
_HEADER_SCAN_LIMIT = 30
_MIN_HEADER_ALIAS_MATCHES = 2
_XLSX_MAGIC = b"PK"


@dataclass(frozen=True)
class ReadFailure:
    """한 판독 실패 항목 — 예외가 아니라 구조화된 사유다."""

    row: int | None
    kind: str
    detail: str

    def to_dict(self) -> dict:
        return {"row": self.row, "kind": self.kind, "detail": self.detail}


@dataclass(frozen=True)
class ReadResult:
    """판독 산출 — 원시 레코드(원문 헤더 dict) 목록 + 메타데이터."""

    records: tuple[dict[str, str], ...]
    encoding: str
    path_kind: str
    header: tuple[str, ...]
    read_failures: tuple[ReadFailure, ...]


class _EncodingExhausted(Exception):
    """모든 인코딩 후보가 실패했다 — 모듈 경계를 넘지 않는 내부 신호다."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def _sniff_bom(data: bytes) -> str | None:
    if data.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return "utf-16"
    return None


def _looks_binary(text: str) -> bool:
    """디코딩은 성공했지만 실제로는 이진 내용일 가능성(모지바케 방지)."""
    if "\x00" in text:
        return True
    if not text:
        return False
    control = sum(1 for ch in text if ord(ch) < 32 and ch not in "\t\n\r")
    return control / len(text) > 0.1


def decode_bytes(data: bytes) -> tuple[str, str]:
    """(text, encoding). 전부 실패하면 :class:`_EncodingExhausted`."""
    bom = _sniff_bom(data)
    order: list[str] = [bom] if bom else []
    order += [enc for enc in _ENCODING_CHAIN if enc not in order]
    last_reason = "알 수 없음"
    for encoding in order:
        try:
            text = data.decode(encoding)
        except (UnicodeDecodeError, LookupError) as error:
            last_reason = str(error)
            continue
        if _looks_binary(text):
            last_reason = f"{encoding} 디코딩은 성공했으나 이진 내용으로 판단됨"
            continue
        return text, encoding
    offset = next((index for index, byte in enumerate(data) if byte == 0), 0)
    raise _EncodingExhausted(f"인코딩 판독 전부 실패 — 바이트 오프셋 {offset} ({last_reason})")


def _split_rows(text: str, delimiter: str) -> list[list[str]]:
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    return [row for row in reader if any(cell.strip() for cell in row)]


def _best_header_candidate(rows: list[list[str]]) -> tuple[int, int]:
    """(row_index, alias_match_count). 최소 기준 미달이면 ``(-1, score)``."""
    best_index, best_score = -1, 0
    for index, row in enumerate(rows[:_HEADER_SCAN_LIMIT]):
        score = match_count(row)
        if score > best_score:
            best_index, best_score = index, score
    if best_score < _MIN_HEADER_ALIAS_MATCHES:
        return -1, best_score
    return best_index, best_score


def _choose_delimiter(text: str) -> tuple[str, list[list[str]], int, int]:
    """별칭 매칭 점수가 가장 높은 구분자를 고른다 — 확장자를 쓰지 않는다."""
    best: tuple[str, list[list[str]], int, int] | None = None
    for delimiter in ("\t", ","):
        rows = _split_rows(text, delimiter)
        header_index, score = _best_header_candidate(rows)
        if best is None or score > best[3]:
            best = (delimiter, rows, header_index, score)
    assert best is not None  # 반복문이 최소 1회 실행되므로 항상 채워진다
    return best


def _uniform_width(rows: list[list[str]]) -> bool:
    widths = {len(row) for row in rows}
    return len(widths) == 1 and rows != []


def _extract_data_block(
    rows: list[list[str]], header_index: int, header: list[str]
) -> tuple[list[dict[str, str]], list[ReadFailure]]:
    """헤더 다음, 컬럼 수가 연속으로 일치하는 구간만 레코드로 채택한다.

    첫 불일치 행에서 구간이 끊긴다(REQ-VWX-002 "연속" 구간). 끊긴 뒤의 모든
    행(소계행 등)은 판독 실패로 개별 기록된다 — 조용히 버리지 않는다.
    """
    width = len(header)
    records: list[dict[str, str]] = []
    failures: list[ReadFailure] = []
    broke = False
    for offset, row in enumerate(rows[header_index + 1 :], start=header_index + 1):
        if not broke and len(row) == width:
            records.append(dict(zip(header, row, strict=False)))
            continue
        broke = True
        failures.append(
            ReadFailure(
                row=offset,
                kind=READ_FAILURE_WORKSHEET_SUBTOTAL,
                detail=(
                    f"헤더 컬럼 수 {width}와 다른 {len(row)}개 필드 — "
                    "소계행 또는 데이터 블록 밖으로 분류(연속 구간 종료)"
                ),
            )
        )
    return records, failures


def _process_rows(rows: list[list[str]], encoding: str, delimiter: str) -> ReadResult:
    header_index, score = _best_header_candidate(rows)
    if header_index < 0:
        if delimiter == "\t" and _uniform_width(rows):
            # 경로 A 시그니처: flat tab-delimited 단일 테이블인데 별칭 매칭 헤더가
            # 없다 — "Export field names as first record" 체크박스 미선택
            # (REQ-VWX-001). 모든 행을 데이터로 채택하되 위치 기반 필드 해석은
            # 하지 않는다(REQ-VWX-005) — 자리표시자 키(col_0..)는 다음 단계
            # (columns.py)에서 별칭 매칭에 실패해 구조화된 판독 실패로 이어진다.
            width = len(rows[0]) if rows else 0
            synthetic_header = [f"col_{i}" for i in range(width)]
            records = [dict(zip(synthetic_header, row, strict=False)) for row in rows]
            return ReadResult(
                records=tuple(records),
                encoding=encoding,
                path_kind=PATH_A,
                header=tuple(synthetic_header),
                read_failures=(),
            )
        return ReadResult(
            records=(),
            encoding=encoding,
            path_kind=PATH_B,
            header=(),
            read_failures=(
                ReadFailure(
                    row=None,
                    kind=READ_FAILURE_BLOCK_UNDETECTED,
                    detail="헤더 없음 — 데이터 블록 미탐(임의 추측으로 자르지 않는다)",
                ),
            ),
        )
    header = rows[header_index]
    if not has_address_family(header):
        return ReadResult(
            records=(),
            encoding=encoding,
            path_kind=PATH_B,
            header=tuple(header),
            read_failures=(
                ReadFailure(
                    row=header_index,
                    kind=READ_FAILURE_NOT_PATCH_SOURCE,
                    detail="패치 출처 아님(주소 열 없음) — Instrument Summary류로 판단",
                ),
            ),
        )
    records, block_failures = _extract_data_block(rows, header_index, header)
    path_kind = PATH_A if header_index == 0 else PATH_B
    return ReadResult(
        records=tuple(records),
        encoding=encoding,
        path_kind=path_kind,
        header=tuple(header),
        read_failures=tuple(block_failures),
    )


def _read_text(data: bytes) -> ReadResult:
    try:
        text, encoding = decode_bytes(data)
    except _EncodingExhausted as error:
        return ReadResult(
            records=(),
            encoding="undetermined",
            path_kind=PATH_A,
            header=(),
            read_failures=(ReadFailure(row=None, kind=READ_FAILURE_ENCODING, detail=error.detail),),
        )
    delimiter, rows, _header_index, _score = _choose_delimiter(text)
    return _process_rows(rows, encoding, delimiter)


def _read_xlsx(data: bytes) -> ReadResult:
    workbook = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    try:
        sheet = workbook.active
        rows: list[list[str]] = []
        for excel_row in sheet.iter_rows(values_only=True):
            rows.append(["" if cell is None else str(cell) for cell in excel_row])
        rows = [row for row in rows if any(cell.strip() for cell in row)]
    finally:
        workbook.close()
    return _process_rows(rows, "xlsx(openpyxl)", ",")


def read(data: bytes, *, _openpyxl_available: bool | None = None) -> ReadResult:
    """Vectorworks export 파일 바이트 -> :class:`ReadResult`.

    확장자를 전혀 참조하지 않는다 — xlsx는 ZIP 매직 바이트(``PK``)로,
    delimiter는 별칭 매칭 점수로 판별한다. ``_openpyxl_available``은
    "미승인 의존성" 축소 분기를 테스트하기 위한 오버라이드다(§D 대응).
    """
    available = OPENPYXL_AVAILABLE if _openpyxl_available is None else _openpyxl_available
    if data[:2] == _XLSX_MAGIC:
        if not available:
            return ReadResult(
                records=(),
                encoding="binary(xlsx)",
                path_kind=PATH_B,
                header=(),
                read_failures=(
                    ReadFailure(
                        row=None,
                        kind=READ_FAILURE_UNAPPROVED_DEPENDENCY,
                        detail="미승인 의존성 — openpyxl 없이는 .xlsx를 판독할 수 없다",
                    ),
                ),
            )
        return _read_xlsx(data)
    return _read_text(data)
