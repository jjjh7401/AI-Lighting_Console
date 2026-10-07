"""t516 리듬 대본 실기 능력 프로브 — t515 미측정 다섯 항목을 가장 작은 실기 묶음으로 잰다.

대본 시연이 아니다. 묻는 것(카드 t516):
  ① `Master 3.<m> At BPM 112.35` 송신·되읽기 — 소수 BPM 을 받는가 (문서만 있고 송신 0건)
  ② 페이저를 SpeedMaster 에 묶고 Measure(박 수)를 같이 쓰기 — 1박·2박·½박
  ③ t514 신규 모양 3개(팬 웨이브·엇갈린 팬 웨이브·가속 스윕)를 position_fx 문법
     (At Relative / At Phase / 속도 줄)으로 만들 수 있는가 — 속도 줄은 At SpeedMaster 로
  ④ 타임코드 하나에 트랙 두 개(장면·박자)
  ⑤ 한 BACK 그룹(그룹 4)을 두 시퀀스가 함께 잡을 때 어느 쪽이 보이는가

쓰는 번호(송신 직전에 비어 있는지 다시 읽는다 — 하나라도 있으면 멈춘다):
  시퀀스 220(⑤ 장면) · 221(②⑤ 박자) · 222(③ 모양) · 타임코드 20(④)
  스피드 마스터 3.<m>(①, --master)
이름은 감독 규칙 'RHYTHM PROBE - <항목>'. 이름 줄은 t513 실기로 확인된 `Set … Property 'Name'` 모양.

세 모드(t506 과 같다):
  --rehearse            가짜 콘솔 + 실제 게이트·규칙집. 네트워크 0
  (기본) 전부-거절       실기. 읽기만 나가고 쓰기 묶음은 승인 요청만 남기고 거절 — 쓰기 0
  --approve <폴더>       실기. 그 폴더 approvals.json 의 묶음과 글자까지 같은 묶음만 승인
덮어쓰기·삭제·쇼 저장(SaveShow) 없음. 게이트의 실행 직전 백업은 「보내지 않고 기록만」.

실행: uv run python .moai/reports/t516/rhythm_probe.py <출력폴더> --master <n>
      [--rehearse | --approve <전부-거절 폴더>]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t506")
import tc_probe  # noqa: E402 — Probe·RecordingApproval 재사용(t506 실기 경로)
from tc_probe import LISTEN_PORT, Probe, RecordingApproval  # noqa: E402

from server.safety.audit import AuditLog  # noqa: E402
from server.safety.console import ExecOutcome, LinkTimeouts, StateQueryError  # noqa: E402
from server.safety.gate import BatchRisk, SafetyGate  # noqa: E402
from server.safety.ruleset import load_ruleset  # noqa: E402

BPM = "112.35"
S_SCENE, S_BEAT, S_SHAPE, TC_NO = 220, 221, 222, 20
G_BACK, G_MOVER, G_ODD, G_EVEN = 4, 13, 17, 18
POOL = "ShowData/DataPools/Default"
TC = f"{POOL}/Timecodes/{TC_NO}"
SEQ = {n: f"{POOL}/Sequences/{n}" for n in (S_SCENE, S_BEAT, S_SHAPE)}
HOLD = 8.0  # 사람이 보는 시간(초) — 1박 0.534초라 8초면 1박 Measure 가 약 15번 깜빡인다
SAMPLE_SECONDS = 6.0

tc_probe.RISK = BatchRisk(
    reason="t516 리듬 능력 프로브 — 빈 번호 220~222·TC20 생성, 마스터 BPM, 재생", kind="t516_probe"
)


def name(item: str) -> str:
    return f"'RHYTHM PROBE - {item}'"


def phaser_cue(group: int, attr: str, steps: list[str], timing: list[str], cue: str) -> list[str]:
    return [
        f"Group {group}",
        *steps,
        *[f"Attribute '{attr}' At {t}" for t in timing],
        cue,
        "ClearAll",
    ]


def build(master: int, tracks: tuple[int, int] = (1, 2)) -> list[tuple[str, list[str]]]:
    """묶음 목록. tracks = 되읽은 두 트랙의 NO(전부-거절에서는 예상값 1·2)."""
    sm = f"SpeedMaster {master}"
    n1, n2 = tracks
    beat = ["ChangeDestination Root", "ClearAll"]
    for cue, measure in ((1, "1"), (2, "2"), (3, "0.5")):
        beat += phaser_cue(
            G_BACK,
            "Dimmer",
            ["Attribute 'Dimmer' At 0", "Step 2", "Attribute 'Dimmer' At 100"],
            [f"Measure {measure}", sm],
            f"Store Sequence {S_BEAT} Cue {cue} 'Measure {measure}'",
        )
    beat.append(f"Set Sequence {S_BEAT} Property 'Name' {name('SPEEDMASTER MEASURE')}")
    rel = ["Attribute 'Pan' At Relative 12"]
    shape = ["ChangeDestination Root", "ClearAll"]
    shape += phaser_cue(
        G_MOVER,
        "Pan",
        [*rel, "Attribute 'Pan' At Phase 0 Thru 360"],
        ["Measure 2", sm],
        f"Store Sequence {S_SHAPE} Cue 1 'Pan Wave'",
    )
    shape += [
        f"Group {G_ODD}",
        *rel,
        "Attribute 'Pan' At Phase 0",
        f"Group {G_EVEN}",
        *rel,
        "Attribute 'Pan' At Phase 180",
        f"Group {G_MOVER}",
        "Attribute 'Pan' At Measure 1",
        f"Attribute 'Pan' At {sm}",
        f"Store Sequence {S_SHAPE} Cue 2 'Crossed Pan Wave'",
        "ClearAll",
    ]
    for cue, measure in ((3, "4"), (4, "2"), (5, "1")):
        shape += phaser_cue(
            G_MOVER,
            "Pan",
            [*rel, "Attribute 'Pan' At Phase 0"],
            [f"Measure {measure}", sm],
            f"Store Sequence {S_SHAPE} Cue {cue} 'Sweep M{measure}'",
        )
    shape.append(f"Set Sequence {S_SHAPE} Property 'Name' {name('NEW SHAPES')}")
    return [
        ("bpm", [f"Master 3.{master} At BPM {BPM}"]),
        (
            "seq_scene",
            [
                "ChangeDestination Root",
                "ClearAll",
                f"Group {G_BACK}",
                "Attribute 'Dimmer' At 30",
                f"Store Sequence {S_SCENE} Cue 1 'Scene Back 30'",
                "ClearAll",
                f"Set Sequence {S_SCENE} Property 'Name' {name('OVERLAP SCENE')}",
            ],
        ),
        ("seq_beat", beat),
        ("seq_shape", shape),
        (
            "tc_a",
            [
                f"Store Timecode {TC_NO}",
                f"Set Timecode {TC_NO} Property 'Name' {name('TWO TRACKS')}",
                f"Set Timecode {TC_NO} Property 'Duration' 10 'AutoStop' 0",
                f"Store Timecode {TC_NO}.1",
                f"Assign Sequence {S_SCENE} At Timecode {TC_NO}.1.1",
                f"Assign Sequence {S_BEAT} At Timecode {TC_NO}.1.2",
            ],
        ),
        (
            "tc_b",
            [f"Store Type 'CmdSubTrack' Timecode {TC_NO}.1.{n}.1" for n in (n1, n2)],
        ),
        (
            "tc_c",
            [
                f"cd Timecode {TC_NO}.1.{n1}.1.1",
                "Store Property 'Time' 1 'AbsTime' 1 'Token' 'Go+'",
                "cd root",
                f"cd Timecode {TC_NO}.1.{n2}.1.1",
                "Store Property 'Time' 2 'AbsTime' 2 'Token' 'Go+'",
                "cd root",
            ],
        ),
        ("play", [f"Go Timecode {TC_NO}"]),
        ("beat_off", [f"Off Sequence {S_BEAT}"]),
        ("tc_off", [f"Off Timecode {TC_NO}", f"Off Sequence {S_SCENE}"]),
        *[(f"measure_{c}", [f"Goto Cue {c} Sequence {S_BEAT}"]) for c in (1, 2, 3)],
        ("measure_off", [f"Off Sequence {S_BEAT}"]),
        *[(f"shape_{c}", [f"Goto Cue {c} Sequence {S_SHAPE}"]) for c in (1, 2, 3, 4, 5)],
        ("shape_off", [f"Off Sequence {S_SHAPE}"]),
    ]


# ---------------------------------------------------------------- 가짜 콘솔(리허설 전용)


class FakeConsole:
    """번호 존재·타임코드 트랙 NO 만 흉내 내는 얕은 모형. 콘솔 의미론의 증거가 아니다."""

    responder_version = "fake"

    def __init__(self) -> None:
        self.sent: list[str] = []
        self.exists: set[str] = set()
        self.tracks: list[int] = []  # 시퀀스 번호, 순서 = NO 1, 2, …
        self.subs: set[int] = set()
        self.events: dict[int, int] = {}
        self.cwd = "root"

    def ping(self) -> bool:
        return True

    def execute(self, command: str) -> ExecOutcome:
        self.sent.append(command)
        if '"' in command:
            return ExecOutcome(status="failed", detail="fake: double quote rejected")
        words = command.split()
        if command.startswith("Store Sequence"):
            self.exists.add(SEQ[int(words[2])])
        elif command == f"Store Timecode {TC_NO}":
            self.exists.add(TC)
        elif command.startswith("Assign Sequence"):
            self.tracks.append(int(words[2]))
        elif command.startswith("Store Type 'CmdSubTrack'"):
            self.subs.add(int(words[-1].split(".")[2]))
        elif command.startswith("cd "):
            self.cwd = words[1] if words[1] == "root" else words[2]
        elif command.startswith("Store Property 'Time'"):
            no = int(self.cwd.split(".")[2])
            self.events[no] = self.events.get(no, 0) + 1
        return ExecOutcome(status="ok", detail="OK")

    def query_state(self, path: str, offset: int = 0) -> dict:
        if (path in SEQ.values() or path.startswith(TC)) and not any(
            path.startswith(p) for p in self.exists
        ):
            raise StateQueryError(f"path segment not found (in {path})")
        kids: list[tuple[str, int]] = []
        if path == f"{TC}/1":
            kids = [("MarkerTrack", 1)] + [("Track", i + 2) for i in range(len(self.tracks))]
        elif path.startswith(f"{TC}/1/") and path.count("/") == 6:
            kids = [("TimeRange", 1)]
        elif path.startswith(f"{TC}/1/") and path.count("/") == 7:
            no = int(path.split("/")[6]) - 1
            kids = [("CmdSubTrack", 1)] if no in self.subs else []
        elif path.startswith(f"{TC}/1/") and path.count("/") == 8:
            no = int(path.split("/")[6]) - 1
            kids = [("CmdEvent", i + 1) for i in range(self.events.get(no, 0))]
        children = [{"class": c, "i": i, "name": c} for c, i in kids]
        return dict(
            ok=True, path=path, node=dict(childCount=len(children)), children=children, fake=True
        )

    def query_properties(self, path: str, names) -> dict:
        reads = []
        for n in names:
            if path.startswith(f"{TC}/1/") and path.count("/") == 6:
                idx = int(path.split("/")[6]) - 2
                v = {"NO": str(idx + 1), "TARGET": f"Sequence {self.tracks[idx]}"}.get(n, "fake")
                reads.append(dict(n=n, ok=True, v=v))
            else:
                reads.append(dict(n=n, ok=True, v="fake"))
        return dict(ok=True, path=path, reads=reads, fake=True)

    def query_property(self, path: str, name: str) -> dict:
        return self.query_properties(path, [name])

    def enumerate_fields(self, path: str, offset: int = 0) -> dict:
        return dict(ok=True, path=path, fields=[], fake=True)


# ---------------------------------------------------------------- 진행


def _value(payload: dict | None, key: str):
    for read in (payload or {}).get("reads") or ():
        if read.get("n") == key and read.get("ok"):
            return read.get("v")
    return None


def _children(payload: dict | None) -> list[dict]:
    return [c for c in (payload or {}).get("children") or () if isinstance(c, dict)]


def run(
    gate: SafetyGate, out: Path, master: int, master_props: list[str], *, deny_all: bool, pace: bool
) -> dict:
    probe = Probe(gate, out)
    master_path = f"ShowData/Masters/3/{master}"
    result: dict = dict(master=master, slots=[S_SCENE, S_BEAT, S_SHAPE, TC_NO], bundles={})

    def stop(reason: str) -> dict:
        result["verdict"] = reason
        with (out / "steps.jsonl").open("w", encoding="utf-8") as handle:
            for row in probe.log:
                handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        return result

    # 사전 판독 — 쓰는 번호가 모두 비었는지, 마스터의 지금 값
    taken = [p for p in [*SEQ.values(), TC] if probe.read_state("pre_slot", p) is not None]
    result["pre_master"] = probe.read_props("pre_master", master_path, master_props)
    if taken:
        return stop(f"stopped: slots not empty {taken}")

    plan = build(master)
    result["planned"] = {label: cmds for label, cmds in plan}
    if deny_all:
        for label, cmds in plan:
            result["bundles"][label] = probe.fire(label, cmds)
        return stop("deny-all: approval texts recorded, nothing written")

    def fire(label: str, cmds: list[str]) -> bool:
        result["bundles"][label] = ok = probe.fire(label, cmds)
        return ok

    by = dict(plan)
    if fire("bpm", by["bpm"]):
        result["post_master"] = probe.read_props("post_master", master_path, master_props)
    for label in ("seq_scene", "seq_beat", "seq_shape"):
        if not fire(label, by[label]):
            return stop(f"{label} not executed")
    for n, p in SEQ.items():
        probe.read_props(f"post_seq_{n}", p, ["NAME"])
    if not fire("tc_a", by["tc_a"]):
        return stop("tc_a not executed")
    tracks = []
    for child in _children(probe.read_state("post_a_group", f"{TC}/1")):
        if child.get("class") == "Track":
            props = probe.read_props("post_a_track", f"{TC}/1/{child['i']}", ["NO", "TARGET"])
            tracks.append(
                dict(i=child["i"], no=_value(props, "NO"), target=_value(props, "TARGET"))
            )
    result["tracks"] = tracks
    want = {f"Sequence {S_SCENE}", f"Sequence {S_BEAT}"}
    if {t["target"] for t in tracks} != want or len(tracks) != 2:
        return stop(f"stopped after tc_a: tracks {tracks} (④ answered: not two tracks as planned)")
    by_target = {t["target"]: t for t in tracks}
    nos = tuple(int(float(by_target[f"Sequence {s}"]["no"])) for s in (S_SCENE, S_BEAT))
    live_plan = dict(build(master, nos))
    if not fire("tc_b", live_plan["tc_b"]):
        return stop("tc_b not executed")
    subs = {}
    for s in (S_SCENE, S_BEAT):
        rng = f"{TC}/1/{by_target[f'Sequence {s}']['i']}/1"
        kids = _children(probe.read_state(f"post_b_range_{s}", rng))
        subs[s] = [k.get("class") for k in kids]
    result["post_b"] = subs
    if any(v != ["CmdSubTrack"] for v in subs.values()):
        return stop(f"stopped before cd: {subs}")
    fire("tc_c", live_plan["tc_c"])
    for s in (S_SCENE, S_BEAT):
        sp = f"{TC}/1/{by_target[f'Sequence {s}']['i']}/1/1"
        result.setdefault("events", {})[s] = len(_children(probe.read_state(f"post_c_{s}", sp)))
    if result["events"] != {S_SCENE: 1, S_BEAT: 1}:
        fire("tc_off", by["tc_off"])
        return stop(f"stopped before play: events {result['events']}")

    if fire("play", by["play"]):
        samples, start = [], time.monotonic()
        while time.monotonic() - start < SAMPLE_SECONDS:
            t = round(time.monotonic() - start, 2)
            row = dict(t=t)
            for s in (S_SCENE, S_BEAT):
                row[s] = _value(
                    probe.read_props("sample_seq", SEQ[s], ["CURRENTCUE"]), "CURRENTCUE"
                )
            row["cursor"] = _value(probe.read_props("sample_tc", TC, ["CURSOR"]), "CURSOR")
            samples.append(row)
            time.sleep(0.2)
        result["samples"] = samples
    # ⑤ 박자 시퀀스를 끄면 BACK 이 장면 30% 로 돌아오는가 — 사람이 본다
    probe.note("watch", say="⑤ 지금 BACK 은 펄스 중. 박자 시퀀스를 끈다 → 30% 로 돌아오는지 보라")
    fire("beat_off", by["beat_off"])
    if pace:
        time.sleep(4.0)
    fire("tc_off", by["tc_off"])
    for label, say in (
        ("measure_1", "② Measure 1 — 1박(0.534초)에 한 번 깜빡여야 한다"),
        ("measure_2", "② Measure 2 — 2박(1.07초)에 한 번"),
        ("measure_3", "② Measure 0.5 — 반 박(0.267초)에 한 번"),
        ("measure_off", ""),
        ("shape_1", "③ 팬 웨이브 — 2박 한 바퀴, 무빙이 줄지어 따라감"),
        ("shape_2", "③ 엇갈린 팬 웨이브 — ODD/EVEN 반대 방향, 1박 한 바퀴"),
        ("shape_3", "③ 가속 스윕 4박"),
        ("shape_4", "③ 가속 스윕 2박"),
        ("shape_5", "③ 가속 스윕 1박"),
        ("shape_off", ""),
    ):
        if say:
            probe.note("watch", say=say)
        fire(label, by[label])
        if pace and say:
            time.sleep(HOLD)
    for n, p in SEQ.items():
        probe.read_props(f"end_seq_{n}", p, ["NAME", "CURRENTCUE"])
    probe.read_props("end_tc", TC, ["NAME", "CURSOR"])
    return stop("ran — ① from post_master, ④ from tracks/events/samples, ②③⑤ by human watch")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    parser.add_argument("--master", type=int, required=True)
    parser.add_argument("--master-props", default="NAME,SPEED,BPM,VALUE,NORMEDVALUE")
    parser.add_argument("--rehearse", action="store_true")
    parser.add_argument("--approve", default=None)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    props = args.master_props.split(",")
    skipped: list[str] = []
    if args.rehearse:
        from server.safety.backup import BackupManager

        console = FakeConsole()
        approval = RecordingApproval([cmds for _, cmds in build(args.master)])
        gate = SafetyGate(
            console=console,
            audit=AuditLog(out / "audit"),
            ruleset=load_ruleset(),
            approval_port=approval,
            backup=BackupManager(
                backup_action=lambda: skipped.append("SaveShow skipped (rehearsal)")
            ),
        )
        result = run(gate, out, args.master, props, deny_all=False, pace=False)
        result["fake_sent"] = console.sent
    else:
        from server.safety.bootstrap import build_console_stack
        from server.tools.probe_preflight import preflight

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
            result = run(stack.gate, out, args.master, props, deny_all=pinned is None, pace=True)
            result["preflight"] = health.get("verdict")
        finally:
            stack.stop()
    result["approval_requests"] = approval.requests
    result["skipped_saveshow"] = skipped
    (out / "approvals.json").write_text(
        json.dumps(approval.requests, ensure_ascii=False, indent=2), "utf-8"
    )
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in ("fake_sent", "planned")},
            ensure_ascii=False,
            indent=2,
        )[:4000]
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
