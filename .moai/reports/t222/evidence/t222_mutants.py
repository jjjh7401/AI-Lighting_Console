"""t222 뮤테이션 — 새 단언이 실제로 무엇을 지키는지 잰다.

§3.3 규약: 치환이 실제로 적용됐는지를 눈이 아니라 단언으로 잰다
(`assert mutated != original`). `if False and ...` 처럼 형태 자체가 린트 위반인
치환은 축을 오염시키므로 쓰지 않는다 — 분기를 통째로 바꾸거나 지운다.
바이트코드 오염을 피하려고 하위 프로세스를 `PYTHONDONTWRITEBYTECODE=1` 로 돌린다.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

DERIVE = Path("server/lxseq/position_derive.py")
TESTS = "server/tests/test_lxseq_position_derive.py"

MUTANTS = [
    (
        "M1 가드 자체를 없앤다 (rig_is_degenerate 가 늘 거짓)",
        DERIVE,
        "    return max(max(xs) - min(xs), max(ys) - min(ys)) <= SPATIAL_ROW_NOISE_SPAN",
        "    return False",
    ),
    (
        "M2 임계를 정확히 0 으로 (노이즈 폭 아래 미세 편차를 놓친다)",
        DERIVE,
        "    return max(max(xs) - min(xs), max(ys) - min(ys)) <= SPATIAL_ROW_NOISE_SPAN",
        "    return max(max(xs) - min(xs), max(ys) - min(ys)) <= 0.0",
    ),
    (
        "M3 z 축까지 요구한다 (한 트러스 리그를 거절한다)",
        DERIVE,
        "    return max(max(xs) - min(xs), max(ys) - min(ys)) <= SPATIAL_ROW_NOISE_SPAN",
        "    zs = [position[2] for position in coordinates.values()]\n"
        "    spans = (max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs))\n"
        "    return max(spans) <= SPATIAL_ROW_NOISE_SPAN",
    ),
    (
        "M4 두 원인을 다시 한 사유로 접는다",
        DERIVE,
        '        (CAUSE_TARGET_COINCIDES, "target_coincides"),',
        '        (CAUSE_TARGET_COINCIDES, "unaimable"),',
    ),
    (
        "M5 원인 분류를 없앤다 (늘 tilt_limit)",
        DERIVE,
        "    if isinstance(error, PointingTargetCoincidesError):\n"
        "        return CAUSE_TARGET_COINCIDES",
        "    if False:\n        pass",
    ),
    (
        "M6 tilt 사유에서 「상한은 가정」 고지를 뺀다",
        DERIVE,
        '        "⚠️ 이 상한은 실측이 아니라 다른 리그 기종(Robe LEDBeam 350 / MMX)에서 온 "\n'
        '        "모듈 상수다 — 이 쇼의 기종 가동범위로 다시 재야 한다"',
        '        "머리 위로 넘어간다"',
    ),
]


def _run() -> tuple[int, str]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", TESTS, "-q", "-p", "no:randomly"],
        capture_output=True,
        text=True,
        env=env,
    )
    return proc.returncode, (proc.stdout or "").strip().splitlines()[-1]


def main() -> int:
    baseline_code, baseline_line = _run()
    print("기준 (뮤턴트 없음):", baseline_code, baseline_line)
    if baseline_code != 0:
        print("기준이 이미 빨갛다 — 뮤테이션이 성립하지 않는다")
        return 1
    verdicts = []
    for name, path, needle, replacement in MUTANTS:
        original = path.read_text(encoding="utf-8")
        if needle not in original:
            print(name, "-> 치환 문자열이 안 맞는다 (적용 안 됨)")
            verdicts.append((name, "NOT_APPLIED", ""))
            continue
        mutated = original.replace(needle, replacement, 1)
        assert mutated != original, name  # 「적용 안 됨」을 눈이 아니라 단언으로
        path.write_text(mutated, encoding="utf-8")
        try:
            code, line = _run()
        finally:
            path.write_text(original, encoding="utf-8")
        verdicts.append((name, "죽었다" if code != 0 else "🔴 살아남았다", line))
        print(name, "->", verdicts[-1][1], "|", line)
    survivors = [v for v in verdicts if v[1] != "죽었다"]
    print("")
    print("생존/미적용:", len(survivors), "/", len(MUTANTS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
