"""카드 t615 — 저장되는 큐가 하나도 없는 트랙은 시퀀스·이름·배정·타임코드를 내지 않는다.

실기 판별(.moai/reports/t615/live/): 맨 ``Store Sequence 790`` 단독이 ``OK`` 였고, 되읽기에
``Cue 1`` 이 생겼다(Name·Assign 줄 없이). 저장 큐가 없는 트랙이 맨 Store 줄을 내면 빈 Cue 1 이
콘솔에 남고, 나중에 그 번호에 큐를 저장하면 ``User Canceled Command`` 로 멈춘다.

콘솔 접촉 0건 — 순수 함수가 명령 문자열만 만든다.
"""

from __future__ import annotations

from server.design.beat_grid_emit import SongTiming, emit_beat_grid_write_bundle
from server.design.beat_grid_probes import DEFAULT_PROBE_IDS

_ALL_PASS = {probe_id: "통과" for probe_id in DEFAULT_PROBE_IDS}
_APPROVED = {"approval": {"by": "supervisor", "date": "2026-10-12", "source": "t615"}}
#: 120 BPM · 4/4 — 1마디 다운비트 = 1.0초 (t612 와 같은 시간 기준).
_TIMING = SongTiming(bpm=120.0, beats_per_bar=4, downbeat_bar1_seconds=1.0)
_TC = 70
_FOH_SEQ = 700
_WASH_SEQ = 703


def _cue(bar: int) -> dict:
    return {
        "bar": bar,
        "position_preset_no": "2.1",
        "evidence": _APPROVED,
        "entry": {"fade_bars": None, "mib_mode": None},
    }


def _foh(cues: list[dict]) -> dict:
    return {"group_name": "FOH", "group_no": 3, "group_no_confirmed": True, "cues": cues}


def _wash(cues: list[dict]) -> dict:
    return {"group_name": "WASH", "group_no": 4, "group_no_confirmed": True, "cues": cues}


def _bundle(tracks: list[dict], *, held_cells: dict | None = None):
    # 두 트랙이 같은 타임코드를 쓴다 — 배정 순번 k 가 트랙 사이에서 어떻게 세지는지 본다.
    return emit_beat_grid_write_bundle(
        tracks,
        timing=_TIMING,
        sequence_numbers={"FOH": _FOH_SEQ, "WASH": _WASH_SEQ},
        timecode_numbers={"FOH": _TC, "WASH": _TC},
        dimmer_attributes={},
        probe_results=_ALL_PASS,
        held_cells=held_cells,
    )


class TestATrackWithoutAStoredCueEmitsNothing:
    def test_no_command_at_all(self) -> None:
        (track,) = _bundle([_foh([])]).tracks
        assert track.commands == ()

    def test_the_bare_store_sequence_line_is_not_emitted(self) -> None:
        # 카드 t615 — 맨 Store Sequence 는 빈 Cue 1 을 만든다. 시퀀스 줄도 이름 줄도 없어야 한다.
        # 카드 t617 — 항상 비던 store_sequence_commands 필드는 없앴다. 맨 줄이 없다는 것은
        # 트랙 줄 전체가 비어 있다는 것으로 확인한다.
        (track,) = _bundle([_foh([])]).tracks
        assert not hasattr(track, "store_sequence_commands")
        assert not any(line.startswith("Store Sequence") for line in track.commands)

    def test_a_cue_held_by_the_pool_check_leaves_the_track_empty(self) -> None:
        # 저장되는 큐가 보류로 전부 막히면 저장 큐 0개와 같다. 칸별 사유는 그대로 남는다.
        bundle = _bundle([_foh([_cue(3)])], held_cells={("FOH", 3): "빈 프리셋"})
        (track,) = bundle.tracks
        assert track.commands == ()
        assert track.cues[0].blocked_reason == "빈 프리셋"


class TestAnEmptyTrackTakesNoTrackAddress:
    def test_the_next_track_in_the_timecode_takes_address_one(self) -> None:
        empty, wash = _bundle([_foh([]), _wash([_cue(3)])]).tracks
        assert empty.assign_timecode_commands == ()
        assert wash.assign_timecode_commands == (
            f"Assign Sequence {_WASH_SEQ} At Timecode {_TC}.1.1",
        )


class TestAnEmptyTrackCreatesNoTimecode:
    def test_a_timecode_used_only_by_empty_tracks_is_not_set_up(self) -> None:
        assert _bundle([_foh([])]).timecode_setup_commands == ()
