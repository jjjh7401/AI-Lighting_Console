from __future__ import annotations

import dataclasses
import re
from pathlib import Path

import pytest
import yaml

from server.fx.loader import load_library_from_dir as load_fx_library_from_dir
from server.looks.loader import load_library_from_dir as load_look_library_from_dir
from server.scene.loader import DEFAULT_LIBRARY_DIR, load_library_from_dir
from server.scene.schema import Scene

HANGUL = re.compile(r"[가-힣]")
AT_STEP_PATTERN = re.compile(r"Attribute\s+'[^']+'\s+At\s+Step\s+\d+", re.IGNORECASE)
PER_SHOW_PATTERN = re.compile(
    r"(?:group|fixture|fid|executor|exec|page|sequence|cue|그룹|픽스처|익스큐터)"
    r"\s*[.#]?\s*\d",
    re.IGNORECASE,
)
PER_SHOW_FIELDS = {
    "group",
    "group_number",
    "group_name",
    "fid",
    "fixture",
    "fixture_id",
    "executor",
    "executor_number",
    "page",
    "sequence",
    "sequence_number",
    "cue",
    "cue_number",
}
COLLISION_ATTRIBUTES = frozenset({"Dimmer", "ColorRGB_R", "ColorRGB_G", "ColorRGB_B"})
MOVEMENT_ATTRIBUTES = frozenset({"Pan", "Tilt"})


@pytest.fixture(scope="module")
def library():
    return load_library_from_dir()


@pytest.fixture(scope="module")
def looks_by_id():
    library = load_look_library_from_dir()
    return {look.look_id: look for look in library.looks}


@pytest.fixture(scope="module")
def fx_by_id():
    library = load_fx_library_from_dir()
    return {entry.fx_id: entry for entry in library.fx}


@pytest.fixture(scope="module")
def asset_paths() -> tuple[Path, ...]:
    return tuple(sorted(DEFAULT_LIBRARY_DIR.glob("*.yaml")))


@pytest.fixture(scope="module")
def asset_payloads(asset_paths) -> tuple[tuple[Path, dict], ...]:
    return tuple((path, yaml.safe_load(path.read_text(encoding="utf-8"))) for path in asset_paths)


def _look_attribute_names(look) -> frozenset[str]:
    return frozenset(attribute.name for attribute in look.attributes)


class TestNoPerShowValues:
    def test_scene_schema_has_no_static_per_show_field(self):
        fields = {field.name for field in dataclasses.fields(Scene)}
        assert fields.isdisjoint(PER_SHOW_FIELDS), (
            f"Scene exposes static per-show field(s): {sorted(fields & PER_SHOW_FIELDS)}"
        )

    def test_no_scene_asset_declares_a_per_show_field(self, asset_payloads):
        for path, payload in asset_payloads:
            for index, scene in enumerate(payload["scenes"], start=1):
                forbidden = set(scene) & PER_SHOW_FIELDS
                assert not forbidden, (
                    f"{path.name}: scene #{index} declares per-show field(s): {sorted(forbidden)}"
                )

    def test_no_asset_file_mentions_a_per_show_binding(self, asset_paths):
        for path in asset_paths:
            for line_number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                match = PER_SHOW_PATTERN.search(line)
                assert match is None, (
                    f"{path.name}:{line_number} contains a per-show binding: {match.group(0)!r}"
                )


class TestAssetShape:
    def test_library_loads_the_default_asset_directory(self, library):
        assert library.scenes

    def test_census_sees_every_scene_in_every_asset_file(self, library, asset_payloads):
        scene_count = sum(len(payload["scenes"]) for _, payload in asset_payloads)
        assert len(library.scenes) == scene_count

    def test_every_scene_has_a_korean_mood_keyword(self, library):
        for scene in library.scenes:
            assert any(HANGUL.search(keyword) for keyword in scene.mood_keywords), (
                f"{scene.scene_id} has no Korean mood keyword"
            )

    def test_no_asset_file_uses_attribute_at_step_form(self, asset_paths):
        for path in asset_paths:
            for line_number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                assert AT_STEP_PATTERN.search(line) is None, (
                    f"{path.name}:{line_number} uses forbidden Attribute ... At Step form"
                )


class TestReferenceCoverage:
    def test_every_look_reference_resolves_in_the_upstream_look_library(self, library, looks_by_id):
        missing = [
            (scene.scene_id, scene.look_id)
            for scene in library.scenes
            if scene.look_id is not None and scene.look_id not in looks_by_id
        ]
        assert missing == []

    def test_every_fx_reference_resolves_in_the_upstream_fx_library(self, library, fx_by_id):
        missing = [
            (scene.scene_id, scene.fx_id)
            for scene in library.scenes
            if scene.fx_id is not None and scene.fx_id not in fx_by_id
        ]
        assert missing == []

    def test_required_scene_kinds_are_present(self, library):
        combined = [scene for scene in library.scenes if scene.look_id and scene.fx_id]
        look_only = [scene for scene in library.scenes if scene.look_id and not scene.fx_id]
        fx_only = [scene for scene in library.scenes if scene.fx_id and not scene.look_id]

        assert len(combined) >= 3
        assert len(look_only) >= 1
        assert len(fx_only) >= 1

    def test_library_contains_a_movement_scene(self, library, fx_by_id):
        movement_scenes = [
            scene.scene_id
            for scene in library.scenes
            if scene.fx_id and set(fx_by_id[scene.fx_id].attributes) & MOVEMENT_ATTRIBUTES
        ]
        assert movement_scenes

    def test_library_contains_a_dimmer_or_color_collision_scene(
        self, library, looks_by_id, fx_by_id
    ):
        witnesses = []
        for scene in library.scenes:
            if not scene.look_id or not scene.fx_id:
                continue
            look_attributes = _look_attribute_names(looks_by_id[scene.look_id])
            fx_attributes = frozenset(fx_by_id[scene.fx_id].attributes)
            overlap = tuple(sorted(look_attributes & fx_attributes & COLLISION_ATTRIBUTES))
            if overlap:
                witnesses.append((scene.scene_id, overlap))

        assert witnesses
