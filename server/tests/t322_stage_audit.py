"""t322 (a) — 봉합을 뗀 번들을 게이트에 통째로 넣고 **단계별로** 무엇이 잡는지 잰다.

t321 은 「분류 층이 잡는가」 하나만 봤다(`verdict.risky`). 이 스크립트는
같은 번들을 **실제 게이트**(`SafetyGate.screen(..., risk=None)`)에 넣고,
파이프라인의 각 단계가 독립으로 그 번들을 세우는지를 관측한다:

    health → grammar → classify(blacklist) → expand → unconfirmed → lock → approval → backup

읽어서 추론하지 않는다 — 넣고, 나온 것을 적는다.

실행: uv run python -m server.tests.t322_stage_audit
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from server.safety.audit import AuditLog
from server.safety.classify import RECOGNIZED_REFERENCE_TYPES, classify_command
from server.safety.console import ConsolePort  # noqa: F401  (문서용)
from server.safety.expand import evaluate_reference
from server.safety.gate import SafetyGate
from server.safety.grammar import validate

from .test_web_session import FakeConsole
from .test_writegate_session_sites import SEAL_DEFENCE, SITES, _build, _Channel


def _capture_bundle(tmp_path, drive) -> list[str]:
    """선언이 붙은 채로 몰아서, 카드에 실린 줄(= 나갈 번들)을 뽑는다."""
    session, _console, _audit, channel = _build(tmp_path, verdict=True)
    drive(session)
    return [item.command for request in channel.requests for item in request.items]


def _fresh_gate(tmp_path, verdict: bool = True):
    channel = _Channel(verdict)
    gate = SafetyGate(
        console=FakeConsole(),
        audit=AuditLog(tmp_path / "audit2"),
        approval_port=channel,
    )
    return gate, channel


def _stage_probe(gate, commands: list[str]) -> dict:
    """단계마다 독립으로 무엇을 잡는지 — 게이트가 쓰는 그 함수에 그대로 물어본다."""
    per_command = []
    for command in commands:
        g = validate(command)
        row = {
            "command": command,
            "grammar_ok": bool(g.ok),
            "grammar_reason": "" if g.ok else g.reason,
            "classify_risky": None,
            "classify_category": None,
            "expand_hold": False,
            "expand_reasons": [],
            "unspecified_target": None,
        }
        if g.ok and g.parsed is not None:
            v = classify_command(
                g.parsed, gate._ruleset, reference_types=RECOGNIZED_REFERENCE_TYPES
            )
            row["classify_risky"] = bool(v.risky)
            row["classify_category"] = v.category
            row["unspecified_target"] = bool(v.unspecified_target)
            if v.category == "invoking":
                e = evaluate_reference(
                    v.reference,
                    ruleset=gate._ruleset,
                    fetcher=gate._body_fetcher,
                    plugin_registry=gate._plugin_registry,
                )
                row["expand_hold"] = bool(e.hold)
                row["expand_reasons"] = list(e.reasons)
        per_command.append(row)
    return per_command


def main() -> int:
    out = []
    with tempfile.TemporaryDirectory() as root:
        for name, drive, kind in SITES:
            tmp = Path(root) / name
            tmp.mkdir(parents=True, exist_ok=True)
            bundle = _capture_bundle(tmp, drive)

            # 봉합을 뗀 번들을 **게이트에 통째로** 넣는다 (risk=None).
            gate, channel = _fresh_gate(tmp)
            stages: list[str] = []
            gate._stage_observer = stages.append
            decision = gate.screen(bundle, risk=None)

            probe = _stage_probe(gate, bundle)
            out.append(
                {
                    "site": name,
                    "kind": kind,
                    "recorded": SEAL_DEFENCE[name],
                    "bundle": bundle,
                    "screen_without_seal": {
                        "cleared": decision.cleared,
                        "status": decision.status,
                        "approval_request": decision.approval_request is not None,
                        "held_commands": (
                            [i.command for i in decision.approval_request.items]
                            if decision.approval_request
                            else []
                        ),
                        "stages_observed": stages,
                        "notice": decision.notice,
                    },
                    "per_command": probe,
                }
            )

    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
