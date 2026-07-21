"""Stage the PyInstaller onedir backend as a Tauri sidecar (M7.4a).

Tauri resolves a `bundle.externalBin` entry by appending the Rust target triple:
``binaries/copilot-backend`` becomes ``binaries/copilot-backend-aarch64-apple-darwin``.
The M6 backend is an **onedir** tree, not a single file — the executable needs
its sibling ``_internal/`` directory to boot — so staging copies the whole tree
and renames only the executable.

Usage (from the repo root, after ``.venv/bin/pyinstaller packaging/GrandMA3-Copilot.spec``)::

    python packaging/stage_sidecar.py            # copy dist/<app>/ -> src-tauri/binaries/
    python packaging/stage_sidecar.py --check    # verify staging without copying

Three placements, because a PyInstaller **onedir** sidecar needs its runtime tree
wherever the executable ends up, and the three hosts put it in three places:

``stage``          ``src-tauri/binaries/`` — the source Tauri bundles from.
``--dev-mirror``   ``src-tauri/target/<profile>/`` — where Cargo copies the
                   single external binary for ``tauri dev`` / a direct run.
``--bundle``       ``<app>/Contents/Frameworks/`` — where the PyInstaller
                   bootloader looks once its executable sits in
                   ``Contents/MacOS/`` of a macOS ``.app``. This is the
                   dev-works / packaged-fails gap: ``externalBin`` carries the
                   named FILE into the bundle and nothing else, so without this
                   step the shipped ``.app`` spawns a backend that dies
                   instantly. ``--verify-bundle`` asserts the payload landed.

The ``Contents/MacOS`` -> ``Contents/Frameworks`` convention is PyInstaller's own
macOS ``.app`` layout (see ``dist/GrandMA3 Copilot.app``: executable in
``Contents/MacOS``, everything else flat in ``Contents/Frameworks``), and it is
verified here rather than assumed.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# The PyInstaller onedir output (packaging/GrandMA3-Copilot.spec APP_NAME).
APP_NAME = "GrandMA3 Copilot"
DIST_DIR = REPO_ROOT / "dist" / APP_NAME

# tauri.conf.json -> bundle.externalBin
SIDECAR_DIR = REPO_ROOT / "src-tauri" / "binaries"
SIDECAR_BASE = "copilot-backend"


def host_target_triple() -> str:
    """The Rust host triple Tauri appends to the sidecar name."""
    proc = subprocess.run(["rustc", "-vV"], capture_output=True, text=True, check=True)
    for line in proc.stdout.splitlines():
        if line.startswith("host:"):
            return line.split(":", 1)[1].strip()
    raise RuntimeError("could not read the host target triple from `rustc -vV`")


def staged_executable(triple: str | None = None) -> Path:
    return SIDECAR_DIR / f"{SIDECAR_BASE}-{triple or host_target_triple()}"


def stage(*, source: Path = DIST_DIR, force: bool = True) -> Path:
    """Copy the onedir tree into ``src-tauri/binaries`` and return the exe path."""
    if not source.is_dir():
        raise SystemExit(
            f"backend onedir tree not found: {source}\n"
            "build it first: .venv/bin/pyinstaller packaging/GrandMA3-Copilot.spec"
        )
    original = source / APP_NAME
    if not original.is_file():
        raise SystemExit(f"onedir executable not found: {original}")

    target = staged_executable()
    if SIDECAR_DIR.exists() and force:
        shutil.rmtree(SIDECAR_DIR)
    SIDECAR_DIR.mkdir(parents=True, exist_ok=True)

    for entry in sorted(source.iterdir()):
        destination = SIDECAR_DIR / (target.name if entry == original else entry.name)
        if entry.is_dir():
            shutil.copytree(entry, destination, symlinks=True, dirs_exist_ok=True)
        else:
            shutil.copy2(entry, destination)
    target.chmod(0o755)
    return target


def mirror_runtime(profile: str = "debug") -> Path:
    """Put ``_internal/`` beside the sidecar Cargo copied into the target dir.

    ``tauri-build`` copies the single ``externalBin`` FILE into
    ``src-tauri/target/<profile>/`` and drops the triple suffix, but a PyInstaller
    **onedir** executable resolves its runtime tree from its own directory — so
    the copied file alone cannot boot. Mirroring ``_internal/`` next to it is what
    makes ``tauri dev`` (and a direct run of the built shell) able to actually
    start the backend. Same PENDING-M7.4b relocation gap as the bundle path,
    solved for the dev path only.
    """
    destination = REPO_ROOT / "src-tauri" / "target" / profile
    copied = destination / SIDECAR_BASE
    if not copied.is_file():
        raise SystemExit(
            f"cargo has not copied the sidecar yet: {copied}\n"
            "build the shell first: cd src-tauri && cargo build"
        )
    source = SIDECAR_DIR / "_internal"
    if not source.is_dir():
        raise SystemExit(
            f"staged runtime tree not found: {source} (run without --dev-mirror first)"
        )
    shutil.copytree(source, destination / "_internal", symlinks=True, dirs_exist_ok=True)
    return copied


# A file PyInstaller always emits into its runtime tree; its presence inside the
# bundle is the cheap proof that the payload actually landed.
_PAYLOAD_SENTINEL = "base_library.zip"


def bundle_payload(app_bundle: Path) -> Path:
    """Copy the onedir runtime tree into ``<app>/Contents/Frameworks``.

    Tauri's ``externalBin`` puts the sidecar EXECUTABLE in ``Contents/MacOS`` and
    carries nothing else. A PyInstaller onedir executable sitting there resolves
    its runtime from ``../Frameworks`` (PyInstaller's own ``.app`` layout), so the
    tree is copied flat into ``Contents/Frameworks`` — NOT as a nested
    ``_internal`` directory, which is the layout the bootloader uses only when the
    executable is not inside a bundle.
    """
    contents = app_bundle / "Contents"
    executable = contents / "MacOS" / SIDECAR_BASE
    if not executable.is_file():
        raise SystemExit(
            f"the bundle carries no sidecar executable: {executable}\n"
            "check tauri.conf.json bundle.externalBin"
        )
    source = SIDECAR_DIR / "_internal"
    if not source.is_dir():
        raise SystemExit(f"staged runtime tree not found: {source} (run the stage step first)")
    frameworks = contents / "Frameworks"
    frameworks.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, frameworks, symlinks=True, dirs_exist_ok=True)
    return frameworks


def verify_bundle(app_bundle: Path) -> int:
    """Fail loudly when the bundled sidecar could not possibly boot."""
    contents = app_bundle / "Contents"
    problems = []
    executable = contents / "MacOS" / SIDECAR_BASE
    sentinel = contents / "Frameworks" / _PAYLOAD_SENTINEL
    if not executable.is_file():
        problems.append(f"no sidecar executable in the bundle: {executable}")
    if not sentinel.is_file():
        problems.append(
            f"no PyInstaller runtime payload in the bundle: {sentinel} — the "
            "sidecar would exit immediately on first launch"
        )
    for problem in problems:
        print(f"stage_sidecar: {problem}", file=sys.stderr)
    if problems:
        return 1
    print(f"stage_sidecar: bundle OK — {app_bundle}")
    return 0


def check() -> int:
    target = staged_executable()
    internal = SIDECAR_DIR / "_internal"
    problems = []
    if not target.is_file():
        problems.append(f"missing staged sidecar executable: {target}")
    if not internal.is_dir():
        problems.append(f"missing PyInstaller runtime tree: {internal}")
    for problem in problems:
        print(f"stage_sidecar: {problem}", file=sys.stderr)
    if problems:
        print("stage_sidecar: run `python packaging/stage_sidecar.py`", file=sys.stderr)
        return 1
    print(f"stage_sidecar: OK — {target}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="verify the staged payload without copying"
    )
    parser.add_argument(
        "--dev-mirror",
        metavar="PROFILE",
        nargs="?",
        const="debug",
        help="mirror _internal/ next to the sidecar cargo copied into target/<PROFILE>/",
    )
    parser.add_argument(
        "--bundle", metavar="APP", help="copy the runtime payload into a built .app bundle"
    )
    parser.add_argument(
        "--verify-bundle", metavar="APP", help="assert a built .app carries a bootable sidecar"
    )
    args = parser.parse_args(argv)
    if args.check:
        return check()
    if args.verify_bundle:
        return verify_bundle(Path(args.verify_bundle))
    if args.bundle:
        app_bundle = Path(args.bundle)
        destination = bundle_payload(app_bundle)
        print(f"stage_sidecar: bundled the runtime payload into {destination}")
        return verify_bundle(app_bundle)
    if args.dev_mirror:
        copied = mirror_runtime(args.dev_mirror)
        print(f"stage_sidecar: mirrored the runtime tree beside {copied}")
        return 0
    target = stage()
    print(f"stage_sidecar: staged {DIST_DIR} -> {target}")
    return 0


if __name__ == "__main__":  # pragma: no cover - operator entry point
    raise SystemExit(main())
