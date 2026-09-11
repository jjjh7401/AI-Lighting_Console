"""룩의 움직임 선언을 콘솔 명령으로 옮기는 이음매 (정본 §6.2 · §6.4 · §12 항목 1).

정본은 `docs/proposals/song-structure-lighting-standard.md` 다.

**고치기 전에 실측한 것**(2026-09-11, main `28a0dc1`): `grep -rn "server.fx"
server/looks server/design` 이 0건이었다. 무빙 페이저는 `server/fx/library/movement.yaml`
에 실재하고 `Look.movement` 필드도 선언돼 있는데, 곡→큐 경로가 fx 계층을 한 번도 부르지
않으므로 룩 YAML 에 움직임을 적으면 **조용히 버려졌다**. 이 모듈이 그 통로다.

**왜 `MovementSpec` 만으로는 안 되는가.** `MovementSpec` 은 축·위상·속도·상대 진폭을
갖고 **스텝을 갖지 않는다**. 그런데 `Relative`/`Phase`/`Speed` 는 이미 있는 페이저를
**수정**할 뿐 만들지 못한다(`server/fx/schema.py` MIN_STEPS 의 @MX:ANCHOR, M0 실측).
선언된 줄을 그대로 내면 모든 줄이 ``ok:true`` 를 받고 무대는 가만히 있는다 — 되읽을 수도
없다. 그래서 이 모듈은 `MovementSpec` 을 **스텝 둘을 가진 `Fx`** 로 옮기고, 명령 문면은
`server.fx.instantiate.phaser_lines` **하나**에서만 나오게 한다. 진폭은 `relative` 가
주는 크기이며, 스텝 둘은 그 크기의 양끝(``-m`` · ``+m``)이다.

**관객 눈 하드룰의 절반만 기계로 막는다**(정본 §6.4). 정본은 두 가지를 요구한다 —
(가) 빔이 관객 한 명의 눈에 5초 넘게 머물러선 안 된다, (나) 빔은 관객 눈높이 위 20~30°
를 유지한다. 저장소에는 **객석 형상이 없다**: `server/spatial/schema.py` 의
`SpatialFixture` 는 장비의 x·y·z 만 갖고, 관객 좌표·눈높이·객석 깊이는 어디에도 없다
(실측: `grep -rn "eye_height|눈높이|house_depth" server` 0건). 그러므로 (나)는 못
막는다 — 빔이 어디를 가리키는지 이 계층은 모른다.

(가)의 **일부**는 막힌다. 정지한 위치를 얼마나 오래 쥐고 있는지에 상한을 거는 것이
그것이다: 속도는 BPM 이고(ASSUMPTION-38 GO, 콘솔 표시를 읽은 값), 한 바퀴의 주기는
``60 / BPM`` 초다. 5초 안에 최소 한 바퀴를 돌게 하려면 속도가 ``60 / 5 = 12`` BPM
이상이어야 한다 — 그것이 :data:`SPEED_FLOOR_BPM` 이고, 느린 대역의 바닥이다. 이 바닥은
빔이 **한 자리에 5초 이상 정지해 있는 것**을 막고, 빔이 어느 관객의 눈을 스쳐 지나가는
것은 막지 못한다. 후자를 막으려면 객석 형상과 Pan/Tilt→방향 사상이 둘 다 필요하다.

정적 Pan/Tilt 는 애초에 룩 스키마가 거절한다(`server/looks/schema.py` band 2) — 빔이
정지 위치로 「쉬는」 갈래가 데이터에 없다는 것이 이 상한의 전제다.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from server.fx.instantiate import phaser_lines
from server.fx.schema import ATTRIBUTE_VALUE_RANGE, Fx, FxStep, StepValue
from server.looks.schema import (
    DYNAMICS_MAX,
    DYNAMICS_MIN,
    MOVEMENT_ONLY_ATTRIBUTES,
    Look,
    MovementSpec,
)

__all__ = [
    "AMPLITUDE_UNDECLARED",
    "AMPLITUDE_UNUSABLE",
    "ATTRIBUTE_NOT_POSITION",
    "AXIS_REPEATED",
    "BAND_ORDER",
    "EYE_DWELL_LIMIT_SECONDS",
    "MOVEMENT_FAST",
    "MOVEMENT_MID",
    "MOVEMENT_SLOW",
    "MOVEMENT_STILL",
    "PHASE_CONFLICT",
    "SPEED_FLOOR_BPM",
    "SPEED_OUT_OF_BAND",
    "MovementError",
    "MovementPlan",
    "band_for_dynamics",
    "band_speed_range",
    "plan_movement",
    "stronger_band",
]

#: 정본 §6.4 의 세 대역 + 「무빙 정지」. 정지는 대역이 아니라 대역의 부재이지만, 이름을
#: 주지 않으면 「아직 안 정했다」와 구별되지 않는다.
MOVEMENT_STILL = "still"
MOVEMENT_SLOW = "slow"
MOVEMENT_MID = "mid"
MOVEMENT_FAST = "fast"

#: 약한 것부터 — 한 번들이 페이저 하나만 낼 수 있으므로 「가장 센 대역」을 고르는 데 쓴다.
BAND_ORDER: tuple[str, ...] = (MOVEMENT_STILL, MOVEMENT_SLOW, MOVEMENT_MID, MOVEMENT_FAST)

#: 정본 §6.4 의 하드룰 숫자. 이 값에서 :data:`SPEED_FLOOR_BPM` 이 나온다.
EYE_DWELL_LIMIT_SECONDS = 5.0

#: 5초 안에 한 바퀴를 돌기 위한 최소 BPM. 유도값이고 상수가 아니다 — 정본의 5초를
#: 바꾸면 이 바닥이 따라 움직인다.
SPEED_FLOOR_BPM = 60.0 / EYE_DWELL_LIMIT_SECONDS

#: 룰북 무드 표(31_choreography_patterns.md:236-241)가 준 두 대역의 경계 —
#: 10~20 warm/ballad, 90~180 energetic/club. `server/fx/library/movement.yaml`
#: 머리말이 같은 표를 시드로 인용하고, 그 파일의 느린 엔트리가 12~18, 빠른 엔트리가
#: 96~120 이라 이 경계 안에 있다. **중속 대역에는 인용된 숫자가 없다** — 표의 세 번째
#: 행("dramatic / accelerating")은 값이 비어 있다. 그래서 중속은 새 숫자를 만들지 않고
#: 인용된 두 대역 **사이**로 정의한다: 느린 대역의 천장부터 빠른 대역의 바닥까지.
_WARM_BAND_TOP = 20.0
_CLUB_BAND_FLOOR = 90.0
_CLUB_BAND_TOP = 180.0

#: 대역별 BPM 구간 (닫힌 구간). 느린 대역의 바닥은 룰북의 10 이 아니라 눈 하드룰이
#: 유도한 12 다 — 둘 중 **더 좁은** 쪽을 쓴다. 매핑 리터럴을 쓰지 않는 것은
#: `songcue.py` 와 같은 규율이고, 여기서는 순서까지 뜻이 있다(약→강).
_BAND_RANGES: tuple[tuple[str, float, float], ...] = (
    (MOVEMENT_SLOW, SPEED_FLOOR_BPM, _WARM_BAND_TOP),
    (MOVEMENT_MID, _WARM_BAND_TOP, _CLUB_BAND_FLOOR),
    (MOVEMENT_FAST, _CLUB_BAND_FLOOR, _CLUB_BAND_TOP),
)

#: 다이내믹스 1~5 → 대역. 정본 §6.4 의 문면 그대로다 — 느림 = 빌드·앰비언스,
#: 중속 = 그루브, **빠름 = 드롭 전용**. 그래서 빠름은 D5 하나뿐이고, 쇼의 대부분을
#: 차지하는 D2·D3 이 느림이다(§6.4 「약 70% 구간은 느린 무빙」과 같은 방향).
#: D1 은 정지다 — §6 표의 앰비언트·브레이크다운·솔로가 「무빙·이펙트 정지」다.
#:
#: 새 어휘를 만들지 않은 것이 요점이다: 구간 이름 → 다이내믹스는 이미
#: `server/looks/matching.py` `DYNAMICS_TERMS` 하나가 갖고 있고, 여기서 구간 라벨을
#: 다시 읽으면 그 어휘가 두 벌이 된다.
_DYNAMICS_BANDS: tuple[str, ...] = (
    MOVEMENT_STILL,
    MOVEMENT_SLOW,
    MOVEMENT_SLOW,
    MOVEMENT_MID,
    MOVEMENT_FAST,
)

# 왜 움직임을 낼 수 없는가. 합치지 않고 따로 두는 것은 이 저장소의 규율이다 — 각각
# 다른 사실이고 고치는 방법이 다르다.
ATTRIBUTE_NOT_POSITION = "movement_attribute_not_position"
AXIS_REPEATED = "movement_axis_repeated"
AMPLITUDE_UNDECLARED = "movement_amplitude_undeclared"
AMPLITUDE_UNUSABLE = "movement_amplitude_unusable"
PHASE_CONFLICT = "movement_phase_conflict"
SPEED_OUT_OF_BAND = "movement_speed_out_of_band"

#: 축이 하나면 좌우(또는 상하) 스윕, 둘이면 두 축이 함께 가는 대각선이다.
#: `circle` 은 못 만든다 — 원은 두 축을 1/4 주기 벌리는 것이고 그 관계는 패턴 종류가
#: 갖는데(`server/fx/instantiate.py` `_phase_lines`), `MovementSpec` 에는 패턴 필드가
#: 없다. 원을 원하면 스키마에 패턴 필드가 먼저 필요하다.
_PATTERN_BY_AXIS_COUNT: tuple[tuple[int, str], ...] = ((1, "sweep"), (2, "diagonal"))


class MovementError(ValueError):
    """움직임 선언을 페이저로 옮길 수 없다. ``reason`` 으로 사실에 분기한다."""

    def __init__(self, reason: str, message: str) -> None:
        self.reason = reason
        super().__init__(message)


@dataclass(frozen=True)
class MovementPlan:
    """한 큐가 실제로 낼 움직임 — 대역·속도·축, 그리고 그 명령 줄들."""

    band: str
    speed: float
    attributes: tuple[str, ...]
    pattern: str
    commands: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "band": self.band,
            "speed": self.speed,
            "pattern": self.pattern,
            "attributes": list(self.attributes),
            "commands": list(self.commands),
        }


def band_for_dynamics(dynamics: int) -> str:
    """이 세기의 움직임 대역 (정본 §6.4)."""
    if isinstance(dynamics, bool) or dynamics < DYNAMICS_MIN or dynamics > DYNAMICS_MAX:
        raise MovementError(
            SPEED_OUT_OF_BAND,
            f"dynamics must be between {DYNAMICS_MIN} and {DYNAMICS_MAX}: {dynamics!r}",
        )
    return _DYNAMICS_BANDS[dynamics - DYNAMICS_MIN]


def band_speed_range(band: str) -> tuple[float, float]:
    """이 대역이 허용하는 BPM 구간. 정지 대역은 구간이 없다."""
    for name, low, high in _BAND_RANGES:
        if name == band:
            return low, high
    raise MovementError(SPEED_OUT_OF_BAND, f"band {band!r} carries no speed range")


def stronger_band(left: str, right: str) -> str:
    """두 대역 중 더 센 쪽 — 한 번들이 페이저 하나만 낼 때 어느 큐가 그것을 갖는가."""
    return left if BAND_ORDER.index(left) >= BAND_ORDER.index(right) else right


def plan_movement(look: Look, *, band: str) -> MovementPlan | None:
    """이 룩의 움직임을 이 대역으로 낸 계획. 낼 것이 없으면 ``None``.

    ``None`` 은 두 갈래다 — 룩이 움직임을 선언하지 않았거나, 대역이 정지다. 둘 다
    「낼 것이 없다」이고 결함이 아니다. 선언은 있는데 페이저로 옮길 수 없는 경우는
    ``None`` 이 아니라 :class:`MovementError` 다: 조용히 버리는 것이 이 카드가
    없애려는 결함 그대로이기 때문이다.
    """
    if not look.movement or band == MOVEMENT_STILL:
        return None
    attributes = _attributes_of(look.movement)
    amplitudes = tuple(
        _amplitude_of(spec, name) for spec, name in zip(look.movement, attributes, strict=True)
    )
    phase_from, phase_to = _phase_of(look.movement)
    speed = _speed_of(look.movement, band=band)
    fx = Fx(
        fx_id=f"look-{look.look_id}-{band}",
        display_name=look.display_name,
        pattern=_pattern_of(attributes),
        steps=(
            FxStep(values=_step_values(attributes, amplitudes, sign=-1.0)),
            FxStep(values=_step_values(attributes, amplitudes, sign=1.0)),
        ),
        phase_from=phase_from,
        phase_to=phase_to,
        speed=speed,
        relative=True,
    )
    return MovementPlan(
        band=band,
        speed=speed,
        attributes=attributes,
        pattern=fx.pattern,
        commands=phaser_lines(fx),
    )


def _step_values(
    attributes: Sequence[str], amplitudes: Sequence[float], *, sign: float
) -> tuple[StepValue, ...]:
    return tuple(
        StepValue(attribute=name, value=sign * size)
        for name, size in zip(attributes, amplitudes, strict=True)
    )


def _attributes_of(specs: Sequence[MovementSpec]) -> tuple[str, ...]:
    seen: list[str] = []
    for spec in specs:
        if spec.attribute not in MOVEMENT_ONLY_ATTRIBUTES:
            raise MovementError(
                ATTRIBUTE_NOT_POSITION,
                f"movement attribute {spec.attribute!r} is not a position axis; this "
                f"seam emits only {list(MOVEMENT_ONLY_ATTRIBUTES)} — an intensity or "
                "colour phaser is a different effect and out of this card's scope",
            )
        if spec.attribute in seen:
            raise MovementError(
                AXIS_REPEATED,
                f"movement declares {spec.attribute!r} twice; one Fx carries one step "
                "value per attribute, so the second declaration would silently win",
            )
        seen.append(spec.attribute)
    return tuple(seen)


def _amplitude_of(spec: MovementSpec, attribute: str) -> float:
    if spec.relative is None:
        raise MovementError(
            AMPLITUDE_UNDECLARED,
            f"movement on {attribute!r} declares no 'relative' amplitude, so no step "
            "run can be built; `Phase`/`Speed`/`Relative` MODIFY a phaser and cannot "
            "create one, so emitting the declaration alone returns ok:true on every "
            "line and leaves the stage still",
        )
    size = abs(float(spec.relative))
    low, high = ATTRIBUTE_VALUE_RANGE[attribute]
    if size == 0.0 or -size < low or size > high:
        raise MovementError(
            AMPLITUDE_UNUSABLE,
            f"movement on {attribute!r} has amplitude {spec.relative!r}; the two steps "
            "are -n and +n, so zero emits one repeated value line (the dedupe drops it "
            "and the phaser loses a step) and the swing must stay inside "
            f"[{low}, {high}]",
        )
    return size


def _phase_of(specs: Sequence[MovementSpec]) -> tuple[float | None, float | None]:
    """엔트리 하나가 위상 쌍 하나를 갖는다 — 축마다 다른 위상은 담을 자리가 없다."""
    pairs = {(spec.phase_from, spec.phase_to) for spec in specs}
    if len(pairs) > 1:
        raise MovementError(
            PHASE_CONFLICT,
            f"movement declares {len(pairs)} different phase pairs; one phaser carries "
            "one phase pair for the whole entry, so picking either would make the other "
            "declaration read as configured while emitting nothing",
        )
    phase_from, phase_to = next(iter(pairs))
    return phase_from, phase_to


def _speed_of(specs: Sequence[MovementSpec], *, band: str) -> float:
    """대역이 속도를 정한다. 룩이 적은 속도는 그 대역 **안에서만** 존중된다.

    대역 밖의 값을 조용히 끌어오지 않는 이유는 방향이 둘 다 나쁘기 때문이다 — 올리면
    저자가 원한 「아주 느림」이 사라지고, 내리면 드롭이 드롭이 아니게 된다. 그리고
    아래쪽 경계는 취향이 아니라 관객 눈 하드룰이다(모듈 머리).
    """
    low, high = band_speed_range(band)
    authored = {spec.speed for spec in specs if spec.speed is not None}
    if not authored:
        return low
    if len(authored) > 1:
        raise MovementError(
            SPEED_OUT_OF_BAND,
            f"movement declares {len(authored)} different speeds; one phaser runs at one speed",
        )
    speed = float(next(iter(authored)))
    if speed < low or speed > high:
        raise MovementError(
            SPEED_OUT_OF_BAND,
            f"movement declares speed {speed} BPM, outside the {band!r} band "
            f"[{low}, {high}] this section routes to (정본 §6.4). Below "
            f"{SPEED_FLOOR_BPM} BPM one cycle takes longer than "
            f"{EYE_DWELL_LIMIT_SECONDS} s, which is the audience-eye hard rule",
        )
    return speed


def _pattern_of(attributes: Sequence[str]) -> str:
    for count, pattern in _PATTERN_BY_AXIS_COUNT:
        if len(attributes) == count:
            return pattern
    raise MovementError(
        ATTRIBUTE_NOT_POSITION,
        f"no pattern kind covers {len(attributes)} position axes; only "
        f"{list(MOVEMENT_ONLY_ATTRIBUTES)} exist as position axes",
    )
