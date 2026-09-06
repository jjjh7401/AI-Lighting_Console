"""t310 — 디자인 큐 시트는 3D 좌표가 없으면 **통째로** 멈춘다.

두 축을 각각 못으로 박는다.

1. **제품 현재 동작(핀 고정)** — 좌표를 못 읽으면 연출 인터뷰가 시작조차 하지
   않고, 사유 문자열이 이유를 그대로 말한다. 이건 「고쳤다」가 아니라 「지금
   이렇다」를 재는 시험이다: 좌표가 없는 리그라도 조도·색 큐는 나오고 **방향
   축만** 불가로 보고하는 편이 옳다고 볼 여지가 있고, 그 판단은 이 카드
   범위 밖이다. 동작을 바꿀 때 이 시험이 먼저 빨개진다.

2. **하네스가 좌표를 답한다** — 가짜 콘솔 `full` 리그의 합성 패치가 응답기를
   지나 실제로 판독된다. 이게 없으면 「가짜 콘솔로 검증했다」는 말이 디자인
   단계를 조용히 빼놓는다. 좌표는 **지어낸 값**이고 하네스에만 있다
   (`server/tests/synthetic_rig.py`).
"""

from __future__ import annotations

import pytest

from server.safety.audit import AuditLog
from server.safety.gate import SafetyGate
from server.tests.fake_console import full_rig_lua
from server.tests.lua_mock_env import ResponderHarness
from server.tests.synthetic_rig import synthetic_fixtures
from server.tests.test_lua_responder import decode_payload
from server.tests.test_safety_gate import FakeConsole
from server.web.approval_bridge import ApprovalChannel
from server.web.session import ChatSession

DESIGN_REQUEST = (
    "디자인 큐 시트, 시퀀스 210, 프리셋 21번부터, 타임코드 9: "
    "인트로 0:00 잔잔하게, 후렴 0:40 클럽 드롭"
)

#: 감독이 브라우저에서 실제로 본 문장(카드 t310 실측, 2026-09-07).
COORD_REFUSAL = "3D 좌표를 읽지 못해 조명 방향 변경을 시작하지 않았습니다."


class RefusingProvider:
    def complete(self, *args, **kwargs):  # pragma: no cover - 불려선 안 된다
        raise AssertionError("이 경로는 모델을 부르지 않는다")


@pytest.fixture
def session(tmp_path):
    audit = AuditLog(tmp_path / "audit")
    channel = ApprovalChannel(timeout_seconds=1.0)
    return ChatSession(
        gate=SafetyGate(console=FakeConsole(), audit=audit, approval_port=channel),
        provider=RefusingProvider(),
        system_prefix="PREFIX",
        audit=audit,
        send_event=lambda event: None,
        approval_channel=channel,
    )


class TestTheWholeDesignStops:
    """좌표 부재는 **방향 축만** 막는 게 아니라 디자인 전체를 막는다."""

    def test_the_refusal_names_the_missing_coordinates(self, session):
        event = session.run_instruction(DESIGN_REQUEST, 1)
        assert COORD_REFUSAL in event["text"]

    def test_no_timeline_is_rendered(self, session):
        # 대조: 사유만 맞고 타임라인이 나오면 「멈췄다」가 아니다.
        event = session.run_instruction(DESIGN_REQUEST, 1)
        assert "큐 1" not in event["text"]

    def test_no_command_reaches_the_console(self, session):
        event = session.run_instruction(DESIGN_REQUEST, 1)
        assert event.get("commands", []) == []


class TestTheHarnessAnswersCoordinates:
    """가짜 콘솔 `full` 리그가 좌표를 답해야 디자인 단계를 굴려 볼 수 있다."""

    @pytest.fixture
    def responder(self):
        return ResponderHarness(extra_env=full_rig_lua())

    def test_the_stage_patch_enumerates(self, responder):
        responder.main(None, "state 1 Patch/Stages/1/Fixtures")
        payload = decode_payload(responder.sent()[0].payload)
        assert payload["ok"] is True
        assert payload["truncated"] is False
        assert payload["node"]["childCount"] == len(synthetic_fixtures())

    def test_every_fixture_answers_its_x_coordinate(self, responder):
        for slot, _fixture in enumerate(synthetic_fixtures(), start=1):
            responder.main(None, f"prop {slot} Patch/Stages/1/Fixtures/{slot} posx")
        replies = [decode_payload(message.payload) for message in responder.sent()]
        assert all(reply["ok"] is True for reply in replies)
        assert [reply["value"] for reply in replies] == [
            str(fixture.x) for fixture in synthetic_fixtures()
        ]

    def test_the_geometry_is_not_degenerate(self):
        # 실기 교정 리그는 19대 전부 (0,0,0) 이었다
        # (SPEC-COPILOT-SPATIAL-001 progress.md §E.2.4 실측). 합성 리그는
        # 일부러 그렇지 않게 만든다 — 축퇴 리그로는 기하 축이 아무것도 못 한다.
        fixtures = synthetic_fixtures()
        assert len({(f.x, f.y, f.z) for f in fixtures}) == len(fixtures)
        assert len({f.fid for f in fixtures}) == len(fixtures)
