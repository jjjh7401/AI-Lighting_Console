"""Single-chokepoint architecture test ① (M4 — REQ-MVP-029, AC-MVP-019 ①).

Static import-boundary scan over the WHOLE server tree: only the safety gate
package may reach the OSC send surface (``server.bridge`` / ``pythonosc``).

Named exemptions: the former ``server/tools/osc_smoke.py`` and
``server/tools/responder_roundtrip.py`` operator diagnostics were deleted as
dead code (never imported by the running app), so their exemptions went with
them. The exemption stays file-exact: any module touching the bridge outside
the allowed prefixes fails this test.

``server/preshow/osc_check.py`` (SPEC-COPILOT-PRESHOW-001) is the one remaining
exemption: a pre-show diagnostic that reuses the ping/state round-trip
pattern. It never sends the ``exec``
verb, so it never executes an end-user MA3 command outside gate screening —
only liveness (``ping``) and read-only object-tree queries (``state``).
"""

from __future__ import annotations

import re
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SERVER_DIR.parent

_IMPORT_LINE = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)", re.MULTILINE)

# Directories allowed to import the OSC send surface.
_ALLOWED_PREFIXES = (
    "server/bridge/",  # the surface itself
    "server/safety/",  # the gate — the ONLY production caller (REQ-MVP-029)
    "server/tests/",  # test code
)

# File-exact operator-utility exemptions (see module docstring).
_NAMED_TOOL_EXEMPTIONS = frozenset(
    {
        "server/preshow/osc_check.py",
    }
)

_FORBIDDEN_MODULE_PREFIXES = ("server.bridge", "pythonosc")


def _imports(path: Path) -> list[str]:
    return _IMPORT_LINE.findall(path.read_text(encoding="utf-8"))


class TestSingleChokepointImportBoundary:
    def test_only_the_safety_gate_reaches_the_osc_send_surface(self):
        violations: list[str] = []
        for source in sorted(SERVER_DIR.rglob("*.py")):
            rel = source.relative_to(PROJECT_ROOT).as_posix()
            if rel.startswith(_ALLOWED_PREFIXES) or rel in _NAMED_TOOL_EXEMPTIONS:
                continue
            for module in _imports(source):
                if module.startswith(_FORBIDDEN_MODULE_PREFIXES):
                    violations.append(f"{rel} imports {module}")
        assert violations == [], (
            "REQ-MVP-029 single-chokepoint violation — modules outside "
            f"server/safety reach the OSC send surface: {violations}"
        )

    def test_the_gate_console_link_is_the_production_bridge_caller(self):
        # Positive control: the boundary is real, not vacuously satisfied.
        console_module = SERVER_DIR / "safety" / "console.py"
        modules = _imports(console_module)
        assert any(m.startswith("server.bridge") for m in modules)

    def test_named_exemptions_still_exist_as_operator_tools(self):
        # If an exempted tool is deleted/renamed, drop it from the exemption
        # list — a stale exemption is a dormant bypass hole.
        for rel in _NAMED_TOOL_EXEMPTIONS:
            assert (PROJECT_ROOT / rel).is_file(), f"stale exemption: {rel}"

    def test_orchestrator_and_llm_packages_have_zero_bridge_imports(self):
        # Explicit spot-check of the packages the model-side code lives in.
        for package in ("orchestrator", "llm", "rulebook"):
            for source in (SERVER_DIR / package).glob("*.py"):
                for module in _imports(source):
                    assert not module.startswith(_FORBIDDEN_MODULE_PREFIXES), (
                        f"server/{package}/{source.name} imports {module}"
                    )
