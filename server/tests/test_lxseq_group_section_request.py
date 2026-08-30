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


class TestTheClassifiedReasonNeverReachesThePayload:
    """3절 -- **실측 기록**: 2절이 가른 사유는 이 도구의 출력에 안 나온다.

    초록이 「그래도 된다」는 뜻이 **아니다**. `map_groups` 가 `section_refusal`
    의 (코드, 사유) 쌍을 받아 `console_read_incomplete=True` 불리언 하나로
    접고, 페이로드의 `console_read_reason` 은 섹션이 아니라 `fid_read` 에서
    온다. 그래서 2절의 두 사유는 이 도구의 사용자에게 **바이트 동일**하다.

    이 검사가 빨개지는 날은 그 손실이 고쳐진 날이고, 그때 t152 의 판정
    (요청 집합 축소가 관측 가능한 변화를 만드는가)이 뒤집힌다.
    """

    def test_a_refused_groups_section_reports_incomplete_with_no_reason(self):
        console = _Console(_patch_fids(), dead=_DEAD_GROUPS)
        execution = _dispatch(console)
        assert execution.result.is_error is False, execution.result.content
        payload = json.loads(execution.result.content)
        assert payload["console_read_incomplete"] is True
        assert payload["batches"] == [], "못 읽은 단면 위에서 배치를 만들었다"
        assert payload["console_read_reason"] is None, (
            "섹션 사유가 페이로드에 도달한다 -- t152 를 다시 열어라"
        )
        # 대조군 -- 사유가 **생산되지 않은** 것이 아니라 **버려진** 것임을 보인다.
        # 이게 없으면 위 None 이 '분류가 없다'인지 '분류를 안 싣는다'인지 안 갈린다.
        blob = json.dumps(payload, ensure_ascii=False)
        for reason in (REASON_UNRESOLVED, REASON_UNREACHABLE):
            assert reason not in blob, "사유 문자열이 페이로드 어딘가에 있다: " + reason

    def test_the_collector_did_produce_a_reason_for_that_same_failure(self):
        """위 검사의 반대 팔 -- 생산자는 분류를 냈다. 잃은 자리는 소비자다."""
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
