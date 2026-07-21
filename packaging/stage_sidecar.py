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
``--bundle``       ``<app>/Contents/`` — where the PyInstaller bootloader looks
                   once its executable sits in ``Contents/MacOS/`` of a macOS
                   ``.app``. This is the dev-works / packaged-fails gap:
                   ``externalBin`` carries the named FILE into the bundle and
                   nothing else, so without this step the shipped ``.app`` spawns
                   a backend that dies instantly. The step then SEALS the bundle
                   (:func:`seal_bundle`), and ``--verify-bundle`` asserts both
                   that the payload landed and that the seal holds.

The ``Contents/MacOS`` -> ``Contents/Frameworks`` convention is PyInstaller's own
macOS ``.app`` layout, but that layout is a code/data **split**, not a flat tree:
``Contents/Frameworks`` holds only Mach-O and symlinks OUT to the data, while
``Contents/Resources`` holds the data and symlinks BACK to the Mach-O. The split
is not cosmetic — ``codesign`` treats everything under ``Contents/Frameworks`` as
nested CODE, so one plain data directory there makes the entire bundle
unsignable ("code object is not signed at all / In subcomponent: ...").

The payload is therefore mirrored from PyInstaller's own ``dist/<app>.app``
rather than re-derived from the flat onedir tree: PyInstaller has already worked
out which entries are code and which are data, and copying its answer is both
simpler and less brittle than reproducing that rule here.
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

# The PyInstaller .app the same spec run emits (its BUNDLE step). Its Contents/
# is the code/data split the Tauri bundle mirrors — see the module docstring.
PYI_APP = REPO_ROOT / "dist" / f"{APP_NAME}.app"

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


def _mirror(source: Path, destination: Path) -> None:
    """Copy every entry of ``source`` over ``destination``, symlinks intact.

    Entry by entry rather than a wholesale wipe, so the mirror only ever
    replaces what PyInstaller owns: Tauri's own ``Resources/icon.icns`` survives,
    while a stale FLAT payload left by an older build is REPLACED (a merge would
    leave a data directory in ``Contents/Frameworks`` and cost the bundle its
    signature).
    """
    destination.mkdir(parents=True, exist_ok=True)
    for entry in sorted(source.iterdir()):
        target = destination / entry.name
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.is_dir():
            shutil.rmtree(target)
        if entry.is_symlink():  # before is_dir(): that follows the link
            target.symlink_to(entry.readlink())
        elif entry.is_dir():
            shutil.copytree(entry, target, symlinks=True)
        else:
            shutil.copy2(entry, target)


def bundle_payload(app_bundle: Path) -> Path:
    """Mirror PyInstaller's own ``.app`` payload into the Tauri bundle.

    Tauri's ``externalBin`` puts the sidecar EXECUTABLE in ``Contents/MacOS`` and
    carries nothing else. A PyInstaller onedir executable sitting there resolves
    its runtime from ``../Frameworks``, so the payload must be reachable there —
    but NOT as a flat copy of the onedir tree, and NOT as a nested ``_internal``
    directory (the layout the bootloader uses only outside a bundle).

    ``dist/<app>.app/Contents`` already holds exactly the right shape: the
    code/data split described in the module docstring, which is what makes the
    result signable. Both halves are mirrored — ``Frameworks`` first, so its
    symlinks into ``Resources`` are resolved a moment later by the second pass.
    """
    contents = app_bundle / "Contents"
    executable = contents / "MacOS" / SIDECAR_BASE
    if not executable.is_file():
        raise SystemExit(
            f"the bundle carries no sidecar executable: {executable}\n"
            "check tauri.conf.json bundle.externalBin"
        )
    source = PYI_APP / "Contents"
    if not (source / "Frameworks").is_dir():
        raise SystemExit(
            f"PyInstaller .app payload not found: {source}\n"
            "build it first: .venv/bin/pyinstaller packaging/GrandMA3-Copilot.spec"
        )
    for half in ("Frameworks", "Resources"):
        _mirror(source / half, contents / half)
    return contents / "Frameworks"


def seal_bundle(app_bundle: Path) -> Path | None:
    """Ad-hoc code-sign the ``.app`` — AFTER its payload has landed.

    ``tauri build`` leaves the bundle UNSEALED: no signing identity is
    configured (and none is wanted — this app is handed to a handful of Macs,
    never distributed), so Tauri skips ``codesign`` entirely. The shell
    executable carries only the linker's ad-hoc signature, ``_CodeSignature/``
    does not exist, and ``codesign --verify`` fails with *"code has no resources
    but signature indicates they must be present"*. Sealing here closes that,
    and sealing HERE specifically — after :func:`bundle_payload` — is what keeps
    the seal honest: anything copied in afterwards is outside it.

    One ``codesign`` call on the bundle root, deliberately:

    * NO ``--deep``. Apple deprecates it for signing, and here it actively
      fails: it walks the payload and tries to sign data directories such as
      ``click-8.4.2.dist-info`` as bundles ("bundle format unrecognized"). The
      root call needs no help — it seals all 1600-odd payload files as
      resources, and the two ``Contents/MacOS`` executables already carry valid
      signatures of their own.
    * NO ``--options runtime`` / entitlements, and so no reuse of
      ``packaging/sign.sh``. Hardened runtime exists to satisfy notarization,
      which is out of scope; turning it on would also put the second executable
      (``copilot-backend``) under library validation WITHOUT the
      disable-library-validation entitlement that only the bundle's
      ``CFBundleExecutable`` receives. ``sign.sh`` additionally signs each
      nested Mach-O by path, and for the ``CFBundleExecutable`` codesign
      resolves that path back to the enclosing bundle — so its inside-out pass
      aborts on this bundle.
    """
    if shutil.which("codesign") is None:
        print("stage_sidecar: codesign unavailable — the bundle is left unsealed", file=sys.stderr)
        return None
    proc = subprocess.run(
        ["codesign", "--force", "--sign", "-", str(app_bundle)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise SystemExit(
            f"codesign could not seal the bundle: {app_bundle}\n"
            f"{(proc.stderr or proc.stdout).strip()}"
        )
    return app_bundle


def _seal_problem(app_bundle: Path) -> str | None:
    """Why the bundle's signature does not verify, or ``None`` when it does.

    ``None`` is also the answer where ``codesign`` does not exist: a missing
    tool is not evidence of a broken seal, so the check skips rather than
    failing a bundle it could not inspect.
    """
    if shutil.which("codesign") is None:
        print("stage_sidecar: codesign unavailable — seal check skipped", file=sys.stderr)
        return None
    proc = subprocess.run(
        ["codesign", "--verify", "--strict", str(app_bundle)],
        capture_output=True,
        text=True,
    )
    if proc.returncode == 0:
        return None
    detail = (proc.stderr or proc.stdout).strip().splitlines()
    return (
        "the bundle's code signature does not verify: "
        f"{detail[0] if detail else f'codesign exited {proc.returncode}'} — "
        "macOS cannot be trusted to launch it on another machine"
    )


def verify_bundle(app_bundle: Path) -> int:
    """Fail loudly when the bundled sidecar could not boot — or is unsealed.

    The payload check alone is not enough: a payload that landed AFTER the
    bundle was sealed leaves the app looking complete while its signature is
    broken. Both halves are checked here so neither step can be dropped in
    silence.
    """
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
    seal = _seal_problem(app_bundle)
    if seal is not None:
        problems.append(seal)
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
        "--bundle",
        metavar="APP",
        help="copy the runtime payload into a built .app bundle, then seal it",
    )
    parser.add_argument(
        "--verify-bundle",
        metavar="APP",
        help="assert a built .app carries a bootable sidecar and a valid seal",
    )
    args = parser.parse_args(argv)
    if args.check:
        return check()
    if args.verify_bundle:
        return verify_bundle(Path(args.verify_bundle))
    if args.bundle:
        # Payload -> seal -> verify, in ONE step. Splitting the seal into a
        # separate build step would re-create the failure being fixed here: a
        # necessary step, placed after the point that seals the bundle, which a
        # later packaging change can quietly drop.
        app_bundle = Path(args.bundle)
        destination = bundle_payload(app_bundle)
        print(f"stage_sidecar: bundled the runtime payload into {destination}")
        if seal_bundle(app_bundle) is not None:
            print(f"stage_sidecar: sealed (ad-hoc) {app_bundle}")
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
