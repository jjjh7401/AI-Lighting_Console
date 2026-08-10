"""M7 — 1단계 공개 계약 무변경 (AC-AUTOPATCH-025).

**무엇을 고정하고 무엇을 고정하지 않는가.** 고정하는 것은 `precheck_vectorworks_diff`
payload의 **최상위 키 집합과 키별 타입 시그니처**다. 값은 고정하지 않는다 — 값 고정은
무관한 변경에도 깨져 곧 무의미해지고, 그러면 스냅샷은 지워지거나 기계적으로 갱신된다
(AC-AUTOPATCH-025①).

키 **내부**의 의미는 여기서 다시 확인하지 않는다 — 1단계 자신의 구조 assert
(`test_vwx_report.py`·`test_vwx_multisystem_real_samples.py` 계열)에 위임한다(AC-025③).
이 파일은 "2단계가 1단계 출력의 **형상**을 바꾸지 않았다"만 본다.

**2단계가 실제로 건드린 것 하나**: `designed_rig.fixtures[*]`에
`gdtf_fixture`·`mode`·`footprint` 열이 **추가**됐다(M7). 패치 계층은 이 payload만 입력으로
받으므로 도면 점유폭이 없으면 주소 계획이 전부 `footprint_unknown`으로 제외되기 때문이다.
그것은 **중첩 키 추가**이고 최상위 계약은 불변이다 — 아래 스냅샷이 그 사실을 강제한다.
"""

from __future__ import annotations

import ast
import base64
import importlib
import json
import re
import sys
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

import pytest

from server.llm.types import ToolCall
from server.orchestrator.tools import build_toolset
from server.prechk.inventory import FIXTURE_ROOT

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = PROJECT_ROOT / "server" / "tests" / "fixtures" / "vwx"
EXPORT = FIXTURE_DIR / "vectorworks_worksheet_multisystem_full.csv"
SNAPSHOT = FIXTURE_DIR / "stage1_contract_snapshot.json"

TOOL = "precheck_vectorworks_diff"


class _NeverCalledExecutionPort:
    def execute(self, command: str):
        raise AssertionError(f"{TOOL} must never call execution_port: {command}")


class _RigPort:
    """빈 콘솔 — 계약 형상은 콘솔 내용과 무관해야 한다."""

    def query_state(self, path: str) -> dict:
        if path == FIXTURE_ROOT:
            return {
                "ok": True,
                "path": path,
                "node": {"name": "Fixtures", "class": "Fixtures", "childCount": 0},
                "children": [],
                "truncated": False,
            }
        return {"ok": False, "path": path, "error": "not readable"}

    def query_property(self, path: str, property_name: str) -> dict:
        return {"ok": False, "path": path, "property": property_name, "error": "not readable"}


def _stage1_payload() -> dict:
    rig = _RigPort()
    registry = build_toolset(
        execution_port=_NeverCalledExecutionPort(), state_port=rig, property_port=rig
    )
    execution = registry.dispatch(
        ToolCall(
            id="c1",
            name=TOOL,
            arguments={
                "file_content_base64": base64.b64encode(EXPORT.read_bytes()).decode("ascii")
            },
        )
    )
    assert execution.result.is_error is False, execution.result.content
    return json.loads(execution.result.content)


def type_signature(value: object) -> object:
    """값이 아니라 **모양**만 남긴다 — AC-AUTOPATCH-025①이 정한 깊이 그대로.

    최상위 값의 타입(dict/list/str/int/bool)과, 리스트면 **원소 타입의 집합**까지다.
    더 깊이 들어가지 않는 것은 의도다: 중첩 구조까지 고정하면 1단계 내부의 정당한
    확장(실제로 M7이 `designed_rig.fixtures[*]`에 열 셋을 더했다)마다 깨지고, 그러면
    스냅샷은 기계적으로 갱신되어 아무것도 막지 못하게 된다. 중첩 의미는 1단계 자신의
    구조 assert가 지킨다(AC-025③) — 여기서 사본을 만들지 않는다.
    """
    if isinstance(value, list):
        return {"list": sorted({type(item).__name__ for item in value})}
    return type(value).__name__


def _top_level_signature(payload: dict) -> dict:
    return {key: type_signature(value) for key, value in sorted(payload.items())}


def test_the_top_level_contract_matches_the_snapshot():
    """AC-025② — 최상위 키 집합과 키별 타입 시그니처가 동일하다."""
    recorded = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    observed = _top_level_signature(_stage1_payload())
    assert set(observed) == set(recorded), "1단계 payload의 최상위 키 집합이 바뀌었다"
    assert observed == recorded


def test_an_added_top_level_key_control_is_caught():
    """AC-025④ 비공허성 — 최상위 키를 하나 추가한 사본에서 위 단정이 실제로 실패한다."""
    recorded = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    planted = {**_stage1_payload(), "patch_result": {"ok": True}}
    observed = _top_level_signature(planted)
    assert set(observed) != set(recorded)
    assert observed != recorded


def test_a_changed_type_signature_control_is_caught():
    """AC-025④ 비공허성 — 키를 남긴 채 타입만 바꿔도 잡힌다(키 집합 비교만으로는 못 잡는다)."""
    recorded = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    planted = {**_stage1_payload(), "summary_ko": ["문자열이 아니라 리스트"]}
    observed = _top_level_signature(planted)
    assert set(observed) == set(recorded), "이 대조군은 키 집합은 그대로여야 의미가 있다"
    assert observed != recorded


def test_the_designed_fixture_rows_carry_the_patch_layer_columns():
    """M7이 **추가**한 중첩 열 — 없으면 패치 계층이 전부 `footprint_unknown`이 된다."""
    payload = _stage1_payload()
    rows = payload["designed_rig"]["fixtures"]
    assert rows, "픽스처가 0대면 이 확인은 공허하다"
    for row in rows:
        assert {"gdtf_fixture", "mode", "footprint"} <= set(row)


def test_the_added_columns_did_not_displace_the_stage_one_columns():
    """추가지 교체가 아니다 — 1단계가 쓰던 열이 그대로 있다."""
    (row, *_) = _stage1_payload()["designed_rig"]["fixtures"]
    assert {
        "unit_number",
        "instrument_type",
        "system",
        "universe",
        "address",
        "classification",
        "address_basis",
    } <= set(row)


# --- round17 스캐너 스코프·앵커 전문 동등 (ScopeAndTables) ---
#
# 이 절은 `test_autopatch_*.py` **전 파일에 걸친** 두 가지 구조적 성질을 고정한다.
# 어느 한 파일 안에 두면 형제 파일이 곧 같은 결함을 다시 만든다 — round11부터 일곱 라운드
# 연속 FAIL의 기제가 정확히 그것이고, round17에서는 **모듈 경계**에서 그 일이 벌어졌다.
#
#   (가) [round17 #7] **AST 스캐너의 스코프가 선언보다 좁다.**
#        `_R16_BOOL_GUARD_ROWS`는 "정수 판독기 **전부**의 규약"이라 선언하면서 파서는
#        `patchplan.py` 한 모듈만 읽었다. 실제 가드는 여섯 곳이고, `typemap._optional_int`와
#        `luagen._lua_int`의 가드를 지워도 스위트 5,690건이 전건 통과했다.
#        `luagen._lua_int`는 **전달물 `fid`를 만드는** 자리다.
#        같은 결함이 `_r16_validate_autopatch_sites`에도 있었다 — 독스트링은
#        `server/vwx/*.py`라 적고 `_R16_VWX_MODULES` 네 모듈만 읽었다(round17에서 넓혔다).
#        그래서 여기서 **직접 `ast.parse`를 부르는 스캐너를 전수 등기**하고,
#        스코프를 소스에서 파생해 선언과 대조하며, 전체성 어휘를 쓰는 스캐너는
#        자기 스코프를 문장 안에 **명시**하도록 강제한다.
#
#   (나) [round17 #6] **앵커 검사가 부분문자열이라 뒤에 붙이면 통과한다.**
#        `_fid_precheck_incomplete_checks` 사유 뒤에 안심 문장을 **덧붙여도** 통과했다 —
#        금지 8문구 회피 + 필수 조각 2개 유지 + 앵커 부분문자열 온전. 심기 앵커는
#        `.replace(anchor, ...)`로만 쓰이므로 앵커가 **소스의 어디까지인지**를 아무도
#        단정하지 않았다. 여기서 앵커마다 **바로 뒤에 와야 하는 리터럴**을 함께 등기해
#        "앵커 뒤에 덧붙은 것이 없다"를 강제한다.

AUTOPATCH_TEST_DIR = PROJECT_ROOT / "server" / "tests"
AUTOPATCH_TEST_FILES = tuple(sorted(p.name for p in AUTOPATCH_TEST_DIR.glob("test_autopatch_*.py")))
VWX_DIR = PROJECT_ROOT / "server" / "vwx"

#: `server/vwx` 순회에서 빼는 디렉터리 이름. **제외 규칙은 이 한 자리에만 있다** —
#: 같은 제외를 열 군데에 복사하면 그 사본들이 다음 라운드의 형제 불일치가 된다.
#: (round15 B가 `_discover_modules`에서 재귀성을 고쳤는데 형제 아홉 자리로 전파되지
#: 않은 것이 이 SPEC의 서명 형태다 — 순회의 정의를 나눠 갖는 순간 같은 일이 반복된다.)
_VWX_SCAN_EXCLUDED_DIRS = frozenset({"__pycache__", ".venv", "venv", ".tox", ".mypy_cache"})


def iter_vwx_modules(root: Path | str = VWX_DIR) -> tuple[Path, ...]:
    """`root`(기본 `server/vwx`) 아래 파이썬 모듈 **전수**. 「전 모듈」의 **유일한** 정의다.

    `rglob`이라 하위 패키지까지 내려간다. 평면 `glob("*.py")`은 `server/vwx/` **바로
    아래**만 보므로 하위 패키지가 하나 생기는 순간 그 파일들이 「전 모듈」 정의에서
    조용히 빠진다. 오늘은 `server/vwx`에 하위 패키지가 없어 두 표현의 결과가 **같다** —
    그래서 실물만으로는 그 축소가 보이지 않고, 아래 (다) 절이 합성 트리와 주입
    대조군으로 그 사각을 대신 잰다.
    """
    return tuple(
        sorted(
            path
            for path in Path(root).rglob("*.py")
            if _VWX_SCAN_EXCLUDED_DIRS.isdisjoint(path.parts)
        )
    )


def vwx_module_label(path: Path | str) -> str:
    """스캔한 경로 → 등기부가 쓰는 모듈 표지. `server/vwx` 기준 상대 posix 경로다.

    `path.name`으로 줄이면 `console/report.py`와 `report.py`가 **같은 표지로 뭉쳐**
    하위 패키지가 생기는 날 두 자리가 하나로 붕괴한다 — 순회만 넓히고 표지를 그대로
    두면 재귀가 반만 된 것이다. 오늘은 전 모듈이 최상위라 `path.name`과 값이 같다.
    """
    _head, separator, tail = Path(path).as_posix().rpartition("server/vwx/")
    return tail if separator else Path(path).name


#: 「전 모듈」의 **분모**. 재귀 순회에서 파생한다 — 분모가 틀리면 그 위의 판정이 전부
#: 같이 틀린다(아래 round17 등기부 전체가 이 집합을 딛는다).
VWX_MODULE_FILES = frozenset(vwx_module_label(path) for path in iter_vwx_modules())

#: **결속에서 빼는** 이름. 분모는 대조용 **이름 집합**이지 "읽을 파일"이 아니다 —
#: 넣으면 등기부를 대조하는 함수(`_r17_ast_scanners`)가 분모를 참조한다는 이유만으로
#: 자기 자신을 「전 모듈을 읽는 스캐너」로 세고, 비공허성 단정이 항진식이 된다.
_R17_NON_READING_NAMES = ("VWX_MODULE_FILES",)

#: 전체성을 주장하는 어휘. 이 중 하나가 스캐너 독스트링에 있으면 스코프를 명시해야 한다.
#: `전체`는 제외한다 — "점 표기 체인 전체"처럼 **스코프가 아닌 것**을 가리키는 용례가 흔해
#: 거짓 양성이 잦고, 흔한 거짓 양성은 게이트의 강제력을 없앤다(§0 2b④가 금하는 바로 그것).
_R17_TOTALITY_WORDS = ("전부", "전수", "모든")

#: 「`server/vwx` **트리 전체**를 읽는다」는 주장으로 세는 어휘. 위 전체성 어휘보다 좁다 —
#: 트리 주장은 `server/vwx` 표기 **바로 뒤**에 붙어야 하고(아래 창), `server/vwx/apply.py`
#: 처럼 잎을 가리키는 표기는 트리 주장이 아니다.
_R24_TREE_CLAIM_WORDS = ("전 모듈", "전부", "전수", "모든")

#: 트리 주장을 세는 창(정규화 후 글자 수). 넓히면 "`server/vwx`의 나머지 … 전부"처럼
#: 자기 스코프가 아닌 문장이 걸리고, 좁히면 "`server/vwx/` **전 모듈**"을 놓친다.
_R24_TREE_CLAIM_WINDOW = 12

#: 「이름을 **임포트 그래프**로 푼다」는 주장으로 세는 어휘. `해석`과 **함께** 나와야 한다 —
#: `임포트`만 보면 임포트 봉인 스캐너들처럼 임포트를 **소재로** 다루는 자리가 전부 걸린다.
_R24_RESOLUTION_CLAIM_WORDS = ("임포트", "재수출", "모듈 속성", "모듈 **속성**", "형제 모듈")

#: 규율의 **정의**를 담은 함수. 그 독스트링에 나오는 위 어휘는 주장이 아니라 뜻풀이다.
#: 빼지 않으면 판정기가 자기 어휘를 자기 주장으로 세어 등기부가 **자기를** 위반자로
#: 신고한다(실측으로 그렇게 됐다) — `_R17_NON_READING_NAMES`가 분모에서 막는 것과 같은
#: 자기참조다. 아래 `test_r24_the_claim_vocabulary_exclusion_is_alive`가 죽은 행을 막는다.
_R24_CLAIM_VOCABULARY_DEFINERS = ("_r24_resolution_kind",)

#: 이 파일 자신의 표지. 등기부가 자기 모듈을 가리킬 때 이름을 손으로 적지 않는다.
_R24_CONTRACT_FILE = Path(__file__).name

_R24_RESOLUTION_IMPORT = "import_bound"
_R24_RESOLUTION_SYNTACTIC = "syntactic"


def _r17_reads_every_vwx_module(node: ast.AST, aliases: dict[str, str]) -> bool:
    """`server/vwx` **전 모듈**을 손에 넣는 표현인가 — 그 디렉터리를 훑거나, 그 디렉터리를
    **자기가 이름 지어** 함수에 넘기거나.

    `Path("server/vwx") / name`처럼 경로를 **조인**하는 것과 구별한다 — 순회는 스코프가
    "그 시점의 전 모듈"이지만 조인은 조인되는 이름이 정한다. 이 구별이 없으면
    두 모듈만 읽는 스캐너가 전 모듈 스캐너로 오분류되어 규율이 거짓 양성을 낸다.

    [round24] 판정을 (다)절의 `_r24_sweep_method`·`_r24_dir_tail`에 **위임**한다. 여기에
    환원기를 다시 적으면 사본이 두 벌이 되고, 갈라진 사본이 곧 다음 라운드의 형제
    불일치다((다)절이 순회의 정의를 하나로 묶는 것과 같은 이유). 리터럴만 보던 구판은
    `VWX_DIR.glob(...)`처럼 경로를 이름에 **한 다리 건너** 담은 순회를 보지 못했다.

    디렉터리를 **인자로 넘기는** 호출도 같은 값으로 본다 —
    `_discover_modules(Path("server/vwx"))`처럼 순회를 함수 뒤로 옮기면 메서드 호출
    형태가 사라진다. 실측: 그 사각에 오늘 스캐너 셋이 들어 있었다. 뿌리가 매개변수면
    `_r24_dir_tail`이 환원하지 못하므로 `iter_vwx_modules(root)`는 여전히 호출자 스코프다.

    인자가 **맨 문자열 리터럴**이면 세지 않는다. `text.startswith("server/vwx/")`처럼
    경로 **접두사**를 다루는 자리가 순회로 오분류되어 실측 거짓 양성 둘을 냈다 —
    디렉터리를 건네는 자리는 `Path(...)`이거나 경로에 결속된 이름이다.
    """
    if _r24_sweep_method(node, aliases) is not None:
        return True
    if not isinstance(node, ast.Call):
        return False
    if _r24_dir_tail(node, aliases) is not None:
        return False  # 경로를 **짓는** 표현이다(`Path(...)`·`.resolve()`) — 훑는 것이 아니다
    if (
        isinstance(node.func, ast.Name)
        and node.func.id == iter_vwx_modules.__name__
        and not node.args
        and not node.keywords
    ):
        return True  # 공용 순회의 **기본 뿌리**가 `server/vwx`다
    return any(
        not isinstance(argument, ast.Constant)
        and (_r24_dir_tail(argument, aliases) or "").rsplit("/", 1)[-1] == "vwx"
        for argument in [*node.args, *(keyword.value for keyword in node.keywords)]
    )


def _autopatch_test_source(name: str) -> str:
    return (AUTOPATCH_TEST_DIR / name).read_text(encoding="utf-8")


def _r17_module_bindings(source: str) -> dict[str, frozenset[str]]:
    """테스트 모듈에서 **이름 → 읽는 `server/vwx` 모듈 파일 집합**을 소스에서 파생한다.

    `PATCHPLAN_PATH = Path("server/vwx/patchplan.py")` 같은 리터럴 결속과,
    `PATCHPLAN_SOURCE = PATCHPLAN_PATH.read_text(...)` 같은 **한 다리 건넌** 결속,
    `_R16_VWX_MODULES = ("apply.py", ...)` 같은 파일명 튜플까지 고정점까지 전파한다.
    """
    tree = ast.parse(source)
    aliases = _r24_path_aliases(tree.body, {})
    bindings: dict[str, frozenset[str]] = {}

    def modules_in(node: ast.AST) -> frozenset[str]:
        found: set[str] = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                text = child.value.rstrip("/")
                if (
                    text.startswith("server/vwx/")
                    and text[len("server/vwx/") :] in VWX_MODULE_FILES
                ):
                    found.add(text[len("server/vwx/") :])
                elif text in VWX_MODULE_FILES:
                    found.add(text)
            elif _r17_reads_every_vwx_module(child, aliases):
                # 디렉터리를 **훑거나** 그 디렉터리를 함수에 넘긴다 — 스코프는 전 모듈이다.
                # 단순히 `Path("server/vwx") / name`으로 **조인**하는 것은 전 모듈이 아니다.
                found |= VWX_MODULE_FILES
            elif isinstance(child, ast.Name):
                found |= bindings.get(child.id, frozenset())
        return frozenset(found)

    targets: list[tuple[str, ast.AST]] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id not in _R17_NON_READING_NAMES:
                    targets.append((target.id, node.value))
        elif isinstance(node, ast.FunctionDef) and not node.args.args:
            targets.append((node.name, node))

    for _ in range(len(targets) + 1):
        changed = False
        for name, value in targets:
            found = modules_in(value)
            if found and bindings.get(name) != found:
                bindings[name] = found
                changed = True
        if not changed:
            break
    return bindings


def _r24_calls_ast_parse(fn: ast.AST) -> bool:
    """이 함수가 **직접** `ast.parse`를 부르는가 — 등기부의 모집단 정의다."""
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "parse"
        and getattr(node.func.value, "id", None) == "ast"
        for node in ast.walk(fn)
    )


def _r24_referenced_names(node: ast.AST) -> set[str]:
    """이 노드가 **이름으로** 언급하는 것 전수 — 호출뿐 아니라 값으로 넘기는 참조까지.

    호출만 세면 `resolve_for = _r23_module_resolver if ... else ...`처럼 헬퍼를 **값으로**
    건네는 자리가 통째로 사각이 된다. R23-3의 해석기가 정확히 그렇게 건네진다.
    """
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id)
        elif isinstance(child, ast.Attribute):
            names.add(child.attr)
    return names


def _r24_reachable_helpers(fn: ast.AST, helpers: dict[str, ast.AST]) -> tuple[ast.AST, ...]:
    """스캐너에서 이름으로 닿는 **같은 모듈 최상위 함수** 전수(자기 포함, 고정점까지)."""
    closure: dict[int, ast.AST] = {id(fn): fn}
    pending = [fn]
    while pending:
        for name in _r24_referenced_names(pending.pop()):
            target = helpers.get(name)
            if target is not None and id(target) not in closure:
                closure[id(target)] = target
                pending.append(target)
    return tuple(closure.values())


def _r24_resolution_kind(closure: tuple[ast.AST, ...]) -> str:
    """이 스캐너가 이름을 **임포트 그래프**로 푸는가, 파싱한 글자로만 푸는가.

    `import_bound`의 서명은 둘이다 — `importlib.import_module(...)`이거나, 두 번째 인자가
    상수가 **아닌** `getattr(...)`(=런타임 객체에서 이름을 꺼낸다). 그 외는 전부
    `syntactic`이다: 이름의 뜻을 자기가 읽은 글자 안에서만 정한다.

    이 값은 「해석이 옳은가」가 아니라 「무엇으로 푸는가」다. 파일별 해석이 **옳은**
    스캐너가 많으므로(`_r17_report_builder_names` 계열) `syntactic`은 결함이 아니다 —
    아래 규율이 거는 것은 값 자체가 아니라 **선언과 값의 일치**다.
    """
    for node in closure:
        for call in ast.walk(node):
            if not isinstance(call, ast.Call):
                continue
            func = call.func
            if isinstance(func, ast.Attribute):
                name = func.attr
            elif isinstance(func, ast.Name):
                name = func.id
            else:
                continue
            if name == "import_module":
                return _R24_RESOLUTION_IMPORT
            if (
                name == "getattr"
                and len(call.args) >= 2
                and not isinstance(call.args[1], ast.Constant)
            ):
                return _R24_RESOLUTION_IMPORT
    return _R24_RESOLUTION_SYNTACTIC


def _r24_claims_cross_module_resolution(docs: tuple[str, ...]) -> bool:
    """이 스캐너(와 그것이 닿는 헬퍼)가 **모듈 경계를 넘는 이름 해석**을 주장하는가."""
    return any(
        "해석" in doc and any(word in doc for word in _R24_RESOLUTION_CLAIM_WORDS) for doc in docs
    )


def _r24_claims_the_whole_tree(doc: str) -> bool:
    """이 문장이 「`server/vwx` **트리 전체**를 읽는다」고 주장하는가.

    `server/vwx` 표기 **바로 뒤**의 좁은 창만 본다. 문서 어디에든 `server/vwx`와 전체성
    어휘가 함께 있으면 걸리게 하면 "`server/vwx`의 나머지 모듈은 …" 같은 참인 문장이
    전부 위반이 되고, 흔한 거짓 양성은 게이트의 강제력을 없앤다(§0 2b④).
    `server/vwx/apply.py`처럼 **잎**을 가리키는 표기는 트리 주장이 아니므로 건너뛴다.
    """
    for match in re.finditer("server/vwx", doc):
        rest = doc[match.end() :]
        if re.match(r"/\w+\.py", rest):
            continue
        window = re.sub(r"[\s`*_—·]", "", rest)[:_R24_TREE_CLAIM_WINDOW]
        if any(word.replace(" ", "") in window for word in _R24_TREE_CLAIM_WORDS):
            return True
    return False


class _R17Scanner(NamedTuple):
    """등기부 한 행. **두 축**을 싣는다 — 어느 파일을 읽는가 · 이름을 무엇으로 푸는가."""

    file: str
    function: str
    kind: str
    modules: tuple[str, ...]
    doc: str
    resolution: str
    resolution_claim: bool


def _r17_scanners_in_source(name: str, source: str) -> tuple[_R17Scanner, ...]:
    """**인자로 받은 소스** 한 벌에서 스캐너 등기 행을 전수로 낸다.

    스코프는 호출자가 준 소스다 — 이 함수는 무엇을 읽을지 스스로 고르지 않는다.
    실물 등기부(`_r17_ast_scanners`)와 주입 대조군이 **같은 판정식**을 딛게 하려고
    소스를 인자로 뺐다. 판정식을 두 벌 두면 대조군은 초록인데 실물은 아무것도 안
    잡는 상태가 성립한다((다)절이 같은 이유로 같은 모양을 취한다).
    """
    tree = ast.parse(source)
    bindings = _r17_module_bindings(source)
    module_aliases = _r24_path_aliases(tree.body, {})
    helpers = {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    scanners: list[_R17Scanner] = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not _r24_calls_ast_parse(fn):
            continue
        aliases = dict(module_aliases)
        aliases.update(_r24_path_aliases(list(ast.walk(fn)), module_aliases))
        aliases.update(_r24_default_aliases(fn, module_aliases))
        reached: set[str] = set()
        for node in ast.walk(fn):
            if isinstance(node, ast.Name):
                reached |= bindings.get(node.id, frozenset())
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                text = node.value.rstrip("/")
                if text.startswith("server/vwx/"):
                    leaf = text[len("server/vwx/") :]
                    if leaf in VWX_MODULE_FILES:
                        reached.add(leaf)
            elif _r17_reads_every_vwx_module(node, aliases):
                reached |= VWX_MODULE_FILES
        if reached:
            kind = "self_bound"
        elif fn.args.args or fn.args.posonlyargs or fn.args.kwonlyargs:
            kind = "caller"
        else:
            kind = "synthetic"
        closure = _r24_reachable_helpers(fn, helpers)
        docs = tuple(
            (ast.get_docstring(node) or "").strip()
            for node in closure
            if getattr(node, "name", None) not in _R24_CLAIM_VOCABULARY_DEFINERS
        )
        scanners.append(
            _R17Scanner(
                name,
                fn.name,
                kind,
                tuple(sorted(reached)),
                (ast.get_docstring(fn) or "").strip(),
                _r24_resolution_kind(closure),
                _r24_claims_cross_module_resolution(docs),
            )
        )
    return tuple(sorted(scanners))


def _r17_ast_scanners() -> tuple[_R17Scanner, ...]:
    """`test_autopatch_*.py`에서 **직접 `ast.parse`를 부르는** 함수를 전수로, 두 축과 함께.

    ㉠ **파일 범위** — `server/vwx` 모듈 파일 목록과 대조해 세 값 중 하나로 정한다:
       `caller`(스코프를 호출자가 정한다) · `self_bound`(자기가 읽을 모듈을 스스로 고른다) ·
       `synthetic`(프로덕션 모듈을 읽지 않는다).
    ㉡ **심볼 해석** — 이름을 임포트 그래프로 푸는가(`import_bound`) 파싱한 글자로만
       푸는가(`syntactic`), 그리고 그 스캐너가 **전자를 주장하는가**.

    [round24] 인자를 받는다는 이유만으로 `caller`로 접지 않는다. `_r17_vwx_trees(overrides)`
    처럼 **대조군용 덧인자**를 가진 스캐너가 실제로는 자기가 고른 트리를 읽는데도 등기에서
    `caller`로 빠져 있었다 — 서명이 아니라 **실제로 닿는 스코프**가 분류를 정한다. 뿌리가
    매개변수인 자리(`iter_vwx_modules(root)`)는 여전히 `caller`다: `_r24_dir_tail`이
    매개변수를 환원하지 않으므로 「자기가 상수를 넘긴다」와 「호출자가 정한다」가 갈린다.
    """
    return tuple(
        sorted(
            row
            for name in AUTOPATCH_TEST_FILES
            for row in _r17_scanners_in_source(name, _autopatch_test_source(name))
        )
    )


#: 이 절은 **손으로 쓴 등기부를 두지 않는다.** 두 축 모두 소스에서 파생하므로 새 스캐너는
#: 자동으로 규율에 들어오고, 지울 행 자체가 없어 조용한 축소가 불가능하다.
#: (round17 #8·#9·#10이 전부 "표는 있는데 행삭제 게이트가 없다"였다 — 표를 없애는 쪽이 낫다.)
#
# [round24] **이 등기부가 재는 두 축.**
#
#   축 ㉠ **파일 범위** — 어느 파일을 읽는가. 여기서 닫은 것:
#        · **경로 심볼 해석** — 순회 수신자를 이름·조인·`Path(...)`까지 환원한다.
#          판정을 (다)절 `_r24_dir_tail`에 **위임**해서 닫았다. round23까지 이 주석은
#          이미 "환원한다"고 적고 있었으나 `_r17_reads_every_vwx_module`은 리터럴만 봤다 —
#          **주석이 코드보다 앞서 나간 상태**였고, 그것이 이 SPEC이 열세 라운드 맞은
#          형태(선언과 실제의 분리)의 문서판이다. round24에서 코드를 주석에 맞췄다.
#        · **함수 뒤로 옮긴 순회** — `_discover_modules(Path("server/vwx"))`처럼 디렉터리를
#          **인자로 넘기는** 호출도 순회로 본다. 이 사각에 스캐너 셋이 들어 있었다.
#        · **덧인자 오분류** — 인자가 있다는 이유만으로 `caller`로 접지 않는다.
#          `_r17_vwx_trees(overrides)`가 그 사각이었다. 뿌리가 **매개변수**면 환원되지
#          않으므로 「자기가 상수를 넘긴다」와 「호출자가 정한다」는 여전히 갈린다.
#        · **분모** — 「전 모듈」이 재귀 순회에서 나온다. 분모가 틀리면 전부 같이 틀린다.
#
#   축 ㉡ **심볼 해석** — 읽은 글자에서 이름을 **무엇으로** 푸는가(`import_bound`/`syntactic`).
#        R23-3은 *넓은 파일 범위 위의 **좁은 이름 해석***이었다 — 형제 모듈에서 임포트한
#        dataclass를 못 알아보는 해석기. 파일 범위는 이미 전 모듈이었으므로 등기부에는
#        `ALL`로 올라 있었고, 그래서 두 라운드를 살아남았다. 축 ㉠만으로는 못 본다.
#
# **왜 「전 스캐너 강제 선언」이 아닌가.** 해석 범위의 *진위*는 기계로 잴 수 없다(아래
# `test_r24_...is_not_vacuous`의 근거를 보라). 그래서 남는 길은 선언인데, 스캐너마다
# 선언을 **의무화**하면 새 스캐너를 쓰는 비용이 올라 사람들이 등기를 피해 다니게 되고
# 그것이 더 나쁜 결과다. 대신 **기본값을 여기 한 자리에 선언한다**:
#
#     달리 적지 않으면 스캐너의 이름 해석은 **파일별**이다(`syntactic`).
#
# 부담은 **주장하는 쪽**에 붙는다 — 아무 말도 하지 않으면 비용 0이고, 「임포트·재수출된
# 이름도 본다」처럼 기본을 넘는 주장을 하면 기계가 **증거를 청구**한다. 「축소는 조용히,
# 확대는 부담」과 같은 형태다. 그리고 주장을 거두는 것(=강등)은 문장을 **지우는** 일이라
# diff에 남는다 — 등기에서 소리 없이 사라지는 것이 이 SPEC의 반복 실패 형태이므로,
# 그것을 「보이는 삭제」로 바꾸는 것이 여기서 살 수 있는 최선이다.


def test_at_least_one_scanner_reads_every_vwx_module():
    """[round17 #7] 비공허성 — `server/vwx` **전 모듈**을 읽는 스캐너가 실제로 존재한다.

    이것이 없으면 아래 정직성 규율은 "전부 좁게 선언하면 통과"로 공허해진다.
    round17에서 `_r16_validate_autopatch_sites`를 네 모듈에서 전 모듈로 넓힌 것이 그 자리다.
    스캔 대상을 다시 손으로 쓴 네 모듈 목록으로 좁히면 여기서 실패한다.
    """
    assert AUTOPATCH_TEST_FILES, "스캔 대상이 0개면 이 확인은 공허하다"
    assert VWX_MODULE_FILES
    widest = {frozenset(row.modules) for row in _r17_ast_scanners() if row.kind == "self_bound"}
    assert VWX_MODULE_FILES in widest, sorted(sorted(scope) for scope in widest)


def test_the_scanner_scope_classification_is_exhaustive():
    """두 축이 **닫힌 값**을 갖고, 각 값의 뜻이 실제 모양과 일치한다.

    `self_bound`는 읽는 모듈이 **비어 있지 않아야** 하고 `caller`·`synthetic`은 비어야 한다.
    """
    scanners = _r17_ast_scanners()
    assert scanners, "AST 스캐너가 0개면 아래 규율이 공허하다"
    assert {row.kind for row in scanners} <= {"caller", "self_bound", "synthetic"}
    assert {row.resolution for row in scanners} <= {
        _R24_RESOLUTION_IMPORT,
        _R24_RESOLUTION_SYNTACTIC,
    }
    for row in scanners:
        if row.kind == "self_bound":
            assert row.modules, (row.file, row.function)
        else:
            assert row.modules == (), (row.file, row.function, row.modules)


def _r17_scope_verdict(doc: str, kind: str, modules: tuple[str, ...]) -> bool:
    """선언과 실제 파일 범위가 맞는가 — **양방향**. 실물 게이트와 대조군의 유일한 판정식.

    ① (round17 #7) 전체성 어휘(`전부`·`전수`·`모든`)를 쓰는 `self_bound` 스캐너는 읽는
       모듈 이름을 전부 적거나, 전 모듈을 읽으면 `server/vwx`를 적어야 한다.
    ② [round24] **역방향** — 문장이 「`server/vwx` 트리 전체를 읽는다」고 주장하는데 실제
       스코프가 전 모듈이 아니면 위반이다. 이것이 **분류 강등의 공시**다: 항목이 명단에서
       빠지는 것은 삭제와 같은 효과인데 diff에는 삭제로 보이지 않는다(round23 `GateScope`가
       자기 강등을 손으로 공시했고, `RecursiveScan`이 8개 동시 강등을 손으로 막았다).
       역방향을 걸면 강등한 사람이 **문장부터 고쳐야** 하고, 그 수정이 diff에 남는다.

    규율 ①은 `self_bound`에만 건다 — `caller`·`synthetic`은 무엇을 읽을지 스스로 고르지
    않으므로 그 독스트링의 "전수"는 "받은 것 전수"라는 참인 문장이다. 규율 ②는 **모든**
    분류에 건다: 강등은 분류가 바뀌는 일이므로 바뀐 뒤의 분류에서도 걸려야 한다.
    """
    reads_the_tree = kind == "self_bound" and set(modules) == VWX_MODULE_FILES
    if _r24_claims_the_whole_tree(doc) and not reads_the_tree:
        return False
    if not any(word in doc for word in _R17_TOTALITY_WORDS):
        return True
    if kind != "self_bound":
        return True
    if reads_the_tree:
        return "server/vwx" in doc
    return all(item in doc for item in modules)


def _r17_scope_declaration_offenders(
    scanners: tuple[_R17Scanner, ...] | None = None,
) -> list[tuple[str, str, str, str]]:
    """선언과 파일 범위가 갈라진 스캐너를 전수로. 소스를 주면 그 소스에 대해 잰다."""
    return [
        (row.file, row.function, row.kind, row.doc.splitlines()[0] if row.doc else "")
        for row in (_r17_ast_scanners() if scanners is None else scanners)
        if not _r17_scope_verdict(row.doc, row.kind, row.modules)
    ]


def test_no_scanner_claims_totality_without_naming_its_own_scope():
    """[round17 #7 / round24] 스캐너의 **문장과 실제 파일 범위가 일치**한다 — 양방향.

    round17의 두 실증이 정방향 위반이었다:
      · `_R16_BOOL_GUARD_ROWS`가 "정수 판독기 **전부**의 규약"이라 선언하고 파서는
        `patchplan.py`만 읽었다 — 여섯 가드 중 둘(`typemap._optional_int`·`luagen._lua_int`)이
        무게이트였고 지워도 5,690건이 전건 통과했다.
      · `_r16_validate_autopatch_sites`가 `server/vwx/*.py`라 적고 네 모듈만 읽었다.

    [round24] 역방향이 실물에서 넷을 잡았다 — 문장은 「`server/vwx` 전 모듈」인데 등기는
    `synthetic`/`caller`였던 자리들(`_r18_production_import_names`·`_r19_production_builtin_usage`·
    `_r19_translation_sites`·`_r17_vwx_trees`). 넷 다 판정기가 순회를 못 알아본 것이었고,
    round24에서 판정기를 고쳐 등기가 문장을 따라잡았다. 앞으로 스코프를 좁히면서 문장을
    그대로 두면 여기서 실패한다 — 어느 방향이든 갈라지는 순간이 곧 실패 지점이다.
    """
    assert _r17_scope_declaration_offenders() == []


def _r24_resolution_offenders(
    scanners: tuple[_R17Scanner, ...] | None = None,
) -> list[tuple[str, str, str]]:
    """**모듈 경계를 넘는 해석**을 주장하면서 임포트 그래프를 쓰지 않는 스캐너를 전수로."""
    return [
        (row.file, row.function, row.resolution)
        for row in (_r17_ast_scanners() if scanners is None else scanners)
        if row.resolution_claim and row.resolution != _R24_RESOLUTION_IMPORT
    ]


def test_r24_a_cross_module_resolution_claim_is_backed_by_the_import_graph():
    """[round24 / R23-3의 축] 「임포트·재수출된 이름도 본다」는 주장에 **증거를 청구**한다.

    R23-3의 구판 해석기는 `if name not in <이 트리가 선언한 이름>: return None`이었다.
    파일 범위는 전 모듈이라 등기부에는 `ALL`로 올라 있었고, 좁았던 것은 **이름 해석**이다.
    처방은 해석을 **모듈 속성 조회**로 바꾼 것이었다 — 임포트 그래프를 타므로 형제 모듈이
    선언한 타입도 같은 규율에 들어온다. 그 처방이 **되돌려지면** 여기서 실패한다:
    `importlib.import_module`/비상수 `getattr`이 사라지는 순간 파생값이 `syntactic`이 되고
    주장만 남기 때문이다. 주장을 지워 침묵시킬 수는 있으나 그 삭제는 **diff에 남는다** —
    조용한 강등을 보이는 삭제로 바꾸는 것이 이 규율의 값이다.

    **이 게이트가 보지 않는 것**(round25 결정사항): *아무 주장도 하지 않는* 새 다중모듈
    스캐너가 파일별 해석을 해도 여기서는 조용하다. 그것까지 닫으려면 스캐너마다 해석
    범위를 **의무 선언**시켜야 하는데, ⓐ 그 의무는 새 스캐너를 쓰는 비용을 올려 사람들이
    등기를 피해 다니게 만들고 ⓑ 해석 범위의 진위는 어차피 기계로 확인할 수 없어 의무
    선언은 「검증되지 않은 문장」을 늘릴 뿐이다. 그 축의 올바른 도구는 등기부가 아니라
    **스캐너별 주입 대조군**이다(R23-3이 실제로 그렇게 닫았다: 형제 모듈이 선언한 타입을
    합성 트리에 심어 해석기가 그것을 보는지 잰다). 아직 그 대조군이 없는 자리는
    `_r19_typeresolution_calls`·`_r19_rejection_codes_in_production`·`_r21_notice_axis_table`
    셋 — 「그 타입/코드는 한 모듈에서만 만들어진다」는 **오늘의 사실**에 기대는 자리들이다
    (round23 감사 목록 D).
    """
    assert _r24_resolution_offenders() == []


def test_r24_the_registry_publishes_a_live_symbol_resolution_axis():
    """[round24] 해석 축이 **실재한다** — 두 값이 다 나오고, 주장하는 자리가 남아 있다.

    ① 축이 상수면(늘 `syntactic`이거나 늘 `import_bound`) 위 규율은 공허하다.
    ② 주장하는 스캐너가 하나도 없으면 위 규율은 지킬 것이 없는 규율이다 — 마지막 주장을
       지우는 것으로 게이트를 끄는 길을 여기서 막는다. 늘리는 것은 조용히 통과한다.
    """
    scanners = _r17_ast_scanners()
    values = {row.resolution for row in scanners}
    assert values == {_R24_RESOLUTION_IMPORT, _R24_RESOLUTION_SYNTACTIC}, sorted(values)
    claimants = [(row.file, row.function) for row in scanners if row.resolution_claim]
    assert claimants, "해석 범위를 주장하는 스캐너가 0건이면 위 규율이 공허하다"
    assert all(
        row.resolution == _R24_RESOLUTION_IMPORT for row in scanners if row.resolution_claim
    ), claimants


def test_r24_the_claim_vocabulary_exclusion_is_alive(monkeypatch):
    """[round24] 어휘 **뜻풀이** 면제가 살아 있고, 딱 그만큼만 면제한다.

    ① 죽은 행이 없다 — 면제된 이름이 실제로 이 모듈에 있다. 죽은 면제는 다음 사람에게
       "여기는 예외 구역"이라는 거짓 신호를 준다((다)절 독립 순회 등기와 같은 규율).
    ② 면제가 **부담을 진다** — 그 독스트링에 실제로 어휘가 들어 있어야 한다. 어휘가 없는
       이름을 면제 목록에 얹는 것은 아무 근거 없이 규율 밖으로 나가는 길이다.
    ③ 면제된 함수는 **스캐너가 아니다** — 스캐너가 자기를 면제 목록에 얹어 규율을 빠져
       나가는 길을 막는다.
    ④ 면제가 **실제로 필요하다** — 걷어내면 등기부가 자기를 위반자로 신고한다. 필요 없는
       면제는 지우는 편이 낫고, 필요하다는 사실은 실측으로 고정해 둔다.
    """
    module = sys.modules[__name__]
    scanners = {row.function for row in _r17_ast_scanners() if row.file == _R24_CONTRACT_FILE}
    assert _R24_CLAIM_VOCABULARY_DEFINERS
    for name in _R24_CLAIM_VOCABULARY_DEFINERS:
        target = getattr(module, name, None)
        assert target is not None, f"죽은 면제 행: {name}"
        doc = (target.__doc__ or "").strip()
        assert "해석" in doc and any(word in doc for word in _R24_RESOLUTION_CLAIM_WORDS), name
        assert name not in scanners, f"스캐너는 자기를 면제할 수 없다: {name}"

    monkeypatch.setattr(module, "_R24_CLAIM_VOCABULARY_DEFINERS", ())
    unmasked = _r24_resolution_offenders()
    assert unmasked, "면제를 걷어냈는데 아무 일도 없다면 그 면제는 지워야 한다"
    assert {row[0] for row in unmasked} == {_R24_CONTRACT_FILE}, unmasked


#: 주입 대조군용 합성 테스트 모듈. 실물 등기부와 **같은 판정식**(`_r17_scanners_in_source`)에
#: 먹인다. 판정식을 두 벌 두면 대조군은 초록인데 실물은 아무것도 안 잡는 상태가 성립한다.
_R24_PLANTED_HEAD = (
    'import ast\nimport importlib\nfrom pathlib import Path\nVWX = Path("server/vwx")\n'
)

_R24_PLANTED_WIDE = (
    "def wide():\n"
    '    """`server/vwx` **전 모듈**에서 무언가를 전수로 뽑는다."""\n'
    '    return [ast.parse(p.read_text()) for p in VWX.rglob("*.py")]\n'
)

_R24_PLANTED_NARROW = (
    "def narrow():\n"
    '    """`patchplan.py` 하나만 읽는다."""\n'
    '    return ast.parse(Path("server/vwx/patchplan.py").read_text())\n'
)


def _r24_planted_rows(*blocks: str) -> tuple[_R17Scanner, ...]:
    return _r17_scanners_in_source("planted.py", _R24_PLANTED_HEAD + "".join(blocks))


def test_the_scope_declaration_rule_is_not_vacuous():
    """대조의 대조 — 판정기가 **거짓 선언을 실제로 거짓이라고 한다**(양방향).

    실물 저장소가 규율을 지키면 위 두 단정은 "0건 == 0건"이라 판정기가 늘 참을 내도
    통과한다. 그래서 합성 소스를 실물과 **같은 판정식**에 직접 먹인다.
    """
    honest_narrow = _r24_planted_rows(_R24_PLANTED_NARROW)
    assert [row.kind for row in honest_narrow] == ["self_bound"]
    assert _r17_scope_declaration_offenders(honest_narrow) == []

    # ① 정방향 — "전부"라 적고 자기 스코프를 밝히지 않는다.
    vague = _r24_planted_rows(
        "def vague():\n"
        '    """정수 판독기 **전부**의 규약을 확인한다."""\n'
        '    return ast.parse(Path("server/vwx/patchplan.py").read_text())\n'
    )
    assert [row[1] for row in _r17_scope_declaration_offenders(vague)] == ["vague"]

    # ② 역방향(강등 공시) — 문장은 「전 모듈」인데 실제로는 한 모듈만 읽는다.
    demoted = _r24_planted_rows(
        "def demoted():\n"
        '    """`server/vwx` **전 모듈**에서 무언가를 전수로 뽑는다."""\n'
        '    return ast.parse(Path("server/vwx/patchplan.py").read_text())\n'
    )
    assert [row.kind for row in demoted] == ["self_bound"]
    assert [row[1] for row in _r17_scope_declaration_offenders(demoted)] == ["demoted"]

    # ③ 같은 강등이 `caller`로 빠지는 형태 — 스코프가 호출자에게 갔는데 문장은 그대로다.
    handed_off = _r24_planted_rows(
        "def handed_off(root):\n"
        '    """`server/vwx` **전 모듈**에서 무언가를 전수로 뽑는다."""\n'
        '    return [ast.parse(p.read_text()) for p in root.rglob("*.py")]\n'
    )
    assert [row.kind for row in handed_off] == ["caller"]
    assert [row[1] for row in _r17_scope_declaration_offenders(handed_off)] == ["handed_off"]


def test_r24_the_resolution_rule_is_not_vacuous():
    """대조의 대조 — 해석 축 판정기가 **주장과 실제를 실제로 가른다**.

    ① 같은 주장, 임포트 그래프로 해석 → 통과. ② 같은 주장, 파싱한 글자로만 해석 → 위반.
    ③ 주장 없이 파일별 해석 → 통과(그것이 **기본값**이다. 여기서 실패하게 만들면 새
       스캐너마다 선언 의무가 생기고, 그 비용이 사람들을 등기 밖으로 내몬다).
    ④ 해석기를 **값으로 건네도** 따라간다 — R23-3의 해석기가 정확히 그렇게 건네졌다.
    ⑤ `importlib` 없이 **모듈 속성 조회만** 해도 임포트 그래프로 센다 — 이미 임포트된
       모듈을 받아 `getattr`로 이름을 꺼내는 것이 R23-3 처방의 핵심 동작이고, 그 갈래를
       빼도 위 ①이 통과해 버리므로(실측 SURVIVED) 여기서 따로 심는다.
    """
    claim = '    """이름을 모듈 **속성**으로 해석한다 — 임포트·재수출된 이름도 본다."""\n'
    by_import = _r24_planted_rows(
        "def resolver(path):\n"
        + claim
        + '    module = importlib.import_module("server.vwx.apply")\n'
        + "    return lambda name: getattr(module, name, None)\n"
        + "def scan():\n"
        + '    """`server/vwx` **전 모듈**을 훑는다."""\n'
        + "    resolve = resolver\n"
        + '    return [ast.parse(p.read_text()) for p in VWX.rglob("*.py")], resolve\n'
    )
    scan = next(row for row in by_import if row.function == "scan")
    assert (scan.resolution_claim, scan.resolution) == (True, _R24_RESOLUTION_IMPORT)
    assert _r24_resolution_offenders(by_import) == []

    by_attribute = _r24_planted_rows(
        "def resolver(module):\n"
        + claim
        + "    return lambda name: getattr(module, name, None)\n"
        + "def scan():\n"
        + '    """`server/vwx` **전 모듈**을 훑는다."""\n'
        + "    resolve = resolver\n"
        + '    return [ast.parse(p.read_text()) for p in VWX.rglob("*.py")], resolve\n'
    )
    attribute_scan = next(row for row in by_attribute if row.function == "scan")
    assert attribute_scan.resolution == _R24_RESOLUTION_IMPORT
    assert _r24_resolution_offenders(by_attribute) == []

    by_source = _r24_planted_rows(
        "def resolver(tree):\n"
        + claim
        + "    declared = {n.name for n in ast.walk(tree)}\n"
        + "    return lambda name: name if name in declared else None\n"
        + "def scan():\n"
        + '    """`server/vwx` **전 모듈**을 훑는다."""\n'
        + "    resolve = resolver\n"
        + '    return [ast.parse(p.read_text()) for p in VWX.rglob("*.py")], resolve\n'
    )
    # `resolver`는 `ast.parse`를 부르지 않아 등기 대상이 아니다 — 주장은 **닿는 쪽**에 붙는다.
    assert [row[1] for row in _r24_resolution_offenders(by_source)] == ["scan"]

    silent = _r24_planted_rows(_R24_PLANTED_WIDE)
    assert [row.resolution for row in silent] == [_R24_RESOLUTION_SYNTACTIC]
    assert [row.resolution_claim for row in silent] == [False]
    assert _r24_resolution_offenders(silent) == []


def test_r24_a_legitimate_change_to_the_scanner_population_stays_green():
    """[round24, HARD] **정당한 변경은 통과한다** — 새 스캐너 · 삭제 · 범위 확대.

    이것이 없으면 위 규율들이 역방향 대조군이 된다: 정상 작동하면서 **틀린 것을 지키는**
    게이트. round22의 치명 2건이 그 형태였다. 세 변경 모두 등기부를 손댈 필요가 없고
    (파생이라 지울 행이 없다) 문장을 고칠 필요도 없다는 것까지 여기서 고정한다.
    """
    base = _r24_planted_rows(_R24_PLANTED_WIDE, _R24_PLANTED_NARROW)
    assert [row.function for row in base] == ["narrow", "wide"]
    assert _r17_scope_declaration_offenders(base) == []
    assert _r24_resolution_offenders(base) == []

    # ① 새 스캐너 추가 — 등기에 자동으로 들어오고, 손으로 등기할 행이 없다.
    added = _r24_planted_rows(
        _R24_PLANTED_WIDE,
        _R24_PLANTED_NARROW,
        "def fresh(source):\n"
        '    """받은 소스에서 무언가를 뽑는다."""\n'
        "    return ast.parse(source)\n",
    )
    assert [row.function for row in added] == ["fresh", "narrow", "wide"]
    assert _r17_scope_declaration_offenders(added) == []
    assert _r24_resolution_offenders(added) == []

    # ② 스캐너 삭제 — 죽은 행이 남지 않으므로 아무것도 고칠 필요가 없다.
    removed = _r24_planted_rows(_R24_PLANTED_WIDE)
    assert [row.function for row in removed] == ["wide"]
    assert _r17_scope_declaration_offenders(removed) == []
    assert _r24_resolution_offenders(removed) == []

    # ③ 범위 확대 — 주장하지 않는 스캐너를 넓히는 것은 **조용히** 통과한다.
    widened = _r24_planted_rows(
        "def grows():\n"
        '    """무언가를 뽑는다."""\n'
        '    return ast.parse(Path("server/vwx/patchplan.py").read_text())\n'
    )
    assert [row.modules for row in widened] == [("patchplan.py",)]
    grown = _r24_planted_rows(
        "def grows():\n"
        '    """무언가를 뽑는다."""\n'
        '    return [ast.parse(p.read_text()) for p in VWX.rglob("*.py")]\n'
    )
    assert set(grown[0].modules) == VWX_MODULE_FILES
    assert _r17_scope_declaration_offenders(grown) == []
    assert _r24_resolution_offenders(grown) == []

    # ④ 넓히면서 「전수」를 주장하면 그때는 트리를 문장에 적어야 한다 — 그 편집만으로 통과한다.
    loud = _r24_planted_rows(
        "def grows():\n"
        '    """무언가를 **전수**로 뽑는다."""\n'
        '    return [ast.parse(p.read_text()) for p in VWX.rglob("*.py")]\n'
    )
    assert [row[1] for row in _r17_scope_declaration_offenders(loud)] == ["grows"]
    assert _r17_scope_declaration_offenders(_r24_planted_rows(_R24_PLANTED_WIDE)) == []


def test_r24_the_registry_follows_the_directory_across_hops():
    """[round24] 「어느 파일을 읽는가」를 **몇 다리 건너 적어도** 등기가 따라간다.

    round23이 남긴 사각이 정확히 이 모양이었다(round24 감사 실측). 재구성 게이트가
    리터럴 글롭을 버리고 `scan(_R23_GATED_TREE)` → `files(root)` → `iter_vwx_modules(root)`로
    **매개변수를 낀 두 홉** 뒤로 순회를 옮기자 그 시험이 `self_bound`(12) → `synthetic`(0)으로
    조용히 강등됐고, 그러면서 스코프 선언 규율의 **분모에서도 빠졌다** — 규율이 약해진 게
    아니라 대상이 사라진 것이라 아무도 울지 않았다. 그것이 이 SPEC의 서명 형태다.

    네 표기가 **같은 값**을 내야 한다(리터럴 · 이름 한 다리 · 매개변수 낀 두 홉 ·
    **기본값이 뿌리를 정하는** 매개변수). 그리고 뿌리를 **호출자가 주는** 자리는 여전히
    `caller`여야 한다 — 그 구별이 무너지면 정당한 매개변수 순회가 전부 전 모듈 스캐너로
    오분류되어 규율이 거짓 양성을 낸다(§0 2b④).

    반대쪽 거짓 양성도 같은 소스에서 잰다: 경로를 **짓기만** 하는 `Path(<이름>)`은 순회가
    아니다. 오늘은 그 표기가 실물에 없어 두 겹의 방어 중 하나만 벗겨도 결과가 같다 —
    「오늘은 결과가 같다」는 사각지대의 서명이라 여기서 값으로 못박는다.
    """
    rows = {
        row.function: row
        for row in _r24_planted_rows(
            "def sweep(root):\n"
            '    """받은 뿌리를 훑는다."""\n'
            '    return sorted(root.rglob("*.py"))\n'
            "def files(root):\n"
            '    """받은 뿌리의 파일 목록."""\n'
            "    return sweep(root)\n"
            "def literal():\n"
            '    """`server/vwx` **전 모듈**을 리터럴로 읽는다."""\n'
            '    return [ast.parse(p.read_text()) for p in Path("server/vwx").rglob("*.py")]\n'
            "def one_hop():\n"
            '    """`server/vwx` **전 모듈**을 이름 한 다리 건너 읽는다."""\n'
            '    return [ast.parse(p.read_text()) for p in VWX.rglob("*.py")]\n'
            "def two_hops():\n"
            '    """`server/vwx` **전 모듈**을 매개변수를 낀 두 홉 뒤에서 읽는다."""\n'
            "    return [ast.parse(p.read_text()) for p in files(VWX)]\n"
            "def handed(root):\n"
            '    """받은 트리를 읽는다 — 스코프는 호출자의 것이다."""\n'
            "    return [ast.parse(p.read_text()) for p in files(root)]\n"
            "def defaulted(root=VWX):\n"
            '    """`server/vwx` **전 모듈**을 읽는다 — 뿌리를 기본값으로 자기가 정한다."""\n'
            '    return [ast.parse(p.read_text()) for p in root.rglob("*.py")]\n'
            "def joins_only():\n"
            '    """`server/vwx` 아래 한 파일만 읽는다 — 조인은 순회가 아니다."""\n'
            '    return ast.parse((Path(VWX) / "apply.py").read_text())\n'
        )
    }
    assert sorted(rows) == [
        "defaulted",
        "handed",
        "joins_only",
        "literal",
        "one_hop",
        "two_hops",
    ]
    for name in ("literal", "one_hop", "two_hops", "defaulted"):
        assert rows[name].kind == "self_bound", name
        assert set(rows[name].modules) == VWX_MODULE_FILES, name
    assert rows["handed"].kind == "caller"
    assert rows["handed"].modules == ()
    assert rows["joins_only"].modules == ()
    assert _r17_scope_declaration_offenders(tuple(rows.values())) == []


# ---- (다) [round24] 「전 모듈」 순회는 재귀이고, 그 정의는 한 자리다 -------------------
#
# **무증상 결함이다.** `server/vwx`에 오늘 하위 패키지가 없어서 평면 `glob("*.py")`과
# 재귀 `rglob("*.py")`은 **같은 답**을 낸다. 그래서 열 자리가 「전 모듈」을 자처하면서
# 평면 글롭인 채로 열세 라운드를 살아남았고, 하위 패키지가 하나 생기는 날 전부 **동시에**
# 사각이 된다. 실물로 대조군을 만들 수 없다는 것이 이 결함의 성질이고, 그래서 이 절은
# 순회를 고치는 대신 **순회가 고쳐진 채로 남는 것**을 강제한다.
#
#   ① 새 평면 글롭이 들어오면 실패한다 — 합성 소스 주입 대조군이 판정기를 직접 잰다.
#   ② 순회의 정의는 `iter_vwx_modules` 하나다 — 제외 규칙이 두 벌이 되는 순간
#      두 벌은 갈라지고, 갈라진 사본이 곧 다음 라운드의 형제 불일치다.
#   ③ 예외를 허용하되 예외는 **부담을 진다** — 등기가 실재·독립·재귀임을 청구하고,
#      줄이는 것은 통과한다(규율 3).
#   ④ 하위 패키지가 생기면 재귀 순회가 그것을 본다 — 임시 트리로 실증한다.
#
# round15 B가 `_discover_modules`에서 정확히 이 결함을 진단·수정했는데 형제 아홉 자리로
# 전파되지 않았다. 「고쳤다」가 「고쳐진 채로 남는다」를 뜻하지 않은 것이 이 SPEC의
# 서명 형태이고, 위 네 항목이 그 간극을 메운다.

#: 디렉터리를 훑는 메서드. `iterdir`는 재귀가 될 수 없어 언제나 평면이다.
_R24_SWEEP_METHODS = ("glob", "rglob", "iterdir")
_R24_RECURSIVE_METHODS = ("rglob",)

#: 순회의 **유일한 정의** 자리. (저장소 상대 경로, 함수 이름).
_R24_CANONICAL_SWEEP = ("server/tests/test_autopatch_contract.py", iter_vwx_modules.__name__)

#: 공용 순회를 쓰지 **않는 것이 옳은** 자리와 사유. 예외는 부담을 진다 — 아래 세 시험이
#: (실재 · 진짜 독립 · 재귀)를 청구하고, 줄이는 것은 통과한다.
_R24_INDEPENDENT_SWEEPS = {
    (
        "server/tests/test_autopatch_types.py",
        "test_r23_the_reconstruction_gate_reads_every_file_in_its_tree",
    ): (
        "게이트의 기대값을 **독립으로** 계산하는 대조군이다. 공용 순회를 쓰면 스캐너와 "
        "기대값이 같은 함수를 딛게 되어, 그 함수가 좁아지는 순간 둘이 같이 좁아진다 — "
        "대조군이 대조군이 아니게 된다."
    ),
    (
        "server/tests/test_autopatch_contract.py",
        "test_r24_shrinking_the_independent_sweep_registry_keeps_the_gate_green",
    ): (
        "공용 순회와 독립 계산이 **같은 답을 내는지**를 재는 자리다. 여기서 공용 순회를 "
        "양변에 쓰면 항진식이 되어, 규율 3(예외를 줄여도 통과한다)의 근거가 사라진다."
    ),
}


def _r24_dir_tail(node: ast.AST, aliases: dict[str, str]) -> str | None:
    """경로식을 **끝 세그먼트들**로 환원한다 — 리터럴 · 이름 결속 · `/` 조인 · `Path(...)`.

    round17 판정기(`_r17_reads_every_vwx_module`)는 수신자 안의 **리터럴**만 봤다. 그래서
    `VWX_DIR.glob(...)`·`package.glob(...)`처럼 경로를 이름에 한 번 담아 두면 순회가
    구조적으로 보이지 않는다. 「어느 파일을 읽는가」를 이름 한 다리 건너 적으면 등기 밖으로
    나가는 것 — 그것이 R23-3이 두 라운드를 살아남은 축(심볼 해석)이다. 여기서 그 축을
    순회에 한해 닫는다.

    환원할 수 없는 뿌리는 `…`로 둔다. 우리가 묻는 것은 "끝이 `vwx`인가"뿐이므로 앞쪽이
    무엇인지는 필요 없다. 인자로 받은 뿌리는 `None`이다 — 그 스코프는 호출자의 것이다.
    """
    if isinstance(node, ast.Constant):
        return node.value.rstrip("/") if isinstance(node.value, str) else None
    if isinstance(node, ast.Name):
        return aliases.get(node.id)
    if isinstance(node, ast.Subscript):  # `parents[1]`
        return _r24_dir_tail(node.value, aliases)
    if isinstance(node, ast.Attribute):
        return "…" if node.attr in ("parent", "parents") else None
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == "Path" and node.args:
            return _r24_dir_tail(node.args[0], aliases)
        if isinstance(node.func, ast.Attribute) and node.func.attr == "resolve":
            return _r24_dir_tail(node.func.value, aliases)
        return None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        right = _r24_dir_tail(node.right, aliases)
        if right is None:
            return None
        return f"{_r24_dir_tail(node.left, aliases) or '…'}/{right}"
    return None


def _r24_path_aliases(nodes, seed: dict[str, str]) -> dict[str, str]:
    """대입에서 **이름 → 경로 꼬리** 결속을 뽑는다(한 다리 건넌 결속까지 고정점)."""
    aliases = dict(seed)
    for _ in range(3):
        for node in nodes:
            if not isinstance(node, ast.Assign):
                continue
            tail = _r24_dir_tail(node.value, aliases)
            if not tail:
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    aliases[target.id] = tail
    return aliases


def _r24_default_aliases(fn: ast.AST, seed: dict[str, str]) -> dict[str, str]:
    """매개변수 **기본값**에서 결속을 뽑는다 — `def f(root=VWX_DIR)`의 스코프는 자기 것이다.

    기본값이 없는 매개변수는 결속하지 않는다. 그 스코프는 호출자가 정하고, 그것을 순회
    자리로 세면 `_r23_reconstruction_files(root)` 같은 정당한 매개변수 순회가 전부
    거짓 양성이 된다.
    """
    args = fn.args
    positional = [*args.posonlyargs, *args.args]
    bound = positional[len(positional) - len(args.defaults) :]
    pairs = list(zip(bound, args.defaults, strict=True))
    pairs += [
        (arg, default)
        for arg, default in zip(args.kwonlyargs, args.kw_defaults, strict=True)
        if default is not None
    ]
    aliases: dict[str, str] = {}
    for arg, default in pairs:
        tail = _r24_dir_tail(default, seed)
        if tail:
            aliases[arg.arg] = tail
    return aliases


def _r24_sweep_method(node: ast.AST, aliases: dict[str, str]) -> str | None:
    """이 표현이 **`vwx` 디렉터리를 훑는** 호출이면 그 메서드 이름, 아니면 `None`.

    `Path("server/vwx") / name` 같은 **조인**은 순회가 아니다 — 스코프를 조인되는 이름이
    정하므로 두 모듈만 읽는 자리가 전 모듈 순회로 오분류되면 규율이 거짓 양성을 낸다.
    """
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
        return None
    if node.func.attr not in _R24_SWEEP_METHODS:
        return None
    tail = _r24_dir_tail(node.func.value, aliases)
    if tail is None or tail.rsplit("/", 1)[-1] != "vwx":
        return None
    return node.func.attr


def _r24_sweeps_in_source(source: str) -> tuple[tuple[str, str, int], ...]:
    """**인자로 받은 소스**에서 `vwx` 디렉터리 순회를 (함수, 메서드, 행)으로 전수한다.

    스코프는 호출자가 준 소스다 — 이 함수는 무엇을 읽을지 스스로 고르지 않는다.
    """
    tree = ast.parse(source)
    module_aliases = _r24_path_aliases(tree.body, {})
    scopes: list[tuple[str, ast.AST, dict[str, str]]] = [("<module>", tree, module_aliases)]
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            inner = _r24_path_aliases(list(ast.walk(fn)), module_aliases)
            inner.update(_r24_default_aliases(fn, module_aliases))
            scopes.append((fn.name, fn, inner))

    found: list[tuple[str, str, int]] = []
    seen: set[int] = set()
    for name, node, aliases in reversed(scopes):  # 안쪽 스코프가 바깥 결속을 이긴다
        for child in ast.walk(node):
            if id(child) in seen:
                continue
            method = _r24_sweep_method(child, aliases)
            if method is None:
                continue
            seen.add(id(child))
            found.append((name, method, child.lineno))
    return tuple(sorted(found, key=lambda row: (row[2], row[0])))


def _r24_flat_sweeps(rows):
    """재귀가 아닌 순회만 남긴다 — 실물 게이트와 주입 대조군이 **같은 판정식**을 딛는다.

    판정식을 두 벌 두면 대조군은 초록인데 실물은 아무것도 안 잡는 상태가 성립한다.
    (행은 실물 4칸 `(파일, 함수, 메서드, 행)` · 합성 3칸 `(함수, 메서드, 행)` 양쪽을 받는다.)
    """
    return [row for row in rows if row[-2] not in _R24_RECURSIVE_METHODS]


def _r24_scan_sources() -> tuple[Path, ...]:
    """규율의 사정권 — `server/tests` 아래 파이썬 소스 전수.

    `test_autopatch_*.py`로 좁히지 않는다. 같은 결함이 `test_vwx_address.py`에도 있었고,
    사정권을 파일 이름으로 좁히면 그 밖에 새 스캐너를 두는 것이 곧 우회로가 된다.
    """
    return tuple(
        sorted(
            path
            for path in AUTOPATCH_TEST_DIR.rglob("*.py")
            if _VWX_SCAN_EXCLUDED_DIRS.isdisjoint(path.parts)
        )
    )


@lru_cache(maxsize=1)
def _r24_vwx_sweeps() -> tuple[tuple[str, str, str, int], ...]:
    """`server/tests` **전 파일**의 `vwx` 디렉터리 순회를 (파일, 함수, 메서드, 행)으로 전수.

    (소스는 한 세션 안에서 바뀌지 않으므로 캐시가 stale이 될 수 없다 — 파일 100여 개를
    매 단정마다 다시 파싱하는 비용만 없앤다.)
    """
    found: list[tuple[str, str, str, int]] = []
    for path in _r24_scan_sources():
        rel = path.relative_to(PROJECT_ROOT).as_posix()
        source = path.read_text(encoding="utf-8")
        found += [(rel, fn, method, line) for fn, method, line in _r24_sweeps_in_source(source)]
    return tuple(sorted(found))


def test_r24_every_vwx_directory_sweep_is_recursive():
    """[round24] `server/vwx`를 훑는 자리는 **전부 재귀**다 — 평면 글롭이 0건이다.

    평면 `glob("*.py")`은 `server/vwx/` 바로 아래만 본다. 오늘은 하위 패키지가 없어
    결과가 같고, 그래서 이 축소는 **실물로는 보이지 않는다**. 하위 패키지가 하나 생기는
    순간 그 모듈들이 「전 모듈」 정의에서 조용히 빠지고, 그 위에 쌓인 전수 주장이 전부
    "스캔한 것 중에는 없다"로 축소된다.
    """
    sweeps = _r24_vwx_sweeps()
    assert sweeps, "순회 자리를 하나도 못 찾았다 — 판정기가 공허하다"
    assert _r24_flat_sweeps(sweeps) == [], (
        f"평면 순회가 「전 모듈」을 자처한다: {_r24_flat_sweeps(sweeps)}"
    )


def test_r24_the_sweep_census_catches_a_flat_glob_however_it_is_spelled():
    """[round24 주입 대조군] 판정기가 **새 평면 글롭을 실제로 잡는다**.

    저장소가 이미 규율을 지키면 위 단정은 "0건 == 0건"이라 판정기가 늘 거짓을 내도
    통과한다. 그래서 합성 소스를 직접 먹인다. 네 가지 표기를 섞는 것이 요점이다 —
    리터럴만 보는 판정기는 ②③④를 놓치고, 놓친 자리가 곧 다음 라운드의 사각이다.
    거짓 양성 두 가지(⑤ 조인 · ⑥ 인자 스코프)도 같은 소스에서 함께 고정한다.
    """
    planted = (
        "from pathlib import Path\n"
        'VWX = Path("server/vwx")\n'
        'FROM_ROOT = Path(__file__).resolve().parents[2] / "server" / "vwx"\n'
        "def alpha():\n"
        '    return sorted(Path("server/vwx").glob("*.py"))\n'
        "def beta():\n"
        '    return sorted(VWX.glob("*.py"))\n'
        "def gamma():\n"
        "    return sorted(FROM_ROOT.iterdir())\n"
        "def delta():\n"
        '    package = Path(__file__).resolve().parents[1] / "vwx"\n'
        '    return sorted(package.glob("*.py"))\n'
        "def epsilon():\n"
        '    return (Path("server/vwx") / "apply.py").read_text()\n'
        "def zeta(root):\n"
        '    return sorted(root.glob("*.py"))\n'
        "def eta():\n"
        '    return sorted(Path("server/vwx").rglob("*.py"))\n'
    )
    measured = _r24_sweeps_in_source(planted)
    assert [(fn, method) for fn, method, _line in measured] == [
        ("alpha", "glob"),  # ① 리터럴
        ("beta", "glob"),  # ② 모듈 상수에 담긴 경로
        ("gamma", "iterdir"),  # ③ 조인으로 지은 경로 + 재귀가 될 수 없는 메서드
        ("delta", "glob"),  # ④ 함수 안에서 지은 경로
        # ⑤ epsilon: 조인은 순회가 아니다  ⑥ zeta: 인자 뿌리는 호출자 스코프다
        ("eta", "rglob"),  # 재귀는 잡되 위반이 아니다
    ]
    # 실물 게이트와 **같은 판정식**을 먹인다 — `rglob`만 재귀로 세는지까지 여기서 고정한다.
    assert [fn for fn, _method, _line in _r24_flat_sweeps(measured)] == [
        "alpha",
        "beta",
        "gamma",
        "delta",
    ]


def test_r24_the_vwx_traversal_has_exactly_one_definition():
    """[round24] 순회의 정의가 **하나**다 — 제외 규칙이 두 벌이 될 수 없다.

    열 자리가 각자 `rglob`을 적으면 오늘은 맞지만, 그 열 벌은 다음 제외 규칙 하나에서
    갈라진다. round15 B의 수정이 형제 아홉 자리로 전파되지 않은 것이 정확히 그 형태다.
    사본을 금지하는 것이 사본을 맞추는 것보다 싸다.
    """
    sweeps = _r24_vwx_sweeps()
    canonical = [row for row in sweeps if (row[0], row[1]) == _R24_CANONICAL_SWEEP]
    assert len(canonical) == 1, canonical
    strays = [
        row
        for row in sweeps
        if (row[0], row[1]) != _R24_CANONICAL_SWEEP
        and (row[0], row[1]) not in _R24_INDEPENDENT_SWEEPS
    ]
    assert strays == [], (
        f"공용 순회를 쓰지 않는 자리다 — `iter_vwx_modules`를 쓰거나 "
        f"`_R24_INDEPENDENT_SWEEPS`에 사유와 함께 등기하라: {strays}"
    )


def test_r24_the_independent_sweep_registry_carries_weight():
    """[round24] 예외가 **부담을 진다** — 실재하고, 진짜 독립이며, 재귀다.

    ① 등기 키가 실측 순회 목록에 있다. 없으면 죽은 행이고, 죽은 행은 다음 사람에게
       "여기는 예외 구역"이라는 거짓 신호를 준다.
    ② 그 함수가 **대조군**이다(`test_` 함수) — 독립 재계산은 대조군으로서만 값이 있다.
       스캐너가 예외로 등기하는 길을 여기서 막는다: 스캐너는 공용 순회를 써야 한다.
    ③ 그 순회가 재귀다 — 예외가 평면 글롭을 밀수하는 통로가 되어서는 안 된다.
    """
    assert _R24_INDEPENDENT_SWEEPS, "예외가 0건이면 아래 대조군이 공허하다"
    measured = {(row[0], row[1]): row[2] for row in _r24_vwx_sweeps()}
    for key, reason in _R24_INDEPENDENT_SWEEPS.items():
        assert key in measured, f"죽은 예외 등기: {key}"
        assert measured[key] in _R24_RECURSIVE_METHODS, (key, measured[key])
        assert len(reason) >= 40, (key, reason)
        assert key[1].startswith("test_"), f"스캐너는 예외가 될 수 없다 — 공용 순회를 써라: {key}"


def test_r24_shrinking_the_independent_sweep_registry_keeps_the_gate_green():
    """[round24] 규율 3 — 예외를 **줄이는 것은 개선**이므로 줄여도 통과해야 한다.

    등기된 독립 계산이 오늘 공용 순회와 **같은 답**을 냄을 실제로 잰다. 같다면 그 자리를
    공용 순회로 옮겨도 게이트는 초록이다(=예외를 줄여도 된다). 같지 않다면 그것은
    "혹시 몰라서" 남은 보호막이 아니라 **다른 답을 내는 자리**이고, 그때는 예외가 아니라
    결함이다 — 어느 쪽이든 이 단정이 그 사실을 말한다.
    """
    independent = sorted(Path("server/vwx").rglob("*.py"))
    shared = [path.relative_to(PROJECT_ROOT) for path in iter_vwx_modules()]
    assert independent == shared, (independent, shared)
    assert len(shared) >= 10, shared  # 트리가 비면 위 등식은 공허하다


def test_r24_the_shared_traversal_descends_into_a_new_subpackage(tmp_path):
    """[round24] 하위 패키지가 생기면 **따라 내려간다** — 오늘 실물로는 잴 수 없는 축이다.

    `server/vwx`에 하위 디렉터리가 없어 실물에서는 `glob`과 `rglob`이 같은 답을 낸다.
    그래서 합성 트리로 잰다: 같은 트리에 평면 글롭을 함께 걸어 **무엇이 빠지는지**를
    같은 단정 안에서 고정한다. 제외 규칙(`__pycache__`)도 여기서 함께 잰다.
    """
    (tmp_path / "top.py").write_text("A = 1\n", encoding="utf-8")
    nested = tmp_path / "console" / "deep"
    nested.mkdir(parents=True)
    (nested / "buried.py").write_text("B = 2\n", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "ghost.py").write_text("C = 3\n", encoding="utf-8")

    found = [path.relative_to(tmp_path).as_posix() for path in iter_vwx_modules(tmp_path)]
    assert found == ["console/deep/buried.py", "top.py"]
    # 평면 글롭이면 하위 패키지가 통째로 빠진다 — 이것이 열 자리가 안고 있던 사각이다.
    assert sorted(path.name for path in tmp_path.glob("*.py")) == ["top.py"]


def test_r24_the_module_label_keeps_subpackages_distinct():
    """[round24] 표지가 하위 패키지를 **구별**한다 — 순회만 넓히면 재귀가 반만 된다.

    `path.name`으로 줄이면 `console/report.py`와 `report.py`가 같은 표지로 뭉쳐, 재귀로
    새로 보이게 된 자리가 등기부 안에서 다시 하나로 붕괴한다. 오늘은 전 모듈이 최상위라
    값이 `path.name`과 같아 실물로는 이 축소가 보이지 않는다.
    """
    assert vwx_module_label("server/vwx/report.py") == "report.py"
    assert vwx_module_label("server/vwx/console/report.py") == "console/report.py"
    assert vwx_module_label(PROJECT_ROOT / "server" / "vwx" / "apply.py") == "apply.py"
    assert {vwx_module_label(path) for path in iter_vwx_modules()} == VWX_MODULE_FILES


def test_r24_the_exclusion_rule_is_named_in_exactly_one_file():
    """[round24] 제외 규칙이 **한 자리**에만 적혀 있다.

    같은 제외를 열 군데에 복사하면 그 사본들이 다음 라운드의 형제 불일치다. 사본을
    맞추는 규율보다 사본을 금지하는 규율이 싸고, 위 「정의는 하나」와 짝을 이룬다.
    """
    holders = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in _r24_scan_sources()
        if "_VWX_SCAN_EXCLUDED_DIRS" in path.read_text(encoding="utf-8")
    ]
    assert holders == [_R24_CANONICAL_SWEEP[0]], holders


def test_r24_the_sweep_census_reads_every_python_file_under_server_tests():
    """[round24] 사정권이 **`server/tests` 트리 전부**다 — 파일 이름으로 좁히지 않는다.

    기대값을 이 시험이 **독립으로** 계산한다. 사정권을 `test_autopatch_*.py`로 좁히면
    오늘은 결과가 같지만(그 밖에 순회가 남아 있지 않다) 그 순간부터 파일 하나를 새로
    만드는 것이 규율의 우회로가 된다 — 「오늘 결과가 같은 축소」가 이 SPEC이 반복해서
    맞은 형태이므로, 범위 자체를 디스크와 등식으로 묶는다.
    """
    expected = sorted(
        path
        for path in (PROJECT_ROOT / "server" / "tests").rglob("*.py")
        if "__pycache__" not in path.parts
    )
    assert list(_r24_scan_sources()) == expected
    assert len(expected) >= 100, len(expected)  # 트리가 비면 위 등식은 공허하다
    assert any(path.name == "test_vwx_address.py" for path in expected)


def test_r24_referencing_the_denominator_does_not_make_a_scanner_a_reader():
    """[round24] 분모를 **참조**하는 것과 전 모듈을 **읽는** 것은 다르다.

    `VWX_MODULE_FILES`는 대조용 이름 집합이다. 이것을 결속에 넣으면 등기부를 대조하는
    함수(`_r17_ast_scanners`)가 분모를 참조한다는 이유만으로 자기를 「전 모듈을 읽는
    스캐너」로 세고, 비공허성 단정(`test_at_least_one_scanner_reads_every_vwx_module`)이
    **자기 자신으로** 충족되는 항진식이 된다 — 게이트가 자기를 증인으로 삼는 형태다.
    분모가 재귀 순회에서 파생되면서 처음 성립한 구멍이라 여기서 함께 닫는다.
    """
    planted = (
        "import ast\n"
        "from pathlib import Path\n"
        'VWX_MODULE_FILES = frozenset(p.name for p in Path("server/vwx").rglob("*.py"))\n'
        "def compares_only():\n"
        "    tree = ast.parse('')\n"
        "    return VWX_MODULE_FILES, tree\n"
    )
    assert "VWX_MODULE_FILES" not in _r17_module_bindings(planted)
    readers = {(row.file, row.function) for row in _r17_ast_scanners() if row.kind == "self_bound"}
    assert ("test_autopatch_contract.py", "_r17_ast_scanners") not in readers, sorted(readers)


def test_r24_the_scope_registry_follows_the_shared_traversal_through_an_import(monkeypatch):
    """[round24] 등기부가 **이름 한 다리 건넌** 순회를 따라간다 — R23-3의 축(심볼 해석).

    round17 판정기는 수신자 안의 리터럴만 봤다. 순회를 공용 함수로 모으는 순간, 그
    판정기로는 「전 모듈을 읽는 스캐너」가 등기에서 **소리 없이** 빠진다. 몇 개나 빠지는지를
    여기서 실측으로 고정한다 — 등기에서 조용히 사라지는 것이 이 SPEC이 열세 라운드 맞은
    형태이고, `_r17_reads_every_vwx_module`을 리터럴 전용으로 되돌리면 여기서 실패한다.
    """

    def literal_only(node: ast.AST, aliases: dict[str, str]) -> bool:
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            return False
        if node.func.attr not in _R24_SWEEP_METHODS:
            return False
        return any(
            isinstance(child, ast.Constant)
            and isinstance(child.value, str)
            and child.value.rstrip("/").endswith("server/vwx")
            for child in ast.walk(node.func.value)
        )

    def every_module_readers():
        return {
            (row.file, row.function)
            for row in _r17_ast_scanners()
            if row.kind == "self_bound" and set(row.modules) == VWX_MODULE_FILES
        }

    wide = every_module_readers()
    monkeypatch.setattr(sys.modules[__name__], "_r17_reads_every_vwx_module", literal_only)
    narrow = every_module_readers()
    lost = wide - narrow
    assert narrow <= wide
    assert len(lost) >= 6, sorted(lost)


#: 산문이 **역따옴표로 인용한 프로젝트 심볼**. 밑줄로 시작하는 비공개 이름만 센다 —
#: `caller`·`mode`·`getattr` 같은 일반 낱말은 산문이지 인용이 아니고, 그것까지 세면
#: 실측 29건이 위반으로 뜨는 거짓 양성 기계가 된다(§0 2b④).
_R24_CITED_SYMBOL = re.compile(r"`(_[A-Za-z][A-Za-z0-9_]{3,})`")


def _r24_defined_names() -> frozenset[str]:
    """저장소가 **실제로 정의하는** 이름 전수 — `server/tests` 트리와 `server/vwx` 전 모듈.

    임포트가 아니라 소스에서 뽑는다: 중첩 함수·지역 이름까지 세야 "이 이름은 어디에도
    없다"는 판정이 거짓 양성을 내지 않는다. 순회는 둘 다 공용 정의를 그대로 쓴다.
    """
    names: set[str] = set()
    for path in (*_r24_scan_sources(), *iter_vwx_modules()):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                names.add(node.id)
            elif isinstance(node, ast.arg):
                names.add(node.arg)
            elif isinstance(node, ast.alias):
                names.add((node.asname or node.name).split(".")[0])
    return frozenset(names)


def test_r24_this_file_cites_no_symbol_that_no_longer_exists():
    """[round24] 이 파일의 산문이 가리키는 심볼이 **실재한다**.

    구멍 ②의 또 다른 얼굴이다 — 등기부는 **없는 심볼을 가리켜도 조용하다**. 이 파일의
    인용 상당수는 *실행 가능한 뮤테이션 지시문*이고("사유 뒤에 … 덧붙이면 … 행이
    실패한다"), 그 대상이 사라졌으면 그 지시문은 **실행해도 아무것도 안 죽이는 공허한
    대조군**이다. round24에서 실제로 그렇게 됐다: 단수형 _fid_precheck_incomplete_check가
    복수형 튜플 반환으로 분해되면서 여기 두 자리가 유령을 가리켰고, **사람이 알려줘서**
    알았다. 그 자리가 이 게이트의 실증이다(그 이름을 여기서 역따옴표 없이 적은 것이
    바로 아래 규율의 실천이다).

    지운 이름을 **역사로** 적고 싶으면 역따옴표를 빼라 — 인용은 "지금 여기에 있다"는
    주장이고, 주장에는 증거가 붙는다.

    **사정권은 이 파일 하나다.** 형제 파일로 넓히면 오늘 아홉 자리가 걸리는데(가정법
    인용과 역사 인용이 섞여 있다) 그 아홉은 이번 라운드에 손댈 수 없는 파일에 있다.
    고칠 수 없는 것을 잡는 게이트는 영구 실패가 되고, 영구 실패는 게이트를 지우게 만든다.
    넓히는 것은 그 아홉을 정리한 라운드의 몫이다(round25 결정사항).
    """
    defined = _r24_defined_names()
    assert len(defined) >= 1000, len(defined)  # 분모가 비면 이 확인은 공허하다
    source = _autopatch_test_source(_R24_CONTRACT_FILE)
    cited = sorted(set(_R24_CITED_SYMBOL.findall(source)))
    assert len(cited) >= 15, cited  # 인용이 없으면 위 단정은 공허하다
    assert [name for name in cited if name not in defined] == []


def test_r24_the_citation_check_sees_a_ghost():
    """[round24 주입 대조군] 인용 검사가 **유령을 실제로 잡는다**.

    저장소가 규율을 지키면 위 단정은 "0건 == 0건"이라 판정기가 늘 참을 내도 통과한다.
    round24에서 사라진 그 이름을 심어 판정식을 직접 잰다 — 정규식이 일반 낱말을 세지
    않는다는 것(거짓 양성 쪽)도 같은 소스에서 함께 고정한다.

    유령 이름을 **조립해서** 만든다. 이 파일 안에 그 이름을 역따옴표로 그대로 적으면
    위 시험이 **자기 대조군을 위반으로 신고한다** — 자기 소스를 읽는 스캐너가 자기
    시험 데이터를 실물로 세는 형태이고, 이 절이 분모에서 이미 한 번 맞은 함정이다.
    """
    ghost = "_fid_precheck_incomplete_" + "check"
    planted = (
        f"# `{ghost}` 사유 뒤에 한 줄 덧붙이면 그 행이 실패한다.\n"
        "# `caller`·`mode`·`getattr`은 산문이지 인용이 아니다.\n"
        '"""`_r17_ast_scanners`는 실재한다."""\n'
    )
    cited = sorted(set(_R24_CITED_SYMBOL.findall(planted)))
    assert cited == [ghost, _r17_ast_scanners.__name__]
    defined = _r24_defined_names()
    assert [name for name in cited if name not in defined] == [ghost]


# ---- (나) 심기 앵커는 앞뒤가 닫혀 있어야 한다 --------------------------------------

#: 심기 앵커 **전수 등기부**. (테스트 파일, 소스 상수 이름, 앵커 상수/리터럴, 바로 뒤 리터럴).
#: 넷째 칸이 이 등기부의 요점이다 — 앵커가 소스에서 **어디서 끝나는지**를 고정한다.
#: 셋째 칸이 이름이면 그 테스트 모듈의 전역에서 값을 꺼낸다.
_R17_PLANT_ANCHORS = (
    (
        "test_autopatch_execute.py",
        "APPLY_SOURCE",
        "'    dry_run: bool = True,'",
        "\n) -> PatchHandoff:\n",
    ),
    (
        "test_autopatch_execute.py",
        "APPLY_SOURCE",
        "'    delivered = not dry_run'",
        "\n\n    target_by_id = {target.id: target for target in targets}\n",
    ),
    (
        "test_autopatch_execute.py",
        "APPLY_SOURCE",
        "_ORIGINAL_DELIVERY_WARNINGS",
        "\n\n\n@dataclass(frozen=True)\nclass HandoffEntry:\n",
    ),
    (
        "test_autopatch_fid.py",
        "PATCHPLAN_SOURCE",
        "INCOMPLETE_REASON_ANCHOR",
        "\n        ),\n        **read.to_dict(),\n    }\n",
    ),
    (
        "test_autopatch_tool.py",
        "TOOLS_SOURCE",
        "ASSIGNMENT_SIGNAL_LINE",
        "\n            # ",
    ),
    (
        "test_autopatch_tool.py",
        "TOOLS_SOURCE",
        "INJECTION_LINE",
        "\n\n    def apply_vectorworks_patch(",
    ),
    (
        "test_autopatch_verify.py",
        "APPLY_SOURCE",
        "'    read_complete: bool = True,'",
        "\n    delivered_ids: Sequence[str] | None = None,\n) -> PatchVerification:\n",
    ),
    (
        "test_autopatch_verify.py",
        "APPLY_SOURCE",
        "'확정 불가(거부 사유가 단일 필드로 환원되지 않는다)'",
        '"\n    return " · ".join(rejected)\n',
    ),
)


def _r17_replace_call_sites() -> tuple[tuple[str, str, str, str], ...]:
    """`<SOURCE>.replace(<앵커>, ...)` 심기 자리를 `test_autopatch_*.py` 전 파일에서 전수.

    각 원소는 `(테스트 파일, 소스 상수, 앵커 식, 감싼 함수 이름)`이다. 앵커 식이
    문자열 리터럴이거나 **모듈 전역 이름**이면 정적으로 값을 알 수 있고(`resolvable`),
    지역 변수·첨자 같은 형태면 알 수 없다 — 두 무리는 서로 다른 규율을 받는다.
    """
    sites: set[tuple[str, str, str, str]] = set()
    for name in AUTOPATCH_TEST_FILES:
        tree = ast.parse(_autopatch_test_source(name))
        globals_ = {
            target.id
            for node in tree.body
            if isinstance(node, ast.Assign)
            for target in node.targets
            if isinstance(target, ast.Name)
        }

        def visit(node: ast.AST, owner: str, globals_=globals_, name=name) -> None:
            for child in ast.iter_child_nodes(node):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    visit(child, child.name)
                    continue
                if (
                    isinstance(child, ast.Call)
                    and isinstance(child.func, ast.Attribute)
                    and child.func.attr == "replace"
                    and isinstance(child.func.value, ast.Name)
                    and child.func.value.id.endswith("SOURCE")
                    and child.args
                ):
                    anchor = child.args[0]
                    if (
                        isinstance(anchor, ast.Constant)
                        and isinstance(anchor.value, str)
                        or isinstance(anchor, ast.Name)
                        and anchor.id in globals_
                    ):
                        resolvable = True
                    else:
                        resolvable = False
                    sites.add(
                        (
                            name,
                            child.func.value.id,
                            ast.unparse(anchor),
                            "" if resolvable else owner,
                        )
                    )
                visit(child, owner)

        visit(tree, "<module>")
    return tuple(sorted(sites))


def _r17_resolvable_anchor_sites() -> tuple[tuple[str, str, str], ...]:
    """정적으로 값을 알 수 있는 심기 앵커 — 등기부가 tail을 고정해야 하는 무리."""
    return tuple(
        sorted(
            {
                (name, source, anchor)
                for name, source, anchor, owner in _r17_replace_call_sites()
                if owner == ""
            }
        )
    )


def _r17_unresolvable_anchor_sites() -> tuple[tuple[str, str, str, str], ...]:
    """앵커가 지역 값이라 등기부가 tail을 못 붙이는 심기 자리 — 다른 규율을 받는다."""
    return tuple(sorted(site for site in _r17_replace_call_sites() if site[3] != ""))


def _r17_anchor_value(test_file: str, expression: str) -> str:
    module = importlib.import_module(f"server.tests.{test_file.removesuffix('.py')}")
    node = ast.parse(expression, mode="eval").body
    if isinstance(node, ast.Constant):
        assert isinstance(node.value, str)
        return node.value
    assert isinstance(node, ast.Name), expression
    return getattr(module, node.id)


def test_the_plant_anchor_registry_is_a_bijection_onto_every_source_replace_site():
    """[round17 #6] 심기 앵커가 하나도 빠짐없이 등기돼 있다.

    새 `<SOURCE>.replace(...)` 심기를 만들고 등기하지 않으면 실패한다 — 등기되지 않은
    앵커는 "뒤에 덧붙은 것이 없다"는 단정을 받지 못하고, 그것이 round17 #6의 기제다.
    등기부에서 행을 지워도 실패한다.
    """
    declared = tuple(sorted({(f, s, a) for f, s, a, _ in _R17_PLANT_ANCHORS}))
    assert declared == _r17_resolvable_anchor_sites()
    assert len(_R17_PLANT_ANCHORS) == len(declared), "같은 앵커를 두 tail로 등기할 수 없다"


@pytest.mark.parametrize(
    "test_file,source_name,anchor_expression,tail",
    _R17_PLANT_ANCHORS,
    ids=[
        f"{f.removeprefix('test_autopatch_').removesuffix('.py')}:{a}"[:60]
        for f, _, a, _ in _R17_PLANT_ANCHORS
    ],
)
def test_nothing_is_appended_after_a_plant_anchor(test_file, source_name, anchor_expression, tail):
    """[round17 #6] 앵커 **바로 뒤**가 등기된 리터럴이다 — 부분문자열 검사의 구멍을 닫는다.

    [round17 #6] `_fid_precheck_incomplete_checks` 사유 뒤에
      `"그 밖에 우려할 것은 없으므로 그대로 진행해도 좋다."` 한 줄을 **덧붙이면**
      `test_autopatch_fid.py:PATCHPLAN_SOURCE:INCOMPLETE_REASON_ANCHOR` 행이 실패한다.
      round16까지 그 조작은 금지 8문구·필수 조각 2개·앵커 부분문자열을 **전부 통과했다**.
    [round17 #6] `build_patch_handoff`에 우회 인자를 하나 더하면 `dry_run` 행이 실패한다 —
      같은 규율이 형제 앵커 일곱 곳에 함께 걸린다.
    """
    module = importlib.import_module(f"server.tests.{test_file.removesuffix('.py')}")
    source = getattr(module, source_name)
    anchor = _r17_anchor_value(test_file, anchor_expression)
    assert source.count(anchor) == 1, (anchor_expression, source.count(anchor))
    assert anchor + tail in source, (anchor_expression, source.split(anchor)[1][: len(tail) + 40])


def _r17_self_checked_anchor_owners() -> tuple[str, ...]:
    """앵커가 지역 값인 심기 자리에서, 감싼 함수가 **스스로 유일성을 단정**하는 것만 전수.

    판정은 소스에서 한다 — 그 함수 안에 `<SOURCE>.count(...) == 1` 비교가 있어야 한다.
    """
    owners: list[str] = []
    for name, source_name, _anchor, owner in _r17_unresolvable_anchor_sites():
        tree = ast.parse(_autopatch_test_source(name))
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) or fn.name != owner:
                continue
            for node in ast.walk(fn):
                if not (isinstance(node, ast.Compare) and len(node.comparators) == 1):
                    continue
                left, right = node.left, node.comparators[0]
                counts = (
                    isinstance(left, ast.Call)
                    and isinstance(left.func, ast.Attribute)
                    and left.func.attr == "count"
                    and getattr(left.func.value, "id", None) == source_name
                )
                if counts and isinstance(right, ast.Constant) and right.value == 1:
                    owners.append(f"{name}:{owner}")
                    break
    return tuple(sorted(set(owners)))


def test_an_anchor_that_cannot_be_registered_must_check_its_own_uniqueness():
    """[round17 #6 형제 축] 지역 앵커는 등기부가 tail을 못 붙인다 — 대신 규율을 강제한다.

    앵커를 지역 변수에 담으면 위 등기부의 도달 범위 **밖으로 나간다**. 그것을 허용하되,
    그런 자리는 감싼 함수가 `SOURCE.count(anchor) == 1`을 **스스로 단정**해야 한다.
    그 단정이 없으면 부분일치 앵커가 여러 곳을 치환하거나 엉뚱한 곳을 쳐도 조용하다.

    [round17 #6] 지역 앵커 심기를 만들면서 유일성 단정을 빠뜨리면 여기서 실패한다.
    """
    unresolvable = _r17_unresolvable_anchor_sites()
    expected = tuple(sorted({f"{name}:{owner}" for name, _, _, owner in unresolvable}))
    assert _r17_self_checked_anchor_owners() == expected, unresolvable


# ==========================================================================
# --- round18 조립 실패의 **툴 경계** 거동 (SentenceScope) ---
#
# [round18 R18-D] 형태 불변식의 유일한 프로덕션 강제 자리는 `patchplan.build_patch_plan`의
# FID 사전검사 거부 사유를 짓는 자리다 — **차단 화면을 짓는 자리**다. round17 판은 거기서
# `ValueError`를 던졌고, `ToolRegistry.dispatch`(`tools.py`)·runner·session 어디에도 가드가
# 없다. 곧 조립이 실패하는 순간 **차단 자체가 사라진다**: fail-closed가 아니라 fail-crash다.
#
# 이 절은 그 경계에서 직접 잰다 — 툴을 실제로 디스패치해서 ① 예외가 나오지 않고
# ② 거부가 그대로 남고 ③ 무엇이 손상됐는지 구조화 칸으로 보이는지를 본다.
# 계약 파일에 두는 이유는 이것이 **툴 경계의 계약**이기 때문이다.
# ==========================================================================

_R18_PATCH_TOOL = "apply_vectorworks_patch"

#: round17 S17-04가 실제로 낸 결함 그대로 — 조각이 ` — `를 품어 완성 문장에 대시가 둘이 된다.
_R18_BROKEN_FRAGMENT = "열거된 슬롯이 선언 총계보다 많다 — 스냅샷이 자기모순이다"


class _R18TruncatingRigPort(_RigPort):
    """`childCount`는 총계인데 자식 목록이 짧게 오는 콘솔 — 이 빌드의 **기본 경로**.

    이 상태에서 FID 사전검사가 불완전이 되고, 강제 자리가 실제로 실행된다.
    """

    def query_state(self, path: str) -> dict:
        payload = super().query_state(path)
        if path == FIXTURE_ROOT:
            payload["node"]["childCount"] = 5
            payload["truncated"] = True
        return payload


_R18_LED = "Robin LEDBeam 350"

#: 후보 1건짜리 1단계 payload — 강제 자리에 도달하려면 실제 후보가 있어야 한다.
_R18_REPORT = {
    "designed_rig": {
        "fixture_count": 1,
        "fixtures": [
            {
                "unit_number": "1",
                "instrument_type": _R18_LED,
                "gdtf_fixture": None,
                "mode": "Mode 1",
                "footprint": 16,
                "system": None,
                "universe": 1,
                "address": 1,
                "classification": "patched",
                "address_basis": "universe_address_direct",
            }
        ],
    },
    "diffs": {
        "performed": True,
        "missing_in_console": [
            {
                "unit_number": "1",
                "instrument_type": _R18_LED,
                "universe": 1,
                "address": 1,
                "detail": "",
            }
        ],
        "address_collision": [],
        "quantity_mismatch": [],
    },
    "skipped_checks": [],
}


def _r18_dispatch_patch_tool():
    """절단된 콘솔에서 패치 툴을 실제로 디스패치한다 — 두 단계(식별자 확보 → 선택).

    절단이면 FID 사전검사가 불완전이 되고, 형태 불변식의 **유일한 프로덕션 강제 자리**가
    그 거부 사유를 짓는다. 곧 이 호출이 그 자리를 툴 경계에서 실제로 통과한다.
    """
    rig = _R18TruncatingRigPort()
    registry = build_toolset(
        execution_port=_NeverCalledExecutionPort(), state_port=rig, property_port=rig
    )

    def dispatch(**arguments):
        return registry.dispatch(ToolCall(id="r18", name=_R18_PATCH_TOOL, arguments=arguments))

    first = json.loads(dispatch(report=_R18_REPORT).result.content)
    candidate = first["plan"]["candidates"][0]["id"]
    return dispatch(
        report=_R18_REPORT,
        selected=[candidate],
        fid_range={"start": 501, "end": 599},
        names={candidate: "LEDBeam 501"},
        type_aliases={_R18_LED: {"type": _R18_LED, "mode": "Mode 1"}},
        dry_run=True,
    )


def test_r18_the_blocking_verdict_reaches_the_tool_boundary_intact():
    """[round18 R18-D 대조군] 정상 갈래 — 툴 경계에서 사유가 **문장**으로 나간다.

    강등이 늘 켜져 있으면 아래 테스트의 관측이 아무것도 말하지 않는다.
    """
    from server.vwx.patchplan import REASON_UNAVAILABLE, sentence_shape_violation

    execution = _r18_dispatch_patch_tool()
    assert execution.result.is_error is False, execution.result.content
    rejection = json.loads(execution.result.content)["plan"]["rejection"]
    assert rejection["code"] == "fid_precheck_read_incomplete"
    assert rejection["reason"] != REASON_UNAVAILABLE
    assert sentence_shape_violation(rejection["reason"]) is None, rejection["reason"]
    assert "reason_defect" not in rejection


def test_r18_a_broken_sentence_does_not_take_the_blocking_screen_down_with_it(monkeypatch):
    """[round18 R18-D] 조립이 깨져도 **툴 경계를 예외가 탈출하지 않고 차단이 남는다**.

    `ToolRegistry.dispatch`는 핸들러를 감싸지 않는다(`tools.py`) — 여기서 던지면 그대로
    올라가고, 되돌릴 수 없는 쓰기를 막던 화면이 통째로 사라진다. 그래서 조립 실패는
    **payload 필드로 강등**한다: 사유 자리에는 등재 코드, 위반 내용은 구조화 칸.

    [round18 #R18-D] `build_patch_plan`의 조립부를 `assemble_sentences`로 되돌리면
      디스패치가 `ValueError`로 터진다 — 이 테스트가 그 순간 실패한다.
    [round18 #R18-D] `PatchPlanRejection.reason_defect` 방출을 빼면 ③이 실패한다.
    """
    from server.vwx.patchplan import REASON_UNAVAILABLE, ExistingFidRead

    monkeypatch.setattr(ExistingFidRead, "reason", lambda self: _R18_BROKEN_FRAGMENT)

    execution = _r18_dispatch_patch_tool()  # ① 예외가 여기서 나오지 않는다

    assert execution.result.is_error is False, execution.result.content
    payload = json.loads(execution.result.content)
    plan = payload["plan"]
    # ② 거부 판정이 그대로다 — 차단은 남는다.
    assert plan["ok"] is False
    assert plan["status"] == "rejected"
    assert plan["rejection"]["code"] == "fid_precheck_read_incomplete"
    assert plan["rejection"]["label"]
    assert "handoff" not in payload, "차단된 호출이 전달물을 내보냈다"
    # ③ 조작자가 무엇이 손상됐는지 구조화 칸으로 본다.
    assert plan["rejection"]["reason"] == REASON_UNAVAILABLE
    defect = plan["rejection"]["reason_defect"]
    assert defect["code"] == "sentence_shape_violation"
    assert "' — '" in defect["violation"], defect
    assert _R18_BROKEN_FRAGMENT in defect["assembled"]
    assert any(_R18_BROKEN_FRAGMENT in fragment for fragment in defect["fragments"]), defect


def test_r18_the_dispatch_boundary_has_no_blanket_exception_guard():
    """[round18 R18-D] `ToolRegistry.dispatch`가 예외를 **뭉개지 않는다**는 사실을 고정한다.

    강등이 필요한 이유가 바로 이것이다. 반대 처방(`except Exception`으로 감싸기)은
    금지다 — 그러면 모든 핸들러의 진짜 결함이 조용한 오류 문자열로 바뀌고, 이 SPEC이
    여덟 라운드 반복한 "조용히 나가서 다음 감사에서야 발견된다"가 다시 열린다.
    실패는 **호출부에서 값으로** 다루고, 경계는 투명하게 둔다.

    [round18 #R18-D] `dispatch`에 `try/except Exception`을 두르면 실패한다.
    """
    source = (PROJECT_ROOT / "server" / "orchestrator" / "tools.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    dispatches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "dispatch"
    ]
    assert len(dispatches) == 1, dispatches
    handlers = [node for node in ast.walk(dispatches[0]) if isinstance(node, ast.ExceptHandler)]
    assert handlers == [], "dispatch가 예외를 삼킨다 — 강등은 호출부에서 값으로 해야 한다"
