"""PRESERVE always-on gate (M7 — AC-OVERLAP-019).

The predecessor SPEC's PRESERVE gate was a ONE-OFF manual procedure, and this
repository runs no CI. A gate nobody re-runs protects nothing, so the boundaries
it named are re-asserted here on every suite run.

**This file owns the PRECHK base and nothing else owns it.** The precedent gate in
``test_songcue_bundle.py`` is anchored to a DIFFERENT base, and its protected
ranges are relative to that one. Mixing the two in one module makes a gate guard
the wrong lines while still passing: at the PRECHK base the precedent's
``(234, 238)`` covers the middle of a comment explaining the dedupe exception,
and ``(524, 569)`` starts thirteen lines ahead of the dedupe execution loop and
closes before its final ``failed = True``. The two constants differ by exactly
thirteen because ``tools.py`` grew by thirteen lines between the bases. Hence a
new file rather than an extension of the old one.

Every assertion here is paired with a non-vacuity guard. ``git diff --stat``
contributes NOTHING for a path that does not exist, so a single typo in the path
list would make this gate pass forever.

**NOT regression tests — this whole module is an INVARIANT GATE**
(``AC-OVERLAP-021`` ⑥). The reverse run confirms it: all of these pass against the
pre-change tree, because the boundaries they assert already held. Catching a fix
is a different job, done by the mutation batteries recorded per milestone. What
this file catches is a FUTURE edit crossing a boundary nobody re-checks, which is
the failure mode a one-off manual gate leaves open.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

#: The PRECHK run-phase base. NOT this SPEC's base: a diff taken from this SPEC's
#: own base is empty the moment the work is committed, which would disable the
#: gate entirely while leaving it green.
_PRECHK_BASE = "95687a0e0eba90b325daf76efbd0ac197e69e2fc"

#: This SPEC's base. Used for exactly ONE assertion -- see
#: :func:`test_the_predecessor_progress_log_is_untouched` for why it is the only
#: valid reference point there.
_OVERLAP_BASE = "85a4b2389003cb61b0ab72eb4aa8d6b2ff90b94a"

#: The ten paths the predecessor SPEC locked, inherited unchanged. Files and
#: directories are NOT separated into two lists: the split is derived
#: mechanically below, so revising this list cannot desynchronise a hand-written
#: count.
_PRESERVE_PATHS = (
    "server/looks/schema.py",
    "server/looks/loader.py",
    "server/looks/roles.py",
    "server/looks/resolver.py",
    "server/looks/instantiate.py",
    "server/looks/matching.py",
    "server/looks/library/",
    "server/web/preview.py",
    "console/lua/",
    "server/rulebook/assets/v2.4.2/",
)

_TOOLS_PATH = "server/orchestrator/tools.py"

#: Protected regions of ``tools.py``, PRECHK-base relative: the programmer-state
#: command tuple and the dedupe execution loop. Position blockade, NOT a
#: deletion count -- ``tools.py`` legitimately deletes one line since this base
#: (an import replaced by a block), so a "zero deletions" rule would fail on
#: arrival and teach the next reader to weaken the gate.
_TOOLS_PROTECTED_OLD_RANGES = ((247, 251), (537, 582))

_SAFETY_DIR = "server/safety/"

#: The safety chokepoint's measured state at this SPEC's start: two files, the
#: property-read addition the predecessor was granted. One deletion exists and it
#: is a docstring line; the TEXT is asserted, because a bare "at most one
#: deletion" lets a meaningful removal hide under the allowance.
_SAFETY_EXPECTED_DELETIONS = {
    "server/safety/console.py": 0,
    "server/safety/gate.py": 1,
}
_SAFETY_ALLOWED_DELETED_LINE = (
    '    """StateQueryPort implementation riding the gate-audited console link."""'
)

_HUNK_RE = re.compile(r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+\d+(?:,\d+)? @@")

_DESCOPE_LINE = "DESCOPE: ASSUMPTION-27"
_PRECHK_SPEC_DIR = ".moai/specs/SPEC-COPILOT-PRECHK-001/"
_PRECHK_PROGRESS = f"{_PRECHK_SPEC_DIR}progress.md"


def _git(*arguments: str) -> str:
    result = subprocess.run(  # noqa: S603
        ["git", *arguments],
        cwd=_REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def _preserve_diff_command() -> list[str]:
    return ["git", "diff", "--stat", f"{_PRECHK_BASE}..HEAD", "--", *_PRESERVE_PATHS]


def _numstat(base: str, *paths: str) -> dict[str, tuple[int, int]]:
    rows = {}
    for line in _git("diff", "--numstat", f"{base}..HEAD", "--", *paths).splitlines():
        added, deleted, path = line.split("\t", 2)
        rows[path] = (int(added), int(deleted))
    return rows


def _hunks(base: str, path: str) -> list[tuple[int, int]]:
    found = []
    for line in _git("diff", "--unified=0", f"{base}..HEAD", "--", path).splitlines():
        match = _HUNK_RE.match(line)
        if match is not None:
            count = match.group("old_count")
            found.append((int(match.group("old_start")), 1 if count is None else int(count)))
    return found


def _overlaps(old_start: int, old_count: int, protected_start: int, protected_end: int) -> bool:
    old_end = old_start + max(old_count, 1) - 1
    return old_start <= protected_end and protected_start <= old_end


class TestPreserveList:
    """AC-OVERLAP-019 ③ — the list is real before it is used."""

    def test_the_list_has_ten_entries(self):
        assert len(_PRESERVE_PATHS) == 10
        assert len(set(_PRESERVE_PATHS)) == 10

    def test_every_entry_exists_on_disk(self):
        missing = [path for path in _PRESERVE_PATHS if not (_REPO_ROOT / path).exists()]
        # A path that does not exist contributes no rows to `--stat`, so one typo
        # turns the gate below into a permanent pass.
        assert missing == []

    def test_the_file_and_directory_split_is_derived_not_written_down(self):
        directories = [path for path in _PRESERVE_PATHS if (_REPO_ROOT / path).is_dir()]
        files = [path for path in _PRESERVE_PATHS if (_REPO_ROOT / path).is_file()]
        # Derived from the list itself: a hand-kept count was wrong once already
        # (the plan-phase audit found "4 directories and 6 files" for a 3/7 split).
        assert len(directories) + len(files) == len(_PRESERVE_PATHS)
        assert len(directories) == 3
        assert len(files) == 7
        # And every directory entry ends with a separator, so `--` treats it as a
        # prefix rather than as a missing file.
        assert all(path.endswith("/") for path in directories)


class TestPreserveDiffIsEmpty:
    """AC-OVERLAP-019 ①② — the range is pinned, then the diff must be empty."""

    def test_the_gate_uses_the_predecessor_base_to_head_range(self):
        command = _preserve_diff_command()
        assert command[:4] == ["git", "diff", "--stat", f"{_PRECHK_BASE}..HEAD"]
        assert command[4] == "--"
        assert tuple(command[5:]) == _PRESERVE_PATHS
        # Explicitly NOT this SPEC's base: that range is empty right after the
        # work is committed, which disables the gate while keeping it green.
        assert _PRECHK_BASE != _OVERLAP_BASE
        assert f"{_OVERLAP_BASE}..HEAD" not in command

    def test_the_preserved_paths_are_unchanged(self):
        assert _PRESERVE_PATHS
        assert _git(*_preserve_diff_command()[1:]) == ""

    def test_the_same_command_detects_a_change_elsewhere(self):
        # Non-vacuity for the emptiness above: the command shape CAN report.
        assert _git("diff", "--stat", f"{_PRECHK_BASE}..HEAD", "--", "server/prechk/") != ""


class TestToolsProtectedRegions:
    """AC-OVERLAP-019 ④ — position blockade on the predecessor's base."""

    def test_no_hunk_crosses_a_protected_region(self):
        hunks = _hunks(_PRECHK_BASE, _TOOLS_PATH)
        assert hunks, "hunk을 하나도 읽지 못하면 교차 0건 판정이 공허하다"
        crossings = [
            (start, count, protected)
            for start, count in hunks
            for protected in _TOOLS_PROTECTED_OLD_RANGES
            if _overlaps(start, count, *protected)
        ]
        assert crossings == []

    def test_the_blockade_would_catch_a_planted_hunk(self):
        # Non-vacuity: the overlap predicate is not simply always false.
        for protected_start, protected_end in _TOOLS_PROTECTED_OLD_RANGES:
            assert _overlaps(protected_start, 1, protected_start, protected_end)
            assert _overlaps(protected_end, 1, protected_start, protected_end)
            assert not _overlaps(protected_end + 1, 1, protected_start, protected_end)

    def test_the_ranges_are_the_predecessor_base_values_not_the_precedent_file_s(self):
        """The two bases differ by thirteen lines; copying is the trap.

        The precedent file's ranges are ``(234, 238)`` and ``(524, 569)``. Using
        those numbers against THIS base guards a comment and stops thirteen lines
        short of the loop's final statement.
        """
        assert _TOOLS_PROTECTED_OLD_RANGES == ((247, 251), (537, 582))
        assert [start for start, _end in _TOOLS_PROTECTED_OLD_RANGES] == [234 + 13, 524 + 13]

    def test_a_deletion_count_rule_would_be_the_wrong_shape_here(self):
        """Why this is a POSITION blockade and not "zero deletions".

        ``tools.py`` deletes one line relative to this base -- an import statement
        replaced by a block. A deletion-count rule would fail on arrival, and the
        next reader would weaken the gate to make it pass.
        """
        added, deleted = _numstat(_PRECHK_BASE, _TOOLS_PATH)[_TOOLS_PATH]
        assert added >= 1
        assert deleted >= 1


class TestSafetyChokepointFileSet:
    """AC-OVERLAP-019 ⑤ — which files, and which deletions."""

    def test_exactly_the_two_expected_files_changed(self):
        rows = _numstat(_PRECHK_BASE, _SAFETY_DIR)
        assert set(rows) == set(_SAFETY_EXPECTED_DELETIONS)

    def test_the_deletion_counts_match(self):
        rows = _numstat(_PRECHK_BASE, _SAFETY_DIR)
        for path, expected in _SAFETY_EXPECTED_DELETIONS.items():
            assert rows[path][1] == expected, path

    def test_the_one_allowed_deletion_is_the_docstring_it_claims_to_be(self):
        """A bare "at most one deletion" lets a meaningful removal hide.

        So the deleted TEXT is asserted, not just the count.
        """
        deleted = [
            line[1:]
            for line in _git(
                "diff", "--unified=0", f"{_PRECHK_BASE}..HEAD", "--", _SAFETY_DIR
            ).splitlines()
            if line.startswith("-") and not line.startswith("---")
        ]
        assert deleted == [_SAFETY_ALLOWED_DELETED_LINE]
        # And it is a docstring STRUCTURALLY, not just by matching a string that
        # happens to be one. Relaxing the exact-text expectation to a count still
        # leaves this standing, so an unknown meaningful deletion is caught even
        # then -- which is the invariant, the text being merely today's instance.
        assert deleted[0].strip().startswith('"""')
        assert deleted[0].strip().endswith('"""')

    def test_the_docstring_rule_rejects_a_meaningful_deletion(self):
        # Non-vacuity for the structural rule above: it is not always true.
        for planted in (
            "        failed = True",
            "    def query_state(self, path: str) -> dict:",
            "        return self._gate._query_state(path)",
        ):
            assert not planted.strip().startswith('"""')

    def test_this_spec_changed_nothing_under_the_chokepoint(self):
        # The two files above are the PREDECESSOR's granted exception. This SPEC
        # reads only `state`, which the chokepoint already exposed, so it needs no
        # opening of its own.
        assert _git("diff", "--stat", f"{_OVERLAP_BASE}..HEAD", "--", _SAFETY_DIR) == ""


class TestPrecedentGateFileIsNotExtended:
    """AC-OVERLAP-019 ⑥ — one base per module."""

    def test_the_precedent_file_carries_no_change_from_this_spec(self):
        rows = _numstat(_OVERLAP_BASE, "server/tests/test_songcue_bundle.py")
        # Zero rows, not "one changed line": every edit this SPEC made to
        # `tools.py` landed inside a hunk region the predecessor had already
        # opened, so the OLD-side boundaries the tripwire snapshots did not move.
        # The tripwire's real invariant -- the protected-range assertion -- keeps
        # holding, and it is asserted in the precedent file on its own base.
        assert rows == {}

    def test_this_file_owns_the_predecessor_base_alone(self):
        """Neither module may hold the other's base.

        The precedent's SHA is READ from its own source rather than retyped here:
        retyping it would both invite drift and put the string this test forbids
        into the very file it is checking.
        """
        precedent = (_REPO_ROOT / "server/tests/test_songcue_bundle.py").read_text(encoding="utf-8")
        assert _PRECHK_BASE not in precedent
        found = re.search(r'_RUN_PHASE_BASE = "([0-9a-f]{40})"', precedent)
        # Non-vacuity: the precedent file really does pin a base -- a different one.
        assert found is not None
        precedent_base = found.group(1)
        assert precedent_base != _PRECHK_BASE
        assert precedent_base != _OVERLAP_BASE
        module_strings = [
            value
            for name, value in globals().items()
            if isinstance(value, str) and not name.startswith("__")
        ]
        assert module_strings, "모듈 상수를 모으지 못하면 이 단정이 공허하다"
        assert precedent_base not in module_strings


class TestPredecessorSpecDocuments:
    """AC-OVERLAP-019 ⑧ — the one assertion that uses THIS SPEC's base."""

    def test_the_predecessor_spec_documents_are_untouched(self):
        assert _git("diff", "--stat", f"{_OVERLAP_BASE}..HEAD", "--", _PRECHK_SPEC_DIR) == ""

    def test_the_predecessor_base_would_be_the_wrong_reference_here(self):
        """Why this single item uses a different base from the rest of the file.

        The predecessor's six SPEC documents were WRITTEN AFTER the base the
        PRESERVE gate uses, so a diff from there carries their entire initial
        authoring and can never be empty. This SPEC's base is the predecessor's
        last documentation commit, so changes after it are exactly what this SPEC
        touched.
        """
        from_predecessor_base = _git(
            "diff", "--numstat", f"{_PRECHK_BASE}..HEAD", "--", _PRECHK_SPEC_DIR
        )
        assert from_predecessor_base != ""
        assert len(from_predecessor_base.splitlines()) >= 2

    def test_the_descope_line_is_still_exactly_one(self):
        text = (_REPO_ROOT / _PRECHK_PROGRESS).read_text(encoding="utf-8")
        hits = [line for line in text.splitlines() if line.startswith(_DESCOPE_LINE)]
        assert len(hits) == 1


class TestTouchedFilesPassLint:
    """AC-OVERLAP-019 ⑨ — on the files this SPEC touched, derived not listed."""

    def _touched(self) -> list[str]:
        return [
            path
            for path in _git("diff", "--name-only", f"{_OVERLAP_BASE}..HEAD", "--", "*.py")
            .strip()
            .splitlines()
            if (_REPO_ROOT / path).is_file()
        ]

    def test_the_touched_set_is_not_empty(self):
        touched = self._touched()
        assert touched, "손댄 파일이 0건이면 아래 두 검사가 공허하다"
        assert all(path.endswith(".py") for path in touched)

    def test_ruff_check_passes_on_them(self):
        finished = subprocess.run(  # noqa: S603
            ["uv", "run", "ruff", "check", *self._touched()],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert finished.returncode == 0, finished.stdout + finished.stderr

    def test_ruff_format_reports_no_change(self):
        finished = subprocess.run(  # noqa: S603
            ["uv", "run", "ruff", "format", "--check", *self._touched()],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert finished.returncode == 0, finished.stdout + finished.stderr
