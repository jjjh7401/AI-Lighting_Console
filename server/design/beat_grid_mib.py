"""MIB(어둠 속 사전이동) — 칸을 바꿀 때 무버를 다음 위치로 미리 옮기는 위치 전용 큐.

화면 규칙(``ui/src/components/beatGridTransition.ts`` 의 ``transitionMib``)과 같은 기준이다.
위치가 바뀌고 앞 칸이 꺼져 있으면, 앞 칸 바로 다음 마디에 위치 전용 큐를 하나 넣는다.
앞 칸이 켜져 있으면 MIB 가 아니다(켜진 채 이동). 사전이동 큐가 나간 뒤 켜지는 칸까지의
어두운 시간이 이동+정착 시간보다 짧으면 큐를 넣지 않고 사유를 남긴다.

사전이동 큐는 칸과 같은 마디 번호 키로 반영 기록에 들어간다. 그래서 다시 반영해도 같은
큐 번호를 쓴다(기록에 없는 새 번호를 만들지 않는다).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol

from server.concept.resolver import MOVE_SECONDS, SETTLE_SECONDS

#: 어두운 시간의 하한(초) — 사전이동 큐가 나간 뒤 켜지는 칸까지 이동과 정착이 끝나야 한다.
MIB_MIN_DARK_SECONDS: float = MOVE_SECONDS + SETTLE_SECONDS

#: 화면 ``cueIsLit`` 과 같다 — 이름이 없거나 대시면 꺼진 칸이다.
_UNLIT_LABELS = frozenset({"", "—"})


class BarClock(Protocol):
    """마디 시작 시각(음원 초)을 주는 곳 — ``beat_grid_emit.SongTiming`` 이 맞는다."""

    def bar_start_seconds(self, bar: int) -> float | None: ...


def cue_is_lit(cue: Mapping[str, object]) -> bool:
    """칸이 빛을 내는가. 값 0 이거나 이름이 비었거나 대시면 꺼진 칸이다."""
    brightness = cue.get("brightness")
    if (
        isinstance(brightness, Mapping)
        and brightness.get("mode") == "value"
        and brightness.get("value_percent") == 0
    ):
        return False
    label = str(cue.get("label") or "").strip()
    return label not in _UNLIT_LABELS


def _has_movement(cue: Mapping[str, object]) -> bool:
    """웨이브(앱 무빙)가 붙은 칸인가."""
    return bool(cue.get("app_movement"))


def _starts_movement_lit(prev: Mapping[str, object], cur: Mapping[str, object]) -> bool:
    """웨이브가 켜진 칸에서 새로 시작하는가 — 앞 칸도 켜져 있어 어둠이 없다(감독 결정 D3(a))."""
    return cue_is_lit(prev) and cue_is_lit(cur) and _has_movement(cur) and not _has_movement(prev)


def movement_lit_starts(cues: Sequence[Mapping[str, object]]) -> list[int]:
    """웨이브가 켜진 칸에서 시작하는 마디들. 화면에는 「켜진 채 움직임 시작」으로 보인다."""
    return [
        int(cur["bar"])  # type: ignore[arg-type]
        for prev, cur in zip(cues, cues[1:], strict=False)
        if _starts_movement_lit(prev, cur)
    ]


def plan_mib_premoves(
    cues: Sequence[Mapping[str, object]], timing: BarClock
) -> tuple[list[dict[str, object]], list[str]]:
    """마디 순서로 정렬된 칸에서 사전이동 큐를 짓는다. ``(사전이동 큐 목록, 불가 사유 목록)``.

    사전이동 큐는 앞 칸 바로 다음 마디에 놓는다. 그 마디에는 칸이 없다(앞 칸이 바로 앞이다).
    위치는 뒤 칸의 위치 프리셋이고, 증거(``evidence``)도 뒤 칸의 것을 그대로 쓴다.
    """
    premoves: list[dict[str, object]] = []
    notes: list[str] = []
    for prev, cur in zip(cues, cues[1:], strict=False):
        if _starts_movement_lit(prev, cur):
            notes.append(
                f"{int(cur['bar'])}마디 켜진 채 움직임 시작 — "  # type: ignore[arg-type]
                "앞 큐가 켜져 있어 웨이브가 켜진 채 시작합니다"
            )
        target = cur.get("position_preset_no")
        if target is None or prev.get("position_preset_no") == target:
            continue  # 위치가 안 바뀜 — MIB 필요 없음
        cur_bar = int(cur["bar"])  # type: ignore[arg-type]
        if cue_is_lit(prev):
            notes.append(f"{cur_bar}마디 MIB 불가 — 앞 큐가 켜져 있어 켜진 채 이동합니다")
            continue
        premove_bar = int(prev["bar"]) + 1  # type: ignore[arg-type]
        if premove_bar >= cur_bar:
            notes.append(f"{cur_bar}마디 MIB 불가 — 앞 큐 바로 다음 마디라 어두운 시간이 없습니다")
            continue
        cur_at = timing.bar_start_seconds(cur_bar)
        premove_at = timing.bar_start_seconds(premove_bar)
        dark = 0.0 if cur_at is None or premove_at is None else cur_at - premove_at
        if dark < MIB_MIN_DARK_SECONDS:
            notes.append(
                f"{cur_bar}마디 MIB 불가 — 어두운 시간 {dark:.1f}초가 "
                f"이동 시간 {MIB_MIN_DARK_SECONDS:.1f}초보다 짧습니다"
            )
            continue
        premoves.append(
            {
                "bar": premove_bar,
                "position_preset_no": target,
                "evidence": cur.get("evidence"),
                "label": "",
                # 전체 실행 C-11 — 격자 칸이 아닌 큐다. 카드가 격자 칸 수와 큐 수의 차이를 센다.
                "mib_premove": True,
            }
        )
    return premoves, notes
