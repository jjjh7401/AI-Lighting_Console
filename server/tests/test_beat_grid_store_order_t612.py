"""카드 t612 — 박자 격자 에미터: 첫 큐 저장이 시퀀스를 만들고 Name 은 그 뒤로.

실기 근거(t608 실행 ``.moai/reports/t608/run-1012.jsonl``, index 30~33): 맨
``Store Sequence 700`` 은 ``OK`` 였고, 그 다음 큐 저장 ``Store Cue 1 Sequence 700``
은 ``User Canceled Command`` 로 멈췄다. 실기 선례(t531 ``approval-v3-package.md:32``,
cue_sheet_apply)는 큐 저장 한 줄 ``Store Sequence <N> Cue <M> ...`` 이 시퀀스를 만들고,
``Set Sequence <N> Property 'Name'`` 은 그 뒤에 온다.

콘솔 접촉 0건 — 순수 함수가 명령 문자열만 만든다.
"""

from __future__ import annotations

from server.design.beat_grid_emit import SongTiming, emit_beat_grid_write_bundle
from server.design.beat_grid_probes import DEFAULT_PROBE_IDS

_ALL_PASS = {probe_id: "통과" for probe_id in DEFAULT_PROBE_IDS}
_APPROVED = {"approval": {"by": "supervisor", "date": "2026-10-12", "source": "t612"}}
#: 120 BPM · 4/4 — 1마디 다운비트 = 1.0초 (t576 과 같은 시간 기준).
_TIMING = SongTiming(bpm=120.0, beats_per_bar=4, downbeat_bar1_seconds=1.0)
_SEQ = 700
_TC = 70
_NAME_PREFIX = f"Set Sequence {_SEQ} Property 'Name' "


def _cue(bar: int) -> dict:
    return {
        "bar": bar,
        "position_preset_no": "2.1",
        "evidence": _APPROVED,
        "entry": {"fade_bars": None, "mib_mode": None},
    }


def _track(cues: list[dict]):
    result = emit_beat_grid_write_bundle(
        [{"group_name": "FOH", "group_no": 3, "group_no_confirmed": True, "cues": cues}],
        timing=_TIMING,
        sequence_numbers={"FOH": _SEQ},
        timecode_numbers={"FOH": _TC},
        dimmer_attributes={},
        probe_results=_ALL_PASS,
    )
    (track,) = result.tracks
    return track


class TestFirstStoredCueCreatesTheSequence:
    def test_the_refused_cue_first_line_is_not_emitted(self) -> None:
        # run-1012 index 33 — 콘솔이 "User Canceled Command" 로 거절한 줄 그대로.
        track = _track([_cue(3)])
        assert f"Store Cue 1 Sequence {_SEQ}" not in track.commands

    def test_no_separate_bare_store_sequence_line_when_a_cue_stores(self) -> None:
        track = _track([_cue(3)])
        assert f"Store Sequence {_SEQ}" not in track.commands

    def test_first_store_is_sequence_first_and_name_follows_it(self) -> None:
        track = _track([_cue(3)])
        store = f"Store Sequence {_SEQ} Cue 1"
        assert store in track.commands
        index = track.commands.index(store)
        assert track.commands[index + 1].startswith(_NAME_PREFIX)

    def test_a_later_cue_stores_in_the_sequence_first_form_too(self) -> None:
        track = _track([_cue(3), _cue(5)])
        assert f"Store Sequence {_SEQ} Cue 2" in track.commands
        assert not any(line.startswith("Store Cue ") for line in track.commands)


class TestTrackWithoutAStoredCueEmitsNothing:
    def test_the_bare_store_line_is_not_emitted(self) -> None:
        # 카드 t615 — 맨 Store Sequence 는 빈 Cue 1 을 만든다(실기 판별: .moai/reports/t615/live/).
        # 저장되는 큐가 하나도 없으면 시퀀스·이름·배정 줄을 아무것도 내지 않는다.
        # 상세 시험은 test_beat_grid_empty_track_t615.py.
        track = _track([])
        assert f"Store Sequence {_SEQ}" not in track.commands
        assert track.commands == ()
