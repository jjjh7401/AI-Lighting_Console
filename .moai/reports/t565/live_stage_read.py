"""t565 — 실기 1회 읽기: 박자 격자 2D 무대(좌표 + 트랙 그룹 소속).

생산 함수 ``server.design.beat_grid_stage.read_beat_grid_stage`` 를 **감사 게이트의
state 포트**(``SafetyGate.state_port``)로 그대로 부른다 — 앱이 부르는 것과 같은 길.
보내는 것: ping · state · prop · props 뿐. exec·deploy 없음(실행 포트를 쓰지 않는다).

응답기가 1.6.6 을 답하지 않으면 읽지 않고 멈춘다(§4.8 나눠 읽기가 1.6.6 부터).
트랙 이름은 LOVE ATTACK 기본 격자 데이터 파일에서 읽는다(코드 상수 아님).

실행 (작업 트리 루트에서):
    uv run python .moai/reports/t565/live_stage_read.py > .moai/reports/t565/live_stage_read.json
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, ".")

import yaml  # noqa: E402

from server.bridge.osc import BridgeConfig, OscBridge  # noqa: E402
from server.design.beat_grid_stage import read_beat_grid_stage  # noqa: E402
from server.orchestrator.tools import DEFAULT_RIG_CONTEXT_PATHS  # noqa: E402
from server.safety.audit import AuditLog  # noqa: E402
from server.safety.console import ConsoleLink  # noqa: E402
from server.safety.gate import SafetyGate  # noqa: E402

REQUIRED = "1.6.6"
DATA = Path("server/design/beat_grid_data/love_attack.yaml")


class CountingPort:
    """감사 포트를 감싸 보낸 요청 종류·경로만 센다(값은 남기지 않는다)."""

    def __init__(self, inner) -> None:
        self.inner = inner
        self.requests: list[dict] = []

    def query_state(self, path, *, offset=0):
        self.requests.append({"verb": "state", "path": path, "offset": offset})
        return self.inner.query_state(path, offset=offset)

    def query_property(self, path, property_name):
        self.requests.append({"verb": "prop", "path": path, "name": property_name})
        return self.inner.query_property(path, property_name)

    def query_properties(self, path, property_names, *, offset=None):
        self.requests.append(
            {"verb": "props", "path": path, "names": list(property_names), "offset": offset}
        )
        if offset is None:
            return self.inner.query_properties(path, property_names)
        return self.inner.query_properties(path, property_names, offset=offset)


def main() -> int:
    tracks = [t["group_name"] for t in yaml.safe_load(DATA.read_text(encoding="utf-8"))["tracks"]]
    link = ConsoleLink(id_prefix="t565")
    config = BridgeConfig(send_host="127.0.0.1", send_port=8000, receive_port=9005)
    with OscBridge(config, consumer=link) as bridge:
        link.bind_send(bridge.send_command)
        alive = link.ping()
        version = link.responder_version
        out: dict = {"ping": alive, "responder_version": version, "track_names": tracks}
        if version != REQUIRED:
            out["refused"] = f"응답기 {version!r} — {REQUIRED} 가 아니라 읽지 않음"
            print(json.dumps(out, ensure_ascii=False, indent=1))
            return 1
        with tempfile.TemporaryDirectory() as audit_dir:
            audit = AuditLog(Path(audit_dir))
            gate = SafetyGate(console=link, audit=audit)
            port = CountingPort(gate.state_port)
            payload = read_beat_grid_stage(
                port,
                fixtures_path=DEFAULT_RIG_CONTEXT_PATHS["fixtures"],
                groups_path=DEFAULT_RIG_CONTEXT_PATHS["groups"],
                track_names=tracks,
            )
        verbs: dict[str, int] = {}
        for request in port.requests:
            verbs[request["verb"]] = verbs.get(request["verb"], 0) + 1
        out.update(
            {
                "request_count": len(port.requests),
                "requests_by_verb": verbs,
                "selection_requests": [
                    r for r in port.requests if r["verb"] == "props" and r.get("offset") is not None
                ],
                "fixture_count": len(payload["fixtures"]),
                "groups": payload["groups"],
                "unread": payload["unread"],
                "fixtures": payload["fixtures"],
            }
        )
        print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
