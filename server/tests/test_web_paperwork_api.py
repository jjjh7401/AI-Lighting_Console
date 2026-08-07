"""Paperwork REST API (W3 — P0 UI exposure).

Mirrors ``test_web_provision_api.py``/``test_web_settings_api.py``'s
router-isolation style (a bare FastAPI app carrying only this one router),
plus the fake-port shapes ``test_paperwork_patch_sheet.py`` /
``test_paperwork_cue_sheet.py`` already established (a dict-backed
StateQueryPort/PropertyQueryPort double, never a real console).
"""

from __future__ import annotations

import ast
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.orchestrator.tools import DEFAULT_RIG_CONTEXT_PATHS
from server.prechk.inventory import FIXTURE_ROOT
from server.web.paperwork_api import PaperworkDeps, build_paperwork_router

_SEQUENCES_PATH = DEFAULT_RIG_CONTEXT_PATHS["sequences"]
_PRESET_POOLS_PATH = DEFAULT_RIG_CONTEXT_PATHS["preset_pools"]


class FakeInventoryPort:
    """Fake StateQueryPort + PropertyQueryPort backed by dicts (same shape
    ``test_paperwork_patch_sheet.py``'s ``FakeInventoryPort`` uses)."""

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


class FakeStatePortOnly:
    """``query_state`` only — no ``query_property``. Proves the
    ``capability_unavailable`` path (property_port unwired) is a DISTINCT
    failure from ``query_failed`` (console unreachable) — brief item ③/④."""

    def __init__(self, states: dict[str, dict]):
        self._states = states

    def query_state(self, path: str) -> dict:
        if path not in self._states:
            raise LookupError(f"unknown state path: {path}")
        return self._states[path]


def _prop(value: str) -> dict:
    return {"ok": True, "value": value}


def _snapshot(entries: list[tuple[int | None, str]]) -> dict:
    children: list[dict[str, object]] = []
    for number, name in entries:
        child: dict[str, object] = {"name": name}
        if number is not None:
            child["i"] = number
        children.append(child)
    return {"children": children}


def _full_states() -> dict[str, dict]:
    return {
        FIXTURE_ROOT: {
            "ok": True,
            "node": {"name": "Fixtures", "class": "Container", "childCount": 1},
            "children": [{"i": 1, "name": "Spot 1"}],
        },
        _SEQUENCES_PATH: _snapshot([(1, "Main Show")]),
        f"{_SEQUENCES_PATH}/1": _snapshot([(1, "Cyan Wash")]),
        _PRESET_POOLS_PATH: _snapshot([(1, "Colors")]),
        f"{_PRESET_POOLS_PATH}/1": _snapshot([(1, "Deep Blue")]),
    }


def _full_properties() -> dict[tuple[str, str], dict]:
    return {
        (f"{FIXTURE_ROOT}/1", "Patch"): _prop("1.001"),
        (f"{FIXTURE_ROOT}/1", "FixtureType"): _prop("Robe MegaPointe"),
        (f"{FIXTURE_ROOT}/1", "Mode"): _prop("Standard"),
        (f"{FIXTURE_ROOT}/1", "Name"): _prop("Spot 1"),
    }


def _client(deps: PaperworkDeps) -> TestClient:
    app = FastAPI()
    app.include_router(build_paperwork_router(deps))
    return TestClient(app)


def _isolate_output_dir(monkeypatch, tmp_path: Path) -> None:
    # Same idiom test_paperwork_output.py / test_tools.py already use — never
    # let a test write into the repo's real server/paperwork_output/.
    monkeypatch.setattr("server.paperwork.output.resolve_paperwork_dir", lambda: tmp_path)


class TestListEndpoint:
    def test_reports_the_three_kinds_with_no_last_result_before_any_generation(
        self, tmp_path, monkeypatch
    ):
        _isolate_output_dir(monkeypatch, tmp_path)
        deps = PaperworkDeps(state_port=FakeInventoryPort(_full_states(), _full_properties()))
        body = _client(deps).get("/api/paperwork").json()
        assert body["kinds"] == ["patch_sheet", "cue_sheet", "preset_list"]
        assert body["last_results"] == {
            "patch_sheet": None,
            "cue_sheet": None,
            "preset_list": None,
        }

    def test_a_last_result_appears_after_a_successful_generation(self, tmp_path, monkeypatch):
        _isolate_output_dir(monkeypatch, tmp_path)
        deps = PaperworkDeps(state_port=FakeInventoryPort(_full_states(), _full_properties()))
        client = _client(deps)
        client.post("/api/paperwork/cue_sheet")
        body = client.get("/api/paperwork").json()
        assert body["last_results"]["cue_sheet"] is not None
        assert body["last_results"]["cue_sheet"]["path"] == str(tmp_path / "cue_sheet.html")
        assert body["last_results"]["patch_sheet"] is None


class TestGenerateSuccess:
    # ① 3종 정상 생성 ---------------------------------------------------------

    def test_patch_sheet_generates_and_writes_a_file(self, tmp_path, monkeypatch):
        _isolate_output_dir(monkeypatch, tmp_path)
        deps = PaperworkDeps(state_port=FakeInventoryPort(_full_states(), _full_properties()))
        response = _client(deps).post("/api/paperwork/patch_sheet")
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["kind"] == "patch_sheet"
        assert body["path"] == str(tmp_path / "patch_sheet.html")
        assert body["fixture_count"] == 1
        assert body["child_count"] == 1
        assert (tmp_path / "patch_sheet.html").is_file()

    def test_cue_sheet_generates_and_writes_a_file(self, tmp_path, monkeypatch):
        _isolate_output_dir(monkeypatch, tmp_path)
        deps = PaperworkDeps(state_port=FakeInventoryPort(_full_states()))
        response = _client(deps).post("/api/paperwork/cue_sheet")
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["sequence_count"] == 1
        assert body["cue_count"] == 1
        assert body["truncated"] is False
        assert (tmp_path / "cue_sheet.html").is_file()

    def test_preset_list_generates_and_writes_a_file(self, tmp_path, monkeypatch):
        _isolate_output_dir(monkeypatch, tmp_path)
        deps = PaperworkDeps(state_port=FakeInventoryPort(_full_states()))
        response = _client(deps).post("/api/paperwork/preset_list")
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["pool_count"] == 1
        assert body["preset_count"] == 1
        assert (tmp_path / "preset_list.html").is_file()

    def test_a_second_generation_overwrites_the_same_deterministic_filename(
        self, tmp_path, monkeypatch
    ):
        _isolate_output_dir(monkeypatch, tmp_path)
        deps = PaperworkDeps(state_port=FakeInventoryPort(_full_states()))
        client = _client(deps)
        client.post("/api/paperwork/preset_list")
        client.post("/api/paperwork/preset_list")
        assert len(list(tmp_path.glob("preset_list*"))) == 1


class TestUnknownKind:
    # ② 미지 kind 400 ---------------------------------------------------------

    def test_an_unrecognised_kind_is_a_400_and_never_touches_disk(self, tmp_path, monkeypatch):
        _isolate_output_dir(monkeypatch, tmp_path)
        deps = PaperworkDeps(state_port=FakeInventoryPort(_full_states(), _full_properties()))
        response = _client(deps).post("/api/paperwork/handover")
        assert response.status_code == 400
        assert response.json()["detail"]["error"] == "unknown_kind"
        assert list(tmp_path.glob("*")) == []

    def test_a_path_traversal_style_kind_is_also_a_400_never_a_write(self, tmp_path, monkeypatch):
        _isolate_output_dir(monkeypatch, tmp_path)
        deps = PaperworkDeps(state_port=FakeInventoryPort(_full_states(), _full_properties()))
        response = _client(deps).post("/api/paperwork/..%2F..%2Fetc%2Fpasswd")
        assert response.status_code in (400, 404)
        assert list(tmp_path.glob("*")) == []


class TestCapabilityUnavailableVsQueryFailed:
    # ③ property_port 미배선 시 "빈 시트"가 아니라 명시적 오류 -----------------

    def test_missing_property_port_is_a_distinct_capability_error_not_an_empty_sheet(
        self, tmp_path, monkeypatch
    ):
        _isolate_output_dir(monkeypatch, tmp_path)
        deps = PaperworkDeps(state_port=FakeStatePortOnly(_full_states()))
        response = _client(deps).post("/api/paperwork/patch_sheet")
        assert response.status_code == 503
        detail = response.json()["detail"]
        assert detail["error"] == "capability_unavailable"
        assert list(tmp_path.glob("*")) == []

    # ④ 콘솔 도달 실패와 ③이 다른 메시지 --------------------------------------

    def test_console_unreachable_is_a_different_error_from_capability_unavailable(
        self, tmp_path, monkeypatch
    ):
        _isolate_output_dir(monkeypatch, tmp_path)
        # query_property IS wired (satisfies the capability), but the root
        # itself reports enumeration failure — a query failure, not a
        # missing capability. Same shape test_paperwork_patch_sheet.py's own
        # "unreadable root" test uses (ok: False), not a raised exception —
        # server/prechk/inventory.py's _root_payload only wraps THIS shape
        # into InventoryReadError.
        unreadable_root = {FIXTURE_ROOT: {"ok": False, "error": "path segment not found"}}
        deps = PaperworkDeps(state_port=FakeInventoryPort(unreadable_root, _full_properties()))
        response = _client(deps).post("/api/paperwork/patch_sheet")
        assert response.status_code == 502
        detail = response.json()["detail"]
        assert detail["error"] == "query_failed"
        assert detail["message"] != (
            "property reads are not wired — the paperwork API needs a "
            "property_port (or a state_port that also implements "
            "query_property)"
        )

    def test_cue_sheet_console_unreachable_reports_query_failed_with_reason(
        self, tmp_path, monkeypatch
    ):
        _isolate_output_dir(monkeypatch, tmp_path)
        deps = PaperworkDeps(state_port=FakeInventoryPort({}))
        response = _client(deps).post("/api/paperwork/cue_sheet")
        assert response.status_code == 502
        detail = response.json()["detail"]
        assert detail["error"] == "query_failed"
        assert detail["reason"] == "console_unreachable"
        assert list(tmp_path.glob("*")) == []

    def test_preset_list_console_unreachable_reports_query_failed_with_reason(
        self, tmp_path, monkeypatch
    ):
        _isolate_output_dir(monkeypatch, tmp_path)
        deps = PaperworkDeps(state_port=FakeInventoryPort({}))
        response = _client(deps).post("/api/paperwork/preset_list")
        assert response.status_code == 502
        detail = response.json()["detail"]
        assert detail["error"] == "query_failed"
        assert detail["reason"] == "console_unreachable"


class TestPropertyPortAutoAdoption:
    def test_a_state_port_that_also_implements_query_property_needs_no_explicit_wiring(
        self, tmp_path, monkeypatch
    ):
        # Mirrors build_toolset's own fallback (server/orchestrator/tools.py):
        # property_port is adopted from state_port when unset, so production
        # wiring (deps.gate.state_port, which implements both) needs no extra
        # plumbing.
        _isolate_output_dir(monkeypatch, tmp_path)
        deps = PaperworkDeps(state_port=FakeInventoryPort(_full_states(), _full_properties()))
        assert deps.property_port is None
        response = _client(deps).post("/api/paperwork/patch_sheet")
        assert response.status_code == 200


# ⑤ 라우터 소스에 OSC/bridge import 0건 (비공허성 포함) ------------------------

_PAPERWORK_API_PATH = Path(__file__).resolve().parents[1] / "web" / "paperwork_api.py"
_FORBIDDEN_MODULE_PREFIXES = ("server.bridge", "pythonosc")
_FORBIDDEN_NAMES = ("CommandExecutionPort", "BundleGate")


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


class TestPaperworkApiNeverTouchesExecution:
    def test_no_bridge_or_osc_import(self):
        modules = _imported_modules(_PAPERWORK_API_PATH)
        offenders = [
            module
            for module in modules
            if any(module.startswith(prefix) for prefix in _FORBIDDEN_MODULE_PREFIXES)
        ]
        assert offenders == []

    def test_no_execution_capable_port_name(self):
        text = _PAPERWORK_API_PATH.read_text(encoding="utf-8")
        offenders = [name for name in _FORBIDDEN_NAMES if name in text]
        assert offenders == []

    def test_the_scan_is_non_vacuous(self):
        # Proves the scan above actually read real content, not an empty or
        # unreadable file — a scan that always passes on zero imports would
        # be a silent no-op guard, not a real one.
        modules = _imported_modules(_PAPERWORK_API_PATH)
        assert "fastapi" in modules
        assert any(module.startswith("server.paperwork") for module in modules)
