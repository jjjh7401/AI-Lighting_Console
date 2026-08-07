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


#: (상수 이름, 표면 이름, 그 표면을 프로덕션에서 만들어 오는 호출)
_R16_HUMAN_SURFACE_PROBES = (
    ("PLUGIN_EXIT_IS_NOT_SUCCESS", "handoff.warnings", _r16_delivered_warnings),
    ("END_TO_END_UNVERIFIED", "handoff.warnings", _r16_delivered_warnings),
    ("HUMAN_EXECUTION_PROCEDURE", "handoff.procedure", _r16_delivered_procedure),
    ("DELIVERY_WARNINGS", "handoff.warnings", _r16_delivered_warnings),
    ("ZERO_CREATED_GUIDANCE", "verification.guidance", _r16_verification_guidance),
    ("NO_AUTO_CORRECTION", "verification.guidance", _r16_verification_guidance),
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
    "observed_type_display",
    "observed_mode_display",
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
    """
    from server.vwx.patchplan import _parse_fid_range

    parsed = _parse_fid_range({"start": 100, "end": 100 + offset})
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
# M35 — 표시 문자열 구조화 필드는 **2객체 × 2필드 = 4칸**이다
#
# round15 D는 네 칸을 만들고 두 칸만 단정했다(`observed_type_display`는 제외 객체에서만,
# `observed_mode_display`는 검증 객체에서만). 그래서 `patchplan.py`의
# `"observed_mode_display": self.observed_mode_display`를 `None`으로 바꿔도 전부 통과했다.
# 여기서는 네 칸을 표로 열거하고, 그 표가 **두 dataclass의 실제 필드 목록과 전단사**임을
# 따로 단정한다 — 필드를 더하면 표 없이는 통과하지 못하고, 표에서 칸을 지우면 실패한다.
# ==========================================================================

#: (객체 이름, 필드 이름) — 손으로 열거한다. 아래 전단사 단정이 프로덕션과 맞춘다.
_R16_DISPLAY_CELLS = (
    ("PatchTargetExclusion", "observed_type_display"),
    ("PatchTargetExclusion", "observed_mode_display"),
    ("VerificationResult", "observed_type_display"),
    ("VerificationResult", "observed_mode_display"),
)


def _r16_display_carrying_classes():
    from server.vwx.apply import VerificationResult
    from server.vwx.patchplan import PatchTargetExclusion

    return (PatchTargetExclusion, VerificationResult)


def test_the_display_cell_table_is_a_bijection_onto_the_production_dataclass_fields():
    """[round16 M35] 표시 문자열 칸 표가 **프로덕션 필드 목록**과 1:1이다.

    `PatchTargetExclusion`·`VerificationResult` 어느 쪽에서든 `observed_*_display` 필드를
    지우거나 더하면 이 단정이 깨진다. 표에서 칸을 지워도 깨진다 — 그래서 아래 네 칸짜리
    parametrize가 "넷 중 둘만" 상태로 조용히 되돌아갈 수 없다.
    """
    import dataclasses

    produced = tuple(
        (cls.__name__, field.name)
        for cls in _r16_display_carrying_classes()
        for field in dataclasses.fields(cls)
        if field.name.startswith("observed_") and field.name.endswith("_display")
    )
    assert produced == _R16_DISPLAY_CELLS


def test_every_display_cell_is_also_a_key_of_its_objects_payload():
    """[round16 M35] 네 칸 전부가 `to_dict()` **키로** 나간다 — 객체 필드만으로는 부족하다.

    `patchplan.py`의 `"observed_mode_display": self.observed_mode_display` 줄을 지우면
    (필드는 남아 있으므로 위 전단사는 통과하는데) 이 단정이 실패한다.
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
    for class_name, field_name in _R16_DISPLAY_CELLS:
        assert field_name in payload_keys[class_name], (class_name, field_name)


def _r16_display_cell_objects():
    """네 칸을 **같은 관측**(`'CD 5'` · `'9 Mode 9'`)으로 채우는 두 프로덕션 산출물."""
    exclusion = _cd_occupied_handoff().exclusions[0]
    result = verify_patch(
        (_entry("a", 1, 1),),
        console_fixtures=_console(_record(1, "1.1", "CD 5", "9 Mode 9")),
    ).results[0]
    return {"PatchTargetExclusion": exclusion, "VerificationResult": result}


@pytest.mark.parametrize(
    "class_name,field_name",
    _R16_DISPLAY_CELLS,
    ids=[f"{cls}.{field}" for cls, field in _R16_DISPLAY_CELLS],
)
def test_each_display_cell_carries_the_observed_string_in_object_and_in_payload(
    class_name: str, field_name: str
):
    """[round16 M35] 네 칸 **전부**가 관측 원문을 싣는다 — 객체에서도, payload에서도.

    `patchplan.py`의 `"observed_mode_display": self.observed_mode_display`를 `None`으로
    바꾸면 `PatchTargetExclusion.observed_mode_display` 행이 실패한다(round15는 통과했다).
    `apply.py`의 `"observed_type_display": self.observed_type_display`를 `None`으로 바꾸면
    `VerificationResult.observed_type_display` 행이 실패한다.
    """
    expected = {"observed_type_display": "CD 5", "observed_mode_display": "9 Mode 9"}[field_name]
    obj = _r16_display_cell_objects()[class_name]

    assert getattr(obj, field_name) == expected
    assert obj.to_dict()[field_name] == expected
    # 그리고 그 원문은 사람이 읽는 **문장**에는 없다 — 구조화 필드로만 나간다(§0 2b④).
    sentence = getattr(obj, "reason", None) or obj.detail
    assert expected not in sentence


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


# (행 이름, 기대 코드 또는 None, 점유 기록, 해석 override, 구조화 필드를 채우는가,
#  문장에 **우리가 승인한** 이름이 실리는가)
_R16_SCREEN_BRANCH_ROWS = (
    ("no_occupant", None, (), None, False, False),
    (
        "multiple_occupants",
        EXISTING_IDENTITY_UNCONFIRMED,
        (
            (1, "1.1", _R16_LED_DISPLAY, _R16_MODE1_DISPLAY),
            (2, "1.1", _R16_LED_DISPLAY, _R16_MODE1_DISPLAY),
        ),
        None,
        False,
        False,
    ),
    (
        "type_confirmation_pending",
        TYPE_CONFIRMATION_PENDING,
        ((1, "1.1", _R16_LED_DISPLAY, _R16_MODE1_DISPLAY),),
        "unresolved",
        True,
        False,
    ),
    (
        "existing_identity_unconfirmed",
        EXISTING_IDENTITY_UNCONFIRMED,
        ((1, "1.1", "CD 5", "9 Mode 9"),),
        None,
        True,
        False,
    ),
    (
        "already_patched_identical",
        ALREADY_PATCHED_IDENTICAL,
        ((1, "1.1", _R16_LED_DISPLAY, _R16_MODE1_DISPLAY),),
        None,
        True,
        True,
    ),
    (
        "address_conflicts_with_existing",
        ADDRESS_CONFLICTS_WITH_EXISTING,
        ((1, "1.1", _R16_LED_DISPLAY, _R16_MODE2_DISPLAY),),
        None,
        True,
        False,
    ),
)


def _r16_production_exclusion_sites():
    """`screen_idempotent` 본문의 `_exclusion(...)` 호출을 **소스 순서대로** 뽑는다.

    각 사이트에서 (제외 코드, 구조화 표시 필드를 넘기는가)를 읽는다 — 표와 맞춰야 하는
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
            _r16_apply_constant(call.args[1].id),
            any(kw.arg == "observed_type_display" for kw in call.keywords)
            and any(kw.arg == "observed_mode_display" for kw in call.keywords),
        )
        for call in calls
    )


def test_the_screen_branch_table_is_a_bijection_onto_the_production_exclusion_sites():
    """[round16 S16-05] 갈래 표가 `screen_idempotent`의 **실제 제외 사이트**와 1:1이다.

    ① 표에서 갈래 행을 지우면 실패한다. ② 프로덕션에 갈래를 더하면 행 없이는 통과하지
    못한다. ③ `ADDRESS_CONFLICTS_WITH_EXISTING`(또는 형제 갈래 어느 쪽이든)에서
    `observed_type_display=` · `observed_mode_display=`를 떼면 두 번째 열이 어긋나 실패한다 —
    round15가 그 상태로 통과했다.
    """
    table = tuple(
        (code, fills) for _, code, _, _, fills, _ in _R16_SCREEN_BRANCH_ROWS if code is not None
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
    "name,code,records,resolution_kind,fills_display,approved_names_in_sentence",
    _R16_SCREEN_BRANCH_ROWS,
    ids=[row[0] for row in _R16_SCREEN_BRANCH_ROWS],
)
def test_every_screen_idempotent_branch_obeys_the_same_display_contract(
    name, code, records, resolution_kind, fills_display, approved_names_in_sentence
):
    """[round16 S16-05] 여섯 갈래 **전부**가 같은 규약을 지킨다.

    이전 판의 `ADDRESS_CONFLICTS_WITH_EXISTING`을 되돌리면
    (`f"{occupant.type_name} · {occupant.mode_name} 픽스처가 점유하고 있다"` +
    구조화 필드 `None`) 'address_conflicts_with_existing' 행이 **두 군데서** 실패한다:
    문장에 점유자 이름이 들어가고, `observed_*_display`가 비어 있다.
    """
    console_records = tuple(_record(*row) for row in records)
    resolutions = (_r16_unresolved_resolution(),) if resolution_kind == "unresolved" else None
    screened = _r16_screen(console_records, resolutions=resolutions)

    if code is None:
        assert screened.exclusions == ()
        assert [entry.candidate_id for entry in screened.entries] == ["a"]
        return

    assert screened.entries == ()
    (exclusion,) = screened.exclusions
    assert exclusion.code == code

    occupants = _console(*console_records)
    if fills_display:
        # ② 단일 점유자를 특정한 갈래는 관측 원문을 구조화 필드로 싣는다.
        (occupant,) = occupants
        assert exclusion.observed_type_display == occupant.type_display
        assert exclusion.observed_mode_display == occupant.mode_display
        assert exclusion.to_dict()["observed_type_display"] == occupant.type_display
        assert exclusion.to_dict()["observed_mode_display"] == occupant.mode_display
    else:
        # 점유자를 특정하지 못한 갈래는 **아무 원문도 주장하지 않는다**.
        assert exclusion.observed_type_display is None
        assert exclusion.observed_mode_display is None

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

# (행 이름, 기대 outcome, 점유 기록, read_complete, 구조화 필드를 채우는가)
_R16_VERIFY_BRANCH_ROWS = (
    (
        "multiple_found",
        VERIFICATION_IDENTITY_UNCONFIRMED,
        (
            (1, "1.1", _R16_LED_DISPLAY, _R16_MODE1_DISPLAY),
            (2, "1.1", _R16_LED_DISPLAY, _R16_MODE1_DISPLAY),
        ),
        True,
        False,
    ),
    ("absent_but_read_incomplete", VERIFICATION_IDENTITY_UNCONFIRMED, (), False, False),
    ("absent_and_read_complete", VERIFICATION_NOT_OBSERVED, (), True, False),
    (
        "identity_unconfirmed",
        VERIFICATION_IDENTITY_UNCONFIRMED,
        ((1, "1.1", "CD 5", "9 Mode 9"),),
        True,
        True,
    ),
    (
        "observed",
        VERIFICATION_OBSERVED,
        ((1, "1.1", _R16_LED_DISPLAY, _R16_MODE1_DISPLAY),),
        True,
        True,
    ),
    (
        "mismatched",
        VERIFICATION_MISMATCHED,
        ((1, "1.1", _R16_LED_DISPLAY, _R16_MODE2_DISPLAY),),
        True,
        True,
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


@pytest.mark.parametrize(
    "name,outcome,records,read_complete,fills_display",
    _R16_VERIFY_BRANCH_ROWS,
    ids=[row[0] for row in _R16_VERIFY_BRANCH_ROWS],
)
def test_every_verify_patch_branch_obeys_the_same_display_contract(
    name, outcome, records, read_complete, fills_display
):
    """[round16 S16-05 형제 표면] `detail` 문장에도 관측 원문이 없고, 단일 점유자면 필드가 찬다.

    `apply.py`의 꼬리
    `observed_type_display=occupant.type_display if occupant is not None else None`을
    `None`으로 바꾸면 'identity_unconfirmed'·'observed'·'mismatched' 세 행이 실패한다.
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
    if fills_display:
        (occupant,) = occupants
        assert result.observed_type_display == occupant.type_display
        assert result.observed_mode_display == occupant.mode_display
        assert result.to_dict()["observed_type_display"] == occupant.type_display
        assert result.to_dict()["observed_mode_display"] == occupant.mode_display
    else:
        assert result.observed_type_display is None
        assert result.observed_mode_display is None

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

_R16_VWX_MODULES = ("apply.py", "patchplan.py", "typemap.py", "verdicts.py")
_R16_UNREGISTERED_CODE = "존재하지 않는 판정 코드"


def _r16_validate_autopatch_sites():
    """`server/vwx/*.py`의 `validate_autopatch(...)` 호출을 (모듈, 어휘식, 값식)으로 전수."""
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
    from server.vwx.typemap import TypeHardStop, _skipped_check
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
        ).row(),
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


#: `_exclusion` 호출 사이트 **전수 표** — (사이트 이름, 함수, 사유 코드, 산출 호출, 필수 문구).
#: 같은 (함수, 코드) 쌍이 두 번 나오는 자리가 있다(`screen_idempotent`의 확인 불가 두 갈래).
#: 그것을 뭉치지 않는 것이 요점이다 — 뭉치면 한 갈래가 비어도 다른 갈래가 가려준다.
_R16_EXCLUSION_SITES = (
    (
        "handoff.type_pending",
        "build_patch_handoff",
        "TYPE_CONFIRMATION_PENDING",
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
        "TYPE_CONFIRMATION_PENDING",
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
    expected_code = getattr(verdicts, code)
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
