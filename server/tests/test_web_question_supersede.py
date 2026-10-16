"""답한 물음은 다시 가지 않고, 답 없는 물음은 재접속마다 정확히 한 장 — 채널 단위 시험.

실측 결함(2026-10-16, 실콘솔 전 과정): 곡 분석의 확인 카드가 답 없이 남으면 새 연결마다 다시
보내졌고, 새 분석이 서도 옛 카드는 거둬지지 않아 한 연결에 1~3장씩 쌓였다(``question-1~3``).
재접속은 :meth:`QuestionChannel.bind` 가 되살리므로 여기서 잰다. 연결 배선과 화면에서 카드가
닫히는 모습은 ``test_web_song_audio.py`` 의 재접속 시험이 본다.
"""

from __future__ import annotations

import threading
import time

from server.web.question import (
    SONG_CONFIRMATION_GROUP,
    SUPERSEDED,
    UNANSWERED,
    QuestionChannel,
    QuestionOption,
    QuestionRequest,
)


class _Screen:
    """화면 하나 — 어떤 물음이 어떤 순서로 도착했고 무엇이 거둬졌는지만 적는다."""

    def __init__(self) -> None:
        self.questions: list[str] = []
        self.withdrawn: list[str] = []

    def notify(self, request_id: str, request: QuestionRequest) -> None:
        self.questions.append(request_id)

    def withdraw(self, request_id: str) -> None:
        self.withdrawn.append(request_id)


class _Asker:
    """물음 하나를 작업 스레드에서 띄우고, 돌아온 답을 기다린다(분석 스레드의 자리)."""

    def __init__(
        self,
        channel: QuestionChannel,
        request: QuestionRequest,
        *,
        session_key: object,
        group: str | None = None,
    ) -> None:
        self.result: str | None = None
        self._thread = threading.Thread(
            target=self._run, args=(channel, request, session_key, group), daemon=True
        )
        self._thread.start()

    def _run(
        self,
        channel: QuestionChannel,
        request: QuestionRequest,
        session_key: object,
        group: str | None,
    ) -> None:
        self.result = channel.ask(request, session_key=session_key, group=group)

    def alive(self) -> bool:
        return self._thread.is_alive()

    def join(self) -> str:
        self._thread.join(timeout=5.0)
        assert not self._thread.is_alive(), "the asking thread is still blocked"
        assert self.result is not None
        return self.result


def _card(prompt: str) -> QuestionRequest:
    return QuestionRequest(prompt=prompt, options=(QuestionOption(label="BPM 130"),), multi=True)


def _wait_for_cards(screen: _Screen, count: int) -> None:
    deadline = time.monotonic() + 5.0
    while len(screen.questions) < count:
        assert time.monotonic() < deadline, f"only {len(screen.questions)} of {count} cards arrived"
        time.sleep(0.01)


class TestAnAnsweredQuestionIsNotReplayed:
    def test_a_new_connection_after_the_answer_gets_nothing(self) -> None:
        channel = QuestionChannel(timeout_seconds=5.0)
        first = _Screen()
        channel.bind(first.notify, session_key="old", withdraw=first.withdraw)
        asker = _Asker(channel, _card("구간과 BPM 을 확인해 주세요."), session_key="old")
        _wait_for_cards(first, 1)
        (request_id,) = first.questions

        assert channel.resolve(request_id, answer="BPM 130") is True
        assert asker.join() == "BPM 130"

        second = _Screen()
        channel.bind(second.notify, session_key="new", withdraw=second.withdraw)
        assert second.questions == []
        assert channel.has_pending(session_key="old") is False


class TestAnUnansweredQuestionComesBackOncePerConnection:
    def test_each_new_connection_gets_the_card_exactly_once(self) -> None:
        channel = QuestionChannel(timeout_seconds=5.0)
        first = _Screen()
        channel.bind(first.notify, session_key="a", withdraw=first.withdraw)
        asker = _Asker(channel, _card("구간과 BPM 을 확인해 주세요."), session_key="a")
        _wait_for_cards(first, 1)
        (request_id,) = first.questions

        second = _Screen()
        channel.bind(second.notify, session_key="b", withdraw=second.withdraw)
        third = _Screen()
        channel.bind(third.notify, session_key="c", withdraw=third.withdraw)
        assert second.questions == [request_id]
        assert third.questions == [request_id]

        channel.resolve(request_id, answer="BPM 130")
        assert asker.join() == "BPM 130"


class TestANewSongCardSupersedesTheOlderOne:
    def test_the_older_card_is_withdrawn_and_only_the_new_one_comes_back(self) -> None:
        channel = QuestionChannel(timeout_seconds=5.0)
        screen = _Screen()
        channel.bind(screen.notify, session_key="a", withdraw=screen.withdraw)
        older = _Asker(
            channel,
            _card("구간과 BPM 을 확인해 주세요."),
            session_key="a",
            group=SONG_CONFIRMATION_GROUP,
        )
        _wait_for_cards(screen, 1)
        (old_id,) = screen.questions

        newer = _Asker(
            channel,
            _card("구간과 BPM 을 확인해 주세요."),
            session_key="a",
            group=SONG_CONFIRMATION_GROUP,
        )
        _wait_for_cards(screen, 2)
        new_id = screen.questions[1]

        # 옛 분석은 미응답이 아니라 「대체됨」을 받는다 — 상태를 쓰지 않고 끝난다.
        assert older.join() == SUPERSEDED
        # 같은 화면의 옛 카드는 거둠 알림으로 닫힌다.
        assert screen.withdrawn == [old_id]
        # 거둬진 카드에 늦게 보낸 답은 이미 끝난 물음이라 거절된다.
        assert channel.resolve(old_id, answer="BPM 90") is False

        # 재접속은 새 카드 한 장만 되살린다.
        later = _Screen()
        channel.bind(later.notify, session_key="b", withdraw=later.withdraw)
        assert later.questions == [new_id]

        channel.resolve(new_id, answer="BPM 130")
        assert newer.join() == "BPM 130"


class TestTheSupersedingStaysInItsGroup:
    def test_an_ungrouped_question_is_left_alone_by_a_song_card(self) -> None:
        channel = QuestionChannel(timeout_seconds=5.0)
        screen = _Screen()
        channel.bind(screen.notify, session_key="a", withdraw=screen.withdraw)
        plain = _Asker(channel, _card("다른 물음"), session_key="a")
        _wait_for_cards(screen, 1)
        song = _Asker(
            channel,
            _card("구간과 BPM 을 확인해 주세요."),
            session_key="a",
            group=SONG_CONFIRMATION_GROUP,
        )
        _wait_for_cards(screen, 2)

        assert screen.withdrawn == []
        assert plain.alive()
        plain_id, song_id = screen.questions
        channel.resolve(plain_id, answer="예")
        channel.resolve(song_id, answer="BPM 130")
        assert plain.join() == "예"
        assert song.join() == "BPM 130"


class TestWithoutALiveScreenNothingIsSuperseded:
    def test_a_card_with_no_connection_does_not_withdraw_the_older_one(self) -> None:
        channel = QuestionChannel(timeout_seconds=5.0)
        screen = _Screen()
        channel.bind(screen.notify, session_key="a", withdraw=screen.withdraw)
        older = _Asker(
            channel,
            _card("구간과 BPM 을 확인해 주세요."),
            session_key="a",
            group=SONG_CONFIRMATION_GROUP,
        )
        _wait_for_cards(screen, 1)
        (old_id,) = screen.questions

        # 볼 사람이 없는 카드는 물음이 아니다 — 기다리지 않고, 옛 카드도 거두지 않는다.
        nobody = channel.ask(
            _card("구간과 BPM 을 확인해 주세요."),
            session_key="nobody",
            group=SONG_CONFIRMATION_GROUP,
        )
        assert nobody == UNANSWERED
        assert screen.withdrawn == []
        assert older.alive()

        channel.resolve(old_id, answer="BPM 130")
        assert older.join() == "BPM 130"
