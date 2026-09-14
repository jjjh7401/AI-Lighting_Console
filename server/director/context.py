"""ContextSnapshot 조립과 binding 재검사 (SPEC-LDSTORE-001 M2 · REQ-LDPLUGIN-004).

서버가 snapshot 을 **발급**한다. 플러그인이 보내온 값을 받아 적는 자리가 아니다 —
계약 §6.1 이 `server-owned` 이라 못박은 이유는 snapshot 이 승인의 근거이기 때문이다.
제출자가 자기 context 를 선언할 수 있으면 승인 무효화 장치 전체가 무의미해진다.

## 아홉 축과 digest 범위

`REQ-LDPLUGIN-004` 의 아홉 축 — audio · show · group membership · preset 내용 ·
compiler · capability · 정책 · identity · 만료 — 이 :data:`NINE_AXES` 다.

[HARD] **아홉 축 전부가 snapshot 에 있고, digest 는 아홉 축 전부를 덮는다.**
`digest.context_digest` 가 최상위 ``context_digest`` key 하나만 제거하므로 이 범위는
자동으로 지켜지지만, :data:`NINE_AXES` 는 그 사실을 **기계로 잴 수 있게** 만든다.
어느 축이 digest 밖으로 새면 그 축이 바뀌어도 이전 승인이 유효하게 남는다 —
preset 내용이 바뀐 리그에 옛 승인이 적용될 수 있다 (`AC-LDPLUGIN-004`).

## 못 읽은 값을 승격하지 않는다

이 모듈의 ``resolve_*`` 함수들은 **판독 실패를 정직하게 표현하는 것**만 한다.
계약의 enum 이 그 자리를 이미 마련해 두었다: identity·preset 내용은 ``unreadable``,
beat map 은 ``absent``/``unconfirmed``, section role 은 ``unknown``.

특히 **``COUNT 0`` 은 부재의 증거가 아니다.** 내용이 있는 Group 이 0 을 답한 실측
사례가 있다(우산 `research.md`). 그래서 :func:`resolve_group_fixtures` 는 0개 판독을
"빈 그룹 확인" 으로 기록하지 않고 거절한다 — 그렇게 기록하면 그 그룹의 fixture 가
조명 계획에서 조용히 사라진다.

## M2 최소판에서 유보한 것

풍부함만 유보하고 축은 전부 둔다 (plan §2.1):

- audio — 근거 요약 수준까지. 전체 분석 산출물 연결은 M2 나머지.
- preset 내용 — 점유·이름까지. 값은 애초에 이 통로로 못 읽는다.
- capability — 선언된 범위까지. 실제 compiler+rig+target 출력 기반 광고는
  `SPEC-LDCOMPILE-001`(REQ-LDPLUGIN-013) 이 맡는다.

이 모듈은 관측을 **조립**한다. 관측을 **수행**하는 것(콘솔 판독, 오디오 분석)은 이
층의 일이 아니다 — 그래서 여기에는 OSC 도, 예술 판정기도 들어오지 않는다.
"""

from __future__ import annotations

import copy
import dataclasses
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from server.director.digest import context_digest, raw_digest

#: 계약 §2 — 이 교환 객체의 message_type 과 wire version.
MESSAGE_TYPE = "context_snapshot"
SCHEMA_VERSION = "1.0.0"

#: `REQ-LDPLUGIN-004` 의 아홉 축 → 그 축이 소유하는 snapshot 최상위 key.
#:
#: 이 표가 축과 필드를 잇는 단일 원본이다. 새 필드를 넣을 때 어느 축에 속하는지
#: 여기 적지 않으면 `test_no_top_level_key_escapes_axis_ownership` 이 잡는다 —
#: 어느 축에도 속하지 않은 필드는 "무엇이 바뀌었나" 를 답할 수 없게 만든다.
NINE_AXES: Mapping[str, tuple[str, ...]] = {
    "audio": ("audio", "music_revision", "music_sections", "beat_map"),
    "show": ("show_id", "show_revision"),
    "group_membership": ("groups", "rig_revision"),
    "preset_content": ("presets",),
    "compiler": ("compiler",),
    "capability": ("capabilities", "capability_revision"),
    "policy": ("safety", "safety_policy_revision", "limits"),
    "identity": ("target",),
    "expiry": ("expires_at",),
}

#: snapshot 자신의 identity·유효 범위. 축이 아니라 봉투다 (계약 §6.1).
ENVELOPE_KEYS: tuple[str, ...] = (
    "message_type",
    "schema_version",
    "environment",
    "context_id",
    "context_digest",
    "project_id",
    "created_at",
)

#: 여러 축에 걸친 출처·근거 catalog. 한 축에 귀속시키면 거짓이 된다 — `evidence` 는
#: music_map 과 rig_inventory 를 같은 배열에 담는다 (계약 §6.1). digest 에는 물론
#: 포함되므로 바뀌면 승인은 무효화된다.
CROSS_AXIS_KEYS: tuple[str, ...] = ("sources", "evidence")

#: 계약 §6.2 — plan 의 bindings 일곱. 전부 current snapshot 과 일치해야 한다.
BINDING_FIELDS: tuple[str, ...] = (
    "context_id",
    "context_digest",
    "audio_sha256",
    "music_revision",
    "rig_revision",
    "capability_revision",
    "safety_policy_revision",
)

#: 재발급 판정에서 **제외**하는 key. 계약 §6.1: *"매 GET마다 created_at만 바꾸어
#: pending plan을 stale로 만들지 않는다. ... 관측 시각 자체를 source 변경으로 보지
#: 않는다."* ``context_id``/``context_digest`` 는 재발급의 *결과*이므로 원인 비교에
#: 넣으면 순환이다.
_REISSUE_EXEMPT: frozenset[str] = frozenset({"created_at", "context_id", "context_digest"})


class ContextBuildError(Exception):
    """관측을 snapshot 으로 옮길 수 없을 때. 추측으로 메우지 않고 멈춘다."""


@dataclass(frozen=True, slots=True)
class ContextObservations:
    """snapshot 하나를 만들기 위해 서버가 관측한 값 전부.

    ``context_digest`` 는 여기 없다 — 그것은 관측이 아니라 관측의 **함수**다.
    제출자가 digest 를 선언할 수 없어야 한다는 계약 §9 의 요구(`LD-HASH-001`:
    *"payload 자체에 claimed digest가 있다고 신뢰하지 않는다"*)가 이 형태로 나타난다.
    """

    environment: str
    context_id: str
    project_id: str
    show_id: str
    show_revision: int
    created_at: str
    expires_at: str
    audio: Mapping[str, Any]
    music_revision: int
    rig_revision: int
    capability_revision: int
    safety_policy_revision: int
    compiler: Mapping[str, Any]
    target: Mapping[str, Any]
    sources: Sequence[Mapping[str, Any]]
    evidence: Sequence[Mapping[str, Any]]
    music_sections: Sequence[Mapping[str, Any]]
    beat_map: Mapping[str, Any]
    groups: Sequence[Mapping[str, Any]]
    presets: Sequence[Mapping[str, Any]]
    capabilities: Sequence[Mapping[str, Any]]
    safety: Mapping[str, Any]
    limits: Mapping[str, Any] = field(default_factory=lambda: dict(_CONTRACT_LIMITS))

    @classmethod
    def from_snapshot(cls, snapshot: Mapping[str, Any]) -> ContextObservations:
        """발급된 snapshot 을 관측으로 되분해한다.

        `context_digest` 는 버린다 — 다시 조립할 때 계산되어야 하는 값이므로,
        옮겨오면 재계산이 아니라 복사가 된다.

        Raises:
            ContextBuildError: 아홉 축 중 빠진 것이 있을 때.
        """
        absent = missing_axes(snapshot)
        if absent:
            raise ContextBuildError(f"아홉 축 중 빠진 것이 있습니다: {absent}")

        fields = {f.name for f in dataclasses.fields(cls)}
        payload = {key: copy.deepcopy(value) for key, value in snapshot.items() if key in fields}
        return cls(**payload)

    def replace(self, **changes: Any) -> ContextObservations:
        """한 축만 바꾼 사본. 관측은 불변이므로 제자리 수정을 제공하지 않는다."""
        return dataclasses.replace(self, **changes)


#: 계약 §6.1 의 고정 전송 상한. 스키마가 `const` 로 못박아 두었으므로 서버가 고른
#: 값이 아니라 계약이 정한 값이다.
_CONTRACT_LIMITS: Mapping[str, int] = {
    "plan_bytes": 2 * 1024 * 1024,
    "cues": 2048,
    "groups": 256,
    "actions_per_cue": 128,
}


def build_snapshot(observations: ContextObservations) -> dict[str, Any]:
    """관측에서 `ContextSnapshot` 하나를 발급한다.

    ``context_digest`` 는 조립이 끝난 **뒤** 계산한다 — 아홉 축 전부와 모든 metadata
    가 이미 자리에 있는 상태에서 계산해야 그 범위가 실제로 아홉 축을 덮는다.

    같은 관측을 넣으면 같은 snapshot 이 나온다(결정적). 계약 §6.1 이 *"source
    revision과 live binding이 그대로이고 미만료이면 같은 current snapshot을
    반환한다"* 고 요구하므로, 발급 시각을 이 함수가 스스로 읽지 않는다 —
    ``created_at`` 은 호출자가 관측으로 준다.
    """
    snapshot: dict[str, Any] = {
        "message_type": MESSAGE_TYPE,
        "schema_version": SCHEMA_VERSION,
        "environment": observations.environment,
        "context_id": observations.context_id,
        "project_id": observations.project_id,
        "show_id": observations.show_id,
        "show_revision": observations.show_revision,
        "created_at": observations.created_at,
        "expires_at": observations.expires_at,
        "audio": copy.deepcopy(dict(observations.audio)),
        "music_revision": observations.music_revision,
        "rig_revision": observations.rig_revision,
        "capability_revision": observations.capability_revision,
        "safety_policy_revision": observations.safety_policy_revision,
        "compiler": copy.deepcopy(dict(observations.compiler)),
        "target": copy.deepcopy(dict(observations.target)),
        "sources": copy.deepcopy(list(observations.sources)),
        "evidence": copy.deepcopy(list(observations.evidence)),
        "music_sections": copy.deepcopy(list(observations.music_sections)),
        "beat_map": copy.deepcopy(dict(observations.beat_map)),
        "groups": copy.deepcopy(list(observations.groups)),
        "presets": copy.deepcopy(list(observations.presets)),
        "capabilities": copy.deepcopy(list(observations.capabilities)),
        "safety": copy.deepcopy(dict(observations.safety)),
        "limits": copy.deepcopy(dict(observations.limits)),
    }
    _reject_promoted_unknowns(snapshot)
    snapshot["context_digest"] = context_digest(snapshot)
    return snapshot


def _reject_promoted_unknowns(snapshot: Mapping[str, Any]) -> None:
    """조립 지점에서 승격을 막는다.

    ``resolve_*`` 함수들만으로는 부족하다 — 호출자가 그것들을 우회해 dict 를 직접
    만들 수 있으므로, 부품이 초록이어도 경로는 안 이어진 상태가 된다. 그래서 판정을
    발급 직전에 한 번 더 둔다. 여기서 통과한 값만 digest 에 묶인다.

    Raises:
        ContextBuildError: 판독 실패가 확인으로 기록되어 있을 때.
    """
    for group in snapshot["groups"]:
        # `resolve_group_fixtures` 와 같은 판정. COUNT 0 은 부재의 증거가 아니다.
        resolve_group_fixtures(read_fixture_ids=group.get("fixture_ids"))

    beat_map = snapshot["beat_map"]
    if beat_map.get("status") == "confirmed" and len(beat_map.get("segments", ())) == 0:
        raise ContextBuildError(
            "beat_map 이 segment 없이 confirmed 입니다. 근거 없는 확인은 beat 기반 FX "
            "차단을 무력화하므로 absent 로 남겨야 합니다."
        )

    target = snapshot["target"]
    if (
        target.get("identity_status") == "observed"
        and len(target.get("identity_evidence_refs", ())) == 0
    ):
        raise ContextBuildError(
            "target identity 가 근거 없이 observed 입니다. 값만으로는 판독을 주장할 수 없습니다."
        )


def missing_axes(snapshot: Mapping[str, Any]) -> tuple[str, ...]:
    """아홉 축 중 snapshot 에 자리가 없는 것들.

    키 유무를 ``in`` 으로 본다 — ``.get()`` 은 "키 없음" 과 "값이 None" 을 같은
    ``None`` 으로 답하므로 축의 존재를 잴 계기가 못 된다.
    """
    return tuple(
        axis for axis, keys in NINE_AXES.items() if any(key not in snapshot for key in keys)
    )


def should_reissue(snapshot: Mapping[str, Any], observations: ContextObservations) -> bool:
    """새 context 를 발급해야 하는가.

    계약 §6.1: *"실제 재관측은 frozen snapshot의 show/group/preset/destination
    identity와 비교하며 관측 시각 자체를 source 변경으로 보지 않는다."* 따라서
    ``created_at`` 이 흐른 것만으로는 재발급하지 않는다 — 그렇게 하면 매 GET 이
    pending plan 을 stale 로 만들어 사람이 검토를 끝낼 수 없다.
    """
    rebuilt = build_snapshot(observations)
    keys = (set(rebuilt) | set(snapshot)) - _REISSUE_EXEMPT
    return any(rebuilt.get(key) != snapshot.get(key) for key in keys)


# ---------------------------------------------------------------------------
# 판독 결과를 정직하게 옮기는 함수들 — 승격은 여기서 막는다
# ---------------------------------------------------------------------------


def resolve_identity_status(
    *, observed_console_id: str | None, evidence_refs: Sequence[str]
) -> str:
    """콘솔 identity 상태 (계약 §6.1 · `LD-CTX-001`).

    값과 근거가 **함께** 있을 때만 ``observed`` 다. 값만 있고 근거가 없으면 판독했다고
    말할 수 없다 — 그 상태로 승인을 유지하면 계약 §8 `LD-CTX-001` 의 *"현재 identity가
    unreadable이면 requery/범위가 명확한 operator attestation 없이는 승인을 유지하지
    않는다"* 가 무력해진다.
    """
    if observed_console_id and len(evidence_refs) > 0:
        return "observed"
    return "unreadable"


def resolve_group_fixtures(*, read_fixture_ids: Sequence[str] | None) -> tuple[str, ...]:
    """판독된 group membership.

    [HARD] **``COUNT 0`` 을 "빈 그룹 확인" 으로 기록하지 않는다.** 내용이 있는 Group 이
    0 을 답한 실측 사례가 있다(우산 `research.md`) — 이 통로의 0/빈값은 부재의 증거가
    아니다. 0 을 그대로 적으면 그 그룹의 fixture 가 충돌 검사와 조명 계획에서 조용히
    사라지고, 실제로는 켜지는 장비가 계획에 없는 상태가 된다.

    계약 스키마도 ``fixture_ids`` 에 ``minItems: 1`` 을 걸어 "빈 그룹" 을 표현할 수
    없게 해 두었다. 그래서 여기서 멈추는 것이 맞다.

    Raises:
        ContextBuildError: 판독하지 못했거나 0개를 답했을 때.
    """
    if read_fixture_ids is None:
        raise ContextBuildError(
            "group membership 을 판독하지 못했습니다. 빈 그룹으로 기록하지 않습니다."
        )
    if len(read_fixture_ids) == 0:
        raise ContextBuildError(
            "group membership 판독이 COUNT 0 을 답했습니다. COUNT 0 은 부재의 증거가 "
            "아니므로(내용 있는 Group 이 0 을 답한 실측 사례) 빈 그룹으로 기록하지 "
            "않고 재판독을 요구합니다."
        )
    return tuple(read_fixture_ids)


def raw_content_digest(payload: bytes) -> str:
    """preset 내용 bytes 의 digest. JCS 를 적용하지 않는다 (계약 §9)."""
    return raw_digest(payload)


def resolve_preset_content(
    *, export_bytes: bytes | None, attestation_bytes: bytes | None
) -> tuple[str, str | None]:
    """preset 내용의 상태와 digest (계약 §6.1).

    세 갈래다:

    - **observed** — 서버가 보관한 실제 frozen preset export bytes 를 해시한다.
    - **attested** — 읽을 수 없어 immutable operator attestation bytes 를 대신 묶는다.
      digest 는 나오지만 ``observed`` 로 올리지 않는다. 계약 §6.1: *"attestation은
      측정 검증이 아니다."*
    - **unreadable** — 둘 다 없다. digest 도 없다. 계약 §6.1 은 이 상태에서
      ready 를 막으라고 규정한다.

    Returns:
        ``(status, digest)``. ``unreadable`` 일 때 digest 는 ``None`` 이다 —
        빈 문자열이나 0으로 채우면 "묶었다" 로 오독된다.
    """
    if export_bytes is not None:
        return "observed", raw_content_digest(export_bytes)
    if attestation_bytes is not None:
        return "attested", raw_content_digest(attestation_bytes)
    return "unreadable", None


def resolve_beat_map_status(
    *, segments: Sequence[Mapping[str, Any]], confirmed_evidence: bool
) -> str:
    """beat map 상태 (계약 §6.1 · `LD-TIME-002`).

    segment 가 없으면 ``absent``, 있어도 확인 근거가 없으면 ``unconfirmed`` 다.
    ``confirmed`` 로 올리면 계약 §6.1 의 *"absent/unconfirmed에서는 beat 기반 FX를
    실행하지 않는다"* 차단이 그대로 풀린다 — tempo 불명인데 120 BPM 을 가정한 FX 가
    무대에서 음악과 어긋나 돈다.

    ``synthetic`` 은 이 함수가 만들지 않는다. 계약 §8 `LD-SYN-001` 이 fixture 전용으로
    한정했으므로 합성 harness 가 명시적으로 지정해야 한다.
    """
    if len(segments) == 0:
        return "absent"
    return "confirmed" if confirmed_evidence else "unconfirmed"


def resolve_section_role(
    *, observed_role: str | None, confidence: float | None = None
) -> tuple[str, float]:
    """음악 구간 role 과 confidence (계약 §6.1).

    role 을 판정하지 못하면 ``("unknown", 0.0)`` 이다. 계약 §6.1: *"role
    unknown/confidence 0이 허용되며 unknown을 chorus로 채우지 않는다."*
    가장 흔한 role 로 메우면 그 구간의 조명이 근거 없이 후렴처럼 밝아진다.
    """
    if observed_role is None:
        return "unknown", 0.0
    return observed_role, 0.0 if confidence is None else confidence


# ---------------------------------------------------------------------------
# binding 재검사 — 승인 무효화의 실제 판정
# ---------------------------------------------------------------------------


def current_bindings(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """current snapshot 이 요구하는 binding 일곱 (계약 §6.2)."""
    return {
        "context_id": snapshot["context_id"],
        "context_digest": snapshot["context_digest"],
        "audio_sha256": snapshot["audio"]["sha256"],
        "music_revision": snapshot["music_revision"],
        "rig_revision": snapshot["rig_revision"],
        "capability_revision": snapshot["capability_revision"],
        "safety_policy_revision": snapshot["safety_policy_revision"],
    }


def stale_bindings(
    snapshot: Mapping[str, Any], bindings: Mapping[str, Any], *, now: str
) -> tuple[str, ...]:
    """제출된 binding 중 current snapshot 과 어긋난 것들 (`AC-LDPLUGIN-004`).

    빈 tuple 이 아니면 그 승인은 쓸 수 없다. 만료도 어긋남으로 센다 — 만료는 아홉째
    축이므로, binding 일곱이 전부 맞아도 시간이 지나면 승인은 무효다.

    Args:
        now: 판정 시각. 이 함수가 시계를 스스로 읽지 않는다 — 시험이 만료 경계를
            잴 수 있어야 하고, 판정 시각은 호출자의 감사 기록에 남아야 한다.

    Returns:
        어긋난 필드 이름들. 순서는 :data:`BINDING_FIELDS` 를 따르고 만료가 마지막이다.
    """
    stale = [
        field_name
        for field_name, expected in current_bindings(snapshot).items()
        if bindings.get(field_name) != expected
    ]
    if _parse_utc(now) > _parse_utc(snapshot["expires_at"]):
        stale.append("expires_at")
    return tuple(stale)


def _parse_utc(value: str) -> datetime:
    """계약 §2 의 시각(끝이 ``Z``)을 datetime 으로.

    문자열 비교로 대신하지 않는다 — 같은 순간을 다르게 적은 두 표기(``10:00:00Z`` 와
    ``10:00:00.000Z``)에서 사전순이 시간순과 어긋난다.
    """
    return datetime.fromisoformat(value)
