"""SPEC-LDBEAT-001 0.5.0 — 박자 격자 에미터가 전환 ``entry``를 큐 명령에 싣는다
(카드 t576, REQ-LDBEAT-006(i-4)~(i-4f)·011~013).

- 저장은 음악 단위(마디·박) 그대로다. 초는 **송신할 때** 그 곡 BPM으로 바꾼다.
- 콘솔 명령 문면은 저장소에 이미 있는 실기 선례만 쓴다:
  - 페이드: ``CueFade`` (``server/design/cue_fade.py``)
  - 트래킹: ``Property 'Release'``·``Block``·``/CueOnly`` (``cue_sheet_apply.py``, 카드 t469)
  - 트리거: ``TrigTime`` (t549 에미터)
- 실기 미확인 칸(딜레이·위치만 늦게)과 MIB(콘솔 값이 아님, ``cue_sheet_apply`` 선례)는
  보내지 않고 이유를 남긴다.

콘솔 접촉 0건 — 순수 함수가 명령 문자열만 만든다.
"""

from __future__ import annotations

from server.design.beat_grid_emit import SongTiming, emit_beat_grid_write_bundle
from server.design.beat_grid_probes import DEFAULT_PROBE_IDS
from server.design.beat_grid_send import apply_beat_grid_ownership_reuse

_ALL_PASS = {probe_id: "통과" for probe_id in DEFAULT_PROBE_IDS}
_APPROVED = {"approval": {"by": "supervisor", "date": "2026-10-11", "source": "t576"}}
#: 120 BPM · 4/4 — 한 박 0.5초, 한 마디 2초. 1마디 다운비트 = 1.0초.
_TIMING = SongTiming(bpm=120.0, beats_per_bar=4, downbeat_bar1_seconds=1.0)
_SEQ = 300


def _cue(bar: int, **entry: object) -> dict:
    return {
        "bar": bar,
        "position_preset_no": "2.1",
        "evidence": _APPROVED,
        "entry": {"fade_bars": None, "mib_mode": None, **entry},
    }


def _emit(cue: dict):
    result = emit_beat_grid_write_bundle(
        [{"group_name": "BACK", "group_no": 7, "group_no_confirmed": True, "cues": [cue]}],
        timing=_TIMING,
        sequence_numbers={"BACK": _SEQ},
        timecode_numbers={"BACK": 20},
        dimmer_attributes={},
        probe_results=_ALL_PASS,
    )
    (track,) = result.tracks
    (emitted,) = track.cues
    return emitted


def _store_line(emitted) -> str:
    (line,) = [c for c in emitted.commands if c.startswith("Store Sequence ")]
    return line


def _trig_time(emitted) -> str:
    (line,) = [c for c in emitted.commands if "'TrigTime'" in c]
    return line


class TestNoEntryKeepsTheCueBaseline:
    def test_an_empty_entry_emits_the_sequence_first_cue_lines(self) -> None:
        # 카드 t612 — 첫 큐 저장이 시퀀스를 만들고, 이름 줄은 그 바로 뒤에 온다.
        emitted = _emit(_cue(2))
        assert emitted.commands == (
            "Group 7 ; At Preset 2.1",
            f"Store Sequence {_SEQ} Cue 1",
            f"Set Sequence {_SEQ} Property 'Name' 'LDBEAT BACK'",
            "ClearAll",
            f"Set Cue 1 Sequence {_SEQ} Property 'TrigType' 'Time'",
            f"Set Cue 1 Sequence {_SEQ} Property 'TrigTime' 3",
        )
        assert emitted.skipped_fields == ()


class TestFade:
    def test_fade_bars_become_seconds_at_send_time(self) -> None:
        # 2마디 × 4박 × 0.5초 = 4초
        assert _store_line(_emit(_cue(2, fade_bars=2))) == f"Store Sequence {_SEQ} Cue 1 CueFade 4"

    def test_fade_beats_become_seconds_at_send_time(self) -> None:
        # 1박 × 0.5초 = 0.5초
        assert (
            _store_line(_emit(_cue(2, fade_beats=1))) == f"Store Sequence {_SEQ} Cue 1 CueFade 0.5"
        )

    def test_zero_fade_is_sent_as_a_snap(self) -> None:
        assert _store_line(_emit(_cue(2, fade_bars=0))) == f"Store Sequence {_SEQ} Cue 1 CueFade 0"

    def test_both_fade_units_at_once_blocks_the_cell(self) -> None:
        emitted = _emit(_cue(2, fade_bars=1, fade_beats=2))
        assert emitted.commands == ()
        assert "fade_bars" in emitted.blocked_reason and "fade_beats" in emitted.blocked_reason

    def test_the_stored_entry_keeps_musical_units(self) -> None:
        cue = _cue(2, fade_bars=2)
        _emit(cue)
        assert cue["entry"]["fade_bars"] == 2
        assert "fade_seconds" not in cue["entry"]


class TestTriggerBeat:
    def test_trigger_beat_moves_the_trigger_inside_the_bar(self) -> None:
        # 2마디 시작 3.0초 + (3박 - 1) × 0.5초 = 4.0초
        assert _trig_time(_emit(_cue(2, trigger_beat=3))).endswith("'TrigTime' 4")

    def test_trigger_beat_one_is_the_bar_start(self) -> None:
        assert _trig_time(_emit(_cue(2, trigger_beat=1))).endswith("'TrigTime' 3")

    def test_an_out_of_range_trigger_beat_blocks_the_cell(self) -> None:
        for beat in (0, 5):
            emitted = _emit(_cue(2, trigger_beat=beat))
            assert emitted.commands == ()
            assert "trigger_beat" in emitted.blocked_reason


class TestTracking:
    def test_release_is_set_after_the_cue_is_stored(self) -> None:
        commands = _emit(_cue(2, tracking="Release")).commands
        line = f"Set Cue 1 Sequence {_SEQ} Property 'Release' 1"
        assert line in commands
        assert commands.index(line) > commands.index(f"Store Sequence {_SEQ} Cue 1")

    def test_block_is_a_keyword_command_after_the_store(self) -> None:
        commands = _emit(_cue(2, tracking="Block")).commands
        assert commands[-1] == f"Block Sequence {_SEQ} Cue 1"

    def test_cue_only_is_a_store_option(self) -> None:
        assert (
            _store_line(_emit(_cue(2, tracking="Cue Only")))
            == f"Store Sequence {_SEQ} Cue 1 /CueOnly"
        )

    def test_track_sends_nothing_extra(self) -> None:
        assert _emit(_cue(2, tracking="Track")).commands == _emit(_cue(2)).commands

    def test_fade_and_cue_only_order_matches_the_measured_form(self) -> None:
        # 실측 순서(cue_sheet_apply): Store … CueFade <초> 뒤에 저장 옵션.
        assert (
            _store_line(_emit(_cue(2, fade_beats=2, tracking="Cue Only")))
            == f"Store Sequence {_SEQ} Cue 1 CueFade 1 /CueOnly"
        )


class TestUnsentFields:
    def test_delay_beats_is_not_sent_and_says_why(self) -> None:
        emitted = _emit(_cue(2, delay_beats=1))
        assert emitted.commands == _emit(_cue(2)).commands
        assert any("delay_beats" in reason for reason in emitted.skipped_fields)

    def test_position_late_beats_is_not_sent_and_says_why(self) -> None:
        emitted = _emit(_cue(2, position_late_beats=2))
        assert emitted.commands == _emit(_cue(2)).commands
        assert any("position_late_beats" in reason for reason in emitted.skipped_fields)

    def test_mib_mode_is_not_a_console_value(self) -> None:
        emitted = _emit(_cue(2, mib_mode="dark"))
        assert emitted.commands == _emit(_cue(2)).commands
        assert any("mib_mode" in reason for reason in emitted.skipped_fields)

    def test_mib_none_is_silent(self) -> None:
        assert _emit(_cue(2, mib_mode="none")).skipped_fields == ()


class TestReapplyOverwriteStillLands:
    def test_overwrite_is_appended_to_a_store_line_that_carries_a_fade(self) -> None:
        result = emit_beat_grid_write_bundle(
            [
                {
                    "group_name": "BACK",
                    "group_no": 7,
                    "group_no_confirmed": True,
                    "cues": [_cue(2, fade_bars=2, tracking="Cue Only")],
                }
            ],
            timing=_TIMING,
            sequence_numbers={"BACK": _SEQ},
            timecode_numbers={"BACK": 20},
            dimmer_attributes={},
            probe_results=_ALL_PASS,
            recorded_cue_numbers={"BACK": {2: 1}},
        )
        reused = apply_beat_grid_ownership_reuse(
            result,
            owned_sequences={"BACK": _SEQ},
            owned_timecode=20,
            recorded_cue_numbers={"BACK": {2: 1}},
        )
        assert f"Store Sequence {_SEQ} Cue 1 CueFade 4 /CueOnly /Overwrite" in reused.commands


# =============================================================================
# 세션 경로 — 새 줄이 승인 묶음·승인=송신 대조에 들어가고, 안 보낸 칸은 승인 카드에
# =============================================================================


class TestSessionApplyCarriesEntry:
    def test_entry_lines_ride_the_one_approval_and_unsent_fields_are_shown(self, tmp_path) -> None:
        from server.web.session import SongTimelineStore

        from .test_beat_grid_reapply_t572 import _APPROVED_EVIDENCE, _new_session, _timeline

        cue = {
            "bar": 2,
            "position_preset_no": "2.1",
            "evidence": _APPROVED_EVIDENCE,
            "entry": {"fade_bars": 1, "mib_mode": None, "delay_beats": 1, "tracking": "Block"},
        }
        store = SongTimelineStore()
        store.latest = _timeline(cues=[cue])
        session, console, approval, _audit = _new_session(tmp_path, store=store)

        event = session.beat_grid_apply()

        assert event["ok"] is True
        assert event["approval_vs_sent"]["match"] is True
        assert len(approval.requests) == 1
        approved = approval.requests[0].commands
        # 페이드(1마디)와 트래킹(Block) 줄이 승인 묶음 안에 있고, 그대로 나갔다.
        store_lines = [c for c in approved if c.startswith("Store Sequence ") and " Cue 1 " in c]
        assert len(store_lines) == 1 and " CueFade " in store_lines[0]
        assert any(c.startswith("Block Sequence ") for c in approved)
        assert all(c in console.executed for c in approved)
        # 딜레이는 보내지 않았고, 승인 카드에 그 이유가 있다.
        assert not any("Delay" in c for c in console.executed)
        reasons = [r for item in approval.requests[0].items for r in item.risk_reasons]
        assert any("보내지 않은 전환 칸 1개" in r and "delay_beats" in r for r in reasons)
