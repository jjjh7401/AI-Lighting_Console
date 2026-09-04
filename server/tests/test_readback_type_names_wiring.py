"""`read_inventory` 호출 지점의 타입명 표 배관 — SPEC-COPILOT-READBACK-002 M1.

`read_inventory(..., type_names=)` kwarg 는 **이미 존재하고 이미 한 곳에서 옳게
쓰인다**(`tools.py:6356`). 나머지 여섯 자리가 그것을 빠뜨려 VWX diff 가 타입별로
전부 0 을 세고 패치 시트가 `FixtureType 12` 핸들을 그대로 인쇄한다.

여기서 재는 것은 셋이다.

1. **전수 정합**(AC-READBACK2-007) — `ast` 로 호출 노드를 센다. 줄 단위 grep 은
   쓰지 않는다: `pyproject.toml:59` 가 `line-length = 100` 이라 수리 뒤 포매터가
   호출을 여러 줄로 쪼개므로 한 줄 안에서 `read_inventory(` 와 `type_names=` 를
   함께 찾는 계기는 올바른 구현 뒤에도 7 을 답하지 않는다.
2. **지점당 조회 상한 1회**(AC-READBACK2-013a) — 늘어나는 것은
   `read_fixture_type_names` 의 목록 조회 1회뿐이다.
3. **한 핸들러의 두 자리가 표를 나눠 쓴다**(AC-READBACK2-013b) —
   `tools.py:4433`·`:4624` 는 같은 `patch_fixtures` 호출이다. 「호출 지점당 1회」를
   「자리마다 한 번씩」으로 읽으면 이 핸들러에서 조회가 **두 번** 늘어난다.

**계기의 한계를 먼저 적는다.** 조회 로그는 **경로**만 기록하므로
`read_fixture_type_names` 와 `read_type_mode_widths` 의 루트 판독은 둘 다
`Patch/FixtureTypes` 로 나타나 경로만으로는 갈라지지 않는다. 둘을 가르는 것은
**per-type 후속 조회의 유무**다 — 모드 판독은 루트에 이어
`Patch/FixtureTypes/<슬롯>/DMXModes` 를 읽고, 목록 판독은
`mode_read.py:141` 문면 그대로 「Query count is 1」이라 루트만 읽는다. 그래서
이 파일은 절대값이 아니라 **루트 경로 계수의 리터럴**을 단언하고, 그 리터럴의
수리 전 기준은 `progress.md` §E.2 조회 계수표에 남는다(VCI §2 — 기억된 숫자는
기준이 아니다).
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

from server.llm.types import ToolCall
from server.orchestrator.tools import ANSWER_RAN_IT, build_toolset
from server.prechk.mode_read import read_fixture_type_names

_TOOLS_PY = Path(__file__).resolve().parents[1] / "orchestrator" / "tools.py"

#: 타입 트리 루트. `DEFAULT_RIG_CONTEXT_PATHS["fixture_types"]` 와 같은 값이며,
#: 이 파일은 기본 리그 경로로만 툴셋을 만든다.
_TYPES_ROOT = "Patch/FixtureTypes"

_TYPE = "Sharpy 250W Beam"
_MODE = "Mode 0"

#: 타입 트리가 선언하는 (슬롯, 이름) 쌍. 슬롯 4 는 아래 픽스처들이 답하는
#: `FixtureType 4` 핸들의 대응 이름이다.
_TYPE_PAIRS = ((4, _TYPE),)


# --- AC-READBACK2-007 — 일곱 호출자 전수 대조 (AST, 줄 경계 무관) ---------------


def _read_inventory_calls() -> list[ast.Call]:
    tree = ast.parse(_TOOLS_PY.read_text(encoding="utf-8"))
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (
            getattr(node.func, "id", None) == "read_inventory"
            or getattr(node.func, "attr", None) == "read_inventory"
        )
    ]


class TestEverySiteIsAudited:
    """`acceptance.md` §A 의 `ast` 계수 스니펫을 테스트로 고정한 것."""

    def test_the_census_still_finds_exactly_seven_call_sites(self):
        # 계기의 양성 대조군: 7 이 아니면 호출 지점이 늘거나 줄었다는 뜻이고,
        # 그때는 아래 전수 단언이 「전수」를 뜻하지 않게 된다.
        calls = _read_inventory_calls()

        assert len(calls) == 7, sorted(call.lineno for call in calls)

    def test_every_call_site_passes_the_type_name_table(self):
        # [HARD] 하나만 고치면 나머지가 같은 결함으로 남아 있다는 사실이
        # 보이지 않게 된다(REQ-READBACK2-006).
        calls = _read_inventory_calls()
        without = sorted(
            call.lineno
            for call in calls
            if not any(keyword.arg == "type_names" for keyword in call.keywords)
        )

        assert without == [], f"type_names 를 안 넘기는 호출 지점: {without}"


#: 여섯 호출 지점을 소유하는 **다섯** 핸들러(§B B5) + 참조 구현 하나.
#: `:4433` 과 `:4624` 는 둘 다 `patch_fixtures` 안이므로 이 표의 항목은 5+1 이다.
_HANDLERS_OWNING_A_SITE = (
    "precheck_patch",  # :3014
    "precheck_vectorworks_diff",  # :3206
    "apply_vectorworks_patch",  # :3397
    "resolve_patch_address",  # :4039
    "patch_fixtures",  # :4433 · :4624 — 두 자리, 한 핸들러
    "import_lxseq_patch",  # :6356 — 참조 구현 (이미 옳다)
)


def _handler_bodies() -> dict[str, ast.FunctionDef]:
    tree = ast.parse(_TOOLS_PY.read_text(encoding="utf-8"))
    return {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name in _HANDLERS_OWNING_A_SITE
    }


class TestTheListReadIsIssuedOncePerHandler:
    """지점별 조회 계상을 **구조로** 판정한다 — 여섯 자리 전부를 덮는다.

    `:3206`·`:3397` 은 base64 VWX 아카이브와 diff 리포트 페이로드를 요구해
    이 파일이 실행으로 구동하지 않는다(그 두 자리는 아래 계수 단언이 아니라 이
    구조 단언으로만 계상된다 — 완료 보고 미검증 절에 그대로 적힌다). 그러나
    「목록 판독을 몇 번 발행하는가」는 실행 없이도 이진 판정된다: 핸들러 본문의
    `read_fixture_type_names` 호출 노드를 세면 된다.

    `patch_fixtures` 가 **1** 이어야 하는 것이 이 단언의 핵심이다 — 2 면 두 자리가
    표를 각각 읽었다는 뜻이고 REQ-READBACK2-012 위반이다.
    """

    def test_each_owning_handler_issues_exactly_one_list_read(self):
        bodies = _handler_bodies()
        missing = sorted(set(_HANDLERS_OWNING_A_SITE) - set(bodies))
        assert missing == [], f"핸들러를 못 찾았다 — 앵커가 옮겨졌다: {missing}"

        counts = {
            name: sum(
                1
                for node in ast.walk(body)
                if isinstance(node, ast.Call)
                and getattr(node.func, "id", None) == "read_fixture_type_names"
            )
            for name, body in bodies.items()
        }

        assert counts == dict.fromkeys(_HANDLERS_OWNING_A_SITE, 1), counts


# --- 조회를 세는 가짜 포트 -------------------------------------------------------


class CountingConsolePorts:
    """`query_state` 경로를 전부 기록하는 콘솔 — 전후로 다른 픽스처 목록을 낸다.

    `test_vwx_stagedpatch.py` 의 `ConsolePorts` 와 같은 모양이지만 **조회 로그**를
    싣는다. 픽스처 목록 조회만 before/after 장면을 넘기고, 타입 트리 조회는 장면
    카운터를 소모하지 않는다 — 소모하면 내가 더한 목록 판독이 장면을 밀어
    「패치가 먹혔다」를 조작하게 된다.
    """

    MODE_FOOTPRINTS = {1: 14}

    def __init__(self, before, after=None) -> None:
        self.scenes = [before, after if after is not None else before]
        self.reads = 0
        #: 이 포트가 받은 `query_state` 경로 전부, 순서대로.
        self.state_log: list[str] = []
        self.property_log: list[tuple[str, str]] = []

    # -- 계수 도우미 ----------------------------------------------------------
    @property
    def types_root_reads(self) -> int:
        """타입 트리 **루트** 판독 횟수.

        루트만 세는 것이 요점이다. `read_fixture_type_names` 는 루트 1회로
        끝나고(`mode_read.py:141`), `read_type_mode_widths` 는 루트에 이어
        `.../DMXModes` 를 읽는다 — 그래서 per-type 경로는 따로 센다.
        """
        return self.state_log.count(_TYPES_ROOT)

    @property
    def per_type_reads(self) -> int:
        return sum(
            1
            for path in self.state_log
            if path.startswith(f"{_TYPES_ROOT}/") and path != _TYPES_ROOT
        )

    def _current(self):
        return self.scenes[min(self.reads - 1, len(self.scenes) - 1)]

    def query_state(self, path: str) -> dict:
        self.state_log.append(path)
        if path.startswith(_TYPES_ROOT):
            return self._type_tree(path)
        self.reads += 1
        rows = self._current()
        return {
            "ok": True,
            "path": path,
            "truncated": False,
            "node": {"childCount": len(rows)},
            "children": [
                {"class": "Fixture", "i": index + 1, "name": row[0]}
                for index, row in enumerate(rows)
            ],
        }

    def _type_tree(self, path: str) -> dict:
        if path == _TYPES_ROOT:
            children = [
                {"i": slot, "name": name, "class": "FixtureType"} for slot, name in _TYPE_PAIRS
            ]
        elif path == f"{_TYPES_ROOT}/4/DMXModes":
            children = [{"i": 1, "name": _MODE, "class": "DMXMode"}]
        else:
            return {"ok": False}
        return {
            "ok": True,
            "path": path,
            "truncated": False,
            "node": {"childCount": len(children)},
            "children": children,
        }

    def query_property(self, path: str, property_name: str) -> dict:
        self.property_log.append((path, property_name))
        if path.startswith(f"{_TYPES_ROOT}/4/DMXModes/"):
            if property_name != "TotalFootprint":
                return {"ok": False}
            slot = int(path.rsplit("/", 1)[-1])
            width = self.MODE_FOOTPRINTS.get(slot)
            return {"ok": True, "value": width} if width is not None else {"ok": False}
        index = int(path.rsplit("/", 1)[-1]) - 1
        rows = self._current()
        if not 0 <= index < len(rows):
            return {"ok": False}
        name, patch = rows[index]
        value = {
            "Name": name,
            "Patch": patch,
            # 실기 콘솔이 실제로 돌려주는 형태 — 이름이 아니라 핸들이다.
            "FixtureType": "FixtureType 4",
            "Mode": _MODE,
            "FID": str(index + 1),
        }.get(property_name)
        return {"ok": True, "value": value} if value is not None else {"ok": False}


class ScriptedDeploy:
    def __init__(self, status: str = "deployed") -> None:
        self.status = status
        self.sent: list[object] = []

    def deploy(self, *args, **kwargs):
        self.sent.append((args, kwargs))
        return type(
            "D",
            (),
            {"status": self.status, "destructive": False, "detail": "", "compile_error": None},
        )()


class ScriptedExec:
    def __init__(self) -> None:
        self.sent: list[str] = []

    def execute(self, command: str):
        self.sent.append(command)
        return type("R", (), {"command": command, "ok": True, "detail": "OK"})()


class SaysRan:
    def __init__(self, answer: str = ANSWER_RAN_IT) -> None:
        self.answer = answer
        self.asked: list[object] = []

    def ask(self, request) -> str:
        self.asked.append(request)
        return self.answer


_TWO = [("Spot 1", "1.001"), ("Spot 2", "1.015")]
_FOUR = _TWO + [(f"{_TYPE} 1", "4.001"), (f"{_TYPE} 2", "4.015")]


# --- 계기 자체의 양성 대조군 (B-6) ---------------------------------------------


class TestTheQueryCounterIsNotBlind:
    """0 을 부재의 증거로 쓰기 전에, 이 계기가 **0 이 아닌 값을 낼 수 있음**을 본다.

    이 저장소는 「내용 있는 Group 이 COUNT 0 을 답한다」를 이미 기록해 두었다.
    계수기가 타입 트리 루트 경로를 못 보는 상태로도 아래 상한 단언은 전부
    통과하므로, 날조 대조군을 먼저 쏘지 않으면 「상한을 지켰다」와
    「계기가 눈이 멀었다」가 구별되지 않는다.
    """

    def test_a_fabricated_list_read_registers_on_the_counter(self):
        port = CountingConsolePorts(_TWO)

        answer = read_fixture_type_names(port, root=_TYPES_ROOT)

        assert answer.attempted is True
        assert answer.by_slot() == {4: _TYPE}
        # 계기가 이 경로를 본다 — 아래의 「루트 판독 1회」는 실측이지 침묵이 아니다.
        assert port.types_root_reads == 1
        assert port.per_type_reads == 0, "목록 판독은 타입마다 캐묻지 않는다"

    def test_two_fabricated_list_reads_register_as_two(self):
        # 상한 초과가 계기에 **보인다**는 것까지 확인한다. 이것이 없으면
        # AC-013b 의 「정확히 한 번」은 통과해도 의미가 없다.
        port = CountingConsolePorts(_TWO)

        read_fixture_type_names(port, root=_TYPES_ROOT)
        read_fixture_type_names(port, root=_TYPES_ROOT)

        assert port.types_root_reads == 2


# --- AC-READBACK2-013a — 지점당 정확히 N+1 --------------------------------------


def _resolve_patch_address(port) -> dict:
    registry = build_toolset(
        execution_port=None,
        state_port=port,
        property_port=port,
    )
    execution = registry.dispatch(
        ToolCall(
            id="c1",
            name="resolve_patch_address",
            arguments={"address": "9.001", "count": 2, "channels_per_fixture": 14},
        )
    )
    return json.loads(execution.result.content)


class TestOneExtraQueryPerCallSite:
    """`resolve_patch_address`(`tools.py:4039`) — 수리 전 루트 판독 **0** 회.

    §B B5 가 「아니오」로 실측한 세 지점 중 하나다. 이 핸들러는 자기 이유로
    fixture-type 루트를 걷지 않으므로 수리 전 루트 계수가 0 이고, 수리 뒤 1 이
    된다 — 늘어난 1회의 정체가 경로 계수만으로 모호하지 않은 자리다.

    수리 전 기준 N(2026-09-04 RED 단계 실측, `progress.md` §E.2 조회 계수표):
    `:4039` → `query_state` 전체 **1** 회(`['Patch/Stages/1/Fixtures']`) · 루트 **0** 회.
    """

    def test_the_handler_reads_the_type_list_exactly_once(self):
        port = CountingConsolePorts(_TWO)

        _resolve_patch_address(port)

        assert port.types_root_reads == 1, port.state_log
        # 늘어난 조회가 **목록** 판독임을 조회 로그가 답한다: 루트 1회, per-type 0회.
        # 모드 판독이었다면 `.../4/DMXModes` 가 로그에 함께 남는다.
        assert port.per_type_reads == 0, port.state_log

    def test_the_total_query_count_grows_by_exactly_one(self):
        # 수리 전 실측 1회(픽스처 루트) → 수리 후 2회. N+2 이상은 FAIL 이다
        # (REQ-READBACK2-012).
        port = CountingConsolePorts(_TWO)

        _resolve_patch_address(port)

        assert len(port.state_log) == 2, port.state_log

    def test_the_handle_is_translated_in_the_occupant_readout(self):
        # 표를 넘기는 목적이 여기서 관측된다 — 핸들이 이름으로 바뀐다.
        port = CountingConsolePorts(_TWO)

        payload = _resolve_patch_address(port)

        assert "FixtureType 4" not in json.dumps(payload, ensure_ascii=False)


def _precheck_patch(port) -> dict:
    registry = build_toolset(
        execution_port=None,
        state_port=port,
        property_port=port,
    )
    execution = registry.dispatch(ToolCall(id="c1", name="precheck_patch", arguments={}))
    return json.loads(execution.result.content)


class TestTheSiteThatAlreadyWalksTheRootStillPaysOnlyOne:
    """`precheck_patch`(`tools.py:3014`) — §B B5 가 「예」로 실측한 세 자리 중 하나.

    이 핸들러는 `walk_mode_widths`(`:3046-3055`)로 이미 fixture-type 루트를 걷는다.
    그래도 **재사용은 불가능**하다 — `WalkOutcome` 은 `queried_paths` 로 경로
    문자열만 돌려주고 (슬롯, 이름) 쌍을 호출자에게 주지 않으며, 그 쌍을 흘리려면
    `server/prechk/**` 를 고쳐야 하고 REQ-READBACK2-010 이 금지한다(§B B4).
    **호출자가 조회를 냈다는 것과 페이로드를 쥐고 있다는 것은 다르다.**

    그러므로 여기서 재는 것은 재사용 여부가 아니라 **상한**이다: 목록 판독은
    정확히 1회 늘고, 그 이상은 FAIL 이다.
    """

    def test_the_repair_adds_exactly_one_root_read(self):
        port = CountingConsolePorts(_TWO)

        _precheck_patch(port)

        # 수리 전 실측(RED 단계): 루트 판독 **1** 회(`walk_mode_widths`).
        # 수리 후 **2** 회 = N+1. 3 이면 상한 초과다.
        assert port.types_root_reads == 2, port.state_log


# --- AC-READBACK2-013b — 한 핸들러의 두 자리가 표를 나눠 쓴다 --------------------


def _patch_fixtures(port) -> dict:
    registry = build_toolset(
        execution_port=ScriptedExec(),
        state_port=port,
        property_port=port,
        deploy_pipeline=ScriptedDeploy(),
        question_port=SaysRan(),
    )
    execution = registry.dispatch(
        ToolCall(
            id="c1",
            name="patch_fixtures",
            arguments={
                "console_type": _TYPE,
                "console_mode": _MODE,
                "address": "4.1",
                "count": 2,
                "channels_per_fixture": 14,
            },
        )
    )
    return json.loads(execution.result.content)


class TestTheCeilingHoldsInsideOneHandler:
    """`patch_fixtures`(`tools.py:4433`·`:4624`) — 두 자리, 한 핸들러.

    이 대조군이 없으면 「호출 지점당 1회」를 「자리마다 한 번씩」으로 읽어 한
    핸들러에서 조회가 두 번 늘어난 것이 통과한다(§G 안티패턴).

    수리 전 기준 N(2026-09-04 RED 단계 실측, `progress.md` §E.2 조회 계수표):
    `query_state` 전체 **5** 회 · 루트 **1** 회 — `read_type_mode_widths` `:4295` 가
    낸 그 한 번이다. 수리 뒤 루트는 **2**(= N+1) 여야 하고 **3**(= N+2)은 FAIL 이다.
    """

    def test_the_type_list_is_read_once_for_both_call_sites(self):
        port = CountingConsolePorts(_TWO, _FOUR)

        payload = _patch_fixtures(port)

        assert payload.get("status") == "created", payload
        # [HARD] 루트 계수 2 = 모드 판독 1(`:4295`) + 목록 판독 1(내 수리).
        # 3 이면 `before` 와 `_verify` 가 표를 각각 읽었다는 뜻이며 FAIL 이다.
        assert port.types_root_reads == 2, port.state_log

    def test_the_verify_arm_reuses_the_same_table(self):
        # 재조회 팔이 자기 표를 새로 읽으면 위 계수가 3 이 된다. 그 갈래를
        # 별도 이름으로 못박아 둔다 — 한 단언이 두 사실을 지키면 회귀가
        # 어느 쪽에서 왔는지 보이지 않는다.
        port = CountingConsolePorts(_TWO, _FOUR)

        _patch_fixtures(port)

        root_reads_after_mode_read = port.types_root_reads - 1
        assert root_reads_after_mode_read == 1, (
            "두 read_inventory 자리가 목록 조회를 각각 발행했다 — "
            f"루트 판독 {port.types_root_reads}회: {port.state_log}"
        )

    def test_the_verify_readout_carries_names_not_handles(self):
        port = CountingConsolePorts(_TWO, _FOUR)

        payload = _patch_fixtures(port)

        assert "FixtureType 4" not in json.dumps(payload, ensure_ascii=False)
