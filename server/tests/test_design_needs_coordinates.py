"""t310 — 하네스가 좌표를 답한다 (+ t311 이 걷어낸 통짜 중단의 자리).

원래 이 파일은 두 축을 못으로 박았다. 두 번째(하네스)는 그대로다. 첫 번째는
카드 t311 이 **의도적으로 뒤집었다** — 아래 그 전후를 남긴다.

1. **t310 이 고정했던 것**: 좌표를 못 읽으면 연출 인터뷰가 시작조차 하지 않고
   「3D 좌표를 읽지 못해 조명 방향 변경을 시작하지 않았습니다.」로 끝난다.
   t310 자신이 「방향 축만 불가로 보고하는 편이 옳다고 볼 여지가 있다」고
   적어 두었고, t311 이 그 판단을 했다. 그래서 이 파일의
   ``TestTheWholeDesignStops`` 세 시험은 **사라진 것이 아니라 이동했다**:
   `test_design_without_coordinates.py` 가 같은 리그로 「큐가 나온다」를 잰다.

   여기 남기는 것은 그 뒤집기가 조용하지 않도록 하는 못 하나다 —
   ``TestTheAbortIsGone``: 옛 문면이 디자인 응답에 **다시 나타나면** 빨개진다.

2. **하네스가 좌표를 답한다**(t310 원본, 무수정) — 가짜 콘솔 `full` 리그의
   합성 패치가 응답기를 지나 실제로 판독된다. 이게 없으면 「가짜 콘솔로
   검증했다」는 말이 디자인 단계를 조용히 빼놓는다. 좌표는 **지어낸 값**이고
   하네스에만 있다 (`server/tests/synthetic_rig.py`).
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


class TestTheAbortIsGone:
    """t311 — 좌표 부재는 이제 디자인 전체를 막지 않는다.

    t310 의 세 핀이 무엇을 단언했고 지금은 무엇을 단언하는지:

    * ``test_the_refusal_names_the_missing_coordinates`` — **전**: 디자인 응답이
      조준 거절문(``COORD_REFUSAL``)을 담는다. **후**: 담지 않는다(아래).
      조준 경로가 같은 문장으로 여전히 거절하는지는
      `test_design_without_coordinates.py::TestAimingStillRefuses` 가 잰다.
    * ``test_no_timeline_is_rendered`` — **전**: 타임라인이 안 나온다.
      **후**: 나온다 —
      `TestACoordinatelessRigStillGetsCues::test_the_timeline_carries_a_cue_per_section`.
    * ``test_no_command_reaches_the_console`` — **전후 동일**: 승인 전에는
      콘솔에 아무것도 안 나간다. 그 단언은 옮겨 간 파일이 그대로 들고 있다
      (``test_no_console_write_happens_before_approval``). 좌표가 생겨서 쓰기가
      열린 것이 아니므로 여기서도 계속 참이다 — 그래서 그대로 둔다.
    """

    def test_the_design_no_longer_borrows_the_aim_refusal(self, session):
        event = session.run_instruction(DESIGN_REQUEST, 1)
        assert COORD_REFUSAL not in event["text"]

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
