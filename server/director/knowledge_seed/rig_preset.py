"""주제 4/5 — rig·preset 규칙 (design.md §3 표 4행, SPEC-LDSTORE-001 M3). 순수 데이터."""

from __future__ import annotations

from typing import Any

TOPIC: dict[str, Any] = {
    "record_id": "kb-rig-preset-rules",
    "kind": "rule",
    "scope": "user_style",
    "summary": (
        "조명 계획은 실제 group/preset 참조를 쓰고, 현장 position record·footprint·mode 를 "
        "확인하며, content 와 attestation 을 구분한다."
    ),
    "applicability": (
        "group/preset 을 plan 의 action 에 참조로 넣을 때",
        "제안 장비를 계획에 포함할지 판단할 때",
    ),
    "exceptions": ("제안 장비를 confirmed inventory 로 승격하지 않는다.",),
    "provenance": {
        "origin": "human_confirmed",
        "actor_ref": "kb-reviewer-001",
        "source_refs": ("rig-pack", "stage-setup-source"),
        "evidence_refs": ("evidence-rig-pack-001",),
        "rationale": (
            "RIG 팩 및 stage-setup source 로 검토했다. 제안 장비를 confirmed inventory 로 "
            "승격하지 않는다."
        ),
    },
    "evidence_refs": ("evidence-rig-pack-001",),
    "resource_id": "resource-kb-rig-preset-rules-v1",
    "reviewed_revision": 1,
    "rights_scope": (
        "사용자 소유 환경의 local RIG 팩 참조·요약만 제공한다. 팩 원문을 재배포하지 않는다."
    ),
    "details": {
        "procedure": [
            "action 의 group_id/preset_id 는 현재 context 의 실제 group/preset 참조만 쓴다.",
            "현장 position record·footprint·mode 를 확인한 뒤 참조한다.",
            "preset content 가 observed(실측) 인지 attested(운영자 확인) 인지 구분해 기록한다.",
        ],
        "avoid": [
            "제안 단계의 장비를 confirmed inventory 인 것처럼 계획에 넣는 것.",
            "content 와 attestation 을 구분하지 않고 값을 확정으로 다루는 것.",
        ],
    },
}
