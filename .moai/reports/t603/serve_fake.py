"""t603 사본(원본 t583/t599) — 콘솔 없이 앱 서버를 띄워 런북 박자 격자 화면을 헤드리스로 찍는
일회용 실행기. t599 에서 바뀐 것: 가짜 풀에 혼합 효과 풀(All 1, 22 — 앱이 찾는 이름 `beat_grid_presets._POOL_NAME_TO_EFFECT_KIND`)을 더했다.

제품 코드와 같은 `create_app` 에 시험과 같은 FakeConsole(쓰기 0 · 실기 포트 0)과
임시 폴더만 물린다. 사용자 앱 데이터 폴더(`~/Library/Application Support/...`)·
실기 콘솔·키체인은 건드리지 않는다.

데이터 출처(전부 이 저장소에 이미 있는 실측):
- 마디 지도: `.moai/reports/t509/evidence/love_attack_map_phase1.json`(LOVE ATTACK 실제 음원
  분석의 박 시각 · 못갖춘마디) → 제품 생산자 `build_bar_map_payload` 로 변환.
- 구간: `.moai/reports/t509/evidence/app_sections.json`(앱 경로 분석 10구간, BPM 112.35, d=에너지).
- 박자 격자: 제품 기본값 `attach_beat_grid_default` + `attach_beat_grid_runtime_extras`(세션이
  화면에 보내기 전 거치는 단계 그대로).
- 2D 무대: `.moai/reports/t534/stage_fixtures.json`(t525 가 실기 응답기로 읽은 60대 좌표,
  t525 §② 가 확인한 8대만 그룹 소속) — 콘솔 판독 대신 이 기록을 돌려준다.

실행: `uv run --with uvicorn python .moai/reports/t583/serve_fake.py 8798`
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from server.audio.bar_map_store import build_bar_map_payload  # noqa: E402
from server.design.beat_grid import (  # noqa: E402
    attach_beat_grid_default,
    attach_beat_grid_runtime_extras,
)
from server.safety.audit import AuditLog  # noqa: E402
from server.safety.gate import SafetyGate  # noqa: E402
from server.tests.test_runner_self_correction import ScriptedProvider  # noqa: E402
from server.tests.test_safety_gate import FakeConsole, ScriptedApproval  # noqa: E402
from server.web import session as session_module  # noqa: E402
from server.web.app import WebDeps, create_app  # noqa: E402
from server.web.approval_bridge import ApprovalChannel  # noqa: E402
from server.web.panel import PanelStore, PinStore  # noqa: E402
from server.web.timeline_library import SongTimelineLibrary  # noqa: E402

EVIDENCE = ROOT / ".moai" / "reports"


def _bar_map() -> dict:
    phase1 = json.loads((EVIDENCE / "t509/evidence/love_attack_map_phase1.json").read_text())
    # beats_s 는 못갖춘마디 박(pickup_beats_s)을 이미 맨 앞에 담고 있다 — 박 목록은
    # beats_s 하나, 못갖춘마디 길이만 pickup_beats_s 에서 센다.
    beats = [round(s * 1000) for s in phase1["beats_s"]]
    return build_bar_map_payload(
        beats,
        len(phase1["pickup_beats_s"]),
        bpm=float(phase1["app_path_bpm"]),
        time_signature=(4, 4),
    )


def _sections(bar_map: dict) -> list[dict]:
    measured = json.loads((EVIDENCE / "t509/evidence/app_sections.json").read_text())
    bar_starts = [(b["bar"], b["start_ms"]) for b in bar_map["bars"] if b["bar"] >= 1]
    out = []
    for s in measured["sections"]:
        # 구간 시작 시각 이전(±50ms)에 시작한 마지막 마디 — 없으면(곡 첫머리) 1마디.
        bar_start = max((bar for bar, ms in bar_starts if ms <= s["start_ms"] + 50), default=1)
        out.append(
            {
                "index": s["i"] + 1,
                "label": s["name"],
                "start_ms": s["start_ms"],
                "end_ms": s["end_ms"],
                "duration_ms": s["end_ms"] - s["start_ms"],
                "bar_start": bar_start,
                "d_level": s["d"],
                "role": s["role"],
                "accents": [],
                # 프로토콜(`ui/src/protocol.ts` SongTimelineSection) 필수 칸 — 실측에
                # 없는 연출 값은 「미정」으로 비운다(지어내지 않는다).
                "cue_number": s["i"] + 1,
                "palette": [],
                "position": "",
                "texture": "",
                "fx": [],
                "mib": False,
                "trig_time_seconds": None,
            }
        )
    for current, nxt in zip(out, out[1:] + [None], strict=True):
        end_bar = nxt["bar_start"] if nxt else max(b["bar"] for b in bar_map["bars"]) + 1
        current["bar_count"] = max(1, end_bar - current["bar_start"])
    return out


def _timeline() -> dict:
    bar_map = _bar_map()
    timeline = {
        "song_title": "LOVE ATTACK",
        "sequence_name": None,
        "sequence_number": 210,
        "timing_mode": "timecode",
        "timecode_number": 20,
        # 프로토콜(SongTimelineView) 필수 칸 — 설계·승인 이력이 없는 초안 상태로 비운다.
        "lifecycle": "draft",
        "approval": "pending",
        "director_decisions": [],
        "lint": [],
        "unresolved": [],
        "disabled": [],
        "readback": {"verified": None, "message": None},
        "bpm": bar_map["bpm"],
        "time_signature": "4/4",
        "seconds_per_bar": 4 * 60.0 / bar_map["bpm"],
        "bar_map": bar_map,
        "bar_count": max(b["bar"] for b in bar_map["bars"]),
        "sections": _sections(bar_map),
    }
    return attach_beat_grid_runtime_extras(attach_beat_grid_default(timeline))


def _fake_stage(*_args, track_names, **_kwargs) -> dict:
    fixtures = json.loads((EVIDENCE / "t534/stage_fixtures.json").read_text())
    groups = []
    unread = []
    for no, name in enumerate(track_names, start=1):
        fids = [f["fid"] for f in fixtures if f.get("confirmedGroupName") == name]
        if fids:
            groups.append(
                {"group_no": no, "group_name": name, "member_fids": fids, "complete": False}
            )
        else:
            unread.append(f"(t583 하네스) '{name}' 소속은 t525 기록에 없음 — 지어내지 않음")
    points = [{k: f[k] for k in ("fid", "name", "x", "y", "z")} for f in fixtures]
    return {"fixtures": points, "groups": groups, "unread": unread}


def main() -> None:
    def _pools(pools: dict[str, int]) -> dict:
        children = [{"i": no, "name": name} for name, no in pools.items()]
        return {"children": children, "node": {"childCount": len(children)}}

    def _slots(entries: dict[int, str | None]) -> dict:
        children = [{"i": slot, "name": name} for slot, name in entries.items()]
        return {"children": children, "node": {"childCount": len(children)}}

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8798
    # t585 — 전후 비교용: 둘째 인자로 빌드 폴더(ui/dist 또는 ui/dist-before)를 고른다.
    ui_dist = ROOT / "ui" / (sys.argv[2] if len(sys.argv) > 2 else "dist")
    tmp = Path(tempfile.mkdtemp(prefix="t583-"))
    session_module.read_beat_grid_stage = _fake_stage
    executed_log = Path(__file__).resolve().parent / f"console_executed_{port}.log"
    executed_log.write_text("")

    class _LoggingConsole(FakeConsole):
        """받은 쓰기 명령을 받는 즉시 파일에 남긴다 — 강제 종료돼도 「쓰기 0」이 증거로 남는다."""

        def execute(self, command: str):
            with executed_log.open("a") as handle:
                handle.write(command + "\n")
            return super().execute(command)

    console = _LoggingConsole(
        state_tree={
            "DataPool/Sequences": {"children": []},
            "DataPool/Timecodes": {"children": [], "node": {"childCount": 0, "enumeration": "ok"}},
            # t589 — 캡처 전용: 서랍이 풀을 읽어 편집 칸 드롭다운이 켜지도록 작은
            # 가짜 풀 셋(이름은 시안 예시 'LA …'를 흉내 낸 시험값, 실기 값 아님).
            # 위치 풀 2.61 은 이름 없는 점유 슬롯 — 빈 번호가 2.62 로 가야 한다.
            # t603 — 혼합 효과 풀(All 1, 22 — 앱이 찾는 이름 `beat_grid_presets._POOL_NAME_TO_EFFECT_KIND`)을 더했다. 22.5 만 점유(시험값).
            "DataPool/PresetPools": _pools({"Dimmer": 1, "Position": 2, "Color": 4, "All 1": 22}),
            "DataPool/PresetPools/1": _slots({1: "LA Full", 21: "LA Dim Pulse"}),
            "DataPool/PresetPools/2": _slots({41: "LA Center", 61: None}),
            "DataPool/PresetPools/4": _slots({21: "LA White", 41: "LA Color Chase"}),
            "DataPool/PresetPools/22": _slots({5: "LA Mixed Test"}),
        }
    )
    audit = AuditLog(tmp / "audit")
    channel = ApprovalChannel(timeout_seconds=5.0)
    gate = SafetyGate(console=console, audit=audit, approval_port=ScriptedApproval(decisions=()))
    deps = WebDeps(
        gate=gate,
        provider=ScriptedProvider([]),
        system_prefix="PREFIX",
        audit=audit,
        approval_channel=channel,
        timeline_library=SongTimelineLibrary(tmp / "library.json"),
        panel=PanelStore(pins=PinStore(tmp / "pins.json"), state_port=gate.state_port),
        rig_paths={"fixtures": "Patch/Stages/1/Fixtures", "groups": "DataPool/Groups"},
        ui_dist=ui_dist,
    )
    deps.song_timeline_store.latest = _timeline()
    print(f"[t583] tmp={tmp} executed-writes will be checked on exit", flush=True)
    try:
        uvicorn.run(create_app(deps), host="127.0.0.1", port=port, log_level="warning")
    finally:
        print(f"[t583] console.executed={console.executed!r}", flush=True)


if __name__ == "__main__":
    main()
