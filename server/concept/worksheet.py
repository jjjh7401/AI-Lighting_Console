# SPEC-LDDESIGN-001 M1 — 워크시트 YAML 스키마 로더 (REQ-LDDESIGN-011~016).
#
# 순수 데이터 모듈이다 — OSC 송신·콘솔 접근·네트워크를 하지 않는다. YAML
# 파싱은 ``server/fx/loader.py``·``server/measurement/corpus.py`` 와 같은
# 저장소 관행(``yaml.safe_load(path.read_text(encoding="utf-8"))``)을
# 따른다.

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from server.concept.vocab import (
    VocabError,
    validate_one_shot,
    validate_operation,
    validate_section,
    validate_trigger,
)


class WorksheetError(VocabError):
    """워크시트 스키마 위반 — spec.md §3.3 (REQ-011~016)."""


# REQ-011 — 최소 4개 최상위 구획.
_TOP_LEVEL_KEYS = ("palette", "concept", "sections", "notes")

# REQ-014 — sections.rows 각 줄의 필수 필드(memo 는 선택).
_SECTION_ROW_REQUIRED = ("section", "occurrence", "operation")

# REQ-015 — sections.one_shots 각 항목의 필수 필드(전부 필수).
_ONE_SHOT_REQUIRED = ("shot", "anchor_section", "anchor_occurrence", "at")


@dataclass(frozen=True)
class Palette:
    """REQ-012 — palette 구획, 정확히 4개 필드.

    ``reserved`` 를 워크시트가 생략하면 기본값은 ``climax`` 와 동일한
    한 칸짜리 목록이다(REQ-012 본문) — frozen dataclass 는 default
    factory 가 다른 필드를 참조할 수 없으므로 이 기본값은 로더
    (:func:`_load_palette`)가 채운다.
    """

    primary: str
    secondary: str
    climax: str
    reserved: tuple[str, ...]


@dataclass(frozen=True)
class SectionRow:
    """REQ-014 — sections.rows 한 줄."""

    section: str
    occurrence: int
    operation: str
    trigger: str | None = None
    memo: str | None = None


@dataclass(frozen=True)
class OneShotRow:
    """REQ-015 — sections.one_shots 한 항목.

    ``at`` 은 "구간 내 상대 위치 서술 또는 초" 다(REQ-015 본문) — 자유
    문자열 서술("1박째" 등)이거나 초 단위 숫자(``int``/``float``)로
    받는다. 어느 쪽이든 원래 타입 그대로 보존한다(강제 변환하지 않음).
    """

    shot: str
    anchor_section: str
    anchor_occurrence: int
    at: str | int | float


@dataclass(frozen=True)
class Worksheet:
    """REQ-011 — 워크시트 최상위 4구획을 담는 파싱 결과."""

    palette: Palette
    concept: str
    sections: tuple[SectionRow, ...]
    one_shots: tuple[OneShotRow, ...]
    notes: str = ""


def _require_mapping(value: Any, *, field_name: str) -> dict:
    if not isinstance(value, dict):
        raise WorksheetError(f"{field_name}: 매핑이어야 하는데 {type(value).__name__} 를 받음")
    return value


def _require_str(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise WorksheetError(f"{field_name}: 문자열이어야 하는데 {type(value).__name__} 를 받음")
    return value


def _require_int(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise WorksheetError(f"{field_name}: 정수여야 하는데 {value!r} 를 받음")
    return value


def _vocab(validator, value: str, *, path: str) -> str:
    """어휘 검증기(``validate_*``, ``vocab.py``)를 호출하고, 그 안에서 난
    :class:`VocabError` 를 경로 정보(``path``)를 얹은 :class:`WorksheetError`
    로 다시 던진다.

    ``WorksheetError`` 는 ``VocabError`` 의 하위 클래스라 ``validate_*`` 가
    직접 던지는 ``VocabError`` 인스턴스는 (부모이지 자식이 아니므로)
    ``isinstance(error, WorksheetError)`` 가 거짓이다 — 이 경계를 여기서
    한 번에 다시 던져 워크시트 로더가 일관되게 ``WorksheetError`` 만
    내도록 한다(REQ-016).
    """
    try:
        return validator(value)
    except VocabError as error:
        raise WorksheetError(f"{path}: {error}") from error


def _load_palette(raw: Any) -> Palette:
    data = _require_mapping(raw, field_name="palette")
    missing = [key for key in ("primary", "secondary", "climax") if key not in data]
    if missing:
        raise WorksheetError(f"palette: 필수 필드 누락 {missing}")
    primary = _require_str(data["primary"], field_name="palette.primary")
    secondary = _require_str(data["secondary"], field_name="palette.secondary")
    climax = _require_str(data["climax"], field_name="palette.climax")
    reserved_raw = data.get("reserved")
    if reserved_raw is None:
        reserved = (climax,)  # REQ-012 — 기본값은 climax 와 동일
    else:
        if not isinstance(reserved_raw, list):
            raise WorksheetError(
                f"palette.reserved: 목록이어야 하는데 {type(reserved_raw).__name__} 를 받음"
            )
        reserved = tuple(
            _require_str(item, field_name="palette.reserved[]") for item in reserved_raw
        )
    return Palette(primary=primary, secondary=secondary, climax=climax, reserved=reserved)


def _load_section_row(raw: Any, *, index: int) -> SectionRow:
    data = _require_mapping(raw, field_name=f"sections.rows[{index}]")
    missing = [key for key in _SECTION_ROW_REQUIRED if key not in data]
    if missing:
        raise WorksheetError(f"sections.rows[{index}]: 필수 필드 누락 {missing}")
    section = _vocab(
        validate_section,
        _require_str(data["section"], field_name=f"sections.rows[{index}].section"),
        path=f"sections.rows[{index}].section",
    )
    occurrence = _require_int(data["occurrence"], field_name=f"sections.rows[{index}].occurrence")
    operation = _vocab(
        validate_operation,
        _require_str(data["operation"], field_name=f"sections.rows[{index}].operation"),
        path=f"sections.rows[{index}].operation",
    )
    trigger_raw = data.get("trigger")
    trigger = (
        _vocab(
            validate_trigger,
            _require_str(trigger_raw, field_name=f"sections.rows[{index}].trigger"),
            path=f"sections.rows[{index}].trigger",
        )
        if trigger_raw is not None
        else None
    )
    memo = data.get("memo")
    if memo is not None:
        memo = _require_str(memo, field_name=f"sections.rows[{index}].memo")
    return SectionRow(
        section=section, occurrence=occurrence, operation=operation, trigger=trigger, memo=memo
    )


def _load_one_shot_row(raw: Any, *, index: int) -> OneShotRow:
    data = _require_mapping(raw, field_name=f"sections.one_shots[{index}]")
    missing = [key for key in _ONE_SHOT_REQUIRED if key not in data]
    if missing:
        raise WorksheetError(f"sections.one_shots[{index}]: 필수 필드 누락 {missing}")
    shot = _vocab(
        validate_one_shot,
        _require_str(data["shot"], field_name=f"sections.one_shots[{index}].shot"),
        path=f"sections.one_shots[{index}].shot",
    )
    anchor_section = _vocab(
        validate_section,
        _require_str(
            data["anchor_section"], field_name=f"sections.one_shots[{index}].anchor_section"
        ),
        path=f"sections.one_shots[{index}].anchor_section",
    )
    anchor_occurrence = _require_int(
        data["anchor_occurrence"], field_name=f"sections.one_shots[{index}].anchor_occurrence"
    )
    at_raw = data["at"]
    if isinstance(at_raw, bool) or not isinstance(at_raw, (str, int, float)):
        raise WorksheetError(
            f"sections.one_shots[{index}].at: 문자열 또는 숫자(초)여야 하는데 "
            f"{type(at_raw).__name__} 를 받음"
        )
    return OneShotRow(
        shot=shot, anchor_section=anchor_section, anchor_occurrence=anchor_occurrence, at=at_raw
    )


def _load_sections(raw: Any) -> tuple[tuple[SectionRow, ...], tuple[OneShotRow, ...]]:
    data = _require_mapping(raw, field_name="sections")
    rows_raw = data.get("rows", [])
    if not isinstance(rows_raw, list):
        raise WorksheetError(f"sections.rows: 목록이어야 하는데 {type(rows_raw).__name__} 를 받음")
    rows = tuple(_load_section_row(item, index=i) for i, item in enumerate(rows_raw))

    one_shots_raw = data.get("one_shots", [])
    if not isinstance(one_shots_raw, list):
        raise WorksheetError(
            f"sections.one_shots: 목록이어야 하는데 {type(one_shots_raw).__name__} 를 받음"
        )
    one_shots = tuple(_load_one_shot_row(item, index=i) for i, item in enumerate(one_shots_raw))
    return rows, one_shots


def parse_worksheet(raw: Any) -> Worksheet:
    """이미 파싱된 YAML 딕셔너리 하나에서 Worksheet 를 만든다(REQ-011~016)."""
    data = _require_mapping(raw, field_name="<root>")
    missing = [key for key in _TOP_LEVEL_KEYS if key not in data]
    if missing:
        raise WorksheetError(
            f"워크시트 최상위 구획 누락: {missing} (요구: {list(_TOP_LEVEL_KEYS)})"
        )
    palette = _load_palette(data["palette"])
    concept = _require_str(data["concept"], field_name="concept")
    rows, one_shots = _load_sections(data["sections"])
    notes_raw = data.get("notes", "")
    notes = _require_str(notes_raw, field_name="notes") if notes_raw is not None else ""
    return Worksheet(
        palette=palette, concept=concept, sections=rows, one_shots=one_shots, notes=notes
    )


def load_worksheet(path: Path) -> Worksheet:
    """YAML 파일 경로에서 워크시트를 읽어 파싱한다(REQ-011).

    ``server/measurement/corpus.py::load_corpus`` 와 같은 모양 — 파일
    부재는 먼저 걸러내고, YAML 파싱 실패는 원인 예외를 ``from`` 으로
    엮는다.
    """
    path = Path(path)
    if not path.is_file():
        raise WorksheetError(f"워크시트 파일을 찾을 수 없음: {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise WorksheetError(f"{path.name} 은 올바른 YAML 이 아님: {error}") from error
    return parse_worksheet(raw)
