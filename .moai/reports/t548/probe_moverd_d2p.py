"""t548 D2' — Pan 물결 재시험(기울인 기준). 설계·리허설·전부-거절·승인 고정.

D2(기준 2.1)는 「판정 불가」였다: 2.1 에서 빔이 거의 수직 아래라 Pan 이 빔 축 회전으로만
나타났다(리드 캡처, 프레임 변화 0.02~0.03%). D2' 는 기준을 기울여 Pan 이 화면에 보이게 한다.

기울이는 법: t538 A0′ 의 실측 기준 줄 `Attribute 'Tilt' At 45`(MegaPointe 에서 2단계 물결이
그 자리 중심으로 돈다고 감독 확인) — 위치 프리셋 대신 절대 Tilt 각도. 45 는 각도 값이지 장비·
그룹·프리셋 번호가 아니다. 선택(Group)·디머 줄·BPM 은 probe_moverd.py 와 같이 데이터에서 읽는다.

기울었는지 아는 법: 첫 묶음 t0(프로그래머만, Store 0)이 같은 기준으로 켜기만 한다 — 리드가
3D 캡처로 바닥 스폿이 v0b(2.1, 장비 바로 아래)에서 옆으로 옮겨졌는지 본 뒤 D2' 를 보낸다.

실행 (R=.moai/reports/t548):
  리허설:    uv run python $R/probe_moverd_d2p.py $R/rehearse_d2p --rehearse
  전부-거절: uv run python $R/probe_moverd_d2p.py $R/denyall_d2p
실기 전송은 리드 「실행」 뒤에만(--approve $R/denyall_d2p). 쇼 저장 0.
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t531")
sys.path.insert(0, ".moai/reports/t548")
import probe_moverd as base  # noqa: E402
from m1_common import main_cli, seq_path  # noqa: E402

TILTED_BASE = "Attribute 'Tilt' At 45"  # t538 A0′ 실측 기준 줄(각도 값)
SEQ_NO = 335


def _head(sel: str) -> list[str]:
    return [
        "ChangeDestination Root",
        "ClearAll",
        f"{sel} ; Attribute 'Dimmer' At 70",
        f"{sel} ; Attribute 'Dimmer2' At 70",
        f"{sel} ; {TILTED_BASE}",
    ]


def build_plan() -> list[tuple[str, list[str]]]:
    sel = base.selection()
    name = "'T548 - D2p pan wave 2 beats tilted base'"
    body = [
        *_head(sel),
        f"{sel} ; Attribute 'Pan' At Relative -{base.SIZE}",
        "Step 2",
        f"Attribute 'Pan' At Relative {base.SIZE}",
        *base.CURVE,
        "Attribute 'Pan' At Phase 0 Thru 360",
        f"Attribute 'Pan' At Speed {base.speed(2)}",
    ]
    return [
        ("t0_tilted_lit", _head(sel)),
        ("t0_clear", ["ClearAll"]),
        (
            "store_D2p",
            [
                *body,
                f"Store Sequence {SEQ_NO} Cue 1 {name}",
                "ClearAll",
                f"Set Sequence {SEQ_NO} Property 'Name' {name}",
            ],
        ),
        ("play_D2p", [f"Goto Cue 1 Sequence {SEQ_NO}"]),
        ("off_D2p", [f"Off Sequence {SEQ_NO}"]),
        ("final_clear", ["ClearAll"]),
    ]


if __name__ == "__main__":
    sys.exit(
        main_cli(
            item="T548D2p",
            risk_reason="t548 D2' Pan 물결 재시험 — 시험 시퀀스 335(새), 쇼 저장 0",
            build_plan=build_plan,
            free_slots=[seq_path(SEQ_NO)],
            extra_notes=[
                f"선택 {base.selection()} · 기준 {TILTED_BASE}(t538 A0′) · "
                f"BPM {base.song_bpm():.3f} → Speed {base.speed(2)}",
                "t0 는 프로그래머만(Store 0) — 기울었는지 리드 캡처로 확인 뒤 D2' 전송",
            ],
        )
    )
