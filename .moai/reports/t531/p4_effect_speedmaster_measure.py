"""P4 (리드 리뷰 수정판) — 프리셋이 SpeedMaster 15 + Measure 바인딩을 갖는가.

리드 리뷰(2026-10-10) 세 항목 중 1번 수정: 원판은 t516 을 다시 재는 페이저-in-큐
대체물이었다 — 항목 ④가 묻는 "이펙트 프리셋"을 전혀 답하지 않았다. 이펙트 프리셋을
Store 하는 형태는 이 리포에 실측 전례가 있다:

    `.moai/reports/t513/run6_A1/rebuilt_sent.txt:20-34`
        Group 1
        Attribute 'ColorRGB_R' At 100 ; ... ; Attribute 'Dimmer' At 100
        Step 2
        Attribute 'ColorRGB_R' At 100 ; ... ; Attribute 'Dimmer' At 0
        Step 1 At Accel 0 / Step 1 At Decel 0 / Step 2 At Accel 0 / Step 2 At Decel 0
        Attribute 'ColorRGB_R' At Phase 0 / ... / Attribute 'Dimmer' At Phase 270
        Attribute 'ColorRGB_R' At Speed 30 ; ... ; Attribute 'Dimmer' At Speed 30
        Store Preset 21.7 'Finale Slam' /Universal
        Label Preset 21.7 'Finale Slam'
        ClearAll

이 프로브는 그 형태를 그대로 쓰되, 디머 한 속성만(색은 빼고) 두 단계로 두고,
타이밍 줄만 리드 지시대로 t513 의 고정 ``At Speed 30`` 대신 ``At Measure 1`` +
``At SpeedMaster 15`` 로 바꾼다(그 묶음 자체는 t516 rhythm_probe.py ``phaser_cue``
의 타이밍 줄과 동일 문법). ``ChangeDestination Root``/``ClearAll`` 은 두 전례
모두 번들 사이에 그대로 쓰는 형태 그대로 가져왔다(새로 발명하지 않음).

새 번호: 프리셋 21.301(새) · 시퀀스 301(새, 큐 1 이 그 프리셋을 recall).
프리셋 recall 문법은 t513 이 실측한 건 **Fixture 선택**(`<fixture 목록> ; At
Preset 4.9`, `rebuilt_sent.txt` 전역) 뿐이다 — Group 선택으로 큐에 recall 하는
형태는 t513/t520 어디에도 전례가 없다. 그래서 이 프로브는 "선택 뒤 바로 `At
Preset 21.301`"(Attribute 접두 없이, 선택 형태만 Fixture→Group 으로 바꿈)을
쓰되 이 대체를 🔴 미측정으로 명시한다 — "프리셋이 SpeedMaster+Measure 를
갖는가"는 recall 에 선행하는 Store 단계에서 이미 답이 나므로, recall 자체가
막혀도 ④의 핵심 질문엔 영향이 없다.

🔴 마스터 보호(리드 지시, 절대 준수): 이 프로브는 Master 3.15 를 **절대 쓰지
않는다**. 재생 전에 ``NORMEDVALUE`` 를 한 번 읽고, t520 이 기록한 값(69,
`verdict.md:24,107`)과 다르면 **아무것도 보내지 않고 멈춘다**. 전역 마스터를
다시 쓰는 줄은 "새 번호만" 규칙 밖이라 이 파일에 존재하지 않는다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, ".moai/reports/t531")
from m1_common import (  # noqa: E402
    MASTER_15_EXPECTED_NORMEDVALUE,
    MASTER_15_PATH,
    GenericFakeConsole,
    Probe,
    RecordingApproval,
    check_free,
    preset_path,
    preset_pool_path,
    seq_path,
)

sys.path.insert(0, ".moai/reports/t506")
import tc_probe  # noqa: E402

from server.safety.audit import AuditLog  # noqa: E402
from server.safety.gate import BatchRisk, SafetyGate  # noqa: E402
from server.safety.ruleset import load_ruleset  # noqa: E402

PRESET_POOL = 21
PRESET_NO = 301
SEQ_NO = 301
# t531 v2: 감독 눈에 보였던 그룹(Group 11 MOVER-U, t516 verdict.md:264)으로 교체
# Group 4 BACK 은 t516 에서 안 보였다(:134-138, :219-220)
GROUP_BACK = 11
PRESET_NAME = "LDBEAT M1 - P4 SM15 MEASURE"

# 🔴 미확인 — 어느 속성 이름이 실제로 존재하는지는 live 에서 introspect 가 답한다.
# SPEED/MEASURE/SPEEDMASTER 는 후보일 뿐, 이 리포에 프리셋 레벨 속성명 실측이 없다.
CANDIDATE_PRESET_PROPS = ["NAME", "SPEED", "MEASURE", "SPEEDMASTER", "NORMEDVALUE", "PRESETDATA"]


def build_store_preset() -> list[str]:
    # t513 rebuilt_sent.txt:20-34 의 두-단계 페이저 형태(색 생략, Dimmer 만) +
    # t516 phaser_cue 의 타이밍 줄(Measure/SpeedMaster) 로 교체.
    return [
        "ChangeDestination Root",
        "ClearAll",
        f"Group {GROUP_BACK}",
        "Attribute 'Dimmer' At 0",
        "Step 2",
        "Attribute 'Dimmer' At 100",
        "Attribute 'Dimmer' At Measure 1",
        "Attribute 'Dimmer' At SpeedMaster 15",
        f"Store Preset {PRESET_POOL}.{PRESET_NO} '{PRESET_NAME}' /Universal",
        f"Label Preset {PRESET_POOL}.{PRESET_NO} '{PRESET_NAME}'",
        "ClearAll",
    ]


def build_store_cue() -> list[str]:
    # 🔴 미측정 — recall 은 t513 이 Fixture 선택으로만 실측(`<fids> ; At Preset 4.9`).
    # 여기선 Group 선택으로 대체(선택 형태만 바뀜, "At Preset" 뒤 형태는 동일).
    return [
        "ChangeDestination Root",
        "ClearAll",
        f"Group {GROUP_BACK}",
        f"At Preset {PRESET_POOL}.{PRESET_NO}",
        f"Store Sequence {SEQ_NO} Cue 1 'LDBEAT M1 - P4 recall'",
        f"Set Sequence {SEQ_NO} Property 'Name' 'LDBEAT M1 - P4 recall SM15 measure'",
        "ClearAll",
    ]


PLAY = [f"Goto Cue 1 Sequence {SEQ_NO}"]
RELEASE = [f"Off Sequence {SEQ_NO}"]


def run(gate: SafetyGate, out: Path, *, deny_all: bool = False, hold: bool = False) -> dict:
    # deny_all: 묶음이 거절돼도 멈추지 않고 다음 묶음의 승인 요청까지 띄운다 —
    # 전부-거절 1회로 보낼 명령 전체의 승인 문면을 모으기 위해서다(쓰기는 0).
    probe = Probe(gate, out)
    result: dict = dict(item="P4", preset=f"{PRESET_POOL}.{PRESET_NO}", sequence=SEQ_NO)

    free_slots = [preset_path(PRESET_POOL, PRESET_NO), seq_path(SEQ_NO)]
    occupied = check_free(probe, "pre_free", free_slots)
    result["occupied_before"] = occupied
    if occupied:
        result["verdict"] = f"stopped: slots not free {occupied}"
        return finish(probe, result)

    master_read = probe.read_props("pre_master", MASTER_15_PATH, ["NORMEDVALUE"])
    observed = None
    for read in (master_read or {}).get("reads", []):
        if read.get("n") == "NORMEDVALUE" and read.get("ok"):
            observed = read.get("v")
    result["master_normedvalue_observed"] = observed
    result["master_normedvalue_expected"] = MASTER_15_EXPECTED_NORMEDVALUE
    if observed != MASTER_15_EXPECTED_NORMEDVALUE:
        result["verdict"] = (
            f"stopped: Master 3.15 NORMEDVALUE={observed!r}, 기대값 "
            f"{MASTER_15_EXPECTED_NORMEDVALUE!r}(t520) 과 달라 아무것도 보내지 않음"
        )
        return finish(probe, result)

    bundles: dict[str, bool] = {}
    bundles["store_preset"] = probe.fire("store_preset", build_store_preset())
    if not bundles["store_preset"] and not deny_all:
        result["bundles"] = bundles
        result["verdict"] = "stopped: store_preset not executed"
        return finish(probe, result)

    preset_path_str = preset_path(PRESET_POOL, PRESET_NO)
    probe.read_state("post_store_preset_pool", preset_pool_path(PRESET_POOL))
    try:
        fields = gate_introspect(probe, preset_path_str)
        result["preset_introspect_fields"] = fields
    except Exception as error:  # noqa: BLE001 — 사유를 그대로 싣는다
        result["preset_introspect_fields"] = dict(error=str(error))
    result["preset_props_candidates"] = probe.read_props(
        "post_store_preset_props", preset_path_str, CANDIDATE_PRESET_PROPS
    )

    bundles["store_cue"] = probe.fire("store_cue", build_store_cue())
    if not bundles["store_cue"] and not deny_all:
        result["bundles"] = bundles
        result["verdict"] = "stopped: store_cue not executed (recall 문법 거절 가능 — 🔴 미측정)"
        return finish(probe, result)

    bundles["play"] = probe.fire("play", PLAY)
    if hold:
        # 감독이 켜진 상태를 볼 수 있게 끄기 전에 멈춘다 — 끄기는 --release-only 로 따로.
        result["bundles"] = bundles
        result["verdict"] = "held — played, release not sent (감독 관찰 대기)"
        return finish(probe, result)
    bundles["release"] = probe.fire("release", RELEASE)
    result["bundles"] = bundles
    if deny_all:
        result["verdict"] = "deny-all: nothing written"
    else:
        result["verdict"] = "ok — preset stored+recalled; 재생 속도 비교는 감독 관찰(마스터 미변경)"
    return finish(probe, result)


def gate_introspect(probe: Probe, path: str) -> dict:
    payload = probe.port.enumerate_fields(path)
    probe.note("post_store_preset_introspect", kind="introspect", path=path, payload=payload)
    return payload


def finish(probe: Probe, result: dict) -> dict:
    out = probe.out
    out.mkdir(parents=True, exist_ok=True)
    with (out / "steps.jsonl").open("w", encoding="utf-8") as handle:
        for row in probe.log:
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    return result


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("out")
    parser.add_argument("--rehearse", action="store_true")
    parser.add_argument("--approve", default=None)
    parser.add_argument("--hold", action="store_true", help="재생 후 끄기 전에 멈춘다")
    parser.add_argument("--release-only", action="store_true", help="승인된 끄기 묶음만 보낸다")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    tc_probe.RISK = BatchRisk(
        reason="t531 M1 P4(수정판) — 프리셋 21.301(새), SpeedMaster15+Measure1, 마스터 미변경",
        kind="t531_m1_p4",
    )
    skipped: list[str] = []

    if not args.rehearse:
        return main_live(args, out, skipped)

    from server.safety.backup import BackupManager

    console = GenericFakeConsole()
    approval = RecordingApproval([build_store_preset(), build_store_cue(), PLAY, RELEASE])
    gate = SafetyGate(
        console=console,
        audit=AuditLog(out / "audit"),
        ruleset=load_ruleset(),
        approval_port=approval,
        backup=BackupManager(backup_action=lambda: skipped.append("SaveShow skipped (rehearsal)")),
    )
    result = run(gate, out)
    result["fake_sent"] = console.sent
    result["approval_requests"] = approval.requests
    result["skipped_saveshow"] = skipped
    (out / "approvals.json").write_text(
        json.dumps(approval.requests, ensure_ascii=False, indent=2), "utf-8"
    )
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
    print(
        json.dumps(
            {k: v for k, v in result.items() if k != "fake_sent"}, ensure_ascii=False, indent=2
        )[:6000]
    )
    return 0


def main_live(args, out: Path, skipped: list[str]) -> int:
    """실기 경로 — m1_common.main_cli 의 deny-all/--approve 와 같은 틀."""
    from m1_common import LISTEN_PORT, LinkTimeouts

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
        if args.release_only:
            probe = Probe(stack.gate, out)
            result = dict(item="P4", bundles=dict(release=probe.fire("release", RELEASE)))
            result["verdict"] = "release only"
            finish(probe, result)
        else:
            result = run(stack.gate, out, deny_all=(pinned is None), hold=args.hold)
        result["preflight"] = health.get("verdict")
    finally:
        stack.stop()
    result["approval_requests"] = approval.requests
    result["skipped_saveshow"] = skipped
    (out / "approvals.json").write_text(
        json.dumps(approval.requests, ensure_ascii=False, indent=2), "utf-8"
    )
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2)[:6000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
