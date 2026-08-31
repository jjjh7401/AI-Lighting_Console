"""t186 2단계 프로브 — S1/S2/S3 가 **최종 페이로드**에서 갈리는가.

리드 지시: 재야 할 것은 GroupMapResult 가 아니라 페이로드다.
기존 t182 하네스를 그대로 쓴다 — 새 계기를 만들면 그 계기부터 검증해야 한다(규약 §3.6).
S1 은 FID 루트를 StateQueryError 로 죽이고(_RaisingFixtureRoot) 동시에 groups 단면을
죽인다(_DEAD_GROUPS). 실물에서 일어나는 조합이라고 그 하네스 독스트링이 적어뒀다.
"""

import json
import sys

sys.path.insert(0, ".")

from server.safety.console import StateQueryError
from server.tests.test_lxseq_group_section_request import (
    _DEAD_GROUPS,
    _Console,
    _dispatch,
    _patch_fids,
    _RaisingFixtureRoot,
)

KEYS = ("console_read_incomplete", "console_read_reason", "refusal", "refusal_detail")


def payload_of(port):
    execution = _dispatch(port)
    if execution.result.is_error:
        return None
    return json.loads(execution.result.content)


def arm_s1():
    return _RaisingFixtureRoot(_Console(_patch_fids(), dead=_DEAD_GROUPS), StateQueryError)


def arm_s2():
    return _Console(_patch_fids(), dead=_DEAD_GROUPS)


def arm_s3():
    return _Console(_patch_fids())


shots = []
for label, builder in (("S1", arm_s1), ("S2", arm_s2), ("S3", arm_s3)):
    p = payload_of(builder())
    print("=== " + label)
    if p is None:
        print("    도구가 오류를 냈다")
        shots.append(None)
        continue
    slim = dict((k, p.get(k)) for k in KEYS)
    slim["batches_len"] = len(p.get("batches") or [])
    for k in KEYS:
        print("    " + k + " :", repr(slim[k]))
    print("    batches 수 :", slim["batches_len"])
    shots.append(slim)
    print()

print("=== 판정")
print("S1 == S2 (네 필드) :", shots[0] == shots[1])
print("S1 == S3 (네 필드) :", shots[0] == shots[2])
if shots[0] is not None and shots[1] is not None:
    diff = [k for k in shots[0] if shots[0][k] != shots[1][k]]
    print("S1/S2 가 갈리는 필드 :", diff)
