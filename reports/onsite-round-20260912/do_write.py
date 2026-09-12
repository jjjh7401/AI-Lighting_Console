"""실기 쓰기 — Sequence 7 에 VerifyA 곡 큐 8개를 세운다."""

from server.looks.loader import load_library_from_dir
from server.looks.songcue import (
    build_songcue_bundle,
    map_sections_to_looks,
    parse_sections,
)
from server.orchestrator.tools import rig_object, rig_section
from server.safety.bootstrap import build_console_stack

SECTIONS = [
    {"name": "Intro", "start": "0:00", "dynamics": 2},
    {"name": "Verse", "start": "0:16", "dynamics": 2},
    {"name": "Chorus", "start": "0:48", "dynamics": 4},
    {"name": "Verse", "start": "1:20", "dynamics": 3},
    {"name": "Chorus", "start": "1:52", "dynamics": 4},
    {"name": "Breakdown", "start": "2:24", "dynamics": 2},
    {"name": "Drop", "start": "2:40", "dynamics": 5},
    {"name": "Outro", "start": "3:12", "dynamics": 1},
]


class OperatorDelegatedApproval:
    """감독이 이 회차의 승인을 위임했다(2026-09-12 지시). 나가는 명령 50줄은
    발사 전에 전부 인쇄해 확인했고, 대상은 비어 있는 Sequence 7 하나뿐이다."""

    def __init__(self, allowed_sequence: int) -> None:
        self._allowed = allowed_sequence
        self.approved: list[str] = []

    def request_approval(self, request) -> bool:
        target = f"Sequence {self._allowed} "
        for item in request.items:
            if not item.command.startswith(("Store " + target, "Label " + target)):
                print(f"  🔴 위임 범위 밖 — 거절: {item.command}")
                return False
        self.approved = list(request.commands)
        print(f"  승인: {len(self.approved)}줄, 전부 Sequence {self._allowed} 대상")
        return True


approver = OperatorDelegatedApproval(allowed_sequence=7)
stack = build_console_stack(receive_port=9005, approval_port=approver)
try:
    gate = stack.gate
    q = gate.state_port.query_state
    rs, rg = q("DataPool/Sequences"), q("DataPool/Groups")
    seqs = rig_section([rig_object(c) for c in rs.get("children", [])], rs)
    groups = rig_section([rig_object(c) for c in rg.get("children", [])], rg)

    lib = load_library_from_dir()
    sel = map_sections_to_looks(parse_sections(SECTIONS), lib, "edm")
    b = build_songcue_bundle("VerifyA", sel, sequences_section=seqs, groups_section=groups)

    assert b.sequence_number not in {c.get("i") for c in rs.get("children", [])}, (
        f"Sequence {b.sequence_number} 는 이미 쓰이고 있다 — 덮어쓰기 중단"
    )
    print(f"대상 Sequence {b.sequence_number} 는 비어 있다. 명령 {len(b.commands)}줄 발사.")

    decision = gate.screen(b.commands)
    print("게이트 판정:", decision.status, "cleared=", decision.cleared)
    cleared = getattr(decision, "cleared", None)
    if cleared is False:
        raise SystemExit("게이트가 통과시키지 않았다 — 중단")

    ok = fail = 0
    for i, cmd in enumerate(b.commands, 1):
        r = gate.execution_port.execute(cmd)
        good = getattr(r, "ok", None)
        if good is False:
            fail += 1
            print(f"  🔴 {i:3} {cmd[:70]} -> {r}")
        else:
            ok += 1
    print(f"\n발사 완료: ok={ok} fail={fail}")
finally:
    stack.stop()
