"""설계상 리그(designed rig) 도메인 모델 (REQ-VWX-012~017). 문서 근거 · 실물 미검증.

콘솔 슬롯 대응이 아니라 도면이 선언한 장비 목록의 구조화된 표현이다.
``Part Index`` 멀티셀 폴딩, ``Device Type`` 액세서리 필터링, 타입·모드
퍼지 매칭, 파일 내부 조인키(``channel`` 최우선, 차선 ``(position,unit_number)``) 충돌 거부,
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
    fixture_name: str | None = None
    gdtf_fixture: str | None = None
    footprint: int | None = None
    #: System(A-Z) 문자 — 결함 1(P0, v0.1.6) 멀티시스템 주소 아이덴티티 확장.
    #: ``(system, universe, address)``가 진짜 주소 스코프다; System 컬럼이
    #: 없으면 단일 암묵 스코프(``None``)로 취급한다.
    system: str | None = None
    extra: dict[str, str] = field(default_factory=dict)

    @property
    def match_type(self) -> str:
        """타입 퍼지 매칭용 값 — ``gdtf_fixture``가 있으면 우선, 없으면 ``instrument_type``.

        M0 실물 샘플이 드러낸 개선: 자유문자열 ``Fixture Type``보다 정규화된
        GDTF 제조사@모델 식별자가 더 신뢰도 높은 타입 소스다(REQ-VWX-015).
        """
        return self.gdtf_fixture or self.instrument_type


@dataclass(frozen=True)
class DesignOverlapEntry:
    """설계 도면 내부 주소 구간 겹침 — (universe, address, footprint)만으로 판정한다.

    콘솔 SLOT 키가 필요한 ``FootprintPolicy.widths``(``server/prechk/patch.py``,
    PRESERVE)는 여기서 쓰지 않는다 — 설계 측 자체 판정이며, 콘솔 측 폭 주입은
    (유니버스,주소) 조인 이후의 별도 2차 작업으로 미룬다(범위 밖).
    """

    universe: int
    detail: str
    members: tuple[str, ...]  # unit_number 목록(겹치는 두 픽스처)


@dataclass(frozen=True)
class JoinKeyConflict:
    """파일 내부 조인키(channel 최우선, 차선 (position,unit_number)) 충돌 — last-write-wins 거부."""

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
    design_overlaps: tuple[DesignOverlapEntry, ...] = ()
    footprint_data_present: bool = False
    #: 파일 전체에서 관측된 System(A-Z) 문자 집합 — 결함 1(P0, v0.1.6).
    #: 2개 이상이면 콘솔에는 System 개념이 없어 콘솔 대조(diff.py)만
    #: 별도로 미수행 처리한다; 설계 측 산출(픽스처 목록·수량·내부 주소
    #: 충돌·미패치 목록·멀티셀 폴딩)은 System 수와 무관하게 항상 낸다.
    observed_systems: frozenset[str] = field(default_factory=frozenset)


def _part_index_sort_key(record: ResolvedRecord) -> tuple[int, int]:
    """``Part Index`` 최솟값 행을 대표로 채택한다(닫힌 결정, AC-VWX-013 ②)."""
    raw = record.fields.get("part_index", "")
    try:
        value = int(raw.strip())
    except (ValueError, AttributeError):
        value = 0
    return (value, record.row_index)


def _is_accessory_row(record: ResolvedRecord, device_type_present: bool) -> bool:
    """``Device Type``이 액세서리 계열을 표시하는가(문자열 리터럴 무관, 결함 2·4 P1).

    실물 샘플은 DMX를 먹는 액세서리(Coloram 스크롤러)와 안 먹는 액세서리
    (Top Hat)가 **똑같이** ``"Accessory"`` 리터럴을 쓴다 — ``STATIC_ACCESSORY``
    (``"Static Accessory"``) 하나만 비교하던 예전 규칙은 이 파일에서 둘 다
    걸러내지 못한다. 이 함수는 "액세서리 계열인가"만 판정한다(부분 문자열
    포함, 대소문자 무시) — DMX 소비 여부는 :func:`_is_non_dmx_accessory`가
    footprint로 별도 판정한다.
    """
    if not device_type_present:
        return False
    device_type = record.fields.get("device_type")
    if device_type is None:
        return False
    return "accessory" in device_type.strip().lower()


def _parse_footprint(raw: str | None) -> int | None:
    if raw is None or not raw.strip():
        return None
    try:
        value = int(raw.strip())
    except ValueError:
        return None
    return value if value > 0 else None


def _is_non_dmx_accessory(record: ResolvedRecord, device_type_present: bool) -> bool:
    """대조 계수에서 배제할 비-DMX 액세서리인가(REQ-VWX-014, 결함 2 P1 재교정).

    구분 기준은 문자열 리터럴(``"Static Accessory"``)이 아니라 **실제 DMX
    점유 여부**다 — 액세서리 계열(:func:`_is_accessory_row`)이면서 양수
    ``DMX Footprint``가 없으면(공란·0·비파싱) 비-DMX로 배제한다. DMX를
    먹는 액세서리(양수 footprint)는 리터럴이 같아도 배제하지 않는다.
    """
    if not _is_accessory_row(record, device_type_present):
        return False
    return _parse_footprint(record.fields.get("footprint")) is None


def _normalize_system(raw: str | None) -> str | None:
    """System 문자 하나로 정규화한다 — ``address._observed_system_letters``와
    동일 규약(대문자 첫 글자)이다. 공란이면 단일 암묵 스코프(``None``)."""
    if raw is None or not raw.strip():
        return None
    return raw.strip().upper()[:1]


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
        fixture_name=representative.fields.get("fixture_name"),
        gdtf_fixture=representative.fields.get("gdtf_fixture"),
        footprint=_parse_footprint(representative.fields.get("footprint")),
        system=_normalize_system(representative.fields.get("system")),
        extra=dict(representative.extra),
    )


def _compute_design_overlaps(fixtures: list[DesignedFixture]) -> list[DesignOverlapEntry]:
    """설계 측 (universe, address, footprint)만으로 구간 겹침을 판정한다.

    콘솔 SLOT 폭 주입 없이도 가능한 판정이다 — 이 파일 스코프 내부의 주소
    구간이 서로 겹치는지만 본다. 정확히 같은 시작 주소의 다중패치는
    ``vw_patch_conflicts``가 이미 별도로(의도적일 수 있는 규약으로) 처리하므로
    여기서는 실패시키지 않고 별개 구조로 보고한다.
    """
    intervals: list[tuple[str | None, int, int, int, DesignedFixture]] = []
    for fixture in fixtures:
        if (
            fixture.classification != PATCHED
            or fixture.universe is None
            or fixture.address is None
            or fixture.footprint is None
        ):
            continue
        intervals.append(
            (
                fixture.system,
                fixture.universe,
                fixture.address,
                fixture.address + fixture.footprint - 1,
                fixture,
            )
        )
    # 정렬 키에 system을 포함한다 — 결함 1(P0, v0.1.6): System별로 Universe가
    # 독립 스코프이므로(B/U1/1과 A/U1/1은 서로 다른 주소다), system이 다르면
    # 절대 겹침으로 보지 않는다. None(암묵 스코프)은 문자열보다 먼저 정렬된다.
    intervals.sort(key=lambda item: ((item[0] is not None, item[0] or ""), item[1], item[2]))

    overlaps: list[DesignOverlapEntry] = []
    for i, (sys1, u1, s1, e1, fx1) in enumerate(intervals):
        for sys2, u2, s2, e2, fx2 in intervals[i + 1 :]:
            if sys2 != sys1 or u2 != u1:
                break  # 정렬 순서상 이 (system, universe) 스코프는 더 이상 등장하지 않는다.
            if s2 > e1:
                break  # 시작 주소가 이미 앞 구간 끝을 넘으면 이후는 전부 겹치지 않는다.
            scope = f"System {sys1} 유니버스 {u1}" if sys1 else f"유니버스 {u1}"
            overlaps.append(
                DesignOverlapEntry(
                    universe=u1,
                    detail=(
                        f"{scope} — 주소 {s1}~{e1}({fx1.footprint}ch, "
                        f"{fx1.unit_number}) 와 {s2}~{e2}({fx2.footprint}ch, {fx2.unit_number}) "
                        "구간 겹침"
                    ),
                    members=(str(fx1.unit_number), str(fx2.unit_number)),
                )
            )
    return overlaps


def _fold_by_channel(
    records: list[ResolvedRecord],
) -> tuple[dict[str, list[ResolvedRecord]], list[str], list[ResolvedRecord]]:
    """``channel``(Vectorworks 전역 유일 디자이너 번호) 값으로 그룹핑한다.

    최우선 조인 키다(REQ-VWX-016 v0.1.5) — 파일 전체에서 유일하기 때문에
    ``unit_number``(포지션 안에서만 유일)보다 안전하다. 문서상 비숫자
    ("channel name")일 수 있으므로 항상 문자열로 다룬다 — 정수 변환을
    시도하지 않는다. 공란인 레코드는 다음 우선순위(position+unit_number)로
    넘어간다.
    """
    groups: dict[str, list[ResolvedRecord]] = {}
    order: list[str] = []
    unkeyed: list[ResolvedRecord] = []
    for record in records:
        raw_channel = record.fields.get("channel")
        if raw_channel and raw_channel.strip():
            key = raw_channel.strip()
            if key not in groups:
                groups[key] = []
                order.append(key)
            groups[key].append(record)
        else:
            unkeyed.append(record)
    return groups, order, unkeyed


def _fold_by_position_and_unit_number(
    records: list[ResolvedRecord],
) -> tuple[
    dict[tuple[str, str], list[ResolvedRecord]], list[tuple[str, str]], list[ResolvedRecord]
]:
    """``(position, unit_number)`` 복합 키로 그룹핑한다 — channel이 없을 때의 차선책.

    ``Unit Number``는 Vectorworks에서 **포지션 안에서만 유일**하다(전역 유일이
    아니다 — 트러스마다 1번부터 다시 센다, 브리핑이 이미 경고했던 함정).
    ``unit_number``만으로 그룹핑하면 서로 다른 포지션의 동명 유닛이 충돌로
    오판정돼 실사용 리그 대부분이 전멸한다(코디네이터 재현). ``position``이
    공란이면 그 자체가 하나의 스코프다 — 공란끼리만 서로 충돌한다.
    ``unit_number``가 공란인 레코드는 이 계층에서도 조인 불가로 다음
    우선순위(둘 다 없음)로 넘어간다.
    """
    groups: dict[tuple[str, str], list[ResolvedRecord]] = {}
    order: list[tuple[str, str]] = []
    unkeyed: list[ResolvedRecord] = []
    for record in records:
        raw_unit = record.fields.get("unit_number")
        if not raw_unit or not raw_unit.strip():
            unkeyed.append(record)
            continue
        raw_position = record.fields.get("position")
        position_key = raw_position.strip() if raw_position and raw_position.strip() else ""
        key = (position_key, raw_unit.strip())
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(record)
    return groups, order, unkeyed


def _classify_vw_conflicts(fixtures: list[DesignedFixture]) -> list[VwPatchConflictEntry]:
    """파일 내부에서 (universe, address)를 공유하는 patched 픽스처들 —
    Vectorworks 자체 패치 충돌 분류(REQ-VWX-017)를 구조화된 부류로 통과시킨다.
    """
    by_address: dict[tuple[str | None, int, int], list[DesignedFixture]] = {}
    for fixture in fixtures:
        if fixture.classification != PATCHED or fixture.universe is None or fixture.address is None:
            continue
        # 결함 1(P0, v0.1.6): system을 키에 포함한다 — System이 다르면 같은
        # (universe, address)라도 서로 다른 물리 주소이므로 충돌이 아니다.
        by_address.setdefault((fixture.system, fixture.universe, fixture.address), []).append(
            fixture
        )

    def _sort_key(item: tuple[tuple[str | None, int, int], list[DesignedFixture]]):
        system, universe, address = item[0]
        return ((system is not None, system or ""), universe, address)

    conflicts: list[VwPatchConflictEntry] = []
    for (_system, universe, address), members in sorted(by_address.items(), key=_sort_key):
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
    key_label: str,
    members: list[ResolvedRecord],
    device_type_present: bool,
) -> tuple[DesignedFixture | None, JoinKeyConflict | None]:
    """한 조인키 그룹을 접는다 — Part Index가 전량 있으면 멀티셀 폴딩, 없으면
    진짜 중복(join key conflict)이다. ``key_label``은 이미 사람이 읽을 수 있는
    형태(어느 스코프에서 중복인지 포함)로 준비돼 들어온다."""
    if len(members) > 1 and not all(m.fields.get("part_index", "").strip() for m in members):
        conflict = JoinKeyConflict(
            key=key_label,
            detail=f"{key_label} 중복 {len(members)}건 — Part Index 없이 last-write-wins 병합 거부",
            rows=tuple(m.row_index for m in members),
        )
        return None, conflict
    representative = min(members, key=_part_index_sort_key)
    if _is_non_dmx_accessory(representative, device_type_present):
        return None, None  # 대조 계수 이전 필터링(REQ-VWX-014) — 충돌도 아니다
    return _to_designed_fixture(representative, members), None


def build_designed_rig(records: list[ResolvedRecord]) -> DesignedRig:
    """주소 해석까지 끝난 레코드 목록 -> 설계상 리그 모델(REQ-VWX-012~017).

    조인 키 우선순위(REQ-VWX-016 v0.1.5/v0.1.6 — 코디네이터 재현으로 드러난 결함 수정):
    ① ``channel`` — Vectorworks 전역 유일 디자이너 번호(비숫자 가능, 문자열로 취급).
       **액세서리 행(Device Type이 액세서리 계열)은 이 계층을 건너뛴다** — 액세서리는
       부모 픽스처의 channel 번호를 그대로 물려받아 channel 우선 조인을 쓰면 서로
       다른 유닛(부모+액세서리 여러 개)이 하나로 잘못 접힌다(결함 4, P1, v0.1.6).
    ② ``(position, unit_number)`` 복합 키 — channel이 없거나 공란인 일반 레코드 +
       모든 액세서리 레코드가 대상. ``unit_number``는 포지션 안에서만 유일하므로
       position과 묶지 않으면 서로 다른 포지션의 동명 유닛이 충돌로 오판정된다.
       position 공란도 하나의 스코프다.
    ③ 둘 다 없으면 조인 불가로 거부(기존과 동일).
    """
    device_type_present = any("device_type" in record.fields for record in records)
    accessory_records = [r for r in records if _is_accessory_row(r, device_type_present)]
    non_accessory_records = [r for r in records if not _is_accessory_row(r, device_type_present)]

    fixtures: list[DesignedFixture] = []
    join_conflicts: list[JoinKeyConflict] = []

    # ① channel — 전역 유일 디자이너 번호(최우선, 액세서리 제외).
    channel_groups, channel_order, no_channel = _fold_by_channel(non_accessory_records)
    for key in channel_order:
        label = f"channel '{key}'"
        fixture, conflict = _fold_group(label, channel_groups[key], device_type_present)
        if fixture is not None:
            fixtures.append(fixture)
        if conflict is not None:
            join_conflicts.append(conflict)

    # ② (position, unit_number) 복합 키 — channel이 없는 일반 레코드 + 액세서리 전량.
    pu_groups, pu_order, truly_unjoinable = _fold_by_position_and_unit_number(
        no_channel + accessory_records
    )
    for key in pu_order:
        position_key, unit_key = key
        scope_label = f"포지션 '{position_key}'" if position_key else "포지션 공란"
        label = f"{scope_label} 내 unit_number '{unit_key}'"
        fixture, conflict = _fold_group(label, pu_groups[key], device_type_present)
        if fixture is not None:
            fixtures.append(fixture)
        if conflict is not None:
            join_conflicts.append(conflict)

    # ③ 둘 다 없음 — 조인 불가.
    for record in truly_unjoinable:
        join_conflicts.append(
            JoinKeyConflict(
                key="",
                detail="channel·unit_number 둘 다 공란 — 조인 불가",
                rows=(record.row_index,),
            )
        )

    vw_conflicts = _classify_vw_conflicts(fixtures)
    design_overlaps = _compute_design_overlaps(fixtures)
    footprint_data_present = any(fixture.footprint is not None for fixture in fixtures)
    observed_systems = frozenset(
        _normalize_system(record.fields.get("system"))
        for record in records
        if _normalize_system(record.fields.get("system")) is not None
    )

    return DesignedRig(
        fixtures=tuple(fixtures),
        join_key_conflicts=tuple(join_conflicts),
        vw_patch_conflicts=tuple(vw_conflicts),
        device_type_column_present=device_type_present,
        design_overlaps=tuple(design_overlaps),
        footprint_data_present=footprint_data_present,
        observed_systems=observed_systems,
    )
