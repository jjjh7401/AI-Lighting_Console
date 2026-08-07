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
VWX_MODULE_FILES = frozenset(p.name for p in VWX_DIR.glob("*.py"))

#: 전체성을 주장하는 어휘. 이 중 하나가 스캐너 독스트링에 있으면 스코프를 명시해야 한다.
#: `전체`는 제외한다 — "점 표기 체인 전체"처럼 **스코프가 아닌 것**을 가리키는 용례가 흔해
#: 거짓 양성이 잦고, 흔한 거짓 양성은 게이트의 강제력을 없앤다(§0 2b④가 금하는 바로 그것).
_R17_TOTALITY_WORDS = ("전부", "전수", "모든")

#: 인자로 소스를 받는 스캐너는 스코프가 **호출자에게** 있다. 그 사실을 문장이 밝혀야 한다.
_R17_CALLER_SCOPE_MARKERS = ("소스", "인자", "심은", "사본", "지정한", "plant")


def _r17_globs_the_vwx_directory(node: ast.AST) -> bool:
    """`Path("server/vwx").glob(...)`처럼 **디렉터리를 훑는** 표현인가.

    `Path("server/vwx") / name`처럼 경로를 **조인**하는 것과 구별한다 — 전자는 스코프가
    "그 시점의 전 모듈"이지만 후자는 조인되는 이름이 정한다. 이 구별이 없으면
    두 모듈만 읽는 스캐너가 전 모듈 스캐너로 오분류되어 규율이 거짓 양성을 낸다.
    """
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
        return False
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
            elif _r17_globs_the_vwx_directory(child):
                # 디렉터리를 **훑는다** — 스코프는 그 시점의 전 모듈이다. 단순히
                # `Path("server/vwx") / name`으로 **조인**하는 것은 전 모듈이 아니다.
                found |= VWX_MODULE_FILES
            elif isinstance(child, ast.Name):
                found |= bindings.get(child.id, frozenset())
        return frozenset(found)

    targets: list[tuple[str, ast.AST]] = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
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
                elif _r17_globs_the_vwx_directory(node):
                    reached |= VWX_MODULE_FILES
            kind = "self_bound" if reached else "synthetic"
            scanners.append((name, fn.name, kind, tuple(sorted(reached))))
    return tuple(sorted(scanners))


#: 이 절은 **손으로 쓴 등기부를 두지 않는다.** 스코프 대조는 소스에서 전부 파생하므로
#: 새 스캐너는 자동으로 규율에 들어오고, 지울 행 자체가 없어 조용한 축소가 불가능하다.
#: (round17 #8·#9·#10이 전부 "표는 있는데 행삭제 게이트가 없다"였다 — 표를 없애는 쪽이 낫다.)


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
