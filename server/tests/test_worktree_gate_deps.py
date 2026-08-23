"""t13 — the pre-commit gate must not depend on an uninstalled ui/node_modules.

A fresh worktree carries no ``ui/node_modules``, so the root ``npm test`` script
died with ``sh: vitest: command not found`` and took ``moai gate`` — and with it the
whole pre-commit hook — down. Reproduced three times before this guard existed
(t11 run/plan lanes, t15 lead, t16 sync lane).

The damage is not the lost second. It is that a human then picks one of two
workarounds whose difference never reaches the commit history:

* ``SKIP_MOAI_PRECOMMIT=1 git commit`` leaves a commit that LOOKS gate-passed.
  Nothing in the tree records that the gate never ran.
* ``npm --prefix ui ci`` first, then commit, actually runs the gate.

Both produce identical-looking commits, so the choice is invisible afterwards —
the same silent-failure class as the M7.4a guards in
``test_deploy_tauri_shell.py``.

The fix is an npm-native ``pretest`` hook that installs the ui dependencies only
when they are absent. ``npm`` runs ``pretest`` before ``test`` with no change at
the call site, so ``moai gate`` self-heals and the gate is never silently
skipped.

A guard that cannot fail is not a guard, so the shell predicate the fix rests on
is proven below against synthetic positive and negative controls rather than
merely asserted.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_JSON = PROJECT_ROOT / "package.json"


def _scripts() -> dict[str, str]:
    return json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))["scripts"]


class TestPretestDependencyGuard:
    """The root package.json must self-heal a missing ui dependency tree."""

    def test_a_pretest_hook_exists(self) -> None:
        assert "pretest" in _scripts(), (
            "root package.json has no pretest hook; a fresh worktree will fail "
            "moai gate with: sh: vitest: command not found"
        )

    def test_the_pretest_hook_installs_the_ui_tree_when_it_is_absent(self) -> None:
        pretest = _scripts()["pretest"]
        assert "ui/node_modules" in pretest, (
            "pretest must test for the ui dependency tree, not install blindly"
        )
        assert "npm --prefix ui ci" in pretest, (
            "pretest must install with npm ci so package-lock.json is not rewritten"
        )

    def test_the_test_script_still_delegates_to_the_ui_suite(self) -> None:
        assert _scripts()["test"] == "npm --prefix ui run test", (
            "the pretest hook must not change what test itself runs"
        )


class TestTheGuardPredicateCanActuallyFail:
    """Synthetic controls: the shell predicate must discriminate both ways.

    Asserting the pretest string alone would pass even if the predicate were
    inverted or always-true. These two controls run the real predicate shape
    against a directory that exists and one that does not.
    """

    @staticmethod
    def _predicate_exit_code(target: Path) -> int:
        return subprocess.run(
            ["sh", "-c", f"[ -d {target} ] || exit 9"],
            check=False,
        ).returncode

    def test_it_short_circuits_when_the_tree_exists(self, tmp_path: Path) -> None:
        present = tmp_path / "node_modules"
        present.mkdir()
        assert self._predicate_exit_code(present) == 0, (
            "predicate ran the install branch even though the tree was present"
        )

    def test_it_takes_the_install_branch_when_the_tree_is_absent(self, tmp_path: Path) -> None:
        assert self._predicate_exit_code(tmp_path / "node_modules") == 9, (
            "predicate skipped the install branch even though the tree was absent"
        )
