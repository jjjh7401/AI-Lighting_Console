from __future__ import annotations

import argparse
import json

import pytest

from server.safety.console import StateQueryError
from server.tools import introspect_probe


class FakeStatePort:
    def __init__(self, error: StateQueryError | None = None):
        self.error = error
        self.calls: list[tuple[str, str, tuple[str, ...] | None]] = []

    def enumerate_fields(self, path: str) -> dict[str, object]:
        self.calls.append(("introspect", path, None))
        if self.error:
            raise self.error
        return {"kind": "introspect", "ok": True, "path": path, "fields": []}

    def query_properties(self, path: str, names: tuple[str, ...]) -> dict[str, object]:
        self.calls.append(("props", path, names))
        if self.error:
            raise self.error
        return {"kind": "props", "ok": True, "path": path, "reads": [{"n": names[0]}]}


class FakeGate:
    def __init__(self, state_port: FakeStatePort):
        self.state_port = state_port


class FakeStack:
    def __init__(self, state_port: FakeStatePort, kwargs: dict[str, object]):
        self.gate = FakeGate(state_port)
        self.kwargs = kwargs
        self.stopped = False

    def stop(self) -> None:
        self.stopped = True


def _install_stack(monkeypatch: pytest.MonkeyPatch, state_port: FakeStatePort) -> list[FakeStack]:
    stacks: list[FakeStack] = []

    def fake_build_console_stack(**kwargs: object) -> FakeStack:
        stack = FakeStack(state_port, kwargs)
        stacks.append(stack)
        return stack

    monkeypatch.setattr(introspect_probe, "build_console_stack", fake_build_console_stack)
    return stacks


def test_names_arg_strips_csv_and_rejects_empty_values():
    assert introspect_probe._names_arg(" CURRENTCUE, NAME ,,") == ("CURRENTCUE", "NAME")
    with pytest.raises(argparse.ArgumentTypeError, match="at least one property name"):
        introspect_probe._names_arg(" , ")


def test_main_without_names_sends_introspect_and_prints_payload(monkeypatch, capsys, tmp_path):
    state_port = FakeStatePort()
    stacks = _install_stack(monkeypatch, state_port)
    code = introspect_probe.main(
        [
            "--path",
            "DataPool/Sequences/Sequence 101",
            # t61 — `--listen-port` 는 필수다. 예전엔 이 호출이 침묵의 9000 을
            # 받았고, 그래서 **이 도구가 어느 포트로 쏘는지 아무 검사도 안
            # 재고 있었다**(현장은 9005 다). 명시가 그 구멍을 닫는다.
            "--listen-port",
            "9005",
            "--timeout-seconds",
            "1.25",
            "--audit-dir",
            str(tmp_path),
        ]
    )
    output = json.loads(capsys.readouterr().out)
    assert code == 0
    assert output == {
        "mode": "introspect",
        "payload": {
            "kind": "introspect",
            "ok": True,
            "path": "DataPool/Sequences/Sequence 101",
            "fields": [],
        },
    }
    assert state_port.calls == [("introspect", "DataPool/Sequences/Sequence 101", None)]
    assert stacks[0].stopped is True
    assert stacks[0].kwargs["audit_dir"] == tmp_path
    assert stacks[0].kwargs["attempt_session_backup"] is False
    assert stacks[0].kwargs["timeouts"].state_query_seconds == 1.25


def test_main_with_names_sends_props_and_prints_payload(monkeypatch, capsys):
    state_port = FakeStatePort()
    _install_stack(monkeypatch, state_port)
    code = introspect_probe.main(
        [
            "--path",
            "DataPool/Sequences/Sequence 101",
            "--listen-port",
            "9005",
            "--names",
            " CURRENTCUE, NAME ",
        ]
    )
    output = json.loads(capsys.readouterr().out)
    assert code == 0
    assert output["mode"] == "props"
    assert output["payload"]["kind"] == "props"
    assert state_port.calls == [
        ("props", "DataPool/Sequences/Sequence 101", ("CURRENTCUE", "NAME"))
    ]


def test_main_rejects_empty_names_without_building_stack(monkeypatch, capsys):
    state_port = FakeStatePort()
    stacks = _install_stack(monkeypatch, state_port)
    with pytest.raises(SystemExit) as exc:
        introspect_probe.main(["--path", "DataPool/Sequences/Sequence 101", "--names", " , "])
    assert exc.value.code == 2
    assert stacks == []
    assert "--names must include at least one property name" in capsys.readouterr().err


def test_main_returns_one_and_stops_stack_on_query_error(monkeypatch, capsys):
    state_port = FakeStatePort(StateQueryError("no reply"))
    stacks = _install_stack(monkeypatch, state_port)
    code = introspect_probe.main(
        [
            "--path",
            "DataPool/Sequences/Sequence 101",
            "--listen-port",
            "9005",
            "--names",
            "CURRENTCUE",
        ]
    )
    captured = capsys.readouterr()
    assert code == 1
    assert captured.out == ""
    assert "props failed: no reply" in captured.err
    assert stacks[0].stopped is True


def test_the_listen_port_actually_reaches_the_stack(monkeypatch, capsys, tmp_path):
    """t61 — **넘긴 포트가 실제로 쓰이는지** 잰다.

    이 카드 전까지 이 도구의 세 검사는 `--listen-port` 를 아예 안 넘겼고 침묵의
    9000 이 채워 줬다. 즉 **어떤 검사도 이 도구가 어느 포트로 쏘는지 재고 있지
    않았다** — 값이 틀렸던 것이 아니라 값이 관측되지 않고 있었다. 인자를
    넘기기만 하고 단언하지 않으면 그 상태 그대로다.
    """
    state_port = FakeStatePort()
    stacks = _install_stack(monkeypatch, state_port)
    code = introspect_probe.main(
        [
            "--path",
            "DataPool/Sequences/Sequence 101",
            "--listen-port",
            "9005",
            "--audit-dir",
            str(tmp_path),
        ]
    )
    capsys.readouterr()
    assert code == 0
    assert stacks[0].kwargs["receive_port"] == 9005


def test_a_different_listen_port_reaches_the_stack_too(monkeypatch, capsys, tmp_path):
    """비공허 — 위 단언이 9005 를 어딘가에 박아 둔 것과 구분되지 않으면 안 된다.

    다른 값을 넘겨 다른 값이 도착하는 것까지 봐야 「전달된다」를 잰 것이다.
    """
    state_port = FakeStatePort()
    stacks = _install_stack(monkeypatch, state_port)
    code = introspect_probe.main(
        [
            "--path",
            "DataPool/Sequences/Sequence 101",
            "--listen-port",
            "9123",
            "--audit-dir",
            str(tmp_path),
        ]
    )
    capsys.readouterr()
    assert code == 0
    assert stacks[0].kwargs["receive_port"] == 9123
