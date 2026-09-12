"""항목 순서 실측 — `_match_blacklist` 는 첫 일치를 돌려주므로, 동사를 공유하는
기존 항목(`Set Fixture`)과의 배치 순서가 귀속(matched_entry)을 바꾸는지 잰다.

v7 은 `Store Cue` 가 `Store Sequence` 와 동사를 공유해서 순서가 의미를 가졌고,
v8 은 동사가 겹치지 않아 무관했다. 이 리비전은 동사가 겹치는 쪽이므로 v7 과 같은
검사를 돌린다 — 다만 겹치는 것은 동사뿐이고 오브젝트 키워드가 다르다.
"""

import dataclasses

from server.safety.classify import classify_command
from server.safety.grammar import validate
from server.safety.ruleset import load_ruleset

base = load_ruleset()
NEW = "Set Layout"

tail = dataclasses.replace(base, version=9, blacklist=base.blacklist + (NEW,))
# 새 항목을 맨 앞으로 — `Set Fixture` 보다 먼저 만나게 한다.
head = dataclasses.replace(base, version=9, blacklist=(NEW,) + base.blacklist)

PROBES = [
    "Set Layout 1.1 'PositionX' 5.0",
    "Set Layout 1.1 'PositionY' 5.0",
    "Set Fixture 11 Posx '5.0'",
    "Set Fixture 11 Rotx '90.0'",
    "Set Fix 11 Posx '1.0'",
    "Set Fixture 1 Thru 18 Posz '5.0'",
    "Set Fixture 11 Name 'Spot 11'",
    # 두 오브젝트 키워드가 같은 줄에 있는 교차 형태 — 귀속이 순서에 의존하는지
    # 드러나는 유일한 자리다.
    "Set Fixture 11 Layout 3",
    "Set Layout 1.1 Fixture 11",
    "Set Selection MAtricks 'PhaseFromX' 0",
    "Store Page 3",
    "Copy Page 1 At Page 4",
    "Assign Preset 4.1 At Executor 101",
    "Label Group 3 'Vocals'",
    "Group 4",
    "At 100",
]


def verdict(cmd, rs):
    g = validate(cmd)
    if not g.ok:
        return ("PARSE-FAIL", None)
    f = classify_command(g.parsed, rs)
    return (f.category, f.matched_entry)


moved = 0
for c in PROBES:
    t, h = verdict(c, tail), verdict(c, head)
    flag = "SAME" if t == h else "*** MOVED ***"
    if t != h:
        moved += 1
    print(f"{c:40s} tail={str(t):32s} head={str(h):32s} {flag}")
print()
print(f"귀속이 움직인 줄: {moved}건")
verbs = {e.split()[0] for e in base.blacklist}
print(f"기존 항목 동사 집합: {sorted(verbs)}")
print(f"새 항목 동사 `{NEW.split()[0]}` 교차: {'YES' if NEW.split()[0] in verbs else 'NO'}")
print(f"동사를 공유하는 기존 항목: {[e for e in base.blacklist if e.split()[0] == NEW.split()[0]]}")
