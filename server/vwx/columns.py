"""컬럼 별칭 테이블 + 컬럼 해석 (REQ-VWX-005~007). 문서 근거 · 실물 미검증.

``research.md`` §3의 별칭 테이블 초안을 정본으로 삼는다 — M0(실물 샘플 확보)가
BLOCKED이므로 이 테이블은 Vectorworks 공식 문서 조사에 근거한 강력한 초안이지
실물 헤더로 검증된 정본이 아니다(``ASSUMPTION-68``). 매칭은 대소문자·공백·
구두점을 무시하는 **비위치 기반**이다 — 컬럼 순서로 의미를 추정하지 않는다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

#: 정규 필드 -> 별칭(원문 표기, 비교 시 정규화된다). ``research.md`` §3이 정본.
ALIAS_TABLE: dict[str, tuple[str, ...]] = {
    "instrument_type": ("Instrument Type", "InstrumentType", "Type", "Fixture Type"),
    # M0 실물 샘플(2026-08-05, vectorworks_export_sample_with_data.csv)이 ASSUMPTION-68을
    # NEGATIVE로 닫으며 승격시킨 2개 필드. `fixture_name`은 콘솔에서 실제로 읽을 수 있는
    # 4개 화이트리스트 속성 중 하나(FixtureRecord.name)와 대응하는 몇 안 되는 축이라
    # 결정적이다. `symbol_name`과는 다른 필드다 — 합치지 않는다.
    "fixture_name": ("Fixture Name", "FixtureName", "Instrument Name"),
    # 정규화된 GDTF 제조사@모델 식별자 — 자유문자열 instrument_type보다 신뢰도 높은
    # 타입 소스다(REQ-VWX-015 퍼지 매칭에서 우선 사용). "GDTF Fixture Mode"(mode 별칭)와
    # 정규화 키가 충돌하지 않음을 테스트로 확인했다(gdtffixture vs gdtffixturemode).
    "gdtf_fixture": ("GDTF Fixture", "GDTFFixture"),
    "symbol_name": ("Symbol Name", "SymbolName"),
    "mode": ("Fixture Mode", "GDTF Fixture Mode", "Mode"),
    "footprint": ("DMX Footprint", "Num Channels", "NumChannels"),
    "channel": ("Channel", "Chan", "Ch"),
    "unit_number": ("Unit Number", "UnitNumber", "Unit", "U#"),
    "position": ("Position", "Hanging Position"),
    "purpose": ("Purpose",),
    "universe_address": ("Universe/Address", "Universe Address", "Uni/Addr", "U/A"),
    "universe": ("Universe", "Uni"),
    "address": ("DMX Address", "U Address", "UAddress", "User U Address", "U Dimmer", "Addr"),
    "absolute_address": ("Absolute Address", "Address", "User Address", "Abs Address"),
    "system": ("System",),
    "dimmer": ("Dimmer", "Dim"),
    "circuit_number": ("Circuit Number", "Circuit #", "Circuit"),
    "circuit_name": ("Circuit Name",),
    "color": ("Color", "Colour", "Gel"),
    "device_type": ("Device Type", "DeviceType"),
    "layer": ("Layer", "Design Layer", "Class"),
    "uid": ("UID", "Unique ID", "EID", "External ID", "VW_ID"),
    "fixture_id": ("Fixture ID", "FixtureID", "FID"),
    "part_index": ("Part Index", "PartIndex", "Part#"),
}

#: 해석 가능한 "주소 표현"으로 인정되는 정규 필드 집합. REQ-VWX-007(최소 유효
#: 레코드)과 REQ-VWX-003(Instrument Summary 거부 — 이 계열이 전혀 없으면
#: 패치 출처가 아니다) 둘 다 이 집합을 쓴다.
ADDRESS_FAMILY_FIELDS = frozenset({"universe_address", "universe", "address", "absolute_address"})

_PUNCT_RE = re.compile(r"[^a-z0-9]+")


def normalize_header(text: str) -> str:
    """대소문자·공백·구두점을 무시한 헤더 비교 키(REQ-VWX-005)."""
    return _PUNCT_RE.sub("", text.strip().lower())


def _build_alias_lookup() -> dict[str, str]:
    lookup: dict[str, str] = {}
    for canonical, aliases in ALIAS_TABLE.items():
        for alias in aliases:
            lookup[normalize_header(alias)] = canonical
    return lookup


#: normalize_header(별칭) -> 정규 필드. 위치가 아니라 이 맵 하나로만 해석한다.
ALIAS_LOOKUP: dict[str, str] = _build_alias_lookup()


def resolve_header(raw_header: str) -> str | None:
    """원문 헤더 문자열 하나를 정규 필드 이름으로. 매칭 없으면 ``None``."""
    return ALIAS_LOOKUP.get(normalize_header(raw_header))


def match_count(headers: list[str]) -> int:
    """헤더 후보 행의 별칭 매칭 개수(REQ-VWX-002 헤더 후보 판정에 재사용)."""
    return sum(1 for header in headers if resolve_header(header) is not None)


def has_address_family(headers: list[str]) -> bool:
    """주소 계열 컬럼이 하나라도 해석되는가(REQ-VWX-003 Instrument Summary 거부)."""
    return any(resolve_header(header) in ADDRESS_FAMILY_FIELDS for header in headers)


READ_FAILURE_MIN_RECORD = "min_record_incomplete"


@dataclass(frozen=True)
class ColumnRecord:
    """별칭 해석이 끝난 레코드 하나."""

    fields: dict[str, str] = field(default_factory=dict)
    extra: dict[str, str] = field(default_factory=dict)
    row_index: int = 0


@dataclass(frozen=True)
class ColumnReadFailure:
    """구조화된 판독 실패 — 예외 대신 이 형태로 반환한다(REQ-VWX-007)."""

    row: int | None
    kind: str
    detail: str


def resolve_columns(
    raw_records: list[dict[str, str]],
) -> tuple[list[ColumnRecord], list[ColumnReadFailure]]:
    """원시 레코드(원문 헤더 dict) 목록을 (해석 레코드, 판독 실패)로 나눈다.

    최소 유효 레코드 = ``instrument_type`` + 해석 가능한 주소 표현 하나
    (REQ-VWX-007). 미달 레코드는 예외를 던지지 않고 판독 실패로 분류되며
    판정에 쓰이지 않는다. 별칭 테이블 밖 컬럼은 폐기하지 않고 ``extra``에
    원문 그대로 보존한다(REQ-VWX-006).
    """
    records: list[ColumnRecord] = []
    failures: list[ColumnReadFailure] = []
    for row_index, raw in enumerate(raw_records):
        fields: dict[str, str] = {}
        extra: dict[str, str] = {}
        for header, value in raw.items():
            canonical = resolve_header(header)
            if canonical is None:
                extra[header] = value
            else:
                # 같은 행에서 별칭이 우연히 중복 매칭되면(드문 경우) 첫 값을
                # 유지한다 — 나중 값으로 조용히 덮어쓰지 않는다.
                fields.setdefault(canonical, value)
        has_type = bool(fields.get("instrument_type", "").strip())
        has_address = any(fields.get(name, "").strip() for name in ADDRESS_FAMILY_FIELDS)
        if not has_type or not has_address:
            failures.append(
                ColumnReadFailure(
                    row=row_index,
                    kind=READ_FAILURE_MIN_RECORD,
                    detail=(
                        "instrument_type 또는 해석 가능한 주소 표현이 없다 — "
                        "최소 유효 레코드 조건 미달"
                    ),
                )
            )
            continue
        records.append(ColumnRecord(fields=fields, extra=extra, row_index=row_index))
    return records, failures
