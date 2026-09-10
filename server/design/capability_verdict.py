"""장비 능력 -> **계획 단계 판정** — 이 기종에 이 프리셋을 줘도 되는가.

t344 B. A 편(:mod:`server.design.capability_join`)은 「이 fid 가 무엇을 조정할 수
있는가」까지 읽고 멈췄고, 비테스트 호출자가 0 이었다. 이 모듈이 그 판독을 **연출
계획의 거절**로 바꾼다 — 그리고 :mod:`server.web.session` 이 이것을 부른다.

## 두 가지 거절 (감독 지시 2026-09-10)

1. **팬틸트 없는 기종에 포지션 프리셋을 주지 않는다.** 고정 장비(리그 실측 15기종 중
   4기종)는 헤드를 못 돌리므로 포지션 프리셋이 닿을 축이 없다. 계획 단계에서
   **이름 대어** 거절한다 — 조용히 빠뜨리면 감독은 그 기종이 포함된 줄 안다.
2. **측정된 범위 밖 값은 보류한다(clamp 하지 않는다).** MegaPointe Zoom 은 실측
   42.0 -> 1.8 이다. 45° 요구는 범위 밖이고, 그때 조용히 42 로 깎으면 감독이 요구한
   것과 콘솔에 가는 것이 달라진다. :class:`RangeVerdict` 는 **보류 사유에 측정 범위를
   싣는다**.

## 어휘 표는 **의도적으로 부분집합**이다

오늘 어떤 소비자든 실제로 읽는 능력 이름은 하나뿐이다 —
``energy.EFFECT_AXIS_CAPABILITY`` (``"effect"``, :mod:`server.design.energy` 에서
소비). 그래서 이 표는 이 카드가 필요한 두 개만 싣는다:

    Pan · Tilt  -> POSITION_CAPABILITY   포지션 프리셋 가능 여부
    Zoom        -> ZOOM_CAPABILITY       줌 범위 대조 대상

🔴 ``"effect"`` 는 **일부러 매핑하지 않는다.** 어떤 속성이 있으면 이펙트 축이
열리는지는 이 저장소에서 측정된 바가 없다. 여기서 지어 넣으면
``energy.axis_budget`` 이 추측 위에서 이펙트 어휘를 열고, 그 거짓은 실패가 아니라
**조용히 잘못된 큐**로 나타난다. 전체 어휘 표는 후속 카드다.

## 방향과 미판독

🔴 **:class:`AxisRange` 를 정렬하지 않는다.** 방향이 어느 끝이 DMX 0 인지를 나른다
(A 편·``capability_read`` 독스트링). 범위 대조는 두 끝에서 지역 최소/최대를
**계산**할 뿐 축 자체를 건드리지 않는다.

🔴 **부재와 미판독을 가른다.** 판독이 부분(``FixtureCapability.whole`` 이 거짓)인
기종은 「팬틸트가 없다」고 단정하지 않고 :attr:`PositionVerdict.unknown` 에 앉는다.
잘린 목록으로 거절하면 있는 장비를 없다고 말한다.

**읽기 전용.** 이 모듈은 콘솔에 쓰지 않는다.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from server.design.capability_join import FixtureCapability, RigCapabilities
from server.prechk.capability_read import AxisRange

__all__ = [
    "CAPABILITY_VOCABULARY",
    "PAN_ATTRIBUTE",
    "POSITION_CAPABILITY",
    "TILT_ATTRIBUTE",
    "ZOOM_ATTRIBUTE",
    "ZOOM_CAPABILITY",
    "PositionVerdict",
    "RangeVerdict",
    "VERDICT_ABSENT",
    "VERDICT_HELD",
    "VERDICT_OK",
    "VERDICT_UNMEASURED",
    "axis_for_type",
    "patch_records",
    "position_verdict",
    "range_verdict",
    "type_names_of",
]

#: 콘솔이 답한 속성 철자 그대로. A 편이 이름을 바꾸지 않고 나르므로 대조도
#: 그 철자로 한다(대소문자만 무관 — ``has_attribute`` 의 계약).
PAN_ATTRIBUTE = "Pan"
TILT_ATTRIBUTE = "Tilt"
ZOOM_ATTRIBUTE = "Zoom"

#: 소비자가 읽는 능력 이름. ``rig.RigFixtureRecord.capabilities`` 에 실린다.
POSITION_CAPABILITY = "position"
ZOOM_CAPABILITY = "zoom"

#: 능력 이름 -> 그것을 여는 속성들. **any-of** 다: Pan 만 있는 장비도 헤드가
#: 움직이므로 포지션이 닿는다. all-of 로 하면 Tilt 전용 장비가 거절된다.
CAPABILITY_VOCABULARY: Mapping[str, tuple[str, ...]] = {
    POSITION_CAPABILITY: (PAN_ATTRIBUTE, TILT_ATTRIBUTE),
    ZOOM_CAPABILITY: (ZOOM_ATTRIBUTE,),
}

#: :class:`RangeVerdict` 의 네 갈래. 「범위 밖」과 「범위를 못 읽었다」와 「그 축이
#: 없다」는 서로 다른 사실이고, 감독에게 할 말도 다르다.
VERDICT_OK = "ok"
VERDICT_HELD = "held"
VERDICT_UNMEASURED = "unmeasured"
VERDICT_ABSENT = "absent"


def _capabilities_of(capability: FixtureCapability) -> frozenset[str]:
    """한 fid 가 여는 능력 이름들 — 표에 있는 것만, any-of 로."""
    return frozenset(
        name
        for name, attributes in CAPABILITY_VOCABULARY.items()
        if any(capability.has_attribute(attribute) for attribute in attributes)
    )


def patch_records(caps: RigCapabilities) -> tuple[dict[str, object], ...]:
    """``build_rig_profile(patch=...)`` 가 받는 레코드 목록.

    못 읽은 fid(:attr:`RigCapabilities.unread`)는 **실리지 않는다**. 능력 없는
    레코드로 실으면 ``RigFixtureRecord`` 의 「빈 집합 = 미선언」이 「능력 없음」으로
    읽히고, 그 침묵이 바로 이 카드가 막는 거짓 부재다. 실리지 않은 fid 는
    ``unread`` 에 사유와 함께 남아 호출자가 고지한다.
    """
    return tuple(
        {
            "fid": fid,
            "type_name": capability.type_name,
            "capabilities": sorted(_capabilities_of(capability)),
        }
        for fid, capability in sorted(caps.fixtures.items())
    )


@dataclass(frozen=True)
class PositionVerdict:
    """포지션 프리셋을 줄 수 있는 기종과 **거절되는 기종**.

    세 갈래를 따로 둔다. ``refused`` 는 전수 판독에서 Pan·Tilt 가 **둘 다** 없던
    기종이고, ``unknown`` 은 판독이 부분이라 단정할 수 없는 기종이다. 둘을 합치면
    잘린 판독이 거절 근거가 되어 있는 장비를 없다고 말한다.
    """

    allowed: tuple[str, ...] = ()
    refused: tuple[str, ...] = ()
    unknown: tuple[str, ...] = ()

    @property
    def any_positionable(self) -> bool:
        """포지션 축을 세울 수 있는가. 미판독 기종은 **막지 않는다** —
        부분 판독을 근거로 축을 닫으면 있는 장비의 포지션을 잃는다."""
        return bool(self.allowed) or bool(self.unknown)

    def reason(self) -> str:
        """거절 사유 한 줄 — 거절이 없으면 빈 문자열.

        문면에 기종 이름을 싣는다. 「거절됨」만 있는 사유는 참 거절과 거짓 거절을
        구별할 수 없고, 이 저장소는 그 실패를 이미 겪었다(t112).
        """
        if not self.refused:
            return ""
        parts = [f"팬/틸트가 없어 포지션 프리셋을 만들지 않은 기종: {', '.join(self.refused)}"]
        if self.unknown:
            parts.append(f"능력 판독이 부분이라 판정을 보류한 기종: {', '.join(self.unknown)}")
        return " · ".join(parts)


def position_verdict(caps: RigCapabilities) -> PositionVerdict:
    """기종 단위 포지션 판정. **fid 가 아니라 타입** 이 단위다.

    능력은 개별 장비의 성질이 아니라 기종(FixtureType)의 성질이다 — 같은 기종의
    두 fid 가 서로 다른 축을 가질 수는 없다. 그래서 판정도 기종별로 한 번만 내고,
    같은 기종의 fid 를 여러 번 세지 않는다.
    """
    allowed: dict[str, None] = {}
    refused: dict[str, None] = {}
    unknown: dict[str, None] = {}
    for capability in caps.fixtures.values():
        name = capability.type_name
        movable = capability.has_attribute(PAN_ATTRIBUTE) or capability.has_attribute(
            TILT_ATTRIBUTE
        )
        if movable:
            allowed[name] = None
        elif capability.whole:
            refused[name] = None
        else:
            # 부분 판독 — 목록에 없다는 것이 부재의 증거가 아니다.
            unknown[name] = None
    # 한 기종이 두 갈래에 동시에 앉는 일은 없어야 하지만, 모드가 다르면 축이
    # 달라질 수 있다. 그때는 **가능**이 이긴다: 하나라도 움직이는 모드가 있으면
    # 그 기종에 포지션이 닿는다.
    for name in allowed:
        refused.pop(name, None)
        unknown.pop(name, None)
    for name in refused:
        unknown.pop(name, None)
    return PositionVerdict(
        allowed=tuple(sorted(allowed)),
        refused=tuple(sorted(refused)),
        unknown=tuple(sorted(unknown)),
    )


@dataclass(frozen=True)
class RangeVerdict:
    """요구한 값이 그 축의 **측정된** 범위 안인가.

    ``status`` 가 :data:`VERDICT_HELD` 면 값을 깎지 않고 **보류**한다. clamp 는
    감독이 요구한 값과 콘솔에 가는 값을 조용히 다르게 만든다.
    """

    status: str
    attribute: str
    requested: float
    low: float | None = None
    high: float | None = None
    descending: bool | None = None
    detail: str = ""

    @property
    def held(self) -> bool:
        return self.status == VERDICT_HELD


def range_verdict(
    axis: AxisRange | None, requested: float, *, attribute: str | None = None
) -> RangeVerdict:
    """``requested`` 를 축의 물리 범위와 대조한다. **정렬하지 않는다.**

    ``axis`` 가 ``None`` 이면 그 축이 이 목록에 없다(:data:`VERDICT_ABSENT`) —
    호출자는 그 판독이 전수였는지(:attr:`FixtureCapability.whole`)를 함께 봐야
    「없다」와 「못 읽었다」를 가를 수 있다.

    범위 두 끝 중 하나라도 안 읽혔으면 :data:`VERDICT_UNMEASURED` 다. 이때 통과로
    처리하지 않는다 — 안 잰 범위는 안전장치가 아니다.

    단위는 속성마다 다르다(Frost 0~1 정규화, Zoom 도). 이 함수는 숫자만 대조하고
    단위를 추론하지 않는다.
    """
    name = attribute if attribute is not None else (axis.attribute if axis else "?")
    if axis is None:
        return RangeVerdict(
            status=VERDICT_ABSENT,
            attribute=name,
            requested=requested,
            detail=f"{name} 축이 판독 목록에 없습니다",
        )
    if not axis.measurable:
        return RangeVerdict(
            status=VERDICT_UNMEASURED,
            attribute=axis.attribute,
            requested=requested,
            low=None,
            high=None,
            descending=axis.descending,
            detail=f"{axis.attribute} 물리 범위를 읽지 못해 대조하지 못했습니다",
        )
    # 정렬이 아니라 **계산**이다. `axis` 는 읽은 방향 그대로 남고, 여기서 만든
    # 두 수는 대조에만 쓰인다. Zoom(42.0 -> 1.8)이 이 갈래의 실측 예다.
    first = axis.physical_from
    second = axis.physical_to
    if first is None or second is None:  # measurable 가 이미 막지만 타입을 좁힌다
        return RangeVerdict(
            status=VERDICT_UNMEASURED,
            attribute=axis.attribute,
            requested=requested,
            descending=axis.descending,
            detail=f"{axis.attribute} 물리 범위를 읽지 못해 대조하지 못했습니다",
        )
    low = min(first, second)
    high = max(first, second)
    if low <= requested <= high:
        return RangeVerdict(
            status=VERDICT_OK,
            attribute=axis.attribute,
            requested=requested,
            low=low,
            high=high,
            descending=axis.descending,
        )
    return RangeVerdict(
        status=VERDICT_HELD,
        attribute=axis.attribute,
        requested=requested,
        low=low,
        high=high,
        descending=axis.descending,
        detail=(
            f"{axis.attribute} 요구값 {requested:g} 이 측정 범위 "
            f"{first:g}~{second:g} 밖이라 보류했습니다 (값을 깎지 않았습니다)"
        ),
    )


def axis_for_type(
    caps: RigCapabilities, type_name: str, attribute: str
) -> tuple[AxisRange | None, bool]:
    """``(축, 전수였는가)`` — 기종 이름으로 축 하나를 찾는다.

    능력은 기종의 성질이라 fid 를 고를 필요가 없다. 첫 일치 fid 의 판독을 쓰되
    **전수 여부**를 함께 돌려준다: 거짓이면 ``None`` 을 부재로 읽어서는 안 된다.
    """
    for capability in caps.fixtures.values():
        if capability.type_name != type_name:
            continue
        found = capability.axis(attribute)
        if found is not None:
            return found, capability.whole
        if capability.whole:
            return None, True
    return None, False


def type_names_of(records: Sequence[Mapping[str, object]]) -> tuple[str, ...]:
    """``patch_records`` 결과에 실린 기종 이름들 — 진단·고지용."""
    seen: dict[str, None] = {}
    for record in records:
        name = record.get("type_name")
        if isinstance(name, str) and name:
            seen[name] = None
    return tuple(sorted(seen))
