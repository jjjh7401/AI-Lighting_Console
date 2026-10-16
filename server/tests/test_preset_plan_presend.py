"""SPEC-LDRHYTHM-001 stage 2 — 연출 프리셋 계획 카드: 채워진 번호는 빼고 다시 승인받는다.

카드는 프리셋 수십 개를 한 번에 올린다. 승인 창이 떠 있는 사이 콘솔에서 한 번호가 채워졌거나 그
풀을 다시 못 읽으면, 승인 직후 게이트가 송신 직전 재확인(``BatchRisk.recheck``, 카드 t598)으로
묶음 전체를 0줄로 막는다. 그러면 걸린 프리셋만 뺀 나머지를 **새 승인 카드**로 한 번 더 올린다 —
감독의 승인은 항상 실제로 나가는 줄에 대한 것이다(승인된 카드에서 줄을 덜어 보내지 않는다). 한
번 누르면 승인 카드는 두 장까지이고, 두 번째도 막히거나 거절되면 아무것도 보내지 않는다. 칸 참조 ·
색 · 이름 기록은 실제로 보낸 카드의 프리셋 몫만 적는다. 콘솔 접촉 0건 — 가짜 콘솔
(``FakeConsole``)과 가짜 승인만 쓴다.

두 층: ① 몸체가 기운 장비의 보류 사유(순수 함수) ② 세션의 승인 카드(가짜 콘솔).
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from server.design.beat_grid import check_evidence_approval
from server.design.beat_grid_position_presets import (
    POSITION_COORDS_UNREAD,
    POSITION_UNAIMABLE,
    PointingFrames,
)
from server.design.preset_plan import save_commands
from server.design.send_approval import build_write_approval_batch
from server.web.session import SongTimelineStore

from .test_new_preset_dialog_t589 import ScriptedApproval
from .test_preset_plan import (
    _COLOR_CHILDREN,
    _DIMMER_CHILDREN,
    _EXPECTED_SAVE,
    _POSITION_CHILDREN,
    _cue_of,
    _pool_children_payload,
    _preset,
    _real_channel_session,
)
from .test_preset_plan_store_all import (
    _COLOR_NUMBERS,
    _FLOOR_NUMBERS,
    _POSITIONS,
    _store_session,
    _with_stores,
)
from .test_safety_gate import FakeConsole

_POOLS = "DataPool/PresetPools"
#: 계획이 저장하는 디머 프리셋 번호 — 풀 1 의 빈 번호(1~7 사용)에서 앞에서부터 고른다.
_DIMMER_NUMBERS = ("1.8", "1.9", "1.10", "1.11", "1.12")
#: 카드 하나가 싣는 프리셋 열한 개(디머 5 · 색 4 · 위치 2)의 번호.
_EVERY_NUMBER = (*_DIMMER_NUMBERS, *_COLOR_NUMBERS.values(), *_FLOOR_NUMBERS.values())
#: 풀 번호 → 가짜 콘솔이 처음 쥔 슬롯. 승인 창 사이 채워진 번호는 여기에 더해 다시 만든다.
_BASE_POOLS = {1: _DIMMER_CHILDREN, 2: _POSITION_CHILDREN, 4: _COLOR_CHILDREN}
#: 막힌 것이 없을 때 사유 — 예전부터 같은 문장이다(막은 프리셋이 없으면 바뀌지 않는다).
_PLAIN_REASON = "연출 프리셋 11개(디머 5 · 색 4 · 위치 2)를 저장하고 칸에 번호를 적었습니다."
#: 막힌 것이 없는데 카드가 실행되지 않았을 때(승인 거절 등) 사유 — 예전부터 같은 문장이다.
_GENERIC_FAILURE = (
    "LOVE ATTACK 프리셋 저장이 실행되지 않았습니다(승인 거절·게이트 차단·"
    "콘솔 무응답 중 하나). 격자는 그대로입니다."
)


# == ① 몸체가 기운 장비의 보류 사유 =================================================


class TestTiltedFixtureReason:
    def _tilted(self, *fids: int):
        positions = {fid: p for fid, p in _POSITIONS.items() if fid not in fids}
        return PointingFrames(positions=positions, rotz={}, rotation_skipped=fids)

    def test_the_reader_drops_a_tilted_fixture_so_the_reason_names_the_tilt(self) -> None:
        # 실기 판독은 몸체가 기운 장비를 좌표 표에서 뺀다 — 예전에는 「좌표를 못 읽음」이라 적혔다.
        _grid, plan = _with_stores(frames=self._tilted(201))

        up = _preset(plan, "FLOOR MOVER-U")
        assert up.ready is False and up.store is None
        assert POSITION_UNAIMABLE in up.hold
        assert "FID 201" in up.hold
        assert "몸체 기울임" in up.hold and "Rotx/Roty" in up.hold
        assert POSITION_COORDS_UNREAD not in up.hold
        assert "Store Preset 2.31" not in "\n".join(save_commands(plan))

    def test_only_the_group_with_the_tilted_fixture_is_held(self) -> None:
        _grid, plan = _with_stores(frames=self._tilted(201))
        assert _preset(plan, "FLOOR MOVER-D").ready is True
        assert any(line.startswith("FLOOR MOVER-U") for line in plan.unresolved)

    def test_every_tilted_fixture_of_the_group_is_named(self) -> None:
        _grid, plan = _with_stores(frames=self._tilted(201, 202))
        assert "FID 201, 202" in _preset(plan, "FLOOR MOVER-U").hold

    def test_a_fixture_that_is_really_unread_still_says_unread(self) -> None:
        partial = PointingFrames(
            positions={fid: p for fid, p in _POSITIONS.items() if fid != 202},
            rotz={},
            rotation_skipped=(),
        )
        _grid, plan = _with_stores(frames=partial)
        assert _preset(plan, "FLOOR MOVER-U").hold == POSITION_COORDS_UNREAD


# == ② 세션의 승인 카드 (가짜 콘솔) ==================================================

_Hook = Callable[[FakeConsole], None]


def _fill(console: FakeConsole, *numbers: str) -> None:
    """승인 창이 떠 있는 사이 다른 사람이 콘솔에서 ``numbers``(``"4.34"`` 꼴)를 채운 것과 같게
    만든다. 번호가 든 풀만 다시 쓰고, 앞서 채워진 풀은 그대로 둔다."""
    for pool_no, base in _BASE_POOLS.items():
        extra = {
            int(number.partition(".")[2]): "SOMEONE ELSE"
            for number in numbers
            if number.startswith(f"{pool_no}.")
        }
        if extra:
            console.state_tree[f"{_POOLS}/{pool_no}"] = _pool_children_payload({**base, **extra})


def _fill_sky(console: FakeConsole) -> None:
    _fill(console, "4.34")


def _fill_every_number(console: FakeConsole) -> None:
    _fill(console, *_EVERY_NUMBER)


def _drop_color_pool(console: FakeConsole) -> None:
    del console.state_tree[f"{_POOLS}/4"]


@dataclass
class _Run:
    """카드 한 번 누름의 결과와, 승인 요청이 올 때마다 남긴 관측."""

    event: dict
    console: FakeConsole
    approval: ScriptedApproval
    store: SongTimelineStore
    before: dict  # 카드를 누르기 전 격자
    reads: list[str]  # 콘솔을 읽은 경로 전부(시간 순)
    sent_at: list[list[str]]  # 승인 요청마다, 그때까지 콘솔에 나간 줄
    reads_at: list[int]  # 승인 요청마다, 그때까지 읽은 횟수

    @property
    def cards(self) -> list[list[str]]:
        """감독 앞에 올라온 카드들의 줄 — 올라온 순서."""
        return [list(request.commands) for request in self.approval.requests]


def _run_card(
    tmp_path,
    monkeypatch,
    *,
    decisions: Sequence[bool],
    during: Sequence[_Hook] = (),
    setup: _Hook | None = None,
) -> _Run:
    """프리셋 계획 카드를 가짜로 승인한다. 승인 요청이 올 때마다 ``during[n]`` (n 은 0부터 센 카드
    순번)이 먼저 콘솔을 바꾼다 — 카드가 떠 있는 사이 누가 콘솔에서 그 번호를 쓴 것과 같다.
    ``setup`` 은 누르기 전에 콘솔을 한 번 손본다."""
    session, console, approval, store = _store_session(tmp_path, monkeypatch, decisions=decisions)
    if setup is not None:
        setup(console)
    before = copy.deepcopy(store.latest["beat_grid"])
    reads: list[str] = []
    sent_at: list[list[str]] = []
    reads_at: list[int] = []
    query = console.query_state

    def counted(path, *args, **kwargs):
        reads.append(path)
        return query(path, *args, **kwargs)

    console.query_state = counted
    original = approval.request_approval

    def request_approval(request):
        n = len(approval.requests)  # 이 요청이 쌓이기 전 개수 = 이번 카드의 순번
        sent_at.append(list(console.executed))
        reads_at.append(len(reads))
        if n < len(during):
            during[n](console)
        return original(request)

    approval.request_approval = request_approval
    event = session.beat_grid_preset_plan()
    return _Run(event, console, approval, store, before, reads, sent_at, reads_at)


def _block_of(card: list[str], number: str) -> tuple[int, int]:
    """카드에서 번호 ``number`` 프리셋의 묶음 범위 — 앞 ClearAll 다음 줄부터 뒤 ClearAll 까지.
    프로덕션 코드를 쓰지 않고 카드 문면에서 따로 구한다."""
    store_at = card.index(f"Store Preset {number}")
    start = max(i for i in range(store_at) if card[i] == "ClearAll") + 1
    end = store_at + card[store_at:].index("ClearAll") + 1
    return start, end


def _without(card: list[str], *numbers: str) -> list[str]:
    """카드에서 ``numbers`` 프리셋의 묶음을 뺀 줄 — 남은 줄은 카드 순서 그대로다."""
    spans = [_block_of(card, number) for number in numbers]
    return [line for i, line in enumerate(card) if not any(s <= i < e for s, e in spans)]


def _declared(request) -> str:
    """카드에 실린 사유 한 줄 — 호출자가 선언한 「연출 프리셋 저장 — …」."""
    reasons = {reason for item in request.items for reason in item.risk_reasons}
    (declared,) = [reason for reason in reasons if reason.startswith("연출 프리셋 저장 — ")]
    return declared


class TestFilledSlotDuringApproval:
    def test_the_second_card_is_the_first_minus_the_filled_block_and_only_it_is_sent(
        self, tmp_path, monkeypatch
    ) -> None:
        run = _run_card(tmp_path, monkeypatch, decisions=(True, True), during=[_fill_sky])

        assert len(run.approval.requests) == 2  # 카드는 두 장이다
        first, second = run.cards
        start, end = _block_of(first, "4.34")
        assert first[start:end][-3:-1] == ["Store Preset 4.34", "Label Preset 4.34 'SKY'"]
        assert first[end - 1] == "ClearAll"
        # 두 번째 카드는 첫 카드에서 4.34 묶음(값 줄 · Store · Label · 닫는 ClearAll)만 뺀 것이다.
        assert second == first[:start] + first[end:]
        assert run.sent_at[1] == []  # 첫 카드가 승인된 뒤에도 한 줄도 나가지 않았다
        assert run.console.executed == second  # 감독이 두 번째로 승인한 줄이 그대로 나갔다
        assert "Store Preset 4.34" not in run.console.executed
        assert "Label Preset 4.34 'SKY'" not in run.console.executed
        for number in (*_DIMMER_NUMBERS, "4.33", "4.35", "4.36", "2.31", "2.32"):
            assert f"Store Preset {number}" in run.console.executed
        assert run.event["ok"] is True
        assert "4.34" in run.event["reason"]
        assert "10개" in run.event["reason"]  # 11개 중 10개를 저장했다

    def test_the_filled_preset_leaves_no_trace_in_the_grid_and_the_rest_are_repointed(
        self, tmp_path, monkeypatch
    ) -> None:
        run = _run_card(tmp_path, monkeypatch, decisions=(True, True), during=[_fill_sky])
        grid = run.store.latest["beat_grid"]

        # 하늘(BACK 0 → 4.34)의 칸은 바이트까지 그대로다 — 번호도 승인 기록도 없다.
        assert _cue_of(grid, "BACK", 0) == _cue_of(run.before, "BACK", 0)
        assert _cue_of(grid, "BACK", 0)["color_preset_no"] != "4.34"
        assert "4.34" not in grid["preset_colors"]
        assert "4.34" not in grid["preset_labels"]
        assert set(grid["preset_colors"]) == {"4.33", "4.35", "4.36"}
        # 나머지는 보낸 번호를 가리키고 승인이 적힌다.
        for group, bar, number in (
            ("WASH-ALL", 7, "4.33"),
            ("WASH-ALL", 14, "4.33"),
            ("WASH-ALL", 18, "4.35"),
            ("WASH-ALL", 22, "4.36"),
        ):
            assert _cue_of(grid, group, bar)["color_preset_no"] == number
        assert _cue_of(grid, "MOVER-U", 0)["position_preset_no"] == "2.31"
        assert _cue_of(grid, "MOVER-D", 0)["position_preset_no"] == "2.32"
        assert _cue_of(grid, "WASH-ALL", 7)["brightness"]["preset_no"] == "1.8"
        for group, bar in (("WASH-ALL", 7), ("MOVER-U", 0), ("MOVER-D", 0)):
            assert check_evidence_approval(_cue_of(grid, group, bar)) is None

    def test_the_pools_are_read_again_after_the_first_approval(self, tmp_path, monkeypatch) -> None:
        run = _run_card(tmp_path, monkeypatch, decisions=(True, True), during=[_fill_sky])

        # 첫 카드를 승인한 뒤 두 번째 카드가 오기 전에, 저장할 프리셋의 풀 셋을 한 번씩 다시 읽었다.
        reread = run.reads[run.reads_at[0] : run.reads_at[1]]
        assert sorted(reread) == [f"{_POOLS}/1", f"{_POOLS}/2", f"{_POOLS}/4"]

    def test_the_second_card_says_why_the_preset_is_missing(self, tmp_path, monkeypatch) -> None:
        run = _run_card(tmp_path, monkeypatch, decisions=(True, True), during=[_fill_sky])

        first, second = (_declared(request) for request in run.approval.requests)
        assert first.startswith("연출 프리셋 저장 — 프리셋 11개(디머 5 · 색 4 · 위치 2) 저장: ")
        assert second.startswith("연출 프리셋 저장 — 프리셋 10개(디머 5 · 색 3 · 위치 2) 저장: ")
        # 빠진 하늘은 「미정」에 이유와 함께 보인다 — 감독은 왜 카드가 달라졌는지 읽을 수 있다.
        undecided = second.partition("미정(이번 계획에서 제외): ")[2]
        assert "SKY" in undecided and "후보 4.34" in undecided
        assert "승인 창 사이 콘솔에서 4.34 번호가 채워져" in undecided

    def test_the_approval_record_names_the_card_that_was_sent(self, tmp_path, monkeypatch) -> None:
        run = _run_card(tmp_path, monkeypatch, decisions=(True, True), during=[_fill_sky])
        first, second = run.cards
        grid = run.store.latest["beat_grid"]

        # 승인 기록의 출처는 실제로 보낸 두 번째 카드의 해시다 — 첫 카드의 것이 아니다.
        approval = _cue_of(grid, "WASH-ALL", 7)["evidence"]["approval"]
        assert approval["source"] == f"preset_plan:{build_write_approval_batch([second]).sha256}"
        assert approval["source"] != f"preset_plan:{build_write_approval_batch([first]).sha256}"


class TestSecondCardRejected:
    def test_nothing_is_sent_and_the_grid_is_untouched(self, tmp_path, monkeypatch) -> None:
        run = _run_card(tmp_path, monkeypatch, decisions=(True, False), during=[_fill_sky])

        assert len(run.approval.requests) == 2
        assert run.console.executed == []
        assert run.event["ok"] is False
        assert run.store.latest["beat_grid"] == run.before  # 격자는 바이트까지 그대로다
        reason = run.event["reason"]
        assert "4.34" in reason
        assert "아무것도 보내지 않았습니다" in reason
        assert "거절" in reason
        assert "프리셋 계획 만들기" in reason  # 새 빈 번호를 받으려면 다시 계획한다


class TestTwoFilledSlots:
    def test_both_blocks_are_dropped_from_the_second_card(self, tmp_path, monkeypatch) -> None:
        def fill_dimmer_and_floor(console: FakeConsole) -> None:
            _fill(console, "1.9", "2.32")

        run = _run_card(
            tmp_path, monkeypatch, decisions=(True, True), during=[fill_dimmer_and_floor]
        )

        first, second = run.cards
        assert second == _without(first, "1.9", "2.32")
        assert run.console.executed == second
        assert run.event["ok"] is True
        reason = run.event["reason"]
        assert "프리셋 9개" in reason  # 11개 중 9개
        assert "1.9 DIM-25" in reason and "2.32 FLOOR MOVER-D" in reason
        grid = run.store.latest["beat_grid"]
        assert _cue_of(grid, "WASH-ALL", 14)["brightness"]["preset_no"] != "1.9"
        assert _cue_of(grid, "MOVER-D", 0)["position_preset_no"] != "2.32"
        assert "2.32" not in grid["preset_labels"]


class TestEverySlotFilled:
    def test_one_card_only_nothing_is_sent_and_the_reason_lists_what_was_held(
        self, tmp_path, monkeypatch
    ) -> None:
        run = _run_card(tmp_path, monkeypatch, decisions=(True,), during=[_fill_every_number])

        assert len(run.approval.requests) == 1  # 남은 프리셋이 없어 두 번째 카드는 없다
        assert run.console.executed == []  # 머리 ClearAll 한 줄도 나가지 않는다
        assert run.event["ok"] is False
        reason = run.event["reason"]
        for number in _EVERY_NUMBER:
            assert number in reason, number
        assert "프리셋 11개" in reason
        assert "아무것도 보내지 않았습니다" in reason
        assert "남지 않아" in reason
        assert "프리셋 계획 만들기" in reason
        assert run.store.latest["beat_grid"] == run.before


class TestPoolUnreadableOnReread:
    def test_the_blocks_of_the_unreadable_pool_are_dropped_and_the_rest_go_out(
        self, tmp_path, monkeypatch
    ) -> None:
        run = _run_card(tmp_path, monkeypatch, decisions=(True, True), during=[_drop_color_pool])

        first, second = run.cards
        # 색 풀(4)을 다시 못 읽었다 — 색 네 묶음만 빠지고 디머와 위치는 두 번째 카드로 나간다.
        assert second == _without(first, *_COLOR_NUMBERS.values())
        assert run.console.executed == second
        assert not any(
            line.startswith(("Store Preset 4.", "Label Preset 4.")) for line in run.console.executed
        )
        assert "Store Preset 1.8" in run.console.executed
        assert "Store Preset 2.31" in run.console.executed
        assert run.event["ok"] is True
        assert "다시 읽지 못해" in run.event["reason"]
        assert "프리셋 7개" in run.event["reason"]  # 11개 중 7개
        grid = run.store.latest["beat_grid"]
        assert _cue_of(grid, "WASH-ALL", 7)["color_preset_no"] is None
        assert _cue_of(grid, "BACK", 0) == _cue_of(run.before, "BACK", 0)
        assert _cue_of(grid, "WASH-ALL", 7)["brightness"]["preset_no"] == "1.8"
        assert _cue_of(grid, "MOVER-U", 0)["position_preset_no"] == "2.31"
        assert "preset_colors" not in grid


class TestFilledAgainDuringTheSecondCard:
    def test_two_cards_at_most_and_nothing_is_sent(self, tmp_path, monkeypatch) -> None:
        def fill_dimmer(console: FakeConsole) -> None:
            _fill(console, "1.9")

        run = _run_card(
            tmp_path, monkeypatch, decisions=(True, True, True), during=[_fill_sky, fill_dimmer]
        )

        assert len(run.approval.requests) == 2  # 세 번째 카드는 올라오지 않는다
        assert run.console.executed == []
        assert run.event["ok"] is False
        reason = run.event["reason"]
        assert "4.34" in reason and "1.9" in reason  # 두 번 걸린 프리셋이 모두 적힌다
        assert "아무것도 보내지 않았습니다" in reason
        assert "막혔" in reason
        assert run.store.latest["beat_grid"] == run.before


class TestNothingFilled:
    def test_one_card_goes_out_whole_with_the_plain_reason(self, tmp_path, monkeypatch) -> None:
        run = _run_card(tmp_path, monkeypatch, decisions=(True,))

        assert len(run.approval.requests) == 1
        (card,) = run.cards
        assert run.console.executed == card  # 바뀐 것이 없으면 카드가 통째로 나간다
        assert run.event["ok"] is True
        assert run.event["reason"] == _PLAIN_REASON
        # 승인 뒤 송신 직전에 저장할 프리셋의 풀을 다시 읽었다.
        reread = run.reads[run.reads_at[0] :]
        assert sorted(reread) == [f"{_POOLS}/1", f"{_POOLS}/2", f"{_POOLS}/4"]


class TestSecondCardOverTheRealChannel:
    def test_the_second_card_gets_its_own_request_and_the_other_thread_approves_it(
        self, tmp_path, monkeypatch
    ) -> None:
        # 운영 배선과 같은 비동기 승인 통로: 카드가 뜨면 다른 스레드가 (콘솔을 바꾼 뒤) 답한다.
        cards: list[int] = []
        holder: dict[str, FakeConsole] = {}

        def on_card(_store) -> None:
            cards.append(len(cards) + 1)
            if len(cards) == 1:  # 첫 카드가 떠 있는 사이 누가 콘솔에서 1.9 를 채웠다
                _fill(holder["console"], "1.9")

        session, console, store = _real_channel_session(tmp_path, monkeypatch, on_card=on_card)
        holder["console"] = console

        event = session.beat_grid_preset_plan()

        assert cards == [1, 2]  # 카드마다 새 요청이 올라가 다른 스레드가 각각 답했다
        assert event["ok"] is True
        assert console.executed == _without(list(_EXPECTED_SAVE), "1.9")
        assert "1.9 DIM-25" in event["reason"]
        grid = store.latest["beat_grid"]
        assert _cue_of(grid, "WASH-ALL", 7)["brightness"]["preset_no"] == "1.8"
        assert _cue_of(grid, "WASH-ALL", 14)["brightness"]["preset_no"] != "1.9"


class TestFailureTextStaysHonest:
    def test_a_rejected_first_card_keeps_the_generic_text(self, tmp_path, monkeypatch) -> None:
        run = _run_card(tmp_path, monkeypatch, decisions=(False,))

        assert len(run.approval.requests) == 1
        assert run.console.executed == []
        assert run.event["ok"] is False
        assert run.event["reason"] == _GENERIC_FAILURE
        assert run.store.latest["beat_grid"] == run.before

    def test_a_send_that_failed_midway_does_not_claim_that_nothing_was_sent(
        self, tmp_path, monkeypatch
    ) -> None:
        def fail_a_dimmer_store(console: FakeConsole) -> None:
            console.fail_on["Store Preset 1.10"] = "console refused"

        run = _run_card(
            tmp_path,
            monkeypatch,
            decisions=(True, True),
            during=[_fill_sky],
            setup=fail_a_dimmer_store,
        )

        # 두 번째 카드는 승인과 재확인을 지났고 보내다가 한 줄이 실패했다 — 앞 줄은 이미 나갔다.
        assert len(run.approval.requests) == 2
        assert "Store Preset 1.8" in run.console.executed
        assert run.event["ok"] is False
        assert run.event["reason"] == _GENERIC_FAILURE
        assert "아무것도 보내지 않았습니다" not in run.event["reason"]
