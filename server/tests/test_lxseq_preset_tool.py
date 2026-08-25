"""SPEC-COPILOT-LXSEQ-003 M3 — 툴 등재와 배선.

AC-LXSEQ3-010  툴이 등재되고 인자 집합이 닫혀 있다 (레지스트리에서 **읽어** 단언)
AC-LXSEQ3-011  세 헤더가 각각 하나로 갈린다 (+ 포함검사 대조군 `count == 2`)
AC-LXSEQ3-012  `server/lxseq/` 에 콘솔 쓰기 수단이 없다 (+ 양성 대조군)

순수 검증이다. 콘솔·네트워크 접촉 0.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from server.sheets.registry import (
    REGISTRY,
    ExactColumns,
    RequiredForbidden,
    SheetKindRow,
    discriminate,
)

RIG = Path("src/Lighting_Designer/02_RIG팩")
STEM = "LXSEQ_RIG_01_ShowBase_r3.preset-"
TOOL = "import_lxseq_presets"
PRESET_KINDS = ("preset-dim", "preset-col", "preset-bm")


def _bytes(kind: str) -> bytes:
    return (RIG / (STEM + kind + ".csv")).read_bytes()


class TestToolRegistration:
    def test_the_tool_name_is_registered(self):
        from server.orchestrator.tools import TOOL_NAMES

        assert TOOL in TOOL_NAMES

    def test_the_definition_is_read_from_the_registry_not_grepped(self):
        """AC-010 — **레지스트리에서 정의를 읽어** 단언한다.

        문면의 `grep -c '"import_lxseq_presets"' … >= 2` 는 주석·독스트링에도
        걸린다. 이름이 등장하는 것과 툴이 **실제로 제공되는** 것은 다르다.
        """
        from server.orchestrator.tools import build_toolset

        class _Port:
            def execute(self, command):
                raise AssertionError("이 경로는 발화하면 안 된다: " + command)

            def query_state(self, path):
                return None

        registry = build_toolset(execution_port=_Port(), state_port=_Port())
        definition = next(d for d in registry.definitions() if d.name == TOOL)
        assert definition.parameters.get("additionalProperties") is False
        properties = definition.parameters["properties"]
        assert "file_content_base64" in properties
        assert properties["action"]["enum"] == ["preview", "apply"]

    def test_the_argument_set_carries_no_path(self):
        """바이트는 파일에서만 온다 — 서버는 경로를 받지 않는다(001 규약)."""
        from server.orchestrator.tools import build_toolset

        class _Port:
            def execute(self, command):
                raise AssertionError("발화 금지")

            def query_state(self, path):
                return None

        registry = build_toolset(execution_port=_Port(), state_port=_Port())
        definition = next(d for d in registry.definitions() if d.name == TOOL)
        names = set(definition.parameters["properties"])
        assert not any("path" in n or n == "file_path" for n in names), names

    def test_the_sheet_kind_actions_are_wired(self):
        from server.orchestrator.tools import SHEET_KIND_ACTIONS

        for kind in PRESET_KINDS:
            assert SHEET_KIND_ACTIONS.get(kind) == ("preview", "apply"), kind


class TestThreeHeadersSplitOneEach:
    @pytest.mark.parametrize("kind", ["dim", "col", "bm"])
    def test_each_header_matches_exactly_one_signature(self, kind):
        result = discriminate(_bytes(kind))
        assert result.count == 1, (kind, result.outcome, result.matched)
        assert result.matched == ("preset-" + kind,)
        assert result.outcome != "ambiguous_sheet_kind"

    def test_pos_matches_none(self):
        """대조군 — 넷째 헤더는 어느 서명에도 안 맞는다. 행을 안 만들었기 때문이다."""
        result = discriminate(_bytes("pos"))
        assert result.count == 0
        assert result.matched == ()

    def test_no_config_errors_now_that_the_handler_exists(self):
        """행은 **핸들러가 실재해야** 문다(t51). 툴 등재 전에는 이 셋이
        `no_target_tool` 이었다 — 그 사실이 이 검사의 반대편이다."""
        assert discriminate(_bytes("dim")).config_errors == ()

    def test_an_inclusion_predicate_would_make_bm_ambiguous(self):
        """AC-011 비공허성(필수) — `AC-FILEARG-018` 이 명시한 대조군을 승계한다.

        `preset-col` 을 **포함 검사** 세 열(ID·Name·Value)로 바꾸면 `preset-bm`
        헤더가 두 서명에 맞아 **`count == 2`** 가 되어야 한다. 이 대조군이
        통과해 버리면 시험이 술어의 힘을 재고 있지 않다는 뜻이다.
        """
        weakened = tuple(
            SheetKindRow(
                kind=row.kind,
                predicate=RequiredForbidden(required_columns=("ID", "Name", "Value")),
                handler=row.handler,
                passthrough_args=row.passthrough_args,
            )
            if row.kind == "preset-col"
            else row
            for row in REGISTRY
        )
        result = discriminate(_bytes("bm"), registry=weakened)
        assert result.count == 2, (result.outcome, result.matched)

    def test_the_shipped_predicates_are_exact_column_sets(self):
        """대조군의 짝 — 실제로 배송되는 술어가 **정확 열 집합**인지."""
        for row in REGISTRY:
            if row.kind in PRESET_KINDS:
                assert isinstance(row.predicate, ExactColumns), row.kind


class TestNoConsoleWriteMeansInLxseq:
    """AC-012 — `server/lxseq/` 에 콘솔 쓰기 수단이 없다."""

    PATTERN = "execution_port\\|OscBridge\\|socket"

    def test_the_package_has_none(self):
        result = subprocess.run(
            [
                "grep",
                "-rn",
                "--include=*.py",
                "-E",
                "execution_port|OscBridge|socket",
                "server/lxseq/",
            ],
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() == "", result.stdout

    def test_the_same_grep_finds_them_in_the_tool_layer(self):
        """양성 대조군 — grep 이 도는지 먼저 확인한다. 이게 없으면 위 빈 출력이
        「없다」인지 「grep 이 안 돌았다」인지 구분되지 않는다."""
        result = subprocess.run(
            [
                "grep",
                "-rn",
                "--include=*.py",
                "-E",
                "execution_port|OscBridge|socket",
                "server/orchestrator/tools.py",
            ],
            capture_output=True,
            text=True,
        )
        assert result.stdout.strip() != ""

    def test_the_preset_modules_do_not_import_the_builder(self):
        """번역이 툴 층에 있다는 것의 반대편 — `server/lxseq/` 는 빌더도 안 부른다."""
        for name in ("preset_parser.py", "preset_mapper.py"):
            source = Path("server/lxseq/" + name).read_text(encoding="utf-8")
            assert "preset_store_commands" not in source, name


class TestTheToolActuallyRuns:
    """등재만으로는 도는지 모른다 — 디스패치해서 산출물을 본다."""

    @staticmethod
    def _dispatch(kind: str, action: str = "preview"):
        import base64
        import json

        from server.llm.types import ToolCall
        from server.orchestrator.tools import build_toolset

        class _Console:
            def __init__(self):
                self.executed = []

            def execute(self, command):
                self.executed.append(command)
                raise AssertionError("preview 는 발화하면 안 된다: " + command)

            def query_state(self, path):
                return dict(children=[], node=dict(childCount=0), truncated=False)

        console = _Console()
        registry = build_toolset(execution_port=console, state_port=console)
        execution = registry.dispatch(
            ToolCall(
                id="lx3",
                name=TOOL,
                arguments=dict(
                    file_content_base64=base64.b64encode(_bytes(kind)).decode("ascii"),
                    action=action,
                ),
            )
        )
        return json.loads(execution.result.content), console

    def test_preview_reads_every_row_and_fires_nothing(self):
        payload, console = self._dispatch("dim")
        assert console.executed == [], "preview 가 콘솔에 닿았다"
        assert payload["read"] == 6
        assert payload["sheet_kind"] == "preset-dim"

    def test_the_payload_carries_held_rows_with_their_classes(self):
        """「N건 성공」이 아니라 「읽은 수 · 계획 · 보류(클래스별)」로 나와야 한다."""
        payload, _ = self._dispatch("bm")
        assert payload["read"] == 5
        assert payload["planned"] == []
        assert len(payload["held"]) == 5
        assert all(h["classes"] for h in payload["held"])
        assert payload["held_by_class"]

    def test_the_payload_states_the_confirmation_limit(self):
        payload, _ = self._dispatch("dim")
        assert "value_match" in payload["unverified"]
        assert "값이 맞는지는" in payload["unverified_reason"]

    def test_the_guidance_forbids_calling_it_verified(self):
        payload, _ = self._dispatch("dim")
        assert "검증된" in payload["guidance"]
        assert "짧으니 안전" in payload["guidance"]


class TestOneVocabulary:
    """종류 이름이 **한 어휘**인지 — 파서와 레지스트리가 갈리면 조용히 틀린다.

    처음에 파서는 `dim`·`col`·`bm` 을 쓰고 레지스트리는 `preset-dim` 을 썼다.
    종단 검사가 `sheet_kind` 를 대조하다 그 차이를 잡았다 — 안 잡혔으면 산출물의
    종류 이름이 레지스트리가 말하는 종류와 다른 채로 나갔을 것이다.
    """

    def test_the_parser_and_the_registry_name_the_same_kinds(self):
        from server.lxseq.preset_parser import PRESET_SHEET_COLUMNS

        registry_kinds = set(row.kind for row in REGISTRY if row.kind in PRESET_KINDS)
        assert set(PRESET_SHEET_COLUMNS) == registry_kinds

    def test_the_column_sets_agree_too(self):
        """이름만 같고 열이 갈리면 판별과 파싱이 다른 것을 본다."""
        from server.lxseq.preset_parser import PRESET_SHEET_COLUMNS

        for row in REGISTRY:
            if row.kind not in PRESET_KINDS:
                continue
            assert isinstance(row.predicate, ExactColumns)
            assert set(row.predicate.columns) == set(PRESET_SHEET_COLUMNS[row.kind]), row.kind

    def test_the_pool_family_table_covers_every_kind(self):
        """풀 계열 표에 빠진 종류가 있으면 그 시트는 툴에서 KeyError 로 죽는다."""
        from server.orchestrator.tools import _PRESET_POOL_FAMILY

        assert set(_PRESET_POOL_FAMILY) == set(PRESET_KINDS)
