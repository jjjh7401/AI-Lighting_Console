"""자동 배치 초안 칸의 구조화 값과 송신되지 않는 칸 보고.

초안 칸의 라벨과 구조화 값은 같은 규칙 결정(``_cell_plan``)에서 나온다. 라벨에서 값을 역산하지
않는다. 값이 없는 칸은 송신되지 않으므로 그 수를 반영 결과에 보여 준다.
"""

from __future__ import annotations

import copy

from server.audio.bar_map_store import build_bar_map_payload
from server.design.arrange_apply import apply_arrangement_draft
from server.design.arrange_generator import generate_arrangement_draft
from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid, normalize_beat_grid_cue
from server.design.beat_grid_emit import SongTiming, emit_beat_grid_write_bundle

EVENTS = [
    {"kind": "kick_entry", "start_bar": 9, "end_bar": 9, "start_beat": 1, "grade": "measured"},
    {"kind": "drop", "start_bar": 17, "end_bar": 18, "start_beat": 1, "grade": "measured"},
]
REST = "—"
MOTION = "팬 웨이브 2마디"


def _draft(bars: int = 40) -> dict:
    beats = [index * 500 for index in range(bars * 4)]
    bar_map = build_bar_map_payload(beats, 0, bpm=120.0, events=EVENTS)
    layout = list(default_beat_grid(LOVE_ATTACK_TITLE)["tracks"])
    return generate_arrangement_draft(bar_map, layout)


def _cues(draft: dict) -> list[dict]:
    return [cue for track in draft["tracks"] for cue in track["cues"]]


def test_every_draft_cell_carries_a_brightness_value() -> None:
    cues = _cues(_draft())
    assert cues
    assert all(isinstance(cue["brightness"]["value_percent"], int) for cue in cues)


def test_rest_cells_are_dark_and_lit_cells_are_full() -> None:
    cues = _cues(_draft())
    rests = [cue for cue in cues if cue["label"] == REST]
    lit = [cue for cue in cues if cue["label"] != REST]
    assert rests and all(cue["brightness"]["value_percent"] == 0 for cue in rests)
    assert lit and all(cue["brightness"]["value_percent"] == 100 for cue in lit)


def test_motion_cells_carry_a_wave_movement_on_the_bar_period() -> None:
    moving = [cue for cue in _cues(_draft()) if cue["label"] == MOTION]
    assert moving
    assert all(cue["app_movement"]["shape"] == "wave" for cue in moving)
    assert all(cue["app_movement"]["period_unit"] == "bar" for cue in moving)
    assert all(cue["app_movement"]["period_value"] == 2 for cue in moving)


def test_every_draft_cell_names_the_rule_that_made_it() -> None:
    cues = _cues(_draft())
    assert all(str(cue["source_ref"]).startswith("arrangement_generator:") for cue in cues)


def test_applied_new_cells_take_the_draft_values() -> None:
    grid = copy.deepcopy(default_beat_grid(LOVE_ATTACK_TITLE))
    updated, _report = apply_arrangement_draft(grid, _draft())
    track = next(t for t in updated["tracks"] if t["group_name"] == "BACK")
    cell = next(c for c in track["cues"] if c["bar"] == 30)
    assert isinstance(cell["brightness"]["value_percent"], int)
    assert str(cell["source_ref"]).startswith("arrangement_generator:")


def test_cells_without_structured_values_are_reported_as_unsent() -> None:
    blank = normalize_beat_grid_cue({"bar": 1, "label": "빈 칸"})
    valued = normalize_beat_grid_cue(
        {"bar": 2, "label": "켬", "brightness": {"mode": "value", "value_percent": 100}}
    )
    tracks = [
        {
            "group_no": 4,
            "group_no_confirmed": True,
            "group_name": "BACK",
            "layer_role": "back",
            "cues": [blank, valued],
        }
    ]
    result = emit_beat_grid_write_bundle(
        tracks,
        timing=SongTiming(bpm=120.0, beats_per_bar=4, downbeat_bar1_seconds=0.0),
        sequence_numbers={"BACK": 300},
        timecode_numbers={"BACK": 30},
        dimmer_attributes={"BACK": ("Dimmer",)},
        probe_results={probe: "통과" for probe in range(1, 25)},
    )
    assert result.unsent_cells == (("BACK", 1),)
    assert len(result.unsent_notices) == 1
    assert "1개" in result.unsent_notices[0]
