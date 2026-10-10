"""그룹 11 sf_index(r3_group11.txt) → fid, t525 패치 트리 판독(r4_patch_tree.json)으로 맞춘다.

읽기만 한다(파일 두 개). 실행: uv run python .moai/reports/t538/map_group11.py
"""

import json

tree = json.load(open(".moai/reports/t525/r4_patch_tree.json", encoding="utf-8"))
group = json.loads(open(".moai/reports/t538/r3_group11.txt", encoding="utf-8").read().strip().splitlines()[-1])
wanted = {m["sf_index"] for m in group["members"]}

index = {}


def walk(nodes):
    for node in nodes:
        reads = {r["n"]: r.get("v") for r in node.get("reads", [])}
        if reads.get("SUBFIXTUREINDEX") is not None:
            index[int(reads["SUBFIXTUREINDEX"])] = (reads.get("FID"), reads.get("NAME"))
        children = node.get("children")
        if isinstance(children, list):
            walk(children)


walk(tree["tree"])
for sf in sorted(wanted):
    print(sf, index.get(sf, "NOT FOUND"))
