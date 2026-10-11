"""t553 Part ② 추가 — MOVER-U(Group 11) 기운 기준 Pan 물결 재시험.

리드 지시(2026-10-11, 추가 배차): Part ①(측정된 무빙 허용목록)은 그대로
둔다 — MOVER-D(group 12) Tilt wave bar 7·22는 열리고, MOVER-U(group 11)
Pan 단독 bar 11·18은 그대로 막힌다. 이 프로브는 "MOVER-U도 기준이 기울면
Pan이 보이는가"를 t548 D2'(MOVER-D·Spiider에서 같은 질문)와 같은 형태로
**처음** 잰다 — 결과가 PASS여도 이 카드에서 게이트를 열지 않는다(리드가
직접 실행·판정한 뒤에만 별도 카드로 ``measured_movements.yaml``에 반영).

형태 출처: t538 ``mover_probe_v2.py``의 A0′ 기준 줄
(``"Attribute 'Tilt' At 45"``) — Robin MegaPointe(MOVER-U)에서 2단계
상대 페이저가 그 자리 중심으로 도는 걸 이미 확인한 기준이다(progress.md
"M1 후속" 표 "기준 위치" 행). 선택(Group)·BPM은 데이터에서 읽는다
(``default_beat_grid`` MOVER-U 트랙의 ``group_no``, ``love_attack_
beat_grid.json`` 박 시각 회귀 기울기 — t548 ``probe_moverd.py``와 같은
방식). 디머 속성은 t538 실측대로 ``Dimmer`` 하나뿐이다(Robin MegaPointe
Mode 1, 디머 1개 — Spiider의 Dimmer+Dimmer2 둘과 다르다, 이 리터럴은
리그 전용 상수라 앱 코드가 아니라 이 프로브 스크립트에만 산다).

기울었는지 아는 법: 첫 묶음 ``t0_tilted_lit``(프로그래머만, Store 0)이
같은 기준으로 켜기만 한다 — 리드가 3D 캡처로 바닥 스폿이 수직 기준에서
옆으로 옮겨졌는지 본 뒤 본 묶음을 보낸다.

실행 (R=.moai/reports/t553):
  리허설:    uv run python $R/probe_moveru_pan_tilted.py $R/rehearse_u_pan --rehearse
  전부-거절: uv run python $R/probe_moveru_pan_tilted.py $R/denyall_u_pan
실기 전송은 리드 「실행」 뒤에만(--approve). 쇼 저장 0.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t531")
from m1_common import main_cli, seq_path  # noqa: E402

from server.design.beat_grid import LOVE_ATTACK_TITLE, default_beat_grid  # noqa: E402

TRACK = "MOVER-U"
SIZE = 30  # t538 A0′~A5b 와 같은 크기(크기 효과는 A2 에서 따로 쟀다)
CURVE = [
    "Step 1 At Accel -100",
    "Step 1 At Decel -100",
    "Step 2 At Accel -100",
    "Step 2 At Decel -100",
]
#: t538 mover_probe_v2.py A0′ 실측 기준 줄(각도 값 — 장비·그룹·프리셋 번호가 아니다).
TILTED_BASE = "Attribute 'Tilt' At 45"
#: 시험 시퀀스 번호(실기 읽기로 비어 있음 확인, t548 이 쓴 331~335 바로 다음).
SEQ_NO = 336


def _track() -> dict:
    grid = default_beat_grid(LOVE_ATTACK_TITLE)
    return next(t for t in grid["tracks"] if t["group_name"] == TRACK)


def song_bpm() -> float:
    """박 시각 회귀 기울기 — t548 probe_moverd.py 와 같은 방식(픽스처의
    ``bpm`` 필드는 hop 512 격자에 묶인 값이라 쓰지 않는다, t536 실측)."""
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


def speed(beats_per_cycle: float) -> str:
    value = song_bpm() / beats_per_cycle
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _head(sel: str) -> list[str]:
    return [
        "ChangeDestination Root",
        "ClearAll",
        f"{sel} ; Attribute 'Dimmer' At 70",  # MegaPointe 디머 1개(t538 실측) — Dimmer2 줄 없음
        f"{sel} ; {TILTED_BASE}",
    ]


def build_plan() -> list[tuple[str, list[str]]]:
    sel = selection()
    name = "'T553 - MOVERU pan wave 2 beats tilted base'"
    body = [
        *_head(sel),
        f"{sel} ; Attribute 'Pan' At Relative -{SIZE}",
        "Step 2",
        f"Attribute 'Pan' At Relative {SIZE}",
        *CURVE,
        "Attribute 'Pan' At Phase 0 Thru 360",
        f"Attribute 'Pan' At Speed {speed(2)}",
    ]
    return [
        ("t0_tilted_lit", _head(sel)),
        ("t0_clear", ["ClearAll"]),
        (
            "store_U_pan",
            [
                *body,
                f"Store Sequence {SEQ_NO} Cue 1 {name}",
                "ClearAll",
                f"Set Sequence {SEQ_NO} Property 'Name' {name}",
            ],
        ),
        ("play_U_pan", [f"Goto Cue 1 Sequence {SEQ_NO}"]),
        ("off_U_pan", [f"Off Sequence {SEQ_NO}"]),
        ("final_clear", ["ClearAll"]),
    ]


if __name__ == "__main__":
    sys.exit(
        main_cli(
            item="T553UPan",
            risk_reason=(
                "t553 Part② 추가 — MOVER-U 기운 기준 Pan 물결 재시험, "
                "시험 시퀀스 336(새), 쇼 저장 0"
            ),
            build_plan=build_plan,
            free_slots=[seq_path(SEQ_NO)],
            extra_notes=[
                f"선택 {selection()} · 기준 {TILTED_BASE}(t538 A0′, mover_probe_v2.py) · "
                f"BPM {song_bpm():.3f}(박 시각 회귀) → Speed {speed(2)}",
                "t0 는 프로그래머만(Store 0) — 기울었는지 리드 캡처로 확인 뒤 본 묶음 전송",
                "이 프로브는 측정만 한다 — PASS여도 measured_movements.yaml 반영"
                "(게이트 오픈)은 별도 카드(리드 지시, bar 18 을 지금 열지 않는다)",
            ],
        )
    )
