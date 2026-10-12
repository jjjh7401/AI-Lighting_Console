"""카드 t616 — 소유 기록 큐가 0개인데 콘솔에 시퀀스가 있는 트랙은 Cue 2 부터 저장한다.

콘솔의 맨 ``Store Sequence S`` 는 시퀀스와 함께 빈 자동 Cue 1 을 만든다(t615 실기).
그 시퀀스에 ``Store Sequence S Cue 1`` (옵션 없음)을 보내면 ``User Canceled Command`` 로
멈춘다(t608 v3 S4). 감독 결정(A안, .moai/reports/t616/options.md): 자동 Cue 1 은 그대로 두고
앱 큐는 2 번부터 저장한다. 기존 큐는 건드리지 않는다.

콘솔 접촉 0건 — 순수 함수가 명령 문자열만 만든다.
"""

from __future__ import annotations

from server.design.beat_grid_emit import SongTiming, emit_beat_grid_write_bundle
from server.design.beat_grid_probes import DEFAULT_PROBE_IDS
from server.design.beat_grid_send import (
    apply_beat_grid_ownership_reuse,
    beat_grid_reapply_summary,
)

_ALL_PASS = {probe_id: "통과" for probe_id in DEFAULT_PROBE_IDS}
_APPROVED = {"approval": {"by": "supervisor", "date": "2026-10-12", "source": "t616"}}
_TIMING = SongTiming(bpm=120.0, beats_per_bar=4, downbeat_bar1_seconds=1.0)
_SEQ = 300


def _cue(bar: int) -> dict:
    return {
        "bar": bar,
        "position_preset_no": "2.1",
        "evidence": _APPROVED,
        "entry": {"fade_bars": None, "mib_mode": None},
    }


def _emit(bars: list[int], recorded: dict | None):
    return emit_beat_grid_write_bundle(
        [
            {
                "group_name": "BACK",
                "group_no": 7,
                "group_no_confirmed": True,
                "cues": [_cue(bar) for bar in bars],
            }
        ],
        timing=_TIMING,
        sequence_numbers={"BACK": _SEQ},
        timecode_numbers={"BACK": 20},
        dimmer_attributes={},
        probe_results=_ALL_PASS,
        recorded_cue_numbers=recorded,
    )


def _numbers(result) -> dict[int, int | None]:
    (track,) = result.tracks
    return {cue.bar: cue.cue_number for cue in track.cues}


class TestOwnedTrackWithEmptyRecordStartsAtCue2:
    def test_first_cue_is_stored_as_cue_2_and_next_as_cue_3(self) -> None:
        result = _emit([2, 4], {"BACK": {}})
        assert _numbers(result) == {2: 2, 4: 3}

    def test_store_line_has_no_cue_1_and_no_overwrite_after_reuse(self) -> None:
        result = _emit([2], {"BACK": {}})
        reused = apply_beat_grid_ownership_reuse(
            result,
            owned_sequences={"BACK": _SEQ},
            owned_timecode=20,
            recorded_cue_numbers={"BACK": {}},
        )
        store_lines = [c for c in reused.commands if c.startswith("Store Sequence ")]
        assert store_lines == [f"Store Sequence {_SEQ} Cue 2"]
        assert all("/Overwrite" not in line for line in reused.commands)

    def test_next_record_remembers_cue_2(self) -> None:
        result = _emit([2], {"BACK": {}})
        next_record, _preserved, _out_of_order = beat_grid_reapply_summary(
            result, recorded_cue_numbers={"BACK": {}}
        )
        assert next_record == {"BACK": {2: 2}}


class TestOtherShapesAreUnchanged:
    def test_track_without_an_ownership_record_still_starts_at_cue_1(self) -> None:
        assert _numbers(_emit([2, 4], None)) == {2: 1, 4: 2}
        assert _numbers(_emit([2, 4], {})) == {2: 1, 4: 2}

    def test_recorded_bars_keep_their_numbers_and_new_bar_follows_the_max(self) -> None:
        result = _emit([2, 4, 6], {"BACK": {2: 1, 4: 2}})
        assert _numbers(result) == {2: 1, 4: 2, 6: 3}
