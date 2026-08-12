"""사용자가 콘솔에서 고르는 동안 서버가 기다리다 이어받는가.

MVR도 GDTF도 없을 때의 갈래다. 콘솔 내장 라이브러리가 방대하므로(실물 화면:
``Generic`` 한 제조사에만 136종) 사용자가 ``Patch > Insert New Fixture``에서 고르는
것이 가장 빠르다. 이 파일이 지키는 것은 넷이다.

1. **선택을 감지한다.** 사용자가 "골랐어요"라고 다시 말하지 않아도 된다.
2. **판독 실패와 「변화 없음」을 가른다.** 못 읽은 것을 그대로라고 하면 서버가
   이미 끝난 일을 계속 기다린다.
3. **절단된 기준선을 가른다.** 절단 상태에서 잰 차이는 「사용자가 추가」와
   「가려져 있다가 보임」을 구별할 수 없다.
4. **사용자가 무엇을 고르든 받는다.** 도면이 ``Sharpy``라 적어도 실물이
   ``Sharpy X Frame``이면 사용자가 옳다 — 이름으로 되물어 막지 않는다.

payload 형태는 M8 라이브 세션에서 실측한 responder 응답을 그대로 쓴다
(``ok`` · ``node.childCount`` · ``children[].name`` · ``truncated``).
"""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from server.vwx.librarywatch import (
    ROUNDTRIP_MS,
    SHALLOW_POLL_ROUNDTRIPS,
    WATCH_ADDED,
    WATCH_IDLE,
    WATCH_TRUNCATED_BASELINE,
    WATCH_UNREADABLE,
    compare,
    read_snapshot,
    selection_prompt,
    wait_for_addition,
    watch_until_change,
)
from server.vwx.typemap import FIXTURE_TYPE_LIBRARY_ROOT

#: M8 라이브 세션 실측 기준선 — 이 쇼의 콘솔에 있던 타입 3종.
M8_TYPES = ("Robin MMX Spot", "FixtureType 2", "Robin LEDBeam 350")


class FakeConsole:
    """실측 payload 형태를 그대로 낸다."""

    def __init__(self, names, *, truncated: bool = False, declared: int | None = None):
        self.names = list(names)
        self.truncated = truncated
        self.declared = declared
        self.state_calls = 0
        self.property_calls = 0

    def query_state(self, path: str) -> Mapping[str, object]:
        self.state_calls += 1
        declared = self.declared if self.declared is not None else len(self.names)
        return {
            "ok": True,
            "path": path,
            "truncated": self.truncated,
            "node": {"childCount": declared},
            "children": [
                {"class": "FixtureType", "i": index + 1, "name": name}
                for index, name in enumerate(self.names)
            ],
        }

    def query_property(self, path: str, property_name: str) -> Mapping[str, object]:
        self.property_calls += 1
        return {"ok": False}


class DeadConsole:
    def query_state(self, path: str) -> Mapping[str, object]:
        return {"ok": False, "path": path, "error": "no response"}

    def query_property(self, path: str, property_name: str) -> Mapping[str, object]:
        return {"ok": False}


@pytest.fixture()
def console() -> FakeConsole:
    return FakeConsole(M8_TYPES)


class TestTheShallowRead:
    """폴링용 얕은 판독 — 왕복 하나."""

    def test_it_reads_the_names_and_the_declared_total(self, console: FakeConsole):
        snapshot = read_snapshot(console)
        assert snapshot.names == M8_TYPES
        assert snapshot.declared_count == 3
        assert snapshot.complete is True

    def test_it_costs_exactly_one_roundtrip(self, console: FakeConsole):
        """깊은 열거는 타입 수만큼 왕복이 든다 — 폴링에 쓸 수 없다."""
        read_snapshot(console)
        assert console.state_calls == SHALLOW_POLL_ROUNDTRIPS
        assert console.property_calls == 0

    def test_an_unreadable_console_is_not_an_empty_library(self):
        """[HARD] 못 읽은 것을 「비었다」로 읽으면 전 타입이 사라진 것으로 보인다."""
        snapshot = read_snapshot(DeadConsole())
        assert snapshot.readable is False
        assert snapshot.complete is False

    def test_a_truncated_snapshot_is_not_complete(self):
        console = FakeConsole(M8_TYPES, truncated=True)
        assert read_snapshot(console).complete is False

    def test_a_short_enumeration_is_not_complete(self):
        """선언 총계보다 적게 왔으면 전수가 아니다 — 절단 플래그가 없어도."""
        console = FakeConsole(M8_TYPES, declared=9)
        assert read_snapshot(console).complete is False

    def test_a_port_that_raises_is_a_failed_read_not_a_crash(self):
        """[HARD] 이 모듈은 예외를 밖으로 내지 않는다 — `reader.py`와 같은 규약.

        포트는 런타임에 무엇이든 될 수 있다. 던지는 포트에 터지면 대화 한 턴이
        통째로 죽는다. 대신 `readable=False`로 내고, `compare`가 그것을
        `unreadable`로 **보고**한다 — 조용히 「변화 없음」으로 읽지 않는 것이 핵심이다.
        """

        class Angry:
            def query_state(self, path: str):
                raise LookupError(f"unknown object path: {path}")

            def query_property(self, path: str, property_name: str):
                raise LookupError(path)

        snapshot = read_snapshot(Angry())
        assert snapshot.readable is False
        assert snapshot.complete is False
        assert snapshot.names == ()

    def test_that_failure_is_reported_and_not_read_as_no_change(self, console: FakeConsole):
        """[비공허] 위 판독이 「그대로다」로 읽히면 서버가 영영 기다린다."""

        class Angry:
            def query_state(self, path: str):
                raise RuntimeError("boom")

            def query_property(self, path: str, property_name: str):
                raise RuntimeError("boom")

        base = read_snapshot(console)
        assert compare(base, read_snapshot(Angry())).state == WATCH_UNREADABLE

    def test_rows_it_cannot_use_are_counted_not_dropped(self):
        """[HARD] 버린 것을 세지 않으면 선언 총계와의 차이를 절단으로 오인한다."""

        class Ragged(FakeConsole):
            def query_state(self, path: str) -> Mapping[str, object]:
                self.state_calls += 1
                return {
                    "ok": True,
                    "path": path,
                    "truncated": False,
                    "node": {"childCount": 4},
                    "children": [
                        {"class": "FixtureType", "i": 1, "name": "Robin MMX Spot"},
                        "이건 매핑이 아니다",
                        {"class": "FixtureType", "i": 3, "name": ""},
                        {"class": "FixtureType", "i": 4, "name": "Robin LEDBeam 350"},
                    ],
                }

        snapshot = read_snapshot(Ragged(()))
        assert snapshot.unusable_row_count == 2
        assert snapshot.names == ("Robin MMX Spot", "Robin LEDBeam 350")
        assert snapshot.complete is False

    def test_a_clean_snapshot_counts_nothing_discarded(self, console: FakeConsole):
        """[비공허] 정상 응답에서 폐기가 0이라야 위 시험이 무언가를 재는 것이다."""
        snapshot = read_snapshot(console)
        assert snapshot.unusable_row_count == 0
        assert snapshot.complete is True


class TestDetectingTheSelection:
    """사용자가 Select를 누른 것을 서버가 안다."""

    def test_no_change_reads_as_idle(self, console: FakeConsole):
        base = read_snapshot(console)
        assert compare(base, read_snapshot(console)).state == WATCH_IDLE

    def test_a_new_type_is_detected_and_named(self, console: FakeConsole):
        base = read_snapshot(console)
        console.names.append("Sharpy X Frame")
        result = compare(base, read_snapshot(console))
        assert result.state == WATCH_ADDED
        assert result.added == ("Sharpy X Frame",)

    def test_the_user_may_pick_a_different_name_than_we_asked(self, console: FakeConsole):
        """도면이 'Sharpy'라 해도 실물이 'Sharpy X Frame'이면 사용자가 옳다.

        이름으로 되물어 막지 않는다 — 대신 무엇이 들어왔는지 되돌려 보여 준다.
        """
        base = read_snapshot(console)
        console.names.append("Sharpy X Frame")
        result = compare(base, read_snapshot(console))
        assert result.state == WATCH_ADDED
        assert "Sharpy" not in result.added

    def test_several_picks_in_one_go_are_all_reported(self, console: FakeConsole):
        base = read_snapshot(console)
        console.names.extend(["A Type", "B Type"])
        result = compare(base, read_snapshot(console))
        assert set(result.added) == {"A Type", "B Type"}

    def test_a_removal_is_reported_too(self, console: FakeConsole):
        """사용자가 잘못 넣고 지웠을 수 있다 — 그것도 사실이다."""
        base = read_snapshot(console)
        console.names.remove("FixtureType 2")
        result = compare(base, read_snapshot(console))
        assert result.removed == ("FixtureType 2",)


class TestFailureIsNotSilence:
    """못 읽은 것을 「그대로다」라고 말하지 않는다."""

    def test_an_unreadable_poll_says_so(self, console: FakeConsole):
        base = read_snapshot(console)
        result = compare(base, read_snapshot(DeadConsole()))
        assert result.state == WATCH_UNREADABLE
        assert "관측 실패" in result.detail

    def test_it_does_not_claim_every_type_vanished(self, console: FakeConsole):
        """[HARD] 판독 실패를 차이로 계산하면 전 타입이 제거된 것으로 보고된다."""
        base = read_snapshot(console)
        result = compare(base, read_snapshot(DeadConsole()))
        assert result.removed == ()

    def test_a_truncated_baseline_refuses_to_judge(self):
        """절단 기준선에서는 「추가」와 「가려졌다 보임」을 구별할 수 없다."""
        console = FakeConsole(M8_TYPES, truncated=True)
        base = read_snapshot(console)
        console.truncated = False
        console.names.append("Sharpy X Frame")
        result = compare(base, read_snapshot(console))
        assert result.state == WATCH_TRUNCATED_BASELINE
        assert "구별할 수 없다" in result.detail

    def test_a_complete_baseline_does_judge(self, console: FakeConsole):
        """[비공허] 전수 기준선에서는 정상 판정한다 — 위 시험이 공허하지 않다."""
        base = read_snapshot(console)
        console.names.append("Sharpy X Frame")
        assert compare(base, read_snapshot(console)).state == WATCH_ADDED


class TestWaiting:
    """변화가 잡힐 때까지 본다."""

    def test_it_returns_as_soon_as_something_changes(self, console: FakeConsole):
        base = read_snapshot(console)
        console.state_calls = 0
        ticks = []

        def tick() -> None:
            ticks.append(len(ticks))
            if len(ticks) == 2:
                console.names.append("Sharpy X Frame")

        result = watch_until_change(console, base, attempts=10, sleep=tick)
        assert result.state == WATCH_ADDED
        assert console.state_calls == 3

    def test_exhausting_the_attempts_is_a_result_not_an_error(self, console: FakeConsole):
        """아직 안 골랐다는 것도 답이다 — 예외로 끝내지 않는다."""
        base = read_snapshot(console)
        result = watch_until_change(console, base, attempts=3)
        assert result.state == WATCH_IDLE

    def test_it_never_sleeps_before_the_first_look(self, console: FakeConsole):
        """첫 관측은 즉시 — 이미 골라 둔 사용자를 기다리게 하지 않는다."""
        base = read_snapshot(console)
        console.names.append("Sharpy X Frame")
        slept = []
        result = watch_until_change(console, base, attempts=5, sleep=lambda: slept.append(1))
        assert result.state == WATCH_ADDED
        assert slept == []


class TestThePromptTellsTheRealProcedure:
    """안내가 실제 콘솔 절차와 같은가."""

    def test_it_walks_the_documented_path(self):
        prompt = selection_prompt("Clay Paky Sharpy")
        joined = " ".join(prompt.steps)
        for landmark in ("Menu", "Patch", "Insert New Fixture", "Library", "Select"):
            assert landmark in joined

    def test_it_names_the_type_the_user_should_look_for(self):
        assert "Clay Paky Sharpy" in " ".join(selection_prompt("Clay Paky Sharpy").steps)

    def test_it_says_the_wizard_may_be_closed(self):
        """타입이 쇼에 들어오면 충분하다 — 마법사를 끝까지 밟게 하면 중복 패치가 난다."""
        assert "닫아도 된다" in " ".join(selection_prompt("X").steps)

    def test_it_states_the_polling_cost(self):
        note = selection_prompt("X", poll_seconds=2).poll_note
        assert FIXTURE_TYPE_LIBRARY_ROOT in note
        assert str(ROUNDTRIP_MS) in note or f"{ROUNDTRIP_MS:g}" in note

    def test_the_server_does_not_press_the_button_itself(self):
        """[HARD] 되돌릴 수 없는 쓰기 화면을 서버가 자동으로 열지 않는다.

        그 경로는 미검증이고(`U-21`), 반자동 원칙에도 어긋난다. 안내는 **사람이
        밟을 절차**로만 쓰인다 — 명령을 보내는 문구가 있으면 그 자체가 결함이다.
        """
        prompt = selection_prompt("X")
        assert all(not step.startswith("Cmd") for step in prompt.steps)


class TestWaitingForAPerson:
    """사람을 기다리는 자리 — **추가만이 멈출 이유다.**

    [round24 후속] 실측에서 `watch_until_change`로 사람을 기다렸다가 7.6초 만에
    끝났다. 「무엇이든 달라졌나」는 감시에는 맞지만 기다림에는 틀렸다 — 한 번
    못 읽었다고, 기준선이 절단됐다고, 무언가 지워졌다고 사용자가 고르기를
    그만둔 것은 아니다. 그때 모델은 답을 못 본 채 산문으로 다시 물었다.
    """

    def test_it_ends_when_the_type_arrives(self, console: FakeConsole):
        base = read_snapshot(console)
        calls = {"n": 0}

        def pick():
            calls["n"] += 1
            if calls["n"] == 2:
                console.names.append("Sharpy 250W Beam")

        result = wait_for_addition(console, base, attempts=6, sleep=pick)

        assert result.state == WATCH_ADDED
        assert result.added == ("Sharpy 250W Beam",)

    def test_a_failed_read_does_not_end_the_wait(self):
        # [HARD] 한 번 못 읽은 것을 「사용자가 안 골랐다」로 접으면, 실제로 고른
        # 사람을 두고 대화가 앞으로 못 간다 — 실측에서 일어난 그대로다.
        class FlakyConsole(FakeConsole):
            def query_state(self, path):
                self.state_calls += 1
                if self.state_calls == 2:
                    return {"ok": False, "path": path}
                if self.state_calls >= 4:
                    self.names = [*M8_TYPES, "Sharpy 250W Beam"]
                return super().query_state(path)

        console = FlakyConsole(M8_TYPES)
        base = read_snapshot(console)
        result = wait_for_addition(console, base, attempts=8, sleep=lambda: None)

        assert result.added == ("Sharpy 250W Beam",)

    def test_a_removal_does_not_end_the_wait(self):
        # 사용자가 딴 것을 지우는 동안에도 기다려야 한다.
        console = FakeConsole(M8_TYPES)
        base = read_snapshot(console)
        steps = iter(
            [
                lambda: console.names.remove("FixtureType 2"),
                lambda: console.names.append("Sharpy 250W Beam"),
            ]
        )

        def act():
            step = next(steps, None)
            if step:
                step()

        result = wait_for_addition(console, base, attempts=6, sleep=act)

        assert result.added == ("Sharpy 250W Beam",)

    def test_a_truncated_baseline_does_not_end_the_wait(self):
        # 절단은 기준선의 흠이지 사용자의 답이 아니다.
        console = FakeConsole(M8_TYPES, truncated=True, declared=99)
        base = read_snapshot(console)
        assert base.complete is False
        rounds = {"n": 0}

        def act():
            rounds["n"] += 1

        wait_for_addition(console, base, attempts=5, sleep=act)

        assert rounds["n"] == 4, "절단을 이유로 첫 관측에서 빠져나오면 안 된다"

    def test_running_out_reports_what_it_last_saw(self):
        # 소진을 조용히 「변화 없음」으로 덮으면 연결이 죽은 것을 놓친다.
        result = wait_for_addition(
            DeadConsole(),
            read_snapshot(FakeConsole(M8_TYPES)),
            attempts=3,
            sleep=lambda: None,
        )

        assert result.state == WATCH_UNREADABLE
        assert result.added == ()

    def test_nothing_happening_is_reported_as_idle(self, console: FakeConsole):
        result = wait_for_addition(console, read_snapshot(console), attempts=3, sleep=lambda: None)

        assert result.state == WATCH_IDLE
        assert result.added == ()

    def test_it_observes_once_per_attempt(self, console: FakeConsole):
        base = read_snapshot(console)
        before = console.state_calls

        wait_for_addition(console, base, attempts=5, sleep=lambda: None)

        assert console.state_calls - before == 5
