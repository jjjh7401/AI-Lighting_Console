"""t186 프로브 2 — 이기는 자리를 줄 번호로 못박는다. 코드 수정 없이 line trace."""

import sys

sys.path.insert(0, ".")

from server.lxseq import group_mapper as gm
from server.lxseq.group_parser import LxseqGroupRecord

TARGET = gm.__file__
lines = []


def tracer(frame, event, arg):
    if frame.f_code.co_filename != TARGET:
        return None
    if event == "line":
        lines.append(frame.f_lineno)
    return tracer


DEAD = dict(reason="console_unreachable")
ROWS = (dict(Group="SPOT", FID="1"),)
RECS = (LxseqGroupRecord(group_no=1, name="SPOT", members_raw="", purpose=""),)


def trace_arm(complete):
    del lines[:]
    sys.settrace(tracer)
    gm.map_groups(
        group_records=RECS,
        patch_rows=ROWS,
        console_fids=(1,),
        console_fids_complete=complete,
        groups_section=DEAD,
    )
    sys.settrace(None)
    return [n for n in lines if n >= 255]


s1 = trace_arm(False)
s2 = trace_arm(True)
print("S1 map_groups 실행 줄 :", s1)
print("S1 마지막 줄(반환지점):", s1[-1])
print()
print("S2 map_groups 실행 줄 :", s2)
print("S2 가 382 에 닿았나  :", 382 in s2)
print("S1 이 382 에 닿았나  :", 382 in s1)
