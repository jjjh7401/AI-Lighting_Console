"""t543 ④ — 읽기 전용: 색 프리셋에서 실제 색 값을 읽을 수 있는지 잰다.

t538 r27 은 위치 프리셋(2.1·2.4)만 읽었다 — 색 풀(4)은 안 쟀다. 여기서 색 프리셋
4.1·4.2 의 필드 전량(introspect 페이징)과 값 필드 후보를 직접 읽는다.
보내는 것: ping / introspect / props 만(쓰기 0). 큰 표 값은 1.6.6 offset 으로 받는다.

실행 (R=.moai/reports/t543):
    .venv/bin/python $R/probe_color_values.py > $R/r5_color_values.json
"""

import json
import sys

sys.path.insert(0, ".")
from server.bridge.osc import BridgeConfig, OscBridge  # noqa: E402
from server.safety.console import ConsoleLink, StateQueryError  # noqa: E402

POOL = "ShowData/DataPools/Default/PresetPools/4"
PRESETS = (1, 2)


def all_fields(link, path):
    fields, offset = [], 0
    for _ in range(20):
        reply = link.enumerate_fields(path, offset=offset)
        got = reply.get("fields") or []
        if not got or reply.get("offset") != offset:
            break
        fields.extend(got)
        offset += len(got)
        if not reply.get("truncated"):
            break
    return fields


def main():
    link = ConsoleLink(id_prefix="t543c")
    config = BridgeConfig(send_host="127.0.0.1", send_port=8000, receive_port=9005)
    with OscBridge(config, consumer=link) as bridge:
        link.bind_send(bridge.send_command)
        out = {"ping": link.ping(), "responder_version": link.responder_version, "presets": {}}
        for no in PRESETS:
            path = f"{POOL}/{no}"
            fields = all_fields(link, path)
            names = [f["n"] for f in fields]
            values = []
            for start in range(0, len(names), 16):
                chunk = names[start : start + 16]
                try:
                    values.extend(link.query_properties(path, chunk).get("reads") or [])
                except StateQueryError as error:
                    values.append({"chunk": chunk, "error": str(error)})
            state = link.query_state(path)
            out["presets"][str(no)] = {
                "path": path,
                "field_count": len(fields),
                "values": values,
                "state": state,
            }
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
