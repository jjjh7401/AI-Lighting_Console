"""주제 5/5 — 적용·안전 규칙 (design.md §3 표 5행, SPEC-LDSTORE-001 M3). 순수 데이터."""

from __future__ import annotations

from typing import Any

TOPIC: dict[str, Any] = {
    "record_id": "kb-apply-safety-rules",
    "kind": "rule",
    "scope": "user_style",
    "summary": (
        "적용은 preview → human approval → programming → readback/visual 확인 순서로 "
        "분리하고, live lock·회수 절차를 지킨다."
    ),
    "applicability": (
        "plan 을 승인 후 apply 할 때",
        "recovery 절차를 시작할 때",
    ),
    "exceptions": (
        "자동 rollback·blind resend·silent ClearAll 은 이 규칙의 예외로도 허용되지 않는다.",
    ),
    "provenance": {
        "origin": "human_confirmed",
        "actor_ref": "kb-reviewer-001",
        "source_refs": ("console-transfer-manual-section", "safety-gate-policy"),
        "evidence_refs": ("evidence-safety-gate-current",),
        "rationale": ("console-transfer 의 수동 항목과 현행 SafetyGate 기준을 분리해 기록했다."),
    },
    "evidence_refs": ("evidence-safety-gate-current",),
    "resource_id": "resource-kb-apply-safety-rules-v1",
    "reviewed_revision": 1,
    "rights_scope": (
        "사용자 소유 환경의 local SafetyGate 정책 참조·요약만 제공한다. 정책 원문을 재배포하지 "
        "않는다."
    ),
    "details": {
        "procedure": [
            "preview 를 사람이 검토한 뒤에만 programming 단계로 넘어간다.",
            "programming 이후 readback/visual 확인을 별도 단계로 거친다.",
            "적용 중에는 shared programmer lock 을 유지한다.",
            "실패·미확정 상태는 별도 recovery plan revision 으로 처리한다.",
        ],
        "avoid": [
            "사람 승인 없이 programming 단계로 건너뛰는 것.",
            "자동 rollback·blind resend·silent ClearAll 을 수행하는 것.",
        ],
    },
}
