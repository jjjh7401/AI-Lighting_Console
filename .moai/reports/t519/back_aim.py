# ruff: noqa: E501 — 근거(판독값·인용)를 그대로 싣는 한국어 머리말이라 줄 길이 규칙을 끈다
"""t519 BACK 역광 각도 후보 — 201 한 대를 객석 쪽으로 숙인 정적 큐 3개.

감독 원문(리드 경유, 2026-10-07): 「이전에도 켜졌어. 다만 역광방향으로 비춰지지 않았다는거야」 → 결정 A(객석 쪽으로 기울이기).

판독(읽기 전용, `.moai/reports/t519/r13_pantilt_range.txt`, t516 `diag7_patch.txt`):
- 객석 = −Y: FOH 111~118 Y −6.5, KEY 101~106 Y −9.0, BACK 201~212 Y +4.5 · 높이 6.2, 패치 회전 0.
- 유형 8(Mac Aura XB) Extended: Pan 물리 270 → −270, Tilt −116 → 116, 기본값 둘 다 가운데(0).
방향 모델(`.claude/skills/ma3-spatial-pointing` §1, 2026-08-13 다른 리그 실측):
Pan 0/Tilt 0 = 수직 아래, Tilt + = +Y(무대 뒤), Pan 180 = 객석 방향(FAN 기본 base).
→ Pan 180 + Tilt t 는 빔을 −Y 로 숙인다. 바닥 착지 Y = 4.5 − 6.2·tan t
   t=30 → Y 0.9(무대 가운데) · t=45 → Y −1.7(무대 앞쪽) · t=60 → Y −6.2(객석, FOH 줄).
🔴 이 모델을 Aura XB 에서 잰 적은 없다. 빔이 무대 뒤(+Y)로 가면 부호가 반대다 — 다음 판은 Pan 0 으로 바꾼다.

201 줄은 v5 248 과 같은 꼴에 Pan/Tilt 만 더한다(Dimmer 100, 201·201.1 각각). 이름 'BACK AIM PROBE - <단계>'.
쓰는 번호 260~262 만(t520 은 250~252). 사전 판독으로 세 번호가 비어 있지 않으면 멈춘다. 쇼 저장 없음.
재생: 각 8초 켜고 끈 뒤 2초.
실행: uv run python .moai/reports/t519/back_aim.py <출력폴더> [--rehearse | --approve <전부-거절 폴더>]
🔴 --approve 는 리드의 「실행」 메시지 뒤에만.
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t506")
sys.path.insert(0, ".moai/reports/t516")
import rhythm_probe_v5 as v5  # noqa: E402
import tc_probe  # noqa: E402
from rhythm_probe_v3 import GAP, HOLD  # noqa: E402

from server.safety.gate import BatchRisk  # noqa: E402

TILTS = (30, 45, 60)
SEQS = (260, 261, 262)


def _name(item: str) -> str:
    return f"'BACK AIM PROBE - {item}'"


def _levels() -> list[tuple[int, str, list[str], bool]]:
    out = []
    for seq, tilt in zip(SEQS, TILTS, strict=True):
        lines = [
            f"Fixture 201 ; Attribute 'Dimmer' At 100 ; Attribute 'Pan' At 180 ; Attribute 'Tilt' At {tilt}",
            "Fixture 201.1 ; Attribute 'Dimmer' At 100",
        ]
        out.append((seq, f"PAN 180 TILT {tilt}", lines, False))
    return out


def _playback() -> list[tuple[str, list[str], float, str]]:
    out = []
    for seq, tilt in zip(SEQS, TILTS, strict=True):
        land = {30: "무대 가운데", 45: "무대 앞쪽", 60: "객석"}[tilt]
        out.append(
            (
                f"on_{seq}",
                [f"Goto Cue 1 Sequence {seq}"],
                HOLD,
                f"{seq} — 201 이 객석 쪽으로 숙었나(Tilt {tilt}, 계산상 {land}에 떨어짐)",
            )
        )
        out.append((f"off_{seq}", [f"Off Sequence {seq}"], GAP, ""))
    return out


tc_probe.RISK = BatchRisk(
    reason="t519 BACK 역광 각도 — 빈 번호 260~262 생성·재생", kind="t519_back_aim"
)
v5.tc_probe.RISK = tc_probe.RISK
v5.name = _name
v5.LEVELS = _levels()
v5.PLAYBACK = _playback()

if __name__ == "__main__":
    sys.exit(v5.main())
