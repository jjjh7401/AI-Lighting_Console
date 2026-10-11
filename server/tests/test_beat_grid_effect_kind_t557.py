"""효과 종류가 번호대 검사를 가른다 — 앱이 고른 풀대로 effect_kind 를 보내야 하는 이유 (카드 t557).

같은 색 효과 번호를 `effect_kind="color"` 로 보내면 색 효과 번호대(preset_pools.yaml)
안이라 번호대 경고가 없고, 예전 앱처럼 `"position"` 으로 보내면 위치 효과 번호대
밖이라 번호대 경고(또는 confirmed:true 이면 거절)가 난다. 승인은 같은 변경에 실어
(REQ-LDBEAT-015(h)) 승인 규칙이 이 비교를 가리지 않게 한다.
"""

from __future__ import annotations

from server.design.beat_grid import attach_beat_grid_default
from server.design.beat_grid_edit import apply_beat_grid_edit, load_preset_pool_policy

APPROVAL = {
    "grade": None,
    "approval": {"by": "supervisor", "date": "2026-10-11", "source": "test t557"},
}


def _color_effect_number() -> str:
    """색 효과 번호대의 시작 번호 — 데이터 파일에서 읽는다(코드에 번호 없음)."""
    band = load_preset_pool_policy()["pools"]["color_effect"]
    return str(band["start"])


def _apply(kind: str) -> list[str]:
    grid = attach_beat_grid_default({"song_title": "LOVE ATTACK", "sequence_number": 210})[
        "beat_grid"
    ]
    _, report = apply_beat_grid_edit(
        grid,
        # 앱 무빙이 없는 칸 — 위치 효과와 축 충돌(REQ-006(vi-7))이 비교를 가리지 않게.
        bar=7,
        target="WASH-ALL",
        changes={
            "effect_preset_no": _color_effect_number(),
            "effect_kind": kind,
            "evidence": APPROVAL,
        },
    )
    return report


def test_color_effect_sent_as_color_passes_the_band_check() -> None:
    report = _apply("color")
    assert not any("번호대" in line for line in report), report


def test_same_number_sent_as_position_hits_the_band_check() -> None:
    report = _apply("position")
    assert any("번호대" in line for line in report), report
