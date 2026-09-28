"""카드 t485 — 컨셉 패널 탭 1 인과 불릿(SPEC-LDDESIGN-001 AC-018 잔여, REQ-013·032·080).

원천은 인터뷰 Q1(컨셉) 기록 하나다. 워크시트 YAML 로더(``load_worksheet``)는 앱
경로에서 불리지 않으므로 원천이 될 수 없다(판정서 §2).

고정하는 것:

1. 감독이 실제로 준 글자만 원문으로 싣는다 — 직접 입력·제안 선택·요청 문장에서 읽은 값.
   요약·윤문 없이 바이트 그대로(REQ-032, ``render_concept_bullet``).
2. 빈 답으로 첫 제안이 자동 초안이 된 경우(``auto_draft``)와 기록이 없는 경우는
   원문이 아니다 — ``available: False`` + 사유. 자동 초안 값을 원문으로 보이면
   감독이 하지 않은 말을 감독 말로 표시하게 된다.
3. 런북 타임라인 페이로드에 ``concept_bullet`` 키로 실린다(추가만).
"""

from __future__ import annotations

from server.concept.session_bridge import CONCEPT_BULLET_AUTO_DRAFT_REASON, concept_bullet
from server.design.interview import (
    Q1_CONCEPT,
    Q2_PALETTE,
    SOURCE_AUTO_DRAFT,
    SOURCE_FREE_TEXT,
    SOURCE_OPTION,
    SOURCE_PRE_SPECIFIED,
    AnswerRecord,
    QuestionOption,
)
from server.design.song_cue_composer import compose_song_cue_bundle
from server.tests.test_song_timeline_concept_report_wiring import _plan, _section
from server.web.session import _song_timeline_payload

CAUSAL = "이 곡은 이별 노래다 → 그래서 주조색은 차가운 파랑\n→ 후렴에서만 흰색을 쓴다"


def _record(
    *,
    step: str = Q1_CONCEPT,
    source: str,
    value: object,
    free_text: str | None = None,
    confirmed: bool = True,
    choice: QuestionOption | None = None,
) -> AnswerRecord:
    return AnswerRecord(
        step=step,
        proposals=(),
        choice=choice,
        free_text=free_text,
        value=value,
        confirmed=confirmed,
        source=source,
    )


class TestConceptBulletSource:
    def test_free_text_is_carried_byte_for_byte(self) -> None:
        records = (_record(source=SOURCE_FREE_TEXT, value=CAUSAL, free_text=CAUSAL),)
        result = concept_bullet(records)
        assert result == {
            "available": True,
            "text": CAUSAL,
            "origin": SOURCE_FREE_TEXT,
            "origin_label": "인터뷰 Q1 — 직접 입력",
        }

    def test_free_text_wins_over_value_when_they_differ(self) -> None:
        # value 는 해석된 값, free_text 는 감독이 친 글자다. 원문은 뒤의 것.
        records = (_record(source=SOURCE_FREE_TEXT, value="parsed", free_text="감독이 친 글자"),)
        assert concept_bullet(records)["text"] == "감독이 친 글자"

    def test_chosen_option_is_the_label_the_director_picked(self) -> None:
        option = QuestionOption(label="몽환", description="", value="몽환")
        records = (_record(source=SOURCE_OPTION, value="몽환", choice=option),)
        result = concept_bullet(records)
        assert result["available"] is True
        assert result["text"] == "몽환"
        assert result["origin_label"] == "인터뷰 Q1 — 제안 중 선택"

    def test_pre_specified_names_the_request_sentence(self) -> None:
        records = (_record(source=SOURCE_PRE_SPECIFIED, value="빈티지", free_text="빈티지"),)
        result = concept_bullet(records)
        assert result["text"] == "빈티지"
        assert result["origin_label"] == "인터뷰 Q1 — 요청 문장에서 읽음"


class TestConceptBulletAbsent:
    def test_auto_draft_is_not_the_directors_words(self) -> None:
        option = QuestionOption(label="몽환", description="", value="몽환")
        records = (_record(source=SOURCE_AUTO_DRAFT, value="몽환", confirmed=False, choice=option),)
        result = concept_bullet(records)
        assert result == {"available": False, "reason": CONCEPT_BULLET_AUTO_DRAFT_REASON}
        assert "원문 아님" in CONCEPT_BULLET_AUTO_DRAFT_REASON

    def test_no_q1_record(self) -> None:
        records = (_record(step=Q2_PALETTE, source=SOURCE_FREE_TEXT, value="blue"),)
        assert concept_bullet(records) == {
            "available": False,
            "reason": "인터뷰 Q1(컨셉) 기록이 없다",
        }

    def test_blank_text_is_not_a_bullet(self) -> None:
        records = (_record(source=SOURCE_FREE_TEXT, value="   ", free_text="   "),)
        assert concept_bullet(records) == {
            "available": False,
            "reason": "Q1 컨셉 답이 비어 있다",
        }


def _payload(**kwargs: object) -> dict:
    plan = _plan(bpm=120.0, sections=(_section(1, "Intro", 0, 8_000),))
    return _song_timeline_payload(
        plan,
        compose_song_cue_bundle(plan),
        lifecycle="pending_approval",
        sequence_no=1,
        **kwargs,  # type: ignore[arg-type]
    )


class TestRunbookPayloadCarriesTheBullet:
    def test_payload_has_concept_bullet_from_records(self) -> None:
        records = (_record(source=SOURCE_FREE_TEXT, value=CAUSAL, free_text=CAUSAL),)
        assert _payload(interview_records=records)["concept_bullet"]["text"] == CAUSAL

    def test_payload_without_records_says_why(self) -> None:
        assert _payload()["concept_bullet"] == {
            "available": False,
            "reason": "인터뷰 Q1(컨셉) 기록이 없다",
        }


class TestRealSendSiteCarriesTheBullet:
    """호출 지점(``_song_send_timeline``)이 인터뷰 기록을 넘기는지 — 페이로드 함수를
    직접 부르는 위 시험은 이 배선이 빠져도 초록이다. 실제 세션을 인터뷰부터 끝까지
    돌려(콘솔은 가짜) 나간 타임라인 이벤트를 읽는다."""

    @staticmethod
    def _timeline(tmp_path, monkeypatch, answers: list[str]) -> dict:
        from server.tests import test_song_analysis_to_timeline as seam

        monkeypatch.setattr(seam, "_INTERVIEW_ANSWERS", answers)
        analysis = seam._confirmed((0, 24_000, 2), (24_000, 48_000, 3), (48_000, 72_000, 5))
        events = seam._timeline_events(seam._drive(tmp_path, seam._NO_SECTIONS, analysis))
        assert events, "타임라인 이벤트가 하나도 안 나갔다"
        return events[0]["timeline"]

    def test_director_q1_answer_reaches_the_runbook_timeline(self, tmp_path, monkeypatch) -> None:
        from server.tests.test_song_analysis_to_timeline import _INTERVIEW_ANSWERS

        timeline = self._timeline(tmp_path, monkeypatch, list(_INTERVIEW_ANSWERS))
        assert timeline["concept_bullet"]["available"] is True
        assert timeline["concept_bullet"]["text"] == _INTERVIEW_ANSWERS[0]

    def test_blank_q1_answer_reaches_the_timeline_as_not_verbatim(
        self, tmp_path, monkeypatch
    ) -> None:
        from server.tests.test_song_analysis_to_timeline import _INTERVIEW_ANSWERS

        answers = ["", *_INTERVIEW_ANSWERS[1:]]
        timeline = self._timeline(tmp_path, monkeypatch, answers)
        assert timeline["concept_bullet"] == {
            "available": False,
            "reason": CONCEPT_BULLET_AUTO_DRAFT_REASON,
        }
