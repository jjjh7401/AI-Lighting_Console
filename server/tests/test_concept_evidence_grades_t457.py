"""카드 t457 — 컨셉 리포트 행의 근거 등급(REQ-LDDESIGN-022/071) 생산자 배선.

리드 승인 표(2026-09-27) — 원칙: 조문이 직접 받치는 곳만, 애매하면 None.

- safety 첫(block)·끝(release) → verified (REQ-071 「안전 규칙」)
- section Chorus 2회차~·Final Chorus → practitioner_pattern (REQ-022 「회차 확장」)
- phrase 「빌드업 시작」 → practitioner_pattern (REQ-022 「빌드업」, REQ-037)
- phrase 「악기 추가」 → practitioner_pattern (REQ-043 회차 확장 축, REQ-045)
- phrase 「드롭 직전의 정적」 → designed_rule (REQ-038, 이 SPEC 의 규칙)
- section Pre-Chorus·Post-Chorus·Rap/Solo/Dance Break → director (REQ-022)
- 그 밖(Chorus 1회차·Bridge·Intro·Verse·Outro·「보컬 시작」) → None

조문 인용 전문은 ``.moai/reports/t457/verdict.md`` 에 있다.

RED 재현 — 고치기 전(``origin/main@ab1c12f9``)에는 ``_concept_rows`` 가 모든 행에
``"evidence": None`` 을 실었다(생산자 0곳).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from server.concept.cue_model import EVIDENCE_GRADES
from server.concept.evidence import evidence_for_row
from server.concept.gates import build_song
from server.concept.session_bridge import _concept_rows

_FIXTURE = Path(__file__).parent / "fixtures" / "pilot_baseline.json"
_SONGS = [s for s in json.loads(_FIXTURE.read_text(encoding="utf-8")) if "error" not in s]

_ROW_KEYS = {
    "q",
    "ts",
    "kind",
    "section",
    "occurrence",
    "trigger",
    "tracking",
    "mib",
    "one_shot",
    "evidence",
    "screen_position",
}


class TestEvidenceForRow:
    @pytest.mark.parametrize("section", ["Intro", "Outro"])
    def test_safety_cues_are_verified(self, section):
        assert evidence_for_row("safety", section, None, 0) == "verified"

    @pytest.mark.parametrize("occurrence", [2, 3, 9])
    def test_repeated_chorus_is_practitioner_pattern(self, occurrence):
        assert evidence_for_row("section", "Chorus", None, occurrence) == "practitioner_pattern"

    def test_first_chorus_is_not_graded(self):
        """확장 전 기준 상태 — 「회차 확장」 조문이 받치지 않는다."""
        assert evidence_for_row("section", "Chorus", None, 1) is None

    def test_final_chorus_is_practitioner_pattern(self):
        assert evidence_for_row("section", "Final Chorus", None, 1) == "practitioner_pattern"

    @pytest.mark.parametrize("trigger", ["빌드업 시작", "악기 추가"])
    def test_escalation_phrases_are_practitioner_pattern(self, trigger):
        assert evidence_for_row("phrase", "Chorus", trigger, 2) == "practitioner_pattern"

    def test_eye_reset_phrase_is_designed_rule(self):
        assert evidence_for_row("phrase", "Final Chorus", "드롭 직전의 정적", 1) == "designed_rule"

    @pytest.mark.parametrize("section", ["Pre-Chorus", "Post-Chorus", "Rap/Solo/Dance Break"])
    def test_judge_named_retain_sections_are_director(self, section):
        assert evidence_for_row("section", section, None, 1) == "director"

    @pytest.mark.parametrize(
        ("kind", "section", "trigger"),
        [
            ("section", "Intro", None),
            ("section", "Verse", None),
            ("section", "Bridge", None),
            ("section", "Outro", None),
            ("phrase", "Intro", "보컬 시작"),
        ],
    )
    def test_rows_without_a_backing_clause_stay_none(self, kind, section, trigger):
        assert evidence_for_row(kind, section, trigger, 1) is None


class TestConceptRowsCarryTheGrade:
    """8곡 실측 — 행 키는 그대로, 등급은 4등급 안의 값이거나 None."""

    @pytest.mark.parametrize("song", _SONGS, ids=lambda s: s["song"])
    def test_rows_keep_keys_and_grade_by_table(self, song):
        build = build_song(song)
        rows, _pairing = _concept_rows(build, screen_count=len(song["sections"]))
        for row in rows:
            assert set(row) == _ROW_KEYS
            assert row["evidence"] is None or row["evidence"] in EVIDENCE_GRADES
            assert row["evidence"] == evidence_for_row(
                row["kind"], row["section"], row["trigger"], row["occurrence"]
            )
        # 첫·끝 안전 큐는 모든 곡에 있고 verified 다(REQ-068/069/071).
        assert rows[0]["kind"] == "safety" and rows[0]["evidence"] == "verified"
        assert rows[-1]["kind"] == "safety" and rows[-1]["evidence"] == "verified"

    def test_eight_songs_have_graded_rows(self):
        """배선이 살아 있는지 — 8곡 전체에 None 아닌 등급이 실제로 실린다."""
        graded = 0
        for song in _SONGS:
            rows, _ = _concept_rows(build_song(song), screen_count=len(song["sections"]))
            graded += sum(1 for row in rows if row["evidence"] is not None)
        assert graded > 0
