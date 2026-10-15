"""칸의 구조화 효과 모양 ``effect_shape`` — 라벨이 아니라 app_movement·효과 레시피에서만 파생."""

from __future__ import annotations

from pathlib import Path

import pytest

from server.design.beat_grid import attach_beat_grid_runtime_extras
from server.design.beat_grid_effect_presets import EFFECT_SHAPES, effect_shape_of_cue


def _grid(recipes: dict | None = None) -> dict:
    return {"preset_fx_recipes": recipes or {}}


def _recipe(fx_id: str) -> dict:
    return {"fx_id": fx_id, "period_unit": "beat", "period_value": 2}


@pytest.mark.parametrize(
    ("fx_id", "expected"),
    [
        ("pulse-beat", "pulse"),
        ("chase-warm-cool", "chase"),
        ("wave-soft-rise", "wave"),
        ("sweep-soft-wide", "sweep"),
        ("circle-soft-ballyhoo", None),
        ("diagonal-soft-inphase", None),
    ],
)
def test_recipe_pattern_maps_to_shape(fx_id: str, expected: str | None) -> None:
    cue = {"bar": 1, "effect_preset_no": "22.1"}
    assert effect_shape_of_cue(cue, _grid({"22.1": _recipe(fx_id)})) == expected


def test_app_movement_wave_sweep_wins_others_omitted() -> None:
    cases = (("wave", "wave"), ("sweep", "sweep"), ("circle", None), ("flyout", None))
    for shape, expected in cases:
        cue = {"bar": 1, "app_movement": {"shape": shape}}
        assert effect_shape_of_cue(cue, _grid()) == expected


def test_unknown_inputs_omit() -> None:
    assert effect_shape_of_cue({"bar": 1, "label": "펄스 1·2·4박"}, _grid()) is None
    assert effect_shape_of_cue({"bar": 1, "effect_preset_no": "22.9"}, _grid()) is None
    unknown = _grid({"22.1": _recipe("nope")})
    assert effect_shape_of_cue({"bar": 1, "effect_preset_no": "22.1"}, unknown) is None


def test_vocabulary_is_closed() -> None:
    assert EFFECT_SHAPES == ("pulse", "chase", "wave", "sweep")


def test_runtime_extras_attaches_field_only_when_derivable(tmp_path: Path) -> None:
    grid = {
        "preset_fx_recipes": {"22.1": _recipe("pulse-beat")},
        "tracks": [
            {
                "group_name": "BACK",
                "cues": [
                    {"bar": 1, "label": "x", "effect_preset_no": "22.1"},
                    {"bar": 2, "label": "펄스", "app_movement": {"shape": "sweep"}},
                    {"bar": 3, "label": "펄스 1·2·4박"},
                ],
            }
        ],
    }
    out = attach_beat_grid_runtime_extras(
        {"beat_grid": grid}, progress_md_path=tmp_path / "absent.md"
    )
    cues = out["beat_grid"]["tracks"][0]["cues"]
    assert cues[0]["effect_shape"] == "pulse"
    assert cues[1]["effect_shape"] == "sweep"
    assert "effect_shape" not in cues[2]
