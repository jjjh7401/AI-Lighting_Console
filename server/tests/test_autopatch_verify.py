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
    REFUTED_REMEDY_TOKENS,
    RecordingDeployPipeline,
    RecordingExecutionPort,
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


@pytest.mark.parametrize("word", _PLUGIN_OUTCOME_WORDS)
def test_every_banned_plugin_outcome_word_is_load_bearing(word):
    """[round14 T09] **단어마다** 대조군 — 지우면 잡히지 않는 단어는 장식이다."""
    assert _plugin_outcome_parameters({f"probe_{word}_arg"}) == [f"probe_{word}_arg"]


@pytest.mark.parametrize("token", REFUTED_REMEDY_TOKENS)
def test_every_refuted_remedy_token_is_load_bearing(token):
    planted = f"실행 전에 {token}을(를) 먼저 확인하라."
    assert [t for t in REFUTED_REMEDY_TOKENS if t in planted] != []
