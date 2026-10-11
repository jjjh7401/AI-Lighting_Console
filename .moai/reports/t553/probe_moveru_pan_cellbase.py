"""t553 Part ② 추가 2 — MOVER-U 18마디 칸 자신의 기준(position_preset_no)에서 Pan 물결.

리드 지시(2026-10-11, 336 판정 MOVING 뒤): 18마디 게이트는 (가) — Tilt 45 가 아니라
**그 칸 자체**를 잰다. 기준은 데이터의 bar 18 ``position_preset_no``(t543 승인 "2.1")를
``At Preset`` 으로 — 감독 결정 ②의 정확한 형태. 움직이면 그 칸 단위로 게이트 근거를
기록하고 18마디만 연다. 안 움직이면 닫힌 채 「2.1 에선 Pan 안 보임」을 기록한다.

두 묶음(레인 판단 — 리드가 승인 목록에서 고른다):
- 337 (리드 지시 그대로): 336 과 같은 Pan 물결(±30 · 곡선 · Phase 0 Thru 360 · 2박 Speed),
  기준 줄만 ``Attribute 'Tilt' At 45`` → ``At Preset <bar 18 position_preset_no>``.
  바뀐 변수는 기준 하나.
- 338 (앱 그대로): ``server.design.app_movement.app_movement_commands`` 가 bar 18 칸에 대해
  실제로 내는 줄을 바이트 그대로(±12 · 곡선 · 위상 줄 없음 · Speed 56.001). 게이트를 열면
  콘솔에 나가는 건 이 형태다. 칸에 brightness 가 없어 앱은 디머를 안 내므로, 보이게 하려고
  머리에 336 과 같은 켜기 줄(Dimmer 70)만 붙인다.

선택·기준 프리셋·BPM 은 데이터에서(``default_beat_grid`` MOVER-U 트랙, 픽스처 박 시각 회귀).
실행 (R=.moai/reports/t553):
  리허설:    uv run python $R/probe_moveru_pan_cellbase.py $R/rehearse_u_cell --rehearse
  전부-거절: uv run python $R/probe_moveru_pan_cellbase.py $R/denyall_u_cell
실기 전송은 리드 「실행」 뒤에만(--approve). 쇼 저장 0.
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")
sys.path.insert(0, ".moai/reports/t531")
sys.path.insert(0, ".moai/reports/t553")
from m1_common import main_cli, seq_path  # noqa: E402
from probe_moveru_pan_tilted import CURVE, SIZE, _track, selection, song_bpm, speed  # noqa: E402

from server.design.app_movement import app_movement_commands  # noqa: E402

BAR = 18
SEQ_LITERAL = 337
SEQ_APP = 338


def _cell() -> dict:
    return next(c for c in _track()["cues"] if c["bar"] == BAR)


def base_preset() -> str:
    preset = _cell().get("position_preset_no")
    if not preset:
        raise SystemExit(f"bar {BAR} position_preset_no 없음 — 지어내지 않는다")
    return str(preset)


def _lit(sel: str) -> list[str]:
    return [
        "ChangeDestination Root",
        "ClearAll",
        f"{sel} ; Attribute 'Dimmer' At 70",  # MegaPointe 디머 1개(t538 실측)
    ]


def _literal_body(sel: str) -> list[str]:
    return [
        *_lit(sel),
        f"{sel} ; At Preset {base_preset()}",
        f"{sel} ; Attribute 'Pan' At Relative -{SIZE}",
        "Step 2",
        f"Attribute 'Pan' At Relative {SIZE}",
        *CURVE,
        "Attribute 'Pan' At Phase 0 Thru 360",
        f"Attribute 'Pan' At Speed {speed(2)}",
    ]


def _app_body(sel: str) -> list[str]:
    track = _track()
    cell = _cell()
    commands, reason = app_movement_commands(
        cell["app_movement"],
        group_no=track["group_no"],
        position_preset_no=cell.get("position_preset_no"),
        bpm=song_bpm(),
        beats_per_bar=4,
    )
    if reason is not None:
        raise SystemExit(f"앱 에미터 거절: {reason}")
    return [*_lit(sel), *commands]


def _stored(body: list[str], seq: int, name: str) -> list[str]:
    return [
        *body,
        f"Store Sequence {seq} Cue 1 {name}",
        "ClearAll",
        f"Set Sequence {seq} Property 'Name' {name}",
    ]


def build_plan() -> list[tuple[str, list[str]]]:
    sel = selection()
    lit_name = "'T553 - MOVERU pan wave bar18 base literal'"
    app_name = "'T553 - MOVERU pan wave bar18 app output'"
    return [
        ("store_337", _stored(_literal_body(sel), SEQ_LITERAL, lit_name)),
        ("play_337", [f"Goto Cue 1 Sequence {SEQ_LITERAL}"]),
        ("off_337", [f"Off Sequence {SEQ_LITERAL}", "ClearAll"]),
        ("store_338", _stored(_app_body(sel), SEQ_APP, app_name)),
        ("play_338", [f"Goto Cue 1 Sequence {SEQ_APP}"]),
        ("off_338", [f"Off Sequence {SEQ_APP}", "ClearAll"]),
    ]


if __name__ == "__main__":
    sys.exit(
        main_cli(
            item="T553UCell",
            risk_reason=(
                "t553 Part② 추가 2 — MOVER-U bar 18 칸 기준 Pan 물결, "
                "시험 시퀀스 337·338(새), 쇼 저장 0"
            ),
            build_plan=build_plan,
            # 첫 묶음(store_337)을 보낼 때만 빈 번호를 읽는다. 338 은 리드 순서상 먼저
            # 저장됐으므로(2026-10-11 실기) 여기서는 337 만 확인한다 — 338 은 전부-거절 때
            # 비어 있음을 이미 실기로 확인했다(denyall_u_cell). 보내는 명령 줄은 그대로다.
            free_slots=[seq_path(SEQ_LITERAL)],
            extra_notes=[
                f"선택 {selection()} · 기준 At Preset {base_preset()}"
                f"(bar {BAR} position_preset_no) · BPM {song_bpm():.3f} → Speed {speed(2)}",
                "337 = 336 과 같은 물결, 기준만 칸 프리셋 · "
                "338 = app_movement_commands 출력 그대로",
            ],
        )
    )
