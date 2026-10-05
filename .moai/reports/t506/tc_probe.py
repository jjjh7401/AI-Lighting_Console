"""t506 타임코드 재생 실기 프로브 — 빈 슬롯 하나, 트랙 하나, 이벤트 셋.

묻는 것 (카드 t506):
    (a) 타임코드 재생이 실제로 시퀀스 큐를 넘기는가
        — 2026-09-05 M3-a 2회차는 효과를 잴 채널이 없었다(문서 14 「2회차 정정」).
          이 프로브는 Sequence 의 `CURRENTCUE` 와 Timecode 의 `CURSOR` 를 되읽는다.
    (b) 이벤트를 앱 명령줄로 만들 수 있는가
        — 근거: grandMA3 2.4.2 설치본의 MA 자체 시스템 테스트
          `shared/resource/lib_plugins/systemtests/db/system_test_timecode_record.lua`
          #33162 가 명령줄만으로 CmdSubTrack 과 Go+ 이벤트를 만든다. 그 형태를 그대로 쓴다.
    (c) 시간 정밀도 — 이벤트 1·2·3초에 대해 큐 전환 관측 시각을 적는다(조회 왕복 지연 포함).

대상: 시퀀스 9 「T215 SCRATCH DELETABLE」(큐 1~4 전부 TrigType Go — 저절로 안 넘어간다),
빈 타임코드 슬롯 14. 기존 번호는 덮지도 지우지도 않는다. 쇼 저장 안 함 — 게이트의 실행 직전
백업(SaveShow)은 t498/t501 과 같이 「보내지 않고 기록만」으로 바꿔 끼운다.

세 모드:
    --rehearse        가짜 콘솔(네트워크 0) + 실제 게이트·규칙집.
                      게이트가 각 줄을 어떻게 다루는지 본다.
    (기본) 전부-거절   실기 콘솔. 읽기만 나가고 쓰기 묶음은 승인 요청만 뜬 뒤 거절 — 쓰기 0.
    --approve <폴더>   실기 콘솔. 그 폴더 approvals.json 의 묶음과
                      **글자까지 같은** 묶음만 승인.

실행: .venv/bin/python .moai/reports/t506/tc_probe.py <출력폴더>
      [--rehearse | --approve <전부-거절 폴더>]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")
from server.safety.approval import ApprovalRequest  # noqa: E402
from server.safety.audit import AuditLog  # noqa: E402
from server.safety.console import ExecOutcome, LinkTimeouts, StateQueryError  # noqa: E402
from server.safety.gate import BatchRisk, SafetyGate  # noqa: E402
from server.safety.ruleset import load_ruleset  # noqa: E402

SLOT = 15  # v2: 14 는 1회차(따옴표 정지)의 잔여물로 남아 있다 — 삭제 금지라 새 슬롯
SEQ = 9
TC_NAME = "T506 TCPROBE"
EVENT_TIMES = (1, 2, 3)
SAMPLE_SECONDS = 4.5
LISTEN_PORT = 9005

TC = f"ShowData/DataPools/Default/Timecodes/{SLOT}"
TC_POOL = "ShowData/DataPools/Default/Timecodes"
SEQ_PATH = f"ShowData/DataPools/Default/Sequences/{SEQ}"

PREP = [
    f"Store Timecode {SLOT}",
    f"Set Timecode {SLOT} Property 'Name' '{TC_NAME}'",
    f"Set Timecode {SLOT} Property 'Duration' 5 'AutoStop' 0",
    f"Store Timecode {SLOT}.1",
    f"Assign Sequence {SEQ} At Timecode {SLOT}.1.1",
    f"Store Type 'CmdSubTrack' Timecode {SLOT}.1.1.1",
    f"cd Timecode {SLOT}.1.1.1.1",
    # 큰따옴표는 앱 프로토콜이 송신 전에 거절한다(server/bridge/protocol.py:125-130) — 작은따옴표.
    *[f"Store Property 'Time' {t} 'AbsTime' {t} 'Token' 'Go+'" for t in EVENT_TIMES],
    "cd root",
]
PLAY = [f"Go Timecode {SLOT}"]
RELEASE = [f"Off Timecode {SLOT}", f"Off Sequence {SEQ}"]
BUNDLES = (("prep", PREP), ("play", PLAY), ("release", RELEASE))

# 묶음 전체를 승인 대상으로 선언한다 — 분류가 「안전」으로 본 줄이 전부-거절 실행에서
# 혼자 나가는 일을 막는다(게이트는 묶음 단위 전부-아니면-0).
RISK = BatchRisk(reason="t506 타임코드 프로브 — 빈 슬롯 15 생성·이벤트 3개·재생", kind="t506_probe")


# ---------------------------------------------------------------- 승인 통로


class RecordingApproval:
    def __init__(self, pinned: list[list[str]] | None) -> None:
        self.pinned = pinned
        self.requests: list[dict] = []

    def request_approval(self, request: ApprovalRequest) -> bool:
        commands = list(request.commands)
        approved = self.pinned is not None and commands in self.pinned
        self.requests.append(dict(commands=commands, approved=approved))
        return approved


# ---------------------------------------------------------------- 가짜 콘솔(리허설 전용)


class FakeConsole:
    """명령을 받아 아주 얕은 타임코드 모형만 흉내 낸다. 콘솔 의미론의 증거가 아니다."""

    responder_version = "fake"

    def __init__(self) -> None:
        self.sent: list[str] = []
        self.tc_exists = False
        self.events: list[float] = []
        self.go_at: float | None = None
        self.cwd = "root"

    def ping(self) -> bool:
        return True

    def execute(self, command: str) -> ExecOutcome:
        self.sent.append(command)
        if '"' in command:  # 실제 앱 프로토콜과 같이 송신 전 거절(protocol.py:125-130)
            return ExecOutcome(status="failed", detail="fake: double quote rejected")
        if command == f"Store Timecode {SLOT}":
            self.tc_exists = True
        elif command.startswith("cd "):
            self.cwd = command[3:]
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
        if path.startswith(TC) and not self.tc_exists:
            raise StateQueryError(f"path segment not found: '{SLOT}' (in {path})")
        # 얕은 트리 모형: TC/1(그룹) → 2(Track) → 1(TimeRange) → 1(CmdSubTrack) → 이벤트들
        shapes = {
            f"{TC}/1": [dict(cls="MarkerTrack", i=1), dict(cls="Track", i=2)],
            f"{TC}/1/2": [dict(cls="TimeRange", i=1)],
            f"{TC}/1/2/1": [dict(cls="CmdSubTrack", i=1)],
            f"{TC}/1/2/1/1": [dict(cls="CmdEvent", i=n + 1) for n in range(len(self.events))],
        }
        kids = [dict(**{"class": k["cls"]}, i=k["i"], name=k["cls"]) for k in shapes.get(path, [])]
        return dict(ok=True, path=path, node=dict(childCount=len(kids)), children=kids, fake=True)

    def query_properties(self, path: str, names) -> dict:
        reads = []
        elapsed = self._elapsed()
        for name in names:
            if path == SEQ_PATH and name == "CURRENTCUE":
                fired = [t for t in self.events if elapsed is not None and elapsed >= t]
                if not fired:
                    reads.append(dict(n=name, ok=False, e="property not readable: CURRENTCUE"))
                else:
                    reads.append(dict(n=name, ok=True, v=f"Sequence {SEQ}.{len(fired)}"))
            elif path == TC and name == "CURSOR":
                reads.append(dict(n=name, ok=True, v=f"{elapsed or 0.0:.2f}"))
            else:
                reads.append(dict(n=name, ok=True, v="fake"))
        return dict(ok=True, path=path, reads=reads, fake=True)

    def query_property(self, path: str, name: str) -> dict:
        return self.query_properties(path, [name])

    def enumerate_fields(self, path: str, offset: int = 0) -> dict:
        return dict(ok=True, path=path, fields=[], fake=True)


# ---------------------------------------------------------------- 진행


class Probe:
    def __init__(self, gate: SafetyGate, out: Path) -> None:
        self.gate = gate
        self.port = gate.state_port
        self.out = out
        self.log: list[dict] = []
        self.t0 = time.monotonic()

    def note(self, step: str, **data) -> dict:
        row = dict(step=step, t=round(time.monotonic() - self.t0, 3), **data)
        self.log.append(row)
        print(json.dumps(row, ensure_ascii=False)[:600])
        return row

    def read_state(self, label: str, path: str) -> dict | None:
        try:
            payload = self.port.query_state(path)
        except Exception as error:  # noqa: BLE001 — 사유를 그대로 싣는다
            self.note(label, kind="state", path=path, ok=False, error=str(error))
            return None
        self.note(label, kind="state", path=path, ok=True, payload=payload)
        return payload

    def read_props(self, label: str, path: str, names: list[str]) -> dict | None:
        try:
            payload = self.port.query_properties(path, names)
        except Exception as error:  # noqa: BLE001
            self.note(label, kind="props", path=path, ok=False, error=str(error))
            return None
        self.note(label, kind="props", path=path, ok=True, payload=payload)
        return payload

    def fire(self, label: str, commands: list[str]) -> bool:
        """묶음 하나를 심사받고, 통과하면 한 줄씩 보낸다.

        `cd` 가 실패하면 그 뒤 `Store Property` 줄은 보내지 않는다 — 루트 문맥에서
        `Store Property` 가 무엇을 만들지 모르기 때문이다. `cd root` 는 언제나 보낸다.
        """
        decision = self.gate.screen(commands, risk=RISK)
        self.note(
            label,
            kind="screen",
            cleared=decision.cleared,
            commands=[
                dict(command=c.command, reasons=list(getattr(c, "reasons", ()) or ()))
                for c in decision.commands
            ],
        )
        if not decision.cleared:
            return False
        skip_store_property = False
        all_ok = True
        for command in commands:
            if skip_store_property and command.startswith("Store Property"):
                self.note(label, kind="exec", command=command, fired=False, detail="cd 실패로 보류")
                all_ok = False
                continue
            result = self.gate.execution_port.execute(command)
            self.note(
                label, kind="exec", command=command, fired=True, ok=result.ok, detail=result.detail
            )
            if command.startswith("cd Timecode") and not result.ok:
                skip_store_property = True
            all_ok = all_ok and result.ok
        return all_ok

    def walk_timecode(self) -> int:
        """준비 뒤 슬롯 아래를 이벤트까지 내려가 본다(자식이 오브젝트라 경로 번호로 연다).

        찾은 이벤트 수를 돌려준다 — 재생 묶음은 이 수가 계획(3)과 같을 때만 보낸다.
        """
        found = 0
        root = self.read_state("post_prep_tc", TC)
        if not root:
            return found
        group = self.read_state("post_prep_trackgroup", f"{TC}/1")
        for child in (group or {}).get("children", []):
            if child.get("class") != "Track":
                continue
            track = f"{TC}/1/{child['i']}"
            self.read_props("post_prep_track_props", track, ["NAME", "TARGET"])
            ranges = self.read_state("post_prep_track", track) or {}
            for rng in ranges.get("children", []):
                tr = f"{track}/{rng['i']}"
                subs = self.read_state("post_prep_timerange", tr) or {}
                for sub in subs.get("children", []):
                    sp = f"{tr}/{sub['i']}"
                    events = self.read_state("post_prep_subtrack", sp) or {}
                    first = True
                    for ev in events.get("children", []):
                        found += 1
                        ep = f"{sp}/{ev['i']}"
                        if first:
                            self.note("post_prep_event_fields", kind="introspect_path", path=ep)
                            try:
                                fields = self.port.enumerate_fields(ep)
                                self.note(
                                    "post_prep_event_fields",
                                    kind="introspect",
                                    path=ep,
                                    payload=fields,
                                )
                            except Exception as error:  # noqa: BLE001
                                self.note(
                                    "post_prep_event_fields",
                                    kind="introspect",
                                    path=ep,
                                    error=str(error),
                                )
                            first = False
                        self.read_props(
                            "post_prep_event",
                            ep,
                            ["NAME", "TIME", "ABSTIME", "TOKEN", "CUEDESTINATION"],
                        )
        return found

    def sample_playback(self) -> list[dict]:
        samples = []
        start = time.monotonic()
        while time.monotonic() - start < SAMPLE_SECONDS:
            before = time.monotonic() - start
            seq = self.read_props("sample_seq", SEQ_PATH, ["CURRENTCUE"])
            tc = self.read_props("sample_tc", TC, ["CURSOR"])
            after = time.monotonic() - start

            def first_read(payload):
                reads = (payload or {}).get("reads") or [{}]
                return reads[0].get("v") if reads[0].get("ok") else None

            samples.append(
                dict(
                    t_from_go=[round(before, 3), round(after, 3)],
                    currentcue=first_read(seq),
                    cursor=first_read(tc),
                )
            )
            # 조회 간격 하한 — 실기 왕복이 짧을 때 콘솔을 조회로 두드리지 않는다.
            time.sleep(max(0.0, 0.15 - (after - before)))
        return samples


def run(gate: SafetyGate, out: Path, *, live: bool) -> dict:
    probe = Probe(gate, out)
    result: dict = dict(slot=SLOT, sequence=SEQ, event_times=list(EVENT_TIMES), bundles={})

    # 사전 판독 + 대조군
    pool = probe.read_state("pre_pool", TC_POOL)
    slot_absent = probe.read_state("pre_slot_negative_control", TC) is None
    seq_pre = probe.read_props("pre_seq9", SEQ_PATH, ["CURRENTCUE", "CUENO"])
    seq9_off = bool(seq_pre) and not seq_pre["reads"][0].get("ok")
    taken = [c.get("i") for c in (pool or {}).get("children", [])]
    result.update(pre_pool_numbers=taken, slot_absent=slot_absent, seq9_off_before=seq9_off)
    if SLOT in taken or not slot_absent:
        result["verdict"] = "stopped: slot 14 not free"
        return finish(probe, result)
    if not seq9_off:
        result["verdict"] = "stopped: sequence 9 not off before probe"
        return finish(probe, result)

    ok = probe.fire("prep", PREP)
    result["bundles"]["prep"] = ok
    if not ok:
        # 전부-거절 실행에서도 재생·해제 묶음의 승인 요청 문면을 남긴다 — 승인 실행은
        # 세 묶음 모두를 글자 대조로 고정해야 한다. 거절된 심사는 아무것도 보내지 않는다.
        if not any(r["approved"] for r in getattr(gate._approval_port, "requests", [])):
            for label, bundle in BUNDLES[1:]:
                result["bundles"][label] = probe.fire(label, bundle)
        result["verdict"] = "prep not executed (denied or failed)"
        return finish(probe, result)
    events_found = probe.walk_timecode()
    result["events_found"] = events_found
    if events_found != len(EVENT_TIMES):
        # 이벤트가 계획한 자리에 없으면 재생하지 않는다 — 무엇이 재생될지 모른다.
        result["bundles"]["release"] = probe.fire("release", RELEASE)
        result["verdict"] = (
            f"stopped before play: events found {events_found} != {len(EVENT_TIMES)}"
        )
        return finish(probe, result)

    played = probe.fire("play", PLAY)
    result["bundles"]["play"] = played
    if played:
        result["samples"] = probe.sample_playback()
    result["bundles"]["release"] = probe.fire("release", RELEASE)
    probe.read_props("post_release_seq9", SEQ_PATH, ["CURRENTCUE"])
    probe.read_props("post_release_tc", TC, ["CURSOR", "NAME", "DURATION"])
    result["verdict"] = (
        "ran — judge from samples (live)" if live else "rehearsal — script path only"
    )
    return finish(probe, result)


def finish(probe: Probe, result: dict) -> dict:
    out = probe.out
    out.mkdir(parents=True, exist_ok=True)
    with (out / "steps.jsonl").open("w", encoding="utf-8") as handle:
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

    pinned = None
    if args.approve:
        pinned = [
            r["commands"]
            for r in json.loads((Path(args.approve) / "approvals.json").read_text("utf-8"))
        ]
    approval = RecordingApproval(pinned)
    skipped_backups: list[str] = []

    if args.rehearse:
        from server.safety.backup import BackupManager

        console = FakeConsole()
        gate = SafetyGate(
            console=console,
            audit=AuditLog(out / "audit"),
            ruleset=load_ruleset(),
            approval_port=RecordingApproval([list(b) for _, b in BUNDLES]),
            backup=BackupManager(
                backup_action=lambda: skipped_backups.append("SaveShow skipped (rehearsal)")
            ),
        )
        approval = gate._approval_port  # 리허설은 세 묶음을 모두 승인해 경로를 끝까지 탄다
        result = run(gate, out, live=False)
        result["fake_sent"] = console.sent
    else:
        from server.safety.bootstrap import build_console_stack
        from server.tools.probe_preflight import preflight

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
            result = run(stack.gate, out, live=True)
            result["preflight"] = health.get("verdict")
        finally:
            stack.stop()

    result["approval_requests"] = approval.requests
    result["skipped_saveshow"] = skipped_backups
    (out / "approvals.json").write_text(
        json.dumps(approval.requests, ensure_ascii=False, indent=2), "utf-8"
    )
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
    print(
        json.dumps(
            {k: v for k, v in result.items() if k != "samples"}, ensure_ascii=False, indent=2
        )
    )
    for sample in result.get("samples", []):
        print("SAMPLE", json.dumps(sample, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
