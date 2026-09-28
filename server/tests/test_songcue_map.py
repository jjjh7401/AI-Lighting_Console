from __future__ import annotations

import ast
from pathlib import Path

import server.looks.songcue as songcue
from server.looks.schema import AttributeValue, Look, LookLibrary


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
