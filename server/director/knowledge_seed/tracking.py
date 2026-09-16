"""주제 2/5 — tracking 규칙 (design.md §3 표 2행, SPEC-LDSTORE-001 M3). 순수 데이터."""

from __future__ import annotations

from typing import Any

TOPIC: dict[str, Any] = {
    "record_id": "kb-tracking-rules",
    "kind": "rule",
    "scope": "user_style",
    "summary": (
        "omission=hold, explicit off, FX stop, baseline/terminal 을 구분하고 변경된 축만 "
        "기입하되 첫 상태는 누락하지 않는다."
    ),
    "applicability": (
        "cue 의 action 을 typed field 로 옮길 때",
        "이전 cue 와 비교해 변경 축만 기록할 때",
    ),
    "exceptions": ("legacy CUE/CUE-EX 절차와 현재 계약이 어긋나면 계약을 우선한다.",),
    "provenance": {
        "origin": "derived",
        "actor_ref": "kb-reviewer-001",
        "source_refs": ("legacy-cue-sheet-tracking-procedure",),
        "evidence_refs": ("evidence-cue-ex-tracking-review",),
        "rationale": (
            "legacy CUE/CUE-EX 절차를 현재 계약의 typed semantics 로 재검토했다; 불일치는 "
            "계약이 우선한다."
        ),
    },
    "evidence_refs": ("evidence-cue-ex-tracking-review",),
    "resource_id": "resource-kb-tracking-rules-v1",
    "reviewed_revision": 1,
    "rights_scope": (
        "사용자 소유 환경의 local source 참조·요약만 제공한다. 원문 CUE/CUE-EX 시트를 "
        "재배포하지 않는다."
    ),
    "details": {
        "procedure": [
            "omission 은 hold(이전 값 유지)로 해석한다.",
            "explicit off 와 FX stop 을 서로 다른 typed action 으로 기록한다.",
            "cue 의 baseline/terminal state 를 구분해 남긴다.",
            "변경된 축만 기입하되, 그 cue 가 첫 등장이면 첫 상태를 반드시 기입한다.",
        ],
        "avoid": [
            "omission 을 off 로 잘못 해석하는 것.",
            "첫 상태를 생략한 채 변경 축만 기입하는 것 — 재생 시작점이 불명확해진다.",
        ],
    },
}
