"""digest 계산 (SPEC-LDSTORE-001 M1 · 계약 §9).

계약 §9 의 규정을 그대로 옮긴다:

> 모든 JSON digest 는 `sha256(UTF-8(RFC8785/JCS(value)))` 를 `sha256:<hex>` 로 표시한다.
> JCS 는 object key 를 정렬하고 JSON number 를 규정대로 직렬화한다. 예쁜 출력·공백·key
> 순서는 무관하며 array 순서는 유지한다. **별도 Unicode normalization 을 하지 않는다.**
> 중복 key 는 canonicalization 전에 거부한다. **raw bytes digest 에는 JCS 를 적용하지
> 않는다.**

**JCS 를 손으로 근사하지 않는 이유.** digest 는 외부 플러그인이 같은 값을 계산해야 하는
wire 계약이다. `json.dumps(sort_keys=True, separators=(",", ":"))` 는 계약의 합성 예제
digest 를 **우연히 재현한다** — 그 예제의 float 일곱이 전부 정수값이 아니기 때문이다.
그러나 JCS 가 아니다: 정수값 float 에서 stdlib 은 `1.0`, JCS 는 `1` 을 쓴다(실측). 근사가
어긋나는 날 정상 계획이 조용히 거부되므로 규격 구현(`rfc8785`)을 쓴다.

중복 key 거부는 여기가 아니라 파싱 지점(`models.parse_exchange`)이 맡는다 — 계약이
"canonicalization 전에" 라고 규정했고, dict 가 된 뒤에는 중복이 이미 사라져 있다.
"""

from __future__ import annotations

import hashlib
from typing import Any

import rfc8785

#: 계약 §3 의 envelope 필드. plan 안에 있으면 안 되는 것들이다 (계약 §9.2 는 digest
#: 대상에서 제외하라고 규정하지만, 애초에 plan 에 실려 오면 잘못된 제출이다).
_ENVELOPE_ONLY_FIELDS = ("expected_revision", "idempotency_key")

#: 계약 §9.1 — context_digest 계산에서 제거하는 **최상위** key. 하나뿐이다.
_CONTEXT_SELF_FIELD = "context_digest"


def raw_digest(payload: bytes) -> str:
    """raw bytes 의 digest. JCS 를 적용하지 않는다 (계약 §9).

    audio bytes, compiler build artifact, frozen preset export 가 이 경로다.
    """
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def canonical_digest(value: Any) -> str:
    """JSON 값의 digest — `sha256(UTF-8(JCS(value)))` (계약 §9)."""
    return raw_digest(rfc8785.dumps(value))


def context_digest(snapshot: dict[str, Any]) -> str:
    """ContextSnapshot 의 digest (계약 §9.1).

    최상위 ``context_digest`` key **하나만** 제거한다. compiler·safety·identity·만료와
    모든 metadata 를 포함하며, **중첩된 `content_digest` 등은 제거하지 않는다.**

    이 범위가 안전 장치다: 아홉 축(audio · show · group membership · preset 내용 ·
    compiler · capability · 정책 · identity · 만료) 중 어느 것이 바뀌어도 digest 가
    움직여야 이전 승인이 무효화된다. 일부 축만 넣으면 preset 내용이 바뀐 리그에 옛
    승인이 그대로 유효하게 남는다 (AC-LDPLUGIN-004).
    """
    subject = {key: value for key, value in snapshot.items() if key != _CONTEXT_SELF_FIELD}
    return canonical_digest(subject)


def plan_digest(plan: dict[str, Any]) -> str:
    """제출된 LightingPlan 의 digest (계약 §9.2).

    plan 에는 digest self-field 가 없으므로 제거할 것이 없다. ``base_revision`` ·
    ``provenance`` · ``rationale`` 은 **포함**한다.

    Raises:
        ValueError: plan 에 envelope 전용 필드가 섞여 있을 때. 계약 §9.2 는 그것들을
            digest 대상에서 제외하라고 하지만, 조용히 걸러내면 잘못된 제출이 성공으로
            보인다. 계약 §3 의 envelope 와 exchange 는 다른 객체다.
    """
    intruders = [field for field in _ENVELOPE_ONLY_FIELDS if field in plan]
    if intruders:
        raise ValueError(
            f"LightingPlan 에 envelope 전용 필드가 있습니다: {intruders}. "
            "계약 §3 의 envelope 와 exchange 객체는 분리되어야 합니다."
        )
    return canonical_digest(plan)
