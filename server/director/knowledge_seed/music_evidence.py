"""주제 1/5 — 음악 근거 규칙 (design.md §3 표 1행, SPEC-LDSTORE-001 M3).

이 파일은 순수 데이터다. 검증·조립은 ``server.director.knowledge`` 가 한다 — 순환 임포트를
피하려고 이 패키지는 ``knowledge.py`` 를 참조하지 않는다.
"""

from __future__ import annotations

from typing import Any

TOPIC: dict[str, Any] = {
    "record_id": "kb-music-evidence-rules",
    "kind": "rule",
    "scope": "user_style",
    "summary": (
        "음악 판단은 DERIVED 값과 확인 완료 값을 구분하고, 전곡 합계·구간 경계·beat 근거를 "
        "확인한 뒤에만 조명 계획의 입력으로 쓴다."
    ),
    "applicability": (
        "구간 경계를 확정할 때",
        "beat 근거를 조명 FX 타이밍에 쓸 때",
        "전곡 합계를 검증할 때",
    ),
    "exceptions": (
        "4/4 고정 산식을 모든 곡에 일괄 적용하지 않는다 — 곡마다 실제 박자를 확인한다.",
    ),
    "provenance": {
        "origin": "human_confirmed",
        "actor_ref": "kb-reviewer-001",
        "source_refs": ("legacy-cue-sheet", "lx-seq-v2.1-doc"),
        "evidence_refs": ("evidence-lx-seq-v2.1-section-3",),
        "rationale": (
            "legacy cue-sheet 와 LX-SEQ v2.1 의 정확한 문서/section 참조, frozen source "
            "digest, reviewer·revision 으로 검토했다."
        ),
    },
    "evidence_refs": ("evidence-lx-seq-v2.1-section-3",),
    "resource_id": "resource-kb-music-evidence-rules-v1",
    "reviewed_revision": 1,
    "rights_scope": (
        "사용자 소유 환경의 local source 참조·요약만 제공한다. proprietary archive 를 외부 "
        "공개 라이선스로 재표시하지 않으며 배포 권리 확인 전에는 원문을 재배포하지 않는다."
    ),
    "details": {
        "procedure": [
            "DERIVED 값과 확인 완료 값을 필드 단위로 구분해 표기한다.",
            "전곡 합계가 실제 audio.duration_ms 와 일치하는지 검사한다.",
            "구간 경계가 beat_map evidence 와 일치하는지 검사한다.",
            "beat 근거 없이 beat 기반 FX 를 계획에 넣지 않는다.",
        ],
        "avoid": [
            "4/4 박자를 모든 곡에 고정 산식으로 적용하는 것.",
            "beat_map 이 absent 또는 unconfirmed 인데 확정값처럼 다루는 것.",
        ],
    },
}
