"""Tests for the `import_lxseq_patch` tool — SPEC-COPILOT-LXSEQ-001 M3.

AC-LXSEQ-011: 4지점 등재 · preview는 콘솔에 아무것도 쓰지 않는다.
AC-LXSEQ-012: apply는 `patch_fixtures`에 위임하고, 순서대로 돌다 첫 실패에서 멈춘다.
AC-LXSEQ-013: 같은 파일을 다시 넣어도 중복이 생기지 않는다.
AC-LXSEQ-014: 페이로드는 닫힌 키·닫힌 어휘이고 요약은 성공을 과장하지 않는다.
AC-LXSEQ-017: 채팅 붙여넣기 금지가 명문이고 받은 바이트의 해시가 페이로드에 실린다.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from pathlib import Path

import pytest

from server.llm.types import ToolCall
from server.lxseq.parser import parse_patch_csv
from server.orchestrator.tools import ANSWER_CANCEL, ANSWER_RAN_IT, TOOL_NAMES, build_toolset

FIXTURE_PATH = Path("server/tests/fixtures/lxseq/LXSEQ_RIG_01_ShowBase_r3.patch.csv")

TYPES_ROOT = "Patch/FixtureTypes"

#: `luagen`이 낸 `AddFixtures` 한 줄에서 값만 되뽑는다. 가짜 콘솔이 플러그인을
#: "실행"하려면 계획이 아니라 **생성물**을 읽어야 한다 — 계획을 그대로 믿으면
#: 실행 경로가 시험에서 빠진다.
_LUA_TYPE = re.compile(r'FixtureTypes\["([^"]+)"\]')
_LUA_MODE = re.compile(r'DMXModes\["([^"]+)"\]')
_LUA_FID = re.compile(r'fid = "(\d+)"')
_LUA_NAME = re.compile(r'name = "((?:[^"\\]|\\.)*)"')
_LUA_PATCH = re.compile(r'patch = \{ "([0-9]+\.[0-9]+)" \}')


def _csv_bytes() -> bytes:
    return FIXTURE_PATH.read_bytes()


def _b64(payload: bytes | None = None) -> str:
    return base64.b64encode(_csv_bytes() if payload is None else payload).decode("ascii")


def _records():
    return parse_patch_csv(_csv_bytes().decode("utf-8")).records


def _type_widths() -> dict[str, int]:
    widths: dict[str, int] = {}
    for record in _records():
        widths.setdefault(record.fixture_type, record.channels)
    return widths


def _parse_addfixtures(source: str) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for line in source.splitlines():
        if "AddFixtures(" not in line:
            continue
        type_hit = _LUA_TYPE.search(line)
        mode_hit = _LUA_MODE.search(line)
        fid_hit = _LUA_FID.search(line)
        name_hit = _LUA_NAME.search(line)
        patch_hit = _LUA_PATCH.search(line)
        assert type_hit and mode_hit and fid_hit and name_hit and patch_hit, line
        entries.append(
            {
                "fixture_type": type_hit.group(1),
                "mode": mode_hit.group(1),
                "fid": int(fid_hit.group(1)),
                "name": name_hit.group(1),
                "patch": patch_hit.group(1),
            }
        )
    return entries


class FakeConsole:
    """CSV의 8개 타입을 라이브러리에 갖고, 플러그인 실행으로 픽스처가 **실제로** 생기는 콘솔.

    모드는 타입마다 하나(폭 = CSV의 Ch)라 매퍼의 폭-유일 확정이 성립한다.
    """

    def __init__(
        self,
        fixtures: list[dict[str, object]] | None = None,
        *,
        truncate_at: int | None = None,
        handle_types: bool = False,
    ) -> None:
        self._widths = _type_widths()
        self._slots = {name: index + 1 for index, name in enumerate(self._widths)}
        self.fixtures: list[dict[str, object]] = list(fixtures or [])
        self.deployed: dict[str, str] = {}
        #: 실물 콘솔은 픽스처 열거를 19대에서 자른다 — `childCount`는 진짜 총계로
        #: 남고 `children`만 짧아진다. 절단되지 않는 가짜는 판독 게이트의 한 갈래를
        #: 통째로 가리므로(결함 D1이 실기에서야 드러난 이유) 이 변형을 둔다.
        self.truncate_at = truncate_at
        #: 실물 콘솔의 픽스처 FixtureType 프로퍼티는 이름이 아니라
        #: 'FixtureType <슬롯>' 형태의 객체 핸들을 돌려준다 — 결함 D2.
        #: 라이브 관측: SPEC-COPILOT-LXSEQ-001/progress.md:621~626 (86행 전량이
        #: 8개 슬롯에 걸쳐 같은 형식). 이름을 돌려주는 가짜는 이름-대조 갈래를
        #: 통째로 가리므로 truncate_at 과 같은 모양의 변형을 둔다.
        #: 기본값은 현재 동작(이름)이다 — 켜야만 핸들이 나온다.
        #: 이 형식 문자열은 테스트에 하드코딩된 가정이다(acceptance.md 앞머리
        #: [HARD]). 실기 형식이 다르면 번역은 미번역 경로로 떨어진다.
        self.handle_types = handle_types

    # -- 계획 → 콘솔 상태(테스트가 미리 채워 둘 때 쓴다) --------------------
    @staticmethod
    def mode_name(type_name: str) -> str:
        return f"{type_name} std"

    def _name_for_slot(self, slot: int) -> str | None:
        for name, value in self._slots.items():
            if value == slot:
                return name
        return None

    # -- StateQueryPort -----------------------------------------------------
    def query_state(self, path: str) -> dict:
        if path.startswith(TYPES_ROOT):
            return self._type_tree(path)
        children = [
            {"class": "Fixture", "i": index + 1, "name": row["name"]}
            for index, row in enumerate(self.fixtures)
        ]
        cut = self.truncate_at
        truncated = cut is not None and len(children) > cut
        return {
            "ok": True,
            "path": path,
            # `childCount`는 자르지 않는다 — 그것이 진짜 총계다. 짧아지는 것은
            # `children`뿐이고, 판독기는 슬롯을 하나씩 지목해 복구 스윕한다.
            "truncated": truncated,
            "node": {"childCount": len(children)},
            "children": children[:cut] if truncated else children,
        }

    def _type_tree(self, path: str) -> dict:
        if path == TYPES_ROOT:
            children = [
                {"i": slot, "name": name, "class": "FixtureType"}
                for name, slot in self._slots.items()
            ]
        elif path.endswith("/DMXModes"):
            slot = int(path.split("/")[-2])
            name = self._name_for_slot(slot)
            if name is None:
                return {"ok": False}
            children = [{"i": 1, "name": self.mode_name(name), "class": "DMXMode"}]
        else:
            return {"ok": False}
        return {
            "ok": True,
            "path": path,
            "truncated": False,
            "node": {"childCount": len(children)},
            "children": children,
        }

    # -- PropertyQueryPort --------------------------------------------------
    def query_property(self, path: str, property_name: str) -> dict:
        if path.startswith(f"{TYPES_ROOT}/") and "/DMXModes/" in path:
            if property_name != "TotalFootprint":
                return {"ok": False}
            name = self._name_for_slot(int(path.split("/")[-3]))
            width = self._widths.get(name or "")
            return {"ok": True, "value": width} if width else {"ok": False}
        index = int(path.rsplit("/", 1)[-1]) - 1
        if not 0 <= index < len(self.fixtures):
            return {"ok": False}
        row = self.fixtures[index]
        fixture_type = row["fixture_type"]
        if self.handle_types:
            # 실기와 같은 갈래: 픽스처 프로퍼티만 핸들이고 FixtureTypes 트리
            # 열거(_type_tree)는 이름을 그대로 준다. 둘 다 핸들로 바꾸면 재현이
            # 실기와 어긋난다(REQ-PARITY-003).
            slot = self._slots.get(str(fixture_type))
            if slot is not None:
                fixture_type = f"FixtureType {slot}"
        value = {
            "Name": row["name"],
            "Patch": row["patch"],
            "FixtureType": fixture_type,
            "Mode": row["mode"],
            "FID": str(row["fid"]),
        }.get(property_name)
        return {"ok": True, "value": value} if value is not None else {"ok": False}

    # -- 실행 --------------------------------------------------------------
    def materialize(self, plugin_name: str, limit: int | None = None) -> int:
        source = self.deployed.get(plugin_name)
        if source is None:
            return 0
        entries = _parse_addfixtures(source)
        if limit is not None:
            entries = entries[:limit]
        self.fixtures.extend(entries)
        return len(entries)


class FakeDeploy:
    def __init__(self, console: FakeConsole, status: str = "deployed") -> None:
        self.console = console
        self.status = status
        self.deployed: list[tuple[str, str]] = []

    def deploy(self, name: str, source: str):
        self.deployed.append((name, source))
        if self.status == "deployed":
            self.console.deployed[name] = source
        return type(
            "Outcome",
            (),
            {"status": self.status, "destructive": False, "detail": "", "compile_error": None},
        )()


class FakeExec:
    """`CommandExecutionPort` 그대로 — `execute(command)` 하나뿐이다."""

    def __init__(
        self,
        console: FakeConsole,
        *,
        create: bool = True,
        partial: tuple[int, int] | None = None,
    ) -> None:
        self.console = console
        self.create = create
        #: (몇 번째 플러그인 실행에서, 몇 대만 생기는가) — 부분 생성 시나리오.
        self.partial = partial
        self.sent: list[str] = []

    def execute(self, command: str):
        self.sent.append(command)
        hit = re.fullmatch(r"Plugin '([^']+)'", command)
        if hit is not None and self.create:
            limit = None
            if self.partial is not None and len(self.sent) == self.partial[0]:
                limit = self.partial[1]
            self.console.materialize(hit.group(1), limit=limit)
        return type("R", (), {"command": command, "ok": True, "detail": "OK"})()


class Answers:
    def __init__(self, answer: str = ANSWER_RAN_IT) -> None:
        self.answer = answer
        self.asked: list[object] = []

    def ask(self, request) -> str:
        self.asked.append(request)
        return self.answer


class CountingUpload:
    """세션 업로드 포트 — 읽히면 센다(결정 H의 기각안이 쓰이지 않았음을 증명한다)."""

    def __init__(self) -> None:
        self.reads = 0
        self.report = None

    @property
    def content_base64(self) -> str:
        self.reads += 1
        return _b64()


def _toolset(console: FakeConsole, *, exec_port=None, deploy=None, question=None, upload=None):
    return (
        build_toolset(
            execution_port=exec_port if exec_port is not None else FakeExec(console),
            state_port=console,
            property_port=console,
            deploy_pipeline=deploy if deploy is not None else FakeDeploy(console),
            question_port=question if question is not None else Answers(),
            vectorworks_upload=upload,
        ),
    )[0]


def _call(registry, **arguments):
    if "file_content_base64" not in arguments:
        arguments["file_content_base64"] = _b64()
    execution = registry.dispatch(
        ToolCall(id="lx1", name="import_lxseq_patch", arguments=arguments)
    )
    return json.loads(execution.result.content), execution


def _run(console=None, **arguments):
    console = console if console is not None else FakeConsole()
    deploy = FakeDeploy(console)
    runner = FakeExec(console)
    registry = _toolset(console, exec_port=runner, deploy=deploy)
    payload, execution = _call(registry, **arguments)
    return payload, execution, console, deploy, runner


def _planned_fixtures(payload: dict) -> list[dict[str, object]]:
    """preview 계획을 콘솔 상태 행으로 편다 — 부분 상태를 미리 만들 때 쓴다."""
    rows: list[dict[str, object]] = []
    for run in payload["plan"]["runs"]:
        universe, start = run["address"].split(".")
        width = run["channels_per_fixture"]
        for index, fid in enumerate(run["fids"]):
            rows.append(
                {
                    "fixture_type": run["console_type"],
                    "mode": run["console_mode"],
                    "fid": fid,
                    "name": f"{run['name_prefix']} {fid}",
                    "patch": f"{universe}.{int(start) + index * width}",
                }
            )
    return rows


# ---------------------------------------------------------------------------
# AC-LXSEQ-011 — 4지점 등재 · preview 쓰기 0
# ---------------------------------------------------------------------------


def test_the_tool_is_registered_in_the_closed_set():
    assert "import_lxseq_patch" in TOOL_NAMES
    names = [d.name for d in _toolset(FakeConsole()).definitions()]
    assert "import_lxseq_patch" in names
    assert sorted(names) == sorted(TOOL_NAMES)


def test_preview_is_the_default_action_and_writes_nothing():
    payload, _execution, _console, deploy, runner = _run()

    assert payload["apply"]["entered"] is False
    assert deploy.deployed == []
    assert runner.sent == []


def test_the_write_recorder_is_not_vacuous():
    # 비공허성 — 같은 가짜로 patch_fixtures를 직접 부르면 기록이 남는다.
    console = FakeConsole()
    deploy = FakeDeploy(console)
    runner = FakeExec(console)
    registry = _toolset(console, exec_port=runner, deploy=deploy)
    registry.dispatch(
        ToolCall(
            id="direct",
            name="patch_fixtures",
            arguments={
                "console_type": "Robe MegaPointe",
                "address": "9.1",
                "count": 1,
                "fids": [901],
            },
        )
    )

    assert len(deploy.deployed) >= 1
    assert len(runner.sent) >= 1


def test_preview_plans_twelve_runs_over_the_real_csv():
    payload, _execution, _console, _deploy, _runner = _run()

    assert len(payload["plan"]["runs"]) == 12
    assert payload["plan"]["write_count_planned"] == 86


def test_a_missing_or_corrupt_payload_is_a_korean_error():
    console = FakeConsole()
    registry = _toolset(console)

    missing, missing_exec = _call(registry, file_content_base64=None)
    assert missing_exec.result.is_error is True
    assert "file_content_base64" in json.dumps(missing, ensure_ascii=False)

    broken, broken_exec = _call(registry, file_content_base64="not base64 !!!")
    assert broken_exec.result.is_error is True
    assert "base64" in json.dumps(broken, ensure_ascii=False)


# ---------------------------------------------------------------------------
# AC-LXSEQ-012 — apply는 위임한다 · 순차 · 중단
# ---------------------------------------------------------------------------


def test_apply_delegates_every_run_and_reports_created():
    payload, _execution, _console, deploy, runner = _run(action="apply")

    statuses = [run["status"] for run in payload["apply"]["runs"]]
    assert statuses == ["created"] * 12
    assert len(deploy.deployed) == 12
    assert len([line for line in runner.sent if line.startswith("Plugin ")]) == 12
    assert "86대" in payload["summary_ko"]


def test_each_run_gets_its_own_plugin_name():
    _payload, _execution, _console, deploy, _runner = _run(action="apply")

    # 타입마다 자기 플러그인 — 하나를 돌려 쓰면 뒤 배포가 앞 소스를 덮는다.
    assert len({name for name, _ in deploy.deployed}) == len(
        {run["console_type"] for run in _run(action="preview")[0]["plan"]["runs"]}
    )


def test_the_lua_comes_from_luagen_not_from_lxseq():
    _payload, _execution, _console, deploy, _runner = _run(action="apply")

    source = deploy.deployed[0][1]
    assert "AddFixtures(" in source
    assert 'FixtureTypes["' in source


def test_apply_stops_at_the_first_run_that_is_not_created():
    console = FakeConsole()
    deploy = FakeDeploy(console)
    # 3번째 플러그인 실행에서 1대만 생긴다 → created_partially.
    runner = FakeExec(console, partial=(3, 1))
    registry = _toolset(console, exec_port=runner, deploy=deploy)
    payload, _execution = _call(registry, action="apply")

    runs = payload["apply"]["runs"]
    assert runs[2]["status"] == "created_partially"
    assert payload["apply"]["stopped_at"] == 2
    assert [run["status"] for run in runs[3:]] == ["not_attempted"] * 9
    assert len(deploy.deployed) == 3


def test_apply_propagates_awaited_human_and_stops():
    console = FakeConsole()
    deploy = FakeDeploy(console)
    runner = FakeExec(console, create=False)  # 실행해도 아무것도 안 생긴다
    registry = _toolset(console, exec_port=runner, deploy=deploy, question=Answers(ANSWER_CANCEL))
    payload, execution = _call(registry, action="apply")

    assert payload["apply"]["runs"][0]["status"] == "not_run"
    assert payload["apply"]["stopped_at"] == 0
    assert execution.awaited_human is True
    assert len(deploy.deployed) == 1


def test_only_fids_narrows_the_plan_to_one_run():
    payload, _execution, _console, _deploy, _runner = _run(only_fids=[101, 102])

    assert len(payload["plan"]["runs"]) == 1
    assert payload["plan"]["runs"][0]["count"] == 2
    assert payload["plan"]["runs"][0]["fids"] == [101, 102]


# ---------------------------------------------------------------------------
# AC-LXSEQ-013 — 재실행 멱등
# ---------------------------------------------------------------------------


def test_a_second_preview_after_apply_plans_nothing():
    console = FakeConsole()
    deploy = FakeDeploy(console)
    runner = FakeExec(console)
    registry = _toolset(console, exec_port=runner, deploy=deploy)
    first, _ = _call(registry, action="apply")
    assert first["apply"]["runs"] and all(r["status"] == "created" for r in first["apply"]["runs"])

    second, _ = _call(registry, action="preview")

    assert second["plan"]["runs"] == []
    assert len(second["plan"]["skipped"]) == 86
    assert {row["kind"] for row in second["plan"]["skipped"]} == {"already_patched"}


def test_a_second_apply_writes_nothing_and_is_not_an_error():
    console = FakeConsole()
    deploy = FakeDeploy(console)
    runner = FakeExec(console)
    registry = _toolset(console, exec_port=runner, deploy=deploy)
    _call(registry, action="apply")
    before = len(deploy.deployed)

    payload, execution = _call(registry, action="apply")

    assert len(deploy.deployed) == before
    assert payload["apply"]["entered"] is True
    assert payload["apply"]["runs"] == []
    assert "할 일 없음" in payload["summary_ko"]
    assert execution.result.is_error is False


def test_a_truncating_console_still_reports_already_patched():
    # 결함 D1 (M4 실기): 86대를 채운 콘솔은 열거를 19대에서 자른다. 그때도 선언된
    # 자식은 전부 관측되므로 «이미 패치됨»으로 갈려야 한다 — 「콘솔을 다 못 읽었다」가
    # 아니다. 절단되지 않는 가짜 콘솔은 이 갈래를 영원히 가린다.
    plan_payload, _execution, _console, _deploy, _runner = _run()
    rows = _planned_fixtures(plan_payload)
    assert len(rows) == 86

    console = FakeConsole(fixtures=rows, truncate_at=19)
    payload, execution = _call(_toolset(console), action="preview")

    assert payload["console_read"]["complete_enough_to_judge_absence"] is True
    assert payload["plan"]["runs"] == []
    assert payload["plan"]["write_count_planned"] == 0
    assert {row["kind"] for row in payload["plan"]["skipped"]} == {"already_patched"}
    assert execution.result.is_error is False


def test_a_truncating_console_is_not_vacuously_truncated():
    # 비공허성 — 절단 변형이 실제로 짧은 목록을 낸다(그렇지 않으면 위 테스트는
    # 절단을 시험한 것이 아니라 그냥 온전한 콘솔을 다시 시험한 것이다).
    plan_payload, _execution, _console, _deploy, _runner = _run()
    console = FakeConsole(fixtures=_planned_fixtures(plan_payload), truncate_at=19)

    answer = console.query_state("Patch/Stages/1/Fixtures")

    assert answer["node"]["childCount"] == 86
    assert len(answer["children"]) == 19
    assert answer["truncated"] is True


def test_a_half_patched_console_replans_only_the_remainder():
    # 비공허성 — 부분 상태에서 게이트가 정확히 가른다.
    plan_payload, _execution, _console, _deploy, _runner = _run()
    rows = _planned_fixtures(plan_payload)
    assert len(rows) == 86

    console = FakeConsole(fixtures=rows[:43])
    payload, _ = _call(_toolset(console), action="preview")

    planned = sum(run["count"] for run in payload["plan"]["runs"])
    already = [row for row in payload["plan"]["skipped"] if row["kind"] == "already_patched"]
    assert planned == 43
    assert len(already) == 43


def test_the_handle_branch_is_off_by_default_and_leaves_the_tree_naming():
    # AC-PARITY-001 · 003. 픽스처 프로퍼티만 핸들이고 FixtureTypes 트리 열거는
    # 이름을 유지한다 — 실기에서도 그쪽은 이름이 나오므로, 둘 다 핸들로 바꾸면
    # 재현이 실기와 어긋난다(과하게 맞추는 것도 어긋남이다).
    plain = FakeConsole()
    handled = FakeConsole(handle_types=True)
    type_name = next(iter(plain._slots))
    row = {"fixture_type": type_name, "mode": "m", "fid": 7, "name": "N", "patch": "1.1"}
    plain.fixtures = [row]
    handled.fixtures = [row]

    assert plain.query_property("Patch/x/1", "FixtureType")["value"] == type_name
    assert handled.query_property("Patch/x/1", "FixtureType")["value"] == "FixtureType 1"
    tree_names = [child["name"] for child in handled.query_state(TYPES_ROOT)["children"]]
    assert type_name in tree_names


def test_a_handle_answering_console_still_reports_already_patched():
    # 결함 D2 (M4 실기): 실물 콘솔의 픽스처 FixtureType 은 이름이 아니라
    # "FixtureType <슬롯>" 핸들이다. 매퍼는 이름과 대조하므로 비교가 항상
    # 어긋나 「이미 패치됨」 갈래가 실기에서 한 번도 발화하지 않았다. 번역 전
    # 이 입력은 fid_occupied 86 을 냈다(프로브 실험 B · M1-2 가 재현).
    # 이름을 돌려주는 가짜는 이 갈래를 영원히 가린다.
    console = FakeConsole(handle_types=True)
    deploy = FakeDeploy(console)
    runner = FakeExec(console)
    registry = _toolset(console, exec_port=runner, deploy=deploy)
    _call(registry, action="apply")

    payload, execution = _call(registry, action="preview")

    assert payload["plan"]["runs"] == []
    assert len(payload["plan"]["skipped"]) == 86
    assert {row["kind"] for row in payload["plan"]["skipped"]} == {"already_patched"}
    # 번역이 실제로 일어났음을 값으로 확인한다 — 라벨만 보면, 다른 이유로
    # 같은 라벨이 나와도 통과한다.
    occupant = payload["plan"]["skipped"][0]["occupant"]
    assert not occupant["fixture_type"].startswith("FixtureType ")
    assert occupant["fixture_type"] in _type_widths()
    assert execution.result.is_error is False


def test_the_payload_says_why_a_type_stayed_untranslated():
    """코드리뷰 #3 — 다섯 사유가 감독에게 도달하지 않던 자리.

    사유를 다섯으로 가르는 데 감사 세 라운드를 썼는데 읽는 곳이 0이었다.
    판독이 실패하면 툴은 수정 전과 똑같이 fid_occupied 를 내보내고 신호가
    없다 — 그 침묵이 이 카드가 고치려는 결함과 같은 모양이다.
    """

    class DeadTypeTree(FakeConsole):
        """타입 트리만 답하지 않는 콘솔 — 픽스처 판독은 정상."""

        def query_state(self, path: str) -> dict:
            if path.startswith(TYPES_ROOT):
                return {"ok": False}
            return super().query_state(path)

    # 먼저 정상 콘솔로 86대를 채운다 — 타입 트리가 죽으면 계획 자체가 안 서므로,
    # 죽은 트리로는 「이미 패치된 리그를 다시 읽는」 상황을 만들 수 없다.
    plan_payload, _execution, _console, _deploy, _runner = _run()
    rows = _planned_fixtures(plan_payload)
    assert len(rows) == 86

    console = DeadTypeTree(fixtures=rows, handle_types=True)
    payload, _ = _call(_toolset(console), action="preview")
    translation = payload["console_read"]["type_translation"]

    assert translation["attempted"] is False
    assert translation["named"] == 0
    # 무엇이 몇 건 미번역인지 수로 나온다 — 「조용히 사라짐」의 반대.
    assert translation["untranslated"] == {"type_tree_unreadable": 86}
    assert translation["detail"]


def test_a_failed_translation_blocks_the_occupancy_verdict():
    """P13 — 번역이 실패했는데 계획이 서던 자리. 표에서 가장 위험한 행이다.

    타입 이름을 못 얻으면 「이미 패치됨」 비교가 성립하지 않는다. 그대로
    계획하면 이미 있는 86행이 fid_occupied 로 나가고, **그 라벨이 지시하는
    다음 행동은 「다른 FID 로 다시 패치하라」**다 — 같은 리그를 한 벌 더 만든다.
    이 앱에 실행 취소가 없다.
    """

    class DeadTypeTree(FakeConsole):
        def query_state(self, path: str) -> dict:
            if path.startswith(TYPES_ROOT):
                return {"ok": False}
            return super().query_state(path)

    plan_payload, _execution, _console, _deploy, _runner = _run()
    rows = _planned_fixtures(plan_payload)
    console = DeadTypeTree(fixtures=rows, handle_types=True)

    payload, execution = _call(_toolset(console), action="preview")

    # 「다른 FID 로 다시 패치하라」가 나가지 않는다.
    kinds = {row["kind"] for row in payload["plan"]["skipped"]}
    assert "fid_occupied" not in kinds
    assert kinds == {"console_read_incomplete"}
    assert payload["console_read"]["complete_enough_to_judge_absence"] is False
    assert payload["plan"]["runs"] == []
    assert payload["plan"]["write_count_planned"] == 0
    # 왜 막혔는지가 사유와 함께 나온다 — 침묵이 아니다.
    assert "type_tree_unreadable" in str(payload["console_read"]["caveat"])
    assert execution.result.is_error is False


def test_a_readable_console_is_not_blocked_by_the_translation_gate():
    """대조군 — 과잉으로 막지 않는다.

    콘솔이 이름을 돌려주는 경로(기본값)와 핸들을 이름으로 번역해 낸 경로 둘 다
    미번역 0건이라 이 갈래를 아예 타지 않는다. 이 대조군이 없으면 게이트가
    모든 재실행을 막아도 초록이다.
    """
    for handle in (False, True):
        console = FakeConsole(handle_types=handle)
        deploy = FakeDeploy(console)
        runner = FakeExec(console)
        registry = _toolset(console, exec_port=runner, deploy=deploy)
        _call(registry, action="apply")

        payload, _ = _call(registry, action="preview")

        assert payload["console_read"]["complete_enough_to_judge_absence"] is True
        assert {row["kind"] for row in payload["plan"]["skipped"]} == {"already_patched"}
        assert payload["console_read"]["type_translation"]["untranslated"] == {}


# ---------------------------------------------------------------------------
# AC-LXSEQ-014 — 닫힌 페이로드 · 한국어 · 성공 과장 금지
# ---------------------------------------------------------------------------

_TOP_KEYS = {"source", "types", "console_read", "plan", "apply", "summary_ko", "guidance"}
_SKIP_KINDS = {
    "type_unresolved",
    "mode_unresolved",
    "address_occupied",
    "fid_occupied",
    "already_patched",
    "console_read_incomplete",
    "universe_overflow",
    "rejected_row",
}
_REJECT_KINDS = {
    "non_integer_field",
    "universe_overflow",
    "address_out_of_range",
    "addr_range_mismatch",
    "duplicate_fid",
    "address_overlap_in_file",
    "zero_channels",
}


def test_the_payload_carries_exactly_the_closed_top_level_keys():
    payload, _execution, _console, _deploy, _runner = _run()

    assert set(payload) == _TOP_KEYS


def test_payload_vocabularies_are_closed():
    payload, _ = _call(_toolset(FakeConsole()), action="preview")

    assert {row["kind"] for row in payload["plan"]["skipped"]} <= _SKIP_KINDS
    assert {row["kind"] for row in payload["source"]["rejected"]} <= _REJECT_KINDS


def test_a_partial_apply_summary_never_claims_success():
    console = FakeConsole()
    runner = FakeExec(console, partial=(3, 1))
    registry = _toolset(console, exec_port=runner, deploy=FakeDeploy(console))
    payload, _ = _call(registry, action="apply")

    summary = payload["summary_ko"]
    assert "성공" not in summary
    assert "완료" not in summary
    assert "부분" in summary


def test_a_full_apply_summary_states_the_verified_count():
    payload, _execution, _console, _deploy, _runner = _run(action="apply")

    assert "86대" in payload["summary_ko"]
    assert "확인" in payload["summary_ko"]


def test_zero_writes_is_only_said_when_apply_was_not_entered():
    preview, _execution, _console, _deploy, _runner = _run()
    assert "쓰기 0건" in preview["summary_ko"]

    console = FakeConsole()
    runner = FakeExec(console, create=False)
    registry = _toolset(
        console, exec_port=runner, deploy=FakeDeploy(console), question=Answers(ANSWER_CANCEL)
    )
    applied, _ = _call(registry, action="apply")
    assert applied["apply"]["entered"] is True
    assert "쓰기 0건" not in applied["summary_ko"]


def test_guidance_tells_the_model_what_counts_as_success():
    payload, _execution, _console, _deploy, _runner = _run()

    guidance = payload["guidance"]
    assert "status == created" in guidance
    assert "덮어쓰지" in guidance
    assert "콘솔에서 타입" in guidance


# ---------------------------------------------------------------------------
# AC-LXSEQ-017 — 채팅 붙여넣기 금지 · 바이트 출처 대조
# ---------------------------------------------------------------------------


def _definition():
    for definition in _toolset(FakeConsole()).definitions():
        if definition.name == "import_lxseq_patch":
            return definition
    raise AssertionError("import_lxseq_patch is not registered")


def test_the_definition_forbids_pasting_and_closes_its_argument_set():
    definition = _definition()
    properties = definition.parameters["properties"]

    assert "붙여넣" in definition.description
    assert "파일 선택기" in definition.description
    assert "붙여넣" in properties["file_content_base64"]["description"]
    assert "파일 선택기" in properties["file_content_base64"]["description"]
    assert set(properties) == {
        "file_content_base64",
        "action",
        "name_prefix_mode",
        "only_fids",
        "mode_overrides",
    }
    assert definition.parameters["required"] == ["file_content_base64"]
    assert definition.parameters["additionalProperties"] is False


def test_guidance_repeats_the_paste_ban_to_the_model():
    payload, _execution, _console, _deploy, _runner = _run()

    assert "붙여넣" in payload["guidance"]


def test_the_payload_carries_the_sha256_of_the_bytes_it_received():
    raw = _csv_bytes()
    payload, _execution, _console, _deploy, _runner = _run()

    assert payload["source"]["sha256"] == hashlib.sha256(raw).hexdigest()
    assert payload["source"]["byte_length"] == len(raw)


def test_one_changed_byte_changes_the_hash():
    # 비공허성 — 해시가 실제로 바이트에서 나온다.
    raw = _csv_bytes()
    mutated = raw.replace(b"FOH", b"foh", 1)
    assert mutated != raw
    console = FakeConsole()
    payload, _ = _call(_toolset(console), file_content_base64=_b64(mutated))

    assert payload["source"]["sha256"] == hashlib.sha256(mutated).hexdigest()
    assert payload["source"]["sha256"] != hashlib.sha256(raw).hexdigest()


def test_the_session_upload_port_is_never_read():
    console = FakeConsole()
    upload = CountingUpload()
    registry = _toolset(console, upload=upload)
    _call(registry, action="preview")

    assert upload.reads == 0


@pytest.mark.parametrize("action", ["preview", "apply"])
def test_the_source_block_reports_what_the_parser_saw(action):
    payload, _execution, _console, _deploy, _runner = _run(action=action)

    assert payload["source"]["rows_total"] == 86
    assert payload["source"]["parsed"] == 86
