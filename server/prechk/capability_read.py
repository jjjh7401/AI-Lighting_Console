"""Per-mode capability read — 이 장비가 **무엇을 조정할 수 있는가**, 그리고 각 축의
물리 범위는 어디까지인가.

조명연출은 여기서 시작한다(감독 지시 2026-09-10): 팬틸트가 없는 고정 장비에 포지션
프리셋을 주는 것은 계획 단계에서 막아야 하고, Zoom 45° 를 요구하는 시트는 그 기종의
줌 범위가 1.8~42도라면 **범위 밖**이다. 무엇을 조정할 수 있는지 모르면 어떤 프리셋에
넣을지도, 어떤 이펙트를 걸 수 있는지도 정할 수 없다.

## 왜 새 모듈인가

기존 세 모듈이 픽스처에서 모드까지는 이미 간다:

    inventory.translate_fixture_type   슬롯 -> 'FixtureType 10' -> 타입 이름
    mode_read.read_type_mode_widths    타입 -> 모드 이름 + 주소 폭
    channel_width                      그 둘의 조인

이 모듈은 그 다음 한 층만 소유한다 — **모드 안의 속성 목록과 각 속성의 물리 범위**.
폭(footprint)은 주소 계획의 재료이고 능력은 연출 계획의 재료라, 같은 트리를 걷지만
답하는 질문이 다르다.

## 판독 경로 (실측 2026-09-10, onPC / 응답기 1.6.5, 읽기 전용)

    Patch/FixtureTypes/<타입슬롯>/DMXModes/<모드슬롯>/DMXChannels/<채널>
        -> 채널 이름 예: 'Main Module_Frost1' · 'Main Module_Zoom'
    .../DMXChannels/<채널>/<논리채널>
        -> LogicalChannel, 이름이 속성 이름 예: 'Frost1' · 'Zoom'
    .../<논리채널>/<채널함수>
        -> ChannelFunction, 여기에 범위가 있다:
           ATTRIBUTE · DMXFROM · DMXTO · PHYSICALFROM · PHYSICALTO · DEFAULT

실측 표본(FixtureType 11 = Robin MegaPointe, Mode 1):

    채널 27  Frost1  ATTRIBUTE=Frost1  PHYSICALFROM=0.0   PHYSICALTO=1.0
    채널 28  Zoom    ATTRIBUTE=Zoom    PHYSICALFROM=42.0  PHYSICALTO=1.8

🔴 **Zoom 은 역방향이다** — physical_from 42.0 > physical_to 1.8. DMX 가 커지면
각도가 작아진다. 그래서 이 모듈은 범위를 정렬하지 않고 **읽은 방향 그대로** 나른다:
정렬하면 「어느 끝이 DMX 0 인가」가 사라지고, 그 정보 없이는 퍼센트를 물리값으로 옮길
수 없다. 방향 판단은 소비자 몫이고, :meth:`AxisRange.descending` 이 그것을 답한다.

🔴 **단위는 속성마다 다르다.** Frost 는 0~1 정규화, Zoom 은 도(degree)다. 「퍼센트」
하나로 뭉치면 Zoom 45° 가 45% 로 읽혀 조용히 틀린 자리에 간다. 그래서 이 모듈은
단위를 **추론하지 않고** 숫자만 나른다 — 무엇인지는 속성 이름과 범위가 말한다.

## 안 하는 것

* 콘솔에 쓰지 않는다. ``query_state`` 와 ``query_property`` 두 읽기만 쓴다.
* 능력 이름을 짓지 않는다. 속성 이름을 **콘솔이 답한 그대로** 나른다. 어휘 매핑
  (``Zoom`` -> 능력 ``zoom``)은 이 모듈 밖의 결정이다 — 여기서 이름을 지으면 그
  어휘가 실측과 한 몸이 되어 나중에 못 고친다.
* 못 읽은 것을 기본값으로 채우지 않는다. 읽히지 않은 축은 목록에 **없고**,
  ``gaps`` 가 그 자리를 말한다. 부재와 미판독은 다른 상태다.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol

from server.prechk.footprint import _payload_ok

__all__ = [
    "AXIS_PART_CHANNEL",
    "AXIS_PART_FIXTURE_TYPE",
    "CHANNEL_FUNCTION_PROPERTIES",
    "NORMALIZED_AXIS_MAX",
    "AxisRange",
    "AxisSource",
    "AxisWindow",
    "AxisWindowPart",
    "AxisWindowSource",
    "BulkPropertyReader",
    "ModeCapabilities",
    "PagedStateReader",
    "read_mode_capabilities",
]


class PagedStateReader(Protocol):
    """열거를 **페이징하며** 읽는 포트.

    ``footprint.StateReader`` 보다 넓다 — 그쪽은 ``query_state(path)`` 만 선언해
    페이징을 못 한다. 여기서 넓히는 이유는 실측이다: ``DMXChannels`` 는
    ``childCount`` 32 를 선언하면서 한 응답에 **15개만** 실어 보낸다(2026-09-10,
    페이로드 예산 절단 — 이 저장소가 이미 잰 성질이며 개수 상한이 아니라 바이트
    상한이다). 페이징 없이 읽으면 채널 절반이 조용히 사라지고, 그러면 「이 장비는
    Zoom 이 없다」는 **거짓 부재**가 나온다.
    """

    def query_state(self, path: str, *, offset: int = 0) -> dict: ...


class BulkPropertyReader(Protocol):
    """프로퍼티 여러 개를 한 왕복에 읽는 포트.

    ``query_property`` 는 이름 **하나**만 받는다(``console.py:735``). 콤마로 이어
    붙이면 콘솔이 그 전체를 한 이름으로 읽어 판독이 실패한다 — 실측으로 확인했다.
    여섯 개를 한 번에 읽는 것은 ``query_properties`` 다(``console.py:794``).
    """

    def query_properties(self, path: str, property_names: Sequence[str]) -> dict: ...


#: ``DMXModes`` 아래 채널 목록이 사는 자리. 모드 자식 중 하나이고 이름이 고정이다.
_CHANNELS_SEGMENT = "DMXChannels"

#: ``ChannelFunction`` 에서 읽는 프로퍼티. 이 여섯이 축 하나를 완전히 서술한다 —
#: 무엇인지(ATTRIBUTE), DMX 어디부터 어디까지(DMXFROM/TO), 그것이 물리적으로 무엇인지
#: (PHYSICALFROM/TO), 그리고 아무것도 안 걸었을 때의 값(DEFAULT).
CHANNEL_FUNCTION_PROPERTIES = (
    "ATTRIBUTE",
    "DMXFROM",
    "DMXTO",
    "PHYSICALFROM",
    "PHYSICALTO",
    "DEFAULT",
)


#: 정규화 축(0~1)의 상한. `Frost1` 이 `PHYSICALFROM=0.0 PHYSICALTO=1.0` 인 실측 예다.
#: 도(degree) 값과 정규화 축은 **단위가 다르므로** 대조 자체가 성립하지 않는다 —
#: 그런 짝은 「범위 밖」이라고 부르지 않고 **안 잰 것으로 남긴다**(틀린 사유로 막는
#: 것이 안 막는 것보다 나쁘다).
#:
#: 여기가 유일한 선언 자리다. 소비자 쪽에 상수를 다시 적으면 두 술어가 갈리는 날이
#: 오고, 그날 한쪽만 고쳐진다 — 이 저장소가 포트 기본값에서 이미 치른 값이다(t61).
NORMALIZED_AXIS_MAX = 1.0


#: :attr:`AxisWindowPart.role` 의 두 값. 이름이 **무엇의** 이름인지 말한다.
#:
#: 🔴 개수로 가르지 마라. 「부품 1개면 채널, 2개 이상이면 기종」은 t351 이 처음 쓴
#: 술어이고 **틀렸다**: 기종이 하나뿐인 그룹(`MOVER-U`)의 창도 부품이 1개이고, 그
#: 이름은 기종 이름이다. 검사가 그 자리를 잡았다(`test_lxseq_preset_group_range.py`
#: 의 `test_45_degrees_is_held_and_the_detail_names_the_type`). 역할은 만든 쪽이
#: **선언**해야 하는 것이고 개수에서 추론할 수 있는 것이 아니다.
AXIS_PART_CHANNEL = "channel"
AXIS_PART_FIXTURE_TYPE = "fixture_type"


@dataclass(frozen=True)
class AxisWindowPart:
    """창 하나를 좁힌 자리 — 이름, 그 이름의 **역할**, 그 자리의 정렬된 두 끝.

    ``role`` 이 ``name`` 을 해석하는 열쇠다(:data:`AXIS_PART_CHANNEL` ·
    :data:`AXIS_PART_FIXTURE_TYPE`). 만든 쪽이 선언하고 이 자료형은 나르기만 한다 —
    여기서 「채널인가 기종인가」를 판정하려 들면 이름의 뜻을 아는 자리가 둘이 되고,
    둘이 갈리는 순간 사유 문면이 엉뚱한 것을 가리킨다.
    """

    name: str
    low: float
    high: float
    role: str = AXIS_PART_CHANNEL

    def contains(self, value: float) -> bool:
        """이 자리가 그 값을 낼 수 있는가. 두 끝을 **포함**한다."""
        return self.low <= value <= self.high


@dataclass(frozen=True)
class AxisWindow:
    """대조에 쓰는 **계산된 창** — 축이 아니다.

    ## 왜 축과 창을 가르는가 (이 저장소가 두 번 다시 쓴 술어)

    포함 검사는 방향과 무관하므로 정렬된 두 수가 필요하다. 그런데 축을 정렬해서
    저장하면 「어느 끝이 DMX 0 인가」가 사라진다 — Zoom 실측이 42.0 -> 1.8 역방향
    이고(`capability_read` 모듈 독스트링), 그 방향 없이는 퍼센트를 물리값으로 옮길
    수 없다. 그래서 이 자료형은 **정렬된 두 수와 방향을 따로** 나른다:

        low / high    대조용. 정렬되어 있고, 방향 정보가 없다.
        descending    읽은 방향. ``None`` 은 방향이 **하나로 정해지지 않았다**는 뜻
                      이다(기여한 축들의 방향이 갈렸다) — 거짓이 아니다.

    ``AxisRange`` 자체는 이 창을 만들면서도 **전혀 바뀌지 않는다**. 정렬은 여기서
    파생값으로 일어나고, 축은 읽은 방향 그대로 남는다.

    ## ``parts`` 의 계약 — **역할**이 이름의 뜻을 정한다 (개수가 아니다)

    각 부품은 :attr:`AxisWindowPart.role` 로 자기 이름이 무엇의 이름인지 선언한다:
    단일 모드 판독은 :data:`AXIS_PART_CHANNEL`, 그룹 판독은
    :data:`AXIS_PART_FIXTURE_TYPE`. 소비자는 그 역할로 사유 문면을 고른다.

    🔴 개수로 추론하지 마라 — 기종이 하나뿐인 그룹의 창도 부품이 1개다
    (:data:`AXIS_PART_CHANNEL` 주석의 실패 기록).
    """

    attribute: str
    low: float
    high: float
    descending: bool | None = None
    parts: tuple[AxisWindowPart, ...] = ()

    def contains(self, value: float) -> bool:
        """이 창이 그 값을 담는가. 두 끝을 **포함**한다."""
        return self.low <= value <= self.high

    @property
    def normalized(self) -> bool:
        """두 끝이 **다** 0~1 안인가 — 도 값과 대조하면 안 되는 모양인가.

        두 끝 다를 요구하는 것이 하중을 진다: -180~180(팬 모양)을 정규화로 읽으면
        그 축이 검사에서 통째로 빠진다.
        """
        return self.low >= 0.0 and self.high <= NORMALIZED_AXIS_MAX

    @property
    def empty(self) -> bool:
        """교집합이 비었는가 — 어떤 값도 모두가 낼 수 없는 상태.

        단일 축에서는 절대 참이 아니다(두 끝을 정렬했으므로 ``low <= high``).
        여러 기종의 교집합에서만 참이 될 수 있고, 그때는 「그 그룹이 공통으로 낼 수
        있는 값이 없다」는 뜻이다.
        """
        return self.low > self.high

    def excluding(self, value: float) -> tuple[str, ...]:
        """그 값을 못 내는 자리들의 이름. 창을 만든 순서 그대로.

        ``parts`` 가 비어 있으면 빈 튜플이다 — 자리를 모르면 이름을 지어내지 않는다.
        """
        return tuple(part.name for part in self.parts if not part.contains(value))

    @property
    def names_fixture_types(self) -> bool:
        """부품 이름이 **기종** 이름인가 — 사유 문면을 고르는 술어.

        소비자가 :data:`AXIS_PART_FIXTURE_TYPE` 을 직접 비교하지 않게 하려고 여기에
        둔다. ``server.lxseq.preset_parser`` 는 순수 파서라 런타임에 이 모듈을
        임포트하지 않으므로(형 주석에만), 상수 비교를 그쪽에 두면 그 규율이 깨진다 —
        술어를 주입되는 물건 자신이 갖고 있는 것이 이 카드의 규율 전체와 같은 결이다.
        """
        return any(part.role == AXIS_PART_FIXTURE_TYPE for part in self.parts)


@dataclass(frozen=True)
class AxisRange:
    """조정 가능한 축 하나 — 속성 이름과 그 물리 범위.

    ``physical_from`` / ``physical_to`` 는 **읽은 방향 그대로**다(모듈 독스트링의
    역방향 주의 참조). ``None`` 은 그 프로퍼티가 답하지 않았다는 뜻이고 0 이 아니다.
    """

    attribute: str
    channel_name: str
    dmx_from: int | None = None
    dmx_to: int | None = None
    physical_from: float | None = None
    physical_to: float | None = None
    default: float | None = None

    @property
    def descending(self) -> bool | None:
        """물리값이 DMX 증가에 따라 **줄어드는가**. 범위를 모르면 ``None``.

        Zoom(42.0 -> 1.8)이 참인 예다. 이 값을 모르고 퍼센트를 물리값으로 옮기면
        방향이 뒤집혀 「넓게」가 「좁게」로 나간다.
        """
        if self.physical_from is None or self.physical_to is None:
            return None
        return self.physical_from > self.physical_to

    @property
    def measurable(self) -> bool:
        """물리 범위 두 끝이 다 읽혔는가 — 시트 값을 대조할 수 있는 축인가."""
        return self.physical_from is not None and self.physical_to is not None

    def window(self) -> AxisWindow | None:
        """이 축의 **대조용 창**. 범위를 못 읽었으면 ``None``.

        🔴 **이 저장소의 유일한 포함-검사 술어다.** 예전에는 두 소비자
        (`design.capability_verdict.range_verdict` · `lxseq.preset_parser` 의 bm
        범위 사유)가 각자 `min`/`max` 를 계산했다 — 같은 판정을 두 자리에서 구현한
        상태였고, 그 둘이 갈리는 날 한쪽만 고쳐진다. 술어를 축 자신에게 두면 판독값을
        **주입만 받는** 소비자(순수 파서)도 import 없이 같은 술어를 쓴다.

        ``None`` 은 「범위 밖이 아니다」가 아니라 **「대조할 수 없다」**다. 소비자는
        이것을 통과로 처리하면 안 된다 — 안 잰 범위는 안전장치가 아니다.

        방향은 버리지 않는다: 창에 :attr:`AxisWindow.descending` 으로 실려 나가고,
        축 자신은 읽은 방향 그대로 남는다.
        """
        first = self.physical_from
        second = self.physical_to
        if first is None or second is None:
            return None
        low = min(first, second)
        high = max(first, second)
        return AxisWindow(
            attribute=self.attribute,
            low=low,
            high=high,
            descending=self.descending,
            parts=(
                AxisWindowPart(name=self.channel_name, low=low, high=high, role=AXIS_PART_CHANNEL),
            ),
        )


class AxisSource(Protocol):
    """축 하나를 이름으로 내주는 것들의 계약.

    ``ModeCapabilities``(이 모듈)와 ``design.capability_join.FixtureCapability`` 가
    둘 다 만족한다 — 같은 술어(대소문자 무관 정확 일치)를 각자 갖고 있고, 그것이
    이 Protocol 이 서술하는 전부다. 그룹 판독이 fid 단위 판독을 기종별로 모을 때
    이 계약으로 받으므로 ``capability_verdict`` 가 ``capability_join`` 의 구체 형에
    묶이지 않는다.
    """

    def axis(self, attribute: str) -> AxisRange | None: ...


class AxisWindowSource(Protocol):
    """대조용 창을 내주는 것들의 계약 — 능력 판독을 **주입**으로 받는 소비자용.

    두 구현이 있다:

        ModeCapabilities                       한 기종·한 모드의 판독
        design.capability_verdict.GroupCapabilities   한 그룹(여러 기종)의 판독

    소비자가 이 Protocol 로 받으면 「한 기종이냐 한 그룹이냐」를 몰라도 같은 코드가
    돈다 — 창이 몇 자리에서 왔는지는 :attr:`AxisWindow.parts` 가 답한다.

    ``server.lxseq.preset_parser`` 가 이것으로 받는다. 그 모듈은 순수 파서이므로
    런타임에 이 모듈을 임포트하지 않고(형 주석에만 쓴다), 판독기를 **부르지 않는다** —
    창은 주입으로 들어오고 술어는 주입된 물건 자신이 갖고 있다.
    """

    def window(self, attribute: str, *, exclude_normalized: bool = False) -> AxisWindow | None: ...


@dataclass(frozen=True)
class ModeCapabilities:
    """한 기종의 한 모드가 가진 축 목록.

    ``attempted`` 가 거짓이면 나머지 필드는 의미가 없다. ``axes`` 가 비어 있고
    ``gaps`` 도 비어 있으면 그 모드에 채널이 없다는 뜻이지만, 이 채널의 빈 답은
    부재의 증거가 아니라는 이 저장소의 기록(t105)을 기억하라 — 그래서 ``channel_count``
    를 따로 실어 「채널은 있는데 못 읽었다」와 「채널이 없다」를 가른다.
    """

    attempted: bool
    mode_found: bool = False
    channel_count: int = 0
    axes: tuple[AxisRange, ...] = ()
    gaps: tuple[str, ...] = field(default_factory=tuple)
    detail: str = ""

    def has_attribute(self, attribute: str) -> bool:
        """이 모드가 그 속성을 조정할 수 있는가 — 대소문자 무관 정확 일치.

        🔴 접두 일치를 쓰지 않는다. ``Zoom`` 으로 물으면 ``ZoomMSpeed`` 가 함께
        걸리고, 그것은 줌 각도가 아니라 줌 이동 속도다 — 다른 축이다. 이 저장소는
        접두 매칭이 목록 방향에 따라 과다 수용/과다 차단으로 갈리는 것을 이미
        측정했다(t139).
        """
        wanted = attribute.strip().casefold()
        return any(axis.attribute.casefold() == wanted for axis in self.axes)

    def axis(self, attribute: str) -> AxisRange | None:
        """그 속성의 범위. 없으면 ``None``."""
        wanted = attribute.strip().casefold()
        for candidate in self.axes:
            if candidate.attribute.casefold() == wanted:
                return candidate
        return None

    def window(self, attribute: str, *, exclude_normalized: bool = False) -> AxisWindow | None:
        """그 속성의 **대조용 창**. 축이 없거나 범위를 못 읽었으면 ``None``.

        ``exclude_normalized`` 가 참이면 0~1 모양 축도 ``None`` 이다 — 도(degree)
        값만 대조하는 소비자가 단위 불일치를 「범위 밖」이라 부르지 않게 하는 문턱
        이다(:data:`NORMALIZED_AXIS_MAX` 주석 참조).

        ⚠️ **기종·모드 이름을 싣지 못한다.** 이 자료형은 타입/모드 슬롯을 싣지 않으
        므로 창의 ``parts`` 에 들어갈 이름은 축의 **채널 이름**뿐이다. 어느 기종의
        판독을 주입했는지는 부르는 쪽이 안다. 기종 이름이 필요하면 그룹 단위 판독
        (``server.design.capability_verdict.GroupCapabilities``)을 주입한다.
        """
        axis = self.axis(attribute)
        if axis is None:
            return None
        found = axis.window()
        if found is None:
            return None
        if exclude_normalized and found.normalized:
            return None
        return found

    @property
    def attributes(self) -> tuple[str, ...]:
        """읽힌 속성 이름 전부 — 콘솔이 답한 철자 그대로, 정렬해서."""
        return tuple(sorted({axis.attribute for axis in self.axes}))


def _numeric(payload: dict, name: str) -> float | None:
    """프로퍼티 응답 하나에서 숫자를 꺼낸다. 못 읽으면 ``None``.

    응답기는 값을 **문자열**로 나른다(``{"n": ..., "v": "42.0", "t": "number"}``).
    그래서 float 로 옮기고, 옮기지 못하면 추측하지 않고 ``None`` 이다.
    """
    for read in payload.get("reads") or []:
        if not isinstance(read, dict) or read.get("n") != name:
            continue
        if read.get("ok") is False:
            return None
        raw = read.get("v")
        if raw is None:
            return None
        try:
            return float(str(raw).strip())
        except ValueError:
            return None
    return None


def _text(payload: dict, name: str) -> str:
    """프로퍼티 응답 하나에서 문자열을 꺼낸다. 못 읽으면 빈 문자열."""
    for read in payload.get("reads") or []:
        if not isinstance(read, dict) or read.get("n") != name:
            continue
        if read.get("ok") is False:
            return ""
        raw = read.get("v")
        return "" if raw is None else str(raw).strip()
    return ""


def _children(payload: dict, *, base: int = 1) -> list[tuple[int, str]]:
    """(슬롯, 이름) 쌍. 슬롯이 없는 자식은 열거 순서를 쓴다.

    슬롯을 우선하는 이유는 :func:`server.prechk.mode_read.parse_console_mode_slot`
    과 같다 — 슬롯이 주소이고 순서는 주소가 아니다. ``base`` 는 페이징된 조각의
    시작 번호로, 슬롯이 없는 응답에서 두 조각의 순서 번호가 겹치지 않게 한다.
    """
    pairs: list[tuple[int, str]] = []
    for index, child in enumerate(payload.get("children") or [], start=base):
        if not isinstance(child, dict):
            continue
        slot = child.get("i")
        name = child.get("name")
        pairs.append(
            (
                slot if isinstance(slot, int) and slot >= 1 else index,
                str(name).strip() if name is not None else "",
            )
        )
    return pairs


def read_mode_capabilities(
    reader: PagedStateReader,
    properties: BulkPropertyReader,
    *,
    root: str,
    type_slot: int,
    mode_slot: int,
    budget: int = 256,
) -> ModeCapabilities:
    """한 기종·한 모드의 조정 가능한 축을 전부 읽는다. **읽기 전용.**

    ``root`` 는 픽스처 타입 라이브러리 경로(``Patch/FixtureTypes``)다. 하드코딩하지
    않는 이유는 이 저장소의 은퇴 경로 규율과 같다 — 경로 리터럴이 코드 안에 흩어지면
    한 곳을 고쳐도 다른 곳이 남는다.

    ``budget`` 은 왕복 상한이다. 32채널 기종이 채널마다 논리채널 1개 + 함수 1개면
    약 100 왕복이 든다. 상한에 닿으면 **거기서 멈추고 그 사실을 ``gaps`` 에 적는다** —
    조용히 잘린 목록을 완전한 목록처럼 돌려주지 않는다.
    """
    spent = 0
    gaps: list[str] = []

    def state(path: str, *, offset: int = 0) -> dict | None:
        nonlocal spent
        if spent >= budget:
            return None
        spent += 1
        try:
            payload = reader.query_state(path, offset=offset)
        except Exception as error:  # 포트가 실패를 예외로 내는 형태 — 응답으로 접는다
            gaps.append(f"{path}: {type(error).__name__}")
            return None
        return payload if _payload_ok(payload) else None

    def listing(path: str) -> list[tuple[int, str]] | None:
        """열거를 **끝까지** 읽는다 — 한 응답이 전부라고 믿지 않는다.

        전진은 **받은 개수**만큼이다(``protocol.py:261`` 규율). 요청한 수만큼
        전진하면 절단된 조각에서 건너뛰기가 생긴다. 0개를 받으면 멈춘다 — 그러지
        않으면 무한 루프다(이 저장소가 낡은 응답기에서 실제로 겪은 형태).
        """
        first = state(path)
        if first is None:
            return None
        declared = first.get("node", {}).get("childCount")
        pairs = _children(first)
        while isinstance(declared, int) and len(pairs) < declared:
            page = state(path, offset=len(pairs))
            if page is None:
                gaps.append(f"{path}: offset={len(pairs)} 미판독 — 목록이 잘렸다")
                break
            received = _children(page, base=len(pairs) + 1)
            if not received:
                gaps.append(f"{path}: offset={len(pairs)} 에서 0개 — 열거가 멈췄다")
                break
            pairs.extend(received)
        return pairs

    def props(path: str) -> dict | None:
        nonlocal spent
        if spent >= budget:
            return None
        spent += 1
        try:
            payload = properties.query_properties(path, CHANNEL_FUNCTION_PROPERTIES)
        except Exception as error:
            gaps.append(f"{path}: {type(error).__name__}")
            return None
        return payload if isinstance(payload, dict) and payload.get("ok") is not False else None

    channels_path = f"{root}/{type_slot}/DMXModes/{mode_slot}/{_CHANNELS_SEGMENT}"
    channels = listing(channels_path)
    if channels is None:
        return ModeCapabilities(
            attempted=True,
            mode_found=False,
            gaps=tuple(gaps),
            detail=f"채널 목록을 읽지 못했다: {channels_path}",
        )

    axes: list[AxisRange] = []
    for channel_slot, channel_name in channels:
        channel_path = f"{channels_path}/{channel_slot}"
        logicals = listing(channel_path)
        if logicals is None:
            gaps.append(f"{channel_path}: 논리채널 미판독")
            continue
        for logical_slot, logical_name in logicals:
            logical_path = f"{channel_path}/{logical_slot}"
            functions = listing(logical_path)
            if functions is None:
                gaps.append(f"{logical_path}: 채널함수 미판독")
                continue
            if not functions:
                gaps.append(f"{logical_path}: 채널함수 0개")
                continue
            # 첫 함수만 읽는다 — 그것이 그 축의 **주 기능**이고, 뒤따르는 함수는
            # 스트로브·펄스 같은 파생 모드다(실측: Frost1 아래 'Frost1 1' 다음에
            # FROSTSTROBEPULSEDECREASE/INCREASE). 파생까지 축으로 세면 「이 장비가
            # 조정할 수 있는 것」이 부풀어 연출 판단이 흐려진다.
            function_path = f"{logical_path}/{functions[0][0]}"
            payload = props(function_path)
            if payload is None:
                gaps.append(f"{function_path}: 범위 미판독")
                continue
            attribute = _text(payload, "ATTRIBUTE") or logical_name
            if not attribute:
                gaps.append(f"{function_path}: 속성 이름 없음")
                continue
            dmx_from = _numeric(payload, "DMXFROM")
            dmx_to = _numeric(payload, "DMXTO")
            axes.append(
                AxisRange(
                    attribute=attribute,
                    channel_name=channel_name,
                    dmx_from=int(dmx_from) if dmx_from is not None else None,
                    dmx_to=int(dmx_to) if dmx_to is not None else None,
                    physical_from=_numeric(payload, "PHYSICALFROM"),
                    physical_to=_numeric(payload, "PHYSICALTO"),
                    default=_numeric(payload, "DEFAULT"),
                )
            )

    if spent >= budget:
        gaps.append(f"왕복 예산 {budget} 소진 — 목록이 잘렸다")

    return ModeCapabilities(
        attempted=True,
        mode_found=True,
        channel_count=len(channels),
        axes=tuple(axes),
        gaps=tuple(gaps),
        detail="",
    )
