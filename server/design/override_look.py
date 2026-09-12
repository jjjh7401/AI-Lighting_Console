"""Override look 계획기 — `Global Preset` override slot 하나에 저장할 커맨드 번들.

t373. `docs/research/ma3-effects/20-mblightarts-end-to-end-showfile-process.md`
§10.1(override look 생성)·§11(`create_override_solo_spot` 라우팅)·§12.3
(`OverrideLookPlan` 스키마)을 콘솔에 쏠 수 있는 문형으로 옮긴다.

## 범위 — 이 모듈이 만들지 않는 것

- **`regen override`** — §10.2 의 콘솔 매크로다. 이 모듈은 override look 을
  프로그래머에 채우고 `Store` 하는 §10.1 의 4~14단계까지만 만든다. Regen 은
  별도 카드다.
- **Move In Black 을 켜고 끄는 커맨드.** §10.2 의 MIB 는 override *sequence*
  의 속성이고 `regen override` 이후에 콘솔에서 구성된다 — 이 저장소 어디에도
  그 속성을 토글하는 측정된 문형이 없다. 이 모듈은 그 결정(`move_in_black`)을
  계획에 **정보로만** 싣는다.
- **Stop IFX / Stop PFX 프리셋을 호출하는 커맨드 문형.** §10.1 item 9-10 은
  "Stop IFX/PFX 프리셋을 누른다"고 말하지만 그 프리셋이 어느 풀·번호에 있는지
  이 저장소는 측정한 바가 없다(`grep -rn 'IFX\\|PFX' server/` 0건, 2026-09-13).
  지어낸 문형을 커맨드에 실으면 발사 전 안전 게이트를 통과해 콘솔에 틀린 것이
  갈 수 있다 — 그래서 호출자가 이미 측정해 둔 원문 커맨드를 그대로 실어야
  한다(``stop_ifx_command``/``stop_pfx_command``). 결정이 True 인데 원문이
  없으면 조용히 건너뛰지 않고 거절한다 — 감독이 "멈춰라"라고 답했는데 번들에
  그 줄이 없으면 결정이 사라진 채로 저장된다.

## Slot 점유

§10.1 item 3: "override look용으로 준비된 10개 slot을 확인한다." 어느 슬롯이
비었는지는 **콘솔을 읽어야 아는 사실**이고 이 모듈은 콘솔을 읽지 않는다 —
호출자가 이미 읽은 점유 집합을 ``occupied_slots`` 로 넘긴다. ``None`` 은
"비어 있음"이 아니라 **"못 쟀음"**이다(`AxisRange.window()` 의 "``None``은
범위 밖이 아니라 대조 불가"와 같은 구분) — 못 쟀으면 그 어떤 슬롯도 비었다고
말하지 않고 거절한다.

읽기 전용. 콘솔·네트워크 접촉 0.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from server.presets.store import preset_store_commands
from server.spatial.pointing import PointingTarget, aim_pan_tilt

__all__ = [
    "DEFAULT_OVERRIDE_SLOTS",
    "OverrideLookError",
    "OverrideLookPlan",
    "OverrideSafetyAnswers",
    "plan_override_solo_spot",
    "recommended_safety_answers",
]


class OverrideLookError(ValueError):
    """이 모듈이 커맨드로 바꾸길 거절한 요청."""


#: §10.1 item 3 이 말하는 "준비된 10개 slot". 문서는 슬롯 **번호**를 정하지
#: 않는다(예시는 override preset number 6 하나뿐) — 1..10 은 이 모듈이 고른
#: ASSUMPTION 이고, 실제 쇼파일의 슬롯 번호가 다르면 ``available_slots`` 로
#: 덮어써라.
DEFAULT_OVERRIDE_SLOTS: tuple[int, ...] = tuple(range(1, 11))

#: `preset_apply_color_command` 의 `.1f` 관례를 이 모듈의 모든 프로그래머 값에
#: 통일한다 — 서로 다른 소수 표기가 한 줄에 섞이면 읽는 사람이 어느 쪽이
#: 실측 문형인지 헷갈린다.
_DECIMALS = 1

#: `preset_apply_color_command._COLOR_PERCENT_MAX` 와 같은 상한 — 그 상수는
#: 그 파일 안에서만 쓰이는 비공개 값이라 사본을 여기 별도로 둔다(같은 숫자,
#: 다른 자리 — 공개 API 가 아니므로 import 하지 않는다).
_COLOR_PERCENT_MAX = 100.0
_DIMMER_PERCENT_MAX = 100.0


def _format_value(value: float) -> str:
    return f"{value:.{_DECIMALS}f}"


def _require_finite_number(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OverrideLookError(f"{name} must be a number, got {value!r}")
    if not math.isfinite(value):
        raise OverrideLookError(f"{name} must be finite, got {value!r}")
    return float(value)


def _require_percent(name: str, value: object, *, maximum: float) -> float:
    number = _require_finite_number(name, value)
    if not 0.0 <= number <= maximum:
        raise OverrideLookError(f"{name} {value!r} is outside 0..{maximum:g}")
    return number


@dataclass(frozen=True)
class OverrideSafetyAnswers:
    """§10.1 item 13 이 "자동화하지 않는다"고 못박은 두 결정 + §10.2 의 MIB.

    셋 다 **명시적 bool 이어야 한다.** 하나라도 빠지면(``None`` 이거나 bool 이
    아니면) 계획 전체를 거절한다 — 감독의 답이 없는 채로 조용히 기본값이
    깔리는 것이 이 카드가 막으려는 실패다.
    """

    stop_ifx: bool
    stop_pfx: bool
    move_in_black: bool

    def __post_init__(self) -> None:
        for name in ("stop_ifx", "stop_pfx", "move_in_black"):
            if not isinstance(getattr(self, name), bool):
                raise OverrideLookError(
                    f"{name} must be an explicit bool answer, got {getattr(self, name)!r}"
                )

    def to_dict(self) -> dict[str, bool]:
        return {
            "stop_ifx": self.stop_ifx,
            "stop_pfx": self.stop_pfx,
            "move_in_black": self.move_in_black,
        }


def recommended_safety_answers(*, show_movement: bool = False) -> OverrideSafetyAnswers:
    """§10.1 item 12 / §10.2 가 말하는 표준 솔로 스팟 기본값 — **추천일 뿐**.

    ``show_movement=False`` (표준 솔로 스팟): 셋 다 켠다 — Stop IFX/PFX,
    Move In Black. ``show_movement=True`` ("움직임을 보여줘" 같은 요청, §10.2
    "back spot이 앞으로 움직이며 piano guy를 잡는 장면"): 셋 다 끈다.

    이 함수는 값을 **고르지 않는다** — `plan_override_solo_spot` 은 여전히
    명시적 `OverrideSafetyAnswers` 를 요구한다. 오케스트레이터가 사용자에게
    제안할 기본값이 필요할 때만 쓴다(item 13: 이 결정은 자동화 대상이 아니다).
    """
    return OverrideSafetyAnswers(
        stop_ifx=not show_movement,
        stop_pfx=not show_movement,
        move_in_black=not show_movement,
    )


@dataclass(frozen=True)
class OverrideLookPlan:
    """§12.3 `OverrideLookPlan` 스키마를 이 저장소의 커맨드 문형으로 채운 결과."""

    fixtures: tuple[int, ...]
    target: PointingTarget
    aims: tuple[tuple[int, float, float], ...]
    dimmer_pct: float
    color_percents: tuple[float, float, float]
    zoom_degrees: float
    safety: OverrideSafetyAnswers
    pool_no: int
    slot: int
    label: str | None
    commands: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "fixtures": list(self.fixtures),
            "target": self.target.as_tuple(),
            "aims": [list(aim) for aim in self.aims],
            "dimmer_pct": self.dimmer_pct,
            "color_percents": list(self.color_percents),
            "zoom_degrees": self.zoom_degrees,
            "safety": self.safety.to_dict(),
            "store": {"pool": self.pool_no, "slot": self.slot, "policy": "override"},
            "label": self.label,
            "commands": list(self.commands),
        }


def _resolve_slot(
    *,
    occupied_slots: frozenset[int] | None,
    available_slots: Sequence[int],
    preferred_slot: int | None,
) -> int:
    if occupied_slots is None:
        raise OverrideLookError(
            "override slot occupancy was not established from the rig read — "
            "an unestablished slot is not a free slot"
        )
    slots = tuple(available_slots)
    if not slots:
        raise OverrideLookError("no override slots were offered to choose from")
    if preferred_slot is not None:
        if preferred_slot not in slots:
            raise OverrideLookError(
                f"slot {preferred_slot!r} is not among the prepared override slots {slots!r}"
            )
        if preferred_slot in occupied_slots:
            raise OverrideLookError(f"override slot {preferred_slot!r} is already occupied")
        return preferred_slot
    free = [slot for slot in slots if slot not in occupied_slots]
    if not free:
        raise OverrideLookError(f"all {len(slots)} prepared override slots are occupied")
    return free[0]


def _fixture_look_command(
    fid: int,
    pan: float,
    tilt: float,
    *,
    dimmer_pct: float,
    color_percents: tuple[float, float, float],
    zoom_degrees: float,
) -> str:
    red, green, blue = color_percents
    parts = [
        f"Fixture {fid}",
        f"Attribute 'Dimmer' At {_format_value(dimmer_pct)}",
        f"Attribute 'ColorRGB_R' At {_format_value(red)}",
        f"Attribute 'ColorRGB_G' At {_format_value(green)}",
        f"Attribute 'ColorRGB_B' At {_format_value(blue)}",
        f"Attribute 'Pan' At {_format_value(pan)}",
        f"Attribute 'Tilt' At {_format_value(tilt)}",
        f"Attribute 'Zoom' At {_format_value(zoom_degrees)}",
    ]
    return " ; ".join(parts)


def plan_override_solo_spot(
    fixtures: Sequence[tuple[int, tuple[float, float, float]]],
    target: PointingTarget,
    *,
    safety: OverrideSafetyAnswers,
    pool_no: int,
    occupied_slots: frozenset[int] | None,
    zoom_degrees: float,
    dimmer_pct: float = 100.0,
    color_percents: tuple[float, float, float] = (100.0, 100.0, 100.0),
    available_slots: Sequence[int] = DEFAULT_OVERRIDE_SLOTS,
    preferred_slot: int | None = None,
    label: str | None = None,
    rotz_by_fid: Mapping[int, float] | None = None,
    stop_ifx_command: str | None = None,
    stop_pfx_command: str | None = None,
) -> OverrideLookPlan:
    """§10.1 items 4-14 의 커맨드 번들 — 조준·색·줌을 채우고 override 슬롯에 저장한다.

    ``fixtures`` 는 `server.spatial.pointing.pointing_commands` 와 같은 모양의
    ``(fid, (x, y, z))`` 시퀀스다. ``target`` 을 향한 Pan/Tilt 는
    `aim_pan_tilt` 로 계산하며, 기하가 성립하지 않거나(같은 자리) 틸트가
    한계를 넘으면 그 함수의 `SpatialPointingError` 가 그대로 올라온다 — 이
    모듈이 감싸지 않는 이유는 원인이 이 모듈의 거절(점유·안전답 누락)과
    다른 층의 사실이기 때문이다.

    거절(``OverrideLookError``):

    * ``fixtures`` 가 비었다.
    * ``safety`` 가 ``OverrideSafetyAnswers`` 인스턴스가 아니다(세 답 각각의
      명시-bool 검증은 그 클래스 생성 시점에 이미 끝나 있다).
    * ``occupied_slots`` 가 ``None`` — 점유를 못 쟀다.
    * ``preferred_slot`` 이 주어졌는데 후보 목록 밖이거나 이미 점유됐다.
    * 후보 목록 전체가 점유됐다(``preferred_slot`` 없이).
    * ``safety.stop_ifx``/``stop_pfx`` 가 True 인데 대응 원문 커맨드가 없다 —
      또는 그 반대(답이 False 인데 원문이 주어졌다, 모순 입력).
    * ``dimmer_pct``/``color_percents`` 가 0..100 밖이거나, ``zoom_degrees`` 가
      유한하지 않다.
    """
    if not isinstance(safety, OverrideSafetyAnswers):
        raise OverrideLookError(f"safety must be OverrideSafetyAnswers, got {safety!r}")
    fids = tuple(fixtures)
    if not fids:
        raise OverrideLookError("no fixtures selected for the override look")
    seen: set[int] = set()
    for fid, _position in fids:
        if fid in seen:
            raise OverrideLookError(f"fixture {fid!r} named twice")
        seen.add(fid)

    dimmer = _require_percent("dimmer_pct", dimmer_pct, maximum=_DIMMER_PERCENT_MAX)
    if len(color_percents) != 3:
        raise OverrideLookError(f"color_percents {color_percents!r} must be three values")
    percents = tuple(
        _require_percent(f"color_percents[{i}]", value, maximum=_COLOR_PERCENT_MAX)
        for i, value in enumerate(color_percents)
    )
    zoom = _require_finite_number("zoom_degrees", zoom_degrees)
    if zoom < 0.0:
        raise OverrideLookError(f"zoom_degrees {zoom_degrees!r} must be non-negative")

    for name, decided, raw_command in (
        ("stop_ifx", safety.stop_ifx, stop_ifx_command),
        ("stop_pfx", safety.stop_pfx, stop_pfx_command),
    ):
        if decided and not (isinstance(raw_command, str) and raw_command.strip()):
            raise OverrideLookError(
                f"safety.{name} is True but no {name}_command was supplied — this module "
                "does not guess the console command for stopping IFX/PFX"
            )
        if not decided and raw_command is not None:
            raise OverrideLookError(
                f"{name}_command was supplied but safety.{name} is False — contradictory input"
            )

    slot = _resolve_slot(
        occupied_slots=occupied_slots,
        available_slots=available_slots,
        preferred_slot=preferred_slot,
    )

    rotations = rotz_by_fid or {}
    aims: list[tuple[int, float, float]] = []
    commands: list[str] = []
    for fid, position in fids:
        pan, tilt = aim_pan_tilt(position, target.as_tuple(), rotz=rotations.get(fid, 0.0))
        aims.append((fid, pan, tilt))
        commands.append(
            _fixture_look_command(
                fid,
                pan,
                tilt,
                dimmer_pct=dimmer,
                color_percents=percents,
                zoom_degrees=zoom,
            )
        )

    if safety.stop_ifx:
        assert isinstance(stop_ifx_command, str)  # validated above
        commands.append(stop_ifx_command)
    if safety.stop_pfx:
        assert isinstance(stop_pfx_command, str)  # validated above
        commands.append(stop_pfx_command)

    commands.extend(preset_store_commands(pool_no, slot, label))

    return OverrideLookPlan(
        fixtures=tuple(fid for fid, _ in fids),
        target=target,
        aims=tuple(aims),
        dimmer_pct=dimmer,
        color_percents=percents,
        zoom_degrees=zoom,
        safety=safety,
        pool_no=pool_no,
        slot=slot,
        label=label,
        commands=tuple(commands),
    )
