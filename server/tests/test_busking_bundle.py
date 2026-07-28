"""M2 — 슬롯 원장 + 다중 룩 번들 빌더 (AC-BUSKWIZ-003 ~ 007).

SPEC-COPILOT-BUSKWIZ-001 REQ-BUSKWIZ-004 ~ 010.

본 SPEC의 핵심 마일스톤이다. 선행 구현의 하드 결함 2건이 여기서 해소(슬롯
비전진)·회피(`ChangeDestination Root` dedupe 탈락)되며, 그 두 결함이 **실재
한다는 것**과 **본 계층이 감쌌다는 것**을 같은 파일에서 함께 고정한다.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from server.looks import instantiate as instantiate_mod
from server.looks.busking import (
    VALUE_LINE_COLLISION,
    GenreBundle,
    build_genre_bundle,
    instantiate_genre,
    looks_for_genre,
)
from server.looks.instantiate import (
    CONFLICT,
    NO_FREE_SLOT,
    POOL_UNRESOLVED,
    build_instantiation,
    resolve_pools,
)
from server.looks.loader import load_library_from_dir
from server.looks.resolver import resolve_roles
from server.tests.busking_fixtures import FULL_RIG, make_bundle, make_look
from server.tests.test_looks_instantiate import (
    FOUR_FAMILY_ATTRIBUTES,
    _groups,
    _pools,
    _preset,
)

_BUSKING_MODULE = Path("server/looks/busking.py")


def _stores(commands) -> list[str]:
    return [c for c in commands if c.startswith("Store Preset ")]


def _slots(commands, pool: int) -> list[int]:
    out = []
    for c in _stores(commands):
        match = re.fullmatch(rf"Store Preset {pool}\.(\d+)", c)
        if match:
            out.append(int(match.group(1)))
    return out


@pytest.fixture(scope="module")
def library():
    return load_library_from_dir()


# -- AC-BUSKWIZ-003 ------------------------------------------------------------


class TestRigResolvedExactlyOnce:
    """AC-BUSKWIZ-003 — 룩 수에 비례하는 해석 호출은 실패다."""

    def test_eight_looks_resolve_the_rig_once(self, monkeypatch, library):
        import server.looks.busking as busking

        calls = {"roles": 0, "pools": 0}
        real_roles, real_pools = busking.resolve_roles, busking.resolve_pools

        def spy_roles(section):
            calls["roles"] += 1
            return real_roles(section)

        def spy_pools(section):
            calls["pools"] += 1
            return real_pools(section)

        monkeypatch.setattr(busking, "resolve_roles", spy_roles)
        monkeypatch.setattr(busking, "resolve_pools", spy_pools)

        bundle = instantiate_genre(
            library,
            "worship",
            groups_section=_groups(*FULL_RIG),
            preset_pools_section=_pools(),
        )
        assert len(bundle.looks) == 8, "8룩 장르가 아니면 이 테스트는 비례성을 못 본다"
        assert calls == {"roles": 1, "pools": 1}


# -- AC-BUSKWIZ-004 ------------------------------------------------------------


class TestSlotLedger:
    """AC-BUSKWIZ-004 — 어떤 두 룩도 같은 슬롯을 겨냥하지 않는다."""

    def test_segment_1_three_looks_claim_distinct_slots(self):
        # 구간 1 — 점유 (1,2)에서 시작하면 세 룩이 3·4·5를 나눠 갖는다.
        pools = _pools(contents={4: [_preset(1, "기존 A"), _preset(2, "기존 B")]})
        bundle = make_bundle(
            [
                make_look("a", "룩 A", attrs=(("ColorRGB_R", 100),)),
                make_look("b", "룩 B", attrs=(("ColorRGB_R", 90),)),
                make_look("c", "룩 C", attrs=(("ColorRGB_R", 80),)),
            ],
            pools=pools,
        )
        claimed = _slots(bundle.commands, 4)
        assert claimed == [3, 4, 5]
        assert len(claimed) == len(set(claimed))

    def test_segment_2_the_defect_is_real_and_this_layer_wraps_it(self):
        """구간 2 — 결함의 실재와 해소를 함께 고정한다.

        이 테스트가 사라지면 원장의 존재 이유가 문서에만 남는다.
        """
        looks = [
            make_look("a", "룩 A", attrs=(("ColorRGB_R", 100),)),
            make_look("b", "룩 B", attrs=(("ColorRGB_R", 90),)),
            make_look("c", "룩 C", attrs=(("ColorRGB_R", 80),)),
        ]
        resolution = resolve_roles(_groups(*FULL_RIG))
        pools = resolve_pools(_pools())

        # 선행 구현을 동일 PoolIndex로 그대로 N회 부르면 —
        naive = [build_instantiation(look, resolution=resolution, pools=pools) for look in looks]
        naive_slots = [c.slot for plan in naive for c in plan.created if c.family == "Color"]
        assert naive_slots == [1, 1, 1], "결함이 재현되지 않으면 원장은 아무것도 감싸지 않는다"

        # — 본 계층은 같은 입력에서 서로 다른 슬롯을 낸다.
        wrapped = make_bundle(looks)
        assert _slots(wrapped.commands, 4) == [1, 2, 3]

    def test_segment_3_mixed_partial_success_pool_unresolved(self):
        # 구간 3 (i) — Color 풀이 아예 없는 리그: 그 풀 대상 저장만 전량 건너뜀.
        pools = _pools(pools=((1, "Dimmer"), (5, "Beam"), (6, "Focus")))
        bundle = make_bundle(
            [
                make_look("a", "룩 A", attrs=FOUR_FAMILY_ATTRIBUTES),
                make_look("b", "룩 B", attrs=FOUR_FAMILY_ATTRIBUTES),
            ],
            pools=pools,
        )
        reasons = {s.reason for plan in bundle.looks for s in plan.skipped}
        assert POOL_UNRESOLVED in reasons
        assert bundle.skipped_count > 0, "건너뜀 항목이 비어 있으면 이 구간은 공허하다"
        assert bundle.created_count > 0, "저장 가능한 것은 저장되어야 한다"
        assert not bundle.complete

    def test_segment_3_mixed_partial_success_label_conflict(self):
        # 구간 3 (ii) — 콘솔에 같은 이름의 프리셋이 이미 있다.
        pools = _pools(contents={4: [_preset(1, "룩 A")]})
        bundle = make_bundle(
            [
                make_look("a", "룩 A", attrs=(("ColorRGB_R", 100),)),
                make_look("b", "룩 B", attrs=(("ColorRGB_R", 90),)),
            ],
            pools=pools,
        )
        skipped = [s for plan in bundle.looks for s in plan.skipped]
        assert [s.reason for s in skipped] == [CONFLICT]
        assert _slots(bundle.commands, 4) == [2], "충돌한 룩은 건너뛰고 다음 룩은 계속된다"

    def test_segment_4_families_are_independent(self):
        pools = _pools(contents={1: [_preset(1, "기존"), _preset(2, "기존2")]})
        bundle = make_bundle(
            [make_look("a", "룩 A", attrs=(("Dimmer", 80), ("ColorRGB_R", 100)))],
        )
        assert _slots(bundle.commands, 1) == [1]
        assert _slots(bundle.commands, 4) == [1]

        bundle2 = make_bundle(
            [make_look("a", "룩 A", attrs=(("Dimmer", 80), ("ColorRGB_R", 100)))],
            pools=pools,
        )
        assert _slots(bundle2.commands, 1) == [3], "Dimmer 원장만 전진해야 한다"
        assert _slots(bundle2.commands, 4) == [1], "Color 원장은 영향받지 않는다"

    def test_segment_5_observation_wins_over_the_ledger(self):
        # 구간 5 — 미관측 풀은 원장이 있든 없든 사용 불가.
        pools = _pools()
        pools["objects"][3]["contents_unavailable"] = True  # Color(4번 풀) 관측 실패
        bundle = make_bundle(
            [
                make_look("a", "룩 A", attrs=(("ColorRGB_R", 100),)),
                make_look("b", "룩 B", attrs=(("ColorRGB_R", 90),)),
            ],
            pools=pools,
        )
        assert _slots(bundle.commands, 4) == []
        reasons = {s.reason for plan in bundle.looks for s in plan.skipped}
        assert reasons == {NO_FREE_SLOT}

    def test_segment_6_the_ledger_accumulates_labels_too(self):
        """구간 6 — 콘솔에 기존 라벨이 없어도 같은 번들 안의 동명 룩을 막는다.

        `_plan_stores`는 `binding.labels`(콘솔이 이미 가진 것)만 보므로 이
        판정은 원장이 만든다.
        """
        bundle = make_bundle(
            [
                make_look("a", "같은 이름", attrs=(("ColorRGB_R", 100),)),
                make_look("b", "같은 이름", attrs=(("ColorRGB_R", 90),)),
            ],
        )
        assert _slots(bundle.commands, 4) == [1], "두 번째는 저장되지 않는다"
        skipped = [s for plan in bundle.looks for s in plan.skipped]
        assert [s.reason for s in skipped] == [CONFLICT]


# -- AC-BUSKWIZ-005 ------------------------------------------------------------


class TestBundleShape:
    """AC-BUSKWIZ-005 — `ChangeDestination Root` 선두 정확히 1회."""

    @staticmethod
    def _destination() -> str:
        # 리터럴을 이 테스트가 새로 만들지 않는다 — 단일 룩 번들의 선두가 정본이다.
        single = build_instantiation(
            make_look("x", "단일"),
            resolution=resolve_roles(_groups(*FULL_RIG)),
            pools=resolve_pools(_pools()),
        )
        return single.commands[0]

    def test_destination_appears_exactly_once_at_the_head(self):
        dest = self._destination()
        bundle = make_bundle([make_look(f"l{i}", f"룩 {i}") for i in range(5)])
        assert bundle.commands[0] == dest
        assert bundle.commands.count(dest) == 1

    def test_two_looks_do_not_produce_two_destinations(self):
        # ③ 룩별 번들의 단순 연접이 아님을 고정.
        dest = self._destination()
        bundle = make_bundle([make_look("a", "룩 A"), make_look("b", "룩 B")])
        assert bundle.commands.count(dest) == 1

    def test_every_look_cycle_is_clearall_bracketed(self):
        # 페이로드를 서로 다르게 둔다 — 같으면 값 라인 충돌 가드가 뒤 룩을
        # 건너뛰므로 사이클이 하나만 남고, 이 테스트의 주제가 바뀐다.
        bundle = make_bundle(
            [
                make_look("a", "룩 A", attrs=(("Dimmer", 80),)),
                make_look("b", "룩 B", attrs=(("Dimmer", 70),)),
            ]
        )
        body = bundle.commands[1:]  # 선두 목적지 제외
        assert body[0] == "ClearAll"
        assert body[-1] == "ClearAll"
        cycles = [c for c in _split_cycles(body) if c]
        assert len(cycles) == 2, "룩마다 하나의 캡처 사이클"
        for cycle in cycles:
            assert cycle[-1].startswith("Label Preset ")

    def test_no_line_is_lost_to_dedupe(self):
        # ④ 실제 run_commands 경로로 무손실을 확인한다.
        from server.orchestrator.tools import ToolCall, build_toolset

        executed: list[str] = []

        class _Port:
            def execute(self, command: str):
                from server.orchestrator.ports import ExecutionResult

                executed.append(command)
                return ExecutionResult(ok=True, detail="ok")

        class _State:
            def query_state(self, path: str) -> dict:
                return {}

        # 룩마다 값 라인이 달라야 이 테스트가 재는 것을 잰다. 같은 페이로드를
        # 주면 값 라인이 겹쳐 dedupe가 접는데, 그것은 결합 형상의 결함이 아니라
        # 아래 `TestValueLineCollisionHazard`가 따로 다루는 별개 사실이다.
        bundle = make_bundle(
            [make_look(f"l{i}", f"룩 {i}", attrs=(("Dimmer", 40 + i),)) for i in range(4)]
        )
        registry = build_toolset(execution_port=_Port(), state_port=_State())
        execution = registry.dispatch(
            ToolCall(id="t1", name="run_commands", arguments={"commands": list(bundle.commands)})
        )
        statuses = [outcome.status for outcome in execution.command_outcomes]
        assert statuses, "per-command status가 비어 있으면 이 검사는 공허하다"
        assert "skipped_already_executed" not in statuses
        assert set(statuses) == {"executed_ok"}
        assert executed == list(bundle.commands), "콘솔이 받은 것과 번들이 한 줄도 어긋나지 않는다"

    def test_capture_shape_is_fixed_and_not_a_parameter(self):
        # ⑤ per_family 경로 미접촉을 AST 식별자로 고정 (M1의 교훈 — 텍스트 스캔 금지).
        tree = ast.parse(_BUSKING_MODULE.read_text(encoding="utf-8"))
        identifiers = (
            {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
            | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
            | {
                alias.asname or alias.name
                for n in ast.walk(tree)
                if isinstance(n, ast.ImportFrom | ast.Import)
                for alias in n.names
            }
            | {a.arg for n in ast.walk(tree) if isinstance(n, ast.arguments) for a in n.kwonlyargs}
        )
        assert identifiers, "AST에서 식별자를 하나도 모으지 못했다"
        assert "build_instantiation" in identifiers, "비공허성: 실제로 쓰는 이름이 보여야 한다"
        assert {"CAPTURE_PER_FAMILY", "capture_shape", "shape"} & identifiers == set()

    def test_value_lines_never_collide_inside_one_bundle(self, library):
        # ⑤ 값 라인 중복 0건 — 중복이 생기면 두 번째가 dedupe로 탈락하고
        # 빈 프로그래머로 Store가 실행된다.
        for genre in sorted({look.genre for look in library.looks}):
            bundle = make_bundle(looks_for_genre(library, genre))
            values = [c for c in bundle.commands if c.startswith("Attribute ")]
            assert values, f"{genre}: 값 라인이 하나도 없으면 이 검사는 공허하다"
            assert len(values) == len(set(values)), f"{genre}: 값 라인 중복"


def _split_cycles(body: list[str] | tuple[str, ...]) -> list[list[str]]:
    cycles: list[list[str]] = []
    current: list[str] = []
    for command in body:
        if command == "ClearAll":
            if current:
                cycles.append(current)
            current = []
            continue
        current.append(command)
    if current:
        cycles.append(current)
    return cycles


# -- AC-BUSKWIZ-006 / 007 ------------------------------------------------------


class TestNoDestructiveStore:
    """AC-BUSKWIZ-006 — `Store /Overwrite` 0건, 재슬롯 0건."""

    def test_no_overwrite_is_ever_emitted(self, library):
        for genre in sorted({look.genre for look in library.looks}):
            bundle = make_bundle(looks_for_genre(library, genre))
            for command in bundle.commands:
                assert "/overwrite" not in command.casefold()

    def test_source_never_mentions_overwrite(self):
        source = _BUSKING_MODULE.read_text(encoding="utf-8").casefold()
        assert "/overwrite" not in source

    def test_a_conflicted_look_is_not_reslotted(self):
        pools = _pools(contents={4: [_preset(1, "룩 A")]})
        bundle = make_bundle([make_look("a", "룩 A", attrs=(("ColorRGB_R", 100),))], pools=pools)
        assert _slots(bundle.commands, 4) == []
        assert [s.reason for plan in bundle.looks for s in plan.skipped] == [CONFLICT]


class TestUnobservedIsNotEmpty:
    """AC-BUSKWIZ-007 — 미관측과 검증된 빈 풀은 서로 다른 결과를 낸다."""

    def _bundle_with_color(self, *, unavailable: bool) -> GenreBundle:
        pools = _pools()
        if unavailable:
            pools["objects"][3]["contents_unavailable"] = True
        return make_bundle([make_look("a", "룩 A", attrs=(("ColorRGB_R", 100),))], pools=pools)

    def test_unobserved_pool_skips_every_store(self):
        bundle = self._bundle_with_color(unavailable=True)
        assert _slots(bundle.commands, 4) == []
        assert [s.reason for plan in bundle.looks for s in plan.skipped] == [NO_FREE_SLOT]

    def test_verified_empty_pool_stores_at_slot_one(self):
        bundle = self._bundle_with_color(unavailable=False)
        assert _slots(bundle.commands, 4) == [1]
        assert bundle.skipped_count == 0

    def test_the_two_states_differ(self):
        unobserved = self._bundle_with_color(unavailable=True)
        empty = self._bundle_with_color(unavailable=False)
        assert unobserved.commands != empty.commands


class TestDegenerateCases:
    """acceptance.md §D — 퇴화 케이스가 특수 분기를 만들지 않는다."""

    def test_single_look_genre_matches_the_single_look_path(self):
        look = make_look("solo", "혼자")
        bundle = make_bundle([look])
        single = build_instantiation(
            look,
            resolution=resolve_roles(_groups(*FULL_RIG)),
            pools=resolve_pools(_pools()),
        )
        assert bundle.commands == single.commands

    def test_no_mapped_role_yields_an_empty_bundle(self):
        bundle = make_bundle([make_look("a", "룩 A")], groups=((99, "관계 없는 그룹"),))
        assert bundle.commands == ()
        assert bundle.created_count == 0
        assert all(plan.unmapped for plan in bundle.looks)

    def test_empty_look_set_is_an_empty_bundle(self):
        bundle = make_bundle([])
        assert bundle.commands == ()
        assert bundle.looks == ()
        assert not bundle.complete, "룩이 0개인 실행을 '완전 성공'으로 읽지 않는다"


class TestLooksLayerUntouched:
    """REQ-BUSKWIZ-003 — 감싸되 고치지 않는다."""

    def test_pool_index_and_binding_stay_frozen(self):
        assert instantiate_mod.PoolIndex.__dataclass_params__.frozen
        assert instantiate_mod.PoolBinding.__dataclass_params__.frozen

    def test_the_caller_s_pool_index_is_not_mutated(self):
        pools = resolve_pools(_pools())
        before = pools.bindings["Color"]
        build_genre_bundle(
            "rock",
            (make_look("a", "룩 A", attrs=(("ColorRGB_R", 100),)),),
            resolution=resolve_roles(_groups(*FULL_RIG)),
            pools=pools,
        )
        assert pools.bindings["Color"] is before
        assert pools.bindings["Color"].occupied == before.occupied


class TestValueLineCollisionGuard:
    """값 라인 충돌 — **건너뛰기 + 사유 보고**로 막는다 (결정 H).

    `shared_capture`가 안전한 근거는 "출하 32룩 전수에서 값 라인 중복 0건"이며
    이것은 **라이브러리 데이터의 성질이지 구조적 보장이 아니다**. 한 장르 안에
    전체 속성 페이로드가 동일한 룩이 추가되면 값 라인이 겹치고, 두 번째가
    dedupe로 접히면서 **빈 프로그래머 상태로 `Store`가 실행되고 콘솔은 성공으로
    답한다** — M2가 characterization 테스트로 가시화했던 그 위험이다.

    거부(예외)가 아니라 건너뛰기를 고른 이유: `_plan_stores`가 이미
    `conflict`/`no_free_slot`/`pool_unresolved`를 전부 `SkippedStore`로 답한다
    (`server/looks/instantiate.py:325-384`). "이 저장은 안전하게 일어날 수
    없다"에 대한 이 코드베이스의 답은 예외가 아니라 사유를 단 건너뜀이고,
    `LookInstantiationError`는 구조적 기형(알 수 없는 shape, 목적지 불일치)에만
    쓴다. 장르 하나를 통째로 실패시키면 버스킹 준비가 아무 산출도 못 낸다.

    가드는 `busking.py`에 산다 — `instantiate.py`는 PRESERVE이고, 결정 E가
    "frozen을 바깥에서 감싼다"고 정한 그 형상이다.
    """

    @staticmethod
    def _colliding_pair():
        return [
            make_look("a", "룩 A", attrs=(("Dimmer", 80),)),
            make_look("b", "룩 B", attrs=(("Dimmer", 80),)),  # 동일 페이로드
        ]

    def test_the_colliding_look_emits_no_commands(self):
        bundle = make_bundle(self._colliding_pair())
        values = [c for c in bundle.commands if c.startswith("Attribute ")]
        assert len(values) == 1, "겹치는 값 라인은 애초에 번들에 들어가지 않는다"
        assert bundle.spans[1] == (bundle.spans[1][0], bundle.spans[1][0])

    def test_nothing_is_silently_eaten_by_dedupe_anymore(self):
        from server.orchestrator.tools import ToolCall, build_toolset

        executed: list[str] = []

        class _Port:
            def execute(self, command: str):
                from server.orchestrator.ports import ExecutionResult

                executed.append(command)
                return ExecutionResult(ok=True, detail="ok")

        class _State:
            def query_state(self, path: str) -> dict:
                return {}

        bundle = make_bundle(self._colliding_pair())
        registry = build_toolset(execution_port=_Port(), state_port=_State())
        execution = registry.dispatch(
            ToolCall(id="t1", name="run_commands", arguments={"commands": list(bundle.commands)})
        )
        statuses = [o.status for o in execution.command_outcomes]
        assert statuses, "per-command status가 비어 있으면 이 검사는 공허하다"
        assert "skipped_already_executed" not in statuses
        assert executed == list(bundle.commands), "콘솔이 받은 것과 번들이 한 줄도 어긋나지 않는다"

    def test_the_skip_is_reported_per_preset_store_with_its_reason(self):
        bundle = make_bundle(self._colliding_pair())
        second = bundle.looks[1]
        assert second.created == ()
        assert second.skipped, "조용히 사라지지 않는다 — 사유가 남는다"
        assert {s.reason for s in second.skipped} == {VALUE_LINE_COLLISION}
        # 단위는 프리셋 저장 1회다: Dimmer 하나만 값이 있으므로 1건.
        assert second.skipped_count == 1
        assert "a" in second.skipped[0].detail, "충돌 상대를 사유에 남긴다"

    def test_the_first_look_is_untouched(self):
        bundle = make_bundle(self._colliding_pair())
        assert bundle.looks[0].created, "먼저 온 룩은 온전히 저장된다"
        assert bundle.looks[0].skipped == ()

    def test_the_skipped_look_does_not_consume_a_slot(self):
        looks = [
            *self._colliding_pair(),
            make_look("c", "룩 C", attrs=(("Dimmer", 55),)),
        ]
        bundle = make_bundle(looks)
        slots = [p.slot for plan in bundle.looks for p in plan.created]
        assert slots == [1, 2], "건너뛴 룩이 슬롯을 먹으면 원장에 구멍이 남는다"

    def test_the_guard_does_not_raise(self):
        # 거부가 아니라 건너뛰기다 — 장르 전량이 죽지 않는다.
        bundle = make_bundle(self._colliding_pair())
        assert bundle.commands, "번들은 여전히 실행 가능하다"
        assert len(bundle.looks) == 2, "룩은 둘 다 보고에 나타난다"

    def test_distinct_payloads_are_not_affected(self):
        # 비공허성 — 가드가 정상 경로를 잡아먹지 않는다.
        bundle = make_bundle(
            [
                make_look("a", "룩 A", attrs=(("Dimmer", 80),)),
                make_look("b", "룩 B", attrs=(("Dimmer", 81),)),
            ]
        )
        assert all(plan.created for plan in bundle.looks)
        assert all(plan.skipped == () for plan in bundle.looks)

    def test_a_look_that_stored_nothing_does_not_reserve_its_value_line(self):
        # 그룹이 하나도 안 붙은 룩은 값 라인을 발화하지 않았으므로, **같은 번들
        # 안에서** 같은 페이로드의 뒤 룩이 그것 때문에 막히면 안 된다.
        # 번들을 따로 두 개 만들면 원장이 공유되지 않아 이 검사가 공허해진다 —
        # 실제로 이 테스트의 첫 판이 그래서 "빈 룩도 예약" 뮤테이션을 놓쳤다.
        bundle = make_bundle(
            [
                make_look("a", "룩 A", roles=("프론트",), attrs=(("Dimmer", 80),)),
                make_look("b", "룩 B", roles=("백라이트",), attrs=(("Dimmer", 80),)),
            ],
            groups=((11, "Back Wash"),),  # 백라이트만 주소를 가진 리그
        )
        assert bundle.looks[0].commands == (), "앞 룩은 아무것도 발화하지 않았다"
        assert bundle.looks[0].created == ()
        assert bundle.looks[1].created, "발화하지 않은 값 라인은 예약이 아니다"
        assert bundle.looks[1].skipped == ()
