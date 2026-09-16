"""충돌 검출 시험 — `LD-CONFLICT-001` (SPEC-LDCOMPILE-001 C3).

이 검사의 핵심은 **판정 단위가 group 이 아니라 fixture 라는 것**이다. group 단위로 뭉치면
겹친 두 group 이 같은 fixture 의 같은 축을 동시에 써도 보이지 않는다 — 그것이
`acceptance.md` AC-LDPLUGIN-011 1번이 못박은 것이다.

반열림 구간이 두 번째 축이다. `transition 끝 == 다음 시작` 은 **허용**이고, 겹치면 동일
값이어도 conflict 다. 넓게 잡으면 정상 계획이 막히고, 좁게 잡으면 실제 충돌이 샌다 —
그래서 양쪽을 다 쏜다.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from server.tests.test_director_validate_ready import (
    GROUPS,
    baseline,
    color,
    cue,
    fx_start,
    fx_stop,
    intensity,
    make_plan,
    terminal,
)

_EXAMPLES = Path(__file__).resolve().parents[2] / ".moai/specs/SPEC-LDPLUGIN-001/examples"


def _load(name: str) -> dict[str, Any]:
    return json.loads((_EXAMPLES / name).read_text(encoding="utf-8"))


@pytest.fixture
def plan() -> dict[str, Any]:
    return _load("plan.json")


@pytest.fixture
def context() -> dict[str, Any]:
    return _load("context.json")


def _blocking(diagnostics: list[Any]) -> list[Any]:
    return [d for d in diagnostics if d.blocking]


def _rules(diagnostics: list[Any]) -> set[str]:
    return {d.rule_id for d in diagnostics}


# --------------------------------------------------------------------------- #
# 겹친 group 을 만들려면 context 를 손으로 짜야 한다 — 규범 예제의 두 group 은
# fixture 가 서로 분리되어 있어서 겹침을 만들 수 없다.
# --------------------------------------------------------------------------- #

OVERLAP_A = "group-odd"
OVERLAP_B = "group-warm"


def _group(group_id: str, fixture_ids: list[str]) -> dict[str, Any]:
    return {
        "group_id": group_id,
        "membership_revision": 1,
        "fixture_ids": fixture_ids,
        "safe_state": {
            "intensity_pct": 0,
            "color_ref": "color-amber",
            "position_ref": "pos-center",
            "beam_ref": "beam-wash",
            "active_fx": [],
            "ownership": "held",
        },
    }


def _preset(preset_id: str, kind: str, axes: list[str]) -> dict[str, Any]:
    return {
        "preset_id": preset_id,
        "content_revision": 1,
        "content_digest": "sha256:" + "0" * 64,
        "content_status": "synthetic",
        "kind": kind,
        "label": preset_id,
        "group_ids": [OVERLAP_A, OVERLAP_B, *GROUPS],
        "affects_axes": axes,
        "settle_ms": 0,
        "evidence_refs": ["ev-presets"],
    }


def overlap_context() -> dict[str, Any]:
    """`fixture-2` 를 두 group 이 공유한다 — group 단위로 뭉치면 안 보이는 구조."""
    return {
        "groups": [
            _group(OVERLAP_A, ["fixture-1", "fixture-2", "fixture-3"]),
            _group(OVERLAP_B, ["fixture-2", "fixture-4"]),
        ],
        "presets": [
            _preset("color-amber", "color", ["color"]),
            _preset("color-blue", "color", ["color"]),
            _preset("pos-center", "position", ["pan", "tilt"]),
            _preset("pos-wide", "position", ["pan", "tilt"]),
            _preset("beam-wash", "beam", ["beam"]),
            _preset("beam-narrow", "beam", ["beam"]),
            _preset("fx-pulse", "fx", ["intensity"]),
            _preset("fx-sweep", "fx", ["pan", "tilt"]),
        ],
    }


def disjoint_context() -> dict[str, Any]:
    """겹치지 않는 두 group — 양성 대조의 원본."""
    ctx = overlap_context()
    ctx["groups"] = [
        _group(GROUPS[0], ["fixture-1", "fixture-2"]),
        _group(GROUPS[1], ["fixture-3", "fixture-4"]),
    ]
    return ctx


def two_cue_plan(
    first: list[dict[str, Any]],
    second: list[dict[str, Any]],
    *,
    second_at_ms: int,
    controlled: tuple[str, ...],
) -> dict[str, Any]:
    return make_plan(
        [cue("cue-a", 0, first), cue("cue-b", second_at_ms, second)],
        [terminal(g) for g in controlled],
        controlled=controlled,
    )


# --------------------------------------------------------------------------- #
# 양성 대조 먼저 — 아무것도 막지 않는 상태를 확인한다
# --------------------------------------------------------------------------- #


class TestPositiveControl:
    def test_contract_example_has_no_conflict(self, plan, context):
        """규범 예제는 충돌이 없다. 여기서 빨간 것은 계기가 넓게 잡은 것이다."""
        from server.director.validate.conflict import check_conflicts

        assert _blocking(check_conflicts(plan, context)) == []

    def test_disjoint_groups_writing_simultaneously_pass(self):
        """겹치지 않는 두 group 의 동시 변경은 통과한다 (`AC-LDPLUGIN-011` 양성 대조)."""
        from server.director.validate.conflict import check_conflicts

        plan = make_plan(
            [
                cue(
                    "cue-a",
                    0,
                    [intensity(GROUPS[0], 50, fade=2000), intensity(GROUPS[1], 80, fade=2000)],
                )
            ],
            [terminal(g) for g in GROUPS],
        )
        assert _blocking(check_conflicts(plan, disjoint_context())) == []

    def test_different_axes_on_the_same_fixture_pass(self):
        """같은 fixture 라도 축이 다르면 충돌이 아니다 — 축이 판정 단위다."""
        from server.director.validate.conflict import check_conflicts

        plan = make_plan(
            [
                cue(
                    "cue-a",
                    0,
                    [
                        intensity(OVERLAP_A, 50, fade=3000),
                        color(OVERLAP_B, "color-blue", fade=3000),
                    ],
                )
            ],
            [terminal(g) for g in (OVERLAP_A, OVERLAP_B)],
            controlled=(OVERLAP_A, OVERLAP_B),
        )
        assert _blocking(check_conflicts(plan, overlap_context())) == []


# --------------------------------------------------------------------------- #
# 1번 — fixture 로 전개해야 보인다
# --------------------------------------------------------------------------- #


class TestFixtureExpansion:
    def test_overlapping_groups_same_axis_is_conflict(self):
        """두 group 이 `fixture-2` 를 공유하고 같은 축을 겹치는 시간에 쓴다."""
        from server.director.validate.conflict import check_conflicts

        plan = make_plan(
            [
                cue(
                    "cue-a",
                    0,
                    [
                        intensity(OVERLAP_A, 50, fade=3000),
                        intensity(OVERLAP_B, 80, fade=3000),
                    ],
                )
            ],
            [terminal(g) for g in (OVERLAP_A, OVERLAP_B)],
            controlled=(OVERLAP_A, OVERLAP_B),
        )
        diagnostics = _blocking(check_conflicts(plan, overlap_context()))
        assert "LD-CONFLICT-001" in _rules(diagnostics)

    def test_the_shared_fixture_is_named_in_the_reason(self):
        """진단이 어느 fixture 인지 말한다 — 사람이 고칠 수 있어야 한다."""
        from server.director.validate.conflict import check_conflicts

        plan = make_plan(
            [
                cue(
                    "cue-a",
                    0,
                    [intensity(OVERLAP_A, 50, fade=3000), intensity(OVERLAP_B, 80, fade=3000)],
                )
            ],
            [terminal(g) for g in (OVERLAP_A, OVERLAP_B)],
            controlled=(OVERLAP_A, OVERLAP_B),
        )
        reasons = " ".join(d.reason for d in check_conflicts(plan, overlap_context()) if d.blocking)
        assert "fixture-2" in reasons
        assert "fixture-1" not in reasons, "겹치지 않는 fixture 까지 고발하면 넓게 잡은 것이다"

    def test_group_level_grouping_would_miss_it(self):
        """대조 — 같은 계획을 group 이 분리된 context 로 보면 충돌이 없다.

        즉 이 검사가 잡는 것은 fixture 전개이며, 계획 문면이 아니다.
        """
        from server.director.validate.conflict import check_conflicts

        plan = make_plan(
            [
                cue(
                    "cue-a",
                    0,
                    [intensity(OVERLAP_A, 50, fade=3000), intensity(OVERLAP_B, 80, fade=3000)],
                )
            ],
            [terminal(g) for g in (OVERLAP_A, OVERLAP_B)],
            controlled=(OVERLAP_A, OVERLAP_B),
        )
        ctx = overlap_context()
        ctx["groups"] = [_group(OVERLAP_A, ["fixture-1"]), _group(OVERLAP_B, ["fixture-2"])]
        assert _blocking(check_conflicts(plan, ctx)) == []


# --------------------------------------------------------------------------- #
# 2·3·5번 — 겹침은 동일 값이어도 conflict, 끝==시작은 허용
# --------------------------------------------------------------------------- #


class TestOverlapBoundaries:
    def test_identical_value_overlap_is_still_conflict(self):
        """같은 값이어도 conflict — 「결과가 같으니 괜찮다」는 이 층의 답이 아니다."""
        from server.director.validate.conflict import check_conflicts

        plan = make_plan(
            [
                cue(
                    "cue-a",
                    0,
                    [intensity(OVERLAP_A, 50, fade=3000), intensity(OVERLAP_B, 50, fade=3000)],
                )
            ],
            [terminal(g) for g in (OVERLAP_A, OVERLAP_B)],
            controlled=(OVERLAP_A, OVERLAP_B),
        )
        assert "LD-CONFLICT-001" in _rules(_blocking(check_conflicts(plan, overlap_context())))

    def test_transition_end_equals_next_start_passes(self):
        """5번 — 반열림 구간. `[0,3000)` 다음 `[3000,...)` 은 허용이다."""
        from server.director.validate.conflict import check_conflicts

        plan = two_cue_plan(
            [intensity(OVERLAP_A, 50, fade=3000)],
            [intensity(OVERLAP_B, 80, fade=1000)],
            second_at_ms=3000,
            controlled=(OVERLAP_A, OVERLAP_B),
        )
        assert _blocking(check_conflicts(plan, overlap_context())) == []

    def test_one_ms_before_the_end_is_conflict(self):
        """경계 바깥을 쏜다 — 2999ms 에 시작하면 1ms 겹친다."""
        from server.director.validate.conflict import check_conflicts

        plan = two_cue_plan(
            [intensity(OVERLAP_A, 50, fade=3000)],
            [intensity(OVERLAP_B, 80, fade=1000)],
            second_at_ms=2999,
            controlled=(OVERLAP_A, OVERLAP_B),
        )
        assert "LD-CONFLICT-001" in _rules(_blocking(check_conflicts(plan, overlap_context())))

    def test_duplicate_instant_write_is_conflict(self):
        """3번 — 한 instant 의 중복 쓰기. fade=0 이라 구간 길이가 0 이다."""
        from server.director.validate.conflict import check_conflicts

        plan = make_plan(
            [cue("cue-a", 0, [intensity(OVERLAP_A, 50), intensity(OVERLAP_B, 80)])],
            [terminal(g) for g in (OVERLAP_A, OVERLAP_B)],
            controlled=(OVERLAP_A, OVERLAP_B),
        )
        assert "LD-CONFLICT-001" in _rules(_blocking(check_conflicts(plan, overlap_context())))

    def test_instant_at_the_end_of_a_fade_passes(self):
        """길이 0 구간이 남의 끝점에 놓이는 것은 허용 — 끝==시작 규칙과 같은 규칙이다."""
        from server.director.validate.conflict import check_conflicts

        plan = two_cue_plan(
            [intensity(OVERLAP_A, 50, fade=3000)],
            [intensity(OVERLAP_B, 80)],
            second_at_ms=3000,
            controlled=(OVERLAP_A, OVERLAP_B),
        )
        assert _blocking(check_conflicts(plan, overlap_context())) == []

    def test_instant_inside_a_fade_is_conflict(self):
        """길이 0 구간이 남의 구간 안이면 conflict — fade 중간을 덮어쓴다."""
        from server.director.validate.conflict import check_conflicts

        plan = two_cue_plan(
            [intensity(OVERLAP_A, 50, fade=3000)],
            [intensity(OVERLAP_B, 80)],
            second_at_ms=1500,
            controlled=(OVERLAP_A, OVERLAP_B),
        )
        assert "LD-CONFLICT-001" in _rules(_blocking(check_conflicts(plan, overlap_context())))


class TestDelayIsReserved:
    def test_delay_window_is_a_reservation(self):
        """7번 — delay 구간도 예약이다. `delay=3000` 이면 0ms 부터 이미 잡혀 있다."""
        from server.director.validate.conflict import check_conflicts

        plan = two_cue_plan(
            [intensity(OVERLAP_A, 50, delay=3000, fade=1000)],
            [intensity(OVERLAP_B, 80)],
            second_at_ms=1000,
            controlled=(OVERLAP_A, OVERLAP_B),
        )
        assert "LD-CONFLICT-001" in _rules(_blocking(check_conflicts(plan, overlap_context())))

    def test_reservation_ends_after_delay_plus_fade(self):
        """예약 끝은 `at_ms + delay + fade` 다 — 그 시각에 시작하면 통과한다."""
        from server.director.validate.conflict import check_conflicts

        plan = two_cue_plan(
            [intensity(OVERLAP_A, 50, delay=3000, fade=1000)],
            [intensity(OVERLAP_B, 80)],
            second_at_ms=4000,
            controlled=(OVERLAP_A, OVERLAP_B),
        )
        assert _blocking(check_conflicts(plan, overlap_context())) == []

    def test_one_ms_before_delay_plus_fade_is_conflict(self):
        from server.director.validate.conflict import check_conflicts

        plan = two_cue_plan(
            [intensity(OVERLAP_A, 50, delay=3000, fade=1000)],
            [intensity(OVERLAP_B, 80)],
            second_at_ms=3999,
            controlled=(OVERLAP_A, OVERLAP_B),
        )
        assert "LD-CONFLICT-001" in _rules(_blocking(check_conflicts(plan, overlap_context())))


# --------------------------------------------------------------------------- #
# 4·6번 — FX affects_axes
# --------------------------------------------------------------------------- #


class TestFxAxisOverlap:
    def test_fx_overlapping_static_write_is_conflict(self):
        """`fx-pulse` 는 intensity 축을 쓴다 — 그 사이의 static intensity 는 conflict."""
        from server.director.validate.conflict import check_conflicts

        plan = make_plan(
            [
                cue("cue-a", 0, baseline(OVERLAP_A)),
                cue("cue-fx", 10000, [fx_start(OVERLAP_A, "pulse-a")]),
                cue("cue-static", 15000, [intensity(OVERLAP_A, 60)]),
                cue("cue-off", 20000, [fx_stop(OVERLAP_A, "pulse-a")]),
            ],
            [terminal(OVERLAP_A)],
            controlled=(OVERLAP_A,),
        )
        assert "LD-CONFLICT-001" in _rules(_blocking(check_conflicts(plan, overlap_context())))

    def test_two_fx_sharing_an_axis_is_conflict(self):
        from server.director.validate.conflict import check_conflicts

        plan = make_plan(
            [
                cue("cue-a", 0, baseline(OVERLAP_A)),
                cue("cue-fx1", 10000, [fx_start(OVERLAP_A, "pulse-a")]),
                cue("cue-fx2", 12000, [fx_start(OVERLAP_A, "pulse-b")]),
                cue("cue-off1", 20000, [fx_stop(OVERLAP_A, "pulse-a")]),
                cue("cue-off2", 22000, [fx_stop(OVERLAP_A, "pulse-b")]),
            ],
            [terminal(OVERLAP_A)],
            controlled=(OVERLAP_A,),
        )
        assert "LD-CONFLICT-001" in _rules(_blocking(check_conflicts(plan, overlap_context())))

    def test_two_fx_on_different_axes_pass(self):
        """`fx-pulse`(intensity) 와 `fx-sweep`(pan·tilt) 는 겹쳐도 축이 다르다."""
        from server.director.validate.conflict import check_conflicts

        plan = make_plan(
            [
                cue("cue-a", 0, baseline(OVERLAP_A)),
                cue("cue-fx1", 10000, [fx_start(OVERLAP_A, "pulse-a")]),
                cue("cue-fx2", 12000, [fx_start(OVERLAP_A, "sweep-a", preset_ref="fx-sweep")]),
                cue("cue-off1", 20000, [fx_stop(OVERLAP_A, "pulse-a")]),
                cue("cue-off2", 22000, [fx_stop(OVERLAP_A, "sweep-a")]),
            ],
            [terminal(OVERLAP_A)],
            controlled=(OVERLAP_A,),
        )
        assert _blocking(check_conflicts(plan, overlap_context())) == []

    def test_axis_reuse_before_stop_fade_completes_is_conflict(self):
        """6번 — stop fade 가 끝나기 전에 그 축을 다시 쓰면 conflict."""
        from server.director.validate.conflict import check_conflicts

        plan = make_plan(
            [
                cue("cue-a", 0, baseline(OVERLAP_A)),
                cue("cue-fx", 10000, [fx_start(OVERLAP_A, "pulse-a")]),
                cue("cue-off", 20000, [fx_stop(OVERLAP_A, "pulse-a", fade=2000)]),
                cue("cue-reuse", 21000, [intensity(OVERLAP_A, 60)]),
            ],
            [terminal(OVERLAP_A, intensity_pct=60)],
            controlled=(OVERLAP_A,),
        )
        assert "LD-CONFLICT-001" in _rules(_blocking(check_conflicts(plan, overlap_context())))

    def test_axis_reuse_after_stop_fade_passes(self):
        """양성 대조 — stop fade 완료 시각에 다시 쓰면 통과한다."""
        from server.director.validate.conflict import check_conflicts

        plan = make_plan(
            [
                cue("cue-a", 0, baseline(OVERLAP_A)),
                cue("cue-fx", 10000, [fx_start(OVERLAP_A, "pulse-a")]),
                cue("cue-off", 20000, [fx_stop(OVERLAP_A, "pulse-a", fade=2000)]),
                cue("cue-reuse", 22000, [intensity(OVERLAP_A, 60)]),
            ],
            [terminal(OVERLAP_A, intensity_pct=60)],
            controlled=(OVERLAP_A,),
        )
        assert _blocking(check_conflicts(plan, overlap_context())) == []

    def test_unknown_fx_preset_is_blocking_not_silently_axisless(self):
        """preset 을 못 찾으면 `affects_axes` 를 빈 집합으로 두지 않는다.

        빈 집합으로 두면 FX 가 아무 축도 안 쓰는 것처럼 보여 충돌이 조용히 사라진다.
        """
        from server.director.validate.conflict import check_conflicts

        plan = make_plan(
            [
                cue("cue-a", 0, baseline(OVERLAP_A)),
                cue("cue-fx", 10000, [fx_start(OVERLAP_A, "x", preset_ref="fx-nonexistent")]),
                cue("cue-off", 20000, [fx_stop(OVERLAP_A, "x")]),
            ],
            [terminal(OVERLAP_A)],
            controlled=(OVERLAP_A,),
        )
        assert _blocking(check_conflicts(plan, overlap_context()))


# --------------------------------------------------------------------------- #
# 8번 + 계기 주의 — 순서·개수
# --------------------------------------------------------------------------- #


class TestOrderIndependence:
    def _three_way(self, order: list[int]) -> dict[str, Any]:
        writes = [
            intensity(OVERLAP_A, 10, fade=5000),
            intensity(OVERLAP_B, 20, fade=5000),
            intensity(OVERLAP_A, 30, delay=1000, fade=1000),
        ]
        return make_plan(
            [cue("cue-a", 0, [writes[i] for i in order])],
            [terminal(g) for g in (OVERLAP_A, OVERLAP_B)],
            controlled=(OVERLAP_A, OVERLAP_B),
        )

    def test_array_order_does_not_overwrite_earlier_conflicts(self):
        """8번 — 순서를 뒤집어도 충돌 개수와 대상 fixture 가 같다.

        진단 **문면**까지 같기를 요구하지는 않는다: pointer 가 `/cues/0/actions/{j}` 라
        배열 첨자를 담으므로 순서를 뒤집으면 문면은 당연히 달라진다. 순서와 무관해야
        하는 것은 판정이며, 판정의 관측 가능한 형태는 개수와 대상이다.
        """
        from server.director.validate.conflict import check_conflicts

        ctx = overlap_context()

        def summary(order: list[int]) -> tuple[int, set[str]]:
            found = _blocking(check_conflicts(self._three_way(order), ctx))
            fixtures = {
                token for d in found for token in d.reason.split() if token.startswith("fixture-")
            }
            return len(found), fixtures

        forward = summary([0, 1, 2])
        reverse = summary([2, 1, 0])
        assert forward == reverse
        assert forward[0] >= 2, "겹침 셋 중 하나만 보고하면 뒤 것이 앞 것을 덮은 것이다"
        assert "fixture-2" in forward[1]

    def test_both_directions_of_the_count_delta_are_checked(self):
        """계기 주의 — `|A|−|B|` 를 `A\\B` 로 읽지 않는다. 양방향 차집합을 본다."""
        from server.director.validate.conflict import check_conflicts

        ctx = overlap_context()
        conflicted = {d.reason for d in _blocking(check_conflicts(self._three_way([0, 1, 2]), ctx))}
        clean = {
            d.reason
            for d in _blocking(
                check_conflicts(
                    make_plan(
                        [cue("cue-a", 0, [intensity(OVERLAP_A, 10, fade=5000)])],
                        [terminal(g) for g in (OVERLAP_A, OVERLAP_B)],
                        controlled=(OVERLAP_A, OVERLAP_B),
                    ),
                    ctx,
                )
            )
        }
        assert clean - conflicted == set()
        assert conflicted - clean != set()


# --------------------------------------------------------------------------- #
# 판정 불능은 통과가 아니다
# --------------------------------------------------------------------------- #


class TestUndecidableIsBlocking:
    def test_missing_context_is_blocking(self):
        """context 없이는 fixture 전개를 할 수 없다 — 판정 불능을 수용으로 바꾸지 않는다."""
        from server.director.validate.conflict import check_conflicts

        plan = make_plan(
            [cue("cue-a", 0, [intensity(OVERLAP_A, 50)])],
            [terminal(OVERLAP_A)],
            controlled=(OVERLAP_A,),
        )
        assert _blocking(check_conflicts(plan, None))

    def test_group_absent_from_context_is_blocking(self):
        """계획이 context 에 없는 group 을 쓰면 blocking — 빈 fixture 집합으로 두지 않는다."""
        from server.director.validate.conflict import check_conflicts

        plan = make_plan(
            [cue("cue-a", 0, [intensity("group-ghost", 50)])],
            [terminal("group-ghost")],
            controlled=("group-ghost",),
        )
        assert _blocking(check_conflicts(plan, overlap_context()))


# --------------------------------------------------------------------------- #
# 배선
# --------------------------------------------------------------------------- #


class TestWiredIntoThePipeline:
    def test_stage_three_reports_conflicts(self):
        """3단이 `check_conflicts` 를 실제로 부른다."""
        from server.director.validate.pipeline import run_stages

        plan = make_plan(
            [
                cue(
                    "cue-a",
                    0,
                    [intensity(OVERLAP_A, 50, fade=3000), intensity(OVERLAP_B, 80, fade=3000)],
                )
            ],
            [terminal(g) for g in (OVERLAP_A, OVERLAP_B)],
            controlled=(OVERLAP_A, OVERLAP_B),
        )
        report = run_stages(plan, overlap_context())
        rules = {d["rule_id"] for d in report.diagnostics if d["blocking"]}
        assert "LD-CONFLICT-001" in rules


class TestRoundingDebtIsActuallyWired:
    """C2 가 남긴 빚 — 호출자가 있는 것과 진단이 나오는 것은 다르다.

    `test_rounding_conflicts_has_a_non_test_caller`(ready 파일)는 grep 으로 **존재**만
    센다. 존재는 도달의 증거가 아니므로, 여기서 실제로 반올림이 접히는 입력을 만들어
    `run_stages` 의 출력에 나타나는지 본다.
    """

    def _fast_context(self, bpm: float) -> dict[str, Any]:
        ctx = overlap_context()
        ctx["beat_map"] = {
            "status": "confirmed",
            "segments": [
                {
                    "start_ms": 0,
                    "end_ms": 60000,
                    "start_beat": 0,
                    "bpm": bpm,
                    "evidence_ref": "ev-beat",
                }
            ],
        }
        return ctx

    def _fx_plan(self, cycle_beats: float) -> dict[str, Any]:
        return make_plan(
            [
                cue("cue-a", 0, baseline(OVERLAP_A)),
                cue(
                    "cue-fx",
                    10000,
                    [fx_start(OVERLAP_A, "pulse-a", cycle_beats=cycle_beats)],
                ),
                cue("cue-off", 12000, [fx_stop(OVERLAP_A, "pulse-a")]),
            ],
            [terminal(OVERLAP_A)],
            controlled=(OVERLAP_A,),
        )

    def test_collapsing_fx_cycle_reaches_the_pipeline_verdict(self):
        """날조 대조군 — 박 간격이 1ms 아래로 접히는 FX 는 `LD-TIME-002` 로 막힌다.

        `bpm=60000` 이면 1박이 1ms 이므로 `cycle_beats=0.0625` 는 0.0625ms 마다 경계를
        만든다 — 서로 다른 박이 같은 ms 로 접힌다.
        """
        from server.director.validate.pipeline import run_stages

        report = run_stages(self._fx_plan(0.0625), self._fast_context(60000))
        rules = {d["rule_id"] for d in report.diagnostics if d["blocking"]}
        assert "LD-TIME-002" in rules, "반올림 충돌이 경로를 통과했다 — 배선이 공허하다"

    def test_a_normal_fx_cycle_does_not_trigger_it(self):
        """구멍도 같이 잰다 — 정상 cycle 에서는 이 진단이 나오지 않는다.

        이것이 없으면 위 시험의 초록이 「무조건 막는다」와 구별되지 않는다.
        """
        from server.director.validate.pipeline import run_stages

        report = run_stages(self._fx_plan(4), self._fast_context(120))
        reasons = [d["reason"] for d in report.diagnostics if "반올림" in d["reason"]]
        assert reasons == []


class TestNoConsoleAndNoArtisticImport:
    def test_modules_do_not_import_osc_or_producers(self):
        """이 층은 OSC 도 예술 producer 도 부르지 않는다."""
        import server.director.validate.conflict as conflict_mod
        import server.director.validate.simulate as simulate_mod

        for module in (conflict_mod, simulate_mod):
            source = Path(module.__file__).read_text(encoding="utf-8")
            assert "server.bridge" not in source
            assert "server.looks" not in source
            assert "server.web" not in source
