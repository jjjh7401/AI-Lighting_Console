"""카드 t491 — 한 쇼(세션) 안에서 연속 곡이 앞 곡과 다른 룩으로 열린다.

감독 결정(2026-10-12): 「같은 답을 준 연속 곡도 앱이 스스로 앞 곡과 다른 룩으로
연다」. t486 이 지운 ``SongLookMemory`` 는 ``build_toolset`` 이 안 읽는 죽은
배선이었다 — 그래서 여기 시험의 중심은 순수 함수가 아니라 **대화 길**
(``run_instruction`` → ``_song_compose`` → ``compose_song_cue_bundle``)에서 실제로
효과가 나는지다.

고정하는 것:
- 같은 세션의 둘째 곡은 첫 곡과 다른 첫 큐 룩으로 열린다(같은 답, 같은 구간).
- 새 세션의 같은 곡은 첫 곡과 같다 — 효과는 세션 기억에서 온다(기억 범위 = 한 쇼).
- 「앞 곡 룩 허용」으로 이 곡만 끄면 감독 답 그대로 연다(기본값이지 강제 아님).
- 저장되지 않은 곡(승인 없음)은 기억에 들어가지 않는다.
- 고르기 규칙: 안 쓴 룩 > 가장 오래전에 쓴 룩(멈추지 않음) > 재사용 적음 > 작은 오프셋.
- 오프셋 0 은 오늘과 바이트 동일한 계획을 낸다.
"""

from __future__ import annotations

from server.design.song_look_memory import choose_look_offset
from server.web.question import ConfirmedSongAnalysis

from .test_runner_self_correction import ScriptedProvider
from .test_song_analysis_to_timeline import _INTERVIEW_ANSWERS, _confirmed
from .test_web_session import TestSongDesignInterviewSession as _Harness
from .test_web_session import _session

_SPANS = ((0, 20_000, 2), (20_000, 40_000, 3), (40_000, 60_000, 4), (60_000, 80_000, 5))


def _brief(sequence_no: int) -> str:
    # 같은 세션의 곡끼리 시퀀스·타임코드가 부딪치지 않게 곡마다 번호를 비운다
    # (하네스는 저장 뒤 Timecodes/7 을 점유로 답한다 — 번호 충돌은 이 시험의
    # 질문이 아니다).
    return f"디자인 큐 시트, 시퀀스 {sequence_no}, 프리셋 21번부터, 타임코드 {sequence_no - 103}"


def _new(tmp_path):
    harness = _Harness()
    session, _console, _audit, sent, _ = _session(tmp_path, ScriptedProvider([]))
    session._registry = harness._registry([])
    return harness, session, sent


def _run(harness, session, analysis: ConfirmedSongAnalysis, sequence_no: int, *extra: str):
    """한 곡을 인터뷰 → 리뷰 승인까지 돌린다. ``extra`` 는 승인 전 계획 수정 턴."""
    session._song_analysis = analysis
    if extra:
        session._question_channel = harness._Channel(list(_INTERVIEW_ANSWERS))
        session.run_instruction(_brief(sequence_no))
        for turn in extra[:-1]:
            session.run_instruction(turn)
        session._question_channel = harness._Channel(["승인"])
        return session.run_instruction(extra[-1])
    session._question_channel = harness._Channel([*_INTERVIEW_ANSWERS, "승인"])
    return session.run_instruction(_brief(sequence_no))


def _opening(session) -> tuple:
    return session._song_look_history[-1][0]


class TestConversationPath:
    def test_second_song_in_the_same_show_opens_with_a_different_look(self, tmp_path):
        harness, session, _ = _new(tmp_path)
        analysis = _confirmed(*_SPANS)

        _run(harness, session, analysis, 110)
        first = _opening(session)
        _run(harness, session, analysis, 111)

        assert len(session._song_look_history) == 2, "저장된 두 곡이 모두 기억돼야 한다"
        assert _opening(session) != first, (
            f"같은 답 같은 구간의 둘째 곡이 첫 곡과 같은 룩으로 열렸다: {first}"
        )

    def test_a_fresh_show_has_no_memory_so_the_same_song_opens_the_same(self, tmp_path):
        harness, session, _ = _new(tmp_path / "a")
        analysis = _confirmed(*_SPANS)
        _run(harness, session, analysis, 110)
        first = _opening(session)

        harness_b, session_b, _ = _new(tmp_path / "b")
        _run(harness_b, session_b, analysis, 110)

        assert _opening(session_b) == first

    def test_the_director_can_turn_it_off_for_one_song(self, tmp_path):
        harness, session, _ = _new(tmp_path)
        analysis = _confirmed(*_SPANS)
        _run(harness, session, analysis, 110)
        first = _opening(session)

        result = _run(harness, session, analysis, 111, "앞 곡 룩 허용")

        assert "앞 곡 룩 허용" in result["text"]
        assert len(session._song_look_history) == 2
        assert _opening(session) == first, "끈 곡은 감독 답 그대로(오프셋 0) 열려야 한다"

    def test_the_review_card_tells_the_director_what_changed(self, tmp_path):
        harness, session, _ = _new(tmp_path)
        analysis = _confirmed(*_SPANS)
        _run(harness, session, analysis, 110)

        result = _run(harness, session, analysis, 111)

        assert "앞 곡 룩 허용" in result["text"]

    def test_an_unapproved_song_is_not_remembered(self, tmp_path):
        harness, session, _ = _new(tmp_path)
        session._song_analysis = _confirmed(*_SPANS)
        session._question_channel = harness._Channel(list(_INTERVIEW_ANSWERS))

        session.run_instruction(_brief(110))

        assert session._song_look_history == []


_A = ("Ring In", ("블루", "cyan"))
_B = ("Home", ("cyan", "블루"))
_C = ("Wall", ("블루", "cyan"))


class TestChooseLookOffset:
    def test_no_memory_keeps_the_director_answer(self):
        assert choose_look_offset([(_A,), (_B,)], []) == 0

    def test_an_unused_opening_wins(self):
        assert choose_look_offset([(_A,), (_B,)], [(_A,)]) == 1

    def test_when_all_are_used_the_oldest_wins_instead_of_stopping(self):
        history = [(_B,), (_A,)]
        assert choose_look_offset([(_A,), (_B,)], history) == 1

    def test_a_look_seen_anywhere_in_a_song_counts_as_used(self):
        history = [(_C, _B)]
        assert choose_look_offset([(_B,), (_A,)], history) == 1

    def test_ties_go_to_less_reuse_of_the_previous_song(self):
        history = [(_C, _B)]
        assert choose_look_offset([(_A, _B), (_A, _A)], history) == 1

    def test_full_ties_go_to_the_smaller_offset(self):
        assert choose_look_offset([(_B,), (_C,)], [(_A,)]) == 0


class TestOffsetZeroIsToday:
    def test_offset_zero_plan_is_byte_identical(self, tmp_path):
        harness, session, _ = _new(tmp_path)
        session._song_analysis = _confirmed(*_SPANS)
        session._question_channel = harness._Channel(list(_INTERVIEW_ANSWERS))
        session.run_instruction(_brief(110))
        state = session._pending_song_plan
        assert state is not None

        default_plan, _ = session._song_compose_at(state, 0)
        state.avoid_previous_looks = False
        off_plan, _ = session._song_compose(state)

        assert off_plan == default_plan
        assert state.look_offset == 0
