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
    "CHANNEL_FUNCTION_PROPERTIES",
    "AxisRange",
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
