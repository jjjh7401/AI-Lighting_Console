from __future__ import annotations

import ast
from pathlib import Path

import pytest

import server.looks.songcue as songcue
from server.looks.schema import DYNAMICS_MAX, DYNAMICS_MIN, AttributeValue, Look, LookLibrary
from server.looks.songcue import (
    EXPLICIT_DYNAMICS_REQUIRED,
    UNMAPPED_LOOK,
    map_sections_to_looks,
    parse_sections,
)


def test_explicit_dynamics_selects_each_requested_point():
    library = _library(
        _look("rock-5-a", "rock", 5),
        _look("rock-3-a", "rock", 3),
        _look("rock-1-a", "rock", 1),
        _look("rock-4-a", "rock", 4),
        _look("rock-2-a", "rock", 2),
    )
    sections = parse_sections(
        (
            ("Custom 1", "0:01"),
            ("Custom 2", "0:02"),
            ("Custom 3", "0:03"),
            ("Custom 4", "0:04"),
            ("Custom 5", "0:05"),
        )
    )
    requested = tuple(range(DYNAMICS_MIN, DYNAMICS_MAX + 1))

    selections = map_sections_to_looks(
        sections,
        library,
        "rock",
        explicit_dynamics={
            section.index: dynamics for section, dynamics in zip(sections, requested, strict=True)
        },
    )

    assert [
        selection.look.dynamics if selection.look else None for selection in selections
    ] == list(requested)
    assert [selection.requested_dynamics for selection in selections] == [
        (value,) for value in requested
    ]
    assert [selection.reason for selection in selections] == [None, None, None, None, None]


def test_band_selects_first_matching_look_from_busking_order():
    library = _library(
        _look("edm-drop-z", "edm", 5),
        _look("edm-drop-acid", "edm", 4),
        _look("edm-drop-peak", "edm", 5),
    )
    section = parse_sections((("Drop", "0:00"),))[0]

    selection = map_sections_to_looks((section,), library, "edm")[0]

    assert selection.requested_dynamics == (4, 5)
    assert selection.look is not None
    assert selection.look.look_id == "edm-drop-acid"
    assert selection.look.dynamics == 4
    assert selection.reason is None


def test_explicit_dynamics_overrides_section_band():
    library = _library(_look("rock-chorus-lift", "rock", 4), _look("rock-chorus-peak", "rock", 5))
    section = parse_sections((("Chorus", "0:00"),))[0]

    selection = map_sections_to_looks(
        (section,), library, "rock", explicit_dynamics={section.index: 5}
    )[0]

    assert selection.requested_dynamics == (5,)
    assert selection.look is not None
    assert selection.look.look_id == "rock-chorus-peak"


def test_missing_requested_dynamics_is_unmapped_without_nearest_promotion():
    library = _library(_look("ballad-low", "ballad", 1), _look("ballad-high", "ballad", 5))
    section = parse_sections((("Custom", "0:00"),))[0]

    selection = map_sections_to_looks(
        (section,), library, "ballad", explicit_dynamics={section.index: 3}
    )[0]

    assert selection.requested_dynamics == (3,)
    assert selection.look is None
    assert selection.reason == UNMAPPED_LOOK


def test_unknown_section_without_explicit_dynamics_requires_specification():
    library = _library(_look("rock-low", "rock", 1))
    section = parse_sections((("Breakdown", "0:00"),))[0]

    selection = map_sections_to_looks((section,), library, "rock")[0]

    assert selection.requested_dynamics == ()
    assert selection.look is None
    assert selection.reason == EXPLICIT_DYNAMICS_REQUIRED


def test_invalid_explicit_dynamics_uses_schema_bounds():
    library = _library(_look("rock-low", "rock", 1))
    section = parse_sections((("Custom", "0:00"),))[0]

    with pytest.raises(ValueError) as raised:
        map_sections_to_looks(
            (section,), library, "rock", explicit_dynamics={section.index: DYNAMICS_MAX + 1}
        )

    assert str(DYNAMICS_MIN) in str(raised.value)
    assert str(DYNAMICS_MAX) in str(raised.value)


def test_mapping_reuses_busking_order_and_schema_bounds_by_ast():
    tree = ast.parse(Path(songcue.__file__).read_text(encoding="utf-8"))
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    calls = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    schema_imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "server.looks.schema"
        for alias in node.names
    }

    assert names
    assert "looks_for_genre" in calls
    assert {"DYNAMICS_MIN", "DYNAMICS_MAX"} <= schema_imports


def _look(look_id: str, genre: str, dynamics: int) -> Look:
    return Look(
        look_id=look_id,
        display_name=look_id,
        genre=genre,
        dynamics=dynamics,
        roles=("front",),
        attributes=(AttributeValue("Dimmer", 50),),
    )


def _library(*looks: Look) -> LookLibrary:
    return LookLibrary(schema_version=1, looks=looks)
