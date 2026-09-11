"""t350 계기 8 — 갱신한 재고 튜플이 실제 hunk 시작점과 일치하는지 커밋 **전에** 본다.

트립와이어 검사 자신은 `git diff <base>..HEAD` 를 쓰므로 커밋 전에는 공허하다(계기 7의
🔴 항목). 이 계기는 검사가 비교할 두 값을 **직접** 맞춰 봐서, 커밋 뒤에야 알게 되는
불일치를 미리 잡는다. 튜플은 검사 모듈에서 읽고, 시작점은 git 에서 읽는다.
"""

from __future__ import annotations

import re
import subprocess
import sys

sys.path.insert(0, ".")

from server.tests.test_songcue_bundle import (
    _RUN_PHASE_BASE,
    _TOOLS_EXPECTED_HUNK_OLD_STARTS,
    _TOOLS_PATH,
)

HUNK_RE = re.compile(r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? \+\d+(?:,\d+)? @@")

result = subprocess.run(  # noqa: S603
    ["git", "diff", "--unified=0", f"{_RUN_PHASE_BASE}..HEAD", "--", _TOOLS_PATH],  # noqa: S607
    capture_output=True,
    text=True,
    check=True,
)
observed = tuple(
    int(m.group("old_start")) for line in result.stdout.splitlines() if (m := HUNK_RE.match(line))
)

print(f"git 이 답한 시작점 {len(observed)}개")
print(f"튜플이 든 시작점  {len(_TOOLS_EXPECTED_HUNK_OLD_STARTS)}개")
if observed == _TOOLS_EXPECTED_HUNK_OLD_STARTS:
    print("일치")
else:
    print("불일치 — 아래를 튜플에 반영해야 한다")
    print(
        "  튜플에만 있는 값: " + str(sorted(set(_TOOLS_EXPECTED_HUNK_OLD_STARTS) - set(observed)))
    )
    print(
        "  git 에만 있는 값: " + str(sorted(set(observed) - set(_TOOLS_EXPECTED_HUNK_OLD_STARTS)))
    )
    if sorted(observed) == sorted(_TOOLS_EXPECTED_HUNK_OLD_STARTS):
        print("  집합은 같고 **순서만** 다르다 — 튜플 정렬을 고쳐라")
    sys.exit(1)
