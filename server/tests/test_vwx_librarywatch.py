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
