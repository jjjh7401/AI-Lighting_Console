"""t512 — AC-LDRHYTHM-012 측정기: 승인 파일 대 실제 송신 기록 비교.

무엇을 재나 (acceptance.md AC-LDRHYTHM-012 Then 세 조건):
  (1) 승인 파일 sha256 == 송신 기록에서 재구성한 파일 sha256
  (2) 「송신 안 됨」 0건 — 승인 파일에 없는데 송신 기록에 있는 줄
  (3) 「승인 안 됨」 0건 — 승인 파일에 있는데 송신 기록에 없는 줄
  세 조건이 모두 성립할 때만 PASS(종료 코드 0), 하나라도 어긋나면 FAIL(종료 코드 1).

송신 기록 원천 (t512 판정서 §1 에서 실측으로 정함):
  앱 안전 게이트의 감사 로그 `audit-YYYYMMDD.jsonl`. 게이트는 콘솔에 한 줄 보낼 때마다
  보낸 직후 `{"event": "executed", "kind": "command", "command": ...}` 한 행을 남긴다
  (server/safety/gate.py `_execute_cleared` → server/safety/audit.py `log_executed`, 1:1).
  - 송신으로 세는 행: event == "executed" 이고 kind 가 아래 READ_KINDS 도,
    "deploy"(요약 행)도 아닌 것. command 뿐 아니라 backup(SaveShow)·deploy 하위 송신도
    송신이다 — 승인 파일에 없으면 「송신 안 됨」으로 잡힌다. 모르는 kind 는 송신으로 센다.
  - 읽기 전용 질의(READ_KINDS)는 콘솔 상태를 바꾸지 않으므로 뺀다. probe-*.jsonl 은 안 읽는다.
  - 송신 결과가 ok 가 아닌 행(실패·미확인)은 줄 비교에 그대로 넣고, 따로 WARN 으로 센다
    (판정에는 안 넣는다).

승인 파일 정규형:
  빈 줄과 `#` 로 시작하는 줄(묶음 머리 주석)을 뺀 명령 줄만, 줄 끝 "\n".
  sha256 은 이 정규형끼리 비교하고, 원본 sha256 과 「원본 == 정규형」 여부도 함께 찍는다
  (M2 승인 파일은 주석 없는 맨 줄 권장 — 그러면 둘이 같다).

실행:
  uv run python .moai/reports/t512/approval_vs_sent.py <승인 파일> <감사 로그 폴더|audit-*.jsonl>
      [--out <재구성 파일>] [--since <ISO 시각>] [--until <ISO 시각>]
  --since/--until: 하루치 감사 로그에 여러 실행이 섞여 있을 때 창을 자른다(ts 문자열 비교, UTC).
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

READ_KINDS = frozenset(
    {"props_query", "state_query", "property_query", "introspect_query", "heartbeat"}
)
SUMMARY_KINDS = frozenset({"deploy"})


def canonical_approval(raw: str) -> list[str]:
    return [line for line in raw.splitlines() if line.strip() and not line.lstrip().startswith("#")]


def audit_files(source: Path) -> list[Path]:
    if source.is_dir():
        return sorted(source.glob("audit-*.jsonl"))
    return [source]


def sent_rows(source: Path, since: str | None, until: str | None) -> list[dict]:
    rows = []
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


def as_file(lines: list[str]) -> str:
    return "".join(f"{line}\n" for line in lines)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compare(approved: list[str], sent: list[str]) -> tuple[list[str], list[str]]:
    """(송신 안 됨 = 송신에만 있음, 승인 안 됨 = 승인에만 있음) — 순서를 맞춘 뒤 남는 줄."""
    matcher = difflib.SequenceMatcher(a=approved, b=sent, autojunk=False)
    approved_only, sent_only = [], []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        approved_only += approved[i1:i2]
        sent_only += sent[j1:j2]
    return sent_only, approved_only


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("approval", type=Path)
    parser.add_argument("sent_source", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--since")
    parser.add_argument("--until")
    args = parser.parse_args(argv)

    raw = args.approval.read_text("utf-8")
    approved = canonical_approval(raw)
    rows = sent_rows(args.sent_source, args.since, args.until)
    sent = [row.get("command", "") for row in rows]

    approved_text, sent_text = as_file(approved), as_file(sent)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(sent_text, "utf-8")

    print(f"approval file      : {args.approval}")
    print(f"  raw sha256       : {sha(raw)}")
    print(f"  raw == canonical : {raw == approved_text}")
    print(f"  canonical lines  : {len(approved)}")
    print(f"  canonical sha256 : {sha(approved_text)}")
    names = [p.name for p in audit_files(args.sent_source)]
    print(f"sent source        : {args.sent_source} (files: {names})")
    print(f"  window           : since={args.since} until={args.until}")
    print(f"  send rows        : {len(sent)} by kind {dict(Counter(r.get('kind') for r in rows))}")
    print(f"  rebuilt sha256   : {sha(sent_text)}" + (f" -> {args.out}" if args.out else ""))

    not_ok = [r for r in rows if not r.get("ok", False) or r.get("outcome") not in (None, "ok")]
    print(f"WARN sends not ok  : {len(not_ok)}")
    for row in not_ok:
        print(f"  not-ok [{row.get('outcome')}] {row.get('command', '')[:200]}")

    sha_equal = sha(approved_text) == sha(sent_text)
    sent_not_approved, approved_not_sent = compare(approved, sent)
    print(f"(1) sha256 equal                         : {sha_equal}")
    print(f"(2) 송신 안 됨 (sent, not in approval)    : {len(sent_not_approved)}")
    for line in sent_not_approved:
        print(f"  SENT_NOT_APPROVED: {line[:200]}")
    print(f"(3) 승인 안 됨 (approved, not sent)       : {len(approved_not_sent)}")
    for line in approved_not_sent:
        print(f"  APPROVED_NOT_SENT: {line[:200]}")

    passed = sha_equal and not sent_not_approved and not approved_not_sent
    print(f"VERDICT AC-LDRHYTHM-012: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
