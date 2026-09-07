"""t299 Phase 1 — `SEAL_DEFENCE` 귀속을 다시 재고, 왜 안 움직였는지까지 찍는다.

`test_writegate_session_sites.py` 의 검사는 「표와 실측이 같은가」만 답한다.
AC-CG-005 는 「seal-only 수가 줄었는가」를 묻는데, 안 줄었을 때 **왜**인지는
그 검사가 말해 주지 않는다. 그래서 자리마다 나가는 줄과 잡힌 항목을 직접 찍는다.

실행:  uv run python reports/classifygap-t299-p1/probe_seal_defence.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import server
from server.safety.ruleset import load_ruleset
from server.tests.test_writegate_session_sites import (
    SEAL_DEFENCE,
    SITES,
    _build,
    _classify_carried,
    _showfile,
)


def main() -> None:
    rs = load_ruleset()
    print(f"interpreter : {sys.version.split()[0]}")
    print(f"server pkg  : {server.__file__}")
    print(f"ruleset ver : {rs.version}")
    print(f"blacklist   : {list(rs.blacklist)}\n")

    moved: list[str] = []
    seal_only_now = 0
    for name, drive, _kind in SITES:
        tmp = Path(tempfile.mkdtemp(prefix="t299p1-seal-"))
        session, _console, _audit, channel = _build(tmp, verdict=True)
        drive(session)
        carried = [item.command for request in channel.requests for item in request.items]
        verdicts = _classify_carried(session._gate, carried)
        risky = [v for v in verdicts if v.risky]
        measured = "redundant" if risky else "seal-only"
        if measured == "seal-only":
            seal_only_now += 1
        recorded = SEAL_DEFENCE[name]
        flag = "" if measured == recorded else "  <<< MOVED"
        if flag:
            moved.append(name)
        print(f"{name:38} 표={recorded:10} 실측={measured:10}{flag}")
        print(f"    나가는 쇼파일 쓰기: {_showfile(carried)}")
        print(
            f"    잡힌 항목        : {sorted({v.matched_entry for v in risky if v.matched_entry})}"
        )

    print(f"\nseal-only (실측)  : {seal_only_now}")
    print(f"seal-only (표)    : {sum(1 for v in SEAL_DEFENCE.values() if v == 'seal-only')}")
    print(f"귀속이 움직인 자리: {moved}")


if __name__ == "__main__":
    main()
