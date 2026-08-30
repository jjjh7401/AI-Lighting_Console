"""t152 — `import_lxseq_groups` 가 콘솔에 **무엇을 요청하는가**를 고정한다.

왜 이 파일이 필요한가. 이 도구는 `collect_rig_sections` 에 `groups`·`fixtures`
두 섹션을 요청하는데 `fixtures` 단면을 **한 번도 읽지 않는다**(소비 지점은
`sections["groups"]` 하나뿐). 그런데 그 요청을 그냥 줄이면 낭비만 사라지는 게
아니다 — `collect_rig_sections` 의 실패 분류가 **형제 섹션이 답했는지**를 세므로
(`server/orchestrator/tools.py` 의 `reason = REASON_UNRESOLVED if resolved else
REASON_UNREACHABLE`), 형제가 사라지면 `groups` 실패의 사유가
`path_not_resolved` 에서 `console_unreachable` 로 바뀐다.

t152 배차 시점에 그 변화를 잡는 단언이 이 저장소에 **한 자리도 없었다**
(`test_lxseq_group_tool` · `test_lxseq_group_apply_path` · `test_sheets_registry` ·
`test_sheet_pipe_content_arg` 넷 다 요청 섹션 집합도 실패 사유도 안 본다).
검사 부재는 안전이 아니라 **조용히 바뀐다**는 뜻이므로, 판정보다 이 파일이 먼저다.

**뮤테이션 예고** (맞히려고가 아니라 틀렸을 때 무엇이 틀렸는지 알려고 적는다):

  1) 요청 집합에서 `fixtures` 를 뺀다        -> 1절 두 검사가 죽는다고 본다
  2) 실패 분류 삼항을 뒤집는다               -> 2절 두 검사가 죽는다고 본다
  3) 사유를 페이로드에 실어 보낸다           -> 3절 특성화 검사가 죽는다고 본다
                                              (죽으면 **t152 를 다시 열어라** --
                                               그 순간 요청 집합 축소가 관측
                                               가능한 변화가 되기 때문이다)
  4) `read_existing_fids` 의 예외를 잡는다    -> 4절 특성화 검사가 죽는다고 본다

3절·4절은 **계약이 아니라 실측 기록**이다. 지금 그렇다는 것이지 그래야 한다는
뜻이 아니다. 초록이 정당화가 아니라는 것을 각 검사 본문에 적어 둔다.
"""

from __future__ import annotations

import base64
import csv
import io
import json
from pathlib import Path

import pytest

from server.llm.types import ToolCall
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import (
    DEFAULT_RIG_CONTEXT_PATHS,
    REASON_UNREACHABLE,
    REASON_UNRESOLVED,
    build_toolset,
    collect_rig_sections,
)
from server.rig.section import SECTION_UNREAD
from server.safety.console import StateQueryError
from server.vwx.patchplan import FID_PROPERTY_NAME

GROUP_CSV = Path("server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.group.csv")
PATCH_CSV = Path("server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv")

FIXTURES_PATH = DEFAULT_RIG_CONTEXT_PATHS["fixtures"]
GROUPS_PATH = DEFAULT_RIG_CONTEXT_PATHS["groups"]

TOOL = "import_lxseq_groups"

# 실기 실측값(t151 이 잰 것): fixtures childCount 86, 응답기가 19에서 자른다.
# 창을 24가 아니라 19로 두는 이유는 그 실측이 **개수 캡이 아니라 바이트 예산**에서
# 잘렸음을 말하기 때문이다 -- 24로 두면 페이징 자체가 안 발화해 1절 (b)가 공허해진다.
_LIVE_WINDOW = 19


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _patch_fids() -> list[int]:
    text = PATCH_CSV.read_text(encoding="utf-8-sig")
    out: list[int] = []
    for row in csv.DictReader(io.StringIO(text)):
        raw = (row.get("FID") or "").strip()
        if raw.isdigit():
            out.append(int(raw))
    return sorted(set(out))


class _SilentPort:
    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, command: str) -> ExecutionResult:
        self.executed.append(command)
        return ExecutionResult(ok=True, detail="OK")


class _Console:
    """절단하는 픽스처 컨테이너 + 빈 그룹 풀.

    `dead` 에 든 경로는 **예외를 던진다**. 그것이 프로덕션 포트의 실패 형태다
    (`server/safety/console.py` 의 `query_state` 독스트링: "raises on
    failure/timeout") -- `ok=False` 를 돌려주는 형태로 가짜를 지으면 이 파일이
    재려는 갈래를 아예 안 탄다.
    """

    def __init__(self, fids: list[int], dead: frozenset[str] = frozenset()) -> None:
        self._fids = fids
        self._dead = dead
        self._children = [dict(i=s, name="Spot " + str(s)) for s in range(1, len(fids) + 1)]
        self.state_calls: list[tuple[str, int]] = []

    def query_state(self, path: str, offset: int = 0) -> dict:
        self.state_calls.append((path, offset))
        if path in self._dead:
            raise LookupError("console did not answer: " + path)
        if path == GROUPS_PATH:
            return dict(ok=True, truncated=False, node=dict(childCount=0), children=[])
        if path == FIXTURES_PATH:
            window = self._children[offset : offset + _LIVE_WINDOW]
            return dict(
                ok=True,
                truncated=offset + len(window) < len(self._children),
                offset=offset,
                node=dict(childCount=len(self._children)),
                children=window,
            )
        raise LookupError("unknown object path: " + path)

    def query_property(self, path: str, property_name: str) -> dict:
        prefix = FIXTURES_PATH + "/"
        if path.startswith(prefix) and property_name == FID_PROPERTY_NAME:
            tail = path[len(prefix) :]
            if tail.isdigit() and 1 <= int(tail) <= len(self._fids):
                return dict(ok=True, value=str(self._fids[int(tail) - 1]))
        return dict(ok=False, error="property not readable: " + property_name)


class _DeadPort:
    """`collect_rig_sections` 를 직접 태우는 최소 포트."""

    def __init__(self, dead: frozenset[str]) -> None:
        self._dead = dead

    def query_state(self, path: str, offset: int = 0) -> dict:
        if path in self._dead:
            raise LookupError("console did not answer: " + path)
        return dict(ok=True, truncated=False, node=dict(childCount=0), children=[])


class _ApprovePort:
    def request_approval(self, request) -> bool:
        return True


def _dispatch(console: _Console):
    port = _SilentPort()
    registry = build_toolset(
        execution_port=port,
        state_port=console,
        property_port=console,
        group_approval_port=_ApprovePort(),
    )
    return registry.dispatch(
        ToolCall(
            id="t152",
            name=TOOL,
            arguments=dict(
                group_content_base64=_b64(GROUP_CSV),
                patch_content_base64=_b64(PATCH_CSV),
                action="preview",
            ),
        )
    )


class TestRequestedSectionSet:
    """1절 -- 이 도구가 콘솔에 요청하는 섹션 집합을 고정한다.

    팔이 둘이다. (a)는 수집기에 넘어가는 인자를 직접 본다. (b)는 수집기를
    안 건드리고 **콘솔에 실제로 간 바이트**로 같은 것을 재는데, 이 둘은 서로를
    가리지 않는다: (a)만 있으면 수집기를 인라인해 버리는 변경을 못 잡고,
    (b)만 있으면 `read_existing_fids` 가 같은 경로를 별도로 읽기 때문에
    「fixtures 를 요청했다」와 구분되지 않는다.
    """

    def test_the_collector_is_asked_for_exactly_groups_and_fixtures(self, monkeypatch):
        from server.orchestrator import tools as tools_module

        seen: list[tuple[str, ...]] = []

        def _spy(state_port, paths, drilldown, budget):
            seen.append(tuple(sorted(paths)))
            return collect_rig_sections(state_port, paths, drilldown, budget)

        monkeypatch.setattr(tools_module, "collect_rig_sections", _spy)
        execution = _dispatch(_Console(_patch_fids()))
        assert execution.result.is_error is False, execution.result.content
        # 비공허성 -- 스파이가 한 번도 안 불렸으면 아래 대조가 자동 참이 된다.
        assert seen, "이 도구가 collect_rig_sections 를 부르지 않았다"
        assert seen == [("fixtures", "groups")], (
            "요청 섹션 집합이 바뀌었다. 이건 낭비 조정이 아니라 실패 분류 변경이다 "
            "-- t152 와 2절을 읽고 결정하라: " + str(seen)
        )

    def test_the_fixtures_section_is_walked_to_the_end_not_just_probed(self):
        """(b) 관측 팔 -- 섹션 요청이면 **끝까지 걷는다**(t151).

        `read_existing_fids` 도 같은 경로를 읽지만 offset 0 한 번뿐이다. 그래서
        0을 넘는 offset 의 존재가 「섹션으로도 요청했다」의 관측 가능한 지문이다.
        """
        console = _Console(_patch_fids())
        execution = _dispatch(console)
        assert execution.result.is_error is False, execution.result.content
        offsets = [o for path, o in console.state_calls if path == FIXTURES_PATH]
        assert offsets, "fixtures 경로를 한 번도 안 읽었다"
        assert [o for o in offsets if o > 0], (
            "fixtures 를 offset 0 으로만 읽었다 -- 섹션 요청이 사라졌다는 지문이다. "
            "요청 집합을 줄였다면 2절의 실패 분류 변경을 같이 판정하라. offsets=" + str(offsets)
        )
        # 대조군 -- 그룹 풀은 절단이 없으므로 한 번이어야 한다. 이게 없으면 위 단언이
        # 「모든 경로를 여러 번 읽는다」인지 「이 경로만 걷는다」인지 안 갈린다.
        assert [o for path, o in console.state_calls if path == GROUPS_PATH] == [0]


_BOTH_SECTIONS = dict(groups=GROUPS_PATH, fixtures=FIXTURES_PATH)
_GROUPS_ALONE = dict(groups=GROUPS_PATH)
_DEAD_GROUPS = frozenset([GROUPS_PATH])
_DEAD_BOTH = frozenset([GROUPS_PATH, FIXTURES_PATH])


class TestFailureClassificationDependsOnTheSibling:
    """2절 -- 형제 섹션을 빼면 `groups` 실패의 **사유가 바뀐다**.

    t152 의 차단 근거를 산문이 아니라 실행으로 들고 있는 자리다. 두 검사가
    같은 실패(그룹 풀이 안 답함)에 대해 서로 다른 사유를 단언한다 -- 차이를
    만드는 것은 오직 요청 집합이다.
    """

    def test_a_dead_groups_path_beside_a_live_sibling_blames_the_path(self):
        summary, resolved, failed = collect_rig_sections(
            _DeadPort(_DEAD_GROUPS), _BOTH_SECTIONS, frozenset(), 0
        )
        assert (resolved, failed) == (1, 1)
        assert summary["groups"]["reason"] == REASON_UNRESOLVED
        assert summary["groups"]["reason"] != REASON_UNREACHABLE, (
            "형제가 답했는데 콘솔이 죽었다고 말한다 -- 사람이 콘솔을 고치러 가서 안 낫는다"
        )

    def test_the_same_dead_path_alone_blames_the_console(self):
        summary, resolved, failed = collect_rig_sections(
            _DeadPort(_DEAD_GROUPS), _GROUPS_ALONE, frozenset(), 0
        )
        assert (resolved, failed) == (0, 1)
        assert summary["groups"]["reason"] == REASON_UNREACHABLE, (
            "형제가 없으면 어느 경로도 탓할 수 없다 -- 이것이 t152 가 요청 집합을 "
            "함부로 줄이면 안 되는 이유다"
        )


class TestTheClassifiedReasonReachesThePayload:
    """3절 -- **수리 확인(t167)**: 2절이 가른 사유가 이제 이 도구의 출력에 나온다.

    t152 가 이 자리를 열었고 t163 이 전수로 「접는 자리는 하나」라고 지목했다.
    t167 이 재보니 **카드 문면이 부정확했다**: `map_groups` 가 튜플을 「버린」
    것이 맞지만, 페이로드의 `console_read_reason` 은 애초에 **다른 축**(FID
    판독) 것이었다. `console_read_incomplete` 는 두 축에서 서는데(FID 축과
    단면 축) 사유 채널은 FID 축에만 걸려 있었고, 단면 축으로 True 가 서려면
    FID 게이트를 통과해야 하므로 그 조합은 **항상 「참 플래그 + 빈 사유」**였다.

    수리는 형제(`preset_mapper`)와 **같은 이름** 두 필드를 더하는 것이다.
    `console_read_reason` 은 안 건드린다 -- 두 축이 두 채널을 갖는 것이 정직하다.

    ⚠️ 이 층에서 관측 가능한 분류는 **하나뿐**이다. 4절이 기록하듯
    `console_unreachable` 은 이 도구에서 예외로 먼저 죽어 도달하지 못한다.
    「두 사유가 실제로 갈리는가」는 매퍼 층에서 잰다
    (`test_unmeasured_is_not_empty.py`).
    """

    def test_a_refused_groups_section_now_carries_the_classified_reason(self):
        console = _Console(_patch_fids(), dead=_DEAD_GROUPS)
        execution = _dispatch(console)
        assert execution.result.is_error is False, execution.result.content
        payload = json.loads(execution.result.content)
        assert payload["console_read_incomplete"] is True
        assert payload["batches"] == [], "못 읽은 단면 위에서 배치를 만들었다"
        # 성질 단언 -- 공유 술어의 코드를 그대로 나른다(이 도메인은 자기 어휘가 없다).
        assert payload["refusal"] == SECTION_UNREAD, (
            "단면 축 사유가 페이로드에 없다 -- t167 수리가 풀렸다: " + str(payload.get("refusal"))
        )
        # 문구 단언 -- **어느** 분류인지까지. 성질 단언과 다른 행이다(규약 §3):
        # 코드는 두 분류에서 같고, 갈리는 것은 detail 이다.
        assert REASON_UNRESOLVED in (payload["refusal_detail"] or ""), (
            "거절은 실렸는데 어느 분류인지가 없다: " + str(payload.get("refusal_detail"))
        )

    def test_the_fid_axis_channel_is_untouched(self):
        """축 분리 -- 단면 축을 실었다고 FID 축 채널을 뺏지 않았다.

        이 팔이 없으면 위 검사의 초록이 「단면 사유가 도달한다」인지
        「`console_read_reason` 을 단면 것으로 갈아끼웠다」인지 안 갈린다.
        """
        console = _Console(_patch_fids(), dead=_DEAD_GROUPS)
        payload = json.loads(_dispatch(console).result.content)
        assert payload["console_read_reason"] is None, (
            "FID 축 채널에 단면 사유가 들어갔다 -- 두 축이 한 채널로 합쳐졌다"
        )

    def test_the_collector_did_produce_a_reason_for_that_same_failure(self):
        """생산자 팔 -- 분류는 원래 나오고 있었다. 잃던 자리는 소비자였다."""
        summary, _resolved, _failed = collect_rig_sections(
            _DeadPort(_DEAD_GROUPS), _BOTH_SECTIONS, frozenset(), 0
        )
        assert summary["groups"]["reason"] == REASON_UNRESOLVED


class TestADeadFixturesPathCrashesInsteadOfRefusing:
    """4절 -- **실측 기록**: 픽스처 경로가 안 답하면 도구가 거절이 아니라 죽는다.

    초록이 「그래도 된다」는 뜻이 **아니다**. `collect_rig_sections` 는 예외를
    잡아 `console_unreachable` 로 분류하지만, 바로 다음 줄의
    `read_existing_fids` 는 같은 경로를 **안 잡고** 다시 읽는다
    (`server/vwx/patchplan.py` 의 `_existing_fids_from_console` 은
    `ok is not True` 만 보고 예외는 안 본다). 그래서 이 도구에서
    `console_unreachable` 은 **끝까지 도달하지 못하는 분류**다 -- 2절이 가른
    두 사유 중 하나는 여기서 관측 자체가 불가능하다.

    이것이 t152 의 물음 (a)에 대한 실측 답이다: 「groups 단독에서
    console_unreachable 이 맞는 사유인가」를 묻기 전에, 이 도구는 그 사유를
    사용자에게 낼 수 있는 경로가 없다.
    """

    def test_the_tool_raises_before_it_can_report_console_unreachable(self):
        console = _Console(_patch_fids(), dead=_DEAD_BOTH)
        with pytest.raises(LookupError):
            _dispatch(console)

    def test_a_live_console_does_not_raise(self):
        """대조군 -- 위 예외가 「이 가짜는 늘 터진다」가 아님을 보인다."""
        execution = _dispatch(_Console(_patch_fids()))
        assert execution.result.is_error is False, execution.result.content


# ---------------------------------------------------------------------------
# t182 5절 -- 콘솔이 안 답해도 이 도구는 죽지 않고 사유를 낸다
#
# 고치기 전 실측: 픽스처 경로가 안 답하면 `read_existing_fids` 가 잡히지 않은
# 예외로 죽었고, 그 예외는 `session.py` 의 `except Exception` 까지 올라가
# kind='unexpected' + 「서버 내부 문제가 발생했습니다 … 진단 로그를 확인해
# 주세요」로 접혔다. 콘솔이 안 답한 것을 서버 문제라 하는 거짓 귀속이다.
#
# 4절이 그 죽음을 실측 기록으로 남겼는데, 그 4절은 `LookupError` 를 던지는 가짜로
# 쟀다. **프로덕션 포트가 던지는 것은 `StateQueryError` 다**
# (`server/safety/console.py:89`) -- 형태(예외)는 맞고 종류가 틀렸다. 그래서 이
# 절은 실물 종류로 쏜다. 4절은 그대로 둔다: `LookupError` 는 이 수리가 잡는
# 종류가 아니므로 여전히 죽는 것이 맞고, 그 초록이 **넓히지 않았다**는 증거다.
#
# 수리 자리: 개념(`unreadable_root`)은 `server/vwx/patchplan.py` 에, catch 는
# 호출부에. 순수 로직 층이 `server.safety` 를 임포트한 선례가 0건이라
# 그 방향으로 첫 발을 떼지 않았다 -- 근거는 그 헬퍼 독스트링에 있다.
# ---------------------------------------------------------------------------


class _RaisingFixtureRoot:
    """픽스처 루트만 예외로 만든다. 종류를 밖에서 받는다.

    `FID_FIXTURE_ROOT` 와 `FIXTURES_PATH` 는 **같은 경로**라, 이 하나를 죽이면
    단면 판독과 FID 판독이 함께 실패한다 -- 실물에서 일어나는 조합이다.
    """

    def __init__(self, base, exc_type) -> None:
        self._base = base
        self._exc_type = exc_type

    def _dead(self, path: str) -> bool:
        return path == FIXTURES_PATH or path.startswith(FIXTURES_PATH + "/")

    def query_state(self, path, *args, **kwargs):
        if self._dead(path):
            raise self._exc_type("no state reply for " + repr(path) + " within 5.0s")
        return self._base.query_state(path, *args, **kwargs)

    def query_property(self, path, property_name):
        if self._dead(path):
            raise self._exc_type("no prop reply for " + repr(path) + " within 5.0s")
        return self._base.query_property(path, property_name)

    def __getattr__(self, name):
        return getattr(self._base, name)


class _NotOkFixtureRoot(_RaisingFixtureRoot):
    """팔 B -- 콘솔이 답은 하는데 `ok=False` 다.

    이쪽은 고치기 전에도 정상 동작했다. 같은 사유로 도착해야 두 실패 형태가
    한 자리로 모였다는 뜻이고, 그게 이 수리의 요지다.
    """

    def query_state(self, path, *args, **kwargs):
        if self._dead(path):
            return dict(ok=False, error="console did not answer")
        return self._base.query_state(path, *args, **kwargs)

    def query_property(self, path, property_name):
        if self._dead(path):
            return dict(ok=False, error="not readable")
        return self._base.query_property(path, property_name)


_ROOT_UNREAD_REASON = "콘솔의 픽스처 루트 상태를 읽지 못했다"


def _payload_of(port):
    execution = _dispatch(port)
    assert execution.result.is_error is False, execution.result.content
    return json.loads(execution.result.content)


class TestASilentConsoleIsReportedNotCrashed:
    def test_the_tool_survives_and_names_the_console(self):
        """거짓 귀속 트립와이어.

        둘이 동시에 걸린다. (1) `_dispatch` 가 **예외를 안 낸다** -- catch 를
        지우면 여기서 죽어 빨개진다. 그게 고치기 전 상태이고 사용자에게는
        「서버 내부 문제」로 갔다. (2) 사유 문자열이 **콘솔을 가리킨다**.
        「살아남았다」만 보면 둘 다 놓친다.
        """
        payload = _payload_of(_RaisingFixtureRoot(_Console(_patch_fids()), StateQueryError))

        assert payload["console_read_incomplete"] is True
        assert payload["console_read_reason"] == _ROOT_UNREAD_REASON

    def test_both_failure_shapes_arrive_at_the_same_reason(self):
        """팔 B -- 기존 갈래를 안 깨뜨렸고, 두 형태가 한 자리로 모였다.

        `ok=False` 는 고치기 전에도 이 사유로 도착했다. 예외 형태만 그 갈래를
        못 타서 죽었다. 두 값이 같아야 `unreadable_root()` 하나가 둘의 주인이다.
        이 팔이 없으면 「한쪽만 덮던 것을 양쪽으로 넓혔다」가 추론이 된다.
        """
        raised = _payload_of(_RaisingFixtureRoot(_Console(_patch_fids()), StateQueryError))
        not_ok = _payload_of(_NotOkFixtureRoot(_Console(_patch_fids()), StateQueryError))

        assert raised["console_read_reason"] == not_ok["console_read_reason"]
        assert not_ok["console_read_reason"] == _ROOT_UNREAD_REASON

    def test_an_unrelated_bug_is_not_swallowed(self):
        """넓히기 방지 -- `except Exception` 으로 바꾸면 여기서 빨개진다.

        무관한 버그를 「콘솔이 안 답했다」로 보고하면, 이 수리가 없앤 거짓 귀속을
        **방향만 뒤집어** 새로 만든다. 감독은 이번엔 콘솔을 뒤지는데 고장난 곳은
        코드다. 그래서 잡는 종류를 못 박고 그 밖은 올려보낸다.
        """
        with pytest.raises(ValueError):
            _dispatch(_RaisingFixtureRoot(_Console(_patch_fids()), ValueError))

    def test_a_live_console_carries_no_such_reason(self):
        """대조군 -- 이 사유가 늘 붙는 게 아님을 보인다.

        이 팔이 없으면 위 검사들은 사유를 상수로 하드코딩해도 초록이 난다.
        """
        payload = _payload_of(_Console(_patch_fids()))

        assert payload["console_read_incomplete"] is False
        assert payload["console_read_reason"] is None
