"""카드 WT-wave-custom — 직접 만든 웨이브 프리셋 저장(세션 · 와이어).

실제 세션 · 안전 게이트 · 승인 포트를 쓰고 콘솔만 가짜(``FakeConsole``)다. 승인 카드는 한 장이고,
같은 콘솔 이름이 있으면 건너뛰지 않고 거절하며, 송신 직전 재확인이 걸리면 한 줄도 나가지 않는다.
"""

from __future__ import annotations

import json

import pytest

from server.design.beat_grid_edit import load_preset_pool_policy, validate_preset_pool_assignment
from server.design.beat_grid_effect_presets import effect_template_problem
from server.web.messages import PROTOCOL_VERSION, ProtocolError, parse_client_message
from server.web.session import SongTimelineStore

from .test_apply_time_approval_t577 import _cue_of, _new_session, _state_tree, _timeline
from .test_beat_grid_wave_presets import POOL_21, SPEED_MASTER, _session, _stores, _tree

_SINE_2B = {"shape": "sine", "beats": 2, "label": "MY SINE 2B", "display_name": "내 사인 2박"}


class TestCustomSaveOneCard:
    def test_one_chosen_preset_goes_to_the_console_in_one_approved_batch(self, tmp_path) -> None:
        session, console, approval = _session(tmp_path, tree=_tree({}))

        status = session.beat_grid_wave_custom("BACK", _SINE_2B)

        assert status["ok"] is True
        assert len(approval.requests) == 1
        assert _stores(console.executed) == ["Store Preset 21.1 'MY SINE 2B' /Universal"]
        assert console.executed.count(f"Master 3.{SPEED_MASTER} At BPM 112.35") == 1
        assert "Attribute 'Dimmer' At Measure 2" in console.executed

    def test_a_color_shape_uses_its_color_template(self, tmp_path) -> None:
        session, console, _approval = _session(tmp_path, tree=_tree({}))

        status = session.beat_grid_wave_custom(
            "BACK",
            {"shape": "rainbow", "beats": 1, "label": "MY RAINBOW 1B", "display_name": "내 무지개"},
        )

        assert status["ok"] is True
        assert "Store Preset 21.1 'MY RAINBOW 1B' /Universal" in console.executed
        assert "Attribute 'ColorRGB_R' At Phase 0" in console.executed

    def test_the_first_free_slot_is_used_after_the_occupied_ones(self, tmp_path) -> None:
        session, console, _approval = _session(tmp_path, tree=_tree({1: "P1", 2: "P2"}))

        session.beat_grid_wave_custom("BACK", _SINE_2B)

        assert _stores(console.executed) == ["Store Preset 21.3 'MY SINE 2B' /Universal"]


class TestRefusedBeforeAnyCard:
    def test_a_console_name_already_in_the_pool_is_refused_not_skipped(self, tmp_path) -> None:
        session, console, approval = _session(tmp_path, tree=_tree({3: "MY SINE 2B"}))

        status = session.beat_grid_wave_custom("BACK", _SINE_2B)

        assert status["ok"] is False
        assert "이미 있습니다" in status["reason"]
        assert approval.requests == []
        assert console.executed == []

    @pytest.mark.parametrize(
        ("preset", "word"),
        [
            ({"shape": "square", "beats": 2, "label": "X", "display_name": "n"}, "웨이브 모양"),
            ({"shape": "sine", "beats": 3, "label": "X", "display_name": "n"}, "박 수"),
            ({"shape": "sine", "beats": 2, "label": "내 사인", "display_name": "n"}, "콘솔 이름"),
            ({"shape": "sine", "beats": 2, "label": "X", "display_name": " "}, "화면 이름"),
        ],
    )
    def test_a_bad_value_is_refused_and_no_card_opens(self, tmp_path, preset, word) -> None:
        session, console, approval = _session(tmp_path, tree=_tree({}))

        status = session.beat_grid_wave_custom("BACK", preset)

        assert status["ok"] is False
        assert word in status["reason"]
        assert approval.requests == []
        assert console.executed == []

    def test_an_unconfirmed_line_is_refused_before_the_card(self, tmp_path) -> None:
        session, console, approval = _session(tmp_path, tree=_tree({}), confirmed=False)

        status = session.beat_grid_wave_custom("BACK", _SINE_2B)

        assert status["ok"] is False
        assert "그룹 번호가 아직 확인되지 않아" in status["reason"]
        assert approval.requests == []
        assert console.executed == []


class TestRecheckWhileTheCardIsOpen:
    def test_a_slot_filled_while_the_card_is_open_sends_nothing(self, tmp_path) -> None:
        tree = _tree({})
        session, console, approval = _session(tmp_path, tree=tree)
        original = approval.request_approval

        def fill_slot_one_while_open(request):
            tree[POOL_21]["children"].append({"i": 1, "name": "SOMEONE ELSE"})
            return original(request)

        approval.request_approval = fill_slot_one_while_open

        status = session.beat_grid_wave_custom("BACK", _SINE_2B)

        assert status["ok"] is False
        assert _stores(console.executed) == []
        assert len(approval.requests) == 1

    def test_the_same_console_name_appearing_while_open_is_caught_by_the_recheck(
        self, tmp_path, monkeypatch
    ) -> None:
        tree = _tree({})
        session, _console, _approval = _session(tmp_path, tree=tree)
        captured: dict = {}

        class _Refused:
            class result:  # noqa: N801 — 디스패치 결과 객체의 모양만 흉내 낸다
                is_error = True

            command_outcomes = ()

        def capture(call, *, risk):
            captured["risk"] = risk
            return _Refused()

        monkeypatch.setattr(session, "_dispatch_declared", capture)
        session.beat_grid_wave_custom("BACK", _SINE_2B)
        risk = captured["risk"]
        assert risk.kind == "beat_grid_wave_preset"
        assert risk.recheck() is None

        tree[POOL_21]["children"].append({"i": 9, "name": "MY SINE 2B"})

        assert risk.recheck() is not None


def _session_store(tmp_path, *, decisions=(True,)):
    """저장 뒤 칸 적용을 보려고 격자 저장소를 손에 쥔 세션을 만든다(콘솔은 가짜)."""
    timeline = _timeline()
    store = SongTimelineStore()
    store.latest = timeline
    session, console, approval, _audit = _new_session(
        tmp_path, store=store, state_tree=_tree({}), decisions=decisions
    )
    return session, console, approval, store


class TestWaveBand:
    def test_the_wave_band_is_pool_21_and_stays_apart_from_the_mixed_band(self) -> None:
        policy = load_preset_pool_policy()

        assert validate_preset_pool_assignment("wave", "21.5", policy) is None
        assert validate_preset_pool_assignment("wave", "22.5", policy) is not None
        assert validate_preset_pool_assignment("mixed", "21.5", policy) is not None

    def test_a_wave_template_fits_and_a_position_template_does_not(self) -> None:
        assert effect_template_problem("pulse-sine-breath", "wave") is None
        assert effect_template_problem("chase-rainbow-wave", "wave") is None
        assert effect_template_problem("chase-rainbow-wave", "position") is not None


class TestCellApply:
    def test_the_saved_slot_is_written_to_the_chosen_cell_pending_approval(self, tmp_path) -> None:
        session, _console, _approval, store = _session_store(tmp_path)

        status = session.beat_grid_wave_custom("BACK", _SINE_2B, cells=[("BACK", 1)])

        assert status["ok"] is True
        cue = _cue_of(store.latest["beat_grid"], "BACK", 1)
        assert cue["effect_preset_no"] == "21.1"
        assert cue["effect_kind"] == "wave"
        assert "21.1" in status["reason"]

    def test_a_cell_on_another_line_is_not_written(self, tmp_path) -> None:
        session, _console, _approval, store = _session_store(tmp_path)

        status = session.beat_grid_wave_custom("BACK", _SINE_2B, cells=[("FOH", 1)])

        assert status["ok"] is True
        assert _cue_of(store.latest["beat_grid"], "BACK", 1)["effect_preset_no"] == "4.21"
        assert "다른 줄" in status["reason"]

    def test_no_cells_leaves_every_cell_alone(self, tmp_path) -> None:
        session, _console, _approval, store = _session_store(tmp_path)

        session.beat_grid_wave_custom("BACK", _SINE_2B)

        assert _cue_of(store.latest["beat_grid"], "BACK", 1)["effect_preset_no"] == "4.21"

    def test_a_refused_card_writes_no_cell(self, tmp_path) -> None:
        session, _console, _approval, store = _session_store(tmp_path, decisions=(False,))

        status = session.beat_grid_wave_custom("BACK", _SINE_2B, cells=[("BACK", 1)])

        assert status["ok"] is False
        assert _cue_of(store.latest["beat_grid"], "BACK", 1)["effect_preset_no"] == "4.21"


class TestReflectKeepsAWaveCell:
    def test_a_cell_on_a_preset_already_in_pool_21_is_sent_not_held(self, tmp_path) -> None:
        # 저장된 웨이브 번호가 이미 콘솔 풀 21에 있으면 반영 때 「빈 프리셋」으로 보류되지 않는다.
        timeline = _timeline()
        cue = timeline["beat_grid"]["tracks"][0]["cues"][0]
        cue.update({"effect_preset_no": "21.1", "effect_kind": "wave"})
        tree = _state_tree()
        tree[POOL_21] = {"children": [{"i": 1, "name": "MY SINE 2B"}]}
        store = SongTimelineStore()
        store.latest = timeline
        session, _console, approval, _audit = _new_session(tmp_path, store=store, state_tree=tree)

        status = session.beat_grid_apply()

        assert status["ok"] is True
        assert not status.get("blocked_cells")
        sent = [item.command for request in approval.requests for item in request.items]
        assert any("21.1" in command for command in sent)

    def test_control_a_cell_on_a_number_missing_from_pool_21_is_not_sent_as_existing(
        self, tmp_path
    ) -> None:
        # 대조군: 콘솔 풀 21에 없는 번호를 가리키면 같은 검사가 그 칸을 「빈 프리셋」으로 본다.
        timeline = _timeline()
        cue = timeline["beat_grid"]["tracks"][0]["cues"][0]
        cue.update({"effect_preset_no": "21.2", "effect_kind": "wave"})
        tree = _state_tree()
        tree[POOL_21] = {"children": [{"i": 1, "name": "MY SINE 2B"}]}
        store = SongTimelineStore()
        store.latest = timeline
        session, _console, approval, _audit = _new_session(tmp_path, store=store, state_tree=tree)

        status = session.beat_grid_apply()

        assert status["ok"] is False
        assert status["blocked_cells"][0]["group_name"] == "BACK"
        assert status["blocked_cells"][0]["bar"] == 1
        assert "21.2" in status["reason"]
        assert approval.requests == []


class TestCellsOnTheWire:
    def test_wave_custom_carries_the_chosen_cells(self) -> None:
        raw = json.dumps(
            {
                "v": PROTOCOL_VERSION,
                "type": "beat_grid_apply",
                "mode": "wave_custom",
                "group_name": "BACK",
                "preset": _SINE_2B,
                "cells": [["BACK", 1]],
            }
        )

        parsed = parse_client_message(raw)

        assert parsed["cells"][0][0] == "BACK"
        assert parsed["cells"][0][1] == 1

    def test_cells_stay_refused_for_the_wave_presets_mode(self) -> None:
        raw = json.dumps(
            {
                "v": PROTOCOL_VERSION,
                "type": "beat_grid_apply",
                "mode": "wave_presets",
                "group_name": "BACK",
                "cells": [["BACK", 1]],
            }
        )

        with pytest.raises(ProtocolError, match="only valid"):
            parse_client_message(raw)


class TestWireShape:
    def test_wave_custom_carries_the_line_name_and_the_preset(self) -> None:
        raw = json.dumps(
            {
                "v": PROTOCOL_VERSION,
                "type": "beat_grid_apply",
                "mode": "wave_custom",
                "group_name": "BACK",
                "preset": _SINE_2B,
            }
        )

        assert parse_client_message(raw) == {
            "v": PROTOCOL_VERSION,
            "type": "beat_grid_apply",
            "mode": "wave_custom",
            "group_name": "BACK",
            "preset": _SINE_2B,
        }

    def test_wave_custom_without_a_preset_object_is_a_protocol_error(self) -> None:
        raw = json.dumps(
            {
                "v": PROTOCOL_VERSION,
                "type": "beat_grid_apply",
                "mode": "wave_custom",
                "group_name": "BACK",
            }
        )

        with pytest.raises(ProtocolError, match="preset"):
            parse_client_message(raw)
