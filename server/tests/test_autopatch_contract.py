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
import sys
from functools import lru_cache
from pathlib import Path

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
#        `_fid_precheck_incomplete_check` 사유 뒤에 안심 문장을 **덧붙여도** 통과했다 —
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

#: 인자로 소스를 받는 스캐너는 스코프가 **호출자에게** 있다. 그 사실을 문장이 밝혀야 한다.
_R17_CALLER_SCOPE_MARKERS = ("소스", "인자", "심은", "사본", "지정한", "plant")


def _r17_reads_every_vwx_module(node: ast.AST) -> bool:
    """`server/vwx` **전 모듈**을 손에 넣는 표현인가 — 디렉터리 순회이거나 공용 순회 호출.

    `Path("server/vwx") / name`처럼 경로를 **조인**하는 것과 구별한다 — 순회는 스코프가
    "그 시점의 전 모듈"이지만 조인은 조인되는 이름이 정한다. 이 구별이 없으면
    두 모듈만 읽는 스캐너가 전 모듈 스캐너로 오분류되어 규율이 거짓 양성을 낸다.

    [round24] `iter_vwx_modules(...)` **호출**도 같은 값으로 본다. round17 판정기는
    리터럴 글롭만 봤고, 그래서 순회를 공용 함수로 모으는 순간 여덟 스캐너가 등기부에서
    `self_bound`(전 모듈) → `synthetic`으로 조용히 강등됐다 — 등기에서 소리 없이
    사라지는 것이 이 SPEC의 반복 실패 형태다. 리터럴만 보는 판정기는 「어느 파일을
    읽는가」를 **이름 한 다리 건너** 적으면 못 보고, 그 축이 곧 R23-3의 축(심볼 해석)이다.
    """
    if not isinstance(node, ast.Call):
        return False
    if isinstance(node.func, ast.Name) and node.func.id == iter_vwx_modules.__name__:
        return True
    if not isinstance(node.func, ast.Attribute):
        return False
    if node.func.attr == iter_vwx_modules.__name__:
        return True
    if node.func.attr not in ("glob", "rglob", "iterdir"):
        return False
    return any(
        isinstance(child, ast.Constant)
        and isinstance(child.value, str)
        and child.value.rstrip("/").endswith("server/vwx")
        for child in ast.walk(node.func.value)
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
            elif _r17_reads_every_vwx_module(child):
                # 디렉터리를 **훑거나** 공용 순회를 부른다 — 스코프는 그 시점의 전 모듈이다.
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


def _r17_ast_scanners() -> tuple[tuple[str, str, str, tuple[str, ...]], ...]:
    """`test_autopatch_*.py`에서 **직접 `ast.parse`를 부르는** 함수를 전수로, 스코프와 함께.

    스코프는 `server/vwx` 모듈 파일 목록과 대조해 세 값 중 하나로 정한다 —
    `caller`(소스를 인자로 받는다) · `self_bound`(자기가 읽을 모듈을 스스로 고른다) ·
    `synthetic`(프로덕션 모듈을 읽지 않는다).
    """
    scanners: list[tuple[str, str, str, tuple[str, ...]]] = []
    for name in AUTOPATCH_TEST_FILES:
        source = _autopatch_test_source(name)
        tree = ast.parse(source)
        bindings = _r17_module_bindings(source)
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            parses = any(
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "parse"
                and getattr(node.func.value, "id", None) == "ast"
                for node in ast.walk(fn)
            )
            if not parses:
                continue
            if fn.args.args or fn.args.posonlyargs or fn.args.kwonlyargs:
                scanners.append((name, fn.name, "caller", ()))
                continue
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
                elif _r17_reads_every_vwx_module(node):
                    reached |= VWX_MODULE_FILES
            kind = "self_bound" if reached else "synthetic"
            scanners.append((name, fn.name, kind, tuple(sorted(reached))))
    return tuple(sorted(scanners))


#: 이 절은 **손으로 쓴 등기부를 두지 않는다.** 스코프 대조는 소스에서 전부 파생하므로
#: 새 스캐너는 자동으로 규율에 들어오고, 지울 행 자체가 없어 조용한 축소가 불가능하다.
#: (round17 #8·#9·#10이 전부 "표는 있는데 행삭제 게이트가 없다"였다 — 표를 없애는 쪽이 낫다.)
#
# [round24] **이 등기부가 재는 축과 재지 않는 축.** 여기가 재는 것은 「어느 **파일**을
# 읽는가」뿐이다. R23-3은 *넓은 파일 범위 위의 **좁은 이름 해석***이었고 — 형제 모듈에서
# 임포트한 dataclass를 못 알아보는 해석기 — 그래서 `self_bound`(전 모듈)로 등기된 채 두
# 라운드를 살아남았다. 그 축의 일부를 round24에서 닫았다:
#
#   닫은 것 ㉠ **경로 심볼 해석** — 순회 수신자를 이름·조인·`Path(...)`까지 환원한다
#            (`_r24_dir_tail`). 리터럴만 보던 판정기는 `VWX_DIR.glob(...)`를 못 봤다.
#   닫은 것 ㉡ **모듈 경계를 넘는 심볼** — `iter_vwx_modules(...)` 호출을 순회로 본다.
#            없으면 순회를 공용 함수로 모으는 순간 여덟 스캐너가 등기에서 조용히 빠진다
#            (`test_r24_the_scope_registry_follows_the_shared_traversal_through_an_import`).
#   닫은 것 ㉢ **분모** — 「전 모듈」이 재귀 순회에서 나온다. 분모가 틀리면 이 등기부 위의
#            판정이 전부 같이 틀린다.
#
#   **닫지 않은 것** — 스캐너 **안에서** 식별자를 좁게 해석하는 것(R23-3의 정확한 모양).
#   근거: 그 좁음에는 건전한 구문 서명이 없다. 「파싱한 트리에서 만든 이름 집합과 대조하면
#   의심」 같은 발견법은 `_r17_report_builder_names`처럼 **그렇게 하는 것이 옳은** 스캐너에
#   그대로 발화한다. 흔한 거짓 양성은 게이트의 강제력을 없앤다(§0 2b④) — 열세 라운드 동안
#   이 SPEC을 무너뜨린 것은 게이트의 부재만이 아니라 아무도 믿지 않는 게이트이기도 했다.
#   그 축의 올바른 도구는 등기부가 아니라 **스캐너별 주입 대조군**이다(R23-3이 실제로
#   그렇게 닫았다: 형제 모듈이 선언한 타입을 합성 트리에 심어 해석기가 그것을 보는지 잰다).
#   남은 범위: `_r19_typeresolution_calls`·`_r19_rejection_codes_in_production`·
#   `_r21_notice_axis_table` — 「그 타입/코드는 한 모듈에서만 만들어진다」는 오늘의 사실에
#   기대는 세 자리다(round23 감사 목록 D). 형제 모듈이 그것을 만들기 시작하는 날 사각이
#   되며, 그때 필요한 것은 각 자리의 주입 대조군이지 여기 표 한 줄이 아니다.


def test_at_least_one_scanner_reads_every_vwx_module():
    """[round17 #7] 비공허성 — `server/vwx` **전 모듈**을 읽는 스캐너가 실제로 존재한다.

    이것이 없으면 아래 정직성 규율은 "전부 좁게 선언하면 통과"로 공허해진다.
    round17에서 `_r16_validate_autopatch_sites`를 네 모듈에서 전 모듈로 넓힌 것이 그 자리다.
    스캔 대상을 다시 손으로 쓴 네 모듈 목록으로 좁히면 여기서 실패한다.
    """
    assert AUTOPATCH_TEST_FILES, "스캔 대상이 0개면 이 확인은 공허하다"
    assert VWX_MODULE_FILES
    widest = {
        frozenset(modules) for _, _, kind, modules in _r17_ast_scanners() if kind == "self_bound"
    }
    assert VWX_MODULE_FILES in widest, sorted(sorted(scope) for scope in widest)


def test_the_scanner_scope_classification_is_exhaustive():
    """스캐너 분류가 닫힌 세 값이고, 각 값의 뜻이 실제 모양과 일치한다.

    `self_bound`는 읽는 모듈이 **비어 있지 않아야** 하고 `caller`·`synthetic`은 비어야 한다.
    """
    scanners = _r17_ast_scanners()
    assert scanners, "AST 스캐너가 0개면 아래 규율이 공허하다"
    assert {kind for _, _, kind, _ in scanners} <= {"caller", "self_bound", "synthetic"}
    for name, function, kind, modules in scanners:
        if kind == "self_bound":
            assert modules, (name, function)
        else:
            assert modules == (), (name, function, modules)


def _r17_scope_declaration_offenders() -> list[tuple[str, str, str]]:
    """전체성을 주장하면서 **자기 스코프를 밝히지 않는** `self_bound` 스캐너를 전수로.

    규율은 `self_bound`에만 건다. 스코프 거짓말이 성립하는 자리가 거기뿐이기 때문이다 —
    `caller`·`synthetic` 스캐너는 무엇을 읽을지 **스스로 고르지 않으므로** 그 독스트링의
    "전수"는 "받은 것 전수"라는 참인 문장이다. 그쪽까지 문구를 단속하면 거짓 양성이
    잦아지고, 흔한 거짓 양성은 게이트의 강제력을 없앤다(round15 D가 같은 판단을 했다).
    `caller` 스캐너를 딛는 **표**가 넓게 선언하는 것은 그 표 자신의 전단사가 막는다.

    판정: 독스트링에 `전부`·`전수`·`모든` 중 하나가 있으면 읽는 모듈 이름을 **전부** 적거나,
    전 모듈을 읽으면 `server/vwx`를 적어야 한다.
    """
    offenders: list[tuple[str, str, str]] = []
    for name, function, kind, modules in _r17_ast_scanners():
        if kind != "self_bound":
            continue
        module = importlib.import_module(f"server.tests.{name.removesuffix('.py')}")
        target = getattr(module, function, None)
        doc = (getattr(target, "__doc__", None) or "").strip()
        if not any(word in doc for word in _R17_TOTALITY_WORDS):
            continue
        if set(modules) == VWX_MODULE_FILES:
            ok = "server/vwx" in doc
        else:
            ok = all(item in doc for item in modules)
        if not ok:
            offenders.append((name, function, doc.splitlines()[0]))
    return offenders


def test_no_scanner_claims_totality_without_naming_its_own_scope():
    """[round17 #7] "전부"라고 적은 스캐너는 자기가 **무엇을** 읽는지 문장에 적어야 한다.

    round17의 두 실증이 정확히 이 규율의 위반이었다:
      · `_R16_BOOL_GUARD_ROWS`가 "정수 판독기 **전부**의 규약"이라 선언하고 파서는
        `patchplan.py`만 읽었다 — 여섯 가드 중 둘(`typemap._optional_int`·`luagen._lua_int`)이
        무게이트였고 지워도 5,690건이 전건 통과했다.
      · `_r16_validate_autopatch_sites`가 `server/vwx/*.py`라 적고 네 모듈만 읽었다.

    [round17 #7] 어느 스캐너의 파싱 대상을 좁히면서 독스트링의 "전부"를 그대로 두면
    여기서 실패한다 — 선언과 스코프가 갈라지는 순간이 곧 실패 지점이 된다.
    """
    assert _r17_scope_declaration_offenders() == []


def test_the_scope_declaration_rule_is_not_vacuous():
    """대조의 대조 — 규율 판정기가 **거짓 선언을 실제로 거짓이라고 한다**.

    합성 스캐너를 하나 만들어 규율을 그대로 적용한다. 판정기가 늘 참이면 위 단정은 공허하다.
    """

    def honest():
        """`patchplan.py`에서 무언가를 전수로 뽑는다."""

    def dishonest():
        """정수 판독기 **전부**의 규약을 확인한다."""

    def verdict(target, kind, modules):
        doc = (target.__doc__ or "").strip()
        if not any(word in doc for word in _R17_TOTALITY_WORDS):
            return True
        if kind == "self_bound":
            if set(modules) == VWX_MODULE_FILES:
                return "server/vwx" in doc
            return all(item in doc for item in modules)
        return any(marker in doc for marker in _R17_CALLER_SCOPE_MARKERS)

    assert verdict(honest, "self_bound", ("patchplan.py",)) is True
    assert verdict(dishonest, "self_bound", ("patchplan.py",)) is False


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
    readers = {(name, fn) for name, fn, kind, _m in _r17_ast_scanners() if kind == "self_bound"}
    assert ("test_autopatch_contract.py", "_r17_ast_scanners") not in readers, sorted(readers)


def test_r24_the_scope_registry_follows_the_shared_traversal_through_an_import(monkeypatch):
    """[round24] 등기부가 **이름 한 다리 건넌** 순회를 따라간다 — R23-3의 축(심볼 해석).

    round17 판정기는 수신자 안의 리터럴만 봤다. 순회를 공용 함수로 모으는 순간, 그
    판정기로는 「전 모듈을 읽는 스캐너」가 등기에서 **소리 없이** 빠진다. 몇 개나 빠지는지를
    여기서 실측으로 고정한다 — 등기에서 조용히 사라지는 것이 이 SPEC이 열세 라운드 맞은
    형태이고, `_r17_reads_every_vwx_module`을 리터럴 전용으로 되돌리면 여기서 실패한다.
    """

    def literal_only(node: ast.AST) -> bool:
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
            (name, function)
            for name, function, kind, modules in _r17_ast_scanners()
            if kind == "self_bound" and set(modules) == VWX_MODULE_FILES
        }

    wide = every_module_readers()
    monkeypatch.setattr(sys.modules[__name__], "_r17_reads_every_vwx_module", literal_only)
    narrow = every_module_readers()
    lost = wide - narrow
    assert narrow <= wide
    assert len(lost) >= 6, sorted(lost)


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

    [round17 #6] `_fid_precheck_incomplete_check` 사유 뒤에
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
