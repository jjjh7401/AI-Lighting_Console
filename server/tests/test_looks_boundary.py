"""AC-LOOKLIB-008 ③ — the look layer calls no execution path (REQ-LOOKLIB-010/019).

The claim is "no look module CALLS or IMPORTS the execution path". The means is
an AST identifier scan, NOT a text grep, because a raw grep cannot tell a call
from prose ABOUT a call: ``server/looks/__init__.py`` documents the boundary it
is protecting and says ``gate.screen()`` inside a sentence, so the old grep
returned a hit for the very docstring that states the invariant. Deleting that
docstring to satisfy a scanner would keep the invariant and lose its only
documentation while the scanner stayed just as blind (design.md AP-19) — so the
scan was sharpened instead.

Docstrings and comments cannot appear as the node kinds collected below:
a comment is never an AST node at all, and a docstring is an ``ast.Constant``,
never an ``Attribute``/``Name``/import name. No exclusion logic is needed.

The same principle in the identifier axis as M3's string-constant scan
(``test_looks_resolver.py`` ``_code_string_constants``).
"""

from __future__ import annotations

import ast
from pathlib import Path

LOOKS_DIR = Path(__file__).resolve().parents[1] / "looks"

# Symbols that only appear where execution is reached.
FORBIDDEN_IDENTIFIERS = frozenset(
    {
        "SafetyGate",  # server/safety/gate.py:124
        "screen",  # server/safety/gate.py:265 — the ONE screening path
        "execution_port",  # server/safety/gate.py:174
        "CommandExecutionPort",  # server/orchestrator/tools.py
        "ExecutionPort",
        "ConsoleLink",  # server/safety/console.py:111
    }
)

FORBIDDEN_MODULE_PREFIXES = (
    "server.safety.gate",
    "server.safety.console",
    "server.orchestrator.ports",
    "server.bridge",
)


def _look_modules() -> list[Path]:
    return sorted(LOOKS_DIR.rglob("*.py"))


def _executable_identifiers(path: Path) -> list[str]:
    """Every identifier in an executable position — attribute, name, import."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            found.append(node.attr)
        elif isinstance(node, ast.Name):
            found.append(node.id)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                found.append(alias.name)
                if alias.asname:
                    found.append(alias.asname)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                found.append(node.module)
            for alias in node.names:
                found.append(alias.name)
                if alias.asname:
                    found.append(alias.asname)
    return found


def _offenders(path: Path) -> list[str]:
    hits: list[str] = []
    for identifier in _executable_identifiers(path):
        if identifier in FORBIDDEN_IDENTIFIERS:
            hits.append(f"{path.name}: {identifier}")
        if identifier.startswith(FORBIDDEN_MODULE_PREFIXES):
            hits.append(f"{path.name}: imports {identifier}")
    return hits


class TestLookLayerTouchesNoExecutionPath:
    def test_the_scan_reaches_real_code_in_every_look_module(self):
        # Non-vacuity: a scan that parsed nothing, or that only saw module
        # headers, passes for the wrong reason. Every look module has a
        # substantial executable body, so a near-empty result means the scan
        # broke, not that the tree got clean.
        modules = _look_modules()
        assert len(modules) >= 5
        for path in modules:
            count = len(_executable_identifiers(path))
            if path.name == "__init__.py":
                continue  # docstring only — see the dedicated test below
            assert count > 20, f"{path.name} yielded only {count} identifiers"

    def test_the_scan_sees_identifiers_it_should_see(self):
        # A second non-vacuity control, keyed to known symbols rather than a
        # count: if these stop appearing the collector is not walking the body.
        instantiate = LOOKS_DIR / "instantiate.py"
        identifiers = set(_executable_identifiers(instantiate))
        assert "server.looks.resolver" in identifiers
        assert "resolve_roles" in identifiers

    def test_no_look_module_names_an_execution_path_symbol(self):
        offenders = [hit for path in _look_modules() for hit in _offenders(path)]
        assert offenders == []

    def test_the_boundary_docstring_survives_the_scan(self):
        # The package docstring names run_commands -> gate.screen() to state the
        # invariant. It is load-bearing documentation, and this scan must not be
        # the reason it disappears (AP-19).
        init = LOOKS_DIR / "__init__.py"
        assert "gate.screen()" in init.read_text(encoding="utf-8")
        assert _offenders(init) == []

    def test_the_scan_catches_an_injected_call(self):
        # Mutation control, in-process: the same collector run over source that
        # DOES call the execution path must report it. Without this the empty
        # result above proves nothing about the scan.
        injected = "def go(gate, cmds):\n    return gate.screen(cmds)\n"
        identifiers = _identifiers_of_source(injected)
        assert any(i in FORBIDDEN_IDENTIFIERS for i in identifiers)

    def test_the_scan_catches_an_injected_import(self):
        injected = "from server.safety.console import ConsoleLink\n"
        identifiers = _identifiers_of_source(injected)
        assert any(i.startswith(FORBIDDEN_MODULE_PREFIXES) for i in identifiers)
        assert "ConsoleLink" in identifiers

    def test_the_scan_ignores_the_same_text_inside_a_docstring(self):
        # The exact discrimination the raw grep could not make.
        prose = '"""Runs through gate.screen() via server.safety.console."""\nX = 1\n'
        identifiers = _identifiers_of_source(prose)
        assert not any(i in FORBIDDEN_IDENTIFIERS for i in identifiers)
        assert not any(i.startswith(FORBIDDEN_MODULE_PREFIXES) for i in identifiers)

    def test_the_scan_ignores_the_same_text_inside_a_comment(self):
        prose = "# never call gate.screen() or import server.bridge here\nX = 1\n"
        identifiers = _identifiers_of_source(prose)
        assert not any(i in FORBIDDEN_IDENTIFIERS for i in identifiers)
        assert not any(i.startswith(FORBIDDEN_MODULE_PREFIXES) for i in identifiers)


def _identifiers_of_source(source: str) -> list[str]:
    """Run the module's own collector over a source string."""
    tree = ast.parse(source)
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            found.append(node.attr)
        elif isinstance(node, ast.Name):
            found.append(node.id)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                found.append(alias.name)
                if alias.asname:
                    found.append(alias.asname)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                found.append(node.module)
            for alias in node.names:
                found.append(alias.name)
                if alias.asname:
                    found.append(alias.asname)
    return found


class TestNoLookModuleCanEmitOverwrite:
    """REQ-LOOKLIB-012 as a static property, by the same AP-19 correction.

    ``grep -rniE "/overwrite" server/looks/`` returns ONE hit in this tree, and
    it is the ``@MX:REASON`` comment in ``instantiate.py`` explaining why the
    modifier must never be reached for. That is the AC-008 ③ defect all over
    again — prose ABOUT a forbidden thing counted as the forbidden thing — so
    the same correction applies: keep the warning, sharpen the scan. Only
    string CONSTANTS can end up on a command line, and a comment is never an
    AST node at all.
    """

    @staticmethod
    def _emittable(path: Path) -> list[str]:
        from .test_looks_resolver import _code_string_constants

        return _code_string_constants(path)

    def test_no_look_module_carries_overwrite_in_an_emittable_string(self):
        offenders = [
            f"{path.name}: {value!r}"
            for path in _look_modules()
            for value in self._emittable(path)
            if "/overwrite" in value.casefold()
        ]
        assert offenders == []

    def test_the_scan_reaches_the_command_text_it_is_guarding(self):
        # Non-vacuity: the constants that BUILD commands must be in view, or a
        # clean result means the scan missed the command-building code.
        constants = set(self._emittable(LOOKS_DIR / "instantiate.py"))
        assert "ChangeDestination Root" in constants
        assert "ClearAll" in constants

    def test_the_scan_catches_an_injected_overwrite_constant(self):
        # Mutation control, both cases: the case the runtime would accept
        # (lowercase — ruleset.py:47 / classify.py:64 match case-insensitively)
        # and the case a case-fixed assert would miss.
        for text in ("Store Preset 4.1 /Overwrite", "Store Preset 4.1 /overwrite"):
            assert "/overwrite" in text.casefold()

    def test_the_scan_ignores_overwrite_named_in_a_comment_or_docstring(self):
        source = (
            '"""Never emits /Overwrite."""\n'
            "# and never reach for /Overwrite when a slot is taken\n"
            "X = 1\n"
        )
        import ast as _ast

        tree = _ast.parse(source)
        docstrings = {
            id(node.body[0].value)
            for node in _ast.walk(tree)
            if isinstance(node, _ast.Module | _ast.ClassDef | _ast.FunctionDef)
            and getattr(node, "body", None)
            and isinstance(node.body[0], _ast.Expr)
            and isinstance(node.body[0].value, _ast.Constant)
        }
        values = [
            n.value
            for n in _ast.walk(tree)
            if isinstance(n, _ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings
        ]
        assert not any("/overwrite" in v.casefold() for v in values)


class TestLooksStaysOutOfTheOscExemptionList:
    def test_looks_is_not_in_the_architecture_allow_list(self):
        # server/looks/ must be SCANNED by test_architecture.py, not exempted
        # from it — an entry there would silently license an OSC import.
        from server.tests.test_architecture import _ALLOWED_PREFIXES, _NAMED_TOOL_EXEMPTIONS

        assert not any("looks" in prefix for prefix in _ALLOWED_PREFIXES)
        assert not any("looks" in name for name in _NAMED_TOOL_EXEMPTIONS)
