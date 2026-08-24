"""SPEC-COPILOT-LXSEQ-002 M3 — 툴 등재와 배선 (RED 먼저).

AC-LXSEQ2-013  툴 1종 · preview 쓰기 0 · apply 순차 중단 · 쓰기 수단 0
AC-LXSEQ2-014  시트 종류 레지스트리 group 행 + 동반 4지점
AC-LXSEQ2-015  붙여넣기 금지 문구 · source.sha256 · 미검증 고지 · 금지어

**뮤테이션 예고** (리드 지시 2026-08-24 — 맞히려고가 아니라 틀렸을 때
무엇이 틀렸는지 알려고 적는다):

  M3-① 4지점 중 하나를 뺀다            -> 파리티 검사가 죽는다고 본다
  M3-② preview 에서 발화한다            -> 쓰기 0 검사가 죽는다고 본다
  M3-③ 첫 배치 실패 후에도 둘째를 부른다 -> 순차 중단 검사가 죽는다고 본다
  M3-④ unverified 를 비운다              -> 고지 검사가 죽는다고 본다
  M3-⑤ 레지스트리 group 행을 뺀다        -> t51 검사가 죽는다고 본다
  M3-⑥ SHEET_KIND_ACTIONS 항목을 뺀다    -> t51 검사가 죽는다고 본다
  M3-⑦ 행 계수기를 뺀다                  -> t51 검사가 죽는다고 본다
  M3-⑧ 래퍼 스키마 passthrough 를 뺀다   -> t51 검사가 죽는다고 본다

②는 안 갈릴 가능성이 있다 — preview 경로가 실행 포트를 아예 안 들고
있으면 「발화한다」는 뮤테이션을 심을 자리가 없다(교체 불가).
"""

from __future__ import annotations

import base64
from pathlib import Path

GROUP_CSV = Path("server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.group.csv")
PATCH_CSV = Path("server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv")

TOOL = "import_lxseq_groups"
KIND = "group"


def _b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


class TestRegistryRow:
    """AC-LXSEQ2-014 — group 행과 동반 4지점."""

    def test_registry_carries_the_group_row(self):
        from server.sheets.registry import REGISTRY

        kinds = [row.kind for row in REGISTRY]
        assert KIND in kinds
        assert len(kinds) == len(set(kinds)), "종류 이름이 중복이다"

    def test_the_group_row_names_this_tool(self):
        from server.sheets.registry import REGISTRY

        row = next(r for r in REGISTRY if r.kind == KIND)
        assert row.handler.name == TOOL

    def test_group_header_discriminates_to_group(self):
        from server.sheets.registry import discriminate

        result = discriminate(GROUP_CSV.read_bytes())
        assert result.matched == (KIND,), f"판정: {result.outcome} {result.matched}"
        assert result.count == 1

    def test_patch_header_still_discriminates_to_patch(self):
        """신규 행이 기존 판정을 흔들지 않는다 — 비공허성의 반대편."""
        from server.sheets.registry import discriminate

        result = discriminate(PATCH_CSV.read_bytes())
        assert result.matched == ("patch",), f"판정: {result.outcome} {result.matched}"
        assert result.count == 1

    def test_the_companion_sites_are_filled_for_this_kind(self):
        """동반 4지점. 목록을 새로 짓지 않고 **정본을 임포트해** 대조한다.

        M2 에서 내가 목록을 새로 지어 저장소 가드보다 약해진 일이 있었다.
        여기서는 t51 이 세운 정본을 그대로 읽는다.
        """
        from server.orchestrator.tools import SHEET_KIND_ACTIONS
        from server.tests.test_sheet_kind_consumers import _wrapper_properties
        from server.web.session import _SHEET_ROW_COUNTERS

        actions = SHEET_KIND_ACTIONS.get(KIND)
        assert actions, "소비 지점 2 — SHEET_KIND_ACTIONS"
        assert callable(_SHEET_ROW_COUNTERS.get(KIND)), "소비 지점 3 — 행 계수기"

        from server.sheets.registry import REGISTRY

        row = next(r for r in REGISTRY if r.kind == KIND)
        properties = _wrapper_properties()
        missing = [arg for arg in row.passthrough_args if arg not in properties]
        assert missing == [], f"소비 지점 5 — 래퍼 스키마에 없는 passthrough: {missing}"

        declared = properties.get("action", {}).get("enum")
        assert declared, "래퍼 스키마의 action 에 enum 이 없다"
        assert [a for a in actions if a not in declared] == []

        # 비공허성 — 정본이 비면 위 대조가 전부 자동 참이 된다.
        assert len(REGISTRY) >= 3
        assert len(SHEET_KIND_ACTIONS) >= 2


class _RecordingPort:
    """콘솔 발화를 기록만 한다 — 실제 전송 0."""

    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, command: str):
        self.executed.append(command)
        raise AssertionError("이 테스트 경로는 콘솔에 발화하면 안 된다: " + command)

    def query_state(self, probe: str):
        return None


class TestToolRegistration:
    """AC-LXSEQ2-013 — 툴 1종과 4지점."""

    def test_tool_name_is_registered(self):
        from server.orchestrator.tools import TOOL_NAMES

        assert TOOL in TOOL_NAMES

    def test_tool_definition_is_offered_with_a_closed_schema(self):
        from server.orchestrator.tools import build_toolset

        port = _RecordingPort()
        registry = build_toolset(execution_port=port, state_port=port)
        definition = next(d for d in registry.definitions() if d.name == TOOL)
        assert definition.parameters.get("additionalProperties") is False
        properties = definition.parameters["properties"]
        assert "group_content_base64" in properties
        assert "patch_content_base64" in properties
        assert properties["action"]["enum"] == ["preview", "apply"]

    def test_the_tool_count_constant_moved_with_the_tool(self):
        """파리티 — 툴을 넣었으면 상수도 같이 자라야 한다."""
        from server.orchestrator.tools import TOOL_NAMES

        expected = len(TOOL_NAMES)
        source = Path("server/tests/test_tools.py").read_text(encoding="utf-8")
        assert f"== {expected}" in source, (
            f"test_tools.py 의 툴 수 상수가 {expected} 를 말하지 않는다"
        )


class TestToolContract:
    """AC-LXSEQ2-015 — 문면과 페이로드의 보루."""

    def _definition(self):
        from server.orchestrator.tools import build_toolset

        port = _RecordingPort()
        registry = build_toolset(execution_port=port, state_port=port)
        return next(d for d in registry.definitions() if d.name == TOOL)

    def test_description_forbids_pasting(self):
        text = self._definition().description
        assert "붙여넣" in text, "채팅 붙여넣기 금지가 설명문에 없다"
        assert "파일" in text

    def test_description_says_membership_is_unmeasured_not_impossible(self):
        text = self._definition().description
        assert "미측정" in text
        for banned in ("원리적 불가", "원리적으로 불가", "읽을 수 없다"):
            assert banned not in text, f"하향된 단정형이 설명문에 있다: {banned}"

    def test_the_payload_guidance_also_says_unmeasured(self):
        """설명문과 **페이로드 안내**는 다른 자리다.

        M3-④ 뮤테이션이 처음에 안 갈렸다 — 이 검사가 설명문만 봤기 때문이다.
        안내 상수는 매 페이로드에 실려 모델이 매번 읽는 자리라 여기도 막는다.
        """
        from server.orchestrator.tools import LXSEQ_GROUPS_GUIDANCE

        assert "미측정" in LXSEQ_GROUPS_GUIDANCE
        for banned in ("원리적 불가", "원리적으로 불가", "읽을 수 없다"):
            assert banned not in LXSEQ_GROUPS_GUIDANCE
        assert "붙여넣" in LXSEQ_GROUPS_GUIDANCE
        assert "human_check_commands" in LXSEQ_GROUPS_GUIDANCE

    def test_no_downgraded_wording_anywhere_in_the_new_modules(self):
        """금지어 grep — 범위는 run 산출물이고 SPEC 문서 넷은 제외한다.

        SPEC 문서는 금지어를 **금지하려고** 인용하므로 범위에 넣으면 이
        검사가 구조적으로 0을 못 낸다.
        """
        targets = [
            Path("server/lxseq/group_parser.py"),
            Path("server/lxseq/group_mapper.py"),
        ]
        banned = ("원리적 불가", "원리적으로 불가", "읽을 수 없다")
        offenders = []
        for target in targets:
            text = target.read_text(encoding="utf-8")
            offenders += [f"{target}: {b}" for b in banned if b in text]
        assert offenders == []
        # 날조 대조군 — 스캐너가 실제로 찾는지 먼저 증명한다.
        planted = "이 줄은 원리적 불가 라고 적는다"
        assert [b for b in banned if b in planted] == ["원리적 불가"]


class TestBatchDispatchPolicy:
    """AC-LXSEQ2-013 ④ — 순차 위임과 **첫 실패에서 중단**.

    툴 전체를 태우지 않고 그 결정만 잰다. 결정이 정책이고 나머지는 배선이다.

    **뮤테이션 예고**: 중단 조건을 없애면 이 검사가 죽는다고 본다.
    (M3-③ 이 처음에 안 갈렸던 이유가 이 검사가 없었기 때문이다 — 「결함이
    아니라 검사 부족」이었고, 예고를 적어 뒀기에 그것을 바로 갈랐다.)
    """

    def test_all_batches_run_when_each_succeeds(self):
        from server.orchestrator.tools import apply_group_batches

        seen: list[int] = []

        def run(index: int):
            seen.append(index)
            return "ok", {"index": index}

        applied, stopped = apply_group_batches([0, 1], run)
        assert seen == [0, 1]
        assert stopped is None
        assert [a["status"] for a in applied] == ["ok", "ok"]

    def test_the_second_batch_never_runs_after_the_first_fails(self):
        from server.orchestrator.tools import apply_group_batches

        seen: list[int] = []

        def run(index: int):
            seen.append(index)
            return ("error" if index == 0 else "ok"), {"index": index}

        applied, stopped = apply_group_batches([0, 1], run)
        assert seen == [0], "둘째 배치가 실행됐다 — 첫 실패에서 멈춰야 한다"
        assert stopped == 0
        assert len(applied) == 1

    def test_the_failure_is_recorded_not_swallowed(self):
        from server.orchestrator.tools import apply_group_batches

        applied, stopped = apply_group_batches([0], lambda i: ("error", {"why": "거절"}))
        assert applied[0]["status"] == "error"
        assert applied[0]["result"] == {"why": "거절"}
        assert stopped == 0

    def test_no_automatic_retry(self):
        """재시도가 있으면 같은 index 가 두 번 나온다.

        멤버십은 되읽히지 않으므로 중복 발화가 만든 결과는 사후에 못 가른다.
        """
        from server.orchestrator.tools import apply_group_batches

        seen: list[int] = []

        def run(index: int):
            seen.append(index)
            return "error", {}

        apply_group_batches([0, 1], run)
        assert seen == [0]
        assert len(seen) == len(set(seen))
