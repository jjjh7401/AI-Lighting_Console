"""Panel store, catalog builder and pin persistence (SHOWUI M2).

The panel's server half: the rig-enumerated catalog (REQ-SHOWUI-001/002/003),
the pinned-tile store that survives a restart (REQ-SHOWUI-004/005/023), and the
membership predicate M3 will check a client-supplied target against
(REQ-SHOWUI-022, membership half).

Every test drives the builder through an in-memory ``StateQueryPort`` fake — the
same shape ``gate.state_port`` presents — so nothing here can reach the console
or the OSC send surface (REQ-SHOWUI-007).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from server.orchestrator.last_created import LastCreated
from server.web.messages import PANEL_TARGET_KINDS, panel_item
from server.web.panel import (
    PANEL_CATALOG_SECTIONS,
    PIN_FILE_NAME,
    PIN_SEED_UNAVAILABLE_MESSAGE,
    PanelStore,
    PinSeedUnavailable,
    PinStore,
    PinStoreError,
    SectionSpec,
    build_catalog,
    pin_store_path,
)


class FakeStatePort:
    """Fake StateQueryPort backed by path -> decoded snapshot payload.

    Mirrors ``server/tests/test_tools.py::FakeStatePort`` — the panel reads the
    console through the SAME gate-audited seam the rig-context tool uses.
    """

    def __init__(self, tree: dict):
        self.tree = tree
        self.queries: list[str] = []

    def query_state(self, path: str) -> dict:
        self.queries.append(path)
        if path not in self.tree:
            raise LookupError(f"unknown object path: {path}")
        return self.tree[path]


class DeadStatePort:
    """Every query fails — the console did not answer at all."""

    def __init__(self) -> None:
        self.queries: list[str] = []

    def query_state(self, path: str) -> dict:
        self.queries.append(path)
        raise TimeoutError("no reply")


def _snapshot(path: str, entries: list[tuple[int | None, str]], **extra) -> dict:
    """One responder snapshot. ``None`` as the number means the responder could
    not establish that child's slot, so it arrives WITHOUT ``i``."""
    children = []
    for number, name in entries:
        child: dict[str, object] = {"name": name}
        if number is not None:
            child["i"] = number
        children.append(child)
    payload: dict[str, object] = {"v": 1, "kind": "state", "path": path, "children": children}
    payload.update(extra)
    return payload


# A rig whose pool numbers are deliberately NON-CONTIGUOUS: sequences live at
# 2, 7 and 41, so "the 3rd tile" and "object 3" are different objects and any
# index-keyed builder resolves the wrong one (REQ-SHOWUI-003).
def _rig_tree() -> dict:
    return {
        "DataPool/Sequences": _snapshot(
            "DataPool/Sequences", [(2, "Warm Wash"), (7, "Cyan Look"), (41, "Summer Rock")]
        ),
        "DataPool/Pages": _snapshot("DataPool/Pages", [(1, "Main")]),
        "DataPool/Pages/1": _snapshot(
            "DataPool/Pages/1", [(191, "Summer Rock"), (201, "Cyan Look")]
        ),
        # Present in the showfile, and deliberately NOT a catalog source: a
        # fixture's `no` is its patch slot, not an address the console fires.
        "Patch/Stages/1/Fixtures": _snapshot(
            "Patch/Stages/1/Fixtures", [(1, "Spot 1"), (2, "Wash 1")]
        ),
    }


def _ids(items) -> list[str]:
    return [item["id"] for item in items]


def _section(catalog, name: str) -> dict:
    for section in catalog.sections:
        if section["name"] == name:
            return section
    raise AssertionError(f"no section named {name!r}: {catalog.sections}")


# -- catalog accuracy (AC-SHOWUI-002 / AC-SHOWUI-003) --------------------------


class TestCatalogKeying:
    def test_tiles_carry_the_real_pool_number_never_a_list_position(self):
        catalog = build_catalog(FakeStatePort(_rig_tree()))
        sequence_ids = [i for i in _ids(catalog.items) if i.startswith("sequence:")]
        assert sequence_ids == ["sequence:2", "sequence:7", "sequence:41"]
        # The regression this pins: the 3rd sequence tile is object 41, and a
        # positional builder would have produced "sequence:3".
        assert "sequence:3" not in _ids(catalog.items)

    def test_v1_emits_no_executor_tiles_from_the_catalog(self):
        # SHOWUI v1 descope (→ SPEC-COPILOT-EXECREF-001): the executor page
        # drill-down is STRUCTURALLY absent from the catalog because the drill-down
        # index is not the console command-line number (live-proven console# = 100+i,
        # progress.md §M6) and the i=101 collision would silently fire the wrong
        # object. Executors reach the panel ONLY via pins (which carry the real
        # console number), never from an auto-enumerated catalog tile.
        catalog = build_catalog(FakeStatePort(_rig_tree()))
        executors = [i for i in _ids(catalog.items) if i.startswith("executor:")]
        assert executors == []

    def test_every_tile_addresses_a_kind_the_console_actually_fires(self):
        catalog = build_catalog(FakeStatePort(_rig_tree()))
        assert {i["target_kind"] for i in catalog.items} <= set(PANEL_TARGET_KINDS)

    def test_no_catalog_section_reads_fixtures(self):
        # Structural, not incidental: "fixtures" is not a catalog source at all,
        # so a populated fixture list cannot become a tile (REQ-SHOWUI-003).
        paths = {spec.path for spec in PANEL_CATALOG_SECTIONS}
        assert "Patch/Stages/1/Fixtures" not in paths
        assert not any(spec.name == "fixtures" for spec in PANEL_CATALOG_SECTIONS)

    def test_no_catalog_section_drills_into_executors(self):
        # The v1 executor descope, made non-regressable in the same STRUCTURAL way
        # as the fixtures exclusion above: no section auto-enumerates executors and
        # no section drills down. Executors are a pin-only tile source in v1; the
        # drill-down section returns only under SPEC-COPILOT-EXECREF-001.
        assert not any(spec.drilldown for spec in PANEL_CATALOG_SECTIONS)
        assert not any(spec.target_kind == "executor" for spec in PANEL_CATALOG_SECTIONS)
        assert not any(spec.name == "pages" for spec in PANEL_CATALOG_SECTIONS)

    def test_a_populated_fixture_list_yields_zero_execution_tiles(self):
        port = FakeStatePort(_rig_tree())
        catalog = build_catalog(port)
        assert "Patch/Stages/1/Fixtures" not in port.queries
        assert not any(i["name"] in ("Spot 1", "Wash 1") for i in catalog.items)

    def test_a_child_without_a_slot_number_is_not_a_tile(self):
        tree = _rig_tree()
        tree["DataPool/Sequences"] = _snapshot(
            "DataPool/Sequences", [(2, "Warm Wash"), (None, "Unnumbered")]
        )
        catalog = build_catalog(FakeStatePort(tree))
        # No number means no address; inventing one is how a misfire happens.
        assert "Unnumbered" not in [i["name"] for i in catalog.items]
        assert "sequence:2" in _ids(catalog.items)

    def test_tiles_are_auto_sourced_and_named_verbatim(self):
        catalog = build_catalog(FakeStatePort(_rig_tree()))
        assert {i["source"] for i in catalog.items} == {"auto"}
        assert "Summer Rock" in [i["name"] for i in catalog.items]


class TestCatalogCompleteness:
    # v1 ships ONE catalog section (`sequences`); the completeness signals are
    # retargeted to it. Drill-down-only signals (contents_unavailable via a
    # page-open failure, drilldown_capped) have no subject in a single
    # non-drilldown section — their machinery is exercised by
    # ``TestRetainedDrilldownMachineryForExecref`` below, which monkeypatches the
    # two-section catalog EXECREF-001 restores.
    def test_truncated_is_propagated_not_dropped(self):
        tree = _rig_tree()
        tree["DataPool/Sequences"] = _snapshot(
            "DataPool/Sequences", [(2, "Warm Wash")], truncated=True
        )
        catalog = build_catalog(FakeStatePort(tree))
        assert _section(catalog, "sequences")["truncated"] is True

    def test_a_normal_read_reports_full_completeness(self):
        # The remaining completeness flags on the sequences section: a clean read
        # is neither truncated, nor capped, nor contents-unavailable.
        catalog = build_catalog(FakeStatePort(_rig_tree()))
        section = _section(catalog, "sequences")
        assert section["truncated"] is False
        assert section["drilldown_capped"] is False
        assert section["contents_unavailable"] is False

    def test_every_section_reports_a_status(self):
        catalog = build_catalog(FakeStatePort(_rig_tree()))
        assert [s["status"] for s in catalog.sections] == ["ok"]


class TestCatalogFailureReasons:
    def test_nothing_answering_is_an_unreachable_console(self):
        catalog = build_catalog(DeadStatePort())
        assert [s["status"] for s in catalog.sections] == ["console_unreachable"]

    def test_a_failed_section_contributes_no_tiles(self):
        catalog = build_catalog(DeadStatePort())
        assert catalog.items == ()


class TestRetainedDrilldownMachineryForExecref:
    """The drill-down walk and the split-failure classifier survive the v1
    executor descope, because SPEC-COPILOT-EXECREF-001 re-adds an executor
    section on top of them. v1 ships ONE section, so path_not_resolved (a sibling
    answered, THIS path is wrong) and the drill-down completeness flags cannot
    arise from the default catalog — they need a second, drilling section. These
    tests monkeypatch that two-section catalog so the descope cannot silently
    regress the retained machinery (the `console# = 100+i` addressing fix EXECREF
    adds is orthogonal — it changes the tile's number, not the walk)."""

    _TWO_SECTIONS = (
        SectionSpec(name="sequences", path="DataPool/Sequences", target_kind="sequence"),
        SectionSpec(
            name="pages", path="DataPool/Pages", target_kind="executor", drilldown=True
        ),
    )

    def _patch(self, monkeypatch):
        from server.web import panel as panel_module

        monkeypatch.setattr(panel_module, "PANEL_CATALOG_SECTIONS", self._TWO_SECTIONS)

    def test_the_split_failure_classification_is_never_merged(self, monkeypatch):
        self._patch(monkeypatch)
        tree = _rig_tree()
        del tree["DataPool/Pages"]
        partial = build_catalog(FakeStatePort(tree))
        # sequences answered, so the console IS reachable and THIS path is wrong.
        assert _section(partial, "sequences")["status"] == "ok"
        assert _section(partial, "pages")["status"] == "path_not_resolved"
        dead = build_catalog(DeadStatePort())
        assert _section(dead, "pages")["status"] == "console_unreachable"
        # The two reasons ask for different operator actions and must stay distinct.
        assert _section(partial, "pages")["status"] != _section(dead, "pages")["status"]

    def test_contents_unavailable_is_propagated(self, monkeypatch):
        self._patch(monkeypatch)
        tree = _rig_tree()
        tree["DataPool/Pages"] = _snapshot("DataPool/Pages", [(1, "Main"), (2, "Spare")])
        # Page 2 cannot be opened — distinct from a verified-empty page.
        catalog = build_catalog(FakeStatePort(tree))
        assert _section(catalog, "pages")["contents_unavailable"] is True

    def test_a_verified_empty_page_is_not_contents_unavailable(self, monkeypatch):
        self._patch(monkeypatch)
        tree = _rig_tree()
        tree["DataPool/Pages/1"] = _snapshot("DataPool/Pages/1", [])
        catalog = build_catalog(FakeStatePort(tree))
        assert _section(catalog, "pages")["contents_unavailable"] is False

    def test_drilldown_capped_is_propagated(self, monkeypatch):
        self._patch(monkeypatch)
        tree = _rig_tree()
        pages = [(n, f"Page {n}") for n in range(1, 6)]
        tree["DataPool/Pages"] = _snapshot("DataPool/Pages", pages)
        for number, _ in pages:
            tree[f"DataPool/Pages/{number}"] = _snapshot(
                f"DataPool/Pages/{number}", [(100 + number, f"Exec {number}")]
            )
        catalog = build_catalog(FakeStatePort(tree), query_cap=2)
        assert _section(catalog, "pages")["drilldown_capped"] is True
        # A capped walk still yields the tiles it DID open.
        assert "executor:101" in _ids(catalog.items)


class TestCatalogSeam:
    def test_the_builder_reads_only_through_the_injected_state_port(self):
        port = FakeStatePort(_rig_tree())
        build_catalog(port)
        # v1 reads ONE source; DataPool/Pages is no longer enumerated (executor
        # descope → EXECREF-001).
        assert port.queries == ["DataPool/Sequences"]

    def test_paths_are_overridable_so_a_site_can_move_them(self):
        tree = {"Elsewhere/Sequences": _snapshot("Elsewhere/Sequences", [(5, "Site Look")])}
        port = FakeStatePort(tree)
        catalog = build_catalog(port, paths={"sequences": "Elsewhere/Sequences"})
        assert "Elsewhere/Sequences" in port.queries
        assert "sequence:5" in _ids(catalog.items)


# -- pin persistence (AC-SHOWUI-004b) ------------------------------------------


def _pin(target_kind: str = "sequence", target: int = 71, name: str = "Cyan Look") -> dict:
    return panel_item(
        kind="sequence",
        target_kind=target_kind,
        target=target,
        name=name,
        source="pin",
        appearance="#00c8ff",
    )


class TestPinPersistence:
    def test_a_pin_survives_a_restart(self, tmp_path):
        path = tmp_path / PIN_FILE_NAME
        PinStore(path).add(_pin())
        # A fresh process reads the same file — this is the restart.
        assert _ids(PinStore(path).items()) == ["sequence:71"]

    def test_the_write_goes_through_a_same_directory_temp_and_os_replace(
        self, tmp_path, monkeypatch
    ):
        path = tmp_path / PIN_FILE_NAME
        calls: list[tuple[str, str]] = []
        real_replace = os.replace

        def spy(src, dst):
            calls.append((str(src), str(dst)))
            real_replace(src, dst)

        monkeypatch.setattr(os, "replace", spy)
        PinStore(path).add(_pin())
        assert calls, "the pin file must be swapped into place with os.replace"
        src, dst = calls[-1]
        assert dst == str(path)
        assert src != dst
        # Same directory: os.replace is only atomic within one filesystem.
        assert Path(src).parent == path.parent
        # Nothing left behind — iterdir, not glob, so a dot-prefixed temp counts.
        assert list(tmp_path.iterdir()) == [path]

    def test_a_failed_swap_leaves_the_previous_file_intact(self, tmp_path, monkeypatch):
        path = tmp_path / PIN_FILE_NAME
        store = PinStore(path)
        store.add(_pin())
        before = path.read_text(encoding="utf-8")

        def boom(src, dst):
            raise OSError("disk full")

        monkeypatch.setattr(os, "replace", boom)
        with pytest.raises(OSError):
            store.add(_pin(target=72))
        assert path.read_text(encoding="utf-8") == before
        assert list(tmp_path.iterdir()) == [path]

    def test_an_absent_file_starts_an_empty_panel(self, tmp_path):
        assert PinStore(tmp_path / PIN_FILE_NAME).items() == []

    def test_a_corrupt_file_starts_empty_and_the_next_write_repairs_it(self, tmp_path):
        path = tmp_path / PIN_FILE_NAME
        path.write_text("{not json at all", encoding="utf-8")
        store = PinStore(path)
        assert store.items() == []  # fail-open read — never a startup crash
        store.add(_pin())
        assert _ids(PinStore(path).items()) == ["sequence:71"]

    def test_a_structurally_wrong_file_starts_empty(self, tmp_path):
        path = tmp_path / PIN_FILE_NAME
        path.write_text(json.dumps({"pins": {"not": "a list"}}), encoding="utf-8")
        assert PinStore(path).items() == []

    def test_a_record_that_cannot_be_addressed_is_not_restored(self, tmp_path):
        path = tmp_path / PIN_FILE_NAME
        path.write_text(
            json.dumps({"version": 1, "pins": [{"target_kind": "fixture", "target": 3}]}),
            encoding="utf-8",
        )
        # A fixture is not an address the console fires — the whole file is
        # treated as unusable rather than partially trusted.
        assert PinStore(path).items() == []

    def test_the_default_path_lives_under_the_user_data_dir(self):
        from server.deploy.settings import user_data_dir

        assert pin_store_path() == user_data_dir() / PIN_FILE_NAME

    def test_the_store_reports_the_file_it_owns(self, tmp_path):
        path = tmp_path / PIN_FILE_NAME
        assert PinStore(path).path == path

    @pytest.mark.parametrize(
        "body",
        [
            json.dumps([1, 2, 3]),  # valid JSON, wrong top-level shape
            json.dumps({"version": 1, "pins": ["not a record"]}),
            json.dumps({"version": 1}),  # no pins key at all
            "",  # truncated to nothing mid-write
        ],
        ids=["array-toplevel", "non-dict-record", "no-pins-key", "empty-file"],
    )
    def test_every_malformed_shape_starts_empty_instead_of_raising(self, tmp_path, body):
        # Fail-open is only useful if it covers EVERY defect shape: one branch
        # that raises instead of returning turns a bad pin file into an app that
        # will not start a show.
        path = tmp_path / PIN_FILE_NAME
        path.write_text(body, encoding="utf-8")
        assert PinStore(path).items() == []

    @pytest.mark.parametrize(
        "field,value",
        [("name", 123), ("appearance", 7)],
        ids=["non-string-name", "non-string-appearance"],
    )
    def test_a_wrongly_typed_field_is_refused_on_write(self, tmp_path, field, value):
        store = PinStore(tmp_path / PIN_FILE_NAME)
        with pytest.raises(PinStoreError):
            store.add({**_pin(), field: value})


class TestPinStoreSecurity:
    def test_a_credential_like_key_is_refused_on_write(self, tmp_path):
        path = tmp_path / PIN_FILE_NAME
        store = PinStore(path)
        with pytest.raises(PinStoreError):
            store.add({**_pin(), "api_key": "sk-live-secret"})
        assert not path.exists()
        assert store.items() == []

    def test_a_credential_like_key_anywhere_refuses_the_write(self, tmp_path):
        store = PinStore(tmp_path / PIN_FILE_NAME)
        for key in ("token", "secret", "password", "credentials"):
            with pytest.raises(PinStoreError):
                store.add({**_pin(), key: "x"})

    def test_the_written_file_carries_only_the_known_tile_fields(self, tmp_path):
        path = tmp_path / PIN_FILE_NAME
        PinStore(path).add(_pin())
        data = json.loads(path.read_text(encoding="utf-8"))
        assert set(data["pins"][0]) == {"kind", "target_kind", "target", "name", "appearance"}

    def test_a_file_carrying_a_credential_key_is_not_loaded(self, tmp_path):
        path = tmp_path / PIN_FILE_NAME
        path.write_text(
            json.dumps({"version": 1, "pins": [], "api_key": "sk-live"}), encoding="utf-8"
        )
        assert PinStore(path).items() == []


class TestPinOrderingAndUnpin:
    def test_pins_append_and_never_reorder(self, tmp_path):
        store = PinStore(tmp_path / PIN_FILE_NAME)
        store.add(_pin(target=71))
        store.add(_pin(target=12))
        store.add(_pin(target_kind="executor", target=201))
        assert _ids(store.items()) == ["sequence:71", "sequence:12", "executor:201"]

    def test_pinning_the_same_tile_twice_does_not_duplicate_it(self, tmp_path):
        store = PinStore(tmp_path / PIN_FILE_NAME)
        assert store.add(_pin()) is True
        assert store.add(_pin()) is False
        assert _ids(store.items()) == ["sequence:71"]

    def test_the_same_number_on_two_object_classes_are_two_tiles(self, tmp_path):
        store = PinStore(tmp_path / PIN_FILE_NAME)
        store.add(_pin(target_kind="sequence", target=41))
        store.add(_pin(target_kind="executor", target=41))
        assert _ids(store.items()) == ["sequence:41", "executor:41"]

    def test_unpin_removes_the_tile_and_persists_the_removal(self, tmp_path):
        path = tmp_path / PIN_FILE_NAME
        store = PinStore(path)
        store.add(_pin(target=71))
        store.add(_pin(target=12))
        assert store.remove("sequence", 71) is True
        assert _ids(store.items()) == ["sequence:12"]
        # The removal survives the restart too, not just this process.
        assert _ids(PinStore(path).items()) == ["sequence:12"]

    def test_unpinning_an_absent_tile_is_a_no_op(self, tmp_path):
        store = PinStore(tmp_path / PIN_FILE_NAME)
        store.add(_pin(target=71))
        assert store.remove("sequence", 999) is False
        assert _ids(store.items()) == ["sequence:71"]

    def test_unpinning_leaves_the_remaining_order_untouched(self, tmp_path):
        store = PinStore(tmp_path / PIN_FILE_NAME)
        for target in (71, 12, 5):
            store.add(_pin(target=target))
        store.remove("sequence", 12)
        assert _ids(store.items()) == ["sequence:71", "sequence:5"]


# -- pin seed (AC-SHOWUI-004a) --------------------------------------------------


class TestPinSeed:
    def test_a_seed_with_an_executor_pins_the_executor(self, tmp_path):
        store = PanelStore(
            state_port=FakeStatePort(_rig_tree()), pins=PinStore(tmp_path / PIN_FILE_NAME)
        )
        item = store.pin_from_seed(LastCreated(sequence=71, executor=201))
        assert item["target_kind"] == "executor"
        assert item["target"] == 201
        assert item["source"] == "pin"
        # The executor is the ADDRESS; the sequence is the look's identity.
        assert "71" in item["name"]

    def test_a_seed_without_an_executor_pins_the_sequence(self, tmp_path):
        store = PanelStore(
            state_port=FakeStatePort(_rig_tree()), pins=PinStore(tmp_path / PIN_FILE_NAME)
        )
        item = store.pin_from_seed(LastCreated(sequence=71))
        assert (item["target_kind"], item["target"]) == ("sequence", 71)

    def test_an_absent_seed_is_an_explicit_error_never_a_silent_no_op(self, tmp_path):
        store = PanelStore(
            state_port=FakeStatePort(_rig_tree()), pins=PinStore(tmp_path / PIN_FILE_NAME)
        )
        with pytest.raises(PinSeedUnavailable):
            store.pin_from_seed(None)
        assert store.pins.items() == []

    def test_a_seed_with_no_sequence_is_the_same_explicit_error(self, tmp_path):
        store = PanelStore(
            state_port=FakeStatePort(_rig_tree()), pins=PinStore(tmp_path / PIN_FILE_NAME)
        )
        with pytest.raises(PinSeedUnavailable):
            store.pin_from_seed(LastCreated(sequence=None, executor=5))

    def test_the_error_carries_a_korean_message_the_ui_can_show(self):
        assert PIN_SEED_UNAVAILABLE_MESSAGE
        assert any("가" <= ch <= "힣" for ch in PIN_SEED_UNAVAILABLE_MESSAGE)

    def test_a_pinned_seed_is_persisted(self, tmp_path):
        path = tmp_path / PIN_FILE_NAME
        store = PanelStore(state_port=FakeStatePort(_rig_tree()), pins=PinStore(path))
        store.pin_from_seed(LastCreated(sequence=71, executor=201))
        assert _ids(PinStore(path).items()) == ["executor:201"]

    def test_the_chat_session_exposes_the_seed(self):
        from server.web.session import ChatSession

        # The seam M3 reads: the session's cross-turn memory, not a new source.
        assert isinstance(ChatSession.last_created, property)


# -- composed store (ordering + refresh semantics) ------------------------------


class TestPanelStore:
    def _store(self, tmp_path, tree=None):
        return PanelStore(
            state_port=FakeStatePort(_rig_tree() if tree is None else tree),
            pins=PinStore(tmp_path / PIN_FILE_NAME),
        )

    def test_pins_lead_the_grid_so_a_rig_change_cannot_move_them(self, tmp_path):
        store = self._store(tmp_path)
        store.pins.add(_pin(target=71))
        store.refresh_catalog()
        assert _ids(store.items())[0] == "sequence:71"

    def test_a_refresh_replaces_the_catalog_instead_of_merging(self, tmp_path):
        store = self._store(tmp_path)
        store.refresh_catalog()
        assert "sequence:41" in _ids(store.items())
        smaller = {
            "DataPool/Sequences": _snapshot("DataPool/Sequences", [(2, "Warm Wash")]),
        }
        store.state_port = FakeStatePort(smaller)
        store.refresh_catalog()
        assert _ids(store.items()) == ["sequence:2"]

    def test_before_the_first_refresh_the_panel_is_empty_not_stale(self, tmp_path):
        store = self._store(tmp_path)
        assert store.items() == []
        assert store.sections() == []

    def test_sections_come_from_the_last_refresh(self, tmp_path):
        store = self._store(tmp_path)
        store.refresh_catalog()
        assert [s["name"] for s in store.sections()] == ["sequences"]

    def test_unpin_goes_through_the_store(self, tmp_path):
        store = self._store(tmp_path)
        store.pins.add(_pin(target=71))
        assert store.unpin("sequence", 71) is True
        assert store.items() == []


# -- membership predicate (REQ-SHOWUI-022, membership half; wired in M3) --------


class TestMembership:
    def _store(self, tmp_path):
        return PanelStore(
            state_port=FakeStatePort(_rig_tree()), pins=PinStore(tmp_path / PIN_FILE_NAME)
        )

    def test_a_catalog_tile_is_a_member(self, tmp_path):
        store = self._store(tmp_path)
        store.refresh_catalog()
        assert store.contains("sequence", 41) is True
        # Executors are no longer auto-enumerated (v1 descope → EXECREF-001): an
        # executor is a member ONLY once pinned, never straight from the catalog.
        assert store.contains("executor", 191) is False
        store.pins.add(_pin(target_kind="executor", target=191, name="Pinned"))
        assert store.contains("executor", 191) is True

    def test_a_pinned_tile_is_a_member_without_any_catalog(self, tmp_path):
        store = self._store(tmp_path)
        store.pins.add(_pin(target=71))
        assert store.contains("sequence", 71) is True

    def test_an_unknown_target_is_not_a_member(self, tmp_path):
        store = self._store(tmp_path)
        store.refresh_catalog()
        assert store.contains("sequence", 999) is False

    def test_the_object_class_is_part_of_the_identity(self, tmp_path):
        store = self._store(tmp_path)
        store.refresh_catalog()
        # Sequence 41 exists; Executor 41 does not. A number-only membership
        # check would wave the wrong object straight through to the gate.
        assert store.contains("sequence", 41) is True
        assert store.contains("executor", 41) is False

    def test_an_object_class_the_console_never_fires_is_not_a_member(self, tmp_path):
        store = self._store(tmp_path)
        store.refresh_catalog()
        # "fixture" is not in PANEL_TARGET_KINDS; membership refuses it outright
        # rather than searching for it and happening to find nothing.
        assert store.contains("fixture", 1) is False

    def test_the_last_enumeration_is_readable(self, tmp_path):
        store = self._store(tmp_path)
        assert store.catalog.items == ()
        assert store.refresh_catalog() is store.catalog

    def test_an_unpinned_tile_stops_being_a_member(self, tmp_path):
        store = self._store(tmp_path)
        store.pins.add(_pin(target=71))
        store.unpin("sequence", 71)
        assert store.contains("sequence", 71) is False


# -- import boundary (AC-SHOWUI-006) -------------------------------------------


class TestPanelModuleBoundary:
    def test_the_panel_module_never_reaches_the_osc_send_surface(self):
        source = Path(__file__).resolve().parents[1] / "web" / "panel.py"
        text = source.read_text(encoding="utf-8")
        for forbidden in ("server.bridge", "pythonosc"):
            assert forbidden not in text, f"panel.py must not reference {forbidden}"

    def test_the_panel_module_declares_no_execution_surface(self):
        # Reads are the panel's only console contact in M2; execution arrives in
        # M3 and goes through gate.screen(), never a second path.
        from server.web import panel

        assert not hasattr(panel, "execute")
        assert not hasattr(panel, "screen")
