"""SPEC-COPILOT-FILEARG-001 M1 — 시트 종류 레지스트리와 판별기.

업로드된 바이트가 **무엇인가**(신원)만 답한다. "패치를 뽑을 수 있는가"(사용성)는
대상이 판단하며 판별의 입력이 아니다 — REQ-FILEARG-022.

술어는 정본을 **호출**하고 사본을 만들지 않는다:

* ``patch`` — 열 집합 술어. 정본은 ``server/lxseq/parser.py`` 의
  :data:`CANONICAL_COLUMNS` 이며 **참조로** 들고 있다(사본 금지 · AC-FILEARG-006 ②).
* ``vectorworks`` — 신원 술어. zip이면 **판독 가능한 아카이브인가**만 묻고
  (``.mvr``·``.xlsx`` 두 형상 모두 참 — 둘 다 Vectorworks가 내보내는 형식이며,
  *어느* zip인가는 신원이 아니라 뒷단이 가른다), 아니면
  ``server/vwx/reader.py:158`` 의 ``_best_header_candidate(rows)[0] >= 0``.
  여기에 **레지스트리의 다른 행에 맞지 않을 것**이라는 배제 절이 붙는다(결정 L).

순수 함수 계층이다 — 콘솔·네트워크 접촉 0.
"""

from __future__ import annotations

import csv
import io
import zipfile
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from server.lxseq.parser import CANONICAL_COLUMNS, _normalize_header
from server.vwx.reader import (
    _best_header_candidate,
    _choose_delimiter,
    _uniform_width,
    decode_bytes,
)

#: 판별기가 낼 수 있는 결과의 닫힌 집합 (REQ-FILEARG-002~004).
OUTCOME_RESOLVED = "resolved"
OUTCOME_UNKNOWN = "unknown_sheet_kind"
OUTCOME_AMBIGUOUS = "ambiguous_sheet_kind"
OUTCOMES = (OUTCOME_RESOLVED, OUTCOME_UNKNOWN, OUTCOME_AMBIGUOUS)

#: 판별 시점 설정 오류 (REQ-FILEARG-008 · REQ-FILEARG-016).
CONFIG_ERROR_NO_TARGET_TOOL = "no_target_tool"
CONFIG_ERROR_UNSUPPORTED_PREDICATE = "unsupported_predicate_form"

#: 핸들러 태그 — 열 하나가 두 종류를 담으므로 태그가 필수다(결정 M).
HANDLER_TAG_TOOL = "tool"
HANDLER_TAG_SESSION_METHOD = "session_method"
HANDLER_TAGS = (HANDLER_TAG_TOOL, HANDLER_TAG_SESSION_METHOD)

#: 조건부 재수출 힌트 — 형상 관측이지 신원 주장이 아니다 (REQ-FILEARG-023).
REEXPORT_HINT = (
    "헤더 행이 없는 균일폭 표로 보인다. Vectorworks에서 내보낸 것이라면 "
    "'Export field names as first record'를 켜고 다시 내보내라."
)

#: ZIP 매직 바이트. 확장자·MIME이 아니라 바이트로 가른다 (REQ-FILEARG-019).
_ZIP_MAGIC = b"PK"


@dataclass(frozen=True)
class Handler:
    """누가 이 시트를 받는가 — ``(kind_tag, name)`` 태그 쌍 (결정 M)."""

    kind_tag: str
    name: str


@dataclass(frozen=True)
class ExactColumns:
    """(i) 정확 열 집합 — 헤더의 정규 열 집합이 이것과 정확히 같을 때만 일치."""

    columns: tuple[str, ...]


@dataclass(frozen=True)
class RequiredForbidden:
    """(ii) 포함·배제 쌍 — 오늘의 포함 검사는 배제 목록이 빈 경우다."""

    required_columns: tuple[str, ...]
    forbidden_columns: tuple[str, ...] = ()


@dataclass(frozen=True)
class DelegatedPredicate:
    """(B) 위임 술어 — 기존 판정을 호출한다. 열을 세지 않는다.

    ``excluded_by_other_rows`` 는 배제 절이다. 종류 이름을 열거하지 않고
    레지스트리를 참조하므로 후속 SPEC이 행을 더해도 문면은 O(1)로 그대로다.
    우선순위 순서가 **아니다** — 술어를 서로 배타적으로 만들 뿐이며 전수 계수는
    그대로 돈다(REQ-FILEARG-002).
    """

    identity: Callable[[bytes], bool]
    source: str
    excluded_by_other_rows: bool = False


@dataclass(frozen=True)
class SheetKindRow:
    kind: str
    predicate: Any
    handler: Any
    passthrough_args: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConfigError:
    """판별 시점에 드러난 설정 오류 — 조용한 무시가 아니다."""

    kind: str
    reason: str
    detail: str


@dataclass(frozen=True)
class Discrimination:
    outcome: str
    matched: tuple[str, ...]
    count: int
    header_read: tuple[str, ...]
    filename_hint: str | None
    signatures: tuple[tuple[str, str], ...]
    config_errors: tuple[ConfigError, ...]
    hint: str | None


def read_header(data: bytes) -> tuple[str, ...] | None:
    """헤더 행을 **원문 그대로** 돌려준다. 읽을 수 없으면 ``None``.

    열 집합 술어는 헤더 행을 읽을 수 있을 때만 참이 될 수 있다
    (REQ-FILEARG-019). zip 아카이브와 디코딩되지 않는 바이트는 헤더가 없다.
    """
    if data[:2] == _ZIP_MAGIC:
        return None
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None
    if "\x00" in text:
        return None
    try:
        for row in csv.reader(io.StringIO(text, newline="")):
            if any(cell.strip() for cell in row):
                return tuple(row)
    except csv.Error:
        return None
    return None


def vectorworks_identity(data: bytes) -> bool:
    """두 갈래 **전역 함수** — 어떤 바이트가 와도 True/False 하나를 낸다.

    REQ-FILEARG-021 · design.md §4. 배제 절은 여기 없다 — 그것은 레지스트리를
    참조해야 하므로 판별기가 두 번째 훑기에서 적용한다.

    zip 갈래는 **둘로 갈라지며 둘 다 참이다**: ``SCENE_ENTRY``가 있으면 ``.mvr``,
    없으면 ``.xlsx`` — 둘 다 Vectorworks가 내보내는 형식이므로 신원은 참이고,
    *어느* zip인가는 신원이 아니라 뒷단의 판단이다(리드 재정 · G-2). 판독
    **불가능한** 아카이브만 거짓이다 — 그 경계는 넓히지 않았다.

    판독기 갈래의 결과에 값을 배정한다: 헤더 미발견 → False · 판독기 예외 →
    False("신원을 확인하지 못했다"로 번역한다) · ``not_patch_source`` → True
    (헤더는 찾았다; 사용성은 대상이 판단한다). zip은 **신원 단계에서** 판독기에
    도달하지 않으므로 ``unapproved_dependency``는 여기서 나오지 않는다 — 그것은
    ``.xlsx``가 뒷단 판독기에 닿을 때 openpyxl 없는 환경에서 나온다.
    """
    if data[:2] == _ZIP_MAGIC:
        try:
            with zipfile.ZipFile(io.BytesIO(data)):
                return True
        except (zipfile.BadZipFile, OSError):
            return False
    try:
        text, _encoding = decode_bytes(data)
        _delimiter, rows, _index, _score = _choose_delimiter(text)
    except Exception:
        return False
    return _best_header_candidate(rows)[0] >= 0


def _looks_headerless_uniform_grid(data: bytes) -> bool:
    """형상 관측 — 신원 주장이 아니다 (REQ-FILEARG-023)."""
    if data[:2] == _ZIP_MAGIC:
        return False
    try:
        text, _encoding = decode_bytes(data)
        delimiter, rows, header_index, _score = _choose_delimiter(text)
    except Exception:
        return False
    return header_index < 0 and delimiter == "\t" and _uniform_width(rows)


def _normalized(names: Iterable[str]) -> set[str]:
    """헤더 정규화 규약은 `server/lxseq/parser.py` 가 소유한다 — 재정의하지 않는다."""
    return {_normalize_header(name) for name in names}


def _match_column_set(predicate: Any, header: tuple[str, ...] | None) -> bool:
    if header is None:
        return False
    present = _normalized(header)
    if isinstance(predicate, ExactColumns):
        return present == _normalized(predicate.columns)
    required = _normalized(predicate.required_columns)
    forbidden = _normalized(predicate.forbidden_columns)
    return required <= present and not (forbidden & present)


def _predicate_form_error(row: SheetKindRow) -> ConfigError | None:
    """해석하지 못하는 형태는 조용히 건너뛰지 않는다 (REQ-FILEARG-016)."""
    if isinstance(row.predicate, ExactColumns | RequiredForbidden | DelegatedPredicate):
        return None
    return ConfigError(
        row.kind,
        CONFIG_ERROR_UNSUPPORTED_PREDICATE,
        f"판별기가 해석할 수 없는 술어 형식이다: {type(row.predicate).__name__}",
    )


def _handler_error(row: SheetKindRow) -> ConfigError | None:
    """핸들러가 **자기 태그가 지정하는** 레지스트리에서 해소되는가 (AC-FILEARG-023)."""
    handler = row.handler
    if not isinstance(handler, Handler) or handler.kind_tag not in HANDLER_TAGS:
        return ConfigError(
            row.kind,
            CONFIG_ERROR_NO_TARGET_TOOL,
            "핸들러 태그가 선언되지 않았다 — 어느 레지스트리로 확인할지 정해지지 않는다",
        )
    if handler.kind_tag == HANDLER_TAG_TOOL:
        from server.orchestrator.tools import TOOL_NAMES

        if handler.name in TOOL_NAMES:
            return None
        return ConfigError(
            row.kind,
            CONFIG_ERROR_NO_TARGET_TOOL,
            f"등록 툴 집합에 없다: {handler.name}",
        )
    from server.web.session import ChatSession

    if callable(getattr(ChatSession, handler.name, None)):
        return None
    return ConfigError(
        row.kind,
        CONFIG_ERROR_NO_TARGET_TOOL,
        f"ChatSession의 호출 가능한 속성이 아니다: {handler.name}",
    )


def _signature_description(row: SheetKindRow) -> str:
    """거절 보고에 싣는 서명 설명 (REQ-FILEARG-003)."""
    predicate = row.predicate
    if isinstance(predicate, ExactColumns):
        return "정확 열 집합: " + ", ".join(predicate.columns)
    if isinstance(predicate, RequiredForbidden):
        text = "포함: " + ", ".join(predicate.required_columns)
        if predicate.forbidden_columns:
            text += " / 배제: " + ", ".join(predicate.forbidden_columns)
        return text
    if isinstance(predicate, DelegatedPredicate):
        return "위임 술어: " + predicate.source
    return "해석할 수 없는 술어 형식"


def _raw_match(row: SheetKindRow, data: bytes, header: tuple[str, ...] | None) -> bool:
    if isinstance(row.predicate, DelegatedPredicate):
        return row.predicate.identity(data)
    return _match_column_set(row.predicate, header)


def _is_exclusive(row: SheetKindRow) -> bool:
    return isinstance(row.predicate, DelegatedPredicate) and row.predicate.excluded_by_other_rows


#: `patch` — 열 집합 술어. 정본을 **참조로** 든다(사본 금지).
PATCH_ROW = SheetKindRow(
    kind="patch",
    predicate=RequiredForbidden(required_columns=CANONICAL_COLUMNS),
    handler=Handler(HANDLER_TAG_TOOL, "import_lxseq_patch"),
    passthrough_args=("action", "name_prefix_mode", "only_fids", "mode_overrides"),
)

#: `vectorworks` — 신원 술어 + 배제 절. 신규 파서·핸들러·판정 논리는 0건이다.
VECTORWORKS_ROW = SheetKindRow(
    kind="vectorworks",
    predicate=DelegatedPredicate(
        identity=vectorworks_identity,
        source=(
            "zip이면 판독 가능한 아카이브인가(.mvr·.xlsx 두 형상 모두 참 — "
            "어느 zip인가는 뒷단이 가른다), 아니면 "
            "server/vwx/reader.py _best_header_candidate(rows)[0] >= 0 "
            "(임계 _MIN_HEADER_ALIAS_MATCHES) AND NOT 레지스트리의 다른 행 일치"
        ),
        excluded_by_other_rows=True,
    ),
    handler=Handler(HANDLER_TAG_SESSION_METHOD, "upload_vectorworks_export"),
)

#: 표 하나. 오늘 채워진 행은 둘이며, 예약된 종류의 행은 만들지 않는다
#: (REQ-FILEARG-017 — 그 종류의 파서·핸들러가 아직 없다).
REGISTRY: tuple[SheetKindRow, ...] = (PATCH_ROW, VECTORWORKS_ROW)


def discriminate(
    data: bytes,
    *,
    filename_hint: str | None = None,
    registry: Sequence[SheetKindRow] = REGISTRY,
) -> Discrimination:
    """바이트가 어느 종류인지 센다 — 첫 일치에서 멈추지 않는다.

    파일 이름·확장자·MIME은 **기록만** 하고 분기에 쓰지 않는다
    (REQ-FILEARG-001). 실제 파서는 호출하지 않는다 — 판별은 가벼운 술어로만
    하고 진짜 파싱은 종류가 정해진 뒤 한 번 돈다(REQ-FILEARG-005 · §F 속성 B).
    """
    table = tuple(registry)
    header = read_header(data)

    config_errors: list[ConfigError] = []
    usable: list[SheetKindRow] = []
    for row in table:
        error = _predicate_form_error(row) or _handler_error(row)
        if error is None:
            usable.append(row)
        else:
            config_errors.append(error)

    # 1차 훑기 — 레지스트리 전체를 돌며 원시 일치를 잰다(조기 반환 없음).
    raw = {row.kind: _raw_match(row, data, header) for row in usable}

    # 2차 훑기 — 배제 절을 적용한다. 순차 평가가 아니라 배타화다(결정 L).
    matched: list[str] = []
    for row in usable:
        if not raw[row.kind]:
            continue
        if _is_exclusive(row) and any(
            raw[other.kind] for other in usable if other.kind != row.kind
        ):
            continue
        matched.append(row.kind)

    count = len(matched)
    if count == 0:
        outcome = OUTCOME_UNKNOWN  # REQ-FILEARG-003이 선언한 결과 (암묵적 else 아님)
    elif count == 1:
        outcome = OUTCOME_RESOLVED
    else:  # count >= 2 — REQ-FILEARG-004가 선언한 결과
        outcome = OUTCOME_AMBIGUOUS

    hint = None
    if outcome == OUTCOME_UNKNOWN and _looks_headerless_uniform_grid(data):
        hint = REEXPORT_HINT

    return Discrimination(
        outcome=outcome,
        matched=tuple(matched),
        count=count,
        header_read=() if header is None else header,
        filename_hint=filename_hint,
        signatures=tuple((row.kind, _signature_description(row)) for row in table),
        config_errors=tuple(config_errors),
        hint=hint,
    )
