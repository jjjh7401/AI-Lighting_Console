"""M5 — 익스큐터 레이아웃 GO/DESCOPE 분기 고정.

SPEC-COPILOT-BUSKWIZ-001 AC-BUSKWIZ-012 / AC-BUSKWIZ-013.

**M0 판정은 ② DESCOPE다.** `REQ-BUSKWIZ-016`의 게이트는 `16 ∧ 17 ∧ 19`이고
측정 2 하나만으로 이미 거짓이다 — 미점유 익스큐터 인덱스가 어느 주소형으로도
해석되지 않아 "비어 있는 익스큐터"를 식별하는 질의 경로가 존재하지 않는다
(`progress.md` §E.2 M0 측정 2). 따라서 v1은 익스큐터·페이지 대상 커맨드를
**0건** 발화하고, 이 파일이 그것을 기계로 고정한다.

**GO 분기 테스트는 삭제하지 않고 `skip` 사유를 명시한 채 남긴다** — 후속 SPEC이
게이트를 다시 열 때 출발점이 되기 때문이다(`AC-BUSKWIZ-012` 비고). M0가 남긴
정정도 함께 인수한다: 익스큐터 축은 "문법이 없다"가 아니라 **"문법은 파싱되나
효과와 대상 식별이 미검증"**에서 출발해야 한다(`progress.md` G2).

주소 금지 규율(`AC-BUSKWIZ-013`)은 **분기와 무관하게** 적용되므로 DESCOPE인
지금도 전부 실행한다.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

from server.llm.types import ToolCall
from server.looks.busking import build_genre_bundle, genres_in, looks_for_genre
from server.looks.instantiate import resolve_pools
from server.looks.loader import load_library_from_dir
from server.looks.resolver import resolve_roles
from server.orchestrator.tools import build_toolset
from server.tests.busking_fixtures import FULL_RIG
from server.tests.test_looks_instantiate import _groups, _pools
from server.tests.test_looks_tool import _RecordingPort, _RigStatePort, _tree

_PROGRESS = Path(".moai/specs/SPEC-COPILOT-BUSKWIZ-001/progress.md")
_SPEC_MODULES = (
    Path("server/looks/busking.py"),
    Path("server/looks/report.py"),
)

# 익스큐터 축의 어휘. 오브젝트 타입으로 등장하는지만 본다.
_EXECUTOR_WORDS = re.compile(r"\b(Executor|Page)\b")
# `Page 1.201` 같은 dotted 주소형. 소스가 아니라 **생성된 커맨드**에 건다.
_DOTTED = re.compile(r"\b(?:Page|Executor)\s+\d+\.\d+")


def _every_generated_command() -> list[str]:
    """4장르 전량이 실제로 생성한 커맨드. 소스 grep이 아니라 산출물 전수다.

    소스 정규식은 금지 대상이 구현될 수 있는 형태를 놓친다: dotted form이 실제로
    발화되는 유일한 경로는 `f"Page {page}.{executor}"` 같은 변수 조립이고, 그
    소스 문자열에는 숫자가 없어 `\\d+\\.\\d+`가 결코 매치하지 않는다
    (`AC-BUSKWIZ-013` v0.1.3 — 감사 D3).
    """
    library = load_library_from_dir()
    resolution = resolve_roles(_groups(*FULL_RIG))
    commands: list[str] = []
    for genre in genres_in(library):
        bundle = build_genre_bundle(
            genre,
            looks_for_genre(library, genre),
            resolution=resolution,
            pools=resolve_pools(_pools()),
        )
        commands.extend(bundle.commands)
    return commands


def _constants_in_arithmetic(tree: ast.AST) -> set[float]:
    """산술식(`BinOp`)에 직접 등장하는 숫자 상수."""
    found: set[float] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.BinOp):
            continue
        for side in (node.left, node.right):
            if isinstance(side, ast.Constant) and isinstance(side.value, int | float):
                found.add(side.value)
    return found


# -- AC-BUSKWIZ-012 ② — DESCOPE 분기 --------------------------------------------


class TestDescopeBranch:
    def test_no_generated_command_targets_an_executor_or_page(self):
        commands = _every_generated_command()
        assert len(commands) > 50, "비공허성: 스캔 대상이 실제로 존재한다"
        offenders = [c for c in commands if _EXECUTOR_WORDS.search(c)]
        assert offenders == [], f"익스큐터 축은 v1에서 닫혀 있다: {offenders[:3]}"

    def test_the_scan_would_catch_an_executor_command(self):
        # 비공허성 — 스캐너 자체가 동작함을 증명한다. 이것이 없으면 위 테스트는
        # "정규식이 아무것도 안 잡는다"와 구별되지 않는다.
        planted = ["Store Preset 4.1", "Assign Sequence 17 At Executor 191"]
        assert [c for c in planted if _EXECUTOR_WORDS.search(c)] == [planted[1]]

    def test_the_tool_path_emits_none_either(self):
        # 빌더뿐 아니라 모델이 닿는 경로에서도 0건임을 확인한다.
        port = _RecordingPort()
        registry = build_toolset(
            execution_port=port,
            state_port=_RigStatePort(_tree(groups=FULL_RIG)),
        )
        execution = registry.dispatch(
            ToolCall(id="t1", name="prepare_busking", arguments={"genre": "록"})
        )
        payload = json.loads(execution.result.content)
        assert payload["executed"] is True
        assert port.executed, "비공허성: 실제로 커맨드가 나갔다"
        assert [c for c in port.executed if _EXECUTOR_WORDS.search(c)] == []

    def test_the_descope_reason_is_recorded_in_progress(self):
        """`AC-BUSKWIZ-012` ②는 사유가 M0 절에 기록되어 있을 것을 요구한다."""
        text = _PROGRESS.read_text(encoding="utf-8")
        assert "ASSUMPTION-17" in text
        assert "DESCOPE" in text
        # 게이트가 3항 논리곱이고 어느 항이 닫았는지가 적혀 있어야 한다.
        assert "16 ∧ 17 ∧ 19" in text
        assert "M5는 ② DESCOPE 분기로 확정" in text


# -- AC-BUSKWIZ-013 — 익스큐터 주소 금지 규율 (분기 무관) -------------------------


class TestExecutorAddressingDiscipline:
    def test_no_dotted_address_form_is_ever_generated(self):
        commands = _every_generated_command()
        assert commands, "비공허성: 스캔 대상이 비어 있지 않다"
        offenders = [c for c in commands if _DOTTED.search(c)]
        assert offenders == [], f"dotted 주소형은 발화하지 않는다: {offenders[:3]}"

    def test_the_dotted_scan_would_catch_the_forbidden_form(self):
        # LOOKLIB M7 라이브에서 모델이 창발적으로 발화해 executed 로그에 남은
        # 실제 형태다 — 금지의 성격은 "콘솔이 거부한다"가 아니라 "검증되지 않은
        # 주소형을 우리가 만들지 않는다"이다.
        planted = "Assign Sequence 17 At Page 1.102"
        assert _DOTTED.search(planted)

    @pytest.mark.parametrize("module", _SPEC_MODULES, ids=lambda p: p.name)
    def test_no_page_times_hundred_arithmetic(self, module: Path):
        """`page_no*100 + slot`을 일반 규칙으로 하드코딩하지 않는다.

        이 관례는 **페이지 1에서만** 라이브 관측되었고(`server/web/dash.py:145-157`),
        `REQ-EXECBODY-007`/`-008`이 2개 이상 페이지의 라이브 검증 전 하드코딩을
        금지하며 그 조건은 아직 충족되지 않았다.
        """
        tree = ast.parse(module.read_text(encoding="utf-8"))
        assert list(ast.walk(tree)), "비공허성: 파싱된 트리가 비어 있지 않다"
        assert 100 not in _constants_in_arithmetic(tree)

    def test_the_arithmetic_scan_would_catch_the_forbidden_expression(self):
        # 비공허성 — 스캐너가 실제로 그 형태를 잡는지 심어서 확인한다.
        planted = ast.parse("executor = page_no * 100 + slot")
        assert 100 in _constants_in_arithmetic(planted)

    def test_the_handler_holds_no_executor_arithmetic_either(self):
        tools = ast.parse(Path("server/orchestrator/tools.py").read_text(encoding="utf-8"))
        handler = next(
            node
            for node in ast.walk(tools)
            if isinstance(node, ast.FunctionDef) and node.name == "prepare_busking"
        )
        assert 100 not in _constants_in_arithmetic(handler)


# -- AC-BUSKWIZ-012 ① — GO 분기 (미실행, 삭제 금지) ------------------------------


_GO_SKIP = (
    "M0 판정이 DESCOPE다 — REQ-BUSKWIZ-016의 게이트 `16 ∧ 17 ∧ 19`가 측정 2에서 "
    "닫혔다: 미점유 익스큐터 인덱스가 어느 주소형으로도 해석되지 않아 '비어 있는 "
    "익스큐터'를 식별하는 질의 경로가 없다(progress.md §E.2 M0 측정 2). 이 분기를 "
    "삭제하지 않고 남기는 이유는 후속 SPEC이 게이트를 다시 열 때의 출발점이기 "
    "때문이다(AC-BUSKWIZ-012 비고). 출발점은 '문법이 없다'가 아니라 '문법은 "
    "파싱되나 효과와 대상 식별이 미검증'이다(progress.md G2)."
)


@pytest.mark.skip(reason=_GO_SKIP)
class TestGoBranch:
    def test_the_layout_uses_only_the_measured_command_form(self):
        # 발화 형식은 M0의 ASSUMPTION-19가 **실측한 것 하나뿐**이어야 한다.
        # `Assign Sequence <n> At Executor <m>`은 목적어가 시퀀스라 그대로 쓸 수
        # 없다 — 본 SPEC의 산출물은 프리셋이고, 시퀀스 생성은 §D 범위 밖이다.
        raise AssertionError("GO 분기 미구현 — M0가 DESCOPE로 판정했다")

    def test_executor_numbers_come_from_the_empty_executor_path(self):
        # 번호 출처는 `resolved_executor_nos`가 **아니다**: 그 함수는
        # `meta["resolved"] is True` 항목만 반환하므로 정의상 **점유된** 익스큐터
        # 목록이고, 그것을 출처로 쓰면 운영자가 쓰던 플레이백을 덮는다
        # (`server/web/dash.py:309-327`, design.md 위험 #4).
        raise AssertionError("GO 분기 미구현 — 빈 익스큐터 식별 경로가 미확정이다")

    def test_the_binding_target_already_exists(self):
        # 바인딩 대상은 이미 존재하는 오브젝트여야 한다 — 그렇지 않으면 시퀀스
        # 생성이 암묵적으로 범위에 들어온다(spec.md §D).
        raise AssertionError("GO 분기 미구현 — 대상 식별 경로가 없다")
