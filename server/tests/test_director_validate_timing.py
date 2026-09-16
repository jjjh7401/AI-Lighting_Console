"""C2 시간 해석 — RED (SPEC-LDCOMPILE-001, REQ-LDPLUGIN-009 계산부).

이 파일이 고정하는 것은 계약 `LD-TIME-001`~`003` + `LD-MIB-001`(음수 ms 부분)이며,
전부 **순수 함수**다. 콘솔 무접촉 · OSC 무접촉.

계약이 아니라 이 파일이 정하는 것이 하나 있다 — **음수 ms 처리의 판정**. 계약 `LD-MIB-001`
은 *"compiler 준비 동작은 negative ms 금지"* 라 하고 기존 코드 `server/lxseq/cue_time.py:27`
의 `CUE_TIME_PREROLL` 은 음수를 지원한다. 감독 판정(2026-09-15): **경로 분리** —
Director 경로는 음수를 거부하고 「원점을 확장한 새 audio/context」를 요청하며, 기존 LXSEQ
시트 경로는 그대로 둔다. 계약 개정 없음. 실측 근거 둘:

1. `CUE_TIME_PREROLL` 참조 8건이 전부 `cue_time.py` 한 파일 안이고 외부 소비자 0건.
2. 스키마의 `at_ms`·`delay_ms`·`fade_ms` 가 `integer, minimum: 0` — 음수는 wire 에서
   표현 자체가 불가능하다. 즉 이 거부는 스키마가 이미 집행하는 것을 진단으로 말하는 것.

`beat_map.status` 의 갈등도 여기서 고정한다. `LD-TIME-002` 는 *"confirmed 근거 필수"* 라
쓰지만 계약 §6.1 이 *"absent/unconfirmed 에서는 beat 기반 FX 를 실행하지 않는다.
`synthetic` 은 합성 harness 에서만 허용한다"* 로 예외를 적었다. 그래서 규칙은
`confirmed`, 또는 (`synthetic` AND `environment == "synthetic"`) 다 — 계약 fixture 가
`synthetic`/`synthetic` 이므로 이 예외 없이는 규범 예제가 스스로 막힌다.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from server.director.validate.diagnostics import (
    STATUS_ACCEPTED,
    STATUS_CONFLICT,
    STATUS_UNSUPPORTED,
)
from server.director.validate.timing import (
    TempoUnknownError,
    beat_at,
    bundle_cues,
    check_timing,
    ms_at_beat,
    round_half_up,
    trig_time_bundles,
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


# ─────────────────────────────────────────────────────────────
# 반올림 — 계약 §7 *"정확한 .5는 +방향"*
# ─────────────────────────────────────────────────────────────


class TestRoundHalfUp:
    """파이썬 내장 `round()` 는 은행가 반올림이라 계약을 위반한다.

    `round(2.5) == 2` 다. 계약은 `.5` 를 **항상 +방향**으로 보내라고 했으므로 3 이어야 한다.
    이 시험이 없으면 누군가 `round()` 로 「단순화」하며 조용히 계약을 깬다.
    """

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (0.5, 1),
            (1.5, 2),
            (2.5, 3),  # round() 는 2 를 답한다
            (3.5, 4),
            (-0.5, 0),  # +방향이므로 0
            (-1.5, -1),  # +방향이므로 -1
            (0.4999, 0),
            (0.5001, 1),
            (12.0, 12),
        ],
    )
    def test_exact_half_goes_toward_plus(self, value: float, expected: int) -> None:
        assert round_half_up(value) == expected

    def test_result_is_int_not_float(self) -> None:
        result = round_half_up(2.5)
        assert isinstance(result, int)
        assert not isinstance(result, bool)

    def test_does_not_match_builtin_round_at_the_boundary(self) -> None:
        # 양성 대조: 두 함수가 실제로 다르다는 것을 명시한다. 같아지면 구현이 round() 다.
        assert round_half_up(2.5) != round(2.5)


# ─────────────────────────────────────────────────────────────
# beat(t) — 계약 LD-TIME-002
# ─────────────────────────────────────────────────────────────


_TWO_SEGMENTS = {
    "status": "confirmed",
    "segments": [
        {"start_ms": 0, "end_ms": 60000, "start_beat": 0, "bpm": 120, "evidence_ref": "ev-a"},
        {"start_ms": 60000, "end_ms": 120000, "start_beat": 120, "bpm": 60, "evidence_ref": "ev-b"},
    ],
}


class TestBeatAt:
    """`beat(t)=start_beat+(t-start_ms)*bpm/60000`, segment 는 `[start,end)`."""

    def test_formula_matches_contract(self) -> None:
        # 120 BPM 에서 30초 = 60 박
        assert beat_at(_TWO_SEGMENTS, 30000) == pytest.approx(60.0)

    def test_segment_is_half_open(self) -> None:
        # 60000 은 앞 segment 의 end 이므로 뒤 segment 가 답한다.
        assert beat_at(_TWO_SEGMENTS, 60000) == pytest.approx(120.0)

    def test_adjacent_segments_are_continuous(self) -> None:
        """인접 경계에서 값이 이어져야 한다 — 앞 segment 의 극한 == 뒤 segment 의 시작."""
        left_limit = beat_at(_TWO_SEGMENTS, 59999)
        right = beat_at(_TWO_SEGMENTS, 60000)
        # 1ms 차이는 120BPM 에서 0.002 박
        assert right - left_limit == pytest.approx(120 / 60000, abs=1e-9)

    def test_unknown_tempo_raises_and_never_assumes_120(self) -> None:
        """계약: *"tempo 불명인데 120 BPM을 가정하지 않는다"*."""
        empty = {"status": "absent", "segments": []}
        with pytest.raises(TempoUnknownError):
            beat_at(empty, 1000)

    def test_time_outside_every_segment_raises(self) -> None:
        with pytest.raises(TempoUnknownError):
            beat_at(_TWO_SEGMENTS, 120000)  # 마지막 end 는 열려 있다


class TestMsAtBeat:
    """beat→ms 는 반올림 경계다 (계약 §7 마지막 문장)."""

    def test_uses_half_up_rounding(self) -> None:
        # 120 BPM: 1 박 = 500ms. 0.001 박 = 0.5ms → +방향
        assert ms_at_beat(_TWO_SEGMENTS, 0.001) == 1

    def test_round_trip_is_stable_on_integer_beats(self) -> None:
        for beat in (0, 1, 2, 60, 119):
            ms = ms_at_beat(_TWO_SEGMENTS, beat)
            assert beat_at(_TWO_SEGMENTS, ms) == pytest.approx(beat)

    def test_unknown_tempo_raises(self) -> None:
        with pytest.raises(TempoUnknownError):
            ms_at_beat({"status": "absent", "segments": []}, 4)


# ─────────────────────────────────────────────────────────────
# 동일 ms 묶기 — 계약 LD-TIME-001
# ─────────────────────────────────────────────────────────────


def _cue(cue_id: str, section_id: str, at_ms: int, n_actions: int = 1) -> dict[str, Any]:
    provenance = {
        "origin": "synthetic",
        "actor_ref": "author-fixture",
        "source_refs": ["src-fixture"],
        "evidence_refs": ["ev-music"],
        "rationale": "시험용 합성 입력이며 실제 관측을 주장하지 않는다.",
    }
    return {
        "cue_id": cue_id,
        "section_id": section_id,
        "at_ms": at_ms,
        "label": f"시험 큐 {cue_id}",
        "provenance": provenance,
        "actions": [
            {
                "op": "intensity_set",
                "action_id": f"{cue_id}-a{i}",
                "group_id": "group-front",
                "provenance": provenance,
                "value_pct": 10,
                "timing": {"intensity": {"delay_ms": 0, "fade_ms": 0, "curve": "linear"}},
            }
            for i in range(n_actions)
        ],
    }


class TestBundleCues:
    """*"같은 ms는 단일 semantic cue로 묶고 array 순서는 deterministic emit order로만"*."""

    def test_same_ms_becomes_one_bundle(self) -> None:
        cues = [_cue("c1", "intro", 0), _cue("c2", "intro", 5000), _cue("c3", "intro", 5000)]
        bundles = bundle_cues({"cues": cues})
        assert [b.at_ms for b in bundles] == [0, 5000]
        assert len(bundles[1].cue_indices) == 2

    def test_bundles_are_time_ordered_even_if_input_is_not(self) -> None:
        cues = [_cue("c1", "intro", 9000), _cue("c2", "intro", 0)]
        assert [b.at_ms for b in bundle_cues({"cues": cues})] == [0, 9000]

    def test_action_order_within_a_bundle_is_preserved(self) -> None:
        """배열 순서는 emit 순서로만 쓴다 — 뒤가 앞을 덮는 의미가 아니므로 순서가 보존된다."""
        cues = [_cue("c1", "intro", 0, n_actions=3)]
        bundle = bundle_cues({"cues": cues})[0]
        assert bundle.action_pointers == [
            "/cues/0/actions/0",
            "/cues/0/actions/1",
            "/cues/0/actions/2",
        ]

    def test_contract_example_bundles_are_strictly_increasing(self, plan: dict[str, Any]) -> None:
        at_values = [b.at_ms for b in bundle_cues(plan)]
        assert at_values == sorted(set(at_values))


# ─────────────────────────────────────────────────────────────
# playback delta — 계약 LD-TIME-003
# ─────────────────────────────────────────────────────────────


class TestTrigTimeBundles:
    """*"첫 GO는 operator, 나머지는 최종 bundle 순서의 절대 시각 차이를 relative_ms로"*."""

    def test_first_bundle_is_manual_go_zero(self) -> None:
        cues = [_cue("c1", "intro", 0), _cue("c2", "intro", 4000)]
        bundles = trig_time_bundles({"cues": cues, "playback": {"mode": "trig_time"}})
        assert bundles[0].trig == "manual_go"
        assert bundles[0].relative_ms == 0

    def test_later_relative_ms_is_delta_from_previous_final_bundle(self) -> None:
        cues = [_cue("c1", "intro", 0), _cue("c2", "intro", 4000), _cue("c3", "intro", 4500)]
        bundles = trig_time_bundles({"cues": cues, "playback": {"mode": "trig_time"}})
        assert [b.relative_ms for b in bundles] == [0, 4000, 500]

    def test_absolute_at_ms_is_never_passed_through_as_trig(self) -> None:
        """*"기존 emitter에 절대 at_ms를 그대로 TrigTime으로 넘기지 않는다"*."""
        cues = [_cue("c1", "intro", 0), _cue("c2", "intro", 35000)]
        bundles = trig_time_bundles({"cues": cues, "playback": {"mode": "trig_time"}})
        assert bundles[1].relative_ms == 35000  # 우연히 같은 값
        cues2 = [_cue("c1", "intro", 0), _cue("c2", "intro", 10000), _cue("c3", "intro", 35000)]
        bundles2 = trig_time_bundles({"cues": cues2, "playback": {"mode": "trig_time"}})
        assert bundles2[2].relative_ms == 25000  # 절대값이면 35000 이 나온다

    def test_preparation_cue_counts_in_the_delta_chain(self) -> None:
        """준비 cue 도 delta 계산에 포함된다 — 건너뛰면 뒤 큐가 전부 밀린다."""
        cues = [
            _cue("c1", "intro", 0),
            _cue("prep-dark-move", "intro", 3000),  # 준비 cue
            _cue("c3", "intro", 5000),
        ]
        bundles = trig_time_bundles({"cues": cues, "playback": {"mode": "trig_time"}})
        assert [b.relative_ms for b in bundles] == [0, 3000, 2000]
        assert sum(b.relative_ms for b in bundles) == 5000

    def test_manual_go_mode_marks_every_bundle_manual(self) -> None:
        """*"manual_go는 모든 cue의 수동 진행이고 at_ms는 음악 참조"*."""
        cues = [_cue("c1", "intro", 0), _cue("c2", "intro", 4000)]
        bundles = trig_time_bundles({"cues": cues, "playback": {"mode": "manual_go"}})
        assert all(b.trig == "manual_go" for b in bundles)
        assert all(b.relative_ms == 0 for b in bundles)

    def test_contract_example_delta_chain_sums_to_last_at_ms(self, plan: dict[str, Any]) -> None:
        bundles = trig_time_bundles(plan)
        assert plan["playback"]["mode"] == "trig_time"
        assert sum(b.relative_ms for b in bundles) == bundles[-1].at_ms


# ─────────────────────────────────────────────────────────────
# check_timing — 파이프라인 2단이 실제로 쓰는 진단 생산자
# ─────────────────────────────────────────────────────────────


class TestContractExamplePasses:
    """양성 대조. 규범 예제가 이 단계에서 막히면 우리가 정책을 주입한 것이다."""

    def test_no_blocking_diagnostic_on_the_normative_pair(
        self, plan: dict[str, Any], context: dict[str, Any]
    ) -> None:
        diagnostics = check_timing(plan, context)
        assert diagnostics, "진단 0개는 조용한 수용이다 — 계약 §6.3 위반"
        assert _blocking(diagnostics) == []
        assert all(d.stage == "time_reference" for d in diagnostics)

    def test_synthetic_beat_map_is_allowed_only_in_synthetic_environment(
        self, plan: dict[str, Any], context: dict[str, Any]
    ) -> None:
        """계약 §6.1: *"`synthetic`은 합성 harness에서만 허용한다"*.

        같은 beat_map 을 production 환경에 두면 막혀야 한다. 이 시험이 없으면
        synthetic 예외가 production 우회 통로가 된다.
        """
        assert context["environment"] == "synthetic"
        assert context["beat_map"]["status"] == "synthetic"
        assert _blocking(check_timing(plan, context)) == []

        production = deepcopy(context)
        production["environment"] = "production"
        blocked = _blocking(check_timing(plan, production))
        assert blocked, "production 에서 synthetic beat_map 이 통과했다"
        assert "LD-TIME-002" in _rules(blocked)


class TestSectionCoverage:
    """계약 LD-TIME-001: *"context sections는 전곡 [0,duration)를 겹침·공백 없이 분할"*."""

    def test_gap_between_sections_is_blocking(
        self, plan: dict[str, Any], context: dict[str, Any]
    ) -> None:
        broken = deepcopy(context)
        broken["music_sections"][1]["start_ms"] = 21000  # intro 는 20000 에서 끝난다 → 1초 공백
        blocked = _blocking(check_timing(plan, broken))
        assert "LD-TIME-001" in _rules(blocked)

    def test_overlap_between_sections_is_blocking(
        self, plan: dict[str, Any], context: dict[str, Any]
    ) -> None:
        broken = deepcopy(context)
        broken["music_sections"][1]["start_ms"] = 19000  # 1초 겹침
        assert "LD-TIME-001" in _rules(_blocking(check_timing(plan, broken)))

    def test_coverage_must_start_at_zero(
        self, plan: dict[str, Any], context: dict[str, Any]
    ) -> None:
        broken = deepcopy(context)
        broken["music_sections"][0]["start_ms"] = 500
        assert "LD-TIME-001" in _rules(_blocking(check_timing(plan, broken)))

    def test_coverage_must_reach_duration(
        self, plan: dict[str, Any], context: dict[str, Any]
    ) -> None:
        broken = deepcopy(context)
        broken["music_sections"][-1]["end_ms"] = 179000  # duration 은 180000
        assert "LD-TIME-001" in _rules(_blocking(check_timing(plan, broken)))


class TestCueBoundaries:
    """*"cue는 자기 section의 start<=at<end, 첫 cue=0"*."""

    def test_first_cue_must_be_zero(self, plan: dict[str, Any], context: dict[str, Any]) -> None:
        broken = deepcopy(plan)
        broken["cues"][0]["at_ms"] = 1
        blocked = _blocking(check_timing(broken, context))
        assert "LD-TIME-001" in _rules(blocked)
        assert any(d.pointer == "/cues/0/at_ms" for d in blocked)

    def test_cue_at_its_section_end_belongs_to_the_next_section(
        self, plan: dict[str, Any], context: dict[str, Any]
    ) -> None:
        """경계는 반열림이다 — intro 는 [0,20000) 이므로 20000 은 intro 가 아니다."""
        broken = deepcopy(plan)
        broken["cues"][1]["section_id"] = "intro"
        broken["cues"][1]["at_ms"] = 20000
        assert "LD-TIME-001" in _rules(_blocking(check_timing(broken, context)))

    def test_cue_before_its_section_start_is_blocking(
        self, plan: dict[str, Any], context: dict[str, Any]
    ) -> None:
        broken = deepcopy(plan)
        target = next(c for c in broken["cues"] if c["section_id"] == "chorus-a")
        target["at_ms"] = 49999  # chorus-a 는 50000 에서 시작
        assert "LD-TIME-001" in _rules(_blocking(check_timing(broken, context)))

    def test_fade_must_complete_within_duration(
        self, plan: dict[str, Any], context: dict[str, Any]
    ) -> None:
        """*"모든 delay/fade/settle는 duration 이내"*."""
        broken = deepcopy(plan)
        last = broken["cues"][-1]
        last["actions"][0]["timing"] = {
            "intensity": {"delay_ms": 0, "fade_ms": 999_000, "curve": "linear"}
        }
        assert "LD-TIME-001" in _rules(_blocking(check_timing(broken, context)))


class TestNegativeMsIsRefused:
    """감독 판정(2026-09-15) — 경로 분리. Director 경로는 음수를 거부한다."""

    def test_negative_at_ms_is_blocking_with_new_origin_guidance(
        self, plan: dict[str, Any], context: dict[str, Any]
    ) -> None:
        broken = deepcopy(plan)
        broken["cues"][1]["at_ms"] = -500
        blocked = _blocking(check_timing(broken, context))
        assert "LD-MIB-001" in _rules(blocked)
        offender = next(d for d in blocked if d.rule_id == "LD-MIB-001")
        assert offender.status == STATUS_UNSUPPORTED
        # 사람이 무엇을 해야 하는지가 사유에 있어야 한다 — 「금지」만으로는 행동을 못 한다.
        assert "원점" in offender.reason

    def test_negative_delay_is_blocking(
        self, plan: dict[str, Any], context: dict[str, Any]
    ) -> None:
        broken = deepcopy(plan)
        broken["cues"][0]["actions"][0]["timing"]["intensity"]["delay_ms"] = -1
        assert "LD-MIB-001" in _rules(_blocking(check_timing(broken, context)))

    def test_lxseq_preroll_path_is_untouched(self) -> None:
        """경로 분리의 나머지 절반 — 기존 시트 경로는 음수를 계속 지원한다.

        이 단언이 깨지면 「Director 만 거부」가 아니라 기능을 걷어낸 것이다.
        """
        from server.lxseq.cue_time import CUE_TIME_PREROLL, parse_cue_time

        assert parse_cue_time("-00:30.0").kind == CUE_TIME_PREROLL


class TestPlaybackModeRefusals:
    """*"timecode mode·숨은 offset·자동 GO는 거부한다"*."""

    @pytest.mark.parametrize("mode", ["timecode", "auto_go", "smpte"])
    def test_unknown_playback_mode_is_blocking(
        self, plan: dict[str, Any], context: dict[str, Any], mode: str
    ) -> None:
        broken = deepcopy(plan)
        broken["playback"]["mode"] = mode
        blocked = _blocking(check_timing(broken, context))
        assert "LD-TIME-003" in _rules(blocked)

    def test_origin_other_than_audio_start_is_blocking(
        self, plan: dict[str, Any], context: dict[str, Any]
    ) -> None:
        """숨은 offset 은 origin 을 바꿔 들어온다."""
        broken = deepcopy(plan)
        broken["playback"]["origin"] = "custom_offset"
        assert "LD-TIME-003" in _rules(_blocking(check_timing(broken, context)))


class TestRoundingConflictIsRefused:
    """*"rounding으로 충돌이 생기면 거부한다"*."""

    def test_two_distinct_beats_collapsing_to_one_ms_on_the_same_axis_conflicts(self) -> None:
        """서로 다른 authored beat 둘이 같은 ms 로 반올림되면 conflict 다.

        400 BPM 에서 1 박 = 150ms 이므로 0.001 박 차이는 0.15ms — 같은 ms 로 접힌다.
        """
        from server.director.validate.timing import rounding_conflicts

        beat_map = {
            "status": "confirmed",
            "segments": [
                {
                    "start_ms": 0,
                    "end_ms": 60000,
                    "start_beat": 0,
                    "bpm": 400,
                    "evidence_ref": "ev-a",
                }
            ],
        }
        requests = [
            ("group-front", "intensity", 4.000),
            ("group-front", "intensity", 4.001),
        ]
        conflicts = rounding_conflicts(beat_map, requests)
        assert conflicts, "다른 beat 둘이 같은 ms 로 접혔는데 통과했다"
        assert conflicts[0].status == STATUS_CONFLICT
        assert conflicts[0].blocking is True

    def test_same_ms_on_different_axes_is_not_a_conflict(self) -> None:
        """축이 다르면 같은 ms 여도 충돌이 아니다 — 여기서 넓게 잡으면 정상 계획이 막힌다."""
        from server.director.validate.timing import rounding_conflicts

        beat_map = {
            "status": "confirmed",
            "segments": [
                {
                    "start_ms": 0,
                    "end_ms": 60000,
                    "start_beat": 0,
                    "bpm": 400,
                    "evidence_ref": "ev-a",
                }
            ],
        }
        requests = [
            ("group-front", "intensity", 4.000),
            ("group-front", "color", 4.001),
        ]
        assert rounding_conflicts(beat_map, requests) == []


class TestFxCrossingTempoSegments:
    """*"FX 한 instance의 active 구간이 다른 bpm segment를 가로지르면 분할하거나 unsupported"*."""

    def _fx_plan(self, start_ms: int, stop_ms: int) -> dict[str, Any]:
        provenance = {
            "origin": "synthetic",
            "actor_ref": "author-fixture",
            "source_refs": ["src-fixture"],
            "evidence_refs": ["ev-music"],
            "rationale": "시험용 합성 입력이며 실제 관측을 주장하지 않는다.",
        }

        def fx(op: str, at_ms: int, cue_id: str) -> dict[str, Any]:
            action: dict[str, Any] = {
                "op": op,
                "action_id": f"{cue_id}-fx",
                "group_id": "group-front",
                "provenance": provenance,
                "instance_id": "fx-inst-1",
                "timing": {"fx": {"delay_ms": 0, "fade_ms": 0, "curve": "linear"}},
            }
            if op == "fx_start":
                action["preset_ref"] = "preset-fx"
                action["cycle_beats"] = 4
                action["phase_beats"] = 0
            return {
                "cue_id": cue_id,
                "section_id": "intro",
                "at_ms": at_ms,
                "label": f"시험 큐 {cue_id}",
                "provenance": provenance,
                "actions": [action],
            }

        return {
            "playback": {"mode": "trig_time", "origin": "audio_start"},
            "cues": [
                _cue("c-baseline", "intro", 0),
                fx("fx_start", start_ms, "c-fx-start"),
                fx("fx_stop", stop_ms, "c-fx-stop"),
            ],
        }

    def _one_section_context(self) -> dict[str, Any]:
        return {
            "environment": "synthetic",
            "audio": {"duration_ms": 120000},
            "music_sections": [
                {"section_id": "intro", "start_ms": 0, "end_ms": 120000, "role": "intro"}
            ],
            "beat_map": _TWO_SEGMENTS,
        }

    def test_instance_spanning_a_bpm_boundary_is_blocking(self) -> None:
        # segment 경계는 60000. 50000~70000 은 가로지른다.
        diagnostics = check_timing(self._fx_plan(50000, 70000), self._one_section_context())
        blocked = _blocking(diagnostics)
        assert "LD-TIME-002" in _rules(blocked)

    def test_instance_inside_one_segment_is_accepted(self) -> None:
        diagnostics = check_timing(self._fx_plan(10000, 50000), self._one_section_context())
        assert _blocking(diagnostics) == [], "한 segment 안에 있는 FX 가 막혔다"
        assert any(d.rule_id == "LD-TIME-002" and d.status == STATUS_ACCEPTED for d in diagnostics)

    def test_instance_ending_exactly_at_the_boundary_is_accepted(self) -> None:
        """구간은 `[start,end)` 이므로 60000 에 끝나는 것은 가로지르지 않는다."""
        diagnostics = check_timing(self._fx_plan(10000, 60000), self._one_section_context())
        assert _blocking(diagnostics) == []


class TestFxTempoCoverage:
    """`LD-TIME-002` — tempo 지도가 FX 구간을 안 덮으면 막는다.

    자기 검토에서 찾은 구멍이다. `beat_at` 은 tempo 불명에 예외를 던지지만 **아무도 큐
    시각으로 그것을 부르지 않았기 때문에** 지도가 곡 뒷부분을 안 덮어도 조용히 통과했다.
    실측: 규범 예제의 tempo 지도를 90초로 줄여도 blocking 이 0 이었다.
    """

    def test_fx_beyond_the_tempo_map_is_blocking(
        self, plan: dict[str, Any], context: dict[str, Any]
    ) -> None:
        shortened = deepcopy(context)
        shortened["beat_map"]["segments"][0]["end_ms"] = 90000  # 곡은 180000
        blocked = _blocking(check_timing(plan, shortened))
        assert blocked, "tempo 지도가 곡 뒷부분을 안 덮는데 통과했다"
        assert "LD-TIME-002" in _rules(blocked)
        assert any("tempo segment 가 없습니다" in d.reason for d in blocked)

    def test_full_coverage_stays_accepted(
        self, plan: dict[str, Any], context: dict[str, Any]
    ) -> None:
        """음성 대조 — 지도가 전곡을 덮는 원본은 막히지 않아야 한다."""
        assert _blocking(check_timing(plan, context)) == []

    def test_static_plan_without_fx_needs_no_tempo_map(
        self, plan: dict[str, Any], context: dict[str, Any]
    ) -> None:
        """범위 한정의 반대편 — 박 계산이 필요 없는 계획을 tempo 부재로 막지 않는다.

        일반 cue 의 `at_ms` 는 절대 시각이다. 여기까지 막으면 tempo 지도 없이도 유효한
        정적 계획이 통째로 막힌다.
        """
        static_plan = deepcopy(plan)
        static_plan["cues"] = [
            cue
            for cue in static_plan["cues"]
            if not any("instance_id" in action for action in cue["actions"])
        ]
        no_tempo = deepcopy(context)
        no_tempo["beat_map"] = {"status": "absent", "segments": []}
        blocked = _blocking(check_timing(static_plan, no_tempo))
        assert "LD-TIME-002" not in _rules(blocked)

    def test_gap_between_two_segments_inside_an_fx_span_is_blocking(self) -> None:
        """붙어 있지 않은 segment 둘 사이의 공백도 미덮임이다."""
        gapped = {
            "status": "confirmed",
            "segments": [
                {
                    "start_ms": 0,
                    "end_ms": 20000,
                    "start_beat": 0,
                    "bpm": 120,
                    "evidence_ref": "ev-a",
                },
                {
                    "start_ms": 40000,
                    "end_ms": 120000,
                    "start_beat": 40,
                    "bpm": 120,
                    "evidence_ref": "ev-b",
                },
            ],
        }
        crossing = TestFxCrossingTempoSegments()
        context = crossing._one_section_context()
        context["beat_map"] = gapped
        blocked = _blocking(check_timing(crossing._fx_plan(10000, 50000), context))
        assert "LD-TIME-002" in _rules(blocked)


class TestDiagnosticCoverage:
    """계약 §6.3 — 조용한 수용은 이 층의 합법적인 답이 아니다."""

    def test_every_diagnostic_carries_a_reason(
        self, plan: dict[str, Any], context: dict[str, Any]
    ) -> None:
        for diagnostic in check_timing(plan, context):
            assert diagnostic.reason.strip()

    def test_accepted_diagnostic_leaves_before_and_after_absent(
        self, plan: dict[str, Any], context: dict[str, Any]
    ) -> None:
        """*"단순 수용은 before/after 둘 다 present=false 로 하고 사유를 밝힌다"*."""
        for diagnostic in check_timing(plan, context):
            if diagnostic.status != STATUS_ACCEPTED:
                continue
            wire = diagnostic.to_wire("diagnostic-0001")
            assert wire["before"] == {"present": False}
            assert wire["after"] == {"present": False}

    def test_pointers_are_rooted_at_the_submitted_plan(
        self, plan: dict[str, Any], context: dict[str, Any]
    ) -> None:
        for diagnostic in check_timing(plan, context):
            assert diagnostic.pointer == "" or diagnostic.pointer.startswith("/")


class TestWiredIntoThePipeline:
    """부품이 초록인 것과 경로가 이어진 것은 다르다 — 2단이 실제로 `timing.py` 를 부르는가."""

    def test_stage_two_emits_timing_diagnostics_when_context_is_given(
        self, plan: dict[str, Any], context: dict[str, Any]
    ) -> None:
        from server.director.validate.pipeline import run_stages

        core = run_stages(plan, context)
        stage_two = [d for d in core.diagnostics if d["stage"] == "time_reference"]
        assert stage_two, "2단 진단이 없다"
        # C1 자리표시자는 LD-TIME-001 하나뿐이었다. 실제 검사기는 003 까지 낸다.
        assert {d["rule_id"] for d in stage_two} >= {"LD-TIME-001", "LD-TIME-002", "LD-TIME-003"}

    def test_a_timing_defect_reaches_the_pipeline_verdict(
        self, plan: dict[str, Any], context: dict[str, Any]
    ) -> None:
        """날조 대조군 — 2단만의 결함이 파이프라인 진단에 실제로 나타나는가.

        전체 outcome 은 capability 단계가 무조건 blocking 이라 어차피 `blocked` 다. 그래서
        outcome 으로는 배선을 확인할 수 없고, **2단 진단 자체**를 봐야 한다.
        """
        broken = deepcopy(plan)
        broken["cues"][0]["at_ms"] = 7  # 첫 cue = 0 위반
        from server.director.validate.pipeline import run_stages

        stage_two = [
            d for d in run_stages(broken, context).diagnostics if d["stage"] == "time_reference"
        ]
        assert any(d["blocking"] and d["pointer"] == "/cues/0/at_ms" for d in stage_two)

    def test_missing_context_blocks_instead_of_silently_accepting(
        self, plan: dict[str, Any]
    ) -> None:
        """seam 은 계획만 넘긴다. 판정 불능을 수용으로 바꾸면 시간 검사가 조용히 사라진다."""
        from server.director.validate.pipeline import run_stages

        stage_two = [d for d in run_stages(plan).diagnostics if d["stage"] == "time_reference"]
        assert stage_two
        assert all(d["blocking"] for d in stage_two)

    def test_validator_carries_the_injected_context(
        self, plan: dict[str, Any], context: dict[str, Any]
    ) -> None:
        from server.director.validate.pipeline import PipelineValidator

        without = PipelineValidator().validate(plan)
        with_context = PipelineValidator(context).validate(plan)
        # 둘 다 blocked 다(capability 때문). 다른 것은 2단 진단의 내용이다.
        #
        # 개수 비교가 아니라 내용 비교다 — C6 round 5(pan==tilt Position timing 관측,
        # `server/director/validate/capability.py::AXIS_TIMING_OBSERVED`) 이후 규범
        # 예제의 두 position_set(pan==tilt==0) 이 with_context 쪽에서 진단을 하나씩
        # 덜 받아 우연히 개수가 같아질 수 있다 — 개수가 아니라 내용이 달라야 한다.
        assert without["outcome"] == with_context["outcome"] == "blocked"
        assert with_context["diagnostics"] != without["diagnostics"]


class TestNoConsoleAndNoArtisticImport:
    """이 모듈은 OSC 도 예술 producer 도 만지지 않는다 (주석이 아니라 실제 import 를 본다)."""

    def test_timing_module_imports_no_forbidden_package(self) -> None:
        source = Path("server/director/validate/timing.py").read_text(encoding="utf-8")
        for forbidden in ("server.bridge", "server.looks", "server.web"):
            assert forbidden not in source, f"{forbidden} 를 import 했다"
