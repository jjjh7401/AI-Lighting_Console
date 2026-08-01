"""Scene schema + loader tests (M1 — AC-SCENE-001, AC-SCENE-002).

Covers REQ-SCENE-001 (the scene axes — identity, references, timing, label,
schema_version), REQ-SCENE-003 (a scene with neither reference is not a scene),
REQ-SCENE-004 (no per-show binding field exists) and REQ-SCENE-006 (the loader
reports every violation explicitly instead of serving a partly broken library).

Every failure mode is a SEPARATE test on purpose (design.md §8 — merging them
hides which rejection actually fired).

Two of the checks carry extra weight because the runtime gives no signal:

* The closed field set is the only thing keeping a per-show value (a group
  number, an executor, a cue number) out of a static asset. Nothing downstream
  would reject it — it would simply be honoured.
* The trigger vocabulary is Capitalized (31_choreography_patterns.md:115). A
  lowercase token is not rejected by the console in any way this repository can
  observe, so this loader check is the only net under it.

Nothing here touches a console: pure functions over in-memory data, plus the one
tmp_path group that exercises the YAML directory wrapper.
"""

from __future__ import annotations

from dataclasses import fields

import pytest
import yaml

from server.scene.loader import (
    SceneSchemaError,
    load_library,
    load_library_from_dir,
    parse_timing,
)
from server.scene.schema import (
    SCENE_SCHEMA_VERSION,
    TRIGGER_TOKENS,
    Scene,
    SceneLibrary,
    SceneTiming,
    scene_to_dict,
)

# REQ-SCENE-004 — the per-show axes that must have no home in a static asset.
# `sequence_number`/`cue_number` are here too: they are CALL ARGUMENTS
# (`SceneTiming`), never asset fields.
PER_SHOW_KEYS = (
    "group",
    "group_number",
    "group_name",
    "fid",
    "executor",
    "executor_number",
    "sequence_number",
    "cue_number",
)

# REQ-SCENE-001 — the scene schema holds REFERENCES, never a copy of the look or
# fx value axis. These are the upstream field names it must not grow.
VALUE_AXIS_KEYS = ("attributes", "values", "steps", "dimmer", "colour", "color")


def _scene(**overrides) -> dict:
    """A minimal valid scene dict; overrides replace individual keys."""
    entry = {
        "scene_id": "blue-backlight-wave",
        "display_name": "파란 백라이트 웨이브",
        "label": "SCN BLUE WAVE",
        "look_id": "worship-blue-wash",
        "fx_id": "dimmer-wave-slow",
        "aliases": ["파란 웨이브"],
        "mood_keywords": ["차분한", "느린"],
    }
    entry.update(overrides)
    return entry


def _library(*entries: dict) -> dict:
    return {
        "schema_version": SCENE_SCHEMA_VERSION,
        "scenes": list(entries or (_scene(),)),
    }


class TestTriggerVocabularyIsClosed:
    """REQ-SCENE-001 — the trigger token set is enumerated, not open."""

    def test_the_set_is_exactly_the_five_rulebook_tokens(self):
        assert TRIGGER_TOKENS == ("Go", "Time", "Follow", "Sound", "BPM")

    def test_every_token_is_capitalized(self):
        # 31_choreography_patterns.md:115 — the console form is Capitalized and
        # the repository has no measurement saying a lowercase token is refused.
        assert all(token[0].isupper() for token in TRIGGER_TOKENS)


class TestSceneAxes:
    """REQ-SCENE-001 — identity, references, label, schema_version."""

    def test_the_scene_field_set_is_exactly_the_authored_axes(self):
        assert {f.name for f in fields(Scene)} == {
            "scene_id",
            "display_name",
            "label",
            "look_id",
            "fx_id",
            "aliases",
            "mood_keywords",
            "trig_type",
            "trig_time",
        }

    @pytest.mark.parametrize("key", PER_SHOW_KEYS)
    def test_no_per_show_axis_exists_on_the_scene_dataclass(self, key):
        # REQ-SCENE-004. Rig binding happens at compile time; a field here would
        # be honoured by every consumer with no complaint at all.
        assert key not in {f.name for f in fields(Scene)}

    @pytest.mark.parametrize("key", VALUE_AXIS_KEYS)
    def test_the_scene_does_not_copy_the_upstream_value_axes(self, key):
        assert key not in {f.name for f in fields(Scene)}

    def test_both_references_are_optional_on_the_dataclass(self):
        by_name = {f.name: f for f in fields(Scene)}
        assert by_name["look_id"].default is None
        assert by_name["fx_id"].default is None

    def test_the_library_carries_an_explicit_schema_version(self):
        library = load_library(_library())
        assert isinstance(library, SceneLibrary)
        assert library.schema_version == SCENE_SCHEMA_VERSION


class TestTimingIsACallArgument:
    """REQ-SCENE-004 — the timing axes live on the call, not on the asset."""

    def test_the_timing_field_set_is_exactly_the_four_timing_axes(self):
        assert {f.name for f in fields(SceneTiming)} == {
            "sequence_number",
            "cue_number",
            "trig_type",
            "trig_time",
        }

    def test_every_timing_axis_is_optional(self):
        assert parse_timing({}) == SceneTiming()

    def test_a_full_timing_call_parses(self):
        assert parse_timing(
            {
                "sequence_number": 21,
                "cue_number": 3,
                "trig_type": "Follow",
                "trig_time": 14,
            }
        ) == SceneTiming(sequence_number=21, cue_number=3, trig_type="Follow", trig_time=14.0)

    def test_an_unknown_timing_key_is_refused(self):
        with pytest.raises(SceneSchemaError, match="unknown key"):
            parse_timing({"executor": 7})


class TestValidLibraryLoads:
    """REQ-SCENE-006 — the happy path returns schema shapes, not raw dicts."""

    def test_every_entry_comes_back_as_a_scene(self):
        library = load_library(_library())
        assert [type(entry) for entry in library.scenes] == [Scene]

    def test_a_minimal_asset_defaults_its_optional_axes(self):
        # Only the three required fields plus one reference: the optional
        # sequences must come back empty, not absent.
        scene = load_library(
            _library(
                {
                    "scene_id": "bare",
                    "display_name": "맨몸 씬",
                    "label": "SCN BARE",
                    "fx_id": "dimmer-wave-slow",
                }
            )
        ).by_id("bare")
        assert scene.aliases == ()
        assert scene.mood_keywords == ()

    def test_the_entry_keeps_its_authored_axes(self):
        scene = load_library(_library()).by_id("blue-backlight-wave")
        assert scene.display_name == "파란 백라이트 웨이브"
        assert scene.label == "SCN BLUE WAVE"
        assert scene.look_id == "worship-blue-wash"
        assert scene.fx_id == "dimmer-wave-slow"
        assert scene.aliases == ("파란 웨이브",)
        assert scene.mood_keywords == ("차분한", "느린")
        assert scene.trig_type is None
        assert scene.trig_time is None

    def test_by_id_raises_for_an_absent_scene(self):
        with pytest.raises(KeyError):
            load_library(_library()).by_id("nope")

    def test_a_loaded_scene_round_trips_through_its_wire_form(self):
        scene = load_library(_library()).by_id("blue-backlight-wave")
        reloaded = load_library(_library(scene_to_dict(scene))).by_id("blue-backlight-wave")
        assert reloaded == scene


class TestUnknownFieldsAreRefused:
    """AC-SCENE-001 ① — the schema is CLOSED, not merely documented."""

    def test_an_unknown_scene_key_is_refused(self):
        with pytest.raises(SceneSchemaError, match="unknown key"):
            load_library(_library(_scene(tempo="fast")))

    def test_an_unknown_top_level_key_is_refused(self):
        data = _library()
        data["looks"] = []
        with pytest.raises(SceneSchemaError, match="unknown top-level key"):
            load_library(data)

    @pytest.mark.parametrize("key", PER_SHOW_KEYS)
    def test_a_per_show_key_is_refused_as_an_unknown_field(self, key):
        # REQ-SCENE-004 mechanically: the rejection of unknown keys IS the
        # enforcement — there is no separate per-show blocklist to fall out of
        # date with the schema.
        with pytest.raises(SceneSchemaError, match="unknown key"):
            load_library(_library(_scene(**{key: 3})))

    def test_a_wrong_schema_version_is_refused(self):
        data = _library()
        data["schema_version"] = 99
        with pytest.raises(SceneSchemaError, match="schema_version"):
            load_library(data)

    def test_a_missing_required_field_is_refused(self):
        entry = _scene()
        del entry["display_name"]
        with pytest.raises(SceneSchemaError, match="missing required field"):
            load_library(_library(entry))


class TestMalformedShapesAreNamed:
    """REQ-SCENE-006 — a broken library never loads half-way and quietly."""

    def test_a_library_that_is_not_a_mapping_is_refused(self):
        with pytest.raises(SceneSchemaError, match="must be a mapping"):
            load_library([_scene()])

    def test_a_scene_that_is_not_a_mapping_is_refused(self):
        with pytest.raises(SceneSchemaError, match="must be a mapping"):
            load_library({"schema_version": SCENE_SCHEMA_VERSION, "scenes": ["blue"]})

    @pytest.mark.parametrize("entries", [[], "blue", None])
    def test_an_empty_or_non_list_scenes_axis_is_refused(self, entries):
        with pytest.raises(SceneSchemaError, match="non-empty list"):
            load_library({"schema_version": SCENE_SCHEMA_VERSION, "scenes": entries})

    def test_a_non_list_alias_axis_is_refused(self):
        with pytest.raises(SceneSchemaError, match="aliases"):
            load_library(_library(_scene(aliases="파란 웨이브")))

    def test_a_non_string_alias_entry_is_refused(self):
        with pytest.raises(SceneSchemaError, match="aliases"):
            load_library(_library(_scene(aliases=[7])))

    def test_a_non_string_mood_keyword_is_refused(self):
        with pytest.raises(SceneSchemaError, match="mood_keywords"):
            load_library(_library(_scene(mood_keywords=[None])))

    def test_timing_that_is_not_a_mapping_is_refused(self):
        with pytest.raises(SceneSchemaError, match="must be a mapping"):
            parse_timing([("cue_number", 2)])


class TestDuplicateSceneIdsAreRefused:
    """AC-SCENE-001 ② — two scenes cannot answer to one id."""

    def test_a_duplicate_scene_id_is_refused(self):
        with pytest.raises(SceneSchemaError, match="duplicate scene id"):
            load_library(_library(_scene(), _scene(display_name="다른 이름")))

    def test_two_distinct_ids_load(self):
        library = load_library(_library(_scene(), _scene(scene_id="other")))
        assert [s.scene_id for s in library.scenes] == [
            "blue-backlight-wave",
            "other",
        ]


class TestAtLeastOneReferenceIsRequired:
    """AC-SCENE-002 (REQ-SCENE-003) — a scene with nothing to compose is not a scene."""

    def test_a_scene_with_neither_reference_is_refused(self):
        entry = _scene()
        del entry["look_id"]
        del entry["fx_id"]
        with pytest.raises(SceneSchemaError, match="look_id.*fx_id|fx_id.*look_id"):
            load_library(_library(entry))

    def test_an_explicit_null_pair_is_refused_too(self):
        with pytest.raises(SceneSchemaError, match="look_id.*fx_id|fx_id.*look_id"):
            load_library(_library(_scene(look_id=None, fx_id=None)))

    def test_both_references_present_is_legal(self):
        scene = load_library(_library(_scene())).by_id("blue-backlight-wave")
        assert (scene.look_id, scene.fx_id) == (
            "worship-blue-wash",
            "dimmer-wave-slow",
        )

    def test_a_look_only_scene_is_legal(self):
        entry = _scene()
        del entry["fx_id"]
        scene = load_library(_library(entry)).by_id("blue-backlight-wave")
        assert scene.look_id == "worship-blue-wash"
        assert scene.fx_id is None

    def test_an_fx_only_scene_is_legal(self):
        entry = _scene()
        del entry["look_id"]
        scene = load_library(_library(entry)).by_id("blue-backlight-wave")
        assert scene.look_id is None
        assert scene.fx_id == "dimmer-wave-slow"


class TestNumericRangesAreEnforced:
    """AC-SCENE-001 ④ — `cue_number` > 0 integer, `trig_time` >= 0."""

    @pytest.mark.parametrize("bad", [0, -1])
    def test_a_non_positive_cue_number_is_refused(self, bad):
        with pytest.raises(SceneSchemaError, match="cue_number"):
            parse_timing({"cue_number": bad})

    @pytest.mark.parametrize("bad", [1.5, "2", True])
    def test_a_non_integer_cue_number_is_refused(self, bad):
        # `True` is included deliberately: bool is an int subclass in Python, so
        # a naive isinstance check would accept `cue_number: true`.
        with pytest.raises(SceneSchemaError, match="cue_number"):
            parse_timing({"cue_number": bad})

    @pytest.mark.parametrize("bad", [0, -1, 2.5, True])
    def test_a_bad_sequence_number_is_refused(self, bad):
        with pytest.raises(SceneSchemaError, match="sequence_number"):
            parse_timing({"sequence_number": bad})

    def test_a_negative_trig_time_is_refused_on_the_call(self):
        with pytest.raises(SceneSchemaError, match="trig_time"):
            parse_timing({"trig_time": -0.5})

    def test_a_negative_trig_time_is_refused_on_the_asset(self):
        with pytest.raises(SceneSchemaError, match="trig_time"):
            load_library(_library(_scene(trig_type="Time", trig_time=-1)))

    def test_a_zero_trig_time_is_legal(self):
        # acceptance.md §D — the range check refuses `< 0` only.
        scene = load_library(_library(_scene(trig_type="Time", trig_time=0))).by_id(
            "blue-backlight-wave"
        )
        assert scene.trig_time == 0.0

    def test_a_non_numeric_trig_time_is_refused(self):
        with pytest.raises(SceneSchemaError, match="trig_time"):
            load_library(_library(_scene(trig_type="Time", trig_time="soon")))


class TestTriggerTokensAreClosed:
    """AC-SCENE-001 ⑤ — unknown or lowercase `trig_type` is refused."""

    @pytest.mark.parametrize("token", TRIGGER_TOKENS)
    def test_every_closed_token_is_accepted(self, token):
        scene = load_library(_library(_scene(trig_type=token))).by_id("blue-backlight-wave")
        assert scene.trig_type == token

    def test_an_unknown_token_is_refused(self):
        with pytest.raises(SceneSchemaError, match="trig_type"):
            load_library(_library(_scene(trig_type="Cue")))

    @pytest.mark.parametrize("token", TRIGGER_TOKENS)
    def test_a_lowercase_token_is_refused(self, token):
        # The Capitalized form is the rulebook's; the console gives this
        # repository no way to observe a rejection, so the loader is the net.
        with pytest.raises(SceneSchemaError, match="trig_type"):
            load_library(_library(_scene(trig_type=token.lower())))

    @pytest.mark.parametrize("token", [t for t in TRIGGER_TOKENS if t.upper() != t])
    def test_an_all_caps_token_is_refused(self, token):
        # `BPM` is excluded by construction: it IS the closed token, and a
        # parametrisation that fed it back here would assert the opposite of
        # `test_every_closed_token_is_accepted`.
        with pytest.raises(SceneSchemaError, match="trig_type"):
            load_library(_library(_scene(trig_type=token.upper())))

    def test_a_lowercase_token_is_refused_on_the_call_too(self):
        with pytest.raises(SceneSchemaError, match="trig_type"):
            parse_timing({"trig_type": "follow"})


class TestLabelIsStorable:
    """REQ-SCENE-001 — the label is inlined into the `Store` literal."""

    def test_an_empty_label_is_refused(self):
        with pytest.raises(SceneSchemaError, match="label"):
            load_library(_library(_scene(label="   ")))

    def test_a_label_carrying_a_quote_is_refused(self):
        # It is inlined between single quotes on the MA3 command line
        # (`Store Sequence <s> Cue <c> '<label>'`), so a quote breaks the line
        # itself — the same guard fx spells LABEL_UNQUOTABLE.
        with pytest.raises(SceneSchemaError, match="label"):
            load_library(_library(_scene(label="SCN 'X'")))

    def test_a_label_carrying_a_newline_is_refused(self):
        with pytest.raises(SceneSchemaError, match="label"):
            load_library(_library(_scene(label="SCN\nX")))

    def test_a_non_ascii_label_is_refused(self):
        # spec.md §A ("라벨 | ASCII, Store 리터럴에 인라인"). The Korean display
        # name lives on `display_name`; the stored label stays ASCII.
        with pytest.raises(SceneSchemaError, match="label"):
            load_library(_library(_scene(label="파란 웨이브")))


class TestDirectoryLoader:
    """REQ-SCENE-006 — the YAML wrapper reports its own failures explicitly."""

    def _write(self, directory, name: str, data: dict) -> None:
        (directory / name).write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    def test_every_yaml_in_the_directory_is_merged(self, tmp_path):
        self._write(tmp_path, "a.yaml", _library(_scene()))
        self._write(tmp_path, "b.yaml", _library(_scene(scene_id="second")))
        library = load_library_from_dir(tmp_path)
        assert sorted(s.scene_id for s in library.scenes) == [
            "blue-backlight-wave",
            "second",
        ]

    def test_a_cross_file_duplicate_id_is_refused(self, tmp_path):
        # The collision a per-file loader would never see.
        self._write(tmp_path, "a.yaml", _library(_scene()))
        self._write(tmp_path, "b.yaml", _library(_scene()))
        with pytest.raises(SceneSchemaError, match="duplicate scene id"):
            load_library_from_dir(tmp_path)

    def test_a_missing_directory_is_refused(self, tmp_path):
        with pytest.raises(SceneSchemaError, match="directory not found"):
            load_library_from_dir(tmp_path / "absent")

    def test_an_empty_directory_is_refused(self, tmp_path):
        with pytest.raises(SceneSchemaError, match="no scene assets"):
            load_library_from_dir(tmp_path)

    def test_invalid_yaml_names_the_file(self, tmp_path):
        (tmp_path / "broken.yaml").write_text("scenes: [", encoding="utf-8")
        with pytest.raises(SceneSchemaError, match="broken.yaml"):
            load_library_from_dir(tmp_path)
