"""진단 하나의 형태 — 계약 §6.3 의 9개 필드 (SPEC-LDCOMPILE-001 C1).

이 모듈이 있는 이유는 하나다. **조용한 수용을 진단 부재로 표현할 수 없게** 만드는 것.

계약 §6.3 은 *"action 전체 단순 수용은 before/after 둘 다 present=false 로 하고 변경
없음임을 reason 에 밝힌다"* 고 규정한다. 즉 「아무 말 없음」은 이 층에서 합법적인 답이
아니다 — 수용도 진단이고, 사유가 붙는다. 그래서 진단을 만드는 통로를 한 자리로 모으고,
`before`/`after` 를 dict 리터럴로 손으로 쓰지 못하게 `absent()`/`present()` 로만 낸다.

콘솔 무접촉 · OSC 무접촉 — 순수 함수만 있다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

#: 계약 §6.3 의 status enum. 여섯 갈래이며 각각 사람이 할 행동이 다르다.
STATUS_ACCEPTED = "accepted"
STATUS_DERIVED = "derived"
STATUS_UNSUPPORTED = "unsupported"
STATUS_UNRESOLVED = "unresolved"
STATUS_CONFLICT = "conflict"
STATUS_SAFETY_BLOCKED = "safety_blocked"

STATUSES: tuple[str, ...] = (
    STATUS_ACCEPTED,
    STATUS_DERIVED,
    STATUS_UNSUPPORTED,
    STATUS_UNRESOLVED,
    STATUS_CONFLICT,
    STATUS_SAFETY_BLOCKED,
)

#: 계약 §6.3 의 diagnostic required 9개. `build_report` 가 이 집합만 낸다.
WIRE_FIELDS: tuple[str, ...] = (
    "diagnostic_id",
    "rule_id",
    "pointer",
    "status",
    "blocking",
    "before",
    "after",
    "reason",
    "evidence_refs",
)

#: 숫자 상한 — 계약 §6.3 *"숫자는 finite -1e9..1e9"*.
_NUM_LIMIT = 1e9


def absent() -> dict[str, Any]:
    """`present=false` — value 를 들지 않는다.

    계약 §6.3: *"present=true면 value가 반드시 있고 false면 없어야 한다"*. 키를 아예
    넣지 않는 것이 규정이며 `value: None` 은 위반이다.
    """
    return {"present": False}


def present(value: Any) -> dict[str, Any]:
    """`present=true` — value 가 반드시 있다.

    Raises:
        ValueError: 숫자가 유한 범위(-1e9..1e9) 밖이거나, object 전체를 넣으려 할 때.
            계약 §6.3 이 *"object 전체는 value로 넣지 않고 해당 leaf에 진단한다"* 고
            규정하므로 dict/list-of-dict 는 여기서 막는다.
    """
    if isinstance(value, bool):
        # bool 은 int 의 하위형이라 아래 숫자 검사에 먼저 걸린다. 먼저 빼낸다.
        return {"present": True, "value": value}
    if isinstance(value, (int, float)):
        if value != value or abs(value) > _NUM_LIMIT:  # NaN 은 자기와 다르다
            raise ValueError(f"유한 -1e9..1e9 밖의 숫자입니다: {value!r}")
        return {"present": True, "value": value}
    if isinstance(value, str):
        return {"present": True, "value": value}
    if isinstance(value, (list, tuple)):
        items = list(value)
        if all(isinstance(x, str) for x in items):
            return {"present": True, "value": items}
        raise ValueError("Id[] 가 아닌 배열입니다. leaf 에 따로 진단하십시오.")
    raise ValueError(
        f"object 전체는 value 로 넣지 않습니다({type(value).__name__}). "
        "leaf pointer 에 진단하십시오."
    )


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """진단 하나. `stage` 는 내부 추적용이며 wire 로 나가지 않는다.

    스키마가 `additionalProperties: false` 라서 `stage` 가 새어 나가면 보고서 전체가
    거절된다. 그래서 wire 변환은 `to_wire()` 한 자리에서만 일어난다.
    """

    rule_id: str
    pointer: str
    status: str
    blocking: bool
    reason: str
    stage: str
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ValueError(f"계약 §6.3 밖의 status 입니다: {self.status!r}")
        if not self.reason.strip():
            raise ValueError("사유 없는 진단은 조용한 수용입니다. reason 을 채우십시오.")

    def to_wire(self, diagnostic_id: str) -> dict[str, Any]:
        """계약 §6.3 의 9개 필드로 변환한다. `stage` 는 빠진다."""
        return {
            "diagnostic_id": diagnostic_id,
            "rule_id": self.rule_id,
            "pointer": self.pointer,
            "status": self.status,
            "blocking": self.blocking,
            "before": self.before if self.before is not None else absent(),
            "after": self.after if self.after is not None else absent(),
            "reason": self.reason,
            "evidence_refs": list(self.evidence_refs),
        }

    def to_internal(self) -> dict[str, Any]:
        """`stage` 를 포함한 내부 형태. 파이프라인 안에서만 쓴다."""
        wire = self.to_wire("pending")
        del wire["diagnostic_id"]
        wire["stage"] = self.stage
        return wire
