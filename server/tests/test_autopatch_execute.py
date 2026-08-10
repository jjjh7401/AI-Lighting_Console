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

from server.tests.test_autopatch_contract import iter_vwx_modules
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
    [round24] 재귀성과 제외 규칙의 정의는 `iter_vwx_modules` 한 자리로 모았다 —
    round15 B의 수정이 형제 아홉 자리로 전파되지 않은 것이 이 SPEC의 서명 형태라,
    같은 표현을 두 벌 두지 않는다.
    """
    return iter_vwx_modules(root)


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
#: [round17 S17-01] `find_spec`을 더했다 — `importlib.util.find_spec("server.bridge")`는
#: 모듈을 해석해 봉인 대상 패키지를 실제로 임포트한다(런타임 확인). 어휘 밖이면 무게이트였다.
_DYNAMIC_IMPORT_CALLEES = frozenset({"import_module", "__import__", "find_spec"})


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

    [round17 S17-01] 그 판도 **`node.args`만** 봤다. 적대 감사가 통과하는 8형태를 더 실증했다:

      6. `importlib.import_module(name="server.bridge")`     — 모듈명이 **키워드 인자**다
      7. `__import__(name="server.safety")`                  — 같은 이유
      8. `importlib.import_module(".gate", package="server.safety")` — 앵커가 키워드에
      9. `importlib.util.find_spec("server.bridge")`         — 호출자 어휘 밖이었다
     10. `importlib.import_module("server" + ".bridge")`     — 인자가 **상수가 아니다**
     11. `importlib.import_module(_NAME)`                    — 이름 바인드 상수
     12. `importlib.import_module(f"server.{_LEAF}")`        — f-string
     13. `importlib.import_module(*_ARGS)`                   — 스타드 인자

    그래서 (a) `node.level > 0`이면 `package`를 기준으로 절대명을 **복원**하고,
    (b) `ImportFrom`의 alias 이름을 모듈명에 **이어 붙인 형태도 함께** 싣고,
    (c) 동적 import 호출의 상수 문자열을 **위치 인자와 키워드 인자 양쪽에서** 수집하며,
    (d) 상수가 아닌 인자는 `_UNREADABLE_DYNAMIC_IMPORT` 표식으로 **그 자체를 위반**으로 올린다.
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
                # [round17 S17-01] **위치 인자와 키워드 인자를 함께** 본다. round16 판은
                # `node.args`만 봤고, 적대 감사가 `import_module(name="server.bridge")` 등
                # 키워드 형태 2종과 `package="server.safety"` 상대 동적 import를 실증했다
                # (런타임 동등성 확인됨).
                arguments = [*node.args, *(keyword.value for keyword in node.keywords)]
                for argument in arguments:
                    if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                        names.add(argument.value)
                    else:
                        # 문자열을 정적으로 못 읽으면 **봉인할 수 없다** — 그 자체가 위반이다.
                        names.add(f"{_UNREADABLE_DYNAMIC_IMPORT}:{type(argument).__name__}")
    return names


# `server.bridge`/`pythonosc`만 막으면 봉인이 완결되지 않는다 — 실제 콘솔 도달 경로는
# vwx → `server.safety.gate` → `server.safety.console` → `server.bridge`이고, 그 첫 칸은
# `test_architecture.py`의 금지 목록에 없다(round11 M5 N01). 그래서 **여기서 막는다**:
# `server/vwx/**`는 안전 게이트도 import하지 않는다. 포트가 필요하면 프로토콜을 인자로 받는다
# (`patchplan.FidPropertyPort`·`typemap.LibraryPort` 선례).
_CONSOLE_WARD_MODULES = ("server.bridge", "pythonosc", "server.safety")

#: [round17 S17-01] 동적 import 인자를 **정적으로 읽을 수 없을 때** 붙는 표식.
#: `importlib.import_module(_NAME)`·`import_module("server" + ".bridge")`·f-string·`*args`는
#: 문자열이 소스에 없으므로 접두사 대조가 원리적으로 불가능하다. 그것 **자체가 위반**이다 —
#: 읽을 수 없는 것은 봉인할 수 없고, 봉인이 성립하지 않는 코드를 통과시키면 게이트가 장식이 된다.
_UNREADABLE_DYNAMIC_IMPORT = "<unreadable-dynamic-import>"

#: 정적으로 읽을 수 없는 인자의 AST 노드 종류 — 적대 감사가 실증한 네 형태.
_UNREADABLE_DYNAMIC_ARGUMENT_KINDS = ("BinOp", "JoinedStr", "Name", "Starred")

_CONSOLE_WARD_OFFENDER_PREFIXES = (*_CONSOLE_WARD_MODULES, _UNREADABLE_DYNAMIC_IMPORT)


def _console_ward_offenders(source: str, *, package: str = "server.vwx") -> list[str]:
    """봉인에 걸리는 import 이름을 **정렬·중복제거해** 돌려준다.

    [round17 S17-01] `_UNREADABLE_DYNAMIC_IMPORT` 표식도 위반으로 센다 — 동적 import의
    모듈명을 정적으로 읽을 수 없으면 **봉인이 성립하지 않기** 때문이다.
    """
    return sorted(
        {
            name
            for name in _imported_modules(source, package=package)
            if name.startswith(_CONSOLE_WARD_OFFENDER_PREFIXES)
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
# 1~3행은 round14 판(절대 import), 4~8행은 round15 적대 감사가 실측한 우회로,
# **9~16행은 round17 S17-01이 실측한 우회로**다 — 키워드 인자 2종 · 상대 동적 import의
# 앵커 키워드 · `find_spec` · 그리고 **정적으로 읽을 수 없는 인자 4형태**.
# `expected`는 그 소스에서 스캐너가 내야 하는 **정렬된 위반 이름 전부**다.
# 9~12행의 런타임 동등성은 실행으로 확인했다(`import_module(name=...)`·`__import__(name=...)`·
# `import_module(".util", package=...)`·`util.find_spec(...)` 모두 실제로 모듈을 해석한다).
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
    (
        "importlib_keyword_argument",
        'import importlib\n\n_gate = importlib.import_module(name="server.bridge")',
        ("server.bridge",),
    ),
    (
        "dunder_import_keyword_argument",
        '_gate = __import__(name="server.safety")',
        ("server.safety",),
    ),
    (
        "relative_dynamic_import_anchor_keyword",
        'import importlib\n\n_gate = importlib.import_module(".gate", package="server.safety")',
        ("server.safety",),
    ),
    (
        "find_spec_resolves_the_module",
        'import importlib.util\n\n_spec = importlib.util.find_spec("server.bridge")',
        ("server.bridge",),
    ),
    (
        "concatenated_constant",
        'import importlib\n\n_gate = importlib.import_module("server" + ".bridge")',
        ("<unreadable-dynamic-import>:BinOp",),
    ),
    (
        "name_bound_constant",
        'import importlib\n\n_NAME = "server.bridge"\n_gate = importlib.import_module(_NAME)',
        ("<unreadable-dynamic-import>:Name",),
    ),
    (
        "f_string_constant",
        'import importlib\n\n_LEAF = "bridge"\n_gate = importlib.import_module(f"server.{_LEAF}")',
        ("<unreadable-dynamic-import>:JoinedStr",),
    ),
    (
        "starred_argument",
        'import importlib\n\n_ARGS = ("server.bridge",)\n_gate = importlib.import_module(*_ARGS)',
        ("<unreadable-dynamic-import>:Starred",),
    ),
)


@pytest.mark.parametrize(
    "plant,expected",
    [(plant, expected) for _, plant, expected in _CONSOLE_IMPORT_PLANTS],
    ids=[name for name, _, _ in _CONSOLE_IMPORT_PLANTS],
)
def test_console_import_scanner_control_is_caught(plant, expected):
    """AC-018③ 비공허성 — **16형태 전부** 심은 사본에서 스캐너가 실제로 잡는다.

    [round15 B] 4~8행은 round14 스캐너를 **그대로 통과했다**(실측).
    [round17 S17-01] 9~16행은 round16 스캐너를 **그대로 통과했다**(실측, 런타임 동등성 확인).
    어느 형태의 수집을 되돌려도 그 행이 빈 목록을 받아 실패한다.
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


# --------------------------------------------------------------------------
# --- round16 사람이 읽는 문장 내용 고정 (TextContentGates) ---
#
# round16 적대 감사가 살려 보낸 뮤테이션의 공통 기제는 하나다: **게이트가 문자열의
# "CD 토큰 없음"만 보고 내용은 보지 않는다.** 그래서 `HUMAN_EXECUTION_PROCEDURE` 5단계를
#
#     "실행이 끝나면 완료다 — 플러그인이 오류 없이 끝나면 생성된 것이다."
#
# 로 바꿔도 스위트 5,354건이 **전건 통과**했다(M53). `procedure`는 콘솔 표면이고 사람이
# 그대로 따라 한다. 게다가 그 문장은 같은 payload의 `warnings`로 함께 나가는
# `PLUGIN_EXIT_IS_NOT_SUCCESS`("플러그인이 오류 없이 끝난 것은 성공이 아니다")와 **정면
# 모순**한다 — §0 함정 4가 직접 경고한 오독이고, 그 오독의 대가는 되돌릴 수 없는 중복 생성이다.
#
# 두 축으로 잠근다.
#   축 1 — 5단계 **전문 동등**. 표는 프로덕션 상수에서 파생하지 않는다(파생하면 자기 비교라
#          무엇으로 바꿔도 통과한다). 표에서 행을 지우면 튜플 동등이 깨진다(HARD 규율 3).
#   축 2 — **비모순 단정**. 어떤 절차 문장도 "무오류 종료 = 성공/생성"으로 읽힐 수 없고,
#          절차가 나가면 `PLUGIN_EXIT_IS_NOT_SUCCESS`가 **반드시 함께** 나간다(AC-021②).
# 축 1만 두면 토큰을 피해 문구만 바꾼 형제 변조가 빠져나가고, 축 2만 두면 토큰을 피한
# 재작성이 빠져나간다. 두 축 모두 **프로덕션 사본에 심어** 잡히는 것을 확인한다.
# --------------------------------------------------------------------------

#: 절차 5단계의 **전문**. 손으로 옮겨 적은 것이며 `HUMAN_EXECUTION_PROCEDURE`에서
#: 파생하지 않는다 — 파생은 자기 비교이고, 자기 비교는 게이트가 아니다(round16 지적 3).
_R16_PROCEDURE_STEPS = (
    (1, "1. 아래 Lua 소스를 플러그인 라이브러리 파일로 저장한다."),
    (
        2,
        "2. 콘솔에서 Import Plugin '<파일명>' 으로 임포트한다 — 이 빌드의 deploy 동사는 "
        "플러그인 소스를 쓰지 못하므로"
        "(객체만 생기고 소스는 빈 상태로 조용히 실행된다) 쓰지 않는다.",
    ),
    (
        3,
        "3. 같은 이름으로 재임포트하면 소스가 갱신되지 않는다 — 새 이름을 쓰거나 "
        "슬롯을 비우고 임포트한다.",
    ),
    (4, "4. 임포트한 플러그인을 콘솔에서 사람이 실행한다. 서버는 이 실행을 대행하지 않는다."),
    (5, "5. 실행이 끝나면 서버에 검증 읽기를 요청한다 — 생성 여부는 그 재조회로만 확정된다."),
)

_R16_PROCEDURE_TEXTS = tuple(text for _, text in _R16_PROCEDURE_STEPS)


def test_the_execution_procedure_is_pinned_step_by_step_verbatim():
    """[round16 M53] `apply.py:119`의 5단계를 다른 문장으로 바꾸면 이 단정이 실패한다.

    표에서 행을 하나 지워도 실패한다 — 튜플 동등이 곧 전단사다(HARD 규율 3).
    """
    assert _R16_PROCEDURE_TEXTS == HUMAN_EXECUTION_PROCEDURE
    assert tuple(number for number, _ in _R16_PROCEDURE_STEPS) == (1, 2, 3, 4, 5)


@pytest.mark.parametrize(
    "number,text", _R16_PROCEDURE_STEPS, ids=[f"step{n}" for n, _ in _R16_PROCEDURE_STEPS]
)
def test_each_procedure_step_ships_verbatim_in_the_delivered_payload(number, text):
    """단계별 전문 동등을 **payload에서** 확인한다 — 상수가 아니라 나가는 값이 기준이다.

    [round16 M53] 5단계를 바꾸면 `step5` 행이 실패한다.
    """
    payload = _handoff(dry_run=False).to_dict()
    assert payload["procedure"][number - 1] == text
    assert text.startswith(f"{number}. ")


def test_the_procedure_payload_is_exactly_the_pinned_table_in_order():
    """순서까지 고정한다 — 단계 순서가 바뀌면 사람이 캐싱된 소스를 실행하게 된다(§0 항목 9)."""
    assert _handoff(dry_run=False).to_dict()["procedure"] == list(_R16_PROCEDURE_TEXTS)
    assert _handoff(dry_run=True).to_dict()["procedure"] == []


# --------------------------------------------------------------------------
# 축 2 — 비모순. "무오류 종료 = 성공/생성"으로 읽히는 어휘는 절차에 들어갈 수 없다.
#
# 이 스캔의 대상은 **절차뿐**이다. `PLUGIN_EXIT_IS_NOT_SUCCESS`는 같은 어휘("오류 없이")를
# **부정형으로** 쓰는 것이 임무이므로 경고 축에 이 스캔을 걸면 거짓 양성이 된다 —
# 흔한 거짓 양성은 게이트의 강제력을 없앤다(round15 D가 CD 게이트에서 배운 것).
# --------------------------------------------------------------------------

_R16_SUCCESS_CLAIM_TOKENS = (
    "오류 없이",
    "완료다",
    "성공이다",
    "성공한 것이다",
    "생성된 것이다",
    "생성됐다",
    "확인하지 않아도",
    "생략해도",
)

#: 침해 표본 — (토큰, 그 토큰 **하나에만** 걸리는 절차 문장). 토큰 목록에서 파생하지 않는다.
_R16_SUCCESS_CLAIM_PROBES = (
    ("오류 없이", "6. 플러그인이 오류 없이 끝나면 다음 단계로 넘어간다."),
    ("완료다", "6. 실행이 끝나면 완료다."),
    ("성공이다", "6. 플러그인 실행은 그 자체로 성공이다."),
    ("성공한 것이다", "6. 플러그인이 끝났다면 성공한 것이다."),
    ("생성된 것이다", "6. 실행 뒤에는 픽스처가 생성된 것이다."),
    ("생성됐다", "6. 실행했다면 픽스처가 생성됐다."),
    ("확인하지 않아도", "6. 재조회는 확인하지 않아도 된다."),
    ("생략해도", "6. 검증 읽기는 생략해도 된다."),
)


def _r16_success_claims(text: str) -> list[str]:
    return [token for token in _R16_SUCCESS_CLAIM_TOKENS if token in text]


def test_the_success_claim_probe_table_is_a_bijection_onto_the_token_list():
    """[round16] 토큰을 지우거나 더하면 이 단정이 깨진다 — 목록과 표본이 1:1이다."""
    assert tuple(token for token, _ in _R16_SUCCESS_CLAIM_PROBES) == _R16_SUCCESS_CLAIM_TOKENS


@pytest.mark.parametrize(
    "token,probe", _R16_SUCCESS_CLAIM_PROBES, ids=[t for t, _ in _R16_SUCCESS_CLAIM_PROBES]
)
def test_each_success_claim_probe_is_caught_by_exactly_one_token(token, probe):
    """표본이 겨냥한 토큰에만 걸린다 — 인과가 다른 토큰에 가려지지 않는다."""
    assert _r16_success_claims(probe) == [token]


@pytest.mark.parametrize(
    "token,probe", _R16_SUCCESS_CLAIM_PROBES, ids=[t for t, _ in _R16_SUCCESS_CLAIM_PROBES]
)
def test_the_non_contradiction_scan_catches_each_probe_planted_in_the_production_procedure(
    token, probe
):
    """AC-021② 비공허성(전수) — 표본을 **프로덕션 절차에 심어** 프로덕션 산출물을 훑는다.

    `HUMAN_EXECUTION_PROCEDURE`는 `build_patch_handoff`가 호출 시점에 읽는 모듈 전역이므로
    사본에서 재바인딩하면 **적재된 프로덕션 함수의 반환값**에 그대로 실린다.
    """
    planted = APPLY_SOURCE + (
        f'\n\nHUMAN_EXECUTION_PROCEDURE = (*HUMAN_EXECUTION_PROCEDURE, "{probe}")\n'
    )
    namespace = _load(planted)
    handoff = namespace["build_patch_handoff"](**_handoff_kwargs(dry_run=False))
    assert _r16_success_claims("\n".join(handoff.procedure)) == [token]


def test_no_production_procedure_step_can_be_read_as_a_success_claim():
    """대조군의 대조군 — 심지 않은 프로덕션 절차에서는 같은 훑기가 0건이다."""
    handoff = _handoff(dry_run=False)
    assert handoff.procedure
    assert _r16_success_claims("\n".join(handoff.procedure)) == []


_R16_M53_PLANTED_STEP_5 = "5. 실행이 끝나면 완료다 — 플러그인이 오류 없이 끝나면 생성된 것이다."


def test_the_m53_procedure_mutation_is_caught_on_both_axes():
    """[round16 M53] 감사가 심은 **바로 그 문장**을 프로덕션 사본에 심어 두 축을 확인한다.

    축 1(전문 동등)과 축 2(비모순 스캔)가 **각각 독립으로** 잡는다. 한 축만 있으면
    형제 변조가 빠져나간다 — 그것이 여섯 라운드 연속 실패의 기제였다.

    같은 단정에서 **모순의 실체**도 고정한다: 이 사본은 `warnings`에
    "오류 없이 끝난 것은 성공이 아니다"를 실은 채 절차에는 그 반대를 적어 내보낸다.
    """
    planted = APPLY_SOURCE + (
        "\n\nHUMAN_EXECUTION_PROCEDURE = "
        f'(*HUMAN_EXECUTION_PROCEDURE[:4], "{_R16_M53_PLANTED_STEP_5}")\n'
    )
    namespace = _load(planted)
    handoff = namespace["build_patch_handoff"](**_handoff_kwargs(dry_run=False))

    # 축 1 — 전문 동등이 깨진다.
    assert tuple(handoff.procedure) != _R16_PROCEDURE_TEXTS
    assert handoff.procedure[4] != _R16_PROCEDURE_STEPS[4][1]
    # 축 2 — 비모순 스캔이 세 토큰을 잡는다.
    assert _r16_success_claims("\n".join(handoff.procedure)) == [
        "오류 없이",
        "완료다",
        "생성된 것이다",
    ]
    # 그리고 그 사본은 정반대 경고를 **같은 payload에** 실어 내보낸다.
    assert PLUGIN_EXIT_IS_NOT_SUCCESS in handoff.warnings


def _r16_procedure_warning_violations(payload: dict) -> list[str]:
    """절차가 나가는데 무오류-종료 경고가 빠진 payload를 잡는다.

    §0 함정 4 · AC-021② — 절차만 읽고 경고를 못 본 조작자는 플러그인 종료를 성공으로
    읽는다. 그래서 둘은 **함께** 나가야 하고, 그 동반을 payload에서 확인한다.
    """
    if not payload["procedure"]:
        return []
    return [
        warning
        for warning in (PLUGIN_EXIT_IS_NOT_SUCCESS, IRREVERSIBLE_WARNING, END_TO_END_UNVERIFIED)
        if warning not in payload["warnings"]
    ]


def test_the_procedure_never_ships_without_the_plugin_exit_warning():
    """[round16 M53 형제] 절차가 나가는 payload는 세 경고를 **반드시** 함께 싣는다."""
    delivered = _handoff(dry_run=False).to_dict()
    assert delivered["procedure"], "절차가 비면 이 게이트는 공허하다"
    assert _r16_procedure_warning_violations(delivered) == []
    assert delivered["warnings"][1] == PLUGIN_EXIT_IS_NOT_SUCCESS


def test_the_warning_coshipment_gate_is_not_vacuous():
    """비공허성 — 경고를 뺀 프로덕션 사본에서는 같은 게이트가 발화한다.

    `warnings`는 dataclass 필드 기본값이라 적재 후 재바인딩이 닿지 않는다 —
    `_apply_source_with_cd_in_warnings`와 같은 이유로 **소스 치환**으로 심는다.
    """
    planted = APPLY_SOURCE.replace(
        _ORIGINAL_DELIVERY_WARNINGS,
        "DELIVERY_WARNINGS = (IRREVERSIBLE_WARNING, END_TO_END_UNVERIFIED)",
        1,
    )
    assert planted != APPLY_SOURCE, "DELIVERY_WARNINGS 앵커가 사라졌다"
    namespace = _load(planted)
    payload = namespace["build_patch_handoff"](**_handoff_kwargs(dry_run=False)).to_dict()
    assert payload["procedure"]
    assert _r16_procedure_warning_violations(payload) == [PLUGIN_EXIT_IS_NOT_SUCCESS]


# --------------------------------------------------------------------------
# [round16 M72 · M79] payload 상태 문자열은 **리터럴로** 고정한다.
#
# `assert payload["status"] == HANDOFF_STATUS_DRY_RUN`는 프로덕션 상수를 프로덕션 값과
# 비교하는 **자기 비교**라 상수를 무엇으로 바꿔도 통과한다. 실제로 `HANDOFF_STATUS_DRY_RUN`을
# `"delivered"`로 바꿔도(드라이런 payload의 `status`가 `"delivered"`가 된다) 스위트 5,354건이
# 전건 통과했다. 그래서 리터럴로 적고, **문자열이 실리는 payload 키를 전수 분류**한다.
# --------------------------------------------------------------------------

#: payload에 실리는 문자열 키의 전수 분류. 새 문자열 필드가 생기면 분류하지 않고는
#: `test_every_string_valued_handoff_key_is_classified`가 통과하지 못한다.
_R16_HANDOFF_STRING_KEYS = (
    ("status", "status_token"),
    ("next_step", "status_token"),
    ("execution_performed_by", "status_token"),
    # 생성물이라 리터럴로 고정하지 않는다 — M4 계약과 CD 게이트가 따로 지킨다.
    ("lua_source", "generated_source"),
)

#: `status_token` 축이 실제로 갖는 값. (시나리오, dry_run, 키, **리터럴**)
_R16_PAYLOAD_STATUS_ROWS = (
    ("dry_run", True, "status", "dry_run"),
    ("dry_run", True, "next_step", "review_dry_run"),
    ("dry_run", True, "execution_performed_by", "human"),
    ("delivered", False, "status", "delivered"),
    ("delivered", False, "next_step", "human_execution_then_verification_read"),
    ("delivered", False, "execution_performed_by", "human"),
)

#: 그 값을 만드는 모듈 상수 전수. `test_autopatch_verify.py`의 `_R16_APPLY_CONSTANTS`가
#: 이 튜플과 전단사임을 따로 단정한다 — 두 표가 서로를 묶는다.
_R16_PAYLOAD_TOKEN_CONSTANTS = (
    "HANDOFF_STATUS_DRY_RUN",
    "HANDOFF_STATUS_DELIVERED",
    "NEXT_STEP_REVIEW",
    "NEXT_STEP_HUMAN_EXECUTION",
    "EXECUTION_PERFORMED_BY",
)


def _r16_string_payload_keys(payload: dict) -> tuple[str, ...]:
    return tuple(sorted(key for key, value in payload.items() if isinstance(value, str)))


def test_every_string_valued_handoff_key_is_classified():
    """[round16 HARD 규율 1] 문자열 축이 하나 생기면 분류 없이는 통과하지 못한다."""
    declared = tuple(sorted(key for key, _ in _R16_HANDOFF_STRING_KEYS))
    assert len(_R16_HANDOFF_STRING_KEYS) == len(set(declared))
    for dry_run in (True, False):
        assert _r16_string_payload_keys(_handoff(dry_run=dry_run).to_dict()) == declared
    tokens = {key for key, kind in _R16_HANDOFF_STRING_KEYS if kind == "status_token"}
    # 두 시나리오 × 상태 토큰 전부가 표에 있어야 한다 — 키 집합만 비교하면 `dry_run` 행을
    # 지워도 `delivered` 행이 같은 키를 대신 채워 삭제가 보이지 않는다(HARD 규율 3).
    assert {(scenario, key) for scenario, _, key, _ in _R16_PAYLOAD_STATUS_ROWS} == {
        (scenario, key) for scenario in ("dry_run", "delivered") for key in tokens
    }
    assert len(_R16_PAYLOAD_STATUS_ROWS) == 2 * len(tokens)
    assert {scenario: dry_run for scenario, dry_run, _, _ in _R16_PAYLOAD_STATUS_ROWS} == {
        "dry_run": True,
        "delivered": False,
    }


@pytest.mark.parametrize(
    "scenario,dry_run,key,literal",
    _R16_PAYLOAD_STATUS_ROWS,
    ids=[f"{scenario}.{key}" for scenario, _, key, _ in _R16_PAYLOAD_STATUS_ROWS],
)
def test_every_payload_status_token_is_pinned_to_its_literal(scenario, dry_run, key, literal):
    """[round16 M72] `HANDOFF_STATUS_DRY_RUN`을 `"delivered"`로 바꾸면 `dry_run.status` 행이,
    [round16 M79] `NEXT_STEP_HUMAN_EXECUTION`을 `"done"`으로 바꾸면 `delivered.next_step`
    행이 실패한다. 리터럴이므로 상수를 무엇으로 바꿔도 따라가지 않는다.
    """
    assert _handoff(dry_run=dry_run).to_dict()[key] == literal


#: (상수 이름, 심을 리터럴 소스, dry_run, payload 키, 프로덕션 리터럴)
_R16_PAYLOAD_TOKEN_PLANTS = (
    ("HANDOFF_STATUS_DRY_RUN", '"delivered"', True, "status", "dry_run"),
    ("HANDOFF_STATUS_DELIVERED", '"dry_run"', False, "status", "delivered"),
    ("NEXT_STEP_REVIEW", '"done"', True, "next_step", "review_dry_run"),
    (
        "NEXT_STEP_HUMAN_EXECUTION",
        '"done"',
        False,
        "next_step",
        "human_execution_then_verification_read",
    ),
    ("EXECUTION_PERFORMED_BY", '"server"', False, "execution_performed_by", "human"),
)


def test_the_payload_token_plant_table_covers_every_status_constant():
    """[round16 HARD 규율 3] 상태 상수가 하나 늘면 심는 표도 함께 늘어야 한다."""
    assert tuple(name for name, *_ in _R16_PAYLOAD_TOKEN_PLANTS) == _R16_PAYLOAD_TOKEN_CONSTANTS


@pytest.mark.parametrize(
    "name,planted_literal,dry_run,key,literal",
    _R16_PAYLOAD_TOKEN_PLANTS,
    ids=[name for name, *_ in _R16_PAYLOAD_TOKEN_PLANTS],
)
def test_the_literal_status_gate_catches_each_constant_plant(
    name, planted_literal, dry_run, key, literal
):
    """비공허성(전수) — 상수를 **프로덕션 사본에서** 바꾸면 리터럴 단정이 실제로 깨진다.

    자기 비교였다면 이 사본도 통과한다. 그것이 M72·M79가 살아남은 이유다.
    """
    namespace = _load(APPLY_SOURCE + f"\n\n{name} = {planted_literal}\n")
    planted_payload = namespace["build_patch_handoff"](**_handoff_kwargs(dry_run=dry_run)).to_dict()
    assert planted_payload[key] != literal

    control = _load(APPLY_SOURCE)["build_patch_handoff"](
        **_handoff_kwargs(dry_run=dry_run)
    ).to_dict()
    assert control[key] == literal


# --- round16 표 전단사·문장 전문 고정 (TableBijection) ---
#
# 이 절이 닫는 두 구멍:
#   ① `_CONSOLE_BOUND_HANDOFF_KEYS`/`_DIAGNOSTIC_HANDOFF_KEYS`는 **양분 게이트만** 있었다 —
#      두 표가 서로 겹치지 않고 합쳐서 payload를 덮는지는 봤지만 **분류가 옳은지**는
#      아무도 강제하지 않았다. 적대 감사 실측(P12): `procedure`를 진단 축으로 옮기고
#      `_CD_SURFACE_PLANTS`의 짝 행을 함께 지우면 두 표가 여전히 정합해 **조용히 통과**한다.
#      그 상태에서 절차문에 심긴 반증 처방·CD는 게이트 밖으로 나간다.
#   ② `_CONSOLE_IMPORT_PLANTS`에 전단사 게이트가 없어 우회 형태 한 줄을 지워도 조용했다.


def _round16_payload_texts(value: object) -> list[str]:
    """payload 값에서 **길이 2 이상 문자열**을 전부 끄집어낸다(중첩 목록·사전 포함).

    길이 1을 버리는 이유는 우연 일치 때문이다 — `candidate_id`의 `'a'`는 어떤 Lua
    소스에도 부분문자열로 들어 있어 판정에 아무 정보도 주지 않는다.
    """
    if isinstance(value, str):
        return [value] if len(value) >= 2 else []
    if isinstance(value, dict):
        return [text for item in value.values() for text in _round16_payload_texts(item)]
    if isinstance(value, (list, tuple, set, frozenset)):
        return [text for item in value for text in _round16_payload_texts(item)]
    return []


def test_the_console_axis_classification_is_fixed_by_what_the_text_actually_is():
    """분류가 **옳은지**를 표 대조가 아니라 값의 정체로 고정한다.

    콘솔 축의 정의는 "사람이 콘솔에 입력하거나 그대로 따라 실행할 텍스트"다. 그 정의를
    기계적으로 판정한다 — 축이 싣는 모든 문자열이 (a) 조작자가 임포트해 실행할 **Lua
    소스 자체**이거나, (b) 그 Lua 소스 안에 **글자 그대로 박혀 있거나**, (c) 인간 실행
    절차·경고·다음 단계를 정의하는 **프로덕션 상수**여야 한다. 진단 축은 셋 중 어디에도
    해당하지 않는다.

    표를 참조하지 않으므로 **행을 지워서 빠져나갈 수 없다**.

    [round16 P12] `_CONSOLE_BOUND_HANDOFF_KEYS`에서 `procedure`를 빼
      `_DIAGNOSTIC_HANDOFF_KEYS`로 옮기면 — `_CD_SURFACE_PLANTS`의 짝 행을 함께 지워
      기존 게이트를 전부 만족시키더라도 — 진단 축 단정이 실패한다. `procedure`는
      `HUMAN_EXECUTION_PROCEDURE` 그 자체이기 때문이다.
    [round16] 반대로 `status`·`execution_performed_by` 같은 진단 축을 콘솔 축으로
      옮겨도 콘솔 축 단정이 실패한다.
    [round16] `apply.py`가 `procedure=HUMAN_EXECUTION_PROCEDURE`를 다른 문자열로
      바꾸면 콘솔 축 단정이 실패한다 — 절차문이 프로덕션 상수에서 떨어져 나간 것이다.
    """
    from server.vwx.apply import (
        DELIVERY_WARNINGS,
        HUMAN_EXECUTION_PROCEDURE,
        NEXT_STEP_HUMAN_EXECUTION,
    )

    payload = _handoff(dry_run=False).to_dict()
    lua = str(payload["lua_source"])
    assert "AddFixtures({" in lua, lua
    console_constants = (
        frozenset(HUMAN_EXECUTION_PROCEDURE)
        | frozenset(DELIVERY_WARNINGS)
        | {NEXT_STEP_HUMAN_EXECUTION, lua}
    )

    def console_destined(key: str) -> bool:
        texts = _round16_payload_texts(payload[key])
        return bool(texts) and all(text in console_constants or text in lua for text in texts)

    for key in _CONSOLE_BOUND_HANDOFF_KEYS:
        assert console_destined(key), (key, _round16_payload_texts(payload[key]))
    for key in _DIAGNOSTIC_HANDOFF_KEYS:
        assert not console_destined(key), (key, _round16_payload_texts(payload[key]))


def test_the_console_axis_classification_probe_is_not_vacuous():
    """대조의 대조 — 판정기가 **아무거나 콘솔 축이라고 하지는 않는다**.

    Lua에도 없고 프로덕션 상수도 아닌 문자열을 콘솔 축 자리에 놓으면 판정이 뒤집힌다.
    이것이 없으면 위 테스트는 "전부 참"으로 공허해질 수 있다.
    """
    from server.vwx.apply import DELIVERY_WARNINGS, HUMAN_EXECUTION_PROCEDURE

    payload = _handoff(dry_run=False).to_dict()
    lua = str(payload["lua_source"])
    console_constants = frozenset(HUMAN_EXECUTION_PROCEDURE) | frozenset(DELIVERY_WARNINGS)
    stranger = "이 문장은 Lua에도 없고 프로덕션 상수도 아니다"
    assert stranger not in lua
    assert stranger not in console_constants
    texts = _round16_payload_texts({"reason": stranger, "count": 3})
    assert texts == [stranger]
    assert not all(text in console_constants or text in lua for text in texts)


#: `_CONSOLE_IMPORT_PLANTS`의 **축소 트립와이어**. 우회 형태를 하나 지우면 어긋난다.
#: [round17 S17-01] 8행 → **16행**. 뒤 8행은 round16 스캐너를 그대로 통과한 우회로다.
_ROUND16_CONSOLE_IMPORT_PLANT_IDS = frozenset(
    {
        "absolute_bridge",
        "absolute_safety_gate",
        "absolute_pythonosc",
        "relative_bridge",
        "relative_safety_gate",
        "alias_is_the_submodule",
        "importlib_string_argument",
        "dunder_import_string_argument",
        "importlib_keyword_argument",
        "dunder_import_keyword_argument",
        "relative_dynamic_import_anchor_keyword",
        "find_spec_resolves_the_module",
        "concatenated_constant",
        "name_bound_constant",
        "f_string_constant",
        "starred_argument",
    }
)


def _round16_plant_mechanisms(plant: str) -> frozenset[tuple[str, str]]:
    """심은 소스가 **어느 수집 기제로** 어느 봉인 모듈에 닿는지 태그해서 돌려준다.

    `_imported_modules`와 같은 순회를 하되 이름만이 아니라 **그 이름을 만든 기제**를
    함께 싣는다. 기제 어휘는 `_DYNAMIC_IMPORT_CALLEES`에서 파생하므로 스캐너가 동적
    호출을 하나 더 보게 되면 이 어휘도 함께 늘어난다.
    """
    tagged: set[tuple[str, str]] = set()

    def ward(name: str) -> str | None:
        for module in _CONSOLE_WARD_MODULES:
            if name.startswith(module):
                return module
        return None

    for node in ast.walk(ast.parse(plant)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = ward(alias.name)
                if module:
                    tagged.add(("import", module))
        elif isinstance(node, ast.ImportFrom):
            anchor = "server" if node.level else ""
            base = ".".join(part for part in (anchor, node.module or "") if part)
            module = ward(base)
            if module:
                tagged.add(("from_relative" if node.level else "from_absolute", module))
                continue
            for alias in node.names:
                module = ward(f"{base}.{alias.name}" if base else alias.name)
                if module:
                    # 금지 이름이 `node.module`이 아니라 **alias**에 있는 형태.
                    tagged.add(("from_alias", module))
        elif isinstance(node, ast.Call):
            callee = node.func
            name = callee.attr if isinstance(callee, ast.Attribute) else getattr(callee, "id", None)
            if name in _DYNAMIC_IMPORT_CALLEES:
                # [round17 S17-01] 위치 인자·키워드 인자·**읽을 수 없는 인자**를 서로 다른
                # 기제로 태그한다. 셋을 뭉치면 한 형태만 잡혀도 다른 형태가 가려진다.
                for argument in node.args:
                    if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                        module = ward(argument.value)
                        if module:
                            tagged.add((f"dynamic:{name}", module))
                    else:
                        tagged.add(
                            (
                                f"dynamic_unreadable:{name}",
                                f"{_UNREADABLE_DYNAMIC_IMPORT}:{type(argument).__name__}",
                            )
                        )
                for keyword in node.keywords:
                    argument = keyword.value
                    if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                        module = ward(argument.value)
                        if module:
                            tagged.add((f"dynamic_kw:{name}", module))
                    else:
                        tagged.add(
                            (
                                f"dynamic_unreadable:{name}",
                                f"{_UNREADABLE_DYNAMIC_IMPORT}:{type(argument).__name__}",
                            )
                        )
    return frozenset(tagged)


def test_the_console_import_plant_table_covers_every_bypass_mechanism_and_every_ward():
    """`_CONSOLE_IMPORT_PLANTS` 전단사 — 행을 지우거나 기제를 놓치면 실패한다.

    [round16 A1] 16행 중 어느 행을 지워도 id 집합 단정이 실패한다 — 이전에는 우회 형태
      한 줄을 지워도 스위트가 조용히 축소됐다.
    [round16] 두 행이 같은 (기제, 표적) 쌍을 덮으면 단사성 단정이 실패한다 —
      중복 행은 곧 "지워도 되는 행"이다.
    [round16] `_CONSOLE_WARD_MODULES`에 모듈을 더하면 그 모듈을 심는 행이 없어 실패한다.
    [round16] `_DYNAMIC_IMPORT_CALLEES`에 호출자를 더하면 그 호출자를 심는 행이 없어 실패한다.
    [round17 S17-01] 수집 **계열**(`dynamic` · `dynamic_kw` · `dynamic_unreadable`) 중
      하나를 스캐너에서 되돌리면 그 계열을 덮는 행이 사라져 실패한다.
    [round17 S17-01] `_UNREADABLE_DYNAMIC_ARGUMENT_KINDS`에 종류를 더하면 그 종류를 심는
      행이 없어 실패한다.
    """
    names = [name for name, _, _ in _CONSOLE_IMPORT_PLANTS]
    assert len(names) == len(set(names)) == len(_ROUND16_CONSOLE_IMPORT_PLANT_IDS)
    assert set(names) == _ROUND16_CONSOLE_IMPORT_PLANT_IDS

    tagged_by_name: dict[str, tuple[str, str]] = {}
    for name, plant, _expected in _CONSOLE_IMPORT_PLANTS:
        tags = _round16_plant_mechanisms(plant)
        # 한 행은 **정확히 한 가지 우회로**를 실증한다 — 섞으면 무엇이 잡혔는지 모른다.
        assert len(tags) == 1, (name, sorted(tags))
        tagged_by_name[name] = next(iter(tags))

    assert len(set(tagged_by_name.values())) == len(tagged_by_name), tagged_by_name

    observed = {mechanism for mechanism, _ in tagged_by_name.values()}
    # ① 정적 기제 넷 + 동적 계열 셋이 **전부** 덮인다.
    families = {"import", "from_absolute", "from_relative", "from_alias"}
    families |= {"dynamic", "dynamic_kw", "dynamic_unreadable"}
    assert {mechanism.split(":", 1)[0] for mechanism in observed} == families
    # ② 동적 호출자 어휘가 **전부** 덮인다 — 어휘에 더하면 심는 행이 있어야 한다.
    assert {mechanism.split(":", 1)[1] for mechanism in observed if ":" in mechanism} == set(
        _DYNAMIC_IMPORT_CALLEES
    )
    # ③ 표적 전수 — 봉인 모듈 셋 + 읽을 수 없는 인자 종류 넷.
    assert {target for _, target in tagged_by_name.values()} == set(_CONSOLE_WARD_MODULES) | {
        f"{_UNREADABLE_DYNAMIC_IMPORT}:{kind}" for kind in _UNREADABLE_DYNAMIC_ARGUMENT_KINDS
    }


def test_the_console_import_plant_mechanism_tagger_sees_nothing_in_clean_production():
    """대조의 대조 — 심지 않은 프로덕션 소스에는 어떤 기제 태그도 붙지 않는다."""
    assert _round16_plant_mechanisms(APPLY_SOURCE) == frozenset()


# --- round18 import 봉인 화이트리스트 역전 (SealWhitelist) ---
#
# **열거 전략은 졌다.** round14가 3형태, round15가 8형태, round17이 16형태를 막았고
# round18 적대 감사가 **17~22번째 6형태**를 또 실증했다:
#
#   17. `from importlib import import_module as _imp` 뒤 `_imp("server.bridge")`
#   18. `importlib.util.spec_from_file_location(...)` — 파일 경로로 직접 로드
#   19. `builtins.__import__("server.safety")`
#   20. `exec("import server.bridge")`
#   21. `runpy.run_module("server.bridge")`
#   22. `SourceFileLoader("gate", "server/safety/gate.py").load_module()`
#
# 실측(아래 `test_the_enumerating_gate_blind_spots_are_exactly_the_registered_set`):
# `_console_ward_offenders`(열거 게이트)는 이 여섯 중 **다섯을 그대로 통과시킨다**.
# ~~23번째 형태는 다음 라운드에 나온다~~ — **[round19 정정] 23번째는 이번 라운드에 나왔다.**
# 그것도 넷이(형태 23~26), 그리고 그 넷은 아래 규칙 ①②가 아니라 **여전히 열거로 남아 있던
# 규칙 ③④**를 통과했다. 이 주석은 "화이트리스트 역전"을 표방했지만 실제로 역전한 것은
# 규칙 ①②뿐이었다 — 그 자기 진단이 틀렸다. 이어지는 정정과 규칙 ⑤~⑨는 이 파일 끝
# `round19 봉인 규칙 ③④ 화이트리스트 역전 (GateHoles19)` 절에 있다.
#
# **그래서 방향을 뒤집는다.** "무엇이 금지인가"를 세는 대신 "무엇이 허용인가"를 동결한다.
# `server/vwx/**`의 실측 import는 **완전 모듈명 25개 / 최상위 루트 14개**이고 상대 import는
# 0건이며 동적 import·`exec`·`runpy`·`SourceFileLoader`는 프로덕션에서 **한 번도 쓰이지 않는다**.
# 그 사실 위에 네 규칙을 세운다:
#
#   ① 아래 **동결 화이트리스트 25항목** 밖의 import는 전부 위반
#   ② 상대 import 금지(`node.level > 0`) — 접두사 대조를 원리적으로 우회하는 형태다
#   ③ bare 호출 금지: `exec` · `eval` · `__import__` · `compile`
#      (`re.compile`은 `Attribute` 호출이라 걸리지 않는다 — 프로덕션 6곳 확인)
#   ④ 모듈 기계장치 이름 참조 금지: `__builtins__` · `__import__` · `__loader__` · `__spec__`
#      (import 없이 로더에 닿는 유일한 통로다)
#
# **트레이드오프(의도된 것)**: `server/vwx/`에 새 의존을 더하려면 아래 등기부에 **손으로 한 줄**
# 더해야 하고, 더하기 전까지 `test_no_vwx_module_imports_outside_the_frozen_registry`가 실패한다.
# 등기부를 프로덕션에서 파생하면 편하지만 그것은 **자기충족**이다 — 새 import가 조용히 통과한다.
# 등기부는 손으로 동결하고, 벗어나면 **반드시 실패해야** 한다. 그게 이 게이트의 전부다.
#
# 구 열거 게이트(`_console_ward_offenders`)는 **지우지 않는다** — 봉인 대상 세 모듈에 대한
# 명시적 진술로 남기고, 아래 대조가 25형태 전부를 **두 게이트에 함께** 통과시킨다.

#: `server/vwx/**` 전 모듈이 import해도 되는 **완전 모듈명 전수**. 손으로 동결했다.
#: 파생 금지 — 프로덕션에서 계산하면 새 import가 스스로를 승인한다.
_REGISTERED_VWX_IMPORTS = frozenset(
    {
        # 표준 라이브러리 — 순수 계산·직렬화·해시. 어느 것도 모듈을 동적으로 싣지 않는다.
        "__future__",
        "collections.abc",
        "csv",
        "dataclasses",
        "hashlib",
        "io",
        "json",
        "re",
        "types",
        "typing",
        # [round24 후속] MVR 판독(`server/vwx/mvr.py`)이 더한 둘. MVR은 ZIP 컨테이너에
        # `GeneralSceneDescription.xml`과 GDTF를 담은 형식이라 두 표준 모듈이 필수다.
        # 어느 것도 모듈을 동적으로 싣지 않는다 — `zipfile`은 바이트를, `ElementTree`는
        # 텍스트를 읽을 뿐이고 규칙 ③④(bare 호출 · 로더 기계장치)와 무관하다.
        # `ElementTree.fromstring`은 외부 엔티티를 확장하지 않는다(파이썬 기본 파서).
        "xml.etree.ElementTree",
        "zipfile",
        # 서드파티 — xlsx 판독 한 곳.
        "openpyxl",
        # 1단계 계층 — 읽기 전용 데이터 계약. 콘솔 발화 표면이 아니다.
        "server.prechk.inventory",
        "server.prechk.patch",
        # 자기 패키지 내부 — 절대 경로로만 쓴다(상대 import는 규칙 ②가 금지한다).
        "server.vwx.address",
        "server.vwx.columns",
        "server.vwx.diff",
        "server.vwx.luagen",
        # [round24 후속] 인테이크가 DMX 주소 산술을 mvr 한 자리에서 빌려 쓴다 —
        # 각자 나누기를 쓰면 그것이 형제 표면이다.
        "server.vwx.mvr",
        "server.vwx.patchplan",
        "server.vwx.reader",
        "server.vwx.rig",
        "server.vwx.typemap",
        "server.vwx.verdicts",
    }
)

#: 규칙 ③ — bare 호출로 임의 코드/모듈을 실어 오는 내장 넷.
_R18_SEAL_FORBIDDEN_BARE_CALLEES = frozenset({"exec", "eval", "__import__", "compile"})

#: 규칙 ④ — import 문 없이 로더·내장 네임스페이스에 닿는 이름 넷.
_R18_SEAL_FORBIDDEN_NAMES = frozenset({"__builtins__", "__import__", "__loader__", "__spec__"})


def _import_seal_violations(
    source: str, *, registry: frozenset[str] = _REGISTERED_VWX_IMPORTS
) -> list[str]:
    """화이트리스트 역전 봉인 — 네 규칙 위반을 **정렬·중복제거해** 돌려준다.

    `registry`를 인자로 뺀 것은 등기부 자체에 대조군을 붙이기 위해서다
    (`test_shrinking_the_frozen_registry_makes_production_fail`).
    """
    tree = ast.parse(source)
    violations: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name not in registry:
                    violations.add(f"unregistered-import:{alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.level > 0:
                # 상대 import는 절대명이 소스에 없다 — 접두사 대조가 원리적으로 성립하지 않는다.
                violations.add(f"relative-import:{'.' * node.level}{node.module or ''}")
            elif (node.module or "") not in registry:
                violations.add(f"unregistered-import:{node.module or ''}")
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in _R18_SEAL_FORBIDDEN_BARE_CALLEES
        ):
            violations.add(f"forbidden-call:{node.func.id}")
        if isinstance(node, ast.Name) and node.id in _R18_SEAL_FORBIDDEN_NAMES:
            violations.add(f"forbidden-name:{node.id}")
    return sorted(violations)


def _r18_unregistered_names(violations: list[str]) -> list[str]:
    """실패 메시지가 **등기할 정확한 항목**을 찍도록 위반 목록에서 모듈명만 뽑는다."""
    prefix = "unregistered-import:"
    return [name.removeprefix(prefix) for name in violations if name.startswith(prefix)]


@pytest.mark.parametrize("module", VWX_MODULES, ids=lambda path: str(path))
def test_no_vwx_module_imports_outside_the_frozen_registry(module: Path):
    """R18-F — 화이트리스트 역전 봉인: 등기부 밖 import·상대 import·로더 접근 0건.

    죽이는 뮤테이션:
      · `server/vwx/*.py`에 **어떤** 새 import를 심어도(봉인 모듈이든 아니든) 실패한다 —
        열거 게이트가 어휘 밖이라 놓치던 `runpy`·`importlib.machinery`·`builtins`가 여기서 걸린다.
      · `from ..bridge import osc` 같은 상대 import를 심으면 규칙 ②가 잡는다.
      · `exec("import server.bridge")`를 심으면 규칙 ③이 잡는다.
      · `__builtins__["__import__"]("server.safety")`를 심으면 규칙 ④가 잡는다.
      · `_REGISTERED_VWX_IMPORTS`에서 항목을 지우면 그 항목을 쓰는 모듈이 실패한다.
    """
    assert VWX_MODULES, "스캔 대상이 0개면 이 확인은 공허하다"
    violations = _import_seal_violations(module.read_text(encoding="utf-8"))
    assert violations == [], (
        f"{module}: 봉인 화이트리스트 밖이다. 정당한 의존이면 `_REGISTERED_VWX_IMPORTS`에 "
        f"다음 항목을 **손으로** 등기하라 → {_r18_unregistered_names(violations)} "
        f"(전체 위반: {violations}). 등기 편집 한 줄이 이 게이트의 비용이고, 그게 의도다."
    )


def _r18_production_import_names() -> set[str]:
    """`server/vwx/**`가 실제로 쓰는 완전 모듈명 전수 — **등기부와 대조하기 위해서만** 쓴다."""
    observed: set[str] = set()
    for module in VWX_MODULES:
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                observed.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                observed.add(node.module or "")
    return observed


def test_the_frozen_import_registry_is_exactly_what_production_imports():
    """등기부 전단사 — **더해도 지워도** 실패한다.

    죽이는 뮤테이션:
      · `_REGISTERED_VWX_IMPORTS`에서 한 항목을 지우면 `missing`이 비지 않아 실패한다.
      · 쓰지도 않는 항목을 **미리** 등기해 두면(예: `"importlib"`) `stale`이 비지 않아 실패한다 —
        선제 등기는 봉인을 미리 열어 두는 것이고, 그것이 화이트리스트를 무력화하는 유일한 길이다.
      · 프로덕션에 새 import가 생기면 등기 전까지 실패한다(위 전수 테스트와 같은 방향).
    """
    observed = _r18_production_import_names()
    missing = sorted(observed - _REGISTERED_VWX_IMPORTS)
    stale = sorted(_REGISTERED_VWX_IMPORTS - observed)
    assert missing == [], f"등기되지 않은 프로덕션 import: {missing}"
    assert stale == [], (
        f"등기부에만 있고 프로덕션이 쓰지 않는 항목: {stale}. "
        "쓰지 않는 등기는 **미리 열어 둔 문**이다 — 지워라."
    )
    # 실측 고정 — 규모가 조용히 부풀지 않는다(round18 실측: 완전 모듈명 22 / 최상위 루트 12).
    assert len(_REGISTERED_VWX_IMPORTS) == 25
    assert len({name.split(".", 1)[0] for name in _REGISTERED_VWX_IMPORTS}) == 14


def test_production_has_no_relative_import_and_no_loader_machinery():
    """규칙 ②③④의 **전제**를 실측으로 고정한다 — 전제가 무너지면 규칙이 거짓 양성이 된다.

    죽이는 뮤테이션: 프로덕션에 상대 import나 bare `exec`/`eval`/`compile`/`__import__`,
    또는 `__builtins__`·`__loader__`·`__spec__` 참조를 심으면 실패한다.
    """
    kinds: set[str] = set()
    for module in VWX_MODULES:
        for violation in _import_seal_violations(module.read_text(encoding="utf-8")):
            kinds.add(violation.split(":", 1)[0])
    assert kinds == set()


#: round18 적대 감사가 실증한 **17~22번째** 우회 형태. `caught_by_the_enumerating_gate`는
#: 구 게이트(`_console_ward_offenders`)가 그 형태를 잡는지의 **실측 특성화**다.
#: 구 게이트를 늘려 이 값이 바뀌면 이 표를 갱신해야 한다 — 그 갱신 부담이 열거 전략의 비용이고,
#: 화이트리스트 역전이 그 부담을 지지 않는다는 증거다.
_ROUND18_SEAL_BYPASS_PLANTS = (
    (
        "aliased_import_module",
        'from importlib import import_module as _imp\n\n_gate = _imp("server.bridge")',
        ("unregistered-import:importlib",),
        False,
    ),
    (
        "spec_from_file_location",
        "from importlib.util import spec_from_file_location\n\n"
        '_spec = spec_from_file_location("gate", "server/safety/gate.py")',
        ("unregistered-import:importlib.util",),
        False,
    ),
    (
        "builtins_module_dunder_import",
        'import builtins\n\n_gate = builtins.__import__("server.safety")',
        ("unregistered-import:builtins",),
        True,
    ),
    (
        "exec_of_an_import_statement",
        '_ns: dict = {}\nexec("import server.bridge", _ns)',
        ("forbidden-call:exec",),
        False,
    ),
    (
        "runpy_run_module",
        'import runpy\n\n_ns = runpy.run_module("server.bridge")',
        ("unregistered-import:runpy",),
        False,
    ),
    (
        "source_file_loader",
        "from importlib.machinery import SourceFileLoader\n\n"
        '_m = SourceFileLoader("gate", "server/safety/gate.py").load_module()',
        ("unregistered-import:importlib.machinery",),
        False,
    ),
)

#: 규칙 ②③④ 중 위 25형태가 **덮지 못하는 갈래**를 채우는 심기. 규칙에 대조군이 없으면
#: 그 규칙을 지워도 조용하다 — round16이 형태판정 표에서 당한 것과 같은 결함 클래스다.
_ROUND18_SEAL_RULE_PLANTS = (
    (
        # 규칙 ②의 **독립 살상력**. 규칙 ②를 되돌리면 이 행은 조용해지지 않고
        # `unregistered-import:patchplan`으로 **라벨이 바뀌어** 실패한다 — 규칙 ①이
        # 우연히 덮는 것과 규칙 ②가 의도적으로 막는 것을 구분한다.
        "relative_sibling_module",
        "from .patchplan import PatchCandidate  # noqa: F401",
        ("relative-import:.patchplan",),
    ),
    (
        "relative_parent_package",
        "from ..safety.gate import SafetyGate  # noqa: F401",
        ("relative-import:..safety.gate",),
    ),
    (
        "builtins_namespace_subscript",
        '_gate = __builtins__["__import__"]("server.safety")',
        ("forbidden-name:__builtins__",),
    ),
    (
        "module_loader_attribute",
        '_m = __loader__.load_module("server.bridge")',
        ("forbidden-name:__loader__",),
    ),
    (
        "module_spec_loader",
        '_m = __spec__.loader.load_module("server.safety")',
        ("forbidden-name:__spec__",),
    ),
    (
        "eval_of_a_dunder_import",
        "_gate = eval(\"__import__('server.bridge')\")",
        ("forbidden-call:eval",),
    ),
    (
        "compile_of_an_import_statement",
        '_code = compile("import server.safety", "<seal>", "exec")',
        ("forbidden-call:compile",),
    ),
)

#: 두 표의 **축소 트립와이어**. 우회 형태를 한 줄 지우면 어긋난다.
_ROUND18_SEAL_BYPASS_PLANT_IDS = frozenset(
    {
        "aliased_import_module",
        "spec_from_file_location",
        "builtins_module_dunder_import",
        "exec_of_an_import_statement",
        "runpy_run_module",
        "source_file_loader",
    }
)

_ROUND18_SEAL_RULE_PLANT_IDS = frozenset(
    {
        "relative_sibling_module",
        "relative_parent_package",
        "builtins_namespace_subscript",
        "module_loader_attribute",
        "module_spec_loader",
        "eval_of_a_dunder_import",
        "compile_of_an_import_statement",
    }
)


@pytest.mark.parametrize(
    "plant,expected",
    [(plant, expected) for _, plant, expected, _ in _ROUND18_SEAL_BYPASS_PLANTS],
    ids=[name for name, _, _, _ in _ROUND18_SEAL_BYPASS_PLANTS],
)
def test_the_whitelist_seal_catches_the_six_forms_the_enumerating_gate_missed(plant, expected):
    """R18-F 비공허성 — 17~22번째 우회 형태를 화이트리스트 게이트가 **실제로** 잡는다.

    죽이는 뮤테이션: 규칙 ①(등기부 대조)이나 규칙 ③(bare 호출)을 되돌리면 해당 행이
    빈 목록을 받아 실패한다.
    """
    assert _import_seal_violations(APPLY_SOURCE + "\n\n" + plant + "\n") == sorted(expected)


@pytest.mark.parametrize(
    "plant,expected",
    [(plant, expected) for _, plant, expected in _ROUND18_SEAL_RULE_PLANTS],
    ids=[name for name, _, _ in _ROUND18_SEAL_RULE_PLANTS],
)
def test_the_whitelist_seal_catches_loader_machinery_and_bare_builtin_calls(plant, expected):
    """규칙 ③④ 비공허성 — import 문 **없이** 로더에 닿는 다섯 형태를 잡는다.

    죽이는 뮤테이션: `_R18_SEAL_FORBIDDEN_NAMES`나 `_R18_SEAL_FORBIDDEN_BARE_CALLEES`에서
    항목을 지우면 그 항목을 심는 행이 빈 목록을 받아 실패한다.
    """
    assert _import_seal_violations(APPLY_SOURCE + "\n\n" + plant + "\n") == sorted(expected)


@pytest.mark.parametrize(
    "plant",
    [plant for _, plant, _ in _CONSOLE_IMPORT_PLANTS],
    ids=[f"legacy:{name}" for name, _, _ in _CONSOLE_IMPORT_PLANTS],
)
def test_the_whitelist_seal_also_catches_every_legacy_enumerated_bypass(plant):
    """25형태 대조 — 구 표 16행이 **새 게이트에도** 전부 걸린다.

    두 게이트를 병존시키는 근거다. 새 게이트가 구 게이트의 도달 범위를 **덮지 못하면**
    구 표를 지울 수 없고, 여기서 그 포함관계를 실측한다.

    죽이는 뮤테이션: 규칙 ①②③ 중 하나를 되돌리면 그 규칙이 유일하게 잡던 행이 실패한다
    (①: 절대 import 6행 · ②: 상대 import 2행 · ③: `__import__` bare 호출 2행).
    """
    assert _import_seal_violations(APPLY_SOURCE + "\n\n" + plant + "\n") != []


def test_the_enumerating_gate_blind_spots_are_exactly_the_registered_set():
    """**왜 역전했는가**를 실측으로 남긴다 — 구 게이트가 놓치는 형태의 전수.

    round18 실측: 17~22번째 6형태 중 **다섯**을 구 게이트가 그대로 통과시킨다
    (`builtins.__import__`만 `__import__`가 어휘에 있어 우연히 걸린다).
    구 게이트를 늘려 이 집합이 바뀌면 이 단정이 실패한다 — **그 갱신 부담 자체가
    열거 전략의 비용**이고, 아래 화이트리스트 단정에는 그 부담이 없다.

    죽이는 뮤테이션: 새 게이트가 이 다섯 중 하나라도 놓치면 두 번째 단정이 실패한다.
    """
    missed = {
        name
        for name, plant, _expected, _caught in _ROUND18_SEAL_BYPASS_PLANTS
        if not _console_ward_offenders(APPLY_SOURCE + "\n\n" + plant + "\n")
    }
    declared = {name for name, _, _, caught in _ROUND18_SEAL_BYPASS_PLANTS if not caught}
    assert missed == declared, sorted(missed ^ declared)
    assert len(missed) == 5
    # …그리고 화이트리스트 게이트는 그 다섯을 **전부** 잡는다.
    for name, plant, _expected, _caught in _ROUND18_SEAL_BYPASS_PLANTS:
        assert _import_seal_violations(APPLY_SOURCE + "\n\n" + plant + "\n") != [], name


def test_the_whitelist_seal_reports_nothing_without_a_plant():
    """클린 대조군 — 심지 않은 **프로덕션 12모듈 전수**에서 같은 게이트가 0건이다.

    이것이 없으면 위 행들이 "원래부터 걸려 있던 것"을 보고 통과할 수 있다.
    """
    assert VWX_MODULES, "스캔 대상이 0개면 이 확인은 공허하다"
    clean = {
        str(module): _import_seal_violations(module.read_text(encoding="utf-8"))
        for module in VWX_MODULES
    }
    assert {path: found for path, found in clean.items() if found} == {}


def test_shrinking_the_frozen_registry_makes_production_fail():
    """등기부 자체의 비공허성 — 항목을 하나 빼면 프로덕션이 **실제로** 걸린다.

    등기부를 프로덕션에서 파생했다면 이 단정은 원리적으로 성립하지 않는다
    (파생 등기부는 무엇을 빼도 자기를 다시 채운다). 손으로 동결했기에 성립한다.

    죽이는 뮤테이션: `_import_seal_violations`가 `registry`를 무시하고 전역을 보게 하면 실패한다.
    """
    for dropped in ("server.vwx.verdicts", "dataclasses", "__future__"):
        shrunk = _REGISTERED_VWX_IMPORTS - {dropped}
        offenders = {
            str(module)
            for module in VWX_MODULES
            if f"unregistered-import:{dropped}"
            in _import_seal_violations(module.read_text(encoding="utf-8"), registry=shrunk)
        }
        assert offenders, dropped


def test_the_round18_seal_plant_tables_are_a_bijection_onto_all_four_rules():
    """새 두 표의 **행삭제 프로브** + 네 규칙 전수 — 행을 지우거나 규칙을 놓치면 실패한다.

    죽이는 뮤테이션:
      · 두 표 중 어느 행을 지워도 id 집합 단정이 실패한다.
      · `_R18_SEAL_FORBIDDEN_BARE_CALLEES`나 `_R18_SEAL_FORBIDDEN_NAMES`에 항목을 **더하면**
        그 항목을 심는 행이 없어 실패한다(무대조군 어휘 금지).
      · 규칙 넷 중 하나를 스캐너에서 되돌리면 그 규칙만 덮던 행이 사라져 실패한다.
    """
    bypass_ids = [name for name, _, _, _ in _ROUND18_SEAL_BYPASS_PLANTS]
    rule_ids = [name for name, _, _ in _ROUND18_SEAL_RULE_PLANTS]
    assert len(bypass_ids) == len(set(bypass_ids)) == len(_ROUND18_SEAL_BYPASS_PLANT_IDS)
    assert set(bypass_ids) == _ROUND18_SEAL_BYPASS_PLANT_IDS
    assert len(rule_ids) == len(set(rule_ids)) == len(_ROUND18_SEAL_RULE_PLANT_IDS)
    assert set(rule_ids) == _ROUND18_SEAL_RULE_PLANT_IDS
    assert set(bypass_ids) & set(rule_ids) == set()

    # 한 행은 **정확히 한 가지 위반**을 실증한다 — 섞으면 무엇이 잡혔는지 모른다.
    observed: set[str] = set()
    rows = [(n, p, e) for n, p, e, _ in _ROUND18_SEAL_BYPASS_PLANTS]
    rows += list(_ROUND18_SEAL_RULE_PLANTS)
    for name, _plant, expected in rows:
        assert len(expected) == 1, name
        observed.add(expected[0])
    assert len(observed) == len(rows), "같은 위반을 두 행이 덮으면 한 행은 지워도 되는 행이다"

    # 네 규칙이 전부 덮인다 — 구 표 16행이 ①②③을, 새 표가 ①③④를 덮는다.
    legacy_kinds = {
        violation.split(":", 1)[0]
        for _name, plant, _expected in _CONSOLE_IMPORT_PLANTS
        for violation in _import_seal_violations(APPLY_SOURCE + "\n\n" + plant + "\n")
    }
    kinds = {name.split(":", 1)[0] for name in observed} | legacy_kinds
    assert kinds == {"unregistered-import", "relative-import", "forbidden-call", "forbidden-name"}

    # 어휘 전수 — 금지 호출자 넷·금지 이름 넷이 **각각** 심는 행을 갖는다.
    # `__import__`는 새 표가 아니라 구 표 2행(`__import__("server.safety")` 계열)이 덮는다.
    dunder = _import_seal_violations(APPLY_SOURCE + '\n\n_g = __import__("server.safety")\n')
    assert dunder == ["forbidden-call:__import__", "forbidden-name:__import__"]
    planted = observed | set(dunder)
    assert {
        name.removeprefix("forbidden-call:")
        for name in planted
        if name.startswith("forbidden-call:")
    } == set(_R18_SEAL_FORBIDDEN_BARE_CALLEES)
    assert {
        name.removeprefix("forbidden-name:")
        for name in planted
        if name.startswith("forbidden-name:")
    } == set(_R18_SEAL_FORBIDDEN_NAMES)


# --- round18 이름 가드 경계 전수 (VacuityAndData) ---
#
# [round18 R18-H] `apply.py:241`의 `if not isinstance(name, str) or not name.strip():`는
# 두 절이다. `.strip()`을 떼는 뮤테이션(`or not name`)이 SURVIVED였고, 그 뮤턴트는
# **공백만 이름을 전달물에 그대로 싣는다**(round18 실측:
# `AddFixtures({ … name = "   ", … })`). 사용자 결정 P6이 이름 없는 항목에 `ZZAP<n>`을
# 쓰기로 정했으므로 공백 이름은 더욱 불허다 — 지어내지 않고 **제외**한다.
#
# 아래 표는 값의 축을 **값에서 계산**한다(자유 라벨 금지) — 한 행을 지우면 축이 사라진다.

_R18_NAME_AXES = (
    "not_a_string_none",
    "not_a_string_int",
    "not_a_string_list",
    "empty",
    "blank_ascii_spaces",
    "blank_ascii_control",
    "blank_unicode",
    "substantive_digit",
    "substantive_letter",
    "substantive_padded",
)


def _r18_name_axis(value: object) -> str:
    """이름 값의 축을 값에서 계산한다 — 표가 자기충족이 되지 않게 한다."""
    if value is None:
        return "not_a_string_none"
    if not isinstance(value, str):
        return f"not_a_string_{type(value).__name__}"
    if value == "":
        return "empty"
    if value.strip() == "":
        if not value.isascii():
            return "blank_unicode"
        return "blank_ascii_spaces" if value.isprintable() else "blank_ascii_control"
    if value != value.strip():
        return "substantive_padded"
    return "substantive_digit" if value.isdecimal() else "substantive_letter"


#: 이름 경계 전수. `delivered`는 그 이름으로 항목이 전달물에 실리는가다.
_R18_NAME_ROWS = (
    (None, False),
    (123, False),
    (["LEDBeam"], False),
    ("", False),
    ("   ", False),
    ("\t\n\r", False),
    ("\u00a0\u2003", False),
    ("0", True),
    ("LEDBeam 101", True),
    ("  LEDBeam 101  ", True),
)


def _r18_assert_name_table_shape(rows: tuple[tuple[object, bool], ...]) -> None:
    """행 삭제 프로브 — 축 하나에 행 하나다."""
    axes = tuple(_r18_name_axis(value) for value, _delivered in rows)
    assert len(axes) == len(set(axes)), axes
    assert set(axes) == set(_R18_NAME_AXES), sorted(axes)
    assert len(rows) == len(_R18_NAME_AXES)
    # 양쪽 판정이 다 있어야 게이트가 의미를 갖는다.
    assert {delivered for _value, delivered in rows} == {False, True}


class TestRound18FixtureNameGuardBoundary:
    """[round18 R18-H] 이름 가드의 두 절 전수 — 공백만 이름은 전달물에 닿지 않는다."""

    def test_the_name_table_shape_detects_row_deletion(self):
        _r18_assert_name_table_shape(_R18_NAME_ROWS)
        for index in range(len(_R18_NAME_ROWS)):
            pruned = tuple(row for position, row in enumerate(_R18_NAME_ROWS) if position != index)
            with pytest.raises(AssertionError):
                _r18_assert_name_table_shape(pruned)

    def test_every_blank_name_is_excluded_and_every_substantive_name_is_delivered(self):
        """[round18 R18-H] `apply.py`의 이름 가드에서 다음 중 하나를 바꾸면 실패한다:

        · `not name.strip()` -> `not name` — 공백만·제어문자만·유니코드 공백만 이름 네 행이
          전달로 뒤집히고 `name = "   "`가 산출물에 실린다(실증).
        · `not isinstance(name, str)` 절 제거 — `None`·`123`·`list` 세 행이
          `AttributeError`로 죽거나 통과한다.
        · 가드 전체 제거 — 위 일곱 행 전부가 전달로 뒤집힌다.
        · 가드를 `not name.strip()`만 남기고 `isinstance`를 버려도 `123`에서 죽는다.
        """
        for value, delivered in _R18_NAME_ROWS:
            handoff = _handoff(names={"a": value})
            context = (_r18_name_axis(value), repr(value))
            if delivered:
                assert [entry.candidate_id for entry in handoff.entries] == ["a"], context
                assert handoff.exclusions == (), context
            else:
                assert handoff.entries == (), context
                assert [exclusion.code for exclusion in handoff.exclusions] == [
                    FIXTURE_NAME_MISSING
                ], context

    def test_a_blank_name_never_reaches_the_rendered_lua(self):
        """[round18 R18-H 도달성] 공백만 이름이 **전달물까지** 가지 않는다.

        `.strip()`을 떼면 이 단정이 정확히 잡는다: 뮤턴트의 `lua_source`에
        `name = "   "`이 실리고 `AddFixtures({`가 1건 생긴다(round18 실증).
        """
        for value in ("   ", "\t\n\r", "\u00a0\u2003"):
            handoff = _handoff(names={"a": value}, dry_run=False)
            rendered = handoff.lua_source or ""
            assert "AddFixtures({" not in rendered, repr(value)
            assert "name =" not in rendered, repr(value)
            assert value not in rendered, repr(value)
            assert handoff.lua_source is None, repr(value)

    def test_the_control_a_substantive_name_does_reach_the_rendered_lua(self):
        """비공허성 — 같은 하네스로 정상 이름은 전달물에 실린다. 이 대조군이 없으면 위
        테스트는 전달 경로가 통째로 막혀도 통과한다.
        """
        handoff = _handoff(names={"a": "LEDBeam 101"}, dry_run=False)
        rendered = handoff.lua_source or ""
        assert rendered.count("AddFixtures({") == 1
        assert 'name = "LEDBeam 101"' in rendered

    def test_a_padded_substantive_name_is_delivered_verbatim_not_trimmed(self):
        """[round18 R18-H 경계] 가드는 **공백 제거기가 아니다** — 양끝 공백이 있는 정상
        이름은 도면 값 그대로 전달된다(값을 조용히 고치지 않는다).

        가드를 `names[...] = name.strip()`처럼 값을 고치는 형태로 바꾸면 실패한다 —
        이 앱은 사용자 값을 조용히 손대지 않는다.
        """
        handoff = _handoff(names={"a": "  LEDBeam 101  "}, dry_run=False)
        assert 'name = "  LEDBeam 101  "' in (handoff.lua_source or "")

    def test_the_exclusion_code_is_registered_and_labelled(self):
        """제외 사유는 등재 어휘로만 나간다(AC-AUTOPATCH-026④)."""
        assert FIXTURE_NAME_MISSING in TARGET_EXCLUSION_REASON
        assert target_exclusion_label(FIXTURE_NAME_MISSING)
        handoff = _handoff(names={"a": "   "})
        (exclusion,) = handoff.exclusions
        payload = exclusion.to_dict()
        assert payload["code"] == FIXTURE_NAME_MISSING
        assert payload["label"] == target_exclusion_label(FIXTURE_NAME_MISSING)
        # 거부된 값을 사유에 되싣지 않는다 — 공백은 눈에 보이지 않아 더 위험하다.
        assert "   " not in payload["reason"]

    def test_a_missing_name_key_is_the_same_verdict_as_a_blank_one(self):
        """[round18 R18-H 형제] `names`에 키가 아예 없는 경우도 같은 갈래다 —
        `names.get(...)`이 `None`을 내고 같은 가드에 걸린다. 두 입력이 갈리면 조작자가
        같은 사건에 다른 사유를 보게 된다.
        """
        absent = _handoff(names={})
        blank = _handoff(names={"a": "   "})
        assert [exclusion.code for exclusion in absent.exclusions] == [
            exclusion.code for exclusion in blank.exclusions
        ]
        assert absent.entries == blank.entries == ()


# --- round19 봉인 규칙 ③④ 화이트리스트 역전 (GateHoles19) ---
#
# **round18 봉인 주석의 자기 진단이 틀렸다.** 주석은 "열거가 끝나지 않는다 → 화이트리스트
# 역전"을 표방했지만 실제로 역전된 것은 규칙 ①②(import 문)뿐이고, **규칙 ③(bare 호출 넷)과
# 규칙 ④(이름 넷)는 여전히 금지 열거**다. 그리고 주석이 적어 둔 "23번째 형태는 **다음**
# 라운드에 나온다"는 **정정한다 — 23번째는 이번 라운드에 나왔다. 그것도 넷이:**
#
#   23. `globals()["__bui" + "ltins__"]["__imp" + "ort__"]("server.bridge")`
#       `globals`는 금지 호출자 넷에 없고 이름이 **문자열 리터럴**이라 `ast.Name` 검사에도
#       걸리지 않는다.
#   24. 같은 형태의 `vars()` 변형.
#   25. `().__class__.__base__.__subclasses__()` — **봉인 주석 자신이 22번째로 적어 둔**
#       `SourceFileLoader`에 import 문 하나 없이 닿는다.
#   26. 등기된 `server.prechk.patch`에서 가져온 이름의 `__init__.__globals__` —
#       규칙 ①을 정면으로 **통과하면서** 모듈 네임스페이스 전체에 닿는다.
#
# **그래서 규칙 ③④도 역전한다.** round19 실측(`server/vwx/**` 12모듈 전수):
#   · bare 호출되는 **내장** 이름 24개  · 어떤 위치로든 참조되는 내장 이름 35개
#   · 던더 **속성** 접근 1종(`__init__` — `reader.py:74·88`의 `super().__init__(detail)`)
#   · 던더 **이름** 참조 1종(`__all__` — `server/vwx/__init__.py`)
#   · 던더꼴 문자열 리터럴 **0건**
# 그 다섯을 손으로 동결하고 **그 밖은 전부 위반**으로 센다(규칙 ⑤~⑨). 금지 목록이 아니다.
#
# **던더 속성 전면 금지는 불가능했다 — 이유를 적는다.** 처방 기준이 "먼저 재라, 0건이면
# 전면 금지"였는데 실측이 0건이 아니다: `reader.py`가 예외 두 클래스에서
# `super().__init__(detail)`를 쓴다. 이것을 없애려면 프로덕션을 고쳐야 하고 이번 라운드는
# **테스트만** 고친다. 그래서 전면 금지 대신 `__init__` **한 항목만** 화이트리스트에 남겼다.
# 형태 26이 노리는 `__globals__`는 그 다음 홉에서 걸린다 — `__init__`을 허용해도 형태 26은
# 잡힌다는 뜻이고, 아래 표가 그 정확도를 실측한다.
#
# **잔여 구멍 하나를 정직하게 적는다.** `apply.py:345`의 `getattr(entry, field)`는 속성
# 이름이 **런타임 변수**다. 그래서 `getattr`를 호출 화이트리스트에서 뺄 수 없고
# `getattr(x, 런타임에_조립한_던더)` 경로는 이 게이트가 정적으로 막지 못한다. 리터럴 경로는
# 규칙 ⑨(던더꼴 문자열 리터럴 금지)가 막는다 — `"__cla" + "ss__"` 같은 상수 접합도 접어서
# 본다. 남는 것은 런타임 조립뿐이고, 그것을 막으려면 `apply.py`의 필드 순회를 바꿔야 하므로
# **프로덕션 변경 없이는 불가능**하다.
#
# **열거가 남은 규칙이 어느 것인지.** 새 규칙 ⑤~⑨는 전부 허용 목록이다. 열거가 남은 곳은
# 구 규칙 ③④(`_R18_SEAL_FORBIDDEN_BARE_CALLEES`·`_R18_SEAL_FORBIDDEN_NAMES`)이고, 그것은
# **지우지 않고 병존**시킨다 — 새 게이트가 구 게이트의 합집합이며 아래 포함관계 테스트가
# 그것을 실측한다. 구 규칙 ①(등기부)은 **모듈명 단위**라는 한계가 남는다: 등기된 모듈 안의
# 무엇이든 쓸 수 있고, 형태 26이 정확히 그 틈으로 들어왔다(그래서 규칙 ⑧이 필요했다).

#: 규칙 ⑤ — `server/vwx/**`가 **bare 호출하는 내장** 전수. 손으로 동결했다(round19 실측 24).
_R19_ALLOWED_BUILTIN_CALLEES = frozenset(
    {
        "ValueError",
        "all",
        "any",
        "bool",
        "dict",
        "enumerate",
        "frozenset",
        "getattr",
        "int",
        "isinstance",
        "len",
        "list",
        "max",
        "min",
        "next",
        "ord",
        "range",
        "set",
        "sorted",
        "str",
        "sum",
        "super",
        "tuple",
        "zip",
    }
)

#: 규칙 ⑥ — 호출이 아니어도(주석·`except` 절·타입 표기 포함) 참조되는 내장 전수(실측 35).
#: 호출 화이트리스트의 진부분집합이 아니라 **초집합**이다 — 이름으로만 쓰이는 11개가 더 있다.
#: 두 표를 나눈 이유: `_f = exec` 뒤 `_f(...)`처럼 **호출 자리에 이름이 안 보이는** 형태를
#: 규칙 ⑤ 혼자서는 못 잡는다.
_R19_ALLOWED_BUILTIN_NAMES = _R19_ALLOWED_BUILTIN_CALLEES | frozenset(
    {
        "AttributeError",
        "Exception",
        "ImportError",
        "KeyError",
        "LookupError",
        "UnicodeDecodeError",
        "bytearray",
        "bytes",
        "float",
        "object",
        "property",
    }
)

#: 규칙 ⑦ — 던더 **이름** 화이트리스트. 실측 1종. `ctx`를 가리지 않는다 —
#: `__builtins__ = {...}` 같은 **대입**도 로더 도달 통로이므로 Store도 센다.
_R19_ALLOWED_DUNDER_NAMES = frozenset({"__all__"})

#: 규칙 ⑧ — 던더 **속성** 화이트리스트. 실측 1종(`super().__init__`). 위 주석 참조.
_R19_ALLOWED_DUNDER_ATTRIBUTES = frozenset({"__init__"})


def _r19_is_dunder(name: str) -> bool:
    return len(name) > 4 and name.startswith("__") and name.endswith("__")


def _r19_folded_string(node) -> str | None:
    """상수 문자열을 **접어서** 돌려준다 — `"__cla" + "ss__"`도 한 값으로 본다.

    쪼갠 조각(`"__cla"`·`"ss__"`)은 각각으로는 던더꼴이 아니다. 접지 않으면 규칙 ⑨가
    쪼개기 한 번에 무력해진다(형태 23·24가 정확히 그 수법이다).
    """
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _r19_folded_string(node.left)
        right = _r19_folded_string(node.right)
        return None if left is None or right is None else left + right
    return None


def _r19_import_seal_violations(
    source: str,
    *,
    registry: frozenset[str] = _REGISTERED_VWX_IMPORTS,
    builtin_callees: frozenset[str] = _R19_ALLOWED_BUILTIN_CALLEES,
    builtin_names: frozenset[str] = _R19_ALLOWED_BUILTIN_NAMES,
    dunder_names: frozenset[str] = _R19_ALLOWED_DUNDER_NAMES,
    dunder_attributes: frozenset[str] = _R19_ALLOWED_DUNDER_ATTRIBUTES,
) -> list[str]:
    """구 봉인 ∪ 역전된 규칙 ⑤~⑨. 구 게이트를 **감싼다** — 포함관계가 정의상 성립하고
    아래 `test_r19_the_new_seal_contains_the_round18_seal`이 표 위에서 그것을 실측한다.

    네 화이트리스트를 인자로 뺀 것은 표 자체에 대조군을 붙이기 위해서다
    (`test_r19_shrinking_any_whitelist_makes_production_fail`).
    """
    import builtins

    violations = set(_import_seal_violations(source, registry=registry))
    for node in ast.walk(ast.parse(source)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and hasattr(builtins, node.func.id)
            and node.func.id not in builtin_callees
        ):
            violations.add(f"unregistered-builtin-call:{node.func.id}")
        if isinstance(node, ast.Name):
            if _r19_is_dunder(node.id):
                if node.id not in dunder_names:
                    violations.add(f"unregistered-dunder-name:{node.id}")
            elif (
                isinstance(node.ctx, ast.Load)
                and hasattr(builtins, node.id)
                and node.id not in builtin_names
            ):
                violations.add(f"unregistered-builtin-name:{node.id}")
        if (
            isinstance(node, ast.Attribute)
            and _r19_is_dunder(node.attr)
            and node.attr not in dunder_attributes
        ):
            violations.add(f"unregistered-dunder-attribute:{node.attr}")
        if isinstance(node, (ast.Constant, ast.BinOp)):
            folded = _r19_folded_string(node)
            if folded is not None and _r19_is_dunder(folded):
                violations.add(f"dunder-literal:{folded}")
    return sorted(violations)


def _r19_production_builtin_usage() -> dict[str, set[str]]:
    """프로덕션 실측 — **화이트리스트와 대조하기 위해서만** 쓴다(파생 금지).

    스코프를 문장에 적는다(round17 #7 규율): `VWX_MODULES`가 재귀로 모은
    `server/vwx/**` **전 모듈**을 읽는다. 좁히면 이 문장부터 고쳐야 한다.
    """
    import builtins

    found: dict[str, set[str]] = {
        "callees": set(),
        "names": set(),
        "dunder_names": set(),
        "dunder_attributes": set(),
    }
    for module in VWX_MODULES:
        for node in ast.walk(ast.parse(module.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and hasattr(builtins, node.func.id)
            ):
                found["callees"].add(node.func.id)
            if isinstance(node, ast.Name):
                if _r19_is_dunder(node.id):
                    found["dunder_names"].add(node.id)
                elif isinstance(node.ctx, ast.Load) and hasattr(builtins, node.id):
                    found["names"].add(node.id)
            if isinstance(node, ast.Attribute) and _r19_is_dunder(node.attr):
                found["dunder_attributes"].add(node.attr)
    return found


#: 규칙 ⑤~⑧의 화이트리스트 넷 — 전단사·행삭제 프로브가 이 표를 순회한다.
_R19_WHITELISTS = (
    ("callees", "unregistered-builtin-call", _R19_ALLOWED_BUILTIN_CALLEES),
    ("names", "unregistered-builtin-name", _R19_ALLOWED_BUILTIN_NAMES),
    ("dunder_names", "unregistered-dunder-name", _R19_ALLOWED_DUNDER_NAMES),
    ("dunder_attributes", "unregistered-dunder-attribute", _R19_ALLOWED_DUNDER_ATTRIBUTES),
)

_R19_WHITELIST_KINDS = frozenset({"callees", "names", "dunder_names", "dunder_attributes"})

#: **감사가 준 대조군을 그대로 옮긴 표** — caught 4 / MISSED 4.
#: 열: (id, 심는 소스, 구 봉인이 내는 것, 새 봉인이 내는 것 전수).
#: `caught` 여부는 세 번째 열이 비었는지로 **파생**한다 — 손으로 적으면 어긋날 수 있다.
_R19_SEAL_PLANTS = (
    (
        "caught:aliased_import_module",
        'from importlib import import_module as _imp\n\n_gate = _imp("server.bridge")',
        ("unregistered-import:importlib",),
        ("unregistered-import:importlib",),
    ),
    (
        "caught:relative_parent_package",
        "from ..safety.gate import SafetyGate  # noqa: F401",
        ("relative-import:..safety.gate",),
        ("relative-import:..safety.gate",),
    ),
    (
        "caught:bare_exec",
        '_ns: dict = {}\nexec("import server.bridge", _ns)',
        ("forbidden-call:exec",),
        (
            "forbidden-call:exec",
            "unregistered-builtin-call:exec",
            "unregistered-builtin-name:exec",
        ),
    ),
    (
        "caught:builtins_namespace_subscript",
        '_gate = __builtins__["__import__"]("server.safety")',
        ("forbidden-name:__builtins__",),
        (
            "dunder-literal:__import__",
            "forbidden-name:__builtins__",
            "unregistered-dunder-name:__builtins__",
        ),
    ),
    (
        # 형태 23 — `globals`는 금지 호출자 넷에 없고 이름은 리터럴 접합이다.
        "missed:globals_builtins_subscript",
        '_gate = globals()["__bui" + "ltins__"]["__imp" + "ort__"]("server.bridge")',
        (),
        (
            "dunder-literal:__builtins__",
            "dunder-literal:__import__",
            "unregistered-builtin-call:globals",
            "unregistered-builtin-name:globals",
        ),
    ),
    (
        # 형태 24 — `vars()` 변형. 한 홉 더 거쳐 호출 자리에서 이름이 사라진다.
        "missed:vars_builtins_subscript",
        '_ns = vars()\n_gate = _ns["__bui" + "ltins__"]["__imp" + "ort__"]("server.safety")',
        (),
        (
            "dunder-literal:__builtins__",
            "dunder-literal:__import__",
            "unregistered-builtin-call:vars",
            "unregistered-builtin-name:vars",
        ),
    ),
    (
        # 형태 25 — import 문 0개로 `SourceFileLoader`(22번째 형태)에 닿는다.
        "missed:subclasses_walk_to_loader",
        "_loaders = ().__class__.__base__.__subclasses__()",
        (),
        (
            "unregistered-dunder-attribute:__base__",
            "unregistered-dunder-attribute:__class__",
            "unregistered-dunder-attribute:__subclasses__",
        ),
    ),
    (
        # 형태 26 — 규칙 ①을 **통과하는** 등기 모듈로 네임스페이스 전체에 닿는다.
        # `__init__`은 화이트리스트에 있으므로 걸리는 것은 `__globals__` 한 홉뿐이다.
        "missed:registered_module_globals",
        "from server.prechk.patch import classify_patch_value\n\n"
        "_ns = classify_patch_value.__init__.__globals__",
        (),
        ("unregistered-dunder-attribute:__globals__",),
    ),
)

#: 표의 축소 트립와이어 — 행을 하나 지우면 어긋난다.
_R19_SEAL_PLANT_IDS = frozenset(
    {
        "caught:aliased_import_module",
        "caught:relative_parent_package",
        "caught:bare_exec",
        "caught:builtins_namespace_subscript",
        "missed:globals_builtins_subscript",
        "missed:vars_builtins_subscript",
        "missed:subclasses_walk_to_loader",
        "missed:registered_module_globals",
    }
)


@pytest.mark.parametrize(
    "plant,r18_expected,r19_expected",
    [(plant, old, new) for _, plant, old, new in _R19_SEAL_PLANTS],
    ids=[name for name, _, _, _ in _R19_SEAL_PLANTS],
)
def test_r19_every_audited_bypass_form_is_caught_by_the_inverted_seal(
    plant, r18_expected, r19_expected
):
    """감사 대조군 8행(caught 4 / MISSED 4) — **여덟 전부** 새 봉인에 걸린다.

    구 봉인이 내는 것도 같은 행에서 함께 고정한다: MISSED 4행은 구 봉인이 **빈 목록**이고
    (그것이 "놓쳤다"의 실측 정의다) 새 봉인은 비지 않는다.

    죽이는 뮤테이션:
      · 규칙 ⑤(내장 호출 화이트리스트)를 되돌리면 형태 23·24가 빈 목록을 받아 실패한다.
      · 규칙 ⑧(던더 속성 화이트리스트)을 되돌리면 형태 25·26이 실패한다.
      · 규칙 ⑨(던더꼴 리터럴)의 **접기**를 빼면 형태 23·24의 두 리터럴 행이 사라져 실패한다.
      · `_R19_ALLOWED_DUNDER_ATTRIBUTES`에서 `"__init__"`을 빼면 형태 26의 기대값이
        한 항목 늘어 실패한다 — 화이트리스트의 **정확도**까지 이 행이 고정한다.
    """
    source = APPLY_SOURCE + "\n\n" + plant + "\n"
    assert _import_seal_violations(source) == sorted(r18_expected)
    assert _r19_import_seal_violations(source) == sorted(r19_expected)
    assert _r19_import_seal_violations(source) != [], "새 봉인이 놓쳤다"


def test_r19_the_audit_control_table_is_four_caught_and_four_missed():
    """표 행삭제 프로브 + 감사 진술 대조 — caught 4 / MISSED 4가 **실측과 일치**한다.

    죽이는 뮤테이션:
      · 어느 행을 지워도 id 집합 단정이 실패한다.
      · 구 봉인을 늘려 MISSED 행 하나가 걸리게 되면 4/4가 깨져 실패한다(그때는 감사 표를
        갱신해야 하고, 그 갱신 부담이 열거 전략의 비용이다).
    """
    ids = [name for name, _, _, _ in _R19_SEAL_PLANTS]
    assert len(ids) == len(set(ids)) == len(_R19_SEAL_PLANT_IDS) == 8
    assert set(ids) == _R19_SEAL_PLANT_IDS

    caught = {
        name
        for name, plant, _old, _new in _R19_SEAL_PLANTS
        if _import_seal_violations(APPLY_SOURCE + "\n\n" + plant + "\n")
    }
    assert caught == {name for name in ids if name.startswith("caught:")}
    assert len(caught) == 4 and len(ids) - len(caught) == 4
    # 라벨과 실측이 어긋나면 표가 거짓말을 하고 있는 것이다.
    for name, _plant, old, _new in _R19_SEAL_PLANTS:
        assert bool(old) is name.startswith("caught:"), name

    # 표의 **기대 열** 자체에 독립 핀을 박는다 — 행별 등식 단정이 느슨해져도 이것이 남는다.
    # ① 선언된 위반 어휘가 아홉 종(구 규칙 넷 + 새 규칙 다섯)을 **전수** 덮는다.
    declared = {violation for _n, _p, _o, new in _R19_SEAL_PLANTS for violation in new}
    assert {violation.split(":", 1)[0] for violation in declared} == {
        "unregistered-import",
        "relative-import",
        "forbidden-call",
        "forbidden-name",
        "unregistered-builtin-call",
        "unregistered-builtin-name",
        "unregistered-dunder-name",
        "unregistered-dunder-attribute",
        "dunder-literal",
    }
    # ② 선언 열과 실측이 **행 단위로** 일치한다 — 어느 행의 기대값이 느슨해지거나 틀려도
    #    여기서 걸린다(행별 등식 단정을 지우는 편집에 대한 독립 핀).
    assert {name: sorted(new) for name, _p, _o, new in _R19_SEAL_PLANTS} == {
        name: _r19_import_seal_violations(APPLY_SOURCE + "\n\n" + plant + "\n")
        for name, plant, _o, _new in _R19_SEAL_PLANTS
    }
    # ③ 구 봉인이 내는 것도 행 단위로 고정한다 — caught/MISSED 라벨의 근거다.
    assert {name: sorted(old) for name, _p, old, _n in _R19_SEAL_PLANTS} == {
        name: _import_seal_violations(APPLY_SOURCE + "\n\n" + plant + "\n")
        for name, plant, _o, _new in _R19_SEAL_PLANTS
    }


def test_r19_the_new_seal_contains_the_round18_seal():
    """포함관계 실측 — 구 게이트가 잡는 것은 새 게이트도 **전부** 잡는다(병존의 근거).

    구 표 16행 + round18 표 13행 + round19 표 8행 전수에서 확인한다.

    죽이는 뮤테이션: `_r19_import_seal_violations`가 구 게이트를 합집합하지 않으면 실패한다.
    """
    plants = (
        [plant for _, plant, _ in _CONSOLE_IMPORT_PLANTS]
        + [plant for _, plant, _, _ in _ROUND18_SEAL_BYPASS_PLANTS]
        + [plant for _, plant, _ in _ROUND18_SEAL_RULE_PLANTS]
        + [plant for _, plant, _, _ in _R19_SEAL_PLANTS]
    )
    assert len(plants) == 16 + 6 + 7 + 8, len(plants)
    for plant in plants:
        source = APPLY_SOURCE + "\n\n" + plant + "\n"
        old = set(_import_seal_violations(source))
        new = set(_r19_import_seal_violations(source))
        assert old <= new, sorted(old - new)
        assert new != set(), plant


def test_r19_the_inverted_seal_reports_nothing_on_clean_production():
    """클린 대조군 BYPASS — 심지 않은 프로덕션 12모듈 전수에서 새 봉인이 0건이다.

    새 규칙이 현행 프로덕션을 깨면 **규칙이 틀린 것**이다. 여기가 그 판정 자리다.
    """
    assert VWX_MODULES, "스캔 대상이 0개면 이 확인은 공허하다"
    dirty = {
        str(module): _r19_import_seal_violations(module.read_text(encoding="utf-8"))
        for module in VWX_MODULES
    }
    assert {path: found for path, found in dirty.items() if found} == {}


def test_r19_the_four_whitelists_are_a_bijection_onto_production():
    """화이트리스트 넷 전단사 — **더해도 지워도** 실패한다.

    `stale`(쓰지 않는데 등기된 항목)을 금지하는 것이 핵심이다 — 선제 등기는 문을 미리
    열어 두는 것이고 화이트리스트를 무력화하는 유일한 길이다(round18 등기부와 같은 규율).

    죽이는 뮤테이션: 어느 화이트리스트에 `"globals"`나 `"__class__"`를 미리 넣어 두면
    `stale`이 비지 않아 실패한다 — 형태 23·25를 조용히 통과시키는 유일한 편집이 막힌다.
    """
    observed = _r19_production_builtin_usage()
    assert set(observed) == _R19_WHITELIST_KINDS
    for kind, _label, whitelist in _R19_WHITELISTS:
        missing = sorted(observed[kind] - whitelist)
        stale = sorted(whitelist - observed[kind])
        assert missing == [], f"{kind}: 화이트리스트 밖의 프로덕션 사용 {missing}"
        assert stale == [], f"{kind}: 프로덕션이 쓰지 않는 등기 {stale} — 미리 열어 둔 문이다"
    # 규모 고정 — 조용히 부풀지 않는다(round19 실측).
    assert len(_R19_ALLOWED_BUILTIN_CALLEES) == 24
    assert len(_R19_ALLOWED_BUILTIN_NAMES) == 35
    assert len(_R19_ALLOWED_DUNDER_NAMES) == 1
    assert len(_R19_ALLOWED_DUNDER_ATTRIBUTES) == 1
    # 두 내장 표는 **다르다** — 이름으로만 쓰이는 11개가 호출 화이트리스트에는 없다.
    assert _R19_ALLOWED_BUILTIN_CALLEES < _R19_ALLOWED_BUILTIN_NAMES
    assert len(_R19_ALLOWED_BUILTIN_NAMES - _R19_ALLOWED_BUILTIN_CALLEES) == 11


@pytest.mark.parametrize(
    "kind,label,dropped",
    [
        (kind, label, dropped)
        for kind, label, whitelist in _R19_WHITELISTS
        for dropped in sorted(whitelist)
    ],
)
def test_r19_shrinking_any_whitelist_makes_production_fail(kind, label, dropped):
    """행삭제 프로브 61행 — 어느 화이트리스트에서 **어느 한 항목**을 빼도 프로덕션이 걸린다.

    곧 이 표들에 공허한 행은 하나도 없다. 각 행은 실제로 무언가를 허용하고 있다.

    죽이는 뮤테이션: 화이트리스트를 프로덕션에서 파생하면(자기충족) 이 단정이 원리적으로
    성립하지 않는다 — 파생 표는 무엇을 빼도 스스로를 다시 채운다.
    """
    overrides = {
        "builtin_callees": _R19_ALLOWED_BUILTIN_CALLEES,
        "builtin_names": _R19_ALLOWED_BUILTIN_NAMES,
        "dunder_names": _R19_ALLOWED_DUNDER_NAMES,
        "dunder_attributes": _R19_ALLOWED_DUNDER_ATTRIBUTES,
    }
    key = {
        "callees": "builtin_callees",
        "names": "builtin_names",
        "dunder_names": "dunder_names",
        "dunder_attributes": "dunder_attributes",
    }[kind]
    overrides[key] = overrides[key] - {dropped}
    offenders = [
        str(module)
        for module in VWX_MODULES
        if f"{label}:{dropped}"
        in _r19_import_seal_violations(module.read_text(encoding="utf-8"), **overrides)
    ]
    assert offenders, f"{kind}/{dropped}: 이 행은 아무것도 허용하지 않는다 — 공허하다"


def test_r19_the_folding_literal_rule_is_not_defeated_by_splitting():
    """규칙 ⑨ 경계 — 쪼개기·중첩 접합·비던더는 각각 제대로 갈린다.

    죽이는 뮤테이션: `_r19_folded_string`이 `BinOp`를 접지 않으면 첫 두 단정이 실패하고,
    던더 판정이 `startswith("__")`만 보면 마지막 단정이 거짓 양성을 낸다.
    """

    def folded(expression: str):
        return _r19_folded_string(ast.parse(expression, mode="eval").body)

    assert folded('"__cla" + "ss__"') == "__class__"
    assert folded('"__" + "sub" + "classes" + "__"') == "__subclasses__"
    assert folded('"plain"') == "plain"
    assert folded('prefix + "ss__"') is None
    assert _r19_is_dunder("__class__") is True
    assert _r19_is_dunder("__cla") is False
    assert _r19_is_dunder("ss__") is False
    assert _r19_is_dunder("____") is False
    # 쪼갠 조각만으로는 위반이 아니고, 접은 값이 던더일 때만 걸린다.
    assert _r19_import_seal_violations(APPLY_SOURCE + '\n\n_x = "__cla" + "ss__"\n') == [
        "dunder-literal:__class__"
    ]
    assert _r19_import_seal_violations(APPLY_SOURCE + '\n\n_x = "__cla" + "ss"\n') == []


# ==========================================================================
# --- round19 막다른 길 어휘 (DeadEndVocab) ---
#
# [round19 major#4] 기제는 **상태를 거부 사유로 번역하는 자리가 상태의 세부를 버린다**이다.
# R18-E는 `payload["types"]`에서 "확인할 후보 0건인데 확인 대기라 적는 것"을 고쳤지만,
# **조작자가 마지막에 읽는 표면**인 `handoff.exclusions`는 고치지 않았다. 그 자리는
# `status != resolved`를 전부 `type_confirmation_pending` 한 코드로 뭉갰고
# `TypeResolution.hard_stop_code`를 보지 않았다 — 한 payload가 같은 후보를 두고
# "확인 경로 없음, 하드 스톱"과 "확인 대기"를 **동시에** 말했다.
#
# 이 섹션이 세우는 것 셋:
#   ① 번역 자리 **등기부 + 전단사** — `server/vwx/` 전 모듈에서 상위 판정 상태를 닫힌 어휘
#      코드로 옮기는 자리를 AST로 전수하고, 새 자리가 생기면 등기 없이는 통과하지 못한다.
#   ② **모순 불변식 대조군** — 같은 payload의 두 표면이 같은 후보에 모순된 말을 하지 않는다.
#      이것이 진짜 처방이다: 자리를 하나 고치는 것이 아니라 표면 사이의 일관성을 단정한다.
#   ③ **고칠 축(fix axis) 구별성** — 신설·재등재 코드가 "있어야 조작자가 무엇을 고칠지 옳게
#      판단한다"는 근거를, 리터럴 비교가 아니라 **축 특정 가능성**으로 단정한다.
#      ③의 쌍 범위(`fid_below_minimum`·`address_below_minimum`)는
#      `server/tests/test_autopatch_fid.py`의 round19 섹션이 따로 단정한다.
# ==========================================================================

_R19_LIBRARY = [("MegaPointe", [("Mode 1", 24), ("Mode 2", 16)])]
_R19_ALIAS_MODE_1 = {"MegaPointe": {"type": "MegaPointe", "mode": "Mode 1"}}
_R19_ALIAS_MODE_9 = {"MegaPointe": {"type": "MegaPointe", "mode": "Mode 9"}}


#: 판정 세부를 담는 칸을 이름 규약으로 고른다 — `status` · `*_code` · `*_kind`.
#: 표가 아니라 **규약**이라, 새 칸이 생기면 아래 등기부 전단사가 자동으로 그것을 요구한다.
def _r19_is_verdict_detail(field_name: str) -> bool:
    return field_name == "status" or field_name.endswith(("_code", "_kind"))


def _r19_verdict_detail_fields() -> dict[str, tuple[str, ...]]:
    """판정 세부 칸을 가진 dataclass를 `server/vwx/` 전 모듈에서 모은다.

    읽는 범위는 `_discover_modules(Path("server/vwx"))`가 재귀로 낸 `server/vwx` 아래
    모든 `.py`다 — 하위 패키지가 생겨도 스코프가 줄지 않는다.
    """
    import dataclasses
    import importlib

    found: dict[str, tuple[str, ...]] = {}
    for path in _discover_modules(Path("server/vwx")):
        if path.stem == "__init__":
            continue
        module = importlib.import_module(f"server.vwx.{path.stem}")
        for name in dir(module):
            obj = getattr(module, name)
            if not (isinstance(obj, type) and dataclasses.is_dataclass(obj)):
                continue
            if not obj.__module__.startswith("server.vwx."):
                continue
            fields = tuple(
                f.name for f in dataclasses.fields(obj) if _r19_is_verdict_detail(f.name)
            )
            if fields:
                found[obj.__name__] = fields
    return found


#: 닫힌 어휘 판정을 **짓는** 호출 — 이 이름이 함수 본문에 있으면 그 함수는 판정을 낸다.
_R19_VERDICT_BUILDERS = (
    "_exclusion",
    "PatchTargetExclusion",
    "_skipped_check",
    "PatchPlanRejection",
    "TypeHardStop",
)


def _r19_translation_sites() -> tuple[tuple[str, str, str, tuple[str, ...]], ...]:
    """상태를 닫힌 어휘 코드로 번역하는 자리를 `server/vwx/` 전 모듈에서 전수로 뽑는다.

    읽는 범위는 `_discover_modules(Path("server/vwx"))`가 재귀로 낸 `server/vwx` 아래
    모든 `.py`다. 한 자리는 (모듈, 함수, 상위 상태 dataclass, 그 함수가 **읽는** 판정 세부 칸)
    이고, 자리로 치는 조건은 둘 다다:
      · 파라미터 주석에 판정 세부 칸을 가진 dataclass 이름이 있다(= 상위 상태를 받는다), **그리고**
      · 본문이 판정을 짓거나(`_R19_VERDICT_BUILDERS`) 판정 세부 칸을 읽는다.
    """
    detail = _r19_verdict_detail_fields()
    sites: list[tuple[str, str, str, tuple[str, ...]]] = []
    for path in _discover_modules(Path("server/vwx")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            called = {
                getattr(call.func, "id", None)
                for call in ast.walk(node)
                if isinstance(call, ast.Call)
            }
            read = {item.attr for item in ast.walk(node) if isinstance(item, ast.Attribute)}
            annotations = " ".join(
                ast.unparse(arg.annotation)
                for arg in list(node.args.args) + list(node.args.kwonlyargs)
                if arg.annotation is not None
            )
            for cls, fields in sorted(detail.items()):
                if cls not in annotations:
                    continue
                if not (called.intersection(_R19_VERDICT_BUILDERS) or read.intersection(fields)):
                    continue
                sites.append((path.name, node.name, cls, tuple(f for f in fields if f in read)))
    return tuple(sorted(sites))


#: 번역 자리 **등기부**. (모듈, 함수, 상위 상태, 읽는 판정 세부 칸, 위임처, 근거).
#: 마지막 칸은 **행동 게이트 이름**이다 — 문장이 아니라 이 파일에 실재하는 테스트를 가리킨다.
#: 자리가 읽는 칸이 전부가 아니어도 되는 이유는 그 자리가 세부를 **위임**하거나, 남은 칸이
#: 낼 수 있는 코드를 바꾸지 않기 때문이며, 그 주장은 근거 칸의 게이트가 실행으로 확인한다.
_R19_TRANSLATION_SITES = (
    (
        "apply.py",
        "_unresolved_type_verdict",
        "TypeResolution",
        ("hard_stop_code", "incompleteness_kind"),
        None,
        # `status`는 읽지 않는다: 세 상태(하드 스톱 · 관측 불완전 · 진짜 확인 대기)의 구별은
        # 나머지 두 칸으로 전부 재현된다. 그 주장은 아래 게이트가 **전 상태 코퍼스**로 잰다.
        "test_r19_no_two_surfaces_contradict_each_other_about_one_candidate",
    ),
    (
        "apply.py",
        "_unresolved_type_exclusion",
        "TypeResolution",
        (),
        "_unresolved_type_verdict",
        "test_r19_no_two_surfaces_contradict_each_other_about_one_candidate",
    ),
    (
        "apply.py",
        "build_patch_handoff",
        "TypeResolution",
        ("status",),
        "_unresolved_type_verdict",
        "test_r19_no_two_surfaces_contradict_each_other_about_one_candidate",
    ),
    (
        "apply.py",
        "screen_idempotent",
        "TypeResolution",
        (),
        "_unresolved_type_verdict",
        "test_r19_the_idempotency_screen_says_the_same_thing_as_the_type_table",
    ),
    (
        # [round19 major#4 형제 필드] 판정을 **짓지는** 않지만 판정 세부를 읽어 상위 갈래를
        # 가른다. `status`를 안 보던 이전 판은 확정되지 않은 해상 결과의 타입·모드로
        # 점유자와 대조해 `already_patched_identical`까지 갈 수 있었다.
        "apply.py",
        "_expected_identity",
        "TypeResolution",
        ("status",),
        None,
        "test_r19_the_idempotency_screen_says_the_same_thing_as_the_type_table",
    ),
)


def _r19_translation_registry_keys() -> tuple[tuple[str, str, str, tuple[str, ...]], ...]:
    return tuple(
        sorted(
            (module, func, cls, reads) for module, func, cls, reads, _, _ in _R19_TRANSLATION_SITES
        )
    )


def test_r19_the_translation_site_registry_is_a_bijection_onto_production():
    """[round19 major#4] 상태를 사유로 번역하는 자리가 늘거나 줄면 여기서 먼저 깨진다.

    죽이는 뮤테이션:
      · `apply._unresolved_type_verdict`에서 `resolution.hard_stop_code` 갈래를 지우면
        그 자리의 읽는 칸이 줄어 등기부와 어긋난다(= R18-E 무시 복귀가 여기서 잡힌다).
      · 같은 함수에서 `resolution.incompleteness_kind` 갈래를 지워도 같다.
      · `screen_idempotent`에 미확정 갈래를 하나 더 만들어도, 새 자리는 등기 없이 통과하지 못한다.
    """
    assert _r19_translation_sites() == _r19_translation_registry_keys()
    labels = [(module, func, cls) for module, func, cls, _, _, _ in _R19_TRANSLATION_SITES]
    assert len(labels) == len(set(labels))


@pytest.mark.parametrize("index", range(len(_R19_TRANSLATION_SITES)))
def test_r19_deleting_any_translation_registry_row_breaks_the_bijection(index: int):
    """행 삭제 프로브 — 등기부에서 어느 행을 지워도 프로덕션 전수와 어긋난다."""
    shrunk = _R19_TRANSLATION_SITES[:index] + _R19_TRANSLATION_SITES[index + 1 :]
    keys = tuple(sorted((module, func, cls, reads) for module, func, cls, reads, _, _ in shrunk))
    assert keys != _r19_translation_sites()


def test_r19_every_translation_row_names_a_gate_that_actually_exists():
    """근거 칸이 **실재하는 테스트**를 가리킨다 — 문장으로 때우면 다음 라운드에 또 뚫린다.

    죽이는 뮤테이션: 근거 칸을 산문으로 바꾸면 이름 조회가 실패한다.
    """
    for module, func, _cls, _reads, delegate, gate in _R19_TRANSLATION_SITES:
        assert gate.startswith("test_r19_"), (module, func, gate)
        assert callable(globals().get(gate)), (module, func, gate)
        if delegate is not None:
            # 위임처도 프로덕션에 실재해야 한다 — 없는 이름을 적어 두면 등기가 거짓이 된다.
            from server.vwx import apply as apply_module

            assert hasattr(apply_module, delegate), (module, func, delegate)


# ---- ② 모순 불변식 대조군 -------------------------------------------------
#
# 같은 payload 안에서 `types` 표와 `handoff.exclusions`가 **같은 후보**에 대해 서로 다른
# 말을 하지 않는다. 자리 하나를 고치는 것으로는 이 불변식을 세울 수 없다 — 그래서 이것이
# major#4의 진짜 처방이다.

#: (시나리오, 도면 타입, 도면 모드, 도면 점유폭, 별칭, 포트 kwargs) — `assumption_72="go"` 고정.
#: 아래 게이트가 이 코퍼스가 `TYPE_RESOLUTION_STATUS` **전 상태**에 닿음을 단정하므로
#: 상태가 하나 늘면 코퍼스 없이는 통과하지 못한다.
_R19_STATE_CORPUS = (
    ("resolved", "MegaPointe", "Mode 1", 24, _R19_ALIAS_MODE_1, {}),
    ("candidates_presented", "MegaPointe", "Mode 1", 24, None, {}),
    ("footprint_choosable", "MegaPointe", "Mode 1", 16, _R19_ALIAS_MODE_1, {}),
    ("footprint_unmatchable", "MegaPointe", "Mode 1", 99, _R19_ALIAS_MODE_1, {}),
    (
        "footprint_unverified",
        "MegaPointe",
        "Mode 1",
        99,
        _R19_ALIAS_MODE_1,
        {"modes_truncated": True},
    ),
    ("type_absent", "Nope", "Mode 1", 24, None, {}),
    ("mode_absent", "MegaPointe", "Mode 9", 24, _R19_ALIAS_MODE_9, {}),
    ("library_truncated", "MegaPointe", "Mode 9", 24, None, {"modes_truncated": True}),
    ("name_unusable", "---", "Mode 1", 24, None, {}),
)


def _r19_library_port(port_kwargs):
    """시나리오의 포트. `partial_channels`는 **모드 하나만** 채널 수를 못 읽는 실측 형태다.

    `LibraryRigPort(channels_readable=False)`는 전부를 못 읽어 점유폭 대조 자체가 수행되지
    않는다 — 그 상태는 이 게이트가 재려는 것(맞는 모드의 **부재를 단정할 수 없다**)이 아니다.
    """
    from server.tests.test_autopatch_types import LibraryRigPort

    kwargs = dict(port_kwargs)
    # [round21 R20-D] 폐기 행 스냅샷 — 열거는 `ok=true`로 끝까지 왔고 그 안의 행이
    # 슬롯 번호를 갖고 있지 않다. 절단(`modes_truncated`)과도 판독 실패
    # (`partial_channels`)와도 다른 세 번째 축이라 포트도 따로 둔다.
    if kwargs.pop("slotless_modes", False):
        return _r19_slotless_mode_port(kwargs)
    if not kwargs.pop("partial_channels", False):
        return LibraryRigPort(_R19_LIBRARY, **kwargs)

    class _PartialChannelPort(LibraryRigPort):
        def _channels(self, type_index: int, mode_index: int, path: str) -> dict:
            if mode_index == 2:
                return {"ok": False, "path": path, "error": "path segment not found"}
            return super()._channels(type_index, mode_index, path)

    return _PartialChannelPort(_R19_LIBRARY, **kwargs)


def _r19_slotless_mode_port(port_kwargs):
    """[round21 R20-D] DMXModes 행 하나가 슬롯 번호(`i`)를 갖고 있지 않은 포트.

    responder `safe_children`의 `probe_slots` nil / per-child `slot_confirms` 폴백이
    실제로 만드는 스냅샷이다(PRESERVE `server/prechk/inventory.py` 독스트링). 열거 응답은
    `ok=true`이고 목록도 끝까지 왔다 — **절단도 판독 실패도 아니다.**
    """
    from server.tests.test_autopatch_types import LibraryRigPort

    class _SlotlessModePort(LibraryRigPort):
        def query_state(self, path: str) -> dict:
            state = super().query_state(path)
            if not path.endswith("/DMXModes") or state.get("ok") is not True:
                return state
            children = [dict(row) for row in state["children"]]
            for row in children:
                if row.get("i") == 2:
                    row.pop("i")
            return {**state, "children": children}

    return _SlotlessModePort(_R19_LIBRARY, **dict(port_kwargs))


def _r19_resolve(scenario) -> object:
    from server.vwx.typemap import resolve_fixture_types

    _name, designed_type, mode, footprint, aliases, port_kwargs = scenario
    return resolve_fixture_types(
        [
            TypeRequest(
                candidate_id="a", instrument_type=designed_type, mode=mode, footprint=footprint
            )
        ],
        library_port=_r19_library_port(port_kwargs),
        type_aliases=aliases,
        assumption_72="go",
    )


def _r19_surfaces(scenario):
    """한 시나리오의 **두 표면**을 같은 해상 결과에서 만든다 — 조작자가 한 payload로 보는 것."""
    plan = _r19_resolve(scenario)
    payload = plan.to_dict()
    handoff = _handoff(resolutions=plan.resolutions, dry_run=False)
    return payload, payload["type_table"]["rows"][0], handoff


def test_r19_the_state_corpus_reaches_every_type_resolution_status():
    """대조군 건전성 — 코퍼스가 닫힌 상태 어휘 **전부**에 닿는다.

    `server/vwx/verdicts.py`의 `TYPE_RESOLUTION_STATUS`가 기준이다. 상태를 하나 더하면
    (예: round19가 더한 `designed_footprint_unmatchable`) 코퍼스 없이는 실패한다 —
    닿지 않는 상태가 있으면 아래 불변식이 그 상태에서 공허해진다.
    """
    from server.vwx.verdicts import TYPE_RESOLUTION_STATUS

    reached = {_r19_surfaces(scenario)[1]["status"] for scenario in _R19_STATE_CORPUS}
    assert reached == set(TYPE_RESOLUTION_STATUS)


def test_r19_no_two_surfaces_contradict_each_other_about_one_candidate():
    """[round19 major#4 · 불변식] 한 payload가 같은 후보에 모순된 말을 하지 않는다.

    세 절 전부가 **프로덕션 두 표면**을 실제로 만들어 비교한다:
      ㉠ `types.hard_stops`에 있는 후보의 전달물 배제 코드는 **그 하드 스톱 코드와 같다**.
      ㉡ `confirmation_required`가 거짓이면 배제 코드가 `type_confirmation_pending`이 **아니다**.
      ㉢ `confirmation_required`가 참이면 배제 코드가 `type_confirmation_pending`이다.

    죽이는 뮤테이션:
      · `apply._unresolved_type_verdict`의 `hard_stop_code` 갈래 제거 → ㉠·㉡이 하드 스톱
        시나리오 넷에서 실패한다(= R18-E 무시 복귀).
      · 같은 함수의 `incompleteness_kind` 갈래 제거 → ㉡이 관측 불완전 시나리오 둘에서 실패한다.
      · `typemap`의 점유폭 하드 스톱을 `TYPE_NEEDS_CONFIRMATION`으로 되돌림 → ㉠이 실패한다.
    """
    from server.vwx.verdicts import TYPE_CONFIRMATION_PENDING as PENDING

    for scenario in _R19_STATE_CORPUS:
        payload, row, handoff = _r19_surfaces(scenario)
        name = scenario[0]
        codes = [exclusion.code for exclusion in handoff.exclusions]
        stops = [stop["code"] for stop in payload["hard_stops"]]
        if row["status"] == TYPE_RESOLVED:
            assert codes == [], name
            assert stops == [], name
            continue
        assert len(codes) == 1, (name, codes)
        if stops:
            assert codes == stops, name
        if row["confirmation_required"]:
            assert codes == [PENDING], name
        else:
            assert codes != [PENDING], name


def test_r19_the_idempotency_screen_says_the_same_thing_as_the_type_table():
    """[round19 major#4 형제 표면] `screen_idempotent`도 같은 불변식을 진다.

    같은 주소에 픽스처가 이미 있는 상태에서 타입·모드가 미확정이면 이 자리가 배제를 짓는다.
    이전 판은 `_expected_identity`만 보고 `type_confirmation_pending`을 못 박아, 하드 스톱과
    관측 불완전 상태에서도 "확인 대기"라 적었다 — `build_patch_handoff`와 **같은 기제, 같은
    payload, 다른 표면**이다.

    죽이는 뮤테이션: `screen_idempotent`의 `unresolved_code`를 `TYPE_CONFIRMATION_PENDING`
    리터럴로 되돌리면 하드 스톱·관측 불완전 시나리오 여섯에서 실패한다.
    """
    from server.tests.test_autopatch_verify import _console, _record
    from server.vwx.apply import screen_idempotent
    from server.vwx.verdicts import TYPE_CONFIRMATION_PENDING as PENDING

    occupied = _console(_record(1, "1.1", "FixtureType 3", "1 Mode 1"))
    for scenario in _R19_STATE_CORPUS:
        plan = _r19_resolve(scenario)
        row = plan.to_dict()["type_table"]["rows"][0]
        if row["status"] == TYPE_RESOLVED:
            continue
        screened = screen_idempotent(
            (_candidate(candidate_id="a"),),
            address_plan=AddressPlan(entries=(_planned(candidate_id="a"),)),
            resolutions=plan.resolutions,
            console_fixtures=occupied,
        )
        codes = [exclusion.code for exclusion in screened.exclusions]
        assert len(codes) == 1, (scenario[0], codes)
        assert (codes == [PENDING]) is bool(row["confirmation_required"]), (scenario[0], codes)
        # 두 표면이 같은 후보에 **같은 코드**를 낸다 — 밀도가 갈리면 조작자가 둘 중 하나를 믿는다.
        handoff = _handoff(resolutions=plan.resolutions, dry_run=False)
        assert codes == [exclusion.code for exclusion in handoff.exclusions], scenario[0]


# ---- ③ 고칠 축(fix axis) 구별성 -------------------------------------------
#
# round18은 `fid_below_minimum`을 신설하면서 **유일한 근거를 "라벨이 가리키는 축"**으로 삼았다.
# 그런데 라벨을 주소축 문구로 통째로 바꿔도 1,480건이 전부 통과했다 — 근거를 단정하는 자리가
# 어디에도 없었다(round19 감사 M24 = 진짜 공백). round19가 신설·재등재한 코드도 같은 성질이라
# 여기서 **축 특정 가능성**을 단정한다. 리터럴 문자열 비교가 아니다.
#
# 게이트 둘:
#   A(완전성) — `verdicts.TARGET_EXCLUSION_REASON` 전 코드가 축 표에 1:1로 등기돼 있다.
#   B(구별성) — round19가 손댄 코드마다, 라벨을 **형제 축 라벨로 통째 교체**하면 프로덕션
#              payload에서 축이 더 이상 특정되지 않는다. 통과하면 라벨이 유일 근거가
#              아니라는 뜻이고, 그때는 그 코드의 존재 근거를 다시 적어야 한다.
#
# B의 쌍 범위 두 행(`fid_below_minimum` · `address_below_minimum`)은
# `server/tests/test_autopatch_fid.py`의 round19 섹션이 같은 형태로 단정한다 — 여기서는
# 축 표에만 등기한다(표가 둘이 되면 다음 라운드에 어긋난다).

#: 조작자가 **무엇을 고쳐야 하는가**의 닫힌 어휘. 코드가 늘면 이 중 하나에 배정돼야 한다.
_R19_FIX_AXES = (
    "design_address",
    "design_fid",
    "design_type_name",
    "design_footprint",
    "fixture_name",
    "user_input_range",
    "type_confirmation",
    "console_library",
    "console_patch",
    "console_read",
    "deliverable_field",
    "no_action",
)

#: 축을 **지목하는 토큰** — 라벨에서 그 축을 특정하는 어구. 게이트 B의 판별식이 쓴다.
#: 토큰은 축마다 배타적이어야 한다(아래 게이트가 그 배타성을 직접 단정한다).
_R19_AXIS_TOKENS = {
    "design_footprint": ("도면 DMX Footprint", "도면 점유폭", "점유폭 미확정"),
    "console_library": ("라이브러리",),
    "type_confirmation": ("사용자 확인",),
    "design_type_name": ("도면 타입 이름",),
}

#: 배제 코드 -> 조작자가 고쳐야 할 축. `TARGET_EXCLUSION_REASON` 전수와 1:1이다.
_R19_FIX_AXIS = {
    "fid_range_exhausted": "user_input_range",
    "fid_already_in_use": "user_input_range",
    "fid_not_assigned": "user_input_range",
    "fid_below_minimum": "design_fid",
    "fid_precheck_read_incomplete": "console_read",
    "address_already_occupied": "design_address",
    "address_overlap_in_plan": "design_address",
    "address_below_minimum": "design_address",
    "address_conflicts_with_existing_fixture": "console_patch",
    "existing_fixture_identity_unconfirmed": "console_patch",
    "already_patched_identical": "no_action",
    "console_read_incomplete": "console_read",
    "fixture_name_missing": "fixture_name",
    "lua_generation_refused": "deliverable_field",
    "type_confirmation_pending": "type_confirmation",
    "fixture_type_not_in_library": "console_library",
    "dmx_mode_not_in_library": "console_library",
    "fixture_type_library_truncated": "console_library",
    "fixture_type_library_unreadable": "console_library",
    "fixture_type_name_unusable": "design_type_name",
    "footprint_unknown": "design_footprint",
    "designed_footprint_matches_no_console_mode": "design_footprint",
    # [round21 R20-D] 폐기 축 — 라이브러리는 온전히 있고 목록도 끝까지 왔다. 고칠 곳은
    # 도면도 사용자 입력도 아니라 콘솔 열거 응답이므로 `console_library` 축이다.
    "fixture_type_library_rows_discarded": "console_library",
}


def test_r19_the_fix_axis_table_is_a_bijection_onto_the_exclusion_vocabulary():
    """게이트 A — `server/vwx/verdicts.py`의 배제 어휘 전 코드가 축 표에 등기돼 있다.

    코드를 신설하면(round19가 `designed_footprint_matches_no_console_mode`를 더했듯이)
    등기 없이는 통과하지 못하고, 등기하는 순간 "조작자가 무엇을 고치는가"를 적게 된다.
    """
    from server.vwx.verdicts import TARGET_EXCLUSION_REASON

    assert set(_R19_FIX_AXIS) == set(TARGET_EXCLUSION_REASON)
    assert set(_R19_FIX_AXIS.values()) <= set(_R19_FIX_AXES)
    # 축 어휘가 비어 있는 항목을 들고 있으면 표가 느슨해진다 — 전 축이 실제로 쓰인다.
    assert set(_R19_FIX_AXIS.values()) == set(_R19_FIX_AXES)


@pytest.mark.parametrize("code", sorted(_R19_FIX_AXIS))
def test_r19_deleting_any_fix_axis_row_breaks_the_bijection(code: str):
    """행 삭제 프로브 — 축 표에서 어느 행을 지워도 배제 어휘 전수와 어긋난다."""
    from server.vwx.verdicts import TARGET_EXCLUSION_REASON

    shrunk = {key: value for key, value in _R19_FIX_AXIS.items() if key != code}
    assert set(shrunk) != set(TARGET_EXCLUSION_REASON)


def _r19_identified_axis(text: str) -> str | None:
    """이 문장이 **정확히 한 축**을 지목하면 그 축, 모호하면 `None`.

    형제 `TruncationSweep`의 쌍 범위 판별식과 같은 형태다 — 축별 토큰 집합 중 정확히 하나만
    나타나야 한다. 두 축이 함께 나타나면 조작자는 무엇을 고칠지 고를 수 없다.
    """
    hit = {
        axis for axis, tokens in _R19_AXIS_TOKENS.items() if any(token in text for token in tokens)
    }
    return next(iter(hit)) if len(hit) == 1 else None


def test_r19_the_axis_tokens_are_mutually_exclusive_on_their_own_labels():
    """판별식 건전성 — 토큰 집합이 서로 겹치면 게이트 B가 공허해진다.

    각 축의 토큰이 **그 축 코드의 라벨에서만** 축을 특정하는지 실측한다. 어느 축의 토큰을
    다른 축의 토큰으로 바꾸면(예: `console_library`에 `"도면 점유폭"` 추가) 실패한다.
    """
    from server.vwx.verdicts import target_exclusion_label

    for code, axis in sorted(_R19_FIX_AXIS.items()):
        if axis not in _R19_AXIS_TOKENS:
            continue
        assert _r19_identified_axis(target_exclusion_label(code)) == axis, code


#: round19가 신설하거나 배제 어휘에 재등재한 코드 -> (그 코드를 내는 시나리오, 형제 축의 코드).
#: 형제 축 코드는 **구현자가 재사용했을 법한 이웃**이다 — 그것으로 갈음했을 때 조작자가 축을
#: 잘못 짚는다는 것이 이 코드들의 존재 근거다.
_R19_NEW_CODE_AXIS_PROBES = (
    (
        "designed_footprint_matches_no_console_mode",
        "footprint_unmatchable",
        "dmx_mode_not_in_library",
    ),
    ("fixture_type_library_truncated", "library_truncated", "type_confirmation_pending"),
    ("fixture_type_library_unreadable", "library_unreadable", "type_confirmation_pending"),
    (
        "fixture_type_library_rows_discarded",
        "library_rows_discarded",
        "type_confirmation_pending",
    ),
)


def _r19_scenario_named(name: str):
    if name == "library_unreadable":
        # 모드 하나만 채널 수를 못 읽는다 — 맞는 모드가 있는지 **단정할 수 없는** 상태다.
        return (
            "library_unreadable",
            "MegaPointe",
            "Mode 1",
            99,
            _R19_ALIAS_MODE_1,
            {"partial_channels": True},
        )
    if name == "library_rows_discarded":
        # [round21 R20-D] DMXModes 행 하나에 슬롯 번호가 없다 — 목록은 끝까지 왔고
        # 응답도 정상이다. 절단·판독실패 어느 어휘로 적어도 관측 사실이 거짓이 된다.
        return (
            "library_rows_discarded",
            "MegaPointe",
            "Mode 1",
            99,
            _R19_ALIAS_MODE_1,
            {"slotless_modes": True},
        )
    return next(row for row in _R19_STATE_CORPUS if row[0] == name)


def test_r19_every_new_code_probe_names_a_reachable_production_scenario():
    """대조군 건전성 — 프로브가 가리키는 시나리오가 실제로 그 코드를 낸다.

    시나리오가 그 코드에 닿지 않으면 아래 구별성 게이트는 아무것도 재지 않는다.
    """
    for code, scenario_name, sibling in _R19_NEW_CODE_AXIS_PROBES:
        scenario = _r19_scenario_named(scenario_name)
        plan = _r19_resolve(scenario)
        handoff = _handoff(resolutions=plan.resolutions, dry_run=False)
        assert [item.code for item in handoff.exclusions] == [code], scenario_name
        assert _R19_FIX_AXIS[sibling] != _R19_FIX_AXIS[code], code


@pytest.mark.parametrize(
    "code,scenario_name,sibling",
    _R19_NEW_CODE_AXIS_PROBES,
    ids=[row[0] for row in _R19_NEW_CODE_AXIS_PROBES],
)
def test_r19_the_label_is_load_bearing_evidence_for_the_fix_axis(code, scenario_name, sibling):
    """게이트 B — 라벨을 형제 축 라벨로 통째 교체하면 프로덕션 payload가 축을 잘못 짚는다.

    ㉠ 실제 payload: 배제 라벨이 그 코드의 축을 **정확히 하나로** 지목한다.
    ㉡ 뮤턴트 payload: 라벨을 형제 축 코드의 라벨로 바꾸면 지목되는 축이 달라진다.

    ㉡이 통과하지 못하면(= 라벨을 바꿔도 축이 그대로면) 라벨은 축 특정의 근거가 아니고,
    그 코드의 존재 근거를 다시 적어야 한다 — round18 `fid_below_minimum`이 정확히 그 상태였다.
    교체는 `verdicts`의 라벨 표를 직접 바꾸고, payload는 **프로덕션 경로**로 다시 만든다.
    """
    from server.vwx import verdicts

    scenario = _r19_scenario_named(scenario_name)
    axis = _R19_FIX_AXIS[code]
    sibling_axis = _R19_FIX_AXIS[sibling]

    plan = _r19_resolve(scenario)
    produced = _handoff(resolutions=plan.resolutions, dry_run=False).exclusions[0].to_dict()
    assert produced["code"] == code
    assert _r19_identified_axis(produced["label"]) == axis

    original = verdicts._TARGET_EXCLUSION_LABELS[code]
    verdicts._TARGET_EXCLUSION_LABELS[code] = verdicts._TARGET_EXCLUSION_LABELS[sibling]
    try:
        mutant = _handoff(resolutions=plan.resolutions, dry_run=False).exclusions[0].to_dict()
        assert mutant["code"] == code
        assert _r19_identified_axis(mutant["label"]) != axis, mutant["label"]
        assert _r19_identified_axis(mutant["label"]) in (sibling_axis, None)
    finally:
        verdicts._TARGET_EXCLUSION_LABELS[code] = original

    restored = _handoff(resolutions=plan.resolutions, dry_run=False).exclusions[0].to_dict()
    assert restored["label"] == original
