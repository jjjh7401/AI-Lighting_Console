"""전환 entry 확장 필드 — 정규화·검증·저장 (카드 t574, SPEC-LDBEAT-001 0.5.0).

REQ-LDBEAT-006(i-4a)~(i-4f) · REQ-LDBEAT-020(e) · AC-LDBEAT-020(f)~(k).
음악 단위만 저장한다(초 저장 금지). 마디당 박 수는 곡 박자표에서 읽는다.
"""

from __future__ import annotations

import copy
import inspect

import pytest

from server.design import beat_grid_edit
from server.design.beat_grid import BeatGridEntry, normalize_beat_grid_cue
from server.design.beat_grid_edit import (
    BeatGridEditError,
    apply_beat_grid_edit,
    apply_beat_grid_edit_range,
    beats_per_bar_from_timeline,
)
from server.design.cue_sheet_edit import TRACKING_VALUES

NEW_KEYS = ("fade_beats", "trigger_beat", "delay_beats", "position_late_beats", "tracking")


def _grid() -> dict:
    cue = normalize_beat_grid_cue({"bar": 4, "label": "켜짐"})
    return {
        "song_title": "T",
        "bar_range": {"start": 0, "end": 8},
        "tracks": [
            {
                "group_no": 1,
                "group_no_confirmed": True,
                "group_name": "WASH",
                "layer_role": "wash",
                "cues": [normalize_beat_grid_cue({"bar": 0, "label": "켜짐"}), cue],
            }
        ],
        "scene_memos": [],
        "probe_results": {},
        "source": "custom",
        "note": None,
    }


def _entry(**fields) -> dict:
    base = {"fade_bars": None, "mib_mode": None, **{k: None for k in NEW_KEYS}}
    base.update(fields)
    return base


def _edit(entry: dict, beats_per_bar: int | None = 4) -> dict:
    grid, _ = apply_beat_grid_edit(
        _grid(), bar=4, target="WASH", changes={"entry": entry}, beats_per_bar=beats_per_bar
    )
    return grid["tracks"][0]["cues"][1]["entry"]


# -- 정규화 ---------------------------------------------------------------------


def test_entry_type_declares_the_five_new_fields() -> None:
    assert set(BeatGridEntry.__annotations__) == {"fade_bars", "mib_mode", *NEW_KEYS}


def test_missing_new_fields_normalize_to_none() -> None:
    cue = normalize_beat_grid_cue({"bar": 7, "label": "x", "entry": {"fade_bars": 2}})
    assert cue["entry"] == _entry(fade_bars=2)


def test_new_fields_survive_normalization() -> None:
    raw = {"bar": 7, "label": "x", "entry": _entry(fade_beats=1, trigger_beat=3, tracking="Block")}
    assert normalize_beat_grid_cue(raw)["entry"] == _entry(
        fade_beats=1, trigger_beat=3, tracking="Block"
    )


# -- AC-020(f) 페이드 배타 ------------------------------------------------------


def test_one_fade_unit_is_accepted() -> None:
    assert _edit(_entry(fade_bars=2))["fade_bars"] == 2
    assert _edit(_entry(fade_beats=2))["fade_beats"] == 2
    assert _edit(_entry())["fade_bars"] is None


def test_both_fade_units_are_rejected() -> None:
    with pytest.raises(BeatGridEditError, match="i-4a"):
        _edit(_entry(fade_bars=1, fade_beats=2))


# -- AC-020(j) 1박 페이드 저장 --------------------------------------------------


def test_one_beat_fade_is_storable() -> None:
    assert _edit(_entry(fade_beats=1)) == _entry(fade_beats=1)


# -- AC-020(h) 트래킹 닫힌 집합 -------------------------------------------------


def test_tracking_reuses_the_existing_closed_set() -> None:
    assert beat_grid_edit.TRACKING_VALUES is TRACKING_VALUES
    for value in TRACKING_VALUES:
        assert _edit(_entry(tracking=value))["tracking"] == value


def test_tracking_outside_the_set_is_rejected() -> None:
    with pytest.raises(BeatGridEditError, match="트래킹"):
        _edit(_entry(tracking="Tracking"))


# -- AC-020(i) 트리거 박 범위는 그 곡 박자표 ------------------------------------


@pytest.mark.parametrize(("beats_per_bar", "ok", "bad"), [(4, 4, 5), (3, 3, 4)])
def test_trigger_beat_range_follows_the_song_meter(beats_per_bar, ok, bad) -> None:
    assert _edit(_entry(trigger_beat=ok), beats_per_bar)["trigger_beat"] == ok
    with pytest.raises(BeatGridEditError, match="트리거"):
        _edit(_entry(trigger_beat=bad), beats_per_bar)


def test_trigger_beat_zero_is_rejected() -> None:
    with pytest.raises(BeatGridEditError, match="트리거"):
        _edit(_entry(trigger_beat=0))


def test_trigger_beat_without_known_meter_is_rejected_not_guessed() -> None:
    with pytest.raises(BeatGridEditError, match="박자표"):
        _edit(_entry(trigger_beat=2), beats_per_bar=None)
    # 트리거를 안 건드리면 박자표를 몰라도 저장된다.
    assert _edit(_entry(fade_beats=1), beats_per_bar=None)["fade_beats"] == 1


# -- 딜레이·위치만 따로 --------------------------------------------------------


@pytest.mark.parametrize("field", ["fade_beats", "delay_beats", "position_late_beats"])
@pytest.mark.parametrize("value", [-1, 1.5, True, "2"])
def test_beat_counts_must_be_non_negative_integers(field, value) -> None:
    with pytest.raises(BeatGridEditError):
        _edit(_entry(**{field: value}))


def test_delay_and_position_late_are_stored() -> None:
    assert _edit(_entry(delay_beats=2, position_late_beats=1)) == _entry(
        delay_beats=2, position_late_beats=1
    )


# -- AC-020(g) 초 단위 리터럴 0 -------------------------------------------------


def test_no_seconds_field_in_entry_storage() -> None:
    assert not any("second" in key for key in BeatGridEntry.__annotations__)
    assert "_seconds" not in inspect.getsource(beat_grid_edit._validate_entry)


# -- 범위 편집도 같은 검증 ------------------------------------------------------


def test_range_edit_carries_the_meter() -> None:
    with pytest.raises(BeatGridEditError, match="트리거"):
        apply_beat_grid_edit_range(
            _grid(),
            bar_start=0,
            bar_end=4,
            target="WASH",
            changes={"entry": _entry(trigger_beat=4)},
            beats_per_bar=3,
        )


def test_rejection_leaves_the_grid_untouched() -> None:
    grid = _grid()
    before = copy.deepcopy(grid)
    with pytest.raises(BeatGridEditError):
        apply_beat_grid_edit(
            grid, bar=4, target="WASH", changes={"entry": _entry(fade_bars=1, fade_beats=1)}
        )
    assert grid == before


# -- 곡 박자표 읽기 (i-4f) -------------------------------------------------------


@pytest.mark.parametrize(
    ("timeline", "expected"),
    [
        ({"time_signature": "4/4"}, 4),
        ({"time_signature": "3/4"}, 3),
        ({"bar_map": {"time_signature": [6, 8]}}, 6),
        ({"time_signature": "엉터리"}, None),
        ({"time_signature": "0/4"}, None),
        ({}, None),
        (None, None),
    ],
)
def test_beats_per_bar_from_timeline(timeline, expected) -> None:
    assert beats_per_bar_from_timeline(timeline) == expected


# -- 세션 경로: 곡 박자표가 검증까지 간다 ---------------------------------------


def test_session_edit_reads_the_song_meter(tmp_path) -> None:
    from server.safety.audit import AuditLog
    from server.safety.gate import SafetyGate
    from server.web.approval_bridge import ApprovalChannel
    from server.web.session import ChatSession, SongTimelineStore
    from server.web.timeline_library import SongTimelineLibrary

    from .test_safety_gate import FakeConsole

    class _NoModel:
        def complete(self, *args, **kwargs):  # pragma: no cover - must not be called
            raise AssertionError("이 경로는 모델을 부르지 않는다")

    store = SongTimelineStore()
    store.latest = {"song_title": "LOVE ATTACK", "sequence_number": 210, "time_signature": "3/4"}
    sent: list[dict] = []
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=1.0)
    console = FakeConsole()
    session = ChatSession(
        gate=SafetyGate(console=console, audit=audit, approval_port=channel),
        provider=_NoModel(),
        system_prefix="PREFIX",
        audit=audit,
        send_event=sent.append,
        approval_channel=channel,
        timeline_store=store,
        timeline_library=SongTimelineLibrary(tmp_path / "library.json"),
    )
    session.beat_grid_edit(7, "WASH-ALL", {"entry": _entry(fade_bars=2, trigger_beat=4)})
    assert any("트리거" in str(e.get("text", "")) for e in sent)
    sent.clear()
    session.beat_grid_edit(7, "WASH-ALL", {"entry": _entry(fade_bars=2, trigger_beat=3)})
    track = next(t for t in store.latest["beat_grid"]["tracks"] if t["group_name"] == "WASH-ALL")
    cue = next(c for c in track["cues"] if c["bar"] == 7)
    assert cue["entry"]["trigger_beat"] == 3
    assert console.executed == []
