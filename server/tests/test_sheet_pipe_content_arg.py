"""카드 t112 — 전달 래퍼가 대상 인자명을 무시해 거절 문면이 거짓말을 한다.

`import_uploaded_sheet` 는 세션 슬롯의 바이트를 형제 툴의 인자에 실어 나른다.
대상 **툴 이름**은 레지스트리 행에서 읽는데(`test_sheet_pipe.py` 2번 축),
바이트를 담는 **인자 이름**은 하드코딩이었다 — 항상 `file_content_base64`.

`import_lxseq_groups` 는 그 이름을 안 읽는다. `group_content_base64` 를 읽고
없으면 「'group_content_base64'가 없다 — GROUP 시트 **파일**에서 읽은 바이트를
base64로 넘겨라」로 거절한다. 사용자는 파일을 줬는데도.

그 문면은 **거짓**이다. 그리고 그 거짓이 진짜 거절을 가린다: 바이트가 제 이름으로
도착하면 그 다음 관문인 「FID 매핑원이 없다」(`patch_content_base64`)에서 거절되고,
그것이 `server/sheets/registry.py` 의 GROUP_ROW 주석이 이미 적어 둔 참인 사유다.

이 카드의 범위는 **정직한 거절**이다. 업로드 능력은 열지 않는다 — 고쳐도 그룹
시트만으로는 여전히 못 만든다. 두 시트를 어떻게 실어 나를지는 카드 t53 이 정한다.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from server.llm.types import ToolCall
from server.orchestrator.tools import ExecutionContext, build_toolset
from server.sheets.registry import HANDLER_TAG_TOOL

GROUP_CSV = Path("server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.group.csv")
PATCH_CSV = Path("server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv")

WRAPPER = "import_uploaded_sheet"
GROUP_TOOL = "import_lxseq_groups"


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


class _NeverCalledExecutionPort:
    def execute(self, command: str):
        raise AssertionError("시트 경로는 콘솔에 발화하지 않는다: " + command)


class _NeverCalledStatePort:
    def query_state(self, probe: str):
        raise AssertionError("시트 경로는 콘솔 상태를 읽지 않는다: " + probe)


class _FakeUploadedSheet:
    def __init__(self, *, file_name=None, kind=None, content_base64=None):
        self.file_name = file_name
        self.kind = kind
        self.content_base64 = content_base64


def _registry(uploaded_sheet=None):
    return build_toolset(
        execution_port=_NeverCalledExecutionPort(),
        state_port=_NeverCalledStatePort(),
        uploaded_sheet=uploaded_sheet,
    )


def _group_registry():
    return _registry(
        _FakeUploadedSheet(
            file_name="rig.group.csv",
            kind="group",
            content_base64=_b64(GROUP_CSV.read_bytes()),
        )
    )


def _wrapper_call(**arguments) -> ToolCall:
    return ToolCall(id="t112", name=WRAPPER, arguments=dict(arguments))


def _payload(execution) -> dict:
    return json.loads(execution.result.content)


def _spy_on(registry, tool_name, seen):
    original = registry._handlers[tool_name]

    def _spy(call, context):
        seen.append(call)
        return original(call, context)

    registry._handlers[tool_name] = _spy


# -- 1. 정직한 거절 --------------------------------------------------------------


class TestHonestRefusal:
    """첨부 경로로 그룹 시트를 준 사용자가 받는 문면이 참이어야 한다."""

    def _refusal(self) -> dict:
        execution = _group_registry().dispatch(_wrapper_call(), ExecutionContext())
        assert execution.result.is_error, "이 경로는 아직 거절이 맞다 — 능력은 안 열린다"
        return _payload(execution)

    def test_refusal_does_not_claim_the_file_is_missing(self):
        """사용자가 파일을 줬다. 「그룹 바이트가 없다」는 거짓이다."""
        error = self._refusal()["error"]
        assert "'group_content_base64'가 없다" not in error, (
            "파일을 줬는데 없다고 한다 — 래퍼가 바이트를 대상이 안 읽는 이름으로 실었다"
        )

    def test_refusal_names_the_true_cause(self):
        """참인 사유: 그룹 시트만으로는 FID 매핑원이 없다."""
        error = self._refusal()["error"]
        assert "'patch_content_base64'가 없다" in error
        assert "FID" in error

    def test_refusal_still_refuses(self):
        """능력 인도가 아니다 — 고쳐도 이 경로로는 그룹이 만들어지지 않는다."""
        assert self._refusal()["error"], "거절 문면이 비었다"

    def test_group_bytes_reach_the_target_under_the_name_it_reads(self):
        """대상 툴이 실제로 자기가 읽는 이름으로 바이트를 받는다."""
        seen: list[ToolCall] = []
        registry = _group_registry()
        _spy_on(registry, GROUP_TOOL, seen)
        registry.dispatch(_wrapper_call(), ExecutionContext())

        assert len(seen) == 1, "형제 툴이 내부 ToolCall로 정확히 한 번 불려야 한다"
        forwarded = seen[0].arguments
        assert forwarded.get("group_content_base64") == _b64(GROUP_CSV.read_bytes())

    def test_patch_sheet_path_is_unchanged(self):
        """반대편 — 기존 patch 경로는 그대로 file_content_base64 로 도착한다."""
        seen: list[ToolCall] = []
        registry = _registry(
            _FakeUploadedSheet(
                file_name="rig.patch.csv",
                kind="patch",
                content_base64=_b64(PATCH_CSV.read_bytes()),
            )
        )
        _spy_on(registry, "import_lxseq_patch", seen)
        registry.dispatch(_wrapper_call(action="preview"), ExecutionContext())

        assert len(seen) == 1
        assert seen[0].arguments.get("file_content_base64") == _b64(PATCH_CSV.read_bytes())


# -- 2. 인자 이름은 레지스트리 행이 지목한다 (하드코딩 금지) -----------------------


class TestContentArgFromRow:
    def test_content_arg_is_read_from_the_registry_row(self, monkeypatch):
        """행의 content_arg 를 갈아 끼우면 래퍼가 그 이름으로 싣는다.

        하드코딩돼 있으면 이 검사가 빨개진다 — 대상 **이름**에 대한
        `test_sheet_pipe.py` 2번 축을, 대상 **인자명**에 대해 세운다.
        """
        import server.orchestrator.tools as tools_module
        from server.sheets.registry import SheetKindRow

        original = next(r for r in tools_module.SHEET_REGISTRY if r.kind == "group")
        rerouted = SheetKindRow(
            kind="group",
            predicate=original.predicate,
            handler=original.handler,
            passthrough_args=original.passthrough_args,
            content_arg="renamed_content_base64",
        )
        monkeypatch.setattr(tools_module, "SHEET_REGISTRY", (rerouted,))

        seen: list[ToolCall] = []
        registry = _group_registry()
        _spy_on(registry, GROUP_TOOL, seen)
        registry.dispatch(_wrapper_call(), ExecutionContext())

        assert len(seen) == 1
        assert "renamed_content_base64" in seen[0].arguments
        assert "file_content_base64" not in seen[0].arguments

    def test_default_content_arg_is_the_historical_name(self):
        """행이 말하지 않으면 예전 그대로다 — 다른 종류는 안 흔들린다."""
        from server.sheets.registry import SheetKindRow

        row = SheetKindRow(kind="x", predicate=None, handler=None)
        assert row.content_arg == "file_content_base64"


# -- 3. 계열 전수 — 행이 지목한 인자명이 대상 스키마의 required 에 있어야 한다 ------


class TestRowContentArgMatchesTargetSchema:
    """점-수정이 아니라 계열을 막는다: 어느 행이든 이 비대칭이면 빨개진다."""

    def _definitions(self) -> dict:
        return dict((d.name, d.parameters) for d in _registry().definitions())

    def test_every_tool_row_forwards_a_name_its_target_requires(self):
        import server.orchestrator.tools as tools_module

        schemas = self._definitions()
        checked = 0
        for row in tools_module.SHEET_REGISTRY:
            if getattr(row.handler, "kind_tag", None) != HANDLER_TAG_TOOL:
                continue
            target = row.handler.name
            assert target in schemas, row.kind + ": 대상이 정의 목록에 없다 — " + target
            required = tuple(schemas[target].get("required", ()))
            assert row.content_arg in required, (
                row.kind
                + " 행은 '"
                + row.content_arg
                + "' 로 싣는데 "
                + target
                + " 의 required 는 "
                + repr(required)
                + " 다 — 바이트가 대상이 안 읽는 이름으로 도착한다"
            )
            checked += 1

        assert checked >= 5, "tool 종 행을 전수로 안 봤다 — 본 개수: " + str(checked)

    def test_the_group_row_is_actually_one_of_the_checked_rows(self):
        """비공허성 — 위 전수 검사가 실제로 group 행을 지난다."""
        import server.orchestrator.tools as tools_module

        row = next(r for r in tools_module.SHEET_REGISTRY if r.kind == "group")
        assert row.handler.kind_tag == HANDLER_TAG_TOOL
        assert row.content_arg == "group_content_base64"


@pytest.mark.parametrize("kind", ["patch", "preset-dim", "preset-col", "preset-bm"])
def test_other_kinds_keep_the_historical_content_arg(kind):
    """대조군 — group 만 다르다. 전부 바꿔 놓고 초록을 받는 일을 막는다."""
    import server.orchestrator.tools as tools_module

    row = next(r for r in tools_module.SHEET_REGISTRY if r.kind == kind)
    assert row.content_arg == "file_content_base64"
