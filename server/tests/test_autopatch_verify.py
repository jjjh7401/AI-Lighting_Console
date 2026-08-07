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

import pytest

from server.prechk.inventory import (
    COMPLETE,
    FIXTURE_ROOT,
    FixtureRecord,
    Inventory,
    ReadFailure,
)
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
)
from server.vwx.verdicts import (
    ADDRESS_ALREADY_OCCUPIED,
    ADDRESS_CONFLICTS_WITH_EXISTING,
    ALREADY_PATCHED_IDENTICAL,
    EXISTING_FOOTPRINT_UNREADABLE,
    EXISTING_IDENTITY_UNCONFIRMED,
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
    return FixtureTypeLibrary(types=types, available=available)


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
        # [round15 D] 라이브러리 확정 이름과 **콘솔 원문**을 함께 싣는다 — 원문은 사유·detail
        # 문장에서 빠졌고(2b④) 대신 여기 구조화 필드로 온다(2c①).
        "observed_type_display": "FixtureType 3",
        "observed_mode_display": "2 Mode 2",
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
    """[N01] 열거가 절단되면 '그 이름의 타입이 없다'를 단정할 수 없다 — 모호성 가드가 공허해진다."""
    truncated = FixtureTypeLibrary(
        types=(LibraryType(index=2, name="Robin MMX"),), available=True, truncated=True
    )
    (observed,) = _console(_record(1, "1.1", "FixtureType 2", "1 Mode 1"), library=truncated)
    assert observed.type_name is None
    assert observed.identity_resolved is False


def test_the_truncation_refusal_control_a_complete_library_still_resolves():
    """비공허성 — 같은 입력이 완전한 열거에서는 해석된다."""
    complete = FixtureTypeLibrary(
        types=(LibraryType(index=2, name="Robin MMX", modes=(LibraryMode(index=1, name=MODE_1),)),),
        available=True,
        truncated=False,
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
    library = FixtureTypeLibrary(types=tuple(by_index[i] for i in order))
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


@pytest.mark.parametrize("token", _ROUND15_REASSURING_TOKENS)
def test_every_reassuring_token_is_load_bearing(token):
    """단어마다 대조군 — 지워도 잡히지 않는 단어는 장식이다(round14 T09와 같은 규율)."""
    assert _round15_reassurances(f"예비 픽스처가 있다 — {token}") == [token]


@pytest.mark.parametrize("token", _ROUND15_CAUTION_TOKENS)
def test_every_caution_token_is_load_bearing(token):
    assert _round15_cautions(f"이 갈래는 {token}") == [token]


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
    """[round15 D 축 2] 문장은 좌표·필드 이름만, 원문은 구조화 필드로(§0 2b④ + 2c①).

    `screen_idempotent`의 사유 문장에 `occupant.type_display`를 되싣도록 되돌리면 이 단정이
    실패한다 — 그리고 그 회귀가 곧 위 거짓 양성의 원인이다.
    """
    exclusion = _cd_occupied_handoff().exclusions[0]
    assert "CD 5" not in exclusion.reason
    assert "9 Mode 9" not in exclusion.reason
    assert CD_TOKEN.search(exclusion.reason) is None
    assert "유니버스 1 주소 1" in exclusion.reason
    assert exclusion.observed_type_display == "CD 5"
    assert exclusion.observed_mode_display == "9 Mode 9"
    assert exclusion.to_dict()["observed_type_display"] == "CD 5"


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
    assert result.observed_type_display == "CD 5"
    assert result.observed_mode_display == "9 Mode 9"
    assert result.to_dict()["observed_mode_display"] == "9 Mode 9"


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
