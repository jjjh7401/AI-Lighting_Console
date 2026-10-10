"""t531 M1 — 아홉 개 최소 프로브가 공유하는 뼈대.

t506(`tc_probe.py`)·t516(`rhythm_probe.py`/`control_probe.py`) 의 진행 틀
(Probe·RecordingApproval·세 모드·실제 SafetyGate+ruleset)을 그대로 재사용한다.
이 파일은 그 틀 위에 "번호대 밴드·빈 슬롯 재확인·가짜 콘솔" 공통부만 얹는다.

번호대 밴드(절대 안 건드리는 기존 번호와 분리):
    시퀀스 300~319 · 타임코드 30~34 · 프리셋 풀마다 301 번부터.
    기존 시퀀스(228~233 등)는 참조만 하고 절대 Store/수정하지 않는다.

각 p<n>.py 는 이 모듈에서 Probe·RecordingApproval·run_probe 를 가져와
자기 번들 목록(build_plan)과 자기 자유-슬롯 목록(free_slots)만 정의한다.

이 세션은 --rehearse 만 돈다(실기 송신 금지). 세 모드 전부를 구현해 두는 건
t506/t516 과 같은 안전 계약을 깨지 않기 위해서다 — deny-all·--approve 경로는
실행하지 않을 뿐 코드로는 존재한다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t506")
import tc_probe  # noqa: E402 — Probe·RecordingApproval 재사용
from tc_probe import LISTEN_PORT, Probe, RecordingApproval  # noqa: E402

from server.bridge.protocol import build_plugin_call  # noqa: E402
from server.safety.audit import AuditLog  # noqa: E402
from server.safety.console import ExecOutcome, LinkTimeouts, StateQueryError  # noqa: E402
from server.safety.gate import BatchRisk, SafetyGate  # noqa: E402
from server.safety.ruleset import load_ruleset  # noqa: E402

POOL = "ShowData/DataPools/Default"
SEQ_BAND = range(300, 320)  # 새 시퀀스는 이 번호대에서만 고른다
TC_BAND = range(30, 35)  # 새 타임코드는 이 번호대에서만 고른다
PRESET_START = 301  # 각 풀에서 새 프리셋은 301 번부터

# 2026-10-10 실측(r0~r0c): 이 세션에서 아직 쓰이지 않은 것으로 확인된 번호.
# 실행 전 r1_free_slots.txt 로 다시 읽어 재확인한다 — 이 상수는 「계획값」이다.
MEASURED_EXISTING_SEQUENCES = frozenset(
    {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 210, 219}
    | set(range(220, 234))
    | {1999, 2000}
)
MEASURED_EXISTING_TIMECODES = frozenset({1, 2, 7, 8, 9, 19, 20, 21})
MASTER_15_PATH = "ShowData/Masters/3/15"
MASTER_15_EXPECTED_NORMEDVALUE = "69"  # t520 verdict.md:24,107 — t516 이 112.35BPM 으로 둔 값

GROUPS = {
    "ALL": 1,
    "KEY": 2,
    "FOH": 3,
    "BACK": 4,
    "SIDE-L": 5,
    "SIDE-R": 6,
    "SIDE-ALL": 7,
    "WASH-U": 8,
    "WASH-D": 9,
    "WASH-ALL": 10,
    "MOVER-U": 11,
    "MOVER-D": 12,
    "MOVER-ALL": 13,
    "BLIND": 14,
    "STROBE": 15,
    "HAZE": 16,
    "ODD": 17,
    "EVEN": 18,
}


def seq_path(no: int) -> str:
    return f"{POOL}/Sequences/{no}"


def tc_path(no: int) -> str:
    return f"{POOL}/Timecodes/{no}"


def preset_pool_path(pool: int) -> str:
    return f"{POOL}/PresetPools/{pool}"


def preset_path(pool: int, no: int) -> str:
    return f"{preset_pool_path(pool)}/{no}"


def label(item: str, name: str) -> str:
    """감독 규칙 'LDBEAT M1 - P<n> <name>' — 작은 따옴표(큰따옴표는 송신 전 거절)."""
    text = name.strip()
    if '"' in text or "'" in text:
        raise ValueError(f"name carries a quote, cannot be sent: {name!r}")
    return f"'LDBEAT M1 - {item} {text}'"


# ---------------------------------------------------------------- 가짜 콘솔(리허설 전용)


class GenericFakeConsole:
    """아홉 프로브 공통 가짜 콘솔 — 존재 여부·cd 맥락만 아주 얕게 흉내 낸다.

    콘솔 의미론의 증거가 아니다. 이 세션의 목적은 "실제 SafetyGate·ruleset 이
    각 줄을 어떻게 심사하는가" 이므로, 이 가짜 콘솔은 그 심사가 끝까지 진행되게
    (예외 없이, Store 이후 자식 조회가 빈 테이블이라도 ok 로) 받아주는 역할만 한다.
    """

    responder_version = "fake"

    def __init__(self) -> None:
        self.sent: list[str] = []
        self.exists: set[str] = set()
        self.cwd = "root"

    def ping(self) -> bool:
        return True

    def execute(self, command: str) -> ExecOutcome:
        self.sent.append(command)
        if '"' in command:  # 실제 앱 프로토콜과 같이 송신 전 거절(protocol.py)
            return ExecOutcome(status="failed", detail="fake: double quote rejected")
        words = command.split()
        if command.startswith("Store Sequence"):
            self.exists.add(seq_path(int(words[2])))
        elif command.startswith("Store Timecode"):
            self.exists.add(tc_path(int(words[2].split(".")[0])))
        elif command.startswith("Store Preset"):
            pool, no = words[2].split(".")
            self.exists.add(preset_path(int(pool), int(no)))
        elif command.startswith("Store Type 'CmdSubTrack'") or command.startswith("Store Property"):
            self.exists.add(self.cwd)
        elif command.startswith("cd "):
            self.cwd = " ".join(words[1:])
        return ExecOutcome(status="ok", detail="OK")

    def query_state(self, path: str, offset: int = 0) -> dict:
        root = path.split(".")[0]
        if root not in self.exists and any(
            path.startswith(pfx)
            for pfx in (f"{POOL}/Sequences/", f"{POOL}/Timecodes/", f"{POOL}/PresetPools/")
        ):
            raise StateQueryError(f"path segment not found (in {path})")
        return dict(ok=True, path=path, node=dict(childCount=0), children=[], fake=True)

    def query_properties(self, path: str, names) -> dict:
        # Master 3.15 NORMEDVALUE 는 t520 이 기록한 실측 기준값(69)로 고정 응답한다 —
        # P4 의 "재생 전 69 가 아니면 중단" 전제 검사가 리허설에서도 끝까지 가게 하려고다.
        # 다른 어떤 속성도 이 상수를 흉내 내지 않는다(가짜 콘솔 의미론은 안 잰다).
        if path == MASTER_15_PATH and "NORMEDVALUE" in names:
            reads = [
                dict(
                    n=n, ok=True, v=MASTER_15_EXPECTED_NORMEDVALUE if n == "NORMEDVALUE" else "fake"
                )
                for n in names
            ]
            return dict(ok=True, path=path, reads=reads, fake=True)
        reads = [dict(n=n, ok=True, v="fake") for n in names]
        return dict(ok=True, path=path, reads=reads, fake=True)

    def query_property(self, path: str, name: str) -> dict:
        return self.query_properties(path, [name])

    def enumerate_fields(self, path: str, offset: int = 0) -> dict:
        return dict(ok=True, path=path, fields=[], fake=True)


# ---------------------------------------------------------------- 공통 진행


def check_free(probe: Probe, label_: str, paths: list[str]) -> list[str]:
    """비어 있어야 할 경로를 다시 읽는다. 하나라도 있으면 그 경로 목록을 돌려준다."""
    occupied = []
    for path in paths:
        payload = probe.read_state(f"{label_}:{path}", path)
        if payload is not None:
            occupied.append(path)
    return occupied


def run_plan(
    probe: Probe,
    plan: list[tuple[str, list[str]]],
    *,
    deny_all: bool,
) -> dict[str, bool]:
    bundles: dict[str, bool] = {}
    for bundle_label, commands in plan:
        if deny_all:
            bundles[bundle_label] = probe.fire(bundle_label, commands)
            continue
        bundles[bundle_label] = probe.fire(bundle_label, commands)
        if not bundles[bundle_label]:
            break
    return bundles


def main_cli(
    *,
    item: str,
    risk_reason: str,
    build_plan,
    free_slots: list[str],
    extra_notes: list[str] | None = None,
) -> int:
    """세 모드 공통 진입점. ``build_plan() -> list[(label, [cmd,...])]``.

    이 세션에서는 ``--rehearse`` 만 실제로 돈다. deny-all/--approve 경로는
    t506/t516 과 같은 모양으로 남겨 두되(안전 계약 유지), 실기 전송은
    이 프로브 묶음에서 쓰지 않는다 — 카드 t531 범위는 리허설 결과까지다.
    """
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    parser.add_argument("--rehearse", action="store_true")
    parser.add_argument("--approve", default=None)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    tc_probe.RISK = BatchRisk(reason=risk_reason, kind=f"t531_m1_{item.lower()}")
    skipped: list[str] = []

    if args.rehearse:
        from server.safety.backup import BackupManager

        console = GenericFakeConsole()
        plan = build_plan()
        approval = RecordingApproval([list(cmds) for _, cmds in plan])
        gate = SafetyGate(
            console=console,
            audit=AuditLog(out / "audit"),
            ruleset=load_ruleset(),
            approval_port=approval,
            backup=BackupManager(
                backup_action=lambda: skipped.append("SaveShow skipped (rehearsal)")
            ),
        )
        probe = Probe(gate, out)
        free = check_free(probe, "pre_free", free_slots)
        result: dict = dict(
            item=item,
            free_slots=free_slots,
            occupied_before=free,
            planned={lbl: cmds for lbl, cmds in plan},
        )
        if extra_notes:
            result["notes"] = extra_notes
        if free:
            result["verdict"] = f"stopped: slots not free in fake console {free}"
        else:
            result["bundles"] = run_plan(probe, plan, deny_all=False)
            all_ok = all(result["bundles"].values())
            result["verdict"] = (
                "rehearsal ok — all bundles cleared+executed"
                if all_ok
                else ("rehearsal stopped — a bundle was not executed (see bundles)")
            )
        result["fake_sent"] = console.sent
        result["approval_requests"] = approval.requests
        result["skipped_saveshow"] = skipped
        with (out / "steps.jsonl").open("w", encoding="utf-8") as handle:
            for row in probe.log:
                handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        (out / "approvals.json").write_text(
            json.dumps(approval.requests, ensure_ascii=False, indent=2), "utf-8"
        )
        (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
        print(
            json.dumps(
                {k: v for k, v in result.items() if k not in ("fake_sent", "planned")},
                ensure_ascii=False,
                indent=2,
            )[:6000]
        )
        return 0

    # deny-all / --approve — 실기 경로. 이 카드에서는 호출하지 않는다(설계 유지용).
    from server.safety.bootstrap import build_console_stack
    from server.tools.probe_preflight import preflight

    plan = build_plan()
    pinned = None
    if args.approve:
        pinned = [
            r["commands"]
            for r in json.loads((Path(args.approve) / "approvals.json").read_text("utf-8"))
        ]
    approval = RecordingApproval(pinned)
    stack = build_console_stack(
        send_host="127.0.0.1",
        send_port=8000,
        receive_host="127.0.0.1",
        receive_port=LISTEN_PORT,
        approval_port=approval,
        audit_dir=out / "audit",
        timeouts=LinkTimeouts(state_query_seconds=6.0),
        attempt_session_backup=False,
    )
    stack.backup._backup_action = lambda: skipped.append("SaveShow skipped (supervisor)")
    try:
        health = preflight(
            stack.gate, receive_host="127.0.0.1", receive_port=LISTEN_PORT, console_port=8000
        )
        if health.get("verdict") != "responder_ok":
            print(json.dumps(dict(preflight=health), ensure_ascii=False, indent=2))
            return 1
        probe = Probe(stack.gate, out)
        free = check_free(probe, "pre_free", free_slots)
        result = dict(item=item, free_slots=free_slots, occupied_before=free)
        if free:
            result["verdict"] = f"stopped: slots not free {free}"
        else:
            result["bundles"] = run_plan(probe, plan, deny_all=(pinned is None))
            result["verdict"] = "ran live" if pinned is not None else "deny-all: nothing written"
        result["preflight"] = health.get("verdict")
    finally:
        stack.stop()
    result["approval_requests"] = approval.requests
    result["skipped_saveshow"] = skipped
    with (out / "steps.jsonl").open("w", encoding="utf-8") as handle:
        for row in probe.log:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    (out / "approvals.json").write_text(
        json.dumps(approval.requests, ensure_ascii=False, indent=2), "utf-8"
    )
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2)[:6000])
    return 0


def props_offset_wire(request_id: str, path: str, names: list[str], offset: int) -> str:
    """1.6.6 props 페이징 요청 줄 — ``build_props_query`` 가 offset 을 못 받으므로
    probe_readonly.py 가 state/introspect 에 쓰는 것과 같은 방식으로 직접 조립한다.

    PROTOCOL.md §4.8: 테이블 값(``SELECTIONDATA`` 등)에 offset 페이징이 붙는 건
    read 항목 내부의 ``offset``/``total``/``truncated`` 다 — 요청 쪽 트레일링
    토큰은 기존 state/introspect 와 같은 자리(맨 끝, ``offset=<n>``)에 붙는다.
    """
    rest = f"props {request_id} {','.join(names)} {path}"
    if offset:
        rest = f"{rest} offset={offset}"
    return build_plugin_call(rest)
