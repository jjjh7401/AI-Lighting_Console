# ruff: noqa: E501 — 근거(파일·줄 수)를 그대로 싣는 한국어 머리말이라 줄 길이 규칙을 끈다
"""t516 리듬 능력 프로브 v2 — v1 이 실기에서 조명을 하나도 켜지 못한 원인을 가르고, 같은 항목을 다시 잰다.

v1 다시 보기 결과(감독 관찰, 2026-10-06): 조명 0. 시퀀스 219(앱 연출)는 켜진다 → 출력·화면 정상, 원인은
우리 큐 내용(판정서 §4-3). v2 가 바꾸는 것(근거는 `line_shapes.txt` · `v2_patch_readonly.txt`):

  ① BACK 저장 모양 A/B/C 를 각각 따로 시퀀스로 — 어느 모양이 켜지는지 가른다(트래킹 섞임 없음)
     A(223) v1 모양: `Group 4` 한 줄 + `Attribute 'Dimmer' At 30` 다음 줄
     B(224) 앱 모양 1: `Group 4 ; Attribute 'Dimmer' At 30` 한 줄 (t513 219 파일 110줄 · t498 14줄)
     C(225) 앱 모양 2: `Fixture 201 + … + 212 ; Attribute 'Dimmer' At 30` 한 줄 (219 33줄 · t498 37줄)
     BACK = 201~212 는 오늘 실기 패치 판독(`Patch/Stages/1/Fixtures` 86대, 이름 `BACK 201`~`BACK 212`)
  ② 나머지 큐(박자 226 · 모양 227 · 겹침 장면=225)는 C 모양(Fixture 번호 목록 ; 값 한 줄)으로 저장한다
     무빙 = MOVER-U 501~508 + MOVER-D 521~528, ODD/EVEN 은 그 16대의 홀·짝 순번(그룹 17/18 대신)
  ③ 무빙 모양 큐에 `Attribute 'Dimmer' At 70` 을 같이 준다(v1 222 는 Dimmer 0줄 — 어두운 채 움직였을 것)
  ④ 큐 이름에 점을 쓰지 않는다(v1 'Measure 0.5' → 'Measure 05' 로 저장됨) — 'Measure Half'
  이름 규칙 'RHYTHM PROBE v2 - <항목>'. 새 번호만(223~227 · TC21) — v1 의 220~222·TC20 은 손대지 않는다.

모드·안전 장치는 v1 과 같다(빈 번호 재확인 · 트랙 NO 되읽기 · 묶음 전체 승인 대상 · SaveShow 기록만).
실행: uv run python .moai/reports/t516/rhythm_probe_v2.py <출력폴더> --master 15
      [--rehearse | --approve <전부-거절 폴더>]
🔴 --approve 는 리드의 「실행」 메시지 뒤에만.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t506")
sys.path.insert(0, ".moai/reports/t516")
import tc_probe  # noqa: E402
from rhythm_probe import _children, _value  # noqa: E402
from tc_probe import LISTEN_PORT, Probe, RecordingApproval  # noqa: E402

from server.safety.audit import AuditLog  # noqa: E402
from server.safety.console import ExecOutcome, LinkTimeouts, StateQueryError  # noqa: E402
from server.safety.gate import BatchRisk, SafetyGate  # noqa: E402
from server.safety.ruleset import load_ruleset  # noqa: E402

BPM = "112.35"
S_A, S_B, S_C, S_BEAT, S_SHAPE, TC_NO = 223, 224, 225, 226, 227, 21
S_SCENE = S_C  # 겹침(⑤) 장면 = C 모양 BACK 30%
BACK = list(range(201, 213))
MOVERS = [*range(501, 509), *range(521, 529)]
ODD, EVEN = MOVERS[0::2], MOVERS[1::2]
POOL = "ShowData/DataPools/Default"
TC = f"{POOL}/Timecodes/{TC_NO}"
SEQ = {n: f"{POOL}/Sequences/{n}" for n in (S_A, S_B, S_C, S_BEAT, S_SHAPE)}
HOLD, GAP, SAMPLE_SECONDS = 8.0, 2.0, 6.0

tc_probe.RISK = BatchRisk(
    reason="t516 v2 — 빈 번호 223~227·TC21 생성, 마스터 BPM, 재생", kind="t516_probe_v2"
)


def name(item: str) -> str:
    return f"'RHYTHM PROBE v2 - {item}'"


def fx(ids: list[int]) -> str:
    return "Fixture " + " + ".join(str(i) for i in ids)


def store(seq: int, cue: int, label: str) -> list[str]:
    return [f"Store Sequence {seq} Cue {cue} '{label}'", "ClearAll"]


def build(master: int, tracks: tuple[int, int] = (1, 2)) -> list[tuple[str, list[str]]]:
    sm = f"SpeedMaster {master}"
    head = ["ChangeDestination Root", "ClearAll"]
    beat = list(head)
    for cue, measure, label in (
        (1, "1", "Measure 1"),
        (2, "2", "Measure 2"),
        (3, "0.5", "Measure Half"),
    ):
        beat += [
            f"{fx(BACK)} ; Attribute 'Dimmer' At 0",
            "Step 2",
            "Attribute 'Dimmer' At 100",
            f"Attribute 'Dimmer' At Measure {measure}",
            f"Attribute 'Dimmer' At {sm}",
            *store(S_BEAT, cue, label),
        ]
    beat.append(f"Set Sequence {S_BEAT} Property 'Name' {name('SPEEDMASTER MEASURE')}")
    rel = "Attribute 'Pan' At Relative 12"
    lit = " ; Attribute 'Dimmer' At 70"
    shape = list(head) + [
        f"{fx(MOVERS)}{lit}",
        rel,
        "Attribute 'Pan' At Phase 0 Thru 360",
        "Attribute 'Pan' At Measure 2",
        f"Attribute 'Pan' At {sm}",
        *store(S_SHAPE, 1, "Pan Wave"),
        f"{fx(ODD)}{lit}",
        rel,
        "Attribute 'Pan' At Phase 0",
        f"{fx(EVEN)}{lit}",
        rel,
        "Attribute 'Pan' At Phase 180",
        f"{fx(MOVERS)} ; Attribute 'Pan' At Measure 1",
        f"Attribute 'Pan' At {sm}",
        *store(S_SHAPE, 2, "Crossed Pan Wave"),
    ]
    for cue, measure in ((3, "4"), (4, "2"), (5, "1")):
        shape += [
            f"{fx(MOVERS)}{lit}",
            rel,
            "Attribute 'Pan' At Phase 0",
            f"Attribute 'Pan' At Measure {measure}",
            f"Attribute 'Pan' At {sm}",
            *store(S_SHAPE, cue, f"Sweep M{measure}"),
        ]
    shape.append(f"Set Sequence {S_SHAPE} Property 'Name' {name('NEW SHAPES')}")
    n1, n2 = tracks
    return [
        ("bpm", [f"Master 3.{master} At BPM {BPM}"]),
        (
            "seq_a",
            [
                *head,
                "Group 4",
                "Attribute 'Dimmer' At 30",
                *store(S_A, 1, "A Group Two Line"),
                f"Set Sequence {S_A} Property 'Name' {name('A GROUP TWO LINE')}",
            ],
        ),
        (
            "seq_b",
            [
                *head,
                "Group 4 ; Attribute 'Dimmer' At 30",
                *store(S_B, 1, "B Group One Line"),
                f"Set Sequence {S_B} Property 'Name' {name('B GROUP ONE LINE')}",
            ],
        ),
        (
            "seq_c",
            [
                *head,
                f"{fx(BACK)} ; Attribute 'Dimmer' At 30",
                *store(S_C, 1, "C Fixture List"),
                f"Set Sequence {S_C} Property 'Name' {name('C FIXTURE LIST')}",
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
        ("tc_b", [f"Store Type 'CmdSubTrack' Timecode {TC_NO}.1.{n}.1" for n in (n1, n2)]),
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
        *[
            item
            for seq, tag in ((S_A, "a"), (S_B, "b"), (S_C, "c"))
            for item in (
                (f"ab_{tag}", [f"Goto Cue 1 Sequence {seq}"]),
                (f"ab_{tag}_off", [f"Off Sequence {seq}"]),
            )
        ],
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
        self.tracks: list[int] = []
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
        depth = path.count("/")
        if path == f"{TC}/1":
            kids = [("MarkerTrack", 1)] + [("Track", i + 2) for i in range(len(self.tracks))]
        elif path.startswith(f"{TC}/1/") and depth == 6:
            kids = [("TimeRange", 1)]
        elif path.startswith(f"{TC}/1/") and depth == 7:
            no = int(path.split("/")[6]) - 1
            kids = [("CmdSubTrack", 1)] if no in self.subs else []
        elif path.startswith(f"{TC}/1/") and depth == 8:
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

WATCH = {
    "ab_a": "A — 223 BACK 30% (v1 두 줄 모양): 켜지는가",
    "ab_b": "B — 224 BACK 30% (Group 4 ; 한 줄): 켜지는가",
    "ab_c": "C — 225 BACK 30% (Fixture 201~212 ; 한 줄): 켜지는가",
    "play": "⑤ 타임코드 21: 1초 BACK 30%, 2초부터 BACK 1박 깜빡임",
    "beat_off": "⑤ 깜빡임 끄면 BACK 30% 로 돌아오는가",
    "measure_1": "② Measure 1 — 1박에 한 번(8초 약 15번)",
    "measure_2": "② Measure 2 — 2박에 한 번(약 7번)",
    "measure_3": "② Measure 0.5 — 반 박에 한 번(약 30번)",
    "shape_1": "③ 팬 웨이브(무빙 70%) — 줄지어 따라가는 파도, 2박",
    "shape_2": "③ 엇갈린 팬 웨이브 — 홀·짝 반대, 1박",
    "shape_3": "③ 가속 스윕 4박",
    "shape_4": "③ 가속 스윕 2박",
    "shape_5": "③ 가속 스윕 1박",
}
HOLDS = {
    **{k: HOLD for k in ("ab_a", "ab_b", "ab_c")},
    **{f"ab_{t}_off": GAP for t in "abc"},
    "beat_off": 4.0,
    "tc_off": GAP,
    **{f"measure_{c}": HOLD + GAP for c in (1, 2, 3)},
    "measure_off": GAP,
    **{f"shape_{c}": HOLD + GAP for c in (1, 2, 3, 4, 5)},
}


def run(
    gate: SafetyGate, out: Path, master: int, props: list[str], *, deny_all: bool, pace: bool
) -> dict:
    probe = Probe(gate, out)
    master_path = f"ShowData/Masters/3/{master}"
    result: dict = dict(master=master, slots=[*SEQ, f"TC{TC_NO}"], bundles={})

    def stop(reason: str) -> dict:
        result["verdict"] = reason
        with (out / "steps.jsonl").open("w", encoding="utf-8") as handle:
            for row in probe.log:
                handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        return result

    taken = [p for p in [*SEQ.values(), TC] if probe.read_state("pre_slot", p) is not None]
    result["pre_master"] = probe.read_props("pre_master", master_path, props)
    if taken:
        return stop(f"stopped: slots not empty {taken}")
    plan = build(master)
    result["planned"] = {label: cmds for label, cmds in plan}
    if deny_all:
        for label, cmds in plan:
            result["bundles"][label] = probe.fire(label, cmds)
        return stop("deny-all: approval texts recorded, nothing written")

    def fire(label: str, cmds: list[str]) -> bool:
        if label in WATCH:
            probe.note("watch", say=WATCH[label])
        result["bundles"][label] = ok = probe.fire(label, cmds)
        if pace and label in HOLDS:
            time.sleep(HOLDS[label])
        return ok

    by = dict(plan)
    if fire("bpm", by["bpm"]):
        result["post_master"] = probe.read_props("post_master", master_path, props)
    for label in ("seq_a", "seq_b", "seq_c", "seq_beat", "seq_shape"):
        if not fire(label, by[label]):
            return stop(f"{label} not executed")
    for n, p in SEQ.items():
        probe.read_props(f"post_seq_{n}", p, ["NAME"])
        probe.read_props(f"post_part_{n}", f"{p}/3/1", ["NAME", "MEMORYFOOTPRINT"])
    if not fire("tc_a", by["tc_a"]):
        return stop("tc_a not executed")
    tracks = []
    for child in _children(probe.read_state("post_a_group", f"{TC}/1")):
        if child.get("class") == "Track":
            p = probe.read_props("post_a_track", f"{TC}/1/{child['i']}", ["NO", "TARGET"])
            tracks.append(dict(i=child["i"], no=_value(p, "NO"), target=_value(p, "TARGET")))
    result["tracks"] = tracks
    by_target = {t["target"]: t for t in tracks}
    if set(by_target) != {f"Sequence {S_SCENE}", f"Sequence {S_BEAT}"} or len(tracks) != 2:
        return stop(f"stopped after tc_a: tracks {tracks}")
    nos = tuple(int(float(by_target[f"Sequence {s}"]["no"])) for s in (S_SCENE, S_BEAT))
    live = dict(build(master, nos))
    if not fire("tc_b", live["tc_b"]):
        return stop("tc_b not executed")
    subs = {}
    for s in (S_SCENE, S_BEAT):
        rng = f"{TC}/1/{by_target[f'Sequence {s}']['i']}/1"
        subs[s] = [k.get("class") for k in _children(probe.read_state(f"post_b_{s}", rng))]
    result["post_b"] = subs
    if any(v != ["CmdSubTrack"] for v in subs.values()):
        return stop(f"stopped before cd: {subs}")
    fire("tc_c", live["tc_c"])
    for s in (S_SCENE, S_BEAT):
        sp = f"{TC}/1/{by_target[f'Sequence {s}']['i']}/1/1"
        result.setdefault("events", {})[s] = len(_children(probe.read_state(f"post_c_{s}", sp)))
    if result["events"] != {S_SCENE: 1, S_BEAT: 1}:
        return stop(f"stopped before playback: events {result['events']}")

    for tag in "abc":
        fire(f"ab_{tag}", by[f"ab_{tag}"])
        fire(f"ab_{tag}_off", by[f"ab_{tag}_off"])
    if fire("play", by["play"]):
        samples, start = [], time.monotonic()
        while time.monotonic() - start < SAMPLE_SECONDS:
            row = dict(t=round(time.monotonic() - start, 2))
            for s in (S_SCENE, S_BEAT):
                row[s] = _value(probe.read_props("sample", SEQ[s], ["CURRENTCUE"]), "CURRENTCUE")
            row["cursor"] = _value(probe.read_props("sample_tc", TC, ["CURSOR"]), "CURSOR")
            samples.append(row)
            time.sleep(0.2)
        result["samples"] = samples
    for label in (
        "beat_off",
        "tc_off",
        "measure_1",
        "measure_2",
        "measure_3",
        "measure_off",
        "shape_1",
        "shape_2",
        "shape_3",
        "shape_4",
        "shape_5",
        "shape_off",
    ):
        fire(label, by[label])
    return stop("ran — A/B/C ②③⑤ by director watch, ④ by samples")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    parser.add_argument("--master", type=int, required=True)
    parser.add_argument("--master-props", default="NAME,NORMEDVALUE,SPEEDSCALE")
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
            requests = json.loads((Path(args.approve) / "approvals.json").read_text("utf-8"))
            pinned = [r["commands"] for r in requests]
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
    keep = ("verdict", "bundles", "tracks", "post_b", "events", "pre_master", "post_master")
    print(json.dumps({k: result.get(k) for k in keep}, ensure_ascii=False)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
