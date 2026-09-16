"""`server.director.emit` — frozen artifact 와 manifest 를 내는 층의 시험.

이 시험이 지키는 것은 셋이다.

1. **계약 형태**(`SPEC-LDPLUGIN-001/contract.md:145`) — bundle 순서·`cue_number`·
   `trigger.relative_ms` 사슬. 「돌았다」만 보면 순서가 뒤바뀐 구현도 초록이므로
   순서와 개수를 **단언**한다.
2. **축별 timing 은 거부된다.** 실측된 문법은 큐 단위 스칼라 `CueFade` 하나뿐이고
   축별 통로는 관측 0건이다. 조용히 clamp·drop·대체하면 `AC-LDPLUGIN-008` 위반이다.
   거부는 **사유 문자열까지** 단언한다 — 거짓 사유로 먼저 거절하면 참 사유가 안 보인다.
3. **문법이 두 벌로 갈라지지 않는다.** 생산 모듈은 `server.design.cue_fade` 를
   import 하지 않는다(`plan.md §3` 이 그 경로를 읽기 전용으로 정했다). 대신 이 시험이
   두 자리가 **같은 문면**을 내는지 대조한다.
"""

from __future__ import annotations

import hashlib
from typing import Any

import pytest

from server.director.emit import (
    AxisTimingUnsupportedError,
    emit_compiled,
)

TARGET = {"console_id": "console-1", "session_id": "session-1", "destination": "seq-9001"}

DIGESTS: dict[str, Any] = {
    "compiler_id": "ld-emit",
    "compiler_version": "0.1.0",
    "compiler_build_digest": "sha256:build",
    "plan_digest": "sha256:plan",
    "context_digest": "sha256:ctx",
}


def _cue(cue_id: str, at_ms: int, *, fade_s: float | None = None, timing: dict | None = None):
    action: dict[str, Any] = {
        "action_id": f"{cue_id}-a0",
        "op": "intensity_set",
        "group_id": "group-front",
        "value_pct": 50,
    }
    if timing is not None:
        action["timing"] = timing
    cue: dict[str, Any] = {"cue_id": cue_id, "at_ms": at_ms, "actions": [action]}
    if fade_s is not None:
        cue["fade_s"] = fade_s
    return cue


def _plan(*cues: dict[str, Any], playback: str = "manual_go") -> dict[str, Any]:
    return {"plan_id": "plan-emit", "playback": playback, "cues": list(cues)}


# ── 계기 검정: 날조 대조군을 먼저 쏜다 ───────────────────────────────────────
# 재려는 불변식만 위반한다. 포맷·린트를 함께 깨면 게이트가 무엇을 잡았는지
# 모호해진다.


def test_control_a_reordered_expectation_fails() -> None:
    """`cue_number` 를 일부러 틀린 순서로 기대하면 이 시험 장치가 **실패한다**.

    이것이 없으면 뒤의 순서 단언이 초록이어도 그 초록이 무엇을 뜻하는지 모른다.
    """
    compiled, _ = emit_compiled(_plan(_cue("c0", 0), _cue("c1", 1000)), target=TARGET, **DIGESTS)
    numbers = [b["cue_number"] for b in compiled["manifest"]["bundles"]]
    assert numbers == [1, 2]
    with pytest.raises(AssertionError):
        assert numbers == [2, 1]


def test_control_b_a_per_axis_plan_is_not_silently_accepted() -> None:
    """축별 timing 을 담은 plan 이 **통과하지 않는다**(음성 대조)."""
    with pytest.raises(AxisTimingUnsupportedError):
        emit_compiled(
            _plan(_cue("c0", 0, timing={"intensity": {"fade_ms": 500}})),
            target=TARGET,
            **DIGESTS,
        )


# ── 계약 형태 ────────────────────────────────────────────────────────────────


class TestManifestShape:
    def test_manifest_carries_exactly_the_contract_keys(self) -> None:
        compiled, _ = emit_compiled(_plan(_cue("c0", 0)), target=TARGET, **DIGESTS)
        assert compiled["available"] is True
        assert set(compiled["manifest"]) == {
            "compiler_id",
            "compiler_version",
            "compiler_build_digest",
            "plan_digest",
            "context_digest",
            "target",
            "playback",
            "bundles",
        }

    def test_compiled_digest_is_not_invented_here(self) -> None:
        """`compiled_digest` 는 이 층이 만들지 않는다.

        manifest 전체를 정규화해 해시해야 하고, JCS 정규화를 표준 라이브러리로
        근사하면 깨진다 — 지어내는 대신 호출자(`SPEC-LDSTORE-001`)에 남긴다.
        """
        compiled, _ = emit_compiled(_plan(_cue("c0", 0)), target=TARGET, **DIGESTS)
        assert "compiled_digest" not in compiled

    def test_bundle_carries_exactly_the_contract_keys(self) -> None:
        compiled, _ = emit_compiled(_plan(_cue("c0", 0)), target=TARGET, **DIGESTS)
        assert set(compiled["manifest"]["bundles"][0]) == {
            "bundle_id",
            "cue_id",
            "action_ids",
            "at_ms",
            "cue_number",
            "trigger",
            "artifact_resource_id",
            "artifact_sha256",
        }

    def test_target_and_playback_are_passed_through_unchanged(self) -> None:
        compiled, _ = emit_compiled(
            _plan(_cue("c0", 0), playback="trig_time"), target=TARGET, **DIGESTS
        )
        assert compiled["manifest"]["target"] == TARGET
        assert compiled["manifest"]["playback"] == "trig_time"


class TestCueNumbering:
    def test_cue_number_is_one_to_n_in_final_order(self) -> None:
        compiled, _ = emit_compiled(
            _plan(_cue("c0", 0), _cue("c1", 1000), _cue("c2", 2500)),
            target=TARGET,
            **DIGESTS,
        )
        bundles = compiled["manifest"]["bundles"]
        assert [b["cue_number"] for b in bundles] == [1, 2, 3]
        assert [b["cue_id"] for b in bundles] == ["c0", "c1", "c2"]

    def test_a_preparation_cue_takes_a_number_like_any_other(self) -> None:
        """준비 cue 도 최종 순서에 든다 (계약: *"준비 cue 도 최종 순서와 delta 계산에 포함"*)."""
        prep = _cue("c-prep", 500)
        prep["preparation"] = True
        compiled, _ = emit_compiled(
            _plan(_cue("c0", 0), prep, _cue("c1", 1000)), target=TARGET, **DIGESTS
        )
        bundles = compiled["manifest"]["bundles"]
        assert [b["cue_id"] for b in bundles] == ["c0", "c-prep", "c1"]
        assert [b["cue_number"] for b in bundles] == [1, 2, 3]


class TestTriggerChain:
    def test_manual_go_gives_every_bundle_relative_zero(self) -> None:
        compiled, _ = emit_compiled(
            _plan(_cue("c0", 0), _cue("c1", 1000), _cue("c2", 4000), playback="manual_go"),
            target=TARGET,
            **DIGESTS,
        )
        triggers = [b["trigger"] for b in compiled["manifest"]["bundles"]]
        assert all(t == {"type": "manual_go", "relative_ms": 0} for t in triggers)

    def test_trig_time_first_is_manual_then_deltas(self) -> None:
        compiled, _ = emit_compiled(
            _plan(_cue("c0", 0), _cue("c1", 1000), _cue("c2", 4000), playback="trig_time"),
            target=TARGET,
            **DIGESTS,
        )
        triggers = [b["trigger"] for b in compiled["manifest"]["bundles"]]
        assert triggers[0] == {"type": "manual_go", "relative_ms": 0}
        assert triggers[1] == {"type": "time", "relative_ms": 1000}
        assert triggers[2] == {"type": "time", "relative_ms": 3000}

    def test_identical_at_ms_gives_delta_zero_not_a_refusal(self) -> None:
        """같은 ms 는 경계 사례이고 거부 사유가 아니다 — delta 가 0 이다."""
        compiled, _ = emit_compiled(
            _plan(_cue("c0", 0), _cue("c1", 1000), _cue("c2", 1000), playback="trig_time"),
            target=TARGET,
            **DIGESTS,
        )
        assert compiled["manifest"]["bundles"][2]["trigger"] == {
            "type": "time",
            "relative_ms": 0,
        }

    def test_an_unsupported_playback_mode_is_refused(self) -> None:
        with pytest.raises(ValueError) as caught:
            emit_compiled(_plan(_cue("c0", 0), playback="timecode"), target=TARGET, **DIGESTS)
        assert "timecode" in str(caught.value)


class TestFrozenArtifactBytes:
    def test_sha256_hashes_the_bytes_actually_returned(self) -> None:
        """`artifact_sha256` 은 **이 층이 실제로 낸 bytes** 를 해시한다 (계약 §209)."""
        compiled, artifacts = emit_compiled(
            _plan(_cue("c0", 0), _cue("c1", 1000)), target=TARGET, **DIGESTS
        )
        for bundle in compiled["manifest"]["bundles"]:
            payload = artifacts[bundle["artifact_resource_id"]]
            assert isinstance(payload, bytes)
            assert bundle["artifact_sha256"] == hashlib.sha256(payload).hexdigest()

    def test_artifact_bytes_are_stable_across_two_runs(self) -> None:
        """같은 입력이 같은 bytes 를 낸다 — 재현 가능해야 digest 가 뜻을 갖는다."""
        first, first_bytes = emit_compiled(_plan(_cue("c0", 0)), target=TARGET, **DIGESTS)
        second, second_bytes = emit_compiled(_plan(_cue("c0", 0)), target=TARGET, **DIGESTS)
        assert first == second
        assert first_bytes == second_bytes


class TestMeasuredFadeSyntaxOnly:
    def test_cue_fade_uses_the_measured_literal_form(self) -> None:
        """`CueFade 2` 형태다 — `:g` 라서 `2.0` 이 아니라 `2` 로 나간다."""
        _, artifacts = emit_compiled(_plan(_cue("c0", 0, fade_s=2.0)), target=TARGET, **DIGESTS)
        payload = next(iter(artifacts.values())).decode("utf-8")
        assert "CueFade 2" in payload
        assert "CueFade 2.0" not in payload

    def test_absent_fade_emits_no_fade_token_at_all(self) -> None:
        """페이드가 없는 입력은 `CueFade` 를 아예 붙이지 않는다 (항등 갈래)."""
        _, artifacts = emit_compiled(_plan(_cue("c0", 0)), target=TARGET, **DIGESTS)
        assert "CueFade" not in next(iter(artifacts.values())).decode("utf-8")

    def test_property_fade_never_appears(self) -> None:
        """`Property 'Fade'` 는 금지다 — 실측 근거는 handoff 문서 19행."""
        _, artifacts = emit_compiled(_plan(_cue("c0", 0, fade_s=1.5)), target=TARGET, **DIGESTS)
        assert "Property" not in next(iter(artifacts.values())).decode("utf-8")

    @pytest.mark.parametrize(
        "timing",
        [
            {"intensity": {"fade_ms": 500}},
            {"pan": {"delay_ms": 200}},
            {"color": {"fade_ms": 0}},
        ],
    )
    def test_per_axis_timing_is_refused_with_the_observation_reason(
        self, timing: dict[str, Any]
    ) -> None:
        """거부 **사유**를 단언한다. 다른 이유로 거절돼도 통과해버리면 참 사유가 안 보인다."""
        with pytest.raises(AxisTimingUnsupportedError) as caught:
            emit_compiled(_plan(_cue("c0", 0, timing=timing)), target=TARGET, **DIGESTS)
        reason = str(caught.value)
        assert "관측" in reason
        assert next(iter(timing)) in reason

    def test_refusal_names_every_requested_axis_not_just_the_first(self) -> None:
        with pytest.raises(AxisTimingUnsupportedError) as caught:
            emit_compiled(
                _plan(_cue("c0", 0, timing={"pan": {"fade_ms": 1}, "tilt": {"fade_ms": 2}})),
                target=TARGET,
                **DIGESTS,
            )
        reason = str(caught.value)
        assert "pan" in reason
        assert "tilt" in reason


class TestNoDivergentCopyOfTheSyntax:
    def test_emit_module_does_not_import_the_design_helper(self) -> None:
        """생산 모듈은 `server.design.cue_fade` 를 들여오지 않는다 (`plan.md §3`)."""
        from pathlib import Path

        import server.director.emit as emit_module

        source = Path(emit_module.__file__).read_text(encoding="utf-8")
        assert "server.design" not in source

    def test_the_two_sites_produce_the_same_literal_text(self) -> None:
        """두 벌이 갈라지지 않는지 **대조**한다 — 이것이 복사를 허용한 대가다.

        import 하지 않는 대신 이 시험이 갈라짐을 잡는다. 한쪽만 바뀌면 여기서 깨진다.
        """
        from server.design.cue_fade import store_with_fade
        from server.director.emit import store_with_measured_fade

        store = "Store Sequence 9001 Cue 1 'c0'"
        for fade in (None, 0, 0.2, 2.0, 12.0):
            assert store_with_measured_fade(store, fade) == store_with_fade(store, fade)
