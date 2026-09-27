"""근거 등급 설명·공개 근거 없음 표시 — SPEC-LDDESIGN-001 M5
(REQ-LDDESIGN-071~072).

``evidence`` 등급 어휘 자체(4등급)는 M2(:mod:`server.concept.cue_model`)
가 이미 정의한다 — 이 파일은 그 어휘를 화면(M7 스코프)에 노출할 때 쓰는
**설명 텍스트**와, 자동 채움 항목에 붙는 "[공개 근거 없음]" 마커만
담는다.
"""

from __future__ import annotations

from server.concept.cue_model import validate_evidence

__all__ = [
    "VERIFIED_EXPLANATION",
    "NO_PUBLIC_EVIDENCE_MARKER",
    "EVIDENCE_FOR_SAFETY",
    "EVIDENCE_FOR_FADE",
    "EVIDENCE_FOR_MIB_TIMING",
    "evidence_for_row",
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


# --- 카드 t457 — 큐 행 하나의 근거 등급(REQ-022) ------------------------------
#
# 리드 승인 표(2026-09-27). 원칙: 조문이 직접 받치는 곳만 등급을 붙이고, 애매하면
# None 이다 — 등급을 지어내지 않는다.

# REQ-022 「회차 확장·빌드업 등 실무 관행」 — 빌드업(REQ-037)과 후렴 안 프레이즈
# 밀도(REQ-043 회차 확장 축 「큐 밀도」, REQ-045).
_PRACTITIONER_TRIGGERS = frozenset({"빌드업 시작", "악기 추가"})

# REQ-038 — 피날레 앞 눈 리셋은 이 SPEC 이 구성한 규칙이다.
_DESIGNED_RULE_TRIGGERS = frozenset({"드롭 직전의 정적"})

# REQ-022 「구간 판정기 출력을 그대로 옮긴 경우」 — 컴파일러가 규칙 없이 상태만
# 유지하는(retain) 판정기 이름 구간(``density.compile_density`` 의 else 분기).
_JUDGE_RETAIN_SECTIONS = frozenset({"Pre-Chorus", "Post-Chorus", "Rap/Solo/Dance Break"})


def evidence_for_row(kind: str, section: str, trigger: str | None, occurrence: int) -> str | None:
    """컨셉 큐 행 하나의 근거 등급(REQ-022) — 조문이 받치지 않으면 ``None``.

    - safety(곡 첫 block·끝 release, REQ-068/069) → ``verified`` (REQ-071 「안전 규칙」)
    - 후렴 2회차부터·Final Chorus → ``practitioner_pattern`` (REQ-022 「회차 확장」,
      REQ-042~044·048). 후렴 1회차는 확장 전 기준 상태라 ``None``.
    - 「빌드업 시작」·「악기 추가」 프레이즈 → ``practitioner_pattern``
    - 「드롭 직전의 정적」 프레이즈 → ``designed_rule`` (REQ-038)
    - 판정기 이름 retain 구간 → ``director``
    - 그 밖(Intro·Verse·Bridge·Outro 구간, 「보컬 시작」) → ``None``
    """
    grade: str | None = None
    if kind == "safety":
        grade = EVIDENCE_FOR_SAFETY
    elif kind == "section":
        if section == "Final Chorus" or (section == "Chorus" and occurrence >= 2):
            grade = "practitioner_pattern"
        elif section in _JUDGE_RETAIN_SECTIONS:
            grade = "director"
    elif kind == "phrase":
        if trigger in _PRACTITIONER_TRIGGERS:
            grade = "practitioner_pattern"
        elif trigger in _DESIGNED_RULE_TRIGGERS:
            grade = "designed_rule"
    return None if grade is None else validate_evidence(grade)
