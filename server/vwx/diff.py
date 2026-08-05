"""precheck_patch 대조 (REQ-VWX-018~022). 문서 근거 · 실물 미검증.

조인 키는 **(유니버스, 주소) + 픽스처 타입**이다. ``FID``/``CID``는 조인
비교 연산자의 피연산자로 절대 쓰지 않는다(REQ-VWX-018) — 슬롯==FID 우연일치
쇼파일에서는 원리적으로 그 대조가 불가능하기 때문이다(``console/lua/
PROTOCOL.md:322-324``). 그 불가능성은 ``SkippedCheck``와 동형인 구조로
명시한다(REQ-VWX-019) — 산문으로만 흘리지 않는다.

콘솔 실측 측은 ``server/prechk/inventory.py``의 ``read_inventory`` 또는
``server/paperwork/data.py``의 ``build_patch_sheet``로만 얻는다(REQ-VWX-022)
— 이미 라이브 검증된 경로를 소비만 하며 재구현하지 않는다. 주소 충돌은
``server/prechk/patch.py``의 ``evaluate_patch``가 이미 판정한 결과를
재사용한다(REQ-VWX-020 ②) — 재계산하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass

from server.prechk.inventory import Inventory
from server.prechk.patch import FootprintPolicy, evaluate_patch, normalize_address
from server.vwx.rig import DesignedRig, fuzzy_type_equal

FID_CID_UNREACHABLE = "fid_cid_identity_unreachable"
FOOTPRINT_OVERLAP_DESCOPE = "footprint_overlap_descope"
WORKSHEET_BLOCK_UNDETECTED = "worksheet_block_undetected"
#: M0 실물 샘플이 DMX Footprint 폭 출처를 줘서 설계 측 구간 겹침 판정(``rig.py``
#: ``design_overlaps``)은 이제 항상 수행된다. 콘솔 SLOT 키 폭 주입((유니버스,주소)
#: 조인 이후에나 가능한 2차 작업)만은 이번 SPEC에서 의도적으로 미룬다 — 그 결정을
#: 구조화된 미수행 판정으로 남긴다(범위 밖, `progress.md` §E.2 M0 절 참조).
CONSOLE_FOOTPRINT_WIDTH_INJECTION_DEFERRED = "console_footprint_width_injection_deferred"
#: 결함 1(P0, v0.1.6) — 멀티시스템(System 2개 이상 관측)에서는 콘솔에 System
#: 개념이 없어 System->콘솔 유니버스 매핑을 추측할 수 없다. 설계 측 산출은
#: 전부 정상 수행하되 콘솔 대조(missing_in_console/quantity_mismatch)만 이
#: 사유로 미수행 처리한다 — 일반 판독 실패 사유와 절대 뭉뚱그리지 않는다.
MULTI_SYSTEM_MAPPING_ABSENT = "multi_system_mapping_absent"

SKIPPED_CHECK_KIND_VWX = frozenset(
    {
        FID_CID_UNREACHABLE,
        FOOTPRINT_OVERLAP_DESCOPE,
        WORKSHEET_BLOCK_UNDETECTED,
        CONSOLE_FOOTPRINT_WIDTH_INJECTION_DEFERRED,
        MULTI_SYSTEM_MAPPING_ABSENT,
    }
)

MISSING_IN_CONSOLE = "missing_in_console"
ADDRESS_COLLISION = "address_collision"
QUANTITY_MISMATCH = "quantity_mismatch"

DIFF_KIND = frozenset({MISSING_IN_CONSOLE, ADDRESS_COLLISION, QUANTITY_MISMATCH})

FID_CID_UNREACHABLE_REASON = (
    "슬롯==FID 우연일치 쇼파일에서는 FID 프로브와 슬롯 프로브를 구별할 수 없다"
    "(console/lua/PROTOCOL.md:322-324). 조인 키는 (유니버스,주소)+타입에 한정한다."
)


@dataclass(frozen=True)
class MissingInConsoleEntry:
    """도면에는 있으나 콘솔 실측에 대응 항목이 없는 픽스처."""

    unit_number: str | None
    instrument_type: str
    universe: int
    address: int
    detail: str


@dataclass(frozen=True)
class AddressCollisionEntry:
    """콘솔 실측 기준 주소 충돌 — ``evaluate_patch``의 판정을 재사용한다."""

    universe: int
    address: int
    detail: str
    members: tuple[str, ...]


@dataclass(frozen=True)
class QuantityMismatchEntry:
    """타입별 도면 수량과 콘솔 관측 수량이 다른 항목."""

    instrument_type: str
    designed_count: int
    console_count: int


@dataclass(frozen=True)
class SkippedCheckEntry:
    """수행하지 않은 판정 — ``server.prechk.patch.SkippedCheck``와 동형 구조."""

    kind: str
    reason: str


@dataclass(frozen=True)
class DiffResult:
    designed_rig: DesignedRig
    console_inventory: Inventory
    missing_in_console: tuple[MissingInConsoleEntry, ...]
    address_collisions: tuple[AddressCollisionEntry, ...]
    quantity_mismatches: tuple[QuantityMismatchEntry, ...]
    skipped_checks: tuple[SkippedCheckEntry, ...]


def _console_rows(inventory: Inventory) -> list[tuple[int, int | None, int | None, str | None]]:
    """(slot, universe, address, fixture_type) — ``Patch`` 값을 정규화한다."""
    rows = []
    for fixture in inventory.fixtures:
        parse = normalize_address(fixture.patch_raw)
        rows.append((fixture.slot, parse.universe, parse.address, fixture.fixture_type))
    return rows


def compare(
    designed_rig: DesignedRig,
    console_inventory: Inventory,
    *,
    footprint_policy: FootprintPolicy | None = None,
) -> DiffResult:
    """설계상 리그 vs 콘솔 실측 대조(REQ-VWX-018~021).

    결함 1(P0, v0.1.6) — System이 2개 이상 관측되면 콘솔 대조(System->콘솔
    유니버스 매핑 부재)만 미수행 처리한다. 설계 측 산출(``designed_rig``의
    픽스처 목록·수량·내부 주소 충돌·미패치 목록·멀티셀 폴딩)은 이 함수
    호출 이전에 이미 완결돼 있으므로 System 수와 무관하다 — 여기서 건너뛰는
    것은 오직 콘솔과의 조인(missing_in_console/quantity_mismatch)뿐이다.
    """
    console_rows = _console_rows(console_inventory)
    multi_system = len(designed_rig.observed_systems) >= 2

    missing: list[MissingInConsoleEntry] = []
    mismatches: list[QuantityMismatchEntry] = []
    if not multi_system:
        console_by_address: dict[tuple[int, int], list[tuple[int, str | None]]] = {}
        for slot, universe, address, fixture_type in console_rows:
            if universe is None or address is None:
                continue
            console_by_address.setdefault((universe, address), []).append((slot, fixture_type))

        for fixture in designed_rig.fixtures:
            # 미패치("설계됨·미배정")는 콘솔에 대응 주소가 없는 게 정상이다 —
            # missing_in_console(콘솔 부재)과 혼동하지 않는다(REQ-VWX-008).
            unresolved_address = fixture.universe is None or fixture.address is None
            if fixture.classification != "patched" or unresolved_address:
                continue
            candidates = console_by_address.get((fixture.universe, fixture.address), [])
            found = any(fuzzy_type_equal(fixture.match_type, ftype) for _slot, ftype in candidates)
            if found:
                continue
            missing.append(
                MissingInConsoleEntry(
                    unit_number=fixture.unit_number,
                    instrument_type=fixture.instrument_type,
                    universe=fixture.universe,
                    address=fixture.address,
                    detail=(
                        f"도면 유니버스 {fixture.universe} 주소 {fixture.address} "
                        f"'{fixture.instrument_type}'가 콘솔 실측에 없다"
                    ),
                )
            )

        # quantity_mismatch — 타입별 도면 수량 vs 콘솔 관측 수량.
        designed_counts: dict[str, int] = {}
        for fixture in designed_rig.fixtures:
            itype = fixture.match_type
            designed_counts[itype] = designed_counts.get(itype, 0) + 1
        console_counts: dict[str, int] = {}
        for _slot, _universe, _address, fixture_type in console_rows:
            if fixture_type is None:
                continue
            console_counts[fixture_type] = console_counts.get(fixture_type, 0) + 1

        for instrument_type in sorted(designed_counts):
            designed_count = designed_counts[instrument_type]
            matched_console_type = next(
                (ctype for ctype in console_counts if fuzzy_type_equal(instrument_type, ctype)),
                None,
            )
            console_count = (
                console_counts.get(matched_console_type, 0) if matched_console_type else 0
            )
            if designed_count != console_count:
                mismatches.append(
                    QuantityMismatchEntry(
                        instrument_type=instrument_type,
                        designed_count=designed_count,
                        console_count=console_count,
                    )
                )

    # address_collision — precheck_patch의 판정을 재사용한다(재계산 금지).
    # 콘솔 실측 자체 내부 판정이라 System 관측 수와 무관하게 항상 수행한다.
    evaluation = evaluate_patch(console_inventory, footprint=footprint_policy)
    collisions = tuple(
        AddressCollisionEntry(
            universe=c.universe,
            address=c.address,
            detail=c.detail,
            members=tuple(str(member.slot) for member in c.members),
        )
        for c in evaluation.address_duplicates
    )

    skipped = [SkippedCheckEntry(kind=FID_CID_UNREACHABLE, reason=FID_CID_UNREACHABLE_REASON)]
    if multi_system:
        observed = " ".join(sorted(designed_rig.observed_systems))
        skipped.append(
            SkippedCheckEntry(
                kind=MULTI_SYSTEM_MAPPING_ABSENT,
                reason=(
                    f"System {observed} 관측 — System→콘솔 유니버스 매핑이 없어 콘솔 대조를 "
                    "수행하지 않았다. 매핑이 주어지면 수행 가능하다."
                ),
            )
        )
    if footprint_policy is None or not footprint_policy.enabled:
        skipped.append(
            SkippedCheckEntry(
                kind=FOOTPRINT_OVERLAP_DESCOPE,
                reason="FootprintPolicy가 주입되지 않아 구간 겹침 확장 판정을 수행하지 않았다.",
            )
        )
    if designed_rig.footprint_data_present:
        # 설계 측 구간 겹침(designed_rig.design_overlaps)은 이미 수행됐다 —
        # 여기서 미수행으로 남기는 것은 콘솔 SLOT 키 폭 주입(2차 작업)뿐이다.
        skipped.append(
            SkippedCheckEntry(
                kind=CONSOLE_FOOTPRINT_WIDTH_INJECTION_DEFERRED,
                reason=(
                    "설계 측 구간 겹침은 DMX Footprint 컬럼으로 수행했다. 콘솔 SLOT 키 폭 "
                    "주입((유니버스,주소) 조인 이후 2차 작업)은 이번 SPEC 범위 밖이라 "
                    "의도적으로 미룬다."
                ),
            )
        )

    return DiffResult(
        designed_rig=designed_rig,
        console_inventory=console_inventory,
        missing_in_console=tuple(missing),
        address_collisions=collisions,
        quantity_mismatches=tuple(mismatches),
        skipped_checks=tuple(skipped),
    )
