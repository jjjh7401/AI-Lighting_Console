"""t230 — 콘솔 시퀀스의 큐가 무엇을 담고 있는지 읽기 전용으로 훑는다.

쓰기 0건. query_state 와 query_properties 만 쓴다.
Patch/Stages 경로는 밟지 않는다(t220·t225 침묵 상관).

한 스택으로 전부 읽는다 — 프로세스를 큐마다 새로 띄우면 콘솔에 같은 수의
연결이 오간다.
"""

from __future__ import annotations

import argparse
import json
import sys

from server.safety.bootstrap import build_console_stack
from server.safety.console import LinkTimeouts, StateQueryError
from server.tools.probe_preflight import add_listen_port_argument, preflight
from server.tools.tree_identity import assert_same_tree

assert_same_tree(__file__)

PROBE_NAMES = (
    "OWNDATAPRESENT",
    "OWNNONCOOKEDDATAPRESENT",
    "STOREDDATA",
    "REFERENCES",
    "DEPENDENCIES",
    "MEMORYFOOTPRINT",
    "HASANYMATRICKSDATA",
    "SELECTIONDATA",
    "PRESETDATA",
    "COUNT",
)


def read_state(port, path):
    """단발 조회. 자식이 잘릴 수 있으므로 목록이 필요하면 read_children 를 써라."""
    try:
        return port.query_state(path), None
    except StateQueryError as error:
        return None, str(error)


def read_children(port, path):
    """자식을 소진할 때까지 페이징한다 — 받은 개수만큼 전진한다.

    🔴 단발 query_state 는 응답기 payload 예산에서 잘린다. 실측(t230):
    childCount 21 인 시퀀스가 한 번에 13~17 개만 답했고, 잘린 목록을
    「이게 전부」로 읽으면 큐 8개가 조용히 사라진다. 이름이 한글이면 바이트가
    커서 더 일찍 잘린다 — 그래서 같은 childCount 21 이 시퀀스마다 다른 수로
    잘렸다.

    반환은 (자식목록, childCount, 사유). 진전이 없으면 멈추고 사유를 남긴다.
    """
    children = []
    offset = 0
    child_count = None
    while True:
        try:
            payload = port.query_state(path, offset=offset)
        except StateQueryError as error:
            return children, child_count, str(error)
        if child_count is None:
            child_count = (payload.get("node") or dict()).get("childCount")
        window = list(payload.get("children") or [])
        echoed = payload.get("offset")
        children.extend(window)
        if not payload.get("truncated"):
            return children, child_count, None
        if not window:
            return children, child_count, "truncated 인데 빈 창이 왔다 — 전진 없음"
        if echoed is not None and echoed != offset:
            return children, child_count, "offset 반향 불일치 — 같은 창 반복 방지로 중단"
        offset += len(window)


def read_props(port, path, names=PROBE_NAMES):
    try:
        payload = port.query_properties(path, names)
    except StateQueryError as error:
        return None, str(error)
    out = dict()
    for entry in payload.get("reads") or []:
        ok = entry.get("ok")
        out[entry.get("n")] = entry.get("v") if ok else "!" + str(entry.get("e"))
    return out, None


def main(argv=None) -> int:
    """회신 포트는 인자로 받는다 — 박아 두지 않는다.

    앞 회차(t230)가 이 도구를 9005 아닌 포트로 돌려 **전면 침묵**을 만났고,
    그 침묵은 「응답기가 죽었다」와 바이트 동일이었다. 포트를 박아 두면 그
    사고가 조용히 반복된다. 그래서 t61 의 공용 선언을 부르고, 프리플라이트로
    침묵에 이름을 붙인다 — 틀린 포트인지 응답기가 죽은 것인지 갈라 준다.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    add_listen_port_argument(parser)
    parser.add_argument("--host", default="127.0.0.1", help="콘솔 OSC 입력 호스트")
    parser.add_argument("--port", type=int, default=8000, help="onPC OSC 입력 포트")
    args = parser.parse_args(argv)

    stack = build_console_stack(
        send_host=args.host,
        send_port=args.port,
        receive_host="127.0.0.1",
        receive_port=args.listen_port,
        audit_dir=None,
        timeouts=LinkTimeouts(state_query_seconds=6.0),
        attempt_session_backup=False,
    )
    port = stack.gate.state_port
    result = dict(listen_port=args.listen_port, sequences=[])
    try:
        result["preflight"] = preflight(
            stack.gate,
            receive_host="127.0.0.1",
            receive_port=args.listen_port,
            console_port=args.port,
        )
        pool, error = read_state(port, "DataPool/Sequences")
        if pool is None:
            print("pool read failed: " + str(error), file=sys.stderr)
            return 1
        for seq in pool.get("children") or []:
            seq_i = seq.get("i")
            seq_path = "DataPool/Sequences/" + str(seq_i)
            entry = dict(i=seq_i, name=seq.get("name"), cues=[])
            cue_children, child_count, error = read_children(port, seq_path)
            entry["childCount"] = child_count
            entry["listed"] = len(cue_children)
            if error is not None:
                entry["error"] = error
            for cue in cue_children:
                cue_i = cue.get("i")
                cue_path = seq_path + "/" + str(cue_i)
                row = dict(i=cue_i, cueNo=cue.get("cueNo"), name=cue.get("name"), parts=[])
                part_children, part_count, error = read_children(port, cue_path)
                row["partCount"] = part_count
                row["partsListed"] = len(part_children)
                if error is not None:
                    row["error"] = error
                for part in part_children:
                    part_i = part.get("i")
                    part_path = cue_path + "/" + str(part_i)
                    props, error = read_props(port, part_path)
                    row["parts"].append(dict(i=part_i, path=part_path, props=props, error=error))
                entry["cues"].append(row)
            result["sequences"].append(entry)
    finally:
        stack.stop()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
