"""카드 t553 — 타임코드 한 개에 붙일 수 있는 트랙 수 상한은 실기 측정 기록에서 온다.

2026-10-11 실기(.moai/reports/t553/live/p1b, 되읽기 live/p1b_readback.txt):
타임코드 32 에 시퀀스 트랙 8개를 붙이고 되읽어 childCount 9(Marker 1 + Track 8),
TARGET 226..233 순서 일치 — 리드 판정 PASS. 상한 값은 코드 상수가 아니라
``beat_grid_data/measured_console.yaml`` 에 근거와 함께 산다.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from server.design import beat_grid_emit
from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid
from server.design.beat_grid_emit import MEASURED_MAX_TIMECODE_TRACKS, emit_beat_grid_write_bundle
from server.design.beat_grid_probes import read_m1_probe_results_from_path

_DATA = Path(beat_grid_emit.__file__).resolve().parent / "beat_grid_data" / "measured_console.yaml"


def test_cap_comes_from_the_measured_console_data_file() -> None:
    document = yaml.safe_load(_DATA.read_text("utf-8"))
    assert document["max_timecode_tracks"] == MEASURED_MAX_TIMECODE_TRACKS
    assert document["source"]


def test_cap_reflects_the_eight_track_measurement() -> None:
    assert MEASURED_MAX_TIMECODE_TRACKS == 8


def test_all_eight_love_attack_tracks_fit_on_one_timecode() -> None:
    from server.tests.test_beat_grid_emit_t549 import _TIMING, default_progress_md_path

    tracks = default_beat_grid(LOVE_ATTACK_TITLE)["tracks"]
    assert len(tracks) == 8
    result = emit_beat_grid_write_bundle(
        tracks,
        timing=_TIMING,
        sequence_numbers={t["group_name"]: 300 + i for i, t in enumerate(tracks)},
        timecode_numbers={t["group_name"]: 30 for t in tracks},
        dimmer_attributes={t["group_name"]: ("Dimmer",) for t in tracks},
        probe_results=read_m1_probe_results_from_path(default_progress_md_path()),
    )
    timecode_refusals = [
        track.blocked_reason
        for track in result.tracks
        if track.blocked_reason and "타임코드" in track.blocked_reason
    ]
    assert timecode_refusals == []
