"""t525 — 읽기 전용: 개별 그룹 오브젝트의 필드 101개를 introspect offset 페이징으로 전량 읽는다.

목적: 그룹 소속(멤버 fid)을 앱이 콘솔에서 읽을 수 있는지 판정.
t520(groups_readonly.txt) 은 Groups/13 introspect 첫 창 27/101 만 받았다(truncated).
응답기 1.6.2+ 는 introspect offset 을 받는다(ConsoleLink.enumerate_fields).

보내는 것: ping / state / introspect / props 만. exec·deploy 없음.

실행 (프로젝트 루트에서, R=.moai/reports/t525):
    .venv/bin/python $R/probe_groups.py 13 4 5 14 > $R/r3_group_fields.json
"""

import json
import sys

sys.path.insert(0, ".")
from server.bridge.osc import BridgeConfig, OscBridge  # noqa: E402
from server.safety.console import ConsoleLink, StateQueryError  # noqa: E402

GROUPS = "ShowData/DataPools/Default/Groups"


def all_fields(link, path):
    """offset 을 받은 개수만큼 밀며 끝까지 읽는다. 진전이 없으면 멈춘다."""
    fields, offset, total, pages = [], 0, None, []
    while True:
        reply = link.enumerate_fields(path, offset=offset)
        got = reply.get("fields") or []
        total = reply.get("total", total)
        pages.append(
            {
                "offset": offset,
                "echo_offset": reply.get("offset"),
                "got": len(got),
                "truncated": reply.get("truncated"),
            }
        )
        if not got or reply.get("offset") != offset:
            break
        fields.extend(got)
        offset += len(got)
        if isinstance(total, int) and offset >= total:
            break
        if len(pages) > 20:
            break
    return fields, total, pages


def main(group_nos):
    link = ConsoleLink(id_prefix="t525g")
    config = BridgeConfig(send_host="127.0.0.1", send_port=8000, receive_port=9005)
    with OscBridge(config, consumer=link) as bridge:
        link.bind_send(bridge.send_command)
        out = {"ping": link.ping(), "responder_version": link.responder_version}
        out["pool"] = link.query_state(GROUPS)
        out["groups"] = {}
        for no in group_nos:
            path = f"{GROUPS}/{no}"
            entry = {"path": path, "state": link.query_state(path)}
            fields, total, pages = all_fields(link, path)
            entry.update({"total": total, "received": len(fields), "pages": pages})
            entry["fields"] = fields
            # 이름·타입만으로 고르지 않고, 받은 필드 전부를 16개씩 값까지 읽는다.
            values = []
            names = [f["n"] for f in fields]
            for start in range(0, len(names), 16):
                chunk = names[start : start + 16]
                try:
                    values.extend(link.query_properties(path, chunk).get("reads") or [])
                except StateQueryError as error:
                    values.append({"chunk": chunk, "error": str(error)})
            entry["values"] = values
            out["groups"][str(no)] = entry
        print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:] or ["13"])
