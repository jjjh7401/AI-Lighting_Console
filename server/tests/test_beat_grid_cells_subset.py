"""박자 격자 칸 단위 반영·일괄 편집 (``cells``) — 서버 쪽 (SPEC-LDRHYTHM-001, 칸 단위 반영).

두 선택 필드를 다룬다.

* ``beat_grid_apply`` 의 ``cells`` — 고른 (줄 이름, 마디) 칸의 큐를 콘솔에 ``/Merge`` 로 덧쓴다.
  칸 기록(스냅샷)이 있으면 **바뀐 칸**만, 서버를 다시 띄워 칸 기록이 없으면 소유 기록을 기준으로
  고른 칸을 모두 보낸다(``subset.baseline``·``beat_grid.partial_baseline``). 콘솔에 이미 있는
  프리셋 번호의 승인 대기 칸은 번호 줄만 보내고 승인을 기록한다. 타임코드·프리셋 만들기·시퀀스
  새로 만들기는 한 줄도 보내지 않는다.
* ``beat_grid_edit`` 의 ``cells`` — ``bar``+``target`` 한 쌍 대신 칸 여러 개에 같은 ``changes`` 를
  한 번에 씌운다. 한 칸이라도 거절되면 아무 칸도 바꾸지 않는다.

층: (1) 프로토콜 파서, (2) ``server.design.beat_grid_send`` 의 순수 헬퍼, (3) 세션 통합
(``test_beat_grid_send_t563`` 의 가짜 콘솔 하네스를 그대로 쓴다), (4) WebSocket 배선.

콘솔 접촉: 0건. ``FakeConsole`` 만 쓰고 실기 포트로는 한 바이트도 나가지 않는다. 앱 데이터 폴더도
건드리지 않는다(``tmp_path`` 만 쓴다).
"""

from __future__ import annotations

import copy
import json
import re
from collections.abc import Callable
from dataclasses import dataclass, replace
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from server.design.beat_grid import pending_preset_approvals
from server.design.beat_grid_emit import (
    CueEmitResult,
    SongTiming,
    emit_beat_grid_write_bundle,
)
from server.design.beat_grid_send import (
    CELL_UNCHANGED_REASON,
    PartialCellSnapshot,
    apply_beat_grid_ownership_reuse,
    beat_grid_cell_snapshot,
    cell_apply_units,
    cells_needing_whole_apply,
    cells_with_removed_fields,
    format_cell_list,
    merge_applied_cues_into_record,
    merge_cell_snapshot,
    merge_store_line,
    owned_record_has_tracks,
    partial_apply_baseline,
    recorded_cue_conflict,
    removed_cue_fields,
    snapshot_known_cells,
    subset_line_violation,
    unsent_beat_grid_cells,
)
from server.design.cue_fade import store_with_fade
from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.web.app import WebDeps, create_app
from server.web.approval_bridge import ApprovalChannel
from server.web.messages import (
    BEAT_GRID_CELLS_MAX,
    PROTOCOL_VERSION,
    ProtocolError,
    beat_grid_send_status_event,
    parse_client_message,
)
from server.web.session import ChatSession, SongTimelineStore, derive_beat_grid_fields
from server.web.timeline_library import SongTimelineLibrary

from .conftest import drain_until
from .test_beat_grid_send_t563 import _APPROVED_EVIDENCE, _new_session, _state_tree, _timeline
from .test_position_preset_create_t592 import _FRAMES as _POSITION_FRAMES
from .test_position_preset_create_t592 import _RECIPE as _POSITION_RECIPE
from .test_runner_self_correction import ScriptedProvider
from .test_safety_gate import FakeConsole
from .test_web_beat_grid_send_t563 import _approve_until, _deps, _send

# =============================================================================
# 1. 프로토콜 — beat_grid_apply / beat_grid_edit 의 cells
# =============================================================================


def _raw(**fields: object) -> str:
    return json.dumps({"v": PROTOCOL_VERSION, **fields}, ensure_ascii=False)


#: 칸 목록으로 받아들여지면 안 되는 값들 — 이유를 한 줄씩 단다.
_BAD_CELL_LISTS = [
    pytest.param([], id="empty-list"),
    pytest.param(None, id="null"),
    pytest.param("BACK", id="string-not-list"),
    pytest.param({"BACK": 1}, id="object-not-list"),
    pytest.param([["BACK"]], id="item-with-one-element"),
    pytest.param([["BACK", 1, 2]], id="item-with-three-elements"),
    pytest.param([["BACK", 1], "FOH"], id="item-not-array"),
    pytest.param([{"group_name": "BACK", "bar": 1}], id="item-is-object"),
    pytest.param([[1, 1]], id="group-not-string"),
    pytest.param([["", 1]], id="group-empty"),
    pytest.param([["   ", 1]], id="group-blank"),
    pytest.param([["BACK", True]], id="bool-bar-is-not-an-int"),
    pytest.param([["BACK", False]], id="bool-false-bar"),
    pytest.param([["BACK", 0]], id="bar-zero"),
    pytest.param([["BACK", -3]], id="bar-negative"),
    pytest.param([["BACK", "1"]], id="bar-string"),
    pytest.param([["BACK", 1.5]], id="bar-float"),
    pytest.param([["BACK", None]], id="bar-null"),
]


class TestBeatGridApplyCellsMessage:
    def test_cells_parse_as_tuples_under_the_cells_key(self) -> None:
        message = parse_client_message(
            _raw(type="beat_grid_apply", cells=[["BACK", 1], ["FOH", 3]])
        )
        assert message == {
            "v": PROTOCOL_VERSION,
            "type": "beat_grid_apply",
            "mode": "apply",
            "cells": [("BACK", 1), ("FOH", 3)],
        }

    def test_explicit_apply_mode_accepts_cells(self) -> None:
        message = parse_client_message(_raw(type="beat_grid_apply", mode="apply", cells=[["A", 2]]))
        assert message["cells"] == [("A", 2)]

    def test_without_cells_the_message_is_byte_identical_to_before(self) -> None:
        assert parse_client_message(_raw(type="beat_grid_apply")) == {
            "v": PROTOCOL_VERSION,
            "type": "beat_grid_apply",
            "mode": "apply",
        }

    def test_duplicates_are_removed_and_order_is_kept(self) -> None:
        message = parse_client_message(
            _raw(type="beat_grid_apply", cells=[["FOH", 3], ["BACK", 1], ["FOH", 3], ["BACK", 1]])
        )
        assert message["cells"] == [("FOH", 3), ("BACK", 1)]

    @pytest.mark.parametrize("cells", _BAD_CELL_LISTS)
    def test_invalid_cells_are_a_protocol_error(self, cells: object) -> None:
        with pytest.raises(ProtocolError):
            parse_client_message(_raw(type="beat_grid_apply", cells=cells))

    def test_exactly_the_limit_is_accepted(self) -> None:
        cells = [["BACK", bar] for bar in range(1, BEAT_GRID_CELLS_MAX + 1)]
        message = parse_client_message(_raw(type="beat_grid_apply", cells=cells))
        assert len(message["cells"]) == BEAT_GRID_CELLS_MAX == 400

    def test_more_than_the_limit_is_rejected(self) -> None:
        cells = [["BACK", bar] for bar in range(1, BEAT_GRID_CELLS_MAX + 2)]
        with pytest.raises(ProtocolError):
            parse_client_message(_raw(type="beat_grid_apply", cells=cells))

    def test_the_limit_counts_received_items_not_distinct_ones(self) -> None:
        with pytest.raises(ProtocolError):
            parse_client_message(
                _raw(type="beat_grid_apply", cells=[["BACK", 1]] * (BEAT_GRID_CELLS_MAX + 1))
            )

    def test_cells_are_only_valid_with_the_apply_mode(self) -> None:
        with pytest.raises(ProtocolError):
            parse_client_message(_raw(type="beat_grid_apply", mode="preset_plan", cells=[["A", 1]]))

    def test_preset_plan_mode_without_cells_still_parses(self) -> None:
        message = parse_client_message(_raw(type="beat_grid_apply", mode="preset_plan"))
        assert message["mode"] == "preset_plan"
        assert "cells" not in message


_CHANGES = {"entry": {"fade_bars": 1, "mib_mode": None}}


class TestBeatGridEditCellsMessage:
    def test_cells_with_changes_parse(self) -> None:
        message = parse_client_message(
            _raw(type="beat_grid_edit", cells=[["BACK", 1], ["BACK", 2]], changes=_CHANGES)
        )
        assert message == {
            "v": PROTOCOL_VERSION,
            "type": "beat_grid_edit",
            "cells": [("BACK", 1), ("BACK", 2)],
            "changes": _CHANGES,
        }

    def test_the_single_cell_form_is_unchanged(self) -> None:
        message = parse_client_message(
            _raw(type="beat_grid_edit", bar=11, target="MOVER-U", changes=_CHANGES)
        )
        assert message == {
            "v": PROTOCOL_VERSION,
            "type": "beat_grid_edit",
            "bar": 11,
            "target": "MOVER-U",
            "changes": _CHANGES,
        }
        assert "cells" not in message

    def test_the_sentence_form_is_unchanged(self) -> None:
        message = parse_client_message(
            _raw(type="beat_grid_edit", sentence="11마디 BACK 밝기를 70%로")
        )
        assert message == {
            "v": PROTOCOL_VERSION,
            "type": "beat_grid_edit",
            "sentence": "11마디 BACK 밝기를 70%로",
        }

    def test_duplicates_are_removed_and_order_is_kept(self) -> None:
        message = parse_client_message(
            _raw(type="beat_grid_edit", cells=[["B", 2], ["A", 1], ["B", 2]], changes=_CHANGES)
        )
        assert message["cells"] == [("B", 2), ("A", 1)]

    @pytest.mark.parametrize("cells", _BAD_CELL_LISTS)
    def test_invalid_cells_are_a_protocol_error(self, cells: object) -> None:
        with pytest.raises(ProtocolError):
            parse_client_message(_raw(type="beat_grid_edit", cells=cells, changes=_CHANGES))

    def test_bool_bar_in_a_cell_is_rejected(self) -> None:
        with pytest.raises(ProtocolError):
            parse_client_message(
                _raw(type="beat_grid_edit", cells=[["BACK", True]], changes=_CHANGES)
            )

    def test_more_than_the_limit_is_rejected(self) -> None:
        cells = [["BACK", bar] for bar in range(1, BEAT_GRID_CELLS_MAX + 2)]
        with pytest.raises(ProtocolError):
            parse_client_message(_raw(type="beat_grid_edit", cells=cells, changes=_CHANGES))

    def test_both_addressing_forms_are_rejected(self) -> None:
        with pytest.raises(ProtocolError):
            parse_client_message(
                _raw(
                    type="beat_grid_edit",
                    cells=[["BACK", 1]],
                    bar=1,
                    target="BACK",
                    changes=_CHANGES,
                )
            )

    def test_cells_with_only_bar_is_still_both_forms(self) -> None:
        with pytest.raises(ProtocolError):
            parse_client_message(
                _raw(type="beat_grid_edit", cells=[["BACK", 1]], bar=1, changes=_CHANGES)
            )

    def test_cells_with_only_target_is_still_both_forms(self) -> None:
        with pytest.raises(ProtocolError):
            parse_client_message(
                _raw(type="beat_grid_edit", cells=[["BACK", 1]], target="BACK", changes=_CHANGES)
            )

    def test_null_bar_and_target_next_to_cells_are_not_a_second_form(self) -> None:
        message = parse_client_message(
            _raw(
                type="beat_grid_edit", cells=[["BACK", 1]], bar=None, target=None, changes=_CHANGES
            )
        )
        assert message["cells"] == [("BACK", 1)]

    def test_neither_addressing_form_is_rejected(self) -> None:
        with pytest.raises(ProtocolError):
            parse_client_message(_raw(type="beat_grid_edit", changes=_CHANGES))

    def test_changes_are_required_with_cells(self) -> None:
        with pytest.raises(ProtocolError):
            parse_client_message(_raw(type="beat_grid_edit", cells=[["BACK", 1]]))

    def test_empty_changes_are_rejected_with_cells(self) -> None:
        with pytest.raises(ProtocolError):
            parse_client_message(_raw(type="beat_grid_edit", cells=[["BACK", 1]], changes={}))

    def test_changes_must_be_an_object_with_cells(self) -> None:
        with pytest.raises(ProtocolError):
            parse_client_message(_raw(type="beat_grid_edit", cells=[["BACK", 1]], changes=[1]))

    def test_cells_cannot_ride_with_a_sentence(self) -> None:
        with pytest.raises(ProtocolError):
            parse_client_message(
                _raw(
                    type="beat_grid_edit", cells=[["BACK", 1]], sentence="11마디 BACK 밝기를 70%로"
                )
            )

    def test_cells_with_both_changes_and_sentence_is_still_rejected(self) -> None:
        with pytest.raises(ProtocolError):
            parse_client_message(
                _raw(
                    type="beat_grid_edit",
                    cells=[["BACK", 1]],
                    changes=_CHANGES,
                    sentence="11마디 BACK 밝기를 70%로",
                )
            )


class TestBeatGridSendStatusEventSubset:
    _BASE: dict[str, Any] = {
        "pending_apply_count": 2,
        "last_action": "apply",
        "ok": True,
        "blocked_cells": [],
    }

    def test_subset_key_is_absent_unless_given(self) -> None:
        assert "subset" not in beat_grid_send_status_event(**self._BASE)

    def test_subset_key_is_carried_when_given(self) -> None:
        subset = {"requested": 2, "applied": [["BACK", 1]], "not_applied": []}
        assert beat_grid_send_status_event(**self._BASE, subset=subset)["subset"] == subset


# =============================================================================
# 2. 순수 헬퍼 — server.design.beat_grid_send (콘솔 접촉 0, 세션 없음)
# =============================================================================


class TestMergeStoreLine:
    def test_merge_goes_after_the_cue_fade_and_before_other_options(self) -> None:
        assert (
            merge_store_line("Store Sequence 3 Cue 7 CueFade 1.5 /CueOnly")
            == "Store Sequence 3 Cue 7 CueFade 1.5 /Merge /CueOnly"
        )

    def test_a_plain_store_line_gets_merge(self) -> None:
        assert merge_store_line("Store Sequence 3 Cue 7") == "Store Sequence 3 Cue 7 /Merge"

    def test_options_without_a_fade_keep_their_order(self) -> None:
        assert (
            merge_store_line("Store Sequence 3 Cue 7 /CueOnly")
            == "Store Sequence 3 Cue 7 /Merge /CueOnly"
        )

    def test_a_fade_alone_gets_merge_at_the_end(self) -> None:
        assert (
            merge_store_line("Store Sequence 3 Cue 7 CueFade 2")
            == "Store Sequence 3 Cue 7 CueFade 2 /Merge"
        )

    def test_an_exponent_fade_is_still_one_token(self) -> None:
        assert (
            merge_store_line("Store Sequence 3 Cue 7 CueFade 1e-05 /CueOnly")
            == "Store Sequence 3 Cue 7 CueFade 1e-05 /Merge /CueOnly"
        )

    def test_a_line_that_already_has_merge_is_unchanged(self) -> None:
        line = "Store Sequence 3 Cue 7 CueFade 2 /Merge /CueOnly"
        assert merge_store_line(line) == line

    @pytest.mark.parametrize(
        "line",
        [
            "ClearAll",
            "Store Timecode 20",
            "Store Cue 7 Sequence 3",  # 옛 어순 — 에미터가 더는 내지 않는 줄이다.
            "Store Sequence 3 Cue 7x",
            "Store Sequence 3",
            "",
        ],
    )
    def test_anything_that_is_not_a_cue_store_line_is_refused(self, line: str) -> None:
        with pytest.raises(ValueError):
            merge_store_line(line)

    def test_it_equals_what_cue_sheet_apply_builds_from_the_same_parts(self) -> None:
        # ``cue_sheet_apply`` 는 ``f"{store} /Merge{options}"`` 로 짓는다 — 같은 부품에서 같은
        # 줄이 나와야 한다.
        for fade in (None, 0.25, 2.0, 2.13618):
            store = store_with_fade("Store Sequence 9 Cue 4", fade)
            for options in ("", " /CueOnly"):
                emitter_line = store + options  # 에미터는 저장 줄 뒤에 옵션을 그대로 붙인다.
                assert merge_store_line(emitter_line) == f"{store} /Merge{options}"


_TIMING = SongTiming(bpm=120.0, beats_per_bar=4, downbeat_bar1_seconds=1.0)
_SEQUENCES = {"BACK": 1, "FOH": 2}


def _color_cell(bar: int, slot: int | None = None, **extra: object) -> dict:
    """승인된 색 프리셋 칸 — 위치가 안 바뀌어 MIB 큐가 끼지 않고, M1 항목에도 기대지 않는다."""
    return {
        "bar": bar,
        "color_preset_no": f"4.{slot or bar}",
        "evidence": _APPROVED_EVIDENCE,
        **extra,
    }


def _plan(tracks: list[dict]):
    """에미터 → 재반영 변환까지 — 세션이 쓰는 ``result`` 와 같은 모양(두 줄 다 소유한 시퀀스)."""
    result = emit_beat_grid_write_bundle(
        tracks,
        timing=_TIMING,
        sequence_numbers=_SEQUENCES,
        timecode_numbers={name: 20 for name in _SEQUENCES},
        dimmer_attributes={},
        probe_results={},
        song_end_seconds=30.0,
    )
    return apply_beat_grid_ownership_reuse(
        result, owned_sequences=_SEQUENCES, owned_timecode=None, recorded_cue_numbers={}
    )


def _two_track_plan():
    return _plan(
        [
            {
                "group_name": "BACK",
                "group_no": 7,
                "group_no_confirmed": True,
                "cues": [
                    _color_cell(1),
                    _color_cell(2, entry={"fade_bars": 1}),
                    _color_cell(4, entry={"tracking": "Cue Only", "fade_beats": 2}),
                ],
            },
            {
                "group_name": "FOH",
                "group_no": 8,
                "group_no_confirmed": True,
                "cues": [_color_cell(1), _color_cell(2), {"bar": 3}],
            },
        ]
    )


def _with_cue(result, track_index: int, cue_index: int, cue: CueEmitResult):
    """``result`` 의 한 큐를 바꿔 끼운 사본."""
    track = result.tracks[track_index]
    cues = list(track.cues)
    cues[cue_index] = cue
    tracks = list(result.tracks)
    tracks[track_index] = replace(track, cues=tuple(cues))
    return replace(result, tracks=tuple(tracks))


class TestCellApplyUnits:
    def test_only_the_selected_cells_are_kept_in_plan_order(self) -> None:
        units = cell_apply_units(
            _two_track_plan(), [("FOH", 2), ("BACK", 4)], owned_sequences=_SEQUENCES
        )  # 고른 순서와 무관하게 계획(줄·마디) 순서로 나온다
        assert list(units.units) == [("BACK", 4), ("FOH", 2)]
        assert units.not_applied == {}

    def test_cue_numbers_are_the_whole_song_numbers(self) -> None:
        # BACK 은 마디 1·2·4 가 큐 1·2·3 이다(빈 마디는 번호를 쓰지 않는다).
        units = cell_apply_units(
            _two_track_plan(), [("BACK", 4), ("BACK", 1), ("FOH", 2)], owned_sequences=_SEQUENCES
        )
        assert units.cue_numbers == {("BACK", 1): 1, ("BACK", 4): 3, ("FOH", 2): 2}

    def test_the_first_cue_loses_the_rebuild_lines_but_keeps_its_values(self) -> None:
        units = cell_apply_units(_two_track_plan(), [("BACK", 1)], owned_sequences=_SEQUENCES)
        assert units.units[("BACK", 1)] == (
            "Group 7 ; At Preset 4.1",
            "Store Sequence 1 Cue 1 /Merge",
            "ClearAll",
            "Set Cue 1 Sequence 1 Property 'TrigType' 'Time'",
            "Set Cue 1 Sequence 1 Property 'TrigTime' 1",
        )

    def test_the_whole_song_plan_really_carries_the_lines_the_unit_drops(self) -> None:
        # 위 단언이 공허하지 않다는 증거 — 같은 큐의 전체 반영 줄에는 이 줄들이 있다.
        first = _two_track_plan().tracks[0].cues[0].commands
        assert "Delete Sequence 1 /NoConfirm" in first
        assert any(line.startswith("Set Sequence 1 Property 'Name'") for line in first)
        assert "Set Sequence 1 Property 'WrapAround' 0" in first

    def test_a_fade_and_an_option_keep_their_order_inside_the_unit(self) -> None:
        units = cell_apply_units(_two_track_plan(), [("BACK", 4)], owned_sequences=_SEQUENCES)
        stores = [line for line in units.units[("BACK", 4)] if line.startswith("Store Sequence")]
        assert stores == ["Store Sequence 1 Cue 3 CueFade 1 /Merge /CueOnly"]

    def test_unchanged_cells_are_reported_and_never_sent(self) -> None:
        units = cell_apply_units(
            _two_track_plan(),
            [("BACK", 1), ("BACK", 2)],
            owned_sequences=_SEQUENCES,
            unchanged=[("BACK", 1)],
        )
        assert list(units.units) == [("BACK", 2)]
        assert units.not_applied == {("BACK", 1): CELL_UNCHANGED_REASON}
        assert CELL_UNCHANGED_REASON == "콘솔과 같음(바뀐 칸 아님)"

    def test_refused_cells_never_reach_the_units_or_the_cue_numbers(self) -> None:
        reason = "지운 항목(color_preset_no)은 콘솔에 남아 있어 칸 단위로 지울 수 없습니다"
        units = cell_apply_units(
            _two_track_plan(),
            [("BACK", 1), ("BACK", 2), ("FOH", 1)],
            owned_sequences=_SEQUENCES,
            refused={("BACK", 2): reason, ("ZZZ", 9): "고르지 않은 칸의 사유는 무시한다"},
        )
        assert list(units.units) == [("BACK", 1), ("FOH", 1)]  # 나머지는 그대로 나간다
        assert ("BACK", 2) not in units.cue_numbers
        assert units.not_applied == {("BACK", 2): reason}

    def test_an_unchanged_cell_keeps_its_own_reason_over_a_refusal(self) -> None:
        units = cell_apply_units(
            _two_track_plan(),
            [("BACK", 1)],
            owned_sequences=_SEQUENCES,
            unchanged=[("BACK", 1)],
            refused={("BACK", 1): "다른 사유"},
        )
        assert units.not_applied == {("BACK", 1): CELL_UNCHANGED_REASON}

    def test_a_cell_without_lines_is_reported(self) -> None:
        units = cell_apply_units(_two_track_plan(), [("FOH", 3)], owned_sequences=_SEQUENCES)
        assert units.units == {}
        assert "보낼 줄이 없습니다" in units.not_applied[("FOH", 3)]

    def test_a_blocked_cell_carries_the_emitters_own_reason(self) -> None:
        blocked = _color_cell(2, brightness={"mode": "value", "value_percent": 50})
        result = _plan(
            [
                {
                    "group_name": "BACK",
                    "group_no": 7,
                    "group_no_confirmed": True,
                    "cues": [_color_cell(1), blocked],
                }
            ]
        )
        emitter_reason = result.tracks[0].cues[1].blocked_reason
        assert emitter_reason
        units = cell_apply_units(result, [("BACK", 2), ("BACK", 1)], owned_sequences=_SEQUENCES)
        assert list(units.units) == [("BACK", 1)]
        assert units.not_applied == {("BACK", 2): emitter_reason}

    def test_cells_the_plan_does_not_know_are_reported(self) -> None:
        units = cell_apply_units(
            _two_track_plan(), [("FOH", 9), ("ZZZ", 1)], owned_sequences=_SEQUENCES
        )
        assert units.units == {}
        assert set(units.not_applied) == {("FOH", 9), ("ZZZ", 1)}

    def test_a_cell_of_a_track_that_is_not_an_owned_console_sequence_is_not_sent(self) -> None:
        units = cell_apply_units(
            _two_track_plan(), [("BACK", 1), ("FOH", 1)], owned_sequences={"BACK": 1}
        )
        assert list(units.units) == [("BACK", 1)]
        assert "콘솔에 만들어진 시퀀스가 아니라서" in units.not_applied[("FOH", 1)]

    def test_a_planned_sequence_number_that_differs_from_the_owned_one_is_not_sent(self) -> None:
        units = cell_apply_units(_two_track_plan(), [("BACK", 1)], owned_sequences={"BACK": 5})
        assert units.units == {}
        assert ("BACK", 1) in units.not_applied

    def test_a_forbidden_line_inside_a_cue_keeps_that_cell_out(self) -> None:
        result = _two_track_plan()
        cue = result.tracks[0].cues[1]
        tampered = _with_cue(
            result, 0, 1, replace(cue, commands=(*cue.commands, "Store Timecode 20.1"))
        )
        units = cell_apply_units(tampered, [("BACK", 2), ("BACK", 1)], owned_sequences=_SEQUENCES)
        assert list(units.units) == [("BACK", 1)]
        assert "Store Timecode 20.1" in units.not_applied[("BACK", 2)]

    def test_a_line_touching_another_sequence_keeps_that_cell_out(self) -> None:
        result = _two_track_plan()
        cue = result.tracks[0].cues[1]
        extra = "Set Cue 1 Sequence 9 Property 'TrigType' 'Time'"
        tampered = _with_cue(result, 0, 1, replace(cue, commands=(*cue.commands, extra)))
        units = cell_apply_units(tampered, [("BACK", 2)], owned_sequences=_SEQUENCES)
        assert units.units == {}
        assert "Sequence 9" in units.not_applied[("BACK", 2)]

    def test_a_cue_with_two_store_lines_is_not_guessed_at(self) -> None:
        result = _two_track_plan()
        cue = result.tracks[0].cues[1]
        tampered = _with_cue(
            result, 0, 1, replace(cue, commands=(*cue.commands, "Store Sequence 1 Cue 9"))
        )
        units = cell_apply_units(tampered, [("BACK", 2)], owned_sequences=_SEQUENCES)
        assert units.units == {}
        assert ("BACK", 2) in units.not_applied

    def test_a_mib_premove_cue_is_never_a_grid_cell(self) -> None:
        result = _two_track_plan()
        track = result.tracks[0]
        premove = CueEmitResult(
            bar=3,
            commands=("Group 7 ; At Preset 2.9", "Store Sequence 1 Cue 9", "ClearAll"),
            blocked_reason=None,
            cue_number=9,
            premove=True,
        )
        with_premove = replace(
            result, tracks=(replace(track, cues=(*track.cues, premove)), *result.tracks[1:])
        )
        units = cell_apply_units(with_premove, [("BACK", 3)], owned_sequences=_SEQUENCES)
        assert units.units == {}
        assert ("BACK", 3) in units.not_applied

    def test_duplicates_in_the_selection_count_once(self) -> None:
        units = cell_apply_units(
            _two_track_plan(), [("BACK", 1), ("BACK", 1)], owned_sequences=_SEQUENCES
        )
        assert list(units.units) == [("BACK", 1)]

    def test_the_recorded_cue_numbers_gate_each_cell(self) -> None:
        recorded = {"BACK": {"cues": {"1": 1, "2": 2, "4": 9}}, "FOH": {"cues": {"1": 1, "2": 2}}}
        units = cell_apply_units(
            _two_track_plan(),
            [("BACK", 2), ("BACK", 4), ("FOH", 2)],
            owned_sequences=_SEQUENCES,
            recorded_tracks=recorded,
        )
        assert list(units.units) == [("BACK", 2), ("FOH", 2)]
        assert "큐 9번" in units.not_applied[("BACK", 4)]

    def test_no_unit_of_any_cell_carries_a_forbidden_line(self) -> None:
        result = _two_track_plan()
        every_cell = [(t.group_name, c.bar) for t in result.tracks for c in t.cues]
        units = cell_apply_units(result, every_cell, owned_sequences=_SEQUENCES)
        assert units.units  # 공허하지 않다
        lines = [line for unit in units.units.values() for line in unit]
        stored = {(_SEQUENCES[name], units.cue_numbers[(name, bar)]) for name, bar in units.units}
        violation = subset_line_violation(
            lines, sequence_numbers=set(_SEQUENCES.values()), store_cues=stored
        )
        assert violation is None


class TestRemovedCueFields:
    def test_a_newly_added_key_is_not_a_removal(self) -> None:
        assert removed_cue_fields({"bar": 2}, {"bar": 2, "color_preset_no": "4.2"}) == ()
        # 이전에 값이 없던 키(None)가 값을 얻은 것도 지움이 아니다.
        assert removed_cue_fields({"color_preset_no": None}, {"color_preset_no": "4.2"}) == ()

    def test_a_changed_value_is_not_a_removal(self) -> None:
        assert removed_cue_fields({"color_preset_no": "4.2"}, {"color_preset_no": "4.3"}) == ()
        assert removed_cue_fields({"entry": {"fade_bars": 1}}, {"entry": {"fade_bars": 2}}) == ()

    @pytest.mark.parametrize("emptied", [None, "", [], {}], ids=["none", "text", "list", "dict"])
    def test_an_emptied_key_is_a_removal(self, emptied: object) -> None:
        assert removed_cue_fields({"color_preset_no": "4.2"}, {"color_preset_no": emptied}) == (
            "color_preset_no",
        )

    def test_a_key_that_disappeared_is_a_removal(self) -> None:
        assert removed_cue_fields({"bar": 2, "color_preset_no": "4.2"}, {"bar": 2}) == (
            "color_preset_no",
        )

    @pytest.mark.parametrize(
        "key",
        [
            "position_preset_name",
            "color_preset_name",
            "effect_preset_name",
            "color_planned",
            "planned_color",
            "planned_position",
            "planned_dimmer_name",
            "planned_position_name",
            "color_rgb",
        ],
    )
    def test_an_emptied_display_only_key_is_not_a_removal(self, key: str) -> None:
        assert removed_cue_fields({"bar": 2, key: "x"}, {"bar": 2, key: None}) == ()
        assert removed_cue_fields({"bar": 2, key: "x"}, {"bar": 2}) == ()

    def test_a_cleared_approval_record_is_not_a_removal(self) -> None:
        # 프리셋 번호를 바꾸면 그 칸의 승인(``evidence.approval``)이 지워져 승인 대기가 된다 — 승인
        # 기록은 콘솔 값이 아니라서 지운 항목이 아니다(아니면 승인 대기 칸이 늘 거절된다).
        approved = {"grade": "A", "approval": {"by": "supervisor", "date": "d", "source": "s"}}
        previous = {"color_preset_no": "4.2", "evidence": approved}
        assert removed_cue_fields(previous, {"color_preset_no": "4.5", "evidence": None}) == ()
        assert removed_cue_fields(previous, {"color_preset_no": "4.5"}) == ()
        # 같은 칸에서 정말 지운 색 번호는 여전히 잡힌다.
        assert removed_cue_fields(previous, {"color_preset_no": None, "evidence": None}) == (
            "color_preset_no",
        )

    def test_the_names_come_back_sorted(self) -> None:
        previous = {"position_preset_no": "2.1", "color_preset_no": "4.2", "bar": 2}
        assert removed_cue_fields(previous, {"bar": 2}) == ("color_preset_no", "position_preset_no")

    def test_a_key_that_was_already_empty_is_never_a_removal(self) -> None:
        assert removed_cue_fields({"color_preset_no": None, "label": ""}, {}) == ()

    def test_zero_and_false_are_values_not_blanks(self) -> None:
        assert removed_cue_fields({"gain": 0}, {"gain": None}) == ("gain",)
        assert removed_cue_fields({"gain": 5}, {"gain": 0}) == ()
        assert removed_cue_fields({"flag": False}, {}) == ("flag",)

    def test_a_cleared_container_is_named_by_the_leaves_that_were_set(self) -> None:
        # 정규화된 칸은 밝기·들어올 때를 값이 전부 None 인 사전으로 둔다 —
        # 속의 잎마다 이름이 나온다.
        value = {"mode": "value", "value_percent": 70, "preset_no": None}
        blank = {"mode": None, "value_percent": None, "preset_no": None}
        assert removed_cue_fields({"brightness": value}, {"brightness": blank}) == (
            "brightness.mode",
            "brightness.value_percent",
        )
        fade = {"fade_bars": 1, "mib_mode": None, "fade_beats": None}
        assert removed_cue_fields({"entry": fade}, {"entry": {**blank, "fade_bars": None}}) == (
            "entry.fade_bars",
        )
        # 속이 여전히 값을 가진 잎은 값이 바뀌어도 지움이 아니다.
        assert removed_cue_fields(
            {"brightness": value}, {"brightness": {**blank, "mode": "x"}}
        ) == ("brightness.value_percent",)


_MOVEMENT = {
    "shape": "wave",
    "axes": ["Tilt"],
    "period_unit": "beat",
    "period_value": 2,
    "phase_spread": None,
}
_BRIGHT = {"mode": "value", "value_percent": 70, "preset_no": None}


class TestRemovedCueFieldsNested:
    """속이 있는 항목(앱 움직임·밝기·들어올 때)은 잎마다 점 경로로 본다."""

    def test_a_cleared_shape_is_named_while_speed_and_axis_stay(self) -> None:
        previous = {"app_movement": _MOVEMENT}
        current = {"app_movement": {**_MOVEMENT, "shape": None}}
        assert removed_cue_fields(previous, current) == ("app_movement.shape",)

    def test_a_cleared_brightness_percent_is_named_while_the_mode_stays(self) -> None:
        previous = {"brightness": _BRIGHT}
        current = {"brightness": {**_BRIGHT, "value_percent": None}}
        assert removed_cue_fields(previous, current) == ("brightness.value_percent",)

    def test_a_cleared_fade_is_named(self) -> None:
        previous = {"entry": {"fade_bars": 1, "tracking": "Release"}}
        current = {"entry": {"fade_bars": None, "tracking": "Release"}}
        assert removed_cue_fields(previous, current) == ("entry.fade_bars",)

    def test_several_cleared_leaves_come_back_sorted(self) -> None:
        previous = {"app_movement": _MOVEMENT, "color_preset_no": "4.2"}
        current = {
            "app_movement": {**_MOVEMENT, "shape": None, "axes": []},
            "color_preset_no": None,
        }
        assert removed_cue_fields(previous, current) == (
            "app_movement.axes",
            "app_movement.shape",
            "color_preset_no",
        )

    def test_a_nested_value_that_changed_but_is_still_set_is_not_a_removal(self) -> None:
        previous = {"app_movement": _MOVEMENT, "brightness": _BRIGHT, "entry": {"fade_bars": 1}}
        current = {
            "app_movement": {**_MOVEMENT, "period_value": 4, "shape": "circle"},
            "brightness": {**_BRIGHT, "value_percent": 50},
            "entry": {"fade_bars": 2},
        }
        assert removed_cue_fields(previous, current) == ()

    def test_a_nested_key_that_was_added_is_not_a_removal(self) -> None:
        previous = {"entry": {"fade_bars": 1}, "app_movement": None, "brightness": {"mode": None}}
        current = {
            "entry": {"fade_bars": 1, "tracking": "Release"},
            "app_movement": _MOVEMENT,
            "brightness": _BRIGHT,
        }
        assert removed_cue_fields(previous, current) == ()

    def test_an_object_that_vanished_is_one_removal_at_its_own_key(self) -> None:
        assert removed_cue_fields({"app_movement": _MOVEMENT}, {"app_movement": None}) == (
            "app_movement",
        )
        assert removed_cue_fields({"app_movement": _MOVEMENT}, {}) == ("app_movement",)

    def test_an_object_that_held_nothing_is_not_a_removal(self) -> None:
        blank = {"mode": None, "value_percent": None, "preset_no": None}
        assert removed_cue_fields({"brightness": blank}, {"brightness": None}) == ()
        assert removed_cue_fields({"brightness": blank}, {}) == ()

    def test_an_object_replaced_by_a_set_value_is_not_a_removal(self) -> None:
        assert removed_cue_fields({"entry": {"fade_bars": 1}}, {"entry": "x"}) == ()

    def test_lists_are_not_entered(self) -> None:
        both = {"app_movement": {**_MOVEMENT, "axes": ["Pan", "Tilt"]}}
        # 목록이 줄어도 아직 값이 있으면 지움이 아니다.
        one = {"app_movement": {**_MOVEMENT, "axes": ["Pan"]}}
        assert removed_cue_fields(both, one) == ()
        # 비지 않은 목록이 비게 되면 그 키 하나가 지움이다.
        none = {"app_movement": {**_MOVEMENT, "axes": []}}
        assert removed_cue_fields(both, none) == ("app_movement.axes",)
        # 목록 안의 사전 속은 보지 않는다.
        assert removed_cue_fields({"x": [{"a": 1, "b": 2}]}, {"x": [{"a": 1}]}) == ()
        assert removed_cue_fields({"x": [{"a": 1}]}, {"x": [{"a": None}]}) == ("x",)

    def test_color_rgb_is_ignored_at_any_depth(self) -> None:
        previous = {"color_rgb": [1, 2, 3], "split": {"left": {"color": "x", "color_rgb": [1, 2]}}}
        current = {"color_rgb": None, "split": {"left": {"color": "x", "color_rgb": None}}}
        assert removed_cue_fields(previous, current) == ()
        current["split"]["left"]["color"] = None
        assert removed_cue_fields(previous, current) == ("split.left.color",)

    def test_the_display_only_ignore_set_applies_only_at_the_top_level(self) -> None:
        top = removed_cue_fields({"position_preset_name": "A"}, {"position_preset_name": None})
        assert top == ()
        nested = {"x": {"position_preset_name": "A"}}
        assert removed_cue_fields(nested, {"x": {"position_preset_name": None}}) == (
            "x.position_preset_name",
        )


class TestCellsWithRemovedFields:
    def test_a_removed_field_names_the_cell_and_the_fields(self) -> None:
        previous = {("BACK", 2): {"bar": 2, "color_preset_no": "4.2", "effect_preset_no": "22.1"}}
        current = {("BACK", 2): {"bar": 2, "color_preset_no": None, "effect_preset_no": None}}
        reasons = cells_with_removed_fields(previous, current, [("BACK", 2)])
        assert reasons == {
            ("BACK", 2): (
                "지운 항목(color_preset_no, effect_preset_no)은 콘솔에 남아 있어 칸 단위로 지울 수 "
                "없습니다 — 전체 「⇪ 콘솔에 반영」으로 지워 주세요"
            )
        }

    def test_a_nested_leaf_is_named_by_its_dotted_path_in_the_reason(self) -> None:
        previous = {("BACK", 2): {"bar": 2, "app_movement": _MOVEMENT}}
        current = {("BACK", 2): {"bar": 2, "app_movement": {**_MOVEMENT, "shape": None}}}
        (reason,) = cells_with_removed_fields(previous, current, [("BACK", 2)]).values()
        assert reason.startswith("지운 항목(app_movement.shape)은 콘솔에 남아 있어")

    def test_only_the_given_cells_are_looked_at(self) -> None:
        previous = {
            ("BACK", 1): {"color_preset_no": "4.1"},
            ("BACK", 2): {"color_preset_no": "4.2"},
        }
        current = {("BACK", 1): {"color_preset_no": None}, ("BACK", 2): {"color_preset_no": None}}
        assert set(cells_with_removed_fields(previous, current, [("BACK", 2)])) == {("BACK", 2)}

    def test_a_cell_the_last_apply_did_not_have_has_nothing_to_remove(self) -> None:
        current = {("BACK", 5): {"bar": 5}}
        assert cells_with_removed_fields({}, current, [("BACK", 5)]) == {}
        assert cells_with_removed_fields(None, current, [("BACK", 5)]) == {}

    def test_an_unchanged_value_is_not_reported(self) -> None:
        body = {("BACK", 2): {"color_preset_no": "4.2"}}
        assert cells_with_removed_fields(body, body, [("BACK", 2)]) == {}


class TestRecordedCueConflict:
    def test_same_number_is_fine(self) -> None:
        assert recorded_cue_conflict({"1": 1, "2": 2}, 2, 2) is None

    def test_a_shifted_number_is_a_conflict(self) -> None:
        reason = recorded_cue_conflict({"1": 1, "2": 2, "4": 3}, 4, 4)
        assert reason is not None
        assert "큐 3번" in reason
        assert "큐 4번" in reason

    def test_a_new_cell_on_a_number_another_bar_uses_is_a_conflict(self) -> None:
        reason = recorded_cue_conflict({"1": 1, "2": 2, "4": 3}, 3, 3)
        assert reason is not None
        assert "4마디" in reason

    def test_a_new_cell_appended_after_every_recorded_cue_is_fine(self) -> None:
        assert recorded_cue_conflict({"1": 1, "2": 2, "4": 3}, 5, 4) is None

    def test_garbage_in_the_record_is_ignored_not_trusted(self) -> None:
        assert recorded_cue_conflict({"x": "y", "2": None, "3": 3}, 5, 4) is None
        assert recorded_cue_conflict({}, 1, 1) is None


#: 칸 단위 반영 묶음에 한 줄도 있으면 안 되는 줄의 머리 — 리드의 금지 목록을 그대로 옮겼다.
#: (모듈 상수를 가져다 쓰지 않는다: 상수가 줄어들면 이 시험이 같이 느슨해지기 때문이다.)
_FORBIDDEN_PREFIXES = (
    "Delete",
    "Store Timecode",
    "Store Preset",
    "Label Preset",
    "Store Type",
    "Store Property",
    "Set Sequence",
)


class TestSubsetLineViolation:
    _OK = [
        "Group 7 ; At Preset 4.2",
        "Store Sequence 1 Cue 2 CueFade 2 /Merge",
        "ClearAll",
        "Set Cue 2 Sequence 1 Property 'TrigType' 'Time'",
        "Set Cue 2 Sequence 1 Property 'TrigTime' 3",
        "Set Cue 2 Sequence 1 Property 'Release' 1",
        "Block Sequence 1 Cue 2",
    ]

    def _check(self, lines: list[str]) -> str | None:
        return subset_line_violation(lines, sequence_numbers={1}, store_cues={(1, 2)})

    def test_the_allowed_kinds_pass(self) -> None:
        assert self._check(self._OK) is None

    @pytest.mark.parametrize("prefix", _FORBIDDEN_PREFIXES)
    def test_every_forbidden_prefix_is_caught(self, prefix: str) -> None:
        assert self._check([*self._OK, f"{prefix} 1 /NoConfirm"]) is not None

    @pytest.mark.parametrize(
        "line",
        [
            "Delete Sequence 1 /NoConfirm",
            "Delete Cue 2 Sequence 1",
            "Delete Timecode 20 /NoConfirm",
            "Store Timecode 20",
            "Store Preset 4.5",
            "Label Preset 4.5 'x'",
            "Store Type 'CmdSubTrack' Timecode 20.1.1.1",
            "Store Property 'Time' 1 'AbsTime' 1 'Token' 'Go+'",
            "Set Sequence 1 Property 'Name' 'LDBEAT BACK'",
            "Set Sequence 1 Property 'WrapAround' 0",
        ],
    )
    def test_the_lead_listed_lines_are_caught(self, line: str) -> None:
        assert self._check([line]) is not None

    def test_a_store_line_for_a_cue_that_was_not_chosen_is_caught(self) -> None:
        assert self._check(["Store Sequence 1 Cue 3 /Merge"]) is not None
        assert self._check(["Store Sequence 2 Cue 2 /Merge"]) is not None

    def test_a_line_touching_another_sequence_is_caught(self) -> None:
        assert self._check(["Set Cue 2 Sequence 2 Property 'TrigTime' 3"]) is not None
        assert self._check(["Block Sequence 9 Cue 2"]) is not None

    def test_the_first_offender_is_named(self) -> None:
        reason = self._check(["ClearAll", "Delete Sequence 1 /NoConfirm"])
        assert reason is not None
        assert "Delete Sequence 1" in reason

    def test_an_empty_batch_has_no_violation(self) -> None:
        assert self._check([]) is None


class TestMergeCellSnapshot:
    def test_applied_cells_take_the_current_value_and_the_rest_keep_the_old_one(self) -> None:
        existing = {
            ("BACK", 1): {"v": "old1"},
            ("BACK", 2): {"v": "old2"},
            ("FOH", 1): {"v": "old3"},
        }
        current = {
            ("BACK", 1): {"v": "new1"},
            ("BACK", 2): {"v": "new2"},
            ("FOH", 1): {"v": "new3"},
        }
        merged = merge_cell_snapshot(existing, current, [("BACK", 2)])
        assert merged == {
            ("BACK", 1): {"v": "old1"},
            ("BACK", 2): {"v": "new2"},
            ("FOH", 1): {"v": "old3"},
        }

    def test_the_input_snapshot_is_not_mutated(self) -> None:
        existing = {("BACK", 1): {"v": "old"}}
        before = copy.deepcopy(existing)
        merge_cell_snapshot(existing, {("BACK", 1): {"v": "new"}}, [("BACK", 1)])
        assert existing == before

    def test_with_no_earlier_snapshot_it_starts_a_partial_one_from_the_sent_cells(self) -> None:
        current = {("BACK", 1): {"v": 1}, ("BACK", 2): {"v": 2}}
        merged = merge_cell_snapshot(None, current, [("BACK", 2)])
        assert merged == {("BACK", 2): {"v": 2}}
        assert isinstance(merged, PartialCellSnapshot)  # 나머지 칸은 모른다 — 전체 기록이 아니다

    def test_a_full_snapshot_stays_full(self) -> None:
        existing = {("BACK", 1): {"v": 1}, ("BACK", 2): {"v": 2}}
        merged = merge_cell_snapshot(existing, {("BACK", 2): {"v": 9}}, [("BACK", 2)])
        assert merged == {("BACK", 1): {"v": 1}, ("BACK", 2): {"v": 9}}
        assert not isinstance(merged, PartialCellSnapshot)

    def test_a_partial_snapshot_stays_partial_and_gains_the_sent_cells(self) -> None:
        existing = PartialCellSnapshot({("BACK", 2): {"v": 2}})
        current = {("BACK", 2): {"v": 2}, ("FOH", 3): {"v": 3}, ("FOH", 4): {"v": 4}}
        merged = merge_cell_snapshot(existing, current, [("FOH", 3)])
        assert isinstance(merged, PartialCellSnapshot)
        assert merged == {("BACK", 2): {"v": 2}, ("FOH", 3): {"v": 3}}  # FOH 4 는 계속 모르는 칸
        assert existing == {("BACK", 2): {"v": 2}}  # 입력은 그대로

    def test_an_unselected_changed_cell_stays_unsent_after_the_merge(self) -> None:
        def grid(entries: dict[int, str]) -> dict:
            cues = [{"bar": bar, "position_preset_no": no} for bar, no in entries.items()]
            return {"tracks": [{"group_name": "BACK", "cues": cues}]}

        snapshot = beat_grid_cell_snapshot(grid({1: "2.1", 2: "2.2", 3: "2.3"}))
        edited = grid({1: "2.1", 2: "2.9", 3: "2.8"})  # 2·3마디가 바뀌었다
        merged = merge_cell_snapshot(snapshot, beat_grid_cell_snapshot(edited), [("BACK", 2)])
        assert unsent_beat_grid_cells(edited, merged) == [{"group_name": "BACK", "bar": 3}]


def _bars_grid(group: str, entries: dict[int, str]) -> dict:
    """줄 하나에 마디마다 위치 프리셋 번호만 가진 최소 격자."""
    cues = [{"bar": bar, "position_preset_no": no} for bar, no in entries.items()]
    return {"tracks": [{"group_name": group, "cues": cues}]}


def _partial_of(grid: dict, *bars: int, group: str = "BACK") -> PartialCellSnapshot:
    """``grid`` 의 지정한 마디만 담은 부분 기록 — 나머지 칸은 모르는 칸이다."""
    cells = beat_grid_cell_snapshot(grid)
    return PartialCellSnapshot({key: cells[key] for key in ((group, bar) for bar in bars)})


class TestUnsentOverAPartialSnapshot:
    def test_cells_absent_from_the_snapshot_are_unknown_not_unsent(self) -> None:
        grid = _bars_grid("BACK", {1: "2.1", 2: "2.2", 3: "2.3"})
        # 2마디만 아는 기록 — 1·3마디는 콘솔과 같은지 다른지 모른다.
        assert unsent_beat_grid_cells(grid, _partial_of(grid, 2)) == []

    def test_a_known_cell_that_differs_is_unsent_and_unknown_neighbours_are_not(self) -> None:
        then = _bars_grid("BACK", {1: "2.1", 2: "2.2", 3: "2.3"})
        now = _bars_grid("BACK", {1: "2.9", 2: "2.8", 3: "2.7"})  # 세 칸 모두 바뀌었다
        assert unsent_beat_grid_cells(now, _partial_of(then, 2)) == [
            {"group_name": "BACK", "bar": 2}
        ]

    def test_a_known_cell_that_is_the_same_is_not_listed(self) -> None:
        then = _bars_grid("BACK", {1: "2.1", 2: "2.2"})
        now = _bars_grid("BACK", {1: "2.9", 2: "2.2"})
        assert unsent_beat_grid_cells(now, _partial_of(then, 2)) == []

    def test_a_known_cell_that_left_the_grid_is_unsent(self) -> None:
        then = _bars_grid("BACK", {1: "2.1", 2: "2.2"})
        now = _bars_grid("BACK", {1: "2.1"})  # 2마디가 사라졌다
        assert unsent_beat_grid_cells(now, _partial_of(then, 2)) == [
            {"group_name": "BACK", "bar": 2}
        ]

    def test_a_full_snapshot_still_counts_a_cell_it_never_saw(self) -> None:
        # 대조군 — 전체 기록에 없는 칸은 새 칸(바뀐 칸)이지만, 부분 기록에서는 모르는 칸이다.
        then = _bars_grid("BACK", {1: "2.1"})
        now = _bars_grid("BACK", {1: "2.1", 2: "2.2"})
        assert unsent_beat_grid_cells(now, beat_grid_cell_snapshot(then)) == [
            {"group_name": "BACK", "bar": 2}
        ]
        assert unsent_beat_grid_cells(now, _partial_of(then, 1)) == []

    def test_a_partial_snapshot_gives_a_list_never_none(self) -> None:
        grid = _bars_grid("BACK", {1: "2.1"})
        assert unsent_beat_grid_cells(grid, PartialCellSnapshot()) == []
        assert unsent_beat_grid_cells(grid, None) is None


class TestSnapshotKnownCells:
    def test_only_a_partial_snapshot_lists_its_cells_sorted(self) -> None:
        partial = PartialCellSnapshot({("FOH", 3): {}, ("BACK", 5): {}, ("BACK", 2): {}})
        assert snapshot_known_cells(partial) == [["BACK", 2], ["BACK", 5], ["FOH", 3]]

    def test_a_full_snapshot_or_none_has_nothing_to_list(self) -> None:
        assert snapshot_known_cells({("BACK", 2): {}}) is None
        assert snapshot_known_cells(None) is None


class TestMergeAppliedCuesIntoRecord:
    _RECORD = {
        "timecode_number": 20,
        "timecode_name": "LDBEAT Timecode 20",
        "extra_timecodes": [{"timecode_number": 21, "timecode_name": "LDBEAT Timecode 21"}],
        "tracks": {
            "BACK": {
                "sequence_number": 1,
                "sequence_name": "LDBEAT BACK",
                "cues": {"1": 1, "2": 2},
            },
            "FOH": {"sequence_number": 2, "sequence_name": "LDBEAT FOH", "cues": {"1": 1}},
            "OLD": {"sequence_number": 3, "sequence_name": "LDBEAT OLD", "cues": {"1": 1}},
        },
    }

    def test_only_the_applied_cue_numbers_change(self) -> None:
        merged = merge_applied_cues_into_record(self._RECORD, {"BACK": {2: 2, 5: 4}})
        assert merged["tracks"]["BACK"]["cues"] == {"1": 1, "2": 2, "5": 4}
        # 다른 줄과 줄 이름·번호, 타임코드 이름·번호, 추가 타임코드는 그대로다
        # (사라진 줄 정리도 없다).
        assert merged["tracks"]["FOH"] == self._RECORD["tracks"]["FOH"]
        assert merged["tracks"]["OLD"] == self._RECORD["tracks"]["OLD"]
        assert merged["tracks"]["BACK"]["sequence_number"] == 1
        assert merged["tracks"]["BACK"]["sequence_name"] == "LDBEAT BACK"
        for key in ("timecode_number", "timecode_name", "extra_timecodes"):
            assert merged[key] == self._RECORD[key]

    def test_the_input_record_is_not_mutated(self) -> None:
        before = copy.deepcopy(self._RECORD)
        merge_applied_cues_into_record(self._RECORD, {"BACK": {9: 9}})
        assert before == self._RECORD

    def test_an_existing_cue_number_is_replaced_by_the_stored_one(self) -> None:
        merged = merge_applied_cues_into_record(self._RECORD, {"FOH": {1: 7}})
        assert merged["tracks"]["FOH"]["cues"] == {"1": 7}

    def test_a_track_missing_from_the_record_is_not_invented(self) -> None:
        merged = merge_applied_cues_into_record(self._RECORD, {"NEW": {1: 1}})
        assert "NEW" not in merged["tracks"]
        assert merged == self._RECORD

    def test_a_record_without_cues_gets_them_for_the_applied_track_only(self) -> None:
        record = {"tracks": {"BACK": {"sequence_number": 1, "sequence_name": "LDBEAT BACK"}}}
        merged = merge_applied_cues_into_record(record, {"BACK": {3: 2}})
        assert merged["tracks"]["BACK"]["cues"] == {"3": 2}


class TestCellsNeedingWholeApply:
    def test_each_kind_names_its_cells_and_labels(self) -> None:
        found = cells_needing_whole_apply(
            held=[{"group_name": "FOH", "bar": 1}, {"group_name": "BACK", "bar": 2}],
            released=[{"group_name": "BACK", "bar": 2}, {"group_name": "FOH", "bar": 4}],
        )
        assert found == {
            ("FOH", 1): ["빈 프리셋 보류"],
            ("BACK", 2): ["빈 프리셋 보류", "새로 만들 프리셋"],
            ("FOH", 4): ["새로 만들 프리셋"],
        }

    def test_a_pending_approval_is_not_a_reason_to_need_the_whole_apply(self) -> None:
        # 콘솔에 이미 있는 번호의 승인 대기 칸은 칸 단위 반영이 맡는다 — 이 함수는 더 받지도 않는다.
        with pytest.raises(TypeError):
            cells_needing_whole_apply(  # type: ignore[call-arg]
                pending=[{"group_name": "BACK", "bar": 2}], held=[], released=[]
            )

    def test_entries_without_a_real_bar_are_skipped(self) -> None:
        found = cells_needing_whole_apply(
            held=[{"group_name": "BACK", "bar": None}, {"group_name": "BACK", "bar": True}],
            released=[],
        )
        assert found == {}


class TestOwnedRecordHasTracks:
    def test_a_record_with_a_track_counts(self) -> None:
        assert owned_record_has_tracks({"tracks": {"BACK": {"sequence_number": 1}}}) is True

    @pytest.mark.parametrize(
        "record",
        [
            pytest.param(None, id="no-record"),
            pytest.param({}, id="empty-record"),
            pytest.param({"tracks": {}}, id="no-tracks"),
            pytest.param({"tracks": None}, id="tracks-null"),
            pytest.param({"tracks": [{"sequence_number": 1}]}, id="tracks-not-a-mapping"),
            pytest.param({"timecode_number": 20}, id="timecode-only"),
        ],
    )
    def test_anything_without_a_track_does_not(self, record) -> None:
        assert owned_record_has_tracks(record) is False


class TestPartialApplyBaseline:
    @pytest.mark.parametrize(
        ("has_snapshot", "has_owned_record", "expected"),
        [
            (True, True, "snapshot"),
            (True, False, "snapshot"),
            (False, True, "record"),
            (False, False, None),
        ],
    )
    def test_the_snapshot_wins_then_the_record_then_nothing(
        self, has_snapshot, has_owned_record, expected
    ) -> None:
        assert (
            partial_apply_baseline(has_snapshot=has_snapshot, has_owned_record=has_owned_record)
            == expected
        )


class TestFormatCellList:
    def test_names_every_cell(self) -> None:
        assert format_cell_list([("BACK", 3), ("FOH", 7)]) == "BACK 3마디, FOH 7마디"

    def test_a_limit_shortens_the_list(self) -> None:
        cells = [("BACK", bar) for bar in range(1, 6)]
        assert format_cell_list(cells, limit=2) == "BACK 1마디, BACK 2마디 외 3칸"
        assert format_cell_list(cells, limit=5) == format_cell_list(cells)


# =============================================================================
# 3. 세션 통합 — ChatSession.beat_grid_apply(cells=…) / beat_grid_edit(cells=…)
#    (test_beat_grid_send_t563 의 가짜 콘솔 하네스 ``_new_session`` 을 그대로 쓴다)
# =============================================================================

SONG_KEY = ("LOVE ATTACK", 210)
#: 칸을 "바뀐 칸"으로 만드는 가장 작은 편집 — 프리셋 번호를 건드리지 않아 승인 대기가 생기지 않는다.
ENTRY = {"entry": {"fade_bars": 1, "mib_mode": None}}
_FADE_STORE = re.compile(r"Store Sequence (\d+) Cue (\d+) CueFade [0-9.]+ /Merge")
#: 칸 기록(스냅샷)도 소유 기록도 없는 곡의 거절 사유 — 칸 단위로 보낼 기준이 전혀 없다.
NO_RECORD_REASON = "이 곡은 아직 콘솔 반영 기록이 없어요 — 「전체 다시 반영」으로 먼저 맞춰 주세요."
#: 칸에서 색을 지웠을 때 그 칸을 거절하는 사유.
COLOR_REMOVED_REASON = (
    "지운 항목(color_preset_no)은 콘솔에 남아 있어 칸 단위로 지울 수 없습니다 — "
    "전체 「⇪ 콘솔에 반영」으로 지워 주세요"
)


def _grid_timeline() -> dict:
    """BACK(마디 1·2·4)과 FOH(마디 1~4) 두 줄 — 모두 승인된 색 프리셋 칸이다."""
    timeline = _timeline()
    timeline["beat_grid"] = {
        "tracks": [
            {
                "group_name": "BACK",
                "group_no": 7,
                "group_no_confirmed": True,
                "cues": [_color_cell(bar) for bar in (1, 2, 4)],
            },
            {
                "group_name": "FOH",
                "group_no": 8,
                "group_no_confirmed": True,
                "cues": [_color_cell(bar) for bar in (1, 2, 3, 4)],
            },
        ],
        "probe_results": timeline["beat_grid"]["probe_results"],
    }
    return timeline


@dataclass
class Applied:
    """전체 반영을 한 번 마친 세션 — 소유 기록·스냅샷·마지막 반영 상태가 모두 생겨 있다."""

    session: ChatSession
    console: Any
    approval: Any
    store: SongTimelineStore
    sent: list[dict]

    def lines(self) -> list[str]:
        """첫 전체 반영 뒤로 콘솔에 나간 쓰기 줄(게이트 백업 줄 제외)."""
        return [line for line in self.console.executed if line != "SaveShow"]

    def approved_lines(self) -> list[str]:
        """마지막 승인 카드가 담은 줄."""
        return [item.command for item in self.approval.requests[-1].items]

    def edit(self, bar: int, target: str, changes: dict) -> dict:
        return self.session.beat_grid_edit(bar, target, changes)

    def unsent(self) -> list[dict] | None:
        return unsent_beat_grid_cells(
            self.store.latest["beat_grid"], self.store.beat_grid_snapshots.get(SONG_KEY)
        )

    def mark_sent(self) -> None:
        """칸 기록(스냅샷)을 지금 격자에 맞춘다 — 가짜 콘솔이 받지 못하는 칸(앱 움직임·밝기 값)을
        「이미 보낸」 상태로 만들 때 쓴다."""
        self.store.beat_grid_snapshots[SONG_KEY] = beat_grid_cell_snapshot(
            self.store.latest["beat_grid"]
        )

    def mutate_tracks(self, change: Callable[[list[dict]], None]) -> None:
        """저장소의 격자를 직접 고친다(감독이 격자에 칸을 넣거나 줄을 더한 것과 같다)."""
        timeline = copy.deepcopy(self.store.latest)
        change(timeline["beat_grid"]["tracks"])
        self.store.latest = timeline

    def state(self) -> dict:
        """칸 단위 반영이 건드릴 수 있는 모든 상태의 사본 — 거절·실패 뒤 그대로인지 비교한다."""
        applied = self.store.beat_grid_applied
        return copy.deepcopy(
            {
                "latest": self.store.latest,
                "snapshot": self.store.beat_grid_snapshots.get(SONG_KEY),
                "record": self.store.beat_grid_allocation(SONG_KEY),
                "applied": (applied.sequence_numbers, applied.cue_numbers) if applied else None,
            }
        )


def _show_applied_on_console(console: Any, record: dict) -> None:
    """가짜 콘솔은 명령을 받아도 상태를 바꾸지 않는다 — 이 앱이 방금 만든 시퀀스·타임코드가 콘솔에
    실제로 있다고 보여 준다(소유권 확인이 읽는 자리). 내용은 소유 기록에서 그대로 옮긴다."""
    console.state_tree["DataPool/Sequences"] = {
        "children": [
            {"i": track["sequence_number"], "name": track["sequence_name"]}
            for track in record["tracks"].values()
        ]
    }
    console.state_tree["DataPool/Timecodes"] = {
        "children": [{"i": record["timecode_number"], "name": record["timecode_name"]}],
        "node": {"childCount": 1},
    }


def _applied(tmp_path, *, decisions: tuple[bool, ...] = (True,) * 12) -> Applied:
    store = SongTimelineStore()
    store.latest = _grid_timeline()
    sent: list[dict] = []
    session, console, approval, _audit = _new_session(
        tmp_path, store=store, decisions=decisions, sent=sent
    )
    first = session.beat_grid_apply()
    assert first["ok"] is True
    assert first["approval_vs_sent"]["match"] is True
    record = store.beat_grid_allocation(SONG_KEY)
    # 전제 확인 — 아래 시험이 기대는 큐 번호(빈 마디는 번호를 쓰지 않는다).
    assert record["tracks"]["BACK"]["cues"] == {"1": 1, "2": 2, "4": 3}
    assert record["tracks"]["FOH"]["cues"] == {"1": 1, "2": 2, "3": 3, "4": 4}
    _show_applied_on_console(console, record)
    console.executed.clear()
    approval.requests.clear()
    sent.clear()
    return Applied(session, console, approval, store, sent)


@pytest.fixture
def applied(tmp_path) -> Applied:
    return _applied(tmp_path)


def _count_console_reads(console: Any) -> list[str]:
    """가짜 콘솔의 읽기(``query_state``·``query_properties``) 경로를 모으는 목록 — 거절이 콘솔을
    읽기 전에 일어났는지 본다. 읽기 결과는 그대로 돌려준다."""
    reads: list[str] = []
    for name in ("query_state", "query_properties"):
        original = getattr(console, name)

        def counting(path, *args, _original=original, **kwargs):
            reads.append(path)
            return _original(path, *args, **kwargs)

        setattr(console, name, counting)
    return reads


def _assert_refused_untouched(s: Applied, status: dict, *, before: dict, reason_has: str) -> None:
    assert status["ok"] is False
    assert reason_has in status["reason"]
    assert "subset" not in status
    assert "completed" not in status
    assert s.lines() == []  # 콘솔에 한 줄도 나가지 않았다
    assert s.approval.requests == []  # 승인 카드도 올리지 않았다
    assert s.state() == before  # 격자·스냅샷·소유 기록·반영 상태 모두 그대로다


class TestSubsetApply:
    def test_only_the_selected_changed_cells_reach_the_console_with_merge(self, applied) -> None:
        s = applied
        s.edit(2, "BACK", ENTRY)
        s.edit(3, "FOH", ENTRY)
        s.edit(4, "FOH", ENTRY)  # 바뀌었지만 고르지 않은 칸
        status = s.session.beat_grid_apply(cells=[("BACK", 2), ("FOH", 3)])

        assert status["ok"] is True
        assert status["last_action"] == "apply"
        assert status["approval_vs_sent"]["match"] is True
        assert status["completed"] == "reflected"
        assert status["subset"] == {
            "requested": 2,
            "applied": [["BACK", 2], ["FOH", 3]],
            "not_applied": [],
            "baseline": "snapshot",
        }
        assert status["blocked_cells"] == []
        lines = s.lines()
        stores = [line for line in lines if line.startswith("Store Sequence")]
        # BACK(시퀀스 1)의 큐 2, FOH(시퀀스 2)의 큐 3 — 전체 반영과 같은 번호, 저장 줄마다 /Merge.
        assert [_FADE_STORE.fullmatch(line).groups() for line in stores] == [("1", "2"), ("2", "3")]
        assert len(lines) == 10  # 칸마다 값·저장·ClearAll·TrigType·TrigTime 다섯 줄
        assert "Group 7 ; At Preset 4.2" in lines
        assert "Group 8 ; At Preset 4.3" in lines
        assert "Set Cue 2 Sequence 1 Property 'TrigType' 'Time'" in lines
        assert "Set Cue 3 Sequence 2 Property 'TrigType' 'Time'" in lines
        # 고르지 않은 칸(바뀐 FOH 4 = 시퀀스 2의 큐 4 포함)의 줄은 한 줄도 없다.
        assert not any(re.search(r"\bCue 4\b", line) for line in lines)
        # 승인 카드는 그 한 묶음 하나뿐이고 카드의 줄이 곧 보낸 줄이다.
        assert len(s.approval.requests) == 1
        assert s.approved_lines() == lines
        reasons = s.approval.requests[-1].items[0].risk_reasons
        assert reasons[0] == "박자 격자 칸 반영 — 선택한 2칸만 1회 승인"

    def test_nothing_about_the_timecode_or_the_sequence_shell_is_sent(self, applied) -> None:
        s = applied
        s.edit(2, "BACK", ENTRY)
        s.edit(3, "FOH", ENTRY)
        s.session.beat_grid_apply(cells=[("BACK", 2), ("FOH", 3)])
        lines = s.lines()
        assert lines
        assert not any("Timecode" in line for line in lines)
        assert not any(line.startswith("Assign ") for line in lines)
        assert not any(line.startswith(("Delete", "Label", "cd ")) for line in lines)
        assert not any(line.startswith("Set Sequence") for line in lines)
        assert not any(line.startswith("Store Preset") for line in lines)

    def test_the_timecode_rebuild_helper_is_never_called(self, applied, monkeypatch) -> None:
        def boom(*args, **kwargs):
            raise AssertionError("칸 단위 반영이 타임코드 지우기를 불렀다")

        monkeypatch.setattr("server.web.session.clear_app_timecode_before_rebuild", boom)
        s = applied
        s.edit(2, "BACK", ENTRY)
        assert s.session.beat_grid_apply(cells=[("BACK", 2)])["ok"] is True

    def test_the_first_cue_of_a_sequence_never_deletes_or_renames_it(self, applied) -> None:
        s = applied
        # 큐 1 — 전체 반영에서는 Delete Sequence·이름·WrapAround 가 붙는 큐다.
        s.edit(1, "BACK", ENTRY)
        s.edit(1, "FOH", ENTRY)
        status = s.session.beat_grid_apply(cells=[("BACK", 1), ("FOH", 1)])
        assert status["ok"] is True
        lines = s.lines()
        stores = [line for line in lines if line.startswith("Store Sequence")]
        assert [_FADE_STORE.fullmatch(line).groups() for line in stores] == [("1", "1"), ("2", "1")]
        assert not any(line.startswith(("Delete", "Set Sequence")) for line in lines)

    def test_an_unselected_changed_cell_stays_unsent(self, applied) -> None:
        s = applied
        s.edit(2, "BACK", ENTRY)
        s.edit(3, "FOH", ENTRY)
        s.edit(4, "FOH", ENTRY)
        status = s.session.beat_grid_apply(cells=[("BACK", 2), ("FOH", 3)])
        assert s.unsent() == [{"group_name": "FOH", "bar": 4}]
        assert status["pending_apply_count"] == 1
        timeline_events = [e for e in s.sent if e.get("type") == "song_timeline"]
        assert timeline_events[-1]["timeline"]["beat_grid"]["unsent_cells"] == [
            {"group_name": "FOH", "bar": 4}
        ]
        # 이벤트는 반환값과 같은 것이다(상태 이벤트가 연결로 나갔다).
        assert [e for e in s.sent if e.get("type") == "beat_grid_send_status"][-1] == status

    def test_a_following_apply_of_the_left_over_cell_still_works(self, applied) -> None:
        s = applied
        s.edit(3, "FOH", ENTRY)
        s.edit(4, "FOH", ENTRY)
        assert s.session.beat_grid_apply(cells=[("FOH", 3)])["ok"] is True
        s.console.executed.clear()
        status = s.session.beat_grid_apply(cells=[("FOH", 4)])
        assert status["ok"] is True
        assert s.unsent() == []
        stores = [line for line in s.lines() if line.startswith("Store Sequence")]
        assert [_FADE_STORE.fullmatch(line).groups() for line in stores] == [("2", "4")]

    def test_a_cell_that_lost_a_value_is_refused_while_the_other_changed_cell_goes(
        self, applied
    ) -> None:
        s = applied
        # BACK 2마디의 색을 지웠다 — 색 줄이 없는 큐를 /Merge 로 덧써도 콘솔 큐는 옛 색을
        # 그대로 갖는다.
        s.edit(2, "BACK", {"color_preset_no": None})
        s.edit(3, "FOH", ENTRY)
        before = s.state()
        status = s.session.beat_grid_apply(cells=[("BACK", 2), ("FOH", 3)])

        assert status["ok"] is True
        assert status["subset"] == {
            "requested": 2,
            "applied": [["FOH", 3]],
            "not_applied": [{"group_name": "BACK", "bar": 2, "reason": COLOR_REMOVED_REASON}],
            "baseline": "snapshot",
        }
        assert status["blocked_cells"] == [
            {"group_name": "BACK", "bar": 2, "reason": COLOR_REMOVED_REASON}
        ]
        # 지운 칸은 한 줄도 나가지 않았다 — 다른 칸(FOH 3 = 시퀀스 2의 큐 3)만 나갔다.
        stores = [line for line in s.lines() if line.startswith("Store Sequence")]
        assert [_FADE_STORE.fullmatch(line).groups() for line in stores] == [("2", "3")]
        assert not any("Sequence 1" in line for line in s.lines())
        # 지운 칸의 스냅샷 항목과 소유 기록은 그대로라 그 칸은 계속 미반영이다.
        after = s.state()
        assert after["snapshot"][("BACK", 2)] == before["snapshot"][("BACK", 2)]
        assert after["record"] == before["record"]
        assert s.unsent() == [{"group_name": "BACK", "bar": 2}]
        assert status["pending_apply_count"] == 1
        # 승인 카드는 보내지 않는 칸과 그 사유를 보여 준다.
        card_reason = s.approval.requests[-1].items[0].risk_reasons[0]
        assert card_reason.startswith("박자 격자 칸 반영 — 선택한 1칸만 1회 승인")
        assert "BACK 2마디(지운 항목(color_preset_no)" in card_reason

    def test_a_cell_with_only_a_removed_value_leaves_nothing_to_send(self, applied) -> None:
        s = applied
        s.edit(2, "BACK", {"color_preset_no": None})
        before = s.state()
        status = s.session.beat_grid_apply(cells=[("BACK", 2)])
        assert status["ok"] is False
        assert "칸 단위로 보낼 수 있는 칸이 없습니다" in status["reason"]
        assert f"BACK 2마디: {COLOR_REMOVED_REASON}" in status["reason"]
        assert s.lines() == []
        assert s.approval.requests == []
        assert s.state() == before

    def test_removing_a_fade_that_an_earlier_subset_apply_sent_is_refused(self, applied) -> None:
        s = applied
        s.edit(2, "BACK", ENTRY)
        assert (
            s.session.beat_grid_apply(cells=[("BACK", 2)])["ok"] is True
        )  # 페이드가 콘솔에 올라갔다
        s.console.executed.clear()
        # 페이드를 지우면 새 큐는 CueFade 가 없는 저장 줄을 내고, /Merge 는 콘솔 큐의 옛 페이드를
        # 남긴다.
        s.edit(2, "BACK", {"entry": {"fade_bars": None, "mib_mode": None}})
        before = s.state()
        status = s.session.beat_grid_apply(cells=[("BACK", 2)])
        assert status["ok"] is False
        assert "지운 항목(entry.fade_bars)" in status["reason"]
        assert s.lines() == []
        assert s.state() == before
        assert s.unsent() == [{"group_name": "BACK", "bar": 2}]

    def test_a_cleared_shape_with_speed_and_axis_left_is_refused(self, applied) -> None:
        s = applied
        # 앱 움직임이 있는 칸이 이미 반영됐다(가짜 콘솔은 움직임 칸을 못 받으니 기록만 맞춘다).
        s.edit(2, "BACK", {"app_movement": _MOVEMENT})
        s.mark_sent()
        s.edit(3, "FOH", ENTRY)
        # 모양만 지웠다 — 에미터는 shape 가 없으면 움직임 줄을 안 내, 콘솔은 옛 움직임을
        # 그대로 갖는다.
        s.edit(2, "BACK", {"app_movement": {**_MOVEMENT, "shape": None}})
        before = s.state()
        status = s.session.beat_grid_apply(cells=[("BACK", 2), ("FOH", 3)])

        assert status["ok"] is True
        reason = (
            "지운 항목(app_movement.shape)은 콘솔에 남아 있어 칸 단위로 지울 수 없습니다 — "
            "전체 「⇪ 콘솔에 반영」으로 지워 주세요"
        )
        assert status["subset"] == {
            "requested": 2,
            "applied": [["FOH", 3]],
            "not_applied": [{"group_name": "BACK", "bar": 2, "reason": reason}],
            "baseline": "snapshot",
        }
        assert "app_movement.shape" in status["subset"]["not_applied"][0]["reason"]
        assert not any("Sequence 1" in line for line in s.lines())  # BACK 은 한 줄도 안 나갔다
        after = s.state()
        assert after["snapshot"][("BACK", 2)] == before["snapshot"][("BACK", 2)]
        assert s.unsent() == [{"group_name": "BACK", "bar": 2}]

    def test_a_cleared_brightness_percent_with_the_mode_left_is_refused(self, applied) -> None:
        s = applied
        s.edit(2, "BACK", {"brightness": {"mode": "value", "value_percent": 70}})
        s.mark_sent()
        s.edit(3, "FOH", ENTRY)
        s.edit(2, "BACK", {"brightness": {"mode": "value", "value_percent": None}})
        status = s.session.beat_grid_apply(cells=[("BACK", 2), ("FOH", 3)])

        assert status["ok"] is True
        assert status["subset"]["applied"] == [["FOH", 3]]
        (skipped,) = status["subset"]["not_applied"]
        assert (skipped["group_name"], skipped["bar"]) == ("BACK", 2)
        # 에미터도 이 칸을 막지만(값 모드인데 값이 없다) 지운 항목 사유가 앞선다.
        assert skipped["reason"].startswith("지운 항목(brightness.value_percent)은")
        assert s.unsent() == [{"group_name": "BACK", "bar": 2}]

    def test_a_nested_value_that_changed_but_is_still_set_is_not_refused(self, applied) -> None:
        s = applied
        s.edit(2, "BACK", ENTRY)
        assert s.session.beat_grid_apply(cells=[("BACK", 2)])["ok"] is True
        s.console.executed.clear()
        s.edit(2, "BACK", {"entry": {"fade_bars": 2, "mib_mode": None}})  # 1마디 → 2마디
        status = s.session.beat_grid_apply(cells=[("BACK", 2)])
        assert status["ok"] is True
        assert status["subset"]["applied"] == [["BACK", 2]]
        assert status["subset"]["not_applied"] == []
        assert s.unsent() == []

    def test_a_nested_key_that_was_added_is_not_refused(self, applied) -> None:
        s = applied
        s.edit(2, "BACK", ENTRY)
        assert s.session.beat_grid_apply(cells=[("BACK", 2)])["ok"] is True
        s.console.executed.clear()
        s.edit(2, "BACK", {"entry": {"fade_bars": 1, "mib_mode": None, "tracking": "Release"}})
        status = s.session.beat_grid_apply(cells=[("BACK", 2)])
        assert status["ok"] is True
        assert status["subset"]["applied"] == [["BACK", 2]]
        assert status["subset"]["not_applied"] == []
        assert "Set Cue 2 Sequence 1 Property 'Release' 1" in s.lines()
        assert s.unsent() == []

    def test_changing_a_value_is_not_removing_it(self, applied) -> None:
        s = applied
        # 색 번호를 다른 승인된 번호로 바꾸는 편집은 지움이 아니다(승인은 함께 보낸다).
        approval = {"approval": {"by": "supervisor", "date": "2026-10-18", "source": "test"}}
        s.edit(2, "BACK", {"color_preset_no": "4.5", "evidence": approval})
        status = s.session.beat_grid_apply(cells=[("BACK", 2)])
        assert status["ok"] is True
        assert status["subset"]["not_applied"] == []
        assert "Group 7 ; At Preset 4.5" in s.lines()
        assert s.unsent() == []

    def test_without_a_last_apply_state_none_is_not_invented(self, applied) -> None:
        s = applied
        s.store.beat_grid_applied = None  # 서버를 다시 띄운 직후 — 메모리의 마지막 반영 상태가 없다
        s.edit(2, "BACK", ENTRY)
        assert s.session.beat_grid_apply(cells=[("BACK", 2)])["ok"] is True
        assert s.store.beat_grid_applied is None  # 일부 칸만 담은 상태를 새로 만들지 않는다

    def test_selected_cells_that_match_the_console_are_reported_not_resent(self, applied) -> None:
        s = applied
        s.edit(2, "BACK", ENTRY)
        status = s.session.beat_grid_apply(cells=[("BACK", 2), ("FOH", 1), ("BACK", 1)])
        assert status["ok"] is True
        assert status["subset"] == {
            "requested": 3,
            "applied": [["BACK", 2]],
            "not_applied": [
                {"group_name": "FOH", "bar": 1, "reason": "콘솔과 같음(바뀐 칸 아님)"},
                {"group_name": "BACK", "bar": 1, "reason": "콘솔과 같음(바뀐 칸 아님)"},
            ],
            "baseline": "snapshot",
        }
        assert status["blocked_cells"] == []  # 같은 칸은 「막힌 칸」이 아니다
        stores = [line for line in s.lines() if line.startswith("Store Sequence")]
        assert [_FADE_STORE.fullmatch(line).groups() for line in stores] == [("1", "2")]
        reasons = s.approval.requests[-1].items[0].risk_reasons[0]
        assert reasons.startswith("박자 격자 칸 반영 — 선택한 1칸만 1회 승인")
        assert "보내지 않는 칸 2개" in reasons

    def test_a_blocked_selected_cell_is_reported_and_the_rest_still_go(self, applied) -> None:
        s = applied
        # 밝기 값 칸은 디머 속성을 읽지 못하면 에미터가 막는다(가짜 콘솔은 기종을 모른다).
        s.edit(2, "BACK", {"brightness": {"mode": "value", "value_percent": 50}})
        s.edit(3, "FOH", ENTRY)
        status = s.session.beat_grid_apply(cells=[("BACK", 2), ("FOH", 3)])
        assert status["ok"] is True
        assert status["subset"]["applied"] == [["FOH", 3]]
        (skipped,) = status["subset"]["not_applied"]
        assert (skipped["group_name"], skipped["bar"]) == ("BACK", 2)
        assert skipped["reason"]
        assert status["blocked_cells"] == [
            {"group_name": "BACK", "bar": 2, "reason": skipped["reason"]}
        ]
        stores = [line for line in s.lines() if line.startswith("Store Sequence")]
        assert [_FADE_STORE.fullmatch(line).groups() for line in stores] == [("2", "3")]
        # 막힌 칸은 스냅샷에도 올라가지 않아 계속 미반영이다.
        assert s.unsent() == [{"group_name": "BACK", "bar": 2}]

    def test_an_appended_new_last_cell_is_stored_and_recorded(self, applied) -> None:
        s = applied
        s.mutate_tracks(lambda tracks: tracks[0]["cues"].append(_color_cell(5)))
        assert s.unsent() == [{"group_name": "BACK", "bar": 5}]
        status = s.session.beat_grid_apply(cells=[("BACK", 5)])
        assert status["ok"] is True
        assert status["subset"]["applied"] == [["BACK", 5]]
        stores = [line for line in s.lines() if line.startswith("Store Sequence")]
        assert stores == ["Store Sequence 1 Cue 4 /Merge"]
        # 소유 기록과 마지막 반영 상태가 새 칸의 큐 번호를 더했다.
        record = s.store.beat_grid_allocation(SONG_KEY)
        assert record["tracks"]["BACK"]["cues"] == {"1": 1, "2": 2, "4": 3, "5": 4}
        assert s.store.beat_grid_applied.cue_numbers["BACK"] == {1: 1, 2: 2, 4: 3, 5: 4}
        assert s.unsent() == []

    def test_a_cell_whose_cue_number_would_overwrite_another_bar_is_refused(self, applied) -> None:
        s = applied
        # BACK 3마디를 중간에 넣으면 전체 반영 번호가 밀린다(4마디가 큐 3 → 4). 큐 3은 콘솔에서
        # 4마디의 큐라, 3마디를 큐 3에 덧쓰면 4마디를 망가뜨린다.
        s.mutate_tracks(lambda tracks: tracks[0]["cues"].insert(2, _color_cell(3)))
        before = s.state()
        status = s.session.beat_grid_apply(cells=[("BACK", 3)])
        assert status["ok"] is False
        assert "칸 단위로 보낼 수 있는 칸이 없습니다" in status["reason"]
        assert "BACK 3마디" in status["reason"]
        assert "큐 3번" in status["reason"]
        assert s.lines() == []
        assert s.approval.requests == []
        assert s.state() == before

    def test_the_cells_that_would_collide_are_listed_while_safe_ones_go(self, applied) -> None:
        s = applied
        s.mutate_tracks(lambda tracks: tracks[0]["cues"].insert(2, _color_cell(3)))
        s.edit(2, "FOH", ENTRY)
        status = s.session.beat_grid_apply(cells=[("BACK", 3), ("FOH", 2)])
        assert status["ok"] is True
        assert status["subset"]["applied"] == [["FOH", 2]]
        (skipped,) = status["subset"]["not_applied"]
        assert (skipped["group_name"], skipped["bar"]) == ("BACK", 3)
        assert "큐 3번" in skipped["reason"]
        stores = [line for line in s.lines() if line.startswith("Store Sequence")]
        assert [_FADE_STORE.fullmatch(line).groups() for line in stores] == [("2", "2")]
        assert not any("Sequence 1" in line for line in s.lines())  # BACK(시퀀스 1)은 손대지 않았다

    def test_state_is_merged_not_replaced(self, applied) -> None:
        s = applied
        s.edit(2, "BACK", ENTRY)
        s.edit(3, "FOH", ENTRY)
        s.edit(4, "FOH", ENTRY)
        before = s.state()
        status = s.session.beat_grid_apply(cells=[("BACK", 2), ("FOH", 3)])
        assert status["ok"] is True
        after = s.state()
        # 스냅샷 — 보낸 두 칸은 지금 값으로, 나머지는 옛 기록 그대로(FOH 4 는 바뀐 채 미반영).
        current = beat_grid_cell_snapshot(s.store.latest["beat_grid"])
        for cell, entry in after["snapshot"].items():
            if cell in {("BACK", 2), ("FOH", 3)}:
                assert entry == current[cell]
            else:
                assert entry == before["snapshot"][cell]
        assert after["snapshot"][("FOH", 4)] != current[("FOH", 4)]
        assert set(after["snapshot"]) == set(before["snapshot"])
        # 소유 기록 — 큐 번호가 같아 그대로고, 줄·시퀀스·타임코드 항목이 하나도 줄지 않았다.
        assert after["record"] == before["record"]
        # 마지막 반영 상태 — 시퀀스 번호와 다른 줄·마디의 큐 번호는 그대로다.
        assert after["applied"] == before["applied"]

    def test_the_record_keeps_other_tracks_and_does_not_prune_stale_ones(self, applied) -> None:
        s = applied
        # 격자에서 사라진 줄(OLD)이 기록에 남아 있다 — 전체 반영은 정리하지만 칸 단위 반영은 아니다.
        record = s.store.beat_grid_allocation(SONG_KEY)
        record["tracks"]["OLD"] = {
            "sequence_number": 7,
            "sequence_name": "LDBEAT OLD",
            "cues": {"1": 1},
        }
        s.store.set_beat_grid_allocation(SONG_KEY, record)
        s.console.state_tree["DataPool/Sequences"]["children"].append(
            {"i": 7, "name": "LDBEAT OLD"}
        )
        s.edit(2, "BACK", ENTRY)
        status = s.session.beat_grid_apply(cells=[("BACK", 2)])
        assert status["ok"] is True
        assert status["stale_tracks"] == []
        assert s.store.beat_grid_allocation(SONG_KEY)["tracks"]["OLD"] == record["tracks"]["OLD"]

    def test_a_pending_approval_on_an_unselected_cell_is_not_recorded_as_sent(
        self, applied
    ) -> None:
        s = applied
        s.edit(2, "BACK", ENTRY)
        s.edit(4, "FOH", {"color_preset_no": "4.5"})  # 승인 없는 새 번호 — 승인 대기
        assert [
            (p["group_name"], p["bar"])
            for p in pending_preset_approvals(s.store.latest["beat_grid"])
        ] == [("FOH", 4)]
        before_grid = copy.deepcopy(s.store.latest["beat_grid"])
        status = s.session.beat_grid_apply(cells=[("BACK", 2)])
        assert status["ok"] is True
        # 승인 기록(``evidence.approval``)이 어느 칸에도 새로 적히지 않았다 — 격자가 그대로다.
        foh_4 = next(
            cue
            for track in s.store.latest["beat_grid"]["tracks"]
            if track["group_name"] == "FOH"
            for cue in track["cues"]
            if cue["bar"] == 4
        )
        assert foh_4["evidence"] is None or "approval" not in (foh_4["evidence"] or {})
        assert s.store.latest["beat_grid"] == before_grid
        assert [
            (p["group_name"], p["bar"])
            for p in pending_preset_approvals(s.store.latest["beat_grid"])
        ] == [("FOH", 4)]
        # 그 칸은 한 줄도 나가지 않았고 계속 미반영이다.
        assert not any("Preset 4.5" in line for line in s.lines())
        assert {"group_name": "FOH", "bar": 4} in s.unsent()

    def test_the_whole_song_apply_is_unchanged_when_cells_is_none(self, applied) -> None:
        s = applied
        s.edit(2, "BACK", ENTRY)
        status = s.session.beat_grid_apply(cells=None)
        assert status["ok"] is True
        assert "subset" not in status
        lines = s.lines()
        # 전체 반영은 소유한 시퀀스를 지우고 다시 만들고 타임코드도 다시 만든다.
        assert "Delete Sequence 1 /NoConfirm" in lines
        assert "Delete Sequence 2 /NoConfirm" in lines
        assert any(line.startswith("Store Timecode") for line in lines)
        assert s.unsent() == []


class TestSubsetApplyForbiddenLines:
    """리드 지시 — 칸 단위 묶음에 금지 줄이 한 줄도 없어야 한다.

    승인 카드가 담은 줄과 실제로 콘솔에 나간 줄 둘 다 본다."""

    def test_the_batch_has_no_forbidden_line(self, applied) -> None:
        s = applied
        # 첫 큐(Delete/이름/WrapAround 가 붙는 큐)·중간 큐·새 끝 칸·고르지 않은 바뀐 칸·
        # 승인 대기 칸을 섞는다.
        s.mutate_tracks(lambda tracks: tracks[0]["cues"].append(_color_cell(5)))
        s.edit(1, "BACK", ENTRY)
        s.edit(2, "BACK", ENTRY)
        s.edit(1, "FOH", ENTRY)
        s.edit(3, "FOH", ENTRY)  # 고르지 않는다
        s.edit(4, "FOH", {"color_preset_no": "4.5"})  # 승인 대기 — 고르지 않는다
        selected = [("BACK", 1), ("BACK", 2), ("BACK", 5), ("FOH", 1)]
        status = s.session.beat_grid_apply(cells=selected)
        assert status["ok"] is True
        assert [tuple(cell) for cell in status["subset"]["applied"]] == selected

        sequences = {1, 2}  # 콘솔에 이미 있는 이 곡의 시퀀스(BACK=1, FOH=2)
        stored = {(1, 1), (1, 2), (1, 4), (2, 1)}  # 고른 칸의 (시퀀스, 큐 번호)
        for label, lines in (("approved", s.approved_lines()), ("sent", s.lines())):
            assert lines, label
            forbidden = [line for line in lines if line.startswith(_FORBIDDEN_PREFIXES)]
            assert forbidden == [], f"{label}: 금지 줄 {forbidden}"
            stores = [line for line in lines if line.startswith("Store Sequence")]
            assert len(stores) == len(selected), label
            for line in stores:
                match = re.fullmatch(
                    r"Store Sequence (\d+) Cue (\d+)( CueFade [0-9.]+)? /Merge", line
                )
                assert match, f"{label}: /Merge 가 없는 저장 줄 {line!r}"
                assert (int(match[1]), int(match[2])) in stored, f"{label}: 고르지 않은 칸 {line!r}"
            for line in lines:
                for number in re.findall(r"\bSequence (\d+)\b", line):
                    assert int(number) in sequences, f"{label}: 만들어 두지 않은 시퀀스 {line!r}"
        assert s.approved_lines() == s.lines()

    def test_the_forbidden_scan_would_catch_the_whole_song_batch(self, applied) -> None:
        # 위 시험이 공허하지 않다는 증거 — 같은 검사를 전체 반영 묶음에 대면 금지 줄이 잔뜩 걸린다.
        s = applied
        s.edit(2, "BACK", ENTRY)
        assert s.session.beat_grid_apply()["ok"] is True
        forbidden = [line for line in s.lines() if line.startswith(_FORBIDDEN_PREFIXES)]
        assert any(line.startswith("Delete Sequence") for line in forbidden)
        assert any(line.startswith("Set Sequence") for line in forbidden)
        assert any(line.startswith("Store Timecode") for line in forbidden)


def _plan_a_new_position_preset(s: Applied) -> None:
    """BACK 2마디가 위치 풀(2)의 비어 있는 71번을 쓰고, 곡 격자에 목표 좌표 레시피가 있다 — 전체
    반영이라면 반영 때 목표 좌표로 그 프리셋을 만드는 칸이다(``test_position_preset_create_
    t592``)."""
    s.mutate_tracks(
        lambda tracks: tracks[0]["cues"][1].update({"position_preset_no": "2.71", "evidence": None})
    )
    timeline = copy.deepcopy(s.store.latest)
    timeline["beat_grid"].update(_POSITION_RECIPE)
    s.store.latest = timeline
    s.session._beat_grid_group_members = lambda names, **_: {"BACK": [101, 102]}
    s.session._beat_grid_pointing_frames = lambda: _POSITION_FRAMES


class TestSubsetApplyRefusals:
    def test_a_cell_missing_from_the_grid_is_refused_before_anything_is_read(self, applied) -> None:
        s = applied
        s.edit(2, "BACK", ENTRY)
        before = s.state()
        status = s.session.beat_grid_apply(cells=[("BACK", 2), ("BACK", 3), ("ZZZ", 1)])
        _assert_refused_untouched(s, status, before=before, reason_has="BACK 3마디, ZZZ 1마디")
        assert "격자에 없습니다" in status["reason"]

    def test_an_empty_selection_is_refused(self, applied) -> None:
        s = applied
        before = s.state()
        status = s.session.beat_grid_apply(cells=[])
        _assert_refused_untouched(s, status, before=before, reason_has="고르지 않았습니다")

    def test_a_track_that_is_not_yet_a_console_sequence_names_the_whole_song_apply(
        self, applied
    ) -> None:
        s = applied
        s.mutate_tracks(
            lambda tracks: tracks.append(
                {
                    "group_name": "SIDE",
                    "group_no": 9,
                    "group_no_confirmed": True,
                    "cues": [_color_cell(1)],
                }
            )
        )
        before = s.state()
        status = s.session.beat_grid_apply(cells=[("SIDE", 1)])
        _assert_refused_untouched(s, status, before=before, reason_has="SIDE")
        assert "전체 「⇪ 콘솔에 반영」으로 먼저 만들어 주세요" in status["reason"]

    def test_a_console_sequence_that_is_no_longer_ours_is_not_written_to(self, applied) -> None:
        s = applied
        # 감독이 콘솔의 같은 번호에 다른 시퀀스를 만들었다 — 이름이 기록과 달라 이 앱의 것이 아니다.
        s.console.state_tree["DataPool/Sequences"]["children"][0]["name"] = "SOMEONE ELSES SHOW"
        s.edit(2, "BACK", ENTRY)
        before = s.state()
        status = s.session.beat_grid_apply(cells=[("BACK", 2)])
        _assert_refused_untouched(s, status, before=before, reason_has="BACK")
        assert "전체 「⇪ 콘솔에 반영」" in status["reason"]

    def test_a_song_with_neither_a_snapshot_nor_an_owned_track_is_refused_before_any_read(
        self, applied
    ) -> None:
        s = applied
        # 서버를 다시 띄운 것과 같다(칸 기록 없음). 소유 기록은 남았지만 줄이 하나도 없다 — 이 앱이
        # 콘솔에 만들어 둔 시퀀스가 없으니 칸 단위로 덧쓸 곳이 없다.
        s.store.beat_grid_snapshots.clear()
        s.store.set_beat_grid_allocation(
            SONG_KEY, {**s.store.beat_grid_allocation(SONG_KEY), "tracks": {}}
        )
        s.edit(2, "BACK", ENTRY)
        reads = _count_console_reads(s.console)
        before = s.state()
        status = s.session.beat_grid_apply(cells=[("BACK", 2), ("FOH", 1)])
        _assert_refused_untouched(s, status, before=before, reason_has="전체 다시 반영")
        assert status["reason"] == NO_RECORD_REASON
        assert reads == []  # 승인 카드는 물론 콘솔 읽기도 한 번 없이 거절했다
        # 고른 칸을 바뀐 칸으로 치고 새 기록을 시작하지 않는다.
        assert s.store.beat_grid_snapshots == {}

    def test_a_never_applied_song_is_refused_for_lack_of_an_apply_record(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _grid_timeline()
        session, console, approval, _audit = _new_session(tmp_path, store=store)
        reads = _count_console_reads(console)
        status = session.beat_grid_apply(cells=[("BACK", 1)])
        assert status["ok"] is False
        assert status["reason"] == NO_RECORD_REASON
        assert reads == []
        assert console.executed == []
        assert approval.requests == []
        assert store.beat_grid_allocation(SONG_KEY) is None
        assert store.beat_grid_snapshots == {}

    def test_cells_that_all_match_the_console_are_refused(self, applied) -> None:
        s = applied
        s.edit(3, "FOH", ENTRY)  # 바뀐 칸이 있어도 고른 칸이 아니면 소용없다
        before = s.state()
        status = s.session.beat_grid_apply(cells=[("BACK", 1), ("FOH", 1)])
        _assert_refused_untouched(
            s, status, before=before, reason_has="이미 콘솔에 반영된 내용과 같아"
        )

    def test_a_cell_holding_an_empty_preset_needs_the_whole_song_apply(self, applied) -> None:
        s = applied
        s.edit(2, "BACK", {"color_preset_no": "4.40"})  # 콘솔 풀에 없는 번호 — 송신 보류
        s.edit(3, "FOH", ENTRY)  # 같이 골라도 아무것도 나가지 않는다
        before = s.state()
        status = s.session.beat_grid_apply(cells=[("BACK", 2), ("FOH", 3)])
        _assert_refused_untouched(s, status, before=before, reason_has="BACK 2마디(빈 프리셋 보류)")
        assert "FOH 3마디" not in status["reason"]
        assert "승인 대기" not in status["reason"]
        assert "전체 「⇪ 콘솔에 반영」" in status["reason"]

    def test_a_cell_that_needs_a_new_preset_created_needs_the_whole_song_apply(
        self, applied
    ) -> None:
        s = applied
        _plan_a_new_position_preset(s)
        s.edit(3, "FOH", ENTRY)
        before = s.state()
        status = s.session.beat_grid_apply(cells=[("BACK", 2), ("FOH", 3)])
        _assert_refused_untouched(
            s, status, before=before, reason_has="BACK 2마디(새로 만들 프리셋)"
        )
        assert "FOH 3마디" not in status["reason"]
        assert "Store Preset" not in " ".join(s.console.executed)

    def test_a_preset_planned_for_an_unselected_cell_is_not_created_or_approved(
        self, applied
    ) -> None:
        s = applied
        _plan_a_new_position_preset(s)  # BACK 2 가 새 프리셋을 쓴다 — 고르지 않는다
        s.edit(3, "FOH", ENTRY)
        status = s.session.beat_grid_apply(cells=[("FOH", 3)])
        assert status["ok"] is True
        assert status["subset"]["applied"] == [["FOH", 3]]
        lines = s.lines()
        # 프리셋을 만드는 줄(조준·저장·이름)이 한 줄도 없다 — 고른 칸의 큐 줄뿐이다.
        assert not any(line.startswith(_FORBIDDEN_PREFIXES) for line in lines)
        assert not any(line.startswith(("Fixture ", "Label Preset")) for line in lines)
        assert _stored(lines) == [("2", "3")]
        assert (
            s.approval.requests[-1].items[0].risk_reasons[0]
            == "박자 격자 칸 반영 — 선택한 1칸만 1회 승인"
        )
        # 새 프리셋을 쓰는 칸은 만들어지지도 승인되지도 않았다 — 계속 승인 대기·미반영이다.
        assert "approval" not in (_cell(s.store, "BACK", 2)["evidence"] or {})
        assert s.unsent() == [{"group_name": "BACK", "bar": 2}]

    def test_only_blocked_or_empty_cells_leave_nothing_to_send(self, applied) -> None:
        s = applied
        s.edit(2, "BACK", {"brightness": {"mode": "value", "value_percent": 50}})
        before = s.state()
        status = s.session.beat_grid_apply(cells=[("BACK", 2)])
        assert status["ok"] is False
        assert "칸 단위로 보낼 수 있는 칸이 없습니다" in status["reason"]
        assert "BACK 2마디" in status["reason"]
        assert status["blocked_cells"][0]["group_name"] == "BACK"
        assert s.lines() == []
        assert s.approval.requests == []
        assert s.state() == before

    def test_a_declined_approval_changes_nothing(self, tmp_path) -> None:
        s = _applied(tmp_path, decisions=(True, False))
        s.edit(2, "BACK", ENTRY)
        before = s.state()
        status = s.session.beat_grid_apply(cells=[("BACK", 2)])
        assert status["ok"] is False
        assert "subset" not in status
        assert "completed" not in status
        assert s.lines() == []  # 승인을 거절하면 콘솔에 아무것도 나가지 않는다
        assert len(s.approval.requests) == 1
        assert s.state() == before
        assert s.unsent() == [{"group_name": "BACK", "bar": 2}]

    def test_a_byte_mismatch_between_approval_and_send_changes_no_state(
        self, applied, monkeypatch
    ) -> None:
        s = applied
        s.edit(2, "BACK", ENTRY)
        before = s.state()
        mismatch = SimpleNamespace(passed=False, sent_not_approved=("stray",), approved_not_sent=())
        monkeypatch.setattr(
            s.session, "_beat_grid_verify_approval_vs_sent", lambda *args, **kwargs: mismatch
        )
        status = s.session.beat_grid_apply(cells=[("BACK", 2)])
        assert status["approval_vs_sent"]["match"] is False
        assert "completed" not in status
        assert s.state() == before  # 스냅샷·소유 기록·반영 상태 모두 그대로 — 계속 미반영이다
        assert s.unsent() == [{"group_name": "BACK", "bar": 2}]


_STORE_ANY = re.compile(r"Store Sequence (\d+) Cue (\d+)(?: CueFade [0-9.]+)? /Merge")


def _stored(lines: list[str]) -> list[tuple[str, str]]:
    """보낸 줄의 저장 줄이 가리킨 (시퀀스, 큐) 쌍 — ``/Merge`` 가 없는 저장 줄이 있으면 실패한다."""
    stores = [line for line in lines if line.startswith("Store Sequence")]
    matches = [_STORE_ANY.fullmatch(line) for line in stores]
    assert all(matches), stores
    return [match.groups() for match in matches]  # type: ignore[union-attr]


def _restart_server(s: Applied) -> None:
    """서버를 다시 띄운 것과 같다 — 칸 기록(스냅샷)은 파일에 저장하지 않아 사라지고, 소유 기록은
    파일에 남는다."""
    s.store.beat_grid_snapshots.clear()


class TestRecordBaseline:
    """서버를 다시 띄운 뒤 — 칸 기록은 없지만 이 앱이 콘솔에 만들어 둔 시퀀스의 소유 기록이 있다.

    이때 칸 단위 반영은 고른 칸을 모두 보낸다(어느 칸이 바뀌었는지는 알 수 없다). 첫 성공은 보낸
    칸만 담은 **부분** 칸 기록을 남긴다 — 전체 기록으로 만들면 나머지 칸이 콘솔과 같다는 거짓 기준이
    된다(그 뒤의 동작은 ``TestPartialSnapshot``)."""

    def test_every_selected_cell_is_sent_and_a_partial_snapshot_is_left(self, applied) -> None:
        s = applied
        s.edit(2, "BACK", ENTRY)
        _restart_server(s)
        reads = _count_console_reads(s.console)
        # FOH 1마디는 바뀌지 않았다 — 기록 기준은 같은지 알 수 없으므로 고른 칸을 그대로 보낸다.
        status = s.session.beat_grid_apply(cells=[("BACK", 2), ("FOH", 1)])

        assert status["ok"] is True
        assert status["completed"] == "reflected"
        assert status["approval_vs_sent"]["match"] is True
        assert status["subset"] == {
            "requested": 2,
            "applied": [["BACK", 2], ["FOH", 1]],
            "not_applied": [],
            "baseline": "record",
        }
        assert status["blocked_cells"] == []
        # 소유 기록의 큐 번호 그대로 — BACK(시퀀스 1)의 큐 2, FOH(시퀀스 2)의 큐 1.
        lines = s.lines()
        assert _stored(lines) == [("1", "2"), ("2", "1")]
        assert not any(line.startswith(_FORBIDDEN_PREFIXES) for line in lines)
        assert s.approved_lines() == lines
        assert s.approval.requests[-1].items[0].risk_reasons[0] == (
            "박자 격자 칸 반영 — 선택한 2칸만 1회 승인"
        )
        assert reads  # 시퀀스 소유 확인은 콘솔을 읽는다(칸 기록 없이 소유 기록만 믿지 않는다)
        # 보낸 두 칸만 아는 부분 기록이 남았다 — 나머지 칸은 모르는 칸이라 대기 수에 들지 않는다.
        snapshot = s.store.beat_grid_snapshots[SONG_KEY]
        assert isinstance(snapshot, PartialCellSnapshot)
        assert set(snapshot) == {("BACK", 2), ("FOH", 1)}
        assert s.unsent() == []
        assert status["pending_apply_count"] == 0

    def test_the_owned_record_and_last_apply_state_still_gain_the_cue_numbers(
        self, applied
    ) -> None:
        s = applied
        s.mutate_tracks(lambda tracks: tracks[0]["cues"].append(_color_cell(5)))
        _restart_server(s)
        before = s.state()
        status = s.session.beat_grid_apply(cells=[("BACK", 5)])

        assert status["ok"] is True
        assert status["subset"]["baseline"] == "record"
        assert _stored(s.lines()) == [("1", "4")]
        record = s.store.beat_grid_allocation(SONG_KEY)
        assert record["tracks"]["BACK"]["cues"] == {"1": 1, "2": 2, "4": 3, "5": 4}
        assert record["tracks"]["FOH"] == before["record"]["tracks"]["FOH"]
        assert record["timecode_number"] == before["record"]["timecode_number"]
        assert s.store.beat_grid_applied.cue_numbers["BACK"] == {1: 1, 2: 2, 4: 3, 5: 4}
        assert s.store.beat_grid_applied.sequence_numbers == before["applied"][0]
        assert set(s.store.beat_grid_snapshots[SONG_KEY]) == {("BACK", 5)}

    def test_the_timeline_frame_after_the_send_lists_the_known_cells(self, applied) -> None:
        s = applied
        s.edit(2, "BACK", ENTRY)
        _restart_server(s)
        s.sent.clear()
        assert s.session.beat_grid_apply(cells=[("BACK", 2)])["ok"] is True
        grid = [e for e in s.sent if e.get("type") == "song_timeline"][-1]["timeline"]["beat_grid"]
        assert grid["unsent_cells"] == []
        assert grid["known_cells"] == [["BACK", 2]]
        assert grid["partial_baseline"] == "snapshot"

    def test_a_removed_value_cannot_be_told_without_a_snapshot_so_the_cell_is_sent(
        self, applied
    ) -> None:
        s = applied
        s.edit(2, "BACK", ENTRY)
        assert (
            s.session.beat_grid_apply(cells=[("BACK", 2)])["ok"] is True
        )  # 페이드가 콘솔에 올라갔다
        s.console.executed.clear()
        s.edit(2, "BACK", {"entry": {"fade_bars": None, "mib_mode": None}})  # 페이드를 지웠다
        _restart_server(s)
        status = s.session.beat_grid_apply(cells=[("BACK", 2)])
        # 칸 기록이 있었다면 이 칸은 거절된다(``test_removing_a_fade_that_an_earlier_subset_apply_
        # sent_is_refused``). 마지막 반영 때의 칸 내용이 없으니 지운 항목을 가려낼 수 없다 — 보낸다.
        assert status["ok"] is True
        assert status["subset"]["applied"] == [["BACK", 2]]
        assert status["subset"]["not_applied"] == []
        assert status["subset"]["baseline"] == "record"
        assert s.lines().count("Store Sequence 1 Cue 2 /Merge") == 1  # 이제 CueFade 가 없는 저장 줄

    def test_a_track_the_record_does_not_know_is_still_refused(self, applied) -> None:
        s = applied
        s.mutate_tracks(
            lambda tracks: tracks.append(
                {
                    "group_name": "SIDE",
                    "group_no": 9,
                    "group_no_confirmed": True,
                    "cues": [_color_cell(1)],
                }
            )
        )
        _restart_server(s)
        before = s.state()
        status = s.session.beat_grid_apply(cells=[("SIDE", 1)])
        _assert_refused_untouched(s, status, before=before, reason_has="SIDE")
        assert "전체 「⇪ 콘솔에 반영」으로 먼저 만들어 주세요" in status["reason"]

    def test_a_cell_whose_cue_number_would_overwrite_another_bar_is_still_refused(
        self, applied
    ) -> None:
        s = applied
        s.mutate_tracks(lambda tracks: tracks[0]["cues"].insert(2, _color_cell(3)))
        _restart_server(s)
        before = s.state()
        status = s.session.beat_grid_apply(cells=[("BACK", 3)])
        assert status["ok"] is False
        assert "큐 3번" in status["reason"]
        assert s.lines() == []
        assert s.state() == before

    def test_a_console_sequence_that_is_no_longer_ours_is_still_not_written_to(
        self, applied
    ) -> None:
        s = applied
        s.console.state_tree["DataPool/Sequences"]["children"][0]["name"] = "SOMEONE ELSES SHOW"
        _restart_server(s)
        before = s.state()
        status = s.session.beat_grid_apply(cells=[("BACK", 2)])
        _assert_refused_untouched(s, status, before=before, reason_has="BACK")

    def test_a_declined_card_leaves_the_song_without_a_snapshot(self, tmp_path) -> None:
        s = _applied(tmp_path, decisions=(True, False))
        s.edit(2, "BACK", ENTRY)
        _restart_server(s)
        before = s.state()
        status = s.session.beat_grid_apply(cells=[("BACK", 2)])
        assert status["ok"] is False
        assert "subset" not in status
        assert s.lines() == []
        assert s.state() == before
        assert s.store.beat_grid_snapshots == {}

    def test_a_following_whole_song_apply_makes_the_snapshot_full(self, applied) -> None:
        s = applied
        s.edit(2, "BACK", ENTRY)
        _restart_server(s)
        assert s.session.beat_grid_apply(cells=[("BACK", 2)])["ok"] is True
        assert isinstance(s.store.beat_grid_snapshots[SONG_KEY], PartialCellSnapshot)
        assert s.session.beat_grid_apply()["ok"] is True
        assert not isinstance(s.store.beat_grid_snapshots[SONG_KEY], PartialCellSnapshot)
        assert s.unsent() == []  # 전체 반영이 칸 기록을 전체로 갈아 끼운다

    def test_with_a_snapshot_the_baseline_is_the_snapshot_not_the_record(self, applied) -> None:
        s = applied
        s.edit(2, "BACK", ENTRY)
        status = s.session.beat_grid_apply(cells=[("BACK", 2), ("FOH", 1)])
        assert status["subset"]["baseline"] == "snapshot"
        # 칸 기록이 있으면 같은 칸은 그대로 보내지 않는다.
        assert status["subset"]["applied"] == [["BACK", 2]]
        assert status["subset"]["not_applied"][0]["reason"] == CELL_UNCHANGED_REASON


class TestPendingPresetApproval:
    """콘솔에 이미 있는 프리셋 번호의 승인 대기 칸 — 번호 줄만 보내고, 승인은 보낸 칸에만 적는다."""

    @staticmethod
    def pending(s: Applied) -> list[tuple[str, int]]:
        return [
            (p["group_name"], p["bar"])
            for p in pending_preset_approvals(s.store.latest["beat_grid"])
        ]

    def test_a_selected_pending_cell_is_sent_and_approved_only_after_success(self, applied) -> None:
        s = applied
        s.edit(4, "FOH", {"color_preset_no": "4.5"})  # 승인 대기 — 고른다
        s.edit(3, "FOH", {"color_preset_no": "4.4"})  # 승인 대기 — 고르지 않는다
        assert self.pending(s) == [("FOH", 3), ("FOH", 4)]
        status = s.session.beat_grid_apply(cells=[("FOH", 4)])

        assert status["ok"] is True
        assert status["approval_vs_sent"]["match"] is True
        assert status["subset"] == {
            "requested": 1,
            "applied": [["FOH", 4]],
            "not_applied": [],
            "baseline": "snapshot",
        }
        lines = s.lines()
        # 번호 줄과 저장 줄뿐이다 — 프리셋을 만들거나 이름·타입·속성을 쓰는 줄은 한 줄도 없다.
        assert "Group 8 ; At Preset 4.5" in lines
        assert not any("Preset 4.4" in line for line in lines)
        assert _stored(lines) == [("2", "4")]
        assert not any(line.startswith(_FORBIDDEN_PREFIXES) for line in lines)
        assert not any(
            line.startswith(("Store Preset", "Label Preset", "Store Type", "Store Property"))
            for line in lines
        )
        assert s.approved_lines() == lines
        reasons = s.approval.requests[-1].items[0].risk_reasons
        assert reasons[0] == "박자 격자 칸 반영 — 선택한 1칸만 1회 승인 · 프리셋 승인 1칸 포함"

        # 승인은 보낸 칸에만 적혔고(승인 카드 묶음의 해시가 출처), 고르지 않은 칸은 그대로 대기다.
        approval = _cell(s.store, "FOH", 4)["evidence"]["approval"]
        assert approval["by"] == "supervisor"
        assert approval["source"] == f"beat_grid_apply:{status['approval_vs_sent']['sha256']}"
        assert "approval" not in (_cell(s.store, "FOH", 3)["evidence"] or {})
        assert self.pending(s) == [("FOH", 3)]
        # 칸 기록에는 승인까지 담긴 지금 값이 올라 보낸 칸은 미반영이 아니다.
        assert s.unsent() == [{"group_name": "FOH", "bar": 3}]
        assert status["pending_apply_count"] == 1

    def test_the_card_counts_the_cells_that_carry_a_preset_approval(self, applied) -> None:
        s = applied
        s.edit(4, "FOH", {"color_preset_no": "4.5"})
        s.edit(3, "FOH", {"color_preset_no": "4.4"})
        s.edit(2, "BACK", ENTRY)  # 승인 대기가 아닌 바뀐 칸
        status = s.session.beat_grid_apply(cells=[("FOH", 3), ("FOH", 4), ("BACK", 2)])
        assert status["ok"] is True
        reasons = s.approval.requests[-1].items[0].risk_reasons
        assert reasons[0] == "박자 격자 칸 반영 — 선택한 3칸만 1회 승인 · 프리셋 승인 2칸 포함"
        assert self.pending(s) == []

    def test_the_card_text_has_no_approval_suffix_without_a_pending_cell(self, applied) -> None:
        s = applied
        s.edit(2, "BACK", ENTRY)
        s.edit(4, "FOH", {"color_preset_no": "4.5"})  # 승인 대기지만 고르지 않는다
        assert s.session.beat_grid_apply(cells=[("BACK", 2)])["ok"] is True
        reasons = s.approval.requests[-1].items[0].risk_reasons
        assert reasons[0] == "박자 격자 칸 반영 — 선택한 1칸만 1회 승인"
        assert self.pending(s) == [("FOH", 4)]

    def test_a_pending_cell_is_sent_on_the_record_baseline_too(self, applied) -> None:
        s = applied
        s.edit(4, "FOH", {"color_preset_no": "4.5"})
        _restart_server(s)
        status = s.session.beat_grid_apply(cells=[("FOH", 4)])
        assert status["ok"] is True
        assert status["subset"]["baseline"] == "record"
        assert "Group 8 ; At Preset 4.5" in s.lines()
        assert self.pending(s) == []  # 승인은 저장된 격자에 적혔다
        # 부분 기록에는 승인까지 담긴 값이 올라, 보낸 칸이 바뀐 칸으로 다시 잡히지 않는다.
        assert set(s.store.beat_grid_snapshots[SONG_KEY]) == {("FOH", 4)}
        assert s.unsent() == []

    def test_the_approval_note_is_not_taken_for_a_changed_cell_afterwards(self, applied) -> None:
        s = applied
        s.edit(4, "FOH", {"color_preset_no": "4.5"})
        assert s.session.beat_grid_apply(cells=[("FOH", 4)])["ok"] is True
        s.console.executed.clear()
        # 다시 보내도 이미 같은 칸이다 — 승인 기록 때문에 바뀐 칸으로 잡히지 않는다.
        status = s.session.beat_grid_apply(cells=[("FOH", 4)])
        assert status["ok"] is False
        assert "이미 콘솔에 반영된 내용과 같아" in status["reason"]
        assert s.lines() == []

    def test_a_declined_card_records_no_approval(self, tmp_path) -> None:
        s = _applied(tmp_path, decisions=(True, False))
        s.edit(4, "FOH", {"color_preset_no": "4.5"})
        before = s.state()
        status = s.session.beat_grid_apply(cells=[("FOH", 4)])
        assert status["ok"] is False
        assert s.lines() == []
        assert s.state() == before
        assert self.pending(s) == [("FOH", 4)]

    def test_a_byte_mismatch_records_no_approval_and_no_snapshot_change(
        self, applied, monkeypatch
    ) -> None:
        s = applied
        s.edit(4, "FOH", {"color_preset_no": "4.5"})
        before = s.state()
        mismatch = SimpleNamespace(passed=False, sent_not_approved=("stray",), approved_not_sent=())
        monkeypatch.setattr(
            s.session, "_beat_grid_verify_approval_vs_sent", lambda *args, **kwargs: mismatch
        )
        status = s.session.beat_grid_apply(cells=[("FOH", 4)])
        assert status["approval_vs_sent"]["match"] is False
        assert "completed" not in status
        # 승인 카드는 통과해 줄이 나갔지만 승인=송신이 어긋났으니 승인도 칸 기록도 남기지 않는다.
        assert s.lines()
        assert s.state() == before
        assert self.pending(s) == [("FOH", 4)]

    def test_an_edit_made_while_the_card_was_open_is_not_marked_as_sent(
        self, applied, monkeypatch
    ) -> None:
        s = applied
        s.edit(4, "FOH", {"color_preset_no": "4.5"})
        real_dispatch = s.session._dispatch_declared

        def dispatch_then_edit(*args, **kwargs):
            executed = real_dispatch(*args, **kwargs)
            # 승인 카드가 떠 있는 동안 감독이 같은 칸의 색 번호를 바꿨다.
            s.edit(4, "FOH", {"color_preset_no": "4.4"})
            return executed

        monkeypatch.setattr(s.session, "_dispatch_declared", dispatch_then_edit)
        status = s.session.beat_grid_apply(cells=[("FOH", 4)])
        assert status["ok"] is True
        # 보낸 것은 4.5 였다 — 4.4 로 바뀐 칸은 승인도 못 받고 미반영으로 남는다.
        assert "Group 8 ; At Preset 4.5" in s.lines()
        assert _cell(s.store, "FOH", 4)["color_preset_no"] == "4.4"
        assert self.pending(s) == [("FOH", 4)]
        assert s.unsent() == [{"group_name": "FOH", "bar": 4}]


_FADE_GONE = {"entry": {"fade_bars": None, "mib_mode": None}}


def _first_partial_apply(s: Applied) -> dict:
    """BACK 2마디를 고치고 서버를 다시 띄운 뒤 그 칸만 칸 단위로 먼저 보낸다 — 부분 칸 기록이
    남는다. 이어지는 시험이 콘솔 줄과 승인 카드를 새로 볼 수 있게 비워 둔다."""
    s.edit(2, "BACK", ENTRY)
    _restart_server(s)
    status = s.session.beat_grid_apply(cells=[("BACK", 2)])
    assert status["ok"] is True
    assert status["subset"]["baseline"] == "record"
    s.console.executed.clear()
    s.approval.requests.clear()
    return status


def _replayed_grid(s: Applied) -> dict:
    return s.session.song_timeline_replay()["timeline"]["beat_grid"]


class TestPartialSnapshot:
    """서버를 다시 띄운 뒤 칸 단위로 먼저 보낸 곡 — 칸 기록이 **부분**이다(보낸 칸만 안다).

    기록에 없는 칸은 모르는 칸이다: 바뀐 칸으로 세지도, 콘솔과 같다고 하지도 않는다."""

    def test_the_first_record_apply_stores_a_partial_snapshot_with_nothing_pending(
        self, applied
    ) -> None:
        s = applied
        status = _first_partial_apply(s)
        snapshot = s.store.beat_grid_snapshots[SONG_KEY]
        assert isinstance(snapshot, PartialCellSnapshot)
        # 보낸 칸의 지금 값만 담긴다 — 나머지 칸은 모르는 칸이다.
        current = beat_grid_cell_snapshot(s.store.latest["beat_grid"])
        assert snapshot == {("BACK", 2): current[("BACK", 2)]}
        # 보낸 칸은 아는 칸이고 같다 — 대기 수는 null 이 아니라 0이다.
        assert status["pending_apply_count"] == 0
        assert s.unsent() == []
        grid = _replayed_grid(s)
        assert grid["unsent_cells"] == []
        assert grid["known_cells"] == [["BACK", 2]]
        assert grid["partial_baseline"] == "snapshot"

    def test_changing_a_sent_cell_makes_it_pending(self, applied) -> None:
        s = applied
        _first_partial_apply(s)
        s.edit(2, "BACK", {"entry": {"fade_bars": 2, "mib_mode": None}})
        assert _status_events(s.sent, "edit")[-1]["pending_apply_count"] == 1
        assert s.unsent() == [{"group_name": "BACK", "bar": 2}]
        grid = _replayed_grid(s)
        assert grid["unsent_cells"] == [{"group_name": "BACK", "bar": 2}]
        assert grid["known_cells"] == [["BACK", 2]]

    def test_changing_an_unknown_cell_is_not_counted(self, applied) -> None:
        s = applied
        _first_partial_apply(s)
        s.edit(3, "FOH", ENTRY)  # FOH 3마디는 모르는 칸이다
        status = _status_events(s.sent, "edit")[-1]
        assert status["ok"] is True
        assert status["pending_apply_count"] == 0
        assert s.unsent() == []
        grid = _replayed_grid(s)
        assert grid["unsent_cells"] == []
        assert grid["known_cells"] == [["BACK", 2]]  # 모르는 칸이 아는 칸이 되지도 않는다

    def test_an_unknown_selected_cell_is_sent_and_a_known_unchanged_one_is_not(
        self, applied
    ) -> None:
        s = applied
        _first_partial_apply(s)
        s.edit(3, "FOH", ENTRY)
        # BACK 2 는 아는 칸이고 같다 · FOH 3 은 모르는 칸이고 바뀌었다 · FOH 4 는 모르는 칸이다
        # (내용은 같지만 같은지 알 수 없다).
        status = s.session.beat_grid_apply(cells=[("BACK", 2), ("FOH", 3), ("FOH", 4)])

        assert status["ok"] is True
        assert status["subset"] == {
            "requested": 3,
            "applied": [["FOH", 3], ["FOH", 4]],
            "not_applied": [{"group_name": "BACK", "bar": 2, "reason": CELL_UNCHANGED_REASON}],
            "baseline": "snapshot",
        }
        assert status["blocked_cells"] == []  # 같은 칸은 「막힌 칸」이 아니다
        assert _stored(s.lines()) == [("2", "3"), ("2", "4")]
        assert not any(line.startswith(_FORBIDDEN_PREFIXES) for line in s.lines())
        # 보낸 칸이 부분 기록에 더해졌고, 기록은 계속 부분이다.
        snapshot = s.store.beat_grid_snapshots[SONG_KEY]
        assert isinstance(snapshot, PartialCellSnapshot)
        assert set(snapshot) == {("BACK", 2), ("FOH", 3), ("FOH", 4)}
        assert status["pending_apply_count"] == 0
        assert _replayed_grid(s)["known_cells"] == [["BACK", 2], ["FOH", 3], ["FOH", 4]]

    def test_a_known_changed_cell_is_sent_and_the_snapshot_stays_partial(self, applied) -> None:
        s = applied
        _first_partial_apply(s)
        s.edit(2, "BACK", {"entry": {"fade_bars": 2, "mib_mode": None}})
        status = s.session.beat_grid_apply(cells=[("BACK", 2)])
        assert status["ok"] is True
        assert status["subset"]["applied"] == [["BACK", 2]]
        assert status["subset"]["baseline"] == "snapshot"
        assert _stored(s.lines()) == [("1", "2")]
        snapshot = s.store.beat_grid_snapshots[SONG_KEY]
        assert isinstance(snapshot, PartialCellSnapshot)
        assert snapshot == {
            ("BACK", 2): beat_grid_cell_snapshot(s.store.latest["beat_grid"])[("BACK", 2)]
        }
        assert s.unsent() == []

    def test_only_known_unchanged_cells_leave_nothing_to_send(self, applied) -> None:
        s = applied
        _first_partial_apply(s)
        before = s.state()
        status = s.session.beat_grid_apply(cells=[("BACK", 2)])
        _assert_refused_untouched(
            s, status, before=before, reason_has="이미 콘솔에 반영된 내용과 같아"
        )
        assert isinstance(s.store.beat_grid_snapshots[SONG_KEY], PartialCellSnapshot)

    def test_the_removal_check_is_kept_for_known_cells_only(self, applied) -> None:
        s = applied
        s.edit(2, "BACK", ENTRY)
        s.edit(3, "FOH", ENTRY)
        _restart_server(s)
        # 기록 기준으로 BACK 2 만 보낸다 — 이 칸만 아는 칸이 된다(페이드가 콘솔에 올라갔다).
        assert s.session.beat_grid_apply(cells=[("BACK", 2)])["ok"] is True
        s.console.executed.clear()
        s.edit(2, "BACK", _FADE_GONE)  # 아는 칸의 페이드를 지웠다
        s.edit(3, "FOH", _FADE_GONE)  # 모르는 칸의 페이드를 지웠다 — 전에 무엇이 있었는지 모른다
        status = s.session.beat_grid_apply(cells=[("BACK", 2), ("FOH", 3)])

        assert status["ok"] is True
        assert status["subset"]["applied"] == [["FOH", 3]]
        (skipped,) = status["subset"]["not_applied"]
        assert (skipped["group_name"], skipped["bar"]) == ("BACK", 2)
        assert skipped["reason"].startswith("지운 항목(entry.fade_bars)은")
        assert _stored(s.lines()) == [("2", "3")]
        # 지운 칸은 기록이 그대로라 계속 미반영이고, 보낸 모르던 칸은 기록에 더해졌다.
        assert s.unsent() == [{"group_name": "BACK", "bar": 2}]
        assert set(s.store.beat_grid_snapshots[SONG_KEY]) == {("BACK", 2), ("FOH", 3)}

    def test_a_known_cell_that_left_the_grid_still_counts_as_unsent(self, applied) -> None:
        s = applied
        _first_partial_apply(s)
        s.mutate_tracks(lambda tracks: tracks[0]["cues"].pop(1))  # BACK 의 2마디 칸을 뺐다
        assert s.unsent() == [{"group_name": "BACK", "bar": 2}]

    def test_the_flag_survives_every_frame_and_the_replay(self, applied) -> None:
        s = applied
        _first_partial_apply(s)
        s.sent.clear()
        s.edit(3, "FOH", ENTRY)
        frames = [e for e in s.sent if e.get("type") == "song_timeline"]
        assert frames
        for frame in frames + [s.session.song_timeline_replay()]:
            grid = frame["timeline"]["beat_grid"]
            assert grid["known_cells"] == [["BACK", 2]]
            assert grid["partial_baseline"] == "snapshot"
        status = [e for e in s.sent if e.get("type") == "beat_grid_send_status"][-1]
        assert status["pending_apply_count"] == 0  # 상태 이벤트의 대기 수도 같은 기준이다

    def test_a_whole_song_apply_replaces_it_with_a_full_snapshot(self, applied) -> None:
        s = applied
        _first_partial_apply(s)
        s.sent.clear()
        assert s.session.beat_grid_apply()["ok"] is True
        snapshot = s.store.beat_grid_snapshots[SONG_KEY]
        assert not isinstance(snapshot, PartialCellSnapshot)
        assert set(snapshot) == set(beat_grid_cell_snapshot(s.store.latest["beat_grid"]))
        grid = [e for e in s.sent if e.get("type") == "song_timeline"][-1]["timeline"]["beat_grid"]
        assert "known_cells" not in grid
        assert grid["unsent_cells"] == []
        assert grid["partial_baseline"] == "snapshot"
        assert "known_cells" not in _replayed_grid(s)
        # 이제 모든 칸이 아는 칸이다 — 전에 모르던 칸도 같으면 보내지 않는다.
        status = s.session.beat_grid_apply(cells=[("FOH", 1)])
        assert status["ok"] is False
        assert "이미 콘솔에 반영된 내용과 같아" in status["reason"]


class TestPartialBaselineFlag:
    """``beat_grid.partial_baseline`` — 칸 단위 반영이 무엇을 기준으로 삼는지, 모든 타임라인
    프레임에 ``unsent_cells`` 옆에 실린다."""

    @staticmethod
    def grid_of(frame: dict) -> dict:
        return frame["timeline"]["beat_grid"]

    def test_a_never_applied_song_has_no_baseline(self, tmp_path) -> None:
        store = SongTimelineStore()
        store.latest = _grid_timeline()
        session, _console, _approval, _audit = _new_session(tmp_path, store=store)
        grid = self.grid_of(session.song_timeline_replay())
        assert grid["unsent_cells"] is None
        assert grid["partial_baseline"] is None

    def test_after_a_whole_song_apply_the_snapshot_is_the_baseline(self, applied) -> None:
        grid = self.grid_of(applied.session.song_timeline_replay())
        assert grid["unsent_cells"] == []
        assert grid["partial_baseline"] == "snapshot"

    def test_after_a_restart_the_record_is_the_baseline(self, applied) -> None:
        _restart_server(applied)
        grid = self.grid_of(applied.session.song_timeline_replay())
        assert grid["unsent_cells"] is None  # 의미는 그대로 — 칸 기록이 없으면 null
        assert grid["partial_baseline"] == "record"

    def test_a_record_without_tracks_is_no_baseline(self, applied) -> None:
        _restart_server(applied)
        applied.store.set_beat_grid_allocation(
            SONG_KEY, {**applied.store.beat_grid_allocation(SONG_KEY), "tracks": {}}
        )
        grid = self.grid_of(applied.session.song_timeline_replay())
        assert grid["unsent_cells"] is None
        assert grid["partial_baseline"] is None

    def test_every_live_frame_carries_it(self, applied) -> None:
        s = applied
        _restart_server(s)
        s.sent.clear()
        s.edit(2, "BACK", ENTRY)  # 편집 프레임 — 아직 칸 기록이 없다
        edit_frames = [e for e in s.sent if e.get("type") == "song_timeline"]
        assert edit_frames
        assert [self.grid_of(frame)["partial_baseline"] for frame in edit_frames] == [
            "record"
        ] * len(edit_frames)
        s.sent.clear()
        assert s.session.beat_grid_apply(cells=[("BACK", 2)])["ok"] is True  # 반영 프레임
        apply_frames = [e for e in s.sent if e.get("type") == "song_timeline"]
        assert apply_frames  # 첫 성공이 부분 칸 기록을 남겼다 — 이제 기준은 칸 기록이다
        assert [self.grid_of(frame)["partial_baseline"] for frame in apply_frames] == [
            "snapshot"
        ] * len(apply_frames)

    def test_the_whole_song_apply_moves_the_baseline_to_the_snapshot(self, applied) -> None:
        s = applied
        _restart_server(s)
        s.sent.clear()
        assert s.session.beat_grid_apply()["ok"] is True
        frame = [e for e in s.sent if e.get("type") == "song_timeline"][-1]
        assert self.grid_of(frame)["partial_baseline"] == "snapshot"

    def test_the_pure_derivation_defaults_to_no_record(self) -> None:
        timeline = _grid_timeline()
        key = (timeline.get("song_title"), timeline.get("sequence_number"))
        snapshot = {key: beat_grid_cell_snapshot(timeline["beat_grid"])}

        def derived(snapshots, **extra) -> dict:
            return derive_beat_grid_fields(
                timeline, snapshots=snapshots, pool_slots={}, empty_marks={}, **extra
            )["beat_grid"]

        assert derived({})["partial_baseline"] is None
        assert derived({}, has_owned_record=True)["partial_baseline"] == "record"
        assert derived(snapshot)["partial_baseline"] == "snapshot"
        assert derived(snapshot, has_owned_record=True)["partial_baseline"] == "snapshot"

    def test_the_pure_derivation_lists_known_cells_only_for_a_partial_snapshot(self) -> None:
        timeline = _grid_timeline()
        key = (timeline.get("song_title"), timeline.get("sequence_number"))
        cells = beat_grid_cell_snapshot(timeline["beat_grid"])
        full = dict(cells)
        partial = PartialCellSnapshot(
            {("FOH", 3): cells[("FOH", 3)], ("BACK", 2): cells[("BACK", 2)]}
        )

        def derived(snapshot, stored_extra=None) -> dict:
            source = copy.deepcopy(timeline)
            source["beat_grid"].update(stored_extra or {})
            snapshots = {} if snapshot is None else {key: snapshot}
            return derive_beat_grid_fields(
                source, snapshots=snapshots, pool_slots={}, empty_marks={}, has_owned_record=True
            )["beat_grid"]

        grid = derived(partial)
        assert grid["known_cells"] == [["BACK", 2], ["FOH", 3]]  # 정렬한 [줄, 마디]
        assert grid["unsent_cells"] == []  # 아는 칸은 모두 지금과 같다 — 목록이다(null 이 아니다)
        assert grid["partial_baseline"] == "snapshot"
        # 전체 기록이나 기록이 없으면 키 자체가 없다 — 저장된 격자에 남은 옛 키도 싣지 않는다.
        stale = {"known_cells": [["OLD", 1]]}
        assert "known_cells" not in derived(full)
        assert "known_cells" not in derived(None)
        assert "known_cells" not in derived(full, stale)
        assert "known_cells" not in derived(None, stale)
        assert derived(full)["unsent_cells"] == []

    def test_the_library_load_response_carries_it_too(self, tmp_path) -> None:
        deps = _deps(tmp_path)
        title = deps.song_timeline_store.latest["song_title"]

        def save_and_load(client: TestClient) -> dict:
            saved = client.post("/api/timelines", json={"name": title})
            assert saved.status_code == 200, saved.text
            loaded = client.post(f"/api/timelines/{saved.json()['item']['id']}/load")
            assert loaded.status_code == 200, loaded.text
            return loaded.json()["timeline"]["beat_grid"]

        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            _send(ws, type="beat_grid_apply")
            assert _approve_until(ws, "beat_grid_send_status")["ok"] is True
            grid = save_and_load(client)
            assert (grid["unsent_cells"], grid["partial_baseline"]) == ([], "snapshot")
            deps.song_timeline_store.beat_grid_snapshots.clear()  # 서버를 다시 띄운 것과 같다
            grid = save_and_load(client)
            assert (grid["unsent_cells"], grid["partial_baseline"]) == (None, "record")


# =============================================================================
# 3-b. 일괄 편집 — beat_grid_edit(cells=…)
# =============================================================================


def _edit_session(tmp_path):
    store = SongTimelineStore()
    store.latest = _grid_timeline()
    sent: list[dict] = []
    session, console, _approval, _audit = _new_session(tmp_path, store=store, sent=sent)
    return session, console, store, sent


def _cell(store: SongTimelineStore, group_name: str, bar: int) -> dict:
    track = next(t for t in store.latest["beat_grid"]["tracks"] if t["group_name"] == group_name)
    return next(c for c in track["cues"] if c["bar"] == bar)


def _status_events(sent: list[dict], action: str) -> list[dict]:
    return [
        e
        for e in sent
        if e.get("type") == "beat_grid_send_status" and e.get("last_action") == action
    ]


class TestBulkEdit:
    def test_every_chosen_cell_is_edited_and_the_others_are_not(self, tmp_path) -> None:
        session, console, store, sent = _edit_session(tmp_path)
        before = copy.deepcopy(store.latest["beat_grid"])
        event = session.beat_grid_edit(
            None, None, ENTRY, cells=[("BACK", 1), ("FOH", 2), ("FOH", 4)]
        )
        assert event["status"] == "ok"
        for group_name, bar in (("BACK", 1), ("FOH", 2), ("FOH", 4)):
            assert _cell(store, group_name, bar)["entry"]["fade_bars"] == 1
        for group_name, bar in (("BACK", 2), ("BACK", 4), ("FOH", 1), ("FOH", 3)):
            assert "entry" not in _cell(store, group_name, bar)
        assert store.latest["beat_grid"] != before
        assert console.executed == []  # 콘솔 무접촉
        assert "BACK 1마디" in event["text"]
        assert "FOH 4마디" in event["text"]

    def test_the_result_equals_the_same_edits_made_one_cell_at_a_time(self, tmp_path) -> None:
        (tmp_path / "bulk").mkdir()
        (tmp_path / "single").mkdir()
        bulk_session, _c, bulk_store, _s = _edit_session(tmp_path / "bulk")
        bulk_session.beat_grid_edit(None, None, ENTRY, cells=[("BACK", 1), ("FOH", 2)])
        single_session, _c2, single_store, _s2 = _edit_session(tmp_path / "single")
        single_session.beat_grid_edit(1, "BACK", ENTRY)
        single_session.beat_grid_edit(2, "FOH", ENTRY)
        assert bulk_store.latest["beat_grid"] == single_store.latest["beat_grid"]

    def test_it_is_stored_once_and_undone_in_one_step(self, tmp_path) -> None:
        session, _console, store, sent = _edit_session(tmp_path)
        original = copy.deepcopy(store.latest["beat_grid"])
        session.beat_grid_edit(None, None, ENTRY, cells=[("BACK", 1), ("FOH", 2), ("FOH", 3)])
        timeline_events = [e for e in sent if e.get("type") == "song_timeline"]
        assert len(timeline_events) == 1  # 칸마다 저장·전송하지 않는다
        assert store.latest["draft"]["depth"] == 1
        edit_statuses = _status_events(sent, "edit")
        assert len(edit_statuses) == 1
        assert edit_statuses[0]["ok"] is True
        session.undo_timeline_draft()
        assert store.latest["beat_grid"] == original

    def test_one_refused_cell_changes_nothing_at_all(self, tmp_path) -> None:
        session, console, store, sent = _edit_session(tmp_path)
        # FOH 3마디만 같은 축을 앱 움직임과 효과 프리셋이 함께 쓴다 — effect_kind 를 위치로 바꾸면
        # 이 칸만 거절된다(다른 칸은 통과한다).
        movement = {
            "shape": "wave",
            "axes": ["Tilt"],
            "period_unit": "beat",
            "period_value": 2,
            "phase_spread": None,
        }
        timeline = copy.deepcopy(store.latest)
        foh_3 = next(
            c
            for t in timeline["beat_grid"]["tracks"]
            if t["group_name"] == "FOH"
            for c in t["cues"]
            if c["bar"] == 3
        )
        foh_3.update(app_movement=movement, effect_preset_no="22.1")
        store.latest = timeline
        before = copy.deepcopy(store.latest)
        depth_before = session._draft_history.depth
        sent.clear()

        event = session.beat_grid_edit(
            None, None, {"effect_kind": "position"}, cells=[("BACK", 1), ("FOH", 3), ("FOH", 2)]
        )

        assert "박자 격자를 수정하지 않았습니다" in event["text"]
        assert "FOH 3마디" in event["text"]
        assert "BACK 1마디" not in event["text"]  # 거절한 칸만 이름으로 적는다
        assert "FOH 2마디" not in event["text"]
        assert "REQ-LDBEAT-006" in event["text"]  # 기존 검증기의 사유가 그대로 실린다
        assert store.latest == before  # 통과한 칸(BACK 1·FOH 2)도 바뀌지 않았다
        assert session._draft_history.depth == depth_before  # 되돌리기 단계도 쌓지 않았다
        assert console.executed == []
        assert [e for e in sent if e.get("type") == "song_timeline"] == []
        (status,) = _status_events(sent, "edit")
        assert status["ok"] is False
        assert "FOH 3마디" in status["reason"]

    def test_the_same_reason_is_not_repeated_for_every_refused_cell(self, tmp_path) -> None:
        session, _console, store, _sent = _edit_session(tmp_path)
        before = copy.deepcopy(store.latest)
        event = session.beat_grid_edit(
            None, None, {"not_a_real_field": 1}, cells=[("BACK", 1), ("BACK", 2), ("FOH", 3)]
        )
        assert event["text"].count("not_a_real_field") == 1
        assert "BACK 1마디, BACK 2마디, FOH 3마디" in event["text"]
        assert store.latest == before

    def test_a_cell_missing_from_the_grid_is_refused_and_named(self, tmp_path) -> None:
        session, _console, store, _sent = _edit_session(tmp_path)
        before = copy.deepcopy(store.latest)
        event = session.beat_grid_edit(None, None, ENTRY, cells=[("BACK", 1), ("BACK", 3)])
        assert "BACK 3마디" in event["text"]
        assert "격자에 없습니다" in event["text"]
        assert store.latest == before  # 있는 칸(BACK 1)도 바뀌지 않았다

    def test_missing_cells_are_never_created(self, tmp_path) -> None:
        session, _console, store, _sent = _edit_session(tmp_path)
        session.beat_grid_edit(None, None, ENTRY, cells=[("BACK", 99)])
        assert all(c["bar"] != 99 for t in store.latest["beat_grid"]["tracks"] for c in t["cues"])

    def test_cells_next_to_bar_target_or_sentence_are_refused(self, tmp_path) -> None:
        session, _console, store, _sent = _edit_session(tmp_path)
        before = copy.deepcopy(store.latest)
        for kwargs in (
            {"bar": 1, "target": None, "sentence": None},
            {"bar": None, "target": "BACK", "sentence": None},
            {"bar": None, "target": None, "sentence": "1마디 BACK 밝기를 70%로"},
        ):
            event = session.beat_grid_edit(
                kwargs["bar"], kwargs["target"], ENTRY, kwargs["sentence"], cells=[("BACK", 1)]
            )
            assert "함께 쓸 수 없습니다" in event["text"]
        assert store.latest == before

    def test_empty_changes_or_empty_cells_are_refused(self, tmp_path) -> None:
        session, _console, store, _sent = _edit_session(tmp_path)
        before = copy.deepcopy(store.latest)
        no_changes = session.beat_grid_edit(None, None, {}, cells=[("BACK", 1)])
        no_cells = session.beat_grid_edit(None, None, ENTRY, cells=[])
        assert "못 읽었습니다" in no_changes["text"]
        assert "못 읽었습니다" in no_cells["text"]
        assert store.latest == before

    def test_the_single_cell_path_is_unchanged(self, tmp_path) -> None:
        session, console, store, _sent = _edit_session(tmp_path)
        event = session.beat_grid_edit(2, "FOH", ENTRY)
        assert event["status"] == "ok"
        assert _cell(store, "FOH", 2)["entry"]["fade_bars"] == 1
        assert console.executed == []


# =============================================================================
# 4. WebSocket 배선 — cells 가 app.py 디스패치를 지나 세션에 닿는다
# =============================================================================


def _wired_deps(tmp_path) -> tuple[WebDeps, Any]:
    """콘솔 핸들을 쥔 웹 배선 — 시험이 가짜 콘솔에 「이 앱이 방금 만든 시퀀스」를 보여 준다."""
    console = FakeConsole(state_tree=_state_tree())
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=5.0)
    gate = SafetyGate(console=console, audit=audit, approval_port=channel)
    deps = WebDeps(
        gate=gate,
        provider=ScriptedProvider([]),
        system_prefix="PREFIX",
        audit=audit,
        approval_channel=channel,
        timeline_library=SongTimelineLibrary(tmp_path / "library.json"),
    )
    deps.song_timeline_store.latest = _grid_timeline()
    return deps, console


class TestCellsOverTheWire:
    def test_apply_with_cells_reaches_the_subset_path(self, tmp_path) -> None:
        deps = _deps(tmp_path)
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            _send(ws, type="beat_grid_apply", cells=[["BACK", 1]])
            status = drain_until(ws, "beat_grid_send_status")
        # 전체 반영이 돌았다면 승인 카드가 먼저 떴을 것이다 — 칸 단위 길의 거절 사유가 왔다는 것은
        # ``cells`` 가 파서와 app.py 분기를 지나 ``session.beat_grid_apply(cells=…)`` 에 닿았다는
        # 뜻이다.
        assert status["last_action"] == "apply"
        assert status["ok"] is False
        assert status["reason"] == NO_RECORD_REASON

    def test_bulk_edit_over_the_wire(self, tmp_path) -> None:
        deps = _deps(tmp_path)
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            _send(ws, type="beat_grid_edit", cells=[["BACK", 1]], changes=ENTRY)
            status = drain_until(ws, "beat_grid_send_status")
        assert status["last_action"] == "edit"
        assert status["ok"] is True
        cue = deps.song_timeline_store.latest["beat_grid"]["tracks"][0]["cues"][0]
        assert cue["entry"]["fade_bars"] == 1

    def test_a_malformed_cells_frame_is_a_protocol_error(self, tmp_path) -> None:
        deps = _deps(tmp_path)
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            _send(ws, type="beat_grid_apply", cells=[["BACK", True]])
            event = drain_until(ws, "error")
        assert event["kind"] == "protocol"

    def test_the_whole_song_message_is_still_a_whole_song_apply(self, tmp_path) -> None:
        deps = _deps(tmp_path)
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            _send(ws, type="beat_grid_apply")
            status = _approve_until(ws, "beat_grid_send_status")
        assert status["ok"] is True
        assert "subset" not in status
        assert status["completed"] == "reflected"

    def test_a_subset_apply_works_end_to_end_over_the_wire(self, tmp_path) -> None:
        # 전체 반영 → (콘솔에 만들어진 시퀀스 보이기) → 일괄 편집 → 칸 단위 반영, 전부 WebSocket.
        deps, console = _wired_deps(tmp_path)
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            _send(ws, type="beat_grid_apply")
            assert _approve_until(ws, "beat_grid_send_status")["ok"] is True
            _show_applied_on_console(
                console, deps.song_timeline_store.beat_grid_allocation(SONG_KEY)
            )
            console.executed.clear()
            _send(ws, type="beat_grid_edit", cells=[["BACK", 2], ["FOH", 3]], changes=ENTRY)
            assert drain_until(ws, "beat_grid_send_status")["last_action"] == "edit"
            _send(ws, type="beat_grid_apply", cells=[["BACK", 2], ["FOH", 3], ["FOH", 1]])
            status = _approve_until(ws, "beat_grid_send_status")
        assert status["ok"] is True
        assert status["subset"] == {
            "requested": 3,
            "applied": [["BACK", 2], ["FOH", 3]],
            "not_applied": [
                {"group_name": "FOH", "bar": 1, "reason": "콘솔과 같음(바뀐 칸 아님)"},
            ],
            "baseline": "snapshot",
        }
        assert status["pending_apply_count"] == 0
        lines = [line for line in console.executed if line != "SaveShow"]
        stores = [line for line in lines if line.startswith("Store Sequence")]
        assert [_FADE_STORE.fullmatch(line).groups() for line in stores] == [("1", "2"), ("2", "3")]
        assert not any(
            "Timecode" in line or line.startswith(("Delete", "Set Sequence")) for line in lines
        )

    def test_the_partial_snapshot_reaches_the_library_load_and_a_fresh_connection(
        self, tmp_path
    ) -> None:
        # 서버를 다시 띄운 것처럼 칸 기록을 비운 뒤 칸 단위로 먼저 보낸다 — 전부 WebSocket + REST.
        deps, console = _wired_deps(tmp_path)
        store = deps.song_timeline_store
        title = store.latest["song_title"]
        with TestClient(create_app(deps)) as client, client.websocket_connect("/ws") as ws:
            _send(ws, type="beat_grid_apply")
            assert _approve_until(ws, "beat_grid_send_status")["ok"] is True
            _show_applied_on_console(console, store.beat_grid_allocation(SONG_KEY))
            store.beat_grid_snapshots.clear()
            _send(ws, type="beat_grid_edit", cells=[["BACK", 2]], changes=ENTRY)
            assert drain_until(ws, "beat_grid_send_status")["last_action"] == "edit"
            _send(ws, type="beat_grid_apply", cells=[["BACK", 2]])
            status = _approve_until(ws, "beat_grid_send_status")
            assert status["ok"] is True
            assert status["subset"]["baseline"] == "record"
            assert status["pending_apply_count"] == 0

            saved = client.post("/api/timelines", json={"name": title})
            assert saved.status_code == 200, saved.text
            loaded = client.post(f"/api/timelines/{saved.json()['item']['id']}/load")
            assert loaded.status_code == 200, loaded.text
            load_grid = loaded.json()["timeline"]["beat_grid"]
            with client.websocket_connect("/ws") as fresh:
                replay_grid = drain_until(fresh, "song_timeline")["timeline"]["beat_grid"]

        for grid in (load_grid, replay_grid):
            assert grid["unsent_cells"] == []
            assert grid["known_cells"] == [["BACK", 2]]
            assert grid["partial_baseline"] == "snapshot"
