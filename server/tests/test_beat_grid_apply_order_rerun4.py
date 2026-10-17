"""SPEC-LDRHYTHM-001 재실행 4 — 재반영이 「Delete Cue 2 Sequence 63」에서 멈추고
타임코드가 반쪽으로 남던 결함.

실콘솔은 ``Delete Cue <n> Sequence <s>`` 를 「Not allowed」로 거절했다(rerun4 감사 로그, t608 v4).
번들이 ``Delete Timecode 5`` 로 시작했으므로 거절 지점에서 Timecode 5 는 지워진 채 시퀀스 62 하나만
다시 붙어 있었다.

- 큐 하나 지우기는 실콘솔이 거절하므로(t618) 소유 시퀀스를 통째로 지우고(``Delete Sequence N
  /NoConfirm``, rerun2 실기 OK 8건) 같은 번호로 다시 만든다. 옛 큐가 남지 않는다.
- 시퀀스·큐를 모두 쓴 뒤에 타임코드를 지우고 다시 만든다 — 큐 쓰기에서 멈추면 옛 타임코드가
  그대로다.

콘솔 접촉 0건 — 순수 함수가 명령 문자열만 만든다.
"""

from __future__ import annotations

from server.design.beat_grid_emit import SongTiming, emit_beat_grid_write_bundle
from server.design.beat_grid_probes import DEFAULT_PROBE_IDS
from server.design.beat_grid_send import (
    apply_beat_grid_ownership_reuse,
    beat_grid_reapply_summary,
    clear_app_timecode_before_rebuild,
)

_ALL_PASS = {probe_id: "통과" for probe_id in DEFAULT_PROBE_IDS}
_APPROVED = {"approval": {"by": "supervisor", "date": "2026-10-17", "source": "rerun4"}}


def _track(name: str, group_no: int, bars: list[int]) -> dict:
    return {
        "group_name": name,
        "group_no": group_no,
        "group_no_confirmed": True,
        "cues": [
            {
                "bar": bar,
                "position_preset_no": "2.1",
                "evidence": _APPROVED,
                "entry": {"fade_bars": None, "mib_mode": None},
            }
            for bar in bars
        ],
    }


def _emit():
    return emit_beat_grid_write_bundle(
        [_track("FOH", 3, [1, 5]), _track("BACK", 7, [1, 2])],
        timing=SongTiming(bpm=120.0, beats_per_bar=4, downbeat_bar1_seconds=1.0),
        sequence_numbers={"FOH": 62, "BACK": 63},
        timecode_numbers={"FOH": 5, "BACK": 5},
        dimmer_attributes={},
        probe_results=_ALL_PASS,
        recorded_cue_numbers=None,
    )


# BACK 의 3마디(큐 2)는 이번 격자에서 빠졌다.
_RECORDED = {"FOH": {1: 1, 5: 2}, "BACK": {1: 1, 3: 2}}


def _reapply():
    reused = apply_beat_grid_ownership_reuse(
        _emit(),
        owned_sequences={"FOH": 62, "BACK": 63},
        owned_timecode=None,
        recorded_cue_numbers=_RECORDED,
    )
    return clear_app_timecode_before_rebuild(reused, 5)


def test_reapply_deletes_each_owned_sequence_once_before_its_first_cue() -> None:
    commands = list(_reapply().commands)
    assert not any(line.startswith("Delete Cue") for line in commands)
    assert not any("/Overwrite" in line for line in commands)
    for seq in (62, 63):
        delete_at = commands.index(f"Delete Sequence {seq} /NoConfirm")
        first_store = min(
            i for i, line in enumerate(commands) if line.startswith(f"Store Sequence {seq} Cue")
        )
        assert delete_at < first_store
    assert _reapply().rebuilt_sequences == (62, 63)


def test_next_record_has_only_the_new_cues() -> None:
    result = _reapply()
    next_record, _preserved, out_of_order = beat_grid_reapply_summary(
        result, recorded_cue_numbers={}
    )
    assert next_record["BACK"] == {1: 1, 2: 2}
    assert next_record["FOH"] == {1: 1, 5: 2}
    assert out_of_order == 0


def test_timecode_is_deleted_and_rebuilt_only_after_every_cue_is_written() -> None:
    commands = list(_reapply().commands)
    last_cue = max(i for i, line in enumerate(commands) if line.startswith("Store Sequence "))
    last_seq_delete = max(
        i for i, line in enumerate(commands) if line.startswith("Delete Sequence ")
    )
    assert last_seq_delete < last_cue
    delete_tc = commands.index("Delete Timecode 5 /NoConfirm")
    store_tc = commands.index("Store Timecode 5")
    first_assign = min(i for i, line in enumerate(commands) if line.startswith("Assign Sequence "))
    first_event = min(i for i, line in enumerate(commands) if "CmdSubTrack" in line)
    assert last_cue < delete_tc < store_tc < first_assign < first_event


def test_first_apply_also_writes_cues_before_the_timecode() -> None:
    commands = list(_emit().commands)
    last_cue = max(i for i, line in enumerate(commands) if line.startswith("Store Sequence "))
    assert last_cue < commands.index("Store Timecode 5")
    assigns = [line for line in commands if line.startswith("Assign Sequence ")]
    assert assigns == [
        "Assign Sequence 62 At Timecode 5.1.1",
        "Assign Sequence 63 At Timecode 5.1.2",
    ]
