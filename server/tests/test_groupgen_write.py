"""RED-GREEN-REFACTOR coverage for server/groupgen/write.py (design.md §6).

The measured pool fixture below is the M0 live-probe result
(progress.md §E.2.3): occupied slots {1, 11, 12, 13, 15}, empty
{2..10, 14, 16+}, truncated:false.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from server.groupgen.write import (
    DEFAULT_GROUP_PLAN_CAP,
    FIXTURE_LIST_TRUNCATED,
    FIXTURE_LIST_UNREAD,
    GROUP_LINE_COLLISION,
    GROUP_PLAN_TOO_LARGE,
    GROUP_POOL_TRUNCATED,
    GROUP_POOL_UNAVAILABLE,
    GROUP_SLOT_OCCUPIED,
    GroupSlotError,
    build_group_write_plan,
    guard_bundle_collision,
    guard_fixture_list_truncation,
    guard_plan_size,
    is_programmer_state,
    measure_empty_slots,
    select_group_slot,
)

MEASURED_GROUPS_SECTION = {
    "ok": True,
    "truncated": False,
    "objects": [{"no": n} for n in (1, 11, 12, 13, 15)],
}
MEASURED_OCCUPIED = frozenset({1, 11, 12, 13, 15})

# 픽스처 단면 가짜는 `objects` 를 실어야 한다(t179). 이 키가 없으면
# `section_refusal` 이 단면을 **미판독**으로 읽는다 — 즉 「읽었고 안 잘렸다」를
# 태우려던 가짜가 실은 「한 줄도 못 읽었다」를 태우고 있었다.
_FIXTURE_OBJECTS = [{"no": n} for n in range(1, 20)]  # childCount 19 와 일치

UNTRUNCATED_FIXTURES_SECTION = {
    "ok": True,
    "truncated": False,
    "childCount": 19,
    "objects": _FIXTURE_OBJECTS,
}
TRUNCATED_FIXTURES_SECTION = {
    "ok": True,
    "truncated": True,
    "childCount": 19,
    # 잘린 목록 — 도착 수가 `childCount` 보다 적다
    "objects": _FIXTURE_OBJECTS[:18],
}

#: `section_refusal` 이 미판독으로 읽는 세 신호. 셋째는 위 가짜들이
#: t179 이전까지 **실수로** 갖고 있던 바로 그 모양이다.
UNREAD_FIXTURES_SECTIONS = (
    pytest.param({"ok": False, "reason": "console did not answer"}, id="not-ok"),
    pytest.param(
        {"ok": True, "truncated": False, "reason": "path_not_resolved"},
        id="reason-string",
    ),
    pytest.param({"ok": True, "truncated": False, "childCount": 19}, id="objects-absent"),
)


# -- select_group_slot -------------------------------------------------------


@pytest.mark.parametrize("occupied", sorted(MEASURED_OCCUPIED))
def test_select_group_slot_statically_blocks_every_occupied_slot(occupied: int) -> None:
    with pytest.raises(GroupSlotError) as excinfo:
        select_group_slot(MEASURED_GROUPS_SECTION, requested=occupied)
    assert excinfo.value.code == GROUP_SLOT_OCCUPIED


def test_select_group_slot_accepts_a_measured_empty_slot() -> None:
    assert select_group_slot(MEASURED_GROUPS_SECTION, requested=2) == 2
    assert select_group_slot(MEASURED_GROUPS_SECTION, requested=14) == 14


def test_select_group_slot_rejects_truncated_pool() -> None:
    truncated = {"ok": True, "truncated": True, "objects": []}
    with pytest.raises(GroupSlotError) as excinfo:
        select_group_slot(truncated, requested=2)
    assert excinfo.value.code == GROUP_POOL_TRUNCATED


def test_select_group_slot_rejects_unreadable_pool() -> None:
    unreadable = {"ok": False, "reason": "timeout"}
    with pytest.raises(GroupSlotError) as excinfo:
        select_group_slot(unreadable, requested=2)
    assert excinfo.value.code == GROUP_POOL_UNAVAILABLE


# -- measure_empty_slots ------------------------------------------------------


def test_measure_empty_slots_matches_the_measured_noncontiguous_pool() -> None:
    assert measure_empty_slots(MEASURED_GROUPS_SECTION, count=12) == (
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        14,
        16,
        17,
    )


def test_measure_empty_slots_never_returns_an_occupied_slot() -> None:
    measured = measure_empty_slots(MEASURED_GROUPS_SECTION, count=20)
    assert MEASURED_OCCUPIED.isdisjoint(measured)


def test_measure_empty_slots_rejects_truncated_pool() -> None:
    truncated = {"ok": True, "truncated": True, "objects": []}
    with pytest.raises(GroupSlotError) as excinfo:
        measure_empty_slots(truncated, count=1)
    assert excinfo.value.code == GROUP_POOL_TRUNCATED


def test_measure_empty_slots_rejects_unreadable_pool() -> None:
    unreadable = {"reason": "no response"}
    with pytest.raises(GroupSlotError) as excinfo:
        measure_empty_slots(unreadable, count=1)
    assert excinfo.value.code == GROUP_POOL_UNAVAILABLE


# -- guard_fixture_list_truncation -------------------------------------------


def test_guard_fixture_list_truncation_rejects_truncated_list() -> None:
    with pytest.raises(GroupSlotError) as excinfo:
        guard_fixture_list_truncation(TRUNCATED_FIXTURES_SECTION)
    assert excinfo.value.code == FIXTURE_LIST_TRUNCATED


def test_guard_fixture_list_truncation_passes_untruncated_list() -> None:
    guard_fixture_list_truncation(UNTRUNCATED_FIXTURES_SECTION)  # must not raise


@pytest.mark.parametrize("section", UNREAD_FIXTURES_SECTIONS)
def test_guard_fixture_list_truncation_refuses_an_unread_list(section) -> None:
    """t179 — 이 가드가 막아야 할 **가장 나쁜 입력**을 막는가.

    이 가드는 잠들어 있다(프로덕션 호출자 0). 깨우는 것은 독스트링이 예고한
    auto-selection caller 하나이고, 그 호출자는 **바로 이 못 읽은 목록에서**
    ``fids`` 를 뽑는다. t179 이전에는 실패 단면에 `truncated` 키가 아예 없어
    그냥 통과했다.

    거절 갈래가 이제 둘이므로 「거절됐다」가 아니라 **어느 사유로** 거절됐는지를
    단언한다(규약 §3) — 거짓 사유로 먼저 거절되면 참 사유가 안 보인다.
    """
    with pytest.raises(GroupSlotError) as excinfo:
        guard_fixture_list_truncation(section)
    assert excinfo.value.code == FIXTURE_LIST_UNREAD
    assert excinfo.value.code != FIXTURE_LIST_TRUNCATED, (
        "미판독을 절단으로 답하면 사람이 페이징을 고치러 가서 안 낫는다"
    )
    assert "never read" in excinfo.value.message


def test_guard_fixture_list_truncation_still_says_truncated_for_a_read_cut_list() -> None:
    """대조군 — 두 갈래가 갈린다. 읽었지만 잘린 목록은 절단으로 답한다."""
    with pytest.raises(GroupSlotError) as excinfo:
        guard_fixture_list_truncation(TRUNCATED_FIXTURES_SECTION)
    assert excinfo.value.code == FIXTURE_LIST_TRUNCATED
    assert "never read" not in excinfo.value.message


# -- build_group_write_plan ---------------------------------------------------


def test_build_group_write_plan_happy_path_emits_the_fixed_chain() -> None:
    plan = build_group_write_plan(
        buckets={"a": (1, 2)},
        names={"a": "GEO Downstage"},
        groups_section=MEASURED_GROUPS_SECTION,
        fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
    )
    assert len(plan.steps) == 1
    step = plan.steps[0]
    assert step.slot == 2  # first measured empty slot
    assert step.fids == (1, 2)
    assert step.commands == (
        "ClearAll",
        "Fixture 1 + 2",
        "Store Group 2",
        "Label Group 2 'GEO Downstage'",
        "ClearAll",
    )
    assert step.verification == (
        "state DataPool/Groups/2",
        "prop DataPool/Groups/2 Name",
    )


def test_build_group_write_plan_always_flags_membership_unverified() -> None:
    plan = build_group_write_plan(
        buckets={"a": (1,)},
        names={"a": "GEO Downstage"},
        groups_section=MEASURED_GROUPS_SECTION,
        fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
    )
    assert plan.unverified == ("membership",)
    assert plan.unverified_reason  # non-empty human-readable string
    assert plan.human_check_commands == ("Group 2",)


def test_unverified_reason_states_membership_as_unmeasured_not_impossible() -> None:
    """사유 문장이 판독 불가를 **단정**하지 않는다 (t49).

    이 문자열은 조작자에게 나가는 고지다. 한때 *"grandMA3 does not expose group
    membership on any readable channel"* 로 단정형이었는데, 그 판정의 전제가
    만료됐다 — RESTORE-001 `readability-survey.md` §A.2 가 지적하고 §A.5 가
    **미측정**으로 하향했으며, 재측정은 그룹이 있는 쇼파일을 기다린다.

    **동작은 이 테스트의 대상이 아니다.** `unverified` 고지도
    `human_check_commands` 도 그대로여야 하고(위 테스트가 잡는다), 여기서 잡는
    것은 **사유 문장의 단정도(斷定度)** 하나다. 불가로 못박힌 채 출하되면
    나중에 판독이 열려도 아무도 다시 열어 보지 않는다.
    """
    plan = build_group_write_plan(
        buckets={"a": (1,)},
        names={"a": "GEO Downstage"},
        groups_section=MEASURED_GROUPS_SECTION,
        fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
    )
    reason = plan.unverified_reason

    # ① 단정형 어휘가 없다 — 되돌리면 여기서 걸린다
    assert "does not expose" not in reason
    assert "cannot be read" not in reason
    assert "impossible" not in reason.replace("'principally impossible' verdict", "")

    # ② 미측정임을 **판정으로** 말한다. 낱말 하나로 잡으면 안 된다 — 뒤쪽
    #    하향 근거절에도 "unmeasured" 가 또 나와서, 앞 판정절을 통째로 지워도
    #    통과해 버린다(t49 뮤테이션 M8 에서 실제로 통과했다). 표기 강조는 자유.
    assert "unmeasured, not settled" in reason.lower()

    # ③ 하향 근거에 도달할 수 있다 — §E.2.8 만 달면 그게 만료 지적을
    #    받은 기록인 줄 모른다
    assert "RESTORE-001" in reason
    assert "§A.2" in reason
    assert "§A.5" in reason

    # ④ 실무상 결론은 바뀌지 않았다 — 재조회로는 확인 못 한다
    assert "re-querying after Store cannot" in reason


def test_build_group_write_plan_proceeds_on_truncated_fixture_list() -> None:
    """REQ-GROUPGEN-024 amendment (2026-08-04, user decision): the write path
    consumes caller-supplied ``fids``, not the re-queried fixture listing —
    a truncated listing (39-fixture rig, 18 returned) never blocks an
    explicit-fids group write. This is a LIVE-shape regression: the scenario
    is exactly ``{"ok": True, "truncated": True, "objects": [18 entries]}``
    against a rig whose real ``childCount`` is 39."""
    live_shape_truncated_fixtures = {
        "ok": True,
        "truncated": True,
        "childCount": 39,
        # 39 중 18 만 도착 — 위 독스트링이 적은 그 모양이다(t179 전까지
        # 리터럴엔 `objects` 가 없어 이 검사가 라이브 모양을 안 태웠다)
        "objects": [{"i": n} for n in range(1, 19)],
    }
    plan = build_group_write_plan(
        buckets={"a": (1, 2)},
        names={"a": "GEO Downstage"},
        groups_section=MEASURED_GROUPS_SECTION,
        fixtures_section=live_shape_truncated_fixtures,
    )
    assert len(plan.steps) == 1
    assert plan.steps[0].fids == (1, 2)


def test_build_group_write_plan_structurally_flags_fixture_list_truncation() -> None:
    """Mutation-required: removing the population of ``fixture_list_truncated``
    on the returned plan must turn this test RED — the fact is a STRUCTURAL
    field, never docstring-only prose (함정 6)."""
    plan = build_group_write_plan(
        buckets={"a": (1, 2)},
        names={"a": "GEO Downstage"},
        groups_section=MEASURED_GROUPS_SECTION,
        fixtures_section=TRUNCATED_FIXTURES_SECTION,
    )
    assert plan.fixture_list_truncated is True
    assert plan.fixture_list_truncated_reason  # non-empty human-readable string


def test_build_group_write_plan_flags_no_truncation_when_list_was_complete() -> None:
    plan = build_group_write_plan(
        buckets={"a": (1, 2)},
        names={"a": "GEO Downstage"},
        groups_section=MEASURED_GROUPS_SECTION,
        fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
    )
    assert plan.fixture_list_truncated is False
    assert plan.fixture_list_truncated_reason == ""


#: 미판독 사유에만 나오는 문면. 절단 사유에는 없다.
_PRODUCER_UNREAD_PHRASE = "could not be read at all"


@pytest.mark.parametrize("section", UNREAD_FIXTURES_SECTIONS)
def test_build_group_write_plan_never_calls_an_unread_listing_untruncated(section) -> None:
    """t179 — 생산 지점이 「못 읽었다」를 「안 잘렸다」로 답하지 않는다.

    실패 단면에는 `truncated` 키가 아예 없어 `bool(...)` 이 False 가 됐다. 그
    False 는 사실의 부재가 아니라 **거짓 사실**이다 — 데이터클래스 독스트링이
    「a caller that only reads the plan field still receives the truncation
    fact」라고 약속한 그 필드가, 아무것도 안 읽은 상태에서 「깨끗하게 다
    읽었다」와 바이트 동일로 나갔다.
    """
    plan = build_group_write_plan(
        buckets={"a": (1, 2)},
        names={"a": "GEO Downstage"},
        groups_section=MEASURED_GROUPS_SECTION,
        fixtures_section=section,
    )
    assert plan.fixture_list_truncated is True
    assert _PRODUCER_UNREAD_PHRASE in plan.fixture_list_truncated_reason, (
        "미판독인데 사유가 미판독이라고 말하지 않는다: " + plan.fixture_list_truncated_reason
    )


def test_build_group_write_plan_reports_truncation_as_truncation_not_as_unread() -> None:
    """대조군 ① — 두 사유가 갈린다. 읽었지만 잘린 목록은 절단으로 보고된다."""
    plan = build_group_write_plan(
        buckets={"a": (1, 2)},
        names={"a": "GEO Downstage"},
        groups_section=MEASURED_GROUPS_SECTION,
        fixtures_section=TRUNCATED_FIXTURES_SECTION,
    )
    assert plan.fixture_list_truncated is True
    assert _PRODUCER_UNREAD_PHRASE not in plan.fixture_list_truncated_reason, (
        "절단을 미판독 사유로 보고한다 — 두 갈래가 다시 섞였다: "
        + plan.fixture_list_truncated_reason
    )


def test_build_group_write_plan_passes_a_legitimately_empty_but_read_listing() -> None:
    """대조군 ② — 「빈 관측」은 「관측 없음」이 아니다.

    콘솔이 답했고 그 답이 「없다」인 단면은 정당한 관측이다
    (`server/rig/section.py` 계약). 이 팔이 없으면 위 수정이 필드를 True 로
    굳혀도 초록이 나고, 정상적인 첫 임포트가 영영 「절단」으로 보고된다.
    """
    plan = build_group_write_plan(
        buckets={"a": (1, 2)},
        names={"a": "GEO Downstage"},
        groups_section=MEASURED_GROUPS_SECTION,
        fixtures_section={"ok": True, "truncated": False, "objects": []},
    )
    assert plan.fixture_list_truncated is False
    assert plan.fixture_list_truncated_reason == ""


def test_build_group_write_plan_rejects_truncated_group_pool() -> None:
    truncated_pool = {"ok": True, "truncated": True, "objects": []}
    with pytest.raises(GroupSlotError) as excinfo:
        build_group_write_plan(
            buckets={"a": (1, 2)},
            names={"a": "GEO Downstage"},
            groups_section=truncated_pool,
            fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
        )
    assert excinfo.value.code == GROUP_POOL_TRUNCATED


def test_build_group_write_plan_never_targets_an_occupied_slot() -> None:
    buckets = {f"b{i}": (i,) for i in range(1, 13)}
    names = {key: f"Bucket {key}" for key in buckets}
    plan = build_group_write_plan(
        buckets=buckets,
        names=names,
        groups_section=MEASURED_GROUPS_SECTION,
        fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
    )
    written_slots = {step.slot for step in plan.steps}
    assert written_slots.isdisjoint(MEASURED_OCCUPIED)


def test_write_scope_matches_measured_empty_slots_exactly() -> None:
    """§6.5 정적 단언 — 발화 슬롯 집합 == 실측 빈 슬롯 집합."""
    buckets = {f"b{i}": (i,) for i in range(1, 5)}
    names = {key: f"Bucket {key}" for key in buckets}
    plan = build_group_write_plan(
        buckets=buckets,
        names=names,
        groups_section=MEASURED_GROUPS_SECTION,
        fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
    )
    written_slot_numbers = {
        int(match.group(1))
        for step in plan.steps
        for command in step.commands
        if (match := re.fullmatch(r"Store Group (\d+)", command))
    }
    expected = set(measure_empty_slots(MEASURED_GROUPS_SECTION, count=len(buckets)))
    assert written_slot_numbers == expected


def test_no_double_quote_appears_in_any_emitted_command() -> None:
    plan = build_group_write_plan(
        buckets={"a": (1, 2, 3)},
        names={"a": "GEO Downstage"},
        groups_section=MEASURED_GROUPS_SECTION,
        fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
    )
    for step in plan.steps:
        for command in step.commands:
            assert '"' not in command


def test_label_name_with_single_quote_has_pinned_behavior() -> None:
    """No escape convention exists (00_grammar.md:66) — refusal is pinned."""
    with pytest.raises(ValueError):
        build_group_write_plan(
            buckets={"a": (1,)},
            names={"a": "GEO O'Brien"},
            groups_section=MEASURED_GROUPS_SECTION,
            fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
        )


def test_label_name_with_double_quote_has_pinned_behavior() -> None:
    with pytest.raises(ValueError):
        build_group_write_plan(
            buckets={"a": (1,)},
            names={"a": 'GEO "Downstage"'},
            groups_section=MEASURED_GROUPS_SECTION,
            fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
        )


# -- layering: no transport / safety import ----------------------------------


def test_module_source_imports_no_transport_or_safety() -> None:
    source = Path("server/groupgen/write.py").read_text(encoding="utf-8")
    assert not re.search(r"\bserver\.bridge\b", source)
    assert not re.search(r"\bpythonosc\b", source)
    assert not re.search(r"\bserver\.safety\b", source)


# -- guard_plan_size / grid slot-explosion cap (D-Q6 discipline: reject, ------
#    never warn-and-proceed; never silently truncate) -------------------------


def _wide_grid_buckets(depth: int, lateral: int) -> dict[str, tuple[int, ...]]:
    """A synthetic axis-separated grid bucket set (design.md §D-Q2): depth +
    lateral buckets, ``depth + lateral`` groups total — one fixture per
    bucket is enough, only the bucket *count* matters for the cap."""
    fid = 1
    buckets: dict[str, tuple[int, ...]] = {}
    for i in range(depth):
        buckets[f"depth{i}"] = (fid,)
        fid += 1
    for i in range(lateral):
        buckets[f"lateral{i}"] = (fid,)
        fid += 1
    return buckets


def test_guard_plan_size_accepts_a_request_at_or_below_the_cap() -> None:
    guard_plan_size(DEFAULT_GROUP_PLAN_CAP, cap=DEFAULT_GROUP_PLAN_CAP)  # must not raise


def test_guard_plan_size_rejects_a_request_above_the_cap() -> None:
    with pytest.raises(GroupSlotError) as excinfo:
        guard_plan_size(DEFAULT_GROUP_PLAN_CAP + 1, cap=DEFAULT_GROUP_PLAN_CAP)
    assert excinfo.value.code == GROUP_PLAN_TOO_LARGE
    # error message states what the caller needs and what the cap is
    assert str(DEFAULT_GROUP_PLAN_CAP + 1) in excinfo.value.message
    assert str(DEFAULT_GROUP_PLAN_CAP) in excinfo.value.message


def test_3x10_grid_axis_separated_groups_pass_under_the_default_cap() -> None:
    """3x10 그리드(축별 분리 3+10=13그룹, design.md §D-Q2) — 기본 상한(16) 이하이므로
    거부 없이 전량 발화된다. 이 테스트 이름/독스트링이 곧 '통과가 의도'라는 명세다.
    """
    buckets = _wide_grid_buckets(depth=3, lateral=10)
    names = {key: f"GEO Bucket {key}" for key in buckets}
    plan = build_group_write_plan(
        buckets=buckets,
        names=names,
        groups_section=MEASURED_GROUPS_SECTION,
        fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
    )
    assert len(buckets) == 13
    # 조용한 절단 0: 계획의 step 수 == 요청된 버킷 수 == 할당 슬롯 수.
    assert len(plan.steps) == len(buckets)
    assert len({step.slot for step in plan.steps}) == len(buckets)


def test_5x20_grid_axis_separated_groups_are_rejected_by_the_default_cap() -> None:
    """5x20 그리드(축별 분리 5+20=25그룹) — 기본 상한(16)을 넘으므로 **거부**된다.
    이 테스트 이름/독스트링이 곧 '거부가 의도'라는 명세다 — 부분 계획으로 조용히
    절단하는 대신 GROUP_PLAN_TOO_LARGE 로 전량 거부한다(D-Q6 규율 계승).
    """
    buckets = _wide_grid_buckets(depth=5, lateral=20)
    names = {key: f"GEO Bucket {key}" for key in buckets}
    assert len(buckets) == 25
    with pytest.raises(GroupSlotError) as excinfo:
        build_group_write_plan(
            buckets=buckets,
            names=names,
            groups_section=MEASURED_GROUPS_SECTION,
            fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
        )
    assert excinfo.value.code == GROUP_PLAN_TOO_LARGE


def test_plan_size_cap_is_reachable_and_never_silently_truncates() -> None:
    """A plan above the DEFAULT cap must be entirely refused, never demoted to
    a partial plan covering only the first ``cap`` buckets — mutating
    ``build_group_write_plan`` to silently slice ``buckets`` to ``cap`` and
    proceed would make this RED (no exception, and the plan would carry a
    step count smaller than the requested bucket count, both of which the
    surrounding cap tests already pin)."""
    buckets = _wide_grid_buckets(depth=5, lateral=20)
    names = {key: f"GEO Bucket {key}" for key in buckets}
    with pytest.raises(GroupSlotError):
        build_group_write_plan(
            buckets=buckets,
            names=names,
            groups_section=MEASURED_GROUPS_SECTION,
            fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
        )


def test_max_plan_size_is_an_explicit_per_call_override() -> None:
    """The cap is a policy DEFAULT, not a ceiling baked into the code — a
    caller may explicitly raise it for one call (design.md-mandated
    keyword-only override on build_group_write_plan)."""
    buckets = _wide_grid_buckets(depth=5, lateral=20)
    names = {key: f"GEO Bucket {key}" for key in buckets}
    plan = build_group_write_plan(
        buckets=buckets,
        names=names,
        groups_section=MEASURED_GROUPS_SECTION,
        fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
        max_plan_size=30,
    )
    assert len(plan.steps) == len(buckets) == 25


# -- guard_bundle_collision: the dedupe hazard, refused at build time --------
#
# `run_commands` folds a line that already succeeded into
# `skipped_already_executed` unless it establishes programmer state. A group
# chain's MULTI-fixture selection is not exempt, so a bundle carrying two
# groups over the same fids loses the second selection and stores an empty
# programmer into the slot — `ok:true` on every line, and unreadable
# afterwards (progress.md §E.2.8). Same class of fact, same shape of guard, as
# `server/fx/instantiate.py` and `server/scene/compile.py` `_guard_collision`.

SELECTION_123 = "Fixture 1 + Fixture 2 + Fixture 3"

#: 같은 대상을 규칙서 검증 문법으로 압축한 형태 — 이제 이 모듈이 내는 줄이다.
#: 반복 키워드형(위)과 달리 `_SELECTION_OPERAND` 가 **매치한다**. 둘을 나란히
#: 두는 이유는 t66 이 고친 것이 정확히 그 차이이기 때문이다.
COMPACT_123 = "Fixture 1 Thru 3"


def test_guard_bundle_collision_refuses_a_repeated_non_exempt_line() -> None:
    with pytest.raises(GroupSlotError) as excinfo:
        guard_bundle_collision([SELECTION_123, "Store Group 2", SELECTION_123])
    assert excinfo.value.code == GROUP_LINE_COLLISION
    assert SELECTION_123 in excinfo.value.message


def test_guard_bundle_collision_allows_a_repeated_exempt_line() -> None:
    """Non-vacuity in the other direction: the chain opens AND closes with
    `ClearAll` on purpose — two MOMENTS, not one instruction typed twice. A
    guard that refused those would refuse every plan this module builds."""
    assert is_programmer_state("ClearAll") is True
    guard_bundle_collision(["ClearAll", "Store Group 2", "ClearAll"])  # must not raise


def test_guard_bundle_collision_allows_a_repeated_single_fixture_selection() -> None:
    """A ONE-fixture selection IS exempt (`Fixture 1` matches the bare
    selection form), so it was never the line at risk — pinning it keeps the
    guard from being read as "any repeated selection"."""
    assert is_programmer_state("Fixture 1") is True
    assert is_programmer_state(SELECTION_123) is False
    guard_bundle_collision(["Fixture 1", "Store Group 2", "Fixture 1"])  # must not raise


def _two_identical_fid_groups_plan():
    """The ordinary shape that triggers this: a 1:1 manufacturer:model rig
    makes `type_axis_groups` emit byte-identical fid tuples for two axes."""
    return build_group_write_plan(
        buckets={"right": (1, 2, 3), "left": (1, 2, 3)},
        names={"right": "GEO Stage Right", "left": "GEO Stage Left"},
        groups_section=MEASURED_GROUPS_SECTION,
        fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
    )


def test_the_concatenated_plan_no_longer_collides_because_the_selection_is_exempt() -> None:
    """t66 — 이 검사는 **뒤집혔다.** 뒤집힌 이유를 함께 못박는다.

    예전에는 두 그룹이 같은 fid 를 고르면 이어 붙인 번들이 거절됐다. 선택 줄이
    반복 키워드형이라 `is_programmer_state` 의 면제를 못 받았고, 그래서
    run_commands dedupe 가 둘째 선택을 떨어뜨렸기 때문이다. 지금은 압축형을
    내고 그 형태는 면제를 받으므로 **둘째 선택이 떨어지지 않는다** — 거절해야
    할 위험 자체가 사라졌다.

    단언을 약하게 바꾸는 것이므로 **무엇이 그것을 성립시키는지**를 같이 잰다.
    아래 면제 단언이 False 로 돌아가면 이 검사는 그 자리에서 빨개져야 한다.
    """
    plan = _two_identical_fid_groups_plan()
    for step in plan.steps:
        guard_bundle_collision(step.commands)  # 각 단계는 여전히 단독으로 안전하다
    selections = [c for step in plan.steps for c in step.commands if c.startswith("Fixture")]
    assert selections == [COMPACT_123, COMPACT_123]
    assert is_programmer_state(COMPACT_123) is True, (
        "압축형이 면제를 못 받으면 아래 이어붙임은 다시 위험해진다"
    )
    concatenated = [command for step in plan.steps for command in step.commands]
    guard_bundle_collision(concatenated)  # 더는 충돌이 아니다


def test_a_genuine_collision_is_still_refused() -> None:
    """위 검사가 가드를 통째로 무력화한 것이 아님을 반대편에서 잰다 —
    면제 대상이 아닌 줄이 반복되면 여전히 거절된다."""
    with pytest.raises(GroupSlotError) as excinfo:
        guard_bundle_collision(["Store Group 2", COMPACT_123, "Store Group 2"])
    assert excinfo.value.code == GROUP_LINE_COLLISION
    assert "Store Group 2" in excinfo.value.message


def test_two_identical_fid_groups_still_build_a_full_two_step_plan() -> None:
    """The guard is bundle-scoped, never plan-scoped: two groups over the same
    fids are a legitimate request and must still be planned in full."""
    plan = _two_identical_fid_groups_plan()
    assert [step.slot for step in plan.steps] == [2, 3]
    assert all(COMPACT_123 in step.commands for step in plan.steps)


def test_build_group_write_plan_screens_every_step_it_builds(monkeypatch) -> None:
    """Non-vacuity for the guard's placement: the plan builder must actually
    call it, on each step's own chain. Deleting the call makes this RED."""
    observed: list[tuple[str, ...]] = []
    real = guard_bundle_collision

    def _recording(commands):
        observed.append(tuple(commands))
        return real(commands)

    monkeypatch.setattr("server.groupgen.write.guard_bundle_collision", _recording)
    plan = _two_identical_fid_groups_plan()
    assert observed == [step.commands for step in plan.steps]


# -- the dedupe exemption set is the SAME set the tool layer uses ------------
#
# `server/fx/instantiate.py`'s `@MX:ANCHOR` obligation, inherited here: this
# module decides which of ITS OWN lines the dedupe will compare. NARROWER than
# the tool's is a false alarm (loud, harmless); WIDER waves through a line the
# dedupe then drops, silently. Both directions are asserted — a set equality
# has no cheaper form. The mirror test is
# `server/tests/test_fx_boundary.py::TestTheDedupeExemptionSetsAreEqual`.


def _pattern_set(patterns) -> set[tuple[str, int]]:
    """A compiled-regex tuple as comparable (pattern text, flags) pairs."""
    return {(p.pattern, p.flags) for p in patterns}


def _both_declarations():
    from server.groupgen.write import _PROGRAMMER_STATE_COMMANDS as write_side
    from server.orchestrator.tools import _PROGRAMMER_STATE_COMMANDS as tool_side

    return write_side, tool_side


def test_the_two_declarations_are_the_same_set() -> None:
    write_side, tool_side = _both_declarations()
    assert _pattern_set(write_side) == _pattern_set(tool_side)


def test_neither_declaration_is_empty() -> None:
    # Non-vacuity: two empty tuples are equal and would prove nothing.
    write_side, tool_side = _both_declarations()
    assert len(_pattern_set(write_side)) == 3
    assert len(_pattern_set(tool_side)) == 3


def test_the_comparison_notices_a_widened_tool_side() -> None:
    # The dangerous direction: the tool exempts MORE than this guard knows.
    write_side, tool_side = _both_declarations()
    widened = (*tool_side, re.compile(r"Store\s+Group\s+\d+", re.IGNORECASE))
    assert _pattern_set(write_side) != _pattern_set(widened)


def test_the_comparison_notices_a_narrowed_tool_side() -> None:
    write_side, tool_side = _both_declarations()
    assert _pattern_set(write_side) != _pattern_set(tool_side[:-1])


def test_the_comparison_notices_a_changed_flag() -> None:
    # A same-text pattern with different flags is a different matcher —
    # dropping IGNORECASE on one side alone diverges on "clearall".
    write_side, tool_side = _both_declarations()
    reflagged = tuple(re.compile(p.pattern) for p in tool_side)
    assert _pattern_set(write_side) != _pattern_set(reflagged)


#: Lines that separate the two predicates if either is consumed differently
#: (a `search` instead of a `fullmatch` would exempt `ClearAll Sequence 1`).
ADVERSARIAL_LINES = (
    "ClearAll",
    "Clear",
    "clearall",
    "Fixture 1",
    "Fixture 1 Thru 10",
    "Group 2",
    SELECTION_123,  # 반복 키워드형 — 면제 밖 (t66 이 고친 그 형태)
    COMPACT_123,  # 압축형 — 면제 안. 둘을 나란히 둬야 차이가 관측된다
    "ClearAll Sequence 1",  # fullmatch says no; a search would say yes
    "Store Group 2",
    "Label Group 2 'GEO Stage Right'",
    "  ClearAll  ",  # both sides strip before matching
)


def _emitted_lines() -> list[str]:
    buckets = {"a": (1,), "b": (1, 2, 3), "c": (4, 5)}
    names = {"a": "GEO A", "b": "GEO B", "c": "GEO C"}
    plan = build_group_write_plan(
        buckets=buckets,
        names=names,
        groups_section=MEASURED_GROUPS_SECTION,
        fixtures_section=UNTRUNCATED_FIXTURES_SECTION,
    )
    return [command for step in plan.steps for command in step.commands]


def test_the_predicate_corpus_is_not_degenerate() -> None:
    # An all-exempt or all-non-exempt corpus makes agreement trivial.
    lines = _emitted_lines() + list(ADVERSARIAL_LINES)
    assert len(_emitted_lines()) == 15
    assert {is_programmer_state(line) for line in lines} == {True, False}


def test_both_predicates_agree_on_every_line_this_module_emits() -> None:
    from server.orchestrator.tools import _is_programmer_state as tool_side

    disagreements = [
        (line, is_programmer_state(line), tool_side(line))
        for line in _emitted_lines() + list(ADVERSARIAL_LINES)
        if is_programmer_state(line) != tool_side(line)
    ]
    assert disagreements == []


def test_a_trailing_object_defeats_the_exemption_on_both_sides() -> None:
    from server.orchestrator.tools import _is_programmer_state as tool_side

    assert is_programmer_state("ClearAll") is True
    assert is_programmer_state("ClearAll Sequence 1") is False
    assert tool_side("ClearAll") is True
    assert tool_side("ClearAll Sequence 1") is False
