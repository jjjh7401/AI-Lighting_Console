"""SPEC-LDSEND-001 M3 · REQ-LDSEND-007/009/012 · AC-LDSEND-007/009/012(부분).

``server/tools/director_apply_observe.py`` 는 관측 도구의 **골격**이다 —
인자 파싱, dry-run 기본값, 로컬 plan/승인 구성 헬퍼, cleanup 출력,
``run_director_apply()`` 배선까지만 이 파일이 잰다. 시나리오 본문(021/024/
032 의 실제 명령 내용, destination 점유 확인, readback 재확인, 백업
선행조건 관측)은 M4 의 몫이다(plan.md §4 M3~M4) — 이 파일은 그 시나리오
함수가 ``run_director_apply()`` 를 실제로 한 번 타게 하는 최소 배선만
잰다.

이 파일이 확인하는 것:

- ``build_console_stack()`` 이 dry-run 에서 ``attempt_session_backup=False``
  로 불린다(D11) — mock 호출 인자로 확인.
- dry-run 은 어떤 인자 조합으로도 콘솔(fake gate)에 아무것도 보내지
  않는다 — 세션 시작 백업 포함.
- 도구가 ``server.director.director_api``·``server.bridge`` 를 import 하지
  않는다(정적 검사).
- 도구가 ``run_director_apply`` 를 호출한다는 정적 표지, 그리고 ``--execute``
  경로에서 시나리오 개수(=1, run = CLI 1회 호출 = 시나리오 1개)만큼
  ``run_director_apply()`` 가 호출된다(mock 카운트).
- 로컬 ``DirectorStore``/``ApprovalRegistry`` 로 만든 ``ApprovalBinding`` 의
  ``principal_id`` 가 ``ldsend-observe-harness`` 이고, 이 도구가
  ``server/web/serve.py`` 에 배선되지 않았다.
- cleanup 은 ``Delete Sequence <N>`` 문자열만 표준출력에 내고, 콘솔로는
  아무것도 보내지 않으며, 어떤 ``ApprovalBinding`` 도 만들지 않는다.
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
from server.director.store import DirectorStore
from server.safety.audit import AuditLog
from server.safety.console import ExecOutcome
from server.safety.gate import SafetyGate

_MODULE_SOURCE = Path(tool.__file__).read_text(encoding="utf-8")
_SERVE_PY = Path(__file__).resolve().parents[1] / "web" / "serve.py"


# ---------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------


class _FakeConsoleLink:
    """``SafetyGate`` 를 실제로 통과시키는 최소 콘솔 대역 — ``server.bridge``
    없음. ``server/tests/test_run_director_apply.py`` 의 ``_AlwaysOkConsole``
    과 같은 패턴이다."""

    def __init__(self) -> None:
        self.executed: list[str] = []

    def execute(self, command: str) -> ExecOutcome:
        self.executed.append(command)
        return ExecOutcome(status="ok", detail="OK")

    def ping(self) -> bool:
        return True

    def query_state(self, path: str) -> dict[str, Any]:  # pragma: no cover - 이 시험은 안 씀
        raise RuntimeError(f"no such path: {path}")


def _fake_stack(tmp_path: Path) -> SimpleNamespace:
    """``ConsoleStack`` 대역 — 진짜 ``SafetyGate`` 를 fake 콘솔에 묶는다."""
    console = _FakeConsoleLink()
    gate = SafetyGate(console=console, audit=AuditLog(tmp_path / "audit"))
    calls = {"stop": 0}

    def _stop() -> None:
        calls["stop"] += 1

    return SimpleNamespace(gate=gate, stop=_stop, console=console, _calls=calls)


class _RecordingBuildStack:
    """``build_console_stack`` 대역 — 호출 인자를 기록하고 mock 스택을
    반환한다. 스택의 ``gate`` 는 ``MagicMock`` 이라 호출 카운트를 그대로
    관측할 수 있다."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.stacks: list[SimpleNamespace] = []

    def __call__(self, **kwargs: Any) -> SimpleNamespace:
        self.calls.append(kwargs)
        gate = MagicMock(name="fake-gate")
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
        # 자리표시자 bundle 의 명령 하나가 fake 콘솔까지 실제로 도달했다 —
        # run_director_apply() -> execute_bundles() -> GateBundleSender ->
        # 진짜 SafetyGate.execution_port -> fake 콘솔 링크, 전체 경로가 탄다.
        assert stack.console.executed == ["Fixture 901 At 50"]


# ---------------------------------------------------------------------------
# cleanup 단계 — 명령만 출력, 콘솔 송신 0회, ApprovalBinding 0개.
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
