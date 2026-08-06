"""M5·M6 — 실행 전달(사람) · 멱등 · 검증 읽기
(REQ-AUTOPATCH-004·018·020·021·022·023·024).

**이 모듈은 콘솔에 아무것도 쓰지 않는다.** 서버가 패치를 실행하지 않는 것은 구현 편의가
아니라 실측 결과다 — `AddFixtures` 자동 실행은 실행 경로 10가지 · 인자 변형 8종에서
픽스처를 **한 대도** 만들지 못했다(`progress.md` §E.2 M0 1~5차). v0.1.3 반자동 모델에서
서버의 일은 **검토용 Lua 소스와 실행 절차를 사람에게 넘기는 것**까지이고, 그 다음 동작은
사람의 실행이 끝난 뒤의 **검증 읽기**(REQ-AUTOPATCH-023, M6)다.

**금지를 검사가 아니라 구조로 둔다** — `luagen`이 목적지 변경 명령을 만들 수 없게 한 것과
같은 방식이다(design.md §5 슬롯 C). 이 모듈은 실행 포트도 배포 파이프라인도 **인자로 받지
않고 import하지도 않는다.** 발화할 대상이 없으므로 "승인이 있으면 서버가 실행한다"는 분기가
애초에 조립될 수 없다(AC-AUTOPATCH-015②③ · 018 · 019).

**전달물의 본체는 `luagen.render_addfixtures_plugin(entries)`다.** 이 모듈은 그 결과에
자유 문자열을 덧붙이지 않는다 — Lua 본문에 닿는 유일한 통로는 `LuaPatchEntry`의 6필드이며,
생성기가 거부한 항목은 **조용히 고치지 않고 사유와 함께 제외**한다(M4 계약).

**드라이런과 전달의 차이는 한 줄(`delivered = not dry_run`)이다.** 드라이런도 Lua 소스
전문을 낸다(REQ-AUTOPATCH-003 · AC-AUTOPATCH-004②). 다르게 만드는 것은 **실행 절차와
검증 인계**뿐이며, 한 호출 안에서 드라이런이 전달로 승격되는 경로는 없다(AC-019④).

**M6 — 콘솔을 읽는 경로를 여기서 만들지 않는다.** 멱등 재조회도 검증 읽기도
`server/prechk/inventory.py`의 `read_inventory`가 만든 `Inventory`를 **소비만** 하고,
주소는 `server/prechk/patch.py`의 `normalize_address`가 판독한다 — 1단계 `diff.py`가
세운 선례를 그대로 따른다(REQ-AUTOPATCH-023 · AC-021③).

**[HARD] 콘솔이 돌려주는 타입·모드는 표시 문자열이지 이름이 아니다.**
실측 형태는 `FixtureType 3` · `2 Mode 2`인데 라이브러리 쪽 이름은 `Robin LEDBeam 350` ·
`Mode 2`다(§E.2 M0 1차). 그래서 REQ-AUTOPATCH-022의 네 값 일치는 **문자열 동등으로
성립하지 않는다.** 이 모듈은 표시 문자열을 **열거된 라이브러리에 대조해** 해석하되,
`FixtureType <n>` 형태와 실제 타입 **이름**이 서로 다른 대상을 가리킬 수 있으면
(슬롯==FID 우연일치와 같은 구조) **해석을 거부하고 `identity_unconfirmed`로 보고**한다.
확인 불가를 멱등으로 올리지 않는 쪽이 안전하다 — 올리면 필요한 픽스처가 생성되지 않는다.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from server.prechk.inventory import Inventory
from server.prechk.patch import normalize_address
from server.vwx.luagen import (
    LuaGenerationError,
    LuaPatchEntry,
    render_addfixtures_call,
    render_addfixtures_plugin,
)
from server.vwx.patchplan import (
    IRREVERSIBLE_WARNING,
    AddressPlan,
    AddressPlanEntry,
    PatchCandidate,
    PatchTargetExclusion,
)
from server.vwx.typemap import FixtureTypeLibrary, LibraryMode, LibraryType, TypeResolution
from server.vwx.verdicts import (
    ADDRESS_ALREADY_OCCUPIED,
    ADDRESS_CONFLICTS_WITH_EXISTING,
    ALREADY_PATCHED_IDENTICAL,
    CONSOLE_READ_INCOMPLETE,
    CONSOLE_READ_INDEX_DOMAIN_UNKNOWN,
    EXISTING_FOOTPRINT_UNREADABLE,
    EXISTING_IDENTITY_UNCONFIRMED,
    FID_NOT_ASSIGNED,
    FIXTURE_NAME_MISSING,
    LUA_GENERATION_REFUSED,
    TYPE_CONFIRMATION_PENDING,
    TYPE_RESOLVED,
    VERIFICATION_IDENTITY_UNCONFIRMED,
    VERIFICATION_MISMATCHED,
    VERIFICATION_NOT_OBSERVED,
    VERIFICATION_OBSERVED,
    console_read_caveat_label,
    skipped_check_label,
    validate_autopatch,
    verification_outcome_label,
)

HANDOFF_STATUS_DRY_RUN = "dry_run"
HANDOFF_STATUS_DELIVERED = "delivered"

NEXT_STEP_REVIEW = "review_dry_run"
NEXT_STEP_HUMAN_EXECUTION = "human_execution_then_verification_read"

EXECUTION_PERFORMED_BY = "human"

# 함정 4 — 플러그인이 오류 없이 끝난 것은 성공이 아니다. 2026-08-06 실물 재현:
# `exec`가 OK를 반환하고 픽스처는 0건 생성됐다.
PLUGIN_EXIT_IS_NOT_SUCCESS = (
    "플러그인이 오류 없이 끝난 것은 성공이 아니다 — AddFixtures는 실패해도 nil을 반환할 뿐이다. "
    "생성 여부는 서버의 검증 읽기로만 확정된다."
)

# 정직 고지 — 사람이 실행하는 경로의 종단 성공은 이 빌드에서 아직 확인되지 않았다.
END_TO_END_UNVERIFIED = (
    "이 절차의 종단 성공은 이 빌드에서 아직 확인되지 않았다 — 서버 자동 실행 경로는 "
    "전부 0건이었고, "
    "사람이 실행하는 경로의 종단 확인은 라이브 검증 마일스톤에 남아 있다."
)

# 실행 절차는 실측으로 확정된 것만 적는다(`progress.md` §0 항목 4·9, 함정 9·11).
# 반증된 처방(패치 편집기 선행 · 목적지 이동)은 **적지 않는다** — REQ-AUTOPATCH-024 [v0.1.3].
HUMAN_EXECUTION_PROCEDURE = (
    "1. 아래 Lua 소스를 플러그인 라이브러리 파일로 저장한다.",
    "2. 콘솔에서 Import Plugin '<파일명>' 으로 임포트한다 — 이 빌드의 deploy 동사는 "
    "플러그인 소스를 쓰지 못하므로(객체만 생기고 소스는 빈 상태로 조용히 실행된다) 쓰지 않는다.",
    "3. 같은 이름으로 재임포트하면 소스가 갱신되지 않는다 — 새 이름을 쓰거나 "
    "슬롯을 비우고 임포트한다.",
    "4. 임포트한 플러그인을 콘솔에서 사람이 실행한다. 서버는 이 실행을 대행하지 않는다.",
    "5. 실행이 끝나면 서버에 검증 읽기를 요청한다 — 생성 여부는 그 재조회로만 확정된다.",
)

DELIVERY_WARNINGS = (IRREVERSIBLE_WARNING, PLUGIN_EXIT_IS_NOT_SUCCESS, END_TO_END_UNVERIFIED)


@dataclass(frozen=True)
class HandoffEntry:
    """전달물에 남은 항목 하나. `address`는 **언제나 도면 주소 그대로**다."""

    candidate_id: str
    fid: int
    name: str
    console_type: str
    console_mode: str
    universe: int
    address: int
    footprint: int

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "fid": self.fid,
            "name": self.name,
            "console_type": self.console_type,
            "console_mode": self.console_mode,
            "universe": self.universe,
            "address": self.address,
            "footprint": self.footprint,
        }


@dataclass(frozen=True)
class PatchHandoff:
    dry_run: bool
    delivered: bool
    status: str
    next_step: str
    lua_source: str | None
    entries: tuple[HandoffEntry, ...] = ()
    exclusions: tuple[PatchTargetExclusion, ...] = ()
    procedure: tuple[str, ...] = ()
    warnings: tuple[str, ...] = DELIVERY_WARNINGS

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": True,
            "status": self.status,
            "dry_run": self.dry_run,
            "delivered": self.delivered,
            "next_step": self.next_step,
            "execution_performed_by": EXECUTION_PERFORMED_BY,
            "lua_source": self.lua_source,
            "entries": [entry.to_dict() for entry in self.entries],
            "exclusions": [exclusion.to_dict() for exclusion in self.exclusions],
            "procedure": list(self.procedure),
            "warnings": list(self.warnings),
        }


def build_patch_handoff(
    targets: Sequence[PatchCandidate],
    *,
    address_plan: AddressPlan,
    resolutions: Sequence[TypeResolution],
    names: Mapping[str, str],
    dry_run: bool = True,
) -> PatchHandoff:
    """계획된 항목을 **사람이 콘솔에서 실행할 전달물**로 만든다 (REQ-AUTOPATCH-018).

    서버는 여기서 아무것도 발화하지 않는다 — 실행 포트도 배포 파이프라인도 이 함수의
    어휘에 없다. 승인(`dry_run=false`)이 있어도 달라지는 것은 **실행 절차와 검증 인계를
    함께 내보내는지**뿐이며, 실행 자체는 사람의 몫이다(AC-AUTOPATCH-015②③).

    `names`는 호출자가 주는 픽스처 이름이다 — 이 계층은 이름을 **지어내지 않는다**.
    비어 있거나 생성기가 거부하면 그 항목을 **제외하고 사유를 보고**한다.
    """
    delivered = not dry_run

    target_by_id = {target.id: target for target in targets}
    resolution_by_id = {resolution.request.candidate_id: resolution for resolution in resolutions}

    entries: list[HandoffEntry] = []
    lua_entries: list[LuaPatchEntry] = []
    exclusions: list[PatchTargetExclusion] = list(address_plan.exclusions)

    for planned in address_plan.entries:
        target = target_by_id.get(planned.candidate_id)
        if target is None:
            raise ValueError(
                f"주소 계획에 대상 없는 항목이 있다: {planned.candidate_id!r} — "
                "계획과 대상 집합은 같은 호출에서 나온 것이어야 한다."
            )

        resolution = resolution_by_id.get(planned.candidate_id)
        if (
            resolution is None
            or resolution.status != TYPE_RESOLVED
            or resolution.console_type is None
            or resolution.console_mode is None
        ):
            exclusions.append(
                _exclusion(
                    target,
                    TYPE_CONFIRMATION_PENDING,
                    "콘솔 타입·모드가 확정되지 않았다 — "
                    "확인 전에 되돌릴 수 없는 생성을 전달하지 않는다.",
                )
            )
            continue

        if target.assigned_fid is None:
            exclusions.append(
                _exclusion(
                    target,
                    FID_NOT_ASSIGNED,
                    "FID가 배정되지 않았다 — 배정 없이 생성하면 엉뚱한 픽스처를 덮을 수 있다.",
                )
            )
            continue

        name = names.get(planned.candidate_id)
        if not isinstance(name, str) or not name.strip():
            exclusions.append(
                _exclusion(
                    target,
                    FIXTURE_NAME_MISSING,
                    "픽스처 이름이 제공되지 않았다 — 이름을 지어내지 않고 제외한다.",
                )
            )
            continue

        lua_entry = LuaPatchEntry(
            console_type=resolution.console_type.name,
            console_mode=resolution.console_mode.name,
            fid=target.assigned_fid,
            name=name,
            universe=planned.universe,
            address=planned.address,
        )
        try:
            render_addfixtures_call(lua_entry)
        except LuaGenerationError:
            # 거부 사유에 **거부된 입력을 되싣지 않는다** — 그 값이 목적지 토큰을 담고 있으면
            # 사유 문구가 산출물 스캐너에 거짓 양성을 내 AC-AUTOPATCH-014①이 강제력을 잃는다.
            # 단 **어느 필드가 거부됐는지는 말한다**(round11 M5 N3) — 생성기는 이름뿐 아니라
            # 콘솔 타입·모드·정수 필드도 거부하는데, 전부 "이름을 고쳐라"로 적으면 사용자는
            # 원인이 아닌 필드를 고치게 되고 재시도는 영원히 실패한다.
            exclusions.append(
                _exclusion(
                    target,
                    LUA_GENERATION_REFUSED,
                    "Lua 생성기가 이 항목의 "
                    f"{_rejected_field(lua_entry)} 필드를 거부했다 — "
                    "조용히 고치지 않고 제외한다.",
                )
            )
            continue

        lua_entries.append(lua_entry)
        entries.append(
            HandoffEntry(
                candidate_id=planned.candidate_id,
                fid=target.assigned_fid,
                name=name,
                console_type=resolution.console_type.name,
                console_mode=resolution.console_mode.name,
                universe=planned.universe,
                address=planned.address,
                footprint=planned.footprint,
            )
        )

    lua_source = render_addfixtures_plugin(lua_entries) if lua_entries else None

    return PatchHandoff(
        dry_run=dry_run,
        delivered=delivered,
        status=HANDOFF_STATUS_DELIVERED if delivered else HANDOFF_STATUS_DRY_RUN,
        next_step=NEXT_STEP_HUMAN_EXECUTION if delivered else NEXT_STEP_REVIEW,
        lua_source=lua_source,
        entries=tuple(entries),
        exclusions=tuple(exclusions),
        procedure=HUMAN_EXECUTION_PROCEDURE if delivered else (),
    )


def _rejected_field(entry: LuaPatchEntry) -> str:
    """생성기가 거부한 필드 이름 — **값은 싣지 않는다**."""
    rejected = [
        field
        for field, value in (
            ("name", entry.name),
            ("console_type", entry.console_type),
            ("console_mode", entry.console_mode),
        )
        if _rejects(field, value, entry)
    ]
    return " · ".join(rejected) if rejected else "정수(fid/universe/address)"


def _rejects(field: str, value: object, entry: LuaPatchEntry) -> bool:
    from dataclasses import replace

    probe = replace(entry, **{field: "ok"}) if isinstance(value, str) else entry
    try:
        render_addfixtures_call(probe)
    except LuaGenerationError:
        return False  # 이 필드를 중립값으로 바꿔도 여전히 거부 -> 원인이 아니다
    return True


def _exclusion(target: PatchCandidate, code: str, reason: str) -> PatchTargetExclusion:
    return PatchTargetExclusion(
        candidate_id=target.id,
        code=code,
        reason=reason,
        proposed_fid=target.assigned_fid,
    )


# ==========================================================================
# M6 — 멱등 재조회 · 검증 읽기 (REQ-AUTOPATCH-022·023·024)
# ==========================================================================

# 콘솔이 픽스처의 `FixtureType`/`Mode` 프로퍼티로 돌려주는 **표시 문자열**의 실측 형태.
# 이름이 없는 타입은 `FixtureType <index>`로, 모드는 `<index> <이름>`으로 나타났다
# (§E.2 M0 1차, 표본 7건 · 타입 1종). 형태 자체는 그 한 표본에서 온 **가설**이므로
# 여기서 파싱한 결과는 반드시 열거된 라이브러리에 대조해 확정한다 — 대조가 모호하면 거부한다.
_TYPE_DISPLAY_INDEX = re.compile(r"^FixtureType (\d+)$")
_MODE_DISPLAY_INDEX = re.compile(r"^(\d+) (.+)$")

ZERO_CREATED_GUIDANCE = (
    "승인 항목 중 재조회에서 관측된 것이 0건이다 — 플러그인을 실제로 실행했는지, "
    "그리고 실행 절차의 각 단계(라이브러리 파일 저장 → Import Plugin → 재임포트 캐싱 주의 → "
    "플러그인 실행)를 다시 확인하라."
)
NO_AUTO_CORRECTION = (
    "서버는 자동으로 재시도하거나 보정하지 않는다 — 다시 시도하려면 사람이 다시 요청해야 한다."
)


@dataclass(frozen=True)
class ConsoleFixture:
    """재조회로 관측된 픽스처 하나.

    `type_display`/`mode_display`가 콘솔이 실제로 준 문자열이고,
    `type_name`/`mode_name`은 **라이브러리 대조로 확정된 경우에만** 채워진다.
    확정하지 못했으면 `None`으로 남기고 `identity_resolved`가 `False`가 된다 —
    미확정을 이름처럼 흘려보내지 않기 위해 두 쌍을 분리해 들고 다닌다.
    """

    slot: int
    universe: int | None
    address: int | None
    type_display: str | None
    mode_display: str | None
    type_name: str | None
    mode_name: str | None

    @property
    def identity_resolved(self) -> bool:
        return self.type_name is not None and self.mode_name is not None

    def to_dict(self) -> dict[str, object]:
        return {
            "slot": self.slot,
            "universe": self.universe,
            "address": self.address,
            "type_display": self.type_display,
            "mode_display": self.mode_display,
            "type_name": self.type_name,
            "mode_name": self.mode_name,
            "identity_resolved": self.identity_resolved,
        }


def read_console_fixtures(
    inventory: Inventory, *, library: FixtureTypeLibrary
) -> tuple[ConsoleFixture, ...]:
    """`read_inventory` 산출물을 (유니버스, 주소, 타입, 모드)로 정규화한다.

    **콘솔에 질의하지 않는다** — 이미 읽힌 `Inventory`를 소비할 뿐이며, 주소 판독은
    `server/prechk/patch.py`의 `normalize_address`가 한다(AC-AUTOPATCH-021③).
    """
    observed: list[ConsoleFixture] = []
    for fixture in inventory.fixtures:
        parse = normalize_address(fixture.patch_raw)
        console_type = _resolve_library_type(fixture.fixture_type, library)
        console_mode = _resolve_library_mode(fixture.mode, console_type)
        observed.append(
            ConsoleFixture(
                slot=fixture.slot,
                universe=parse.universe if parse.ok else None,
                address=parse.address if parse.ok else None,
                type_display=fixture.fixture_type,
                mode_display=fixture.mode,
                type_name=console_type.name if console_type is not None else None,
                mode_name=console_mode.name if console_mode is not None else None,
            )
        )
    return tuple(observed)


def _resolve_library_type(display: str | None, library: FixtureTypeLibrary) -> LibraryType | None:
    """표시 문자열을 라이브러리 타입으로 확정한다 — 모호하면 `None`.

    두 해석이 있다: 그 문자열이 **타입의 이름**이거나, `FixtureType <index>` **형태**거나.
    둘 다 성립하면서 **서로 다른 타입**을 가리키면 확정할 수 없다 — 이것이
    `PROTOCOL.md`의 슬롯==FID 우연일치와 같은 구조이고, 우연일치를 판별하는 실험은
    이 저장소에서 아직 수행되지 않았다. 추측 대신 거부한다.
    """
    # [round11 N01] 열거가 절단됐으면 "그 이름의 타입이 없다"를 단정할 수 없다 —
    # `by_name`이 비었다는 사실이 증거가 되지 못하므로 모호성 가드가 바로 그때 공허해진다.
    # `typemap.LIBRARY_TRUNCATED_REASON`이 같은 라이브러리 객체에 대해 이미 같은 규율을 정했다.
    if display is None or not library.available or library.truncated:
        return None
    by_name = [entry for entry in library.types if entry.name == display]
    index_match = _TYPE_DISPLAY_INDEX.match(display)
    by_index = (
        [entry for entry in library.types if entry.index == int(index_match.group(1))]
        if index_match is not None
        else []
    )
    return _single_unambiguous(by_name, by_index)


def _resolve_library_mode(
    display: str | None, console_type: LibraryType | None
) -> LibraryMode | None:
    if display is None or console_type is None:
        return None
    by_name = [mode for mode in console_type.modes if mode.name == display]
    index_match = _MODE_DISPLAY_INDEX.match(display)
    by_index = (
        [
            mode
            for mode in console_type.modes
            if mode.index == int(index_match.group(1)) and mode.name == index_match.group(2)
        ]
        if index_match is not None
        else []
    )
    return _single_unambiguous(by_name, by_index)


def _single_unambiguous(by_name: list, by_index: list):
    """두 해석이 **각각 유일**하고 **같은 대상**을 가리킬 때만 확정한다.

    [round11 N06] 이전 판은 두 목록이 비어 있지 않으면 첫 원소만 비교해서, 이름이 같은 타입이
    둘 있을 때 열거 **순서에 따라** 확정하기도 거부하기도 했다. 모호성 판정이 순서에 의존하면
    그것은 판정이 아니다.
    """
    if by_name and by_index:
        if len(by_name) != 1 or len(by_index) != 1:
            return None
        return by_name[0] if by_name[0] is by_index[0] else None
    candidates = by_name or by_index
    return candidates[0] if len(candidates) == 1 else None


def _address_readable(fixture) -> bool:
    """그 픽스처의 `Patch` 값이 주소로 판독됐는가 — 판독 실패는 **미판독**이다."""
    return normalize_address(fixture.patch_raw).ok


def console_read_caveat(inventory: Inventory) -> dict[str, object] | None:
    """재조회가 무엇을 못 봤는지 — 구조화해서 돌려준다. 완전하면 `None`.

    `read_inventory`는 **절단을 기본 경로로** 다루고(실물 콘솔은 픽스처 19대에서 이미
    절단됐다 — §E.2 M0 1차) 두 가지를 구별해 보고한다:

    - `missing_count > 0` — 선언된 자식 중 **못 읽은 것이 남아 있다**. 이 상태에서
      "그 주소에 아무것도 없다"는 관측이 아니라 **미판독**이다.
    - `missing_count == 0` 인데 `index_domain_unknown` — 열거는 짧았지만 선언된 것을
      전부 관측했다. `childCount`가 진짜 총계이므로 **수량 비교는 정확하다**
      (`server/prechk/inventory.py` 모듈 독스트링 2번). 주의는 남기되 막지 않는다.
    """
    # [round11 N02] `missing_count`는 **열거·복구** 축만 센다. 열거는 됐는데 그 픽스처의
    # `Patch` 프로퍼티를 못 읽었으면 주소가 `None`이 되어 점유·멱등·검증 어디에서도 보이지
    # 않는다 — 그것도 미판독이다. `read_inventory`가 그 사실을 `read_failures`로 이미 들고 있다.
    unreadable_addresses = sum(
        1 for fixture in inventory.fixtures if not _address_readable(fixture)
    )
    unread = inventory.missing_count + unreadable_addresses
    if unread > 0:
        return {
            "kind": validate_autopatch("console_read_caveat_kind", CONSOLE_READ_INCOMPLETE),
            "label": console_read_caveat_label(CONSOLE_READ_INCOMPLETE),
            "completeness": inventory.completeness,
            "child_count": inventory.child_count,
            "observed_count": inventory.observed_count,
            "missing_count": inventory.missing_count,
            "unreadable_address_count": unreadable_addresses,
            "unread_count": unread,
            "reason": (
                f"콘솔 재조회에서 선언된 {inventory.child_count}대 중 "
                f"{inventory.missing_count}대를 열거하지 못했고 {unreadable_addresses}대는 "
                "주소를 판독하지 못했다 — 이 상태의 '없음'은 관측이 아니라 미판독이다."
            ),
        }
    if inventory.index_domain_unknown:
        return {
            "kind": validate_autopatch(
                "console_read_caveat_kind", CONSOLE_READ_INDEX_DOMAIN_UNKNOWN
            ),
            "label": console_read_caveat_label(CONSOLE_READ_INDEX_DOMAIN_UNKNOWN),
            "completeness": inventory.completeness,
            "child_count": inventory.child_count,
            "observed_count": inventory.observed_count,
            "missing_count": 0,
            "unreadable_address_count": 0,
            "unread_count": 0,
            "reason": (
                "열거가 절단됐으나 선언된 자식을 전부 관측했다 — 수량 비교는 정확하고, "
                "인덱스 도메인만 미상이다."
            ),
        }
    return None


def screen_console_read(
    targets: Sequence[PatchCandidate],
    *,
    address_plan: AddressPlan,
    inventory: Inventory,
) -> AddressPlan:
    """재조회에 **미판독이 남아 있으면 아무것도 생성 대상으로 넘기지 않는다**.

    멱등 판정은 "그 주소에 이미 있는가"를 묻는데, 못 읽은 픽스처가 남아 있으면 그 물음에
    답할 수 없다 — 없다고 답하면 **중복 생성**이고, 이 앱에는 실행 취소가 없다.
    그래서 막고 사유를 붙인다. 되돌릴 수 없는 쓰기에서 "모르면 하지 않는다"가 기본값이다.

    `missing_count == 0`이면 통과시킨다 — 열거 절단만으로는 막지 않는다(위 독스트링).
    """
    caveat = console_read_caveat(inventory)
    if caveat is None or caveat["kind"] != CONSOLE_READ_INCOMPLETE:
        return address_plan

    target_by_id = {target.id: target for target in targets}
    exclusions = list(address_plan.exclusions)
    for planned in address_plan.entries:
        target = target_by_id.get(planned.candidate_id)
        if target is None:
            raise ValueError(
                f"주소 계획에 대상 없는 항목이 있다: {planned.candidate_id!r} — "
                "계획과 대상 집합은 같은 호출에서 나온 것이어야 한다."
            )
        exclusions.append(_exclusion(target, CONSOLE_READ_INCOMPLETE, str(caveat["reason"])))
    return AddressPlan(entries=(), exclusions=tuple(exclusions))


def screen_console_occupancy(
    targets: Sequence[PatchCandidate],
    *,
    address_plan: AddressPlan,
    console_fixtures: Sequence[ConsoleFixture],
) -> AddressPlan:
    """계획 구간 **안쪽에서 시작하는 남의 픽스처**를 잡아 그 항목을 제외한다.

    자기 도면 주소에 있는 픽스처는 건드리지 않는다 — 그것은 `screen_idempotent`가 타입·모드까지
    보고 멱등/충돌/확인 불가로 갈라야 하는 대상이다. 여기서 먼저 점유로 잡으면 그 셋이 뭉개진다.

    **점유폭은 1채널로만 본다.** 기존 픽스처의 폭을 읽을 경로가 이 빌드에 없다(`DMXFootprint`는
    직렬화되지 않고 `DMXChannels` 개수는 폭이 아니다 — M0 함정 7). 그래서 **꼬리 방향 겹침**
    (기존 픽스처가 우리 구간 **앞에서** 시작해 우리 시작 주소를 덮는 경우)은 **검출되지 않는다** —
    그 미검출은 추측으로 메우지 않고 `existing_footprint_unreadable`로 보고한다(round11 N04).
    """
    target_by_id = {target.id: target for target in targets}
    kept: list[AddressPlanEntry] = []
    exclusions: list[PatchTargetExclusion] = list(address_plan.exclusions)

    for planned in address_plan.entries:
        target = target_by_id.get(planned.candidate_id)
        if target is None:
            raise ValueError(
                f"주소 계획에 대상 없는 항목이 있다: {planned.candidate_id!r} — "
                "계획과 대상 집합은 같은 호출에서 나온 것이어야 한다."
            )
        intruder = next(
            (
                fixture
                for fixture in console_fixtures
                if fixture.universe == planned.universe
                and fixture.address is not None
                and planned.address < fixture.address <= planned.end_address
            ),
            None,
        )
        if intruder is None:
            kept.append(planned)
            continue
        exclusions.append(
            _exclusion(
                target,
                ADDRESS_ALREADY_OCCUPIED,
                f"유니버스 {planned.universe} 주소 {planned.address}~{planned.end_address} 구간 "
                f"안에서 기존 픽스처(슬롯 {intruder.slot}, 주소 {intruder.address})가 시작한다 — "
                "빈 주소로 옮겨 붙이지 않고 제외한다.",
            )
        )

    return AddressPlan(entries=tuple(kept), exclusions=tuple(exclusions))


def existing_footprint_skipped_check() -> Mapping[str, object]:
    """기존 픽스처 점유폭 미판독 — **무엇을 못 잡는지** 구조화해 보고한다(round11 N04)."""
    return {
        "kind": validate_autopatch("skipped_check_kind", EXISTING_FOOTPRINT_UNREADABLE),
        "label": skipped_check_label(EXISTING_FOOTPRINT_UNREADABLE),
        "reason": (
            "기존 픽스처의 점유폭을 읽을 경로가 이 빌드에 없어(DMXFootprint 미직렬화 · "
            "DMXChannels 개수는 폭이 아님) 기존 픽스처를 시작 주소 1채널로만 본다 — "
            "기존 픽스처가 계획 구간 **앞에서** 시작해 우리 주소를 덮는 겹침은 검출되지 않는다."
        ),
    }


def screen_idempotent(
    targets: Sequence[PatchCandidate],
    *,
    address_plan: AddressPlan,
    resolutions: Sequence[TypeResolution],
    console_fixtures: Sequence[ConsoleFixture],
) -> AddressPlan:
    """이미 존재하는 항목을 **생성 산출물에서 빼고** 사유를 붙인 계획을 돌려준다.

    반환값이 다시 `AddressPlan`인 것은 의도다 — `build_patch_handoff`이 그대로 받아
    같은 보고 경로로 내보내므로, 멱등 판정이 **전달되는 Lua의 내용**에 반영된다
    (AC-AUTOPATCH-020①). 판정은 세 갈래이며 서로 뭉뚱그리지 않는다:

    - 네 값(유니버스·주소·타입·모드) 전부 일치 → **멱등 건너뜀**
    - 주소는 같은데 타입 또는 모드가 다름 → **충돌**(건너뛰지 않는다)
    - 주소는 같은데 기존 픽스처의 정체를 확정할 수 없음 → **확인 불가**
    """
    target_by_id = {target.id: target for target in targets}
    resolution_by_id = {resolution.request.candidate_id: resolution for resolution in resolutions}

    kept: list = []
    exclusions: list[PatchTargetExclusion] = list(address_plan.exclusions)

    for planned in address_plan.entries:
        target = target_by_id.get(planned.candidate_id)
        if target is None:
            raise ValueError(
                f"주소 계획에 대상 없는 항목이 있다: {planned.candidate_id!r} — "
                "계획과 대상 집합은 같은 호출에서 나온 것이어야 한다."
            )
        resolution = resolution_by_id.get(planned.candidate_id)
        occupants = _fixtures_at(console_fixtures, planned.universe, planned.address)

        if not occupants:
            kept.append(planned)
            continue

        # [round11 N10] 그 주소에 둘 이상이 있으면 어느 것과 대조해야 하는지 알 수 없다 —
        # 첫 일치가 우리와 같다고 '이미 했음'으로 삼키면 두 번째 점유자를 못 본 채 넘긴다.
        if len(occupants) > 1:
            exclusions.append(
                _exclusion(
                    target,
                    EXISTING_IDENTITY_UNCONFIRMED,
                    f"유니버스 {planned.universe} 주소 {planned.address}에 "
                    f"픽스처가 {len(occupants)}대 관측된다 — 어느 것과 대조할지 확정할 수 없다.",
                )
            )
            continue

        occupant = occupants[0]

        # [round11 N08] 우리 쪽 타입이 미확정이면 그것은 '남의 픽스처가 점유'가 아니라
        # '우리가 아직 확인을 못 받았다'이다. 둘을 같은 코드로 적으면 사용자가 원인을 오독한다.
        expected_type, expected_mode = _expected_identity(resolution)
        if expected_type is None or expected_mode is None:
            exclusions.append(
                _exclusion(
                    target,
                    TYPE_CONFIRMATION_PENDING,
                    "콘솔 타입·모드가 확정되지 않아 기존 픽스처와 대조할 수 없다 — "
                    "확인 전에는 멱등 판정도 충돌 판정도 내리지 않는다.",
                )
            )
            continue

        if not occupant.identity_resolved:
            exclusions.append(
                _exclusion(
                    target,
                    EXISTING_IDENTITY_UNCONFIRMED,
                    f"유니버스 {planned.universe} 주소 {planned.address}에 픽스처가 있으나 "
                    f"표시 문자열({occupant.type_display!r} · {occupant.mode_display!r})을 "
                    "라이브러리에 대조해 확정할 수 없다 — 이미 했음으로 간주하지 않는다.",
                )
            )
            continue

        if occupant.type_name == expected_type and occupant.mode_name == expected_mode:
            exclusions.append(
                _exclusion(
                    target,
                    ALREADY_PATCHED_IDENTICAL,
                    f"유니버스 {planned.universe} 주소 {planned.address}에 "
                    f"{expected_type} · {expected_mode} 픽스처가 이미 있다 — 중복 생성하지 않는다.",
                )
            )
            continue

        exclusions.append(
            _exclusion(
                target,
                ADDRESS_CONFLICTS_WITH_EXISTING,
                f"유니버스 {planned.universe} 주소 {planned.address}를 "
                f"{occupant.type_name} · {occupant.mode_name} 픽스처가 점유하고 있다 — "
                "무관한 픽스처를 '이미 했음'으로 삼키지 않는다.",
            )
        )

    return AddressPlan(entries=tuple(kept), exclusions=tuple(exclusions))


def _expected_identity(resolution: TypeResolution | None) -> tuple[str | None, str | None]:
    if resolution is None or resolution.console_type is None or resolution.console_mode is None:
        return None, None
    return resolution.console_type.name, resolution.console_mode.name


def _fixtures_at(
    console_fixtures: Sequence[ConsoleFixture], universe: int, address: int
) -> tuple[ConsoleFixture, ...]:
    return tuple(
        fixture
        for fixture in console_fixtures
        if fixture.universe == universe and fixture.address == address
    )


def _fixture_at(
    console_fixtures: Sequence[ConsoleFixture], universe: int, address: int
) -> ConsoleFixture | None:
    """그 주소의 픽스처. **둘 이상이면 `None`이 아니라 모호**이므로 호출자가 갈라 처리한다.

    [round11 N10] 이전 판은 첫 일치만 돌려줘서, 콘솔에 이미 중복이 있고 첫 일치가 우리와
    동일하면 두 번째 충돌 점유자를 보지 못한 채 `already_patched_identical`을 냈다.
    """
    found = _fixtures_at(console_fixtures, universe, address)
    return found[0] if len(found) == 1 else None


@dataclass(frozen=True)
class VerificationResult:
    candidate_id: str
    universe: int
    address: int
    expected_type: str
    expected_mode: str
    outcome: str
    observed_type: str | None
    observed_mode: str | None
    detail: str

    def to_dict(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "universe": self.universe,
            "address": self.address,
            "expected_type": self.expected_type,
            "expected_mode": self.expected_mode,
            "observed_type": self.observed_type,
            "observed_mode": self.observed_mode,
            "outcome": validate_autopatch("verification_outcome", self.outcome),
            "label": verification_outcome_label(self.outcome),
            "detail": self.detail,
        }


@dataclass(frozen=True)
class PatchVerification:
    results: tuple[VerificationResult, ...] = ()
    guidance: tuple[str, ...] = ()

    def _count(self, outcome: str) -> int:
        return sum(1 for result in self.results if result.outcome == outcome)

    @property
    def observed_count(self) -> int:
        return self._count(VERIFICATION_OBSERVED)

    @property
    def created_count(self) -> int:
        """관측으로 **확정된** 생성 건수. 불일치·확인 불가는 여기에 들어오지 않는다."""
        return self.observed_count

    @property
    def mismatch_count(self) -> int:
        return self._count(VERIFICATION_MISMATCHED)

    @property
    def all_observed(self) -> bool:
        return all(result.outcome == VERIFICATION_OBSERVED for result in self.results)

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": True,
            "all_observed": self.all_observed,
            "observed_count": self.observed_count,
            "not_observed_count": self._count(VERIFICATION_NOT_OBSERVED),
            "mismatch_count": self.mismatch_count,
            "identity_unconfirmed_count": self._count(VERIFICATION_IDENTITY_UNCONFIRMED),
            "created_count": self.created_count,
            "results": [result.to_dict() for result in self.results],
            "guidance": list(self.guidance),
        }


def verify_patch(
    entries: Sequence[HandoffEntry],
    *,
    console_fixtures: Sequence[ConsoleFixture],
    read_complete: bool = True,
) -> PatchVerification:
    """전달한 항목이 실제로 그 주소에 그 타입으로 생겼는지 **재조회로만** 판정한다.

    **플러그인의 종료 상태를 받는 인자가 없다** — 그것이 성공의 근거가 될 수 없기 때문이다
    (함정 4 · AC-AUTOPATCH-021②). 성공은 오직 관측에서 나온다. `read_complete`는 그 반대편을
    막는다: 재조회가 불완전하면 **미판독을 미관측으로 적지 않는다**.
    불일치는 구조화해 보고하고 **자동 보정도 재시도도 하지 않는다**(AC-AUTOPATCH-022).
    """
    results: list[VerificationResult] = []
    for entry in entries:
        occupant = _fixture_at(console_fixtures, entry.universe, entry.address)
        if occupant is None and not read_complete:
            # 못 읽은 픽스처가 남아 있으면 "없다"고 단정할 수 없다 — 미판독을 미관측으로
            # 적으면 사용자가 "실행이 안 됐다"고 읽고 다시 실행해 중복을 만든다.
            outcome = VERIFICATION_IDENTITY_UNCONFIRMED
            detail = "재조회가 불완전해 그 주소의 상태를 단정할 수 없다 — 미관측이 아니다."
        elif occupant is None:
            outcome = VERIFICATION_NOT_OBSERVED
            detail = "그 유니버스·주소에서 픽스처가 관측되지 않았다."
        elif not occupant.identity_resolved:
            outcome = VERIFICATION_IDENTITY_UNCONFIRMED
            detail = (
                f"픽스처는 있으나 표시 문자열({occupant.type_display!r} · "
                f"{occupant.mode_display!r})을 라이브러리에 대조해 확정할 수 없다."
            )
        elif occupant.type_name == entry.console_type and occupant.mode_name == entry.console_mode:
            outcome = VERIFICATION_OBSERVED
            detail = "승인한 타입·모드로 관측됐다."
        else:
            outcome = VERIFICATION_MISMATCHED
            detail = "그 주소에 다른 타입 또는 모드가 관측됐다."

        results.append(
            VerificationResult(
                candidate_id=entry.candidate_id,
                universe=entry.universe,
                address=entry.address,
                expected_type=entry.console_type,
                expected_mode=entry.console_mode,
                outcome=outcome,
                observed_type=occupant.type_name if occupant is not None else None,
                observed_mode=occupant.mode_name if occupant is not None else None,
                detail=detail,
            )
        )

    verification = PatchVerification(results=tuple(results))
    if results and verification.created_count == 0:
        verification = PatchVerification(
            results=tuple(results), guidance=(ZERO_CREATED_GUIDANCE, NO_AUTO_CORRECTION)
        )
    elif not verification.all_observed:
        verification = PatchVerification(results=tuple(results), guidance=(NO_AUTO_CORRECTION,))
    return verification
