"""칸의 방향 값(``direction``) — SPEC-LDRHYTHM-001 D4·D8·D9·D10·D11 (순수 계산, 콘솔 무접촉).

격자 칸 하나는 구조화된 「방향 값」 하나를 가진다. 자동 배치는 칸마다 규칙 결정(``_CellPlan``)을
한 번만 내리는데, 라벨·무대 미리보기·프리셋 계획·콘솔 송신이 그 결정을 따로 다시 알아내면 서로
어긋난다. 그래서 결정을 이 모양으로 칸에 싣고, 아래 소비처가 전부 이 값을 읽는다.

- 라벨: ``direction_label`` 한 함수가 값에서 만든다(상수 표에서 고르지 않는다).
- 색 이름: ``assign_color_names`` 한 함수가 정한다. 팔레트 표에 있으면 그 이름, 없으면 가장 가까운
  표 이름에 번호를 붙인다. 같은 색 모음이면 항상 같은 이름이다.
- 불일치 검사: ``label_value_mismatches`` 가 라벨과 값, 값과 값이 서로 맞는지 본다.

값의 모양::

    {"brightness_percent": int | None,
     "color": {"name": str | None, "rgb": [r, g, b] | None} | None,
     "position": {"name": str | None} | None,
     "effect_kind": "pulse" | "chase" | "motion" | "hold" | "blind" | "strobe" | "static" | "rest"
                    | "pre_hit" | None,
     "movement": {"shape", "axes", "period_unit", "period_value", "phase_spread"} | None,
     "entry": {"trigger_beat": int | None}}

라벨 글자는 읽지 않는다(REQ-LDBEAT-006(ii-2)). 값은 라벨에서 역산되지 않고 규칙 결정에서 온다.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import TypedDict

from server.design.arrange_policy import ARRANGEMENT_COLOR_NAMES
from server.design.beat_grid_measured import canonical_axes

__all__ = [
    "BASIC_WORDS",
    "EFFECT_KINDS",
    "SEGMENT_WORDS",
    "CellDirection",
    "assign_color_names",
    "build_direction",
    "direction_label",
    "label_value_mismatches",
    "normalize_direction",
    "sync_direction_with_edit",
]

_Rgb = tuple[int, int, int]

#: 규칙 종류 어휘 — ``arrange_generator._CellPlan.kind`` 와 같다.
EFFECT_KINDS: tuple[str, ...] = (
    "pulse",
    "chase",
    "motion",
    "hold",
    "blind",
    "strobe",
    "static",
    "rest",
    "pre_hit",
)
#: 쉬는 밝기(0)를 내는 규칙 종류. 예고 칸은 쉼과 밝기가 같다.
_DARK_KINDS = frozenset({"rest", "pre_hit"})

#: 구간 단위 생성기(``arrange_segments``)의 칸 말 — 기본 격자(``love_attack.yaml``)와 배치 규칙서의
#: 말이다. ``static:<역할>`` 은 유지 칸이 줄 역할마다 다르게 부르는 말이고, 없으면 ``static`` 이다.
SEGMENT_WORDS: dict[str, str] = {
    "rest": "—",
    "hold": "정지",
    "static": "유지",
    "static:key": "FOH 켬",
    "static:wash": "워시",
    "pulse": "킥 1·2·4박",
    "chase": "SIDE-L/R 2·4박 번갈이",
    "motion": "팬 웨이브(한 바퀴 2마디)",
    "motion:Tilt": "틸트 웨이브(한 바퀴 2마디)",
    "blind": "BLIND 2박",
    "strobe": "STROBE 1마디 박마다",
    "pre_hit": "3·4박 전부 비움(예고)",
}
#: 모든 마디에 칸을 내는 기존 생성기(``arrange_generator``)의 칸 말. 규칙 제안
#: (``beat_grid_suggestion_rules``)이 이 말로 칸을 알아본다.
BASIC_WORDS: dict[str, str] = {
    "rest": "—",
    "hold": "정지",
    "static": "유지",
    "pulse": "펄스 1·2·4박",
    "chase": "체이스 2·4박",
    "motion": "팬 웨이브 2마디",
    "blind": "블라인드 2박",
    "strobe": "스트로브 1마디",
}

_AXES = ("Pan", "Tilt")
_PERIOD_UNITS = ("beat", "bar")
#: 프리셋 이름에 쓸 수 있는 글자(``beat_grid_edit._ASCII_LABEL_PATTERN`` 의 허용 글자와 같다).
_CONSOLE_NAME = re.compile(r"[0-9A-Za-z _.-]+")


class CellDirectionColor(TypedDict):
    name: str | None
    rgb: list[int] | None


class CellDirectionPosition(TypedDict):
    name: str | None


class CellDirectionMovement(TypedDict):
    shape: str | None
    axes: list[str]
    period_unit: str | None
    period_value: int | None
    phase_spread: bool | None


class CellDirectionEntry(TypedDict):
    trigger_beat: int | None


class CellDirection(TypedDict):
    """칸 하나의 방향 값. 키 여섯이 항상 있다."""

    brightness_percent: int | None
    color: CellDirectionColor | None
    position: CellDirectionPosition | None
    effect_kind: str | None
    movement: CellDirectionMovement | None
    entry: CellDirectionEntry


# --- 만들기 · 정규화 ------------------------------------------------------------------------------


def build_direction(
    *,
    brightness_percent: int | None,
    kind: str | None,
    rgb: Iterable[int] | None = None,
    color_name: str | None = None,
    position: str | None = None,
    movement: Mapping[str, object] | None = None,
    trigger_beat: int | None = None,
) -> CellDirection:
    """규칙 결정의 값으로 방향 값을 만든다. 같은 입력이면 같은 값이다."""
    raw = {
        "brightness_percent": brightness_percent,
        "color": None if rgb is None else {"name": color_name, "rgb": list(rgb)},
        "position": None if position is None else {"name": position},
        "effect_kind": kind,
        "movement": None if movement is None else dict(movement),
        "entry": {"trigger_beat": trigger_beat},
    }
    built = normalize_direction(raw)
    assert built is not None
    return built


def _int_in(value: object, low: int, high: int | None = None) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value < low or (high is not None and value > high):
        return None
    return value


def _normalize_color(raw: object) -> CellDirectionColor | None:
    if not isinstance(raw, Mapping):
        return None
    name = raw.get("name")
    clean_name = (
        name.strip() if isinstance(name, str) and _CONSOLE_NAME.fullmatch(name.strip()) else None
    )
    rgb = raw.get("rgb")
    clean_rgb: list[int] | None = None
    if isinstance(rgb, (list, tuple)) and len(rgb) == 3:
        channels = [_int_in(channel, 0, 100) for channel in rgb]
        if all(channel is not None for channel in channels):
            clean_rgb = [int(channel) for channel in channels]  # type: ignore[arg-type]
    if clean_name is None and clean_rgb is None:
        return None
    return CellDirectionColor(name=clean_name, rgb=clean_rgb)


def _normalize_movement(raw: object) -> CellDirectionMovement | None:
    if not isinstance(raw, Mapping):
        return None
    shape = raw.get("shape")
    if not isinstance(shape, str) or not shape.strip():
        return None
    axes_raw = raw.get("axes")
    axes = (
        [axis for axis in canonical_axes(axes_raw) if axis in _AXES]
        if isinstance(axes_raw, (list, tuple))
        else []
    )
    unit = raw.get("period_unit")
    spread = raw.get("phase_spread")
    return CellDirectionMovement(
        shape=shape.strip(),
        axes=[axis for axis in _AXES if axis in axes],
        period_unit=unit if unit in _PERIOD_UNITS else None,
        period_value=_int_in(raw.get("period_value"), 1),
        phase_spread=spread if isinstance(spread, bool) else None,
    )


def normalize_direction(raw: object) -> CellDirection | None:
    """저장 경계에서 방향 값을 읽는다. 모양이 틀린 부분은 버리고 나머지는 둔다(라벨은 읽지 않는다).

    ``raw`` 가 사전이 아니면 ``None`` 이다(칸에 방향 값이 없다). 사전이면 키 여섯이 전부 있다.
    """
    if not isinstance(raw, Mapping):
        return None
    position_raw = raw.get("position")
    position_name = position_raw.get("name") if isinstance(position_raw, Mapping) else None
    entry_raw = raw.get("entry")
    kind = raw.get("effect_kind")
    return CellDirection(
        brightness_percent=_int_in(raw.get("brightness_percent"), 0, 100),
        color=_normalize_color(raw.get("color")),
        position=(
            CellDirectionPosition(name=position_name.strip())
            if isinstance(position_name, str) and position_name.strip()
            else None
        ),
        effect_kind=kind if kind in EFFECT_KINDS else None,
        movement=_normalize_movement(raw.get("movement")),
        entry=CellDirectionEntry(
            trigger_beat=_int_in(
                entry_raw.get("trigger_beat") if isinstance(entry_raw, Mapping) else None, 1
            )
        ),
    )


def sync_direction_with_edit(
    direction: Mapping[str, object], changes: Mapping[str, object]
) -> CellDirection:
    """감독의 칸 편집(``changes``)이 방향 값이 되풀이하는 필드를 바꿨으면 방향 값도 따라 바꾼다.

    방향 값이 되풀이하는 옛 필드는 밝기 값·진입 박·앱 움직임이다. 편집이 이들을 바꾸고 방향 값을
    그대로 두면 낡은 값이 남아 라벨·미리보기·검사가 서로 다른 말을 한다. 밝기는 값(``value``)
    모드일 때만 따라간다(프리셋 번호 모드는 밝기 퍼센트를 말하지 않는다). 편집이 건드리지 않은
    부분과 라벨은 그대로 둔다.
    """
    synced = dict(direction)
    brightness = changes.get("brightness")
    if isinstance(brightness, Mapping) and brightness.get("mode") == "value":
        synced["brightness_percent"] = brightness.get("value_percent")
    entry = changes.get("entry")
    if isinstance(entry, Mapping) and "trigger_beat" in entry:
        synced["entry"] = {"trigger_beat": entry.get("trigger_beat")}
    if "app_movement" in changes:
        synced["movement"] = changes["app_movement"]
    result = normalize_direction(synced)
    assert result is not None
    return result


# --- 라벨 -----------------------------------------------------------------------------------------


def direction_label(
    direction: Mapping[str, object],
    layer_role: object = None,
    *,
    words: Mapping[str, str] = SEGMENT_WORDS,
) -> str | None:
    """방향 값이 말하는 칸 이름. 규칙 종류가 없거나 ``words`` 에 말이 없으면 ``None`` 이다.

    유지(``static``) 칸은 줄 역할이 이름을 가른다(``words`` 에 ``static:<역할>`` 이 있을 때).
    """
    kind = direction.get("effect_kind")
    if not isinstance(kind, str):
        return None
    if kind == "static":
        return words.get(f"static:{layer_role}") or words.get("static")
    movement = direction.get("movement")
    if kind == "motion" and isinstance(movement, Mapping) and movement.get("axes") == ["Tilt"]:
        return words.get("motion:Tilt") or words.get(kind)
    return words.get(kind)


# --- 색 이름 --------------------------------------------------------------------------------------


def _nearest_name(rgb: _Rgb) -> str:
    """표에서 RGB 거리(제곱합)가 가장 가까운 색의 이름. 같은 거리면 이름 순이다."""
    return min(
        ARRANGEMENT_COLOR_NAMES.items(),
        key=lambda item: (sum((a - b) ** 2 for a, b in zip(item[0], rgb, strict=True)), item[1]),
    )[1]


def assign_color_names(
    rgbs: Iterable[Iterable[int]],
    *,
    preferred: Mapping[_Rgb, str] | None = None,
    hints: Mapping[_Rgb, str] | None = None,
) -> dict[_Rgb, str]:
    """RGB 마다 콘솔 영문 이름 하나를 정한다. 이름은 색마다 다르고 비는 일이 없다.

    우선순위: ``preferred``(곡 주석의 콘솔 이름처럼 확정된 이름) → ``hints``(이미 칸에 실린 이름) →
    팔레트 표에 정확히 있는 색 → 표에서 가장 가까운 이름. 같은 이름을 다른 RGB 가 이미 가졌으면
    「PINK 2」「PINK 3」처럼 번호를 붙인다. 각 단계 안에서는 RGB 오름차순으로 처리하므로 같은 색
    모음이면 입력 순서와 상관없이 항상 같은 이름이다.
    """
    unique = sorted({(int(r), int(g), int(b)) for r, g, b in (tuple(rgb) for rgb in rgbs)})
    names: dict[_Rgb, str] = {}
    used: set[str] = set()

    def take(rgb: _Rgb, base: str) -> None:
        name, turn = base, 2
        while name in used:
            name, turn = f"{base} {turn}", turn + 1
        used.add(name)
        names[rgb] = name

    tiers: tuple[Mapping[_Rgb, str], ...] = (
        preferred or {},
        hints or {},
        {rgb: ARRANGEMENT_COLOR_NAMES[rgb] for rgb in unique if rgb in ARRANGEMENT_COLOR_NAMES},
    )
    for tier in tiers:
        for rgb in unique:
            if rgb not in names and tier.get(rgb):
                take(rgb, tier[rgb])
    for rgb in unique:
        if rgb not in names:
            take(rgb, _nearest_name(rgb))
    return names


# --- 라벨·값 불일치 -------------------------------------------------------------------------------


def _same_movement(direction_movement: Mapping[str, object], app: Mapping[str, object]) -> bool:
    def key(movement: Mapping[str, object]) -> tuple[object, ...]:
        axes = movement.get("axes") or ()
        return (
            movement.get("shape"),
            tuple(canonical_axes(axes)) if isinstance(axes, (list, tuple)) else (),
            movement.get("period_unit"),
            movement.get("period_value"),
        )

    return key(direction_movement) == key(app)


def label_value_mismatches(grid: Mapping[str, object]) -> list[dict[str, object]]:
    """방향 값을 가진 칸마다 라벨과 값, 값과 값이 서로 맞는지 본다. 어긋난 칸을
    ``{"group_name", "bar", "reason"}`` 로 돌려준다(없으면 빈 목록). 방향 값이 없는 칸(감독이 손으로
    만든 칸)은 판정하지 않는다.

    - 라벨 = 방향 값에서 만든 이름(구간 단위 말 또는 기존 생성기 말).
    - 움직임이 있다 ⇔ 규칙 종류가 ``motion``. 무빙 칸의 효과 번호에는 움직임이 있다.
    - 밝기 0 ⇔ 쉼·예고 종류.
    - 방향 값 ↔ 칸의 옛 필드(밝기 값·진입 박·계획 색·계획 위치·``app_movement``)가 같다.
    """
    found: list[dict[str, object]] = []
    for track in grid.get("tracks") or []:  # type: ignore[union-attr]
        if not isinstance(track, Mapping):
            continue
        role = track.get("layer_role")
        for cue in track.get("cues") or []:
            if not isinstance(cue, Mapping) or not isinstance(cue.get("direction"), Mapping):
                continue
            for reason in _cue_mismatches(cue, cue["direction"], role):  # type: ignore[arg-type]
                found.append(
                    {"group_name": track.get("group_name"), "bar": cue.get("bar"), "reason": reason}
                )
    return found


def _cue_mismatches(
    cue: Mapping[str, object], direction: Mapping[str, object], role: object
) -> list[str]:
    reasons: list[str] = []
    kind = direction.get("effect_kind")
    if kind is None:
        reasons.append("방향 값에 규칙 종류가 없음")
    else:
        accepted = {
            direction_label(direction, role, words=words) for words in (SEGMENT_WORDS, BASIC_WORDS)
        }
        if cue.get("label") not in accepted:
            reasons.append("라벨이 값과 다름")
    movement = direction.get("movement")
    if (movement is not None) != (kind == "motion"):
        reasons.append("움직임 값과 규칙 종류가 어긋남(움직임은 motion 칸에만 있다)")
    if role == "mover" and cue.get("effect_preset_no") and movement is None:
        reasons.append("무빙 칸의 효과 번호인데 방향 값에 움직임이 없음")
    percent = direction.get("brightness_percent")
    if percent is not None and kind is not None and (percent == 0) != (kind in _DARK_KINDS):
        reasons.append("밝기 0 과 쉼 종류가 어긋남")
    brightness = cue.get("brightness")
    if (
        isinstance(brightness, Mapping)
        and brightness.get("mode") == "value"
        and percent is not None
        and brightness.get("value_percent") != percent
    ):
        reasons.append("밝기가 방향 값과 다름")
    entry = cue.get("entry")
    beat = (direction.get("entry") or {}).get("trigger_beat")  # type: ignore[union-attr]
    if isinstance(entry, Mapping) and beat is not None and entry.get("trigger_beat") != beat:
        reasons.append("진입 박이 방향 값과 다름")
    color = direction.get("color")
    planned = cue.get("planned_color")
    if (
        isinstance(color, Mapping)
        and color.get("rgb") is not None
        and planned is not None
        and list(planned) != list(color["rgb"])  # type: ignore[arg-type]
    ):
        reasons.append("계획 색이 방향 값과 다름")
    position = direction.get("position")
    planned_position = cue.get("planned_position")
    if (
        isinstance(position, Mapping)
        and planned_position is not None
        and position.get("name") != planned_position
    ):
        reasons.append("계획 위치가 방향 값과 다름")
    app = cue.get("app_movement")
    if isinstance(movement, Mapping):
        if not (isinstance(app, Mapping) and app.get("shape") is not None):
            reasons.append("방향 값의 움직임이 app_movement 에 없음")
        elif not _same_movement(movement, app):
            reasons.append("app_movement 가 방향 값의 움직임과 다름")
    return reasons
