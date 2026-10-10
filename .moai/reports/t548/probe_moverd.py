"""t548 ③ — MOVER-D 2단계 무빙 실기 프로브(설계·리허설·전부-거절·승인 고정).

감독 결정 2026-10-11(리드 경유):
① 팬 흔들기 = position_fx 의 wave 에 축 매개변수 추가(새 모양 아님)
② 무빙 기준 위치 = 그 칸의 position_preset_no
③ run 전 MOVER-D 2단계 무빙 실기 프로브 — 시험 시퀀스만, 쇼 저장 0

형태는 t538 의 실측 정답(A3 기준 프리셋 + 2단계 상대값, A5b 곡선)을 그대로 쓴다.
t538 은 MegaPointe(MOVER-U)에서만 쟀다 — 이 프로브가 Spiider(MOVER-D)에서 같은 형태가
도는지 처음 잰다.

상수 금지(감독 원칙): 그룹 번호·기준 위치 프리셋 번호·BPM 은 전부 데이터에서 읽는다.
- 그룹 번호: `default_beat_grid("LOVE ATTACK")` 의 MOVER-D 트랙 `group_no`
- 기준 위치: 같은 트랙에서 `position_preset_no` 가 있는 큐(감독 승인 2026-10-10)
- BPM: `server/tests/fixtures/love_attack_beat_grid.json` 박 시각의 회귀 기울기
  (그 파일의 `bpm` 필드는 hop 512 격자에 묶인 값이라 쓰지 않는다 — t536 실측)
속도는 「한 바퀴 N박」을 BPM 으로 바꾼다: MA Speed 는 분당 바퀴 수이므로 BPM / N.

시퀀스 번호는 시험용 빈 번호대(아래 SEQ)만 쓰고, 전부-거절 때 콘솔에서 비어 있는지 읽는다.

실행 (R=.moai/reports/t548):
  리허설:    uv run python $R/probe_moverd.py $R/rehearse --rehearse
  전부-거절: uv run python $R/probe_moverd.py $R/denyall
실기 전송은 리드 「실행」 뒤에만(--approve).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t531")
from m1_common import main_cli, seq_path  # noqa: E402

from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid  # noqa: E402

TRACK = "MOVER-D"
BEATS_PER_BAR = 4
SIZE = 30  # 2단계 상대값 크기 — t538 A0′~A5b 와 같은 값(크기 효과는 A2 에서 따로 쟀다)
CURVE = [
    "Step 1 At Accel -100",
    "Step 1 At Decel -100",
    "Step 2 At Accel -100",
    "Step 2 At Decel -100",
]

#: 시험 시퀀스 번호(빈 번호대). 전부-거절 preflight 가 콘솔에서 비어 있는지 읽는다.
SEQ = {"D1": 331, "D2": 332, "D3": 333, "D4": 334}


def _track():
    grid = default_beat_grid(LOVE_ATTACK_TITLE)
    return next(t for t in grid["tracks"] if t["group_name"] == TRACK)


def song_bpm() -> float:
    data = json.loads(Path("server/tests/fixtures/love_attack_beat_grid.json").read_text())
    beats = [b / 1000.0 for b in data["beat_times_ms"]]
    n = len(beats)
    mean_i = (n - 1) / 2
    mean_t = sum(beats) / n
    slope = sum((i - mean_i) * (t - mean_t) for i, t in enumerate(beats)) / sum(
        (i - mean_i) ** 2 for i in range(n)
    )
    return 60.0 / slope


def selection() -> str:
    track = _track()
    if not track["group_no_confirmed"] or track["group_no"] is None:
        raise SystemExit(f"{TRACK} group_no 미확인 — 데이터에 없으면 보내지 않는다")
    return f"Group {track['group_no']}"


def base_preset() -> str:
    numbers = {c["position_preset_no"] for c in _track()["cues"] if c["position_preset_no"]}
    if len(numbers) != 1:
        raise SystemExit(f"{TRACK} 기준 위치 프리셋이 하나가 아니다: {sorted(numbers)}")
    return numbers.pop()


def speed(beats_per_cycle: float) -> str:
    value = song_bpm() / beats_per_cycle
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _name(item: str, text: str) -> str:
    # 점(.)은 MA3 가 이름에서 지운다 — 이름엔 점을 넣지 않는다.
    return f"'T548 - {item} {text}'"


def _store(item: str, text: str) -> list[str]:
    no = SEQ[item]
    return [
        f"Store Sequence {no} Cue 1 {_name(item, text)}",
        "ClearAll",
        f"Set Sequence {no} Property 'Name' {_name(item, text)}",
    ]


def _play(item: str) -> list[tuple[str, list[str]]]:
    no = SEQ[item]
    return [
        (f"play_{item}", [f"Goto Cue 1 Sequence {no}"]),
        (f"off_{item}", [f"Off Sequence {no}"]),
    ]


def _head(sel: str) -> list[str]:
    return [
        "ChangeDestination Root",
        "ClearAll",
        f"{sel} ; Attribute 'Dimmer' At 70",
        f"{sel} ; Attribute 'Dimmer2' At 70",
        f"{sel} ; At Preset {base_preset()}",
    ]


def _wave(sel: str, axis: str, beats_per_cycle: float) -> list[str]:
    return [
        *_head(sel),
        f"{sel} ; Attribute '{axis}' At Relative -{SIZE}",
        "Step 2",
        f"Attribute '{axis}' At Relative {SIZE}",
        *CURVE,
        f"Attribute '{axis}' At Phase 0 Thru 360",
        f"Attribute '{axis}' At Speed {speed(beats_per_cycle)}",
    ]


def _circle(sel: str, beats_per_cycle: float) -> list[str]:
    s = speed(beats_per_cycle)
    return [
        *_head(sel),
        f"{sel} ; Attribute 'Pan' At Relative -{SIZE}",
        f"{sel} ; Attribute 'Tilt' At Relative -{SIZE}",
        "Step 2",
        f"Attribute 'Pan' At Relative {SIZE}",
        f"Attribute 'Tilt' At Relative {SIZE}",
        *CURVE,
        "Attribute 'Pan' At Phase 0",
        "Attribute 'Tilt' At Phase 90",
        f"Attribute 'Pan' At Speed {s}",
        f"Attribute 'Tilt' At Speed {s}",
    ]


def build_plan() -> list[tuple[str, list[str]]]:
    sel = selection()
    head = _head(sel)
    plan: list[tuple[str, list[str]]] = [
        # V0 — 움직임 없이 켜지는지(Spiider 는 디머가 둘, t516 가설 미측정). 프로그래머만, Store 0.
        # v0a 는 Dimmer 줄만, v0b 는 Dimmer2 까지 — 어느 줄이 빛을 내는지 감독이 가른다.
        ("v0a_dimmer_only", [line for line in head if "'Dimmer2'" not in line]),
        ("v0a_clear", ["ClearAll"]),
        ("v0b_dimmer_and_dimmer2", head),
        ("v0b_clear", ["ClearAll"]),
    ]
    items = [
        # D1 — §4 MOVER-D 7 「틸트 웨이브, 한 바퀴 2마디, 위상 펼침」
        ("D1", "tilt wave 2 bars", _wave(sel, "Tilt", 2 * BEATS_PER_BAR)),
        # D2 — 결정 ① 팬 흔들기 = wave 에 축 Pan(§4 MOVER-U 18 「팬 웨이브 한 바퀴 2박」 형태)
        ("D2", "pan wave 2 beats", _wave(sel, "Pan", 2)),
        # D3 — §4 MOVER-D 22 「틸트 웨이브(한 바퀴 2박)」
        ("D3", "tilt wave 2 beats", _wave(sel, "Tilt", 2)),
        # D4 — t538 A5b 원(곡선) 이 Spiider 에서도 원인지
        ("D4", "pan tilt circle 2 beats", _circle(sel, 2)),
    ]
    for item, text, body in items:
        plan.append((f"store_{item}", [*body, *_store(item, text)]))
        plan += _play(item)
    return plan


if __name__ == "__main__":
    sys.exit(
        main_cli(
            item="T548",
            risk_reason="t548 MOVER-D 2단계 무빙 프로브 — 시험 시퀀스 331~334(새), 쇼 저장 0",
            build_plan=build_plan,
            free_slots=[seq_path(n) for n in SEQ.values()],
            extra_notes=[
                f"선택 {selection()} · 기준 위치 At Preset {base_preset()} · "
                f"BPM {song_bpm():.3f}(박 시각 회귀) — 전부 데이터에서 읽음",
                "v0 는 프로그래머만(Store 0), Dimmer2 줄은 t516 채널 표의 이름 — 미측정",
            ],
        )
    )
