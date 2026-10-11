"""look_reuse.json 에서 판정서용 예시와 검산을 뽑는다(새 실행 없음)."""

import itertools
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
r = json.loads((HERE / "look_reuse.json").read_text("utf-8"))


def look(c):
    return (c["position"], tuple(c["palette"]))


print("## fixed/same_session 곡별 첫 큐 룩 · 서로 다른 룩 수")
for row in r["runs"]["fixed/same_session"]:
    looks = [look(c) for c in row["cues"]]
    print(row["song"], "|", looks[0], "| distinct", len(set(looks)), "/", len(looks))

print("\n## fixed 이웃 쌍별 다음 곡 재사용")
for p in r["analysis"]["fixed/same_session"]["adjacent"]["pairs"]:
    print(
        p["a"],
        "->",
        p["b"],
        p["b_cues_reusing_a_look"],
        "/",
        p["b_cues"],
        "shared distinct",
        p["shared_distinct"],
    )

print("\n## fixed 앞 곡 Club Diver -> Cut and Run 큐 대조(처음 6개)")
rows = r["runs"]["fixed/same_session"]
a, b = rows[0], rows[1]
sa = {look(c) for c in a["cues"]}
for c in b["cues"][:6]:
    print(c["no"], c["name"], look(c), "앞 곡에 있음" if look(c) in sa else "새 룩")

print("\n## fixed 8곡 전체에서 쓰인 서로 다른 룩 수")
print(len({look(c) for row in rows for c in row["cues"]}))

print("\n## rotated: 첫 큐 같은 쌍 = 같은 컨셉 쌍인가")
rot = r["runs"]["rotated/same_session"]
same_concept = 0
for x, y in itertools.combinations(rot, 2):
    sc = x["concept_answer"] == y["concept_answer"]
    so = look(x["cues"][0]) == look(y["cues"][0])
    same_concept += sc
    if sc != so:
        print("MISMATCH", x["song"], y["song"], sc, so)
print("same-concept pairs", same_concept)
for row in rot:
    print(row["song"], row["concept_answer"], look(row["cues"][0]))
