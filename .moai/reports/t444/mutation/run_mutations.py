"""카드 t444 변이 시험 — 한 번에 하나씩 코드를 망가뜨리고 이 카드의 시험이
빨개지는지 잰다. 원본은 매번 되돌린다(finally).

실행: uv run python .moai/reports/t444/mutation/run_mutations.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

OUT = Path(".moai/reports/t444/mutation")
TESTS = ["server/tests/test_concept_color_input_t444.py", "server/tests/test_concept_gates.py"]

MUTATIONS = {
    "m1_resolver_drops_secondary": (
        "server/concept/resolver.py",
        'secondary = op.get("secondary")  # type: ignore[assignment]',
        "secondary = None",
    ),
    "m2_path_a_drops_palette": (
        "server/concept/session_bridge.py",
        '                "palette": list(decision.palette.colors),\n',
        "",
    ),
    "m3_path_b_call_site_drops_palettes": (
        "server/orchestrator/tools.py",
        "palettes=_songcue_concept_palettes(selections, records=interview_records_current),",
        "palettes=None,",
    ),
    "m6_director_primaries_drift_from_override": (
        "server/orchestrator/tools.py",
        # 첫 시도(occurrence=1 로 바꾸기)는 살아남았다 — 주색은 항상 base[0]
        # 이라 회차와 무관한 등가 변이였다(m6_first_try_equivalent.txt). 실제로
        # 일어날 법한 어긋남인 "주색 대신 보조색을 집는다"로 바꿨다.
        "primaries.append(colors[0] if colors else None)",
        "primaries.append(colors[-1] if colors else None)",
    ),
    "m4_input_color_before_restore": (
        "server/concept/gates.py",
        'insert_at = max((i + 1 for i, op in enumerate(ops) if op.get("op") == "restore"), default=0)',  # noqa: E501
        "insert_at = 0",
    ),
    "m5_constant_palette_judged_again": (
        "server/concept/gates.py",
        '    if build.color_source != "input":\n        return GateResult(None, NO_INPUT_COLOR_REASON)\n    cues = _concept_cues(build.table)\n    bridge',  # noqa: E501
        "    cues = _concept_cues(build.table)\n    bridge",
    ),
}

for name, (path, old, new) in MUTATIONS.items():
    file = Path(path)
    original = file.read_text(encoding="utf-8")
    assert original.count(old) == 1, (name, original.count(old))
    try:
        file.write_text(original.replace(old, new), encoding="utf-8")
        proc = subprocess.run(
            ["uv", "run", "pytest", *TESTS, "-q", "-p", "no:cacheprovider"],
            capture_output=True,
            text=True,
        )
        tail = "\n".join(proc.stdout.strip().splitlines()[-12:])
        (OUT / f"{name}.txt").write_text(f"exit={proc.returncode}\n{tail}\n", encoding="utf-8")
        print(name, "exit", proc.returncode, "|", proc.stdout.strip().splitlines()[-1])
    finally:
        file.write_text(original, encoding="utf-8")
