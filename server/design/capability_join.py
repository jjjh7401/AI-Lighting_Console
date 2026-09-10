"""Per-fixture capability join — 이 fid 는 **무엇을 조정할 수 있는가**.

t344 A. ``prechk.capability_read.read_mode_capabilities`` 는 2026-09-10 에
실측까지 갔지만 **비테스트 호출자가 0** 이었다. 읽을 수 있는데 아무도 안 부르는
상태는 능력이 아니라 부채다 — 이 모듈이 그 배선이다.

## 왜 ``server/design/`` 인가 (모듈 위치 선택)

``prechk/channel_width.py`` 에 얹지 않았다. 그 모듈이 답하는 질문은 **주소 계획**
이다 — 이 fid 가 몇 칸을 먹는가(``TotalFootprint``). 이 모듈이 답하는 질문은
**연출 계획**이다 — 이 fid 로 무엇을 할 수 있는가. 같은 트리를 걷고 같은 파싱
단계를 재사용하지만 소비자가 다르다(주소는 패치, 능력은 큐시트·프리셋 선택).
``server/design/rig.py`` 가 「이 리그가 무엇을 말할 수 있는가」를 이미 이 폴더에서
소유하고 있어, 능력 판독의 이웃은 여기다.

## 조합하는 기존 단계 (하나도 다시 구현하지 않는다)

    inventory.HANDLE_TEXT              'FixtureType 11' -> 타입 슬롯 11
    inventory.translate_fixture_type   그 핸들 -> 타입 이름
    channel_width.parse_mode_reference '1 Mode 1'      -> 모드 슬롯 1 + 이름
    mode_read.read_type_mode_widths    타입 이름       -> 모드 목록 + 폭
    channel_width.resolve_widths       위 둘의 조인 + **모드 이름 자기검사**
    capability_read.read_mode_capabilities  타입·모드 -> 축 목록 + 물리 범위

## 이 모듈이 지키는 두 경계

🔴 **부재와 미판독은 다른 상태다.** 축이 목록에 없다는 것과 축을 못 읽었다는 것을
한 값으로 뭉치지 않는다. 못 읽은 fid 는 :attr:`RigCapabilities.unread` 에 사유
문자열과 함께 앉고, **부분만 읽힌** fid 는 :attr:`RigCapabilities.incomplete` 에
따로 앉는다. 절단된 목록을 완전한 목록처럼 돌려주면 「이 장비는 Zoom 이 없다」는
거짓 부재가 나오고, 그 거짓은 ``capability_read`` 의 페이징이 막으려던 바로 그
실패다.

🔴 **속성 이름은 콘솔이 답한 철자 그대로 나른다.** ``Zoom`` -> ``zoom`` 같은 어휘
매핑은 t344 B 의 몫이다. 여기서 이름을 지으면 그 어휘가 실측과 한 몸이 되어 나중에
못 고친다.

🔴 **범위를 정렬하지 않는다.** Zoom 은 실측 42.0 -> 1.8 로 역방향이다(DMX 가 커지면
각도가 작아진다). 정렬하면 어느 끝이 DMX 0 인지가 사라져 퍼센트를 물리값으로 옮길
수 없다. ``AxisRange`` 를 그대로 통과시키는 것이 규율이다.

## 왕복 절약

15기종 리그에서 fid 는 수십~수백이지만 (타입, 모드) 쌍은 스무 개 안쪽이다. 그래서
타입별 모드 판독과 (타입, 모드)별 능력 판독을 **캐시**한다 — fid 마다 같은 모드를
다시 읽는 것은 순수한 낭비다. :attr:`RigCapabilities.mode_reads` /
:attr:`RigCapabilities.capability_reads` 가 실제 호출 수를 답한다.

**읽기 전용.** ``query_state`` · ``query_property`` · ``query_properties`` 세 읽기만
쓴다. 콘솔 쓰기 0 — ``Store`` 도, ``Go`` 도, 실행 포트도 건드리지 않는다.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from server.prechk.capability_read import (
    AxisRange,
    BulkPropertyReader,
    ModeCapabilities,
    PagedStateReader,
    read_mode_capabilities,
)
from server.prechk.channel_width import (
    FixtureModeRef,
    parse_mode_reference,
    resolve_widths,
)
from server.prechk.inventory import HANDLE_TEXT, translate_fixture_type
from server.prechk.mode_read import TypeModeRead, read_type_mode_widths

__all__ = [
    "UNREAD_CAPABILITY_UNREAD",
    "UNREAD_MODE_UNPARSED",
    "UNREAD_TYPE_NAME_ABSENT",
    "UNREAD_TYPE_SLOT_UNKNOWN",
    "FixtureCapability",
    "FixtureTypeRef",
    "RigCapabilities",
    "read_rig_capabilities",
]

#: fid 를 능력까지 못 데려간 사유. 하나로 뭉치지 않는 이유는
#: ``inventory`` 의 미번역 사유 열거와 같다 — 각각이 **다른 행동**을 부른다.
#: 슬롯을 모르면 판독 순서가 잘못됐고(핸들을 못 받았다), 모드가 안 파싱되면 그
#: fid 의 Mode 프로퍼티가 이상하고, 능력이 안 읽히면 콘솔을 다시 물어야 한다.
UNREAD_TYPE_SLOT_UNKNOWN = "type_slot_unknown"
UNREAD_TYPE_NAME_ABSENT = "type_name_absent"
UNREAD_MODE_UNPARSED = "mode_unparsed"
UNREAD_CAPABILITY_UNREAD = "capability_unread"


@dataclass(frozen=True)
class FixtureTypeRef:
    """조인이 필요한 fid 하나 — fid, 그 fid 의 FixtureType 판독, Mode 판독.

    콘솔에서 이 두 문자열을 읽는 일은 이 모듈이 하지 않는다. ``channel_width``
    의 :class:`~server.prechk.channel_width.FixtureModeRef` 와 같은 규율이다:
    호출자가 이미 읽은 값을 넘긴다. 그래야 이 조인이 픽스처 프로퍼티 판독의
    실패 모양까지 상속하지 않는다.
    """

    fid: int
    type_raw: str | None
    mode_raw: str | None


@dataclass(frozen=True)
class FixtureCapability:
    """한 fid 가 조정할 수 있는 것 — 그리고 **못 읽은 것**.

    ``axes`` 는 ``capability_read`` 가 읽은 순서·방향 그대로다. ``gaps`` 가 비어
    있지 않으면 이 목록은 부분집합이고, 그때 「이 속성이 없다」는 결론을 내릴 수
    없다.
    """

    fid: int
    type_slot: int
    type_name: str
    mode_slot: int
    mode_name: str
    mode_width: int | None
    channel_count: int
    axes: tuple[AxisRange, ...] = ()
    gaps: tuple[str, ...] = ()

    @property
    def attributes(self) -> tuple[str, ...]:
        """읽힌 속성 이름 전부 — 콘솔 철자 그대로. 이름을 바꾸지 않는다."""
        return tuple(sorted({axis.attribute for axis in self.axes}))

    @property
    def whole(self) -> bool:
        """이 판독이 **전수**인가. 거짓이면 부재를 단정할 수 없다."""
        return not self.gaps

    def has_attribute(self, attribute: str) -> bool:
        """그 속성을 조정할 수 있는가 — 대소문자 무관 **정확** 일치.

        접두 일치를 쓰지 않는 이유는 ``ModeCapabilities.has_attribute`` 와 같다:
        ``Zoom`` 이 ``ZoomMSpeed``(줌 이동 속도)를 함께 걸어버린다.
        """
        wanted = attribute.strip().casefold()
        return any(axis.attribute.casefold() == wanted for axis in self.axes)

    def axis(self, attribute: str) -> AxisRange | None:
        """그 속성의 물리 범위. 목록에 없으면 ``None``.

        ``None`` 은 「없다」가 아니라 「이 목록에 없다」다. :attr:`whole` 이 거짓이면
        미판독일 수 있다.
        """
        wanted = attribute.strip().casefold()
        for candidate in self.axes:
            if candidate.attribute.casefold() == wanted:
                return candidate
        return None


@dataclass
class RigCapabilities:
    """리그 전체의 능력 판독 결과 — 읽힌 것, 못 읽은 것, 부분만 읽힌 것.

    ``frozen`` 이 아닌 유일한 자료형이다 — 조인이 fid 를 훑으며 세 갈래에 채워
    넣는 누산기라서 그렇다. 축 자체(``AxisRange``)와 fid 단위 결과
    (``FixtureCapability``)는 그대로 frozen 이다.

    세 갈래를 따로 두는 것이 이 자료형의 핵심이다. ``fixtures`` 만 보면 못 읽은
    fid 가 조용히 사라지고, 그 침묵은 「능력이 없는 장비」와 바이트 동일하다.
    """

    fixtures: dict[int, FixtureCapability] = field(default_factory=dict)
    unread: dict[int, str] = field(default_factory=dict)
    incomplete: dict[int, str] = field(default_factory=dict)
    mode_reads: int = 0
    capability_reads: int = 0

    @property
    def round_trips(self) -> int:
        """콘솔을 향한 상위 판독 호출 수 — 캐시가 실제로 먹었는지 재는 계기."""
        return self.mode_reads + self.capability_reads


def _type_slot(raw: str | None) -> int | None:
    """FixtureType 판독에서 라이브러리 슬롯. 핸들 모양이 아니면 ``None``.

    ``inventory.HANDLE_TEXT`` 를 재사용한다 — 핸들 문법을 두 곳에서 알면 한 곳을
    고쳐도 다른 곳이 남는다. 이름으로 온 판독은 슬롯이 **없다**: 이름에서 슬롯을
    거꾸로 찾는 것은 ``translate_fixture_type`` 이 금지한 역방향이고, 같은 이름을
    쓰는 두 슬롯에서 조용히 틀린다(t334).
    """
    if raw is None:
        return None
    hit = HANDLE_TEXT.match(raw.strip())
    return int(hit.group(1)) if hit else None


def read_rig_capabilities(
    reader: PagedStateReader,
    properties: BulkPropertyReader,
    *,
    root: str,
    fixtures: Sequence[FixtureTypeRef],
    type_names: Mapping[int, str] | None = None,
    budget: int = 256,
) -> RigCapabilities:
    """fid 목록을 각자의 타입·모드·조정 가능한 축으로 조인한다. **읽기 전용.**

    ``root`` 는 픽스처 타입 라이브러리 경로(``Patch/FixtureTypes``)다. 하드코딩하지
    않는 이유는 하위 모듈들과 같다 — 경로 리터럴이 흩어지면 한 곳만 고쳐진다.

    ``type_names`` 는 슬롯 -> 타입 이름 표다(``inventory`` 가 이미 읽어둔 것).
    ``None`` 이면 핸들을 이름으로 옮길 수 없어 해당 fid 는 미판독이다 — 추측하지
    않는다.

    ``budget`` 은 (타입, 모드) 한 쌍당 왕복 상한이며 ``read_mode_capabilities`` 로
    그대로 넘어간다. 상한에 닿은 판독은 축 목록이 잘린 채로 오고, 그 사실은
    ``gaps`` 를 거쳐 :attr:`RigCapabilities.incomplete` 에 나타난다.
    """
    result = RigCapabilities()

    #: 타입 이름 -> 모드 판독. fid 마다 다시 읽지 않기 위한 캐시.
    type_reads: dict[str, TypeModeRead] = {}
    #: (타입 슬롯, 모드 슬롯) -> 능력 판독. 같은 기종·같은 모드를 한 번만 읽는다.
    mode_caps: dict[tuple[int, int], ModeCapabilities] = {}

    # ── 1단계: fid 를 타입 슬롯·타입 이름·모드 슬롯까지 데려간다. ──
    resolved: dict[int, tuple[int, str, int, str]] = {}
    refs: list[FixtureModeRef] = []
    for fixture in fixtures:
        fid = fixture.fid
        slot = _type_slot(fixture.type_raw)
        if slot is None:
            result.unread[fid] = UNREAD_TYPE_SLOT_UNKNOWN
            continue
        type_name, untranslated = translate_fixture_type(fixture.type_raw, type_names)
        if untranslated is not None or type_name is None:
            result.unread[fid] = f"{UNREAD_TYPE_NAME_ABSENT}: {untranslated}"
            continue
        parsed = parse_mode_reference(fixture.mode_raw)
        if parsed is None:
            result.unread[fid] = UNREAD_MODE_UNPARSED
            continue
        if type_name not in type_reads:
            type_reads[type_name] = read_type_mode_widths(
                reader, properties, root=root, type_name=type_name
            )
            result.mode_reads += 1
        resolved[fid] = (slot, type_name, parsed.slot, parsed.name)
        refs.append(FixtureModeRef(slot=fid, type_name=type_name, mode_raw=fixture.mode_raw))

    # ── 2단계: 모드 이름 자기검사 + 폭. 기존 조인을 그대로 부른다. ──
    # 이 검사가 하는 일: Mode 문자열이 말하는 모드와 그 슬롯이 가리키는 노드의
    # 이름이 **같은지** 본다. 어긋나면 폭이 안 나오고, 그 fid 는 다른 모드의
    # 능력을 뒤집어쓰는 대신 사유와 함께 미판독으로 남는다.
    widths = resolve_widths(refs, type_reads)

    # ── 3단계: (타입, 모드) 캐시를 통해 축을 읽는다. ──
    for fid, (type_slot, type_name, mode_slot, mode_name) in resolved.items():
        reason = widths.unresolved.get(fid)
        # 폭만 못 읽은 것(``width_unread``)은 능력 판독을 막지 않는다 — 주소와 능력은
        # 다른 질문이고, 폭을 모른다고 축을 못 읽는 것은 아니다. 그 외의 사유는 모드
        # 자체가 확정되지 않았다는 뜻이라 여기서 멈춘다.
        if reason is not None and reason != "width_unread":
            result.unread[fid] = f"{UNREAD_MODE_UNPARSED}: {reason}"
            continue
        key = (type_slot, mode_slot)
        caps = mode_caps.get(key)
        if caps is None:
            caps = read_mode_capabilities(
                reader,
                properties,
                root=root,
                type_slot=type_slot,
                mode_slot=mode_slot,
                budget=budget,
            )
            mode_caps[key] = caps
            result.capability_reads += 1
        if not caps.mode_found:
            result.unread[fid] = f"{UNREAD_CAPABILITY_UNREAD}: {caps.detail or '사유 없음'}"
            continue
        result.fixtures[fid] = FixtureCapability(
            fid=fid,
            type_slot=type_slot,
            type_name=type_name,
            mode_slot=mode_slot,
            mode_name=mode_name,
            mode_width=widths.widths.get(fid),
            channel_count=caps.channel_count,
            axes=caps.axes,
            gaps=caps.gaps,
        )
        if caps.gaps:
            # 부분 판독은 **성공이 아니다**. 여기 적히지 않으면 잘린 목록이 전수처럼
            # 읽혀 「이 장비는 그 축이 없다」는 거짓 부재가 나온다.
            result.incomplete[fid] = " · ".join(caps.gaps)

    return result
