"""LX-SEQ v2.1 RIG 팩 패치 CSV 파서 (SPEC-COPILOT-LXSEQ-001 M1).

순수 함수다 — 콘솔·네트워크 입출력 0. 바이트를 레코드로 바꾸는 일만 한다.

REQ-LXSEQ-001: 이름 기반 컬럼 매칭(위치 해석 금지), 9개 정규 컬럼, `extra` 보존.
REQ-LXSEQ-002: 행 검증 실패는 예외가 아니라 구조화된 거부로 분류한다.
REQ-LXSEQ-003: FID는 자리(universe/address) 계산에 절대 쓰지 않는다.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from typing import Any

# 정규 컬럼 9개. 헤더는 이 이름들로만 맞춘다 — 위치는 보지 않는다.
CANONICAL_COLUMNS: tuple[str, ...] = (
    "FID",
    "Group",
    "FixtureType",
    "Mode",
    "Ch",
    "Universe",
    "Address",
    "AddrRange",
    "Position",
)

# AddrRange 구분자 관용 집합 — hyphen · en-dash · em-dash.
_RANGE_DASHES: tuple[str, ...] = ("–", "-", "—")

# 한 유니버스의 DMX 주소 상한.
_UNIVERSE_CHANNEL_CEILING = 512


class MissingColumnsError(ValueError):
    """정규 9개 중 하나라도 헤더에 없을 때 — 파일 단위 판독 실패."""

    def __init__(self, missing: tuple[str, ...]) -> None:
        self.missing = missing
        super().__init__(f"missing_columns: {', '.join(missing)}")


@dataclass(frozen=True)
class LxseqPatchRecord:
    """검증을 통과한 패치 1행."""

    fid: int
    group: str
    fixture_type: str
    mode_label: str
    channels: int
    universe: int
    address: int
    addr_range_raw: str
    position: str
    extra: dict[str, str] = field(default_factory=dict)

    def __eq__(self, other: object) -> bool:
        # dict 필드가 있어 dataclass 기본 eq를 쓰되, 비교 대상 타입만 좁힌다.
        if not isinstance(other, LxseqPatchRecord):
            return NotImplemented
        return (
            self.fid,
            self.group,
            self.fixture_type,
            self.mode_label,
            self.channels,
            self.universe,
            self.address,
            self.addr_range_raw,
            self.position,
            self.extra,
        ) == (
            other.fid,
            other.group,
            other.fixture_type,
            other.mode_label,
            other.channels,
            other.universe,
            other.address,
            other.addr_range_raw,
            other.position,
            other.extra,
        )

    __hash__ = None  # type: ignore[assignment]


@dataclass(frozen=True)
class RowRejection:
    """행 거부 — 닫힌 `kind` 집합 7부류."""

    row: int
    fid_raw: str
    kind: str
    detail: str


@dataclass(frozen=True)
class ExcludedRow:
    """DMX를 점유하지 않는 행(Ch=0) — 거부가 아니라 제외다."""

    row: int
    fid_raw: str
    kind: str
    detail: str


@dataclass(frozen=True)
class ParseResult:
    records: tuple[LxseqPatchRecord, ...]
    rejected: tuple[RowRejection, ...]
    excluded: tuple[ExcludedRow, ...]


def _normalize_header(name: str) -> str:
    return name.strip().replace(" ", "").replace("﻿", "").lower()


def _resolve_header_map(fieldnames: list[str]) -> dict[str, str]:
    """정규 이름 → 실제 헤더 문자열. 대소문자·공백 무시, 위치 무관."""
    normalized = {_normalize_header(name): name for name in fieldnames}
    resolved: dict[str, str] = {}
    missing: list[str] = []
    for canonical in CANONICAL_COLUMNS:
        actual = normalized.get(_normalize_header(canonical))
        if actual is None:
            missing.append(canonical)
        else:
            resolved[canonical] = actual
    if missing:
        raise MissingColumnsError(tuple(missing))
    return resolved


def _expected_addr_range(universe: int, address: int, channels: int) -> str:
    last = address + channels - 1
    return f"{universe}.{address:03d}–{last:03d}"


def _addr_range_matches(raw: str, universe: int, address: int, channels: int) -> bool:
    """구분자는 관용하되 숫자가 다르면 불일치."""
    expected = _expected_addr_range(universe, address, channels)
    candidate = raw.strip()
    for dash in _RANGE_DASHES:
        candidate = candidate.replace(dash, "–")
    return candidate == expected


def _parse_int(raw: str) -> int | None:
    text = raw.strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def parse_patch_csv(text: str) -> ParseResult:
    """패치 CSV 본문을 레코드·거부·제외로 가른다.

    행 검증 실패는 예외로 새어나가지 않는다(REQ-LXSEQ-002). 파일 단위 실패인
    `missing_columns`만 `MissingColumnsError`로 올린다.
    """
    if text.startswith("﻿"):
        text = text[1:]

    reader = csv.DictReader(io.StringIO(text))
    fieldnames = list(reader.fieldnames or [])
    header_map = _resolve_header_map(fieldnames)
    canonical_actuals = set(header_map.values())
    extra_columns = [name for name in fieldnames if name not in canonical_actuals]

    records: list[LxseqPatchRecord] = []
    rejected: list[RowRejection] = []
    excluded: list[ExcludedRow] = []

    # 파일 전역 검사(중복 FID · 구간 겹침)는 개별 행 검증을 마친 뒤에 돈다.
    # 관여 행을 "전부" 거부해야 하므로 후보를 먼저 모은다.
    staged: list[tuple[int, dict[str, Any], LxseqPatchRecord]] = []

    for offset, raw_row in enumerate(reader):
        row_no = offset + 2  # 헤더가 1행
        fid_raw = (raw_row.get(header_map["FID"]) or "").strip()

        int_fields: dict[str, int] = {}
        non_integer: str | None = None
        for canonical in ("FID", "Ch", "Universe", "Address"):
            value = _parse_int(raw_row.get(header_map[canonical]) or "")
            if value is None:
                non_integer = canonical
                break
            int_fields[canonical] = value

        if non_integer is not None:
            rejected.append(
                RowRejection(
                    row=row_no,
                    fid_raw=fid_raw,
                    kind="non_integer_field",
                    detail=f"{non_integer} is not an integer",
                )
            )
            continue

        channels = int_fields["Ch"]
        universe = int_fields["Universe"]
        address = int_fields["Address"]

        if channels == 0:
            excluded.append(
                ExcludedRow(
                    row=row_no,
                    fid_raw=fid_raw,
                    kind="zero_channels",
                    detail="Ch=0 — DMX를 점유하지 않는 행",
                )
            )
            continue

        if channels < 0:
            rejected.append(
                RowRejection(
                    row=row_no,
                    fid_raw=fid_raw,
                    kind="negative_channels",
                    detail=f"Ch={channels} — 채널 수는 음수일 수 없다",
                )
            )
            continue

        if address < 1 or universe < 1:
            rejected.append(
                RowRejection(
                    row=row_no,
                    fid_raw=fid_raw,
                    kind="address_out_of_range",
                    detail=f"universe={universe} address={address}",
                )
            )
            continue

        if address + channels - 1 > _UNIVERSE_CHANNEL_CEILING:
            rejected.append(
                RowRejection(
                    row=row_no,
                    fid_raw=fid_raw,
                    kind="universe_overflow",
                    detail=f"address+{channels}-1={address + channels - 1} > 512",
                )
            )
            continue

        addr_range_raw = (raw_row.get(header_map["AddrRange"]) or "").strip()
        if not _addr_range_matches(addr_range_raw, universe, address, channels):
            rejected.append(
                RowRejection(
                    row=row_no,
                    fid_raw=fid_raw,
                    kind="addr_range_mismatch",
                    detail=(
                        f"expected {_expected_addr_range(universe, address, channels)}, "
                        f"got {addr_range_raw}"
                    ),
                )
            )
            continue

        record = LxseqPatchRecord(
            fid=int_fields["FID"],
            group=(raw_row.get(header_map["Group"]) or "").strip(),
            fixture_type=(raw_row.get(header_map["FixtureType"]) or "").strip(),
            mode_label=(raw_row.get(header_map["Mode"]) or "").strip(),
            channels=channels,
            universe=universe,
            address=address,
            addr_range_raw=addr_range_raw,
            position=(raw_row.get(header_map["Position"]) or "").strip(),
            extra={name: (raw_row.get(name) or "") for name in extra_columns},
        )
        staged.append((row_no, raw_row, record))

    kept, cross_row_rejections = _reject_cross_row_conflicts(staged)
    rejected.extend(cross_row_rejections)
    records.extend(kept)

    rejected.sort(key=lambda item: item.row)
    return ParseResult(
        records=tuple(records),
        rejected=tuple(rejected),
        excluded=tuple(excluded),
    )


def _reject_cross_row_conflicts(
    staged: list[tuple[int, dict[str, Any], LxseqPatchRecord]],
) -> tuple[list[LxseqPatchRecord], list[RowRejection]]:
    """파일 전역 충돌(중복 FID · 같은 유니버스 구간 겹침)을 가른다.

    관여 행은 한쪽만이 아니라 **전부** 거부한다(validate_rig R1·R2 거울).
    """
    rejections: list[RowRejection] = []
    doomed: set[int] = set()

    # 중복 FID — R1 거울.
    by_fid: dict[int, list[int]] = {}
    for row_no, _raw, record in staged:
        by_fid.setdefault(record.fid, []).append(row_no)
    for duplicate_fid, rows in by_fid.items():
        if len(rows) > 1:
            for row_no in rows:
                doomed.add(row_no)
                rejections.append(
                    RowRejection(
                        row=row_no,
                        fid_raw=str(duplicate_fid),
                        kind="duplicate_fid",
                        detail=f"FID {duplicate_fid} appears on rows {rows}",
                    )
                )

    # 같은 유니버스 안 구간 겹침 — R2 거울.
    by_universe: dict[int, list[tuple[int, int, int, int]]] = {}
    for row_no, _raw, record in staged:
        span = (record.address, record.address + record.channels - 1, row_no, record.fid)
        by_universe.setdefault(record.universe, []).append(span)

    for universe, spans in by_universe.items():
        spans.sort()
        for i in range(len(spans)):
            start_a, end_a, row_a, fid_a = spans[i]
            for j in range(i + 1, len(spans)):
                start_b, end_b, row_b, fid_b = spans[j]
                if start_b > end_a:
                    break
                for row_no, fid_value, other in (
                    (row_a, fid_a, row_b),
                    (row_b, fid_b, row_a),
                ):
                    if row_no in doomed and any(
                        r.row == row_no and r.kind == "address_overlap_in_file" for r in rejections
                    ):
                        continue
                    doomed.add(row_no)
                    rejections.append(
                        RowRejection(
                            row=row_no,
                            fid_raw=str(fid_value),
                            kind="address_overlap_in_file",
                            detail=(f"universe {universe} span overlaps row {other}"),
                        )
                    )

    kept = [record for row_no, _raw, record in staged if row_no not in doomed]
    return kept, rejections
