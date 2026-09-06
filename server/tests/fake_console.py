"""실사용 검증용 가짜 콘솔 — 실제 Lua 응답기를 lupa 로 돌려 ping/state/exec 에 답한다.

콘솔 쓰기는 어디에도 닿지 않는다(실기 onPC 가 아니라 이 프로세스가 받는다).

지금까지 이 하네스는 `.moai/state/verify/musicsync-ui/fake_console.py` 에
추적되지 않은 채로만 있었다. 카드 t310 에서 리그에 **3D 좌표**를 붙이면서,
같은 사슬을 다시 굴릴 수 있도록 저장소 안으로 들여왔다. `full` 리그는 이제
그룹 풀뿐 아니라 합성 패치(`synthetic_rig.py`)도 들고 있어서 업로드 → 분석 →
확인 → **디자인** 까지 끝단이 이어진다.

사용법::

    uv run python -m server.tests.fake_console <cmd_port> <reply_port> [rig]

``rig`` 는 ``default`` (기본) 또는 ``full``. 포트 8000 은 감독의 실기
grandMA3 데스크라 **절대 쓰지 않는다**.
"""

from __future__ import annotations

import re
import sys
import threading

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

from server.bridge.osc import CMD_ADDRESS
from server.tests.lua_mock_env import ResponderHarness
from server.tests.synthetic_rig import synthetic_patch_lua

_PLUGIN_CALL = re.compile(r'^Plugin "CopilotResponder" "(.*)"$')

# 곡 → 큐 리스트 끝단 실측용 리그: 룩 역할 6종에 맞는 그룹, 시퀀스 3, **빈** Timecodes 풀
# (1.6.5 응답기라면 enumeration:"ok" 로 답해 슬롯 판정이 free 가 된다), 빈 Macros 풀.
_FULL_RIG_DATAPOOL_LUA = r"""
local node = __NODE
__DATAPOOL = node("Default", "DataPool", {
    node("Sequences", "Pool", {
        node("Sequence 1", "Sequence"),
        node("Sequence 2", "Sequence"),
        node("Sequence 3", "Sequence"),
    }),
    node("Groups", "Pool", {
        node("Back Wash", "Group"),
        node("FOH Wash", "Group"),
        node("Side L", "Group"),
        node("Top", "Group"),
        node("Cyc", "Group"),
        node("Special", "Group"),
    }),
    node("Timecodes", "Pool", {}),
    node("Macros", "Pool", {}),
})
function DataPool() return __DATAPOOL end
"""


def full_rig_lua() -> str:
    """`full` 리그의 Lua 환경 — 데이터풀 + **합성** 3D 패치.

    좌표는 지어낸 값이다(`synthetic_rig` 모듈 주석 참고). 실기에서 읽은
    기하가 아니라, 디자인 단계를 굴려 보기 위한 무대다.
    """
    return _FULL_RIG_DATAPOOL_LUA + "\n" + synthetic_patch_lua()


#: 이전 이름을 쓰던 호출자를 위한 별칭(데이터풀만 담고 있던 상수).
FULL_RIG_LUA = _FULL_RIG_DATAPOOL_LUA


def main(cmd_port: int, reply_port: int, rig: str = "default") -> None:
    harness = ResponderHarness(extra_env=full_rig_lua() if rig == "full" else "")
    client = SimpleUDPClient("127.0.0.1", reply_port)
    forwarded = 0
    lock = threading.Lock()

    def on_cmd(address, *args):
        nonlocal forwarded
        match = _PLUGIN_CALL.match(args[0]) if args else None
        print("cmd:", (args[0] if args else "")[:120], flush=True)
        if match is None:
            return
        with lock:
            harness.main(None, match.group(1))
            sent = harness.sent()
            for message in sent[forwarded:]:
                client.send_message(message.address, message.payload)
            forwarded = len(sent)

    dispatcher = Dispatcher()
    dispatcher.map(CMD_ADDRESS, on_cmd)
    server = ThreadingOSCUDPServer(("127.0.0.1", cmd_port), dispatcher)
    print(f"fake console on {cmd_port} -> replies to {reply_port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else "default")
