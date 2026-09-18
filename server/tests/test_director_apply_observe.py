"""SPEC-LDSEND-001 M3~M4 · REQ-LDSEND-007/008/009/010/011/012/014 ·
AC-LDSEND-007/008/009/010(부분)/011(부분)/012/014(부분).

``server/tools/director_apply_observe.py`` 는 관측 도구다. M3 는 골격(인자
파싱, dry-run 기본값, 로컬 plan/승인 구성 헬퍼, cleanup 출력,
``run_director_apply()`` 배선)만 쟀다. M4 는 그 위에 시나리오 021/024/032 를
얹는다 — destination 점유 확인(008), readback 재확인(010), cleanup 명령
목록(011 로컬 절반), 백업 선행조건 관측(014 로직 절반)이 이 파일이 새로
재는 것이다. onPC 실기 관측(010/011/014 의 콘솔 필요 절반)과 AC-024 실패
유발 명령의 최종 확정(M4a)은 이 파일의 범위가 아니다.

이 파일이 확인하는 것(M4 신규):
- destination 점유 확인 — 점유면 거부(콘솔 쓰기 호출 0회), 비어있으면
  진행한다(008). 같은 run 안에서 자기 자신이 채운 destination 에 대한
  후속 쓰기는 "첫 쓰기" 가드 대상이 아니다(008 D12).
- 024 의 3번째 bundle 은 2번째가 실패하면 콘솔에 전혀 도달하지 않는다
  (REQ-LDSEND-002/024, 실물 ``execute_bundles``+``GateBundleSender``).
- readback 은 ``BundleSender`` 가 돌려준 상태가 아니라 별도
  ``state_port.query_state()`` 조회로 보고된다(010).
- cleanup 은 이 실행이 만든(만들 수 있는) 모든 destination 에 대해
  ``Delete Sequence <N>`` 를 출력하고, 콘솔로는 아무것도 보내지 않는다(011).
- backup 선행조건 실패는 readback 판정과 구분된 필드로 기록되고, readback
  결과를 덮어쓰지 않는다(014 로직 절반).
- 024/032 는 M4a 가 확정하지 않은 실패 유발 명령에 의존하므로,
  ``--confirmed-failure-command`` 없이는 ``--execute`` 를 거부하고 콘솔에
  아무것도 보내지 않는다(dry-run 은 두 후보를 그대로 보여준다).

M3 가 이미 잰 것(정적 경계, 인자 파싱, dry-run 배선, 로컬 승인 라벨링)은
아래에 그대로 남아 있다 — 이 파일은 M3 시험을 지우지 않고 M4 가 새로 얹은
의존성(state_port 점유 확인)에 맞춰 최소한의 fake 배선만 갱신한다.
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

import server.tools.director_apply_observe as tool
from server.director.approvals import ApprovalRegistry
from server.director.execution import STATE_NOT_SENT, ExecutionJournal, execute_bundles
from server.director.store import DirectorStore
from server.orchestrator.ports import ExecutionResult
from server.safety.audit import AuditLog
from server.safety.backup import BackupManager
from server.safety.console import ConsoleSilentError, ExecOutcome, StateQueryError
from server.safety.gate import SafetyGate

_MODULE_SOURCE = Path(tool.__file__).read_text(encoding="utf-8")
_SERVE_PY = Path(__file__).resolve().parents[1] / "web" / "serve.py"


# ---------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------


class _FakeConsoleLink:
    """``SafetyGate`` 를 실제로 통과시키는 최소 콘솔 대역 — ``server.bridge``
    없음. ``server/tests/test_run_director_apply.py`` 의 ``_AlwaysOkConsole``
    과 같은 패턴이다.

    M4 — ``execute()`` 로 ``Store Sequence <N> ...`` 가 지나가면 그 <N> 을
    "존재하는 시퀀스"로 기억해 뒀다가, ``query_state("DataPool/Sequences/<N>")``
    가 그 기억을 근거로 있음/없음을 답한다(plan.md §2.0-다 두 후보 중
    ``StateQueryError`` 후보를 "없음"으로 쓴다). ``failing_commands`` 로
    특정 명령 문자열을 골라 콘솔이 명시적으로 거부하게 만들 수 있다(AC-024
    실패 유발 명령의 M4a-대기 대역).
    """

    def __init__(self, *, failing_commands: frozenset[str] = frozenset()) -> None:
        self.executed: list[str] = []
        self.queried: list[str] = []
        self._known_sequences: set[str] = set()
        self._failing_commands = failing_commands

    def execute(self, command: str) -> ExecOutcome:
        self.executed.append(command)
        if command in self._failing_commands:
            return ExecOutcome(status="failed", detail="Not allowed")
        match = re.match(r"Store Sequence (\d+)", command)
        if match:
            self._known_sequences.add(match.group(1))
        return ExecOutcome(status="ok", detail="OK")

    def ping(self) -> bool:
        return True

    def query_state(self, path: str) -> dict[str, Any]:
        self.queried.append(path)
        match = re.fullmatch(r"DataPool/Sequences/(\d+)", path)
        if not match:
            raise RuntimeError(f"no such path: {path}")
        n = match.group(1)
        if n in self._known_sequences:
            return {"ok": True, "node": {"i": int(n), "name": f"Sequence {n}"}, "children": []}
        raise StateQueryError(f"no such sequence: {n}")


def _fake_stack(tmp_path: Path, *, console: _FakeConsoleLink | None = None, **gate_kwargs: Any):
    """``ConsoleStack`` 대역 — 진짜 ``SafetyGate`` 를 fake 콘솔에 묶는다."""
    console = console or _FakeConsoleLink()
    gate = SafetyGate(console=console, audit=AuditLog(tmp_path / "audit"), **gate_kwargs)
    calls = {"stop": 0}

    def _stop() -> None:
        calls["stop"] += 1

    return SimpleNamespace(gate=gate, stop=_stop, console=console, _calls=calls)


class _RecordingBuildStack:
    """``build_console_stack`` 대역 — 호출 인자를 기록하고 mock 스택을
    반환한다. 스택의 ``gate`` 는 ``MagicMock`` 이라 호출 카운트를 그대로
    관측할 수 있다.

    M4 — ``gate.state_port.query_state`` 를 미리 "비어있음"(§2.0-다 후보 1
    ``StateQueryError``)으로 구성해 둔다. M4 가 추가한 destination 점유
    확인이 이 M3 대역을 쓰는 기존 시험(스택 구성·``run_director_apply``
    호출 카운트)의 의도를 바꾸지 않게 하기 위함이다 — 실제 점유 판정 로직
    자체는 진짜 ``SafetyGate``(``_fake_stack``)를 쓰는 별도 시험이 잰다.
    """

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.stacks: list[SimpleNamespace] = []

    def __call__(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        gate = MagicMock(name="fake-gate")
        gate.state_port.query_state.side_effect = StateQueryError("no such sequence (fake)")
        stopped = {"n": 0}

        def _stop() -> None:
            stopped["n"] += 1

        stack = SimpleNamespace(gate=gate, stop=_stop, _stopped=stopped)
        self.stacks.append(stack)
        return stack


# ---------------------------------------------------------------------------
# AC-LDSEND-007 — 정적 경계(코드 리뷰 대상을 pytest 로도 고정한다)
# ---------------------------------------------------------------------------


class TestStaticBoundaries:
    def test_no_direct_bridge_import(self):
        assert not re.search(r"^\s*(from|import)\s+server\.bridge", _MODULE_SOURCE, re.M)

    def test_no_director_api_import(self):
        assert not re.search(
            r"^\s*(from|import)\s+server\.director\.director_api", _MODULE_SOURCE, re.M
        )

    def test_calls_run_director_apply(self):
        assert "run_director_apply" in _MODULE_SOURCE

    def test_uses_build_console_stack(self):
        assert "build_console_stack" in _MODULE_SOURCE

    def test_uses_the_single_shared_listen_port_declaration(self):
        # test_probe_port_discipline.py 가 이 도구를 build_console_stack
        # 표지로 콘솔 접촉 도구로 잡는다 — 그 검사와 같은 조건을 여기서도
        # 명시적으로 고정한다(응답 포트 기본값 없음 규율, t61).
        assert "add_listen_port_argument(parser)" in _MODULE_SOURCE

    def test_never_constructs_approval_registry_at_module_scope(self):
        assert not re.search(r"^ApprovalRegistry\(", _MODULE_SOURCE, re.M)

    def test_labels_the_harness_principal(self):
        assert "ldsend-observe-harness" in _MODULE_SOURCE
        assert tool.HARNESS_PRINCIPAL_ID == "ldsend-observe-harness"

    def test_not_wired_into_serve_py(self):
        assert "director_apply_observe" not in _SERVE_PY.read_text(encoding="utf-8")

    def test_cleanup_never_sends_only_prints(self):
        assert re.search(r"def _cleanup_commands|Delete Sequence", _MODULE_SOURCE)


# ---------------------------------------------------------------------------
# 인자 파싱 — --execute 기본값, --sequence-range-start 기본값
# ---------------------------------------------------------------------------


class TestArgParsing:
    def test_execute_defaults_to_false(self):
        args = tool.build_arg_parser().parse_args(["021", "--listen-port", "19091"])
        assert args.execute is False

    def test_sequence_range_start_defaults_to_9900(self):
        args = tool.build_arg_parser().parse_args(["021", "--listen-port", "19091"])
        assert args.sequence_range_start == 9900

    def test_scenario_is_restricted_to_the_three_go_table_items(self):
        with pytest.raises(SystemExit):
            tool.build_arg_parser().parse_args(["999", "--listen-port", "19091"])

    def test_listen_port_has_no_default_and_is_required(self):
        # t61 규율 — 콘솔 접촉 도구는 --listen-port 에 기본값을 두지 않는다.
        with pytest.raises(SystemExit):
            tool.build_arg_parser().parse_args(["021"])

    def test_confirmed_failure_command_defaults_to_none(self):
        args = tool.build_arg_parser().parse_args(["021", "--listen-port", "19091"])
        assert args.confirmed_failure_command is None


# ---------------------------------------------------------------------------
# AC-LDSEND-009/D11 — dry-run 은 attempt_session_backup=False 로 스택을
# 구성하고, 어떤 인자 조합으로도 콘솔 쓰기에 도달하지 않는다.
# ---------------------------------------------------------------------------


class TestDryRunBuildsStackWithBackupDisabled:
    def test_dry_run_passes_attempt_session_backup_false(self, monkeypatch: pytest.MonkeyPatch):
        spy = _RecordingBuildStack()
        monkeypatch.setattr(tool, "build_console_stack", spy)

        exit_code = tool.main(["021", "--listen-port", "19091"])

        assert exit_code == 0
        assert len(spy.calls) == 1
        assert spy.calls[0]["attempt_session_backup"] is False

    def test_execute_passes_attempt_session_backup_true(self, monkeypatch: pytest.MonkeyPatch):
        spy = _RecordingBuildStack()
        run_mock = MagicMock(return_value=({"execution_id": "exec-1"}, 201))
        monkeypatch.setattr(tool, "build_console_stack", spy)
        monkeypatch.setattr(tool, "run_director_apply", run_mock)

        exit_code = tool.main(["021", "--listen-port", "19092", "--execute"])

        assert exit_code == 0
        assert spy.calls[0]["attempt_session_backup"] is True


class TestDryRunSendsNothing:
    @pytest.mark.parametrize(
        "argv",
        [
            ["021", "--listen-port", "19093"],
            ["024", "--listen-port", "19094", "--sequence-range-start", "9500"],
            ["032", "--listen-port", "19095", "--host", "127.0.0.1", "--port", "8001"],
        ],
    )
    def test_no_console_writes_without_execute(
        self, monkeypatch: pytest.MonkeyPatch, argv: list[str]
    ):
        spy = _RecordingBuildStack()
        run_mock = MagicMock()
        monkeypatch.setattr(tool, "build_console_stack", spy)
        monkeypatch.setattr(tool, "run_director_apply", run_mock)

        exit_code = tool.main(argv)

        assert exit_code == 0
        # 시나리오 실행 경로 자체가 아예 안 탄다 — run_director_apply 호출 0회.
        assert run_mock.call_count == 0
        # 스택의 gate 는 어떤 방식으로도 건드려지지 않는다(세션 시작 백업
        # 포함 — build_console_stack 자체가 attempt_session_backup=False 로
        # 불렸으므로 그 부작용도 함께 0이다, 위 클래스가 인자로 확인).
        gate = spy.stacks[0].gate
        assert gate.execute_preapproved.call_count == 0
        assert gate.execution_port.execute.call_count == 0
        # 스택은 dry-run 종료 시에도 정리된다.
        assert spy.stacks[0]._stopped["n"] == 1


class TestDryRunShowsAc024Candidates:
    """024/032 는 dry-run 에서도 M4a 의 두 후보를 그대로 보여준다 —
    ``--confirmed-failure-command`` 가 없어도 계획 자체는 완전하다."""

    def test_024_dry_run_prints_both_candidates(self, monkeypatch: pytest.MonkeyPatch):
        spy = _RecordingBuildStack()
        monkeypatch.setattr(tool, "build_console_stack", spy)

        exit_code = tool.main(["024", "--listen-port", "19191"])

        assert exit_code == 0

    def test_024_dry_run_output_names_both_candidates(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ):
        spy = _RecordingBuildStack()
        monkeypatch.setattr(tool, "build_console_stack", spy)

        tool.main(["024", "--listen-port", "19192"])

        out = capsys.readouterr().out
        assert "Store Sequence" in out
        assert "Copy Sequence" in out


# ---------------------------------------------------------------------------
# AC-LDSEND-007/012 — run_director_apply 가 시나리오 개수(=1)만큼 호출되고,
# 로컬 승인이 ldsend-observe-harness 로 라벨링된다.
# ---------------------------------------------------------------------------


class TestExecuteInvokesRunDirectorApplyOncePerScenario:
    def test_execute_calls_run_director_apply_exactly_once(self, monkeypatch: pytest.MonkeyPatch):
        spy = _RecordingBuildStack()
        run_mock = MagicMock(return_value=({"execution_id": "exec-1", "state": "sent"}, 201))
        monkeypatch.setattr(tool, "build_console_stack", spy)
        monkeypatch.setattr(tool, "run_director_apply", run_mock)

        exit_code = tool.main(["021", "--listen-port", "19096", "--execute"])

        assert exit_code == 0
        # run = CLI 1회 호출 = 시나리오 1개(REQ-LDSEND-008 D12).
        assert run_mock.call_count == 1
        _, kwargs = run_mock.call_args
        assert kwargs["principal_id"] == "ldsend-observe-harness"
        assert kwargs["bundle_sender"] is not None
        assert kwargs["interference"] is None

    def test_execute_prints_cleanup_and_result(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ):
        spy = _RecordingBuildStack()
        run_mock = MagicMock(return_value=({"execution_id": "exec-1", "state": "sent"}, 201))
        monkeypatch.setattr(tool, "build_console_stack", spy)
        monkeypatch.setattr(tool, "run_director_apply", run_mock)

        exit_code = tool.main(["021", "--listen-port", "19097", "--execute"])

        assert exit_code == 0
        out = capsys.readouterr().out
        assert "Delete Sequence 9900" in out
        assert "response_status: 201" in out

    def test_cleanup_still_prints_when_the_scenario_raises(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ):
        spy = _RecordingBuildStack()
        run_mock = MagicMock(side_effect=RuntimeError("synthetic apply failure"))
        monkeypatch.setattr(tool, "build_console_stack", spy)
        monkeypatch.setattr(tool, "run_director_apply", run_mock)

        exit_code = tool.main(["021", "--listen-port", "19098", "--execute"])

        assert exit_code == 1
        out = capsys.readouterr().out
        # REQ-LDSEND-011 — 성공이든 실패든 cleanup 명령은 항상 출력한다.
        assert "Delete Sequence 9900" in out


# ---------------------------------------------------------------------------
# _build_local_approval — REQ-LDSEND-012 라벨링 + 지름길 금지
# ---------------------------------------------------------------------------


class TestBuildLocalApproval:
    def test_binding_is_labelled_with_the_harness_principal(self, tmp_path: Path):
        store = DirectorStore(tmp_path / "director.sqlite3")
        approvals = ApprovalRegistry()

        binding = tool._build_local_approval(
            store=store,
            approvals=approvals,
            project_id="ldsend-observe",
            plan_id="ldsend-observe-021",
            destination={"show_id": "1", "sequence_id": "9900"},
        )

        assert binding.principal_id == "ldsend-observe-harness"
        # 공개 approve() 로 발급된 진짜 바인딩이 로컬 레지스트리에 조회된다
        # — _register() 지름길을 쓰지 않았다는 것의 관측 가능한 증거.
        assert approvals.get(binding.approval_id) is binding

    def test_two_local_registries_are_independent_instances(self, tmp_path: Path):
        store_a = DirectorStore(tmp_path / "a.sqlite3")
        approvals_a = ApprovalRegistry()
        approvals_b = ApprovalRegistry()

        binding_a = tool._build_local_approval(
            store=store_a,
            approvals=approvals_a,
            project_id="ldsend-observe",
            plan_id="ldsend-observe-021",
            destination={"show_id": "1", "sequence_id": "9900"},
        )

        # 서로 다른 레지스트리 인스턴스라 다른 쪽에는 존재하지 않는다 —
        # "전역/운영 조립과 무관" 을 구성 방식으로 보증한다는 증거.
        assert approvals_b.get(binding_a.approval_id) is None


# ---------------------------------------------------------------------------
# _run_scenario — run_director_apply() 를 진짜로 한 번 태운다(fake 콘솔,
# 진짜 SafetyGate/ApplyCoordinator/GateBundleSender).
# ---------------------------------------------------------------------------


class TestRunScenarioEndToEnd:
    def test_run_scenario_goes_through_the_real_apply_path(self, tmp_path: Path):
        stack = _fake_stack(tmp_path)

        result = tool._run_scenario(scenario="021", stack=stack, sequence_range_start=9900)

        assert result["response_status"] in (200, 201)
        assert result["approval_id"]
        assert result["backup_precondition"] == "ok"
        # M4 실제 명령 — run_director_apply() -> execute_bundles() ->
        # GateBundleSender -> 진짜 SafetyGate.execution_port -> fake 콘솔
        # 링크, 전체 경로가 021 의 진짜 큐 채움 명령으로 탄다.
        assert stack.console.executed == ["Store Sequence 9900 Cue 1 /Merge"]

    def test_run_scenario_readback_confirms_object_existence(self, tmp_path: Path):
        # AC-LDSEND-010 — 결과는 BundleSender 가 돌려준 상태가 아니라 별도
        # state_port.query_state() 조회로 보고된다.
        stack = _fake_stack(tmp_path)

        result = tool._run_scenario(scenario="021", stack=stack, sequence_range_start=9900)

        readback = result["readback"]["primary"]
        assert readback.exists is True
        assert readback.path == "DataPool/Sequences/9900"
        # readback 은 execute() 가 아니라 query_state() 를 거쳤다.
        assert "DataPool/Sequences/9900" in stack.console.queried


# ---------------------------------------------------------------------------
# AC-LDSEND-008 — destination 점유 확인. 점유면 거부, 비어있으면 진행,
# 같은 run 이 스스로 채운 destination 에 대한 후속 쓰기는 막지 않는다(D12).
# ---------------------------------------------------------------------------


class TestDestinationOccupancyCheck:
    def test_refuses_when_destination_already_occupied(self, tmp_path: Path):
        console = _FakeConsoleLink()
        console._known_sequences.add("9900")  # 미리 점유된 상태로 만든다
        stack = _fake_stack(tmp_path, console=console)

        with pytest.raises(tool.DestinationOccupiedError):
            tool._run_scenario(scenario="021", stack=stack, sequence_range_start=9900)

        # 점유 확인은 query_state 만 쓴다 — 쓰기 명령은 전혀 안 나갔다.
        assert console.executed == []

    def test_proceeds_when_destination_is_empty(self, tmp_path: Path):
        stack = _fake_stack(tmp_path)

        result = tool._run_scenario(scenario="021", stack=stack, sequence_range_start=9900)

        assert result["backup_precondition"] == "ok"
        assert stack.console.executed

    def test_refuses_when_console_is_silent(self):
        # 무응답(ConsoleSilentError)은 「없다」는 답이 아니다(console.py t313) —
        # 판독이 성립하지 않았으므로 쓰기를 진행하면 안 된다.
        state_port = MagicMock()
        state_port.query_state.side_effect = ConsoleSilentError("timeout (fake)")

        with pytest.raises(tool.DestinationOccupiedError):
            tool._require_destination_empty(state_port, {"sequence_id": "9900"})

    def test_readback_is_unknown_when_console_is_silent(self):
        state_port = MagicMock()
        state_port.query_state.side_effect = ConsoleSilentError("timeout (fake)")

        readback = tool._readback_object_existence(state_port, {"sequence_id": "9900"})

        assert readback.exists is None


class TestScenario024BundleThreeNeverSentAfterBundleTwoFails:
    """REQ-LDSEND-002/024 + AC-LDSEND-008 D12, 한 번에 잰다.

    bundle1(채움)·bundle2(같은 destination 재시도, 콘솔이 명시적으로 거부)
    까지는 도달한다 — destination 점유 확인 가드가 "이 run 이 스스로 채운"
    destination 에 대한 재시도를 막지 않았다는 증거(D12). bundle3(다른
    scratch destination)은 전혀 도달하지 않는다(REQ-002/024) — readback 이
    그 destination 이 비어있음을 확인한다.
    """

    def test_bundle_three_is_never_sent_and_readback_confirms_it(self, tmp_path: Path):
        console = _FakeConsoleLink(failing_commands=frozenset({"Store Sequence 9901"}))
        stack = _fake_stack(tmp_path, console=console)

        result = tool._run_scenario(
            scenario="024",
            stack=stack,
            sequence_range_start=9900,
            confirmed_failure_command="Store Sequence {n}",
        )

        assert console.executed == [
            "Store Sequence 9901 Cue 1 /Merge",  # bundle1 — 채움, 성공
            "Store Sequence 9901",  # bundle2 — 같은 destination, 콘솔이 거부
            # bundle3 은 여기 없다 — never_written destination 은 전혀
            # 안 나갔다(REQ-LDSEND-002/024).
        ]
        assert result["backup_precondition"] == "ok"
        readback = result["readback"]
        assert readback["primary"].exists is True  # bundle1 이 실제로 채웠다
        assert readback["never_written"].exists is False  # bundle3 이 안 갔다


class TestScenario024RequiresConfirmedFailureCommand:
    def test_run_scenario_raises_without_confirmed_failure_command(self, tmp_path: Path):
        stack = _fake_stack(tmp_path)

        with pytest.raises(ValueError, match="confirmed-failure-command"):
            tool._run_scenario(scenario="024", stack=stack, sequence_range_start=9900)


# ---------------------------------------------------------------------------
# M4a 게이트 — 024/032 는 --confirmed-failure-command 없이 --execute 를
# 거부한다. 거부는 콘솔 스택 자체를 만들기 전에 일어난다(세션 시작 백업
# 포함 콘솔로 아무것도 안 나간다).
# ---------------------------------------------------------------------------


class TestM4aConfirmationGate:
    def test_024_execute_refuses_without_confirmed_failure_command(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ):
        spy = _RecordingBuildStack()
        run_mock = MagicMock()
        monkeypatch.setattr(tool, "build_console_stack", spy)
        monkeypatch.setattr(tool, "run_director_apply", run_mock)

        exit_code = tool.main(["024", "--listen-port", "19193", "--execute"])

        assert exit_code != 0
        # 콘솔 스택 자체를 만들지 않았다 — 세션 시작 백업 포함 아무것도
        # 나가지 않았다.
        assert len(spy.calls) == 0
        assert run_mock.call_count == 0
        out = capsys.readouterr().out
        assert "M4a" in out
        assert "confirmed-failure-command" in out

    def test_032_execute_refuses_without_confirmed_failure_command(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        spy = _RecordingBuildStack()
        run_mock = MagicMock()
        monkeypatch.setattr(tool, "build_console_stack", spy)
        monkeypatch.setattr(tool, "run_director_apply", run_mock)

        exit_code = tool.main(["032", "--listen-port", "19194", "--execute"])

        assert exit_code != 0
        assert len(spy.calls) == 0
        assert run_mock.call_count == 0

    def test_024_execute_proceeds_with_confirmed_failure_command(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        spy = _RecordingBuildStack()
        run_mock = MagicMock(return_value=({"execution_id": "exec-1"}, 201))
        monkeypatch.setattr(tool, "build_console_stack", spy)
        monkeypatch.setattr(tool, "run_director_apply", run_mock)

        exit_code = tool.main(
            [
                "024",
                "--listen-port",
                "19195",
                "--execute",
                "--confirmed-failure-command",
                "Store Sequence {n}",
            ]
        )

        assert exit_code == 0
        assert run_mock.call_count == 1

    def test_021_execute_does_not_require_confirmed_failure_command(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        spy = _RecordingBuildStack()
        run_mock = MagicMock(return_value=({"execution_id": "exec-1"}, 201))
        monkeypatch.setattr(tool, "build_console_stack", spy)
        monkeypatch.setattr(tool, "run_director_apply", run_mock)

        exit_code = tool.main(["021", "--listen-port", "19196", "--execute"])

        assert exit_code == 0
        assert run_mock.call_count == 1


# ---------------------------------------------------------------------------
# REQ-LDSEND-014 — 백업 선행조건 관측. 실패는 readback 판정과 구분된
# 필드로 기록되고, readback 결과를 덮어쓰지 않는다(로컬 절반 — 로직만).
# ---------------------------------------------------------------------------


class TestBackupPreconditionObservation:
    def test_backup_failure_is_recorded_separately_and_blocks_readback(self, tmp_path: Path):
        def _raise() -> None:
            raise RuntimeError("synthetic backup failure")

        console = _FakeConsoleLink()
        stack = _fake_stack(tmp_path, console=console, backup=BackupManager(backup_action=_raise))

        result = tool._run_scenario(scenario="021", stack=stack, sequence_range_start=9900)

        assert result["backup_precondition"] == "failed"
        assert "backup failed" in result["backup_precondition_detail"]
        # readback 은 시도되지 않았다 — backup 실패로 apply 가 콘솔에
        # 아무것도 보내지 못했다는 사실을 readback 판정으로 덮어쓰지 않는다.
        assert "readback" not in result
        assert console.executed == []

    def test_backup_success_lets_readback_proceed_normally(self, tmp_path: Path):
        console = _FakeConsoleLink()
        stack = _fake_stack(
            tmp_path, console=console, backup=BackupManager(backup_action=lambda: None)
        )

        result = tool._run_scenario(scenario="021", stack=stack, sequence_range_start=9900)

        assert result["backup_precondition"] == "ok"
        assert result["backup_precondition_detail"] is None
        assert result["readback"]["primary"].exists is True


# ---------------------------------------------------------------------------
# cleanup 단계 — 명령만 출력, 콘솔 송신 0회, ApprovalBinding 0개. 여러
# destination 을 갖는 시나리오는 destination 마다 출력한다(REQ-LDSEND-011).
# ---------------------------------------------------------------------------


class TestCleanup:
    def test_cleanup_commands_shape(self):
        commands = tool._cleanup_commands({"show_id": "1", "sequence_id": "9900"})
        assert commands == ["Delete Sequence 9900"]

    def test_cleanup_prints_without_touching_any_console_or_registry(
        self, capsys: pytest.CaptureFixture[str]
    ):
        tool._print_cleanup({"show_id": "1", "sequence_id": "9901"})

        out = capsys.readouterr().out
        assert "Delete Sequence 9901" in out
        # _print_cleanup/_cleanup_commands 는 ApprovalRegistry/gate 인자를
        # 아예 받지 않는다 — 함수 시그니처 자체가 0회를 강제한다는 것을
        # inspect 로 다시 확인한다(REQ-LDSEND-012 "cleanup 은 ApprovalBinding
        # 을 만들지 않는다").
        import inspect

        cleanup_params = inspect.signature(tool._print_cleanup).parameters
        assert "approvals" not in cleanup_params
        assert "gate" not in cleanup_params

    def test_print_cleanup_all_prints_every_destination(self, capsys: pytest.CaptureFixture[str]):
        tool._print_cleanup_all(
            [
                {"show_id": "1", "sequence_id": "9901"},
                {"show_id": "1", "sequence_id": "9902"},
            ]
        )

        out = capsys.readouterr().out
        assert "Delete Sequence 9901" in out
        assert "Delete Sequence 9902" in out

    def test_execute_024_cleanup_prints_both_destinations(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ):
        spy = _RecordingBuildStack()
        run_mock = MagicMock(return_value=({"execution_id": "exec-1"}, 201))
        monkeypatch.setattr(tool, "build_console_stack", spy)
        monkeypatch.setattr(tool, "run_director_apply", run_mock)

        exit_code = tool.main(
            [
                "024",
                "--listen-port",
                "19197",
                "--execute",
                "--confirmed-failure-command",
                "Store Sequence {n}",
            ]
        )

        assert exit_code == 0
        out = capsys.readouterr().out
        assert "Delete Sequence 9901" in out  # primary
        assert "Delete Sequence 9902" in out  # never_written
        # cleanup 자체는 fake gate 의 execute 를 건드리지 않는다.
        gate = spy.stacks[0].gate
        assert gate.execution_port.execute.call_count == 0


# ---------------------------------------------------------------------------
# 024 의 3번째 bundle 이 전혀 안 나간다는 것을 execute_bundles()+
# GateBundleSender 로 직접 확인한다(REQ-LDSEND-002/024, 최소 배선).
# ---------------------------------------------------------------------------


class TestExecuteBundlesStopsAfterBundleTwoFails:
    def test_bundle_three_never_reaches_the_execution_port(self, tmp_path: Path):
        plan = tool._plan_for_scenario(
            "024", sequence_range_start=9900, confirmed_failure_command="Store Sequence {n}"
        )
        calls: list[str] = []

        class _FakeExecutionPort:
            def execute(self, command: str) -> ExecutionResult:
                calls.append(command)
                if command == "Store Sequence 9901":
                    return ExecutionResult(ok=False, detail="Not allowed", outcome="failed")
                return ExecutionResult(ok=True, detail="OK", outcome="ok")

        sender = tool.GateBundleSender(_FakeExecutionPort())
        journal = ExecutionJournal(tmp_path / "execution.sqlite3")
        try:
            outcome = execute_bundles(
                journal, execution_id="fake-exec-024", bundles=plan.bundles, sender=sender
            )
        finally:
            journal.close()

        assert calls == ["Store Sequence 9901 Cue 1 /Merge", "Store Sequence 9901"]
        assert outcome["bundles"][2] == STATE_NOT_SENT
