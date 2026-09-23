"""근거 등급 설명·공개 근거 없음 표시 — SPEC-LDDESIGN-001 M5
(REQ-LDDESIGN-071~072).

``evidence`` 등급 어휘 자체(4등급)는 M2(:mod:`server.concept.cue_model`)
가 이미 정의한다 — 이 파일은 그 어휘를 화면(M7 스코프)에 노출할 때 쓰는
**설명 텍스트**와, 자동 채움 항목에 붙는 "[공개 근거 없음]" 마커만
담는다.
"""

from __future__ import annotations

__all__ = [
    "VERIFIED_EXPLANATION",
    "NO_PUBLIC_EVIDENCE_MARKER",
    "EVIDENCE_FOR_SAFETY",
    "EVIDENCE_FOR_FADE",
    "EVIDENCE_FOR_MIB_TIMING",
    "mark_no_public_evidence",
]

# REQ-071 — "verified"는 정본이 실측한 규칙(페이드 문법·안전 큐 정책 등)에만
# 붙는 등급이다 — 이 곡에서 직접 검증됐다는 뜻이 아니다
# (apply-candidates-20260921.md 한계 절과 같은 방향).
VERIFIED_EXPLANATION = (
    "verified 는 정본이 실측한 규칙(페이드 문법·안전 큐 정책 등)에만 붙는 "
    "등급이다 — 이 곡에서 직접 검증됐다는 뜻이 아니다."
)

# REQ-072 — 워크시트나 판정기가 자동으로 채운 항목에 공개 근거가 없으면
# 붙는 표시(문서 §11).
NO_PUBLIC_EVIDENCE_MARKER = "[공개 근거 없음]"

# 안전 큐(REQ-068/069)·페이드(REQ-061)는 이 저장소가 실측한 규칙이다 → verified.
EVIDENCE_FOR_SAFETY = "verified"
EVIDENCE_FOR_FADE = "verified"

# §F 잠정값(MOVE_SECONDS/SETTLE_SECONDS)은 M8 콘솔 프로브 전까지 이
# SPEC이 구성한 규칙이다 → designed_rule.
EVIDENCE_FOR_MIB_TIMING = "designed_rule"


def mark_no_public_evidence(item: str) -> str:
    """REQ-072 — 공개 근거가 없는 자동 채움 항목에 마커를 붙인다."""
    return f"{item} {NO_PUBLIC_EVIDENCE_MARKER}"
