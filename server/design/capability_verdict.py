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

## 어휘 표 — 이제 세 개 (M6, t501, 2026-10-01)

    Pan · Tilt  -> POSITION_CAPABILITY   포지션 프리셋 가능 여부
    Zoom        -> ZOOM_CAPABILITY       줌 범위 대조 대상
    Dimmer      -> EFFECT_CAPABILITY     이펙트(페이저) 축 가능 여부 (``energy.
                                          EFFECT_AXIS_CAPABILITY``, ``"effect"``)

🔴 **이전 버전은 ``"effect"`` 를 일부러 매핑하지 않았다**(M1, `.moai/reports/
t501/M1.md`) — "effect" 가 ``CAPABILITY_VOCABULARY`` 에 없어 8곡 전부
``rig.has_capability("effect")`` 가 ``False`` 로 고정되고, ``energy._fx_axes``
가 항상 예산 0을 돌려줬다(`fx.permitted` 가 요청 유무와 무관하게 늘 빈
튜플). 이 어휘 공백을 메우는 처방은 **``Dimmer``** 다 — 아래가 그 근거다
(추측 아님, 추측을 하지 않는다는 이 모듈의 원칙을 그대로 지킨다):

1. ``docs/proposals/song-lighting-design-standard.md`` §4d F1(이펙트 축별
   용도표)이 "디머 체이스·펄스=리듬 강조(D3+)"를 이펙트 어휘의 정식 항목으로
   적는다 — Dimmer 체이스는 **발명이 아니라 정본에 이미 있는** 이펙트 축이다.
2. ``server/fx/library/dimmer.yaml``(FXLIB 이펙트 라이브러리, 이미 검증·운용
   중)의 모든 항목이 ``Dimmer`` 속성 하나만 스텝에 싣는다 — 전수 확인
   (``grep -En "Attribute|attribute" server/fx/library/dimmer.yaml``에
   ``ColorRGB``·``Pan``·``Tilt``·``Strobe`` 0건). 이것은 이 저장소가 "디머
   페이저"로 이미 운용 중인 축이 정확히 ``Dimmer`` 하나임을 확인한다.
3. 실기 판독(`.moai/reports/t241/verdict.md` §2, 리그 8기종 전수 — 패치/
   DMXModes 조회)이 ``Dimmer`` 애트리뷰트의 실제 보급을 측정했다: 84/86
   (HAZE 2대 제외 전부). 효과 역할 그룹(BLIND/STROBE)도 포함된다 — BLIND
   (CuePix Blinder WW2) Dimmer ✓, STROBE(Atomic 3000 LED) Dimmer ✓. 이것이
   "effect" 능력을 켜는 폭넓고 측정 가능한 신호다.
4. **``"Strobe"``/``"Shutter"`` 는 이 자리의 근거가 될 수 없다** — 이전
   추정(M1 `measure_fx_permitted_zero.py`)이 Strobe/Shutter 선언을 가정했지만,
   이 저장소 자신이 그 경로를 명시적으로 범위 밖으로 닫아 뒀다
   (``server/looks/schema.py:16-18`` "Strobe and shutter are out of scope
   regardless: `server/web/preview.py:131-139` classifies them `danger`")
   — 그리고 ``server/fx/library/{movement,color,dimmer}.yaml`` 전수 확인
   (``grep -rn "Strobe" server/fx/library/``) 결과 0건, FXLIB 가 실제로
   생성하는 어떤 이펙트도 Strobe 축을 건드리지 않는다. 또한 실기 판독
   (`.moai/reports/t442/run7_dmx_channels.txt`)은 ``Strobe1``(모든 기종에
   보급된 범용 셔터 메커니즘 채널)과 ``StrobeMode``/``StrobeDuration``
   (8기종 중 Atomic **하나뿐**)을 구별한다 — 둘 중 어느 쪽으로 게이트를
   잡아도 F1 의 "디머 체이스" 축과 무관하고, 전자는 보급이 너무 넓어
   무의미하며 후자는 FXLIB 가 아예 소비하지 않는 축이다.

에너지 모듈 자신의 docstring(``energy.py:19-22``)이 "이 축은 아직 효과
종류별로 예산을 쪼개지 않는다 — F1 의 어휘가 넓어지면 종류별 능력으로
나눌 수 있다"고 이미 말하고 있다 — 지금은 **하나의** 능력이 F3 전체
(무빙·디머·컬러·줌 네 축 공통) 예산을 여닫는 스탠드인이고, 이 처방은
F1 이 꼽는 네 축 중 가장 보편적이고 FXLIB 가 이미 전량 소비하는 축(Dimmer)
을 그 스탠드인으로 삼는다.

## 방향과 미판독

🔴 **:class:`AxisRange` 를 정렬하지 않는다.** 방향이 어느 끝이 DMX 0 인지를 나른다
(A 편·``capability_read`` 독스트링). 범위 대조는 축 자신의 술어
(:meth:`AxisRange.window`)가 파생한 :class:`~server.prechk.capability_read.AxisWindow`
로 하고, 그 창은 정렬된 두 끝과 **방향을 따로** 나른다 — 축 자체는 건드리지 않는다.

t351 이 그 술어를 축으로 옮겼다. 이전에는 이 모듈과 ``lxseq.preset_parser`` 가 각자
``min``/``max`` 를 계산했고, 같은 판정이 두 자리에 있으면 갈리는 날 한쪽만 고쳐진다.

🔴 **부재와 미판독을 가른다.** 판독이 부분(``FixtureCapability.whole`` 이 거짓)인
기종은 「팬틸트가 없다」고 단정하지 않고 :attr:`PositionVerdict.unknown` 에 앉는다.
잘린 목록으로 거절하면 있는 장비를 없다고 말한다.

**읽기 전용.** 이 모듈은 콘솔에 쓰지 않는다.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from server.design.capability_join import FixtureCapability, RigCapabilities
from server.prechk.capability_read import (
    AXIS_PART_FIXTURE_TYPE,
    AxisRange,
    AxisSource,
    AxisWindow,
    AxisWindowPart,
)

__all__ = [
    "CAPABILITY_VOCABULARY",
    "DIMMER_ATTRIBUTE",
    "EFFECT_CAPABILITY",
    "PAN_ATTRIBUTE",
    "POSITION_CAPABILITY",
    "TILT_ATTRIBUTE",
    "ZOOM_ATTRIBUTE",
    "ZOOM_CAPABILITY",
    "GroupCapabilities",
    "PositionVerdict",
    "RangeVerdict",
    "VERDICT_ABSENT",
    "VERDICT_HELD",
    "VERDICT_OK",
    "VERDICT_UNMEASURED",
    "axis_for_type",
    "group_capabilities",
    "group_capability_source",
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
#: M6(t501) — 실측 전수 애트리뷰트 이름("Dimmer", `reviewed_song_commands`
#: 의 모든 디머 커맨드와 같은 철자). 위 모듈 독스트링 §어휘 표의 근거 1-4 참조.
DIMMER_ATTRIBUTE = "Dimmer"

#: 소비자가 읽는 능력 이름. ``rig.RigFixtureRecord.capabilities`` 에 실린다.
POSITION_CAPABILITY = "position"
ZOOM_CAPABILITY = "zoom"
#: ``energy.EFFECT_AXIS_CAPABILITY`` 와 바이트 동일한 문자열 — 그 상수를
#: import 하지 않는 이유는 기존 구조 그대로다(이 모듈은 energy.py 를
#: import 하지 않는다, 순환 의존 회피).
EFFECT_CAPABILITY = "effect"

#: 능력 이름 -> 그것을 여는 속성들. **any-of** 다: Pan 만 있는 장비도 헤드가
#: 움직이므로 포지션이 닿는다. all-of 로 하면 Tilt 전용 장비가 거절된다.
CAPABILITY_VOCABULARY: Mapping[str, tuple[str, ...]] = {
    POSITION_CAPABILITY: (PAN_ATTRIBUTE, TILT_ATTRIBUTE),
    ZOOM_CAPABILITY: (ZOOM_ATTRIBUTE,),
    EFFECT_CAPABILITY: (DIMMER_ATTRIBUTE,),
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
    # 🔴 포함 검사는 **축 자신의 술어**(`AxisRange.window`)를 쓴다. 정렬이 아니라
    # 계산이고, `axis` 는 읽은 방향 그대로 남는다 — Zoom(42.0 -> 1.8)이 이 갈래의
    # 실측 예다. 여기서 `min`/`max` 를 다시 적으면 이 저장소에 포함-검사 술어가 둘이
    # 되고(t351 이 합친 상태), 그 둘이 갈리는 날 한쪽만 고쳐진다.
    window = axis.window()
    if window is None:
        return RangeVerdict(
            status=VERDICT_UNMEASURED,
            attribute=axis.attribute,
            requested=requested,
            low=None,
            high=None,
            descending=axis.descending,
            detail=f"{axis.attribute} 물리 범위를 읽지 못해 대조하지 못했습니다",
        )
    if window.contains(requested):
        return RangeVerdict(
            status=VERDICT_OK,
            attribute=axis.attribute,
            requested=requested,
            low=window.low,
            high=window.high,
            descending=window.descending,
        )
    return RangeVerdict(
        status=VERDICT_HELD,
        attribute=axis.attribute,
        requested=requested,
        low=window.low,
        high=window.high,
        descending=window.descending,
        detail=(
            f"{axis.attribute} 요구값 {requested:g} 이 측정 범위 "
            f"{axis.physical_from:g}~{axis.physical_to:g} 밖이라 보류했습니다"
            " (값을 깎지 않았습니다)"
        ),
    )


@dataclass(frozen=True)
class GroupCapabilities:
    """한 TargetGroup 이 낼 수 있는 값 — **기종마다 따로** 읽은 채로.

    시트의 `TargetGroup` 은 fid 여럿을 가리키고, 그 fid 들이 **같은 기종이 아닐 수
    있다.** 정본 리그 실측(`LXSEQ_RIG_01_ShowBase_r3.patch.csv`, 2026-09-11):

        MOVER-ALL = MOVER-U + MOVER-D
        MOVER-U   Robe MegaPointe   Mode 1 39ch    8대
        MOVER-D   Robe Spiider      Mode 1 49ch    8대

    두 기종이다. 그래서 「그 그룹이 이 값을 낼 수 있는가」는 한 축으로 답할 수 없다.

    ## 채택한 규칙 — 교집합. 하나라도 못 내면 보류한다

    :meth:`window` 는 그룹의 기종들이 **공통으로** 낼 수 있는 창(교집합)을 낸다.
    값이 그 밖이면 적어도 한 기종이 그 값을 못 내고, 그때 그 행은 보류된다.

    왜 교집합인가 — 프리셋은 **그룹 전체에 한 값**으로 간다. 절반만 낼 수 있는 값을
    통과시키면 콘솔은 못 내는 장비 쪽에서 값을 잘라 받고, 되읽기는 슬롯 점유만
    확인하므로(t108·t110) 그 절단이 **아무 신호도 내지 않는다.** 감독이 요구한 룩과
    무대에 서는 룩이 조용히 달라지는 것이 이 규칙이 막는 실패다. 합집합(하나라도 낼
    수 있으면 통과)은 바로 그 조용한 절단을 허용한다.

    보류 문면은 **어느 기종이 거절했는지 이름을 댄다**(:meth:`AxisWindow.excluding`).
    「거절됨」만 있는 사유는 참 거절과 거짓 거절을 구별할 수 없다(t112).

    ## 이 판정이 **하지 않는** 것 — 세 경계

    1. **축이 없는 기종은 이 판정에 안 든다.** Frost 는 리그 15기종 중 4기종에만
       있다. 축이 아예 없는 것은 「범위 밖」이 아니라 **부재**이고, 그 사유는 t348 의
       `axis_absent` 문턱이 이미 소유한다. 여기서 같이 들면 한 사실에 사유가 둘이 되고
       감독은 무엇을 고쳐야 하는지 못 읽는다.
    2. **미판독은 결함이 아니다.** 두 끝이 안 읽힌 축은 창을 못 만들므로 교집합에
       기여하지 않는다(`AxisRange.window` 가 ``None``). 못 읽은 범위로 막으면
       미판독이 결함으로 바뀐다.
    3. **단위가 다른 축은 빼고 좁힌다.** ``exclude_normalized`` 가 참이면 0~1 모양
       축은 교집합에서 제외된다 — 도 값과 대조 자체가 성립하지 않는다. 🔴 그 제외는
       **사유 문면에 안 실린다**(t351 이 남긴 미검증 자리): 감독은 그 기종이 판정에서
       빠진 것을 문면에서 못 읽는다.

    ``missing_fids`` 는 그룹 명단에 있는데 능력 판독에 없는 fid 들이다. 비어 있지
    않으면 이 판정은 **부분집합**에 대한 것이고, 호출자가 그 사실을 고지한다 —
    조용히 줄어든 그룹은 「장비가 적은 그룹」과 바이트 동일하다.
    """

    group_name: str
    per_type: Mapping[str, AxisSource] = field(default_factory=dict)
    fids: tuple[int, ...] = ()
    missing_fids: tuple[int, ...] = ()

    @property
    def type_names(self) -> tuple[str, ...]:
        """이 그룹에서 능력이 읽힌 기종 이름들 — 정렬해서."""
        return tuple(sorted(self.per_type))

    @property
    def whole(self) -> bool:
        """그룹 명단 전부의 능력을 읽었는가. 거짓이면 판정은 부분집합에 대한 것이다."""
        return not self.missing_fids

    def window(self, attribute: str, *, exclude_normalized: bool = False) -> AxisWindow | None:
        """그룹이 **공통으로** 낼 수 있는 창. 기여하는 축이 없으면 ``None``.

        ``None`` 은 「범위 밖이 아니다」가 아니라 **「대조할 수 없다」**다 — 축이 아무
        기종에도 없거나, 있는 축의 범위를 아무도 못 읽었거나, 단위가 다 어긋났다는
        뜻이다. 소비자는 이것을 통과로 처리하면 안 된다.

        방향(:attr:`AxisWindow.descending`)은 기여한 축들이 **한 방향으로 일치할
        때만** 실린다. 갈리면 ``None`` — 한쪽을 골라 적는 것은 안 잰 방향을 단정하는
        것이다. 포함 검사 자체는 방향과 무관하므로 이 불확정이 판정을 막지 않는다.
        """
        parts: list[AxisWindowPart] = []
        directions: set[bool | None] = set()
        for type_name in sorted(self.per_type):
            axis = self.per_type[type_name].axis(attribute)
            if axis is None:
                # 경계 1 — 축 부재는 t348 의 몫이다. 여기서 들지 않는다.
                continue
            found = axis.window()
            if found is None:
                continue  # 경계 2 — 미판독
            if exclude_normalized and found.normalized:
                continue  # 경계 3 — 단위 불일치
            parts.append(
                AxisWindowPart(
                    name=type_name,
                    low=found.low,
                    high=found.high,
                    # 기종 이름이라고 **선언**한다. 개수로 추론하게 두면 기종이 하나
                    # 뿐인 그룹의 창이 「채널 이름」으로 읽힌다(t351 이 밟은 자리).
                    role=AXIS_PART_FIXTURE_TYPE,
                )
            )
            directions.add(found.descending)
        if not parts:
            return None
        # 교집합: 가장 높은 하한과 가장 낮은 상한. `low > high` 면 공통 창이 없다 —
        # `AxisWindow.empty` 가 그 상태를 말하고, 그때 어떤 도 값도 걸린다(옳다:
        # 그 그룹은 어떤 각도도 전부가 함께 낼 수 없다).
        return AxisWindow(
            attribute=attribute,
            low=max(part.low for part in parts),
            high=min(part.high for part in parts),
            descending=directions.pop() if len(directions) == 1 else None,
            parts=tuple(parts),
        )


def group_capabilities(
    caps: RigCapabilities, group_name: str, fids: Sequence[int]
) -> GroupCapabilities:
    """그룹 명단(fid 들)을 그 그룹의 **기종별** 능력 판독으로 접는다.

    fid 가 조인 키다. 시트의 `FixtureType` **이름**으로 조인하지 않는다 — 정본 패치
    시트는 `Robe MegaPointe` 라 쓰고 콘솔 라이브러리 실측은 `Robin MegaPointe` 였다
    (2026-09-10, FixtureType 11). 두 어휘가 같다는 것은 **안 쟀고**, 안 잰 조인으로
    능력을 붙이면 조용히 엉뚱한 장비를 가리킨다. fid 는 양쪽이 다 실제 FID 로 나르는
    값이다(`design.rig_capability_read` 의 조인 키 실측).

    능력은 기종의 성질이지 개별 장비의 성질이 아니므로(``position_verdict`` 와 같은
    규율) 같은 기종의 fid 여럿은 **한 항목**으로 접힌다. 첫 일치 fid 의 판독을 쓴다.

    판독에 없는 fid 는 ``missing_fids`` 에 남는다 — 조용히 빠지면 그룹이 줄어든 것과
    구별할 수 없다.
    """
    per_type: dict[str, AxisSource] = {}
    missing: list[int] = []
    for fid in fids:
        capability = caps.fixtures.get(fid)
        if capability is None:
            missing.append(fid)
            continue
        per_type.setdefault(capability.type_name, capability)
    return GroupCapabilities(
        group_name=group_name,
        per_type=per_type,
        fids=tuple(fids),
        missing_fids=tuple(missing),
    )


def group_capability_source(
    caps: RigCapabilities, members: Mapping[str, Sequence[int]]
) -> Callable[[str], GroupCapabilities | None]:
    """그룹 이름 -> 그 그룹의 능력 판독. `parse_preset_csv(capabilities_for=...)` 재료.

    ``members`` 는 그룹 이름 -> fid 들이다(시트에서 온다:
    ``lxseq.position_derive.group_members_from_sheets``). 이 모듈은 시트를 읽지 않는다 —
    ``server/design`` 은 ``server/lxseq`` 를 임포트하지 않고(측정: 0건), 그 방향을
    여기서 열면 순수 판정 계층이 시트 파싱의 실패 모양까지 상속한다.

    이름이 명단에 없으면 ``None`` 이다. **빈 그룹을 만들지 않는다**: 축이 하나도 없는
    ``GroupCapabilities`` 는 `window` 가 늘 ``None`` 이라 판정에서는 같아 보이지만,
    「그 그룹을 모른다」와 「그 그룹의 축을 못 읽었다」는 다른 사실이고 호출자가 감독에게
    할 말도 다르다.

    합집합 표기(`KEY+BACK`)는 여기서 풀지 않는다 — ``group_members_from_sheets`` 가
    이미 아는 합집합만 펴서 명단에 담고, 그 밖은 산문이라 풀지 않는다는 규율을 그
    함수가 소유한다. 여기서 두 번째로 펴면 규율이 두 자리에 생긴다.
    """

    def resolve(group_name: str) -> GroupCapabilities | None:
        fids = members.get(group_name)
        if fids is None:
            return None
        return group_capabilities(caps, group_name, fids)

    return resolve


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
