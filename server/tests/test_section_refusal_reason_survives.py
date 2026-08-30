"""t163 — 섹션 실패 **사유**가 소비자를 지나 사용자에게 닿는가.

`collect_rig_sections` 는 실패한 단면을 `{"reason": ..., "path": ..., "error": ...}`
로 바꾸고, 그 사유는 두 값 중 하나다 — `path_not_resolved`(형제가 답했으니 이 경로가
이 쇼파일에 틀렸다)와 `console_unreachable`(아무도 안 답했으니 어느 경로도 못 탓한다).
`server/rig/section.py` 독스트링이 왜 가르는지 말한다: **사람이 무엇을 고쳐야 하는지가
다르다.** 그러니 사유를 접는 소비자는 그 모듈이 존재하는 이유를 되돌린다.

t152 가 `import_lxseq_groups` **한 자리**에서 사유가 접히는 것을 쟀고, 나는 그것을
「소비자에서 소실된다」로 요약했다. t163 이 **10자리 전수**로 그 요약을 반증했다 —
여덟 자리가 살려 보낸다. 이 파일은 그 전수 결과를 고정한다: 살리는 자리가 조용히
접히지 않도록, 그리고 접히는 자리가 「원래 다 그렇다」로 읽히지 않도록.

전수표는 `.moai/reports/t163/census.md`.

**뮤테이션 — 예고가 아니라 실제로 돌린 것과 그 결과**:

  M1 실패 단면의 `reason` 을 `None` 으로 덮는다 (생산 지점에서 사유 소실)
       -> 1절·2절 빨강. 관측대로
  M2 `_guard_pool_readable` 문면에서 사유 보간을 뺀다
       -> 2절 빨강. 관측대로
  M3 미판독 fixtures 단면을 거절하게 고친다 (수리 형태)
       -> 3절·4절 빨강. 관측대로. **전 스위트는 10513 전량 초록** — 즉 이
          축은 이 파일 말고 아무도 안 잰다
  M4 `total is None` 일 때 부족분을 `0` 으로 굳힌다
       -> 4절 빨강. **다만 기존 `test_truncate_disclosure.py::
          test_an_unknown_total_still_requires_the_enumeration` 도 같이 빨강**

M4 가 이 파일에서 제일 값나가는 기록이다. 그 뮤테이션은 **두 상태를 동시에**
바꿨다 — 「응답기가 childCount 를 안 줬다」와 「단면을 아예 못 읽었다」가 코드에서
같은 갈래로 흐르기 때문이다. 그래서 M4 로는 「기존이 못 잡는가」를 못 잰다.
축을 갈라 M3 로 다시 쟀고, 그때 비로소 **인접한 두 축 중 하나만 지켜지고 있다**는
것이 보였다: unknown-total 축은 기존 검사가 지키고, **미판독 축은 아무도 안 지킨다.**

3절·4절은 **계약이 아니라 실측 기록**이다. 초록이 「그래도 된다」가 아니다.
"""

from __future__ import annotations

import json

from server.llm.types import ToolCall
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import (
    DEFAULT_RIG_CONTEXT_PATHS,
    REASON_UNREACHABLE,
    REASON_UNRESOLVED,
    build_toolset,
)

FIXTURES_PATH = DEFAULT_RIG_CONTEXT_PATHS["fixtures"]
GROUPS_PATH = DEFAULT_RIG_CONTEXT_PATHS["groups"]

CREATE = "create_arrangement_groups"
RIG_CONTEXT = "get_rig_context"


class _RecordingPort:
    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, command: str) -> ExecutionResult:
        self.executed.append(command)
        return ExecutionResult(ok=True, detail="OK")


class _ApprovePort:
    def request_approval(self, request) -> bool:
        return True


def _console(dead: frozenset[str], *, declared: int = 8, listed: int = 4):
    """그룹 풀(빈) + 절단된 픽스처 컨테이너.

    `dead` 의 경로는 **예외를 던진다** — 프로덕션 포트의 실패 형태다
    (`server/safety/console.py` 의 `query_state`: "raises on failure/timeout").
    `ok=False` 를 돌려주는 가짜를 쓰면 이 파일이 재려는 갈래를 안 탄다.
    """
    states = dict()
    states[GROUPS_PATH] = dict(ok=True, truncated=False, node=dict(childCount=0), children=[])
    states[FIXTURES_PATH] = dict(
        ok=True,
        truncated=True,
        node=dict(childCount=declared),
        children=[dict(i=s, name="Spot " + str(s)) for s in range(1, listed + 1)],
    )

    class _Console:
        def query_state(self, path: str, offset: int = 0) -> dict:
            if path in dead:
                raise LookupError("console did not answer: " + path)
            if path not in states:
                raise LookupError("unknown object path: " + path)
            return states[path]

        def query_property(self, path: str, property_name: str) -> dict:
            return dict(ok=False, error="property not readable: " + property_name)

    return _Console()


def _dispatch(name: str, arguments: dict, dead: frozenset[str], **console_kwargs):
    port = _RecordingPort()
    console = _console(dead, **console_kwargs)
    registry = build_toolset(
        execution_port=port,
        state_port=console,
        property_port=console,
        group_approval_port=_ApprovePort(),
    )
    execution = registry.dispatch(ToolCall(id="t163", name=name, arguments=arguments))
    return execution, port


_DEAD_GROUPS = frozenset([GROUPS_PATH])
_DEAD_FIXTURES = frozenset([FIXTURES_PATH])
_PARTIAL = dict(name="GEO Stage Left", fids=[2, 3], topology_partial=True)


class TestPreservingConsumersNameTheReason:
    """1절 — 사유를 살려 보내는 자리가 계속 살려 보내는가.

    전수 10자리 중 여덟이 여기 속한다. 표본으로 `get_rig_context` 를 쓴다 —
    가장 넓은 형태(요약을 통째로 직렬화)라 다른 일곱의 관용구가 무너져도
    이 자리는 남는다. 자리별 전수는 census.md 가 든다.
    """

    def test_get_rig_context_carries_the_reason_to_the_caller(self):
        execution, port = _dispatch(RIG_CONTEXT, dict(), _DEAD_GROUPS)
        assert port.executed == [], "읽기 도구가 콘솔에 발화했다"
        payload = json.loads(execution.result.content)
        entry = payload.get("groups")
        assert isinstance(entry, dict), "그룹 단면이 매핑이 아니다: " + repr(entry)
        assert entry.get("reason") == REASON_UNRESOLVED, (
            "실패 단면의 사유가 사라졌다 — 사람이 경로를 볼지 연결을 볼지 못 가른다"
        )
        assert entry.get("path") == GROUPS_PATH, "어느 경로가 실패했는지도 같이 나가야 한다"

    def test_a_live_section_beside_it_still_answers(self):
        """대조군 — 위가 「전부 실패로 보인다」가 아님을 보인다."""
        execution, _port = _dispatch(RIG_CONTEXT, dict(), _DEAD_GROUPS)
        payload = json.loads(execution.result.content)
        fixtures = payload.get("fixtures")
        assert isinstance(fixtures, dict)
        assert "reason" not in fixtures, "산 단면에 실패 사유가 붙었다"
        assert isinstance(fixtures.get("objects"), list)


class TestTheWritePathNamesTheGroupPoolReason:
    """2절 — `create_arrangement_groups` 의 groups 축.

    이 자리는 인라인 검사가 **없다.** 사유는 하류 `_guard_pool_readable` 이
    거절 문면에 보간해 살아 나온다. 기제가 다르므로 결과를 따로 잰다 —
    「검사가 없다」를 「사유가 없다」로 읽으면 틀린다(t163 이 그 자리다).
    """

    def test_an_unreadable_group_pool_refuses_and_names_the_reason(self):
        execution, port = _dispatch(
            CREATE, dict(groups=[dict(name="Plain", fids=[2, 3])]), _DEAD_GROUPS
        )
        assert execution.result.is_error is True
        assert port.executed == [], "못 읽은 풀 위에서 콘솔에 발화했다"
        content = execution.result.content
        assert "GROUP_POOL_UNAVAILABLE" in content
        assert REASON_UNRESOLVED in content, (
            "거절은 했는데 **왜**를 안 말한다 — 사람이 무엇을 고칠지 못 정한다: " + content
        )

    def test_the_same_pool_alive_does_not_refuse(self):
        """대조군 — 위 거절이 「이 가짜는 늘 거절한다」가 아님을 보인다."""
        execution, port = _dispatch(
            CREATE, dict(groups=[dict(name="Plain", fids=[2, 3])]), frozenset()
        )
        assert "GROUP_POOL_UNAVAILABLE" not in execution.result.content
        assert port.executed, "산 풀에서도 한 줄도 안 나갔다 — 대조군이 공허하다"


class TestAnUnreadFixtureSectionIsReportedAsNotTruncated:
    """3절 — **실측 기록**: 픽스처 컨테이너가 안 답하면 「절단 아님」이 나간다.

    초록이 「그래도 된다」는 뜻이 **아니다**. `create_arrangement_groups` 는
    `fixture_list_truncated` 를 `bool(fixtures_section.get("truncated"))` 로 낸다.
    실패 단면에는 그 키가 아예 없으므로 `False` 가 된다 — 즉 **한 글자도 안 읽은
    상태가 「깨끗하게 다 읽었다」와 바이트 동일로** 나간다. 부재를 깨끗한 음성으로
    보고하는 형태다.

    🔴 **이 검사가 빨개지면 그 결함이 수리된 것이다 — t163 이 세운 수리 카드를 닫아라.**
    """

    def test_an_unread_fixture_container_claims_it_was_not_truncated(self):
        execution, _port = _dispatch(
            CREATE,
            dict(groups=[dict(name="Plain", fids=[2, 3])]),
            _DEAD_FIXTURES,
        )
        payload = json.loads(execution.result.content)
        assert "plan" in payload, "그룹 풀은 살아 있으므로 계획은 서야 한다"
        assert payload.get("fixture_list_truncated") is False, (
            "미판독 픽스처 단면이 이제 절단/미판독으로 보고된다 — 수리된 것이니 "
            "t163 이 세운 수리 카드를 닫아라"
        )
        assert payload.get("fixture_list_truncated_reason") == "", (
            "미판독에 사유가 붙기 시작했다 — 수리된 것이니 t163 수리 카드를 닫아라"
        )
        blob = json.dumps(payload, ensure_ascii=False)
        for reason in (REASON_UNRESOLVED, REASON_UNREACHABLE):
            assert reason not in blob, (
                "픽스처 축 사유가 페이로드에 도달한다 — 수리된 것이니 t163 수리 카드를 닫아라"
            )

    def test_a_truncated_but_readable_container_does_say_so(self):
        """대조군 — 위 `False` 가 「이 필드가 늘 False」가 아님을 보인다.

        이게 없으면 3절 전체가 공허하다: 필드가 죽어 있어도 초록이 난다.
        """
        execution, _port = _dispatch(
            CREATE, dict(groups=[dict(name="Plain", fids=[2, 3])]), frozenset()
        )
        payload = json.loads(execution.result.content)
        assert payload.get("fixture_list_truncated") is True
        assert payload.get("fixture_list_truncated_reason"), "절단인데 사유가 비었다"


class TestAnUnreadFixtureSectionDisablesTheAnchorSizeCheck:
    """4절 — **실측 기록**: 미판독 단면이 @MX:ANCHOR 크기 검사를 끈다.

    초록이 「그래도 된다」는 뜻이 **아니다**. `tools.py:7742` 의 부분판독 쓰기 거절
    (SPEC-COPILOT-TRUNCATE-001 REQ-TRUNCATE-008 / AC-TRUNCATE-008,
    mutation-required)은 열거 개수를 **부족분**(`childCount - 열거된 수`)과 대조한다.
    미판독 단면에선 `total` 이 `None` 이라 그 대조가 통째로 건너뛰어진다.

    `:7766-7768` 주석은 그 `None` 을 「응답기가 childCount 를 안 줬을 때」로만
    설명한다 — 참인 문장인데 **범위가 미판독 경우를 안 덮는다.** 그리고 그 문장이
    안전장치의 면제 사유라, 범위가 안 맞는 순간 면제가 의도 밖으로 넓어진다.

    🔴 **이 검사가 빨개지면 그 결함이 수리된 것이다 — t163 이 세운 수리 카드를 닫아라.**
    """

    #: 부족분 = declared 8 - listed 4 = 4. 길이 1 열거는 크기 검사에 걸려야 한다.
    _SHORT_ACK = dict(groups=[_PARTIAL], acknowledged_unread_fids=[5])
    _FULL_ACK = dict(groups=[_PARTIAL], acknowledged_unread_fids=[5, 6, 7, 8])

    def test_a_healthy_container_refuses_an_undersized_enumeration(self):
        """팔 ① — 크기 검사가 **살아 있다**. 이걸 먼저 보여야 아래가 의미를 갖는다."""
        execution, port = _dispatch(CREATE, dict(self._SHORT_ACK), frozenset())
        assert execution.result.is_error is True
        assert port.executed == [], "부족분에 못 미치는 열거로 콘솔에 발화했다"
        assert "acknowledged_unread_fids" in execution.result.content

    def test_a_correctly_sized_enumeration_gets_through_on_the_same_console(self):
        """팔 ② — 위 거절이 「이 가짜는 늘 거절한다」가 아님을 보인다.

        대조군이 셋인 이유: 이 팔이 없으면 팔 ①의 거절과 4절의 통과가
        「크기 검사 때문」인지 「가짜의 다른 성질 때문」인지 안 갈린다.
        """
        execution, port = _dispatch(CREATE, dict(self._FULL_ACK), frozenset())
        assert "plan" in json.loads(execution.result.content)
        assert port.executed, "정답 열거인데 한 줄도 안 나갔다"

    def test_an_unread_container_lets_the_same_undersized_enumeration_write(self):
        """팔 ③ — 그 살아 있는 검사가 미판독일 때만 죽는다. **같은 인자다.**"""
        execution, port = _dispatch(CREATE, dict(self._SHORT_ACK), _DEAD_FIXTURES)
        payload = json.loads(execution.result.content)
        assert "plan" in payload, (
            "미판독 단면에서 부족분 미달 열거가 이제 거절된다 — 수리된 것이니 "
            "t163 이 세운 수리 카드를 닫아라"
        )
        assert port.executed, (
            "계획은 섰는데 발화가 0줄이다 — 이 검사가 재려는 것은 **발화까지 갔다**는 "
            "사실이다. 수리됐다면 t163 수리 카드를 닫아라"
        )
        assert any(c.startswith("Store Group ") for c in port.executed), (
            "쓰기가 실제로 나갔는지가 이 검사의 요점이다: " + str(port.executed)
        )
