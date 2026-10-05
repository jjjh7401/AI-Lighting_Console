"""t506 타임코드 재생 프로브 v3 — 1회차 잔여물 Timecode 14 를 이어 쓴다.

v1(`tc_probe.py` @b4feadd3)은 큰따옴표가 앱 프로토콜에서 송신 전에 거절돼
준비 묶음에서 멈췄다(verdict.md §6). v3 가 바꾼 것:

- 새 슬롯을 만들지 않는다. 이미 Track(대상 Sequence 9)과 TimeRange 1 이 있는 TC14 를 쓴다.
- 트랙 주소를 하드코딩하지 않는다. 송신 직전에 TC14/1 의 자식을 되읽어
  `TARGET == "Sequence 9"` 인 Track 의 `NO` 로 명령 주소를 만든다.
  실측(`r5_track_numbers.txt`): Marker `NO 0`(상태 경로 i=1), Track `NO 1`(i=2).
  명령 주소는 상태 경로 번호가 아니라 `NO` 를 쓴다 — 1회차 `Assign … At Timecode 14.1.1`
  이 Marker 가 아니라 Track 을 만든 것과 맞는다.
- 큰따옴표 없음(`server/bridge/protocol.py:125-130`).
- 준비를 둘로 나눈다. A(Duration · CmdSubTrack 생성) 뒤에 TimeRange 아래를 되읽어
  CmdSubTrack 이 정확히 하나일 때만 B(cd · 이벤트 3 · cd root)를 보낸다.
- 되읽은 이벤트가 3개가 아니면 재생하지 않는다(v1 과 같다).

세 모드는 v1 과 같다: --rehearse / (기본) 전부-거절 / --approve <전부-거절 폴더>.
실행: .venv/bin/python .moai/reports/t506/tc_probe_v3.py <출력폴더>
      [--rehearse | --approve <전부-거절 폴더>]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")
sys.path.insert(0, str(Path(__file__).parent))
from tc_probe import LISTEN_PORT, Probe, RecordingApproval  # noqa: E402

from server.safety.audit import AuditLog  # noqa: E402
from server.safety.console import ExecOutcome, LinkTimeouts, StateQueryError  # noqa: E402
from server.safety.gate import BatchRisk, SafetyGate  # noqa: E402
from server.safety.ruleset import load_ruleset  # noqa: E402

SLOT = 14
SEQ = 9
TC_NAME = "T506 TCPROBE"
EVENT_TIMES = (1, 2, 3)
SAMPLE_SECONDS = 4.5

TC = f"ShowData/DataPools/Default/Timecodes/{SLOT}"
SEQ_PATH = f"ShowData/DataPools/Default/Sequences/{SEQ}"
SEQ_TARGET = f"Sequence {SEQ}"

RISK = BatchRisk(
    reason="t506 v3 — 잔여물 Timecode 14 에 CmdSubTrack·이벤트 3개 추가·재생", kind="t506_probe"
)


def bundles(track_no: int) -> list[tuple[str, list[str]]]:
    addr = f"Timecode {SLOT}.1.{track_no}.1"
    return [
        (
            "prep_a",
            [
                f"Set Timecode {SLOT} Property 'Duration' 5 'AutoStop' 0",
                f"Store Type 'CmdSubTrack' {addr}",
            ],
        ),
        (
            "prep_b",
            [
                f"cd {addr}.1",
                *[f"Store Property 'Time' {t} 'AbsTime' {t} 'Token' 'Go+'" for t in EVENT_TIMES],
                "cd root",
            ],
        ),
        ("play", [f"Go Timecode {SLOT}"]),
        ("release", [f"Off Timecode {SLOT}", f"Off Sequence {SEQ}"]),
    ]


# ---------------------------------------------------------------- 가짜 콘솔(리허설 전용)


class FakeConsoleV3:
    """1회차 잔여물 모양(Marker NO0 i1 · Track NO1 i2 → TimeRange 1)에서 시작하는 얕은 모형."""

    responder_version = "fake"

    def __init__(self) -> None:
        self.sent: list[str] = []
        self.subtrack = False
        self.events: list[float] = []
        self.go_at: float | None = None
        self.cwd = "root"

    def ping(self) -> bool:
        return True

    def execute(self, command: str) -> ExecOutcome:
        self.sent.append(command)
        if '"' in command:  # 실제 앱 프로토콜과 같이 송신 전 거절(protocol.py:125-130)
            return ExecOutcome(status="failed", detail="fake: double quote rejected")
        if command == f"Store Type 'CmdSubTrack' Timecode {SLOT}.1.1.1":
            self.subtrack = True
        elif command.startswith("cd "):
            target = command[3:]
            if target != "root" and not (self.subtrack and target == f"Timecode {SLOT}.1.1.1.1"):
                return ExecOutcome(status="failed", detail="Failed")
            self.cwd = target
        elif command.startswith("Store Property 'Time'"):
            if self.cwd != f"Timecode {SLOT}.1.1.1.1":
                return ExecOutcome(status="failed", detail="fake: not in subtrack")
            self.events.append(float(command.split()[3]))
        elif command == f"Go Timecode {SLOT}":
            self.go_at = time.monotonic()
        elif command.startswith("Off "):
            self.go_at = None
        return ExecOutcome(status="ok", detail="OK")

    def _elapsed(self) -> float | None:
        return None if self.go_at is None else time.monotonic() - self.go_at

    def query_state(self, path: str, offset: int = 0) -> dict:
        shapes = {
            TC: [("TrackGroup", 1)],
            f"{TC}/1": [("MarkerTrack", 1), ("Track", 2)],
            f"{TC}/1/2": [("TimeRange", 1)],
            f"{TC}/1/2/1": [("CmdSubTrack", 1)] if self.subtrack else [],
            f"{TC}/1/2/1/1": [("CmdEvent", n + 1) for n in range(len(self.events))],
        }
        if path not in shapes:
            raise StateQueryError(f"path segment not found (in {path})")
        kids = [{"class": c, "i": i, "name": c} for c, i in shapes[path]]
        return dict(ok=True, path=path, node=dict(childCount=len(kids)), children=kids, fake=True)

    def query_properties(self, path: str, names) -> dict:
        elapsed = self._elapsed()
        values = {
            (f"{TC}/1/1", "NO"): "0",
            (f"{TC}/1/1", "TARGET"): None,
            (f"{TC}/1/2", "NO"): "1",
            (f"{TC}/1/2", "TARGET"): SEQ_TARGET,
            (TC, "NAME"): TC_NAME,
        }
        reads = []
        for name in names:
            if path == SEQ_PATH and name == "CURRENTCUE":
                fired = [t for t in self.events if elapsed is not None and elapsed >= t]
                if fired:
                    reads.append(dict(n=name, ok=True, v=f"Sequence {SEQ}.{len(fired)}"))
                else:
                    reads.append(dict(n=name, ok=False, e="property not readable: CURRENTCUE"))
            elif path == TC and name == "CURSOR":
                reads.append(dict(n=name, ok=True, v=f"{elapsed or 0.0:.2f}"))
            elif (path, name) in values:
                reads.append(dict(n=name, ok=True, v=values[(path, name)]))
            else:
                reads.append(dict(n=name, ok=True, v="fake"))
        return dict(ok=True, path=path, reads=reads, fake=True)

    def query_property(self, path: str, name: str) -> dict:
        return self.query_properties(path, [name])

    def enumerate_fields(self, path: str, offset: int = 0) -> dict:
        return dict(ok=True, path=path, fields=[], fake=True)


# ---------------------------------------------------------------- 진행


def _value(payload: dict | None, name: str):
    for read in (payload or {}).get("reads") or ():
        if read.get("n") == name and read.get("ok"):
            return read.get("v")
    return None


def _children(payload: dict | None) -> list[dict]:
    return [c for c in (payload or {}).get("children") or () if isinstance(c, dict)]


def run(gate: SafetyGate, out: Path, *, live: bool, deny_all: bool) -> dict:
    import tc_probe

    # Probe(v1 모듈)가 모듈 전역으로 읽는 값을 v3 값으로 맞춘다 — 샘플 경로와 승인 사유 문면.
    tc_probe.SEQ_PATH, tc_probe.TC, tc_probe.RISK = SEQ_PATH, TC, RISK
    tc_probe.SAMPLE_SECONDS = SAMPLE_SECONDS
    probe = Probe(gate, out)
    result: dict = dict(slot=SLOT, sequence=SEQ, event_times=list(EVENT_TIMES), bundles={})

    def stop(reason: str) -> dict:
        result["verdict"] = reason
        return finish(probe, result)

    # 사전 판독 — 잔여물 모양이 1회차 그대로인지
    name = _value(probe.read_props("pre_tc_name", TC, ["NAME", "DURATION"]), "NAME")
    group = probe.read_state("pre_trackgroup", f"{TC}/1")
    track = None
    for child in _children(group):
        if child.get("class") != "Track":
            continue
        props = probe.read_props("pre_track_props", f"{TC}/1/{child['i']}", ["NO", "TARGET"])
        if _value(props, "TARGET") == SEQ_TARGET:
            track = dict(i=child["i"], no=int(float(_value(props, "NO"))))
    seq_pre = probe.read_props("pre_seq9", SEQ_PATH, ["CURRENTCUE"])
    seq_off = bool(seq_pre) and _value(seq_pre, "CURRENTCUE") is None
    result.update(tc_name=name, track=track, seq9_off_before=seq_off)
    if name != TC_NAME or track is None:
        return stop("stopped: Timecode 14 is not the run-1 residue with a Sequence 9 track")
    if not seq_off:
        return stop("stopped: sequence 9 not off before probe")
    range_path = f"{TC}/1/{track['i']}/1"
    before = _children(probe.read_state("pre_timerange", range_path))
    if before:
        return stop(f"stopped: TimeRange already has children {before}")

    plan = bundles(track["no"])
    result["planned"] = {label: cmds for label, cmds in plan}
    by_label = dict(plan)

    if deny_all:
        # 전부-거절: 네 묶음의 승인 문면만 남긴다. 거절된 심사는 아무것도 보내지 않는다.
        for label, cmds in plan:
            result["bundles"][label] = probe.fire(label, cmds)
        return stop("deny-all: approval texts recorded, nothing written")

    if not probe.fire("prep_a", by_label["prep_a"]):
        result["bundles"]["prep_a"] = False
        return stop("prep_a not executed (denied or failed)")
    result["bundles"]["prep_a"] = True

    # cd 직전 안전장치: TimeRange 아래에 CmdSubTrack 이 정확히 하나여야 한다
    subs = _children(probe.read_state("post_a_timerange", range_path))
    result["post_a_children"] = [c.get("class") for c in subs]
    if [c.get("class") for c in subs] != ["CmdSubTrack"]:
        return stop(f"stopped before cd: TimeRange children {result['post_a_children']}")

    result["bundles"]["prep_b"] = probe.fire("prep_b", by_label["prep_b"])
    events = _children(probe.read_state("post_b_subtrack", f"{range_path}/{subs[0]['i']}"))
    for ev in events:
        probe.read_props(
            "post_b_event",
            f"{range_path}/{subs[0]['i']}/{ev['i']}",
            ["NAME", "TIME", "ABSTIME", "TOKEN", "CUEDESTINATION"],
        )
    result["events_found"] = len(events)
    if len(events) != len(EVENT_TIMES):
        result["bundles"]["release"] = probe.fire("release", by_label["release"])
        return stop(f"stopped before play: events found {len(events)} != {len(EVENT_TIMES)}")

    played = probe.fire("play", by_label["play"])
    result["bundles"]["play"] = played
    if played:
        result["samples"] = probe.sample_playback()
    result["bundles"]["release"] = probe.fire("release", by_label["release"])
    probe.read_props("post_release_seq9", SEQ_PATH, ["CURRENTCUE"])
    probe.read_props("post_release_tc", TC, ["CURSOR", "NAME", "DURATION"])
    return stop("ran — judge from samples (live)" if live else "rehearsal — script path only")


def finish(probe: Probe, result: dict) -> dict:
    probe.out.mkdir(parents=True, exist_ok=True)
    with (probe.out / "steps.jsonl").open("w", encoding="utf-8") as handle:
        for row in probe.log:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    parser.add_argument("--rehearse", action="store_true")
    parser.add_argument("--approve", default=None, help="전부-거절 실행 폴더(approvals.json)")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    skipped_backups: list[str] = []

    if args.rehearse:
        from server.safety.backup import BackupManager

        console = FakeConsoleV3()
        approval = RecordingApproval([cmds for _, cmds in bundles(1)])
        gate = SafetyGate(
            console=console,
            audit=AuditLog(out / "audit"),
            ruleset=load_ruleset(),
            approval_port=approval,
            backup=BackupManager(
                backup_action=lambda: skipped_backups.append("SaveShow skipped (rehearsal)")
            ),
        )
        result = run(gate, out, live=False, deny_all=False)
        result["fake_sent"] = console.sent
    else:
        from server.safety.bootstrap import build_console_stack
        from server.tools.probe_preflight import preflight

        pinned = None
        if args.approve:
            approvals = json.loads((Path(args.approve) / "approvals.json").read_text("utf-8"))
            pinned = [r["commands"] for r in approvals]
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
        # t498 감독 결정(2026-09-27)·t501 과 같다: 쇼 저장은 보내지 않고 기록만.
        stack.backup._backup_action = lambda: skipped_backups.append(
            "SaveShow skipped (supervisor)"
        )
        try:
            health = preflight(
                stack.gate, receive_host="127.0.0.1", receive_port=LISTEN_PORT, console_port=8000
            )
            if health.get("verdict") != "responder_ok":
                print(json.dumps(dict(preflight=health), ensure_ascii=False, indent=2))
                return 1
            result = run(stack.gate, out, live=True, deny_all=pinned is None)
            result["preflight"] = health.get("verdict")
        finally:
            stack.stop()

    result["approval_requests"] = approval.requests
    result["skipped_saveshow"] = skipped_backups
    (out / "approvals.json").write_text(
        json.dumps(approval.requests, ensure_ascii=False, indent=2), "utf-8"
    )
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
    summary = {k: v for k, v in result.items() if k not in ("samples", "fake_sent")}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    for sample in result.get("samples", []):
        print("SAMPLE", json.dumps(sample, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
