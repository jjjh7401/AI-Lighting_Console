"""패치하고 **콘솔을 다시 읽어** 판정한다 — 실행됐다고 성공이라 하지 않는다.

[round24 후속] 실측: 모델이 손으로 짠 Lua를 배포·실행하고 콘솔이 명령을 받았다는
뜻인 ``ok=true``를 작업 성공으로 읽어 "Sharpy 250W Beam 4대를 FID 301부터
성공적으로 패치하였습니다"라고 보고했다. 콘솔은 **40대 그대로**였다.

그래서 여기서는 "실행했는가"가 아니라 **"실행 뒤 무엇이 실제로 있는가"**만 본다.
"""

from __future__ import annotations

import json

import pytest

from server.llm.types import ToolCall
from server.orchestrator.tools import ANSWER_CANCEL, ANSWER_RAN_IT, build_toolset
from server.vwx.addressfit import Placement
from server.vwx.stagedpatch import free_fids, judge, plan

_TYPE = "Sharpy 250W Beam"
_MODE = "Mode 0"


def _spots(count: int, *, universe: int = 4, width: int = 14):
    return [Placement(universe=universe, address=1 + index * width) for index in range(count)]


class TestPlanning:
    def test_it_renders_one_addfixtures_call_per_fixture(self):
        staged = plan(
            console_type=_TYPE,
            console_mode=_MODE,
            footprint=14,
            placements=_spots(3),
            fids=(41, 42, 43),
        )

        assert staged.lua_source.count("AddFixtures(") == 3

    def test_the_lua_carries_the_console_names_verbatim(self):
        staged = plan(
            console_type=_TYPE,
            console_mode=_MODE,
            footprint=14,
            placements=_spots(1),
            fids=(41,),
        )

        assert f'FixtureTypes["{_TYPE}"]' in staged.lua_source
        assert f'DMXModes["{_MODE}"]' in staged.lua_source

    def test_mismatched_counts_stop_instead_of_truncating(self):
        # [HARD] 짧은 쪽에 맞춰 자르면 6대 요청에 4대만 만들고 성공이라 보고한다.
        with pytest.raises(ValueError, match="맞지 않는다"):
            plan(
                console_type=_TYPE,
                console_mode=_MODE,
                footprint=14,
                placements=_spots(6),
                fids=(41, 42, 43, 44),
            )

    def test_an_empty_plan_is_refused(self):
        with pytest.raises(ValueError):
            plan(
                console_type=_TYPE,
                console_mode=_MODE,
                footprint=14,
                placements=[],
                fids=(),
            )


class TestFidChoice:
    def test_it_takes_a_contiguous_free_block(self):
        assert free_fids([1, 2, 3], count=4, start=1) == (4, 5, 6, 7)

    def test_it_steps_over_a_block_that_is_partly_taken(self):
        # 흩어진 번호를 주면 조작자가 리그를 못 센다.
        assert free_fids([5], count=3, start=3) == (6, 7, 8)

    def test_it_never_reuses_a_live_fid(self):
        # [HARD] 쓰는 번호를 다시 주면 기존 장비를 가리키게 된다.
        taken = [10, 11, 12]
        assert not set(free_fids(taken, count=5, start=8)) & set(taken)


class TestTheVerdictComesFromTheConsole:
    def _fixtures(self, count=3):
        return plan(
            console_type=_TYPE,
            console_mode=_MODE,
            footprint=14,
            placements=_spots(count),
            fids=tuple(range(41, 41 + count)),
        ).fixtures

    def test_nothing_observed_is_created_nothing(self):
        # [HARD] 실물 사고 그대로 — 플러그인은 돌았고 장비는 0대였다.
        verdict = judge(self._fixtures(), occupied_after=[])

        assert verdict.status == "created_nothing"
        assert verdict.created == 0

    def test_everything_observed_is_created(self):
        planned = self._fixtures()
        seats = [(fixture.universe, fixture.address) for fixture in planned]

        assert judge(planned, occupied_after=seats).status == "created"

    def test_some_observed_is_not_success(self):
        # [HARD] 부분 성공을 성공이라 하면 조작자는 없는 장비로 큐를 짠다.
        planned = self._fixtures()
        seats = [(planned[0].universe, planned[0].address)]
        verdict = judge(planned, occupied_after=seats)

        assert verdict.status == "created_partially"
        assert verdict.created == 1

    def test_an_incomplete_read_is_not_reported_as_failure(self):
        # [HARD] 미판독을 미관측으로 적으면 사용자는 다시 실행해 중복을 만든다.
        verdict = judge(self._fixtures(), occupied_after=[], read_complete=False)

        assert verdict.status == "unverified"

    def test_a_complete_read_that_saw_everything_is_still_success(self):
        planned = self._fixtures()
        seats = [(fixture.universe, fixture.address) for fixture in planned]

        assert judge(planned, occupied_after=seats, read_complete=False).status == "created"

    def test_a_fixture_somewhere_else_does_not_count(self):
        # 다른 자리에 뭔가 있다고 내 장비가 생긴 것이 아니다.
        planned = self._fixtures()

        assert judge(planned, occupied_after=[(9, 500)]).created == 0


class ScriptedDeploy:
    def __init__(self, status: str = "deployed") -> None:
        self.status = status
        self.deployed: list[tuple[str, str]] = []

    def deploy(self, name: str, source: str):
        self.deployed.append((name, source))
        return type(
            "Outcome",
            (),
            {"status": self.status, "destructive": False, "detail": "", "compile_error": None},
        )()


class ConsolePorts:
    """실행 전후로 다른 목록을 내는 콘솔 — 패치가 먹혔는지 흉내 낸다."""

    def __init__(self, before, after=None) -> None:
        self.scenes = [before, after if after is not None else before]
        self.reads = 0

    def _current(self):
        return self.scenes[min(self.reads - 1, len(self.scenes) - 1)]

    def query_state(self, path: str) -> dict:
        # 모드/폭 실측 경로 — 장면 카운터(reads)를 소모하지 않는다. 픽스처 목록
        # 조회만 before/after 장면을 넘긴다.
        if path.startswith("Patch/FixtureTypes"):
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

    #: 모드 슬롯 → TotalFootprint. 폭의 출처는 DMXChannels 계수가 아니라 이 속성이다
    #: (실기 2026-08-18: 16bit 채널 때문에 채널 계수는 주소 폭을 밑돈다).
    MODE_FOOTPRINTS = {1: 14}

    def _type_tree(self, path: str) -> dict:
        """타입 4번에 `_TYPE`, 그 아래 `_MODE` 하나(TotalFootprint 14)."""
        if path == "Patch/FixtureTypes":
            children = [{"i": 4, "name": _TYPE, "class": "FixtureType"}]
        elif path == "Patch/FixtureTypes/4/DMXModes":
            children = [
                {"i": slot, "name": name, "class": "DMXMode"} for slot, name in self._mode_names()
            ]
        else:
            return {"ok": False}
        return {
            "ok": True,
            "path": path,
            "truncated": False,
            "node": {"childCount": len(children)},
            "children": children,
        }

    def _mode_names(self) -> list[tuple[int, str]]:
        return [(1, _MODE)]

    def query_property(self, path: str, property_name: str) -> dict:
        if path.startswith("Patch/FixtureTypes/4/DMXModes/"):
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
            "FixtureType": _TYPE,
            "Mode": _MODE,
            # 전수 FID 판독이 성립해야 자동 배정 갈래를 시험할 수 있다.
            "FID": str(index + 1),
        }.get(property_name)
        return {"ok": True, "value": value} if value is not None else {"ok": False}


class ScriptedExec:
    """`CommandExecutionPort` 그대로 — `execute(command)` 하나뿐이다.

    [2026-08-18] 이 가짜가 `run([...])`을 갖고 있던 동안 `patch_fixtures`는
    프로덕션에 없는 그 모양을 호출했고, 스위트는 전부 통과하면서 실기에서는
    AttributeError로 죽었다. 가짜가 실제 포트보다 넓으면 시험은 계약을 지키지
    못한다 — 그래서 여기에는 `run`이 없다.
    """

    def __init__(self) -> None:
        self.sent: list[str] = []

    def execute(self, command: str):
        self.sent.append(command)
        return type("R", (), {"command": command, "ok": True, "detail": "OK"})()


class SaysRan:
    """조작자 대신 «실행했습니다»를 내는 질문 통로."""

    def __init__(self, answer: str = ANSWER_RAN_IT) -> None:
        self.answer = answer
        self.asked: list[object] = []

    def ask(self, request) -> str:
        self.asked.append(request)
        return self.answer


def _patch(
    before,
    after=None,
    *,
    deploy_status="deployed",
    address="4.1",
    count=2,
    question_port=None,
    arguments=None,
    ports=None,
):
    ports = ports if ports is not None else ConsolePorts(before, after)
    deploy = ScriptedDeploy(deploy_status)
    runner = ScriptedExec()
    registry = build_toolset(
        execution_port=runner,
        state_port=ports,
        property_port=ports,
        deploy_pipeline=deploy,
        question_port=question_port if question_port is not None else SaysRan(),
    )
    execution = registry.dispatch(
        ToolCall(
            id="c1",
            name="patch_fixtures",
            arguments=arguments
            if arguments is not None
            else {
                "console_type": _TYPE,
                "console_mode": _MODE,
                "address": address,
                "count": count,
                "channels_per_fixture": 14,
            },
        )
    )
    return json.loads(execution.result.content), deploy, runner


_EMPTY: list[tuple[str, str]] = []
_TWO_NEW = [("Sharpy 250W Beam 1", "4.001"), ("Sharpy 250W Beam 2", "4.015")]


class TestTheServerFiresItThenVerifies:
    """앱이 실행한다 — 단, 성공은 재조회에서만 나온다.

    2026-08-18 재실측(라이브 onPC 2.4.2.2, 앱의 실제 배포+실행 경로):
      편집기 열림 + **서버 실행** -> 60 -> 62 생성됨
      목적지 Root  + 서버 실행    -> 0건
      서버의 목적지 이동 시도는 전부 실패(ChangeDestination Failed / Menu Patch
      Not implemented) — 그래서 편집기를 여는 일만 사람에게 남는다.

    이전 계약("서버가 발화하면 0건이므로 사람이 타이핑해야 한다")은 목적지 조건을
    발화 주체로 오인한 것이었다.
    """

    def test_the_server_runs_the_plugin_itself(self):
        # [HARD] 이 한 줄이 자동화의 전부다 — 조작자는 명령을 타이핑하지 않는다.
        _payload, _deploy, runner = _patch(_EMPTY, _TWO_NEW)

        assert runner.sent == ["Plugin 'CopilotPatchSharpy250WBeam'"]

    def test_each_type_gets_its_own_plugin(self):
        # 하나를 돌려 쓰면 두 번째 타입 배포가 첫 번째 소스를 덮어쓴다.
        _payload, deploy, _runner = _patch(_EMPTY, _TWO_NEW)

        assert [name for name, _ in deploy.deployed] == ["CopilotPatchSharpy250WBeam"]

    def test_the_command_uses_single_quotes_because_execute_rejects_doubles(self):
        # `ConsoleLink.execute`는 이중 인용부호를 담은 명령을 거부한다(실측).
        payload, _deploy, _runner = _patch(_EMPTY, _TWO_NEW)

        assert payload["run_yourself"] == "Plugin 'CopilotPatchSharpy250WBeam'"
        assert '"' not in payload["run_yourself"]

    def test_a_successful_run_asks_the_operator_nothing(self):
        # 생성이 확인되면 카드를 띄우지 않는다 — 불필요한 왕복은 그 자체로 결함이다.
        port = SaysRan()
        payload, _deploy, _runner = _patch(_EMPTY, _TWO_NEW, question_port=port)

        assert payload["status"] == "created"
        assert port.asked == []

    def test_zero_created_asks_only_to_open_the_editor_then_retries(self):
        # 0건이면 목적지 조건이 첫 가설이다. 타이핑을 시키지 않고 편집기만 청한 뒤
        # 앱이 다시 실행한다.
        port = SaysRan()
        payload, _deploy, runner = _patch(_EMPTY, question_port=port)

        assert len(port.asked) == 1
        text = port.asked[0].why + " ".join(port.asked[0].steps)
        assert "Patch" in text
        assert "편집기" in text or "Patch를 엽니다" in text
        assert "타이핑" not in text
        # 서버가 두 번 발화했다: 최초 + 편집기 확인 후 재시도.
        assert runner.sent == ["Plugin 'CopilotPatchSharpy250WBeam'"] * 2
        assert [a["by"] for a in payload["attempts"]] == ["server", "server_retry"]
        assert payload["status"] == "created_nothing"

    def test_the_fallback_command_is_still_offered_on_the_card(self):
        # 자동 실행이 또 실패할 때 조작자가 직접 칠 수 있는 길은 남긴다.
        port = SaysRan()
        _patch(_EMPTY, question_port=port)

        assert port.asked[0].commands == ("Plugin 'CopilotPatchSharpy250WBeam'",)


class TestTheVerdictAfterTheOperatorRuns:
    def test_everything_created_is_reported_as_created(self):
        payload, _deploy, _runner = _patch(_EMPTY, _TWO_NEW)

        assert payload["status"] == "created"
        assert payload["created"] == 2

    def test_nothing_created_says_so(self):
        # [HARD] 실물 사고 그대로 — 조작자가 눌렀는데 0대일 수 있다.
        payload, _deploy, _runner = _patch(_EMPTY, _EMPTY)

        assert payload["status"] == "created_nothing"
        assert "성공했다고 보고하지 마라" in payload["guidance"]

    def test_the_zero_case_points_at_the_editor_condition(self):
        # 두 축 중 무엇이 빠졌는지 알려 주지 않으면 조작자는 같은 실패를 반복한다.
        payload, _deploy, _runner = _patch(_EMPTY, _EMPTY)

        assert "Patch 편집기가" in payload["guidance"]

    def test_a_partial_run_is_not_dressed_up(self):
        payload, _deploy, _runner = _patch(_EMPTY, _TWO_NEW[:1])

        assert payload["status"] == "created_partially"
        assert "성공이라 말하지 마라" in payload["guidance"]

    def test_an_operator_who_did_not_run_it_is_believed(self):
        # [HARD] 안 눌렀다는데 읽어서 0대를 «실패»로 보고하면 원인을 오도한다.
        payload, _deploy, _runner = _patch(_EMPTY, _EMPTY, question_port=SaysRan(ANSWER_CANCEL))

        assert payload["status"] == "not_run"
        assert "만들어졌다고" in payload["guidance"] or "끝내라" in payload["guidance"]

    def test_a_failed_deploy_never_asks_the_operator(self):
        port = SaysRan()
        payload, _deploy, _runner = _patch(
            _EMPTY, _EMPTY, deploy_status="rejected", question_port=port
        )

        assert port.asked == [], "올리지도 못했는데 실행해 달라고 청했다"
        assert payload["status"] == "not_deployed"


class TestWhatItRefusesToDo:
    def test_an_occupied_address_is_refused_not_moved(self):
        # [HARD] 임의로 옮기면 사용자가 모르는 자리에 장비가 생긴다.
        payload, _deploy, runner = _patch([("RLB 1", "4.001")], [("RLB 1", "4.001")], address="4.1")

        assert payload["status"] == "address_not_free"
        assert runner.sent == []
        assert "임의로 옮기지 마라" in payload["guidance"]

    def test_it_uses_the_generator_not_hand_written_lua(self):
        # 손으로 짜면 목적지 변경 금지가 구조에서 사라진다.
        _payload, deploy, _runner = _patch(_EMPTY, _TWO_NEW)

        (_name, source) = deploy.deployed[0]
        assert "AddFixtures(" in source
        assert "ChangeDestination" not in source

    def test_a_guessed_type_is_refused(self):
        ports = ConsolePorts(_EMPTY)
        registry = build_toolset(
            execution_port=ScriptedExec(),
            state_port=ports,
            property_port=ports,
            deploy_pipeline=ScriptedDeploy(),
        )
        execution = registry.dispatch(
            ToolCall(
                id="c1",
                name="patch_fixtures",
                arguments={
                    "console_type": "",
                    "console_mode": _MODE,
                    "address": "4.1",
                    "count": 1,
                    "channels_per_fixture": 14,
                },
            )
        )

        assert execution.result.is_error
        assert "추측하지 마라" in execution.result.content

    def test_without_a_way_to_read_back_it_does_not_write(self):
        # [HARD] 확인할 수 없는 쓰기는 하지 않는다 — 그것이 이 도구의 규약이다.
        # 상태만 읽고 프로퍼티는 못 읽는 포트 = 실행 결과를 대조할 수 없는 세션.
        class StateOnly:
            def query_state(self, path: str) -> dict:
                return ConsolePorts(_EMPTY).query_state(path)

        registry = build_toolset(
            execution_port=ScriptedExec(),
            state_port=StateOnly(),
            property_port=None,
            deploy_pipeline=ScriptedDeploy(),
        )
        execution = registry.dispatch(
            ToolCall(
                id="c1",
                name="patch_fixtures",
                arguments={
                    "console_type": _TYPE,
                    "console_mode": _MODE,
                    "address": "4.1",
                    "count": 1,
                    "channels_per_fixture": 14,
                },
            )
        )

        assert execution.result.is_error
        assert "확인할 수 없는 쓰기는 하지 않는다" in execution.result.content


class TestTheOtherDoorIsShut:
    """패치는 **이 문으로 못 나간다** — 금지를 검사가 아니라 구조로 둔다.

    [round24 후속] 도구 설명에 "손으로 짜지 마라"를 적었는데도 모델은 실측에서
    매번 자기 플러그인을 지어 배포했다(`PatchSharpy`, `PatchSharpy6_U4`,
    `PatchSharpy6_V3`, `PatchSharpy6_Exec`…). 그 경로에는 재조회가 없어서
    콘솔이 명령을 받았다는 뜻인 ok=true가 곧 "패치했습니다"가 됐다.
    """

    def _deploy(self, source: str):
        ports = ConsolePorts(_EMPTY)
        deploy = ScriptedDeploy()
        registry = build_toolset(
            execution_port=ScriptedExec(),
            state_port=ports,
            property_port=ports,
            deploy_pipeline=deploy,
        )
        execution = registry.dispatch(
            ToolCall(
                id="c1",
                name="deploy_plugin",
                arguments={"name": "HandRolled", "lua_source": source},
            )
        )
        return execution, deploy

    def test_hand_written_patch_lua_is_refused(self):
        # [HARD] 이 한 줄이 실물에서 여섯 번 반복된 우회를 닫는다.
        execution, deploy = self._deploy(
            "local function main()\n  AddFixtures({ amount = 1 })\nend\nreturn main\n"
        )

        assert execution.result.is_error
        assert deploy.deployed == [], "거절해 놓고 배포했다"

    def test_the_refusal_names_the_right_door(self):
        # 막기만 하고 갈 곳을 안 알려 주면 모델은 다른 우회를 찾는다.
        execution, _deploy = self._deploy("AddFixtures({})")

        assert "patch_fixtures" in execution.result.content

    def test_other_plugins_still_deploy(self):
        # 패치가 아닌 플러그인까지 막으면 멀쩡한 기능이 죽는다.
        execution, deploy = self._deploy(
            'local function main()\n  Printf("hello")\nend\nreturn main\n'
        )

        assert not execution.result.is_error
        assert len(deploy.deployed) == 1

    def test_the_staged_tool_is_not_blocked_by_its_own_rule(self):
        # [HARD] 생성기가 만든 Lua에도 AddFixtures가 들어 있다 — 자기 길까지
        # 막으면 패치할 방법이 아예 사라진다.
        payload, deploy, _runner = _patch(_EMPTY, _TWO_NEW)

        assert payload["status"] == "created"
        assert "AddFixtures" in deploy.deployed[0][1]


class TestItNeverInventsAFixtureId:
    """이미 쓰는 FID에 패치하면 **엉뚱한 픽스처를 덮는다. 실행 취소가 없다.**

    [round24 후속] 실측: FID 1~39가 쓰이는 쇼에서 이 도구가 1~6을 배정했다.
    원인은 `prechk.inventory`가 FID를 화이트리스트 밖에 두어 **아예 읽지 않는다**는
    것이었다 — `fid_note`는 늘 "미확정"이라 숫자로 읽으면 목록이 빈다.
    """

    def test_it_refuses_when_the_fid_read_is_not_complete(self):
        # [HARD] 못 읽었으면 고르지 않는다. 이 한 줄이 덮어쓰기를 막는다.
        class NoFids(ConsolePorts):
            def query_property(self, path, property_name):
                if property_name == "FID":
                    return {"ok": False}
                return super().query_property(path, property_name)

        rig = [(f"RLB {i}", f"5.{i:03d}") for i in range(1, 7)]
        ports = NoFids(rig, rig)
        registry = build_toolset(
            execution_port=ScriptedExec(),
            state_port=ports,
            property_port=ports,
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
        payload = json.loads(execution.result.content)

        assert payload["status"] == "fids_unknown"
        assert "지어내지 마라" in payload["guidance"]

    def test_it_steps_over_the_fids_already_in_use(self):
        # 대역 콘솔의 기존 장비 FID는 1..n 이다 — 그 위로 가야 한다.
        rows = [(f"RLB {i}", f"5.{i:03d}") for i in range(1, 7)]
        ports = ConsolePorts(rows, rows)
        registry = build_toolset(
            execution_port=ScriptedExec(),
            state_port=ports,
            property_port=ports,
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
                    "address": "9.1",
                    "count": 2,
                    "channels_per_fixture": 14,
                },
            )
        )
        payload = json.loads(execution.result.content)
        assigned = [f["fid"] for f in payload["plan"]["fixtures"]]

        assert min(assigned) > 6, f"쓰는 번호를 배정했다: {assigned}"

    def test_explicit_fids_are_honoured(self):
        # 사용자가 정해 주면 그대로 쓴다 — 그때는 판독이 필요 없다.
        ports = ConsolePorts(_EMPTY, _TWO_NEW)
        deploy = ScriptedDeploy()
        registry = build_toolset(
            execution_port=ScriptedExec(),
            state_port=ports,
            property_port=ports,
            deploy_pipeline=deploy,
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
                    "fids": [201, 202],
                },
            )
        )
        payload = json.loads(execution.result.content)

        assert [f["fid"] for f in payload["plan"]["fixtures"]] == [201, 202]

    def test_the_note_field_is_never_read_as_a_number(self):
        # [HARD] `fid_note`는 값이 아니라 표시다 — 여기서 숫자를 캐면 안 된다.
        from server.prechk.inventory import FID_UNRESOLVED_MARK, fid_note

        assert fid_note() == FID_UNRESOLVED_MARK
        assert not FID_UNRESOLVED_MARK.isdigit()


class TestTheCardCarriesTheDestinationCheck:
    """서버가 목적지를 못 읽으므로, **사람이 눈으로 대조할 문자열**을 카드가 나른다.

    [round24 후속 실측] 실물에서 세 상태를 구별했다:
      `Admin[Fixture]>`                                   편집기 닫힘
      `Admin@ShowData/LivePatch/Stages>`                  창은 떴으나 한 계층 위
      `Admin@ShowData/LivePatch/Stages/Stage 1/Fixtures>` 픽스처 계층 — 이것이어야 한다
    responder는 `CurrentDestination`을 노출하지 않고 Lua `GetFocus()`는 명령줄 위젯만
    돌려주므로(2026-08-18 실측) 서버가 착수 전에 확인하지 못한다.

    카드는 **0건일 때만** 뜬다 — 자동 실행이 성공하면 물을 것이 없다.
    """

    def test_the_card_names_the_prompt_to_look_for(self):
        # [HARD] 이 문자열이 빠지면 조작자는 조건을 못 지킨 채 두고, 결과는 또 0건이다.
        from server.vwx.stagedpatch import DESTINATION_MARKER

        port = SaysRan()
        _patch(_EMPTY, question_port=port)

        steps = " ".join(port.asked[0].steps)
        assert DESTINATION_MARKER in steps

    def test_it_says_what_a_wrong_prompt_looks_like(self):
        # 맞는 모양만 알려 주면 틀린 상태를 알아보지 못한다.
        port = SaysRan()
        _patch(_EMPTY, question_port=port)

        steps = " ".join(port.asked[0].steps)
        assert "Admin[Fixture]" in steps

    def test_the_marker_travels_in_the_payload_too(self):
        payload, _deploy, _runner = _patch(_EMPTY, _TWO_NEW)

        assert payload["destination_marker"].endswith("Fixtures>")


class TwoModePorts(ConsolePorts):
    """모드가 둘인 타입 — Mode 0(TotalFootprint 14)·Mode 1(26). 사용자 선택 갈래의 실물."""

    MODE_FOOTPRINTS = {1: 14, 2: 26}

    def _mode_names(self) -> list[tuple[int, str]]:
        return [(1, "Mode 0"), (2, "Mode 1")]


class PicksMode:
    """첫 질문(모드 선택)에는 모드를, 그다음(실행 인계)에는 «실행했습니다»를 답한다."""

    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.asked: list[object] = []

    def ask(self, request) -> str:
        self.asked.append(request)
        return self.mode if len(self.asked) == 1 else ANSWER_RAN_IT


class TestTheConsoleOwnsTheFootprint:
    """폭과 모드는 콘솔 실측이다 — 모델 추측이 아니다.

    2026-08-18 실전: 모델이 LEDBeam 350 Mode 1을 14ch로 추측해 14 간격 주소
    계획을 만들었고, 실제 폭과 어긋나 수동 실행에서도 전량 거부됐다.
    """

    def test_a_wrong_claimed_width_is_overridden_by_the_measured_one(self):
        # [HARD] 모델이 99ch라고 주장해도 계획은 실측 14ch 간격으로 나간다.
        payload, deploy, _runner = _patch(
            _EMPTY,
            arguments={
                "console_type": _TYPE,
                "console_mode": _MODE,
                "address": "4.1",
                "count": 2,
                "channels_per_fixture": 99,
            },
        )

        assert payload["footprint_corrected"] == {"claimed": 99, "measured": 14}
        assert payload["channels_per_fixture"] == 14
        assert '"4.15"' in deploy.deployed[0][1]  # 두 번째 자리 = 4.1 + 14

    def test_the_width_argument_is_not_required_when_the_console_answers(self):
        payload, _deploy, _runner = _patch(
            _EMPTY,
            arguments={
                "console_type": _TYPE,
                "console_mode": _MODE,
                "address": "4.1",
                "count": 2,
            },
        )

        assert payload["footprint_source"] == "console"
        assert payload["channels_per_fixture"] == 14

    def test_a_mode_the_console_does_not_have_is_refused_not_guessed(self):
        payload, deploy, _runner = _patch(
            _EMPTY,
            arguments={
                "console_type": _TYPE,
                "console_mode": "Mode 9",
                "address": "4.1",
                "count": 2,
                "channels_per_fixture": 14,
            },
        )

        assert payload["status"] == "mode_not_found"
        assert deploy.deployed == []

    def test_an_omitted_mode_is_the_users_choice_not_the_models(self):
        # 사용자가 Mode 1(26ch)을 고르면 계획도 26 간격으로 나간다.
        port = PicksMode("Mode 1")
        payload, deploy, _runner = _patch(
            _EMPTY,
            question_port=port,
            arguments={"console_type": _TYPE, "address": "4.1", "count": 2},
            ports=TwoModePorts(_EMPTY),
        )

        first = port.asked[0]
        assert [option.label for option in first.options][:2] == ["Mode 0", "Mode 1"]
        assert "26채널" in first.options[1].description
        assert payload["console_mode"] == "Mode 1"
        assert payload["channels_per_fixture"] == 26
        assert '"4.27"' in deploy.deployed[0][1]  # 4.1 + 26

    def test_a_cancelled_mode_choice_patches_nothing(self):
        payload, deploy, _runner = _patch(
            _EMPTY,
            question_port=PicksMode(ANSWER_CANCEL),
            arguments={"console_type": _TYPE, "address": "4.1", "count": 2},
            ports=TwoModePorts(_EMPTY),
        )

        assert payload["status"] == "mode_not_chosen"
        assert deploy.deployed == []

    def test_an_unreadable_tree_without_a_fallback_width_refuses(self):
        # 실측도 없고 호출자 폭도 없으면 지어내지 않는다.
        class NoTree(ConsolePorts):
            def _type_tree(self, path: str) -> dict:
                return {"ok": False}

        payload, deploy, _runner = _patch(
            _EMPTY,
            arguments={"console_type": _TYPE, "address": "4.1", "count": 2},
            ports=NoTree(_EMPTY),
        )

        assert payload["status"] == "footprint_unknown"
        assert deploy.deployed == []


class TestItOnlyUsesTheRealExecutionProtocol:
    """도구는 `CommandExecutionPort`에 있는 것만 부른다.

    [2026-08-18 실기] `run([...])`은 테스트 가짜에만 있던 모양이었고, 실기에서
    AttributeError로 «서버 내부 문제»가 되었다. 아래 포트는 `execute` 외의 어떤
    접근도 즉시 실패로 만든다 — 프로토콜을 넓히는 수정이 여기서 먼저 걸린다.
    """

    class StrictPort:
        def __init__(self) -> None:
            self.sent: list[str] = []

        def execute(self, command: str):
            self.sent.append(command)
            return type("R", (), {"command": command, "ok": True, "detail": "OK"})()

        def __getattr__(self, name: str):
            raise AssertionError(f"도구가 프로토콜 밖의 {name!r}을 불렀다")

    def test_the_patch_runs_through_execute_and_nothing_else(self):
        port = self.StrictPort()
        ports = ConsolePorts(_EMPTY, _TWO_NEW)
        registry = build_toolset(
            execution_port=port,
            state_port=ports,
            property_port=ports,
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
                },
            )
        )
        payload = json.loads(execution.result.content)

        assert payload["status"] == "created"
        assert port.sent == ["Plugin 'CopilotPatchSharpy250WBeam'"]


class TestTheGateScreensTheAutomatedRun:
    """자동 실행은 **게이트를 통과해서** 나간다 — 우회하면 라이브 잠금이 무력해진다.

    AC-PRECHK-014 ②(실행 포트의 유일한 호출자는 `run_commands`)를 패치 자동화가
    깨뜨릴 수 있는 자리다. 게이트가 막으면 명령은 콘솔에 닿지 않고, 도구는
    생겼다고 말하지 않는다.
    """

    class BlockingGate:
        def __init__(self) -> None:
            self.screened: list[list[str]] = []

        def screen(self, commands):
            self.screened.append(list(commands))
            rows = tuple(
                type(
                    "D",
                    (),
                    {"command": c, "status": "blocked", "reasons": ("라이브 잠금",)},
                )()
                for c in commands
            )
            return type(
                "S",
                (),
                {
                    "cleared": False,
                    "status": "blocked_live_lock",
                    "notice": "라이브 잠금",
                    "commands": rows,
                },
            )()

    def test_a_blocked_bundle_never_reaches_the_console(self):
        gate = self.BlockingGate()
        ports = ConsolePorts(_EMPTY)
        runner = ScriptedExec()
        registry = build_toolset(
            execution_port=runner,
            state_port=ports,
            property_port=ports,
            deploy_pipeline=ScriptedDeploy(),
            question_port=SaysRan(),
            bundle_gate=gate,
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
                },
            )
        )
        payload = json.loads(execution.result.content)

        assert gate.screened, "게이트가 번들을 보지 못했다 — 우회다"
        assert runner.sent == [], "차단된 명령이 콘솔에 나갔다"
        assert payload["status"] != "created"
        # UI에는 게이트 판정이 올라간다 — 검증 결과(0건)로 덮지 않는다.
        assert [row.status for row in execution.command_outcomes] == ["blocked"]
