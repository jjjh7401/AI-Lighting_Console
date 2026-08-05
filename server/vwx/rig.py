"""설계상 리그(designed rig) 도메인 모델 (REQ-VWX-012~017). 문서 근거 · 실물 미검증.

콘솔 슬롯 대응이 아니라 도면이 선언한 장비 목록의 구조화된 표현이다.
``Part Index`` 멀티셀 폴딩, ``Device Type`` 액세서리 필터링, 타입·모드
퍼지 매칭, 파일 내부 조인키(``unit_number``/``channel``) 충돌 거부,
Vectorworks 자체 패치 충돌 분류(Patch overlap · Identical Patch · Patch
conflict) 통과를 대조(``diff.py``) 이전 단계에서 전부 마친다
(``research.md`` §6 대조 7가지 함정 ①②③⑤⑥).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from server.vwx.address import PATCHED, ResolvedRecord

STATIC_ACCESSORY = "Static Accessory"

VW_PATCH_OVERLAP = "vw_patch_overlap"
VW_IDENTICAL_PATCH = "vw_identical_patch"
VW_PATCH_CONFLICT = "vw_patch_conflict"

JOIN_KEY_CONFLICT = "join_key_conflict"


def _norm_type(text: str) -> str:
    return "".join(ch.lower() for ch in text if ch.isalnum())


def fuzzy_type_equal(a: str | None, b: str | None) -> bool:
    """VW·콘솔 타입/모드 명칭 퍼지 매칭 — 동등 비교(``==``) 금지(REQ-VWX-015).

    서로 다른 소스(도면 vs 콘솔 라이브러리)의 명명 체계는 절대 문자 그대로
    일치하지 않는다 — 정규화 후 완전 일치이거나, 한쪽이 다른 쪽을 포함하면
    같은 타입으로 본다. 어느 쪽도 비어 있으면(공란/None) 해결 불가로 취급해
    False를 반환한다 — 빈 값끼리 우연히 "같다"고 판정하지 않는다.
    """
    if not a or not b:
        return False
    normalized_a, normalized_b = _norm_type(a), _norm_type(b)
    if normalized_a == normalized_b:
        return True
    return normalized_a in normalized_b or normalized_b in normalized_a


@dataclass(frozen=True)
class DesignedFixture:
    """설계상 리그의 논리적 픽스처 하나 — Part Index 폴딩이 끝난 결과."""

    unit_number: str | None
    instrument_type: str
    mode: str | None
    channel: str | None
    universe: int | None
    address: int | None
    classification: str  # "patched" | "unpatched_designed"
    part_indices: tuple[str, ...]
    device_type: str | None
    extra: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class JoinKeyConflict:
    """파일 내부 조인키(unit_number/channel) 충돌 — last-write-wins 거부."""

    key: str
    detail: str
    rows: tuple[int, ...]


@dataclass(frozen=True)
class VwPatchConflictEntry:
    """Vectorworks 자체 패치 충돌 분류(REQ-VWX-017) — 예외가 아니라 구조."""

    kind: str
    universe: int | None
    address: int | None
    detail: str


@dataclass(frozen=True)
class DesignedRig:
    """설계상 리그 도메인 모델 — 대조(diff.py) 단계의 입력."""

    fixtures: tuple[DesignedFixture, ...]
    join_key_conflicts: tuple[JoinKeyConflict, ...]
    vw_patch_conflicts: tuple[VwPatchConflictEntry, ...]
    device_type_column_present: bool


def _part_index_sort_key(record: ResolvedRecord) -> tuple[int, int]:
    """``Part Index`` 최솟값 행을 대표로 채택한다(닫힌 결정, AC-VWX-013 ②)."""
    raw = record.fields.get("part_index", "")
    try:
        value = int(raw.strip())
    except (ValueError, AttributeError):
        value = 0
    return (value, record.row_index)


def _is_static_accessory(record: ResolvedRecord, device_type_present: bool) -> bool:
    if not device_type_present:
        return False
    device_type = record.fields.get("device_type")
    return device_type is not None and device_type.strip() == STATIC_ACCESSORY


def _to_designed_fixture(
    representative: ResolvedRecord, members: list[ResolvedRecord]
) -> DesignedFixture:
    part_indices = tuple(
        member.fields["part_index"].strip()
        for member in members
        if member.fields.get("part_index", "").strip()
    )
    return DesignedFixture(
        unit_number=representative.fields.get("unit_number"),
        instrument_type=representative.fields.get("instrument_type", ""),
        mode=representative.fields.get("mode"),
        channel=representative.fields.get("channel"),
        universe=representative.universe,
        address=representative.address,
        classification=representative.classification,
        part_indices=part_indices,
        device_type=representative.fields.get("device_type"),
        extra=dict(representative.extra),
    )


def _fold_by_key(
    records: list[ResolvedRecord],
    key_field: str,
) -> tuple[dict[str, list[ResolvedRecord]], list[str], list[ResolvedRecord]]:
    """``key_field`` 값으로 레코드를 그룹핑한다. 공란인 레코드는 별도 목록으로."""
    groups: dict[str, list[ResolvedRecord]] = {}
    order: list[str] = []
    unkeyed: list[ResolvedRecord] = []
    for record in records:
        raw_key = record.fields.get(key_field)
        if raw_key and raw_key.strip():
            key = raw_key.strip()
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(record)
        else:
            unkeyed.append(record)
    return groups, order, unkeyed


def _classify_vw_conflicts(fixtures: list[DesignedFixture]) -> list[VwPatchConflictEntry]:
    """파일 내부에서 (universe, address)를 공유하는 patched 픽스처들 —
    Vectorworks 자체 패치 충돌 분류(REQ-VWX-017)를 구조화된 부류로 통과시킨다.
    """
    by_address: dict[tuple[int, int], list[DesignedFixture]] = {}
    for fixture in fixtures:
        if fixture.classification != PATCHED or fixture.universe is None or fixture.address is None:
            continue
        by_address.setdefault((fixture.universe, fixture.address), []).append(fixture)

    conflicts: list[VwPatchConflictEntry] = []
    for (universe, address), members in sorted(by_address.items()):
        if len(members) < 2:
            continue
        channels = {member.channel for member in members}
        if len(channels) == 1 and None not in channels:
            kind = VW_IDENTICAL_PATCH
            detail = (
                f"유니버스 {universe} 주소 {address} — 채널까지 동일(케이블 배선 문제 아닐 수 있음)"
            )
        elif len(channels) > 1 and None not in channels:
            kind = VW_PATCH_CONFLICT
            detail = f"유니버스 {universe} 주소 {address} — 채널이 서로 다름"
        else:
            kind = VW_PATCH_OVERLAP
            detail = f"유니버스 {universe} 주소 {address} — 픽스처 {len(members)}개가 겹침"
        conflicts.append(
            VwPatchConflictEntry(kind=kind, universe=universe, address=address, detail=detail)
        )
    return conflicts


def _fold_group(
    key: str,
    members: list[ResolvedRecord],
    device_type_present: bool,
    conflict_detail_prefix: str,
) -> tuple[DesignedFixture | None, JoinKeyConflict | None]:
    """한 조인키 그룹을 접는다 — Part Index가 전량 있으면 멀티셀 폴딩, 없으면
    진짜 중복(join key conflict)이다."""
    if len(members) > 1 and not all(m.fields.get("part_index", "").strip() for m in members):
        conflict = JoinKeyConflict(
            key=key,
            detail=f"{conflict_detail_prefix} '{key}' 중복 {len(members)}건 — "
            "Part Index 없이 last-write-wins 병합 거부",
            rows=tuple(m.row_index for m in members),
        )
        return None, conflict
    representative = min(members, key=_part_index_sort_key)
    if _is_static_accessory(representative, device_type_present):
        return None, None  # 대조 계수 이전 필터링(REQ-VWX-014) — 충돌도 아니다
    return _to_designed_fixture(representative, members), None


def build_designed_rig(records: list[ResolvedRecord]) -> DesignedRig:
    """주소 해석까지 끝난 레코드 목록 -> 설계상 리그 모델(REQ-VWX-012~017)."""
    device_type_present = any("device_type" in record.fields for record in records)

    unit_groups, unit_order, unkeyed = _fold_by_key(records, "unit_number")

    fixtures: list[DesignedFixture] = []
    join_conflicts: list[JoinKeyConflict] = []

    for key in unit_order:
        fixture, conflict = _fold_group(key, unit_groups[key], device_type_present, "unit_number")
        if fixture is not None:
            fixtures.append(fixture)
        if conflict is not None:
            join_conflicts.append(conflict)

    # unit_number가 공란인 레코드 — 대체 조인키로 channel을 시도한다.
    channel_groups, channel_order, truly_unjoinable = _fold_by_key(unkeyed, "channel")
    for key in channel_order:
        fixture, conflict = _fold_group(
            key, channel_groups[key], device_type_present, "unit_number 공란 + 대체 조인키 channel"
        )
        if fixture is not None:
            fixtures.append(fixture)
        if conflict is not None:
            join_conflicts.append(conflict)

    for record in truly_unjoinable:
        join_conflicts.append(
            JoinKeyConflict(
                key="",
                detail="unit_number·channel 둘 다 공란 — 조인 불가",
                rows=(record.row_index,),
            )
        )

    vw_conflicts = _classify_vw_conflicts(fixtures)

    return DesignedRig(
        fixtures=tuple(fixtures),
        join_key_conflicts=tuple(join_conflicts),
        vw_patch_conflicts=tuple(vw_conflicts),
        device_type_column_present=device_type_present,
    )
