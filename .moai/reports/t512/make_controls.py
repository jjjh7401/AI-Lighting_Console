"""t512 ④ — 양성 대조 입력을 만든다(원본은 건드리지 않고 사본만 controls/ 에).

  c1_approval_injected.txt : t506 v3 승인 파일 「묶음 4」 앞에 `Delete Sequence 14` 를 끼운 사본
                             (카드 ④-1 · AC 측정 문면, t498 control_classify_injected_line 방식)
  c2_audit_line_removed/   : t506 v3 감사 로그에서 송신 행 하나(Go Timecode 14)를 뺀 사본 (카드 ④-2)
  c3_audit_line_added/     : 감사 로그에 승인에 없는 송신 행(SaveShow, kind=backup)을 끼운 사본
                             — 반대 방향(「송신 안 됨」)도 걸리는지 보는 추가 대조
  c4_audit_swapped/        : 송신 행 두 줄(Store Property Time 1·2)의 순서만 바꾼 사본
                             — 집합은 같고 순서만 다를 때

실행: uv run python .moai/reports/t512/make_controls.py
"""

import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]  # .moai/reports — 어디서 실행해도 같은 자리
SRC_APPROVAL = BASE / "t506/commands_for_approval_v3.txt"
SRC_AUDIT = BASE / "t506/live_write_v3/audit/audit-20261005.jsonl"
OUT = BASE / "t512/controls"
OUT.mkdir(parents=True, exist_ok=True)

approval = SRC_APPROVAL.read_text("utf-8")
anchor = "# 묶음 4"
assert approval.count(anchor) == 1
(OUT / "c1_approval_injected.txt").write_text(
    approval.replace(anchor, "Delete Sequence 14\n\n" + anchor), "utf-8"
)

rows = SRC_AUDIT.read_text("utf-8").splitlines()


def is_send(line: str, command: str) -> bool:
    event = json.loads(line)
    return (
        event.get("event") == "executed"
        and event.get("kind") == "command"
        and event.get("command") == command
    )


def write_audit(name: str, lines: list[str]) -> None:
    folder = OUT / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / SRC_AUDIT.name).write_text("".join(f"{x}\n" for x in lines), "utf-8")


go = [i for i, x in enumerate(rows) if is_send(x, "Go Timecode 14")]
assert len(go) == 1
write_audit("c2_audit_line_removed", rows[: go[0]] + rows[go[0] + 1 :])

extra = json.dumps(
    {
        "ts": json.loads(rows[go[0]])["ts"],
        "event": "executed",
        "command": "SaveShow",
        "kind": "backup",
        "ok": True,
        "detail": "OK (control: injected)",
    },
    ensure_ascii=False,
)
write_audit("c3_audit_line_added", rows[: go[0]] + [extra] + rows[go[0] :])

t1 = [
    i for i, x in enumerate(rows) if is_send(x, "Store Property 'Time' 1 'AbsTime' 1 'Token' 'Go+'")
]
t2 = [
    i for i, x in enumerate(rows) if is_send(x, "Store Property 'Time' 2 'AbsTime' 2 'Token' 'Go+'")
]
assert len(t1) == 1 and len(t2) == 1
swapped = list(rows)
swapped[t1[0]], swapped[t2[0]] = rows[t2[0]], rows[t1[0]]
write_audit("c4_audit_swapped", swapped)
print("controls written:", sorted(p.name for p in OUT.iterdir()))
