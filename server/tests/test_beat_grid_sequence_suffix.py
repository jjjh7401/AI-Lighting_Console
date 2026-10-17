"""SPEC-LDRHYTHM-001 재실행 3 B1 — 콘솔이 붙인 「#숫자」 접미사 때문에 재반영이 거절되던 결함.

같은 이름의 시퀀스가 콘솔에 이미 있으면(다른 타임코드가 쓰는 'LDBEAT FOH') 콘솔은 이름 끝에
「#6」 같은 접미사를 붙인다. 소유 기록은 'LDBEAT FOH' 를 기억하므로 이름이 달라 「⇪ 콘솔에
반영」이 통째로 거절됐다(실서버 rerun3 응답 원문). 접미사만 다른 이름은 같은 시퀀스로 인정하고,
재반영 때 이름 줄을 다시 보내지 않아 접미사가 바뀌거나 늘지 않게 한다.

콘솔 접촉 0건 — 순수 함수가 명령 문자열만 만든다.
"""

from __future__ import annotations

import pytest

from server.design.beat_grid_emit import SongTiming, emit_beat_grid_write_bundle
from server.design.beat_grid_probes import DEFAULT_PROBE_IDS
from server.design.beat_grid_send import (
    apply_beat_grid_ownership_reuse,
    verify_owned_sequences,
)

_OWNED = {"FOH": {"sequence_number": 62, "sequence_name": "LDBEAT FOH"}}


def _section(name: str) -> dict:
    return {"objects": [{"no": 62, "name": name}]}


@pytest.mark.parametrize("console_name", ["LDBEAT FOH", "LDBEAT FOH#6", "LDBEAT FOH#12"])
def test_console_hash_suffix_is_the_same_owned_sequence(console_name: str) -> None:
    assert verify_owned_sequences(_section(console_name), _OWNED) == ({"FOH": 62}, None)


@pytest.mark.parametrize(
    "console_name", ["LDBEAT FOHX", "LDBEAT FOH#", "LDBEAT FOH#6a", "LDBEAT FOH 6", "Other"]
)
def test_other_names_are_still_refused(console_name: str) -> None:
    owned, reason = verify_owned_sequences(_section(console_name), _OWNED)
    assert owned == {}
    assert reason is not None and "재적용을 거절" in reason


_ALL_PASS = {probe_id: "통과" for probe_id in DEFAULT_PROBE_IDS}
_APPROVED = {"approval": {"by": "supervisor", "date": "2026-10-17", "source": "rerun3"}}


def _emit(recorded: dict | None):
    return emit_beat_grid_write_bundle(
        [
            {
                "group_name": "FOH",
                "group_no": 3,
                "group_no_confirmed": True,
                "cues": [
                    {
                        "bar": bar,
                        "position_preset_no": "2.1",
                        "evidence": _APPROVED,
                        "entry": {"fade_bars": None, "mib_mode": None},
                    }
                    for bar in (1, 3)
                ],
            }
        ],
        timing=SongTiming(bpm=120.0, beats_per_bar=4, downbeat_bar1_seconds=1.0),
        sequence_numbers={"FOH": 62},
        timecode_numbers={"FOH": 5},
        dimmer_attributes={},
        probe_results=_ALL_PASS,
        recorded_cue_numbers=recorded,
    )


def _name_lines(commands) -> list[str]:
    return [line for line in commands if line.startswith("Set Sequence 62 Property 'Name'")]


def test_first_apply_still_names_the_sequence() -> None:
    assert _name_lines(_emit(None).commands) == ["Set Sequence 62 Property 'Name' 'LDBEAT FOH'"]


def test_reapply_of_owned_track_does_not_rename_the_sequence() -> None:
    recorded = {"FOH": {1: 1}}
    reused = apply_beat_grid_ownership_reuse(
        _emit(recorded),
        owned_sequences={"FOH": 62},
        owned_timecode=5,
        recorded_cue_numbers=recorded,
    )
    assert _name_lines(reused.commands) == []
    # 큐 저장 줄은 그대로 나간다 — 이름 줄만 빠진다.
    assert "Store Sequence 62 Cue 1 /Overwrite" in reused.commands
    assert "Store Sequence 62 Cue 2" in reused.commands
