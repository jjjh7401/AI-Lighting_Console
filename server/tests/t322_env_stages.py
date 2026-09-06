"""t322 (a) 두 번째 축 — **환경 상태** 단계가 seal-only 번들을 세우는가.

첫 스크립트(`t322_stage_audit`)는 번들 내용에 붙는 단계(grammar / classify /
expand)만 쟀다. 게이트에는 번들과 무관하게 도는 단계가 셋 더 있다:
health(`_check_health`) · lock(`_check_lock`) · unconfirmed 이력.

이 셋은 「봉합의 대체 방어인가」라는 물음에 다르게 답한다 — 세우기는
세우는데, **그 번들이라서** 세우는 게 아니다. 그래서 재는 것은 「세우는가」와
「가려서 세우는가」 둘이다: 같은 조건에서 blacklist 든 번들도 똑같이 서면
그 단계는 봉합의 대체가 아니라 전원 차단기다.

실행: uv run python -m server.tests.t322_env_stages
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate

from .test_web_session import FakeConsole
from .test_writegate_session_sites import SITES, _build, _Channel

_SEAL_ONLY = "_position_cue_store"
_REDUNDANT = "run_look_bundle"


def _bundle(tmp_path, name) -> list[str]:
    drive = next(d for n, d, _ in SITES if n == name)
    session, _c, _a, channel = _build(tmp_path, verdict=True)
    drive(session)
    return [i.command for r in channel.requests for i in r.items]


def _gate(tmp_path, tag):
    return SafetyGate(
        console=FakeConsole(),
        audit=AuditLog(tmp_path / f"audit-{tag}"),
        approval_port=_Channel(True),
    )


def main() -> int:
    rows = []
    with tempfile.TemporaryDirectory() as root:
        tmp = Path(root)
        (tmp / "a").mkdir()
        (tmp / "b").mkdir()
        bundles = {
            _SEAL_ONLY: _bundle(tmp / "a", _SEAL_ONLY),
            _REDUNDANT: _bundle(tmp / "b", _REDUNDANT),
        }
        for site, bundle in bundles.items():
            for scenario in ("baseline", "lock_active", "console_offline", "unconfirmed_seeded"):
                gate = _gate(tmp, f"{site}-{scenario}")
                if scenario == "lock_active":
                    gate.lock.activate()
                elif scenario == "console_offline":
                    for _ in range(10):
                        gate.monitor.note_ping_timeout()
                elif scenario == "unconfirmed_seeded":
                    for command in bundle:
                        gate._remember_unconfirmed(command)
                decision = gate.screen(bundle, risk=None)
                rows.append(
                    {
                        "site": site,
                        "scenario": scenario,
                        "monitor_state": gate.monitor.state,
                        "status": decision.status,
                        "cleared": decision.cleared,
                        "card": decision.approval_request is not None,
                        "held": (
                            [i.command for i in decision.approval_request.items]
                            if decision.approval_request
                            else []
                        ),
                    }
                )
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
