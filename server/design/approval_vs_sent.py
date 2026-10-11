"""승인=송신 비교 로직 — 앱 경로 승격 (SPEC-LDBEAT-001 M4, 카드 t549,
REQ-LDBEAT-011).

이 모듈은 `.moai/reports/t512/approval_vs_sent.py`(AC-LDRHYTHM-012가 쓰는
리포트 스크립트, t516/t519/t520이 반복 검증한 로직 — 그러나 그 파일 자체는
`.moai/reports/` 아래의 gitignore 대상 로컬 아티팩트라 앱 코드가 아니다)의
로직을 **바이트 동일**하게 옮긴 것이다. 새 비교 로직을 발명하지 않는다
(REQ-LDBEAT-011(b)) — 콘솔에 아무것도 쓰지 않는다(파일 두 개만 읽는다).

무엇을 재나 (AC-LDRHYTHM-012 / REQ-LDBEAT-011(a) Then 세 조건):

  (1) 승인 파일 sha256 == 송신 기록에서 재구성한 파일 sha256
  (2) 「송신 안 됨」 0건 — 승인 파일에 없는데 송신 기록에 있는 줄
  (3) 「승인 안 됨」 0건 — 승인 파일에 있는데 송신 기록에 없는 줄

  세 조건이 모두 성립할 때만 PASS, 하나라도 어긋나면 FAIL.

송신 기록 원천: 앱 안전 게이트의 감사 로그 `audit-YYYYMMDD.jsonl`
(`server/safety/gate.py` → `server/safety/audit.py` `log_executed`, 1:1).
읽기 전용 질의(``READ_KINDS``)와 요약 행(``SUMMARY_KINDS``)은 콘솔 상태를
바꾸지 않으므로 송신으로 세지 않는다.
"""

from __future__ import annotations

import difflib
import hashlib
import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "READ_KINDS",
    "SUMMARY_KINDS",
    "ApprovalVsSentResult",
    "audit_files",
    "canonical_approval",
    "compare",
    "sent_rows",
    "sha",
    "verify_approval_vs_sent",
]

READ_KINDS = frozenset(
    {"props_query", "state_query", "property_query", "introspect_query", "heartbeat"}
)
SUMMARY_KINDS = frozenset({"deploy"})


def canonical_approval(raw: str) -> list[str]:
    """빈 줄과 ``#`` 로 시작하는 줄(묶음 머리 주석)을 뺀 명령 줄만 돌려준다."""
    return [line for line in raw.splitlines() if line.strip() and not line.lstrip().startswith("#")]


def audit_files(source: Path) -> list[Path]:
    if source.is_dir():
        return sorted(source.glob("audit-*.jsonl"))
    return [source]


def sent_rows(source: Path, since: str | None = None, until: str | None = None) -> list[dict]:
    rows: list[dict] = []
    for path in audit_files(source):
        for line in path.read_text("utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("event") != "executed":
                continue
            kind = event.get("kind")
            if kind in READ_KINDS or kind in SUMMARY_KINDS:
                continue
            ts = event.get("ts", "")
            if since and ts < since:
                continue
            if until and ts > until:
                continue
            rows.append(event)
    return rows


def as_file(lines: Sequence[str]) -> str:
    return "".join(f"{line}\n" for line in lines)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compare(approved: list[str], sent: list[str]) -> tuple[list[str], list[str]]:
    """(송신 안 됨 = 송신에만 있음, 승인 안 됨 = 승인에만 있음) — 순서를
    맞춘 뒤 남는 줄(difflib.SequenceMatcher, 순서 변경도 불일치로 잡는다)."""
    matcher = difflib.SequenceMatcher(a=approved, b=sent, autojunk=False)
    approved_only: list[str] = []
    sent_only: list[str] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        approved_only += approved[i1:i2]
        sent_only += sent[j1:j2]
    return sent_only, approved_only


@dataclass(frozen=True)
class ApprovalVsSentResult:
    """REQ-LDBEAT-011(a) 세 조건의 구조화 판정. ``passed``가 전체 PASS/FAIL이다."""

    approval_raw_sha256: str
    approval_canonical_sha256: str
    approval_raw_equals_canonical: bool
    sent_sha256: str
    sha_equal: bool
    sent_not_approved: list[str]
    approved_not_sent: list[str]
    not_ok_sends: list[dict]
    send_count: int

    @property
    def passed(self) -> bool:
        return self.sha_equal and not self.sent_not_approved and not self.approved_not_sent


def verify_approval_vs_sent(
    approval_path: Path,
    sent_source: Path,
    *,
    since: str | None = None,
    until: str | None = None,
) -> ApprovalVsSentResult:
    """승인 파일과 감사 로그 소스를 읽어 AC-LDRHYTHM-012 / REQ-LDBEAT-011(a)
    판정을 돌려준다. 콘솔 접촉 0건 — 파일 두 개만 읽는다."""
    raw = approval_path.read_text("utf-8")
    approved = canonical_approval(raw)
    rows = sent_rows(sent_source, since, until)
    sent = [row.get("command", "") for row in rows]

    approved_text = as_file(approved)
    sent_text = as_file(sent)

    sent_not_approved, approved_not_sent = compare(approved, sent)
    not_ok = [r for r in rows if not r.get("ok", False) or r.get("outcome") not in (None, "ok")]

    return ApprovalVsSentResult(
        approval_raw_sha256=sha(raw),
        approval_canonical_sha256=sha(approved_text),
        approval_raw_equals_canonical=(raw == approved_text),
        sent_sha256=sha(sent_text),
        sha_equal=(sha(approved_text) == sha(sent_text)),
        sent_not_approved=sent_not_approved,
        approved_not_sent=approved_not_sent,
        not_ok_sends=not_ok,
        send_count=len(sent),
    )


def main(argv: list[str]) -> int:
    """CLI 진입점 — `.moai/reports/t512/approval_vs_sent.py`와 같은 출력
    형식·종료 코드 의미를 유지한다(이식 동등성, REQ-LDBEAT-011(b))."""
    import argparse
    from collections import Counter

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else "")
    parser.add_argument("approval", type=Path)
    parser.add_argument("sent_source", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--since")
    parser.add_argument("--until")
    args = parser.parse_args(argv)

    result = verify_approval_vs_sent(
        args.approval, args.sent_source, since=args.since, until=args.until
    )

    if args.out:
        rows = sent_rows(args.sent_source, args.since, args.until)
        sent_text = as_file([row.get("command", "") for row in rows])
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(sent_text, "utf-8")

    print(f"approval file      : {args.approval}")
    print(f"  raw sha256       : {result.approval_raw_sha256}")
    print(f"  raw == canonical : {result.approval_raw_equals_canonical}")
    print(f"  canonical sha256 : {result.approval_canonical_sha256}")
    names = [p.name for p in audit_files(args.sent_source)]
    print(f"sent source        : {args.sent_source} (files: {names})")
    print(f"  window           : since={args.since} until={args.until}")
    rows = sent_rows(args.sent_source, args.since, args.until)
    by_kind = dict(Counter(r.get("kind") for r in rows))
    print(f"  send rows        : {result.send_count} by kind {by_kind}")
    print(f"  rebuilt sha256   : {result.sent_sha256}" + (f" -> {args.out}" if args.out else ""))

    print(f"WARN sends not ok  : {len(result.not_ok_sends)}")
    for row in result.not_ok_sends:
        print(f"  not-ok [{row.get('outcome')}] {row.get('command', '')[:200]}")

    print(f"(1) sha256 equal                         : {result.sha_equal}")
    print(f"(2) 송신 안 됨 (sent, not in approval)    : {len(result.sent_not_approved)}")
    for line in result.sent_not_approved:
        print(f"  SENT_NOT_APPROVED: {line[:200]}")
    print(f"(3) 승인 안 됨 (approved, not sent)       : {len(result.approved_not_sent)}")
    for line in result.approved_not_sent:
        print(f"  APPROVED_NOT_SENT: {line[:200]}")

    print(f"VERDICT AC-LDRHYTHM-012: {'PASS' if result.passed else 'FAIL'}")
    return 0 if result.passed else 1


if __name__ == "__main__":  # pragma: no cover
    import sys

    sys.exit(main(sys.argv[1:]))
