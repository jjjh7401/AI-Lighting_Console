"""M5 — 실행 전달(사람) · 검증 인계.

AC-AUTOPATCH-015 (사람 실행 전달 · 서버 자동 발화 0건) ·
AC-AUTOPATCH-017 (별도 배포 경로 신설 0건) ·
AC-AUTOPATCH-018 (`execution_port` 직접 호출 0) ·
AC-AUTOPATCH-019 (승인 없는 쓰기 0 · 드라이런 무쓰기 · 승격·재시도 0).

**0건 주장을 어떻게 비공허하게 만드는가** (`design.md` §6.3 · `acceptance.md` §F 항목 7).
`server/vwx/apply.py`는 포트를 인자로 받지 않는다 — 그래서 "기록기에 0건"을 그냥 주장하면
기록기가 애초에 아무것도 볼 수 없는 자리에 놓였을 뿐일 수 있다. 그 공허함을 닫기 위해
이 파일은 **모듈 소스를 실제로 실행하는 하네스**를 쓴다:

  1. `server.bridge`를 기록기(`RecordingExecutionPort` · `RecordingDeployPipeline`)를 담은
     가짜 모듈로 `sys.modules`에 꽂는다 — vwx 코드가 콘솔로 말하려면 반드시 지나야 하는 표면이다
     (`server/tests/test_architecture.py`의 `_FORBIDDEN_MODULE_PREFIXES`가 그 표면을 봉인한다).
  2. **같은 하네스·같은 기록기·같은 진입점**으로 두 소스를 돌린다 — 원본과, 발화·쓰기·우회 배포를
     되살려 심은 **사본**.
  3. 사본에서 기록기가 **실제로 잡는 것**을 보인 뒤에만 원본의 0건을 인수한다.

`server/tests/test_prechk_tool.py`의 `RecordingExecutionPort` 관례와 AST 스캔 관례
(`test_prechk_tool.py:326-344`)를 계승한다.
"""

from __future__ import annotations

import ast
import inspect
import re
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import pytest

from server.vwx.apply import (  # noqa: I001
    END_TO_END_UNVERIFIED,
    HANDOFF_STATUS_DELIVERED,
    HANDOFF_STATUS_DRY_RUN,
    HUMAN_EXECUTION_PROCEDURE,
    NEXT_STEP_HUMAN_EXECUTION,
    NEXT_STEP_REVIEW,
    PLUGIN_EXIT_IS_NOT_SUCCESS,
    _rejected_field,
    build_patch_handoff,
)
from server.vwx.luagen import LuaPatchEntry
from server.vwx.patchplan import (
    IRREVERSIBLE_WARNING,
    AddressPlan,
    AddressPlanEntry,
    PatchCandidate,
    PatchTargetExclusion,
)
from server.vwx.typemap import LibraryMode, LibraryType, TypeRequest, TypeResolution
from server.vwx.verdicts import (
    ADDRESS_ALREADY_OCCUPIED,
    FID_NOT_ASSIGNED,
    FIXTURE_NAME_MISSING,
    LUA_GENERATION_REFUSED,
    TARGET_EXCLUSION_REASON,
    TYPE_CONFIRMATION_PENDING,
    TYPE_NEEDS_CONFIRMATION,
    TYPE_RESOLVED,
    target_exclusion_label,
)

APPLY_PATH = Path("server/vwx/apply.py")
APPLY_SOURCE = APPLY_PATH.read_text(encoding="utf-8")


def _discover_modules(root: Path) -> tuple[Path, ...]:
    """봉인 스캔 대상을 **재귀로** 모은다.

    [round15 B] 이전 판은 평면 `glob('*.py')`이라 `server/vwx/` **바로 아래**만 봤다.
    하위 패키지(`server/vwx/console/…`)가 하나 생기는 순간 그 파일들이 스캔에서 조용히
    빠져나가고, 아래 AC-018 전수 주장이 "스캔한 것 중에는 없다"로 축소된다.
    함수로 뽑아 둔 것은 재귀성 자체에 대조군을 붙이기 위해서다
    (`test_the_seal_scan_discovery_is_recursive`).
    """
    return tuple(sorted(root.rglob("*.py")))


VWX_MODULES = _discover_modules(Path("server/vwx"))

# `CD`/`ChangeDestination` 스캐너 — M4(`test_autopatch_lua.py:47`)와 같은 정규식.
# 전달물(Lua 소스 + 실행 절차 문구)도 콘솔로 갈 산출물이므로 같은 규율을 받는다.
CD_TOKEN = re.compile(r"ChangeDestination|(?<![A-Za-z])CD(?![A-Za-z])")


# --------------------------------------------------------------------------
# 기록기 — `server/tests/test_prechk_tool.py:118-127` 관례 계승
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class _ExecutionResult:
    ok: bool = True
    detail: str = ""


class RecordingExecutionPort:
    """콘솔로 나가려는 문장을 전수 기록한다 — 그 외에는 아무것도 하지 않는다."""

    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, command: str) -> _ExecutionResult:
        self.executed.append(command)
        return _ExecutionResult()


class RecordingDeployPipeline:
    """배포 호출을 전수 기록한다."""

    def __init__(self) -> None:
        self.deployed: list[tuple[str, str]] = []

    def deploy(self, name: str, source: str) -> _ExecutionResult:
        self.deployed.append((name, source))
        return _ExecutionResult()


@contextmanager
def _console_surface(
    port: RecordingExecutionPort, pipeline: RecordingDeployPipeline
) -> Iterator[None]:
    """`server.bridge`를 기록기로 대체한다 — vwx가 콘솔에 닿을 유일한 표면."""
    fake = ModuleType("server.bridge")
    fake.execution_port = port  # type: ignore[attr-defined]
    fake.deploy_pipeline = pipeline  # type: ignore[attr-defined]
    saved = sys.modules.get("server.bridge")
    sys.modules["server.bridge"] = fake
    try:
        yield
    finally:
        if saved is None:
            del sys.modules["server.bridge"]
        else:
            sys.modules["server.bridge"] = saved


_UNDER_TEST = "server.vwx._apply_under_test"


def _load(source: str) -> dict[str, object]:
    """모듈 소스를 **진짜 모듈로** 적재한다 — `dataclass`가 `sys.modules` 조회를 하므로
    네임스페이스 dict만으로는 원본조차 적재되지 않는다."""
    module = ModuleType(_UNDER_TEST)
    module.__file__ = str(APPLY_PATH)
    saved = sys.modules.get(_UNDER_TEST)
    sys.modules[_UNDER_TEST] = module
    try:
        exec(compile(source, str(APPLY_PATH), "exec"), module.__dict__)
    finally:
        if saved is None:
            del sys.modules[_UNDER_TEST]
        else:
            sys.modules[_UNDER_TEST] = saved
    return module.__dict__


def _run(source: str, *, port, pipeline, **call_kwargs):
    """모듈 소스를 실행해 진입점을 부른다 — 원본과 사본에 **똑같이** 쓴다."""
    with _console_surface(port, pipeline):
        namespace = _load(source)
        entry_point = namespace["build_patch_handoff"]
        return entry_point(**{**_handoff_kwargs(), **call_kwargs}), namespace


# --------------------------------------------------------------------------
# 입력 더블
# --------------------------------------------------------------------------

CONSOLE_TYPE = "Robin LEDBeam 350"
CONSOLE_MODE = "Mode 1"


def _candidate(
    *,
    candidate_id: str,
    universe: int = 1,
    address: int = 1,
    fid: int | None = 101,
) -> PatchCandidate:
    return PatchCandidate(
        id=candidate_id,
        unit_number=None,
        instrument_type=CONSOLE_TYPE,
        universe=universe,
        address=address,
        detail="",
        address_basis="universe_address_direct",
        source_index=0,
        assigned_fid=fid,
    )


def _resolution(
    *,
    candidate_id: str,
    status: str = TYPE_RESOLVED,
    console_type: str | None = CONSOLE_TYPE,
    console_mode: str | None = CONSOLE_MODE,
) -> TypeResolution:
    return TypeResolution(
        request=TypeRequest(candidate_id=candidate_id, instrument_type=CONSOLE_TYPE),
        status=status,
        reason="",
        console_type=(None if console_type is None else LibraryType(index=1, name=console_type)),
        console_mode=(None if console_mode is None else LibraryMode(index=1, name=console_mode)),
    )


def _planned(*, candidate_id: str, universe: int = 1, address: int = 1) -> AddressPlanEntry:
    return AddressPlanEntry(
        candidate_id=candidate_id,
        universe=universe,
        address=address,
        footprint=16,
        end_address=address + 15,
    )


def _handoff_kwargs(**overrides):
    base = {
        "targets": (_candidate(candidate_id="a"),),
        "address_plan": AddressPlan(entries=(_planned(candidate_id="a"),)),
        "resolutions": (_resolution(candidate_id="a"),),
        "names": {"a": "LEDBeam 101"},
    }
    base.update(overrides)
    return base


def _handoff(**overrides):
    return build_patch_handoff(**_handoff_kwargs(**overrides))


# --------------------------------------------------------------------------
# [round15 D] AC-014① CD 게이트의 **겨냥 지점**
#
# 이전 판은 `repr(handoff.to_dict())` **전체**를 훑었다. 그래서 계획 주소를 점유한 콘솔
# 픽스처의 `FixtureType` 표시 문자열이 `'CD 5'`이기만 해도 전달물 전체가 위반으로 찍혔다
# (안전 감사 실측 · 재현은 `test_autopatch_verify.py`의
# `test_a_console_display_string_carrying_cd_is_not_a_gate_violation`). 절단·미확정은 이
# 콘솔의 기본 경로라 그런 거짓 양성이 흔하고, 흔한 거짓 양성은 게이트의 강제력을 없앤다.
#
# CD 금지의 실제 대상은 **사람이 콘솔에 입력하거나 그대로 따라 실행할 텍스트**다. 그래서
# payload 키를 두 축으로 **표로 분류**하고, 게이트는 콘솔로 나가는 축만 훑는다. 제외
# 진단문은 콘솔에서 실행되지 않으므로 게이트 밖이며, 그쪽은 §0 2b④(거부된 입력을 사유
# 문장에 되싣지 않는다)가 별도 단정으로 지킨다.
# --------------------------------------------------------------------------

#: 콘솔로 나가는 축. `entries`가 여기 있는 이유는 이름·타입·모드가 **그대로 Lua에 박히기**
#: 때문이다 — 그래서 `lua_source`와 같은 규율을 받는다.
_CONSOLE_BOUND_HANDOFF_KEYS = ("lua_source", "next_step", "procedure", "warnings", "entries")

#: 콘솔에서 실행되지 않는 축 — 상태·진단 보고. 새 키가 생기면 어느 쪽인지 **정해야** 하고,
#: 정하지 않으면 `test_every_handoff_payload_key_is_classified_console_bound_or_diagnostic`이
#: 실패한다(HARD 규율 1 — 형제 축을 표로 열거).
_DIAGNOSTIC_HANDOFF_KEYS = (
    "ok",
    "dry_run",
    "delivered",
    "status",
    "execution_performed_by",
    "exclusions",
)


def _console_bound_text(handoff) -> str:
    """전달물에서 **콘솔로 나가는 축만** 문자열로 모은다 — CD 게이트가 훑는 표면."""
    payload = handoff.to_dict()
    return repr({key: payload[key] for key in _CONSOLE_BOUND_HANDOFF_KEYS})


def test_every_handoff_payload_key_is_classified_console_bound_or_diagnostic():
    """[round15 D] `to_dict()`에 키가 하나 생기면 분류를 **정하지 않고는** 통과하지 못한다.

    좁힌 게이트가 조용히 새는 방식은 하나뿐이다 — 콘솔로 나가는 새 축이 어느 표에도 없는 것.
    """
    payload = _handoff(dry_run=False).to_dict()
    assert set(_CONSOLE_BOUND_HANDOFF_KEYS).isdisjoint(_DIAGNOSTIC_HANDOFF_KEYS)
    assert set(_CONSOLE_BOUND_HANDOFF_KEYS) | set(_DIAGNOSTIC_HANDOFF_KEYS) == set(payload)


# --------------------------------------------------------------------------
# AC-AUTOPATCH-015① — 검토 가능한 Lua 소스와 실행 절차가 전달물에 담긴다
# --------------------------------------------------------------------------


def test_delivery_carries_the_reviewable_lua_source_and_the_execution_procedure():
    handoff = _handoff(dry_run=False)
    assert handoff.delivered is True
    assert handoff.status == HANDOFF_STATUS_DELIVERED
    assert "AddFixtures({" in (handoff.lua_source or "")
    assert 'fid = "101"' in (handoff.lua_source or "")
    assert handoff.procedure == HUMAN_EXECUTION_PROCEDURE
    assert handoff.next_step == NEXT_STEP_HUMAN_EXECUTION


def test_the_procedure_names_the_only_deployment_path_this_build_supports():
    """§0 항목 4·9 실측 — `deploy` 동사는 소스를 쓰지 못하고, 재임포트는 캐싱된다."""
    procedure = "\n".join(HUMAN_EXECUTION_PROCEDURE)
    assert "Import Plugin" in procedure
    assert "재임포트" in procedure
    assert "사람이 실행한다" in procedure


def test_the_delivery_warns_that_a_clean_plugin_exit_is_not_success():
    handoff = _handoff(dry_run=False)
    assert PLUGIN_EXIT_IS_NOT_SUCCESS in handoff.warnings
    assert IRREVERSIBLE_WARNING in handoff.warnings
    assert END_TO_END_UNVERIFIED in handoff.warnings


# 반증된 처방 계열 전체 — 한 문구만 막으면 같은 조언을 다르게 적어 통과한다(round11 M5 N04).
REFUTED_REMEDY_TOKENS = ("편집기", "편집 세션", "Patch 화면", "Fixtures 뷰", "목적지")


def test_the_delivery_does_not_repeat_the_refuted_patch_editor_remedy():
    """REQ-AUTOPATCH-024 [v0.1.3] — 반증된 원인을 사용자에게 안내하지 않는다."""
    text = "\n".join((*HUMAN_EXECUTION_PROCEDURE, *_handoff(dry_run=False).warnings))
    assert [token for token in REFUTED_REMEDY_TOKENS if token in text] == []
    assert CD_TOKEN.search(text) is None


def test_the_refuted_remedy_guard_is_not_vacuous():
    planted = "1. Patch > Fixtures 편집기를 먼저 열어라."
    assert [token for token in REFUTED_REMEDY_TOKENS if token in planted] == ["편집기"]


def test_the_console_bound_surface_carries_no_destination_token():
    """AC-014① — 사람이 콘솔에 입력할 텍스트에 반증된 `CD` 어휘가 0건.

    [round15 D] 이전 이름은 `..._payload_...`였고 `repr(to_dict())` 전체를 훑었다. 그 훑기는
    관측 데이터(점유 픽스처의 표시 문자열)에도 반응해 거짓 양성을 냈다 — 좁힌 이유가 그것이다.
    좁힌 것이 약화가 아님은 아래 표면별 대조군 5건이 보증한다.
    """
    assert CD_TOKEN.search(_console_bound_text(_handoff(dry_run=False))) is None


# --------------------------------------------------------------------------
# AC-AUTOPATCH-015②③ — 패치 실행 발화 0건 (승인 여부와 무관)
# --------------------------------------------------------------------------

_PLANT_EXECUTION = """

_delivered_by_server = build_patch_handoff


def build_patch_handoff(*args, **kwargs):
    from server.bridge import execution_port

    handoff = _delivered_by_server(*args, **kwargs)
    execution_port.execute("Plugin 'VWX AddFixtures'")
    return handoff
"""

_PLANT_CONSOLE_WRITE = """

_written_by_server = build_patch_handoff


def build_patch_handoff(*args, **kwargs):
    from server.bridge import execution_port

    execution_port.execute("Store Fixture 101")
    return _written_by_server(*args, **kwargs)
"""

_PLANT_BYPASS_DEPLOY = """

_deployed_by_server = build_patch_handoff


def build_patch_handoff(*args, **kwargs):
    from server.bridge import deploy_pipeline

    handoff = _deployed_by_server(*args, **kwargs)
    deploy_pipeline.deploy("VWX AddFixtures", handoff.lua_source or "")
    return handoff
"""


@pytest.mark.parametrize("dry_run", [True, False])
def test_no_patch_execution_utterance_reaches_the_recorder(dry_run):
    """AC-015②③ — 승인(`dry_run=false`)이 있어도 서버는 실행을 대행하지 않는다."""
    port, pipeline = RecordingExecutionPort(), RecordingDeployPipeline()
    handoff, _ = _run(APPLY_SOURCE, port=port, pipeline=pipeline, dry_run=dry_run)
    assert handoff is not None
    assert port.executed == []
    assert [command for command in port.executed if command.startswith("Plugin ")] == []


def test_execution_utterance_control_is_caught():
    """AC-015② 비공허성 — 발화를 되살린 **사본**에서 같은 기록기가 실제로 잡는다."""
    port, pipeline = RecordingExecutionPort(), RecordingDeployPipeline()
    _run(APPLY_SOURCE + _PLANT_EXECUTION, port=port, pipeline=pipeline, dry_run=False)
    assert port.executed == ["Plugin 'VWX AddFixtures'"]


def test_the_delivery_names_the_human_as_the_executor():
    payload = _handoff(dry_run=False).to_dict()
    assert payload["execution_performed_by"] == "human"


# --------------------------------------------------------------------------
# AC-AUTOPATCH-017 — 별도 배포 경로 신설 0건
# --------------------------------------------------------------------------


@pytest.mark.parametrize("dry_run", [True, False])
def test_no_deploy_call_leaves_the_module(dry_run):
    """AC-017①③ — 배포 호출 0건이므로 "기존 파이프라인만 경유"가 자동 충족된다."""
    port, pipeline = RecordingExecutionPort(), RecordingDeployPipeline()
    _run(APPLY_SOURCE, port=port, pipeline=pipeline, dry_run=dry_run)
    assert pipeline.deployed == []


def test_bypass_deploy_control_is_caught():
    """AC-017① 비공허성 — 우회 배포를 심은 사본에서 기록기가 실제로 잡는다."""
    port, pipeline = RecordingExecutionPort(), RecordingDeployPipeline()
    _run(APPLY_SOURCE + _PLANT_BYPASS_DEPLOY, port=port, pipeline=pipeline, dry_run=False)
    assert [name for name, _ in pipeline.deployed] == ["VWX AddFixtures"]


def test_the_entry_point_takes_no_review_bypassing_argument():
    """AC-017② — 컴파일 검사·정적 스캔·사람 리뷰를 우회하는 인자가 0건."""
    parameters = set(inspect.signature(build_patch_handoff).parameters)
    assert parameters == {"targets", "address_plan", "resolutions", "names", "dry_run"}


def test_bypass_argument_control_is_caught():
    """AC-017② 비공허성 — 우회 인자를 심은 사본에서 위 단정이 실제로 실패한다."""
    planted = APPLY_SOURCE.replace(
        "    dry_run: bool = True,",
        "    dry_run: bool = True,\n    skip_review: bool = False,",
        1,
    )
    assert planted != APPLY_SOURCE
    namespace = _load(planted)
    parameters = set(inspect.signature(namespace["build_patch_handoff"]).parameters)
    assert "skip_review" in parameters


# --------------------------------------------------------------------------
# AC-AUTOPATCH-018 — `execution_port` 직접 호출 0 · 콘솔 표면 import 0
# --------------------------------------------------------------------------


def _attribute_names(source: str) -> set[str]:
    """**점 표기 체인 전체**의 이름을 모은다 — bare name도, 중간 속성도 포함.

    [round11 M5 N02] 이전 판은 `Attribute.value`가 bare `Name`일 때 그 `id`만 모았다.
    그래서 `execution_port.execute(...)`는 잡았지만 프로덕션의 실제 호출 형태인
    `gate.execution_port.execute(...)` · `self._gate.execution_port.execute(...)`는
    **전부 놓쳤다** — 스캐너가 자기가 볼 수 있는 형태로만 시험되고 있었다.
    """
    tree = ast.parse(source)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.Name):
            names.add(node.id)
    return names


# `server/vwx/**`가 콘솔로 나가려면 반드시 이 이름들 중 하나를 거쳐야 한다.
_CONSOLE_WARD_NAMES = frozenset({"execution_port", "deploy_pipeline", "ConsoleLink", "OscBridge"})


@pytest.mark.parametrize("module", VWX_MODULES, ids=lambda path: path.name)
def test_no_vwx_module_reaches_the_execution_port(module: Path):
    """AC-018① — `server/vwx/` 전수에서 콘솔 발화 표면 참조 0건(점 표기 포함)."""
    assert VWX_MODULES, "스캔 대상이 0개면 이 확인은 공허하다"
    source = module.read_text(encoding="utf-8")
    assert _CONSOLE_WARD_NAMES & _attribute_names(source) == set()


@pytest.mark.parametrize(
    "plant",
    [
        "def _planted(execution_port):\n    execution_port.execute('x')\n",
        "def _planted(gate):\n    gate.execution_port.execute('x')\n",
        "class _P:\n    def go(self):\n        self._gate.execution_port.execute('x')\n",
        "def _planted(build):\n    build().deploy_pipeline.deploy('n', 's')\n",
    ],
    ids=["bare", "through_gate", "through_self", "through_call"],
)
def test_execution_port_scanner_control_is_caught(plant):
    """AC-018② 비공허성 — **프로덕션 호출 형태를 포함해** 심으면 스캐너가 잡는다."""
    assert _CONSOLE_WARD_NAMES & _attribute_names(APPLY_SOURCE + "\n\n" + plant)


def _module_package(path: Path) -> str:
    """파일 경로에서 그 모듈이 속한 **패키지 점 표기**를 만든다 — 상대 import 복원에 쓴다."""
    return ".".join(path.parent.parts)


# 모듈명을 **문자열로** 받는 동적 import 호출. `importlib.import_module(...)` 같은 점 표기와
# `from importlib import import_module` 뒤의 bare 호출을 모두 잡는다.
_DYNAMIC_IMPORT_CALLEES = frozenset({"import_module", "__import__"})


def _imported_modules(source: str, *, package: str = "server.vwx") -> set[str]:
    """소스가 **import로 도달하는 모듈 이름**을 전부 모은다.

    [round15 B] 이전 판은 `ast.Import`의 `alias.name`과 `ast.ImportFrom`의 `node.module`
    **문자열만** 보고 접두사 대조했다. 적대 감사가 그 두 가드를 모두 통과하는 5형태를
    실측했다 — 아래 표가 그 형태고, `_CONSOLE_IMPORT_PLANTS`가 전부에 대조군을 붙인다:

      1. `from ..bridge import osc`         — `node.module`이 `'bridge'`(접두사 불일치)
      2. `from ..safety.gate import Gate`   — `node.module`이 `'safety.gate'`
      3. `from server import safety`        — 금지 이름이 `node.module`이 아니라 **alias**에
      4. `importlib.import_module("server.bridge")` — 모듈명이 **상수 문자열 인자**다
      5. `__import__("server.safety")`              — 같은 이유

    그래서 (a) `node.level > 0`이면 `package`를 기준으로 절대명을 **복원**하고,
    (b) `ImportFrom`의 alias 이름을 모듈명에 **이어 붙인 형태도 함께** 싣고,
    (c) 동적 import 호출의 **상수 문자열 인자**를 수집한다.
    """
    tree = ast.parse(source)
    names: set[str] = set()
    parts = package.split(".") if package else []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            # `from . import x`는 자기 패키지, `from .. import x`는 그 부모를 기준으로 한다.
            anchor = ".".join(parts[: len(parts) - (node.level - 1)]) if node.level else ""
            base = ".".join(part for part in (anchor, node.module or "") if part)
            if base:
                names.add(base)
                names.update(f"{base}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Call):
            callee = node.func
            if isinstance(callee, ast.Attribute):
                callee_name = callee.attr
            elif isinstance(callee, ast.Name):
                callee_name = callee.id
            else:
                callee_name = None
            if callee_name in _DYNAMIC_IMPORT_CALLEES:
                names.update(
                    argument.value
                    for argument in node.args
                    if isinstance(argument, ast.Constant) and isinstance(argument.value, str)
                )
    return names


# `server.bridge`/`pythonosc`만 막으면 봉인이 완결되지 않는다 — 실제 콘솔 도달 경로는
# vwx → `server.safety.gate` → `server.safety.console` → `server.bridge`이고, 그 첫 칸은
# `test_architecture.py`의 금지 목록에 없다(round11 M5 N01). 그래서 **여기서 막는다**:
# `server/vwx/**`는 안전 게이트도 import하지 않는다. 포트가 필요하면 프로토콜을 인자로 받는다
# (`patchplan.FidPropertyPort`·`typemap.LibraryPort` 선례).
_CONSOLE_WARD_MODULES = ("server.bridge", "pythonosc", "server.safety")


def _console_ward_offenders(source: str, *, package: str = "server.vwx") -> list[str]:
    """봉인에 걸리는 import 이름을 **정렬·중복제거해** 돌려준다."""
    return sorted(
        {
            name
            for name in _imported_modules(source, package=package)
            if name.startswith(_CONSOLE_WARD_MODULES)
        }
    )


@pytest.mark.parametrize("module", VWX_MODULES, ids=lambda path: str(path))
def test_no_vwx_module_imports_the_console_send_surface(module: Path):
    """AC-018③ — 콘솔 발화로 이어지는 모듈 import 0건.

    게이트 경유·상대 import·`from server import safety`·동적 import까지 전부 본다
    (`_imported_modules` 독스트링의 5형태). 스캔 대상은 재귀로 모은다.
    """
    assert VWX_MODULES, "스캔 대상이 0개면 이 확인은 공허하다"
    offenders = _console_ward_offenders(
        module.read_text(encoding="utf-8"), package=_module_package(module)
    )
    assert offenders == []


def test_the_seal_scan_discovery_is_recursive(tmp_path: Path):
    """[round15 B] `rglob`을 평면 `glob('*.py')`으로 되돌리면 이 단정이 실패한다.

    같은 발견 표현식을 합성 트리에 적용해 **재귀성 자체**를 본다 — 저장소에 아직 하위
    패키지가 없어서 실물로는 그 회귀가 보이지 않기 때문이다.
    """
    (tmp_path / "console").mkdir()
    (tmp_path / "top.py").write_text("", encoding="utf-8")
    nested = tmp_path / "console" / "link.py"
    nested.write_text("", encoding="utf-8")
    assert set(_discover_modules(tmp_path)) == {tmp_path / "top.py", nested}


# 심는 대조군 — **봉인을 우회하는 형태를 표로 열거**한다(HARD 규율 1: 형제 축을 표로).
# 앞 3형태는 이전 판(절대 import)이고, 뒤 5형태는 적대 감사가 실측한 우회로다.
# `expected`는 그 소스에서 스캐너가 내야 하는 **정렬된 위반 이름 전부**다 — 앞 3형태의
# 기대값이 넓어진 것은 alias 이어붙이기가 추가됐기 때문이며, 약화가 아니라 강화다.
_CONSOLE_IMPORT_PLANTS = (
    (
        "absolute_bridge",
        "from server.bridge import osc  # noqa: F401",
        ("server.bridge", "server.bridge.osc"),
    ),
    (
        "absolute_safety_gate",
        "from server.safety.gate import SafetyGate  # noqa: F401",
        ("server.safety.gate", "server.safety.gate.SafetyGate"),
    ),
    ("absolute_pythonosc", "import pythonosc  # noqa: F401", ("pythonosc",)),
    (
        "relative_bridge",
        "from ..bridge import osc  # noqa: F401",
        ("server.bridge", "server.bridge.osc"),
    ),
    (
        "relative_safety_gate",
        "from ..safety.gate import SafetyGate  # noqa: F401",
        ("server.safety.gate", "server.safety.gate.SafetyGate"),
    ),
    ("alias_is_the_submodule", "from server import safety  # noqa: F401", ("server.safety",)),
    (
        "importlib_string_argument",
        'import importlib\n\n_gate = importlib.import_module("server.bridge")',
        ("server.bridge",),
    ),
    (
        "dunder_import_string_argument",
        '_gate = getattr(__import__("server.safety"), "gate")',
        ("server.safety",),
    ),
)


@pytest.mark.parametrize(
    "plant,expected",
    [(plant, expected) for _, plant, expected in _CONSOLE_IMPORT_PLANTS],
    ids=[name for name, _, _ in _CONSOLE_IMPORT_PLANTS],
)
def test_console_import_scanner_control_is_caught(plant, expected):
    """AC-018③ 비공허성 — **8형태 전부** 심은 사본에서 스캐너가 실제로 잡는다.

    [round15 B] 뒤 5형태는 이전 스캐너를 **그대로 통과했다**(실측). 어느 형태의 수집을
    되돌려도 그 행이 빈 목록을 받아 실패한다.
    """
    assert _console_ward_offenders(APPLY_SOURCE + "\n\n" + plant + "\n") == sorted(expected)


def test_the_console_import_scanner_reports_nothing_without_a_plant():
    """대조군의 대조군 — 심지 않은 프로덕션 소스에서는 같은 스캐너가 0건이다.

    이것이 없으면 위 8행이 "원래부터 걸려 있던 것"을 보고 통과할 수 있다.
    """
    assert _console_ward_offenders(APPLY_SOURCE, package=_module_package(APPLY_PATH)) == []


# --------------------------------------------------------------------------
# AC-AUTOPATCH-019 — 승인 없는 쓰기 0 · 드라이런 무쓰기 · 승격·재시도 0
# --------------------------------------------------------------------------


@pytest.mark.parametrize("dry_run", [True, False])
def test_neither_mode_writes_to_the_console(dry_run):
    """AC-019① — 드라이런과 전달 요청 **양쪽 모두** 쓰기 0건."""
    port, pipeline = RecordingExecutionPort(), RecordingDeployPipeline()
    _run(APPLY_SOURCE, port=port, pipeline=pipeline, dry_run=dry_run)
    assert port.executed == []
    assert pipeline.deployed == []


def test_console_write_control_is_caught():
    """AC-019② 비공허성 — 쓰기를 되살려 심은 사본을 같은 기록기가 실제로 잡는다."""
    port, pipeline = RecordingExecutionPort(), RecordingDeployPipeline()
    _run(APPLY_SOURCE + _PLANT_CONSOLE_WRITE, port=port, pipeline=pipeline, dry_run=True)
    assert port.executed == ["Store Fixture 101"]


def test_dry_run_defaults_to_true():
    """AC-019③ — 기본값이 실행인 인자가 없다."""
    assert inspect.signature(build_patch_handoff).parameters["dry_run"].default is True
    assert _handoff().dry_run is True


def test_dry_run_default_control_is_caught():
    """AC-019③ 비공허성 — 기본값을 false로 바꾼 사본에서 이 단정이 실제로 실패한다."""
    planted = APPLY_SOURCE.replace("    dry_run: bool = True,", "    dry_run: bool = False,", 1)
    assert planted != APPLY_SOURCE
    namespace = _load(planted)
    assert (
        inspect.signature(namespace["build_patch_handoff"]).parameters["dry_run"].default is False
    )


def test_a_dry_run_does_not_promote_itself_into_a_delivery():
    """AC-019④ — 한 호출 안에서 `dry_run=true`가 전달 경로로 흘러가지 않는다."""
    handoff = _handoff()
    assert handoff.delivered is False
    assert handoff.status == HANDOFF_STATUS_DRY_RUN
    assert handoff.procedure == ()
    assert handoff.next_step == NEXT_STEP_REVIEW


def test_the_dry_run_still_shows_the_full_lua_source():
    """REQ-AUTOPATCH-003 · AC-AUTOPATCH-004② — 드라이런은 소스 전문을 낸다."""
    handoff = _handoff()
    assert handoff.lua_source == _handoff(dry_run=False).lua_source
    assert "AddFixtures({" in (handoff.lua_source or "")


def test_promotion_control_is_caught():
    """AC-019④ 비공허성 — 승격 경로를 심은 사본에서 이 단정이 실제로 실패한다."""
    planted = APPLY_SOURCE.replace("    delivered = not dry_run", "    delivered = True", 1)
    assert planted != APPLY_SOURCE
    namespace = _load(planted)
    handoff = namespace["build_patch_handoff"](**_handoff_kwargs(dry_run=True))
    assert handoff.delivered is True


def _counting_namespace(source: str, **call_kwargs):
    namespace = _load(source)
    calls: list[int] = []
    render = namespace["render_addfixtures_plugin"]

    def counted(entries):
        calls.append(1)
        return render(entries)

    namespace["render_addfixtures_plugin"] = counted
    namespace["build_patch_handoff"](**_handoff_kwargs(**call_kwargs))
    return len(calls)


def test_no_automatic_retry_repeats_the_delivery():
    """AC-019⑤ — 한 호출은 전달을 정확히 한 번 만든다."""
    assert _counting_namespace(APPLY_SOURCE, dry_run=False) == 1


def test_automatic_retry_control_is_caught():
    """AC-019⑤ 비공허성 — 자동 재시도를 심은 사본에서 이 단정이 실제로 실패한다."""
    planted = (
        APPLY_SOURCE
        + """

_once = build_patch_handoff


def build_patch_handoff(*args, **kwargs):
    handoff = _once(*args, **kwargs)
    return _once(*args, **kwargs) if handoff.delivered else handoff
"""
    )
    assert _counting_namespace(planted, dry_run=False) == 2


# --------------------------------------------------------------------------
# 항목 제외 + 사유 보고 — M4가 남긴 계약 ②
# --------------------------------------------------------------------------


@pytest.mark.parametrize("hostile", ["ChangeDestination", "CD", "rig CD spare"])
def test_a_name_carrying_the_destination_token_is_excluded_with_a_reason(hostile):
    """M4 계약 ② — `LuaGenerationError`를 잡아 **항목 제외 + 사유 보고**로 처리한다."""
    handoff = _handoff(names={"a": hostile}, dry_run=False)
    assert handoff.entries == ()
    assert handoff.lua_source is None
    codes = [exclusion.code for exclusion in handoff.exclusions]
    assert codes == [LUA_GENERATION_REFUSED]
    assert handoff.exclusions[0].candidate_id == "a"


def test_the_refused_name_is_not_silently_repaired():
    """조용히 고치지 않는다 — 콘솔로 나가는 축에 그 항목이 어떤 형태로도 남지 않는다.

    [round15 D] 훑는 표면을 `_console_bound_text`로 좁혔다. 거부된 **값**이 진단문에도
    남지 않는다는 §0 2b④ 규율은 `test_the_refusal_reason_still_does_not_echo_the_rejected_value`
    가 따로 지킨다 — 한 단정에 두 규율을 겹쳐 놓으면 어느 쪽이 깨졌는지 알 수 없다.
    """
    handoff = _handoff(names={"a": "CD spare"}, dry_run=False)
    assert CD_TOKEN.search(_console_bound_text(handoff)) is None
    assert "CD spare" not in _console_bound_text(handoff)
    assert "a" not in {entry.candidate_id for entry in handoff.entries}


def test_refusal_control_a_clean_name_survives():
    """위 제외가 공허하지 않다 — 정상 이름은 전달물에 남는다."""
    handoff = _handoff(dry_run=False)
    assert [entry.candidate_id for entry in handoff.entries] == ["a"]
    assert handoff.exclusions == ()


def test_a_missing_name_is_excluded_rather_than_invented():
    handoff = _handoff(names={}, dry_run=False)
    assert [exclusion.code for exclusion in handoff.exclusions] == [FIXTURE_NAME_MISSING]
    assert handoff.entries == ()


def test_a_target_without_an_assigned_fid_is_excluded():
    handoff = _handoff(targets=(_candidate(candidate_id="a", fid=None),), dry_run=False)
    assert [exclusion.code for exclusion in handoff.exclusions] == [FID_NOT_ASSIGNED]


def test_an_unconfirmed_type_match_is_excluded():
    """R2 — 사용자 확인이 남은 타입 매칭으로는 되돌릴 수 없는 쓰기를 만들지 않는다."""
    handoff = _handoff(
        resolutions=(_resolution(candidate_id="a", status=TYPE_NEEDS_CONFIRMATION),),
        dry_run=False,
    )
    assert [exclusion.code for exclusion in handoff.exclusions] == [TYPE_CONFIRMATION_PENDING]


def test_address_plan_exclusions_are_carried_through_untouched():
    """설계 슬롯 E — 실패 항목이 있어도 나머지는 진행하고, 건별로 보고한다."""
    upstream = PatchTargetExclusion(
        candidate_id="b", code=ADDRESS_ALREADY_OCCUPIED, reason="콘솔 점유"
    )
    handoff = _handoff(
        targets=(_candidate(candidate_id="a"), _candidate(candidate_id="b", address=100, fid=102)),
        address_plan=AddressPlan(entries=(_planned(candidate_id="a"),), exclusions=(upstream,)),
        resolutions=(_resolution(candidate_id="a"), _resolution(candidate_id="b")),
        names={"a": "LEDBeam 101", "b": "LEDBeam 102"},
        dry_run=False,
    )
    assert [entry.candidate_id for entry in handoff.entries] == ["a"]
    assert [exclusion.code for exclusion in handoff.exclusions] == [ADDRESS_ALREADY_OCCUPIED]
    assert "AddFixtures({" in (handoff.lua_source or "")
    assert handoff.lua_source.count("AddFixtures({") == 1


def test_every_exclusion_code_is_registered_closed_vocabulary():
    for code in (
        LUA_GENERATION_REFUSED,
        FIXTURE_NAME_MISSING,
        FID_NOT_ASSIGNED,
        TYPE_CONFIRMATION_PENDING,
    ):
        assert code in TARGET_EXCLUSION_REASON
        assert target_exclusion_label(code)


def test_an_empty_delivery_reports_no_lua_source():
    handoff = _handoff(
        targets=(), address_plan=AddressPlan(), resolutions=(), names={}, dry_run=False
    )
    assert handoff.lua_source is None
    assert handoff.entries == ()
    assert handoff.delivered is True


def test_a_planned_entry_without_a_target_is_a_caller_error():
    with pytest.raises(ValueError, match="ghost"):
        _handoff(address_plan=AddressPlan(entries=(_planned(candidate_id="ghost"),)))


def test_the_payload_reports_each_entry_with_its_designed_address():
    payload = _handoff(dry_run=False).to_dict()
    assert payload["entries"] == [
        {
            "candidate_id": "a",
            "fid": 101,
            "name": "LEDBeam 101",
            "console_type": CONSOLE_TYPE,
            "console_mode": CONSOLE_MODE,
            "universe": 1,
            "address": 1,
            "footprint": 16,
        }
    ]


def test_the_refusal_reason_names_the_field_that_was_actually_rejected():
    """[round11 M5 N03] 생성기는 이름만 거부하지 않는다 — 원인 필드를 지목해야 재시도가 성립한다.

    이전 판은 어느 필드가 걸렸든 "이름을 고쳐 다시 요청하라"고 적었다. 콘솔 타입·모드는
    라이브러리 열거에서 오지 호출자의 `names`에서 오지 않으므로, 그 안내를 따르면
    사용자는 원인이 아닌 필드를 고치고 재시도는 영원히 실패한다.
    """
    by_name = _handoff(names={"a": "CD spare"}, dry_run=False)
    assert "name 필드를 거부" in by_name.exclusions[0].reason

    by_type = _handoff(
        resolutions=(_resolution(candidate_id="a", console_type="Acme CD 700"),), dry_run=False
    )
    assert by_type.exclusions[0].code == LUA_GENERATION_REFUSED
    assert "console_type 필드를 거부" in by_type.exclusions[0].reason


# §0 2b④ 표 — (호출, 거부된 **값**, 사유가 지목해야 할 필드 이름).
_REJECTED_INPUT_CASES = (
    ("name", {"names": {"a": "CD spare"}}, "CD spare", "name"),
    (
        "console_type",
        {"resolutions": (_resolution(candidate_id="a", console_type="Acme CD 700"),)},
        "Acme CD 700",
        "console_type",
    ),
)


@pytest.mark.parametrize(
    "kwargs,rejected_value,expected_field",
    [(kwargs, value, field) for _, kwargs, value, field in _REJECTED_INPUT_CASES],
    ids=[name for name, _, _, _ in _REJECTED_INPUT_CASES],
)
def test_the_refusal_reason_still_does_not_echo_the_rejected_value(
    kwargs, rejected_value, expected_field
):
    """§0 2b④ — 필드 이름은 말하되 **거부된 값은 문장에 싣지 않는다**(`_rejected_field` 선례).

    [round15 D] 게이트를 콘솔 표면으로 좁힌 뒤 이 규율은 **여기서만** 지켜진다. 그래서
    `repr(to_dict())`에 정규식을 거는 간접 훑기를 버리고 **사유 문장 자체**를 직접 본다 —
    그 간접 훑기는 거부된 값이 아니라 관측 데이터에도 반응하는 것이 실측으로 확인됐다.
    """
    handoff = _handoff(dry_run=False, **kwargs)
    reasons = [exclusion.reason for exclusion in handoff.exclusions]
    assert reasons, "제외가 없으면 이 확인은 공허하다"
    assert [reason for reason in reasons if rejected_value in reason] == []
    assert [reason for reason in reasons if CD_TOKEN.search(reason)] == []
    assert [reason for reason in reasons if f"{expected_field} 필드를 거부" in reason] == reasons


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        ({"names": {"a": "CD spare"}}, "name"),
        (
            {"resolutions": (_resolution(candidate_id="a", console_type="Acme CD 700"),)},
            "console_type",
        ),
    ],
)
def test_the_rejected_field_is_named_for_a_single_offender(kwargs, expected):
    handoff = _handoff(dry_run=False, **kwargs)
    assert f"{expected} 필드를 거부" in handoff.exclusions[0].reason


def test_two_offending_fields_are_both_named_rather_than_blaming_the_integers():
    """[round12 R09] 둘이 동시에 거부되면 이전 판은 전부 무죄로 보고 정수 필드를 지목했다.

    사용자는 멀쩡한 필드를 고치게 되고 재시도는 영원히 실패한다 — round11 N14가
    없애려던 바로 그 실패 양식의 재발이었다.
    """
    handoff = _handoff(
        names={"a": "CD spare"},
        resolutions=(_resolution(candidate_id="a", console_type="Acme CD 700"),),
        dry_run=False,
    )
    reason = handoff.exclusions[0].reason
    assert "name" in reason
    assert "console_type" in reason
    assert "정수" not in reason


def test_an_integer_field_rejection_names_the_integer_field():
    """[round13 S02] 정수 축을 중립화에서 빼면 정수 결함이 문자열 필드로 오귀속된다.

    round11은 한 필드씩 중립화해 둘 이상 거부 시 전부 무죄로 봤고(→ 정수 지목),
    round12는 방향을 뒤집었으나 문자열만 중립화해 정수 결함이 무고한 문자열 셋을 지목했다.
    두 번 다 원인은 "축을 하나 빼놓았다"이다 — 이제 6필드 전부를 중립화한다.
    """
    entry = LuaPatchEntry(
        console_type="Robin LEDBeam 350",
        console_mode="Mode 1",
        fid="7",  # 문자열 — 생성기는 정수를 요구한다
        name="LEDBeam 7",
        universe=1,
        address=1,
    )
    assert _rejected_field(entry) == "fid"


@pytest.mark.parametrize("field", ["fid", "universe", "address"])
def test_each_integer_axis_is_named_individually(field):
    base = {
        "console_type": "Robin LEDBeam 350",
        "console_mode": "Mode 1",
        "fid": 101,
        "name": "LEDBeam 101",
        "universe": 1,
        "address": 1,
    }
    assert _rejected_field(LuaPatchEntry(**{**base, field: "not-an-int"})) == field


def test_a_mixed_string_and_integer_rejection_names_both_axes():
    entry = LuaPatchEntry(
        console_type="Robin LEDBeam 350",
        console_mode="Mode 1",
        fid="7",
        name="CD spare",
        universe=1,
        address=1,
    )
    named = _rejected_field(entry)
    assert "name" in named
    assert "fid" in named


# --------------------------------------------------------------------------
# --- round15 D 콘솔 표면 CD 게이트 비공허성 ---
#
# 게이트를 좁혔으면 **좁힌 자리마다** 심어서 잡히는지 보여야 한다. 대조군 없이 좁히면
# 게이트를 약화시킨 것과 구별되지 않는다. 표면 5개 전부에 프로덕션 사본으로 심는다
# (`test_autopatch_verify.py` 약 463행 · `APPLY_SOURCE` 선례).
# --------------------------------------------------------------------------

_PLANT_CD_IN_LUA_SOURCE = """

_handoff_before_lua_cd_plant = build_patch_handoff


def build_patch_handoff(*args, **kwargs):
    handoff = _handoff_before_lua_cd_plant(*args, **kwargs)
    return replace(handoff, lua_source=(handoff.lua_source or "") + "\\n-- ChangeDestination")
"""

_PLANT_CD_IN_ENTRY_NAME = """

_handoff_before_entry_cd_plant = build_patch_handoff


def build_patch_handoff(*args, **kwargs):
    handoff = _handoff_before_entry_cd_plant(*args, **kwargs)
    return replace(
        handoff, entries=tuple(replace(entry, name="CD spare") for entry in handoff.entries)
    )
"""

_PLANT_CD_IN_NEXT_STEP = """

NEXT_STEP_HUMAN_EXECUTION = NEXT_STEP_HUMAN_EXECUTION + " CD"
"""

_PLANT_CD_IN_PROCEDURE = """

HUMAN_EXECUTION_PROCEDURE = (*HUMAN_EXECUTION_PROCEDURE, "6. CD 로 이동한 뒤 실행한다.")
"""

_ORIGINAL_DELIVERY_WARNINGS = (
    "DELIVERY_WARNINGS = (IRREVERSIBLE_WARNING, PLUGIN_EXIT_IS_NOT_SUCCESS, END_TO_END_UNVERIFIED)"
)


def _apply_source_with_cd_in_warnings() -> str:
    """`warnings`는 dataclass 필드 기본값이라 적재 후 재바인딩이 닿지 않는다 —
    그래서 **소스 치환**으로 심는다."""
    planted = APPLY_SOURCE.replace(
        _ORIGINAL_DELIVERY_WARNINGS,
        _ORIGINAL_DELIVERY_WARNINGS[:-1] + ', "CD 로 옮겨라")',
        1,
    )
    assert planted != APPLY_SOURCE, "DELIVERY_WARNINGS 앵커가 사라졌다"
    return planted


# (표면 이름, 그 표면에만 CD를 심은 프로덕션 사본 소스)
_CD_SURFACE_PLANTS = (
    ("lua_source", APPLY_SOURCE + _PLANT_CD_IN_LUA_SOURCE),
    ("entries", APPLY_SOURCE + _PLANT_CD_IN_ENTRY_NAME),
    ("next_step", APPLY_SOURCE + _PLANT_CD_IN_NEXT_STEP),
    ("procedure", APPLY_SOURCE + _PLANT_CD_IN_PROCEDURE),
    ("warnings", _apply_source_with_cd_in_warnings()),
)


def test_the_cd_surface_plant_table_covers_every_console_bound_key():
    """[round15 D] 콘솔 표면 표에 축을 더하거나 빼면 대조군 표와 어긋나 여기서 걸린다."""
    surfaces = [surface for surface, _ in _CD_SURFACE_PLANTS]
    assert len(surfaces) == len(set(surfaces)) == len(_CONSOLE_BOUND_HANDOFF_KEYS)
    assert set(surfaces) == set(_CONSOLE_BOUND_HANDOFF_KEYS)


@pytest.mark.parametrize(
    "planted",
    [planted for _, planted in _CD_SURFACE_PLANTS],
    ids=[surface for surface, _ in _CD_SURFACE_PLANTS],
)
def test_the_console_bound_cd_gate_catches_a_plant_on_every_surface(planted):
    """AC-014① 비공허성 — 콘솔 표면 **다섯 축 전부**에 심으면 좁힌 게이트가 실제로 잡는다.

    [round15 D] `_CONSOLE_BOUND_HANDOFF_KEYS`에서 축을 하나 빼면 그 행이 잡지 못해 실패한다.
    게이트를 좁힌 것이 약화가 아님을 보증하는 것이 이 표다.
    """
    namespace = _load(planted)
    handoff = namespace["build_patch_handoff"](**_handoff_kwargs(dry_run=False))
    assert CD_TOKEN.search(_console_bound_text(handoff)) is not None


def test_the_console_bound_cd_gate_is_clean_without_a_plant():
    """대조군의 대조군 — 심지 않은 프로덕션 사본에서는 같은 게이트가 0건이다."""
    namespace = _load(APPLY_SOURCE)
    handoff = namespace["build_patch_handoff"](**_handoff_kwargs(dry_run=False))
    assert CD_TOKEN.search(_console_bound_text(handoff)) is None
