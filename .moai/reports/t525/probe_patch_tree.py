"""t525 — 읽기 전용: 패치 트리(픽스처와 서브픽스처)를 끝까지 걸어 순서·fid·자식 수를 기록한다.

목적: 그룹 SELECTIONDATA 의 sf_index 가 어느 fid 인지 대응표를 만들 근거.
보내는 것: ping / state / props 만.

실행 (프로젝트 루트에서):
    .venv/bin/python .moai/reports/t525/probe_patch_tree.py > .moai/reports/t525/r4_patch_tree.json
"""

import json
import sys

sys.path.insert(0, ".")
from server.bridge.osc import BridgeConfig, OscBridge  # noqa: E402
from server.safety.console import ConsoleLink, StateQueryError  # noqa: E402

ROOT = "Patch/Stages/1/Fixtures"


def children(link, path):
    """state 를 offset 으로 넘기며 자식 전부를 모은다."""
    out, offset = [], 0
    while True:
        reply = link.query_state(path, offset=offset)
        got = reply.get("children") or []
        out.extend(got)
        count = (reply.get("node") or {}).get("childCount")
        if not got or not isinstance(count, int) or len(out) >= count:
            return out, count
        if offset and reply.get("offset") != offset:
            return out, count
        offset = len(out)


def walk(link, path, depth):
    kids, count = children(link, path)
    nodes = []
    for c in kids:
        p = f"{path}/{c['i']}"
        try:
            reads = link.query_properties(p, ["FID", "NAME", "INDEX", "SUBFIXTUREINDEX"]).get(
                "reads"
            )
        except StateQueryError as error:
            reads = [{"error": str(error)}]
        node = {
            "path": p,
            "i": c["i"],
            "class": c.get("class"),
            "name": c.get("name"),
            "reads": reads,
        }
        if depth < 3:
            node["children"], node["childCount"] = walk(link, p, depth + 1)
        nodes.append(node)
    return nodes, count


def main():
    link = ConsoleLink(id_prefix="t525p")
    config = BridgeConfig(send_host="127.0.0.1", send_port=8000, receive_port=9005)
    with OscBridge(config, consumer=link) as bridge:
        link.bind_send(bridge.send_command)
        tree, count = walk(link, ROOT, 1)
        print(
            json.dumps(
                {"ping": link.ping(), "root": ROOT, "childCount": count, "tree": tree},
                ensure_ascii=False,
                indent=1,
            )
        )


if __name__ == "__main__":
    main()
