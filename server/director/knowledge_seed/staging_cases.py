"""주제 3/5 — 연출 case (design.md §3 표 3행, SPEC-LDSTORE-001 M3). 순수 데이터.

``kind`` 가 ``case`` 인 유일한 seed 항목이다 — 사례는 법칙이 아니므로 ``outcome`` 에 실제
측정이 없으면 "문서 예시/미측정" 을 명시한다 (design.md §3, 계약 §3 `KnowledgeRecord`).
"""

from __future__ import annotations

from typing import Any

TOPIC: dict[str, Any] = {
    "record_id": "kb-staging-cases",
    "kind": "case",
    "scope": "user_style",
    "summary": (
        "후렴 90/95/100·6–8색·bridge 대비는 특정 공연에서 관측된 예시이며, 반복 motif·같은 "
        "강도·조용한 종료 같은 대안도 유효한 선택으로 함께 제시한다."
    ),
    "applicability": (
        "후렴 강도 단계를 설계할 때",
        "bridge 대비를 설계할 때",
    ),
    "exceptions": ("실제 측정된 성공 사례가 아니면 outcome 에 '문서 예시/미측정' 을 명시한다.",),
    "provenance": {
        "origin": "observed",
        "actor_ref": "kb-reviewer-001",
        "source_refs": ("legacy-staging-notes",),
        "evidence_refs": ("evidence-staging-case-001",),
        "rationale": (
            "원문 인용 범위를 최소화하고 case 임을 표시했다. 성공했다는 실제 측정이 없으면 "
            "outcome 에 문서 예시/미측정을 명시한다."
        ),
    },
    "evidence_refs": ("evidence-staging-case-001",),
    "resource_id": "resource-kb-staging-cases-v1",
    "reviewed_revision": 1,
    "rights_scope": (
        "사용자 소유 환경의 local source 참조·요약만 제공한다. 특정 공연의 원문을 재배포하지 "
        "않는다."
    ),
    "details": {
        "music_context": "후렴 3회 반복 + bridge 1회를 포함한 4분대 곡 구조.",
        "sequence": [
            {
                "section_role": "chorus_1",
                "intent": "강도 90% 로 시작해 다음 후렴과의 상승 여지를 남긴다.",
                "actions_summary": "6색 preset, intensity 90%.",
                "transition_summary": "이전 verse 대비 fade-in 800ms.",
            },
            {
                "section_role": "chorus_2",
                "intent": "강도 95% 로 반복 motif 를 유지한 채 상승한다.",
                "actions_summary": "동일 motif 유지, intensity 95%, 8색으로 확장.",
                "transition_summary": "직전 chorus 종료 상태에서 즉시 상승.",
            },
            {
                "section_role": "bridge",
                "intent": "대비를 위해 강도를 낮추고 색을 축소한다 — 조용한 종료 대안.",
                "actions_summary": "intensity 40%, 2색으로 축소.",
                "transition_summary": "chorus_2 대비 급격한 fade-out.",
            },
            {
                "section_role": "chorus_3",
                "intent": "강도 100% 로 최종 클라이맥스를 낸다.",
                "actions_summary": "8색 유지, intensity 100%.",
                "transition_summary": "bridge 대비 강한 상승.",
            },
        ],
        "outcome": "문서 예시/미측정 — 실제 무대에서의 성공 여부는 관측되지 않았다.",
        "limitations": [
            "이 수치는 강제 규칙이 아니라 한 공연에서 관측된 예시다.",
            "곡의 실제 에너지 곡선에 따라 강도 단계는 달라질 수 있다.",
        ],
    },
}
