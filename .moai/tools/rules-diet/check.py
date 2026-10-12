"""상시 적재 instruction 파일 합계 점검. 한도(150,000자)를 넘으면 종료 코드 1.

저장소 루트에서: python3 .moai/tools/rules-diet/check.py
계산식은 t613 제안서(레인-2 의 measure.py)와 같다 (frontmatter·HTML 주석 제외 글자 수).
"""

import re
import sys

LIMIT = 150000
FILES = [
    "CLAUDE.md",
    ".moai/config/sections/user.yaml",
    ".moai/config/sections/language.yaml",
    ".claude/rules/moai/core/agent-common-protocol.md",
    ".claude/rules/moai/core/askuser-protocol.md",
    ".claude/rules/moai/core/moai-constitution.md",
    ".claude/rules/moai/core/native-idiom-and-register.md",
    ".claude/rules/moai/core/verification-claim-integrity.md",
    ".claude/rules/moai/workflow/cache-aware-execution.md",
    ".claude/rules/moai/workflow/context-window-management.md",
    ".claude/rules/moai/workflow/cross-session-messaging.md",
    ".claude/rules/moai/workflow/goal-directive.md",
    ".claude/rules/moai/workflow/kanban-dispatch.md",
    ".claude/rules/moai/workflow/main-checkout-branch-guard.md",
    ".claude/rules/moai/workflow/session-handoff.md",
    ".claude/rules/moai/workflow/skill-routing.md",
]


def counted(text):
    text = re.sub(r"\A---\n.*?\n---\n", "", text, count=1, flags=re.S)
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def main():
    total = 0
    for f in FILES:
        with open(f, encoding="utf-8") as fh:
            n = len(counted(fh.read()))
        total += n
        print(f"{n:>8}  {f}")
    ok = total <= LIMIT
    verdict = f"OK, margin {LIMIT - total}" if ok else f"FAIL, over by {total - LIMIT}"
    print(f"{total:>8}  TOTAL (limit {LIMIT}) -> {verdict}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
