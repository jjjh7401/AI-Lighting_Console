"""카드 WT-wave-presets — 웨이브 프리셋 저장 메서드(세션)의 승인·송신 경로.

실제 세션 · 안전 게이트 · 승인 포트를 쓰고, 콘솔만 가짜(``FakeConsole``)다. 콘솔에 실제로 나간 줄은
``console.executed`` 로 본다. 승인 카드는 한 장이어야 하고, 송신 직전 재확인이 걸리면 한 줄도
나가지 않아야 한다.
"""

from __future__ import annotations

import json

from server.design.wave_presets import WAVE_PRESETS
from server.web.messages import PROTOCOL_VERSION, ProtocolError, parse_client_message
from server.web.session import _WAVE_WHOLE_BATCH_REASON, SongTimelineStore

from .test_apply_time_approval_t577 import _new_session, _state_tree, _timeline

#: 빈 기록에서 처음 배정되는 곡(LOVE ATTACK)의 스피드 마스터 — 가장 큰 빈 번호.
SPEED_MASTER = 15
POOL_ROOT = "DataPool/PresetPools"
POOL_21 = f"{POOL_ROOT}/21"


def _tree(pool21: dict[int, str] | None = None, *, root: bool = True) -> dict:
    tree = _state_tree()
    if root:
        tree[POOL_ROOT] = {"children": [{"i": 21, "name": "All 1"}, {"i": 4, "name": "Color"}]}
    if pool21 is not None:
        tree[POOL_21] = {"children": [{"i": n, "name": name} for n, name in pool21.items()]}
    return tree


def _session(tmp_path, *, tree, confirmed: bool = True, bar_map: bool = True):
    timeline = _timeline()
    timeline["beat_grid"]["tracks"][0]["group_no_confirmed"] = confirmed
    if not bar_map:
        timeline.pop("bar_map")
    store = SongTimelineStore()
    store.latest = timeline
    session, console, approval, _audit = _new_session(tmp_path, store=store, state_tree=tree)
    return session, console, approval


def _stores(executed: list[str]) -> list[str]:
    return [line for line in executed if line.startswith("Store Preset")]


class _Refused:
    """디스패치가 승인 거절로 돌아온 모양 — 재확인 클로저만 보려고 쓴다."""

    class result:  # noqa: N801 — 디스패치 결과 객체의 모양을 흉내 낸다
        is_error = True

    command_outcomes = ()


class TestOneCardOneBatch:
    def test_five_presets_go_to_the_console_in_one_approved_batch(self, tmp_path) -> None:
        session, console, approval = _session(tmp_path, tree=_tree({}))

        status = session.beat_grid_wave_presets("BACK")

        assert status["ok"] is True
        assert len(approval.requests) == 1
        assert _stores(console.executed) == [
            "Store Preset 21.1 'WAVE DIM SINE 1B' /Universal",
            "Store Preset 21.2 'WAVE DIM SINE 2B' /Universal",
            "Store Preset 21.3 'WAVE DIM SINE 4B' /Universal",
            "Store Preset 21.4 'WAVE COL RAINBOW 2B' /Universal",
            "Store Preset 21.5 'WAVE COL WARMCOOL 2B' /Universal",
        ]
        assert console.executed.count(f"Master 3.{SPEED_MASTER} At BPM 112.35") == 1

    def test_shared_lines_are_not_dropped_by_the_dedupe(self, tmp_path) -> None:
        # 여러 프리셋이 같은 줄을 쓴다. 한 송신 안에서는 건너뛰지 않는다(카드 t601).
        session, console, _approval = _session(tmp_path, tree=_tree({}))

        session.beat_grid_wave_presets("BACK")

        assert console.executed.count("ChangeDestination Root") == len(WAVE_PRESETS)
        assert console.executed.count("Attribute 'Dimmer' At SpeedMaster 15") == 3

    def test_a_free_pool_gives_the_lowest_numbers_after_the_occupied_ones(self, tmp_path) -> None:
        session, console, _approval = _session(tmp_path, tree=_tree({1: "P1", 2: "P2"}))

        session.beat_grid_wave_presets("BACK")

        stores = _stores(console.executed)
        assert stores[0] == "Store Preset 21.3 'WAVE DIM SINE 1B' /Universal"
        assert stores[-1] == "Store Preset 21.7 'WAVE COL WARMCOOL 2B' /Universal"


class TestSameNameIsSkipped:
    def test_a_label_already_in_the_pool_is_not_stored_again(self, tmp_path) -> None:
        session, console, _approval = _session(tmp_path, tree=_tree({3: "WAVE DIM SINE 2B"}))

        status = session.beat_grid_wave_presets("BACK")

        assert status["ok"] is True
        assert not [line for line in _stores(console.executed) if "WAVE DIM SINE 2B" in line]
        assert "WAVE DIM SINE 2B" in status["reason"]
        assert "건너뜀" in status["reason"]

    def test_when_every_name_is_already_there_nothing_is_sent_and_no_card_opens(
        self, tmp_path
    ) -> None:
        names = {number: preset.console_label for number, preset in enumerate(WAVE_PRESETS, 1)}
        session, console, approval = _session(tmp_path, tree=_tree(names))

        status = session.beat_grid_wave_presets("BACK")

        assert status["ok"] is True
        assert console.executed == []
        assert approval.requests == []


class TestRefusalsBeforeAnyCard:
    def test_a_track_without_a_confirmed_console_group_is_refused(self, tmp_path) -> None:
        session, console, approval = _session(tmp_path, tree=_tree({}), confirmed=False)

        status = session.beat_grid_wave_presets("BACK")

        assert status["ok"] is False
        assert "그룹 번호가 아직 확인되지 않아" in status["reason"]
        assert approval.requests == []
        assert console.executed == []

    def test_an_unknown_line_name_is_refused(self, tmp_path) -> None:
        session, console, approval = _session(tmp_path, tree=_tree({}))

        status = session.beat_grid_wave_presets("NOPE")

        assert status["ok"] is False
        assert "찾지 못했습니다" in status["reason"]
        assert approval.requests == []
        assert console.executed == []

    def test_a_missing_song_tempo_is_refused(self, tmp_path) -> None:
        session, console, approval = _session(tmp_path, tree=_tree({}), bar_map=False)

        status = session.beat_grid_wave_presets("BACK")

        assert status["ok"] is False
        assert "BPM" in status["reason"]
        assert approval.requests == []
        assert console.executed == []

    def test_an_unreadable_effect_pool_is_refused(self, tmp_path) -> None:
        session, console, approval = _session(tmp_path, tree=_tree({}, root=False))

        status = session.beat_grid_wave_presets("BACK")

        assert status["ok"] is False
        assert "효과 풀" in status["reason"]
        assert approval.requests == []
        assert console.executed == []


class TestRecheckClosure:
    """송신 직전 재확인 클로저를 직접 본다 — 계획한 번호가 찼는지, 풀을 다시 읽는지."""

    def _risk_of(self, tmp_path, monkeypatch, tree):
        session, _console, _approval = _session(tmp_path, tree=tree)
        captured: dict = {}

        def capture(call, *, risk):
            captured["risk"] = risk
            return _Refused()

        monkeypatch.setattr(session, "_dispatch_declared", capture)
        session.beat_grid_wave_presets("BACK")
        return captured["risk"]

    def test_the_declaration_names_the_wave_kind(self, tmp_path, monkeypatch) -> None:
        risk = self._risk_of(tmp_path, monkeypatch, _tree({}))

        assert risk.kind == "beat_grid_wave_preset"

    def test_it_lets_the_batch_through_while_the_planned_slots_are_free(
        self, tmp_path, monkeypatch
    ) -> None:
        risk = self._risk_of(tmp_path, monkeypatch, _tree({}))

        assert risk.recheck() is None

    def test_it_stops_the_whole_batch_when_a_planned_slot_was_filled(
        self, tmp_path, monkeypatch
    ) -> None:
        tree = _tree({})
        risk = self._risk_of(tmp_path, monkeypatch, tree)
        tree[POOL_21]["children"].append({"i": 1, "name": "SOMEONE ELSE"})

        assert risk.recheck() == _WAVE_WHOLE_BATCH_REASON

    def test_it_stops_the_whole_batch_when_the_pool_cannot_be_read_again(
        self, tmp_path, monkeypatch
    ) -> None:
        tree = _tree({})
        risk = self._risk_of(tmp_path, monkeypatch, tree)
        del tree[POOL_ROOT]

        assert risk.recheck() == _WAVE_WHOLE_BATCH_REASON


class TestWireShape:
    def test_wave_presets_mode_carries_the_line_name(self) -> None:
        raw = json.dumps(
            {
                "v": PROTOCOL_VERSION,
                "type": "beat_grid_apply",
                "mode": "wave_presets",
                "group_name": "BACK",
            }
        )

        parsed = parse_client_message(raw)

        assert parsed == {
            "v": PROTOCOL_VERSION,
            "type": "beat_grid_apply",
            "mode": "wave_presets",
            "group_name": "BACK",
        }

    def test_wave_presets_without_a_line_name_is_a_protocol_error(self) -> None:
        raw = json.dumps({"v": PROTOCOL_VERSION, "type": "beat_grid_apply", "mode": "wave_presets"})

        try:
            parse_client_message(raw)
        except ProtocolError as error:
            assert "group_name" in str(error)
        else:
            raise AssertionError("group_name 없는 wave_presets 가 통과했다")

    def test_the_other_apply_modes_keep_their_old_shape(self) -> None:
        raw = json.dumps({"v": PROTOCOL_VERSION, "type": "beat_grid_apply", "mode": "preset_plan"})

        assert parse_client_message(raw) == {
            "v": PROTOCOL_VERSION,
            "type": "beat_grid_apply",
            "mode": "preset_plan",
        }
