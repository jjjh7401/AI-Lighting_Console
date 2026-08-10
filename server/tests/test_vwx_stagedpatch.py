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
from server.orchestrator.tools import build_toolset
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

    def query_property(self, path: str, property_name: str) -> dict:
        index = int(path.rsplit("/", 1)[-1]) - 1
        rows = self._current()
        if not 0 <= index < len(rows):
            return {"ok": False}
        name, patch = rows[index]
        value = {"Name": name, "Patch": patch, "FixtureType": _TYPE, "Mode": _MODE}.get(
            property_name
        )
        return {"ok": True, "value": value} if value is not None else {"ok": False}


class ScriptedExec:
    def __init__(self) -> None:
        self.sent: list[str] = []

    def run(self, commands):
        self.sent.extend(commands)
        return [
            type("R", (), {"command": command, "ok": True, "detail": "OK"})()
            for command in commands
        ]


def _patch(before, after=None, *, deploy_status="deployed", address="4.1", count=2):
    ports = ConsolePorts(before, after)
    deploy = ScriptedDeploy(deploy_status)
    runner = ScriptedExec()
    registry = build_toolset(
        execution_port=runner,
        state_port=ports,
        property_port=ports,
        deploy_pipeline=deploy,
    )
    execution = registry.dispatch(
        ToolCall(
            id="c1",
            name="patch_fixtures",
            arguments={
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


class TestTheToolTellsTheTruth:
    def test_a_run_that_created_nothing_says_so(self):
        # [HARD] 이 한 줄이 실물 거짓 보고를 막는다.
        payload, _deploy, runner = _patch(_EMPTY, _EMPTY)

        assert runner.sent, "실행은 했다"
        assert payload["status"] == "created_nothing"
        assert payload["created"] == 0
        assert "성공했다고 보고하지 마라" in payload["guidance"]

    def test_a_run_that_created_everything_says_so(self):
        payload, _deploy, _runner = _patch(_EMPTY, _TWO_NEW)

        assert payload["status"] == "created"
        assert payload["created"] == 2
        assert "확인했다" in payload["guidance"]

    def test_a_partial_run_is_not_dressed_up(self):
        payload, _deploy, _runner = _patch(_EMPTY, _TWO_NEW[:1])

        assert payload["status"] == "created_partially"
        assert "성공이라 말하지 마라" in payload["guidance"]

    def test_a_failed_deploy_never_reaches_the_console(self):
        payload, _deploy, runner = _patch(_EMPTY, _EMPTY, deploy_status="rejected")

        assert runner.sent == [], "배포가 안 됐는데 실행을 보냈다"
        assert payload["status"] == "not_deployed"

    def test_the_zero_case_points_at_the_untested_hypothesis(self):
        # 왜 안 되는지가 없으면 사용자는 같은 명령을 다시 누른다.
        payload, _deploy, _runner = _patch(_EMPTY, _EMPTY)

        assert "패치 편집기" in payload["guidance"]


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
