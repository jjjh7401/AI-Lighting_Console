"""솔로 스팟 override look 을 실기 콘솔에 세운다 — 문서20 10.1.

안전 답 셋은 **내가 감독 위임으로 고른다**: Stop IFX/PFX 는 그 명령 문법을
이 저장소가 측정한 적이 없으므로 끈다(지어내지 않는다). MIB 는 표준 솔로
스팟이므로 켠다 — 다만 플래너에서 MIB 는 정보 항목이라 명령을 내지 않는다.
"""

from server.design.override_look import (
    OverrideSafetyAnswers,
    PointingTarget,
    plan_override_solo_spot,
)
from server.safety.bootstrap import build_console_stack

POOL = 22  # All 2 — 실측: childCount 0, truncated False (확정적 빈 풀)
FIX_PATH = "Patch/Stages/1/Fixtures/7"  # FOH 111


class ScopedApproval:
    def __init__(self, pool: int) -> None:
        self._pool = pool

    def request_approval(self, request) -> bool:
        for item in request.items:
            if f" {self._pool}." not in item.command:
                print(f"  🔴 범위 밖 거절: {item.command}")
                return False
        print(f"  승인 {len(request.items)}줄 — 전부 풀 {self._pool}")
        return True


stack = build_console_stack(receive_port=9005, approval_port=ScopedApproval(POOL))
try:
    p = stack.gate.state_port

    def prop(name: str) -> float:
        return float(p.query_property(FIX_PATH, name)["value"])

    fid = int(prop("FID"))
    xyz = (prop("Posx"), prop("Posy"), prop("Posz"))
    rotz = prop("Rotz")
    print(f"픽스처 {fid} @ {xyz} rotz={rotz}")

    pool_read = p.query_state(f"DataPool/PresetPools/{POOL}")
    occupied = frozenset(
        c.get("i") for c in pool_read.get("children", []) if c.get("i") is not None
    )
    print(f"풀 {POOL} 점유 {sorted(occupied) or '없음'} · truncated={pool_read.get('truncated')}")
    if pool_read.get("truncated"):
        raise SystemExit("🔴 목록이 잘렸다 — 점유를 확정할 수 없으므로 중단")

    plan = plan_override_solo_spot(
        fixtures=[(fid, xyz)],
        target=PointingTarget(0.0, 0.0, 1.2),  # 무대 중앙, 사람 높이
        safety=OverrideSafetyAnswers(stop_ifx=False, stop_pfx=False, move_in_black=True),
        pool_no=POOL,
        occupied_slots=occupied,
        zoom_degrees=8.0,
        label="Piano Solo",
        rotz_by_fid={fid: rotz},
    )
    print(f"\n슬롯 {plan.slot} · 명령 {len(plan.commands)}줄")
    for i, c in enumerate(plan.commands, 1):
        print(f"  {i}  {c}")

    d = stack.gate.screen(list(plan.commands))
    print("\n게이트:", d.status, "cleared=", d.cleared)
    if not d.cleared:
        raise SystemExit("게이트가 통과시키지 않았다 — 중단")
    ok = sum(
        1
        for c in plan.commands
        if getattr(stack.gate.execution_port.execute(c), "ok", True) is not False
    )
    print(f"발사 {ok}/{len(plan.commands)}")
finally:
    stack.stop()
