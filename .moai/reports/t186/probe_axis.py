"""t186 1단계 프로브 — map_groups 안에서 FID 축이 섹션 축을 어디서 이기는가.

세 팔. 자극은 한 축(console_fids_complete)만 건드린다 — groups_section 은 세 팔 중
S1/S2 에서 바이트 동일이다. S3 는 계기가 눈멀지 않았음을 보이는 양성 대조군.
"""

import sys

sys.path.insert(0, ".")

from server.lxseq import group_mapper as gm
from server.lxseq.group_parser import LxseqGroupRecord

calls = []
real = gm.section_refusal


def spy(section):
    out = real(section)
    calls.append(out)
    return out


gm.section_refusal = spy

DEAD = dict(reason="console_unreachable")
HEALTHY = dict(objects=[], truncated=False)
ROWS = (dict(Group="SPOT", FID="1"),)
RECS = (LxseqGroupRecord(group_no=1, name="SPOT", members_raw="", purpose=""),)


def run(complete, section):
    del calls[:]
    result = gm.map_groups(
        group_records=RECS,
        patch_rows=ROWS,
        console_fids=(1,),
        console_fids_complete=complete,
        groups_section=section,
    )
    return result, list(calls)


ARMS = (
    ("S1  FID축 시끄러움 + 단면 죽음", False, DEAD),
    ("S2  FID축 조용함  + 단면 죽음", True, DEAD),
    ("S3  FID축 조용함  + 단면 정상", True, HEALTHY),
)

for label, complete, section in ARMS:
    result, seen = run(complete, section)
    print("=== " + label)
    print("    console_fids_complete :", complete)
    print("    console_read_incomplete:", result.console_read_incomplete)
    print("    refusal               :", repr(result.refusal))
    print("    refusal_detail        :", repr(result.refusal_detail))
    print("    section_refusal 호출수 :", len(seen))
    print("    section_refusal 반환   :", seen)
    print()
