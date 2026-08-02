"""Chokepoint boundary test (SPEC-COPILOT-PAPERWORK-001).

``server/paperwork`` is query-only paperwork generation: it must never import
the OSC send surface or any execution port. Mirrors the same import-sweep
discipline ``server/prechk`` and ``server/web`` pin for themselves.
"""

from __future__ import annotations

import ast
from pathlib import Path

PAPERWORK_DIR = Path(__file__).resolve().parents[1] / "paperwork"

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


class TestPaperworkNeverTouchesExecution:
    def test_no_module_imports_the_bridge_or_osc_layer(self):
        offenders = []
        for path in sorted(PAPERWORK_DIR.glob("*.py")):
            modules = _imported_modules(path)
            for module in modules:
                if any(module.startswith(prefix) for prefix in _FORBIDDEN_MODULE_PREFIXES):
                    offenders.append((path.name, module))
        assert offenders == []

    def test_no_module_imports_an_execution_capable_port(self):
        offenders = []
        for path in sorted(PAPERWORK_DIR.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            for name in _FORBIDDEN_NAMES:
                if name in text:
                    offenders.append((path.name, name))
        assert offenders == []
