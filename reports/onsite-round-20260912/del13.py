"""Seq 13 을 지운다 — Executor 105 가 가리키던 자리를 원래대로 비운다.

감독 승인 2026-09-13: "Seq 13 만 지워라". 대상은 정확히 하나다.
"""

from server.safety.bootstrap import build_console_stack

TARGET = 13


class OneSequenceOnly:
    """정확히 Sequence 13 을 지우는 명령만 승인한다."""

    def request_approval(self, request) -> bool:
        allowed = {f"Delete Sequence {TARGET}"}
        for item in request.items:
            if item.command.strip() not in allowed:
                print(f"  🔴 범위 밖 거절: {item.command!r}")
                return False
        print(f"  승인: {[i.command for i in request.items]}")
        return True


stack = build_console_stack(receive_port=9005, approval_port=OneSequenceOnly())
try:
    q = stack.gate.state_port.query_state
    before = {c.get("i"): c.get("name") for c in q("DataPool/Sequences").get("children", [])}
    print("지우기 전 13번:", before.get(TARGET))
    if TARGET not in before:
        raise SystemExit("13번이 이미 없다 — 중단")

    cmd = f"Delete Sequence {TARGET}"
    d = stack.gate.screen([cmd])
    print("게이트:", d.status, "cleared=", d.cleared)
    if not d.cleared:
        raise SystemExit("게이트가 통과시키지 않았다 — 중단")
    r = stack.gate.execution_port.execute(cmd)
    print("실행 결과 전체:", r)
    for f in ("ok", "error", "reason", "detail", "message", "response", "raw"):
        if hasattr(r, f):
            print(f"   {f}: {getattr(r, f)!r}")

    after = {c.get("i"): c.get("name") for c in q("DataPool/Sequences").get("children", [])}
    print("\n=== 되읽기 ===")
    print("남은 시퀀스:", sorted(k for k in after if k))
    print(f"13번 존재: {TARGET in after}")
    e = q("DataPool/Pages/1/105")
    print("Executor 105:", e.get("node"))
finally:
    stack.stop()
