"""t186 프로브 3 — 방향 판정용. 두 팔의 쓰기 계획(batches)이 실제로 같은가."""

import sys

sys.path.insert(0, ".")

from server.lxseq import group_mapper as gm
from server.lxseq.group_parser import LxseqGroupRecord

DEAD = dict(reason="console_unreachable")
ROWS = (dict(Group="SPOT", FID="1"),)
RECS = (LxseqGroupRecord(group_no=1, name="SPOT", members_raw="", purpose=""),)


for label, complete in (("S1", False), ("S2", True)):
    r = gm.map_groups(
        group_records=RECS,
        patch_rows=ROWS,
        console_fids=(1,),
        console_fids_complete=complete,
        groups_section=DEAD,
    )
    print(
        label, "batches =", r.batches, "| 배치수 =", len(r.batches), "| refusal =", repr(r.refusal)
    )
