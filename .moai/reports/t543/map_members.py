"""t543 ① — 그룹 SELECTIONDATA(sf_index) → fid 대응표. 오프라인(콘솔 안 씀).

입력: r2_group_members.jsonl(그룹 18개 전량) · r3_patch_tree.json(SUBFIXTUREINDEX)
      · r1_pools.json(그룹 이름)
대응 규칙은 t525 §② 실측 그대로: 픽스처·서브픽스처마다 SUBFIXTUREINDEX 가 하나씩.
서브픽스처 칸에 떨어진 sf_index 는 부모 fid 와 함께 "sub" 로 표시한다(본체로 뭉개지 않는다).

실행: .venv/bin/python .moai/reports/t543/map_members.py > .moai/reports/t543/r4_group_fids.txt
"""

import json
from pathlib import Path

HERE = Path(__file__).parent


def walk(nodes, parent_fid=None, out=None):
    out = {} if out is None else out
    for node in nodes:
        reads = {r["n"]: r.get("v") for r in node.get("reads") or [] if r.get("ok")}
        fid = reads.get("FID")
        sfi = reads.get("SUBFIXTUREINDEX")
        if sfi is not None:
            out[int(sfi)] = (fid, parent_fid, node.get("name"))
        walk(node.get("children") or [], parent_fid=fid or parent_fid, out=out)
    return out


def main():
    tree = json.loads((HERE / "r3_patch_tree.json").read_text())
    index = walk(tree["tree"])
    pools = json.loads((HERE / "r1_pools.json").read_text())
    names = {c["i"]: c["name"] for c in pools["groups"]["children"]}
    print(f"sf_index entries in patch: {len(index)}")
    for line in (HERE / "r2_group_members.jsonl").read_text().splitlines():
        row = json.loads(line)
        fids, subs, unknown = [], [], []
        for member in row["members"]:
            hit = index.get(member["sf_index"])
            if hit is None:
                unknown.append(member["sf_index"])
            elif hit[1] and not hit[0]:
                subs.append(f"{hit[1]}/{hit[2]}")
            else:
                fids.append(int(hit[0]))
        tail = (" SUB " + str(subs) if subs else "") + (
            " UNKNOWN " + str(unknown) if unknown else ""
        )
        print(
            f"Group {row['group']:>2} {names.get(row['group'], '?'):10} total={row.get('total')} "
            f"recv={row['received']} fids={len(fids)} sub={len(subs)} unknown={len(unknown)} "
            f"-> {fids}{tail}"
        )


if __name__ == "__main__":
    main()
