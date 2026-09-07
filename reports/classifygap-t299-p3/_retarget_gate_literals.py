"""t299 Phase 3 보조 스크립트 — `test_safety_gate.py` 의 운반용 리터럴만 옮긴다.

이 파일에서 v7 이 빨갛게 만든 14건은 전부 게이트 **배관** 검사이고, 쓰는 명령은
「안전한 예」다. 손으로 14곳을 고치면 의도한 자리 밖을 건드릴 위험이 있으므로,
**빨개진 검사 함수의 본문 안에서만** 치환한다. 같은 파일의 다른 자리
(`Store Cue` 를 일부러 위험한 예로 쓰는 t323 주석 자리, 정정 회차 검사 등)는
건드리지 않는다.

한 번 쓰고 버리는 스크립트이고, 무엇을 바꿨는지 출력으로 남기려고 파일로 둔다.

실행:  uv run python reports/classifygap-t299-p3/_retarget_gate_literals.py
"""

from __future__ import annotations

import re
from pathlib import Path

TARGET_FILE = Path("server/tests/test_safety_gate.py")

#: v7 투입 뒤 빨개진 검사 14개. 이 목록 밖은 치환하지 않는다.
RED_TESTS = {
    "test_safe_bundle_clears_and_executes",
    "test_safe_bundle_needs_no_approval_and_no_backup",
    "test_safe_bundle_stops_after_classification",
    "test_unlock_restores_the_normal_path",
    "test_executor_rechecks_the_lock_before_every_send",
    "test_executor_rechecks_health_before_every_send",
    "test_an_exactly_matching_version_is_a_no_op",
    "test_a_version_less_pong_does_not_block",
    "test_unconfirmed_result_is_reported_and_never_auto_resent",
    "test_unconfirmed_set_never_exceeds_the_cap",
    "test_oldest_entry_is_evicted_newest_still_forces_a_hold",
    "test_a_clearance_is_consumed_by_execution",
    "test_a_sessions_screen_does_not_invalidate_anothers_clearance",
    "test_concurrent_sessions_both_execute_their_own_cleared_bundle",
}

_DEF = re.compile(r"^(\s*)def (\w+)\(")


def _spans(lines: list[str]) -> list[tuple[int, int, str]]:
    """각 대상 함수의 [시작, 끝) 줄 범위. 끝은 같은/얕은 들여쓰기의 다음 줄."""
    found: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        match = _DEF.match(line)
        if not match or match.group(2) not in RED_TESTS:
            continue
        indent = len(match.group(1))
        end = index + 1
        while end < len(lines):
            candidate = lines[end]
            if candidate.strip() and (len(candidate) - len(candidate.lstrip())) <= indent:
                break
            end += 1
        found.append((index, end, match.group(2)))
    return found


def _rewrite(line: str) -> str:
    line = re.sub(r'f"Store Cue \{(\w+)\}"', r"safe_line(\1)", line)
    return re.sub(
        r'"Store Cue (\d+)"',
        lambda m: "SAFE_LINE" if m.group(1) == "5" else f"safe_line({m.group(1)})",
        line,
    )


def main() -> None:
    lines = TARGET_FILE.read_text(encoding="utf-8").splitlines(keepends=True)
    spans = _spans(lines)
    missing = RED_TESTS - {name for _, _, name in spans}
    assert not missing, f"대상 검사를 못 찾았다: {sorted(missing)}"

    changed = 0
    for start, end, _name in spans:
        for index in range(start, end):
            new = _rewrite(lines[index])
            if new != lines[index]:
                lines[index] = new
                changed += 1

    TARGET_FILE.write_text("".join(lines), encoding="utf-8")
    print(f"대상 검사 {len(spans)}개, 치환된 줄 {changed}개")

    leftover = [
        (name, index + 1, lines[index].rstrip())
        for start, end, name in spans
        for index in range(start, end)
        if "Store Cue" in lines[index]
    ]
    print(f"대상 본문에 남은 `Store Cue`: {len(leftover)}")
    for name, lineno, text in leftover:
        print(f"  {name}:{lineno}: {text}")


if __name__ == "__main__":
    main()
