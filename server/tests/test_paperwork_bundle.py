"""Handover pack builder (P0 W2 — ``.moai/state/handoff/p0-w2-brief.md``).

``build_handover_pack`` calls the SAME three builders
``test_paperwork_patch_sheet.py`` / ``test_paperwork_cue_sheet.py`` /
``test_paperwork_preset_list.py`` already exercise directly — this suite
fakes the same ``StateQueryPort``/``PropertyQueryPort`` shape those files
use, joined onto one object so it can back all three at once, plus asserts
the NEW behavior: one folder, one index, partial-failure isolation, and the
incompleteness summary landing on the index's first screen.
"""

from __future__ import annotations

import json
from pathlib import Path

from server.orchestrator.tools import DEFAULT_RIG_CONTEXT_PATHS, build_toolset
from server.paperwork.bundle import (
    STATUS_GENERATED,
    STATUS_QUERY_FAILED,
    STATUS_UNWIRED,
    HandoverPack,
    build_handover_pack,
)
from server.prechk.inventory import FIXTURE_ROOT

_SEQUENCES_PATH = DEFAULT_RIG_CONTEXT_PATHS["sequences"]
_PRESET_POOLS_PATH = DEFAULT_RIG_CONTEXT_PATHS["preset_pools"]


class FakeConsolePort:
    """Fake StateQueryPort + PropertyQueryPort backed by dicts — the same
    shape ``test_paperwork_patch_sheet.FakeInventoryPort`` /
    ``test_paperwork_cue_sheet.FakeStatePort`` fake, joined so one port can
    back the patch sheet, cue sheet AND preset list at once."""

    def __init__(
        self, states: dict[str, dict], properties: dict[tuple[str, str], dict] | None = None
    ):
        self._states = states
        self._properties = properties or {}

    def query_state(self, path: str) -> dict:
        if path not in self._states:
            raise LookupError(f"unknown state path: {path}")
        return self._states[path]

    def query_property(self, path: str, property_name: str) -> dict:
        key = (path, property_name)
        if key not in self._properties:
            raise LookupError(f"unknown property: {key}")
        return self._properties[key]


def _prop(value: str) -> dict:
    return {"ok": True, "value": value}


def _snapshot(children: list[dict], **extra) -> dict:
    payload: dict[str, object] = {"children": children}
    payload.update(extra)
    return payload


def _complete_states(fixture_name: str = "Spot 1", cue_name: str = "Cyan Wash") -> dict[str, dict]:
    return {
        FIXTURE_ROOT: {
            "ok": True,
            "node": {"name": "Fixtures", "class": "Container", "childCount": 1},
            "children": [{"i": 1, "name": fixture_name}],
        },
        _SEQUENCES_PATH: _snapshot([{"i": 1, "name": "Main Show"}]),
        f"{_SEQUENCES_PATH}/1": _snapshot([{"i": 1, "name": cue_name}]),
        _PRESET_POOLS_PATH: _snapshot([{"i": 1, "name": "Dimmer"}]),
        f"{_PRESET_POOLS_PATH}/1": _snapshot([{"i": 1, "name": "Full"}]),
    }


def _complete_properties(fixture_name: str = "Spot 1") -> dict[tuple[str, str], dict]:
    return {
        (f"{FIXTURE_ROOT}/1", "Patch"): _prop("1.001"),
        (f"{FIXTURE_ROOT}/1", "FixtureType"): _prop("Robe MegaPointe"),
        (f"{FIXTURE_ROOT}/1", "Mode"): _prop("Standard"),
        (f"{FIXTURE_ROOT}/1", "Name"): _prop(fixture_name),
    }


class TestBuildHandoverPackHappyPath:
    def test_writes_five_files(self, tmp_path):
        port = FakeConsolePort(_complete_states(), _complete_properties())
        pack = build_handover_pack(port, port, directory=tmp_path)
        assert isinstance(pack, HandoverPack)
        for name in (
            "index.html",
            "patch_sheet.html",
            "cue_sheet.html",
            "preset_list.html",
            "magic_sheet.html",
        ):
            assert (tmp_path / name).is_file()

    def test_index_links_all_four_documents_by_relative_path(self, tmp_path):
        port = FakeConsolePort(_complete_states(), _complete_properties())
        pack = build_handover_pack(port, port, directory=tmp_path)
        index_html = pack.index_path.read_text(encoding="utf-8")
        assert 'href="patch_sheet.html"' in index_html
        assert 'href="cue_sheet.html"' in index_html
        assert 'href="preset_list.html"' in index_html
        assert 'href="magic_sheet.html"' in index_html
        # Relative, never absolute: the pack must open correctly from any
        # location it is copied/moved to as one folder.
        assert str(tmp_path) not in index_html

    def test_every_document_is_generated(self, tmp_path):
        port = FakeConsolePort(_complete_states(), _complete_properties())
        pack = build_handover_pack(port, port, directory=tmp_path)
        assert {doc.kind: doc.status for doc in pack.documents} == {
            "patch_sheet": STATUS_GENERATED,
            "cue_sheet": STATUS_GENERATED,
            "preset_list": STATUS_GENERATED,
            "magic_sheet": STATUS_GENERATED,
        }
        assert all(doc.path is not None and doc.path.is_file() for doc in pack.documents)

    def test_generated_at_is_a_utc_iso8601_timestamp(self, tmp_path):
        port = FakeConsolePort(_complete_states(), _complete_properties())
        pack = build_handover_pack(port, port, directory=tmp_path)
        assert pack.generated_at.endswith("Z")
        assert "T" in pack.generated_at


class TestBuildHandoverPackPartialFailure:
    def test_missing_property_port_degrades_only_the_patch_sheet(self, tmp_path):
        port = FakeConsolePort(_complete_states())
        pack = build_handover_pack(port, None, directory=tmp_path)
        by_kind = {doc.kind: doc for doc in pack.documents}
        assert by_kind["patch_sheet"].status == STATUS_UNWIRED
        assert by_kind["patch_sheet"].path is None
        assert by_kind["cue_sheet"].status == STATUS_GENERATED
        assert by_kind["preset_list"].status == STATUS_GENERATED
        assert not (tmp_path / "patch_sheet.html").exists()
        assert (tmp_path / "cue_sheet.html").is_file()
        assert (tmp_path / "preset_list.html").is_file()
        assert (tmp_path / "index.html").is_file()

    def test_unreadable_fixture_root_degrades_only_the_patch_sheet(self, tmp_path):
        states = _complete_states()
        states[FIXTURE_ROOT] = {"ok": False, "error": "no reply within 3.0s"}
        port = FakeConsolePort(states, _complete_properties())
        pack = build_handover_pack(port, port, directory=tmp_path)
        by_kind = {doc.kind: doc for doc in pack.documents}
        assert by_kind["patch_sheet"].status == STATUS_QUERY_FAILED
        assert by_kind["cue_sheet"].status == STATUS_GENERATED
        assert by_kind["preset_list"].status == STATUS_GENERATED

    def test_a_pool_the_console_never_answers_fails_only_that_document(self, tmp_path):
        states = _complete_states()
        del states[_SEQUENCES_PATH]  # the sequence pool never arrives
        port = FakeConsolePort(states, _complete_properties())
        pack = build_handover_pack(port, port, directory=tmp_path)
        by_kind = {doc.kind: doc for doc in pack.documents}
        assert by_kind["cue_sheet"].status == STATUS_QUERY_FAILED
        assert by_kind["cue_sheet"].detail is not None
        assert "console_unreachable" in by_kind["cue_sheet"].detail
        assert by_kind["patch_sheet"].status == STATUS_GENERATED
        assert by_kind["preset_list"].status == STATUS_GENERATED
        assert not (tmp_path / "cue_sheet.html").exists()
        assert (tmp_path / "patch_sheet.html").is_file()
        assert (tmp_path / "preset_list.html").is_file()

    def test_the_failure_reason_reaches_the_index(self, tmp_path):
        states = _complete_states()
        del states[_SEQUENCES_PATH]
        port = FakeConsolePort(states, _complete_properties())
        pack = build_handover_pack(port, port, directory=tmp_path)
        index_html = pack.index_path.read_text(encoding="utf-8")
        assert "console_unreachable" in index_html
        assert STATUS_QUERY_FAILED in index_html


class TestBuildHandoverPackIncompletenessSummary:
    def test_patch_sheet_incompleteness_reaches_the_index(self, tmp_path):
        states = _complete_states()
        # A short root snapshot: childCount claims 3, only 1 arrives.
        states[FIXTURE_ROOT] = {
            "ok": True,
            "node": {"name": "Fixtures", "class": "Container", "childCount": 3},
            "children": [{"i": 1, "name": "Spot 1"}],
        }
        port = FakeConsolePort(states, _complete_properties())
        pack = build_handover_pack(port, port, directory=tmp_path)
        index_html = pack.index_path.read_text(encoding="utf-8")
        assert "1/3건" in index_html
        assert "completeness: incomplete" in index_html

    def test_cue_sheet_truncation_reaches_the_index(self, tmp_path):
        states = _complete_states()
        states[_SEQUENCES_PATH] = _snapshot([{"i": 1, "name": "Main Show"}], truncated=True)
        port = FakeConsolePort(states, _complete_properties())
        pack = build_handover_pack(port, port, directory=tmp_path)
        index_html = pack.index_path.read_text(encoding="utf-8")
        assert "truncated=True" in index_html

    def test_a_fully_complete_pack_still_states_the_axes_explicitly(self, tmp_path):
        # Non-vacuity check for the two assertions above: a complete pack
        # still names truncated/drilldown_capped as False rather than
        # omitting the line, so a reader can tell "checked, clean" apart
        # from "never reported".
        port = FakeConsolePort(_complete_states(), _complete_properties())
        pack = build_handover_pack(port, port, directory=tmp_path)
        index_html = pack.index_path.read_text(encoding="utf-8")
        assert "truncated=False" in index_html
        assert "completeness: complete" in index_html


class TestBuildHandoverPackSelfContainedAndEscaped:
    def test_no_external_resource_references_in_any_document(self, tmp_path):
        port = FakeConsolePort(_complete_states(), _complete_properties())
        build_handover_pack(port, port, directory=tmp_path)
        for path in (tmp_path / name for name in ("index.html", "patch_sheet.html")):
            html = path.read_text(encoding="utf-8")
            assert "<link " not in html
            assert 'src="http' not in html

    def test_injected_fixture_name_is_escaped_not_stripped(self, tmp_path):
        payload = "<script>alert(1)</script>"
        port = FakeConsolePort(
            _complete_states(fixture_name=payload), _complete_properties(payload)
        )
        build_handover_pack(port, port, directory=tmp_path)
        patch_html = (tmp_path / "patch_sheet.html").read_text(encoding="utf-8")
        assert payload not in patch_html
        assert "&lt;script&gt;" in patch_html

    def test_injected_cue_name_is_escaped_not_stripped(self, tmp_path):
        payload = "<img src=x onerror=alert(1)>"
        port = FakeConsolePort(_complete_states(cue_name=payload), _complete_properties())
        build_handover_pack(port, port, directory=tmp_path)
        cue_html = (tmp_path / "cue_sheet.html").read_text(encoding="utf-8")
        assert payload not in cue_html


class TestBuildHandoverPackDeterministicFilenames:
    def test_rerunning_does_not_grow_the_directory(self, tmp_path):
        port = FakeConsolePort(_complete_states(), _complete_properties())
        build_handover_pack(port, port, directory=tmp_path)
        first = sorted(p.name for p in tmp_path.iterdir())
        build_handover_pack(port, port, directory=tmp_path)
        second = sorted(p.name for p in tmp_path.iterdir())
        assert (
            first
            == second
            == [
                "cue_sheet.html",
                "index.html",
                "magic_sheet.html",
                "patch_sheet.html",
                "preset_list.html",
            ]
        )


class _DummyExecutionPort:
    def execute(self, command: str):  # pragma: no cover - never called by this tool
        raise AssertionError("build_handover_pack must never call execution_port")


def _call(name: str) -> object:
    from server.llm.types import ToolCall

    return ToolCall(id="call-1", name=name, arguments={})


class TestBuildHandoverPackToolRegistration:
    """Wires build_handover_pack through build_toolset — the ④ requirement
    in the brief (TOOL_NAMES 18 -> 19). test_tools.py's own count assertion
    covers the closed-set invariant; this class covers that the handler
    actually dispatches and never touches the execution port."""

    def test_the_tool_is_registered(self):
        registry = build_toolset(
            execution_port=_DummyExecutionPort(), state_port=FakeConsolePort({})
        )
        names = [definition.name for definition in registry.definitions()]
        assert "build_handover_pack" in names

    def test_dispatch_writes_the_pack_and_returns_paths_never_html(self, tmp_path, monkeypatch):
        monkeypatch.setattr("server.paperwork.output.resolve_handover_dir", lambda: tmp_path)
        port = FakeConsolePort(_complete_states(), _complete_properties())
        registry = build_toolset(execution_port=_DummyExecutionPort(), state_port=port)
        execution = registry.dispatch(_call("build_handover_pack"))
        assert execution.result.is_error is False
        payload = json.loads(execution.result.content)
        assert Path(payload["index_path"]).is_file()
        assert "<html" not in json.dumps(payload)
        statuses = {doc["kind"]: doc["status"] for doc in payload["documents"]}
        assert statuses == {
            "patch_sheet": STATUS_GENERATED,
            "cue_sheet": STATUS_GENERATED,
            "preset_list": STATUS_GENERATED,
            "magic_sheet": STATUS_GENERATED,
        }

    def test_dispatch_never_calls_execution_port(self, tmp_path, monkeypatch):
        monkeypatch.setattr("server.paperwork.output.resolve_handover_dir", lambda: tmp_path)
        port = FakeConsolePort(_complete_states(), _complete_properties())
        registry = build_toolset(execution_port=_DummyExecutionPort(), state_port=port)
        # _DummyExecutionPort.execute raises if ever called — a clean
        # dispatch below is itself the assertion.
        execution = registry.dispatch(_call("build_handover_pack"))
        assert execution.result.is_error is False


class TestCountsAgreeingIsNotWholeness:
    """A patch sheet whose counts AGREE can still be incomplete — the root
    enumeration came back short and per-slot recovery filled the gap, or a
    whitelisted property failed to read. The index must not let a skimmer read
    "4/4건 관측" as "the whole rig", so it names both possible causes.
    """

    def _sheet(self, *, observed: int, declared: int, completeness: str) -> object:
        from server.paperwork.data import PatchSheet

        return PatchSheet(
            root=FIXTURE_ROOT,
            rows=(),
            child_count=declared,
            observed_count=observed,
            completeness=completeness,
        )

    def _lines(self, sheet) -> tuple[str, ...]:
        from server.paperwork.bundle import _incompleteness_lines
        from server.paperwork.data import PoolListing

        empty = PoolListing(path="x", pools=(), truncated=False, drilldown_capped=False)
        return _incompleteness_lines(sheet, empty, empty)

    def test_agreeing_counts_with_incomplete_verdict_name_the_two_causes(self):
        line = self._lines(self._sheet(observed=4, declared=4, completeness="incomplete"))[0]
        assert "4/4건 관측" in line
        assert "전량으로 볼 수 없다" in line
        assert "절단" in line and "판독" in line

    def test_a_complete_sheet_carries_no_such_warning(self):
        """NON-VACUITY CONTROL: without this the assertion above would also pass
        against a builder that appends the warning unconditionally."""
        line = self._lines(self._sheet(observed=4, declared=4, completeness="complete"))[0]
        assert "전량으로 볼 수 없다" not in line

    def test_short_counts_do_not_get_the_agreeing_counts_wording(self):
        """A 3/4 sheet already SHOWS its gap; the extra clause is for the case
        where the numbers alone hide it."""
        line = self._lines(self._sheet(observed=3, declared=4, completeness="incomplete"))[0]
        assert "3/4건 관측" in line
        assert "전량으로 볼 수 없다" not in line
