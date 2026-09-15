"""SPEC-COPILOT-SONGCONFIRM-001 M1 — 구간 답 판독과 확정 기록.

AC-SONGCONFIRM-001 ~ 006. 콘솔 접촉 0건: 가짜 콘솔(``FakeConsole``)과 미리 정한 답을
즉시 돌려주는 ``_AnsweringChannel`` 위에서만 돈다.

구간 판독은 **라벨 왕복 대조**다(plan.md §C D1). UI 가 서버가 만든 라벨을
``", "`` 로 이어 그대로 되돌려 주므로, 답을 항목으로 나눠 라벨과 **완전 일치**로
대조한다 — 부분문자열 포함은 대조가 아니다(AC-005 (d) 접두 충돌 대조군).

세션 층 시험은 DSP 를 돌리지 않는다. 3초 합성 트랙의 실제 분절 결과는 고정돼 있지
않으므로, ``server.web.session.analyze`` 를 네 구간 고정 결과로 바꿔 끼운다 —
여기서 재는 것은 분석기가 아니라 **답이 기록으로 흐르는 자리**다.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from server.audio.analyze import AnalysisResult, DCandidate
from server.web.question import (
    ANSWER_FREEFORM,
    UNANSWERED,
    SongSectionProposal,
    build_song_confirmation_card,
    parse_confirmed_sections,
)

from .test_web_song_audio import SMALL_WAV_B64, SMALL_WAV_SHA256, _AnsweringChannel, _session

# AC-001 의 제안 4건. 라벨은 카드 빌더(``question.py``)가 만든 것과 같아야 한다 —
# 아래 ``test_the_card_labels_are_the_ones_the_parser_matches`` 가 그 왕복을 고정한다.
_FOUR = (
    SongSectionProposal(start_ms=0, end_ms=15_000, d_level=1),
    SongSectionProposal(start_ms=15_000, end_ms=32_000, d_level=3),
    SongSectionProposal(start_ms=32_000, end_ms=36_000, d_level=5),
    SongSectionProposal(start_ms=36_000, end_ms=40_000, d_level=2),
)
_LABELS = ("0:00–0:15 · D1", "0:15–0:32 · D3", "0:32–0:36 · D5", "0:36–0:40 · D2")


def _joined(*labels: str) -> str:
    """UI ``joinChosenLabels`` 형식 — 체크된 라벨을 ``", "`` 로 잇는다."""
    return ", ".join(labels)


# =============================================================================
# 순수 파서 — parse_confirmed_sections
# =============================================================================


class TestTheCardLabelsRoundTrip:
    def test_the_card_labels_are_the_ones_the_parser_matches(self):
        card = build_song_confirmation_card(proposals=_FOUR, measured_bpm=120.0)
        assert tuple(option.label for option in card.options) == _LABELS


class TestRuleTwoAcceptsEverythingWhenNoLabelIsPresent:
    """규칙 ② — 라벨이 하나도 없으면 카드를 있는 그대로 받아들인 것이다."""

    @pytest.mark.parametrize("answer", ["확인", "BPM 130", "두 번째는 빼 줘", ""])
    def test_prose_and_bpm_overrides_accept_all_proposals(self, answer):
        assert parse_confirmed_sections(answer, proposals=_FOUR) == (True, True, True, True)

    @pytest.mark.parametrize("answer", ["9:59–9:59 · D9", "0:15", "D5"])
    def test_fragments_and_unknown_labels_are_not_a_match(self, answer):
        # AC-005 (a)(b)(c): 카드에 없는 라벨 · 시각 조각 · 등급 조각은 대조가 아니다.
        assert parse_confirmed_sections(answer, proposals=_FOUR) == (True, True, True, True)

    def test_the_positive_control_drops_to_one(self):
        # 양성 대조군 — 계기가 공허하지 않다.
        assert parse_confirmed_sections(_LABELS[2], proposals=_FOUR) == (False, False, True, False)


class TestRuleOneKeepsOnlyTheLabelsPresent:
    """규칙 ① — 라벨이 하나라도 있으면 있는 것만 채택한다."""

    def test_all_four_labels_accept_all(self):
        assert parse_confirmed_sections(_joined(*_LABELS), proposals=_FOUR) == (
            True,
            True,
            True,
            True,
        )

    def test_first_and_third_only(self):
        answer = _joined(_LABELS[0], _LABELS[2])
        assert parse_confirmed_sections(answer, proposals=_FOUR) == (True, False, True, False)

    def test_items_are_stripped_before_comparison(self):
        answer = f"  {_LABELS[1]} ,  {_LABELS[3]}  "
        assert parse_confirmed_sections(answer, proposals=_FOUR) == (False, True, False, True)

    def test_a_label_is_matched_whole_not_as_a_prefix(self):
        # AC-005 (d) 접두 충돌 카드 — ``_format_clock`` 은 분을 0 으로 채우지 않는다.
        # (실측: ``"1:00–1:15 · D1" in "11:00–11:15 · D1"`` 은 False 다 — 끝 시각이
        # 다르다. 그래서 이 카드만으로는 부분문자열 대조와 완전 일치가 갈리지
        # 않고, 갈리는 대조군은 아래 ``test_a_label_inside_a_longer_item_is_not_a_match`` 다.)
        proposals = (
            SongSectionProposal(start_ms=60_000, end_ms=75_000, d_level=1),
            SongSectionProposal(start_ms=660_000, end_ms=675_000, d_level=1),
        )
        card = build_song_confirmation_card(proposals=proposals)
        labels = tuple(option.label for option in card.options)
        assert labels == ("1:00–1:15 · D1", "11:00–11:15 · D1")
        verdict = parse_confirmed_sections("11:00–11:15 · D1", proposals=proposals)
        assert verdict == (False, True)
        assert sum(verdict) == 1

    def test_a_label_inside_a_longer_item_is_not_a_match(self):
        # 완전 일치 ↔ 부분문자열 포함을 실제로 가르는 대조군. 항목 하나 안에 라벨이
        # 통째로 들어 있어도 항목이 라벨과 ``==`` 가 아니면 대조가 아니다 — 부분문자열
        # 대조라면 (True, False, True, False), 완전 일치라면 규칙 ② 로 전부 채택이다.
        answer = f"{_LABELS[0]} 말고 {_LABELS[2]} 로"
        assert parse_confirmed_sections(answer, proposals=_FOUR) == (True, True, True, True)
        answer = f"{_LABELS[0]} (확인)"
        assert parse_confirmed_sections(answer, proposals=_FOUR) == (True, True, True, True)

    def test_duplicate_labels_share_one_verdict(self):
        # B1/W1 — 같은 초·같은 D 등급인 두 제안은 같은 라벨을 갖고 같은 판정을 받는다.
        proposals = (
            SongSectionProposal(start_ms=0, end_ms=15_000, d_level=1),
            SongSectionProposal(start_ms=200, end_ms=15_400, d_level=1),
            SongSectionProposal(start_ms=15_400, end_ms=32_000, d_level=3),
        )
        card = build_song_confirmation_card(proposals=proposals)
        assert card.options[0].label == card.options[1].label
        assert parse_confirmed_sections(card.options[0].label, proposals=proposals) == (
            True,
            True,
            False,
        )


class TestRuleThreeGivesNoVerdict:
    """규칙 ③ — 미응답 · 자유입력 표식 · 문자열 아님은 판정 없음."""

    @pytest.mark.parametrize("answer", [UNANSWERED, ANSWER_FREEFORM, None, 130, ["0:00"]])
    def test_no_verdict(self, answer):
        assert parse_confirmed_sections(answer, proposals=_FOUR) is None


class TestTheParserNeverInventsSections:
    def test_the_verdict_has_exactly_one_entry_per_proposal(self):
        for answer in ("확인", _LABELS[0], _joined(*_LABELS), "9:59–9:59 · D9"):
            verdict = parse_confirmed_sections(answer, proposals=_FOUR)
            assert verdict is not None
            assert len(verdict) == len(_FOUR)


# =============================================================================
# 세션 층 — 기록 생성 · 무기록 · 무효화
# =============================================================================


def _fixed_analysis(monkeypatch) -> None:
    """``analyze`` 를 네 구간 고정 결과로 바꿔 끼운다 — DSP 가 아니라 배관을 잰다."""

    def fake_analyze(_audio_bytes: bytes) -> AnalysisResult:
        return AnalysisResult(
            bpm=129.199,
            bpm_confidence=0.9,
            boundaries_ms=(0, 15_000, 32_000, 36_000, 40_000),
            onsets_ms=(),
            rms_curve=(),
            d_candidates=tuple(
                DCandidate(start_ms=p.start_ms, end_ms=p.end_ms, d_level=p.d_level) for p in _FOUR
            ),
        )

    monkeypatch.setattr("server.web.session.analyze", fake_analyze)


def _analysed(tmp_path, monkeypatch, answer: str, events: list[dict] | None = None):
    _fixed_analysis(monkeypatch)
    channel = _AnsweringChannel(answer)
    session = _session(tmp_path, events, question_channel=channel)
    session.upload_song_audio("track.wav", "audio/wav", SMALL_WAV_B64)
    session.analyse_song_audio()
    return session, channel


class TestAcceptingTheCardRecordsEverySection:
    """AC-SONGCONFIRM-001 ↔ REQ-001 · 002 · 003 ② · 006."""

    def test_the_record_holds_identity_bpm_and_all_four_sections(self, tmp_path, monkeypatch):
        session, channel = _analysed(tmp_path, monkeypatch, _joined(*_LABELS))
        assert tuple(o.label for o in channel.cards[0].options) == _LABELS
        record = session.song_analysis
        assert record is not None
        assert record.source_sha256 == SMALL_WAV_SHA256
        assert record.source_file_name == "track.wav"
        # W5 — 값이 아니라 형식만 단언한다.
        assert datetime.fromisoformat(record.confirmed_at).tzinfo is not None
        assert len(record.sections) == 4
        assert all(section.selected is True for section in record.sections)
        assert len(record.accepted) == 4
        assert record.dropped_count == 0
        for index, (section, proposal, label) in enumerate(
            zip(record.sections, _FOUR, _LABELS, strict=True)
        ):
            assert section.index == index
            assert section.label == label
            assert section.start_ms == proposal.start_ms
            assert section.end_ms == proposal.end_ms
            assert section.d_level == proposal.d_level
        # REQ-006 — 두 정본이 생기지 않는다.
        assert record.bpm is session.song_bpm
        assert record.bpm.bpm == pytest.approx(129.199)

    def test_a_plain_acknowledgement_also_accepts_all(self, tmp_path, monkeypatch):
        session, _channel = _analysed(tmp_path, monkeypatch, "확인")
        assert session.song_analysis is not None
        assert len(session.song_analysis.accepted) == 4


class TestUncheckedSectionsAreDroppedButKept:
    """AC-SONGCONFIRM-002 ↔ REQ-001 · 003 ①."""

    def test_first_and_third_are_accepted_and_the_others_stay_in_the_record(
        self, tmp_path, monkeypatch
    ):
        session, _channel = _analysed(tmp_path, monkeypatch, _joined(_LABELS[0], _LABELS[2]))
        record = session.song_analysis
        assert record is not None
        assert [s.selected for s in record.sections] == [True, False, True, False]
        assert tuple(s.index for s in record.accepted) == (0, 2)
        assert record.dropped_count == 2
        assert len(record.sections) == 4


class TestATypedBpmKeepsTheCardSections:
    """AC-SONGCONFIRM-003 ↔ REQ-003 ② · 004."""

    def test_bpm_override_accepts_all_sections(self, tmp_path, monkeypatch):
        session, _channel = _analysed(tmp_path, monkeypatch, "BPM 130")
        assert session.song_bpm.bpm == 130.0
        assert len(session.song_analysis.accepted) == 4
        assert session.song_analysis.dropped_count == 0
        assert session.song_analysis.bpm is session.song_bpm

    def test_prose_is_not_a_section_edit(self, tmp_path, monkeypatch):
        # 대조군 — 산문은 구간 편집이 아니다(REQ-004).
        session, _channel = _analysed(tmp_path, monkeypatch, "두 번째는 빼 줘")
        assert len(session.song_analysis.accepted) == 4
        assert session.song_analysis.dropped_count == 0


class TestNoAnswerMeansNoRecord:
    """AC-SONGCONFIRM-004 [부정 대조군] ↔ REQ-002."""

    @pytest.mark.parametrize("answer", [UNANSWERED, ANSWER_FREEFORM])
    def test_no_record_and_the_default_bpm_stands(self, tmp_path, monkeypatch, answer):
        session, _channel = _analysed(tmp_path, monkeypatch, answer)
        assert session.song_analysis is None
        assert session.song_bpm.source == "default"
        assert session.song_bpm.bpm is None


class TestLabelsAreMatchedWholeThroughTheSession:
    """AC-SONGCONFIRM-005 — 파서 규칙이 세션 층에서도 그대로다."""

    @pytest.mark.parametrize("answer", ["9:59–9:59 · D9", "0:15", "D5"])
    def test_fragments_accept_everything_and_invent_nothing(self, tmp_path, monkeypatch, answer):
        session, _channel = _analysed(tmp_path, monkeypatch, answer)
        record = session.song_analysis
        assert len(record.accepted) == 4
        assert not any("9:59" in section.label for section in record.sections)

    def test_one_real_label_drops_to_one(self, tmp_path, monkeypatch):
        session, _channel = _analysed(tmp_path, monkeypatch, _LABELS[1])
        assert len(session.song_analysis.accepted) == 1
        assert session.song_analysis.accepted[0].index == 1


class TestANewUploadInvalidatesTheRecord:
    """AC-SONGCONFIRM-006 ↔ REQ-005."""

    def test_the_second_upload_clears_the_record_and_says_so(self, tmp_path, monkeypatch):
        events: list[dict] = []
        session, _channel = _analysed(tmp_path, monkeypatch, "확인", events)
        assert session.song_analysis is not None
        event = session.upload_song_audio("other.wav", "audio/wav", SMALL_WAV_B64)
        assert session.song_analysis is None
        assert "이전 분석 확정" in event["message"]
        assert "무효" in event["message"]

    def test_the_first_upload_notice_is_byte_identical_to_today(self, tmp_path):
        # 대조군 — 기록이 없던 세션의 업로드 고지는 오늘 문면 그대로다.
        session = _session(tmp_path)
        event = session.upload_song_audio("track.wav", "audio/wav", SMALL_WAV_B64)
        n = len(__import__("base64").b64decode(SMALL_WAV_B64))
        assert event["message"] == (
            f"'track.wav' 첨부됨 — 오디오 · sha256 {SMALL_WAV_SHA256} · {n}바이트. "
            "아직 분석한 것은 없습니다 — 무엇을 할지 말씀해 주세요."
        )
        assert "무효" not in event["message"]


# =============================================================================
# t414 — 배수 정정은 구간 확정을 무효로 한다
# =============================================================================


def _analysed_event(tmp_path, monkeypatch, answer: str):
    """``_analysed`` 와 같지만 분석 고지 이벤트도 함께 돌려준다."""
    _fixed_analysis(monkeypatch)
    channel = _AnsweringChannel(answer)
    session = _session(tmp_path, question_channel=channel)
    session.upload_song_audio("track.wav", "audio/wav", SMALL_WAV_B64)
    event = session.analyse_song_audio()
    return session, event


class TestAnOctaveBpmCorrectionVoidsTheSections:
    """t414 — 배수 정정은 마디 길이를 두 배로 바꾼다.

    카드의 구간 경계는 **측정 BPM 의 4마디 하한**이 만든 것이다(`analyze._min_segment_ms`).
    BPM 이 절반으로 정정되면 같은 경계가 실제로는 2마디이므로, 그 구간표는 정정된
    BPM 의 것이 아니다. 실측 근거(2026-09-14, 감독 판정 정답지): Morning.mp3 앱
    117.45 → 진짜 ≈58.7 에서 최소 구간이 4.02마디 → 2.01마디로 읽힌다.

    재계산은 하지 않는다 — REQ-SONGCONFIRM-004 가 카드에 없던 구간을 만드는 것을
    금지한다. 대신 확정을 무효로 하고 다시 분석해 달라고 **말한다**.
    """

    def test_half_bpm_voids_the_record_and_says_so(self, tmp_path, monkeypatch):
        # 129.199 의 절반. BPM 정정 자체는 살아남는다.
        session, event = _analysed_event(tmp_path, monkeypatch, "BPM 64.6")
        assert session.song_bpm.bpm == 64.6
        assert session.song_analysis is None
        assert "무효" in event["message"]
        assert "다시 분석" in event["message"]

    def test_double_bpm_voids_the_record_too(self, tmp_path, monkeypatch):
        session, event = _analysed_event(tmp_path, monkeypatch, "BPM 258.4")
        assert session.song_bpm.bpm == 258.4
        assert session.song_analysis is None
        assert "무효" in event["message"]

    def test_a_nearby_bpm_is_not_an_octave_and_keeps_the_record(self, tmp_path, monkeypatch):
        # 음성 대조군 — 배수가 아닌 정정은 오늘 그대로다(AC-SONGCONFIRM-003 유지).
        session, event = _analysed_event(tmp_path, monkeypatch, "BPM 130")
        assert session.song_bpm.bpm == 130.0
        assert session.song_analysis is not None
        assert len(session.song_analysis.accepted) == 4
        assert "무효" not in event["message"]

    def test_accepting_the_card_keeps_the_record(self, tmp_path, monkeypatch):
        # 양성 대조군 — 계기가 공허하지 않다(정정이 없으면 기록이 남는다).
        session, event = _analysed_event(tmp_path, monkeypatch, "확인")
        assert session.song_analysis is not None
        assert "무효" not in event["message"]
