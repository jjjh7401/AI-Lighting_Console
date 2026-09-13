"""Seq 14 를 빈 실행기에 추가 배정한다 — 205(MST)는 건드리지 않는다.

문법 출처: server/fx/instantiate.py:662 `Assign Sequence <n> At Executor <m>`.
번호 규율: Page children 의 i 는 슬롯 인덱스, 실행기 번호 = i+100
(server/web/session.py:5602, 2026-08-16 콘솔 실측).
"""

from server.safety.bootstrap import build_console_stack

SEQ = 14
WANT = 206  # 205 바로 옆 빈 자리


class OneAssignOnly:
    def request_approval(self, request) -> bool:
        allowed = {f"Assign Sequence {SEQ} At Executor {WANT}"}
        for item in request.items:
            if item.command.strip() not in allowed:
                print(f"  🔴 범위 밖 거절: {item.command!r}")
                return False
        print(f"  승인: {[i.command for i in request.items]}")
        return True


stack = build_console_stack(receive_port=9005, approval_port=OneAssignOnly())
try:
    q = stack.gate.state_port.query_state
    r = q("DataPool/Pages/1")
    if r.get("truncated"):
        raise SystemExit("🔴 목록이 잘렸다 — 점유 확정 불가, 중단")
    taken = {c.get("i") + 100 for c in r.get("children", []) if c.get("i") is not None}
    print(f"점유된 실행기: {sorted(taken)} (childCount={r['node']['childCount']}, truncated=False)")
    if WANT in taken:
        raise SystemExit(f"🔴 Executor {WANT} 는 이미 점유 — 중단")

    cmd = f"Assign Sequence {SEQ} At Executor {WANT}"
    d = stack.gate.screen([cmd])
    print("게이트:", d.status, "cleared=", d.cleared)
    if not d.cleared:
        raise SystemExit("게이트 거절 — 중단")
    res = stack.gate.execution_port.execute(cmd)
    print("실행:", res)

    after = q("DataPool/Pages/1")
    print("\n=== 되읽기 ===")
    for c in after.get("children", []):
        i = c.get("i")
        nd = q(f"DataPool/Pages/1/{i}")["node"]
        print(f"  Executor {i + 100}: name={nd.get('name')!r} -> Sequence {nd.get('sequenceNo')}")
finally:
    stack.stop()
