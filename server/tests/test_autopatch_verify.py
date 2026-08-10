"""M6 — 멱등 · 검증 읽기.

AC-AUTOPATCH-020 (멱등) · AC-AUTOPATCH-021 (검증 읽기) ·
AC-AUTOPATCH-022 (불일치 보고 · 자동 보정 0).

**M0가 이 마일스톤에 남긴 제약** (`progress.md` §E.2 M0 1차, §0 함정 3):
콘솔이 돌려주는 `FixtureType`·`Mode`는 **표시 문자열**이다 — 실측 형태는 `FixtureType 3` ·
`2 Mode 2`이고, 라이브러리 쪽 이름은 `Robin LEDBeam 350` · `Mode 1`이다. 즉 네 값 일치
판정(REQ-AUTOPATCH-022)은 **문자열 동등으로 성립하지 않는다.** 이 파일은 그 해석이
**열거된 라이브러리에 대조해 모호하지 않을 때만** 성립하고, 모호하면 **확인 불가로 보고**하는지를
검증한다 — 슬롯==FID 우연일치를 `fid_cid_identity_unreachable`로 남긴 1단계 선례와 같은 규율이다.

비공허성 하네스(`server.bridge` 기록기 + 모듈 사본)는 `test_autopatch_execute.py`의 것을
그대로 쓴다 — 같은 기록기·같은 적재 방식이어야 "같은 기록기가 잡는다"가 성립한다.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import NamedTuple

import pytest

from server.prechk.inventory import (
    COMPLETE,
    FIXTURE_ROOT,
    FixtureRecord,
    Inventory,
    ReadFailure,
)
from server.tests.test_autopatch_contract import iter_vwx_modules, vwx_module_label
from server.tests.test_autopatch_execute import (
    APPLY_SOURCE,
    CD_TOKEN,
    REFUTED_REMEDY_TOKENS,
    RecordingDeployPipeline,
    RecordingExecutionPort,
    _console_bound_text,
    _console_surface,
    _load,
)
from server.tests.test_autopatch_types import LibraryRigPort
from server.tests.test_autopatch_types import request as _r17_type_request
from server.vwx.apply import (
    _NEUTRAL_FIELDS,
    CONSOLE_READ_INCOMPLETE,
    CONSOLE_READ_INDEX_DOMAIN_UNKNOWN,
    CONSOLE_READ_UNPATCHED_PRESENT,
    NO_AUTO_CORRECTION,
    PATCH_ADDRESSED,
    PATCH_UNPATCHED,
    PATCH_UNREAD,
    ZERO_CREATED_GUIDANCE,
    HandoffEntry,
    build_patch_handoff,
    classify_patch_value,
    console_read_caveat,
    existing_footprint_skipped_check,
    read_console_fixtures,
    screen_console_occupancy,
    screen_console_read,
    screen_idempotent,
    verify_patch,
)
from server.vwx.luagen import LuaPatchEntry
from server.vwx.patchplan import AddressPlan, AddressPlanEntry, PatchCandidate
from server.vwx.typemap import (
    FixtureTypeLibrary,
    LibraryMode,
    LibraryType,
    TypeRequest,
    TypeResolution,
    resolve_fixture_types,
)
from server.vwx.verdicts import (
    ADDRESS_ALREADY_OCCUPIED,
    ADDRESS_CONFLICTS_WITH_EXISTING,
    ALREADY_PATCHED_IDENTICAL,
    EXISTING_FOOTPRINT_UNREADABLE,
    EXISTING_IDENTITY_UNCONFIRMED,
    FIXTURE_TYPE_NAME_UNUSABLE,
    TARGET_EXCLUSION_REASON,
    TYPE_CONFIRMATION_PENDING,
    TYPE_NEEDS_CONFIRMATION,
    TYPE_RESOLVED,
    VERIFICATION_IDENTITY_UNCONFIRMED,
    VERIFICATION_MISMATCHED,
    VERIFICATION_NOT_OBSERVED,
    VERIFICATION_OBSERVED,
    VERIFICATION_OUTCOME,
    target_exclusion_label,
    verification_outcome_label,
)

APPLY_PATH = Path("server/vwx/apply.py")

INCOMPLETE = "incomplete"

LED = "Robin LEDBeam 350"
MMX = "Robin MMX Spot"
MODE_1 = "Mode 1"
MODE_2 = "Mode 2"


# --------------------------------------------------------------------------
# 더블 — 콘솔 라이브러리와 `read_inventory` 산출물
# --------------------------------------------------------------------------


def _library(*types: LibraryType, available: bool = True) -> FixtureTypeLibrary:
    """**전수로 읽힌** 라이브러리 스냅샷 — 선언 총계까지 채운다.

    [round25 R24-2] 이전 판은 `child_count`를 비워 두었다. 그래서 이 파일 **34건**이
    *"선언 총계를 못 읽었다"*는 상태 위에서 돌았고, 그 상태에서 index 형태 단독 해석이
    확정되는 것이 R24-2의 결함이다. 예외 하나가 아니라 **공용 픽스처의 기본값**이
    결함 상태였다는 것이 그 결함이 상용으로 남은 이유다.

    총계·열거 계수·반환 행 수를 **함께** 채운다. 하나만 채우면 `enumeration_short`가
    서서 스냅샷이 자기모순이 된다. 셋을 함께 주는 것이 실물이 준 형태다 —
    `childCount == len(children)` · `truncated=false`(2026-08-08 M8 실측).

    총계를 **비운** 상태를 시험해야 하는 자리는 이 헬퍼를 쓰지 않고
    `_r25_unread_total()`을 쓴다. 그 쌍(채운 것/비운 것)을 의도적으로 남긴다 —
    전부 채우면 `None` 경로가 무방비로 남고, 그것이 지금 상황을 만든 원인이다.
    """
    if not types:
        types = (
            LibraryType(index=1, name=MMX, modes=(LibraryMode(index=1, name=MODE_1),)),
            LibraryType(
                index=3,
                name=LED,
                modes=(
                    LibraryMode(index=1, name=MODE_1),
                    LibraryMode(index=2, name=MODE_2),
                ),
            ),
        )
    return FixtureTypeLibrary(
        types=types,
        available=available,
        child_count=len(types),
        enumerated_count=len(types),
        returned_row_count=len(types),
    )


def _record(slot: int, patch: str | None, type_display: str | None, mode_display: str | None):
    return FixtureRecord(
        slot=slot,
        name=f"fixture {slot}",
        patch_raw=patch,
        fixture_type=type_display,
        mode=mode_display,
    )


def _inventory(*records: FixtureRecord) -> Inventory:
    return Inventory(
        path=FIXTURE_ROOT,
        child_count=len(records),
        enumerated_count=len(records),
        recovered_count=0,
        observed_count=len(records),
        missing_count=0,
        completeness=COMPLETE,
        recovery_boundary=None,
        index_domain_unknown=False,
        fixtures=records,
    )


def _console(*records: FixtureRecord, library: FixtureTypeLibrary | None = None):
    return read_console_fixtures(
        _inventory(*records), library=library if library is not None else _library()
    )


# --------------------------------------------------------------------------
# 더블 — 계획 측
# --------------------------------------------------------------------------


def _candidate(candidate_id: str, universe: int, address: int, fid: int) -> PatchCandidate:
    return PatchCandidate(
        id=candidate_id,
        unit_number=None,
        instrument_type=LED,
        universe=universe,
        address=address,
        detail="",
        address_basis="universe_address_direct",
        source_index=0,
        assigned_fid=fid,
    )


def _resolution(candidate_id: str, *, type_name: str = LED, mode_name: str = MODE_1):
    return TypeResolution(
        request=TypeRequest(candidate_id=candidate_id, instrument_type=LED),
        status=TYPE_RESOLVED,
        reason="",
        console_type=LibraryType(index=3, name=type_name),
        console_mode=LibraryMode(index=1, name=mode_name),
    )


def _planned(candidate_id: str, universe: int, address: int) -> AddressPlanEntry:
    return AddressPlanEntry(
        candidate_id=candidate_id,
        universe=universe,
        address=address,
        footprint=16,
        end_address=address + 15,
    )


def _entry(candidate_id: str, universe: int, address: int, *, mode: str = MODE_1):
    return HandoffEntry(
        candidate_id=candidate_id,
        fid=101,
        name=f"LEDBeam {candidate_id}",
        console_type=LED,
        console_mode=mode,
        universe=universe,
        address=address,
        footprint=16,
    )


def _screen(*, console, targets=None, plan=None, resolutions=None) -> AddressPlan:
    targets = targets or (_candidate("a", 1, 1, 101),)
    plan = plan or AddressPlan(entries=(_planned("a", 1, 1),))
    resolutions = resolutions or tuple(_resolution(target.id) for target in targets)
    return screen_idempotent(
        targets, address_plan=plan, resolutions=resolutions, console_fixtures=console
    )


# --------------------------------------------------------------------------
# 표시 문자열 해석 — 모호하면 확인 불가로 남긴다
# --------------------------------------------------------------------------


def test_the_measured_display_forms_resolve_against_the_enumerated_library():
    """실측 형태 `FixtureType 3` · `2 Mode 2`가 라이브러리 대조로 해석된다."""
    (observed,) = _console(_record(1, "3.1", "FixtureType 3", "2 Mode 2"))
    assert observed.universe == 3
    assert observed.address == 1
    assert observed.type_name == LED
    assert observed.mode_name == MODE_2
    assert observed.identity_resolved is True


def test_a_display_string_that_is_also_a_literal_type_name_stays_unresolved():
    """우연일치는 해석하지 않는다.

    이름이 `FixtureType 2`인 타입이 index 2가 **아니면** 두 해석이 갈라진다 — 모호하다.
    """
    library = _library(
        LibraryType(index=2, name=LED, modes=(LibraryMode(index=1, name=MODE_1),)),
        LibraryType(index=5, name="FixtureType 2", modes=(LibraryMode(index=1, name=MODE_1),)),
    )
    (observed,) = _console(_record(1, "1.1", "FixtureType 2", "1 Mode 1"), library=library)
    assert observed.type_name is None
    assert observed.identity_resolved is False
    assert observed.type_display == "FixtureType 2"


def test_the_ambiguity_control_a_coinciding_index_and_name_is_not_ambiguous():
    """비공허성 — 같은 답으로 수렴하는 우연일치까지 거부하지는 않는다."""
    library = _library(
        LibraryType(index=2, name="FixtureType 2", modes=(LibraryMode(index=1, name=MODE_1),)),
    )
    (observed,) = _console(_record(1, "1.1", "FixtureType 2", "1 Mode 1"), library=library)
    assert observed.type_name == "FixtureType 2"
    assert observed.identity_resolved is True


def test_a_bare_mode_name_also_resolves():
    (observed,) = _console(_record(1, "1.1", "FixtureType 3", MODE_2))
    assert observed.mode_name == MODE_2


def test_an_unreadable_library_leaves_every_identity_unresolved():
    (observed,) = _console(
        _record(1, "1.1", "FixtureType 3", "2 Mode 2"),
        library=FixtureTypeLibrary(available=False),
    )
    assert observed.type_name is None
    assert observed.mode_name is None
    assert observed.identity_resolved is False


def test_an_unparsable_patch_value_is_not_given_a_fabricated_address():
    (observed,) = _console(_record(1, "not-an-address", "FixtureType 3", "2 Mode 2"))
    assert observed.universe is None
    assert observed.address is None


def test_no_channel_count_is_parsed_out_of_a_display_string():
    """함정 3 — 표시 문자열에서 채널 수를 파싱하지 않는다."""
    (observed,) = _console(_record(1, "1.1", "FixtureType 3", "2 Mode 2"))
    assert not hasattr(observed, "footprint")
    assert not hasattr(observed, "channel_count")


# --------------------------------------------------------------------------
# [round25 R24-2] 선언 총계 미판독 — 부정 증거를 쓸 **자격**
# --------------------------------------------------------------------------
#
# round24가 `typemap`에서 명명한 근본 원인(**`None`이 두 뜻**: *"전수 확인함"* /
# *"말할 근거 없음"*)이 형제 표면 `apply._resolve_library_type`에 그대로 남아 있었다.
# 그 자리는 index 형태 해석을 *"그 이름이 열거에 없다"*는 **부정 증거** 위에 세우고,
# 그 증거의 자격을 `library.enumeration_incomplete` 하나로 쟀다 — 그런데 그 union의
# 계수 갈래는 전부 `child_count is None`에서 **거짓**이다. 총계를 못 읽은 스냅샷이
# "전수를 봤다"로 읽혔고, 그 위에서 `FixtureType 2`가 라이브러리 타입으로 **확정**돼
# `screen_idempotent`의 멱등/충돌 판정과 `verify_patch`로 갔다.
#
# 아래 세 시험이 **의도적으로 남긴 한 쌍**이다: `_r25_unread_total()`(비운 것) ·
# `_r25_declared_total()`(채운 것). 공용 픽스처 `_library()`는 이제 총계를 채우므로,
# 이 쌍이 없으면 `None` 경로가 무방비로 남는다 — 그것이 지금 상황을 만든 원인이다.

_R25_TYPES = (
    LibraryType(index=1, name=MMX, modes=(LibraryMode(index=1, name=MODE_1),)),
    LibraryType(
        index=3,
        name=LED,
        modes=(LibraryMode(index=1, name=MODE_1), LibraryMode(index=2, name=MODE_2)),
    ),
)


def _r25_unread_total() -> FixtureTypeLibrary:
    """선언 총계를 **못 읽은** 라이브러리 — 어느 축도 서지 않는다.

    이것이 round24까지 `_library()`의 기본값이었다. 예외가 아니라 **기본값**이었다.
    """
    return FixtureTypeLibrary(types=_R25_TYPES, available=True)


def _r25_declared_total() -> FixtureTypeLibrary:
    """선언 총계를 읽었고 열거가 그것과 일치하는 라이브러리 — 실물 M8이 준 형태다."""
    return FixtureTypeLibrary(
        types=_R25_TYPES,
        available=True,
        child_count=len(_R25_TYPES),
        enumerated_count=len(_R25_TYPES),
        returned_row_count=len(_R25_TYPES),
    )


def test_r25_an_unread_declared_total_refuses_the_index_only_reading():
    """[R24-2 결함 재현] 총계를 못 읽었으면 *"열거에 없다"*를 근거로 쓸 수 없다.

    죽이는 뮤테이션:
      · `_resolve_library_type`의 가드를 `library.enumeration_incomplete`로 되돌리면
        ③이 실패한다(①이 그 값을 거짓으로 못박으므로 가드가 발화하지 못한다).
      · 가드를 통째로 지워도 ③이 실패한다.
      · `_confirmable_from`을 `is not False`로 바꾸면 ②는 살아남고 ③이 실패한다 —
        `None`을 참으로 취급하는 방향이 정확히 이 결함이다.
    """
    from server.vwx.typemap import _confirmable_from, _library_list_completeness

    library = _r25_unread_total()

    # ① 구판 가드가 보던 값은 **전부 거짓**이다 — 축이 하나도 서지 않는다.
    assert library.truncated is False
    assert library.enumeration_short is False
    assert library.over_enumerated is False
    assert library.rows_discarded == 0
    assert library.enumeration_incomplete is False
    # ② 그런데 이 목록을 전수라고 **주장하지도 못한다** — 삼치의 `None`이다.
    assert _library_list_completeness(library).complete is None
    assert _confirmable_from(_library_list_completeness(library)) is False
    # ③ 그래서 index 단독 해석은 확정되지 않는다. 확정보다 약한 근거로 확정이 나갈 수 없다.
    (observed,) = _console(_record(1, "3.1", "FixtureType 3", "2 Mode 2"), library=library)
    assert observed.type_name is None
    assert observed.mode_name is None
    assert observed.identity_resolved is False
    assert observed.type_display == "FixtureType 3"


def test_r25_a_declared_total_that_matches_the_enumeration_still_confirms():
    """[짝 — 정상 확정 무회귀] 총계를 읽었고 열거가 그것과 같으면 여전히 확정된다.

    앞 시험과 **한 칸만** 다르다(`child_count` 계열). 그 한 칸이 판정을 가른다는 것이
    이 쌍의 전부이고, 이 쪽이 없으면 앞 시험은 과차단을 결함으로 오인한 것이 된다.

    죽이는 뮤테이션: 가드를 `not by_name`과 무관하게 발화시키거나 완전성 술어를 항상
    거짓으로 만들면 이 시험이 실패한다(과차단 방향).
    """
    from server.vwx.typemap import _confirmable_from, _library_list_completeness

    library = _r25_declared_total()
    assert _library_list_completeness(library).complete is True
    assert _confirmable_from(_library_list_completeness(library)) is True

    (observed,) = _console(_record(1, "3.1", "FixtureType 3", "2 Mode 2"), library=library)
    assert observed.type_name == LED
    assert observed.mode_name == MODE_2
    assert observed.identity_resolved is True


def test_r25_positive_name_evidence_survives_an_unread_declared_total():
    """[과차단 경계] 가드가 막는 것은 **부정 증거**뿐이다.

    이름이 정확히 일치한 것은 총계를 못 읽었는지와 무관한 **긍정 증거**다. 이것까지
    막으면 총계를 못 읽는 콘솔에서 멱등 판정이 영영 성립하지 않는다 — round11 N01이
    같은 자리에서 이미 내린 판단이고, 그 판단은 이번에도 유효하다.

    죽이는 뮤테이션: 가드에서 `not by_name` 절을 지우면 이 시험이 실패한다.
    """
    library = _r25_unread_total()
    (observed,) = _console(_record(1, "3.1", LED, "2 Mode 2"), library=library)
    assert observed.type_name == LED
    assert observed.mode_name == MODE_2
    assert observed.identity_resolved is True


def test_r25_the_live_m8_library_confirms_every_index_form_display():
    """[HARD 과차단 금지] 실물 M8 라이브러리에서 index 형태 표시가 **8모드 전부** 확정된다.

    이 자리는 **정상 확정 경로**다 — 콘솔이 픽스처에 실어 주는 타입 표시는 실측 형태가
    `FixtureType 3`이라(§E.2 M0 1차) 대개 `by_name`이 비어 있고, 확정은 index 해석에
    달려 있다. 여기를 조이면 멀쩡한 리그에서 정체가 확정되지 않고 멱등 판정이 통째로
    `identity_unconfirmed`로 내려앉는다. 그래서 새 가드가 실물에서 **한 번도 발화하지
    않는다**는 것을 값으로 못박는다.

    실물이 준 형태(`childCount == len(children)` · `truncated=false`)를 그대로 쓰는
    `LibraryRigPort`로 읽고, 3종 × 전 8모드를 index 형태로 대조한다.

    죽이는 뮤테이션: 완전성 술어를 항상 거짓으로 만들거나 가드에서 `not by_name`을
    지우면 8건이 전부 실패한다.
    """
    from server.tests.test_autopatch_types import _R21_THREE_TYPE_LIBRARY
    from server.vwx.typemap import read_fixture_type_library

    library = read_fixture_type_library(LibraryRigPort(_R21_THREE_TYPE_LIBRARY))
    # ① 실물 스냅샷의 형태 전제 — 이것이 깨지면 아래는 M8을 재는 것이 아니다.
    assert library.truncated is False
    assert library.child_count == len(library.types) == 3
    assert library.enumeration_incomplete is False

    cases = [
        (type_index, mode_index, type_name, mode_name)
        for type_index, (type_name, modes) in enumerate(_R21_THREE_TYPE_LIBRARY, start=1)
        for mode_index, (mode_name, _channels) in enumerate(modes, start=1)
    ]
    assert len(cases) == 8, cases  # 4 + 1 + 3 — 실물 3종의 전 모드

    observed = read_console_fixtures(
        _inventory(
            *(
                _record(slot, f"1.{slot}", f"FixtureType {t}", f"{m} {mode_name}")
                for slot, (t, m, _type_name, mode_name) in enumerate(cases, start=1)
            )
        ),
        library=library,
    )
    # ② 8모드 전부 확정 — 미확정이 하나도 없다.
    assert [fixture.identity_resolved for fixture in observed] == [True] * 8
    assert [(fixture.type_name, fixture.mode_name) for fixture in observed] == [
        (type_name, mode_name) for _t, _m, type_name, mode_name in cases
    ]
    # ③ **비공허성** — 이 확정들이 실제로 새 가드를 지나왔다는 증거. 8건 중 7건은
    #    이름 일치가 0건이라 index 해석 **단독**이고, 그것을 허가하는 것이 완전성
    #    술어다(허가가 없으면 ②가 7건 무너진다). 나머지 1건은 실물 M8의
    #    `FixtureType 2` — 이름이 곧 index 형태인 타입이라(U-04 · AC-026⑦) 긍정
    #    증거로도 확정되고, 가드와 무관하다. 그 1건을 7건과 같이 세면 이 대조군이
    #    "가드를 지났다"를 재지 못한다.
    index_only = [
        fixture
        for fixture in observed
        if not [entry for entry in library.types if entry.name == fixture.type_display]
    ]
    assert len(index_only) == 7
    coincident = [fixture for fixture in observed if fixture not in index_only]
    assert {fixture.type_display for fixture in coincident} == {"FixtureType 2"}


#: [round25 R24-2 · 형제 전수] `apply.py`가 **부재를 근거로 결론을 내는 자리** 전수와,
#: 그 결론이 기대는 열거 · 그 열거의 **선언 총계 필드 타입**.
#:
#: 넷 모두 *"열거에 없으니 없다"*를 쓴다. 갈리는 것은 총계를 **못 읽을 수 있는가**다:
#: `prechk.read_inventory`는 `childCount`를 못 읽으면 `InventoryReadError`로 거부하므로
#: 아래 셋에는 *"말할 근거 없음"* 상태가 도착하지 않는다. `FixtureTypeLibrary`만
#: `int | None`이고, 그 비대칭이 R24-2의 뿌리다.
_R25_NEGATIVE_EVIDENCE_SITES = (
    ("_resolve_library_type", "FixtureTypeLibrary", "int | None"),
    ("screen_console_occupancy", "Inventory", "int"),
    ("screen_idempotent", "Inventory", "int"),
    ("verify_patch", "Inventory", "int"),
)


def test_r25_only_one_negative_evidence_surface_reads_an_optional_declared_total():
    """형제 전수 — 부재를 근거로 쓰는 자리 넷 중 **셋은 총계가 필수**다.

    R24-2를 한 자리만 고치고 끝내지 않기 위한 등기다. 다음 라운드가 이 파일에서 같은
    병을 찾으면 이 표부터 본다.

    죽이는 뮤테이션:
      · 표에서 어느 행을 지워도 ①이 실패한다(넷 전부 `apply.py`에 실재해야 한다).
      · `prechk.inventory`가 총계 미판독을 허용하게 바뀌면 ②·④가 실패한다 — 그 순간
        형제 셋이 같은 병에 걸린다는 사실이 여기서 먼저 발화한다.
      · `_resolve_library_type` 행의 타입을 `int`로 적으면 ③이 실패한다.
    """
    import server.vwx.apply as apply_module
    from server.prechk.inventory import FIXTURE_ROOT as _ROOT
    from server.prechk.inventory import Inventory as _Inventory
    from server.prechk.inventory import InventoryReadError, read_inventory

    # ① 표의 자리가 전부 실재한다 — 이름만 남고 함수가 사라지는 등기를 막는다.
    for name, _owner, _annotation in _R25_NEGATIVE_EVIDENCE_SITES:
        assert hasattr(apply_module, name), name

    # ② 선언 총계 타입은 표가 적은 그대로다.
    owners = {"FixtureTypeLibrary": FixtureTypeLibrary, "Inventory": _Inventory}
    for name, owner, annotation in _R25_NEGATIVE_EVIDENCE_SITES:
        assert owners[owner].__dataclass_fields__["child_count"].type == annotation, name

    # ③ 그중 총계를 못 읽을 수 있는 자리는 **하나뿐**이고, 그 자리가 이번에 닫혔다.
    optional = {
        name
        for name, _owner, annotation in _R25_NEGATIVE_EVIDENCE_SITES
        if annotation == "int | None"
    }
    assert optional == {"_resolve_library_type"}

    # ④ 나머지 셋의 근거 — 리더가 총계 미판독을 **거부한다**(단정하지 않는다).
    class _NoTotalPort:
        def query_state(self, path: str) -> dict:
            return {"ok": True, "path": path, "node": {"name": "Fixtures"}, "children": []}

        def query_property(self, path: str, property_name: str) -> dict:  # pragma: no cover
            raise AssertionError("총계를 못 읽으면 프로퍼티까지 가지 않는다")

    with pytest.raises(InventoryReadError, match="childCount"):
        read_inventory(_NoTotalPort())
    assert _ROOT  # 경로 상수가 살아 있어야 위 포트가 그 경로로 불린다


# --------------------------------------------------------------------------
# AC-AUTOPATCH-020 — 멱등
# --------------------------------------------------------------------------


def test_an_identical_existing_fixture_is_skipped_with_a_reason():
    """AC-020① — 네 값 전부 일치하면 산출물에서 제외되고 건너뛴 사실이 보고된다."""
    plan = _screen(console=_console(_record(1, "1.1", "FixtureType 3", "1 Mode 1")))
    assert plan.entries == ()
    assert [exclusion.code for exclusion in plan.exclusions] == [ALREADY_PATCHED_IDENTICAL]


def test_the_skip_removes_the_entry_from_the_delivered_lua():
    """AC-020① [v0.1.3] — 판정 대상은 콘솔로 보낸 명령이 아니라 **생성된 Lua의 내용**이다."""
    plan = _screen(console=_console(_record(1, "1.1", "FixtureType 3", "1 Mode 1")))
    handoff = build_patch_handoff(
        (_candidate("a", 1, 1, 101),),
        address_plan=plan,
        resolutions=(_resolution("a"),),
        names={"a": "LEDBeam 101"},
        dry_run=False,
    )
    assert handoff.lua_source is None
    assert handoff.entries == ()
    assert [exclusion.code for exclusion in handoff.exclusions] == [ALREADY_PATCHED_IDENTICAL]


def test_the_first_pass_control_actually_produces_the_entry():
    """AC-020② 비공허성 — 1회차(빈 콘솔)에서는 같은 경로가 그 항목을 실제로 산출물에 넣는다."""
    plan = _screen(console=_console())
    handoff = build_patch_handoff(
        (_candidate("a", 1, 1, 101),),
        address_plan=plan,
        resolutions=(_resolution("a"),),
        names={"a": "LEDBeam 101"},
        dry_run=False,
    )
    assert [entry.candidate_id for entry in plan.entries] == ["a"]
    assert plan.exclusions == ()
    assert "AddFixtures({" in (handoff.lua_source or "")


def test_a_partial_duplicate_leaves_the_remainder_intact():
    """AC-020③ — 일부만 이미 존재하면 나머지만 생성된다."""
    targets = (_candidate("a", 1, 1, 101), _candidate("b", 1, 17, 102))
    plan = _screen(
        console=_console(_record(1, "1.1", "FixtureType 3", "1 Mode 1")),
        targets=targets,
        plan=AddressPlan(entries=(_planned("a", 1, 1), _planned("b", 1, 17))),
    )
    assert [entry.candidate_id for entry in plan.entries] == ["b"]
    assert [exclusion.candidate_id for exclusion in plan.exclusions] == ["a"]


def test_the_same_address_with_a_different_mode_is_a_conflict_not_a_skip():
    """AC-020④ — 주소는 같지만 모드가 다르면 건너뛰지 않고 충돌로 보고한다."""
    plan = _screen(console=_console(_record(1, "1.1", "FixtureType 3", "2 Mode 2")))
    assert plan.entries == ()
    assert [exclusion.code for exclusion in plan.exclusions] == [ADDRESS_CONFLICTS_WITH_EXISTING]


def test_the_same_address_with_a_different_type_is_a_conflict_not_a_skip():
    plan = _screen(console=_console(_record(1, "1.1", "FixtureType 1", "1 Mode 1")))
    assert [exclusion.code for exclusion in plan.exclusions] == [ADDRESS_CONFLICTS_WITH_EXISTING]


def test_the_conflict_control_shows_the_two_paths_actually_diverge():
    """AC-020④ 비공허성 — 네 값이 모두 같은 입력과 대조해 코드가 실제로 갈라진다."""
    identical = _screen(console=_console(_record(1, "1.1", "FixtureType 3", "1 Mode 1")))
    conflicting = _screen(console=_console(_record(1, "1.1", "FixtureType 3", "2 Mode 2")))
    assert [x.code for x in identical.exclusions] != [x.code for x in conflicting.exclusions]
    assert [x.code for x in identical.exclusions] == [ALREADY_PATCHED_IDENTICAL]


def test_an_unconfirmable_existing_identity_is_neither_skipped_nor_called_a_conflict():
    """확인 불가를 멱등으로도 충돌로도 뭉뚱그리지 않는다 — 셋을 구별해 보고한다."""
    plan = _screen(
        console=_console(
            _record(1, "1.1", "FixtureType 9", "1 Mode 1")  # 라이브러리에 index 9 없음
        )
    )
    assert plan.entries == ()
    assert [exclusion.code for exclusion in plan.exclusions] == [EXISTING_IDENTITY_UNCONFIRMED]


def test_an_unconfirmable_identity_is_never_promoted_to_idempotent():
    """확인 불가가 조용히 '이미 했음'이 되면 필요한 픽스처가 생성되지 않는다."""
    plan = _screen(console=_console(_record(1, "1.1", "FixtureType 9", "1 Mode 1")))
    assert ALREADY_PATCHED_IDENTICAL not in {exclusion.code for exclusion in plan.exclusions}


def test_a_fixture_at_another_address_does_not_interfere():
    plan = _screen(console=_console(_record(1, "2.1", "FixtureType 3", "1 Mode 1")))
    assert [entry.candidate_id for entry in plan.entries] == ["a"]


def test_upstream_exclusions_survive_the_screen():
    plan = _screen(
        console=_console(),
        plan=AddressPlan(entries=(_planned("a", 1, 1),), exclusions=()),
    )
    assert plan.exclusions == ()


def test_screening_codes_are_registered_closed_vocabulary():
    for code in (
        ALREADY_PATCHED_IDENTICAL,
        ADDRESS_CONFLICTS_WITH_EXISTING,
        EXISTING_IDENTITY_UNCONFIRMED,
    ):
        assert code in TARGET_EXCLUSION_REASON
        assert target_exclusion_label(code)


# --------------------------------------------------------------------------
# AC-AUTOPATCH-021 — 검증 읽기
# --------------------------------------------------------------------------


def test_every_approved_entry_gets_an_observed_or_not_observed_verdict():
    """AC-021① — 승인 항목마다 확인 결과가 나온다."""
    entries = (_entry("a", 1, 1), _entry("b", 1, 17))
    report = verify_patch(
        entries, console_fixtures=_console(_record(1, "1.1", "FixtureType 3", "1 Mode 1"))
    )
    outcomes = {result.candidate_id: result.outcome for result in report.results}
    assert outcomes == {"a": VERIFICATION_OBSERVED, "b": VERIFICATION_NOT_OBSERVED}
    assert report.observed_count == 1
    assert report.created_count == 1


def test_a_fixture_at_the_address_with_another_mode_is_reported_as_mismatched():
    report = verify_patch(
        (_entry("a", 1, 1),),
        console_fixtures=_console(_record(1, "1.1", "FixtureType 3", "2 Mode 2")),
    )
    (result,) = report.results
    assert result.outcome == VERIFICATION_MISMATCHED
    assert result.observed_mode == MODE_2
    assert report.created_count == 0


def test_an_unconfirmable_identity_is_reported_as_such_not_as_success():
    report = verify_patch(
        (_entry("a", 1, 1),),
        console_fixtures=_console(_record(1, "1.1", "FixtureType 9", "1 Mode 1")),
    )
    (result,) = report.results
    assert result.outcome == VERIFICATION_IDENTITY_UNCONFIRMED
    assert report.created_count == 0


def test_verification_takes_no_plugin_outcome_argument():
    """AC-021② — 플러그인 무오류 종료만으로 성공 판정하는 경로가 0건.

    파라미터 집합을 통째로 얼리지 않는다 — 그러면 정당한 확장(`read_complete`가 그랬다)마다
    깨지고 결국 기계적으로 갱신된다. 지키려는 것은 **플러그인의 종료 상태가 인자로 들어오지
    않는다**는 것 하나이므로, 그것만 이름으로 금지한다. 아래 대조군이 그 금지의 실효성을 본다.
    """
    assert not _plugin_outcome_parameters(inspect.signature(verify_patch).parameters)


# 플러그인이 "어떻게 끝났는지"를 실어 나를 수 있는 이름들. 집합 동결이 아니라 **금지**다 —
# 동결은 정당한 확장(`read_complete`가 그랬다)마다 깨지고 결국 기계적으로 갱신된다.
_PLUGIN_OUTCOME_WORDS = (
    "plugin",
    "exec",
    "reported",
    "success",
    "outcome",
    "status",
    "result",
    "verified",
    "claimed",
    "assumed",
    "_ok",
    "ok_",
)


def _plugin_outcome_parameters(parameters) -> list[str]:
    return [name for name in parameters if any(w in name.lower() for w in _PLUGIN_OUTCOME_WORDS)]


def test_the_plugin_outcome_parameter_ban_is_not_vacuous():
    """AC-021② 비공허성 — **프로덕션 사본**에 그 인자를 심으면 단정이 실제로 깨진다.

    [round11 N02] 이전 판은 테스트 로컬 헬퍼를 리터럴 집합으로 부를 뿐 `verify_patch`를
    건드리지 않는 자기충족 테스트였다. 이 SPEC이 M5·M6에서 일관되게 쓴 기준
    ("같은 하네스로 사본을 실행해 실제로 잡힌다")에 맞춘다.
    """
    planted = APPLY_SOURCE.replace(
        "    read_complete: bool = True,",
        "    read_complete: bool = True,\n    plugin_reported_ok: bool = False,",
        1,
    )
    assert planted != APPLY_SOURCE
    namespace = _load(planted)
    offenders = _plugin_outcome_parameters(inspect.signature(namespace["verify_patch"]).parameters)
    assert offenders == ["plugin_reported_ok"]


def test_a_clean_plugin_exit_cannot_make_an_absent_fixture_observed():
    """AC-021② — 성공의 근거는 재조회뿐이다. 빈 콘솔은 무조건 미관측이다."""
    report = verify_patch((_entry("a", 1, 1),), console_fixtures=_console())
    assert [result.outcome for result in report.results] == [VERIFICATION_NOT_OBSERVED]
    assert report.all_observed is False


_PLANT_CLEAN_EXIT_IS_SUCCESS = """

_verify_by_requery = verify_patch


def verify_patch(entries, *, console_fixtures, plugin_reported_ok=True):
    if plugin_reported_ok:
        results = tuple(
            VerificationResult(
                delivered=True,
                candidate_id=entry.candidate_id,
                universe=entry.universe,
                address=entry.address,
                expected_type=entry.console_type,
                expected_mode=entry.console_mode,
                outcome=VERIFICATION_OBSERVED,
                observed_type=entry.console_type,
                observed_mode=entry.console_mode,
                detail="플러그인이 오류 없이 끝났다",
            )
            for entry in entries
        )
        return PatchVerification(results=results, guidance=())
    return _verify_by_requery(entries, console_fixtures=console_fixtures)
"""


def test_clean_exit_success_control_is_caught():
    """AC-021② 비공허성.

    무오류 종료를 성공으로 읽는 분기를 심은 사본에서 위 단정이 **실제로 실패한다**.
    """
    namespace = _load(APPLY_SOURCE + _PLANT_CLEAN_EXIT_IS_SUCCESS)
    report = namespace["verify_patch"]((_entry("a", 1, 1),), console_fixtures=_console())
    assert [result.outcome for result in report.results] == [VERIFICATION_OBSERVED]
    assert report.all_observed is True


def test_the_verification_consumes_the_prechk_entry_points():
    """AC-021③ — `server/prechk/`의 기존 진입점을 쓴다(긍정 대조군)."""
    assert "from server.prechk.inventory import" in APPLY_SOURCE
    assert "from server.prechk.patch import" in APPLY_SOURCE


def _console_query_calls(source: str) -> set[str]:
    import ast

    tree = ast.parse(source)
    return {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"query_state", "query_property"}
    }


def test_the_module_issues_no_console_read_of_its_own():
    """AC-021③ — 자체 읽기 경로를 만들지 않는다. `Inventory`를 소비할 뿐이다."""
    assert _console_query_calls(APPLY_SOURCE) == set()


def test_own_read_path_control_is_caught():
    """AC-021③ 비공허성 — 자체 읽기 경로를 심은 사본에서 스캐너가 실제로 잡는다."""
    planted = (
        APPLY_SOURCE
        + "\n\ndef _planted(port):\n    return port.query_state('Patch/Stages/1/Fixtures')\n"
    )
    assert _console_query_calls(planted) == {"query_state"}


# --------------------------------------------------------------------------
# AC-AUTOPATCH-022 — 불일치 보고 · 자동 보정 0
# --------------------------------------------------------------------------


def test_a_mismatch_comes_out_structured():
    """AC-022① — 불일치가 구조화되어 나온다."""
    report = verify_patch(
        (_entry("a", 1, 1),),
        console_fixtures=_console(_record(1, "1.1", "FixtureType 3", "2 Mode 2")),
    )
    payload = report.to_dict()
    assert payload["results"][0] == {
        "delivered": True,
        "candidate_id": "a",
        "universe": 1,
        "address": 1,
        "expected_type": LED,
        "expected_mode": MODE_1,
        "observed_type": LED,
        "observed_mode": MODE_2,
        # [round15 D · round17 S17-03a] 라이브러리 확정 이름과 **콘솔 원문**을 함께 싣는다 —
        # 원문은 사유·detail 문장에서 빠졌고(2b④) 대신 여기 구조화 필드로 온다(2c①).
        # 단수 두 칸이 아니라 **점유자 리스트**다: 단수 쌍은 N>=2를 표현할 수 없어
        # 다중 점유 갈래를 영구 면제로 남긴다(S17-03a).
        "observed_occupants": [
            {
                "slot": 1,
                "universe": 1,
                "address": 1,
                "type_display": "FixtureType 3",
                "mode_display": "2 Mode 2",
                "type_name": LED,
                "mode_name": MODE_2,
                "identity_resolved": True,
            }
        ],
        "outcome": VERIFICATION_MISMATCHED,
        "label": verification_outcome_label(VERIFICATION_MISMATCHED),
        "detail": payload["results"][0]["detail"],
    }
    assert payload["mismatch_count"] == 1


def test_every_verification_outcome_is_registered_closed_vocabulary():
    for code in (
        VERIFICATION_OBSERVED,
        VERIFICATION_NOT_OBSERVED,
        VERIFICATION_MISMATCHED,
        VERIFICATION_IDENTITY_UNCONFIRMED,
    ):
        assert code in VERIFICATION_OUTCOME
        assert verification_outcome_label(code)


def _run_verification(source: str, *, port, pipeline, entries, console_fixtures):
    with _console_surface(port, pipeline):
        namespace = _load(source)
        return namespace["verify_patch"](entries, console_fixtures=console_fixtures)


_PLANT_AUTO_CORRECTION = """

_verify_without_repair = verify_patch


def verify_patch(entries, *, console_fixtures):
    from server.bridge import execution_port

    report = _verify_without_repair(entries, console_fixtures=console_fixtures)
    for result in report.results:
        if result.outcome != VERIFICATION_OBSERVED:
            execution_port.execute("Delete Fixture " + str(result.address))
    return report
"""


@pytest.mark.parametrize(
    "records",
    [(), (("1.1", "FixtureType 3", "2 Mode 2"),)],
    ids=["zero_created", "mismatched"],
)
def test_verification_never_repairs_or_retries(records):
    """AC-022② — 재시도·보정 호출이 0건."""
    port, pipeline = RecordingExecutionPort(), RecordingDeployPipeline()
    console = _console(*(_record(i + 1, *row) for i, row in enumerate(records)))
    _run_verification(
        APPLY_SOURCE,
        port=port,
        pipeline=pipeline,
        entries=(_entry("a", 1, 1),),
        console_fixtures=console,
    )
    assert port.executed == []
    assert pipeline.deployed == []


def test_auto_correction_control_is_caught():
    """AC-022② 비공허성 — 보정 호출을 심으면 같은 기록기가 잡는다."""
    port, pipeline = RecordingExecutionPort(), RecordingDeployPipeline()
    _run_verification(
        APPLY_SOURCE + _PLANT_AUTO_CORRECTION,
        port=port,
        pipeline=pipeline,
        entries=(_entry("a", 1, 1),),
        console_fixtures=_console(),
    )
    assert port.executed == ["Delete Fixture 1"]


def test_zero_created_asks_the_user_to_recheck_execution_and_procedure():
    """AC-022③ — 생성 0건이면 실행 여부와 실행 절차를 재확인하도록 안내한다."""
    report = verify_patch((_entry("a", 1, 1),), console_fixtures=_console())
    assert report.created_count == 0
    assert ZERO_CREATED_GUIDANCE in report.guidance
    assert NO_AUTO_CORRECTION in report.guidance


def test_the_zero_created_guidance_does_not_repeat_the_refuted_remedy():
    """AC-022③ [v0.1.3] — 반증된 원인 설명을 안내하지 않는다.

    한 문구가 아니라 **계열 전체**를 막는다 — 같은 조언을 다르게 적으면 통과하던
    이전 판의 약점을 닫는다(round11 N09).
    """
    assert [t for t in REFUTED_REMEDY_TOKENS if t in ZERO_CREATED_GUIDANCE] == []
    assert "실행" in ZERO_CREATED_GUIDANCE
    assert "절차" in ZERO_CREATED_GUIDANCE


def test_the_zero_created_guard_is_not_vacuous():
    planted = "Patch 화면을 먼저 열어 둔 상태에서 다시 실행하라."
    assert [t for t in REFUTED_REMEDY_TOKENS if t in planted] == ["Patch 화면"]


def test_the_guidance_control_a_successful_verification_does_not_nag():
    """비공허성 — 안내가 무조건 붙는 것이 아니다."""
    report = verify_patch(
        (_entry("a", 1, 1),),
        console_fixtures=_console(_record(1, "1.1", "FixtureType 3", "1 Mode 1")),
    )
    assert report.created_count == 1
    assert ZERO_CREATED_GUIDANCE not in report.guidance


def test_a_partial_success_is_not_reported_as_a_whole_success():
    """설계 슬롯 E — 부분 성공을 전체 성공으로 적지 않는다."""
    report = verify_patch(
        (_entry("a", 1, 1), _entry("b", 1, 17)),
        console_fixtures=_console(_record(1, "1.1", "FixtureType 3", "1 Mode 1")),
    )
    assert report.all_observed is False
    assert report.to_dict()["observed_count"] == 1
    assert report.to_dict()["not_observed_count"] == 1


def test_an_empty_approval_set_is_not_a_zero_creation_alarm():
    report = verify_patch((), console_fixtures=_console())
    assert report.results == ()
    assert report.guidance == ()
    assert report.all_observed is True


# --------------------------------------------------------------------------
# 재조회 불완전 — "관측되지 않음"과 "읽히지 않았음"을 구별한다
#
# `read_inventory`는 **절단을 기본 경로로** 다룬다(실물 콘솔은 19대에서 이미 절단됐다,
# `progress.md` §E.2 M0 1차). 절단된 재조회에서 "그 주소에 아무것도 없다"는 관측이 아니라
# **미판독**일 수 있고, 그것을 관측으로 취급하면 ① 있는 픽스처를 못 보고 중복 생성 대상으로
# 올리고 ② 검증이 거짓 미관측을 낸다. 되돌릴 수 없는 쓰기 앞에서 둘 다 위험하다.
# --------------------------------------------------------------------------


def _truncated_inventory(*records: FixtureRecord, missing: int = 1) -> Inventory:
    return Inventory(
        path=FIXTURE_ROOT,
        child_count=len(records) + missing,
        enumerated_count=len(records),
        recovered_count=0,
        observed_count=len(records),
        missing_count=missing,
        completeness=INCOMPLETE,
        recovery_boundary=len(records),
        index_domain_unknown=True,
        fixtures=records,
    )


def test_a_complete_read_reports_no_caveat():
    assert console_read_caveat(_inventory(_record(1, "1.1", "FixtureType 3", "1 Mode 1"))) is None


def test_an_incomplete_read_is_reported_as_a_caveat():
    caveat = console_read_caveat(_truncated_inventory())
    assert caveat is not None
    assert caveat["kind"] == CONSOLE_READ_INCOMPLETE
    assert caveat["missing_count"] == 1


def test_an_incomplete_read_blocks_every_creation_target():
    """미판독이 남아 있으면 **아무것도 생성 대상으로 넘기지 않는다**."""
    plan = screen_console_read(
        (_candidate("a", 1, 1, 101),),
        address_plan=AddressPlan(entries=(_planned("a", 1, 1),)),
        inventory=_truncated_inventory(),
    )
    assert plan.entries == ()
    assert [exclusion.code for exclusion in plan.exclusions] == [CONSOLE_READ_INCOMPLETE]


def test_the_block_control_a_complete_read_passes_everything_through():
    """비공허성 — 완전한 재조회에서는 같은 경로가 항목을 그대로 통과시킨다."""
    plan = screen_console_read(
        (_candidate("a", 1, 1, 101),),
        address_plan=AddressPlan(entries=(_planned("a", 1, 1),)),
        inventory=_inventory(),
    )
    assert [entry.candidate_id for entry in plan.entries] == ["a"]
    assert plan.exclusions == ()


def test_a_root_truncation_that_recovered_everything_is_a_caveat_not_a_block():
    """열거는 짧았지만 선언된 자식을 전부 관측했다면 **수량 비교는 정확하다**.

    `read_inventory`의 계약이 그렇다 — `childCount`가 진짜 총계이고 절단은 목록만 줄인다.
    그래서 `missing_count == 0`이면 막지 않고, 인덱스 도메인 미상만 주의로 남긴다.
    """
    recovered = Inventory(
        path=FIXTURE_ROOT,
        child_count=1,
        enumerated_count=0,
        recovered_count=1,
        observed_count=1,
        missing_count=0,
        completeness=INCOMPLETE,
        recovery_boundary=1,
        index_domain_unknown=True,
        fixtures=(_record(1, "1.1", "FixtureType 3", "1 Mode 1"),),
    )
    plan = screen_console_read(
        (_candidate("a", 1, 17, 101),),
        address_plan=AddressPlan(entries=(_planned("a", 1, 17),)),
        inventory=recovered,
    )
    assert [entry.candidate_id for entry in plan.entries] == ["a"]
    caveat = console_read_caveat(recovered)
    assert caveat is not None
    assert caveat["kind"] == CONSOLE_READ_INDEX_DOMAIN_UNKNOWN


def test_verification_marks_unobserved_as_unconfirmable_when_the_read_was_short():
    """AC-021② 정신 — 확인할 수 없는 것을 '없다'로 단정하지 않는다."""
    report = verify_patch(
        (_entry("a", 1, 1),),
        console_fixtures=_console(),
        read_complete=False,
    )
    (result,) = report.results
    assert result.outcome == VERIFICATION_IDENTITY_UNCONFIRMED
    assert "재조회가 불완전" in result.detail


def test_the_short_read_control_a_complete_read_still_says_not_observed():
    """비공허성 — 완전한 재조회에서는 같은 입력이 그대로 '미관측'이다."""
    report = verify_patch((_entry("a", 1, 1),), console_fixtures=_console())
    assert [result.outcome for result in report.results] == [VERIFICATION_NOT_OBSERVED]


def test_a_short_read_does_not_downgrade_an_actual_observation():
    report = verify_patch(
        (_entry("a", 1, 1),),
        console_fixtures=_console(_record(1, "1.1", "FixtureType 3", "1 Mode 1")),
        read_complete=False,
    )
    assert [result.outcome for result in report.results] == [VERIFICATION_OBSERVED]


# --------------------------------------------------------------------------
# round11 회귀 — 독립 감사가 잡은 결함을 다시 나지 않게 못박는다
# --------------------------------------------------------------------------


def test_a_truncated_type_library_refuses_to_resolve_a_display_string():
    """[N01] 열거가 절단되면 '그 이름의 타입이 없다'를 단정할 수 없다 — 모호성 가드가 공허해진다.

    [round25 R24-2] 총계를 **선언한다**. 비워 두면 이 시험은 절단 플래그와 총계 미판독
    **둘 다**에 걸려 어느 쪽이 막았는지 말하지 못한다 — 플래그 갈래를 지우는 뮤턴트가
    미판독 갈래에 걸려 살아남는다. 재는 축 하나만 위반시킨다.
    """
    truncated = FixtureTypeLibrary(
        types=(LibraryType(index=2, name="Robin MMX"),),
        available=True,
        truncated=True,
        child_count=1,
        enumerated_count=1,
        returned_row_count=1,
    )
    assert truncated.enumeration_short is False  # 막는 것은 **플래그**다.
    (observed,) = _console(_record(1, "1.1", "FixtureType 2", "1 Mode 1"), library=truncated)
    assert observed.type_name is None
    assert observed.identity_resolved is False


def test_the_truncation_refusal_control_a_complete_library_still_resolves():
    """비공허성 — 같은 입력이 완전한 열거에서는 해석된다.

    [round25 R24-2] *"완전한 열거"*라 이름 붙은 대조군이 **선언 총계를 읽지 않은**
    스냅샷이었다. 이름이 코드보다 앞서 나간 자리다 — 이제 이름이 말하는 것을 값이 준다.
    """
    complete = FixtureTypeLibrary(
        types=(LibraryType(index=2, name="Robin MMX", modes=(LibraryMode(index=1, name=MODE_1),)),),
        available=True,
        truncated=False,
        child_count=1,
        enumerated_count=1,
        returned_row_count=1,
    )
    (observed,) = _console(_record(1, "1.1", "FixtureType 2", "1 Mode 1"), library=complete)
    assert observed.type_name == "Robin MMX"


@pytest.mark.parametrize("order", [(3, 9), (9, 3)], ids=["index3_first", "index9_first"])
def test_ambiguity_is_refused_regardless_of_enumeration_order(order):
    """[N06] 같은 이름의 타입이 둘이면 **열거 순서와 무관하게** 거부한다."""
    by_index = {
        i: LibraryType(index=i, name="FixtureType 3", modes=(LibraryMode(index=1, name=MODE_1),))
        for i in (3, 9)
    }
    # [round25 R24-2] 재는 축은 **모호성**이다 — 총계를 비우면 완전성 가드가 먼저 막아
    # 같은 `None`이 나오고, 이 시험은 순서 불변을 재지 못한 채 초록으로 남는다.
    library = FixtureTypeLibrary(
        types=tuple(by_index[i] for i in order),
        child_count=2,
        enumerated_count=2,
        returned_row_count=2,
    )
    (observed,) = _console(_record(1, "1.1", "FixtureType 3", "1 Mode 1"), library=library)
    assert observed.type_name is None


def test_an_unresolved_own_type_is_not_reported_as_an_address_conflict():
    """[N08] 우리 타입이 미확정인 것과 남의 픽스처가 점유한 것은 다른 사유다."""
    plan = _screen(
        console=_console(_record(1, "1.1", "FixtureType 3", "1 Mode 1")),
        resolutions=(
            TypeResolution(
                request=TypeRequest(candidate_id="a", instrument_type=LED),
                status=TYPE_NEEDS_CONFIRMATION,
                reason="",
                console_type=None,
                console_mode=None,
            ),
        ),
    )
    assert [x.code for x in plan.exclusions] == [TYPE_CONFIRMATION_PENDING]


def test_two_fixtures_at_one_address_are_not_swallowed_as_already_patched():
    """[N10] 첫 일치가 우리와 같아도 두 번째 점유자를 못 본 채 넘기지 않는다."""
    plan = _screen(
        console=_console(
            _record(1, "1.1", "FixtureType 3", "1 Mode 1"),
            _record(2, "1.1", "FixtureType 1", "1 Mode 1"),
        )
    )
    assert [x.code for x in plan.exclusions] == [EXISTING_IDENTITY_UNCONFIRMED]


def test_the_duplicate_control_a_single_occupant_still_reads_as_idempotent():
    plan = _screen(console=_console(_record(1, "1.1", "FixtureType 3", "1 Mode 1")))
    assert [x.code for x in plan.exclusions] == [ALREADY_PATCHED_IDENTICAL]


def test_a_fixture_inside_the_planned_span_is_excluded_as_occupied():
    """[M7 N01] 계획 구간 **안쪽에서** 시작하는 기존 픽스처는 겹침이다."""
    plan = screen_console_occupancy(
        (_candidate("a", 1, 1, 101),),
        address_plan=AddressPlan(entries=(_planned("a", 1, 1),)),
        console_fixtures=_console(_record(1, "1.5", "FixtureType 3", "1 Mode 1")),
    )
    assert plan.entries == ()
    assert [x.code for x in plan.exclusions] == [ADDRESS_ALREADY_OCCUPIED]


def test_the_occupancy_screen_leaves_the_targets_own_address_to_the_idempotency_screen():
    """자기 자리는 여기서 잡지 않는다 — 멱등/충돌/확인 불가 3분기가 그것을 갈라야 한다."""
    plan = screen_console_occupancy(
        (_candidate("a", 1, 1, 101),),
        address_plan=AddressPlan(entries=(_planned("a", 1, 1),)),
        console_fixtures=_console(_record(1, "1.1", "FixtureType 3", "1 Mode 1")),
    )
    assert [entry.candidate_id for entry in plan.entries] == ["a"]


def test_the_unreadable_existing_footprint_is_reported_rather_than_guessed():
    """[N04] 꼬리 방향 겹침을 못 잡는다는 사실을 구조화해 보고한다."""
    check = existing_footprint_skipped_check()
    assert check["kind"] == EXISTING_FOOTPRINT_UNREADABLE
    assert "검출되지 않는다" in check["reason"]


# --------------------------------------------------------------------------
# round12 회귀 — round11 수정이 새로 만든 결함
# --------------------------------------------------------------------------


def test_an_unpatched_fixture_is_not_counted_as_an_unreadable_address():
    """[R08] `Patch = "0.0"`은 판독 실패가 아니라 **패치되지 않았다는 관측**이다 — 막지 않는다.

    이전 판은 주소 파서의 성공 여부로 미판독을 정의해, 미패치 예비 픽스처가 한 대만 있어도
    모든 대상을 막았다 — 툴의 유일한 기능이 정지했다.

    **다만 그 갈래는 미실측 가정 위에 있으므로 계수를 payload에 싣는다**(round14 T01) —
    막지는 않되 조작자가 세션 전에 눈으로 대조할 수 있어야 한다.
    """
    unpatched = FixtureRecord(
        slot=1, name="spare", patch_raw="0.0", fixture_type="FixtureType 3", mode="1 Mode 1"
    )
    caveat = console_read_caveat(_inventory(unpatched))
    assert caveat is not None
    assert caveat["kind"] == CONSOLE_READ_UNPATCHED_PRESENT
    assert caveat["unpatched_count"] == 1
    assert caveat["unread_count"] == 0  # 막는 축은 0이다


def test_the_unpatched_disclosure_does_not_block_creation():
    """비공허성 — 고지일 뿐 차단이 아니다."""
    unpatched = FixtureRecord(
        slot=1, name="spare", patch_raw="0.0", fixture_type="FixtureType 3", mode="1 Mode 1"
    )
    plan = screen_console_read(
        (_candidate("a", 1, 1, 101),),
        address_plan=AddressPlan(entries=(_planned("a", 1, 1),)),
        inventory=_inventory(unpatched),
    )
    assert [entry.candidate_id for entry in plan.entries] == ["a"]


def test_a_genuinely_unread_patch_property_still_counts_as_unread():
    """비공허성 — 진짜 읽기 실패는 그대로 미판독이다."""
    failure = ReadFailure(
        slot=1,
        name="x",
        property="Patch",
        raw_value=None,
        kind="read_failed",
        detail="not readable",
    )
    unread = FixtureRecord(
        slot=1,
        name="x",
        patch_raw=None,
        fixture_type="FixtureType 3",
        mode="1 Mode 1",
        read_failures=(failure,),
    )
    caveat = console_read_caveat(_inventory(unread))
    assert caveat is not None
    assert caveat["unreadable_address_count"] == 1


def test_two_fixtures_at_the_address_verify_as_unconfirmed_not_unobserved():
    """[R02] '둘이라 모른다'를 '아무것도 없다'로 적으면 사용자가 다시 실행해 중복을 만든다."""
    report = verify_patch(
        (_entry("a", 1, 1),),
        console_fixtures=_console(
            _record(1, "1.1", "FixtureType 3", "1 Mode 1"),
            _record(2, "1.1", "FixtureType 1", "1 Mode 1"),
        ),
    )
    (result,) = report.results
    assert result.outcome == VERIFICATION_IDENTITY_UNCONFIRMED
    assert "2대 관측된다" in result.detail


def test_nothing_delivered_means_no_run_the_plugin_guidance():
    """[R04] 전달한 플러그인이 없으면 '실행했는지 확인하라'는 거짓말이다."""
    report = verify_patch((_entry("a", 1, 1),), console_fixtures=_console(), delivered_ids=[])
    assert report.delivered_count == 0
    assert ZERO_CREATED_GUIDANCE not in report.guidance
    assert NO_AUTO_CORRECTION in report.guidance


def test_the_guidance_control_a_delivered_item_with_zero_observations_still_asks():
    """비공허성 — 전달분이 있는데 관측이 0건이면 그때는 물어야 한다."""
    report = verify_patch((_entry("a", 1, 1),), console_fixtures=_console(), delivered_ids=["a"])
    assert ZERO_CREATED_GUIDANCE in report.guidance


def test_created_count_excludes_items_that_were_never_delivered():
    """[R06] 전달하지 않은 주소의 기존 픽스처는 이 호출이 만든 것이 아니다."""
    report = verify_patch(
        (_entry("a", 1, 1),),
        console_fixtures=_console(_record(1, "1.1", "FixtureType 3", "1 Mode 1")),
        delivered_ids=[],
    )
    assert report.observed_count == 1
    assert report.created_count == 0


def test_a_truncated_library_still_accepts_an_exact_name_match():
    """[R07] 절단이 무효화하는 것은 부정 결론뿐 — 이름 일치는 절단과 무관한 긍정 증거다."""
    truncated = FixtureTypeLibrary(
        types=(LibraryType(index=7, name=LED, modes=(LibraryMode(index=1, name=MODE_1),)),),
        available=True,
        truncated=True,
    )
    (observed,) = _console(_record(1, "1.1", LED, MODE_1), library=truncated)
    assert observed.type_name == LED


def test_a_truncated_library_still_refuses_the_index_only_interpretation():
    """비공허성 — 이름이 안 보이는 index 형태 단독 해석은 절단 아래에서 거부된다."""
    truncated = FixtureTypeLibrary(
        types=(LibraryType(index=2, name="Robin MMX", modes=(LibraryMode(index=1, name=MODE_1),)),),
        available=True,
        truncated=True,
    )
    (observed,) = _console(_record(1, "1.1", "FixtureType 2", "1 Mode 1"), library=truncated)
    assert observed.type_name is None


# --------------------------------------------------------------------------
# round13 회귀 — Patch 값 도메인 **전수 분류**
#
# 이 자리에서 두 라운드 연속으로 결함이 났다. 두 번 다 원인은 같다: 입력 도메인을
# 열거하지 않고 한 갈래만 보는 술어를 썼다. 그래서 이번엔 도메인을 **표로** 못박는다 —
# 새 값 형태가 생기면 이 표에 행을 더해야 하고, 더하지 않으면 마지막 테스트가 잡는다.
# --------------------------------------------------------------------------

PATCH_VALUE_DOMAIN = (
    ("1.1", PATCH_ADDRESSED, "정상 주소"),
    ("3.209", PATCH_ADDRESSED, "정상 주소(다른 유니버스)"),
    ("0.0", PATCH_UNPATCHED, "미패치 예비 픽스처 — 판독 실패가 아니라 관측이다"),
    ("1.0", PATCH_UNPATCHED, "주소 축만 0"),
    ("0.1", PATCH_UNPATCHED, "유니버스 축만 0"),
    ("abc", PATCH_UNREAD, "형태 불일치 — shape 게이트는 통과하지만 주소가 아니다"),
    ("1-5", PATCH_UNREAD, "구분자가 다르다"),
    ("1.5.7", PATCH_UNREAD, "토큰이 셋"),
    ("-1.5", PATCH_UNREAD, "음수"),
    ("Universe 1 Addr 5", PATCH_UNREAD, "산문"),
    ("None", PATCH_UNREAD, "콘솔이 부재를 문자열로 준 형태"),
    ("", PATCH_UNREAD, "빈 문자열"),
    (None, PATCH_UNREAD, "값 없음"),
    ("table: 0x105b0f048", PATCH_UNREAD, "Lua 포인터"),
)


@pytest.mark.parametrize(
    "raw,expected,why", PATCH_VALUE_DOMAIN, ids=[row[2] for row in PATCH_VALUE_DOMAIN]
)
def test_every_patch_value_shape_lands_in_exactly_one_class(raw, expected, why):
    assert classify_patch_value(_record(1, raw, "FixtureType 3", "1 Mode 1")) == expected, why


def test_a_read_failure_is_unread_regardless_of_the_value():
    failure = ReadFailure(
        slot=1,
        name="x",
        property="Patch",
        raw_value="1.1",
        kind="read_failed",
        detail="not readable",
    )
    fixture = FixtureRecord(
        slot=1,
        name="x",
        patch_raw="1.1",
        fixture_type="FixtureType 3",
        mode="1 Mode 1",
        read_failures=(failure,),
    )
    assert classify_patch_value(fixture) == PATCH_UNREAD


def test_the_classification_is_total_no_value_falls_through():
    """세 갈래 밖으로 나가는 값이 없다 — 도메인 표 밖의 형태도 반드시 하나로 떨어진다."""
    exotic = ["1.1 ", " 1.1", "1,1", "١.١", "1.1\n", "٩", "1.", ".1", "1..1", "999999.999999"]
    for raw in exotic:
        assert classify_patch_value(_record(1, raw, "FixtureType 3", "1 Mode 1")) in {
            PATCH_UNREAD,
            PATCH_UNPATCHED,
            PATCH_ADDRESSED,
        }


def test_a_shape_ok_but_unparsable_address_blocks_creation():
    """[round13 S01] 읽히긴 했으나 주소가 아닌 값 — 그 픽스처는 어디에서도 보이지 않는다.

    보이지 않는 채로 재조회를 "완전"으로 등급하면, 이미 픽스처가 있는 주소에 생성이
    진행되고 M8에서 사람이 그것을 실행한다. 실행 취소는 없다.
    """
    caveat = console_read_caveat(_inventory(_record(1, "1-5", "FixtureType 3", "1 Mode 1")))
    assert caveat is not None
    assert caveat["kind"] == CONSOLE_READ_INCOMPLETE
    assert caveat["unreadable_address_count"] == 1


def test_the_unparsable_control_a_valid_address_does_not_block():
    assert console_read_caveat(_inventory(_record(1, "1.5", "FixtureType 3", "1 Mode 1"))) is None


def test_the_neutral_field_map_covers_every_entry_field():
    """[round14 T06] "축을 빼놓는 것이 구조적으로 불가능"을 **구조로** 확인한다.

    `_NEUTRAL_FIELDS`는 손으로 유지하는 리터럴이다. `LuaPatchEntry`에 필드가 하나 더 생기면
    그 축이 중립화에서 빠지고 round12 R09가 정확히 재발한다 — 그 재발을 이 단정이 막는다.
    """
    assert set(_NEUTRAL_FIELDS) == set(LuaPatchEntry.__dataclass_fields__)


# [round15 A] 여기 있던 `test_every_banned_plugin_outcome_word_is_load_bearing` ·
# `test_every_refuted_remedy_token_is_load_bearing` 둘을 **삭제**했다. 둘 다 항진명제였다 —
# 전자는 테스트 로컬 목록으로 테스트 로컬 함수를 부를 뿐 `verify_patch`를 건드리지 않았고,
# 후자는 목록에서 만든 문자열을 **같은 목록으로 다시 걸러** 비어있지 않음을 단정했다.
# 실측: 목록에서 토큰을 지우면 케이스가 조용히 사라질 뿐(336 → 335 passed, 실패 0)이라
# "지우면 잡히지 않는 단어는 장식이다"라는 주장이 성립하지 않았다.
# 대체물은 아래 `--- round15 금지 어휘 대조군 ---` 절에 있다 — 목록과 **독립인** 침해 표본
# 표를 두고, 그 표본을 **프로덕션 사본에 심어 프로덕션 함수의 반환값**을 검사한다.
# 그래서 목록에서 토큰을 하나 지우면 그 표본이 빠져나가 테스트가 **실패한다**.


# --------------------------------------------------------------------------
# --- round15 금지 어휘 대조군 ---
#
# 금지 목록은 **그 자체로는 게이트가 아니다.** 목록으로 목록을 검사하면 항상 참이고,
# 목록에서 항목을 지우면 그 항목의 케이스도 함께 사라져 아무것도 실패하지 않는다.
# 그래서 여기서는 목록과 **독립인 침해 표본 표**를 둔다:
#
#   1. 표본은 손으로 열거한다 — 금지 목록에서 파생하지 않는다.
#   2. 표본 하나는 금지 항목 **정확히 하나**에만 걸리도록 고른다(형제 축 표 열거).
#   3. 표본을 **프로덕션 사본에 심어** 프로덕션 함수를 부르고 **그 반환값**을 검사한다.
#   4. 표와 목록이 전단사임을 따로 단정한다.
#
# 결과: 목록에서 항목을 하나 지우면 (2)의 표본이 게이트를 빠져나가 해당 케이스가 실패하고,
# 동시에 (4)가 실패한다. 항목을 이름만 바꿔도 (4)가 잡는다.
# --------------------------------------------------------------------------


# 침해 표본 — (금지 단어, 그 단어에만 걸리는 파라미터 이름). `_PLUGIN_OUTCOME_WORDS`에서
# 파생하지 않는다. 각 이름은 다른 11개 단어 어디에도 걸리지 않도록 골랐다(아래 전단사·유일성
# 단정이 그것을 강제한다).
_PLUGIN_OUTCOME_PROBES = (
    ("plugin", "plugin_hint"),
    ("exec", "exec_finished"),
    ("reported", "reported_clean"),
    ("success", "success_flag"),
    ("outcome", "outcome_note"),
    ("status", "status_code"),
    ("result", "result_seen"),
    ("verified", "verified_by_caller"),
    ("claimed", "claimed_done"),
    ("assumed", "assumed_present"),
    ("_ok", "console_ok"),
    ("ok_", "ok_from_console"),
)


def test_the_plugin_outcome_probe_table_is_a_bijection_onto_the_ban_list():
    """표와 금지 목록이 1:1이다 — 목록에 단어를 더하면 표본 없이는 통과하지 못한다.

    [round15 A1] `_PLUGIN_OUTCOME_WORDS`에서 어느 단어든 지우거나 추가하면 이 단정이 깨진다.
    """
    assert tuple(word for word, _ in _PLUGIN_OUTCOME_PROBES) == _PLUGIN_OUTCOME_WORDS


@pytest.mark.parametrize(
    "word,probe", _PLUGIN_OUTCOME_PROBES, ids=[probe for _, probe in _PLUGIN_OUTCOME_PROBES]
)
def test_each_plugin_outcome_probe_is_caught_by_exactly_one_banned_word(word, probe):
    """표본이 **겨냥한 단어에만** 걸린다 — 그래야 그 단어를 지웠을 때 아래 대조군이 실패한다.

    [round15 A1] `_PLUGIN_OUTCOME_WORDS`에서 `word`를 지우면 짝이 되는 아래 대조군이
    빈 목록을 받아 실패한다. 이 단정은 그 인과가 **다른 단어에 가려지지 않음**을 고정한다.
    """
    assert [w for w in _PLUGIN_OUTCOME_WORDS if w in probe.lower()] == [word]


@pytest.mark.parametrize("probe", [probe for _, probe in _PLUGIN_OUTCOME_PROBES])
def test_the_plugin_outcome_ban_catches_each_probe_planted_in_the_production_signature(probe):
    """AC-021② 비공허성(전수) — 표본마다 **프로덕션 사본**에 인자를 심어 금지가 잡는지 본다.

    `test_the_plugin_outcome_parameter_ban_is_not_vacuous`(약 463행)와 같은 방식이다:
    `APPLY_SOURCE`를 고쳐 진짜 모듈로 적재하고, 적재된 `verify_patch`의 **실제 시그니처**를
    금지 목록으로 훑는다. 테스트가 조립한 기대값이 아니라 프로덕션 산출물을 본다.

    [round15 A1] `_PLUGIN_OUTCOME_WORDS`에서 이 표본이 겨냥한 단어를 지우면
    `offenders`가 비어 이 단정이 실패한다 — 삭제된 구판은 케이스가 사라질 뿐이었다.
    """
    planted = APPLY_SOURCE.replace(
        "    read_complete: bool = True,",
        f"    read_complete: bool = True,\n    {probe}: bool = False,",
        1,
    )
    assert planted != APPLY_SOURCE
    namespace = _load(planted)
    offenders = _plugin_outcome_parameters(inspect.signature(namespace["verify_patch"]).parameters)
    assert offenders == [probe]


# 반증된 처방 표본 — (금지 토큰, 그 토큰에만 걸리는 안내 문장). `REFUTED_REMEDY_TOKENS`에서
# 파생하지 않는다.
_REFUTED_REMEDY_PROBES = (
    ("편집기", "패치 편집기를 먼저 열어라."),
    ("편집 세션", "편집 세션을 유지한 채 다시 실행하라."),
    ("Patch 화면", "Patch 화면으로 이동한 뒤 다시 실행하라."),
    ("Fixtures 뷰", "Fixtures 뷰에서 결과를 확인하라."),
    ("목적지", "목적지를 먼저 지정하고 다시 실행하라."),
)


def test_the_refuted_remedy_probe_table_is_a_bijection_onto_the_token_list():
    """[round15 A2] `REFUTED_REMEDY_TOKENS`에서 토큰을 지우거나 더하면 이 단정이 깨진다."""
    assert tuple(token for token, _ in _REFUTED_REMEDY_PROBES) == REFUTED_REMEDY_TOKENS


@pytest.mark.parametrize(
    "token,phrase", _REFUTED_REMEDY_PROBES, ids=[token for token, _ in _REFUTED_REMEDY_PROBES]
)
def test_each_refuted_remedy_probe_is_caught_by_exactly_one_token(token, phrase):
    """[round15 A2] 표본이 겨냥한 토큰에만 걸린다 — 인과가 다른 토큰에 가려지지 않는다."""
    assert [t for t in REFUTED_REMEDY_TOKENS if t in phrase] == [token]


@pytest.mark.parametrize(
    "token,phrase", _REFUTED_REMEDY_PROBES, ids=[token for token, _ in _REFUTED_REMEDY_PROBES]
)
def test_the_refuted_remedy_guard_catches_each_probe_planted_in_the_production_guidance(
    token, phrase
):
    """AC-022③ 비공허성(전수) — 표본을 **프로덕션 안내 문구에 심어** 게이트가 잡는지 본다.

    `ZERO_CREATED_GUIDANCE`는 `verify_patch`가 호출 시점에 읽는 모듈 전역이다. 사본에서
    그 전역에 표본 문장을 덧붙이고 **프로덕션 `verify_patch`의 반환값**(`report.guidance`)을
    훑는다 — 테스트가 만든 문자열을 테스트가 다시 거르는 구판과 다른 점이 이것이다.

    [round15 A2] `REFUTED_REMEDY_TOKENS`에서 `token`을 지우면 `caught`가 비어 실패한다.
    """
    planted = APPLY_SOURCE + f'\n\nZERO_CREATED_GUIDANCE = ZERO_CREATED_GUIDANCE + " {phrase}"\n'
    namespace = _load(planted)
    report = namespace["verify_patch"]((_entry("a", 1, 1),), console_fixtures=_console())
    assert report.created_count == 0
    caught = [t for t in REFUTED_REMEDY_TOKENS if t in "\n".join(report.guidance)]
    assert caught == [token]


def test_the_refuted_remedy_production_guidance_control_is_clean_without_a_plant():
    """대조군의 대조군 — 심지 않은 사본에서는 같은 훑기가 **아무것도** 잡지 않는다.

    이것이 없으면 위 단정이 "원래부터 걸려 있던 것"을 보고 통과할 수 있다.
    """
    namespace = _load(APPLY_SOURCE)
    report = namespace["verify_patch"]((_entry("a", 1, 1),), console_fixtures=_console())
    assert report.created_count == 0
    assert [t for t in REFUTED_REMEDY_TOKENS if t in "\n".join(report.guidance)] == []


# --------------------------------------------------------------------------
# --- round15 조작자가 읽는 문장 게이트 (CaveatGates) ---
#
# round14가 진단한 발생 기제를 그대로 옮긴다: **숫자 축은 검증했는데 그 숫자를 소비하는
# 문장은 검증하지 않았다.** round14가 신설한 `console_read_unpatched_fixtures_present`
# 갈래에서 그 기제가 그대로 재생산됐다 — 적대 감사는 라벨을 "예비 픽스처가 있다 — 문제 없다"로,
# caveat 사유를 "확인할 것은 없다"로 바꿔도 스위트 전건이 통과하는 것을 실측했다.
#
# 이 caveat은 **막지 않는** 갈래다. 세션은 되돌릴 수 없는 픽스처 생성으로 진행하고,
# 조작자가 사전에 눈으로 대조할 근거는 **그 문장뿐**이다. 그래서 문장을 잠근다.
# --------------------------------------------------------------------------


def _round15_inventory(
    *,
    missing: int = 0,
    unreadable: int = 0,
    unpatched: int = 0,
    addressed: int = 1,
    index_domain_unknown: bool = False,
) -> Inventory:
    """세 입력 축(미판독 열거 · 미판독 주소 · 미패치 · 인덱스 도메인 미상)을 독립으로 세운다."""
    records: list[FixtureRecord] = [
        _record(slot, f"1.{slot}", "FixtureType 3", "1 Mode 1") for slot in range(1, addressed + 1)
    ]
    for offset in range(unreadable):
        slot = addressed + offset + 1
        records.append(
            FixtureRecord(
                slot=slot,
                name=f"unreadable {slot}",
                patch_raw=None,
                fixture_type="FixtureType 3",
                mode="1 Mode 1",
                read_failures=(
                    ReadFailure(
                        slot=slot,
                        name=f"unreadable {slot}",
                        property="Patch",
                        raw_value=None,
                        kind="read_failed",
                        detail="not readable",
                    ),
                ),
            )
        )
    for offset in range(unpatched):
        slot = addressed + unreadable + offset + 1
        records.append(
            FixtureRecord(
                slot=slot,
                name=f"spare {slot}",
                patch_raw="0.0",
                fixture_type="FixtureType 3",
                mode="1 Mode 1",
            )
        )
    return Inventory(
        path=FIXTURE_ROOT,
        child_count=len(records) + missing,
        enumerated_count=len(records),
        recovered_count=0,
        observed_count=len(records),
        missing_count=missing,
        completeness=INCOMPLETE if missing or index_domain_unknown else COMPLETE,
        recovery_boundary=len(records) if index_domain_unknown else None,
        index_domain_unknown=index_domain_unknown,
        fixtures=tuple(records),
    )


#: 조작자를 **안심시키는** 어휘. caveat 라벨·사유에 들어가면 그 자체가 결함이다 —
#: 이 갈래는 막지 않으므로 안심 문구는 곧 "대조하지 않고 진행하라"는 지시가 된다.
_ROUND15_REASSURING_TOKENS = (
    "문제 없다",
    "문제없다",
    "이상 없다",
    "이상없다",
    "정상이다",
    "안전하다",
    "안심",
    "확인할 것은 없다",
    "확인할 필요 없다",
    "그대로 진행",
    "무시해도",
)

#: 경고성 어휘. caveat 라벨·사유는 적어도 하나를 담아야 한다.
_ROUND15_CAUTION_TOKENS = (
    "미판독",
    "미실측",
    "미상",
    "절단",
    "단정할 수 없다",
    "단정 불가",
    "대조하라",
    "확인 불가",
    "주의",
)


def _round15_reassurances(text: str) -> list[str]:
    return [token for token in _ROUND15_REASSURING_TOKENS if token in text]


def _round15_cautions(text: str) -> list[str]:
    return [token for token in _ROUND15_CAUTION_TOKENS if token in text]


# [round16 A1] 여기에 있던 `test_every_reassuring_token_is_load_bearing`(11행)과
# `test_every_caution_token_is_load_bearing`(9행) — **항진명제 20건**을 삭제했다.
# 두 테스트는 `_ROUND15_REASSURING_TOKENS`/`_ROUND15_CAUTION_TOKENS`로 만든 문자열을
# **같은 목록으로 다시 걸렀다**. 프로덕션 호출 0회 — round14 T09가 없앴다고 선언한 구조가
# 그 절 20줄 아래에서 그대로 되살아난 것이다. 게다가 어휘 목록 방식 자체가 반증됐다(M44):
# `_INDEX_DOMAIN_CLAUSE`에 `"주의할 것 없음, "`을 끼우면 안심 목록 11개에 걸리지 않고,
# 하필 경고 토큰 `"주의"`를 부분문자열로 포함해 경고 게이트까지 만족시킨다.
#
# 대체물은 파일 끝 `# --- round16 표 전단사·문장 전문 고정 (TableBijection) ---` 절에 있다:
#   ① caveat 라벨·사유의 **문장 전문 동등** 고정(어휘 휴리스틱이 아니라 `==`),
#   ② 두 어휘 목록의 전단사 게이트(항목을 지우면 실패),
#   ③ 부분문자열 충돌 배제 단정,
#   ④ 토큰별 대조군을 **프로덕션 `console_read_caveat`를 실제로 통과시켜** 세운다.


# `console_read_caveat`의 갈래 전수 표. 입력 축은 셋(미판독 · 미패치 · 인덱스 도메인 미상)이고
# 여덟 조합을 전부 행으로 놓는다. 열은 (입력, 기대 kind, 기대 `unpatched_count`,
# 반드시 들어가야 할 문구, 반드시 들어가서는 안 되는 문구)이다.
_ROUND15_CAVEAT_TABLE = (
    pytest.param({}, None, 0, (), (), id="none__clean_read_has_no_caveat"),
    pytest.param(
        {"index_domain_unknown": True},
        CONSOLE_READ_INDEX_DOMAIN_UNKNOWN,
        0,
        ("열거가 절단됐으나", "인덱스 도메인만 미상이다"),
        ("최소 인덱스 미만", "열거하지 못했다", "주소를 판독하지 못했다"),
        id="idu__truncated_but_fully_observed",
    ),
    pytest.param(
        {"unpatched": 1},
        CONSOLE_READ_UNPATCHED_PRESENT,
        1,
        ("콘솔 픽스처 1대가 최소 인덱스 미만", "세션 전에 눈으로 대조하라"),
        ("인덱스 도메인만 미상이다", "열거하지 못했다", "주소를 판독하지 못했다"),
        id="unpatched__spare_fixture_only",
    ),
    pytest.param(
        {"unpatched": 19, "index_domain_unknown": True},
        CONSOLE_READ_UNPATCHED_PRESENT,
        19,
        (
            "콘솔 픽스처 19대가 최소 인덱스 미만",
            "세션 전에 눈으로 대조하라",
            "또한",
            "인덱스 도메인만 미상이다",
        ),
        (),
        id="unpatched_and_idu__both_sentences_must_ship",
    ),
    pytest.param(
        {"unreadable": 1},
        CONSOLE_READ_INCOMPLETE,
        0,
        ("1대는 주소를 판독하지 못했다", "미판독이다"),
        ("열거하지 못했다", "최소 인덱스 미만"),
        id="unread__unreadable_address_only",
    ),
    pytest.param(
        {"missing": 1, "index_domain_unknown": True},
        CONSOLE_READ_INCOMPLETE,
        0,
        ("선언된 2대 중 1대를 열거하지 못했다", "미판독이다"),
        ("주소를 판독하지 못했다", "최소 인덱스 미만"),
        id="unread_and_idu__enumeration_short_only",
    ),
    pytest.param(
        {"missing": 1, "unreadable": 1},
        CONSOLE_READ_INCOMPLETE,
        0,
        ("선언된 3대 중 1대를 열거하지 못했다", "1대는 주소를 판독하지 못했다"),
        ("최소 인덱스 미만",),
        id="unread__both_unread_axes",
    ),
    pytest.param(
        {"unreadable": 1, "unpatched": 1},
        CONSOLE_READ_INCOMPLETE,
        1,
        ("1대는 주소를 판독하지 못했다", "콘솔 픽스처 1대가 최소 인덱스 미만"),
        ("열거하지 못했다",),
        id="unread_and_unpatched__count_still_ships",
    ),
    pytest.param(
        {"missing": 1, "unpatched": 2, "index_domain_unknown": True},
        CONSOLE_READ_INCOMPLETE,
        2,
        ("선언된 4대 중 1대를 열거하지 못했다", "콘솔 픽스처 2대가 최소 인덱스 미만"),
        ("주소를 판독하지 못했다",),
        id="all_three_axes__blocking_branch_carries_the_count",
    ),
    pytest.param(
        # [round16 A1] 이 행은 round16에서 **추가**됐다. INCOMPLETE 갈래의 세 하위
        # 결정(`missing_count` · `unreadable_addresses` · `unpatched`)이 **동시에 참**인
        # 경로가 표에 없었다 — 아래 전단사 게이트가 그 구멍을 찾아냈다.
        {"missing": 1, "unreadable": 1, "unpatched": 1},
        CONSOLE_READ_INCOMPLETE,
        1,
        (
            "선언된 4대 중 1대를 열거하지 못했다",
            "1대는 주소를 판독하지 못했다",
            "콘솔 픽스처 1대가 최소 인덱스 미만",
        ),
        (),
        id="all_three_incomplete_axes__every_clause_ships",
    ),
)


@pytest.mark.parametrize(
    ("axes", "kind", "unpatched_count", "must_say", "must_not_say"), _ROUND15_CAVEAT_TABLE
)
def test_the_console_read_caveat_branches_say_exactly_what_was_observed(
    axes, kind, unpatched_count, must_say, must_not_say
):
    """네 갈래 · 세 입력 축의 **전수 표** — 숫자와 그 숫자를 소비하는 문장을 함께 잠근다.

    round11·12·13이 세 번 연속 같은 기제로 실패했다: 고친 축만 보고 형제 축은 안 봤다.
    그래서 한 갈래에 대조군을 붙이는 대신 **여덟 조합을 표로 열거**한다.

    [round15] 이 표가 죽이는 뮤테이션:
    - `apply.py` `_unpatched_clause` 반환 문장을 `"확인할 것은 없다"`로 → 필수 문구 소실 +
      안심 어휘 검출(세 갈래 전부에서 깨진다).
    - `apply.py` UNPATCHED 갈래의 `"unpatched_count": unpatched`를 `0`으로 →
      `unpatched__*` 행이 깨진다.
    - `apply.py` INCOMPLETE 갈래의 `"unpatched_count": unpatched`를 `0`으로 →
      `unread_and_unpatched__*` · `all_three_axes__*` 행이 깨진다.
    - `apply.py`의 `if unpatched:` 갈래를 INDEX_DOMAIN 갈래 뒤로 이동(우선순위 반전) →
      `unpatched_and_idu__*` 행의 kind가 뒤집힌다.
    - `apply.py` `reason = f"{reason} 또한 {_INDEX_DOMAIN_CLAUSE}"` 줄 삭제 →
      `unpatched_and_idu__*` 행의 절단 고지가 사라진다.
    - `verdicts.py`의 caveat 라벨 변조 → 라벨 동등 단정과 어휘 단정이 깨진다.
    - INCOMPLETE 사유가 0인 축을 문장에 넣으면(`missing_count=0`인데 "0대를 열거하지
      못했다") `unread__unreadable_address_only` 행이 깨진다.
    """
    from server.vwx.verdicts import console_read_caveat_label

    caveat = console_read_caveat(_round15_inventory(**axes))
    if kind is None:
        assert caveat is None
        return
    assert caveat is not None
    assert caveat["kind"] == kind
    # 라벨은 리터럴 복사가 아니라 **프로덕션 함수**에서 받는다.
    assert caveat["label"] == console_read_caveat_label(kind)

    missing = axes.get("missing", 0)
    unreadable = axes.get("unreadable", 0)
    # 세 갈래 전부가 **관측값**을 싣는다 — 어느 갈래도 0으로 굳히지 않는다.
    assert caveat["unpatched_count"] == unpatched_count
    assert caveat["missing_count"] == missing
    assert caveat["unreadable_address_count"] == unreadable
    assert caveat["unread_count"] == missing + unreadable

    reason = str(caveat["reason"])
    for fragment in must_say:
        assert fragment in reason, reason
    for fragment in must_not_say:
        assert fragment not in reason, reason

    # 관측된 사실만 적는다 — 0인 축은 문장에 넣지 않는다(round15 N12).
    if not missing:
        assert "열거하지 못했다" not in reason, reason
    if not unreadable:
        assert "주소를 판독하지 못했다" not in reason, reason
    if not axes.get("unpatched", 0):
        assert "최소 인덱스 미만" not in reason, reason

    for text in (reason, str(caveat["label"])):
        assert _round15_reassurances(text) == [], text
        assert _round15_cautions(text) != [], text


_ROUND15_CAVEAT_KINDS = (
    CONSOLE_READ_INCOMPLETE,
    CONSOLE_READ_INDEX_DOMAIN_UNKNOWN,
    CONSOLE_READ_UNPATCHED_PRESENT,
)


def test_the_round15_label_gate_covers_every_caveat_kind():
    """형제 경로 누락 방지 — caveat 종류가 하나 늘면 이 단정이 **먼저** 깨진다."""
    from server.vwx.verdicts import CONSOLE_READ_CAVEAT_KIND

    assert set(_ROUND15_CAVEAT_KINDS) == set(CONSOLE_READ_CAVEAT_KIND)


@pytest.mark.parametrize("code", _ROUND15_CAVEAT_KINDS)
def test_every_console_read_caveat_label_warns_rather_than_reassures(code):
    """라벨은 조작자가 보는 첫 문장이다 — 안심 어휘가 들어가면 실패한다.

    [round15] `verdicts.py`의 UNPATCHED_PRESENT 라벨을 `"예비 픽스처가 있다 — 문제 없다"`로
    바꾸면 이 테스트가 실패한다. 리터럴을 복사하지 않고 **프로덕션 함수**에서 받으며,
    같은 검사를 형제 두 종류의 라벨에도 적용한다.
    """
    from server.vwx.verdicts import console_read_caveat_label

    label = console_read_caveat_label(code)
    assert _round15_reassurances(label) == [], label
    assert _round15_cautions(label) != [], label


@pytest.mark.parametrize("truncated", [True, False], ids=["truncated", "not_truncated"])
def test_the_unpatched_caveat_reports_the_truncation_flag_truthfully(truncated):
    """절단 여부를 **삼키지 않고 실어 보낸다** — 억제 가드가 되살아나면 여기서도 갈린다."""
    caveat = console_read_caveat(_round15_inventory(unpatched=1, index_domain_unknown=truncated))
    assert caveat is not None
    assert caveat["kind"] == CONSOLE_READ_UNPATCHED_PRESENT
    assert caveat["index_domain_unknown"] is truncated


def test_the_unpatched_disclosure_outranks_the_index_domain_notice():
    """핵심 행 — 절단은 이 콘솔의 **기본 경로**다(실물 콘솔은 픽스처 19대에서 이미 절단).

    이전 판은 `and not inventory.index_domain_unknown` 가드를 달아, 절단이 참이면
    미실측 가정 고지를 통째로 삼키고 "인덱스 도메인만 미상이다"라는 **안심 문구**만 냈다.
    절단이 기본 경로이므로 그 억제는 실제 세션에서 거의 항상 발동했다.
    두 문장이 **모두** 나가야 한다.

    [round15] `apply.py`의 `if unpatched:` 갈래를 INDEX_DOMAIN 갈래 뒤로 옮기거나
    `reason = f"{reason} 또한 {_INDEX_DOMAIN_CLAUSE}"` 줄을 지우면 이 테스트가 실패한다.
    """
    caveat = console_read_caveat(_round15_inventory(unpatched=19, index_domain_unknown=True))
    assert caveat is not None
    assert caveat["kind"] == CONSOLE_READ_UNPATCHED_PRESENT
    reason = str(caveat["reason"])
    assert "콘솔 픽스처 19대가 최소 인덱스 미만" in reason
    assert "세션 전에 눈으로 대조하라" in reason
    assert "인덱스 도메인만 미상이다" in reason


_ROUND15_UNPATCHED_COUNT_FIELD = '"unpatched_count": unpatched'


def _round15_unpatched_count_gate(source: str) -> tuple[int, int]:
    """(관측값에서 유도한 자리 수, `unpatched_count` 키가 나오는 전체 자리 수)."""
    return source.count(_ROUND15_UNPATCHED_COUNT_FIELD), source.count('"unpatched_count":')


def test_every_caveat_branch_derives_the_unpatched_count_from_the_observation():
    """세 갈래 전부가 **관측값**을 싣는다 — 리터럴로 굳힌 자리가 없다.

    행동으로 잡히는 갈래는 둘이다(위 표의 `unpatched__*` · `unread_and_unpatched__*`).
    INDEX_DOMAIN 갈래는 `unpatched == 0`일 때만 도달하므로 그 자리를 `0`으로 굳혀도
    행동 차이가 없다 — 등가 뮤턴트다. 그래서 그 갈래만은 **구조로** 잠그고,
    아래 대조군이 이 게이트가 실제로 잡는다는 것을 프로덕션 사본으로 확인한다.

    [round15] 세 갈래 중 어느 하나라도 `"unpatched_count": 0`으로 바꾸면 실패한다.
    """
    derived, total = _round15_unpatched_count_gate(APPLY_SOURCE)
    assert derived == total
    assert derived >= len(_ROUND15_CAVEAT_KINDS)


def test_the_unpatched_count_source_gate_catches_a_literal_in_the_last_branch():
    """비공허성 — **마지막** 갈래(INDEX_DOMAIN)에 리터럴을 심으면 게이트가 깨진다.

    같은 사본을 실행해 **행동으로는 구별되지 않는다**는 것까지 보인다 —
    구조 게이트가 왜 필요한지가 그 대비에서 나온다.
    """
    cut = APPLY_SOURCE.rfind(_ROUND15_UNPATCHED_COUNT_FIELD)
    assert cut != -1
    planted = (
        APPLY_SOURCE[:cut]
        + '"unpatched_count": 0'
        + APPLY_SOURCE[cut + len(_ROUND15_UNPATCHED_COUNT_FIELD) :]
    )
    assert planted != APPLY_SOURCE
    derived, total = _round15_unpatched_count_gate(planted)
    assert derived != total

    namespace = _load(planted)
    caveat = namespace["console_read_caveat"](_round15_inventory(index_domain_unknown=True))
    assert caveat["kind"] == CONSOLE_READ_INDEX_DOMAIN_UNKNOWN
    assert caveat["unpatched_count"] == 0


def _round15_valid_lua_entry() -> LuaPatchEntry:
    """생성기가 **받아들이는** 항목 — 어떤 프로브도 거부되지 않으므로 폴백에 도달한다."""
    return LuaPatchEntry(
        console_type=LED,
        console_mode=MODE_1,
        fid=101,
        name="LEDBeam 101",
        universe=1,
        address=1,
    )


#: 예날 폴백 문구가 주장했던 것. 도달 조건은 그 **반대**다 — 프로브가 전부 통과했다는 뜻이다.
_ROUND15_SELF_CONTRADICTING_FALLBACK = "중립 입력도 거부"


def test_the_rejected_field_fallback_does_not_claim_the_opposite_of_its_condition():
    """폴백은 "단일 필드로 환원되지 않는다"까지만 말한다 — 관측하지 않은 것을 주장하지 않는다.

    이 자리는 도달 가능하다: 모든 프로브가 통과하면(= 중립 기준선이 거부되지 **않았다**는 뜻)
    폴백이 나온다. 예날 문구는 하필 그 조건의 반대("중립 입력도 거부됨")를 적어, 사용자가
    무엇을 고쳐야 하는지를 거짓으로 알렸다.

    [round15] `apply.py` 폴백 문구를 `"확정 불가(중립 입력도 거부됨)"`로 되돌리면 실패한다.
    """
    from server.vwx.apply import _rejected_field

    fallback = _rejected_field(_round15_valid_lua_entry())
    assert "확정 불가" in fallback
    assert _ROUND15_SELF_CONTRADICTING_FALLBACK not in fallback
    assert _round15_reassurances(fallback) == [], fallback


def test_no_apply_text_claims_the_neutral_baseline_was_rejected():
    """같은 자기모순 문구가 다른 자리로 옮겨가는 것까지 막는다."""
    assert _ROUND15_SELF_CONTRADICTING_FALLBACK not in APPLY_SOURCE


def test_the_self_contradicting_fallback_gate_is_not_vacuous():
    """비공허성 — 예날 문구를 심은 **프로덕션 사본**에서 위 두 단정이 실제로 깨진다."""
    planted = APPLY_SOURCE.replace(
        "확정 불가(거부 사유가 단일 필드로 환원되지 않는다)",
        "확정 불가(중립 입력도 거부됨)",
        1,
    )
    assert planted != APPLY_SOURCE
    assert _ROUND15_SELF_CONTRADICTING_FALLBACK in planted
    namespace = _load(planted)
    assert _ROUND15_SELF_CONTRADICTING_FALLBACK in namespace["_rejected_field"](
        _round15_valid_lua_entry()
    )


# --------------------------------------------------------------------------
# --- round15 D 콘솔 표시 문자열은 관측 데이터다 ---
#
# 안전 감사 실측: 계획 주소를 점유한 콘솔 픽스처의 `type_display`가 `'CD 5'`이고
# `identity_resolved=False`이면 `CD_TOKEN.search(repr(handoff.to_dict()))`가 **매치**했다.
# 그것은 위반이 아니라 **관측 데이터**다 — 거짓 양성이고, 흔한 거짓 양성은 게이트의
# 강제력을 없앤다(§0 2b④가 정확히 그것을 금한다).
#
# 두 축을 함께 고쳤다:
#   축 1 (게이트) — 훑는 표면을 콘솔로 나가는 축으로 좁혔다(`_console_bound_text`).
#   축 2 (문장)   — 표시 문자열 원문을 사유·detail **문장**에서 빼고 구조화 필드로 옮겼다
#                   (`observed_type_display` · `observed_mode_display`). 값은 버리지 않는다 —
#                   조작자는 무엇을 봤는지 알아야 한다(§0 2c①).
# 한 축만 고치면 다른 축이 곧 같은 결함을 다시 만든다(HARD 규율 1).
# --------------------------------------------------------------------------


def _cd_occupied_handoff():
    """감사자 구성 그대로 — 계획 주소를 `'CD 5'` 표시 문자열 픽스처가 점유한 전달물."""
    console = _console(_record(1, "1.1", "CD 5", "9 Mode 9"))
    targets = (_candidate("a", 1, 1, 101),)
    resolutions = (_resolution("a"),)
    screened = screen_idempotent(
        targets,
        address_plan=AddressPlan(entries=(_planned("a", 1, 1),)),
        resolutions=resolutions,
        console_fixtures=console,
    )
    return build_patch_handoff(
        targets,
        address_plan=screened,
        resolutions=resolutions,
        names={"a": "LEDBeam 101"},
        dry_run=False,
    )


def test_the_cd_occupancy_fixture_actually_reaches_the_identity_unconfirmed_branch():
    """재현 구성이 겨냥한 분기에 실제로 도달한다 — 아니면 아래 두 단정이 공허하다."""
    handoff = _cd_occupied_handoff()
    assert [exclusion.code for exclusion in handoff.exclusions] == [EXISTING_IDENTITY_UNCONFIRMED]


def test_a_console_display_string_carrying_cd_is_not_a_gate_violation():
    """[round15 D 축 1] 관측 데이터의 `CD`는 위반이 아니다 — 좁힌 게이트가 발화하지 않는다.

    좁히기 전(`repr(handoff.to_dict())` 전수 훑기)에는 여기서 게이트가 **잘못** 발화했다.
    """
    assert CD_TOKEN.search(_console_bound_text(_cd_occupied_handoff())) is None


def test_the_observed_display_strings_travel_in_structured_fields_not_in_the_reason_sentence():
    """[round15 D 축 2 · round17 S17-03a] 문장은 좌표만, 관측된 것은 구조화 필드로.

    `screen_idempotent`의 사유 문장에 `occupant.type_display`를 되싣도록 되돌리면 이 단정이
    실패한다 — 그리고 그 회귀가 곧 위 거짓 양성의 원인이다.
    """
    exclusion = _cd_occupied_handoff().exclusions[0]
    assert "CD 5" not in exclusion.reason
    assert "9 Mode 9" not in exclusion.reason
    assert CD_TOKEN.search(exclusion.reason) is None
    assert "유니버스 1 주소 1" in exclusion.reason
    assert [occupant["type_display"] for occupant in exclusion.observed_occupants] == ["CD 5"]
    assert [occupant["mode_display"] for occupant in exclusion.observed_occupants] == ["9 Mode 9"]
    assert exclusion.to_dict()["observed_occupants"] == [
        dict(occupant) for occupant in exclusion.observed_occupants
    ]


def test_the_verification_detail_also_keeps_the_display_strings_out_of_the_sentence():
    """[round15 D 축 2 — 형제 축] `verify_patch`의 `detail`도 같은 규율을 받는다.

    round11·12·13이 세 번 연속으로 놓친 기제가 "고친 축만 보고 형제 축은 안 봤다"이다.
    `screen_idempotent`만 고치고 `verify_patch`를 두면 같은 결함이 그대로 남는다.
    """
    report = verify_patch(
        (_entry("a", 1, 1),),
        console_fixtures=_console(_record(1, "1.1", "CD 5", "9 Mode 9")),
    )
    result = report.results[0]
    assert result.outcome == VERIFICATION_IDENTITY_UNCONFIRMED
    assert "CD 5" not in result.detail
    assert CD_TOKEN.search(result.detail) is None
    assert [occupant["type_display"] for occupant in result.observed_occupants] == ["CD 5"]
    assert [occupant["mode_display"] for occupant in result.observed_occupants] == ["9 Mode 9"]
    assert result.to_dict()["observed_occupants"] == [
        dict(occupant) for occupant in result.observed_occupants
    ]


def test_no_exclusion_reason_leaks_onto_a_console_bound_surface():
    """[round15 D] 제외 진단문이 게이트 밖인 **근거**를 구조로 확인한다.

    사유에 실린 문자열이 `lua_source`·절차·경고·`next_step`·`entries`로 새어 나가면 좁힌
    게이트가 곧 구멍이 된다. 표시 문자열이든 라이브러리 확정 이름이든 마찬가지다.
    """
    handoff = _cd_occupied_handoff()
    console_bound = _console_bound_text(handoff)
    assert handoff.exclusions
    for exclusion in handoff.exclusions:
        assert exclusion.reason not in console_bound


# --------------------------------------------------------------------------
# --- round16 사람이 읽는 문장 내용 고정 (TextContentGates) ---
#
# round16 적대 감사의 공통 기제 두 가지를 여기서 닫는다.
#
#   (가) **자기 비교** — `assert payload["status"] == HANDOFF_STATUS_DRY_RUN`은 프로덕션
#        상수를 프로덕션 값과 비교하므로 상수를 무엇으로 바꿔도 통과한다. `dry_run` payload의
#        `status`가 `"delivered"`가 되어도(M72), `next_step`이 `"done"`이 되어도(M79)
#        스위트 5,354건이 전건 통과했다. 그래서 **리터럴로** 적고, 모듈 상수를 **전수로**
#        열거해 전단사를 건다 — 하나만 고치면 형제가 또 남는다(HARD 규율 1).
#
#   (나) **좁힌 게이트의 형제 누락** — `_CONSOLE_BOUND_HANDOFF_KEYS`는 `PatchHandoff.to_dict()`
#        **안에서만** 전수다. `verify_patch`가 돌려주는 `verification` 블록은 그 표 밖이고,
#        그 안의 `guidance`는 **사람이 콘솔에서 따라 실행할 절차 지시문**이다. 실제로
#        `ZERO_CREATED_GUIDANCE`에 `" 먼저 CD Root 로 이동하라."`를 덧붙여도 어떤 게이트도
#        발화하지 않았다(S16-04). 검증 payload의 키도 **두 축으로 전수 분류**하고,
#        콘솔로 나가는 축에 같은 CD 게이트를 붙인다.
# --------------------------------------------------------------------------


def _r16_module_constant_names(source: str) -> tuple[str, ...]:
    """모듈 최상위 상수 이름을 **소스에서** 전수로 뽑는다 — 표가 아니라 프로덕션이 기준이다."""
    import ast

    names: list[str] = []
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign):
            names.extend(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.append(node.target.id)
    return tuple(names)


def _r16_constant_value(value):
    """비교 가능한 형태로 정규화한다 — 컴파일된 정규식은 동등 비교가 항등이므로 패턴으로 본다."""
    if hasattr(value, "pattern"):
        return value.pattern
    if hasattr(value, "keys"):
        return dict(value)
    return value


def _r16_procedure_texts() -> tuple[str, ...]:
    """절차 전문 표는 `test_autopatch_execute.py`에 손으로 적혀 있다 — 여기서 재활용한다."""
    from server.tests.test_autopatch_execute import _R16_PROCEDURE_TEXTS

    return _R16_PROCEDURE_TEXTS


_R16_IRREVERSIBLE_WARNING = (
    "이 앱에는 실행 취소·백업 복원 경로가 없고, 잘못 생성된 픽스처는 콘솔에서 사람이 지워야 한다."
)
_R16_PLUGIN_EXIT_IS_NOT_SUCCESS = (
    "플러그인이 오류 없이 끝난 것은 성공이 아니다 — AddFixtures는 실패해도 nil을 반환할 뿐이다. "
    "생성 여부는 서버의 검증 읽기로만 확정된다."
)
_R16_END_TO_END_UNVERIFIED = (
    "이 절차의 종단 성공은 이 빌드에서 아직 확인되지 않았다 — 서버 자동 실행 경로는 "
    "전부 0건이었고, "
    "사람이 실행하는 경로의 종단 확인은 라이브 검증 마일스톤에 남아 있다."
)
_R16_ZERO_CREATED_GUIDANCE = (
    "승인 항목 중 재조회에서 관측된 것이 0건이다 — 플러그인을 실제로 실행했는지, "
    "그리고 실행 절차의 각 단계(라이브러리 파일 저장 → Import Plugin → 재임포트 캐싱 주의 → "
    "플러그인 실행)를 다시 확인하라."
)
_R16_NO_AUTO_CORRECTION = (
    "서버는 자동으로 재시도하거나 보정하지 않는다 — 다시 시도하려면 사람이 다시 요청해야 한다."
)
_R16_INDEX_DOMAIN_CLAUSE = (
    "열거가 절단됐으나 선언된 자식을 전부 관측했다 — 수량 비교는 정확하고, "
    "인덱스 도메인만 미상이다."
)
#: [round19 major#4] 확인 경로가 실제로 있는 경우에만 쓰이는 **기본** 배제 사유.
_R19_TYPE_CONFIRMATION_PENDING_REASON = (
    "콘솔 타입·모드가 확정되지 않았다 — 확인 전에 되돌릴 수 없는 생성을 전달하지 않는다."
)

#: `apply.py` 모듈 상수 **전수** — (이름, 종류, 고정 리터럴). 프로덕션에서 파생하지 않는다.
#: 종류는 그 상수가 어디로 나가는지를 정한다:
#:   payload_token        — payload에 그대로 실리는 기계 토큰(`test_autopatch_execute.py`의
#:                          `_R16_PAYLOAD_STATUS_ROWS`가 payload 쪽에서 같은 값을 고정한다)
#:   classification_token — `classify_patch_value`의 반환 어휘
#:   human_text/human_tuple — **사람이 읽는 문장**. 아래 도달 표가 실제 표면까지 확인한다
#:   internal             — 사람에게도 payload에도 나가지 않는 내부 값
_R16_APPLY_CONSTANTS = (
    ("BELOW_MINIMUM_INDEX_ERROR", "internal", "유니버스·주소는 1 이상이어야 한다"),
    ("HANDOFF_STATUS_DRY_RUN", "payload_token", "dry_run"),
    ("HANDOFF_STATUS_DELIVERED", "payload_token", "delivered"),
    ("NEXT_STEP_REVIEW", "payload_token", "review_dry_run"),
    ("NEXT_STEP_HUMAN_EXECUTION", "payload_token", "human_execution_then_verification_read"),
    ("EXECUTION_PERFORMED_BY", "payload_token", "human"),
    ("PLUGIN_EXIT_IS_NOT_SUCCESS", "human_text", _R16_PLUGIN_EXIT_IS_NOT_SUCCESS),
    ("END_TO_END_UNVERIFIED", "human_text", _R16_END_TO_END_UNVERIFIED),
    ("HUMAN_EXECUTION_PROCEDURE", "human_tuple", _r16_procedure_texts()),
    (
        "DELIVERY_WARNINGS",
        "human_tuple",
        (
            _R16_IRREVERSIBLE_WARNING,
            _R16_PLUGIN_EXIT_IS_NOT_SUCCESS,
            _R16_END_TO_END_UNVERIFIED,
        ),
    ),
    (
        "_NEUTRAL_FIELDS",
        "internal",
        {
            "name": "ok",
            "console_type": "ok",
            "console_mode": "ok",
            "fid": 1,
            "universe": 1,
            "address": 1,
        },
    ),
    ("_TYPE_DISPLAY_INDEX", "internal", r"^FixtureType (\d+)$"),
    ("_MODE_DISPLAY_INDEX", "internal", r"^(\d+) (.+)$"),
    ("ZERO_CREATED_GUIDANCE", "human_text", _R16_ZERO_CREATED_GUIDANCE),
    ("NO_AUTO_CORRECTION", "human_text", _R16_NO_AUTO_CORRECTION),
    ("PATCH_UNREAD", "classification_token", "unread"),
    ("PATCH_UNPATCHED", "classification_token", "unpatched"),
    ("PATCH_ADDRESSED", "classification_token", "addressed"),
    ("_INDEX_DOMAIN_CLAUSE", "human_text", _R16_INDEX_DOMAIN_CLAUSE),
    (
        "TYPE_CONFIRMATION_PENDING_REASON",
        "human_text",
        _R19_TYPE_CONFIRMATION_PENDING_REASON,
    ),
)


def test_the_apply_constant_table_is_a_bijection_onto_the_module_constants():
    """[round16 HARD 규율 1·3] `apply.py`에 모듈 상수를 더하거나 지우면 여기서 먼저 깨진다.

    "하나만 고치면 형제가 또 남는다"를 구조로 막는 자리다 — M72(`HANDOFF_STATUS_DRY_RUN`)를
    고치고 M79(`NEXT_STEP_HUMAN_EXECUTION`)를 남긴 것이 정확히 그 실패였다.
    표에서 행을 하나 지우면 이 단정이 실패한다.
    """
    discovered = _r16_module_constant_names(APPLY_SOURCE)
    declared = tuple(name for name, _, _ in _R16_APPLY_CONSTANTS)
    assert len(declared) == len(set(declared)) == len(discovered)
    assert sorted(declared) == sorted(discovered)


@pytest.mark.parametrize(
    "name,kind,expected", _R16_APPLY_CONSTANTS, ids=[n for n, _, _ in _R16_APPLY_CONSTANTS]
)
def test_every_apply_module_constant_is_pinned_to_its_literal(name, kind, expected):
    """[round16 M72] `HANDOFF_STATUS_DRY_RUN`을 `"delivered"`로 바꾸면 그 행이 실패한다.
    [round16 M79] `NEXT_STEP_HUMAN_EXECUTION`을 `"done"`으로 바꾸면 그 행이 실패한다.
    [round16 M53] `HUMAN_EXECUTION_PROCEDURE` 5단계를 바꾸면 그 행이 실패한다.
    [round16 S16-04] `ZERO_CREATED_GUIDANCE`에 문장을 덧붙이면 그 행이 실패한다.

    **리터럴 대조**이므로 상수를 무엇으로 바꿔도 기대값이 따라가지 않는다(자기 비교 금지).
    """
    from server.vwx import apply

    assert kind in {
        "payload_token",
        "classification_token",
        "human_text",
        "human_tuple",
        "internal",
    }
    assert _r16_constant_value(getattr(apply, name)) == expected


def test_the_payload_token_kind_matches_the_execute_side_status_table():
    """두 파일의 표가 서로를 묶는다 — 한쪽에만 상태 상수를 더하면 여기서 깨진다."""
    from server.tests.test_autopatch_execute import _R16_PAYLOAD_TOKEN_CONSTANTS

    tokens = {name for name, kind, _ in _R16_APPLY_CONSTANTS if kind == "payload_token"}
    assert tokens == set(_R16_PAYLOAD_TOKEN_CONSTANTS)


@pytest.mark.parametrize(
    "name,expected",
    [(n, e) for n, k, e in _R16_APPLY_CONSTANTS if k == "classification_token"],
    ids=[n for n, k, _ in _R16_APPLY_CONSTANTS if k == "classification_token"],
)
def test_every_classification_token_is_returned_verbatim_by_the_classifier(name, expected):
    """분류 어휘도 리터럴로 고정한다 — 상수와 비교하면 값이 바뀌어도 통과한다."""
    raw = {"unread": None, "unpatched": "0.0", "addressed": "1.5"}[expected]
    record = _record(1, raw, "FixtureType 3", "1 Mode 1")
    if raw is None:
        record = FixtureRecord(
            slot=1,
            name="unreadable 1",
            patch_raw=None,
            fixture_type="FixtureType 3",
            mode="1 Mode 1",
            read_failures=(
                ReadFailure(
                    slot=1,
                    name="unreadable 1",
                    property="Patch",
                    raw_value=None,
                    kind="read_failed",
                    detail="not readable",
                ),
            ),
        )
    assert classify_patch_value(record) == expected


# --------------------------------------------------------------------------
# 사람이 읽는 상수는 **실제 표면까지 도달**해야 한다. 리터럴만 고정하고 도달을 보지 않으면
# 상수를 그대로 둔 채 payload에서 빼는 변조가 빠져나간다(round14 T02가 명명한 기제).
# --------------------------------------------------------------------------


def _r16_delivered_handoff():
    from server.tests.test_autopatch_execute import _handoff_kwargs

    return build_patch_handoff(**_handoff_kwargs(dry_run=False))


def _r16_zero_created_report():
    """전달분이 있는데 관측이 0건 — `guidance` 두 문장이 모두 나가는 유일한 경로."""
    return verify_patch((_entry("a", 1, 1),), console_fixtures=_console())


def _r16_delivered_warnings() -> tuple[str, ...]:
    return tuple(_r16_delivered_handoff().warnings)


def _r16_delivered_procedure() -> tuple[str, ...]:
    return tuple(_r16_delivered_handoff().procedure)


def _r16_verification_guidance() -> tuple[str, ...]:
    return tuple(_r16_zero_created_report().guidance)


def _r16_index_domain_caveat_reason() -> tuple[str, ...]:
    caveat = console_read_caveat(_round15_inventory(index_domain_unknown=True))
    assert caveat is not None
    return (str(caveat["reason"]),)


def _r19_type_pending_exclusion_reasons() -> tuple[str, ...]:
    """[round19 major#4] 기본 사유가 실제로 `handoff.exclusions`까지 나가는지 — 프로덕션 경로로.

    해상 결과가 아예 없는 후보다(`resolutions=()`). 그 상태는 하드 스톱이 아니라 **진짜
    확인 대기**이므로 이 문장을 쓴다. 하드 스톱 자리는 이 문장을 쓰지 않는다 —
    `handoff.type_hard_stop` 행이 그것을 따로 고정한다.
    """
    return tuple(exclusion.reason for exclusion in _r16_handoff_exclusions(resolutions=()))


#: (상수 이름, 표면 이름, 그 표면을 프로덕션에서 만들어 오는 호출)
_R16_HUMAN_SURFACE_PROBES = (
    ("PLUGIN_EXIT_IS_NOT_SUCCESS", "handoff.warnings", _r16_delivered_warnings),
    ("END_TO_END_UNVERIFIED", "handoff.warnings", _r16_delivered_warnings),
    ("HUMAN_EXECUTION_PROCEDURE", "handoff.procedure", _r16_delivered_procedure),
    ("DELIVERY_WARNINGS", "handoff.warnings", _r16_delivered_warnings),
    ("ZERO_CREATED_GUIDANCE", "verification.guidance", _r16_verification_guidance),
    ("NO_AUTO_CORRECTION", "verification.guidance", _r16_verification_guidance),
    (
        "TYPE_CONFIRMATION_PENDING_REASON",
        "handoff.exclusions.reason",
        _r19_type_pending_exclusion_reasons,
    ),
    ("_INDEX_DOMAIN_CLAUSE", "console_read_caveat.reason", _r16_index_domain_caveat_reason),
)


def test_the_human_surface_probe_table_covers_every_human_constant():
    """[round16 HARD 규율 1] 사람이 읽는 상수를 하나 더하면 도달 표에도 넣어야 통과한다."""
    human = {
        name for name, kind, _ in _R16_APPLY_CONSTANTS if kind in {"human_text", "human_tuple"}
    }
    assert {name for name, _, _ in _R16_HUMAN_SURFACE_PROBES} == human
    assert len(_R16_HUMAN_SURFACE_PROBES) == len(human)


@pytest.mark.parametrize(
    "name,surface_label,surface",
    _R16_HUMAN_SURFACE_PROBES,
    ids=[f"{name}->{label}" for name, label, _ in _R16_HUMAN_SURFACE_PROBES],
)
def test_every_human_constant_reaches_its_surface_verbatim(name, surface_label, surface):
    """상수의 **고정된 리터럴**이 실제 표면에 그대로 실려 나간다.

    비교 대상은 프로덕션 상수가 아니라 위 표의 리터럴이다 — 상수를 바꾸면 표면 값도 함께
    바뀌므로 자기 비교로는 아무것도 잡히지 않는다.
    """
    expected = next(value for entry, _, value in _R16_APPLY_CONSTANTS if entry == name)
    produced = surface()
    if isinstance(expected, tuple):
        assert produced == expected
    else:
        assert expected in produced


# --------------------------------------------------------------------------
# [round16 S16-04] `verification` 블록의 콘솔 표면 등록.
#
# `ZERO_CREATED_GUIDANCE`는 "라이브러리 파일 저장 → Import Plugin → 재임포트 → 실행"을
# 다시 밟으라는 **사람 절차 지시문**이다. `procedure`와 같은 부류인데 `procedure`만
# 게이트 안에 있었다. 여기서 검증 payload의 키를 전수 분류하고 같은 CD 게이트를 건다.
# --------------------------------------------------------------------------

#: 콘솔로 나가는 축 — 사람이 읽고 콘솔에서 따라 실행한다.
_R16_VERIFICATION_CONSOLE_BOUND_KEYS = ("guidance",)

#: 콘솔에서 실행되지 않는 축 — 관측·집계 보고. `results`가 여기 있는 이유는 그 안이
#: **콘솔이 돌려준 원문**(`observed_*_display`)을 싣는 자리이기 때문이다. 원문의 `CD`는
#: 위반이 아니라 관측 데이터이고, 그것을 게이트에 넣으면 거짓 양성이 게이트를 무력화한다
#: (round15 D · `test_a_console_display_string_carrying_cd_is_not_a_gate_violation`).
_R16_VERIFICATION_DIAGNOSTIC_KEYS = (
    "ok",
    "all_observed",
    "observed_count",
    "not_observed_count",
    "mismatch_count",
    "identity_unconfirmed_count",
    "delivered_count",
    "created_count",
    "results",
)

#: `results[]` 원소의 키 전수 — 전부 관측·진단 축이다. 콘솔에 입력할 문자열은 없다.
_R16_VERIFICATION_RESULT_KEYS = (
    "delivered",
    "candidate_id",
    "universe",
    "address",
    "expected_type",
    "expected_mode",
    "observed_type",
    "observed_mode",
    "observed_occupants",
    "outcome",
    "label",
    "detail",
)


def _r16_console_bound_verification_text(report) -> str:
    """검증 payload에서 **콘솔로 나가는 축만** 문자열로 모은다 — CD 게이트가 훑는 표면."""
    payload = report.to_dict()
    return repr({key: payload[key] for key in _R16_VERIFICATION_CONSOLE_BOUND_KEYS})


def test_every_verification_payload_key_is_classified_console_bound_or_diagnostic():
    """[round16 S16-04] `PatchVerification.to_dict()`에 키가 생기면 분류 없이는 통과 못한다.

    `_CONSOLE_BOUND_HANDOFF_KEYS`가 `PatchHandoff` **안에서만** 전수였던 것이 이번 지적의
    핵심이다. 형제 payload에도 같은 표를 세운다(HARD 규율 1).
    """
    payload = _r16_zero_created_report().to_dict()
    assert set(_R16_VERIFICATION_CONSOLE_BOUND_KEYS).isdisjoint(_R16_VERIFICATION_DIAGNOSTIC_KEYS)
    assert set(_R16_VERIFICATION_CONSOLE_BOUND_KEYS) | set(
        _R16_VERIFICATION_DIAGNOSTIC_KEYS
    ) == set(payload)


def test_every_verification_result_key_is_enumerated():
    """형제 축 — `results[]` 원소에 키가 생겨도 분류를 강제한다."""
    payload = _r16_zero_created_report().to_dict()
    assert payload["results"], "결과가 비면 이 게이트는 공허하다"
    for result in payload["results"]:
        assert set(result) == set(_R16_VERIFICATION_RESULT_KEYS)


def test_the_zero_created_guidance_is_registered_as_a_console_bound_surface():
    """[round16 S16-04] 안내 문구가 **게이트가 훑는 표면 안에** 실제로 들어 있다."""
    report = _r16_zero_created_report()
    text = _r16_console_bound_verification_text(report)
    assert ZERO_CREATED_GUIDANCE in text
    assert NO_AUTO_CORRECTION in text
    assert CD_TOKEN.search(text) is None
    assert [token for token in REFUTED_REMEDY_TOKENS if token in text] == []


def _r16_guidance_constant_names(source: str) -> tuple[str, ...]:
    """`verify_patch`가 `guidance=`로 내보내는 상수를 **소스에서** 전수로 뽑는다."""
    import ast

    module = ast.parse(source)
    verify = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == "verify_patch"
    )
    names: set[str] = set()
    for node in ast.walk(verify):
        if isinstance(node, ast.keyword) and node.arg == "guidance":
            names.update(sub.id for sub in ast.walk(node.value) if isinstance(sub, ast.Name))
    return tuple(sorted(names))


#: (안내 상수, 그 상수에 심을 절차 지시문). 감사가 실제로 심은 문장을 그대로 쓴다.
_R16_GUIDANCE_CD_PLANTS = (
    ("NO_AUTO_CORRECTION", " 먼저 ChangeDestination Root 로 이동하라."),
    ("ZERO_CREATED_GUIDANCE", " 먼저 CD Root 로 이동하라."),
)


def test_the_guidance_plant_table_covers_every_guidance_constant():
    """[round16 HARD 규율 3] 안내 상수가 하나 늘면 심는 표도 함께 늘어야 한다.

    표에서 행을 지우면 이 단정이 실패한다.
    """
    assert tuple(name for name, _ in _R16_GUIDANCE_CD_PLANTS) == _r16_guidance_constant_names(
        APPLY_SOURCE
    )


@pytest.mark.parametrize(
    "name,sentence", _R16_GUIDANCE_CD_PLANTS, ids=[name for name, _ in _R16_GUIDANCE_CD_PLANTS]
)
def test_the_verification_cd_gate_catches_a_plant_on_every_guidance_constant(name, sentence):
    """[round16 S16-04] 감사가 심은 그 문장을 **프로덕션 사본에** 심으면 게이트가 잡는다.

    `ZERO_CREATED_GUIDANCE`·`NO_AUTO_CORRECTION`은 `verify_patch`가 호출 시점에 읽는 모듈
    전역이므로, 사본에서 재바인딩하면 **적재된 프로덕션 함수의 반환값**에 그대로 실린다.
    """
    namespace = _load(APPLY_SOURCE + f'\n\n{name} = {name} + "{sentence}"\n')
    report = namespace["verify_patch"]((_entry("a", 1, 1),), console_fixtures=_console())
    assert report.created_count == 0
    assert CD_TOKEN.search(_r16_console_bound_verification_text(report)) is not None


def test_the_verification_cd_gate_is_clean_without_a_plant():
    """대조군의 대조군 — 심지 않은 프로덕션 사본에서는 같은 게이트가 0건이다."""
    namespace = _load(APPLY_SOURCE)
    report = namespace["verify_patch"]((_entry("a", 1, 1),), console_fixtures=_console())
    assert report.created_count == 0
    assert CD_TOKEN.search(_r16_console_bound_verification_text(report)) is None


# --- round16 구간 경계 전수 (OccupancyBoundary) ---
#
# round15의 치명 2건과 round16 M61은 **같은 형태**다 — 구간 비교의 경계 한 칸에 대조군이 없다.
# 이 섹션은 `apply.py`·`patchplan.py`에서 주소·채널·FID **범위를 비교하는 모든 지점**을 표로
# 세우고, 각 표에 "행을 하나 지우면 실패하는" 전수 게이트를 붙인다(규율 3).
#
# 경계 지점 전수 — round16 조사 결과(같은 질문을 다음 라운드가 다시 하지 않도록 여기 남긴다):
#   1. `apply.py`  `planned.address < fixture.address <= planned.end_address`   → A절
#   2. `patchplan.py` `_spans_overlap`의 두 `<=` — **콘솔 점유** 경로            → B절
#   3. 같은 술어 — **계획 내부 겹침** 경로(형제 표면, 같은 표를 그대로 적용)      → B절
#   4. `patchplan.py` `_assign_fids`의 `next_fid > fid_range.end`               → C절
#   5. `patchplan.py` `_parse_fid_range`의 `end < start`                        → C절
#   6. `apply.py` `_fixtures_at`의 `fixture.address == address`                 → D절
#   7. `patchplan.py` 구간 산술 `target.address + footprint - 1`                → E절
#   8. `patchplan.py` `footprint <= 0`                                          → F절
#   9. **유니버스 끝(512) 경계는 이 파이프라인 어디에도 존재하지 않는다** — 무가드
#      경계다. E절이 그 사실을 못박는다(추측으로 메우지 않고 관측을 고정한다).


_BOUNDARY_PLAN_START = 8
_BOUNDARY_GRID_LAST = 20
_BOUNDARY_PLAN_WIDTHS = (5, 1)

_EXCLUDED_OCCUPIED = "excluded_occupied"
_KEPT_DISJOINT = "kept_disjoint"
_KEPT_FOR_IDEMPOTENCY = "kept_for_idempotency"
_KEPT_UNDETECTED_TAIL = "kept_undetected_tail"


def _span_relation(plan_start: int, plan_end: int, other_start: int, other_end: int) -> str:
    """계획 구간 `[a, e]`와 상대 구간 `[oa, oe]`의 관계를 **전수 분류**한다.

    총 함수다 — `oa <= oe`인 모든 조합이 정확히 하나의 이름으로 떨어진다. 이 분류가
    전수라는 사실 자체를 아래 격자 게이트가 프로덕션 호출로 확인한다.
    """
    a, e, oa, oe = plan_start, plan_end, other_start, other_end
    if oe < a - 1:
        return "disjoint_before"
    if oe == a - 1:
        return "abuts_before_plan_start"
    if oa < a:
        if oe == a:
            return "tail_end_equals_plan_start"
        if oe < e:
            return "tail_overlaps_into_plan"
        if oe == e:
            return "tail_covers_through_plan_end"
        return "other_encloses_plan"
    if oa == a:
        if oe < e:
            return "same_start_ends_inside"
        if oe == e:
            return "identical_span"
        return "same_start_extends_past_plan_end"
    if oa < e:
        if oe <= e:
            return "contained_strictly_inside_plan"
        return "starts_inside_extends_past_plan_end"
    if oa == e:
        return "start_equals_plan_end"
    if oa == e + 1:
        return "starts_one_after_plan_end"
    return "disjoint_after"


# ==========================================================================
# A절 — `screen_console_occupancy`의 중첩 판정 경계 (M61)
# ==========================================================================
#
# (관계 이름, 계획 폭, 기존 픽스처 시작, 기존 픽스처 **개념상** 끝, 처분)
#
# 프로덕션은 기존 픽스처의 폭을 읽을 수 없어(N04) 시작 주소 1채널로만 본다. 그래서 개념상
# 끝은 프로덕션이 **못 보는 값**이고, 표는 그 미검출을 `kept_undetected_tail`로 명시한다 —
# "무엇을 못 잡는지"를 표에 적어두지 않으면 다음 라운드가 그것을 통과로 오독한다.
_OCCUPANCY_BOUNDARY_ROWS = (
    ("disjoint_before", 5, 3, 5, _KEPT_DISJOINT),
    ("abuts_before_plan_start", 5, 5, 7, _KEPT_DISJOINT),
    ("tail_end_equals_plan_start", 5, 6, 8, _KEPT_UNDETECTED_TAIL),
    ("tail_overlaps_into_plan", 5, 6, 10, _KEPT_UNDETECTED_TAIL),
    ("tail_covers_through_plan_end", 5, 6, 12, _KEPT_UNDETECTED_TAIL),
    ("other_encloses_plan", 5, 6, 15, _KEPT_UNDETECTED_TAIL),
    ("same_start_ends_inside", 5, 8, 10, _KEPT_FOR_IDEMPOTENCY),
    ("identical_span", 5, 8, 12, _KEPT_FOR_IDEMPOTENCY),
    ("same_start_extends_past_plan_end", 5, 8, 15, _KEPT_FOR_IDEMPOTENCY),
    ("contained_strictly_inside_plan", 5, 9, 11, _EXCLUDED_OCCUPIED),
    ("starts_inside_extends_past_plan_end", 5, 11, 15, _EXCLUDED_OCCUPIED),
    # ↓ [round16 M61] 이 한 칸이 무대조군이었다. `<=`를 `<`로 바꾸면 계획 구간의 **마지막
    #   채널에서 시작하는** 기존 픽스처를 놓치고, 겹치는 항목이 전달물로 나간다.
    ("start_equals_plan_end", 5, 12, 12, _EXCLUDED_OCCUPIED),
    ("starts_one_after_plan_end", 5, 13, 14, _KEPT_DISJOINT),
    ("disjoint_after", 5, 16, 18, _KEPT_DISJOINT),
    # 1채널 폭 계획 — `a == e`라 중첩 판정 구간이 비어 있다(잡을 수 있는 칸이 없다).
    ("disjoint_before", 1, 3, 5, _KEPT_DISJOINT),
    ("abuts_before_plan_start", 1, 5, 7, _KEPT_DISJOINT),
    ("tail_end_equals_plan_start", 1, 6, 8, _KEPT_UNDETECTED_TAIL),
    ("other_encloses_plan", 1, 6, 15, _KEPT_UNDETECTED_TAIL),
    ("identical_span", 1, 8, 8, _KEPT_FOR_IDEMPOTENCY),
    ("same_start_extends_past_plan_end", 1, 8, 10, _KEPT_FOR_IDEMPOTENCY),
    ("starts_one_after_plan_end", 1, 9, 10, _KEPT_DISJOINT),
    ("disjoint_after", 1, 11, 13, _KEPT_DISJOINT),
)


def _boundary_plan(width: int, *, candidate_id: str = "a", universe: int = 1) -> AddressPlan:
    start = _BOUNDARY_PLAN_START
    return AddressPlan(
        entries=(
            AddressPlanEntry(
                candidate_id=candidate_id,
                universe=universe,
                address=start,
                footprint=width,
                end_address=start + width - 1,
            ),
        )
    )


def _run_occupancy(width: int, fixture_start: int, *, universe: int = 1) -> AddressPlan:
    """프로덕션 `screen_console_occupancy`를 그대로 호출한다 — 로컬 리터럴 대조가 아니다."""
    return screen_console_occupancy(
        (_candidate("a", 1, _BOUNDARY_PLAN_START, 101),),
        address_plan=_boundary_plan(width),
        console_fixtures=_console(
            _record(1, f"{universe}.{fixture_start}", "FixtureType 3", "1 Mode 1")
        ),
    )


@pytest.mark.parametrize(
    ("relation", "width", "fixture_start", "fixture_end", "disposition"),
    _OCCUPANCY_BOUNDARY_ROWS,
    ids=[f"{row[0]}-w{row[1]}" for row in _OCCUPANCY_BOUNDARY_ROWS],
)
def test_the_occupancy_screen_decides_every_span_boundary_as_the_table_declares(
    relation, width, fixture_start, fixture_end, disposition
):
    """계획 구간과 기존 픽스처 구간의 **모든 경계 관계**를 한 행씩 세우고 결과를 단정한다.

    [round16 M61] `apply.py`의 `planned.address < fixture.address <= planned.end_address`에서
    `<=`를 `<`로 바꾸면 `start_equals_plan_end` 행이 실패한다(제외돼야 할 항목이 `kept`에 남는다).
    같은 식의 `planned.address <`를 `<=`로 바꾸면 `same_start_*`·`identical_span` 세 행이
    실패한다 — 멱등 3분기로 가야 할 자기 자리가 점유로 뭉개진다.

    **비공허성**: 겹치지 않는 행은 실제로 `kept`에 남는지도 같은 표에서 단정한다. 그것이
    없으면 "무엇을 해도 막는다"를 통과로 읽는 공허 표가 된다.
    """
    start = _BOUNDARY_PLAN_START
    end = start + width - 1
    assert _span_relation(start, end, fixture_start, fixture_end) == relation
    truly_overlaps = fixture_start <= end and start <= fixture_end

    plan = _run_occupancy(width, fixture_start)

    if disposition == _EXCLUDED_OCCUPIED:
        assert truly_overlaps
        assert plan.entries == ()
        assert [x.code for x in plan.exclusions] == [ADDRESS_ALREADY_OCCUPIED]
        reason = plan.exclusions[0].reason
        assert f"주소 {start}~{end} 구간" in reason
        assert f"주소 {fixture_start})" in reason
        return

    # 비공허성 — 여기부터는 전부 "통과해서 kept에 남는다"를 실제로 확인한다.
    assert [entry.candidate_id for entry in plan.entries] == ["a"]
    assert plan.exclusions == ()

    if disposition == _KEPT_DISJOINT:
        assert not truly_overlaps
        return

    backstop = screen_idempotent(
        (_candidate("a", 1, start, 101),),
        address_plan=plan,
        resolutions=(_resolution("a"),),
        console_fixtures=_console(_record(1, f"1.{fixture_start}", "FixtureType 3", "1 Mode 1")),
    )

    if disposition == _KEPT_FOR_IDEMPOTENCY:
        # 자기 자리는 멱등 3분기가 받는다 — 여기서 점유로 잡으면 그 셋이 뭉개진다.
        assert fixture_start == start
        assert backstop.entries == ()
        assert [x.code for x in backstop.exclusions] == [ALREADY_PATCHED_IDENTICAL]
        return

    assert disposition == _KEPT_UNDETECTED_TAIL
    # [N04] 꼬리 방향 겹침은 **검출되지 않는다**. 백스톱도 없다 — 그 사실을 표에 못박고,
    # 대신 `existing_footprint_skipped_check`가 그것을 구조화해 보고하는지 확인한다.
    assert truly_overlaps and fixture_start < start
    assert [entry.candidate_id for entry in backstop.entries] == ["a"]
    check = existing_footprint_skipped_check()
    assert check["kind"] == EXISTING_FOOTPRINT_UNREADABLE
    assert "앞에서" in str(check["reason"]) and "검출되지 않는다" in str(check["reason"])


def test_the_occupancy_boundary_table_is_the_complete_classification_of_span_relations():
    """[규율 3 전단사] 표에서 행을 하나 지우면 격자와 어긋나 여기서 실패한다.

    기대 집합을 리터럴로 적지 않는다 — `oa <= oe`인 모든 구간을 격자로 훑어 관계 분류를
    돌리고, 그 위에서 **프로덕션 `screen_console_occupancy`를 실제로 호출**해 결과를 모은다.
    그래서 ① 표에 없는 관계가 생기면 실패하고 ② 격자에 없는 죽은 행이 있어도 실패하며
    ③ 관계 분류가 결과를 결정하지 못하면(같은 관계에서 결과가 갈리면) 실패한다.
    """
    excluded_by_start: dict[tuple[int, int], bool] = {}
    observed: dict[tuple[str, int], set[bool]] = {}
    for width in _BOUNDARY_PLAN_WIDTHS:
        start = _BOUNDARY_PLAN_START
        end = start + width - 1
        for other_start in range(1, _BOUNDARY_GRID_LAST + 1):
            key = (width, other_start)
            if key not in excluded_by_start:
                excluded_by_start[key] = _run_occupancy(width, other_start).entries == ()
            for other_end in range(other_start, _BOUNDARY_GRID_LAST + 1):
                relation = _span_relation(start, end, other_start, other_end)
                observed.setdefault((relation, width), set()).add(excluded_by_start[key])

    table = {(row[0], row[1]): row[4] for row in _OCCUPANCY_BOUNDARY_ROWS}
    assert len(table) == len(_OCCUPANCY_BOUNDARY_ROWS)
    assert set(table) == set(observed)
    for key, outcomes in sorted(observed.items()):
        assert outcomes == {table[key] == _EXCLUDED_OCCUPIED}, key
    assert {row[4] for row in _OCCUPANCY_BOUNDARY_ROWS} == {
        _EXCLUDED_OCCUPIED,
        _KEPT_DISJOINT,
        _KEPT_FOR_IDEMPOTENCY,
        _KEPT_UNDETECTED_TAIL,
    }


# ==========================================================================
# B절 — `plan_addresses`의 구간 겹침 판정 (`_spans_overlap`) · **형제 표면 둘 다**
# ==========================================================================
#
# 같은 술어가 두 표면에서 쓰인다: 콘솔 점유(`address_already_occupied`)와 계획 내부
# 겹침(`address_overlap_in_plan`). **한 표를 두 표면에 그대로 적용한다** — 한쪽에만
# 대조군을 붙이는 것이 여섯 라운드째 반복된 발생 기제다.
#
# (관계 이름, 계획 폭, 상대 구간 시작, 상대 구간 끝, 겹치는가)
_PLAN_SPAN_BOUNDARY_ROWS = (
    ("disjoint_before", 5, 3, 5, False),
    ("abuts_before_plan_start", 5, 5, 7, False),
    ("tail_end_equals_plan_start", 5, 6, 8, True),
    ("tail_overlaps_into_plan", 5, 6, 10, True),
    ("tail_covers_through_plan_end", 5, 6, 12, True),
    ("other_encloses_plan", 5, 6, 15, True),
    ("same_start_ends_inside", 5, 8, 10, True),
    ("identical_span", 5, 8, 12, True),
    ("same_start_extends_past_plan_end", 5, 8, 15, True),
    ("contained_strictly_inside_plan", 5, 9, 11, True),
    ("starts_inside_extends_past_plan_end", 5, 11, 15, True),
    ("start_equals_plan_end", 5, 12, 12, True),
    ("starts_one_after_plan_end", 5, 13, 14, False),
    ("disjoint_after", 5, 16, 18, False),
    ("disjoint_before", 1, 3, 5, False),
    ("abuts_before_plan_start", 1, 5, 7, False),
    ("tail_end_equals_plan_start", 1, 6, 8, True),
    ("other_encloses_plan", 1, 6, 15, True),
    ("identical_span", 1, 8, 8, True),
    ("same_start_extends_past_plan_end", 1, 8, 10, True),
    ("starts_one_after_plan_end", 1, 9, 10, False),
    ("disjoint_after", 1, 11, 13, False),
)


def _run_plan_against_console(width: int, other_start: int, other_end: int):
    from server.vwx.patchplan import plan_addresses

    target = _candidate("a", 1, _BOUNDARY_PLAN_START, 101)
    return plan_addresses(
        (target,),
        footprints={"a": width},
        occupied={1: ((other_start, other_end),)},
    )


def _run_plan_against_sibling_entry(width: int, other_start: int, other_end: int):
    """형제 표면 — 상대 구간이 **같은 계획 안의 다른 항목**일 때."""
    from server.vwx.patchplan import plan_addresses

    other = _candidate("z", 1, other_start, 100)
    target = _candidate("a", 1, _BOUNDARY_PLAN_START, 101)
    return plan_addresses(
        (other, target),
        footprints={"z": other_end - other_start + 1, "a": width},
        occupied={},
    )


@pytest.mark.parametrize(
    ("relation", "width", "other_start", "other_end", "overlaps"),
    _PLAN_SPAN_BOUNDARY_ROWS,
    ids=[f"{row[0]}-w{row[1]}" for row in _PLAN_SPAN_BOUNDARY_ROWS],
)
def test_plan_addresses_decides_every_span_boundary_on_both_sibling_surfaces(
    relation, width, other_start, other_end, overlaps
):
    """`_spans_overlap`의 두 `<=` 경계를 **콘솔 점유·계획 내부** 두 표면에서 같이 단정한다.

    [round16] `patchplan.py`의 `left[0] <= right[1]`을 `<`로 바꾸면
    `tail_end_equals_plan_start` 두 행이 실패한다. `right[0] <= left[1]`을 `<`로 바꾸면
    `start_equals_plan_end`·`identical_span`(폭 1) 행이 실패한다. 두 표면 어느 쪽만
    고쳐도 나머지 표면의 같은 행이 남아 잡는다.

    **비공허성**: 겹치지 않는 행은 두 표면 모두에서 실제로 계획에 남는지 단정한다.
    """
    from server.vwx.verdicts import ADDRESS_OVERLAP_IN_PLAN

    start = _BOUNDARY_PLAN_START
    end = start + width - 1
    assert _span_relation(start, end, other_start, other_end) == relation
    assert overlaps == (other_start <= end and start <= other_end)

    console_plan = _run_plan_against_console(width, other_start, other_end)
    sibling_plan = _run_plan_against_sibling_entry(width, other_start, other_end)

    if overlaps:
        assert [e.candidate_id for e in console_plan.entries] == []
        assert [x.code for x in console_plan.exclusions] == [ADDRESS_ALREADY_OCCUPIED]
        assert [e.candidate_id for e in sibling_plan.entries] == ["z"]
        assert [(x.candidate_id, x.code) for x in sibling_plan.exclusions] == [
            ("a", ADDRESS_OVERLAP_IN_PLAN)
        ]
        return

    entry = console_plan.entries[0]
    assert entry.candidate_id == "a"
    assert (entry.address, entry.end_address) == (start, end)
    assert console_plan.exclusions == ()
    assert [e.candidate_id for e in sibling_plan.entries] == ["z", "a"]
    assert sibling_plan.exclusions == ()


def test_the_plan_span_boundary_table_is_the_complete_classification_and_both_surfaces_agree():
    """[규율 3 전단사 + 형제 표면 동치] 행을 지우거나 한 표면만 고치면 여기서 실패한다."""
    from server.vwx.verdicts import ADDRESS_OVERLAP_IN_PLAN

    console_outcomes: dict[tuple[str, int], set[bool]] = {}
    sibling_outcomes: dict[tuple[str, int], set[bool]] = {}
    for width in _BOUNDARY_PLAN_WIDTHS:
        start = _BOUNDARY_PLAN_START
        end = start + width - 1
        for other_start in range(1, _BOUNDARY_GRID_LAST + 1):
            for other_end in range(other_start, _BOUNDARY_GRID_LAST + 1):
                relation = _span_relation(start, end, other_start, other_end)
                console = _run_plan_against_console(width, other_start, other_end)
                sibling = _run_plan_against_sibling_entry(width, other_start, other_end)
                console_blocked = [x.code for x in console.exclusions] == [ADDRESS_ALREADY_OCCUPIED]
                sibling_blocked = [x.code for x in sibling.exclusions] == [ADDRESS_OVERLAP_IN_PLAN]
                # 형제 표면 동치 — 같은 술어이므로 격자 전 칸에서 결론이 같아야 한다.
                assert console_blocked == sibling_blocked, (relation, width, other_start)
                console_outcomes.setdefault((relation, width), set()).add(console_blocked)
                sibling_outcomes.setdefault((relation, width), set()).add(sibling_blocked)

    table = {(row[0], row[1]): row[4] for row in _PLAN_SPAN_BOUNDARY_ROWS}
    assert len(table) == len(_PLAN_SPAN_BOUNDARY_ROWS)
    assert set(table) == set(console_outcomes) == set(sibling_outcomes)
    for key, expected in sorted(table.items()):
        assert console_outcomes[key] == {expected}, key
        assert sibling_outcomes[key] == {expected}, key


# ==========================================================================
# C절 — FID 범위 포함 경계 (`_assign_fids` · `_parse_fid_range`)
# ==========================================================================

_FID_RANGE_START = 100
_FID_RANGE_WIDTHS = (1, 2, 3)
_FID_TARGET_COUNTS = (1, 2, 3, 4)

# (범위 폭, 대상 수, 배정된 FID, 소진 제외 건수)
_FID_RANGE_BOUNDARY_ROWS = (
    (1, 1, (100,), 0),
    (1, 2, (100,), 1),
    (1, 3, (100,), 2),
    (1, 4, (100,), 3),
    (2, 1, (100,), 0),
    (2, 2, (100, 101), 0),
    (2, 3, (100, 101), 1),
    (2, 4, (100, 101), 2),
    (3, 1, (100,), 0),
    (3, 2, (100, 101), 0),
    (3, 3, (100, 101, 102), 0),
    (3, 4, (100, 101, 102), 1),
)


def _run_assign_fids(width: int, count: int, *, existing: frozenset[int] = frozenset()):
    from server.vwx.patchplan import FIDRange, _assign_fids

    targets = tuple(_candidate(f"t{i}", 1, 1 + i, 0) for i in range(count))
    return _assign_fids(
        targets,
        FIDRange(start=_FID_RANGE_START, end=_FID_RANGE_START + width - 1),
        existing_fids=existing,
        fid_range_visually_confirmed_empty=True,
    )


@pytest.mark.parametrize(
    ("width", "count", "assigned", "exhausted"),
    _FID_RANGE_BOUNDARY_ROWS,
    ids=[f"w{row[0]}-n{row[1]}" for row in _FID_RANGE_BOUNDARY_ROWS],
)
def test_the_fid_range_is_inclusive_on_both_ends_at_every_boundary(
    width, count, assigned, exhausted
):
    """FID 범위 `start`·`end`가 **양끝 포함**임을 모든 경계 조합에서 단정한다.

    [round16] `patchplan.py`의 `next_fid > fid_range.end`를 `>=`로 바꾸면 `w1-n1`·`w2-n2`·
    `w3-n3`(정확히 맞는 조합)이 실패한다 — 마지막 FID를 배정하지 못한다. `next_fid`의
    초기값 `fid_range.start`를 `start + 1`로 바꾸면 모든 행의 첫 배정값이 어긋난다.

    **비공허성**: 소진되지 않는 행은 실제로 배정이 이뤄지는지 단정한다.
    """
    from server.vwx.verdicts import FID_RANGE_EXHAUSTED

    planned, exclusions = _run_assign_fids(width, count)
    assert tuple(t.assigned_fid for t in planned) == assigned
    assert len(planned) == len(assigned)
    codes = [x.code for x in exclusions]
    assert codes == [FID_RANGE_EXHAUSTED] * exhausted
    for fid in assigned:
        assert _FID_RANGE_START <= fid <= _FID_RANGE_START + width - 1


def test_the_fid_range_boundary_table_covers_every_width_and_count_combination():
    """[규율 3 전단사] 행을 하나 지우면 격자 곱집합과 어긋나 실패한다."""
    keys = [(row[0], row[1]) for row in _FID_RANGE_BOUNDARY_ROWS]
    expected = {(w, n) for w in _FID_RANGE_WIDTHS for n in _FID_TARGET_COUNTS}
    assert len(keys) == len(set(keys)) == len(expected)
    assert set(keys) == expected
    # 격자를 프로덕션으로 실제 돌려 표의 기대값이 관측과 일치하는지 확인한다.
    for width, count, assigned, exhausted in _FID_RANGE_BOUNDARY_ROWS:
        planned, exclusions = _run_assign_fids(width, count)
        assert tuple(t.assigned_fid for t in planned) == assigned
        assert len(exclusions) == exhausted


# (이미 쓰인 FID의 위치 이름, 점유된 FID 집합)
_FID_TAKEN_ROWS = (
    ("none_taken", frozenset()),
    ("index_0_taken", frozenset({100})),
    ("index_1_taken", frozenset({101})),
    ("index_2_taken", frozenset({102})),
)


@pytest.mark.parametrize(
    ("position", "existing"), _FID_TAKEN_ROWS, ids=[r[0] for r in _FID_TAKEN_ROWS]
)
def test_an_existing_fid_is_refused_at_every_position_including_both_ends(position, existing):
    """범위의 **첫 칸·중간·마지막 칸** 모두에서 기존 FID가 거부되는지 단독 행으로 세운다.

    [round16] `proposed_fid in existing_fids`를 위치 의존적으로 좁히면(예: 첫 칸만 검사)
    `index_2_taken` 행이 실패한다 — 범위 끝의 충돌이 조용히 통과한다.
    """
    from server.vwx.verdicts import FID_ALREADY_IN_USE

    planned, exclusions = _run_assign_fids(3, 3, existing=existing)
    refused = {x.proposed_fid for x in exclusions if x.code == FID_ALREADY_IN_USE}
    assert refused == set(existing)
    assert {t.assigned_fid for t in planned} == {100, 101, 102} - set(existing)


def test_the_fid_taken_position_table_covers_every_slot_of_the_range():
    """[규율 3 전단사] 범위 폭 3의 **모든 칸**과 '점유 없음'이 표에 있어야 한다."""
    names = [row[0] for row in _FID_TAKEN_ROWS]
    expected = {"none_taken", *(f"index_{i}_taken" for i in range(3))}
    assert len(names) == len(set(names)) == len(expected)
    assert set(names) == expected


# (start 대비 end 오프셋, 유효한가)
_FID_RANGE_PARSE_ROWS = ((-1, False), (0, True), (1, True))


@pytest.mark.parametrize(
    ("offset", "valid"),
    _FID_RANGE_PARSE_ROWS,
    ids=["end_below_start", "end_equals_start", "end_above_start"],
)
def test_the_fid_range_parser_accepts_a_single_slot_and_refuses_only_an_inverted_range(
    offset, valid
):
    """`end == start`(1칸 범위)는 **유효**하다 — 그 경계를 단독 행으로 세운다.

    [round16] `patchplan.py`의 `end < start`를 `end <= start`로 바꾸면 `end_equals_start`
    행이 실패한다.

    [round18 R18-A] `_parse_fid_range`가 `FIDRange | None` 대신 `_FidRangeParse`를
    돌려주도록 바뀌었다 — 결함 사유를 축별로 갈라 싣기 위해서다. 이 행이 재는
    **순서 경계**는 그대로이므로 값 접근만 `.parsed`로 옮긴다.
    """
    from server.vwx.patchplan import _parse_fid_range

    parsed = _parse_fid_range({"start": 100, "end": 100 + offset}).parsed
    if valid:
        assert parsed is not None
        assert (parsed.start, parsed.end) == (100, 100 + offset)
    else:
        assert parsed is None


def test_the_fid_range_parse_table_covers_the_whole_neighbourhood_of_the_boundary():
    """[규율 3 전단사] 경계 좌우 한 칸씩이 모두 표에 있어야 한다."""
    offsets = [row[0] for row in _FID_RANGE_PARSE_ROWS]
    assert len(offsets) == len(set(offsets)) == 3
    assert set(offsets) == {-1, 0, 1}


# ==========================================================================
# D절 — `screen_idempotent`의 주소 일치 판정 (`_fixtures_at`)
# ==========================================================================

_IDEMPOTENT_PLAN_WIDTH = 5
_IDEMPOTENT_GRID_UNIVERSES = (1, 2)
_IDEMPOTENT_GRID_ADDRESSES = tuple(range(6, 15))


def _idempotency_cell(universe: int, address: int, plan_start: int, plan_end: int) -> str:
    if universe != 1:
        return "other_universe"
    if address < plan_start:
        return "below_plan_start"
    if address == plan_start:
        return "equals_plan_start"
    if address < plan_end:
        return "inside_plan_span"
    if address == plan_end:
        return "equals_plan_end"
    return "after_plan_end"


# (칸 이름, 유니버스, 주소, 멱등 판정이 잡는가)
_IDEMPOTENT_ADDRESS_ROWS = (
    ("below_plan_start", 1, 7, False),
    ("equals_plan_start", 1, 8, True),
    ("inside_plan_span", 1, 9, False),
    # ↓ [round16 M61 백스톱 부재] 계획 **끝** 칸은 멱등 판정이 보지 않는다. 그래서 A절의
    #   중첩 판정이 유일한 방어선이고, 그 한 칸에 대조군이 없던 것이 M61이었다.
    ("equals_plan_end", 1, 12, False),
    ("after_plan_end", 1, 13, False),
    ("other_universe", 2, 8, False),
)


def _run_idempotent_at(universe: int, address: int) -> AddressPlan:
    return screen_idempotent(
        (_candidate("a", 1, _BOUNDARY_PLAN_START, 101),),
        address_plan=_boundary_plan(_IDEMPOTENT_PLAN_WIDTH),
        resolutions=(_resolution("a"),),
        console_fixtures=_console(_record(1, f"{universe}.{address}", "FixtureType 3", "1 Mode 1")),
    )


@pytest.mark.parametrize(
    ("cell", "universe", "address", "caught"),
    _IDEMPOTENT_ADDRESS_ROWS,
    ids=[row[0] for row in _IDEMPOTENT_ADDRESS_ROWS],
)
def test_the_idempotency_screen_matches_the_start_address_exactly_and_nothing_else(
    cell, universe, address, caught
):
    """멱등 판정은 **시작 주소 정확 일치**만 본다 — 그 경계를 칸마다 단독 행으로 세운다.

    [round16] `_fixtures_at`의 `fixture.address == address`를 `>=`나 `<=`로 넓히면
    `inside_plan_span`·`below_plan_start` 행이 실패하고, `fixture.universe == universe`를
    지우면 `other_universe` 행이 실패한다.

    **비공허성**: 잡히지 않는 칸은 실제로 계획에 남는지 단정한다.
    """
    start = _BOUNDARY_PLAN_START
    end = start + _IDEMPOTENT_PLAN_WIDTH - 1
    assert _idempotency_cell(universe, address, start, end) == cell

    plan = _run_idempotent_at(universe, address)
    if caught:
        assert plan.entries == ()
        assert [x.code for x in plan.exclusions] == [ALREADY_PATCHED_IDENTICAL]
    else:
        assert [entry.candidate_id for entry in plan.entries] == ["a"]
        assert plan.exclusions == ()


def test_the_idempotency_address_table_covers_every_cell_around_the_planned_span():
    """[규율 3 전단사] 행을 하나 지우면 격자 분류와 어긋나 실패한다 — 프로덕션 호출로 확인한다."""
    start = _BOUNDARY_PLAN_START
    end = start + _IDEMPOTENT_PLAN_WIDTH - 1
    observed: dict[str, set[bool]] = {}
    for universe in _IDEMPOTENT_GRID_UNIVERSES:
        for address in _IDEMPOTENT_GRID_ADDRESSES:
            cell = _idempotency_cell(universe, address, start, end)
            plan = _run_idempotent_at(universe, address)
            observed.setdefault(cell, set()).add(plan.entries == ())

    table = {row[0]: row[3] for row in _IDEMPOTENT_ADDRESS_ROWS}
    assert len(table) == len(_IDEMPOTENT_ADDRESS_ROWS)
    assert set(table) == set(observed)
    for cell, outcomes in sorted(observed.items()):
        assert outcomes == {table[cell]}, cell


# ==========================================================================
# E절 — 구간 산술과 **무가드** 유니버스 끝 경계
# ==========================================================================


def test_the_planned_span_is_exactly_start_plus_footprint_minus_one():
    """[round16] `target.address + footprint - 1`에서 `- 1`을 빼거나 `+ 1`로 바꾸면 실패한다.

    격자로 폭 1~20을 전수한다 — 폭 1(시작==끝)이 그 산술의 경계다.
    """
    from server.vwx.patchplan import plan_addresses

    for footprint in range(1, 21):
        plan = plan_addresses(
            (_candidate("a", 1, 100, 101),), footprints={"a": footprint}, occupied={}
        )
        (entry,) = plan.entries
        assert (entry.footprint, entry.address, entry.end_address) == (
            footprint,
            100,
            100 + footprint - 1,
        )


# (이름, 주소, 점유폭, 계산될 끝 주소)
_UNIVERSE_END_ROWS = (
    ("ends_one_below_512", 496, 16, 511),
    ("ends_exactly_at_512", 497, 16, 512),
    ("ends_one_past_512", 498, 16, 513),
    ("single_channel_at_512", 512, 1, 512),
    ("single_channel_past_512", 512, 2, 513),
)


@pytest.mark.parametrize(
    ("name", "address", "footprint", "end_address"),
    _UNIVERSE_END_ROWS,
    ids=[row[0] for row in _UNIVERSE_END_ROWS],
)
def test_the_universe_end_is_an_unguarded_boundary_and_this_pins_that_fact(
    name, address, footprint, end_address
):
    """**유니버스 끝(512) 경계는 이 파이프라인에 존재하지 않는다** — 관측을 고정한다.

    `plan_addresses`도, `screen_*`도, 어휘표(`target_exclusion_reason`)도 "유니버스 끝을
    넘었다"를 표현하지 않는다. 즉 512를 넘는 구간이 **그대로 계획되어 전달물로 나간다.**
    추측으로 프로덕션을 바꾸지 않고, 그 사실을 여기 못박아 다음 라운드가 "무가드인지
    몰랐다"고 말할 수 없게 한다.

    가드를 넣기로 결정하면 `ends_one_past_512`·`single_channel_past_512` 두 행이 실패한다 —
    그때 **의식적으로** 이 표를 고쳐야 한다(조용한 통과가 아니라 강제 재결정).
    """
    from server.vwx.patchplan import plan_addresses

    plan = plan_addresses(
        (_candidate("a", 1, address, 101),), footprints={"a": footprint}, occupied={}
    )
    (entry,) = plan.entries
    assert entry.end_address == end_address
    assert plan.exclusions == ()


def test_no_closed_vocabulary_code_expresses_a_universe_end_violation():
    """무가드라는 진단의 **근거** — 어휘표에 그런 코드 자체가 없다(형제 표면 전수 확인)."""
    from server.vwx.verdicts import AUTOPATCH_CLOSED_VOCABULARIES

    every_code = {code for codes in AUTOPATCH_CLOSED_VOCABULARIES.values() for code in codes}
    assert every_code
    assert not [
        code for code in every_code if "universe" in code and ("end" in code or "over" in code)
    ]


def test_the_universe_end_row_table_covers_both_sides_of_512_on_both_widths():
    """[규율 3 전단사] 경계 좌우와 1채널 폭이 모두 표에 있어야 한다."""
    names = [row[0] for row in _UNIVERSE_END_ROWS]
    assert len(names) == len(set(names)) == 5
    assert {row[3] > 512 for row in _UNIVERSE_END_ROWS} == {True, False}
    assert {row[2] == 1 for row in _UNIVERSE_END_ROWS} == {True, False}
    assert 512 in {row[3] for row in _UNIVERSE_END_ROWS}


# ==========================================================================
# F절 — 점유폭 유효성 경계 (`footprint <= 0`)
# ==========================================================================

# (이름, footprints 매핑에 들어갈 값, 계획에 남는가)
_FOOTPRINT_BOUNDARY_ROWS = (
    ("minus_one", -1, False),
    ("zero", 0, False),
    ("one", 1, True),
    ("two", 2, True),
    ("missing", None, False),
    ("boolean_true", True, False),
    ("string_sixteen", "16", False),
    ("float_sixteen", 16.0, False),
)


@pytest.mark.parametrize(
    ("name", "value", "planned"),
    _FOOTPRINT_BOUNDARY_ROWS,
    ids=[row[0] for row in _FOOTPRINT_BOUNDARY_ROWS],
)
def test_the_footprint_validity_boundary_is_exactly_one_channel(name, value, planned):
    """점유폭 경계는 **1채널**이다 — 0과 1을 단독 행으로 나란히 세운다.

    [round16] `footprint <= 0`을 `< 0`으로 바꾸면 `zero` 행이 실패한다(폭 0짜리 구간이
    계획된다). `isinstance(footprint, bool)` 가드를 지우면 `boolean_true` 행이 실패한다.

    **비공허성**: 유효한 폭은 실제로 계획에 남는지 단정한다.
    """
    from server.vwx.patchplan import plan_addresses
    from server.vwx.verdicts import FOOTPRINT_UNKNOWN

    plan = plan_addresses((_candidate("a", 1, 10, 101),), footprints={"a": value}, occupied={})
    if planned:
        (entry,) = plan.entries
        assert (entry.footprint, entry.end_address) == (value, 10 + value - 1)
        assert plan.exclusions == ()
    else:
        assert plan.entries == ()
        assert [x.code for x in plan.exclusions] == [FOOTPRINT_UNKNOWN]


def test_the_footprint_boundary_table_covers_the_neighbourhood_and_every_wrong_type():
    """[규율 3 전단사] 경계 좌우 두 칸씩과 **거부되어야 할 타입 전부**가 표에 있어야 한다."""
    names = [row[0] for row in _FOOTPRINT_BOUNDARY_ROWS]
    assert len(names) == len(set(names)) == len(_FOOTPRINT_BOUNDARY_ROWS)
    integers = {row[1] for row in _FOOTPRINT_BOUNDARY_ROWS if type(row[1]) is int}
    assert integers == {-1, 0, 1, 2}
    non_integer_types = {
        type(row[1]).__name__ for row in _FOOTPRINT_BOUNDARY_ROWS if type(row[1]) is not int
    }
    assert non_integer_types == {"NoneType", "bool", "str", "float"}


# ==========================================================================
# G절 — **프로덕션 선별 순서**에서의 경계 (tools.py: 멱등 → 점유)
# ==========================================================================
#
# `server/orchestrator/tools.py`는 `plan_addresses(occupied={})` → `screen_console_read`
# → `screen_idempotent` → `screen_console_occupancy` 순으로 돌린다. 즉 **계획 구간의
# 마지막 채널에서 시작하는 기존 픽스처**를 막는 방어선은 `screen_console_occupancy`
# **하나뿐**이다 — 멱등 판정은 시작 주소만 보므로 그 칸을 통과시킨다(D절 `equals_plan_end`).
# M61이 치명이었던 이유가 이것이므로, 단위 표와 별도로 **그 순서 그대로** 한 번 더 세운다.

_PIPELINE_ORDER_ROWS = (
    ("intruder_at_plan_start", 8, True, False),
    ("intruder_inside_plan", 10, False, True),
    ("intruder_at_plan_end", 12, False, True),
    ("intruder_one_after_plan_end", 13, False, False),
)


@pytest.mark.parametrize(
    ("name", "fixture_address", "caught_by_idempotency", "caught_by_occupancy"),
    _PIPELINE_ORDER_ROWS,
    ids=[row[0] for row in _PIPELINE_ORDER_ROWS],
)
def test_the_production_screen_order_still_stops_every_intruder_at_the_span_boundary(
    name, fixture_address, caught_by_idempotency, caught_by_occupancy
):
    """[round16 M61] 프로덕션 순서(멱등 → 점유)에서 어느 방어선이 잡는지를 칸마다 세운다.

    `apply.py`의 `<= planned.end_address`를 `< planned.end_address`로 바꾸면
    `intruder_at_plan_end` 행이 실패한다 — 멱등도 점유도 잡지 않아 **겹치는 픽스처가
    그대로 전달물로 나간다**(적대 감사 실증과 같은 형태).

    **비공허성**: 아무도 잡지 않아야 하는 행은 실제로 계획에 남는지 단정한다.
    """
    targets = (_candidate("a", 1, _BOUNDARY_PLAN_START, 101),)
    console = _console(_record(1, f"1.{fixture_address}", "FixtureType 3", "1 Mode 1"))
    plan = _boundary_plan(5)

    after_idempotency = screen_idempotent(
        targets, address_plan=plan, resolutions=(_resolution("a"),), console_fixtures=console
    )
    assert (after_idempotency.entries == ()) is caught_by_idempotency

    after_occupancy = screen_console_occupancy(
        targets, address_plan=after_idempotency, console_fixtures=console
    )
    stopped = after_occupancy.entries == ()
    assert stopped is (caught_by_idempotency or caught_by_occupancy)
    if caught_by_occupancy:
        assert [x.code for x in after_occupancy.exclusions] == [ADDRESS_ALREADY_OCCUPIED]
    if not stopped:
        assert [entry.candidate_id for entry in after_occupancy.entries] == ["a"]
        assert after_occupancy.exclusions == ()


def test_the_pipeline_order_table_covers_every_defence_line_around_the_span():
    """[규율 3 전단사] 계획 시작·내부·끝·끝 다음 네 칸이 모두 있어야 하고, **두 방어선이
    각각 최소 한 칸씩** 담당해야 한다 — 한쪽 방어선의 행만 남기면 여기서 실패한다."""
    names = [row[0] for row in _PIPELINE_ORDER_ROWS]
    assert len(names) == len(set(names)) == 4
    start = _BOUNDARY_PLAN_START
    assert [row[1] for row in _PIPELINE_ORDER_ROWS] == [start, start + 2, start + 4, start + 5]
    assert {row[2] for row in _PIPELINE_ORDER_ROWS} == {True, False}
    assert {row[3] for row in _PIPELINE_ORDER_ROWS} == {True, False}
    assert [row for row in _PIPELINE_ORDER_ROWS if not row[2] and not row[3]]


# --- round16 형제 필드·형제 사이트 (SiblingFields) ---
#
# 여섯 라운드 연속 같은 기제로 FAIL했다: **어떤 규율을 적용하고 형제 표면에는 적용하지
# 않는다.** round15 D도 같았다 — 표시 문자열 규율을 `screen_idempotent`의 한 갈래와
# `verify_patch`에만 붙이고, 같은 함수의 형제 갈래 셋과 두 객체의 형제 필드 둘을 빠뜨렸다.
# 이 절은 그 도달 범위를 **프로덕션에서 파생해** 고정한다. 손으로 쓴 표가 프로덕션 AST와
# 전단사여야 하므로, 행을 지우면 실패하고 프로덕션에 갈래·사이트를 더해도 실패한다.


def _r16_apply_tree():
    import ast

    return ast.parse(APPLY_SOURCE)


def _r16_function_def(tree, name: str):
    import ast

    return next(
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name
    )


def _r16_in_source_order(nodes):
    return sorted(nodes, key=lambda node: (node.lineno, node.col_offset))


def _r16_apply_constant(name: str):
    """`apply.py`가 실제로 참조하는 이름을 **프로덕션 모듈에서** 값으로 환원한다."""
    import server.vwx.apply as production_apply

    return getattr(production_apply, name)


# ==========================================================================
# M35 → [round17 S17-03a] 관측 원문은 **2객체 × 단수 2칸**이 아니라
#        **2객체 × 점유자 리스트 1칸**이다
#
# round15 D는 단수 네 칸을 만들고 두 칸만 단정했다. round16 M35가 네 칸을 표로 고정해
# 그 구멍을 닫았지만, **표가 고정한 대상 자체가 틀렸다** — 단수 쌍은 N>=2를 구조적으로
# 표현할 수 없으므로 다중 점유 갈래는 "채우지 않는다"가 정답인 **영구 면제**로 남았고,
# 그 갈래의 payload에는 무엇이 점유했는지가 없었다. 리스트 한 칸으로 바꾸면 0·1·N이
# 전부 값이라 면제가 사라진다.
#
# 표는 지우지 않고 **교체**한다. 아래 전단사가 "두 dataclass에서 `observed_`로 시작하는
# 필드 전수"를 프로덕션에서 뽑아 표와 맞추므로 ① 단수 필드를 되살리면 실패하고
# ② 표에서 칸을 지우면 실패한다.
# ==========================================================================

#: (객체 이름, 필드 이름, 칸 종류) — 손으로 열거한다. 아래 전단사 단정이 프로덕션과 맞춘다.
#: 두 종류가 있고 **둘 다 단정한다** — round15가 네 칸 중 둘만 단정해 통과시킨 게 이 SPEC의
#: 선례다. `resolved_name`은 라이브러리로 **확정된 이름**이라 대조 실패 시 `None`이어야 하고
#: (미확정을 이름처럼 흘려보내지 않는다), `occupants`는 콘솔이 실제로 준 것을 전부 싣는다.
_R16_DISPLAY_CELLS = (
    ("PatchTargetExclusion", "observed_occupants", "occupants"),
    ("VerificationResult", "observed_type", "resolved_name"),
    ("VerificationResult", "observed_mode", "resolved_name"),
    ("VerificationResult", "observed_occupants", "occupants"),
)

#: 점유자 한 명이 payload로 나갈 때의 **키 전수**. `ConsoleFixture.to_dict()`와 전단사다.
_R17_OCCUPANT_KEYS = (
    "slot",
    "universe",
    "address",
    "type_display",
    "mode_display",
    "type_name",
    "mode_name",
    "identity_resolved",
)


def _r16_display_carrying_classes():
    from server.vwx.apply import VerificationResult
    from server.vwx.patchplan import PatchTargetExclusion

    return (PatchTargetExclusion, VerificationResult)


def test_the_display_cell_table_is_a_bijection_onto_the_production_dataclass_fields():
    """[round16 M35 · round17 S17-03a] 관측 칸 표가 **프로덕션 필드 목록**과 1:1이다.

    `observed_`로 시작하는 필드를 어느 쪽에서든 지우거나 더하면 깨진다 — 단수
    `observed_type_display`/`observed_mode_display`를 되살리는 것도 '더하기'라 깨진다.
    표에서 칸을 지워도 깨진다.
    """
    import dataclasses

    produced = tuple(
        (
            cls.__name__,
            field.name,
            "occupants" if field.name.endswith("occupants") else "resolved_name",
        )
        for cls in _r16_display_carrying_classes()
        for field in dataclasses.fields(cls)
        if field.name.startswith("observed_")
    )
    assert produced == _R16_DISPLAY_CELLS


def test_the_occupant_key_table_is_a_bijection_onto_console_fixture_to_dict():
    """[round17 S17-03a] 점유자 payload의 키 표가 `ConsoleFixture.to_dict()`와 1:1이다.

    [round17 #S17-03a] `ConsoleFixture.to_dict()`에서 키를 하나(예: `slot`) 지우면 실패한다.
    표에서 행을 지워도 실패한다 — 어느 방향으로도 조용히 줄어들지 않는다.
    """
    from server.vwx.apply import ConsoleFixture

    produced = ConsoleFixture(
        slot=1,
        universe=1,
        address=1,
        type_display="CD 5",
        mode_display="9 Mode 9",
        type_name=None,
        mode_name=None,
    ).to_dict()
    assert tuple(produced) == _R17_OCCUPANT_KEYS


def test_every_display_cell_is_also_a_key_of_its_objects_payload():
    """[round16 M35] 두 칸 전부가 `to_dict()` **키로** 나간다 — 객체 필드만으로는 부족하다.

    `patchplan.py`의 `"observed_occupants": …` 줄을 지우면 (필드는 남아 있으므로 위 전단사는
    통과하는데) 이 단정이 실패한다.
    """
    payload_keys = {
        "PatchTargetExclusion": set(_cd_occupied_handoff().exclusions[0].to_dict()),
        "VerificationResult": set(
            verify_patch(
                (_entry("a", 1, 1),),
                console_fixtures=_console(_record(1, "1.1", "CD 5", "9 Mode 9")),
            )
            .results[0]
            .to_dict()
        ),
    }
    for class_name, field_name, _kind in _R16_DISPLAY_CELLS:
        assert field_name in payload_keys[class_name], (class_name, field_name)


def _r16_display_cell_objects():
    """두 칸을 **같은 관측**(`'CD 5'` · `'9 Mode 9'`)으로 채우는 두 프로덕션 산출물."""
    exclusion = _cd_occupied_handoff().exclusions[0]
    result = verify_patch(
        (_entry("a", 1, 1),),
        console_fixtures=_console(_record(1, "1.1", "CD 5", "9 Mode 9")),
    ).results[0]
    return {"PatchTargetExclusion": exclusion, "VerificationResult": result}


@pytest.mark.parametrize(
    "class_name,field_name,kind",
    _R16_DISPLAY_CELLS,
    ids=[f"{cls}.{field}" for cls, field, _ in _R16_DISPLAY_CELLS],
)
def test_each_display_cell_carries_the_observed_string_in_object_and_in_payload(
    class_name: str, field_name: str, kind: str
):
    """[round16 M35 · round17 S17-03a] **네 칸 전부**를 단정한다 — 종류별로 다른 규약이다.

    round15는 네 칸을 만들고 둘만 단정했다. 여기서는 표가 프로덕션 필드와 전단사이고
    표의 모든 행이 이 parametrize를 통과하므로 조용한 면제 칸이 남지 않는다.

    [round17 #S17-03a] `patchplan.py`/`apply.py`의 `"observed_occupants": …` payload 줄을
      지우거나 `[]`로 고정하면 `occupants` 두 행이 실패한다.
    [round17 #S17-03a] `ConsoleFixture.to_dict()`에서 키를 하나 지우면 같은 두 행이 실패한다.
    """
    obj = _r16_display_cell_objects()[class_name]
    value = getattr(obj, field_name)
    sentence = getattr(obj, "reason", None) or obj.detail

    if kind == "occupants":
        assert [occupant["type_display"] for occupant in value] == ["CD 5"]
        assert [occupant["mode_display"] for occupant in value] == ["9 Mode 9"]
        assert [tuple(occupant) for occupant in value] == [_R17_OCCUPANT_KEYS]
        assert obj.to_dict()[field_name] == [dict(occupant) for occupant in value]
    else:
        # 라이브러리 대조에 실패한 관측이다 — **확정 이름 칸은 비어 있어야** 한다.
        # 여기에 표시 문자열을 흘려 넣으면 미확정이 이름으로 둔갑한다.
        assert value is None
        assert obj.to_dict()[field_name] is None

    assert "CD 5" not in sentence
    assert "9 Mode 9" not in sentence
    # [round17 S17-03b] 포인터 문장도 없다 — payload의 키 이름이 곧 포인터다.
    assert "필드에 있다" not in sentence


# ==========================================================================
# S16-05 — 갈래 규약은 `screen_idempotent`·`verify_patch`의 **모든 갈래**에 같다
#
# 규약(§0 2b④ + 2c①):
#   ① 사유·detail **문장**에 점유자에게서 읽은 문자열을 넣지 않는다 — 표시 원문이든
#      라이브러리 확정 이름이든. 문장에 들어가도 되는 것은 좌표와 **우리가 승인한 값**뿐.
#   ② 단일 점유자를 특정한 갈래는 관측 원문을 `observed_*_display`로 **반드시** 싣는다.
# round15는 ①②를 두 갈래에만 붙였다. `ADDRESS_CONFLICTS_WITH_EXISTING`은 점유자 이름을
# 문장에 f-string으로 박고 구조화 필드를 `None`으로 남겼다 — 같은 payload 안에서 두 갈래가
# 정반대 규약을 쓰는 상태였고, 점유자 타입이 `'CD 5'`면 스캐너가 거짓 양성을 냈다(실측).
# ==========================================================================

#: 우리가 승인한 정체. 점유자 표시 원문(`FixtureType 3` · `2 Mode 2`)과 **다른 문자열**이라
#: "문장에 표시 원문이 없다"와 "문장에 우리 값이 있다"를 서로 구별할 수 있다.
_R16_LED_DISPLAY = "FixtureType 3"
_R16_MODE1_DISPLAY = "1 Mode 1"
_R16_MODE2_DISPLAY = "2 Mode 2"


def _r16_unresolved_resolution(candidate_id: str = "a"):
    """우리 쪽 타입·모드가 미확정인 해석 — `TYPE_CONFIRMATION_PENDING` 갈래를 연다."""
    return TypeResolution(
        request=TypeRequest(candidate_id=candidate_id, instrument_type=LED),
        status=TYPE_NEEDS_CONFIRMATION,
        reason="",
        console_type=None,
        console_mode=None,
    )


def _r16_screen(records, *, resolutions=None):
    """`screen_idempotent`를 후보 1건 · 계획 1건으로 돌린다."""
    return _screen(
        console=_console(*records),
        targets=(_candidate("a", 1, 1, 101),),
        plan=AddressPlan(entries=(_planned("a", 1, 1),)),
        resolutions=resolutions,
    )


# (행 이름, 기대 코드 또는 None, 점유 기록, 해석 override, **기대 점유자 수**,
#  문장에 **우리가 승인한** 이름이 실리는가)
#
# [round17 S17-03a] 다섯째 열은 round16의 `fills_display`를 **교체한 것**이다. 그 열은
# `multiple_occupants` 행에 `False`를 정답으로 고정했다 — 단수 필드 `observed_type_display`
# 한 칸에 2대를 넣을 수 없으니 당시엔 사실이었지만, 동시에 **가장 위험한 갈래가 점유자를
# 하나도 싣지 않는 것을 규약이 승인**하는 열이었다. 계수 열에는 그런 면제가 없다.
_R16_SCREEN_BRANCH_ROWS = (
    ("no_occupant", None, (), None, 0, False),
    (
        "multiple_occupants",
        EXISTING_IDENTITY_UNCONFIRMED,
        (
            (1, "1.1", _R16_LED_DISPLAY, _R16_MODE1_DISPLAY),
            (2, "1.1", _R16_LED_DISPLAY, _R16_MODE1_DISPLAY),
        ),
        None,
        2,
        False,
    ),
    (
        "type_confirmation_pending",
        TYPE_CONFIRMATION_PENDING,
        ((1, "1.1", _R16_LED_DISPLAY, _R16_MODE1_DISPLAY),),
        "unresolved",
        1,
        False,
    ),
    (
        "existing_identity_unconfirmed",
        EXISTING_IDENTITY_UNCONFIRMED,
        ((1, "1.1", "CD 5", "9 Mode 9"),),
        None,
        1,
        False,
    ),
    (
        "already_patched_identical",
        ALREADY_PATCHED_IDENTICAL,
        ((1, "1.1", _R16_LED_DISPLAY, _R16_MODE1_DISPLAY),),
        None,
        1,
        True,
    ),
    (
        "address_conflicts_with_existing",
        ADDRESS_CONFLICTS_WITH_EXISTING,
        ((1, "1.1", _R16_LED_DISPLAY, _R16_MODE2_DISPLAY),),
        None,
        1,
        False,
    ),
)

#: [round19 major#4] `screen_idempotent`의 미확정 갈래가 코드를 담는 지역 이름 -> 그 갈래의
#: 표 시나리오(해상 결과가 `needs_confirmation`)가 내는 코드. **리터럴**이라 자기 비교가 아니다.
_R19_SCREEN_DERIVED_CODE_VALUES = {"unresolved_code": "type_confirmation_pending"}


def _r16_production_exclusion_sites():
    """`screen_idempotent` 본문의 `_exclusion(...)` 호출을 **소스 순서대로** 뽑는다.

    각 사이트에서 (제외 코드, 점유자를 구조화 필드로 넘기는가)를 읽는다 — 표와 맞춰야 하는
    프로덕션 쪽 사실이 바로 이것이다.
    """
    import ast

    fn = _r16_function_def(_r16_apply_tree(), "screen_idempotent")
    calls = _r16_in_source_order(
        node
        for node in ast.walk(fn)
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "_exclusion"
    )
    return tuple(
        (
            # 이름이 아니라 **값**으로 환원한다 — 상수 이름만 바꾼 뮤테이션이 표를
            # 통과하지 못하게 하려면 프로덕션 모듈에서 실제 값을 꺼내야 한다.
            # [round19 major#4] 미확정 갈래는 코드를 모듈 상수가 아니라 공유 번역기
            # `_unresolved_type_verdict`에서 받는다 — 그 지역 이름은 리터럴 표로 환원한다.
            _R19_SCREEN_DERIVED_CODE_VALUES.get(call.args[1].id)
            or _r16_apply_constant(call.args[1].id),
            any(keyword.arg == "observed_occupants" for keyword in call.keywords),
        )
        for call in calls
    )


def test_the_screen_branch_table_is_a_bijection_onto_the_production_exclusion_sites():
    """[round16 S16-05 · round17 S17-03a] 갈래 표가 **실제 제외 사이트**와 1:1이다.

    ① 표에서 갈래 행을 지우면 실패한다. ② 프로덕션에 갈래를 더하면 행 없이는 통과하지
    못한다. ③ **어느 갈래에서든** `observed_occupants=`를 떼면 두 번째 열이 어긋나 실패한다.

    round16 판은 `fills_display`를 그대로 두 번째 열로 썼고 `multiple_occupants` 행이
    `False`였다 — 그래서 그 갈래는 애초에 필드를 넘기지 않는 것이 정답이었다. 제외 사이트는
    **전부** 점유자를 관측한 자리이므로 예외가 없다.
    """
    table = tuple(
        (code, count >= 1)
        for _, code, _, _, count, _ in _R16_SCREEN_BRANCH_ROWS
        if code is not None
    )
    assert table == _r16_production_exclusion_sites()


def test_the_screen_branch_table_covers_the_single_kept_branch_too():
    """[round16 S16-05] 제외하지 않는 갈래(`kept.append`)도 표에 있다 — 전수의 나머지 한 칸.

    프로덕션의 `kept.append(planned)` 호출 수와 표의 `code is None` 행 수가 같아야 한다.
    `no_occupant` 행을 지우면 이 단정이 실패한다.
    """
    import ast

    fn = _r16_function_def(_r16_apply_tree(), "screen_idempotent")
    kept_appends = [
        node
        for node in ast.walk(fn)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "append"
        and getattr(node.func.value, "id", None) == "kept"
    ]
    assert len(kept_appends) == len([row for row in _R16_SCREEN_BRANCH_ROWS if row[1] is None])


@pytest.mark.parametrize(
    "name,code,records,resolution_kind,expected_occupant_count,approved_names_in_sentence",
    _R16_SCREEN_BRANCH_ROWS,
    ids=[row[0] for row in _R16_SCREEN_BRANCH_ROWS],
)
def test_every_screen_idempotent_branch_obeys_the_same_display_contract(
    name, code, records, resolution_kind, expected_occupant_count, approved_names_in_sentence
):
    """[round16 S16-05 · round17 S17-03a] 여섯 갈래 **전부**가 같은 규약을 지킨다.

    ① 사유 문장에는 점유자에게서 읽은 문자열이 없다.
    ② **관측된 점유자 전원**이 구조화 필드로 나간다 — 1대든 2대든 면제가 없다.

    [round17 #S17-03a] 다중 점유 갈래의 `observed_occupants=occupants`를 `()`로 바꾸거나
      지우면 'multiple_occupants' 행이 실패한다. round16 표는 그 갈래에 `False`를 정답으로
      고정하고 있었으므로 **그 상태가 통과였다** — 조작자는 무엇이 점유했는지 모른 채
      되돌릴 수 없는 쓰기를 판단했다.
    [round17 #S17-03a] 단일 점유 네 갈래 어디서든 `observed_occupants=`를 지우면 그 행이
      실패한다.
    [round17 #S17-03a] `ConsoleFixture.to_dict()`에서 키를 하나라도(예: `slot`) 지우면
      점유자가 있는 다섯 행 전부가 실패한다.
    """
    console_records = tuple(_record(*row) for row in records)
    resolutions = (_r16_unresolved_resolution(),) if resolution_kind == "unresolved" else None
    screened = _r16_screen(console_records, resolutions=resolutions)

    occupants = _console(*console_records)
    expected_occupants = tuple(occupant.to_dict() for occupant in occupants)
    assert len(expected_occupants) == expected_occupant_count

    if code is None:
        assert screened.exclusions == ()
        assert [entry.candidate_id for entry in screened.entries] == ["a"]
        return

    assert screened.entries == ()
    (exclusion,) = screened.exclusions
    assert exclusion.code == code

    # ② 점유자 전원이 객체에서도 payload에서도 나온다.
    assert exclusion.observed_occupants == expected_occupants
    assert exclusion.to_dict()["observed_occupants"] == [dict(row) for row in expected_occupants]

    # ① 문장에는 점유자에게서 읽은 문자열이 없다 — 표시 원문도, 확정 이름도.
    for occupant in occupants:
        for observed in (occupant.type_display, occupant.mode_display):
            assert observed is not None
            assert observed not in exclusion.reason, (name, observed)
        if not approved_names_in_sentence:
            for resolved in (occupant.type_name, occupant.mode_name):
                if resolved is not None:
                    assert resolved not in exclusion.reason, (name, resolved)

    # 좌표는 언제나 문장에 있다 — 조작자가 어디를 보러 갈지 알아야 한다(§0 2c①).
    assert "유니버스 1 주소 1" in exclusion.reason or "유니버스 1 주소 1를" in exclusion.reason
    if approved_names_in_sentence:
        # 이 갈래에서만 이름이 문장에 실린다 — 그것은 **우리가 승인한 값**이다.
        assert LED in exclusion.reason and MODE_1 in exclusion.reason


# ---- 형제 표면 `verify_patch`의 갈래 전수 -------------------------------------

# (행 이름, 기대 outcome, 점유 기록, read_complete, **기대 점유자 수**)
#
# [round17 S17-03a] 마지막 열은 round16의 `fills_display`(단수 필드를 채우는가)를 **교체한
# 것**이다. 그 열은 `multiple_found`에 `False`를 정답으로 고정하고 있었다 — 단수 필드로는
# 2대를 표현할 수 없으니 그것이 그 시점의 사실이었지만, 동시에 **점유자를 못 싣는 갈래를
# 규약이 승인**하는 열이기도 했다. 계수 열에는 그런 면제가 없다: 0·1·N이 전부 값이다.
_R16_VERIFY_BRANCH_ROWS = (
    (
        "multiple_found",
        VERIFICATION_IDENTITY_UNCONFIRMED,
        (
            (1, "1.1", _R16_LED_DISPLAY, _R16_MODE1_DISPLAY),
            (2, "1.1", _R16_LED_DISPLAY, _R16_MODE1_DISPLAY),
        ),
        True,
        2,
    ),
    ("absent_but_read_incomplete", VERIFICATION_IDENTITY_UNCONFIRMED, (), False, 0),
    ("absent_and_read_complete", VERIFICATION_NOT_OBSERVED, (), True, 0),
    (
        "identity_unconfirmed",
        VERIFICATION_IDENTITY_UNCONFIRMED,
        ((1, "1.1", "CD 5", "9 Mode 9"),),
        True,
        1,
    ),
    (
        "observed",
        VERIFICATION_OBSERVED,
        ((1, "1.1", _R16_LED_DISPLAY, _R16_MODE1_DISPLAY),),
        True,
        1,
    ),
    (
        "mismatched",
        VERIFICATION_MISMATCHED,
        ((1, "1.1", _R16_LED_DISPLAY, _R16_MODE2_DISPLAY),),
        True,
        1,
    ),
)


def _r16_production_verification_outcomes():
    """`verify_patch` 본문이 참조하는 `VERIFICATION_*` 이름을 **소스 순서대로** 뽑는다."""
    import ast

    fn = _r16_function_def(_r16_apply_tree(), "verify_patch")
    return tuple(
        _r16_apply_constant(node.id)
        for node in _r16_in_source_order(
            node
            for node in ast.walk(fn)
            if isinstance(node, ast.Name) and node.id.startswith("VERIFICATION_")
        )
    )


def test_the_verify_branch_table_is_a_bijection_onto_the_production_outcomes():
    """[round16 S16-05] 형제 표면도 같은 방식으로 전수 고정한다.

    `verify_patch`에서 갈래를 지우거나 더하면, 또는 이 표에서 행을 지우면 실패한다.
    """
    assert (
        tuple(outcome for _, outcome, _, _, _ in _R16_VERIFY_BRANCH_ROWS)
        == _r16_production_verification_outcomes()
    )


def _r17_production_verification_result_sites():
    """`verify_patch`가 짓는 `VerificationResult(...)` **전 사이트**를 소스 순서대로 뽑아,
    각 사이트가 `observed_occupants=`를 넘기는지 돌려준다.

    [round17 S17-03a] round16의 형제 게이트는 **결과 객체의 값**만 봤고 생성 자리 자체는
    세지 않았다. 갈래를 하나 더 만들면서 필드를 빼먹으면 그 갈래의 행이 없는 한 아무도
    실패하지 않는다 — `screen_idempotent` 쪽 전단사와 같은 종류의 자리를 여기에도 세운다.
    """
    import ast

    fn = _r16_function_def(_r16_apply_tree(), "verify_patch")
    calls = _r16_in_source_order(
        node
        for node in ast.walk(fn)
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "VerificationResult"
    )
    return tuple(
        any(keyword.arg == "observed_occupants" for keyword in call.keywords) for call in calls
    )


def test_every_verification_result_construction_site_carries_the_occupants():
    """[round17 S17-03a] `verify_patch`의 **모든** 생성 자리가 점유자를 싣는다.

    [round17 #S17-03a] `apply.py`의 다중 점유 갈래(또는 꼬리 갈래) `VerificationResult(...)`
    에서 `observed_occupants=`를 지우면 실패한다. 자리 수도 함께 고정하므로, 갈래를 더하고
    필드를 빼먹어도 실패한다.
    """
    sites = _r17_production_verification_result_sites()
    assert sites, "verify_patch에서 VerificationResult 생성 자리를 하나도 찾지 못했다"
    assert sites == (True,) * len(sites)
    # 생성 자리는 **둘**이다 — 다중 점유 갈래와 나머지 전 갈래의 공통 꼬리.
    assert len(sites) == 2


@pytest.mark.parametrize(
    "name,outcome,records,read_complete,expected_occupant_count",
    _R16_VERIFY_BRANCH_ROWS,
    ids=[row[0] for row in _R16_VERIFY_BRANCH_ROWS],
)
def test_every_verify_patch_branch_obeys_the_same_display_contract(
    name, outcome, records, read_complete, expected_occupant_count
):
    """[round16 S16-05 형제 표면 · round17 S17-03a] `detail` 문장에 관측 원문이 없고,
    **관측된 점유자 전원**이 구조화 필드로 나간다 — 0대든 1대든 2대든.

    [round17 #S17-03a] `apply.py`의 꼬리 `observed_occupants=tuple(...)`을 `()`로 바꾸면
    'identity_unconfirmed'·'observed'·'mismatched' 세 행이 실패한다.
    [round17 #S17-03a] 다중 점유 갈래의 `observed_occupants=`를 `()`로 바꾸면
    'multiple_found' 행이 실패한다 — round16 표는 그 갈래에 `False`가 정답이라 못 잡았다.
    [round17 #S17-03a] `ConsoleFixture.to_dict()`에서 키를 하나라도 지우면 전 행이 실패한다.
    """
    console_records = tuple(_record(*row) for row in records)
    report = verify_patch(
        (_entry("a", 1, 1),),
        console_fixtures=_console(*console_records),
        read_complete=read_complete,
    )
    (result,) = report.results
    assert result.outcome == outcome

    occupants = _console(*console_records)
    expected_occupants = tuple(occupant.to_dict() for occupant in occupants)
    assert len(expected_occupants) == expected_occupant_count
    assert result.observed_occupants == expected_occupants
    assert result.to_dict()["observed_occupants"] == [dict(row) for row in expected_occupants]

    for occupant in occupants:
        for observed in (occupant.type_display, occupant.mode_display):
            assert observed is not None
            assert observed not in result.detail, (name, observed)


# ==========================================================================
# M51 — `validate_autopatch` 호출 **전수**에 대조군
#
# `patchplan.py`의 `validate_autopatch("target_exclusion_reason", self.code)`를 지워도
# 아무 테스트도 실패하지 않았다(SURVIVED). 닫힌 어휘 검증이 사라지면 오타 하나가
# 조작자 화면의 판정 코드를 조용히 바꾼다 — 이 앱에는 실행 취소가 없다.
#
# 처방의 도달 범위: **`server/vwx` 전 모듈의 모든 호출**. 손으로 쓴 표를 AST 파생과
# 전단사로 묶으므로 어느 사이트에서든 호출을 떼면 이 절이 실패한다. 그 위에,
# 값이 변수인 사이트에는 **미등재 값을 실제로 흘려보내는** 행위 대조군을 붙이고,
# 값이 모듈 상수인 사이트에는 그 상수가 그 어휘에 등재돼 있는지를 단정한다.
# ==========================================================================

#: [round17 #7] 이 표는 round16까지 **네 모듈**만 담았는데 파서 독스트링은 `server/vwx/*.py`라
#: 적었다 — `_R16_BOOL_GUARD_ROWS`와 **같은 스코프 거짓말**이다. 이제 목록을 손으로 쓰지 않고
#: 디렉터리에서 파생한다. 모듈이 하나 생기면 스캔 범위가 자동으로 따라간다.
_R16_VWX_MODULES = tuple(sorted(vwx_module_label(path) for path in iter_vwx_modules()))
_R16_UNREGISTERED_CODE = "존재하지 않는 판정 코드"


def _r16_validate_autopatch_sites():
    """`server/vwx/*.py` **전 모듈**의 `validate_autopatch(...)` 호출을
    (모듈, 어휘식, 값식)으로 전수한다.

    [round17 #7] 스캔 범위를 다시 손으로 쓴 목록으로 좁히면 `test_autopatch_contract.py`의
    `_R17_AST_SCANNER_SCOPES` 등기부가 어긋나 실패한다 — 선언과 스코프가 갈라지는 것을
    그쪽에서 막는다.
    """
    import ast

    sites = []
    for module_name in _R16_VWX_MODULES:
        source = (Path("server/vwx") / module_name).read_text(encoding="utf-8")
        tree = ast.parse(source)
        calls = _r16_in_source_order(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "validate_autopatch"
        )
        for call in calls:
            sites.append(
                (
                    module_name,
                    ast.get_source_segment(source, call.args[0]),
                    ast.get_source_segment(source, call.args[1]),
                )
            )
    return tuple(sites)


#: 손으로 열거한 전수 표. (모듈, 어휘식, 값식, 종류) — `variable`은 값이 바깥에서 들어오는
#: 사이트라 미등재 값을 실제로 흘려보낼 수 있고, `constant`는 모듈 상수라 그럴 수 없다.
_R16_VALIDATE_SITES = (
    ("apply.py", '"console_read_caveat_kind"', "CONSOLE_READ_INCOMPLETE", "constant"),
    ("apply.py", '"console_read_caveat_kind"', "CONSOLE_READ_UNPATCHED_PRESENT", "constant"),
    ("apply.py", '"console_read_caveat_kind"', "CONSOLE_READ_INDEX_DOMAIN_UNKNOWN", "constant"),
    ("apply.py", '"skipped_check_kind"', "EXISTING_FOOTPRINT_UNREADABLE", "constant"),
    ("apply.py", '"verification_outcome"', "self.outcome", "variable"),
    ("patchplan.py", '"target_exclusion_reason"', "self.code", "variable"),
    ("patchplan.py", "self.vocabulary", "self.code", "variable"),
    ("patchplan.py", '"selection_error_reason"', "UNKNOWN_CANDIDATE_ID", "constant"),
    ("patchplan.py", '"skipped_check_kind"', "FID_CONFLICT_PRECHECK_INCOMPLETE", "constant"),
    ("patchplan.py", '"skipped_check_kind"', "FID_CONFLICT_PRECHECK_DESCOPE", "constant"),
    # [round18 R18-J] 2단계가 1단계 대조의 공허명 소멸을 고지하는 자리.
    # [round19 major#3·#1] 축마다·조인 미수행 갈래마다 다른 코드로 갈렸다 — 세 자리 전부
    # 모듈 상수라 미등재 값이 흐를 수 없고, 어휘 검증은 표 조립 시점(import)에 일어난다.
    ("patchplan.py", '"skipped_check_kind"', "DESIGNED_TYPE_NAME_VACUOUS", "constant"),
    (
        "patchplan.py",
        '"skipped_check_kind"',
        "DESIGNED_TYPE_NAME_VACUOUS_QUANTITY_AXIS",
        "constant",
    ),
    (
        "patchplan.py",
        '"skipped_check_kind"',
        "DESIGNED_TYPE_NAME_VACUOUS_JOIN_ABSENT",
        "constant",
    ),
    ("typemap.py", '"target_exclusion_reason"', "self.code", "variable"),
    ("typemap.py", '"type_resolution_status"', "self.status", "variable"),
    ("typemap.py", '"skipped_check_kind"', "kind", "variable"),
    ("verdicts.py", "vocabulary", "code", "variable"),
)


def test_the_validate_autopatch_site_table_is_a_bijection_onto_production():
    """[round16 M51] 어느 사이트에서든 `validate_autopatch(...)` 호출을 떼면 실패한다.

    round16 실측: `patchplan.py`의
    `"code": validate_autopatch("target_exclusion_reason", self.code)`를
    `"code": self.code`로 바꾸는 뮤테이션이 SURVIVED였다. 이제 이 단정이 그것을 잡는다 —
    그리고 형제 사이트 13개 전부에 같은 강제력이 걸린다. 표에서 행을 지워도 깨진다.
    """
    assert _r16_validate_autopatch_sites() == tuple(
        (module, vocabulary, value) for module, vocabulary, value, _ in _R16_VALIDATE_SITES
    )


def _r16_variable_site_probes():
    """값이 변수인 사이트마다 **미등재 값을 실제로 흘려보내는** 프로덕션 호출."""
    from server.vwx.apply import VerificationResult
    from server.vwx.patchplan import PatchPlanRejection, PatchTargetExclusion
    from server.vwx.typemap import ListCompleteness, TypeHardStop, _skipped_check
    from server.vwx.verdicts import autopatch_label

    bad = _R16_UNREGISTERED_CODE
    return {
        ("apply.py", '"verification_outcome"', "self.outcome"): lambda: VerificationResult(
            delivered=True,
            candidate_id="a",
            universe=1,
            address=1,
            expected_type=LED,
            expected_mode=MODE_1,
            outcome=bad,
            observed_type=None,
            observed_mode=None,
            detail="",
        ).to_dict(),
        (
            "patchplan.py",
            '"target_exclusion_reason"',
            "self.code",
        ): lambda: PatchTargetExclusion(candidate_id="a", code=bad, reason="").to_dict(),
        ("patchplan.py", "self.vocabulary", "self.code"): lambda: PatchPlanRejection(
            code=bad, reason="", vocabulary="candidate_rejection_reason"
        ).to_dict(),
        (
            "typemap.py",
            '"target_exclusion_reason"',
            "self.code",
        ): lambda: TypeHardStop(candidate_id="a", code=bad, reason="").to_dict(),
        ("typemap.py", '"type_resolution_status"', "self.status"): lambda: TypeResolution(
            request=TypeRequest(candidate_id="a", instrument_type=LED),
            status=bad,
            reason="",
            # [round21 R20-B] `row()`은 목록 완전성 진술을 **필수 키워드**로 받는다 —
            # 목록을 내면서 완전성을 말하지 않는 조립을 구조적으로 막는다. 여기서 재는
            # 것은 상태 어휘 검증이라 완전성 값 자체는 무관하다: 근거 없음(`None`)을 준다.
        ).row(type_candidates_completeness=ListCompleteness(complete=None)),
        ("typemap.py", '"skipped_check_kind"', "kind"): lambda: _skipped_check(bad, ""),
        ("verdicts.py", "vocabulary", "code"): lambda: autopatch_label(
            "target_exclusion_reason", bad
        ),
    }


_R16_VARIABLE_SITES = tuple(
    (module, vocabulary, value)
    for module, vocabulary, value, kind in _R16_VALIDATE_SITES
    if kind == "variable"
)


def test_every_variable_valued_site_has_exactly_one_probe():
    """[round16 M51] 변수 사이트 표와 대조군 표가 1:1 — 대조군 없는 사이트를 남기지 않는다."""
    assert tuple(sorted(_r16_variable_site_probes())) == tuple(sorted(_R16_VARIABLE_SITES))


@pytest.mark.parametrize(
    "site",
    _R16_VARIABLE_SITES,
    ids=[f"{module}:{value}" for module, _, value in _R16_VARIABLE_SITES],
)
def test_each_variable_valued_site_refuses_an_unregistered_value(site):
    """[round16 M51] 미등재 값이 payload로 나가지 못한다 — **프로덕션 산출 경로**로 확인한다.

    이 단정이 고정하는 것은 **관측 가능한 계약**이다: 미등재 값은 payload를 만들지 못한다.
    테스트가 조립한 목록이 아니라 프로덕션 `to_dict()`/`row()`를 실제로 부른다.

    실측(round16 격리 뮤테이션): `verdicts.autopatch_label`의 `validate_autopatch` 호출을
    떼면 'verdicts.py:code' 행이 여기서 직접 실패한다. 나머지 다섯 사이트는 같은 값이
    `*_label()` 조회로도 흘러 들어가 그쪽이 대신 `UnknownAutopatchVerdict`를 내므로,
    호출 **제거** 자체는 위 전단사 단정이 잡는다(여섯 사이트 전부 KILLED 확인). 두 단정은
    다른 명제를 지킨다 — 이쪽은 "미등재 값이 새어 나가지 않는다", 저쪽은 "검증이 그 자리에
    있다". 어느 한쪽만 두면 round16이 잡은 SURVIVED가 그대로 남는다.
    """
    from server.vwx.verdicts import UnknownAutopatchVerdict

    probe = _r16_variable_site_probes()[site]
    with pytest.raises(UnknownAutopatchVerdict):
        probe()


_R16_CONSTANT_SITES = tuple(
    (module, vocabulary, value)
    for module, vocabulary, value, kind in _R16_VALIDATE_SITES
    if kind == "constant"
)


@pytest.mark.parametrize(
    "module_name,vocabulary_literal,constant_name",
    _R16_CONSTANT_SITES,
    ids=[f"{module}:{value}" for module, _, value in _R16_CONSTANT_SITES],
)
def test_each_constant_valued_site_passes_a_registered_member_of_that_vocabulary(
    module_name: str, vocabulary_literal: str, constant_name: str
):
    """[round16 M51] 상수 사이트는 **어휘와 상수가 실제로 짝**임을 단정한다.

    상수를 다른 어휘의 값으로 바꾸거나 어휘 리터럴을 바꾸면(예: `"skipped_check_kind"`를
    `"verification_outcome"`으로) 그 사이트에서 프로덕션이 즉시 터진다는 것을 여기서
    미리 고정한다 — 위 전단사가 호출 **존재**를, 이 표가 호출 **인자**를 고정한다.
    """
    import importlib

    from server.vwx.verdicts import validate_autopatch as production_validate

    module = importlib.import_module(f"server.vwx.{module_name[: -len('.py')]}")
    value = getattr(module, constant_name)
    vocabulary = vocabulary_literal.strip('"')
    assert production_validate(vocabulary, value) == value


# --- round16 표 전단사·문장 전문 고정 (TableBijection) ---
#
# 이 절이 닫는 두 구멍:
#   ① `_ROUND15_CAVEAT_TABLE`에 **전단사 게이트가 없었다**. 적대 감사 실측 — 행을 지워도
#      전체 스위트가 실패 0으로 조용히 축소됐다. 여기서 표를 **프로덕션이 실제로 밟는
#      갈래 경로 전부**와 묶는다. 경로는 리터럴 목록이 아니라 `console_read_caveat`의
#      **반환값에서** 복원한다 — 갈래가 늘거나 표가 줄면 즉시 어긋난다.
#   ② 안심·경고 **어휘 목록 방식 자체가 반증됐다**(M44). `_INDEX_DOMAIN_CLAUSE`에
#      `"주의할 것 없음, "`을 끼우면 안심 목록 11개를 전부 피하면서 하필 경고 토큰
#      `"주의"`를 부분문자열로 포함해 경고 게이트까지 만족시킨다. 그래서 caveat의
#      라벨·사유를 **문장 전문 동등**으로 고정하고, 어휘 검사는 보조로만 남긴다.
#      이 문장들은 되돌릴 수 없는 쓰기 앞의 **유일한 고지**다 — 리터럴 고정이 바로
#      그 변경을 사람 눈에 띄게 하는 장치다.


def _round16_caveat_path(caveat: dict | None) -> tuple:
    """caveat **반환값만 보고** 프로덕션이 밟은 갈래 경로를 복원한다.

    INCOMPLETE 갈래는 세 하위 결정(`missing_count` · `unreadable_addresses` · `unpatched`)이
    문장을 갈라놓으므로 그 셋을 경로에 싣는다. UNPATCHED 갈래는 `index_domain_unknown`
    하나로 갈리고, IDU 갈래와 "caveat 없음"은 더 갈리지 않는다.
    """
    if caveat is None:
        return ("clean",)
    kind = caveat["kind"]
    if kind == CONSOLE_READ_INCOMPLETE:
        return (
            kind,
            caveat["missing_count"] > 0,
            caveat["unreadable_address_count"] > 0,
            caveat["unpatched_count"] > 0,
        )
    if kind == CONSOLE_READ_UNPATCHED_PRESENT:
        return (kind, bool(caveat["index_domain_unknown"]))
    return (kind,)


def _round16_expected_caveat_paths() -> frozenset[tuple]:
    """세 boolean 축의 `itertools.product`로 **전수 경로**를 만든다.

    INCOMPLETE 갈래는 `unread > 0`이 전제라 `missing`·`unreadable`이 **둘 다 거짓**인
    조합만 도달 불가다 — 8 - 2 = 6. 여기에 UNPATCHED 2 · IDU 1 · 없음 1을 더해 10이다.
    """
    import itertools

    paths: set[tuple] = {("clean",), (CONSOLE_READ_INDEX_DOMAIN_UNKNOWN,)}
    paths |= {(CONSOLE_READ_UNPATCHED_PRESENT, index_domain) for index_domain in (False, True)}
    paths |= {
        (CONSOLE_READ_INCOMPLETE, missing, unreadable, unpatched)
        for missing, unreadable, unpatched in itertools.product((False, True), repeat=3)
        if missing or unreadable
    }
    return frozenset(paths)


def test_the_round15_caveat_table_is_a_bijection_with_every_reachable_caveat_path():
    """`_ROUND15_CAVEAT_TABLE` ↔ `console_read_caveat`의 도달 가능한 갈래 경로 **전단사**.

    [round16 A1] 표에서 어느 행을 지워도 전사성 단정이 실패한다 — round15까지는
      행 삭제가 전체 스위트에서 실패 0으로 조용히 지나갔다.
    [round16 A1] 같은 경로를 두 행이 덮으면 단사성 단정이 실패한다 — 중복 행은
      "지워도 되는 행"을 만들어 위 전사성을 무력화한다.
    [round16] `apply.py`가 갈래를 하나 늘리면(예: 미판독+절단 전용 문장) 그 경로를 덮는
      행이 없어 전사성이 실패한다.
    [round16] `apply.py` INCOMPLETE 갈래의 `if unpatched:` 줄을 지우면 세 행의 경로가
      `unpatched=False` 쪽으로 접혀 단사성이 실패한다.
    """
    expected = _round16_expected_caveat_paths()
    assert len(expected) == 10

    observed: dict[str, tuple] = {}
    for param in _ROUND15_CAVEAT_TABLE:
        axes = param.values[0]
        path = _round16_caveat_path(console_read_caveat(_round15_inventory(**axes)))
        assert path not in observed.values(), (param.id, path, observed)
        observed[param.id] = path

    assert set(observed.values()) == expected, sorted(
        str(path) for path in expected - set(observed.values())
    )
    assert len(_ROUND15_CAVEAT_TABLE) == len(expected)
    assert len(observed) == len(_ROUND15_CAVEAT_TABLE)


#: 갈래별 **문장 전문**. `console_read_caveat`가 사람에게 내보내는 라벨·사유를 글자
#: 하나까지 고정한다 — 어휘 휴리스틱은 M44에서 통째로 뚫렸다. 값이 `None`인 행은
#: "caveat가 없어야 한다"는 뜻이다.
_ROUND16_CAVEAT_VERBATIM: dict[str, tuple[str, str] | None] = {
    "none__clean_read_has_no_caveat": None,
    "idu__truncated_but_fully_observed": (
        "열거는 절단됐으나 선언된 자식을 전부 관측했다 — 인덱스 도메인만 미상",
        (
            "열거가 절단됐으나 선언된 자식을 전부 관측했다 — "
            "수량 비교는 정확하고, 인덱스 도메인만 미상이다."
        ),
    ),
    "unpatched__spare_fixture_only": (
        "최소 인덱스 미만 Patch 값을 가진 픽스처가 있다 — 미실측 가정 위의 판정이니 대조하라",
        (
            "콘솔 픽스처 1대가 최소 인덱스 미만 Patch 값을 가진다 — 이 모듈은 그것을 "
            "'주소를 점유하지 않는다'로 읽지만 그 전제는 미실측이고 server/prechk는 "
            "같은 값을 판독 실패로 등급한다. 세션 전에 눈으로 대조하라."
        ),
    ),
    "unpatched_and_idu__both_sentences_must_ship": (
        "최소 인덱스 미만 Patch 값을 가진 픽스처가 있다 — 미실측 가정 위의 판정이니 대조하라",
        (
            "콘솔 픽스처 19대가 최소 인덱스 미만 Patch 값을 가진다 — 이 모듈은 그것을 "
            "'주소를 점유하지 않는다'로 읽지만 그 전제는 미실측이고 server/prechk는 "
            "같은 값을 판독 실패로 등급한다. 세션 전에 눈으로 대조하라. "
            "또한 열거가 절단됐으나 선언된 자식을 전부 관측했다 — "
            "수량 비교는 정확하고, 인덱스 도메인만 미상이다."
        ),
    ),
    "unread__unreadable_address_only": (
        "재조회에 미판독이 남았다 — 없음을 단정할 수 없다",
        (
            "콘솔 재조회에서 1대는 주소를 판독하지 못했다 — "
            "이 상태의 '없음'은 관측이 아니라 미판독이다."
        ),
    ),
    "unread_and_idu__enumeration_short_only": (
        "재조회에 미판독이 남았다 — 없음을 단정할 수 없다",
        (
            "콘솔 재조회에서 선언된 2대 중 1대를 열거하지 못했다 — "
            "이 상태의 '없음'은 관측이 아니라 미판독이다."
        ),
    ),
    "unread__both_unread_axes": (
        "재조회에 미판독이 남았다 — 없음을 단정할 수 없다",
        (
            "콘솔 재조회에서 선언된 3대 중 1대를 열거하지 못했다 · "
            "1대는 주소를 판독하지 못했다 — "
            "이 상태의 '없음'은 관측이 아니라 미판독이다."
        ),
    ),
    "unread_and_unpatched__count_still_ships": (
        "재조회에 미판독이 남았다 — 없음을 단정할 수 없다",
        (
            "콘솔 재조회에서 1대는 주소를 판독하지 못했다 — "
            "이 상태의 '없음'은 관측이 아니라 미판독이다. "
            "또한 콘솔 픽스처 1대가 최소 인덱스 미만 Patch 값을 가진다 — 이 모듈은 그것을 "
            "'주소를 점유하지 않는다'로 읽지만 그 전제는 미실측이고 server/prechk는 "
            "같은 값을 판독 실패로 등급한다. 세션 전에 눈으로 대조하라."
        ),
    ),
    "all_three_axes__blocking_branch_carries_the_count": (
        "재조회에 미판독이 남았다 — 없음을 단정할 수 없다",
        (
            "콘솔 재조회에서 선언된 4대 중 1대를 열거하지 못했다 — "
            "이 상태의 '없음'은 관측이 아니라 미판독이다. "
            "또한 콘솔 픽스처 2대가 최소 인덱스 미만 Patch 값을 가진다 — 이 모듈은 그것을 "
            "'주소를 점유하지 않는다'로 읽지만 그 전제는 미실측이고 server/prechk는 "
            "같은 값을 판독 실패로 등급한다. 세션 전에 눈으로 대조하라."
        ),
    ),
    "all_three_incomplete_axes__every_clause_ships": (
        "재조회에 미판독이 남았다 — 없음을 단정할 수 없다",
        (
            "콘솔 재조회에서 선언된 4대 중 1대를 열거하지 못했다 · "
            "1대는 주소를 판독하지 못했다 — "
            "이 상태의 '없음'은 관측이 아니라 미판독이다. "
            "또한 콘솔 픽스처 1대가 최소 인덱스 미만 Patch 값을 가진다 — 이 모듈은 그것을 "
            "'주소를 점유하지 않는다'로 읽지만 그 전제는 미실측이고 server/prechk는 "
            "같은 값을 판독 실패로 등급한다. 세션 전에 눈으로 대조하라."
        ),
    ),
}

_ROUND16_ABSENT = object()


def test_the_caveat_verbatim_table_covers_exactly_the_branch_table():
    """전문 표 ↔ 갈래 표 **전단사** — 어느 한쪽에서 행이 빠지면 여기서 걸린다."""
    assert set(_ROUND16_CAVEAT_VERBATIM) == {param.id for param in _ROUND15_CAVEAT_TABLE}
    assert len(_ROUND16_CAVEAT_VERBATIM) == len(_ROUND15_CAVEAT_TABLE)


@pytest.mark.parametrize(
    "axes,expected",
    [
        (param.values[0], _ROUND16_CAVEAT_VERBATIM.get(param.id, _ROUND16_ABSENT))
        for param in _ROUND15_CAVEAT_TABLE
    ],
    ids=[param.id for param in _ROUND15_CAVEAT_TABLE],
)
def test_every_console_read_caveat_sentence_is_fixed_verbatim(axes, expected):
    """조작자가 읽는 **문장 전체**를 프로덕션 반환값과 `==`로 맞춘다.

    [round16 M44] `apply.py` `_INDEX_DOMAIN_CLAUSE`에 `"주의할 것 없음, "`을 끼우면
      `idu__*` · `unpatched_and_idu__*` 두 행이 실패한다. 어휘 목록은 이 삽입을
      **놓쳤다** — 안심 목록 11개 어디에도 안 걸리고, 경고 토큰 `"주의"`를 부분문자열로
      포함해 경고 게이트마저 만족시켰다.
    [round16 M43] `apply.py` `_unpatched_clause`에서 가운데 문장
      (`"…그 전제는 미실측이고 server/prechk는 같은 값을 판독 실패로 등급한다."`)을
      지우면 `unpatched__*` · `unpatched_and_idu__*` · `unread_and_unpatched__*` ·
      `all_three_*` 행이 실패한다.
    [round16] `verdicts.py`의 caveat 라벨 문구를 한 글자라도 바꾸면 해당 행이 실패한다.
    """
    assert expected is not _ROUND16_ABSENT, axes
    caveat = console_read_caveat(_round15_inventory(**axes))
    if expected is None:
        assert caveat is None
        return
    assert caveat is not None
    assert (caveat["label"], caveat["reason"]) == expected


#: 어휘 목록의 **축소 트립와이어**. 목록에서 항목을 하나 지우면 이 집합과 어긋난다 —
#: 파라미터화 대조군은 목록에서 행을 만들기 때문에 **축소를 원리적으로 감지하지 못한다**
#: (round16 A1이 삭제한 항진명제 20건이 정확히 그 구조였다).
_ROUND16_REASSURING_TOKEN_SET = frozenset(
    {
        "문제 없다",
        "문제없다",
        "이상 없다",
        "이상없다",
        "정상이다",
        "안전하다",
        "안심",
        "확인할 것은 없다",
        "확인할 필요 없다",
        "그대로 진행",
        "무시해도",
    }
)

_ROUND16_CAUTION_TOKEN_SET = frozenset(
    {
        "미판독",
        "미실측",
        "미상",
        "절단",
        "단정할 수 없다",
        "단정 불가",
        "대조하라",
        "확인 불가",
        "주의",
    }
)


def test_the_round15_vocabulary_tables_cannot_shrink_silently():
    """[round16 A1] 두 어휘 목록에서 항목을 더하거나 빼면 이 단정이 깨진다."""
    assert len(_ROUND15_REASSURING_TOKENS) == len(set(_ROUND15_REASSURING_TOKENS))
    assert len(_ROUND15_CAUTION_TOKENS) == len(set(_ROUND15_CAUTION_TOKENS))
    assert set(_ROUND15_REASSURING_TOKENS) == _ROUND16_REASSURING_TOKEN_SET
    assert set(_ROUND15_CAUTION_TOKENS) == _ROUND16_CAUTION_TOKEN_SET
    assert set(_ROUND15_REASSURING_TOKENS).isdisjoint(_ROUND15_CAUTION_TOKENS)


def test_no_reassuring_token_contains_a_caution_token_as_a_substring():
    """[round16 M44] 부분문자열 충돌 배제 — `"주의" ⊂ "주의할 것 없음"`이 그 반례다.

    안심 어휘가 경고 어휘를 품고 있으면 그 문구 하나로 **두 게이트를 동시에 만족**시킨다.
    안심 목록에 그런 항목을 추가하는 순간 이 단정이 먼저 깨진다.
    """
    for reassuring in _ROUND15_REASSURING_TOKENS:
        for caution in _ROUND15_CAUTION_TOKENS:
            assert caution not in reassuring, (reassuring, caution)
            assert reassuring not in caution, (reassuring, caution)


@pytest.mark.parametrize("token", _ROUND15_REASSURING_TOKENS)
def test_every_reassuring_token_is_caught_in_a_real_production_caveat(token, monkeypatch):
    """토큰별 대조군을 **프로덕션 `console_read_caveat`를 실제로 통과시켜** 세운다.

    [round16 A1] 삭제된 항진명제는 목록으로 만든 문자열을 같은 목록으로 다시 걸렀다 —
    프로덕션 호출 0회. 여기서는 심은 문구가 `apply.py`의 갈래를 지나 조작자에게 나가는
    `reason`에 실려 나온 뒤에야 검출된다.
    """
    from server.vwx import apply as apply_module

    monkeypatch.setattr(
        apply_module, "_INDEX_DOMAIN_CLAUSE", f"{apply_module._INDEX_DOMAIN_CLAUSE} {token}"
    )
    caveat = console_read_caveat(_round15_inventory(index_domain_unknown=True))
    assert caveat is not None
    assert _round15_reassurances(str(caveat["reason"])) == [token]


@pytest.mark.parametrize("token", _ROUND15_CAUTION_TOKENS)
def test_every_caution_token_is_caught_in_a_real_production_caveat(token, monkeypatch):
    """경고 어휘 쪽도 같은 규율 — 검출은 프로덕션 반환값 위에서만 성립한다."""
    from server.vwx import apply as apply_module

    monkeypatch.setattr(apply_module, "_INDEX_DOMAIN_CLAUSE", f"콘솔 재조회 결과는 {token}")
    caveat = console_read_caveat(_round15_inventory(index_domain_unknown=True))
    assert caveat is not None
    assert _round15_cautions(str(caveat["reason"])) == [token]


# --------------------------------------------------------------------------
# --- round16 조작자가 읽는 사유·계수 (TextContentGates) ---
#
# [M56] `screen_console_read`가 붙이는 사유에서 `str(caveat["reason"])`을 `""`로 바꿔도
# 스위트 5,354건이 전건 통과했다. 그 문자열은 **미판독 때문에 전 항목을 드롭한 이유**이고,
# 그것이 비면 조작자는 자기 세션이 왜 통째로 멈췄는지 알 방법이 없다(§0 2c①).
# 형제 표면도 같다 — `build_patch_handoff`·`screen_console_occupancy`·`screen_idempotent`가
# 만드는 사유 11자리, `verify_patch`가 만드는 `detail` 6갈래 전부를 표로 열거한다.
#
# [M50] 계수 문구는 **계수 1 표본만** 있으면 하드코딩이 보이지 않는다. `patchplan.py:766`의
# `{self.unparsable_rows}`를 `1`로 바꿔도 전건 통과했다 — 테스트가 언제나 1행만 만들었기
# 때문이다. 그래서 계수가 들어가는 자리를 **f-string 보간에서 전수로 뽑아** 분류하고,
# 계수 절마다 **1이 아닌** 표본을 하나씩 박는다.
# --------------------------------------------------------------------------

_R16_PATCHPLAN_SOURCE = Path("server/vwx/patchplan.py").read_text(encoding="utf-8")


def _r16_exclusion_call_sites(source: str) -> tuple[tuple[str, str], ...]:
    """`_exclusion(...)` 호출 사이트를 (함수, 사유 코드)로 **소스에서** 전수로 뽑는다."""
    import ast

    module = ast.parse(source)
    sites: list[tuple[str, str]] = []
    for node in module.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        for call in ast.walk(node):
            if (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Name)
                and call.func.id == "_exclusion"
            ):
                sites.append((node.name, ast.unparse(call.args[1])))
    return tuple(sorted(sites))


def _r16_handoff_kwargs(**overrides):
    base = {
        "targets": (_candidate("a", 1, 1, 101),),
        "address_plan": AddressPlan(entries=(_planned("a", 1, 1),)),
        "resolutions": (_resolution("a"),),
        "names": {"a": "LEDBeam 101"},
        "dry_run": False,
    }
    base.update(overrides)
    return base


def _r16_handoff_exclusions(**overrides):
    return list(build_patch_handoff(**_r16_handoff_kwargs(**overrides)).exclusions)


def _r16_unconfirmed_resolution():
    return TypeResolution(
        request=TypeRequest(candidate_id="a", instrument_type=LED),
        status=TYPE_NEEDS_CONFIRMATION,
        reason="",
        console_type=None,
        console_mode=None,
    )


#: 재조회 미판독 표본 — 계수가 **둘 다 1이 아니다**(M50 형제).
_R16_INCOMPLETE_AXES = {"missing": 2, "unreadable": 3}


def _r16_console_read_exclusions():
    return list(
        screen_console_read(
            (_candidate("a", 1, 1, 101),),
            address_plan=AddressPlan(entries=(_planned("a", 1, 1),)),
            inventory=_round15_inventory(**_R16_INCOMPLETE_AXES),
        ).exclusions
    )


def _r16_occupancy_exclusions():
    return list(
        screen_console_occupancy(
            (_candidate("a", 1, 1, 101),),
            address_plan=AddressPlan(entries=(_planned("a", 1, 1),)),
            console_fixtures=_console(_record(2, "1.5", "FixtureType 3", "1 Mode 1")),
        ).exclusions
    )


def _r16_idempotent_exclusions(*records, resolutions=None):
    return list(
        screen_idempotent(
            (_candidate("a", 1, 1, 101),),
            address_plan=AddressPlan(entries=(_planned("a", 1, 1),)),
            resolutions=resolutions if resolutions is not None else (_resolution("a"),),
            console_fixtures=_console(*records),
        ).exclusions
    )


def _r19_hard_stop_resolution(code=None, reason=None):
    """확인 경로가 **없는** 해상 결과 — `hard_stop_code`가 채워져 있다.

    [round19 major#4] 기본값은 R18-E가 만든 공허 이름 갈래다: 도면 타입 이름이 공허해
    후보가 0건이고, `types.hard_stops`는 그 상태를 "확인 경로 없음"이라 말한다.
    """
    from server.vwx.typemap import VACUOUS_TYPE_KEY_REASON
    from server.vwx.verdicts import FIXTURE_TYPE_NAME_UNUSABLE, TYPE_NAME_UNUSABLE

    return TypeResolution(
        request=TypeRequest(candidate_id="a", instrument_type="---"),
        status=TYPE_NAME_UNUSABLE,
        reason=reason if reason is not None else VACUOUS_TYPE_KEY_REASON,
        hard_stop_code=code if code is not None else FIXTURE_TYPE_NAME_UNUSABLE,
    )


def _r19_incomplete_resolution():
    """확인 경로가 **없는** 또 하나의 상태 — 라이브러리 관측이 불완전하다.

    [round19 major#4 형제 필드] 하드 스톱은 아니지만 확인 대기도 아니다: 제시할 수 있는
    선택지 자체를 다 보지 못했다. `hard_stop_code`만 보던 번역은 이 상태를
    `type_confirmation_pending`으로 뭉갰다 — 한 칸 옆에 남아 있던 같은 기제다.
    """
    from server.vwx.typemap import LIBRARY_TRUNCATED_REASON
    from server.vwx.verdicts import FIXTURE_TYPE_LIBRARY_TRUNCATED, TYPE_LIBRARY_INCOMPLETE

    return TypeResolution(
        request=TypeRequest(candidate_id="a", instrument_type="MegaPointe"),
        status=TYPE_LIBRARY_INCOMPLETE,
        reason=LIBRARY_TRUNCATED_REASON,
        incompleteness_kind=FIXTURE_TYPE_LIBRARY_TRUNCATED,
    )


#: [round19 major#4] 코드를 **상위 상태에서 받는** 자리 — 사이트 이름 -> 그 시나리오가
#: 실제로 내야 하는 코드. 값은 **리터럴**이다: `verdicts` 상수를 참조하면 상수를 바꿔도
#: 기대값이 따라가 자기 비교가 된다(round16 `_R16_APPLY_CONSTANTS`와 같은 규율).
#: 두 자리 모두 시나리오가 "진짜 확인 대기"(해상 결과 없음 · 후보 제시)이므로 기본 코드다.
_R19_DERIVED_EXCLUSION_CODES = {
    "handoff.type_pending": "type_confirmation_pending",
    "idempotent.own_type_pending": "type_confirmation_pending",
}


def _r19_derived_exclusion_codes():
    return dict(_R19_DERIVED_EXCLUSION_CODES)


#: `_exclusion` 호출 사이트 **전수 표** — (사이트 이름, 함수, 사유 코드, 산출 호출, 필수 문구).
#: 같은 (함수, 코드) 쌍이 두 번 나오는 자리가 있다(`screen_idempotent`의 확인 불가 두 갈래).
#: 그것을 뭉치지 않는 것이 요점이다 — 뭉치면 한 갈래가 비어도 다른 갈래가 가려준다.
#:
#: [round19 major#4] 셋째 열은 이제 **verdicts 상수 이름이거나 파생 식**이다.
#: `_unresolved_type_exclusion`과 `screen_idempotent`의 미확정 갈래는 코드를 상수로 박지 않고
#: 공유 번역기 `_unresolved_type_verdict`에서 받는다(그것이 major#4의 처방이다) — 소스 스캔에
#: 지역 이름(`code` · `unresolved_code`)으로 잡히고, 그 자리의 기대 코드는
#: `_r19_derived_exclusion_codes()`가 사이트 이름으로 **리터럴 고정**한다.
#: 상위 상태 세 갈래(하드 스톱 · 관측 불완전 · 진짜 확인 대기)를 그 번역기가 구별하는지는
#: `# --- round19 막다른 길 어휘 (DeadEndVocab) ---` 섹션이 별도로 단정한다.
_R16_EXCLUSION_SITES = (
    (
        "handoff.type_pending",
        "_unresolved_type_exclusion",
        "code",
        lambda: _r16_handoff_exclusions(resolutions=()),
        "콘솔 타입·모드가 확정되지 않았다",
    ),
    (
        "handoff.fid_missing",
        "build_patch_handoff",
        "FID_NOT_ASSIGNED",
        lambda: _r16_handoff_exclusions(targets=(_candidate("a", 1, 1, None),)),
        "FID가 배정되지 않았다",
    ),
    (
        "handoff.name_missing",
        "build_patch_handoff",
        "FIXTURE_NAME_MISSING",
        lambda: _r16_handoff_exclusions(names={}),
        "픽스처 이름이 제공되지 않았다",
    ),
    (
        "handoff.lua_refused",
        "build_patch_handoff",
        "LUA_GENERATION_REFUSED",
        lambda: _r16_handoff_exclusions(names={"a": "CD spare"}),
        "Lua 생성기가",
    ),
    (
        "console_read.incomplete",
        "screen_console_read",
        "CONSOLE_READ_INCOMPLETE",
        _r16_console_read_exclusions,
        "콘솔 재조회에서",
    ),
    (
        "occupancy.occupied",
        "screen_console_occupancy",
        "ADDRESS_ALREADY_OCCUPIED",
        _r16_occupancy_exclusions,
        "유니버스 1 주소",
    ),
    (
        "idempotent.multiple_occupants",
        "screen_idempotent",
        "EXISTING_IDENTITY_UNCONFIRMED",
        lambda: _r16_idempotent_exclusions(
            _record(1, "1.1", "FixtureType 3", "1 Mode 1"),
            _record(2, "1.1", "FixtureType 3", "1 Mode 1"),
        ),
        "확정할 수 없다",
    ),
    (
        "idempotent.own_type_pending",
        "screen_idempotent",
        "unresolved_code",
        lambda: _r16_idempotent_exclusions(
            _record(1, "1.1", "FixtureType 3", "1 Mode 1"),
            resolutions=(_r16_unconfirmed_resolution(),),
        ),
        "기존 픽스처와 대조할 수 없다",
    ),
    (
        "idempotent.occupant_unresolved",
        "screen_idempotent",
        "EXISTING_IDENTITY_UNCONFIRMED",
        lambda: _r16_idempotent_exclusions(_record(1, "1.1", "FixtureType 99", "9 Mode 9")),
        "확정할 수 없다",
    ),
    (
        "idempotent.already_patched",
        "screen_idempotent",
        "ALREADY_PATCHED_IDENTICAL",
        lambda: _r16_idempotent_exclusions(_record(1, "1.1", "FixtureType 3", "1 Mode 1")),
        "중복 생성하지 않는다",
    ),
    (
        "idempotent.conflict",
        "screen_idempotent",
        "ADDRESS_CONFLICTS_WITH_EXISTING",
        lambda: _r16_idempotent_exclusions(_record(1, "1.1", "FixtureType 3", "2 Mode 2")),
        "유니버스 1 주소 1",
    ),
)


def test_the_exclusion_site_table_is_a_bijection_onto_the_production_call_sites():
    """[round16 HARD 규율 1·3] `_exclusion(...)` 호출 자리가 늘거나 줄면 여기서 먼저 깨진다.

    표에서 행을 하나 지우면 정렬 비교가 실패한다. 같은 (함수, 코드) 쌍이 둘인 자리도
    **다중집합으로** 비교하므로 한 갈래를 지우면 잡힌다.
    """
    declared = tuple(sorted((func, code) for _, func, code, _, _ in _R16_EXCLUSION_SITES))
    assert declared == _r16_exclusion_call_sites(APPLY_SOURCE)
    labels = [label for label, _, _, _, _ in _R16_EXCLUSION_SITES]
    assert len(labels) == len(set(labels))


@pytest.mark.parametrize(
    "label,func,code,produce,fragment",
    _R16_EXCLUSION_SITES,
    ids=[label for label, _, _, _, _ in _R16_EXCLUSION_SITES],
)
def test_every_exclusion_site_ships_a_non_empty_reason(label, func, code, produce, fragment):
    """[round16 M56] `screen_console_read`의 `str(caveat["reason"])`을 `""`로 바꾸면
    `console_read.incomplete` 행이 실패한다. 형제 열 자리도 같은 단정을 받는다 —
    사유가 비면 조작자는 왜 막혔는지 모르고, 이 앱에는 실행 취소가 없다.
    """
    from server.vwx import verdicts

    produced = produce()
    # [round19 major#4] 셋째 열이 verdicts 상수 이름이 아니면 파생 자리다 —
    # 그 자리의 기대 코드는 사이트 이름으로 고정한다(자기 비교가 되지 않는다).
    derived = _r19_derived_exclusion_codes()
    expected_code = derived[label] if label in derived else getattr(verdicts, code)
    assert [exclusion.code for exclusion in produced] == [expected_code], produced
    reason = produced[0].reason
    assert reason.strip() != ""
    assert len(reason) >= 20, reason
    assert fragment in reason, reason
    assert produced[0].to_dict()["reason"] == reason


def test_no_two_exclusion_sites_share_the_same_sentence():
    """사유가 서로 구별돼야 조작자가 원인을 짚는다 — 한 자리를 다른 자리 문구로 바꾸면 깨진다."""
    reasons = [produce()[0].reason for _, _, _, produce, _ in _R16_EXCLUSION_SITES]
    assert len(reasons) == len(set(reasons))


def test_the_console_read_block_carries_the_caveat_reason_itself():
    """[round16 M56] 미판독 차단 사유는 **그 재조회의 caveat 사유 전문**이어야 한다.

    `_exclusion(target, CONSOLE_READ_INCOMPLETE, str(caveat["reason"]))`의 셋째 인자를
    `""`로 바꾸거나 고정 문구로 바꾸면 이 테스트가 실패한다 — 계수가 다른 두 재조회가
    **서로 다른 사유**를 내는 것까지 확인하므로 상수 대체도 빠져나가지 못한다.
    """
    first = _round15_inventory(missing=2, unreadable=3)
    second = _round15_inventory(missing=4, unreadable=2)
    reasons = []
    for inventory in (first, second):
        caveat = console_read_caveat(inventory)
        assert caveat is not None
        blocked = screen_console_read(
            (_candidate("a", 1, 1, 101),),
            address_plan=AddressPlan(entries=(_planned("a", 1, 1),)),
            inventory=inventory,
        )
        assert blocked.entries == ()
        assert [exclusion.code for exclusion in blocked.exclusions] == [CONSOLE_READ_INCOMPLETE]
        reason = blocked.exclusions[0].reason
        assert reason == str(caveat["reason"])
        reasons.append(reason)

    assert "2대를 열거하지 못했다" in reasons[0]
    assert "3대는 주소를 판독하지 못했다" in reasons[0]
    assert "4대를 열거하지 못했다" in reasons[1]
    assert "2대는 주소를 판독하지 못했다" in reasons[1]
    assert reasons[0] != reasons[1]


def test_the_skipped_check_report_also_carries_a_reason():
    """형제 표면 — 건너뛴 검사 보고도 사유가 비면 아무 정보가 아니다."""
    report = existing_footprint_skipped_check()
    reason = str(report["reason"])
    assert reason.strip() != ""
    assert len(reason) >= 20
    assert "점유폭" in reason


# --------------------------------------------------------------------------
# `verify_patch`의 `detail` 갈래 전수 — 사유 문장의 형제 축.
# --------------------------------------------------------------------------


def _r16_detail_producer_count(source: str) -> int:
    """`verify_patch` 안에서 `detail` 문장을 만드는 자리를 **소스에서** 센다."""
    import ast

    module = ast.parse(source)
    verify = next(
        node
        for node in module.body
        if isinstance(node, ast.FunctionDef) and node.name == "verify_patch"
    )
    count = 0
    for node in ast.walk(verify):
        is_assignment = isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "detail" for target in node.targets
        )
        # `detail=detail` 은 위 갈래가 만든 값을 실어 나르는 자리다 — 생산자가 아니다.
        is_fresh_keyword = (
            isinstance(node, ast.keyword)
            and node.arg == "detail"
            and not (isinstance(node.value, ast.Name) and node.value.id == "detail")
        )
        if is_assignment or is_fresh_keyword:
            count += 1
    return count


_R16_DETAIL_BRANCHES = (
    (
        "multiple_occupants",
        lambda: verify_patch(
            (_entry("a", 1, 1),),
            console_fixtures=_console(
                _record(1, "1.1", "FixtureType 3", "1 Mode 1"),
                _record(2, "1.1", "FixtureType 3", "1 Mode 1"),
            ),
        ),
        VERIFICATION_IDENTITY_UNCONFIRMED,
        "2대 관측된다",
    ),
    (
        "incomplete_read",
        lambda: verify_patch(
            (_entry("a", 1, 1),), console_fixtures=_console(), read_complete=False
        ),
        VERIFICATION_IDENTITY_UNCONFIRMED,
        "재조회가 불완전해",
    ),
    (
        "not_observed",
        lambda: verify_patch((_entry("a", 1, 1),), console_fixtures=_console()),
        VERIFICATION_NOT_OBSERVED,
        "관측되지 않았다",
    ),
    (
        "occupant_unresolved",
        lambda: verify_patch(
            (_entry("a", 1, 1),),
            console_fixtures=_console(_record(1, "1.1", "FixtureType 99", "9 Mode 9")),
        ),
        VERIFICATION_IDENTITY_UNCONFIRMED,
        "확정할 수 없다",
    ),
    (
        "observed",
        lambda: verify_patch(
            (_entry("a", 1, 1),),
            console_fixtures=_console(_record(1, "1.1", "FixtureType 3", "1 Mode 1")),
        ),
        VERIFICATION_OBSERVED,
        "승인한 타입·모드로 관측됐다",
    ),
    (
        "mismatched",
        lambda: verify_patch(
            (_entry("a", 1, 1),),
            console_fixtures=_console(_record(1, "1.1", "FixtureType 3", "2 Mode 2")),
        ),
        VERIFICATION_MISMATCHED,
        "다른 타입 또는 모드",
    ),
)


def test_the_detail_branch_table_covers_every_production_detail_producer():
    """[round16 HARD 규율 3] `verify_patch`에 `detail` 갈래가 늘면 표도 늘어야 한다.

    표에서 행을 하나 지우면 개수 비교가 실패한다.
    """
    labels = [label for label, _, _, _ in _R16_DETAIL_BRANCHES]
    assert len(labels) == len(set(labels)) == _r16_detail_producer_count(APPLY_SOURCE)


@pytest.mark.parametrize(
    "label,produce,outcome,fragment",
    _R16_DETAIL_BRANCHES,
    ids=[label for label, _, _, _ in _R16_DETAIL_BRANCHES],
)
def test_every_verification_detail_branch_says_something(label, produce, outcome, fragment):
    """[round16 M56 형제] `detail`을 `""`로 바꾸면 그 행이 실패한다.

    판정(`outcome`)만 맞고 문장이 비면 조작자는 다음 행동을 고를 수 없다 — 미관측과
    확인 불가를 가르는 것이 바로 그 문장이다.
    """
    report = produce()
    result = report.results[0]
    assert result.outcome == outcome
    assert result.detail.strip() != ""
    assert len(result.detail) >= 10, result.detail
    assert fragment in result.detail, result.detail
    assert result.to_dict()["detail"] == result.detail


def test_no_two_verification_detail_branches_share_the_same_sentence():
    """여섯 갈래가 서로 다른 문장을 낸다 — 한 갈래를 다른 갈래 문구로 바꾸면 깨진다."""
    details = [produce().results[0].detail for _, produce, _, _ in _R16_DETAIL_BRANCHES]
    assert len(details) == len(set(details))


# --------------------------------------------------------------------------
# [round16 M50] 계수 절에는 **1이 아닌** 표본을 박는다.
# --------------------------------------------------------------------------


def _r16_interpolated_expressions(source: str, *names: str) -> tuple[str, ...]:
    """지정한 최상위 함수들의 f-string **보간 표현식**을 전수로 뽑는다."""
    import ast

    module = ast.parse(source)
    wanted = [
        node for node in module.body if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    assert len(wanted) == len(names), names
    found: set[str] = set()
    for node in wanted:
        for sub in ast.walk(node):
            if isinstance(sub, ast.FormattedValue):
                found.add(ast.unparse(sub.value))
    return tuple(sorted(found))


def _r16_reason_interpolations() -> tuple[str, ...]:
    """`ExistingFidRead.reason()`의 보간 표현식 — 클래스 안이라 따로 찾는다."""
    import ast

    module = ast.parse(_R16_PATCHPLAN_SOURCE)
    cls = next(
        node
        for node in module.body
        if isinstance(node, ast.ClassDef) and node.name == "ExistingFidRead"
    )
    reason = next(
        node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == "reason"
    )
    return tuple(
        sorted(
            {
                ast.unparse(sub.value)
                for sub in ast.walk(reason)
                if isinstance(sub, ast.FormattedValue)
            }
        )
    )


#: `console_read_caveat` · `_unpatched_clause`의 보간 자리 **전수 분류**.
_R16_CAVEAT_INTERPOLATIONS = (
    ("inventory.child_count", "count"),
    ("inventory.missing_count", "count"),
    ("unreadable_addresses", "count"),
    ("unpatched", "count"),
    ("reason", "text"),
    ("_unpatched_clause(unpatched)", "text"),
    ("_INDEX_DOMAIN_CLAUSE", "text"),
)

#: 계수 자리마다 **1이 아닌** 표본. (보간 표현식, 재조회 축, 그 계수를 담은 문구)
_R16_CAVEAT_COUNT_SAMPLES = (
    ("inventory.child_count", {"missing": 3}, "선언된 4대 중"),
    ("inventory.missing_count", {"missing": 3}, "중 3대를 열거하지 못했다"),
    ("unreadable_addresses", {"unreadable": 2}, "2대는 주소를 판독하지 못했다"),
    ("unpatched", {"unpatched": 5}, "콘솔 픽스처 5대가 최소 인덱스 미만"),
)


def test_every_caveat_interpolation_is_classified_and_every_count_has_a_sample():
    """[round16 HARD 규율 1·3] caveat 문장에 보간 자리가 생기면 분류를 강제한다.

    분류 표에서 행을 지우면 전단사가 깨지고, 계수 행을 지우면 표본 대응이 깨진다.
    """
    discovered = _r16_interpolated_expressions(
        APPLY_SOURCE, "console_read_caveat", "_unpatched_clause"
    )
    declared = tuple(sorted(expr for expr, _ in _R16_CAVEAT_INTERPOLATIONS))
    assert declared == discovered
    counts = {expr for expr, kind in _R16_CAVEAT_INTERPOLATIONS if kind == "count"}
    assert counts == {expr for expr, _, _ in _R16_CAVEAT_COUNT_SAMPLES}
    assert len(_R16_CAVEAT_COUNT_SAMPLES) == len(counts)


@pytest.mark.parametrize(
    "expression,axes,fragment",
    _R16_CAVEAT_COUNT_SAMPLES,
    ids=[expr for expr, _, _ in _R16_CAVEAT_COUNT_SAMPLES],
)
def test_every_caveat_count_clause_reports_a_count_other_than_one(expression, axes, fragment):
    """[round16 M50 형제] 계수 자리를 리터럴 `1`로 굳히면 그 행이 실패한다.

    기존 표본이 전부 1이라 하드코딩이 보이지 않던 자리다. 네 계수를 서로 다른 값
    (4 · 3 · 2 · 5)으로 두어 **자리 바꿔치기**도 함께 잡는다.
    """
    assert "1대" not in fragment, "표본이 1이면 하드코딩을 잡지 못한다"
    caveat = console_read_caveat(_round15_inventory(**axes))
    assert caveat is not None
    assert fragment in str(caveat["reason"]), caveat["reason"]


#: `ExistingFidRead.reason()`의 다섯 계수 절 — 여섯 보간 자리 전부에 1이 아닌 표본을 준다.
#: (보간 표현식, 생성자 인자, 기대 문구)
_R16_FID_REASON_COUNT_SAMPLES = (
    (
        "self.enumerated_count",
        {"attempted": True, "over_enumerated": True, "enumerated_count": 7, "child_count": 5},
        "열거된 슬롯 7개가 선언 총계 5개보다 많다",
    ),
    (
        "self.child_count",
        {"attempted": True, "child_count": 9, "unseen": 4},
        "선언 9개 중 4개를 열거하지 못했다",
    ),
    (
        "self.unseen",
        {"attempted": True, "child_count": 9, "unseen": 4},
        "선언 9개 중 4개를 열거하지 못했다",
    ),
    (
        "self.unusable_rows",
        {"attempted": True, "unusable_rows": 3},
        "슬롯 번호가 없거나 중복인 행 3개를 쓰지 못했다",
    ),
    (
        "self.unparsable_rows",
        {"attempted": True, "unparsable_rows": 6},
        "슬롯으로 해석되지 않는 행 6개가 섞여 있다",
    ),
    (
        "self.unreadable_fids",
        {"attempted": True, "unreadable_fids": 8},
        "열거된 슬롯 8개의 FID 값을 얻지 못했다",
    ),
)


def test_the_fid_reason_count_table_is_a_bijection_onto_the_production_interpolations():
    """[round16 HARD 규율 3] `reason()`에 계수 자리가 생기면 표도 늘어야 한다.

    표에서 행을 지우면 이 단정이 실패한다.
    """
    declared = tuple(sorted({expr for expr, _, _ in _R16_FID_REASON_COUNT_SAMPLES}))
    assert declared == _r16_reason_interpolations()


@pytest.mark.parametrize(
    "expression,kwargs,fragment",
    _R16_FID_REASON_COUNT_SAMPLES,
    ids=[expr for expr, _, _ in _R16_FID_REASON_COUNT_SAMPLES],
)
def test_every_fid_read_count_clause_reports_a_count_other_than_one(expression, kwargs, fragment):
    """[round16 M50] `patchplan.py:766`의 `{self.unparsable_rows}`를 `1`로 굳히면
    `self.unparsable_rows` 행이 실패한다. 형제 다섯 자리도 같은 단정을 받는다 —
    한 자리만 고치면 형제가 또 남는다(HARD 규율 1).

    여섯 계수를 서로 다른 값(7 · 5 · 9 · 4 · 3 · 6 · 8)으로 두어 자리 바꿔치기도 잡는다.
    """
    from server.vwx.patchplan import ExistingFidRead

    assert "1개" not in fragment, "표본이 1이면 하드코딩을 잡지 못한다"
    read = ExistingFidRead(**kwargs)
    assert read.complete is False
    assert fragment in read.reason(), read.reason()


# --- round17 결함 R17-A · 주소 바닥 게이트 (AddressGates) ---
#
# 실증(이 섹션 마지막 종단 테스트가 그대로 재현한다): 1단계가 준 유니버스 0 / 음수
# 주소가 `precheck_vectorworks_diff` payload → `_candidates_from_report` →
# `plan_addresses` → `render_addfixtures_plugin`까지 **아무 게이트 없이** 흘러
# `patch = { "0.507" }` · `patch = { "1.-3" }` 인 Lua가 사람 손에 갔다. 되돌릴 수
# 없는 쓰기 경로이므로 round17에서 `plan_addresses`에 `address_below_minimum`
# 배제를 넣었다(자동 보정 0건 — 값을 고쳐 통과시키지 않는다).
#
# **바닥만** 검사한다. 상한을 두지 않는 것은 누락이 아니라 판정이다:
# `server/prechk/patch.py`의 `normalize_address` 독스트링이 "per-universe channel
# capacity is unmeasured(ASSUMPTION-33) — inventing a ceiling would reject addresses
# the console accepts"라고 못박았고, 그 판정이 PRESERVE 경로의 원전이다. 아래
# `test_r17_no_ceiling_is_fabricated_above_the_universe_width`가 그 결정을 고정한다.


class _R17FloorRow(NamedTuple):
    universe: int
    address: int
    excluded: bool
    note: str


#: 콘솔 최소 인덱스 — 프로덕션 상수를 참조하지 않는 독립 리터럴.
_R17_MIN_INDEX_LITERAL = 1
#: 절대주소 역산 전제 폭 — **천장이 아니다**. 천장 없음을 단정하는 데만 쓴다.
_R17_WIDTH_LITERAL_FOR_CEILING_PROBE = 512

#: 유니버스·주소 바닥 경계 전수. 두 축을 각각 최소 인덱스 앞뒤 한 칸씩 훑고,
#: 폭 경계(512·513)는 **통과해야 한다**(천장 날조 금지)는 쪽으로 넣는다.
_R17_ADDRESS_FLOOR_ROWS: tuple[_R17FloorRow, ...] = (
    _R17FloorRow(-1, 1, True, "유니버스 음수"),
    _R17FloorRow(0, 1, True, "유니버스 0 — 콘솔 번호 체계에 없다"),
    _R17FloorRow(0, 507, True, "abs=-5 역산 실측값 — 전달물에 실렸던 바로 그 좌표"),
    _R17FloorRow(1, -3, True, "주소 음수 — DMX Address 직접 읽기 실측값"),
    _R17FloorRow(1, 0, True, "주소 0 — 미패치 sentinel 값이 좌표로 새어 나온 경우"),
    _R17FloorRow(0, 0, True, "두 축 동시 위반"),
    _R17FloorRow(-1, -1, True, "두 축 동시 음수"),
    _R17FloorRow(1, 1, False, "양쪽 바닥 정확히 — 통과해야 한다"),
    _R17FloorRow(1, 2, False, "바닥 바로 위"),
    _R17FloorRow(2, 1, False, "유니버스 바닥 바로 위"),
    _R17FloorRow(1, 512, False, "유니버스 폭 끝 — 천장 아님"),
    _R17FloorRow(1, 513, False, "폭 초과 — 천장을 날조하지 않으므로 통과한다"),
    _R17FloorRow(9, 1024, False, "큰 유니버스·큰 주소 — 상한 없음"),
)

#: 표에서 파생하지 않은 **독립** 커버리지 요구 — 두 축 각각 바닥 앞뒤 한 칸.
_R17_REQUIRED_FLOOR_COORDS = frozenset(
    {(_R17_MIN_INDEX_LITERAL + delta, 1) for delta in (-2, -1, 0, 1)}
    | {(1, _R17_MIN_INDEX_LITERAL + delta) for delta in (-4, -1, 0, 1)}
    | {
        (0, 507),
        (0, 0),
        (-1, -1),
        (1, _R17_WIDTH_LITERAL_FOR_CEILING_PROBE),
        (1, _R17_WIDTH_LITERAL_FOR_CEILING_PROBE + 1),
        (9, 2 * _R17_WIDTH_LITERAL_FOR_CEILING_PROBE),
    }
)


def test_r17_minimum_index_matches_the_preserve_path():
    """[round17 R17-A] `patchplan._MINIMUM_ADDRESS_INDEX`를 1에서 옮기거나
    PRESERVE 경로의 `_MINIMUM_INDEX`와 어긋나게 두면 실패한다.

    바닥값 사본을 두 계층에 두는 대신 **어긋남을 대조군으로 잡는다** — 비공개
    이름을 계층 넘어 import하지 않으면서 단일 진실을 유지하는 방법이다.
    """
    from server.prechk.patch import _MINIMUM_INDEX
    from server.vwx.patchplan import _MINIMUM_ADDRESS_INDEX

    assert _MINIMUM_ADDRESS_INDEX == _R17_MIN_INDEX_LITERAL
    assert _MINIMUM_ADDRESS_INDEX == _MINIMUM_INDEX


def test_r17_address_floor_table_covers_exactly_the_required_coordinates():
    """[round17 표 전수] 행을 하나라도 지우거나 중복시키면 실패한다."""
    coords = tuple((row.universe, row.address) for row in _R17_ADDRESS_FLOOR_ROWS)
    assert len(coords) == 13, "행수 리터럴 — 행 삭제/추가 감지"
    assert len(set(coords)) == len(coords), "같은 좌표가 두 번 들어갔다"
    assert set(coords) == _R17_REQUIRED_FLOOR_COORDS
    # 비공허성 — 배제·통과 두 결론이 모두 표에 있다(한쪽만 남기면 게이트가 공허해진다).
    assert {row.excluded for row in _R17_ADDRESS_FLOOR_ROWS} == {True, False}


@pytest.mark.parametrize("row", _R17_ADDRESS_FLOOR_ROWS, ids=lambda r: f"u{r.universe}a{r.address}")
def test_r17_plan_addresses_excludes_only_coordinates_below_the_console_minimum(row):
    """[round17 R17-A] `plan_addresses`의 바닥 검사를 지우면 배제 행이 계획으로
    남아 실패한다. 바닥을 `<=`로 한 칸 넓히면 `(1, 1)`·`(2, 1)` 행이 배제되어
    실패한다. 유니버스 축만 검사하도록 줄이면 `(1, -3)`·`(1, 0)` 행이,
    주소 축만 검사하도록 줄이면 `(0, 1)`·`(-1, 1)` 행이 실패한다.

    자동 보정 0건 — 살아남은 항목의 좌표는 **입력 그대로**여야 한다(값을 1로
    끌어올려 통과시키는 구현은 이 단정에서 잡힌다).
    """
    from server.vwx.patchplan import plan_addresses
    from server.vwx.verdicts import ADDRESS_BELOW_MINIMUM

    target = _candidate("a", row.universe, row.address, 101)
    plan = plan_addresses((target,), footprints={"a": 4}, occupied={})

    if row.excluded:
        assert plan.entries == (), row.note
        assert [exclusion.code for exclusion in plan.exclusions] == [ADDRESS_BELOW_MINIMUM]
        payload = plan.exclusions[0].to_dict()
        # 좌표는 관측된 사실이므로 싣는다 — 판독 실패 원문을 되싣는 것과 다르다.
        assert f"유니버스 {row.universe} 주소 {row.address}" in payload["reason"]
        assert payload["label"], "닫힌 어휘에 라벨이 등재되어야 한다"
    else:
        assert plan.exclusions == (), row.note
        (entry,) = plan.entries
        assert (entry.universe, entry.address) == (row.universe, row.address)
        assert entry.end_address == row.address + 4 - 1


def test_r17_no_ceiling_is_fabricated_above_the_universe_width():
    """[round17 R17-A 부작용 방지] 바닥 게이트를 넣으면서 512를 천장으로 삼으면 실패한다.

    **근거를 여기 남긴다 — 근거 없이 남으면 다음 사람이 "왜 상한이 없지"라며 넣는다.**

    원전은 PRESERVE 경로인 `server/prechk/patch.py:128-133`
    (:func:`server.prechk.patch.normalize_address` 독스트링)이고 원문은 이렇다:

        "There is deliberately NO upper bound. The per-universe channel capacity
        is unmeasured (``ASSUMPTION-33``), and inventing a ceiling would reject
        addresses the console accepts -- turning a working rig into a read
        failure. So this validation is definite about the FORM and the FLOOR
        only, and a large address parses."

    즉 무상한은 누락이 아니라 **판정**이다. 미실측(ASSUMPTION-33) 위에 천장을 지어내면
    ① PRESERVE 판정과 모순되고 ② 이미 고정된 "512 초과 구간이 그대로 계획되어 전달물로
    나간다"(이 파일 B절 뒤 `test_a_plan_span_may_cross_the_universe_boundary_unguarded`
    계열)를 깨며 ③ 이 SPEC이 여섯 번 자기정정한 과잉주장 유형을 반복한다.

    `server/vwx/address.py`의 `_UNIVERSE_WIDTH`(512)는 **절대주소 역산의 전제**이지
    채널 수용량 천장이 아니므로 여기 상한으로 재사용하지 않는다.
    """
    from server.vwx.patchplan import plan_addresses

    over = _R17_WIDTH_LITERAL_FOR_CEILING_PROBE + 1
    plan = plan_addresses((_candidate("a", 1, over, 101),), footprints={"a": 4}, occupied={})
    assert plan.exclusions == ()
    assert plan.entries[0].address == over
    # 훨씬 큰 주소·유니버스도 마찬가지 — 임의의 큰 값에서 천장이 생기지 않았음을 확인한다.
    far = plan_addresses(
        (_candidate("b", 99, 40 * _R17_WIDTH_LITERAL_FOR_CEILING_PROBE, 102),),
        footprints={"b": 4},
        occupied={},
    )
    assert far.exclusions == ()


#: (라벨, 유니버스, 주소, 폭, 기대 배제코드 또는 None) — 바닥 검사와 기존 `footprint <= 0`
#: 가드의 **상호작용 전수**. 바닥 검사가 루프 맨 앞이므로 `span` 산술이 아예 돌지 않는다.
_R17_FLOOR_FOOTPRINT_ROWS = (
    ("정상 좌표 · 폭 0", 1, 10, 0, "footprint_unknown"),
    ("정상 좌표 · 폭 음수", 1, 10, -4, "footprint_unknown"),
    ("정상 좌표 · 폭 1", 1, 10, 1, None),
    ("바닥 위반 · 폭 0", 0, 507, 0, "address_below_minimum"),
    ("바닥 위반 · 폭 정상", 0, 507, 4, "address_below_minimum"),
    ("주소 음수 · 폭 정상", 1, -3, 4, "address_below_minimum"),
)


@pytest.mark.parametrize(
    ("label", "universe", "address", "footprint", "expected_code"),
    _R17_FLOOR_FOOTPRINT_ROWS,
    ids=[row[0] for row in _R17_FLOOR_FOOTPRINT_ROWS],
)
def test_r17_floor_gate_and_footprint_guard_never_produce_a_backwards_span(
    label, universe, address, footprint, expected_code
):
    """[round17 R17-A · `end_address` 상호작용] 두 가드의 우선순위와 `end < start`
    불가능성을 함께 고정한다.

    · 바닥 위반은 폭과 무관하게 `address_below_minimum`이 먼저다 — 좌표가 성립하지
      않는 대상의 구간 산술은 애초에 의미가 없으므로 `span`을 계산하기 전에 끊는다.
    · 폭 0·음수는 기존 `footprint <= 0` 가드가 잡으므로 `end_address < address`인
      계획 항목은 **어느 경로로도 만들어지지 않는다**(round16 구간 경계 표의 전제).
    바닥 검사를 `footprint` 가드 뒤로 옮기면 "바닥 위반 · 폭 0" 행이 실패한다.
    `footprint <= 0`을 `< 0`으로 바꾸면 "정상 좌표 · 폭 0" 행이 실패한다.
    """
    from server.vwx.patchplan import plan_addresses

    plan = plan_addresses(
        (_candidate("a", universe, address, 101),), footprints={"a": footprint}, occupied={}
    )
    if expected_code is None:
        (entry,) = plan.entries
        assert entry.end_address >= entry.address, label
    else:
        assert plan.entries == (), label
        assert [exclusion.code for exclusion in plan.exclusions] == [expected_code]


def test_r17_floor_footprint_interaction_table_is_complete():
    """[round17 표 전수] 행 삭제 감지 — 두 가드의 조합이 모두 남아 있어야 한다."""
    assert len(_R17_FLOOR_FOOTPRINT_ROWS) == 6
    assert {row[4] for row in _R17_FLOOR_FOOTPRINT_ROWS} == {
        None,
        "footprint_unknown",
        "address_below_minimum",
    }
    # 바닥 위반 × (폭 정상 · 폭 0) 두 칸이 모두 있어야 우선순위가 확인된다.
    below = {row[3] for row in _R17_FLOOR_FOOTPRINT_ROWS if row[4] == "address_below_minimum"}
    assert below == {0, 4}


def test_r17_below_minimum_survives_alongside_normal_targets():
    """[round17 R17-A 비공허성] 같은 계획에 정상 대상과 바닥 위반 대상을 함께 넣으면
    위반만 빠지고 정상 대상은 좌표 그대로 남는다 — 배제가 계획 전체를 무너뜨리지 않는다.
    바닥 검사를 `continue` 없이 넣어 위반 대상까지 계획에 남기면 실패한다."""
    from server.vwx.patchplan import plan_addresses
    from server.vwx.verdicts import ADDRESS_BELOW_MINIMUM

    targets = (
        _candidate("bad", 0, 507, 101),
        _candidate("good", 1, 100, 102),
    )
    plan = plan_addresses(targets, footprints={"bad": 4, "good": 4}, occupied={})
    assert [entry.candidate_id for entry in plan.entries] == ["good"]
    assert plan.entries[0].address == 100
    assert [(x.candidate_id, x.code) for x in plan.exclusions] == [("bad", ADDRESS_BELOW_MINIMUM)]


def _r17_empty_console_inventory():
    from server.prechk.inventory import COMPLETE, Inventory

    return Inventory(
        path="Patch/Stages/1/Fixtures",
        child_count=0,
        enumerated_count=0,
        recovered_count=0,
        observed_count=0,
        missing_count=0,
        completeness=COMPLETE,
        recovery_boundary=None,
        index_domain_unknown=False,
        fixtures=(),
    )


def _r17_pipeline(csv_bytes: bytes):
    """1단계 판독부터 Lua 렌더까지 **툴이 실제로 밟는 순서 그대로** 돌린다.

    로컬 사본이나 헬퍼 재구현이 아니라 프로덕션 함수만 부른다 —
    `server/orchestrator/tools.py`의 `precheck_vectorworks_diff` ·
    `apply_vectorworks_patch`가 같은 순서로 이 함수들을 호출한다.
    """
    from server.vwx.address import resolve_all
    from server.vwx.columns import resolve_columns
    from server.vwx.diff import compare
    from server.vwx.luagen import LuaPatchEntry, render_addfixtures_plugin
    from server.vwx.patchplan import _candidates_from_report, plan_addresses
    from server.vwx.reader import read as read_vwx
    from server.vwx.report import build_vwx_report
    from server.vwx.rig import build_designed_rig

    read_result = read_vwx(csv_bytes)
    column_records, _column_failures, excluded = resolve_columns(list(read_result.records))
    resolved, address_failures = resolve_all(column_records)
    rig = build_designed_rig(resolved, candidate_count=len(column_records))
    payload = build_vwx_report(
        compare(rig, _r17_empty_console_inventory()),
        read_failures=tuple(address_failures),
        excluded_rows=tuple(excluded),
    ).to_dict()
    candidates = _candidates_from_report(payload)
    plan = plan_addresses(
        candidates, footprints={candidate.id: 4 for candidate in candidates}, occupied={}
    )
    lua = render_addfixtures_plugin(
        [
            LuaPatchEntry(
                console_type="Robe Robin MMX Spot",
                console_mode="Mode 1",
                fid=index + 1,
                name=f"MMX_{index + 1}",
                universe=entry.universe,
                address=entry.address,
            )
            for index, entry in enumerate(plan.entries)
        ]
    )
    return payload, plan, lua


#: (라벨, CSV 바이트, 1단계가 리포트에 싣는 좌표) — 좌표는 1단계 **현행 동작 기록**이며
#: 옳다는 판정이 아니다. 1단계 공개 계약은 이 SPEC의 §D Out of Scope다
#: (AC-AUTOPATCH-025) — 우리 책임은 "그 값으로 패치를 만들지 않는 것"이다.
_R17_REACHABILITY_CASES = (
    (
        "absolute_negative",
        b"Instrument Type,Absolute Address,Unit Number\nMMX,-5,101\n",
        (0, 507),
        "0.507",
    ),
    (
        "dmx_address_negative",
        b"Instrument Type,Universe,DMX Address,Unit Number\nMMX,1,-3,101\n",
        (1, -3),
        "1.-3",
    ),
)


def test_r17_reachability_case_table_is_complete():
    """[round17 표 전수] 도달성 사례 행을 지우면 실패한다."""
    assert len(_R17_REACHABILITY_CASES) == 2
    assert len({case[0] for case in _R17_REACHABILITY_CASES}) == 2
    # 두 사례는 **서로 다른 1단계 경로**여야 한다(절대주소 역산 · 직접 읽기).
    assert {case[2][0] for case in _R17_REACHABILITY_CASES} == {0, 1}


@pytest.mark.parametrize(
    ("label", "csv_bytes", "stage_one_coord", "forbidden_patch_token"),
    _R17_REACHABILITY_CASES,
    ids=[case[0] for case in _R17_REACHABILITY_CASES],
)
def test_r17_below_minimum_coordinates_never_reach_the_lua_deliverable(
    label, csv_bytes, stage_one_coord, forbidden_patch_token
):
    """[round17 R17-A 도달성 감지기] `plan_addresses`의 바닥 검사를 지우면 이 테스트가
    `patch = { "0.507" }`(또는 `"1.-3"`)를 렌더된 Lua에서 다시 발견해 실패한다.

    세 층을 한 번에 못박는다:
      1. **1단계는 여전히 그 좌표를 리포트에 싣는다** — 그게 §D 밖의 현행 동작이고,
         조용히 사라지면 조작자가 "왜 후보에 없지"를 알 수 없다(§0 2c② 정신).
      2. **패치 계층이 등재된 코드로 배제한다** — round17 이전에는 exclusions가
         0건이었다. 그 뒤집힘 자체를 여기서 단정한다.
      3. **전달물에는 그 좌표가 없다** — 사람이 콘솔에 임포트하는 Lua가 검사 대상이다.
    """
    from server.vwx.verdicts import ADDRESS_BELOW_MINIMUM

    payload, plan, lua = _r17_pipeline(csv_bytes)

    (row,) = payload["diffs"]["missing_in_console"]
    assert (row["universe"], row["address"]) == stage_one_coord, "1단계 동작이 바뀌었다"

    assert plan.entries == ()
    assert [exclusion.code for exclusion in plan.exclusions] == [ADDRESS_BELOW_MINIMUM]

    assert forbidden_patch_token not in lua, label
    assert "patch = {" not in lua, "계획이 비었으므로 렌더된 Lua에 patch 항목이 없어야 한다"


def test_r17_reachability_detector_is_not_vacuous_on_a_valid_address():
    """[round17 R17-A 비공허성] 같은 파이프라인에 정상 좌표를 넣으면 Lua에
    `patch = { "1.7" }`가 **실제로 나온다** — 위 테스트가 "언제나 비어 있다"를
    확인하는 공허한 검사가 아님을 같은 경로로 증명한다."""
    payload, plan, lua = _r17_pipeline(
        b"Instrument Type,Universe,DMX Address,Unit Number\nMMX,1,7,101\n"
    )
    (row,) = payload["diffs"]["missing_in_console"]
    assert (row["universe"], row["address"]) == (1, 7)
    assert plan.exclusions == ()
    assert [(entry.universe, entry.address) for entry in plan.entries] == [(1, 7)]
    assert 'patch = { "1.7" }' in lua


# ==========================================================================
# --- round17 점유자 전수 · 문장 형태 불변식 (SiblingOccupants) ---
#
# round17의 교훈은 **"게이트가 모듈 경계에서 멈춘다"**이다. 치명 5건 전부가 round15·16이
# 한 번도 뮤테이션하지 않은 모듈에 있었고, round16 게이트는 자기 도달 범위 안에서는
# 견고했다. 그래서 아래 두 축은 **`server/vwx/` 디렉터리를 훑어** 자리를 뽑는다 — 손으로
# 모듈 이름을 적지 않으므로 모듈이 늘어도 범위가 따라 늘어난다.
#
#   축 A (S17-03a·b) — **점유자를 보는 함수 전수**가 점유자를 구조화해 싣는다.
#   축 B (S17-04)    — **사람이 읽는 문자열을 조립하는 자리 전수**가 문장 형태를 지킨다.
# ==========================================================================

_R17_VWX_DIR = Path("server/vwx")

#: 점유자를 보는 함수의 표식 — 이 이름의 매개변수를 받으면 콘솔 점유 관측을 손에 쥔 것이다.
_R17_OCCUPANCY_INPUT = "console_fixtures"
#: 조작자에게 점유 판정을 내보내는 **보고 객체** 전수.
_R17_OCCUPANT_REPORT_CLASSES = ("PatchTargetExclusion", "VerificationResult")


def _r17_vwx_trees(overrides=None):
    """`server/vwx/` 전 모듈의 AST — 목록을 손으로 적지 않고 **디렉터리에서** 뽑는다.

    `overrides`가 있으면 그 모듈만 심어진 소스로 갈아끼운다(비공허성 대조군용).
    """
    import ast

    modules = iter_vwx_modules(_R17_VWX_DIR)
    assert modules, "server/vwx/ 모듈을 하나도 찾지 못했다 — 스캐너가 공허하다"
    overrides = overrides or {}
    return tuple(
        (
            vwx_module_label(path),
            ast.parse(overrides.get(vwx_module_label(path), path.read_text(encoding="utf-8"))),
        )
        for path in modules
    )


def _r17_report_builder_names(tree) -> set[str]:
    """보고 객체를 짓는 이름 전수 — 두 dataclass + **그것을 반환한다고 선언한** 헬퍼.

    헬퍼 이름(`_exclusion`)을 손으로 적지 않는다. 헬퍼를 새로 만들어 그쪽으로 우회해도
    반환 타입 선언이 남는 한 스캐너가 따라간다.
    """
    import ast

    names = set(_R17_OCCUPANT_REPORT_CLASSES)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.FunctionDef)
            and isinstance(node.returns, ast.Name)
            and node.returns.id in _R17_OCCUPANT_REPORT_CLASSES
        ):
            names.add(node.name)
    return names


def _r17_occupant_carrier_sites(overrides=None):
    """점유자를 **보는** 함수 안의 보고 생성 자리 전수와, 각각이 점유자를 싣는지.

    범위를 `apply.py`로 못 박지 않는다 — 다른 모듈이 `console_fixtures`를 받아 판정을
    내리기 시작하면 그 자리도 자동으로 이 표에 들어온다(모듈 경계에서 멈추지 않는다).
    """
    import ast

    rows = []
    for module_name, tree in _r17_vwx_trees(overrides):
        builders = _r17_report_builder_names(tree)
        for function in _r16_in_source_order(
            node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        ):
            arguments = function.args
            parameters = [
                argument.arg
                for argument in (
                    *arguments.posonlyargs,
                    *arguments.args,
                    *arguments.kwonlyargs,
                )
            ]
            if _R17_OCCUPANCY_INPUT not in parameters:
                continue
            for call in _r16_in_source_order(
                node
                for node in ast.walk(function)
                if isinstance(node, ast.Call) and getattr(node.func, "id", None) in builders
            ):
                rows.append(
                    (
                        module_name,
                        function.name,
                        call.func.id,
                        any(keyword.arg == "observed_occupants" for keyword in call.keywords),
                    )
                )
    return tuple(rows)


#: (모듈, 함수, 보고 생성자, 점유자를 싣는가) — 손으로 열거한다. 아래 전단사가 프로덕션과 맞춘다.
#: **네 번째 열은 전부 `True`여야 한다.** round16까지는 `screen_idempotent`의 다중 점유
#: 갈래가 `False`였고(단수 필드로 2대를 표현할 수 없었다) `screen_console_occupancy`는
#: 아예 필드를 넘기지 않았다 — 그 둘이 이 SPEC이 반복한 형제-갈래 면제였다.
_R17_OCCUPANT_CARRIER_SITES = (
    ("apply.py", "screen_console_occupancy", "_exclusion", True),
    ("apply.py", "screen_idempotent", "_exclusion", True),
    ("apply.py", "screen_idempotent", "_exclusion", True),
    ("apply.py", "screen_idempotent", "_exclusion", True),
    ("apply.py", "screen_idempotent", "_exclusion", True),
    ("apply.py", "screen_idempotent", "_exclusion", True),
    ("apply.py", "verify_patch", "VerificationResult", True),
    ("apply.py", "verify_patch", "VerificationResult", True),
)


def test_the_occupant_carrier_registry_is_a_bijection_onto_production():
    """[round17 S17-03a] 점유자 보고 자리 표가 `server/vwx/` **전 모듈**과 1:1이다.

    [round17 #S17-03a] 어느 갈래에서든 `observed_occupants=`를 지우면 네 번째 열이 어긋나
      실패한다 — 다중 점유 갈래도 예외가 아니다.
    [round17 #S17-03a] 점유자를 보는 함수에 갈래를 더하면 표에 행이 없어 실패한다.
    [round17 #S17-03a] 표에서 행을 지우면 실패한다(아래 행삭제 프로브가 전 행에 대해 확인).
    """
    produced = _r17_occupant_carrier_sites()
    assert produced == _R17_OCCUPANT_CARRIER_SITES, (
        "점유자 보고 자리가 표와 다르다 — 등록할 행:\n"
        + "\n".join(f"    {row!r}," for row in produced)
    )


def test_every_occupant_viewing_site_actually_carries_the_occupants():
    """[round17 S17-03a] **면제가 하나도 없다** — 네 번째 열이 전부 참이다.

    이 단정을 표와 따로 두는 이유: 표만 있으면 `False`를 정답으로 적어 면제를 규약으로
    승격시킬 수 있다. round16의 `fills_display` 열이 정확히 그 상태였다.
    """
    sites = _r17_occupant_carrier_sites()
    assert sites, "점유자를 보는 자리를 하나도 찾지 못했다 — 스캐너가 공허하다"
    offenders = [row for row in sites if row[3] is not True]
    assert offenders == [], offenders


def test_the_occupant_carrier_scanner_is_not_vacuous():
    """비공허성 — `observed_occupants=`를 지운 **프로덕션 사본**에서 스캐너가 실제로 잡는다.

    사본 적재 선례(`_load`/`_load_patchplan`/`_load_tools`)의 AST판이다. 스캐너가 늘 참을
    돌려주는 항진식이면 위 두 단정은 아무것도 막지 못한다.
    """
    # 앵커는 **유일**해야 한다 — 여러 곳에 맞으면 어디를 심었는지 모른 채 판정하게 된다.
    # 그래서 다중 점유 갈래의 사유 문장 끝줄에 붙여 유일하게 만든다. 그 갈래가 하필
    # round16까지 **면제**였던 자리다.
    anchor = (
        '                    " — 어느 것과 대조할지 확정할 수 없다.",\n'
        "                    observed_occupants=occupants,\n"
    )
    assert APPLY_SOURCE.count(anchor) == 1, "주입 앵커가 유일하지 않다"
    planted = APPLY_SOURCE.replace(
        anchor, '                    " — 어느 것과 대조할지 확정할 수 없다.",\n', 1
    )
    assert planted != APPLY_SOURCE

    sites = _r17_occupant_carrier_sites({"apply.py": planted})
    assert [row for row in sites if row[3] is not True], "심었는데도 스캐너가 잡지 못했다"
    assert sites != _R17_OCCUPANT_CARRIER_SITES


@pytest.mark.parametrize("index", range(len(_R17_OCCUPANT_CARRIER_SITES)))
def test_deleting_any_occupant_carrier_row_breaks_the_bijection(index: int):
    """행삭제 프로브 — 표에서 **어느 행을 지워도** 전단사가 깨진다."""
    shrunk = _R17_OCCUPANT_CARRIER_SITES[:index] + _R17_OCCUPANT_CARRIER_SITES[index + 1 :]
    assert shrunk != _r17_occupant_carrier_sites()


@pytest.mark.parametrize("index", range(len(_R16_DISPLAY_CELLS)))
def test_deleting_any_display_cell_row_breaks_the_bijection(index: int):
    """행삭제 프로브 — 관측 칸 표에서 어느 칸을 지워도 프로덕션 필드 목록과 어긋난다."""
    import dataclasses

    shrunk = _R16_DISPLAY_CELLS[:index] + _R16_DISPLAY_CELLS[index + 1 :]
    produced = tuple(
        (
            cls.__name__,
            field.name,
            "occupants" if field.name.endswith("occupants") else "resolved_name",
        )
        for cls in _r16_display_carrying_classes()
        for field in dataclasses.fields(cls)
        if field.name.startswith("observed_")
    )
    assert shrunk != produced


@pytest.mark.parametrize("index", range(len(_R17_OCCUPANT_KEYS)))
def test_deleting_any_occupant_key_row_breaks_the_bijection(index: int):
    """행삭제 프로브 — 점유자 키 표에서 어느 키를 지워도 `ConsoleFixture.to_dict()`와 어긋난다."""
    from server.vwx.apply import ConsoleFixture

    shrunk = _R17_OCCUPANT_KEYS[:index] + _R17_OCCUPANT_KEYS[index + 1 :]
    produced = tuple(
        ConsoleFixture(
            slot=1,
            universe=1,
            address=1,
            type_display="CD 5",
            mode_display="9 Mode 9",
            type_name=None,
            mode_name=None,
        ).to_dict()
    )
    assert shrunk != produced


@pytest.mark.parametrize("index", range(len(_R16_SCREEN_BRANCH_ROWS)))
def test_deleting_any_screen_branch_row_breaks_a_gate(index: int):
    """행삭제 프로브 — 갈래 표에서 어느 행을 지워도 **둘 중 한 게이트**가 깨진다.

    제외 갈래 행은 제외 사이트 전단사가, `no_occupant` 행은 `kept.append` 계수 게이트가 잡는다.
    한쪽만 보면 `no_occupant` 행이 조용히 사라질 수 있다.
    """
    import ast

    shrunk = _R16_SCREEN_BRANCH_ROWS[:index] + _R16_SCREEN_BRANCH_ROWS[index + 1 :]
    exclusion_table = tuple(
        (code, count >= 1) for _, code, _, _, count, _ in shrunk if code is not None
    )
    function = _r16_function_def(_r16_apply_tree(), "screen_idempotent")
    kept_appends = [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "append"
        and getattr(node.func.value, "id", None) == "kept"
    ]
    broken_exclusions = exclusion_table != _r16_production_exclusion_sites()
    broken_kept = len(kept_appends) != len([row for row in shrunk if row[1] is None])
    assert broken_exclusions or broken_kept


@pytest.mark.parametrize("index", range(len(_R16_VERIFY_BRANCH_ROWS)))
def test_deleting_any_verify_branch_row_breaks_the_bijection(index: int):
    """행삭제 프로브 — 검증 갈래 표에서 어느 행을 지워도 outcome 전단사가 깨진다."""
    shrunk = _R16_VERIFY_BRANCH_ROWS[:index] + _R16_VERIFY_BRANCH_ROWS[index + 1 :]
    assert (
        tuple(outcome for _, outcome, _, _, _ in shrunk) != _r16_production_verification_outcomes()
    )


# ---- S17-03a 형제 표면: 점유 구간 침입자도 구조화해 싣는다 -----------------------


def test_the_occupancy_intruder_travels_as_a_structured_occupant():
    """[round17 S17-03a] `screen_console_occupancy`도 점유자를 구조화해 싣는다.

    이 갈래는 문장에 슬롯·주소를 주므로 **정보가 가장 많은** 갈래였는데, 정작 타입·모드
    표시 원문은 문장에 담을 수 없어(§0 2b④) 어디에도 없었다.

    [round17 #S17-03a] `apply.py`의 `observed_occupants=(intruder,)`를 지우면 실패한다.
    """
    console = _console(_record(2, "1.3", "CD 5", "9 Mode 9"))
    targets = (_candidate("a", 1, 1, 101),)
    screened = screen_console_occupancy(
        targets,
        address_plan=AddressPlan(
            entries=(
                AddressPlanEntry(
                    candidate_id="a", universe=1, address=1, footprint=4, end_address=4
                ),
            )
        ),
        console_fixtures=console,
    )
    (exclusion,) = screened.exclusions
    assert exclusion.code == ADDRESS_ALREADY_OCCUPIED
    assert exclusion.observed_occupants == tuple(fixture.to_dict() for fixture in console)
    assert [occupant["type_display"] for occupant in exclusion.observed_occupants] == ["CD 5"]
    # 문장에는 좌표만 — 표시 원문은 구조화 칸에만 있다.
    assert "CD 5" not in exclusion.reason
    assert CD_TOKEN.search(exclusion.reason) is None


# ---- S17-03b 두 상태는 payload에서 구별된다 -----------------------------------


def _r17_two_occupants_exclusion():
    return _r16_screen(
        (
            _record(1, "1.1", _R16_LED_DISPLAY, _R16_MODE1_DISPLAY),
            _record(2, "1.1", _R16_LED_DISPLAY, _R16_MODE1_DISPLAY),
        )
    ).exclusions[0]


def _r17_unread_display_exclusion():
    return _r16_screen((_record(1, "1.1", None, None),)).exclusions[0]


def test_two_occupants_and_one_unreadable_occupant_are_distinguishable():
    """[round17 S17-03b] 같은 코드를 내는 두 상태가 **payload에서 갈린다**.

    round16까지 두 상태는 `(existing_fixture_identity_unconfirmed, None, None)`으로 **동일**한
    삼중항을 냈다 — 단수 표시 필드가 2대에서도 비고 미판독에서도 비기 때문이다. 조작자는
    "점유자가 둘이라 확정 못 한다"와 "하나인데 그 하나를 못 읽었다"를 구별할 수 없었다.
    이제 `len(observed_occupants)`가 가른다.

    [round17 #S17-03a] 다중 점유 갈래의 `observed_occupants=`를 `()`로 되돌리면 실패한다.
    """
    two = _r17_two_occupants_exclusion()
    unread = _r17_unread_display_exclusion()

    assert two.code == unread.code == EXISTING_IDENTITY_UNCONFIRMED
    assert len(two.observed_occupants) == 2
    assert len(unread.observed_occupants) == 1
    assert two.to_dict() != unread.to_dict()
    # 그리고 2대 쪽 payload는 **무엇이** 점유했는지 말한다 — 슬롯이 둘 다 들어 있다.
    assert [occupant["slot"] for occupant in two.observed_occupants] == [1, 2]
    assert "슬롯 1 · 2" in two.reason


def test_no_occupancy_sentence_points_at_a_field_by_name():
    """[round17 S17-03b] 포인터 문장을 **전 갈래에서** 지웠다 — 키 이름이 곧 포인터다.

    무조건 붙는 포인터는 값이 빈 상태에서도 "원문은 저 필드에 있다"고 말한다. 그 문장이
    두 상태를 같은 문장으로 만들었다.

    [round17 #S17-03b] 어느 갈래에든 `"관측된 원문은 … 필드에 있다"`를 되살리면 실패한다.
    """
    sentences = [exclusion.reason for exclusion in _r17_all_occupancy_exclusions()]
    sentences += [result.detail for result in _r17_all_verification_results()]
    assert sentences
    for sentence in sentences:
        assert "필드에 있다" not in sentence, sentence
        assert "observed_" not in sentence, sentence


def _r17_all_occupancy_exclusions():
    """갈래 표가 여는 **제외 갈래 전부**를 실제로 돌려 모은다."""
    collected = []
    for _, code, records, resolution_kind, _, _ in _R16_SCREEN_BRANCH_ROWS:
        if code is None:
            continue
        resolutions = (_r16_unresolved_resolution(),) if resolution_kind == "unresolved" else None
        collected.extend(
            _r16_screen(tuple(_record(*row) for row in records), resolutions=resolutions).exclusions
        )
    return collected


def _r17_all_verification_results():
    collected = []
    for _, _, records, read_complete, _ in _R16_VERIFY_BRANCH_ROWS:
        collected.extend(
            verify_patch(
                (_entry("a", 1, 1),),
                console_fixtures=_console(*(_record(*row) for row in records)),
                read_complete=read_complete,
            ).results
        )
    return collected


# ==========================================================================
# 축 B (S17-04) — 사람이 읽는 문자열을 **조립하는 자리 전수**
#
# 이 SPEC은 같은 형태 결함을 세 번 냈다(round15 N11 `..` · round16 S16-01 `. —` ·
# round17 S17-04 한 문장 대시 둘). 셋 다 **조각은 멀쩡하고 조립 결과가 깨진** 형태이고,
# 셋 다 한 자리씩만 고쳤다. 지금까지 형태 단정은 `test_autopatch_fid.py`의 `'..'` 하나뿐이었다.
# 여기서는 `server/vwx/` 전 모듈에서 문장을 조립하는 자리를 AST로 뽑아 전수에 건다.
# ==========================================================================


def _r17_text_skeleton(node):
    """문자열 조립 노드의 **정적 뼈대** — 보간 자리는 `{}`로 남긴다. 조립이 아니면 `None`."""
    import ast

    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else None
    if isinstance(node, ast.JoinedStr):
        return "".join(
            part.value if isinstance(part, ast.Constant) else "{}" for part in node.values
        )
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _r17_text_skeleton(node.left)
        right = _r17_text_skeleton(node.right)
        return None if left is None or right is None else left + right
    # [round18 R18-D] 조립기는 하나가 아니다 — 강등 조립기(`assemble_sentences_or_defect`)도
    # 같은 문장을 짓는다. 이름을 여기 손으로 적지 않고 **등기부**를 본다. 등기부 자체는
    # `test_r18_the_sentence_assembler_registry_is_a_bijection_onto_production`이 프로덕션과 맞춘다.
    if isinstance(node, ast.Call) and getattr(node.func, "id", None) in _R18_SENTENCE_ASSEMBLERS:
        return " ".join(_r17_text_skeleton(arg) or "{}" for arg in node.args)
    return None


def _r17_is_human_sentence(text) -> bool:
    """사람이 읽는 문장인가 — 공백이 있고, 마침표로 끝나거나 문장 구두점을 품는다."""
    if text is None or " " not in text:
        return False
    return text.rstrip().endswith(".") or " — " in text or ". " in text


def _r17_sentence_sites(overrides=None):
    """`server/vwx/` 전 모듈에서 문장을 조립해 **이름 붙여 내보내는** 자리 전수.

    세 형태를 본다: dict 리터럴의 값 · 호출의 키워드 인자 · 이름에 대입. 어느 쪽이든
    "이 문자열이 어떤 이름으로 사람에게 나가는가"가 남는다.
    """
    import ast

    sites = []
    for module_name, tree in _r17_vwx_trees(overrides):
        for node in _r16_in_source_order(
            item for item in ast.walk(tree) if isinstance(item, (ast.Dict, ast.Call, ast.Assign))
        ):
            if isinstance(node, ast.Dict):
                pairs = [
                    (key.value, value)
                    for key, value in zip(node.keys, node.values, strict=True)
                    if isinstance(key, ast.Constant) and isinstance(key.value, str)
                ]
            elif isinstance(node, ast.Call):
                pairs = [(keyword.arg, keyword.value) for keyword in node.keywords if keyword.arg]
            else:
                pairs = [
                    (getattr(target, "id", None) or getattr(target, "attr", None), node.value)
                    for target in node.targets
                ]
            for name, value in pairs:
                if name is None:
                    continue
                skeleton = _r17_text_skeleton(value)
                if _r17_is_human_sentence(skeleton):
                    sites.append((module_name, name, skeleton))
    return tuple(sites)


#: (모듈, 이름) — 사람이 읽는 문장이 나가는 **표면** 전수. 손으로 열거하고 아래가 맞춘다.
#: 자리 **개수**는 고정하지 않는다 — 개수는 아래 형태 게이트가 자리마다 직접 검사하므로,
#: 표는 "어느 모듈의 어느 이름으로 문장이 나가는가"만 고정한다.
_R17_SENTENCE_SURFACES = (
    ("address.py", "ABSOLUTE_BACK_CALCULATED_PREMISE_NOTE"),
    ("address.py", "warning_detail"),
    ("apply.py", "END_TO_END_UNVERIFIED"),
    ("apply.py", "NO_AUTO_CORRECTION"),
    ("apply.py", "PLUGIN_EXIT_IS_NOT_SUCCESS"),
    # [round19 major#4] `_unresolved_type_exclusion`의 **기본** 사유. 하드 스톱은 이 문장을
    # 쓰지 않고 `TypeResolution.reason`을 그대로 옮긴다 — 확인 경로가 없는 상태를
    # "확인 대기"로 적지 않기 위해서다.
    ("apply.py", "TYPE_CONFIRMATION_PENDING_REASON"),
    ("apply.py", "ZERO_CREATED_GUIDANCE"),
    ("apply.py", "_INDEX_DOMAIN_CLAUSE"),
    ("apply.py", "detail"),
    ("apply.py", "reason"),
    ("columns.py", "detail"),
    ("diff.py", "FID_CID_UNREACHABLE_REASON"),
    ("diff.py", "reason"),
    # [round24 후속] MVR 판독 실패 사유. 컨테이너 아님 · 장면 XML 부재/파손 ·
    # GDTF 미동봉 · 주소 비정수 다섯 갈래가 서로 다른 문장을 내고, 넷은 조작자가
    # **파일을 고쳐야** 하는 사건이라 무엇이 없는지 정확히 말해야 한다.
    # [round24 후속] 인테이크는 **질문**을 낸다 — 오류 문구가 아니라 사용자가 답할 수
    # 있는 물음이다. `prompt`는 묻는 말, `why`는 왜 필요한지, `detail`은 자동으로 채운
    # 값의 근거다. 셋 다 사람이 읽고 판단하는 표면이라 같은 규율을 받는다.
    ("intake.py", "detail"),
    ("intake.py", "prompt"),
    ("intake.py", "why"),
    # [round24 후속] 콘솔에서 직접 고르게 할 때의 안내와 관측 사유.
    # `detail`은 무엇이 바뀌었는지(또는 왜 판정할 수 없는지), `poll_note`는 서버가
    # 얼마나 자주 보는지 — 둘 다 사람이 읽고 다음 행동을 정하는 표면이다.
    ("librarywatch.py", "detail"),
    ("librarywatch.py", "poll_note"),
    ("mvr.py", "detail"),
    # [round24 후속] 「세션 착수 전에 끝내라」 — 조달 단계 전부에 붙는 고지다.
    # 이 문장이 빠지면 조작자가 세션 중에 라이브러리를 늘려 그 세션의 판정을 깨뜨린다
    # (round20 세션 GO 조건 ①).
    ("typesource.py", "BEFORE_SESSION_NOTE"),
    ("patchplan.py", "IRREVERSIBLE_WARNING"),
    # [round18 R18-A] `_FidRangeParse.defect` — `fid_range` 입력의 결함 사유가
    # 조작자에게 나가는 표면. 형식·바닥·순서 세 갈래가 서로 다른 문장을 낸다.
    ("patchplan.py", "defect"),
    ("patchplan.py", "reason"),
    ("reader.py", "detail"),
    ("report.py", "address_collision"),
    ("report.py", "missing_in_console"),
    ("report.py", "quantity_mismatch"),
    ("rig.py", "detail"),
    # [round19 major#5] `typemap._resolve_one`의 사유는 전부 **모듈 상수**가 됐다 —
    # 그래서 이전 판의 `("typemap.py", "reason")`(= 갈래 안에 박힌 리터럴 조립) 행이
    # 프로덕션에서 사라졌다. 사유가 상수라야 "확인 대기를 말하는 갈래"를 소스에서
    # 기계적으로 셀 수 있고, 그 전수 없이는 새 갈래가 게이트를 조용히 빠져나간다.
    ("typemap.py", "ALIAS_RESOLVED_REASON"),
    ("typemap.py", "CANDIDATES_PRESENTED_REASON"),
    ("typemap.py", "FOOTPRINT_DESCOPE_REASON"),
    # [round25 R24-1 · SentenceReach] 점유폭 불일치 사유가 **원인별로** 갈렸다 —
    # 타입 미검증과 채널 계수 미판독은 조작자의 조치가 다르므로 문장도 따로다.
    ("typemap.py", "FOOTPRINT_MISMATCH_CHANNEL_COUNTS_UNREAD_REASON"),
    ("typemap.py", "FOOTPRINT_MISMATCH_CHOOSABLE_REASON"),
    ("typemap.py", "FOOTPRINT_MISMATCH_TYPE_UNVERIFIED_REASON"),
    ("typemap.py", "FOOTPRINT_MISMATCH_UNVERIFIED_REASON"),
    ("typemap.py", "FOOTPRINT_UNMATCHABLE_REASON"),
    # [round21 R20-D] 폐기 축 사유 — 절단·판독실패와 **다른 조치**를 가리키므로 문장도
    # 따로다. 어느 쪽 문장을 빌려 써도 payload가 관측 사실을 거짓으로 말한다.
    ("typemap.py", "LIBRARY_ROWS_DISCARDED_REASON"),
    ("typemap.py", "LIBRARY_TRUNCATED_REASON"),
    ("typemap.py", "LIBRARY_UNREADABLE_REASON"),
    ("typemap.py", "MODE_ABSENT_REASON"),
    ("typemap.py", "TYPE_ABSENT_REASON"),
    ("typemap.py", "VACUOUS_TYPE_KEY_REASON"),
)


def test_the_sentence_surface_registry_is_a_bijection_onto_production():
    """[round17 S17-04] 문장 표면 표가 `server/vwx/` **전 모듈**과 1:1이다.

    새 모듈이나 새 표면으로 사람이 읽는 문장을 내보내면 표 없이는 통과하지 못한다 —
    round17이 명명한 "게이트가 모듈 경계에서 멈춘다"를 이 축에서 닫는 장치다.
    표에서 행을 지워도 실패한다(아래 행삭제 프로브가 전 행 확인).
    """
    produced = tuple(sorted({(module, name) for module, name, _ in _r17_sentence_sites()}))
    assert produced == tuple(sorted(_R17_SENTENCE_SURFACES)), (
        "문장 표면이 표와 다르다 — 등록할 행:\n"
        + "\n".join(f'    ("{module}", "{name}"),' for module, name in produced)
    )


@pytest.mark.parametrize("index", range(len(_R17_SENTENCE_SURFACES)))
def test_deleting_any_sentence_surface_row_breaks_the_bijection(index: int):
    """행삭제 프로브 — 문장 표면 표에서 어느 행을 지워도 프로덕션과 어긋난다."""
    shrunk = _R17_SENTENCE_SURFACES[:index] + _R17_SENTENCE_SURFACES[index + 1 :]
    produced = tuple(sorted({(module, name) for module, name, _ in _r17_sentence_sites()}))
    assert tuple(sorted(shrunk)) != produced


def test_every_assembled_sentence_in_vwx_keeps_its_shape():
    """[round17 S17-04] 조립 자리 **전수**가 형태 불변식을 지킨다 — 프로덕션 판정자로 잰다.

    판정은 `patchplan.sentence_shape_violation`이 한다. 테스트가 규칙 사본을 들고 있으면
    프로덕션 규칙을 느슨하게 바꿔도 아무도 실패하지 않는다.

    보간 자리는 중립 토큰으로 채운다 — 값에 무엇이 오든 **뼈대가** 만드는 형태 결함
    (`..` · `. —` · 이중공백 · 한 문장 대시 둘)을 잡는 것이 목적이다.
    """
    from server.vwx.patchplan import sentence_shape_violation

    sites = _r17_sentence_sites()
    assert len(sites) >= len(_R17_SENTENCE_SURFACES), "조립 자리를 표면 수보다 적게 찾았다"
    offenders = [
        (module, name, _r17_skeleton_violation(skeleton), skeleton)
        for module, name, skeleton in sites
        if _r17_skeleton_violation(skeleton) is not None
    ]
    assert offenders == [], offenders
    # 판정자가 프로덕션 것임을 같은 테스트에서 고정한다 — 사본 규칙이면 이 단정이 깨진다.
    assert _r17_skeleton_violation("가 — 나 — 다.") == sentence_shape_violation(
        "가 — 나 — 다.", require_terminal=False
    )


def _r17_skeleton_violation(skeleton: str):
    """정적 뼈대의 형태 위반 — **프로덕션 판정자**로 잰다.

    뼈대는 아직 이어 붙기 전 조각이라 종결 규칙만 면제한다. 나머지(`..` · `. —` ·
    이중공백 · 한 문장 대시 둘)는 조각에도 그대로 성립해야 한다.
    """
    from server.vwx.patchplan import sentence_shape_violation

    return sentence_shape_violation(skeleton.replace("{}", "1"), require_terminal=False)


def test_the_sentence_shape_gate_is_not_vacuous():
    """비공허성 — 대시 둘을 심은 **프로덕션 사본**에서 게이트가 실제로 잡는다.

    심는 대상은 round17 S17-04가 실제로 낸 형태다: 대시를 품은 조각을 대시 있는 문장에
    끼워 넣은 조립. 심는 자리는 `build_patch_plan`의 사유 조립부 — 실제로 사람에게
    나가는 문자열을 짓는 자리다.
    """
    patchplan_source = Path("server/vwx/patchplan.py").read_text(encoding="utf-8")
    anchor = 'f"기존 FID 사전검사가 불완전하다 — {existing_read.reason()}.",'
    assert patchplan_source.count(anchor) == 1, "주입 앵커가 유일하지 않다"
    planted = patchplan_source.replace(
        anchor,
        'f"기존 FID 사전검사가 불완전하다 — 스냅샷이 자기모순이다 — {existing_read.reason()}.",',
        1,
    )
    assert planted != patchplan_source

    clean = [skeleton for module, _, skeleton in _r17_sentence_sites() if module == "patchplan.py"]
    infected = [
        skeleton
        for module, _, skeleton in _r17_sentence_sites({"patchplan.py": planted})
        if module == "patchplan.py"
    ]
    assert all(_r17_skeleton_violation(text) is None for text in clean)
    assert any(_r17_skeleton_violation(text) is not None for text in infected), (
        "심었는데도 형태 게이트가 잡지 못했다"
    )


def test_assemble_sentences_refuses_a_broken_shape():
    """[round17 S17-04] 조립기는 깨진 문장을 **사람에게 내보내지 않고 즉시 실패한다**.

    조용히 나가면 이 SPEC이 일곱 라운드 반복한 대로 다음 감사에서야 발견된다.
    """
    import pytest as _pytest

    from server.vwx.patchplan import assemble_sentences

    assert assemble_sentences("앞 문장이다.", "", "뒤 문장이다.") == "앞 문장이다. 뒤 문장이다."
    with _pytest.raises(ValueError):
        assemble_sentences("끝난 문장이다.", "— 대시로 시작한다.")
    with _pytest.raises(ValueError):
        assemble_sentences("한 문장에 — 대시가 — 둘이다.")
    with _pytest.raises(ValueError):
        assemble_sentences("종결되지 않았다")


def test_every_human_sentence_produced_by_the_apply_surface_keeps_its_shape():
    """[round17 S17-04] 정적 뼈대만이 아니라 **실제로 나간 문자열**도 형태를 지킨다.

    보간 값이 붙어야 드러나는 결함(round15 N11의 `..`가 그랬다)은 뼈대만 봐서는 안 보인다.
    """
    from server.vwx.patchplan import sentence_shape_violation

    produced = [exclusion.reason for exclusion in _r17_all_occupancy_exclusions()]
    produced += [result.detail for result in _r17_all_verification_results()]
    produced += [
        str(guidance)
        for report in (
            verify_patch(
                (_entry("a", 1, 1),),
                console_fixtures=_console(),
            ),
        )
        for guidance in report.guidance
    ]
    assert len(produced) >= 10, "표본이 너무 적어 공허하다"
    offenders = [
        (sentence_shape_violation(text), text)
        for text in produced
        if sentence_shape_violation(text) is not None
    ]
    assert offenders == [], offenders


# --- round17 _single_unambiguous 순서 의존성 (AmbiguityGates) ---
#
# [round17 치명 #3 = round11 N06 재개방] `apply._single_unambiguous`의 폴스루
# `candidates[0] if len(candidates) == 1 else None`을 `>= 1`로 바꿔도 5,690건이 전부
# 통과했다. 같은 함수 20줄 위 `len(by_name) != 1 or len(by_index) != 1`은 KILLED였다 —
# **한 함수 안에서 갈래 하나만 게이트**였다. 이 절은 그 함수의 (by_name, by_index) 격자를
# 전수로 채우고, 후보 2건 갈래에는 **열거 순서 역전 불변**을 단정한다.

_R17_INDEX_FORM = "FixtureType 3"


class _SingleUnambiguousRow(NamedTuple):
    by_name: int
    by_index: int
    #: `by_name[0] is by_index[0]`인가 — 두 목록이 **둘 다 비어 있지 않은** 칸에서만 의미가
    #: 있다(그 밖에는 `None`). 이 축이 없으면 `len(by_index) != 1` → `< 1` 뮤테이션이
    #: 살아남는다: 그 뮤턴트는 교차 점검(`is`)까지 내려가야 관측이 갈리기 때문이다.
    same_target: bool | None
    types: tuple
    display: str
    #: 확정된 타입 이름 · 모호하면 `None`.
    expected: str | None


def _r17_type(index: int, name: str) -> LibraryType:
    return LibraryType(index=index, name=name, modes=(LibraryMode(index=1, name=MODE_1),))


#: `_single_unambiguous`의 (by_name, by_index, same_target) **전수 격자**. `by_name`은 표시
#: 문자열과 이름이 정확히 같은 타입 수, `by_index`는 `FixtureType <n>` 형태가 지목하는 인덱스를
#: 가진 타입 수다. 둘이 동시에 성립하려면 라이브러리에 `"FixtureType 3"`이라는 **이름**이
#: 있어야 한다 — `_X`가 그 역할(이름도 맞고 인덱스도 맞다)이다.
_X = _r17_type(3, _R17_INDEX_FORM)  # 이름 일치 + 인덱스 일치 (교차 점검이 True가 되는 유일한 대상)
_N2 = _r17_type(7, _R17_INDEX_FORM)  # 이름만 일치
_N3 = _r17_type(8, _R17_INDEX_FORM)  # 이름만 일치
_I2 = _r17_type(3, "Alpha")  # 인덱스만 일치
_I3 = _r17_type(3, "Beta")  # 인덱스만 일치

_R17_SINGLE_UNAMBIGUOUS_ROWS = (
    _SingleUnambiguousRow(0, 0, None, (_r17_type(1, MMX),), "Nonexistent Type", None),
    _SingleUnambiguousRow(1, 0, None, (_r17_type(1, MMX), _r17_type(3, LED)), LED, LED),
    _SingleUnambiguousRow(2, 0, None, (_r17_type(3, LED), _r17_type(9, LED)), LED, None),
    _SingleUnambiguousRow(0, 1, None, (_I2,), _R17_INDEX_FORM, "Alpha"),
    _SingleUnambiguousRow(0, 2, None, (_I2, _I3), _R17_INDEX_FORM, None),
    _SingleUnambiguousRow(1, 1, True, (_X,), _R17_INDEX_FORM, _R17_INDEX_FORM),
    _SingleUnambiguousRow(1, 1, False, (_N2, _I2), _R17_INDEX_FORM, None),
    # 이 행이 `len(by_index) != 1` → `< 1` 뮤턴트를 죽인다: 그 뮤턴트는 교차 점검까지
    # 내려가 `by_index[0]`(= `_X`)를 확정하지만, 라이브러리 순서를 뒤집으면 다른 것을 고른다.
    _SingleUnambiguousRow(1, 2, True, (_X, _I2), _R17_INDEX_FORM, None),
    _SingleUnambiguousRow(1, 2, False, (_N2, _I2, _I3), _R17_INDEX_FORM, None),
    # 이 행이 `len(by_name) != 1` → `< 1` 뮤턴트를 죽인다(같은 구조의 형제 갈래).
    _SingleUnambiguousRow(2, 1, True, (_X, _N2), _R17_INDEX_FORM, None),
    _SingleUnambiguousRow(2, 1, False, (_N2, _N3, _I2), _R17_INDEX_FORM, None),
    _SingleUnambiguousRow(2, 2, True, (_X, _N2, _I2), _R17_INDEX_FORM, None),
    _SingleUnambiguousRow(2, 2, False, (_N2, _N3, _I2, _I3), _R17_INDEX_FORM, None),
)


def _r17_assert_su_table_shape(rows: tuple[_SingleUnambiguousRow, ...]) -> None:
    """행 삭제 프로브 — (by_name, by_index) **격자가 빠짐없이** 채워져 있어야 한다.

    리터럴 행 수를 세지 않는다: 두 축의 최댓값이 2(모호)까지 닿고 그 곱집합이 전부 등장해야
    하며, **두 목록이 모두 비어 있지 않은 모든 칸**은 교차 점검이 성립하는 갈래와 성립하지
    않는 갈래를 다 가져야 한다. 어느 행을 지워도 이 중 하나가 깨진다.
    """
    cells = {(row.by_name, row.by_index) for row in rows}
    highest_name = max(row.by_name for row in rows)
    highest_index = max(row.by_index for row in rows)
    assert highest_name >= 2
    assert highest_index >= 2
    assert cells == {
        (name_count, index_count)
        for name_count in range(highest_name + 1)
        for index_count in range(highest_index + 1)
    }
    for cell in cells:
        targets = {row.same_target for row in rows if (row.by_name, row.by_index) == cell}
        if min(cell) >= 1:
            assert targets == {True, False}, cell
        else:
            assert targets == {None}, cell
    assert {row.expected is None for row in rows} == {False, True}
    assert len(rows) == len(cells) + len([cell for cell in cells if min(cell) >= 1])


def _r17_resolved_type_name(row: _SingleUnambiguousRow, *, reverse: bool = False) -> str | None:
    """표시 문자열을 **프로덕션 경로**(`read_console_fixtures`)로 확정해 이름만 꺼낸다.

    [round25 R24-2] 선언 총계를 채운다. 이 격자가 재는 축은 **후보 계수**(by_name ×
    by_index)이지 목록 완전성이 아니다 — 총계를 비우면 `(0, 1)` 칸이 완전성 가드에
    먼저 걸려 `None`이 되고, 격자는 계수 판정을 재지 못한 채 그 칸만 색이 바뀐다.
    """
    types = tuple(reversed(row.types)) if reverse else row.types
    observed = read_console_fixtures(
        _inventory(_record(1, "1.5", row.display, None)),
        library=FixtureTypeLibrary(
            types=types,
            available=True,
            child_count=len(types),
            enumerated_count=len(types),
            returned_row_count=len(types),
        ),
    )
    return observed[0].type_name


class TestRound17SingleUnambiguous:
    """[round17 #3] `apply._single_unambiguous` 격자 전수 + 순서 역전 불변."""

    def test_r17_single_unambiguous_candidate_count_table_holds(self):
        """[round17 #3] `apply.py`의 `len(by_name) != 1` · `len(by_index) != 1` ·
        `len(candidates) == 1`을 각각 `>= 1` · `< 1` · `== 2`로 바꾸면 실패한다.

        `by_index` 갈래는 round17 감사에서 SURVIVED였다 — 한 줄 안에서도 갈래가 갈렸다.
        `!= 1` → `< 1` 뮤턴트는 교차 점검(`by_name[0] is by_index[0]`)까지 내려가야 관측이
        갈리므로, 표는 **두 목록이 모두 비어 있지 않은 칸마다** 교차 점검 성립/불성립 두
        갈래를 다 갖는다.
        """
        for row in _R17_SINGLE_UNAMBIGUOUS_ROWS:
            assert _r17_resolved_type_name(row) == row.expected, row
            # 열거 순서를 뒤집어도 같은 판정이다 — 모호성 판정의 정의이자, 첫 원소를 집는
            # 모든 뮤턴트가 통과할 수 없는 단정이다.
            assert _r17_resolved_type_name(row, reverse=True) == row.expected, row

            # 표의 `same_target` 열이 실제 라이브러리 구성과 일치함을 프로덕션 규칙으로 확인한다.
            by_name = [entry for entry in row.types if entry.name == row.display]
            by_index = (
                [entry for entry in row.types if entry.index == 3]
                if row.display == _R17_INDEX_FORM
                else []
            )
            assert (len(by_name), len(by_index)) == (row.by_name, row.by_index), row
            if by_name and by_index:
                assert (by_name[0] is by_index[0]) is row.same_target, row
            else:
                assert row.same_target is None, row

    def test_r17_single_unambiguous_table_row_deletion_is_detected(self):
        _r17_assert_su_table_shape(_R17_SINGLE_UNAMBIGUOUS_ROWS)
        for index in range(len(_R17_SINGLE_UNAMBIGUOUS_ROWS)):
            pruned = tuple(
                row
                for position, row in enumerate(_R17_SINGLE_UNAMBIGUOUS_ROWS)
                if position != index
            )
            with pytest.raises(AssertionError):
                _r17_assert_su_table_shape(pruned)

    def test_r17_two_fallthrough_candidates_are_order_invariant(self):
        """[round17 #3] `apply.py`의 `candidates[0] if len(candidates) == 1 else None`을
        `>= 1`로 바꾸면 실패한다.

        이름이 같은 타입이 둘 있고 **모드 구성이 다르면**, `>= 1` 뮤턴트는 열거 순서상 첫
        타입을 확정한다 — 순서를 뒤집으면 모드 확정이 갈리고 배제 코드가
        `already_patched_identical`(대상이 사라진다)과 `existing_fixture_identity_unconfirmed`
        사이에서 뒤집힌다. round11 N06: *모호성 판정이 순서에 의존하면 그것은 판정이 아니다.*
        """
        first = LibraryType(index=3, name=LED, modes=(LibraryMode(index=1, name=MODE_1),))
        second = LibraryType(index=9, name=LED, modes=(LibraryMode(index=1, name=MODE_2),))
        plan = AddressPlan(entries=(_planned("c1", 1, 5),))

        verdicts = []
        for types in ((first, second), (second, first)):
            observed = read_console_fixtures(
                _inventory(_record(1, "1.5", LED, MODE_1)),
                library=FixtureTypeLibrary(types=types, available=True),
            )
            assert observed[0].type_name is None, types
            assert observed[0].identity_resolved is False, types

            screened = screen_idempotent(
                [_candidate("c1", 1, 5, 101)],
                address_plan=plan,
                resolutions=[_resolution("c1")],
                console_fixtures=observed,
            )
            assert screened.entries == ()
            codes = [exclusion.code for exclusion in screened.exclusions]
            assert codes == [EXISTING_IDENTITY_UNCONFIRMED], types

            verified = verify_patch([_entry("c1", 1, 5)], console_fixtures=observed)
            assert [result.outcome for result in verified.results] == [
                VERIFICATION_IDENTITY_UNCONFIRMED
            ], types
            verdicts.append((codes, [result.outcome for result in verified.results]))

        # 순서를 뒤집어도 **같은 판정**이다 — 이것이 모호성 판정의 정의다.
        assert verdicts[0] == verdicts[1]

    def test_r17_two_occupants_are_never_reduced_to_the_first(self):
        """[round17 HARD 1] `apply.py` `screen_idempotent`의 `len(occupants) > 1` 갈래를 없애고
        `occupants[0]`으로 바로 가면 실패한다 — 첫 점유자가 우리와 같으면 `이미 했음`으로
        삼켜 두 번째 점유자를 못 본 채 넘긴다(round11 N10).
        """
        matching = _record(1, "1.5", LED, MODE_1)
        other = _record(2, "1.5", MMX, MODE_1)
        plan = AddressPlan(entries=(_planned("c1", 1, 5),))

        codes = []
        for records in ((matching, other), (other, matching)):
            screened = screen_idempotent(
                [_candidate("c1", 1, 5, 101)],
                address_plan=plan,
                resolutions=[_resolution("c1")],
                console_fixtures=_console(*records),
            )
            assert screened.entries == ()
            codes.append([exclusion.code for exclusion in screened.exclusions])

        assert codes[0] == [EXISTING_IDENTITY_UNCONFIRMED]
        assert codes[0] == codes[1]
        assert ALREADY_PATCHED_IDENTICAL not in codes[0]

        # 비공허성 — 점유자가 **그 한 대**뿐이면 정상적으로 멱등 판정이 나온다.
        alone = screen_idempotent(
            [_candidate("c1", 1, 5, 101)],
            address_plan=plan,
            resolutions=[_resolution("c1")],
            console_fixtures=_console(matching),
        )
        assert [exclusion.code for exclusion in alone.exclusions] == [ALREADY_PATCHED_IDENTICAL]

    def test_r17_verify_with_two_occupants_is_order_invariant(self):
        """[round17 HARD 1] `apply.py` `verify_patch`의 `len(found) > 1` 갈래를 없애면 실패한다.

        같은 줄의 `found[0] if len(found) == 1 else None`을 `>= 1`로 바꾸는 것은 위 `> 1`
        갈래가 먼저 `continue`하므로 **의미상 동등 뮤턴트**다(`occupant`가 쓰이지 않는다).
        그래서 이 테스트는 그 술어가 아니라 **판정과 순서 불변**을 고정한다.
        """
        matching = _record(11, "1.5", LED, MODE_1)
        other = _record(22, "1.5", MMX, MODE_1)

        shapes = []
        for records in ((matching, other), (other, matching)):
            verified = verify_patch([_entry("c1", 1, 5)], console_fixtures=_console(*records))
            result = verified.results[0]

            assert result.outcome == VERIFICATION_IDENTITY_UNCONFIRMED, records
            assert result.observed_type is None, records
            assert result.observed_mode is None, records
            assert verified.created_count == 0, records
            # 사유는 관측된 **두 슬롯 전부**를 지목한다 — 열거 순서와 무관한 집합 성질이다.
            assert "11" in result.detail, records
            assert "22" in result.detail, records
            shapes.append((result.outcome, result.observed_type, result.observed_mode))

        assert shapes[0] == shapes[1]

        # 비공허성 — 한 대면 관측으로 확정된다.
        alone = verify_patch([_entry("c1", 1, 5)], console_fixtures=_console(matching))
        assert alone.results[0].outcome == VERIFICATION_OBSERVED

    def test_r17_two_intruders_yield_an_observed_one_and_an_order_invariant_verdict(self):
        """[round17 HARD 1] `apply.py` `screen_console_occupancy`의
        `next((fixture ... if planned.address < fixture.address <= planned.end_address), None)`에서
        구간 술어를 지우면 실패한다 — 구간 **밖** 픽스처가 사유에 지목된다.

        점유 판정 자체는 순서에 무관해야 하고, 사유가 지목하는 픽스처는 **실제로 구간 안에
        있는 것**이어야 한다(둘 중 어느 것이든 무방하다 — 하나라도 있으면 제외가 맞다).
        """
        inside_low = _record(1, "1.8", LED, MODE_1)
        inside_high = _record(2, "1.12", LED, MODE_1)
        outside = _record(3, "1.777", LED, MODE_1)
        plan = AddressPlan(
            entries=(
                AddressPlanEntry(
                    candidate_id="c1", universe=1, address=5, footprint=16, end_address=20
                ),
            )
        )

        reasons = []
        for records in (
            (inside_low, inside_high, outside),
            (outside, inside_high, inside_low),
        ):
            screened = screen_console_occupancy(
                [_candidate("c1", 1, 5, 101)],
                address_plan=plan,
                console_fixtures=_console(*records),
            )
            assert screened.entries == (), records
            assert [exclusion.code for exclusion in screened.exclusions] == [
                ADDRESS_ALREADY_OCCUPIED
            ], records
            reason = screened.exclusions[0].reason
            # 구간 안에서 시작한 픽스처의 주소가 지목돼야 한다.
            assert any(str(address) in reason for address in (8, 12)), reason
            # 구간 밖 픽스처는 절대 지목되지 않는다.
            assert "777" not in reason, reason
            reasons.append(reason)

        # 비공허성 — 구간 밖 픽스처 하나만 있으면 제외되지 않는다.
        clean = screen_console_occupancy(
            [_candidate("c1", 1, 5, 101)],
            address_plan=plan,
            console_fixtures=_console(outside),
        )
        assert len(clean.entries) == 1
        assert clean.exclusions == ()


class TestRound17VacuousTypeKeyReachability:
    """[round17 · 공허 일치 차단 ⓒ] 게이트가 없으면 잘못된 타입이 **전달 Lua까지** 나온다."""

    def test_r17_a_vacuous_type_name_never_reaches_the_delivered_lua(self):
        """[round17 · 공허 일치 차단] `typemap._comparable_key` 필터나 `_resolve_one`의 공허 키
        갈래를 지우면 실패한다.

        도면 타입 이름이 `'---'`이면 `rig._norm_type` 후 빈 문자열이 되고 빈 문자열은 모든
        이름에 포함되므로 라이브러리 항목이 하나뿐일 때 그것이 **유일 후보**가 된다. 저장된
        별칭 값까지 공허하면 그대로 `resolved`가 되어 도면이 이름조차 준 적 없는 FixtureType이
        `Patch().FixtureTypes[...]`로 전달 Lua에 박힌다 — 되돌릴 수 없는 생성이다(실증됨).
        """
        plan = resolve_fixture_types(
            [_r17_type_request("ph", instrument_type="---", mode=MODE_1, footprint=16)],
            library_port=LibraryRigPort([(LED, [(MODE_1, 16)])]),
            type_aliases={"---": {"type": "---", "mode": "--"}},
        )
        handoff = build_patch_handoff(
            [_candidate("ph", 1, 5, 101)],
            address_plan=AddressPlan(entries=(_planned("ph", 1, 5),)),
            resolutions=plan.resolutions,
            names={"ph": "placeholder row"},
            dry_run=False,
        )

        assert handoff.entries == ()
        # [round19 major#4] round17 판은 여기서 `type_confirmation_pending`을 기대했다 —
        # 그게 **거짓 문장이었다**. 같은 payload의 `types.hard_stops`는 같은 후보를 두고
        # "확인 경로 없음, 하드 스톱"이라 말하는데 전달물 배제는 "확인 대기"라 적었다.
        # 배제 어휘는 이제 해소되지 않은 사유를 그대로 반영한다.
        assert [exclusion.code for exclusion in handoff.exclusions] == [FIXTURE_TYPE_NAME_UNUSABLE]
        assert [row["code"] for row in plan.to_dict()["hard_stops"]] == [FIXTURE_TYPE_NAME_UNUSABLE]
        assert handoff.lua_source is None

        # 비공허성 — 정상 이름은 같은 라이브러리에서 전달물까지 나간다.
        good_plan = resolve_fixture_types(
            [_r17_type_request("ok", instrument_type=LED, mode=MODE_1, footprint=16)],
            library_port=LibraryRigPort([(LED, [(MODE_1, 16)])]),
            type_aliases={LED: {"type": LED, "mode": MODE_1}},
        )
        good = build_patch_handoff(
            [_candidate("ok", 1, 5, 101)],
            address_plan=AddressPlan(entries=(_planned("ok", 1, 5),)),
            resolutions=good_plan.resolutions,
            names={"ok": "real row"},
            dry_run=False,
        )
        assert [entry.console_type for entry in good.entries] == [LED]
        assert good.lua_source is not None
        assert f'FixtureTypes["{LED}"]' in good.lua_source


# --- round17 표 행삭제·제외 사유 전 모듈 (ScopeAndTables) ---
#
#   [round17 #9] `_R16_CONSTANT_SITES`는 `_R16_VALIDATE_SITES`의 넷째 칸이 `"constant"`인
#     행만 골라낸 파생표다. 형제 `_R16_VARIABLE_SITES`에는 대조군 전단사가 붙었지만 상수
#     쪽에는 계수 단정이 없었다. 구멍의 정체는 **넷째 칸의 어휘가 닫혀 있지 않다**는 것이다 —
#     `"constant"`를 제3의 문자열로 바꾸면 그 행이 두 파생표 어디에도 들지 않아 대조군을
#     통째로 잃는데, `_R16_VALIDATE_SITES` 전단사는 (모듈, 어휘식, 값식) 셋만 보므로 통과한다.
#     여기서 넷째 칸을 **프로덕션에서 파생**하고 분할이 전수임을 단정한다.
#
#   [round17 #10] `_R16_INCOMPLETE_AXES`는 dict라 항목을 줄여도 아무것도 실패하지 않았다.
#     축 목록을 `console_read_caveat`의 **실제 갈래**에서 파생해 묶는다.
#
#   [round17 S17-05] `_R16_EXCLUSION_SITES`는 `apply.py`의 `_exclusion(...)` 자리만 봤다.
#     `patchplan.py`가 **직접** 짓는 `PatchTargetExclusion`(현재 여섯 자리)은 "빈 사유 금지"도
#     "사유 구별성"도 받지 않았다. 표를 두 모듈로 넓힌다.


#: [round17 S17-05] 제외 사유를 **짓는** 두 자리. `apply.py`는 `_exclusion(...)` 헬퍼로,
#: `patchplan.py`는 `PatchTargetExclusion(...)`를 **직접** 짓는다. round16 표는 앞쪽만 봤고
#: 뒤쪽 여섯 자리는 "빈 사유 금지"·"사유 구별성" 어느 단정도 받지 않았다.
_R17_EXCLUSION_BUILDERS = (
    ("apply.py", "_exclusion"),
    ("patchplan.py", "PatchTargetExclusion"),
)


def _r17_exclusion_call_sites() -> tuple[tuple[str, str, str], ...]:
    """`apply.py`와 `patchplan.py`의 제외 생성 자리를 (모듈, 함수, 사유 코드)로 전수.

    `apply.py`는 `_exclusion(target, CODE, reason)`, `patchplan.py`는
    `PatchTargetExclusion(candidate_id=..., code=CODE, reason=...)` 꼴이다.
    `_exclusion` 헬퍼 **자신**의 생성자 호출은 사이트가 아니라 공장이므로 제외한다.
    """
    import ast

    sites: list[tuple[str, str, str]] = []
    for module_name, builder in _R17_EXCLUSION_BUILDERS:
        source = (Path("server/vwx") / module_name).read_text(encoding="utf-8")
        module = ast.parse(source)
        for node in module.body:
            if not isinstance(node, ast.FunctionDef) or node.name == builder:
                continue
            for call in ast.walk(node):
                if not (
                    isinstance(call, ast.Call)
                    and isinstance(call.func, ast.Name)
                    and call.func.id == builder
                ):
                    continue
                if len(call.args) > 1:
                    code = ast.unparse(call.args[1])
                else:
                    code = next(
                        ast.unparse(keyword.value)
                        for keyword in call.keywords
                        if keyword.arg == "code"
                    )
                sites.append((module_name, node.name, code))
    return tuple(sorted(sites))


def _r17_validate_site_kind(module_name: str, value_expression: str) -> str:
    """사이트의 종류를 **프로덕션에서** 판정한다 — 값식이 그 모듈의 문자열 상수면 `constant`.

    `_R16_VALIDATE_SITES`의 넷째 칸이 손으로 쓴 라벨이라 제3의 값으로 바꿔 두 파생표
    어디에도 안 들게 만들 수 있었다. 라벨을 프로덕션 사실에 묶어 그 우회를 없앤다.
    """
    import ast
    import importlib

    node = ast.parse(value_expression, mode="eval").body
    if not isinstance(node, ast.Name):
        return "variable"
    module = importlib.import_module(f"server.vwx.{module_name[: -len('.py')]}")
    return "constant" if isinstance(getattr(module, node.id, None), str) else "variable"


def test_the_validate_site_kind_column_is_derived_from_production_not_declared():
    """[round17 #9] 넷째 칸이 프로덕션 사실과 일치한다 — 라벨을 바꿔치기할 수 없다.

    [round17 #9] 어느 행의 넷째 칸을 `"constant"`↔`"variable"`로 뒤집으면 실패한다.
    [round17 #9] 제3의 문자열(예: `"skip"`)로 바꿔 두 파생표에서 빠지게 해도 실패한다 —
      round16까지 그 조작은 어떤 단정도 건드리지 않고 상수 사이트 다섯을 무대조군으로 만들었다.
    """
    derived = tuple(
        _r17_validate_site_kind(module, value) for module, _, value, _ in _R16_VALIDATE_SITES
    )
    assert tuple(kind for _, _, _, kind in _R16_VALIDATE_SITES) == derived


def test_the_constant_and_variable_site_partition_is_total():
    """[round17 #9] 상수·변수 두 파생표의 합이 원표와 같다 — 행이 조용히 증발하지 못한다.

    [round17 #9] `_R16_CONSTANT_SITES`가 비면(넷째 칸을 전부 바꾸면) 계수 단정이 실패한다.
    [round17 #9] `_R16_VALIDATE_SITES`에서 상수 행을 지우면 하한과 전단사가 함께 실패한다.
    """
    assert {kind for _, _, _, kind in _R16_VALIDATE_SITES} == {"constant", "variable"}
    assert len(_R16_CONSTANT_SITES) + len(_R16_VARIABLE_SITES) == len(_R16_VALIDATE_SITES)
    assert set(_R16_CONSTANT_SITES).isdisjoint(_R16_VARIABLE_SITES)
    # 두 갈래 **모두** 비어 있지 않다 — 한쪽이 비면 그쪽 대조군이 통째로 사라진 상태다.
    assert len(_R16_CONSTANT_SITES) >= 5, _R16_CONSTANT_SITES
    assert len(_R16_VARIABLE_SITES) >= 5, _R16_VARIABLE_SITES


def _r17_incomplete_axis_names() -> tuple[str, ...]:
    """`_round15_inventory`의 정수 축 중 **단독으로** 재조회 미판독을 만드는 축을 전수.

    프로덕션 `console_read_caveat`를 실제로 불러 갈래를 본다 — 리터럴 목록이 아니다.
    """
    import inspect

    names: list[str] = []
    for name, parameter in inspect.signature(_round15_inventory).parameters.items():
        if parameter.annotation not in (int, "int"):
            continue
        caveat = console_read_caveat(_round15_inventory(**{name: 2}))
        if caveat is not None and caveat["kind"] == CONSOLE_READ_INCOMPLETE:
            names.append(name)
    return tuple(sorted(names))


def test_the_incomplete_axis_table_is_a_bijection_onto_the_production_axes():
    """[round17 #10] 미판독 표본의 축이 프로덕션 갈래와 1:1이다.

    [round17 #10] `_R16_INCOMPLETE_AXES`에서 항목을 지우면 실패한다 — round16까지 dict를
      줄여도 아무것도 실패하지 않았고, 그러면 계수 하드코딩 대조군이 한 축만 남는다.
    [round17 #10] 두 값을 같게 만들면(둘 다 `2`) 실패한다 — 두 계수 절을 서로 바꿔치는
      뮤테이션이 같은 값에서는 보이지 않기 때문이다.
    [round17 #10] 값 중 하나를 `1`로 되돌리면 실패한다(M50이 잡은 하드코딩이 되살아난다).
    """
    assert tuple(sorted(_R16_INCOMPLETE_AXES)) == _r17_incomplete_axis_names()
    assert all(value != 1 for value in _R16_INCOMPLETE_AXES.values()), _R16_INCOMPLETE_AXES
    assert len(set(_R16_INCOMPLETE_AXES.values())) == len(_R16_INCOMPLETE_AXES)

    # 그리고 그 계수들이 **실제로 사유 문장에 나타난다** — 표본이 닿지 않는 축이 없다.
    caveat = console_read_caveat(_round15_inventory(**_R16_INCOMPLETE_AXES))
    assert caveat is not None
    reason = str(caveat["reason"])
    for value in _R16_INCOMPLETE_AXES.values():
        assert str(value) in reason, (value, reason)


# ---- [round17 S17-05] 제외 사유는 **두 모듈** 전수다 --------------------------------


def _r17_plan_address_exclusions(*targets, footprints=None, occupied=None):
    """`patchplan.plan_addresses`를 **프로덕션 그대로** 돌려 제외를 받는다."""
    from server.vwx.patchplan import plan_addresses

    rows = targets or (_candidate("a", 1, 1, 101),)
    widths = {target.id: 16 for target in rows} if footprints is None else footprints
    return list(plan_addresses(rows, footprints=widths, occupied=occupied or {}).exclusions)


def _r17_fid_assignment_exclusions(*, fid_range, existing_fids=frozenset(), count=1):
    """`patchplan._assign_fids`를 **프로덕션 그대로** 돌려 제외를 받는다.

    상위 `build_patch_plan`을 거치지 않는 이유는 이 두 갈래가 배정 루프 안에서만 나오고,
    상위 경로는 그 앞의 사전검사에서 먼저 막혀 갈래에 도달하지 못하는 조합이 있기 때문이다.
    호출하는 것은 프로덕션 함수 자신이고, 단정 대상도 프로덕션이 만든 객체다.
    """
    from server.vwx.patchplan import FIDRange, _assign_fids

    targets = tuple(_candidate(f"c{index}", 1, 1 + index * 16, 0) for index in range(count))
    _kept, exclusions = _assign_fids(
        targets,
        FIDRange(*fid_range),
        existing_fids=frozenset(existing_fids),
        fid_range_visually_confirmed_empty=True,
    )
    return list(exclusions)


#: [round17 S17-05] 제외 생성 자리 **두 모듈 전수 표**.
#: (모듈, 사이트 이름, 함수, 사유 코드, 산출 호출, 필수 문구).
#: 앞 열한 행은 round16 `_R16_EXCLUSION_SITES`와 같은 자리(=`apply.py`)이고,
#: 뒤 일곱 행이 `patchplan.py` 자리다 — 여섯은 round17에서, 마지막 하나는 round18 R18-A에서.
_R17_EXCLUSION_SITES = tuple(
    ("apply.py", label, func, code, produce, fragment)
    for label, func, code, produce, fragment in _R16_EXCLUSION_SITES
) + (
    (
        "patchplan.py",
        "plan_addresses.below_minimum",
        "plan_addresses",
        "ADDRESS_BELOW_MINIMUM",
        lambda: _r17_plan_address_exclusions(_candidate("a", 1, 0, 101)),
        "콘솔 최소 인덱스",
    ),
    (
        "patchplan.py",
        "plan_addresses.footprint_unknown",
        "plan_addresses",
        "FOOTPRINT_UNKNOWN",
        lambda: _r17_plan_address_exclusions(footprints={"a": None}),
        "점유폭이 확정되지 않아",
    ),
    (
        "patchplan.py",
        "plan_addresses.console_occupied",
        "plan_addresses",
        "ADDRESS_ALREADY_OCCUPIED",
        lambda: _r17_plan_address_exclusions(occupied={1: [(1, 16)]}),
        "콘솔에서 이미 점유되어 있다",
    ),
    (
        "patchplan.py",
        "plan_addresses.overlap_in_plan",
        "plan_addresses",
        "ADDRESS_OVERLAP_IN_PLAN",
        lambda: _r17_plan_address_exclusions(
            _candidate("a", 1, 1, 101), _candidate("b", 1, 8, 102)
        ),
        "같은 계획의 다른 항목과 겹친다",
    ),
    (
        "patchplan.py",
        "assign_fids.range_exhausted",
        "_assign_fids",
        "FID_RANGE_EXHAUSTED",
        lambda: _r17_fid_assignment_exclusions(fid_range=(101, 101), count=2),
        "초과해 이 장비에는 FID를 배정하지 않았다",
    ),
    (
        "patchplan.py",
        "assign_fids.already_in_use",
        "_assign_fids",
        "FID_ALREADY_IN_USE",
        lambda: _r17_fid_assignment_exclusions(fid_range=(101, 110), existing_fids={101}),
        "콘솔 기존 픽스처가 이미 사용 중이다",
    ),
    (
        # [round18 R18-A] `_assign_fids`의 **개별 값 바닥** 갈래. 이 표는 자리를
        # 더하면 실패하도록 설계돼 있어(위 `_r17_exclusion_call_sites()` 대조),
        # 새 배제 자리는 반드시 여기 등재되고 사유 문구 대조군을 받는다.
        "patchplan.py",
        "assign_fids.below_minimum",
        "_assign_fids",
        "FID_BELOW_MINIMUM",
        lambda: _r17_fid_assignment_exclusions(fid_range=(-10, -8), count=1),
        "콘솔 최소 FID",
    ),
)


def test_the_exclusion_site_table_covers_both_modules_not_just_apply():
    """[round17 S17-05] 제외 생성 자리 표가 `apply.py`·`patchplan.py` **양쪽**과 1:1이다.

    [round17 S17-05] `patchplan.py`에 `PatchTargetExclusion(...)` 자리를 더하거나 지우면
      실패한다 — round16까지 그 다섯(현재 여섯) 자리는 어떤 사유 단정도 받지 않았다.
    [round17 S17-05] 표에서 행을 지워도 실패한다.
    [round17 S17-05] `apply.py` 쪽 열한 행은 `_R16_EXCLUSION_SITES`에서 파생하므로
      그 표가 줄면 여기서도 함께 어긋난다.
    """
    declared = tuple(
        sorted((module, func, code) for module, _, func, code, _, _ in _R17_EXCLUSION_SITES)
    )
    assert declared == _r17_exclusion_call_sites()
    labels = [label for _, label, _, _, _, _ in _R17_EXCLUSION_SITES]
    assert len(labels) == len(set(labels))
    # `patchplan.py` 쪽이 실제로 표에 들어왔다 — 넓히지 않으면 이 단정이 공허해진다.
    assert len([row for row in _R17_EXCLUSION_SITES if row[0] == "patchplan.py"]) >= 6


@pytest.mark.parametrize(
    "module_name,label,func,code,produce,fragment",
    [row for row in _R17_EXCLUSION_SITES if row[0] == "patchplan.py"],
    ids=[row[1] for row in _R17_EXCLUSION_SITES if row[0] == "patchplan.py"],
)
def test_every_patchplan_exclusion_site_ships_a_non_empty_reason(
    module_name, label, func, code, produce, fragment
):
    """[round17 S17-05] `patchplan.py`의 여섯 자리도 빈 사유를 낼 수 없다.

    [round17 S17-05] 어느 자리의 `reason=`을 `""`로 바꾸면 그 행이 실패한다 — round16까지는
      전부 통과했다. 조작자는 무엇이 왜 빠졌는지 이 문장으로만 안다(§0 2c①).
    """
    from server.vwx import verdicts

    produced = produce()
    expected_code = getattr(verdicts, code)
    assert [exclusion.code for exclusion in produced] == [expected_code], produced
    reason = produced[0].reason
    assert reason.strip() != ""
    assert len(reason) >= 20, reason
    assert fragment in reason, reason
    assert produced[0].to_dict()["reason"] == reason


def test_no_two_exclusion_sites_across_both_modules_share_the_same_sentence():
    """[round17 S17-05] 열일곱 자리의 사유가 서로 구별된다 — 한 자리를 다른 문구로 바꾸면 깨진다.

    round16 판은 `apply.py` 열한 자리만 비교했다. `patchplan.py`의
    `ADDRESS_ALREADY_OCCUPIED`는 `apply.py`의 같은 코드와 **다른 문장**이어야 한다 —
    한쪽은 계획 단계 점유, 다른 쪽은 재조회 점유이고 조작자가 할 일이 다르다.
    """
    reasons = [produce()[0].reason for _, _, _, _, produce, _ in _R17_EXCLUSION_SITES]
    assert len(reasons) == len(set(reasons)), [r for r in reasons if reasons.count(r) > 1]


# ==========================================================================
# --- round18 문장 형태 불변식의 표·범위·실패모드 (SentenceScope) ---
#
# round18 감사 셋이 같은 자리에서 세 가지를 지적했다:
#
#   R18-B  프로덕션 형태판정 표 `_SENTENCE_SHAPE_DEFECTS` **5행 중 4행이 무대조군**이다.
#          round16이 테스트 표에서 닫은 결함 클래스가 round17이 새로 만든 **프로덕션 표**에서
#          그대로 재발했다 — 표를 만들면서 표와 행동의 전단사를 세우지 않았다.
#   R18-C  형태 불변식의 **프로덕션 강제는 한 자리**뿐이다. 나머지 55자리는 정적 뼈대만
#          검사한다(= 소스 AST에서 보이는 리터럴 형태만 보고, 실제로 나가는 값은 보지 않는다).
#   R18-D  그 유일한 강제 자리가 하필 **차단 화면을 짓는 자리**이고 `ValueError`가
#          `ToolRegistry.dispatch`·runner·session 어디에도 가드 없이 툴 경계를 탈출한다 —
#          조립이 실패하면 **차단 자체가 사라진다**. fail-closed가 아니라 fail-crash다.
#
# **강제를 55자리로 확대하는 것은 처방이 아니다.** 정상 도면 값 `MAC — Aura — XB` 같은
# 이름이 프로덕션 뼈대에 들어가면 판정자가 발화한다 — 확대하면 정상 입력이 차단 화면을
# 죽인다. 아래 `_R18_DRAWING_VALUE_FALSE_POSITIVES`가 그 거짓 양성을 **고정**한다.
# 진짜 처방은 **출처로 강제 대상을 가르는 것**이다: 조립기에 들어가는 조각은 리터럴이거나
# 등기된 내부 생산자(`.reason()`·`.notes()`)의 산물만 허용하고, 그 분류를 AST로 전수 게이트한다.
# 그러면 외부값은 강제 자리에 **닿을 수 없고**, 강등까지 더하면 fail-crash 경로가 닫힌다.
# ==========================================================================


# --------------------------------------------------------------------------
# R18-B — 프로덕션 형태판정 표의 행마다 행동 대조군
# --------------------------------------------------------------------------

#: (부분문자열, **조작자가 읽는 라벨**, 그 결함 하나만 품은 프로브 문장).
#: 프로브는 자기 행이 아닌 어느 행에도 걸리지 않고 종결·대시 규칙도 지킨다 —
#: 그래야 "그 행을 지우면 통과한다"가 그 행 하나의 성질이 된다.
#: 라벨을 **여기에 동결**하는 이유: 라벨은 되돌릴 수 없는 쓰기를 판단하는 사람이 읽는
#: 것이다. 프로덕션에서 읽어 오면 라벨을 전부 `"형태가 깨졌다"`로 뭉개도 아무도 실패하지
#: 않는다(round18 실측 — 그 뮤턴트가 살아남았다).
_R18_SHAPE_DEFECT_PROBES = (
    ("..", "마침표가 겹쳤다", "콘솔 관측이 없다.. 사람이 확인하라."),
    (". —", "문장이 대시로 시작한다", "콘솔 관측이 없다. — 이 상태의 없음은 미판독이다."),
    ("  ", "공백이 겹쳤다", "콘솔  관측이 없다."),
    ("· ·", "빈 절이 목록에 있다", "미판독 · · 미배정이다."),
    (" · —", "대시 절이 목록 항목 자리에 있다", "미판독 · — 대시 절이 목록 항목 자리에 있다."),
)


def test_r18_the_shape_defect_table_is_a_bijection_onto_the_probe_table():
    """[round18 R18-B] 프로덕션 표의 행 전수가 프로브 표와 **순서까지** 1:1이다.

    round17은 프로덕션 표를 만들면서 행별 대조군을 만들지 않았다 — 5행 중 4행을 지워도
    아무도 실패하지 않았다. 표를 늘리면 프로브도 늘려야 하고, 그때 "이 행이 무엇을
    잡는가"를 한 번은 실제로 재게 된다. 순서까지 고정하는 이유는 판정자가 **첫 일치**를
    돌려주기 때문이다 — 순서가 바뀌면 조작자가 읽는 라벨이 바뀐다.

    [round18 #R18-B] `_SENTENCE_SHAPE_DEFECTS`에서 어느 행을 지워도 실패한다.
    [round18 #R18-B] 행을 하나 더 넣어도(예: `(" .", ...)`) 실패한다.
    [round18 #R18-B] 라벨을 바꾸거나 전부 같게 만들어도 실패한다.
    """
    from server.vwx.patchplan import _SENTENCE_SHAPE_DEFECTS

    assert tuple(_SENTENCE_SHAPE_DEFECTS) == tuple(
        (needle, label) for needle, label, _ in _R18_SHAPE_DEFECT_PROBES
    )
    labels = [label for _, label, _ in _R18_SHAPE_DEFECT_PROBES]
    assert len(set(labels)) == len(labels), labels


@pytest.mark.parametrize(
    ("needle", "label", "probe"),
    _R18_SHAPE_DEFECT_PROBES,
    ids=[f"row{index}" for index in range(len(_R18_SHAPE_DEFECT_PROBES))],
)
def test_r18_every_shape_defect_row_has_a_behavioural_control(needle, label, probe, monkeypatch):
    """[round18 R18-B] 표의 **각 행**이 실제로 무언가를 잡고, 그 행이 없으면 놓친다.

    세 방향을 함께 잰다:
      ① 프로덕션 판정자에 프로브를 넣으면 **그 행의 부분문자열을 지목한** 위반이 나온다.
      ② 그 위반이 **동결된 라벨**로 무엇이 잘못됐는지 말한다.
      ③ 그 행 하나만 표에서 빼면 같은 프로브가 **통과한다** — 곧 그 행이 유일한 방어선이다.

    [round18 #R18-B] `_SENTENCE_SHAPE_DEFECTS`에서 이 행을 지우면 ③이 실패한다.
    [round18 #R18-B] `sentence_shape_violation`의 `if needle in text`를 무력화하면 ①이 실패한다.
    [round18 #R18-B] 위반 문자열에서 `{label}`을 빼거나 라벨을 뭉개면 ②가 실패한다.
    """
    from server.vwx import patchplan as _patchplan
    from server.vwx.patchplan import _SENTENCE_SHAPE_DEFECTS, sentence_shape_violation

    violation = sentence_shape_violation(probe)
    assert violation is not None, probe
    assert repr(needle) in violation, (needle, violation)
    # 위반 문자열은 **무엇이 잘못됐는지**도 말해야 한다 — 부분문자열만 던지면 조작자는
    # `'· ·'`를 보고도 그것이 "빈 절이 목록에 있다"는 뜻임을 알 수 없다.
    assert label in violation, (label, violation)

    shrunk = tuple(row for row in _SENTENCE_SHAPE_DEFECTS if row[0] != needle)
    assert len(shrunk) == len(_SENTENCE_SHAPE_DEFECTS) - 1, needle
    monkeypatch.setattr(_patchplan, "_SENTENCE_SHAPE_DEFECTS", shrunk)
    assert sentence_shape_violation(probe) is None, (
        f"{needle!r} 행 없이도 프로브가 걸렸다 — 이 프로브는 그 행의 대조군이 아니다"
    )


def test_r18_the_deliberately_absent_row_stays_absent():
    """[round18 R18-B] 표에 **없어야 하는** 행이 없다 — `" ."`는 거짓 양성을 낸다.

    `reader.py`의 `"openpyxl 없이는 .xlsx를 판독할 수 없다"`처럼 확장자·파일명 앞 공백이
    정상적으로 나온다. 흔한 거짓 양성은 게이트를 무력화한다(§0 2b④). 표를 "더 촘촘하게"
    만들려는 다음 라운드가 이 행을 넣으면 여기서 멈춘다.

    [round18 #R18-B] `_SENTENCE_SHAPE_DEFECTS`에 `(" .", ...)`를 넣으면 실패한다.
    """
    from server.vwx.patchplan import sentence_shape_violation

    assert sentence_shape_violation("openpyxl 없이는 .xlsx를 판독할 수 없다.") is None


def test_r18_the_dash_budget_and_the_terminal_rule_are_both_load_bearing():
    """[round18 R18-B 형제 축] 표 밖의 두 규칙에도 양방향 대조군을 건다.

    표만 대조군을 받고 같은 함수의 나머지 두 규칙이 무대조군이면 같은 결함 클래스다 —
    round18이 "형제 표면"이라고 부른 것이 정확히 이것이다.

    [round18 #R18-B] `_MAX_DASHES_PER_SENTENCE`를 2로 올리면 첫 단정이 실패한다.
    [round18 #R18-B] `count(...) > _MAX...`를 `>=`로 바꾸면 둘째 단정이 실패한다.
    [round18 #R18-B] `require_terminal and ...` 절을 지우면 셋째 단정이 실패한다.
    [round18 #R18-B] `require_terminal` 인자를 무시하면 넷째 단정이 실패한다.
    """
    from server.vwx.patchplan import sentence_shape_violation

    assert sentence_shape_violation("가 — 나 — 다.") is not None
    assert sentence_shape_violation("가 — 나.") is None
    assert sentence_shape_violation("종결되지 않았다") is not None
    assert sentence_shape_violation("종결되지 않았다", require_terminal=False) is None
    # 문장 경계를 넘으면 대시 예산은 문장마다 새로 센다 — 문단 전체로 세면 정상이 걸린다.
    assert sentence_shape_violation("가 — 나. 다 — 라.") is None


# --------------------------------------------------------------------------
# R18-C(a) — **확대 금지** 고정: 정상 도면 값이 판정자를 발화시킨다
# --------------------------------------------------------------------------

#: (정상 도면 값, 그 값이 **어느 규칙**을 발화시키는가). 실제 조명 도면에 나오는 값이고
#: 셋이 프로덕션 판정자의 **서로 다른 세 규칙**을 건드린다 —
#: 대시 둘(제조사 — 제품 — 변형) · 생략부호 · 이중공백. 셋 다 도면 입력에서 흔하다.
#: 규칙 축을 함께 적는 이유는 행삭제 프로브를 세우기 위해서다: 행을 지우면
#: 아래 "덮는 규칙 전수" 단정이 어긋난다.
_R18_DRAWING_VALUE_FALSE_POSITIVES = (
    ("MAC — Aura — XB", "' — '"),
    ("MAC Aura .. XB", "'..'"),
    ("MAC  Aura", "'  '"),
)


@pytest.mark.parametrize(
    ("value", "rule"),
    _R18_DRAWING_VALUE_FALSE_POSITIVES,
    ids=[value for value, _ in _R18_DRAWING_VALUE_FALSE_POSITIVES],
)
def test_r18_normal_drawing_values_trip_the_shape_judge_on_their_own(value, rule):
    """[round18 R18-C(a)] 정상 도면 값 자체가 형태 위반으로 판정된다 — 규칙까지 지목한다.

    이 사실이 **확대 금지**의 근거다. 판정자는 "우리가 지은 문장"에만 옳고, 도면에서
    들어온 값에는 옳지 않다.

    [round18 #R18-C] 이 표본을 지우면 그 규칙의 거짓 양성 근거가 사라진다 —
      아래 `..._covers_three_distinct_rules`가 실패한다.
    """
    from server.vwx.patchplan import sentence_shape_violation

    violation = sentence_shape_violation(value, require_terminal=False)
    assert violation is not None, value
    assert rule in violation, (value, rule, violation)


def test_r18_the_false_positive_samples_cover_three_distinct_rules():
    """행삭제 프로브 — 거짓 양성 표본에서 어느 행을 지워도 덮는 규칙 전수가 줄어든다.

    표본이 한 규칙에 몰리면 "그 규칙만 완화하면 된다"는 오독이 열린다. 셋은 서로 다른
    규칙을 건드리므로 **판정자를 조금 느슨하게 해서 확대한다**는 길이 없다.
    """
    rules = [rule for _, rule in _R18_DRAWING_VALUE_FALSE_POSITIVES]
    assert sorted(rules) == sorted({"' — '", "'..'", "'  '"}), rules


def test_r18_widening_the_shape_gate_to_every_site_would_block_normal_input():
    """[round18 R18-C(a)] 강제를 55자리로 넓히면 **정상 입력이 차단 화면을 죽인다**.

    프로덕션 뼈대(소스 AST에서 그대로 뽑은 것)의 보간 자리에 정상 도면 값을 넣으면
    여러 표면이 형태 위반을 낸다. 지금 그 자리들이 강제를 받지 않기 때문에 조작자는
    그 값을 그대로 본다 — 강제를 넓히는 순간 그 자리들이 `ValueError`를 던진다.

    다음 라운드가 "강제를 전 자리로 넓혀라"로 오독하지 않도록 **수치로** 남긴다.

    [round18 #R18-C] `_R18_DRAWING_VALUE_FALSE_POSITIVES`를 비우면 실패한다.
    [round18 #R18-C] 강제 자리를 늘리면 아래 `enforced` 단정이 실패한다 — 늘리려면
      그 자리의 인자 출처가 등기돼 있음을 함께 보여야 한다(다음 절).
    """
    from server.vwx.patchplan import sentence_shape_violation

    interpolating = [
        (module, name, skeleton)
        for module, name, skeleton in _r17_sentence_sites()
        if "{}" in skeleton
    ]
    assert interpolating, "보간 자리를 하나도 찾지 못했다 — 스캐너가 공허하다"
    tripped = {
        (module, name)
        for value, _rule in _R18_DRAWING_VALUE_FALSE_POSITIVES
        for module, name, skeleton in interpolating
        if sentence_shape_violation(skeleton.replace("{}", value), require_terminal=False)
        is not None
    }
    assert len(tripped) >= 5, (
        "정상 도면 값이 거짓 양성을 내는 표면이 이렇게 적을 리 없다 — 표본이 무력해졌다",
        sorted(tripped),
    )
    # 강제 자리는 여전히 하나다 — 그 하나가 아래에서 출처 제한을 받는다.
    enforced = _r18_assembler_call_sites()
    assert len(enforced) == 1, enforced


# --------------------------------------------------------------------------
# R18-C(b) — 출처 기반 분류: 조립기 인자는 리터럴 또는 등기된 내부 생산자의 산물만
# --------------------------------------------------------------------------

#: 문장 조립기 **전수**. 이름을 손으로 적되 아래 전단사가 프로덕션과 맞춘다.
_R18_SENTENCE_ASSEMBLERS = ("assemble_sentences", "assemble_sentences_or_defect")

#: 조립기 인자의 보간 자리에 올 수 있는 **등기된 내부 생산자** 전수 — 인자 없는 메서드다.
#: 이 집합은 **동결**이다. 늘리려면 그 생산자가 도면 값을 그대로 흘리지 않음을 먼저 보여야 한다.
_R18_REGISTERED_SENTENCE_PRODUCERS = ("notes", "reason")


def _r18_assembler_definitions(overrides=None) -> tuple[str, ...]:
    """`server/vwx/`에서 문장 조각 가변인자를 받는 **모듈 최상위 조립기** 전수.

    이름으로 찾지 않는다 — `*sentences` 가변인자라는 **형태**로 찾으므로, 다른 이름으로
    조립기를 하나 더 만들어도 등기부 전단사가 그것을 끌어온다.
    """
    import ast

    found: list[str] = []
    for _, tree in _r17_vwx_trees(overrides):
        for node in tree.body:
            if (
                isinstance(node, ast.FunctionDef)
                and getattr(node.args.vararg, "arg", None) == "sentences"
            ):
                found.append(node.name)
    return tuple(sorted(found))


def _r18_assembler_call_sites(overrides=None):
    """조립기를 **호출하는** 자리 전수 — 조립기 자신의 정의 안은 세지 않는다."""
    import ast

    sites = []
    for module_name, tree in _r17_vwx_trees(overrides):
        inside = {
            id(child)
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name in _R18_SENTENCE_ASSEMBLERS
            for child in ast.walk(node)
        }
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and getattr(node.func, "id", None) in _R18_SENTENCE_ASSEMBLERS
                and id(node) not in inside
            ):
                sites.append((module_name, node.lineno, node))
    return tuple(sites)


def _r18_is_registered_producer_call(node) -> bool:
    """등기된 내부 생산자 호출인가 — `<무언가>.reason()` 처럼 **인자 없는** 메서드 호출."""
    import ast

    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in _R18_REGISTERED_SENTENCE_PRODUCERS
        and not node.args
        and not node.keywords
    )


def _r18_argument_origin_defect(arg) -> str | None:
    """조립기 인자의 출처가 허용되지 않으면 그 서술 — 허용이면 `None`.

    허용은 셋뿐이다: ① 문자열 리터럴 ② 모든 보간 자리가 등기 생산자 호출인 f-string
    ③ 등기 생산자 호출의 `*` 전개. 그 밖은 **외부값이 섞였을 수 있다**는 뜻이고,
    외부값이 강제 자리에 닿으면 정상 입력이 차단 화면을 죽인다(위 거짓 양성 절).
    """
    import ast

    if isinstance(arg, ast.Constant):
        return None if isinstance(arg.value, str) else f"const:{arg.value!r}"
    if isinstance(arg, ast.JoinedStr):
        for part in arg.values:
            if isinstance(part, ast.Constant):
                continue
            if not isinstance(part, ast.FormattedValue):
                return f"interp:{ast.unparse(part)}"
            if not _r18_is_registered_producer_call(part.value):
                return f"interp:{ast.unparse(part.value)}"
        return None
    if isinstance(arg, ast.Starred):
        if _r18_is_registered_producer_call(arg.value):
            return None
        return f"starred:{ast.unparse(arg.value)}"
    return f"expr:{ast.unparse(arg)}"


def _r18_origin_defects(overrides=None) -> tuple[tuple[str, int, str], ...]:
    """조립기 호출 인자 중 **출처가 등기되지 않은** 것 전수."""
    return tuple(
        (module_name, lineno, defect)
        for module_name, lineno, call in _r18_assembler_call_sites(overrides)
        for defect in (
            [_r18_argument_origin_defect(arg) for arg in call.args]
            + [f"kw:{kw.arg}" for kw in call.keywords]
        )
        if defect is not None
    )


def test_r18_the_sentence_assembler_registry_is_a_bijection_onto_production():
    """[round18 R18-C] 조립기 등기부가 프로덕션과 1:1이다.

    조립기를 하나 더 만들어 출처 게이트를 우회하면 여기서 걸린다 — 등기되지 않은
    조립기는 아래 출처 게이트의 도달 범위 밖이고, 그것이 round18이 여덟 라운드째
    지적한 "형제 표면" 기제다.

    [round18 #R18-C] `_R18_SENTENCE_ASSEMBLERS`에서 행을 지우면 실패한다.
    [round18 #R18-C] `patchplan.py`에 `*sentences` 조립기를 하나 더 만들면 실패한다.
    """
    assert _r18_assembler_definitions() == tuple(sorted(_R18_SENTENCE_ASSEMBLERS))


@pytest.mark.parametrize("index", range(len(_R18_SENTENCE_ASSEMBLERS)))
def test_r18_deleting_any_assembler_row_breaks_the_bijection(index: int):
    """행삭제 프로브 — 조립기 등기부에서 어느 행을 지워도 프로덕션과 어긋난다."""
    shrunk = _R18_SENTENCE_ASSEMBLERS[:index] + _R18_SENTENCE_ASSEMBLERS[index + 1 :]
    assert tuple(sorted(shrunk)) != _r18_assembler_definitions()


def test_r18_the_registered_producer_set_is_a_bijection_onto_production():
    """[round18 R18-C] 등기된 생산자 집합이 **실제로 쓰이는 것** 전수와 1:1이다 — 동결.

    집합을 늘리면(= 새 생산자를 조립기에 물리면) 여기서 멈춘다. 그때 그 생산자가
    도면 값을 그대로 흘리지 않음을 먼저 보여야 한다.

    [round18 #R18-C] `_R18_REGISTERED_SENTENCE_PRODUCERS`에서 `"notes"`나 `"reason"`을
      지우면 이 전단사와 아래 출처 게이트가 함께 실패한다.
    [round18 #R18-C] 집합에 쓰이지 않는 이름을 더해도 실패한다.
    """
    import ast

    used: set[str] = set()
    for _, _, call in _r18_assembler_call_sites():
        for arg in call.args:
            nodes = [arg.value] if isinstance(arg, ast.Starred) else []
            if isinstance(arg, ast.JoinedStr):
                nodes = [part.value for part in arg.values if isinstance(part, ast.FormattedValue)]
            for node in nodes:
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    used.add(node.func.attr)
    assert tuple(sorted(used)) == tuple(sorted(_R18_REGISTERED_SENTENCE_PRODUCERS)), sorted(used)


@pytest.mark.parametrize("index", range(len(_R18_REGISTERED_SENTENCE_PRODUCERS)))
def test_r18_deleting_any_registered_producer_row_is_caught(index: int):
    """행삭제 프로브 — 등기 생산자 표에서 행을 지우면 출처 게이트가 위반을 낸다.

    등기부를 줄이면 지금 통과하는 프로덕션 자리가 **위반으로 바뀐다**. 곧 이 표의
    각 행은 실제로 무언가를 허용하고 있다(공허하지 않다).
    """
    import server.tests.test_autopatch_verify as _self

    shrunk = (
        _R18_REGISTERED_SENTENCE_PRODUCERS[:index] + _R18_REGISTERED_SENTENCE_PRODUCERS[index + 1 :]
    )
    saved = _self._R18_REGISTERED_SENTENCE_PRODUCERS
    try:
        _self._R18_REGISTERED_SENTENCE_PRODUCERS = shrunk
        assert _r18_origin_defects() != (), shrunk
    finally:
        _self._R18_REGISTERED_SENTENCE_PRODUCERS = saved


def test_r18_every_assembler_argument_comes_from_a_registered_origin():
    """[round18 R18-C·R18-D] 강제 자리에 **외부값이 닿을 수 없다** — 출처로 가른다.

    이것이 "강제를 55자리로 넓혀라"의 대안이다. 넓히면 정상 도면 값이 차단 화면을
    죽인다(위 절). 대신 **강제 자리의 입력 출처를 닫는다** — 리터럴이거나 등기된
    내부 생산자의 산물만 들어간다. 그러면 형태 불변식은 우리가 지은 문장에만 걸리고,
    도면 값은 애초에 그 자리에 오지 못한다.

    [round18 #R18-C] 조립기 인자에 `f"… {targets[0].instrument_type} …"`를 심으면 실패한다
      (아래 비공허성 대조군이 실제로 심어 확인한다).
    """
    assert _r18_origin_defects() == ()


def test_r18_the_origin_gate_catches_an_external_value_planted_into_the_assembler():
    """[round18 R18-C 비공허성] 외부값을 실제로 심어 출처 게이트가 잡는 것을 확인한다.

    심는 값은 `PatchCandidate.instrument_type` — 도면에서 그대로 올라온 값이고,
    위 거짓 양성 표본이 바로 그 축의 값이다.
    """
    patchplan_source = Path("server/vwx/patchplan.py").read_text(encoding="utf-8")
    anchor = '"부분 관측으로 빈 FID를 단정하면 이미 쓰이는 번호를 배정하게 된다.",'
    assert patchplan_source.count(anchor) == 1, patchplan_source.count(anchor)
    planted = patchplan_source.replace(
        anchor,
        'f"도면 값 {targets[0].instrument_type}을 그대로 싣는다.",',
        1,
    )
    assert planted != patchplan_source
    assert _r18_origin_defects() == ()
    defects = _r18_origin_defects({"patchplan.py": planted})
    assert defects != (), "외부값을 심었는데도 출처 게이트가 잡지 못했다"
    assert any("targets[0].instrument_type" in defect for _, _, defect in defects), defects


def test_r18_the_origin_gate_rejects_a_bare_name_and_a_starred_non_producer():
    """[round18 R18-C 비공허성 형제 축] 세 허용 형태 **밖**의 것이 전부 걸린다.

    f-string 보간뿐 아니라 ① 이름 그대로 넘기기 ② 등기되지 않은 호출의 `*` 전개
    ③ 인자를 받는 생산자 호출도 막는다 — 인자를 받으면 그 인자로 외부값이 들어온다.
    """
    import ast

    def origin(expression: str):
        return _r18_argument_origin_defect(ast.parse(expression, mode="eval").body)

    assert origin('"리터럴 문장이다."') is None
    assert origin('f"조각 {read.reason()}."') is None
    assert origin("detail") == "expr:detail"
    assert origin('f"{candidate.instrument_type}"') == "interp:candidate.instrument_type"
    assert origin('f"{read.reason(verbose)}"') == "interp:read.reason(verbose)"
    assert origin('f"{read.summary()}"') == "interp:read.summary()"
    starred = ast.parse("f(*read.notes())", mode="eval").body.args[0]
    assert _r18_argument_origin_defect(starred) is None
    bad_starred = ast.parse("f(*fragments)", mode="eval").body.args[0]
    assert _r18_argument_origin_defect(bad_starred) == "starred:fragments"


# --------------------------------------------------------------------------
# R18-D — fail-crash → fail-closed 강등
# --------------------------------------------------------------------------

#: 조립기에 넣는 시험 입력 — 성공 갈래와 실패 갈래를 모두 덮는다.
_R18_ASSEMBLY_BATTERY = (
    ("앞 문장이다.", "", "뒤 문장이다."),
    ("한 문장이다.",),
    ("끝난 문장이다.", "— 대시로 시작한다."),
    ("한 문장에 — 대시가 — 둘이다.",),
    ("종결되지 않았다",),
    ("겹친 마침표다..",),
    ("이중  공백이다.",),
    (),
)


def test_r18_the_demoted_assembler_never_raises():
    """[round18 R18-D] 강등 조립기는 **어떤 입력에도 던지지 않는다**.

    유일한 프로덕션 강제 자리가 차단 화면을 짓는 자리다. 거기서 던지면 차단이 사라진다.

    [round18 #R18-D] `assemble_sentences_or_defect`가 `assemble_sentences`를 호출하도록
      되돌리면(= 예외 재탈출) 실패한다.
    """
    from server.vwx.patchplan import (
        REASON_PLACEHOLDER_CODES,
        REASON_UNAVAILABLE,
        SENTENCE_SHAPE_VIOLATION,
        assemble_sentences_or_defect,
    )

    broken = 0
    for fragments in _R18_ASSEMBLY_BATTERY:
        assembled = assemble_sentences_or_defect(*fragments)
        if assembled.defect is None:
            continue
        broken += 1
        assert assembled.text == REASON_UNAVAILABLE
        assert assembled.text in REASON_PLACEHOLDER_CODES
        assert assembled.defect["code"] == SENTENCE_SHAPE_VIOLATION
        assert assembled.defect["violation"], assembled.defect
        assert assembled.defect["fragments"] == tuple(f for f in fragments if f)
    # 행삭제 프로브 — 배터리에서 어느 행을 지워도 성공/실패 갈래 수가 어긋난다.
    healthy = len(_R18_ASSEMBLY_BATTERY) - broken
    assert (healthy, broken) == (2, 6), (healthy, broken)


def test_r18_the_two_assemblers_agree_on_every_input():
    """[round18 R18-D] 강등 조립기와 강제 조립기의 **판정이 갈리지 않는다**.

    갈리면 강등 경로가 조용한 우회로가 된다 — 강제 자리를 강등 조립기로 바꾸는 것만으로
    형태 불변식을 끌 수 있게 된다.

    [round18 #R18-D] `assemble_sentences_or_defect`의 판정을 완화하면 실패한다.
    [round18 #R18-D] `_join_sentences`를 한쪽만 바꿔도 실패한다.
    """
    import pytest as _pytest

    from server.vwx.patchplan import assemble_sentences, assemble_sentences_or_defect

    for fragments in _R18_ASSEMBLY_BATTERY:
        assembled = assemble_sentences_or_defect(*fragments)
        if assembled.defect is None:
            assert assemble_sentences(*fragments) == assembled.text
            continue
        with _pytest.raises(ValueError):
            assemble_sentences(*fragments)


def _r18_incomplete_plan(monkeypatch, *, fragment: str | None):
    """FID 사전검사 **불완전** 갈래를 실제로 돌린다 — `reason()` 조각만 갈아끼운다.

    `fragment`가 있으면 그 조각을 생산자가 돌려주게 한다. round17 S17-04가 실제로 낸
    결함(조각이 대시를 품어 한 문장에 대시가 둘)을 그대로 재현하는 자리다.
    """
    from server.vwx.patchplan import ExistingFidRead, build_patch_plan

    if fragment is not None:
        monkeypatch.setattr(ExistingFidRead, "reason", lambda self: fragment)

    class _BlindPort:
        def query_state(self, path: str):
            return {"ok": False, "path": path, "error": "not readable"}

        def query_property(self, path: str, property_name: str):
            return {"ok": False, "path": path, "property": property_name, "error": "no"}

    return build_patch_plan(
        {"diffs": {"missing_in_console": []}},
        selected=[],
        dry_run=True,
        fid_range={"start": 101, "end": 120},
        assignment_requested=True,
        fid_property_port=_BlindPort(),
    )


def test_r18_a_healthy_assembly_carries_a_sentence_and_no_defect_cell(monkeypatch):
    """[round18 R18-D 대조군] 정상 갈래에서는 사유가 **문장**이고 구조화 칸이 없다.

    강등이 늘 켜져 있으면 "강등됐다"는 관측이 아무것도 말하지 않는다.
    """
    from server.vwx.patchplan import REASON_UNAVAILABLE, sentence_shape_violation

    plan = _r18_incomplete_plan(monkeypatch, fragment=None)
    assert plan.ok is False
    assert plan.rejection.code == "fid_precheck_read_incomplete"
    assert plan.rejection.reason != REASON_UNAVAILABLE
    assert sentence_shape_violation(plan.rejection.reason) is None, plan.rejection.reason
    assert plan.rejection.reason_defect is None
    assert "reason_defect" not in plan.to_dict()["rejection"]


def test_r18_a_broken_assembly_is_demoted_to_a_payload_field_not_an_exception(monkeypatch):
    """[round18 R18-D] 조립이 깨져도 **예외가 나가지 않고 거부가 그대로 남는다**.

    세 가지를 함께 단정한다:
      ① 예외가 `build_patch_plan` 밖으로 나오지 않는다.
      ② 거부 판정(`ok=False` · `fid_precheck_read_incomplete` · 건너뛴 검사)이 **그대로**다.
      ③ 조작자가 무엇이 손상됐는지 **구조화 칸**으로 본다 — 사유 자리에는 등재 코드가 간다.

    [round18 #R18-D] 조립부를 `assemble_sentences`로 되돌리면 ①이 `ValueError`로 실패한다.
    [round18 #R18-D] `reason_defect=` 인자를 빼면 ③이 실패한다.
    [round18 #R18-D] `PatchPlanRejection.to_dict`의 `reason_defect` 방출을 빼면 ③이 실패한다.
    """
    from server.vwx.patchplan import (
        REASON_PLACEHOLDER_CODES,
        REASON_UNAVAILABLE,
        SENTENCE_SHAPE_VIOLATION,
    )

    # round17 S17-04가 실제로 낸 형태 — 조각이 대시를 품어 완성 문장에 대시가 둘이 된다.
    plan = _r18_incomplete_plan(
        monkeypatch, fragment="열거가 총계보다 많다 — 스냅샷이 자기모순이다"
    )

    assert plan.ok is False
    assert plan.rejection.code == "fid_precheck_read_incomplete"
    assert [check["kind"] for check in plan.skipped_checks] == ["fid_conflict_precheck_incomplete"]
    assert plan.targets == () or plan.rejection is not None

    assert plan.rejection.reason == REASON_UNAVAILABLE
    assert plan.rejection.reason in REASON_PLACEHOLDER_CODES
    defect = plan.rejection.reason_defect
    assert defect is not None
    assert defect["code"] == SENTENCE_SHAPE_VIOLATION
    assert "' — '" in defect["violation"], defect["violation"]
    assert "스냅샷이 자기모순이다" in defect["assembled"]

    payload = plan.to_dict()["rejection"]
    assert payload["code"] == "fid_precheck_read_incomplete"
    assert payload["label"], payload
    assert payload["reason"] == REASON_UNAVAILABLE
    assert payload["reason_defect"]["violation"] == defect["violation"]


def test_r18_the_placeholder_code_is_not_a_human_sentence():
    """[round18 R18-D] 사유 자리에 들어가는 등재 코드가 **문장으로 오독되지 않는다**.

    코드 자리에 문장을 넣으면 조작자는 그것을 사유로 읽고 "조립이 깨졌다"는 사실을 놓친다.
    """
    from server.vwx.patchplan import REASON_PLACEHOLDER_CODES, REASON_UNAVAILABLE

    assert frozenset({REASON_UNAVAILABLE}) == REASON_PLACEHOLDER_CODES
    for code in REASON_PLACEHOLDER_CODES:
        assert " " not in code, code
        assert not _r17_is_human_sentence(code), code


# --------------------------------------------------------------------------
# round19 R18-C 출처 게이트 바인딩화 (GateHoles19)
# --------------------------------------------------------------------------
#
# round18이 세운 출처 게이트에는 구멍이 셋 있었다. 원인은 하나다 — **이름으로 봤다.**
#   ① 호출 자리를 `node.func.id`로만 찾았다 → 별칭 import·속성 호출이 통째로 밖이다.
#   ② 등기 생산자를 **메서드 이름**으로만 판정했다 → 아무 클래스에 인자 없는
#      `reason()`/`notes()`를 달면 그 순간 게이트가 오인한다.
#
# 감사가 실증한 세 형태(전부 `_r18_origin_defects()`가 `()`를 돌려준다):
#   (a) `from server.vwx.patchplan import assemble_sentences_or_defect as _A` 뒤 `_A(f"{…}")`
#   (b) `import server.vwx.patchplan` 뒤 `server.vwx.patchplan.assemble_sentences_or_defect(…)`
#   (c) 아무 클래스에 `reason()`을 달아 `f"{target.reason()}"` — **가짜 생산자**
# (a)·(b)는 **R18-F 봉인도 통과한다** — 둘 다 등기된 모듈명이다. 커밋이 말한 "두 게이트에
# 함께 통과"가 이 형태들에는 성립하지 않았다.
#
# **실해가 낮지 않다.** round18이 신설한 `reason_defect.assembled`·`fragments`가 조립기
# 입력을 **원문 그대로 payload에 재방출**한다. 그래서 도면 원문 비보간 규율(§0 2b④ ·
# round17 S17-02)이 이 게이트에 **새로 의존하게 됐다** — 여기가 뚫리면 도면 원문이
# 조작자에게 나가는 payload로 흘러간다.
#
# **처방: 이름 기반 → 바인딩 기반.**
#   · 호출 식별: 같은 모듈의 `def` · `from … import … as …` 별칭 · `import a.b.c` 속성 경로를
#     전부 조립기 호출로 인식한다. 속성 호출의 수신자가 **바인딩된 모듈이 아니면** 그것
#     자체가 결함이다(`assembler-via-unbound-receiver`).
#   · 생산자 판정: 이름이 아니라 **(클래스, 메서드) 쌍**을 동결한다. 현행은
#     `ExistingFidRead.reason` · `ExistingFidRead.notes` 둘뿐이고, 다른 클래스에 같은 이름
#     메서드를 하나 더 달면 `unfrozen-producer:`로 걸린다.
#
# 구 게이트(`_r18_origin_defects`)는 **지우지 않는다** — 새 게이트가 그 위에 얹히고,
# 아래 `test_r19_the_binding_gate_contains_the_round18_origin_gate`가 포함관계를 실측한다.

#: 조립기가 사는 모듈 — 속성 호출(형태 b)의 수신자 대조에 쓴다.
_R19_ASSEMBLER_HOME = "server.vwx.patchplan"

#: 등기 생산자의 **(클래스, 메서드) 쌍** 전수 — 동결. 이름만 동결하면 형태 (c)가 뚫는다.
_R19_REGISTERED_PRODUCER_METHODS = (
    ("ExistingFidRead", "notes"),
    ("ExistingFidRead", "reason"),
)


def _r19_assembler_bindings(tree):
    """모듈 하나에서 조립기에 닿는 **바인딩** 전수 — (지역 이름 집합, 모듈 경로 집합).

    이름이 아니라 바인딩을 본다: 같은 모듈의 정의, `from … import … as _A` 별칭,
    `import a.b.c [as x]`가 만드는 속성 경로.
    """
    import ast

    local: set[str] = set()
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name in _R18_SENTENCE_ASSEMBLERS:
            local.add(node.name)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name in _R18_SENTENCE_ASSEMBLERS:
                    local.add(alias.asname or alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.asname or alias.name)
    return local, modules


def _r19_assembler_call_sites(overrides=None):
    """조립기 호출 자리 전수 — **이름이 아니라 바인딩**으로 찾는다.

    돌려주는 각 항목은 `(모듈명, 줄번호, 호출 노드, 수신자 결함 또는 None)`이다.
    """
    import ast

    sites = []
    for module_name, tree in _r17_vwx_trees(overrides):
        local, modules = _r19_assembler_bindings(tree)
        inside = {
            id(child)
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name in _R18_SENTENCE_ASSEMBLERS
            for child in ast.walk(node)
        }
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or id(node) in inside:
                continue
            receiver_defect = None
            if isinstance(node.func, ast.Name):
                if node.func.id not in local:
                    continue
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr not in _R18_SENTENCE_ASSEMBLERS:
                    continue
                receiver = ast.unparse(node.func.value)
                if receiver not in modules and receiver != _R19_ASSEMBLER_HOME:
                    # 수신자가 무엇인지 정적으로 모르면 **닫는다** — 임의 객체에 조립기
                    # 이름의 메서드를 달아 게이트를 우회하는 형태를 여기서 막는다.
                    receiver_defect = f"assembler-via-unbound-receiver:{receiver}"
            else:
                continue
            sites.append((module_name, node.lineno, node, receiver_defect))
    return tuple(sites)


def _r19_producer_definitions(overrides=None) -> tuple[tuple[str, str], ...]:
    """등기 생산자 **이름**을 쓰는 메서드의 (클래스, 메서드) 전수 — 중첩 클래스도 본다."""
    import ast

    found: list[tuple[str, str]] = []
    for _, tree in _r17_vwx_trees(overrides):
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for member in node.body:
                if (
                    isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and member.name in _R18_REGISTERED_SENTENCE_PRODUCERS
                ):
                    found.append((node.name, member.name))
    return tuple(sorted(found))


def _r19_origin_defects(overrides=None) -> tuple[tuple[str, int, str], ...]:
    """바인딩 기반 출처 결함 전수 — 호출 자리 결함 **+ 생산자 정의 결함**.

    두 갈래를 한 함수로 합친 이유: 형태 (c)는 호출 자리만 보면 **정상으로 보인다**
    (`f"{x.reason()}"`는 등기된 이름이다). 그 형태는 **정의 쪽**에서만 드러난다.
    출처 규율은 "이 호출이 안전한가"가 아니라 "이 이름이 여전히 그 클래스만 가리키는가"다.
    """
    defects: list[tuple[str, int, str]] = []
    for module_name, lineno, call, receiver_defect in _r19_assembler_call_sites(overrides):
        if receiver_defect is not None:
            defects.append((module_name, lineno, receiver_defect))
        for arg in call.args:
            defect = _r18_argument_origin_defect(arg)
            if defect is not None:
                defects.append((module_name, lineno, defect))
        defects.extend((module_name, lineno, f"kw:{kw.arg}") for kw in call.keywords)
    frozen = set(_R19_REGISTERED_PRODUCER_METHODS)
    defects.extend(
        ("<producer-definition>", 0, f"unfrozen-producer:{owner}.{method}")
        for owner, method in _r19_producer_definitions(overrides)
        if (owner, method) not in frozen
    )
    return tuple(defects)


#: 감사 대조군을 **그대로 옮긴 표** — caught 4 / MISSED 3.
#: 열: (id, 심는 모듈, 심기 방식, 페이로드, 구 게이트가 잡는가, 새 게이트가 내야 하는 결함).
#: `anchor`는 프로덕션 유일 호출 자리의 한 인자를 갈아끼우고, `append`는 새 호출 자리를 만든다.
_R19_ORIGIN_ANCHOR = '"부분 관측으로 빈 FID를 단정하면 이미 쓰이는 번호를 배정하게 된다.",'

_R19_ORIGIN_PLANTS = (
    (
        "caught:external_value_interpolation",
        "patchplan.py",
        "anchor",
        'f"도면 값 {targets[0].instrument_type}을 그대로 싣는다.",',
        True,
        "interp:targets[0].instrument_type",
    ),
    (
        "caught:bare_name_argument",
        "patchplan.py",
        "anchor",
        "detail,",
        True,
        "expr:detail",
    ),
    (
        "caught:unregistered_starred",
        "patchplan.py",
        "anchor",
        "*fragments,",
        True,
        "starred:fragments",
    ),
    (
        "caught:producer_taking_an_argument",
        "patchplan.py",
        "anchor",
        'f"조각 {existing_read.reason(verbose)}.",',
        True,
        "interp:existing_read.reason(verbose)",
    ),
    (
        # 형태 (a) — 별칭 import. 구 게이트는 `node.func.id`가 `_A19`라 **호출 자리로도** 안 본다.
        "missed:aliased_import_of_the_assembler",
        "apply.py",
        "append",
        "from server.vwx.patchplan import assemble_sentences_or_defect as _A19\n\n"
        '_leak19 = _A19(f"도면 값 {_target.instrument_type}을 그대로 싣는다.")\n',
        False,
        "interp:_target.instrument_type",
    ),
    (
        # 형태 (b) — 모듈 속성 호출. 등기된 모듈명이라 R18-F 봉인도 함께 통과한다.
        "missed:module_attribute_call",
        "apply.py",
        "append",
        "import server.vwx.patchplan\n\n"
        "_leak19 = server.vwx.patchplan.assemble_sentences_or_defect(\n"
        '    f"도면 값 {_target.instrument_type}을 그대로 싣는다."\n)\n',
        False,
        "interp:_target.instrument_type",
    ),
    (
        # 형태 (c) — 가짜 생산자. 호출 자리만 보면 등기된 이름이라 **정상으로 보인다**.
        "missed:counterfeit_producer_class",
        "patchplan.py",
        "append",
        "class _Counterfeit19:\n"
        "    def reason(self) -> str:\n"
        '        return "무엇이든 흘릴 수 있다"\n\n\n'
        '_leak19 = assemble_sentences_or_defect(f"조각 {_Counterfeit19().reason()}.")\n',
        False,
        "unfrozen-producer:_Counterfeit19.reason",
    ),
)

#: 표 축소 트립와이어.
_R19_ORIGIN_PLANT_IDS = frozenset(
    {
        "caught:external_value_interpolation",
        "caught:bare_name_argument",
        "caught:unregistered_starred",
        "caught:producer_taking_an_argument",
        "missed:aliased_import_of_the_assembler",
        "missed:module_attribute_call",
        "missed:counterfeit_producer_class",
    }
)


def _r19_origin_overrides(filename: str, kind: str, payload: str) -> dict[str, str]:
    """심은 소스를 만든다 — 앵커 교체 1회 또는 파일 끝 덧붙이기."""
    source = (_R17_VWX_DIR / filename).read_text(encoding="utf-8")
    if kind == "anchor":
        assert source.count(_R19_ORIGIN_ANCHOR) == 1, source.count(_R19_ORIGIN_ANCHOR)
        planted = source.replace(_R19_ORIGIN_ANCHOR, payload, 1)
    else:
        planted = source + "\n\n" + payload
    assert planted != source
    return {filename: planted}


def test_r19_the_binding_origin_gate_is_clean_on_production():
    """클린 대조군 BYPASS — 심지 않은 프로덕션에서 새 게이트가 0건이다.

    새 규칙이 현행 프로덕션을 깨면 규칙이 틀린 것이다. 여기가 그 판정 자리다.
    """
    assert _r18_origin_defects() == ()
    assert _r19_origin_defects() == ()
    assert _r19_assembler_call_sites(), "호출 자리가 0개면 이 확인은 공허하다"


@pytest.mark.parametrize(
    "filename,kind,payload,old_catches,expected",
    [(f, k, p, old, exp) for _, f, k, p, old, exp in _R19_ORIGIN_PLANTS],
    ids=[name for name, _, _, _, _, _ in _R19_ORIGIN_PLANTS],
)
def test_r19_every_audited_origin_bypass_is_caught(filename, kind, payload, old_catches, expected):
    """감사 대조군 7행(caught 4 / MISSED 3) — **일곱 전부** 새 게이트에 걸린다.

    같은 행에서 구 게이트의 실측도 고정한다: MISSED 3행에서 구 게이트는 `()`다.

    죽이는 뮤테이션:
      · 호출 식별을 `node.func.id`로 되돌리면 형태 (a)(b)가 빈 결과를 받아 실패한다.
      · 생산자 판정을 이름만으로 되돌리면(= 정의 스캔 제거) 형태 (c)가 실패한다.
      · `_R19_REGISTERED_PRODUCER_METHODS`의 클래스명을 `ExistingFidRead` 밖으로 넓히면
        형태 (c)가 통과해 실패한다.
    """
    overrides = _r19_origin_overrides(filename, kind, payload)
    old = _r18_origin_defects(overrides)
    new = _r19_origin_defects(overrides)
    assert bool(old) is old_catches, (old_catches, old)
    assert new != (), "새 게이트가 놓쳤다"
    assert any(expected == defect for _, _, defect in new), (expected, new)
    assert {defect for _, _, defect in old} <= {defect for _, _, defect in new}


def test_r19_the_origin_control_table_is_four_caught_and_three_missed():
    """표 행삭제 프로브 + 감사 진술 대조 — caught 4 / MISSED 3이 **실측과 일치**한다.

    죽이는 뮤테이션: 어느 행을 지워도 id 집합 단정이 실패한다. 구 게이트를 넓혀
    MISSED 행이 걸리게 되면 4/3이 깨져 실패한다(그때는 표를 갱신해야 한다).
    """
    ids = [name for name, _, _, _, _, _ in _R19_ORIGIN_PLANTS]
    assert len(ids) == len(set(ids)) == len(_R19_ORIGIN_PLANT_IDS) == 7
    assert set(ids) == _R19_ORIGIN_PLANT_IDS
    measured = {
        name: bool(_r18_origin_defects(_r19_origin_overrides(filename, kind, payload)))
        for name, filename, kind, payload, _old, _exp in _R19_ORIGIN_PLANTS
    }
    assert {name for name, caught in measured.items() if caught} == {
        name for name in ids if name.startswith("caught:")
    }
    assert sum(measured.values()) == 4
    assert len(ids) - sum(measured.values()) == 3
    for name, _f, _k, _p, old_catches, _exp in _R19_ORIGIN_PLANTS:
        assert old_catches is name.startswith("caught:"), name

    # 기대 열에 **행 단위 독립 핀**을 박는다 — 행별 단정이 느슨해지거나 기대 문자열이
    # 틀려도 여기서 걸린다. 결함 문자열 전수가 아니라 "그 행이 노린 결함이 실제로 나오는가"를
    # 행마다 잰다(결함 전수는 게이트가 자라면 늘 수 있으므로 포함으로 잰다).
    measured_defects = {
        name: {
            defect
            for _, _, defect in _r19_origin_defects(_r19_origin_overrides(filename, kind, payload))
        }
        for name, filename, kind, payload, _old, _exp in _R19_ORIGIN_PLANTS
    }
    assert {
        name: expected in measured_defects[name]
        for name, _f, _k, _p, _old, expected in _R19_ORIGIN_PLANTS
    } == dict.fromkeys(_R19_ORIGIN_PLANT_IDS, True)
    # 일곱 행이 **서로 다른 것**을 실증한다 — 같은 결함을 두 행이 덮으면 한 행은 잉여다.
    assert len({expected for _n, _f, _k, _p, _o, expected in _R19_ORIGIN_PLANTS}) == 6, (
        "형태 (a)와 (b)는 같은 결함 문자열을 노린다 — 다른 것은 **호출 식별 경로**다"
    )


def test_r19_the_binding_gate_contains_the_round18_origin_gate():
    """포함관계 실측 — 구 게이트가 잡는 것은 새 게이트도 전부 잡는다(병존의 근거).

    구 게이트의 비공허성 심기(round18 `test_r18_the_origin_gate_catches_...`)와 새 표
    7행 전수에서 확인한다.

    죽이는 뮤테이션: 새 게이트가 인자 출처 검사를 빼고 정의 스캔만 하면 caught 4행에서
    포함관계가 깨져 실패한다.
    """
    for _name, filename, kind, payload, _old, _exp in _R19_ORIGIN_PLANTS:
        overrides = _r19_origin_overrides(filename, kind, payload)
        old = {defect for _, _, defect in _r18_origin_defects(overrides)}
        new = {defect for _, _, defect in _r19_origin_defects(overrides)}
        assert old <= new, sorted(old - new)


def test_r19_the_producer_class_method_pairs_are_a_bijection_onto_production():
    """(클래스, 메서드) 쌍 동결 — **더해도 지워도** 실패한다.

    round18은 메서드 **이름**만 동결했다. 이름만으로는 "다른 클래스에 같은 이름을 하나 더"
    라는 한 줄 편집이 게이트를 오인시킨다(형태 c). 쌍으로 동결하면 그 편집이 여기서 멈춘다.

    죽이는 뮤테이션:
      · `_R19_REGISTERED_PRODUCER_METHODS`에서 행을 지우면 프로덕션 정의가 남아 실패한다.
      · 쓰이지 않는 쌍을 미리 등기하면 `stale`이 비지 않아 실패한다 — 선제 등기는
        가짜 생산자 클래스를 **미리 승인해 두는 것**이다.
    """
    observed = _r19_producer_definitions()
    assert observed == tuple(sorted(_R19_REGISTERED_PRODUCER_METHODS)), observed
    # 이름 집합은 구 등기부(`_R18_REGISTERED_SENTENCE_PRODUCERS`)와 정확히 일치한다 —
    # 두 표가 어긋나면 한쪽이 거짓말을 하고 있는 것이다.
    assert {method for _owner, method in observed} == set(_R18_REGISTERED_SENTENCE_PRODUCERS)
    assert {owner for owner, _method in observed} == {"ExistingFidRead"}


@pytest.mark.parametrize("index", range(len(_R19_REGISTERED_PRODUCER_METHODS)))
def test_r19_deleting_any_producer_pair_row_is_caught(index: int):
    """행삭제 프로브 — 쌍 등기부에서 어느 행을 지워도 프로덕션이 결함을 낸다(공허한 행 0).

    `sys.modules[__name__]`으로 **지금 돌고 있는 모듈**을 집는다 — 이름을 손으로 적으면
    이 파일을 다른 이름으로 실은 하네스(뮤테이션 대조군이 그렇다)에서 **엉뚱한 모듈**을
    갈아끼우고, 그러면 프로브가 자기 심기를 못 본다.
    """
    import sys as _sys

    _self = _sys.modules[__name__]

    shrunk = (
        _R19_REGISTERED_PRODUCER_METHODS[:index] + _R19_REGISTERED_PRODUCER_METHODS[index + 1 :]
    )
    saved = _self._R19_REGISTERED_PRODUCER_METHODS
    try:
        _self._R19_REGISTERED_PRODUCER_METHODS = shrunk
        defects = _r19_origin_defects()
        assert defects != (), shrunk
        assert all(defect.startswith("unfrozen-producer:") for _, _, defect in defects), defects
    finally:
        _self._R19_REGISTERED_PRODUCER_METHODS = saved


def test_r19_an_unbound_receiver_on_an_assembler_named_method_is_a_defect():
    """형제 축 — 조립기 **이름의 메서드**를 임의 객체에 달아도 걸린다.

    형태 (b)의 일반화다: 수신자가 바인딩된 모듈이 아니면 우리는 그것이 무엇인지 모르고,
    모르는 것은 통과시키지 않는다.

    죽이는 뮤테이션: `receiver_defect` 갈래를 지우면 첫 단정이 실패한다.
    """
    overrides = _r19_origin_overrides(
        "apply.py",
        "append",
        '_leak19 = _whatever.assemble_sentences(f"조각 {_target.instrument_type}.")\n',
    )
    defects = {defect for _, _, defect in _r19_origin_defects(overrides)}
    assert "assembler-via-unbound-receiver:_whatever" in defects, defects
    assert "interp:_target.instrument_type" in defects, defects
    assert _r18_origin_defects(overrides) == (), "구 게이트가 이미 잡았다면 이 행은 공허하다"


def test_r19_the_assembler_binding_vectors_are_swept_across_every_vwx_module():
    """[HARD 4 형제 표면 전수 · 규율 A] 조립기에 닿는 **세 바인딩 경로**를 vwx 전 모듈에서 전수.

    round19 실측:
      · 조립기 호출 자리 **1건**(`patchplan.py`) — 지역 `def` 바인딩 경로.
      · 조립기를 별칭으로 들여오는 자리 **0건**, 모듈 속성으로 부르는 자리 **0건**.
      · 그러나 **별칭 import 자체는 프로덕션에 실재한다**
        (`address.py`: `normalize_address as console_normalize_address`).
        곧 형태 (a)는 가설이 아니라 이 저장소가 이미 쓰는 문법이다 — 그것이 이 규율의 근거다.

    죽이는 뮤테이션:
      · `server/vwx/`에 조립기 별칭 import나 모듈 속성 호출이 생기면 두 번째·세 번째 단정이
        실패한다(그때는 그 자리가 출처 게이트를 받는지 함께 보여야 한다).
      · 프로덕션에서 별칭 import가 모두 사라지면 네 번째 단정이 실패한다 — 그러면 이 규율의
        비공허성 근거가 사라진 것이고, 표를 갱신해야 한다.
    """
    import ast

    aliased: list[tuple[str, str, str]] = []
    module_attribute_assembler: list[tuple[str, int]] = []
    for module_name, tree in _r17_vwx_trees():
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                aliased.extend(
                    (module_name, alias.name, alias.asname) for alias in node.names if alias.asname
                )
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in _R18_SENTENCE_ASSEMBLERS
            ):
                module_attribute_assembler.append((module_name, node.lineno))

    sites = _r19_assembler_call_sites()
    assert len(sites) == 1, sites
    assert sites[0][0] == "patchplan.py" and sites[0][3] is None, sites
    assert [row for row in aliased if row[1] in _R18_SENTENCE_ASSEMBLERS] == []
    assert module_attribute_assembler == []
    assert aliased, "별칭 import가 프로덕션에 하나도 없으면 형태 (a)의 실재 근거가 사라진다"


def test_r19_the_producer_method_names_are_unique_to_one_class_across_vwx():
    """[HARD 4 형제 표면 전수 · 규율 B] 인자 없는 메서드 이름의 **클래스 다중성**을 전수.

    형태 (c)의 일반형은 "같은 이름의 인자 없는 메서드가 두 클래스에 있다"다. round19 실측:
    `server/vwx/`에는 그런 이름이 **실제로 있다**(`to_dict`가 17개 클래스,
    `_skipped_checks`가 2개 클래스). 곧 이름만으로 생산자를 판정하는 것은 이 저장소에서
    이미 안전하지 않다 — 등기 생산자 두 이름이 지금 1:1인 것은 **우연**이고, 그 우연을
    쌍 동결로 고정하는 것이 처방이다.

    죽이는 뮤테이션:
      · `notes`나 `reason`을 다른 클래스에 하나 더 달면 첫 단정이 실패한다.
      · 중복 이름이 하나도 없어지면 마지막 단정이 실패한다 — 그러면 이 위험의 실재 근거가
        사라진 것이고, 그때는 쌍 동결의 비용을 다시 따져야 한다.
    """
    import ast
    from collections import defaultdict

    owners: dict[str, set[str]] = defaultdict(set)
    for _module_name, tree in _r17_vwx_trees():
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for member in node.body:
                if (
                    isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and len(member.args.args) == 1
                    and not member.args.kwonlyargs
                ):
                    owners[member.name].add(node.name)

    for method in _R18_REGISTERED_SENTENCE_PRODUCERS:
        assert owners[method] == {"ExistingFidRead"}, (method, sorted(owners[method]))
    shared = {name: sorted(classes) for name, classes in owners.items() if len(classes) > 1}
    assert shared, "인자 없는 동명 메서드가 하나도 없으면 형태 (c)의 실재 근거가 사라진다"
    assert set(_R18_REGISTERED_SENTENCE_PRODUCERS) & set(shared) == set(), sorted(shared)
