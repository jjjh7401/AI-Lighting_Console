# ruff: noqa: E501 — 한국어 머리말·안내 문구라 줄 길이 규칙을 끈다
"""t520 M2 묶음 1 재생 — 쓰기 없음(`Go Timecode 22` · `Off …` 두 묶음).

- 사전 판독: 시퀀스 250·251 과 타임코드 22 의 이름이 m2a_batch1.py 가 붙인 이름과 같아야 보낸다.
- `--audio <mp3>`: `Go Timecode 22` 송신이 끝난 뒤 LEAD(3초)에 맞춰 이 Mac 에서 afplay 로 음원을 튼다.
  타임코드 0초 + 3초 = 음악 0초. 음원을 틀기 직전과 직후에 타임코드 CURSOR 를 읽어 어긋남을 기록한다.
  afplay 자체의 시작 지연은 안 잰 것이다.
- 재생 중 0.5초마다 타임코드 CURSOR 와 두 시퀀스 CURRENTCUE 를 읽는다(읽기만).
- 음악 25마디 끝(26마디 1박 55.08초) + 2초 뒤에 끈다.

실행: uv run python .moai/reports/t520/m2a_play.py <출력폴더> [--rehearse | --approve <전부-거절 폴더>] [--audio <mp3>]
🔴 --approve 는 리드의 「실행」 메시지 뒤에만. 감독이 콘솔·무대 화면 앞에 있어야 한다.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t506")
sys.path.insert(0, ".moai/reports/t520")
import m2a_batch1 as gen  # noqa: E402
import tc_probe  # noqa: E402
from m2a_batch1 import LEAD, S_RHY, S_SCENE, SEQ, TC, TC_NO, name  # noqa: E402
from tc_probe import LISTEN_PORT, Probe, RecordingApproval  # noqa: E402

from server.safety.audit import AuditLog  # noqa: E402
from server.safety.console import ExecOutcome, LinkTimeouts  # noqa: E402
from server.safety.gate import BatchRisk, SafetyGate  # noqa: E402
from server.safety.ruleset import load_ruleset  # noqa: E402

tc_probe.RISK = BatchRisk(
    reason="t520 M2 묶음 1 재생 — 타임코드 22 Go/Off(쓰기 없음)", kind="t520_m2a_play"
)
MUSIC_END = 55.08 + 2.0  # 26마디 1박 + 2초
NAMES = {
    SEQ[S_SCENE]: name("SCENE").strip("'"),
    SEQ[S_RHY]: name("RHYTHM").strip("'"),
    TC: name("TC").strip("'"),
}
BUNDLES = [
    ("go", [f"Go Timecode {TC_NO}"]),
    ("off", [f"Off Timecode {TC_NO}", f"Off Sequence {S_SCENE}", f"Off Sequence {S_RHY}"]),
]


def retarget() -> None:
    """gen.apply_target() 뒤 번호·이름·묶음을 다시 맞춘다(--target b 면 253·254·TC23)."""
    global S_SCENE, S_RHY, SEQ, TC, TC_NO, NAMES, BUNDLES
    S_SCENE, S_RHY, SEQ, TC, TC_NO = gen.S_SCENE, gen.S_RHY, gen.SEQ, gen.TC, gen.TC_NO
    NAMES = {
        SEQ[S_SCENE]: gen.name("SCENE").strip("'"),
        SEQ[S_RHY]: gen.name("RHYTHM").strip("'"),
        TC: gen.name("TC").strip("'"),
    }
    BUNDLES = [
        ("go", [f"Go Timecode {TC_NO}"]),
        ("off", [f"Off Timecode {TC_NO}", f"Off Sequence {S_SCENE}", f"Off Sequence {S_RHY}"]),
    ]
    tc_probe.RISK = BatchRisk(
        reason=f"t520 M2 묶음 1 재생 — 타임코드 {TC_NO} Go/Off(쓰기 없음)", kind="t520_m2a_play"
    )


class FakeConsole:
    responder_version = "fake"

    def __init__(self) -> None:
        self.sent: list[str] = []

    def ping(self) -> bool:
        return True

    def execute(self, command: str) -> ExecOutcome:
        self.sent.append(command)
        return ExecOutcome(status="ok", detail="OK")

    def query_state(self, path: str, offset: int = 0) -> dict:
        return dict(ok=True, path=path, node=dict(childCount=0), children=[], fake=True)

    def query_properties(self, path: str, names) -> dict:
        reads = [
            dict(n=n, ok=True, v=NAMES.get(path, "fake") if n == "NAME" else "fake") for n in names
        ]
        return dict(ok=True, path=path, reads=reads, fake=True)

    def query_property(self, path: str, name: str) -> dict:
        return self.query_properties(path, [name])

    def enumerate_fields(self, path: str, offset: int = 0) -> dict:
        return dict(ok=True, path=path, fields=[], fake=True)


def tc_seconds(text: str) -> float:
    """CURSOR 읽기값을 초로. 60초가 넘으면 `1m00.70` 꼴로 온다(t520 다시 보기 1회차에서 잰 것)."""
    text = str(text).strip()
    if "m" in text:
        minutes, seconds = text.split("m", 1)
        return int(minutes) * 60 + float(seconds)
    return float(text)


def _value(payload: dict | None, key: str):
    for read in (payload or {}).get("reads") or ():
        if read.get("n") == key and read.get("ok"):
            return read.get("v")
    return None


def run(
    gate: SafetyGate, out: Path, *, deny_all: bool, audio: str | None, off_only: bool = False
) -> dict:
    probe = Probe(gate, out)
    result: dict = dict(bundles={})

    def stop(reason: str) -> dict:
        result["verdict"] = reason
        with (out / "steps.jsonl").open("w", encoding="utf-8") as handle:
            for row in probe.log:
                handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        return result

    names = {p: _value(probe.read_props("pre_name", p, ["NAME"]), "NAME") for p in NAMES}
    result["pre_names"] = names
    if names != NAMES:
        return stop(f"stopped: names differ {names}")
    if off_only and not deny_all:
        # 앞 재생이 Off 전에 멈췄을 때 승인 문면의 Off 묶음만 보낸다(t520 다시 보기 1회차)
        result["bundles"]["off"] = probe.fire("off", dict(BUNDLES)["off"])
        return stop("off only")
    if deny_all:
        for label, cmds in BUNDLES:
            result["bundles"][label] = probe.fire(label, cmds)
        return stop("deny-all: approval texts recorded, nothing sent")

    by = dict(BUNDLES)
    probe.note("watch", say="LOVE ATTACK 0~25마디 — 타임코드 22 시작. 음악은 타임코드 3초에 시작")
    result["bundles"]["go"] = probe.fire("go", by["go"])
    if not result["bundles"]["go"]:
        return stop("go not executed")
    t_go = time.monotonic()
    player = None
    samples = []
    cursor = lambda label: _value(probe.read_props(label, TC, ["CURSOR"]), "CURSOR")  # noqa: E731
    if audio:
        # 음원 맞추기(B 판 결함 수정): 표본 루프 전에, 타임코드 0초의 이 Mac 시각을 CURSOR 로 추정해 LEAD 에 바로 띄운다.
        # 읽기 한 번의 왕복 중간 시각을 그 CURSOR 값의 시각으로 보고, 세 번 읽어 가운데 값을 쓴다.
        zeros = []
        for k in range(3):
            t0 = time.monotonic()
            c = cursor(f"audio_sync_{k}")
            t1 = time.monotonic()
            if c is not None:
                zeros.append((t0 + t1) / 2 - tc_seconds(c))
        tc_zero = sorted(zeros)[len(zeros) // 2] if zeros else t_go
        while time.monotonic() < tc_zero + LEAD:
            time.sleep(0.002)
        t_play = time.monotonic()
        player = subprocess.Popen(["afplay", audio])
        t_spawned = time.monotonic()
        after = cursor("audio_cursor_after")
        result["audio"] = dict(
            tc_zero_estimates=[round(z - t_go, 4) for z in zeros],
            spawned_tc_estimate=round(t_play - tc_zero, 3),
            popen_seconds=round(t_spawned - t_play, 4),
            cursor_after=after,
            target_tc=LEAD,
        )
    while (elapsed := time.monotonic() - t_go) < LEAD + MUSIC_END:
        row = dict(t=round(elapsed, 2), cursor=cursor("sample_tc"))
        for s in (S_SCENE, S_RHY):
            row[s] = _value(probe.read_props("sample_seq", SEQ[s], ["CURRENTCUE"]), "CURRENTCUE")
        samples.append(row)
        time.sleep(0.5)
    result["samples"] = samples
    result["bundles"]["off"] = probe.fire("off", by["off"])
    if player is not None:
        player.terminate()
    return stop("played — judge by director watch")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    parser.add_argument("--rehearse", action="store_true")
    parser.add_argument("--approve", default=None)
    parser.add_argument("--audio", default=None)
    parser.add_argument("--target", choices=("v2", "b", "b2"), default="v2")
    parser.add_argument("--off-only", action="store_true")
    args = parser.parse_args()
    if args.target == "b":
        gen.configure(253, 254, 23, "M2a B", "main_only", None)  # 재생은 번호·이름만 쓴다
    elif args.target == "b2":
        gen.configure(269, 270, 24, "M2a B2", "group", None)
    retarget()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    skipped: list[str] = []
    if args.rehearse:
        from server.safety.backup import BackupManager

        console = FakeConsole()
        approval = RecordingApproval([cmds for _, cmds in BUNDLES])
        gate = SafetyGate(
            console=console,
            audit=AuditLog(out / "audit"),
            ruleset=load_ruleset(),
            approval_port=approval,
            backup=BackupManager(
                backup_action=lambda: skipped.append("SaveShow skipped (rehearsal)")
            ),
        )
        global MUSIC_END
        MUSIC_END = 0.0  # 리허설은 기다리지 않는다
        result = run(gate, out, deny_all=False, audio=None)
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
            result = run(
                stack.gate, out, deny_all=pinned is None, audio=args.audio, off_only=args.off_only
            )
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
            {k: result.get(k) for k in ("verdict", "bundles", "pre_names", "audio")},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
