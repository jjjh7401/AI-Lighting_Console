"""t538 B1 반복 보기 — 승인 문면 안의 두 줄만 번갈아 보낸다(새 줄 0, 쇼 저장 0).

감독 요청(리드 경유 2026-10-10): 「이동하는 건 못 봤어 — 큐1→큐2 를 반복해서 보여줘」.
`Goto Cue 1 Sequence 320` → 3초 → `Goto Cue 2 Sequence 320` → 3초, 5회. 끝나면 큐2 상태로 둔다.
승인은 v3 전부-거절 목록(approval_t538_v3.txt 와 같은 문면)에 고정 — 목록 밖 줄이면 게이트가 거절한다.

실행: uv run python .moai/reports/t538/b1_repeat.py <out> [<큐a>-<큐b>x<횟수> ...]
  인자 없으면 1-2x5(처음 요청). `w<초>` 로 간격을 바꾼다(기본 3초). 예: 2-3x3 3-4x3 → 큐2↔큐3 3회, 쉼 5초, 큐3↔큐4 3회. 각 쌍은 b 큐에서 끝난다.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t531")
import m1_common  # noqa: E402
from m1_common import LISTEN_PORT, LinkTimeouts, Probe, RecordingApproval  # noqa: E402

from server.safety.bootstrap import build_console_stack  # noqa: E402
from server.tools.probe_preflight import preflight  # noqa: E402

WAIT = 3.0
PAIR_GAP = 5.0


def goto(cue: int) -> list[str]:
    return [f"Goto Cue {cue} Sequence 320"]


def parse_pairs(args: list[str]) -> list[tuple[int, int, int]]:
    pairs = []
    for arg in args or ["1-2x5"]:
        span, _, cycles = arg.partition("x")
        a, _, b = span.partition("-")
        pairs.append((int(a), int(b), int(cycles)))
    return pairs


def main() -> int:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    global WAIT
    args = sys.argv[2:]
    for arg in [a for a in args if a.startswith("w")]:  # 예: w4 → 간격 4초
        WAIT = float(arg[1:])
    pairs = parse_pairs([a for a in args if not a.startswith("w")])
    pinned = [
        r["commands"]
        for r in json.loads(Path(".moai/reports/t538/v3_denyall/approvals.json").read_text("utf-8"))
    ]
    for a, b, _ in pairs:
        assert goto(a) in pinned and goto(b) in pinned, f"큐 {a}/{b} 줄이 승인 목록에 없다"
    m1_common.tc_probe.RISK = m1_common.BatchRisk(
        reason="t538 B1 반복 보기 — 승인 문면 Goto 두 줄만", kind="t538_b1_repeat"
    )
    approval = RecordingApproval(pinned)
    skipped: list[str] = []
    stack = build_console_stack(
        send_host="127.0.0.1",
        send_port=8000,
        receive_host="127.0.0.1",
        receive_port=LISTEN_PORT,
        approval_port=approval,
        audit_dir=out / "audit",
        timeouts=LinkTimeouts(state_query_seconds=6.0),
        attempt_session_backup=False,
    )
    stack.backup._backup_action = lambda: skipped.append("SaveShow skipped (supervisor)")
    marks = []
    try:
        health = preflight(
            stack.gate, receive_host="127.0.0.1", receive_port=LISTEN_PORT, console_port=8000
        )
        if health.get("verdict") != "responder_ok":
            print(json.dumps(dict(preflight=health), ensure_ascii=False))
            return 1
        probe = Probe(stack.gate, out)
        t0 = time.monotonic()
        for p, (a, b, cycles) in enumerate(pairs):
            if p:
                time.sleep(PAIR_GAP)
            for n in range(1, cycles + 1):
                for cue in (a, b):
                    label = f"c{cue}_{a}{b}_{n}"
                    ok = probe.fire(label, goto(cue))
                    marks.append(dict(label=label, ok=ok, t=round(time.monotonic() - t0, 2)))
                    if not ok:
                        raise SystemExit(f"stopped at {label}")
                    time.sleep(WAIT)
    finally:
        stack.stop()
    result = dict(marks=marks, approval_requests=approval.requests, skipped_saveshow=skipped)
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
    with (out / "steps.jsonl").open("w", encoding="utf-8") as handle:
        for row in probe.log:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    print(json.dumps(marks, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
