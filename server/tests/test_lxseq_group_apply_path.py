"""t66 — M4 apply 경로 회귀. **가짜 run 이 아니라 진짜 `_run_batch` 를 태운다.**

왜 이 파일이 필요한가. `test_lxseq_group_tool.py::TestBatchDispatchPolicy` 는
`apply_group_batches` 에 **람다를 넣어** 순차 중단·재시도 없음을 잰다. 그
람다가 대체하는 것이 정확히 `_run_batch` 이고, d7ef181 이 고친 결함 셋은 전부
그 12줄 안에 있었다:

  1. `fid_read.complete()` — @property 를 호출했다
  2. `ToolCall(...)` — 필수 인자 `id` 를 빠뜨렸다
  3. `execution.result.status` / `.payload` — `ToolResult` 에 없는 필드다

셋 다 **정적으로는 안 보이고 실행해야 나온다.** 그리고 그 경로는 P3 미충족
때문에 작성 이후 한 번도 실행된 적이 없었다. 검사가 그 함수를 스텁으로
바꿔치기하는 한 몇 번을 돌려도 안 나온다 — 검사 자신이 공허했다.

그래서 이 파일은 `import_lxseq_groups` 를 `action="apply"` 로 **디스패치해서**
진짜 배치 러너가 돌게 한다. 콘솔만 가짜다.
"""

from __future__ import annotations

import base64
import csv
import io
import json
import re
from pathlib import Path

from server.llm.types import ToolCall
from server.orchestrator.ports import ExecutionResult
from server.orchestrator.tools import DEFAULT_RIG_CONTEXT_PATHS, build_toolset
from server.vwx.patchplan import FID_PROPERTY_NAME

GROUP_CSV = Path("server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.group.csv")
PATCH_CSV = Path("server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv")

FIXTURES_PATH = DEFAULT_RIG_CONTEXT_PATHS["fixtures"]
GROUPS_PATH = DEFAULT_RIG_CONTEXT_PATHS["groups"]

TOOL = "import_lxseq_groups"


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def _patch_fids() -> list[int]:
    text = PATCH_CSV.read_text(encoding="utf-8-sig")
    out = []
    for row in csv.DictReader(io.StringIO(text)):
        raw = (row.get("FID") or "").strip()
        if raw.isdigit():
            out.append(int(raw))
    return sorted(set(out))


_STORE = re.compile(r"^Store Group (\d+)$")
_LABEL = re.compile(r"^Label Group (\d+) '(.*)'$")


class _RecordingExecutionPort:
    """발화를 기록하고, `Store`/`Label` 의 **효과**를 들고 있는다.

    효과를 안 들면 가짜 콘솔이 `Store` 뒤에도 그 슬롯을 모른다고 답하고, 툴의
    재조회 검증이 항상 실패한다 — 그러면 이 테스트는 「배치가 돌았다」는 것만
    재고 「무엇을 만들었나」는 못 잰다.
    """

    def __init__(self) -> None:
        self.executed: list[str] = []
        self.stored: set[int] = set()
        self.labels: dict[int, str] = dict()

    def execute(self, command: str) -> ExecutionResult:
        self.executed.append(command)
        stored = _STORE.match(command)
        if stored is not None:
            self.stored.add(int(stored.group(1)))
        labelled = _LABEL.match(command)
        if labelled is not None:
            self.labels[int(labelled.group(1))] = labelled.group(2)
        return ExecutionResult(ok=True, detail="OK")


class _FakeConsole:
    """픽스처 86대 + 빈 그룹 풀. `test_groupgen_tools.FakeConsole` 의 형태다."""

    def __init__(self, fids: list[int], port: _RecordingExecutionPort) -> None:
        self._port = port
        children = [dict(i=slot, name="Spot " + str(slot)) for slot in range(1, len(fids) + 1)]
        fixtures = dict(
            ok=True, truncated=False, node=dict(childCount=len(fids)), children=children
        )
        groups = dict(ok=True, truncated=False, node=dict(childCount=0), children=[])
        self._states = dict([(FIXTURES_PATH, fixtures), (GROUPS_PATH, groups)])
        self._properties = dict()
        for slot, fid in enumerate(fids, start=1):
            key = (FIXTURES_PATH + "/" + str(slot), FID_PROPERTY_NAME)
            self._properties[key] = dict(ok=True, value=str(fid))
        self.state_calls: list[str] = []

    def _stored_slot(self, path: str) -> int | None:
        prefix = GROUPS_PATH + "/"
        if not path.startswith(prefix):
            return None
        tail = path[len(prefix) :]
        if not tail.isdigit():
            return None
        slot = int(tail)
        return slot if slot in self._port.stored else None

    def query_state(self, path: str) -> dict:
        self.state_calls.append(path)
        slot = self._stored_slot(path)
        if slot is not None:
            return dict(ok=True, truncated=False, node=dict(childCount=0), children=[])
        if path not in self._states:
            raise LookupError("unknown object path: " + path)
        return self._states[path]

    def query_property(self, path: str, property_name: str) -> dict:
        slot = self._stored_slot(path)
        if slot is not None and property_name == "Name":
            return dict(ok=True, value=self._port.labels.get(slot, ""))
        key = (path, property_name)
        if key not in self._properties:
            return dict(ok=False, error="property not readable: " + property_name)
        return self._properties[key]


class _ApprovePort:
    def __init__(self) -> None:
        self.requests: list[object] = []

    def request_approval(self, request) -> bool:
        self.requests.append(request)
        return True


def _dispatch(action: str):
    port = _RecordingExecutionPort()
    console = _FakeConsole(_patch_fids(), port)
    registry = build_toolset(
        execution_port=port,
        state_port=console,
        property_port=console,
        group_approval_port=_ApprovePort(),
    )
    execution = registry.dispatch(
        ToolCall(
            id="t66-apply",
            name=TOOL,
            arguments=dict(
                group_content_base64=_b64(GROUP_CSV),
                patch_content_base64=_b64(PATCH_CSV),
                action=action,
            ),
        )
    )
    return execution, port


class TestApplyPathActuallyRuns:
    """진짜 `_run_batch` 가 도는지. 이 클래스의 모든 단언이 그 위에 선다."""

    def test_apply_reaches_the_real_batch_runner_and_reports_applied(self):
        execution, _port = _dispatch("apply")
        assert execution.result.is_error is False, execution.result.content
        payload = json.loads(execution.result.content)
        assert "applied" in payload, (
            "apply 가 applied 를 안 실었다 — _run_batch 가 돌지 않았다는 뜻이다"
        )
        applied = payload["applied"]
        assert applied, "배치가 하나도 안 돌았다"
        assert [row["status"] for row in applied] == ["ok"] * len(applied)
        assert payload.get("stopped_after_batch") is None

    def test_the_batch_runner_actually_fired_commands(self):
        """비공허성 — applied 가 채워졌어도 콘솔에 한 줄도 안 갔으면 공허하다."""
        execution, port = _dispatch("apply")
        assert execution.result.is_error is False
        assert port.executed, "발화가 0줄이다"
        assert any(c.startswith("Store Group ") for c in port.executed)
        assert any(c.startswith("Label Group ") for c in port.executed)

    def test_every_selection_line_is_the_compact_form(self):
        """t66 의 처방이 이 경로 끝까지 도달하는지 — 반복 키워드형이 남으면 실패."""
        execution, port = _dispatch("apply")
        assert execution.result.is_error is False
        selections = [c for c in port.executed if c.startswith("Fixture ")]
        assert selections, "선택 줄이 하나도 없다"
        repeated = [line for line in selections if "+ Fixture" in line]
        assert repeated == [], "반복 키워드형이 남아 있다: " + str(repeated[:1])

    def test_preview_fires_nothing(self):
        """대조군 — preview 는 같은 경로를 타되 한 줄도 쏘지 않는다.

        이것이 없으면 위 발화 단언이 「apply 라서 쐈다」인지 「무조건 쏜다」인지
        구분되지 않는다.
        """
        execution, port = _dispatch("preview")
        assert execution.result.is_error is False
        payload = json.loads(execution.result.content)
        assert "applied" not in payload
        assert port.executed == []
