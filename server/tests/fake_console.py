"""실사용 검증용 가짜 콘솔 — 실제 Lua 응답기를 lupa 로 돌려 ping/state/exec 에 답한다.

콘솔 쓰기는 어디에도 닿지 않는다(실기 onPC 가 아니라 이 프로세스가 받는다).

지금까지 이 하네스는 `.moai/state/verify/musicsync-ui/fake_console.py` 에
추적되지 않은 채로만 있었다. 카드 t310 에서 리그에 **3D 좌표**를 붙이면서,
같은 사슬을 다시 굴릴 수 있도록 저장소 안으로 들여왔다. `full` 리그는 이제
그룹 풀뿐 아니라 합성 패치(`synthetic_rig.py`)도 들고 있어서 업로드 → 분석 →
확인 → **디자인** 까지 끝단이 이어진다.

사용법::

    uv run python -m server.tests.fake_console <cmd_port> <reply_port> [rig]

``rig`` 는 ``default`` (기본) · ``full`` · ``nocoords`` (패치 없는 리그, 카드
t311). 포트 8000 은 감독의 실기
grandMA3 데스크라 **절대 쓰지 않는다**.
"""

from __future__ import annotations

import re
import sys
import threading
import time
from typing import IO

from pythonosc.dispatcher import Dispatcher
from pythonosc.osc_server import ThreadingOSCUDPServer
from pythonosc.udp_client import SimpleUDPClient

from server.bridge.osc import CMD_ADDRESS
from server.tests.lua_mock_env import ResponderHarness
from server.tests.synthetic_rig import synthetic_patch_lua

_PLUGIN_CALL = re.compile(r'^Plugin "CopilotResponder" "(.*)"$')

#: 준비 완료 배너의 **고정 접두사**. 소켓이 바인드된 뒤에만 나온다 —
#: 이 줄을 읽기 전에 보낸 명령은 커널이 조용히 버린다(카드 t313).
READY_BANNER = "fake console on"


class FakeConsoleNeverReadyError(RuntimeError):
    """가짜 콘솔이 제한 시간 안에 준비 배너를 내지 않았다."""


# @MX:ANCHOR: [AUTO] 하위 프로세스 가짜 콘솔의 유일한 준비 신호
# @MX:REASON: 카드 t313 실측 — 이 대기 없이 보낸 첫 명령은 UDP 라 **오류 없이**
#   사라진다. 프로세스를 띄운 드라이버는 전부 이 함수를 지나야 한다.
def wait_for_ready(stdout: IO[str], timeout: float = 30.0) -> str:
    """준비 배너가 나올 때까지 ``stdout`` 을 읽고 그 줄을 돌려준다.

    `python -m server.tests.fake_console` 는 파이썬 기동 + 임포트 +
    Lua 응답기 구성까지 마쳐야 명령 소켓을 연다. 그 사이에 도착한 UDP
    패킷은 **버려지고 송신 쪽엔 아무 신호도 없다** — 카드 t313 에서 첫
    질의만 시간 초과로 죽은 원인이 이것이다(콘솔 stdout 에 그 명령 자체가
    찍히지 않는다). 고정 지연(`sleep`)은 느린 기계에서 다시 깨지므로
    쓰지 않는다.

    사용::

        proc = subprocess.Popen([...], stdout=subprocess.PIPE, text=True)
        wait_for_ready(proc.stdout)
        # 이 뒤로 보낸 명령만 콘솔에 닿는다
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        line = stdout.readline()
        if not line:
            break
        if line.startswith(READY_BANNER):
            return line.rstrip()
    raise FakeConsoleNeverReadyError(
        f"가짜 콘솔이 {timeout}s 안에 {READY_BANNER!r} 배너를 내지 않았다"
    )


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


def _rig_env(rig: str) -> str:
    """리그 이름 → Lua 환경.

    카드 t311 — `nocoords` 는 `full` 에서 **합성 패치만** 뺀 리그다. 그룹·
    시퀀스·풀은 그대로라 「좌표가 없다」와 「콘솔이 죽었다」가 갈린다: 디자인이
    끝까지 굴러가되 포지션 축만 비활성으로 나오는지를 이 리그로 몬다.
    """
    if rig == "full":
        return full_rig_lua()
    if rig == "nocoords":
        return _FULL_RIG_DATAPOOL_LUA
    return ""


def main(cmd_port: int, reply_port: int, rig: str = "default") -> None:
    harness = ResponderHarness(extra_env=_rig_env(rig))
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
    # 소켓 바인드가 배너보다 **먼저** 일어나야 한다: 배너를 본 드라이버가
    # 곧바로 보낸 명령이 버려지지 않는다는 보장이 이 순서다(카드 t313).
    server = ThreadingOSCUDPServer(("127.0.0.1", cmd_port), dispatcher)
    print(f"{READY_BANNER} {cmd_port} -> replies to {reply_port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3] if len(sys.argv) > 3 else "default")
