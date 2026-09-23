"""근거 등급 데이터 시험 — SPEC-LDDESIGN-001 M5 (REQ-LDDESIGN-071~072, 카드
t438).

렌더링(화면 열 노출)은 M7 스코프다 — 이 파일은 그 화면이 쓸 데이터
(설명 문자열·마커)만 시험한다.
"""

from __future__ import annotations

from server.concept.cue_model import validate_evidence
from server.concept.evidence import (
    EVIDENCE_FOR_FADE,
    EVIDENCE_FOR_MIB_TIMING,
    EVIDENCE_FOR_SAFETY,
    NO_PUBLIC_EVIDENCE_MARKER,
    VERIFIED_EXPLANATION,
    mark_no_public_evidence,
)


class TestEvidenceGrades:
    """REQ-LDDESIGN-022(4등급 어휘) 안에 드는지도 함께 확인한다."""

    def test_safety_is_verified(self):
        assert EVIDENCE_FOR_SAFETY == "verified"
        validate_evidence(EVIDENCE_FOR_SAFETY)

    def test_fade_is_verified(self):
        assert EVIDENCE_FOR_FADE == "verified"
        validate_evidence(EVIDENCE_FOR_FADE)

    def test_mib_provisional_timing_is_designed_rule(self):
        assert EVIDENCE_FOR_MIB_TIMING == "designed_rule"
        validate_evidence(EVIDENCE_FOR_MIB_TIMING)


class TestVerifiedExplanation:
    """REQ-LDDESIGN-071 — verified 는 이 곡에서 검증한 것이 아니라는 설명이
    함께 붙는다."""

    def test_explains_verified_is_not_song_specific(self):
        assert "이 곡에서 직접 검증" in VERIFIED_EXPLANATION

    def test_is_non_empty(self):
        assert VERIFIED_EXPLANATION != ""


class TestMarkNoPublicEvidence:
    """REQ-LDDESIGN-072 — 자동 채움 항목 중 공개 근거가 없는 것은
    "[공개 근거 없음]" 표시를 갖는다."""

    def test_appends_marker(self):
        result = mark_no_public_evidence("남은 상승 단계 자동 채움")
        assert result.endswith(NO_PUBLIC_EVIDENCE_MARKER)
        assert "남은 상승 단계 자동 채움" in result

    def test_marker_literal_value(self):
        assert NO_PUBLIC_EVIDENCE_MARKER == "[공개 근거 없음]"
