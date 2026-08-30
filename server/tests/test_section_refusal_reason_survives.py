"""t163 — 섹션 실패 **사유**가 소비자를 지나 사용자에게 닿는가 (t166 에서 수리 확인으로 전환).

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

🔴 **2026-08-30 t166 이 수리했다 — 위 M1~M4 는 수리 이전의 측정 기록이다(만료 고지).**

3절·4절은 이제 **실측 기록이 아니라 수리 확인**이다. M3 이 「수리 형태」로 돌려본
그 모양이 실제 처방이 됐다: 미판독 단면은 사유를 실어 보고되고(3절), 부분판독
쓰기는 부족분을 못 재면 건너뛰지 않고 **거절된다**(4절, fail-closed). 초록이
이제 계약이고, 빨강은 수리가 풀렸다는 뜻이다.

t166 이 더한 팔 셋:

  대조군 ② 정상·완전 컨테이너는 아무것도 보고하지 않는다 — 이 필드가 True 로
           고정된 것이 아님을 보인다
  팔 ④    맞는 길이의 열거도 미판독에서는 거절된다 — 거절의 축이 **크기가 아니라
           판독 가능성**임을 보인다
  축 분리  childCount 부재는 **여전히** 크기 검사를 건너뛴다 — 수리가 이웃 축을
           덮치지 않았음을 고정한다(규약 §3 「축 하나만」의 검사판)
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


def _console(
    dead: frozenset[str],
    *,
    declared: int | None = 8,
    listed: int = 4,
    truncated: bool = True,
):
    """그룹 풀(빈) + 절단된 픽스처 컨테이너.

    `dead` 의 경로는 **예외를 던진다** — 프로덕션 포트의 실패 형태다
    (`server/safety/console.py` 의 `query_state`: "raises on failure/timeout").
    `ok=False` 를 돌려주는 가짜를 쓰면 이 파일이 재려는 갈래를 안 탄다.
    """
    states = dict()
    states[GROUPS_PATH] = dict(ok=True, truncated=False, node=dict(childCount=0), children=[])
    states[FIXTURES_PATH] = dict(
        ok=True,
        truncated=truncated,
        # `declared=None` 은 「응답기가 childCount 를 안 줬다」를 만든다 —
        # 미판독과 **인접하지만 다른** 축이다(t166 축 분리 검사가 쓴다).
        node=dict(childCount=declared) if declared is not None else dict(),
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


class TestAnUnreadFixtureSectionIsReportedAsUnread:
    """3절 — 수리 확인(t166): 못 읽은 픽스처 컨테이너가 「절단 아님」으로 안 나간다.

    t163 이 이 자리를 기록했을 때는 **초록이 결함**이었다. 실패 단면에는
    `truncated` 키가 아예 없어 `bool(...)` 이 False 가 되고, 한 글자도 안 읽은
    상태가 「깨끗하게 다 읽었다」와 바이트 동일로 나갔다. 그 값은 승인 카드의
    위험 사유에도 실리므로, 쓰기를 승인하는 사람이 「리그를 못 읽었다」를 못 봤다.

    거절 갈래가 둘(미판독·절단)이라 **어느 사유인지**를 문자열로 단언한다 —
    「보고는 됐다」만 보면 거짓 사유가 참 사유를 가린다(규약 §3).
    """

    #: 미판독 사유에만 나오는 문면. 절단 사유에는 없다.
    _UNREAD_PHRASE = "한 줄도 못 읽었다"

    def test_an_unread_fixture_container_says_so_and_names_the_reason(self):
        execution, _port = _dispatch(
            CREATE,
            dict(groups=[dict(name="Plain", fids=[2, 3])]),
            _DEAD_FIXTURES,
        )
        payload = json.loads(execution.result.content)
        assert "plan" in payload, "그룹 풀은 살아 있으므로 계획은 서야 한다"
        assert payload.get("fixture_list_truncated") is True, (
            "미판독 단면이 다시 「절단 아님」으로 나간다 — t166 수리가 풀렸다"
        )
        reason = payload.get("fixture_list_truncated_reason") or ""
        assert self._UNREAD_PHRASE in reason, (
            "미판독인데 사유가 미판독이라고 말하지 않는다: " + reason
        )
        blob = json.dumps(payload, ensure_ascii=False)
        assert REASON_UNRESOLVED in blob or REASON_UNREACHABLE in blob, (
            "픽스처 축 사유 코드가 페이로드에 도달하지 않는다"
        )

    def test_a_truncated_but_readable_container_says_truncated_not_unread(self):
        """대조군 ① — 두 사유가 갈린다. 절단은 절단으로 보고된다."""
        execution, _port = _dispatch(
            CREATE, dict(groups=[dict(name="Plain", fids=[2, 3])]), frozenset()
        )
        payload = json.loads(execution.result.content)
        assert payload.get("fixture_list_truncated") is True
        reason = payload.get("fixture_list_truncated_reason") or ""
        assert reason, "절단인데 사유가 비었다"
        assert self._UNREAD_PHRASE not in reason, (
            "절단을 미판독 사유로 보고한다 — 두 갈래가 다시 섞였다: " + reason
        )

    def test_a_healthy_untruncated_container_reports_nothing(self):
        """대조군 ② — 이 필드가 True 로 고정된 것이 아님을 보인다.

        이 팔이 없으면 위 두 검사는 필드를 하드코딩해도 초록이 난다.

        `declared` 와 `listed` 를 맞추는 것이 요점이다: 가짜의 `truncated=False`
        만으로는 부족하다. `paged_children` 은 `childCount` 가 도착 수보다 크면
        다음 창을 요청하고, 이 가짜는 `offset` 을 에코하지 않아 **무진전**으로
        걸려 절단을 정직하게 보고한다(`server/rig/paging.py:98`). 즉 완전한
        컨테이너는 「더 있다고 주장하지 않는」 컨테이너다.
        """
        execution, _port = _dispatch(
            CREATE,
            dict(groups=[dict(name="Plain", fids=[2, 3])]),
            frozenset(),
            declared=4,
            listed=4,
            truncated=False,
        )
        payload = json.loads(execution.result.content)
        assert payload.get("fixture_list_truncated") is False
        assert payload.get("fixture_list_truncated_reason") == ""


class TestAnUnreadFixtureSectionRefusesThePartialWrite:
    """4절 — 수리 확인(t166): 미판독 단면이 크기 검사를 끄는 대신 쓰기를 거절한다.

    t163 이 기록한 결함: 부분판독 쓰기 거절(SPEC-COPILOT-TRUNCATE-001
    REQ-TRUNCATE-008 / AC-TRUNCATE-008)은 열거 개수를 부족분(`childCount` 빼기
    열거된 수)과 대조하는데, 미판독 단면에선 `total` 이 None 이라 그 대조가 통째로
    건너뛰어졌다. 면제 사유를 적은 주석은 그 None 을 「응답기가 childCount 를 안
    줬을 때」로만 설명했다 — 참인데 **범위가 미판독을 안 덮었다.**

    수리 방향은 fail-closed 다: 부족분을 못 재면 건너뛰는 게 아니라 거절한다.
    그룹 쓰기는 멤버십을 되읽을 수 없어 되돌릴 수 없기 때문이다.
    """

    #: 부족분 = declared 8 - listed 4 = 4. 길이 1 열거는 크기 검사에 걸려야 한다.
    _SHORT_ACK = dict(groups=[_PARTIAL], acknowledged_unread_fids=[5])
    _FULL_ACK = dict(groups=[_PARTIAL], acknowledged_unread_fids=[5, 6, 7, 8])
    #: 미판독 거절에만 나오는 문면. 크기 미달 거절에는 없다.
    _UNREAD_PHRASE = "부족분 자체를 잴 수 없다"

    def test_a_healthy_container_refuses_an_undersized_enumeration(self):
        """팔 ① — 크기 검사가 **살아 있다**. 그리고 그 사유로 거절한다."""
        execution, port = _dispatch(CREATE, dict(self._SHORT_ACK), frozenset())
        assert execution.result.is_error is True
        assert port.executed == [], "부족분에 못 미치는 열거로 콘솔에 발화했다"
        assert "acknowledged_unread_fids" in execution.result.content
        assert self._UNREAD_PHRASE not in execution.result.content, (
            "크기 미달을 미판독 사유로 거절한다 — 거짓 사유가 참 사유를 가린다"
        )

    def test_a_correctly_sized_enumeration_gets_through_on_the_same_console(self):
        """팔 ② — 위 거절이 「이 가짜는 늘 거절한다」가 아님을 보인다."""
        execution, port = _dispatch(CREATE, dict(self._FULL_ACK), frozenset())
        assert "plan" in json.loads(execution.result.content)
        assert port.executed, "정답 열거인데 한 줄도 안 나갔다"

    def test_an_unread_container_refuses_the_same_undersized_enumeration(self):
        """팔 ③ — 죽어 있던 검사가 산다. **팔 ① 과 같은 인자다.**"""
        execution, port = _dispatch(CREATE, dict(self._SHORT_ACK), _DEAD_FIXTURES)
        assert execution.result.is_error is True, (
            "미판독 단면에서 부분판독 쓰기가 다시 통과한다 — t166 수리가 풀렸다"
        )
        assert port.executed == [], "거절인데 콘솔에 나갔다: " + str(port.executed)
        assert self._UNREAD_PHRASE in execution.result.content, (
            "거절은 됐는데 사유가 미판독이 아니다: " + execution.result.content
        )

    def test_an_unread_container_refuses_even_a_correctly_sized_enumeration(self):
        """팔 ④ — 거절의 축이 **크기가 아니라 판독 가능성**임을 보인다.

        팔 ② 에서 통과한 바로 그 열거다. 미판독에서는 부족분을 모르므로
        「맞는 길이」라는 판정 자체가 설 수 없다 — 그래서 fail-closed 다.
        이 팔이 없으면 팔 ③ 의 거절이 「크기 때문」인지 「미판독 때문」인지
        갈리지 않는다.
        """
        execution, port = _dispatch(CREATE, dict(self._FULL_ACK), _DEAD_FIXTURES)
        assert execution.result.is_error is True
        assert port.executed == []
        assert self._UNREAD_PHRASE in execution.result.content

    def test_an_unknown_childcount_still_skips_the_size_check(self):
        """축 분리 — 인접한 다른 상태는 **바뀌지 않았다**.

        응답기가 childCount 를 안 주면 `total` 은 여전히 None 이고 크기 대조는
        적용되지 않는다(나머지 셋은 그대로 산다). 이 팔이 없으면 t166 의 수리가
        두 상태를 **반대 방향으로** 다시 뭉갠 것인지 갈리지 않는다 — 규약 §3
        「뮤테이션은 재려는 축 하나만」의 검사판이다.
        """
        execution, port = _dispatch(
            CREATE,
            dict(self._SHORT_ACK),
            frozenset(),
            declared=None,
            truncated=False,
        )
        assert "plan" in json.loads(execution.result.content), (
            "childCount 부재까지 거절하게 됐다 — 수리가 이웃 축을 덮쳤다"
        )
        assert port.executed, "계획은 섰는데 발화가 0줄이다"
