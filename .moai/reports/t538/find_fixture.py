"""t525 패치 트리 판독에서 FID 501·508 의 콘솔 경로를 찾는다(파일 읽기만).

실행: uv run python .moai/reports/t538/find_fixture.py
"""

import json

tree = json.load(open(".moai/reports/t525/r4_patch_tree.json", encoding="utf-8"))


def walk(nodes):
    for node in nodes:
        reads = {r["n"]: r.get("v") for r in node.get("reads", [])}
        if reads.get("FID") in ("501", "508", "521"):
            print(reads.get("FID"), node.get("path"), node.get("name"), node.get("class"))
        if isinstance(node.get("children"), list):
            walk(node["children"])


walk(tree["tree"])
