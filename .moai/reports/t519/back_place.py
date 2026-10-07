# ruff: noqa: E501 — 근거(경로·판독값)를 그대로 싣는 한국어 머리말이라 줄 길이 규칙을 끈다
"""t519 BACK 201 높이 시험 — 「높이(거리)가 원인인가」를 1대로 가른다.

판독(2026-10-07, 읽기 전용, `.moai/reports/t519/r2_diff.txt`·`r5_floor_poly.txt`·`r9_geom_walk.txt`):
- BACK 201(Fixtures/43)과 켜지는 SIDE-L 301(Fixtures/55)의 패치 속성 78개 중 다른 것은
  번호·이름·서브픽스처 색인·POSX/Y/Z 뿐이다(ROTX/Y/Z 0, VISIBLE3D, 반전, 오프셋, 모드, 유형 같음).
- 무대 바닥(StageElement 1)은 X·Y ±15 m, Z 0 — BACK 이 아래로 비추는 자리(Y 4.5)는 바닥 안이다.
- 유형 8 빔(Body#4 Main Module Beam): 밝기 10000, 필드 25°, Wash. 6.2 m 와 1.2 m 의 거리 제곱 비 ≈ 26.7.
따라서 남은 차이는 높이(6.2 vs 1.2)와 자리(Y 4.5 vs 3.0)다. 이 시험은 201 의 높이 하나만 1.2 m 로 바꾼다.

명령 꼴: `Set Fixture <fid> Posz '<v>'` — t516 바닥 워시 1b·2단계에서 실기로 쓴 꼴(작은따옴표 필수,
`.moai/reports/t516/verdict.md` §4-11·4-12, 401 POSZ 0.3→0.0 되읽기 일치).

단계(--stage):
  d1         201 Posz '1.2'   사전 ROTX/Y/Z 0·POSZ 6.2 → 사후 POSZ 1.2
  d1-revert  201 Posz '6.2'   사전 ROTX/Y/Z 0·POSZ 1.2 → 사후 POSZ 6.2
쇼 저장 없음(감독이 저장). 시퀀스·큐·프리셋 쓰기 없음 — 새 번호를 쓰지 않는다.
실행: uv run python .moai/reports/t519/back_place.py <출력폴더> --stage d1 [--rehearse | --approve <폴더>]
🔴 --approve 는 리드의 「실행」 메시지 뒤에만.
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t506")
sys.path.insert(0, ".moai/reports/t516")
import floor_place  # noqa: E402
import tc_probe  # noqa: E402

PATHS = {201: "Patch/Stages/1/Fixtures/43"}
floor_place.PATHS = PATHS
floor_place.STAGES = {
    "d1": ([201], [("Posz", "1.2")], {"ROTX": 0.0, "POSZ": 6.2}, {"ROTX": 0.0, "POSZ": 1.2}),
    "d1-revert": ([201], [("Posz", "6.2")], {"ROTX": 0.0, "POSZ": 1.2}, {"ROTX": 0.0, "POSZ": 6.2}),
}

_fire = tc_probe.Probe.fire


def _fire_t519(self, label, lines):
    # 감사 로그·승인 요청에 t519 로 남도록 위험 사유만 바꾼다(문면은 floor_place.commands 그대로)
    tc_probe.RISK = tc_probe.RISK.__class__(
        reason=f"t519 BACK 높이 시험 {label} — 1대", kind="t519_back_place"
    )
    return _fire(self, label, lines)


tc_probe.Probe.fire = _fire_t519

if __name__ == "__main__":
    sys.exit(floor_place.main())
