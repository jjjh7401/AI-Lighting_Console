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

#: 2026-08-03 granted exception — SPEC-COPILOT-SPATIAL-001 M3 adds ONE rulebook
#: asset, ``32_spatial_design.md`` (user-approved). The rulebook prefix is a
#: deliberately EXTENSIBLE asset set (00 -> 10 -> 20 -> 30 -> 31 -> 32), so a
#: whole-directory lock would freeze every future rulebook milestone while
#: reading as a preserved boundary. The boundary that actually matters is that
#: the five EXISTING assets stay byte-identical, and that is what is now
#: asserted — by naming them, so a modification to any one of them still fails.
#:
#: Additions are not blanket-permitted either: ``test_the_rulebook_additions_are_
#: only_the_granted_asset`` below pins the added path by name and requires zero
#: deletions across the directory. Another new file, or one byte removed from an
#: old one, still fails the gate. ``server/rulebook/assets/v2.4.2/`` therefore
#: stays in the tuple above as the documented boundary and is swapped for its
#: named members in the diff, the same way ``server/looks/library/`` is.
_RULEBOOK_DIR = "server/rulebook/assets/v2.4.2/"
_RULEBOOK_LOCKED_ASSETS = (
    "server/rulebook/assets/v2.4.2/00_grammar.md",
    "server/rulebook/assets/v2.4.2/10_object_model.md",
    "server/rulebook/assets/v2.4.2/20_korean_terms.md",
    "server/rulebook/assets/v2.4.2/30_plugin_patterns.md",
    "server/rulebook/assets/v2.4.2/31_choreography_patterns.md",
)
_RULEBOOK_GRANTED_ADDITION = "server/rulebook/assets/v2.4.2/32_spatial_design.md"

#: 2026-08-02 granted exception — the upstream vocabulary extension
#: (docs/proposals/2026-08-02-upstream-vocabulary-extension-proposal.md §6,
#: user-approved, lightweight track). ``server/looks/library/`` stays a locked
#: boundary, but this ONE measured diff is sanctioned: 파란 mirrored beside 푸른
#: in exactly these alias/mood lines. The grant is pinned by EXACT line text
#: (the ``_SAFETY_ALLOWED_DELETED_LINES`` precedent): anything beyond these
#: pairs — another file, another line, another wording — still fails the gate.
_LOOKS_LIBRARY_DIR = "server/looks/library/"
_LOOKS_GRANTED_LINE_PAIRS = {
    "server/looks/library/ballad.yaml": (
        (
            '    aliases: ["달빛", "moonlight", "푸른 밤"]',
            '    aliases: ["달빛", "moonlight", "푸른 밤", "파란 밤"]',
        ),
        (
            '    mood_keywords: ["쓸쓸한", "푸른", "밤", "달빛", "차분한", "moonlit", "night"]',
            '    mood_keywords: ["쓸쓸한", "푸른", "파란", "밤", "달빛", "차분한", "moonlit", "night"]',  # noqa: E501
        ),
    ),
    "server/looks/library/edm.yaml": (
        (
            '    mood_keywords: ["깊은", "푸른", "숨고르는", "브레이크다운", "deep", "breakdown"]',
            '    mood_keywords: ["깊은", "푸른", "파란", "숨고르는", "브레이크다운", "deep", "breakdown"]',  # noqa: E501
        ),
    ),
    "server/looks/library/worship.yaml": (
        (
            '    aliases: ["푸른 벌스", "blue verse", "새벽"]',
            '    aliases: ["푸른 벌스", "파란 벌스", "blue verse", "새벽"]',
        ),
        (
            '    mood_keywords: ["서늘한", "고요한", "새벽", "푸른", "벌스", "cool", "calm"]',
            '    mood_keywords: ["서늘한", "고요한", "새벽", "푸른", "파란", "벌스", "cool", "calm"]',  # noqa: E501
        ),
    ),
}

_TOOLS_PATH = "server/orchestrator/tools.py"

#: Protected regions of ``tools.py``, PRECHK-base relative: the programmer-state
#: command tuple and the dedupe execution loop. Position blockade, NOT a
#: deletion count -- ``tools.py`` legitimately deletes one line since this base
#: (an import replaced by a block), so a "zero deletions" rule would fail on
#: arrival and teach the next reader to weaken the gate.
_TOOLS_PROTECTED_OLD_RANGES = ((247, 251), (537, 582))

_SAFETY_DIR = "server/safety/"

#: The OVERLAP SPEC's own merge commit into main (PR #8) -- a FIXED historical
#: endpoint, unlike HEAD. "OVERLAP itself opened nothing new" is a fact about a
#: SPEC that finished long ago; measuring it against the ever-moving HEAD makes
#: it fail the moment any LATER, legitimate SPEC touches the chokepoint again
#: (exactly the "sibling gate breaks by merge order" failure mode documented at
#: `TestPrecedentGateFileIsNotExtended` above). Bounding both ends fixes it.
_OVERLAP_MERGE_COMMIT = "156a3e1aaf6ef78788394d65cf724bacaec7b567"

#: The safety chokepoint's measured state, PRECHK-base relative. Grown four
#: times: the predecessor's (OVERLAP's) property-read addition (console.py,
#: gate.py), then SPEC-COPILOT-BACKUP-001 T-B/T-B2's snapshot-retention +
#: audit-linkage extension (backup.py, gate.py again), then the T-I audit-log
#: crash fix -- audit.py joins the set (SCOPE CORRECTION below), then the
#: closed-set revision below. Every deletion's TEXT is pinned in
#: `_SAFETY_ALLOWED_DELETED_LINES` below, because a bare count lets a
#: meaningful removal hide under the allowance.
#:
#: 2026-08-05 granted exception -- SPEC-COPILOT-WRITEGATE-001 revises the
#: closed-set SSOT `blacklist.yaml` from version 1 to 2, adding exactly ONE
#: entry ("Set Fixture"). User-approved after the alternatives were searched
#: and rejected, which is the part worth recording: a design touching only
#: `gate.py` would have cost ZERO entries here (gate.py is already an allowed
#: row and the addition deletes nothing), but it would have forked the
#: closed-set interpretation that `classify.py`'s @MX:ANCHOR forbids and,
#: concretely, missed a patch write smuggled through a quoted `Property
#: 'Command'` value -- the recursion that catches those calls
#: `classify_command`, not the gate. So the cheaper boundary was declined for
#: the correct layer, and the cost is this one row.
#:
#: Why it could not be avoided at all: `SafetyGate.screen()` takes a command
#: sequence and nothing else, so no caller can declare a bundle risky
#: (SPATIAL-001 progress.md:294-296). Every possible design edits at least one
#: file under `server/safety/`. The FIRST attempt at this change was reverted
#: precisely here (SPATIAL progress.md:302-306) -- it was blocked by ownership,
#: not by being wrong, and WRITEGATE-001 owns `server/safety/`.
#:
#: The grant is one FILE with one PINNED deletion, and it widens nothing else.
#: Another file under the chokepoint, a second deleted line in this one, or any
#: text other than `version: 1` still fails the gate.
_SAFETY_EXPECTED_DELETIONS = {
    "server/safety/audit.py": 1,
    "server/safety/backup.py": 2,
    "server/safety/blacklist.yaml": 1,
    "server/safety/console.py": 0,
    "server/safety/gate.py": 3,
}
_SAFETY_ALLOWED_DELETED_LINES = {
    # SCOPE CORRECTION (T-I audit-log crash fix): AuditLog.record() used a
    # bare `json.dumps(enriched, ensure_ascii=False)` with no fallback for
    # non-serializable values -- a value like a CommandDecision object landing
    # in an event dict raised TypeError mid-write, so the single durable
    # audit write point (@MX:ANCHOR) silently lost the event instead of
    # recording it. The one-line write is replaced by a `default=str`
    # variant that degrades an unserializable value to its str() form rather
    # than dropping the whole event; this legitimately reopens audit.py under
    # the chokepoint for the first time, the same maintenance shape as the
    # `gate.py` extension above.
    "server/safety/audit.py": (
        r'            handle.write(json.dumps(enriched, ensure_ascii=False) + "\n")',
    ),
    "server/safety/backup.py": (
        "Three rules: ① once at session start, ② periodic (default 10 minutes,",
        '    """Drives the 3-rule backup policy against an injected backup action."""',
    ),
    # The version bump IS the revision: `version: 1` is replaced by
    # `version: 2`, which is the one deletion granted above. The entry addition
    # and the REVISION HISTORY block that justifies it are pure additions, so
    # they need no allowance -- and `test_safety_ruleset.py` pins the new
    # content exactly, so this grant cannot be used to smuggle a second entry.
    "server/safety/blacklist.yaml": ("version: 1",),
    "server/safety/gate.py": (
        "from server.safety.backup import BackupError, BackupManager",
        '    """StateQueryPort implementation riding the gate-audited console link."""',
        '        """Attach a BackupManager whose action saves the showfile via this gate."""',
    ),
}

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
    # Two granted extensions are checked by their own narrower gates below: the
    # looks-library one by exact line text, the rulebook one by named added path
    # plus zero deletions. Every OTHER preserved path must still diff empty, and
    # the rulebook's five EXISTING assets are named here so they keep doing so.
    paths = tuple(
        path for path in _PRESERVE_PATHS if path not in (_LOOKS_LIBRARY_DIR, _RULEBOOK_DIR)
    )
    return [
        "git",
        "diff",
        "--stat",
        f"{_PRECHK_BASE}..HEAD",
        "--",
        *paths,
        *_RULEBOOK_LOCKED_ASSETS,
    ]


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
        # Both granted extensions are swapped out of the directory sweep and
        # re-entered as the narrower thing that IS still locked: the looks
        # library by its own exact-text gate, the rulebook by its five named
        # existing assets.
        assert tuple(command[5:]) == (
            *(path for path in _PRESERVE_PATHS if path not in (_LOOKS_LIBRARY_DIR, _RULEBOOK_DIR)),
            *_RULEBOOK_LOCKED_ASSETS,
        )
        # The swap must not silently drop the rulebook from the gate entirely.
        assert _RULEBOOK_DIR not in command
        assert all(asset in command for asset in _RULEBOOK_LOCKED_ASSETS)
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


class TestRulebookGrantedAddition:
    """The 2026-08-03 grant — exactly one added asset, and nothing removed.

    Not a weakening: the five existing assets are named in
    :func:`_preserve_diff_command`, so modifying any of them still fails the
    emptiness gate above. This class is the other half — it bounds what the
    grant permits, so "one new rulebook file" cannot quietly become two, or
    become a rewrite of an old one.
    """

    def test_the_five_existing_assets_are_the_locked_set(self):
        # Non-vacuity: a typo'd path contributes nothing to a git diff, so the
        # locked list is checked against the real directory listing.
        on_disk = sorted(
            path.name for path in (_REPO_ROOT / _RULEBOOK_DIR).iterdir() if path.suffix == ".md"
        )
        locked = sorted(Path(path).name for path in _RULEBOOK_LOCKED_ASSETS)
        assert locked == sorted(set(on_disk) - {Path(_RULEBOOK_GRANTED_ADDITION).name})
        assert len(_RULEBOOK_LOCKED_ASSETS) == 5

    def test_the_only_rulebook_change_is_the_granted_addition(self):
        rows = _numstat(_PRECHK_BASE, _RULEBOOK_DIR)
        assert set(rows) == {_RULEBOOK_GRANTED_ADDITION}

    def test_the_grant_removes_nothing(self):
        # A rulebook asset is a fixed system-prompt prefix; a deletion inside
        # this directory changes what every model call is told, whichever file
        # it lands in.
        rows = _numstat(_PRECHK_BASE, _RULEBOOK_DIR)
        for path, (_added, deleted) in rows.items():
            assert deleted == 0, path

    def test_the_locked_assets_are_byte_identical(self):
        # Stated directly as well as via the emptiness gate: this is the claim
        # the whole grant rests on, and it should be readable on its own.
        assert _git("diff", "--stat", f"{_PRECHK_BASE}..HEAD", "--", *_RULEBOOK_LOCKED_ASSETS) == ""


class TestLooksLibraryGrantedExtension:
    """The 2026-08-02 grant — exactly the sanctioned 파란 mirror, nothing else.

    Not a weakening: the boundary stays locked, and this class IS the lock's
    new shape. Every deleted line must reappear as its paired insertion with
    파란 added; an extra file, an extra hunk, or a different wording fails.
    """

    @staticmethod
    def _diff_lines(path: str) -> tuple[list[str], list[str]]:
        deleted, added = [], []
        for line in _git("diff", "--unified=0", f"{_PRECHK_BASE}..HEAD", "--", path).splitlines():
            if line.startswith("-") and not line.startswith("---"):
                deleted.append(line[1:])
            elif line.startswith("+") and not line.startswith("+++"):
                added.append(line[1:])
        return deleted, added

    def test_the_grant_is_not_an_empty_exemption(self):
        # Non-vacuity, the standard this module sets for itself. All three
        # assertions below are satisfied by an EMPTY dict — `set() == set()`
        # and two loops that never run — while `server/looks/library/` stays
        # filtered out of `_preserve_diff_command()`. That combination is a
        # gate that is off AND green, so pin both halves: the grant has
        # entries, and the directory it exempts really did change.
        assert _LOOKS_GRANTED_LINE_PAIRS
        assert _git("diff", "--stat", f"{_PRECHK_BASE}..HEAD", "--", _LOOKS_LIBRARY_DIR) != ""

    def test_exactly_the_three_granted_files_changed(self):
        rows = _numstat(_PRECHK_BASE, _LOOKS_LIBRARY_DIR)
        assert set(rows) == set(_LOOKS_GRANTED_LINE_PAIRS)

    def test_every_change_is_a_granted_line_pair_and_every_pair_is_present(self):
        for path, pairs in _LOOKS_GRANTED_LINE_PAIRS.items():
            deleted, added = self._diff_lines(path)
            assert deleted == [old for old, _new in pairs], path
            assert added == [new for _old, new in pairs], path

    def test_the_grant_really_is_the_blue_mirror_and_nothing_broader(self):
        # Non-vacuity + shape: each pair differs ONLY by inserting 파란 tokens.
        for pairs in _LOOKS_GRANTED_LINE_PAIRS.values():
            for old, new in pairs:
                assert old != new
                assert "파란" not in old
                assert "파란" in new
                # Removing the 파란 tokens from the new line restores the old
                # one exactly — the grant cannot smuggle an unrelated edit.
                stripped = new.replace(', "파란 밤"', "").replace(', "파란 벌스"', "")
                stripped = stripped.replace('"파란", ', "")
                assert stripped == old


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

    def test_exactly_the_expected_files_changed(self):
        rows = _numstat(_PRECHK_BASE, _SAFETY_DIR)
        assert set(rows) == set(_SAFETY_EXPECTED_DELETIONS)

    def test_the_deletion_counts_match(self):
        rows = _numstat(_PRECHK_BASE, _SAFETY_DIR)
        for path, expected in _SAFETY_EXPECTED_DELETIONS.items():
            assert rows[path][1] == expected, path

    def test_the_deletions_are_exactly_the_pinned_lines(self):
        """A bare count lets a meaningful removal hide -- the deleted TEXT is
        pinned per file, not just the total.

        SCOPE CORRECTION (SPEC-COPILOT-BACKUP-001 T-B/T-B2 integration,
        mirroring the ``tools.py`` correction at
        :class:`TestPrecedentGateFileIsNotExtended`): the predecessor's grant
        removed exactly one docstring line in gate.py. This SPEC legitimately
        extends the chokepoint further -- BackupManager gains snapshot
        retention + a gate-level eviction hook, no restore SEND path (see
        server/safety/backup.py's module docstring) -- so its own edits
        delete an import line and two more docstrings alongside the
        predecessor's line. Not every deletion is a docstring any more (the
        import line is real code), so the old blanket "is-a-docstring" shape
        check is retired in favor of the stricter, general invariant it was
        always standing in for: exact text, per file.
        """
        for path, allowed in _SAFETY_ALLOWED_DELETED_LINES.items():
            deleted = [
                line[1:]
                for line in _git(
                    "diff", "--unified=0", f"{_PRECHK_BASE}..HEAD", "--", path
                ).splitlines()
                if line.startswith("-") and not line.startswith("---")
            ]
            assert deleted == list(allowed), path

    def test_overlap_s_own_scope_changed_nothing_under_the_chokepoint(self):
        """SCOPE CORRECTION (SPEC-COPILOT-BACKUP-001 T-B/T-B2 integration).

        This used to read ``_git("diff", "--stat", f"{_OVERLAP_BASE}..HEAD",
        ...) == ""`` -- "this SPEC changed nothing under the chokepoint". That
        was true and MEASURABLE while OVERLAP's own merge was still HEAD. It
        stops being measurable the moment a later SPEC legitimately reopens
        the chokepoint (exactly the ``tools.py`` failure mode documented at
        :class:`TestPrecedentGateFileIsNotExtended`): the range then spans the
        later SPEC's commits too, and the gate fails while the fact it names
        -- OVERLAP itself opened nothing new -- is still true.

        What survives is bounding BOTH ends instead of leaving one open at
        HEAD: ``_OVERLAP_BASE.._OVERLAP_MERGE_COMMIT`` is OVERLAP's own,
        now-immutable commit range, so this fact is checked exactly where it
        was made rather than at an ever-moving present.
        """
        assert (
            _git("diff", "--stat", f"{_OVERLAP_BASE}..{_OVERLAP_MERGE_COMMIT}", "--", _SAFETY_DIR)
            == ""
        )

    def test_this_spec_s_base_can_still_observe_a_change(self):
        """AC-OVERLAP-002 ④ — 비공허성: 같은 명령이 변화를 볼 수 있는가.

        위 ③은 ``_OVERLAP_BASE.._OVERLAP_MERGE_COMMIT`` 범위에서 chokepoint가
        비어 있다고 주장한다. 같은 명령 형태를 이 SPEC이 실제로 건드린
        ``server/prechk/``에 겨누면 비어 있지 않아야 한다. 여기가 비면 명령이
        변화를 관측하지 못하게 된 것이고, ③의 빈 출력은 아무 의미도 없어진다.

        이 구멍은 좁다: ``_OVERLAP_BASE``를 무력화하는 드리프트는
        :func:`test_the_touched_set_is_not_empty`가 이미 잡는다. 그럼에도 ③이
        이름 붙인 BASE에 대한 대조군은 그 자리에 있어야 한다.
        """
        assert _git("diff", "--stat", f"{_OVERLAP_BASE}..HEAD", "--", "server/prechk/") != ""


class TestPrecedentGateFileIsNotExtended:
    """AC-OVERLAP-019 ⑥ — one base per module."""

    def test_the_precedent_file_still_pins_its_own_protected_ranges(self):
        # SCOPE CORRECTION (SPEC-COPILOT-FXLIB-001 integration, 2026-08-01).
        #
        # This assertion used to read `_numstat(_OVERLAP_BASE, precedent) == {}`
        # -- "this SPEC did not extend the precedent file". That was true and
        # measurable while OVERLAP was the only unmerged work on its base. It
        # stopped being MEASURABLE the moment a sibling SPEC landed on the same
        # base: the range `_OVERLAP_BASE..HEAD` then spans the sibling's commits
        # too, so the diff reports the SIBLING's edits and the gate fails while
        # the property it names is still true. FXLIB legitimately extended the
        # precedent's positional list because it touched `tools.py` -- that is
        # the tripwire's designed maintenance, not a violation.
        #
        # What survives the merge is the invariant the zero-rows form was a
        # proxy FOR: the precedent's tripwire must still pin protected ranges on
        # its own base. That is asserted here, and the precedent asserts the
        # ranges themselves in its own module (one base per module, AC-OVERLAP-019 ⑥).
        precedent = (_REPO_ROOT / "server/tests/test_songcue_bundle.py").read_text(encoding="utf-8")
        assert "_TOOLS_EXPECTED_HUNK_OLD_STARTS" in precedent
        assert "_TOOLS_PROTECTED_RANGES" in precedent or "protected" in precedent
        # Non-vacuity: a file that lost its tripwire would still contain the
        # word "protected" in prose, so the positional list is the real anchor
        # and it is checked by identity above, not by substring in a comment.
        assert re.search(r"_TOOLS_EXPECTED_HUNK_OLD_STARTS\s*=\s*\(", precedent)

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
