"""t224 뮤테이션 — 새 단언이 경계를 실제로 지키는지, 그리고 필요했는지.

두 팔(규약 §3.6):
  arm1  새 검사 파일이 **잡는가**            (기대: failed >= 1)
  arm2  기존 상태에서는 **못 잡는가**        (기대: failed == 0)

`assert mutated != original` 로 「적용 안 됨」 갈래를 기계화한다(규약 §3.3).
바이트코드 오염을 피하려고 하위 실행은 PYTHONDONTWRITEBYTECODE=1 로 돈다.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ARM1 = "server/tests/test_spatial_explicit_arrange.py"
ARM1_JOIN = "server/tests/test_lxseq_position_derive.py"
#: arm2 는 **이 카드 이전에 있던** 검사만 든다. t224 가 더한 파일·클래스를
#: 넣으면 「기존 상태에서는 못 잡는가」가 성립 자체를 안 한다.
ARM2 = [
    "server/tests/test_spatial_arrange.py",
    "server/tests/test_spatial_context.py",
    "server/tests/test_lxseq_cue_mapper.py",
]

MUTANTS = [
    (
        "M1 선언 대조 제거",
        "server/orchestrator/tools.py",
        "            if plan.fids != tuple(raw_fid for raw_fid in fids):",
        "            if False:",
    ),
    (
        "M2 미지 키 검사 제거",
        "server/spatial/presets.py",
        "        unknown = keys - EXPLICIT_ENTRY_KEYS",
        "        unknown = set()",
    ),
    (
        "M3 bool 좌표 검사 제거",
        "server/spatial/presets.py",
        # 이 술어는 파일에 세 번 나온다. 한 줄만 잡으면 첫 출현
        # (`_positive_number`)에 붙어 재려던 축을 안 건드린다 — 첫 회차에
        # 실제로 그렇게 났고 「생존」으로 기록됐다. 아래 count==1 단언이
        # 그 갈래를 기계화한다.
        "    if isinstance(value, bool) or not isinstance(value, (int, float)):\n"
        "        # `True` 는 파이썬에서 `int` 라",
        "    if not isinstance(value, (int, float)):\n        # `True` 는 파이썬에서 `int` 라",
    ),
    (
        "M4 양자화 우회",
        "server/spatial/presets.py",
        "    return _quantise(float(value))",
        "    return float(value)",
    ),
    (
        "M5 빈 꼬리 거절 제거",
        "server/lxseq/position_derive.py",
        '        raise ValueError("label_suffix 가 비었다 — 라벨은 좌표의 출처를 반드시 나른다")',
        "        suffix = DERIVED_LABEL_SUFFIX",
    ),
    (
        "M6 꼬리 인자 무시",
        "server/lxseq/position_derive.py",
        "· {suffix}",
        "· {DERIVED_LABEL_SUFFIX}",
    ),
    (
        "M7 조인 술어를 접두 일치로 무름",
        "server/lxseq/position_derive.py",
        "    if len(digits) != POSITION_ID_DIGITS or not digits.isdigit():\n        return None",
        "    if not digits[:POSITION_ID_DIGITS].isdigit():\n        return None",
    ),
    (
        "M8 콘솔 형태 인식 제거 (점 필수로 되돌림)",
        "server/lxseq/position_derive.py",
        '    bare = head.replace(".", "", 1) if head.startswith(POSITION_ID_PREFIX) else head',
        '    bare = head if head.startswith(POSITION_ID_PREFIX) else ""',
    ),
    (
        "M9 쓰기 라벨에서 점 제거를 되돌림",
        "server/lxseq/position_derive.py",
        '    return preset_id.replace(".", "")',
        "    return preset_id",
    ),
]


def run(paths: list[str]) -> tuple[int, int]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", *paths, "-q", "--no-header", "-p", "no:cacheprovider"],
        capture_output=True,
        text=True,
        env=env,
    )
    tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    failed = 0
    for token in tail.replace(",", " ").split():
        if token.isdigit():
            number = int(token)
        elif token in ("failed", "error", "errors") and "number" in dir():
            failed += number
    return failed, proc.returncode


def main() -> int:
    rows = []
    for name, path, old, new in MUTANTS:
        original = Path(path).read_text(encoding="utf-8")
        # 「적용 안 됨」 갈래의 기계화 — 치환이 안 맞으면 생존으로 기록되지 않는다.
        # 그리고 **유일성**까지 잰다: 여러 번 나오는 술어를 한 번만 치환하면
        # 엉뚱한 자리에 붙어 재려던 축을 안 건드린 채 「생존」이 나온다.
        occurrences = original.count(old)
        assert occurrences == 1, f"{name}: 치환 대상이 {occurrences}곳이다 (1곳이어야 한다)"
        mutated = original.replace(old, new, 1)
        assert mutated != original, f"{name}: 치환 문자열이 소스와 안 맞는다"
        Path(path).write_text(mutated, encoding="utf-8")
        try:
            arm1_failed, _ = run([ARM1, ARM1_JOIN])
            arm2_failed, _ = run(ARM2)
        finally:
            Path(path).write_text(original, encoding="utf-8")
        rows.append((name, arm1_failed, arm2_failed))
        print(f"{name}: arm1 failed={arm1_failed} · arm2 failed={arm2_failed}", flush=True)

    print()
    bad = [row for row in rows if row[1] == 0]
    print("arm1 에서 살아남은 뮤턴트:", [row[0] for row in bad] or "없음")
    print("arm2 가 이미 잡던 뮤턴트:", [row[0] for row in rows if row[2] > 0] or "없음")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
