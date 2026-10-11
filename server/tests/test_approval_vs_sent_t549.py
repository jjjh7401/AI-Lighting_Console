"""SPEC-LDBEAT-001 M4 — 승인=송신 비교 로직의 앱 경로 승격 (카드 t549,
REQ-LDBEAT-011).

`.moai/reports/t512/approval_vs_sent.py`(리포트 스크립트, 앱 코드 아님)의
로직을 바이트 동일하게 `server/design/approval_vs_sent.py`로 옮긴다 — 새
비교 로직을 발명하지 않는다(REQ-LDBEAT-011(b)).

이 시험은 t512의 네 가지 음성 대조(승인에만 있음 주입·감사에서 송신 행
제거·감사에 승인 없는 행 추가·순서만 바뀜)를 합성 최소 fixture로 재현해
FAIL하는지, 그리고 일치하는 승인+감사가 PASS하는지를 잰다(t512 원본의
실제 콘솔 로그를 그대로 복사하지 않는다 — 이 fixture는 t512 통제의 **모양**
만 재현한 합성 데이터다).
"""

from __future__ import annotations

import json

import pytest

from server.design.approval_vs_sent import (
    READ_KINDS,
    SUMMARY_KINDS,
    canonical_approval,
    compare,
    sha,
    verify_approval_vs_sent,
)

_BASE_COMMANDS = (
    "Store Sequence 1",
    "Store Cue 1 Sequence 1",
    "Off Sequence 1",
)


def _audit_line(command: str, *, ts: str = "2026-10-11T00:00:00Z", kind: str = "command") -> str:
    return json.dumps(
        {"ts": ts, "event": "executed", "command": command, "kind": kind, "ok": True},
        ensure_ascii=False,
    )


def _write_audit(tmp_path, name: str, lines: list[str]):
    folder = tmp_path / name
    folder.mkdir()
    path = folder / "audit-20261011.jsonl"
    path.write_text("".join(f"{line}\n" for line in lines), "utf-8")
    return folder


def _approval_text(lines: tuple[str, ...]) -> str:
    return "".join(f"{line}\n" for line in lines)


class TestCanonicalApproval:
    def test_strips_blank_lines_and_comments(self) -> None:
        raw = "# header\nStore Sequence 1\n\n# mid\nOff Sequence 1\n"
        assert canonical_approval(raw) == ["Store Sequence 1", "Off Sequence 1"]


class TestCompare:
    def test_identical_lines_produce_no_diff(self) -> None:
        sent_only, approved_only = compare(list(_BASE_COMMANDS), list(_BASE_COMMANDS))
        assert sent_only == []
        assert approved_only == []


class TestVerifyApprovalVsSentMatchingPass:
    def test_matching_approval_and_audit_passes(self, tmp_path) -> None:
        approval_path = tmp_path / "approval.txt"
        approval_path.write_text(_approval_text(_BASE_COMMANDS), "utf-8")
        audit_dir = _write_audit(tmp_path, "matching", [_audit_line(cmd) for cmd in _BASE_COMMANDS])
        result = verify_approval_vs_sent(approval_path, audit_dir)
        assert result.passed is True
        assert result.sha_equal is True
        assert result.sent_not_approved == []
        assert result.approved_not_sent == []


class TestVerifyApprovalVsSentNegativeControls:
    """t512 control c1~c4 의 모양을 재현한 합성 fixture — 넷 다 FAIL해야 한다."""

    def test_c1_approval_has_extra_line_not_sent(self, tmp_path) -> None:
        # c1_approval_injected — 승인 파일에 송신되지 않은 줄을 끼운다.
        injected = (*_BASE_COMMANDS[:1], "Delete Sequence 14", *_BASE_COMMANDS[1:])
        approval_path = tmp_path / "approval_c1.txt"
        approval_path.write_text(_approval_text(injected), "utf-8")
        audit_dir = _write_audit(tmp_path, "c1", [_audit_line(cmd) for cmd in _BASE_COMMANDS])
        result = verify_approval_vs_sent(approval_path, audit_dir)
        assert result.passed is False
        assert "Delete Sequence 14" in result.approved_not_sent
        assert result.sent_not_approved == []

    def test_c2_audit_line_removed(self, tmp_path) -> None:
        # c2_audit_line_removed — 감사 로그에서 승인된 줄 하나를 뺀다.
        approval_path = tmp_path / "approval_c2.txt"
        approval_path.write_text(_approval_text(_BASE_COMMANDS), "utf-8")
        remaining = [cmd for cmd in _BASE_COMMANDS if cmd != "Off Sequence 1"]
        audit_dir = _write_audit(tmp_path, "c2", [_audit_line(cmd) for cmd in remaining])
        result = verify_approval_vs_sent(approval_path, audit_dir)
        assert result.passed is False
        assert "Off Sequence 1" in result.approved_not_sent
        assert result.sent_not_approved == []

    def test_c3_audit_line_added(self, tmp_path) -> None:
        # c3_audit_line_added — 감사 로그에 승인 없는 송신 행(backup)을 끼운다.
        approval_path = tmp_path / "approval_c3.txt"
        approval_path.write_text(_approval_text(_BASE_COMMANDS), "utf-8")
        lines = [_audit_line(cmd) for cmd in _BASE_COMMANDS]
        lines.insert(1, _audit_line("SaveShow", kind="backup"))
        audit_dir = _write_audit(tmp_path, "c3", lines)
        result = verify_approval_vs_sent(approval_path, audit_dir)
        assert result.passed is False
        assert "SaveShow" in result.sent_not_approved
        assert result.approved_not_sent == []

    def test_c4_audit_lines_swapped(self, tmp_path) -> None:
        # c4_audit_swapped — 송신 두 줄의 순서만 바뀐다(집합은 같음).
        approval_path = tmp_path / "approval_c4.txt"
        approval_path.write_text(_approval_text(_BASE_COMMANDS), "utf-8")
        swapped = (_BASE_COMMANDS[1], _BASE_COMMANDS[0], _BASE_COMMANDS[2])
        audit_dir = _write_audit(tmp_path, "c4", [_audit_line(cmd) for cmd in swapped])
        result = verify_approval_vs_sent(approval_path, audit_dir)
        assert result.passed is False


class TestReadKindsExcluded:
    def test_read_only_and_summary_rows_are_not_counted_as_sends(self, tmp_path) -> None:
        approval_path = tmp_path / "approval_reads.txt"
        approval_path.write_text(_approval_text(_BASE_COMMANDS), "utf-8")
        lines = [_audit_line(cmd) for cmd in _BASE_COMMANDS]
        for kind in sorted(READ_KINDS):
            lines.append(_audit_line("props /some/path", kind=kind))
        for kind in sorted(SUMMARY_KINDS):
            lines.append(_audit_line("deploy summary", kind=kind))
        audit_dir = _write_audit(tmp_path, "reads", lines)
        result = verify_approval_vs_sent(approval_path, audit_dir)
        assert result.passed is True


class TestShaHelper:
    def test_sha_is_sha256_hexdigest(self) -> None:
        # sha256("abc") is a well-known test vector.
        assert sha("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


class TestAppCodeNeverImportsReportsDirectory:
    def test_module_has_zero_python_import_statements_from_moai_reports(self) -> None:
        # 모듈의 실제 import 문만 조사한다(독스트링의 출처 인용 ".moai/reports/..."
        # 는 그 파일의 "앱 코드 자격 없음"을 밝히는 문서 citation일 뿐, 금지
        # 대상인 "그 디렉터리를 import" 하는 것과는 다르다 — REQ-LDBEAT-011(c)).
        import ast
        import inspect

        from server.design import approval_vs_sent as module

        tree = ast.parse(inspect.getsource(module))
        imported_modules = [
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        ] + [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        assert not any("moai" in name.lower() for name in imported_modules)
        assert not any("reports" in name.lower() for name in imported_modules)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
