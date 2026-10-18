"""SPEC-LDRHYTHM-001 재실행 3 B1 — 콘솔이 붙인 「#숫자」 접미사 때문에 재반영이 거절되던 결함.

같은 이름의 시퀀스가 콘솔에 이미 있으면(다른 타임코드가 쓰는 'LDBEAT FOH') 콘솔은 이름 끝에
「#6」 같은 접미사를 붙인다. 소유 기록은 'LDBEAT FOH' 를 기억하므로 이름이 달라 「⇪ 콘솔에
반영」이 통째로 거절됐다(실서버 rerun3 응답 원문). 접미사만 다른 이름은 같은 시퀀스로 인정하고,
재반영은 시퀀스를 다시 만들며 이름을 다시 붙인다(재실행 4).

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
def test_other_names_are_not_overwritten_but_recreated(console_name: str) -> None:
    # WT-play-stale-owner(리드 지시) — 같은 번호를 다른 이름이 쓰면 거절하지 않는다. 소유 목록에서
    # 빼고 빈 번호에 새로 만든다. 덮어쓰기는 이름이 같을 때(위 시험)만.
    owned, reason = verify_owned_sequences(_section(console_name), _OWNED)
    assert owned == {}
    assert reason is None


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


def test_reapply_rebuilds_the_owned_sequence_and_names_it_again() -> None:
    # 재실행 4 — 소유 시퀀스는 통째로 지우고 다시 만들므로 이름도 다시 붙인다. 콘솔이 다시
    # 「#숫자」를 붙여도 소유 확인이 같은 시퀀스로 인정한다(위 시험).
    reused = apply_beat_grid_ownership_reuse(
        _emit(None),
        owned_sequences={"FOH": 62},
        owned_timecode=5,
        recorded_cue_numbers={"FOH": {1: 1}},
    )
    assert reused.commands[0] == "Delete Sequence 62 /NoConfirm"
    assert _name_lines(reused.commands) == ["Set Sequence 62 Property 'Name' 'LDBEAT FOH'"]
    assert "Store Sequence 62 Cue 1" in reused.commands
    assert "Store Sequence 62 Cue 2" in reused.commands


_WRAP_OFF = "Set Sequence 62 Property 'WrapAround' 0"


def test_the_sequence_does_not_wrap_back_to_cue_1_after_the_last_cue() -> None:
    # WT-end-wrap — 앱이 만든 시퀀스는 WRAPAROUND 가 기본 켜짐이다(t538 r5_seq_props).
    # 큐마다 TrigType Time 이라, 마지막 큐 뒤 큐1(TrigTime ≈ 3.96초)로 감겨 다시 켜졌다
    # (barcheck: g178.2 꺼짐 → g182.4 큐1 값). 시퀀스를 만들 때마다 감김을 끈다.
    first = _emit(None).commands
    assert first.count(_WRAP_OFF) == 1
    assert first.index(_WRAP_OFF) > first.index("Store Sequence 62 Cue 1")
    assert first.index(_WRAP_OFF) < first.index("Store Sequence 62 Cue 2")
    reused = apply_beat_grid_ownership_reuse(
        _emit(None),
        owned_sequences={"FOH": 62},
        owned_timecode=5,
        recorded_cue_numbers={"FOH": {1: 1}},
    )
    assert reused.commands.count(_WRAP_OFF) == 1
