"""t299 Phase 2 — `SEAL_DEFENCE` 귀속을 **재서** 표를 채운다.

Phase 1 의 `probe_seal_defence.py` 는 「표와 실측이 같은가」를 물으므로 표에 없는
자리에서 `KeyError` 로 멈춘다. Phase 2 는 자리를 하나 **추가**하므로(반영 자리가
봉합이 됐다) 표에 없는 자리를 먼저 재야 한다 — 손으로 더하지 않고.

그래서 이 프로브는 비교를 하지 않고 **측정만** 한다. 표에 없는 자리는
`(표 없음)` 으로 찍고, 마지막에 `SEAL_DEFENCE` 에 그대로 붙여 쓸 수 있는 형태로
전체를 출력한다.

실행:  uv run python reports/classifygap-t299-p2/probe_seal_defence_p2.py
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
    print(f"자리 수      : {len(SITES)}")
    print(f"blacklist   : {list(rs.blacklist)}\n")

    measured_all: dict[str, str] = {}
    seal_only_now = 0
    for name, drive, _kind in SITES:
        tmp = Path(tempfile.mkdtemp(prefix="t299p2-seal-"))
        session, _console, _audit, channel = _build(tmp, verdict=True)
        drive(session)
        carried = [item.command for request in channel.requests for item in request.items]
        verdicts = _classify_carried(session._gate, carried)
        risky = [v for v in verdicts if v.risky]
        measured = "redundant" if risky else "seal-only"
        measured_all[name] = measured
        if measured == "seal-only":
            seal_only_now += 1
        recorded = SEAL_DEFENCE.get(name, "(표 없음)")
        flag = "" if measured == recorded else "  <<< 표와 다름"
        print(f"{name:32} 표={recorded:10} 실측={measured:10}{flag}")
        print(f"    카드에 실린 줄 수 : {len(carried)}")
        print(f"    나가는 쇼파일 쓰기: {_showfile(carried)}")
        print(
            f"    잡힌 항목        : {sorted({v.matched_entry for v in risky if v.matched_entry})}"
        )

    print(f"\nseal-only (실측)  : {seal_only_now} / {len(SITES)}")
    print(f"seal-only (표)    : {sum(1 for v in SEAL_DEFENCE.values() if v == 'seal-only')}")
    print("\n--- SEAL_DEFENCE 에 붙여 쓸 실측값 ---")
    for name, _drive, _kind in SITES:
        print(f'    "{name}": "{measured_all[name]}",')


if __name__ == "__main__":
    main()
