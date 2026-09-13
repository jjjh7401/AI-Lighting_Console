"""Page children 의 i 는 페이지 슬롯 인덱스다 — 실행기 번호는 i+100.

출처: server/web/session.py:5602 `_page_one_executors` 독스트링(2026-08-16 콘솔 실측).
이 스크립트는 그 매핑을 지켜 읽고, 빈 실행기 자리를 찾는다. 콘솔 쓰기 0.
"""

from server.safety.bootstrap import build_console_stack

SLOT_TO_EXEC = 100  # i + 100 = 실행기 번호

stack = build_console_stack(receive_port=9005)
try:
    q = stack.gate.state_port.query_state
    r = q("DataPool/Pages/1")
    node = r.get("node", {})
    print(f"Page 1 childCount={node.get('childCount')} truncated={r.get('truncated')}")
    if r.get("truncated"):
        print("🔴 잘린 목록 — 점유를 확정할 수 없다")
    taken: dict[int, tuple[str, int | None]] = {}
    for c in r.get("children", []):
        i = c.get("i")
        if i is None:
            print(f"  슬롯 미확정: {c.get('name')!r} — 번호를 못 읽었다")
            continue
        detail = q(f"DataPool/Pages/1/{i}")["node"]
        taken[i + SLOT_TO_EXEC] = (detail.get("name"), detail.get("sequenceNo"))
    print("\n점유된 실행기 (i+100 적용):")
    for ex, (nm, sq) in sorted(taken.items()):
        print(f"  Executor {ex}  name={nm!r}  -> Sequence {sq}")
    print(
        "\n🔴 내가 앞서 '105' 라고 적은 것은 슬롯 인덱스였고 실행기 번호는",
        sorted(taken)[0] if taken else "—",
    )
finally:
    stack.stop()
