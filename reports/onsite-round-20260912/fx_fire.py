"""FX 3종을 실기 콘솔에 쏜다 — 특히 미검증 축 `At Relative` 가 실제로 도는지.

대상은 빈 시퀀스 자리 셋. MOVER 그룹을 쓴다(Pan 축이 있는 기종).
"""

from server.fx.instantiate import build_fx_bundle
from server.fx.loader import load_library_from_dir
from server.safety.bootstrap import build_console_stack

WANT = ["chase-horizontal", "chase-bounce-run", "sweep-vshape-swing"]
SLOTS = {"chase-horizontal": 11, "chase-bounce-run": 12, "sweep-vshape-swing": 13}


class ScopedApproval:
    """감독이 이 회차의 승인을 위임했다. 대상 시퀀스 밖이면 거절한다."""

    def __init__(self, allowed: set[int]) -> None:
        self._allowed = {f"Sequence {n} " for n in allowed}
        self._allowed_bare = {f"Sequence {n}" for n in allowed}

    def request_approval(self, request) -> bool:
        for item in request.items:
            if not any(
                item.command.startswith(("Store " + a, "Label " + a)) for a in self._allowed
            ) and not any(
                item.command.startswith(("Store " + a, "Label " + a)) for a in self._allowed_bare
            ):
                print(f"  🔴 범위 밖 거절: {item.command}")
                return False
        print(f"  승인 {len(request.items)}줄")
        return True


lib = load_library_from_dir()
by_id = {f.fx_id: f for f in lib.fx}
missing = [w for w in WANT if w not in by_id]
if missing:
    raise SystemExit(f"라이브러리에 없다: {missing}")

stack = build_console_stack(receive_port=9005, approval_port=ScopedApproval(set(SLOTS.values())))
try:
    q = stack.gate.state_port.query_state
    used = {c.get("i") for c in q("DataPool/Sequences").get("children", [])}
    groups = {str(c.get("name")): c.get("i") for c in q("DataPool/Groups").get("children", [])}
    gnum = groups.get("MOVER-ALL")
    print(f"MOVER-ALL = Group {gnum} · 이미 쓰는 시퀀스 {sorted(x for x in used if x)}")

    for fx_id in WANT:
        slot = SLOTS[fx_id]
        print(f"\n=== {fx_id} → Sequence {slot} ===")
        if slot in used:
            print("  🔴 자리가 차 있다 — 건너뜀")
            continue
        inst = build_fx_bundle(by_id[fx_id], group=gnum, sequence=slot, label=fx_id)
        cmds = list(inst.commands)
        print(f"  명령 {len(cmds)}줄, Step 2 포함: {'Step 2' in cmds}")
        d = stack.gate.screen(cmds)
        if not d.cleared:
            print("  🔴 게이트 거절:", d.status)
            continue
        ok = sum(
            1
            for c in cmds
            if getattr(stack.gate.execution_port.execute(c), "ok", True) is not False
        )
        print(f"  발사 {ok}/{len(cmds)}")
finally:
    stack.stop()
