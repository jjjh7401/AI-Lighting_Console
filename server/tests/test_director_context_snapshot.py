"""ContextSnapshot 과 binding 무효화 (SPEC-LDSTORE-001 M2 · AC-LDPLUGIN-004).

이 파일이 고정하는 것은 세 가지다 — 어느 하나가 빠지면 안전 장치에 구멍이 난다.

1. **아홉 축이 전부 snapshot 에 있다.** audio · show · group membership · preset 내용 ·
   compiler · capability · 정책 · identity · 만료 (`REQ-LDPLUGIN-004`).
2. **digest 가 아홉 축 전부를 덮는다.** 한 축이라도 digest 밖에 있으면 그 축이 바뀌어도
   이전 승인이 유효하게 남는다 — preset 내용이 바뀐 리그에 옛 승인이 적용될 수 있다.
3. **못 읽은 값은 승격되지 않는다.** `unreadable` 을 `observed` 로, `absent` 를
   `confirmed` 로 올리면 FAIL 이다.

**계기 주의 둘** (프로젝트 실측 기록):

- 키가 없는 것과 값이 ``None`` 인 것은 다르다. ``.get()`` 은 둘을 같은 ``None`` 으로
  답하므로 이 파일은 키 유무를 ``in`` 으로만 단언한다.
- ``COUNT 0`` 은 부재의 증거가 아니다. 내용이 있는 Group 이 0 을 답한 실측 사례가 있다
  (우산 `research.md`). 그래서 fixture 0개 판독은 "빈 그룹 확인" 이 아니라 판독 실패다.

**양성 대조가 이 파일의 뼈대다.** 전부 거절하거나 아무 값이나 내는 조립기는 "digest 가
움직인다" 류의 시험을 그냥 통과한다. 그래서 계약 §11 의 예제(`examples/context.json`,
digest 실측 일치 확인)를 재조립해 **바이트 동일**한지를 같은 회차에서 확인한다.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from server.director import context as ctx
from server.director.digest import context_digest
from server.director.models import parse_exchange

_EXAMPLE_PATH = (
    Path(__file__).resolve().parents[2]
    / ".moai"
    / "specs"
    / "SPEC-LDPLUGIN-001"
    / "examples"
    / "context.json"
)

#: 계약 §6.2 — plan 의 bindings 일곱. 전부 current snapshot 과 일치해야 한다.
_BINDING_FIELDS: tuple[str, ...] = (
    "context_id",
    "context_digest",
    "audio_sha256",
    "music_revision",
    "rig_revision",
    "capability_revision",
    "safety_policy_revision",
)


def _example() -> dict[str, Any]:
    return json.loads(_EXAMPLE_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def example() -> dict[str, Any]:
    return _example()


@pytest.fixture
def observations(example: dict[str, Any]) -> ctx.ContextObservations:
    return ctx.ContextObservations.from_snapshot(example)


# ---------------------------------------------------------------------------
# 양성 대조 — 예제를 재조립해 바이트 동일해야 한다
# ---------------------------------------------------------------------------


def test_rebuilds_the_contract_example_byte_identically(
    example: dict[str, Any], observations: ctx.ContextObservations
) -> None:
    """계약 §11 예제를 관측으로 분해해 다시 조립하면 같은 객체가 나온다.

    이것이 없으면 아래 시험 전부가 공허하다 — 아무 dict 나 내는 조립기도
    "축이 바뀌면 digest 가 바뀐다" 를 만족시킨다.
    """
    rebuilt = ctx.build_snapshot(observations)

    assert rebuilt == example
    assert rebuilt["context_digest"] == example["context_digest"]


def test_built_snapshot_passes_the_contract_schema(
    observations: ctx.ContextObservations, example: dict[str, Any]
) -> None:
    """조립 결과가 계약 스키마의 closed-world 검사를 통과한다."""
    snapshot = ctx.build_snapshot(observations)

    parsed = parse_exchange(
        json.dumps(snapshot).encode("utf-8"), environment=example["environment"]
    )
    assert parsed["message_type"] == "context_snapshot"


# ---------------------------------------------------------------------------
# 1. 아홉 축의 존재
# ---------------------------------------------------------------------------


def test_exactly_nine_axes_are_named() -> None:
    assert len(ctx.NINE_AXES) == 9, sorted(ctx.NINE_AXES)
    assert set(ctx.NINE_AXES) == {
        "audio",
        "show",
        "group_membership",
        "preset_content",
        "compiler",
        "capability",
        "policy",
        "identity",
        "expiry",
    }


@pytest.mark.parametrize("axis", sorted(ctx.NINE_AXES))
def test_every_axis_key_is_present(axis: str, observations: ctx.ContextObservations) -> None:
    """축이 소유한 키가 실제로 snapshot 에 있다.

    ``in`` 으로 단언한다 — ``.get()`` 은 "키 없음" 과 "값이 None" 을 같은 답으로
    뭉개므로 키 존재를 잴 계기가 못 된다.
    """
    snapshot = ctx.build_snapshot(observations)

    for key in ctx.NINE_AXES[axis]:
        assert key in snapshot, f"{axis} 축의 {key!r} 가 snapshot 에 없습니다"


def test_no_top_level_key_escapes_axis_ownership(observations: ctx.ContextObservations) -> None:
    """모든 최상위 키가 아홉 축 또는 명시된 예외 목록 중 하나에 속한다.

    이 시험이 없으면 새 필드가 조용히 어느 축에도 속하지 않은 채 들어와, 그 필드만
    바뀌었을 때 "어느 축이 바뀌었나" 를 답할 수 없게 된다.
    """
    snapshot = ctx.build_snapshot(observations)

    owned = {key for keys in ctx.NINE_AXES.values() for key in keys}
    allowed = owned | set(ctx.ENVELOPE_KEYS) | set(ctx.CROSS_AXIS_KEYS)

    assert set(snapshot) - allowed == set()


def test_missing_axes_reports_a_removed_axis(observations: ctx.ContextObservations) -> None:
    """축을 빼면 그 축의 이름이 보고된다 (음성 대조 포함)."""
    snapshot = ctx.build_snapshot(observations)
    assert ctx.missing_axes(snapshot) == ()

    stripped = {key: value for key, value in snapshot.items() if key != "compiler"}
    assert ctx.missing_axes(stripped) == ("compiler",)


# ---------------------------------------------------------------------------
# 2. digest 가 아홉 축 전부를 덮는다
# ---------------------------------------------------------------------------


def _mutate_audio(obs: ctx.ContextObservations) -> ctx.ContextObservations:
    audio = dict(obs.audio)
    audio["duration_ms"] = audio["duration_ms"] + 1000
    return obs.replace(audio=audio)


def _mutate_show(obs: ctx.ContextObservations) -> ctx.ContextObservations:
    return obs.replace(show_revision=obs.show_revision + 1)


def _mutate_group_membership(obs: ctx.ContextObservations) -> ctx.ContextObservations:
    groups = copy.deepcopy(obs.groups)
    groups[0]["fixture_ids"] = groups[0]["fixture_ids"][:-1]
    return obs.replace(groups=groups)


def _mutate_preset_content(obs: ctx.ContextObservations) -> ctx.ContextObservations:
    presets = copy.deepcopy(obs.presets)
    presets[0]["content_revision"] = presets[0]["content_revision"] + 1
    presets[0]["content_digest"] = "sha256:" + "0" * 64
    return obs.replace(presets=presets)


def _mutate_compiler(obs: ctx.ContextObservations) -> ctx.ContextObservations:
    compiler = dict(obs.compiler)
    compiler["build_digest"] = "sha256:" + "1" * 64
    return obs.replace(compiler=compiler)


def _mutate_capability(obs: ctx.ContextObservations) -> ctx.ContextObservations:
    capabilities = copy.deepcopy(obs.capabilities)
    capabilities[0]["random_access"] = not capabilities[0]["random_access"]
    return obs.replace(capabilities=capabilities)


def _mutate_policy(obs: ctx.ContextObservations) -> ctx.ContextObservations:
    safety = dict(obs.safety)
    safety["max_intensity_pct"] = 80
    return obs.replace(safety=safety)


def _mutate_identity(obs: ctx.ContextObservations) -> ctx.ContextObservations:
    target = copy.deepcopy(obs.target)
    target["session_id"] = "session-reconnected"
    return obs.replace(target=target)


def _mutate_expiry(obs: ctx.ContextObservations) -> ctx.ContextObservations:
    return obs.replace(expires_at="2026-09-13T12:00:00Z")


#: 축 이름 → 그 축만 건드리는 변형. 아홉 축 전부에 하나씩 있어야 한다.
_AXIS_MUTATIONS: dict[str, Callable[[ctx.ContextObservations], ctx.ContextObservations]] = {
    "audio": _mutate_audio,
    "show": _mutate_show,
    "group_membership": _mutate_group_membership,
    "preset_content": _mutate_preset_content,
    "compiler": _mutate_compiler,
    "capability": _mutate_capability,
    "policy": _mutate_policy,
    "identity": _mutate_identity,
    "expiry": _mutate_expiry,
}


def test_every_axis_has_a_mutation_case() -> None:
    """변형 표가 아홉 축을 빠짐없이 덮는다 — 표가 새면 그 축은 시험되지 않는다."""
    assert set(_AXIS_MUTATIONS) == set(ctx.NINE_AXES)


@pytest.mark.parametrize("axis", sorted(_AXIS_MUTATIONS))
def test_axis_change_moves_the_digest(axis: str, observations: ctx.ContextObservations) -> None:
    """아홉 축 어느 것이 바뀌어도 context_digest 가 움직인다."""
    before = ctx.build_snapshot(observations)
    after = ctx.build_snapshot(_AXIS_MUTATIONS[axis](observations))

    assert after["context_digest"] != before["context_digest"], f"{axis} 축이 digest 밖입니다"
    assert after["context_digest"] == context_digest(after)


def test_identical_observations_give_the_same_digest(
    observations: ctx.ContextObservations,
) -> None:
    """음성 대조 — 아무것도 바꾸지 않으면 digest 도 그대로다."""
    assert ctx.build_snapshot(observations) == ctx.build_snapshot(observations)


# ---------------------------------------------------------------------------
# 2-b. 관측 시각 자체는 source 변경이 아니다 (계약 §6.1)
# ---------------------------------------------------------------------------


def test_clock_alone_does_not_reissue(observations: ctx.ContextObservations) -> None:
    """계약 §6.1: *"매 GET마다 created_at만 바꾸어 pending plan을 stale로 만들지 않는다."*

    관측 시각이 흘렀을 뿐이면 같은 snapshot 을 그대로 돌려주어야 한다.
    """
    snapshot = ctx.build_snapshot(observations)
    later = observations.replace(created_at="2026-09-13T10:30:00Z")

    assert ctx.should_reissue(snapshot, later) is False


@pytest.mark.parametrize("axis", sorted(_AXIS_MUTATIONS))
def test_axis_change_reissues(axis: str, observations: ctx.ContextObservations) -> None:
    snapshot = ctx.build_snapshot(observations)

    assert ctx.should_reissue(snapshot, _AXIS_MUTATIONS[axis](observations)) is True


# ---------------------------------------------------------------------------
# 3. 못 읽은 값은 승격되지 않는다
# ---------------------------------------------------------------------------


def test_unreadable_identity_stays_unreadable() -> None:
    """콘솔 identity 를 못 읽으면 ``unreadable`` 이다 — ``observed`` 로 올리지 않는다."""
    assert (
        ctx.resolve_identity_status(observed_console_id=None, evidence_refs=("ev-rig",))
        == "unreadable"
    )


def test_identity_without_evidence_is_not_observed() -> None:
    """근거가 없으면 판독했다고 말할 수 없다 — 값이 있어도 ``observed`` 가 아니다."""
    assert (
        ctx.resolve_identity_status(observed_console_id="console-1", evidence_refs=())
        == "unreadable"
    )


def test_observed_identity_needs_both_value_and_evidence() -> None:
    """양성 대조 — 값과 근거가 함께 있을 때만 ``observed`` 다."""
    assert (
        ctx.resolve_identity_status(observed_console_id="console-1", evidence_refs=("ev-rig",))
        == "observed"
    )


def test_zero_count_fixture_read_is_not_an_empty_group() -> None:
    """``COUNT 0`` 은 부재의 증거가 아니다 — 판독 실패로 다룬다.

    내용이 있는 Group 이 0 을 답한 실측 사례가 있다 (우산 `research.md`). 0 을
    "빈 그룹 확인" 으로 기록하면 그 그룹의 fixture 가 조명 계획에서 조용히 사라진다.
    """
    with pytest.raises(ctx.ContextBuildError) as caught:
        ctx.resolve_group_fixtures(read_fixture_ids=[])

    assert "COUNT 0" in str(caught.value)


def test_unread_fixture_list_is_not_an_empty_group() -> None:
    with pytest.raises(ctx.ContextBuildError):
        ctx.resolve_group_fixtures(read_fixture_ids=None)


def test_read_fixture_list_passes_through() -> None:
    """양성 대조 — 실제로 판독된 목록은 그대로 통과한다."""
    assert ctx.resolve_group_fixtures(read_fixture_ids=["fixture-1", "fixture-2"]) == (
        "fixture-1",
        "fixture-2",
    )


def test_preset_without_export_or_attestation_is_unreadable() -> None:
    """계약 §6.1: unreadable 이고 attestation 도 없으면 ready 를 막는다."""
    status, digest = ctx.resolve_preset_content(export_bytes=None, attestation_bytes=None)

    assert status == "unreadable"
    assert digest is None


def test_attested_preset_is_not_observed() -> None:
    """attestation 은 측정 검증이 아니다 — digest 는 묶지만 status 는 ``attested`` 다."""
    status, digest = ctx.resolve_preset_content(
        export_bytes=None, attestation_bytes=b"operator says amber, full range"
    )

    assert status == "attested"
    assert digest is not None and digest.startswith("sha256:")


def test_observed_preset_hashes_the_export_bytes() -> None:
    """양성 대조 — 실제 frozen export bytes 가 있으면 ``observed`` 다."""
    status, digest = ctx.resolve_preset_content(
        export_bytes=b"frozen export", attestation_bytes=None
    )

    assert status == "observed"
    assert digest == ctx.raw_content_digest(b"frozen export")


def test_absent_beat_map_is_not_confirmed() -> None:
    """segment 가 없으면 ``absent`` 다 — ``confirmed`` 로 올리지 않는다.

    계약 §6.1: absent/unconfirmed 에서는 beat 기반 FX 를 실행하지 않는다. 여기서
    confirmed 로 올리면 그 차단이 그대로 풀린다.
    """
    assert ctx.resolve_beat_map_status(segments=(), confirmed_evidence=False) == "absent"


def test_unconfirmed_beat_map_stays_unconfirmed() -> None:
    segments = ({"start_ms": 0, "end_ms": 1000, "start_beat": 0, "bpm": 120, "evidence_ref": "e"},)

    assert ctx.resolve_beat_map_status(segments=segments, confirmed_evidence=False) == "unconfirmed"


def test_confirmed_beat_map_needs_both_segments_and_evidence() -> None:
    """양성 대조."""
    segments = ({"start_ms": 0, "end_ms": 1000, "start_beat": 0, "bpm": 120, "evidence_ref": "e"},)

    assert ctx.resolve_beat_map_status(segments=segments, confirmed_evidence=True) == "confirmed"


def test_assembly_rejects_a_zero_fixture_group(observations: ctx.ContextObservations) -> None:
    """판정이 조립 경로에 이어져 있다 — 헬퍼를 우회해도 발급 직전에 잡힌다.

    이것이 없으면 `resolve_group_fixtures` 는 아무도 부르지 않는 초록 부품이 된다.
    """
    groups = copy.deepcopy(observations.groups)
    groups[0]["fixture_ids"] = []

    with pytest.raises(ctx.ContextBuildError) as caught:
        ctx.build_snapshot(observations.replace(groups=groups))

    assert "COUNT 0" in str(caught.value)


def test_assembly_rejects_a_confirmed_beat_map_without_segments(
    observations: ctx.ContextObservations,
) -> None:
    beat_map = {"status": "confirmed", "segments": []}

    with pytest.raises(ctx.ContextBuildError):
        ctx.build_snapshot(observations.replace(beat_map=beat_map))


def test_assembly_rejects_observed_identity_without_evidence(
    observations: ctx.ContextObservations,
) -> None:
    target = copy.deepcopy(observations.target)
    target["identity_status"] = "observed"
    target["identity_evidence_refs"] = []

    with pytest.raises(ctx.ContextBuildError):
        ctx.build_snapshot(observations.replace(target=target))


def test_unknown_role_is_never_filled_with_chorus() -> None:
    """계약 §6.1: role unknown/confidence 0 이 허용되며 unknown 을 chorus 로 채우지 않는다."""
    assert ctx.resolve_section_role(observed_role=None) == ("unknown", 0.0)


# ---------------------------------------------------------------------------
# 4. binding 무효화
# ---------------------------------------------------------------------------


def _bindings_of(snapshot: dict[str, Any]) -> dict[str, Any]:
    return ctx.current_bindings(snapshot)


def test_current_bindings_carry_exactly_the_seven_contract_fields(
    observations: ctx.ContextObservations,
) -> None:
    snapshot = ctx.build_snapshot(observations)

    assert set(_bindings_of(snapshot)) == set(_BINDING_FIELDS)


def test_matching_bindings_are_not_stale(observations: ctx.ContextObservations) -> None:
    """양성 대조 — 방금 발급한 snapshot 의 binding 은 신선하다."""
    snapshot = ctx.build_snapshot(observations)

    assert ctx.stale_bindings(snapshot, _bindings_of(snapshot), now="2026-09-13T10:30:00Z") == ()


@pytest.mark.parametrize("field", _BINDING_FIELDS)
def test_each_binding_field_is_checked(field: str, observations: ctx.ContextObservations) -> None:
    """일곱 필드 각각이 실제로 대조된다 — 하나라도 안 보면 그 축의 변경이 통과한다."""
    snapshot = ctx.build_snapshot(observations)
    bindings = dict(_bindings_of(snapshot))
    bindings[field] = 999 if isinstance(bindings[field], int) else "sha256:" + "e" * 64

    assert ctx.stale_bindings(snapshot, bindings, now="2026-09-13T10:30:00Z") == (field,)


def test_expired_snapshot_is_stale_even_when_every_binding_matches(
    observations: ctx.ContextObservations,
) -> None:
    """만료는 아홉째 축이다 — binding 이 전부 맞아도 만료되면 승인을 쓸 수 없다."""
    snapshot = ctx.build_snapshot(observations)

    stale = ctx.stale_bindings(snapshot, _bindings_of(snapshot), now="2026-09-13T11:00:01Z")

    assert stale == ("expires_at",)


def test_previous_approval_digest_is_blocked_after_an_axis_change(
    observations: ctx.ContextObservations,
) -> None:
    """AC-LDPLUGIN-004 의 본문 — preset 내용이 바뀌면 이전 승인이 차단된다."""
    old = ctx.build_snapshot(observations)
    old_bindings = _bindings_of(old)

    new = ctx.build_snapshot(_mutate_preset_content(observations))

    assert ctx.stale_bindings(new, old_bindings, now="2026-09-13T10:30:00Z") == ("context_digest",)
