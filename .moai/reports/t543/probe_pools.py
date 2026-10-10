"""t543 ① — 읽기 전용: 프리셋 풀·그룹 풀 목록(번호+이름)을 끝까지 읽는다.

보내는 것: ping / state 만. exec·deploy·props 쓰기 없음(콘솔 쓰기 0).
state 자식 창은 응답기 상한(24)이 있어 offset 을 "받은 개수"만큼 밀며 끝까지 받는다.

실행 (워크트리 루트에서):
    .venv/bin/python .moai/reports/t543/probe_pools.py > .moai/reports/t543/r1_pools.json
"""

import json
import sys

sys.path.insert(0, ".")
from server.bridge.osc import BridgeConfig, OscBridge  # noqa: E402
from server.safety.console import ConsoleLink  # noqa: E402

ROOT = "ShowData/DataPools/Default"


def all_children(link, path):
    """offset 을 받은 개수만큼 밀며 자식 목록을 끝까지 모은다. 진전이 없으면 멈춘다."""
    children, offset, node, pages = [], 0, None, 0
    while pages < 40:
        reply = link.query_state(path, offset=offset)
        pages += 1
        node = reply.get("node", node)
        got = reply.get("children") or []
        if not reply.get("ok", True) or not got:
            break
        # 응답 창이 겹칠 수 있다(t538 r0: offset=40 창이 309 를 다시 줬다) — i 로 중복 제거
        seen = {c.get("i") for c in children}
        children.extend(c for c in got if c.get("i") not in seen)
        if not reply.get("truncated"):
            break
        offset += len(got)
    return {"path": path, "node": node, "pages": pages, "children": children}


def main():
    link = ConsoleLink(id_prefix="t543p")
    config = BridgeConfig(send_host="127.0.0.1", send_port=8000, receive_port=9005)
    with OscBridge(config, consumer=link) as bridge:
        link.bind_send(bridge.send_command)
        out = {"ping": link.ping(), "responder_version": link.responder_version}
        out["datapools"] = all_children(link, ROOT)
        pools = all_children(link, f"{ROOT}/PresetPools")
        out["preset_pools"] = pools
        out["presets"] = {}
        for pool in pools["children"]:
            no = pool.get("i")
            out["presets"][str(no)] = all_children(link, f"{ROOT}/PresetPools/{no}")
        out["groups"] = all_children(link, f"{ROOT}/Groups")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
