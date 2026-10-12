"""Build a safe cleanup list from runner logs (offline; touches no console).

Only ``Store Preset/Timecode/Sequence`` lines whose status is ``ok`` in the given
``run-*.jsonl`` files count as "created". Deleting an object that was never created fails
with ``Illegal object`` and stops the runner, so nothing else is ever listed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

PATTERNS = [
    re.compile(r"Store (Preset \d+\.\d+)"),
    re.compile(r"Store (Timecode \d+)(?![\d.])"),
    re.compile(r"Store (Sequence \d+)"),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", required=True, help="run-*.jsonl (repeatable)")
    ap.add_argument("--out", help="write the cleanup file here")
    ap.add_argument("--include-22-0", action="store_true", help="also delete Preset 22.0")
    args = ap.parse_args()
    objs: list[str] = []
    for path in args.run:
        for raw in Path(path).read_text(encoding="utf-8").splitlines():
            rec = json.loads(raw)
            if rec.get("status") != "ok" or "line" not in rec:
                continue
            for pat in PATTERNS:
                m = pat.match(rec["line"])
                if m and m.group(1) not in objs:
                    objs.append(m.group(1))
    if not args.include_22_0:
        objs = [o for o in objs if o != "Preset 22.0"]
    ordered = (
        [o for o in objs if o.startswith("Timecode")]
        + [o for o in objs if o.startswith("Sequence")]
        + [o for o in objs if o.startswith("Preset")]
    )
    lines = ["ClearAll", *[f"Delete {o} /NoConfirm" for o in ordered], "ClearAll"]
    text = "".join(f"{x}\n" for x in lines)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(text, end="")
    print(f"# lines={len(lines)} sha256={hashlib.sha256(text.encode()).hexdigest()}")


if __name__ == "__main__":
    main()
