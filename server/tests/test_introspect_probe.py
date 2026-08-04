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
        ["--path", "DataPool/Sequences/Sequence 101", "--names", " CURRENTCUE, NAME "]
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
        ["--path", "DataPool/Sequences/Sequence 101", "--names", "CURRENTCUE"]
    )
    captured = capsys.readouterr()
    assert code == 1
    assert captured.out == ""
    assert "props failed: no reply" in captured.err
    assert stacks[0].stopped is True
