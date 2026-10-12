"""구현 후 look_reuse.json 에서 곡별 첫 큐 룩과 전체 쌍 충돌을 뽑는다(새 실행 없음)."""

import itertools
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
after = json.loads((HERE / "look_reuse.json").read_text("utf-8"))
before = json.loads((HERE / "look_reuse_before.json").read_text("utf-8"))


def look(c):
    return (c["position"], tuple(c["palette"]))


for key in ("fixed/same_session", "rotated/same_session"):
    print("##", key, "곡별 첫 큐 룩 (전 → 후)")
    for b, a in zip(before["runs"][key], after["runs"][key], strict=True):
        print(" ", a["song"], "|", look(b["cues"][0]), "→", look(a["cues"][0]))
    print("  전체 쌍 중 첫 큐가 같은 쌍:")
    rows = after["runs"][key]
    for x, y in itertools.combinations(range(len(rows)), 2):
        if look(rows[x]["cues"][0]) == look(rows[y]["cues"][0]):
            print("   ", rows[x]["song"], "(", x + 1, ")", "=", rows[y]["song"], "(", y + 1, ")")
    distinct = {look(c) for r in rows for c in r["cues"]}
    print("  8곡 전체 서로 다른 룩 수:", len(distinct))
    print("  이웃 쌍별 재사용:")
    for p in after["analysis"][key]["adjacent"]["pairs"]:
        print("   ", p["a"], "->", p["b"], p["b_cues_reusing_a_look"], "/", p["b_cues"])
