"""리그 능력 판독 -> 룩 저장 계획의 축 판정 (t348).

:mod:`server.looks.instantiate` 의 :class:`~server.looks.instantiate.AxisPresence`
계약을 실제 콘솔 판독(:class:`server.design.capability_join.RigCapabilities`) 위에
구현한다. t344 가 만든 판독을 **두 번째 소비 지점**에 배선하는 것이 이 모듈의 전부다:
첫 소비 지점은 포지션 질문 건너뛰기(:mod:`server.design.capability_verdict`)였고,
이쪽은 프리셋 저장 보류다.

## 이 모듈이 하지 않는 일

🔴 **숫자를 비교하지 않는다.** 룩 라이브러리의 값은 0~100 퍼센트다
(``server/looks/library/edm.yaml`` 의 ``Zoom: 35`` 가 ``ColorRGB_R: 100`` 옆에 앉아
있다). 판독의 범위는 **물리 단위**이고 축마다 다르다(MegaPointe Zoom 실측 42.0 ->
1.8 **도**, 역방향). 퍼센트를 도와 견주면 조용히 틀린 값이 나간다 —
``server/prechk/capability_read.py`` 독스트링이 경고하는 바로 그 함정이다. 그래서
이 모듈은 ``axis()`` 도 ``range_verdict`` 도 부르지 않고 **축이 있는지만** 묻는다.

🔴 **범위를 정렬하지 않는다.** 애초에 범위를 만지지 않는다.

## 왜 판정 대상 철자를 제한하는가

:meth:`FixtureCapability.has_attribute` 는 **정확**(대소문자 무관) 일치다. 룩 스키마의
속성 이름이 콘솔이 답한 철자와 다르면 그 불일치가 **거짓 부재**로 나타나고, 거짓 부재는
되던 저장을 막는다. 이 저장소에서 콘솔 철자로 실측된 이름은
:data:`MEASURED_ATTRIBUTE_SPELLINGS` 뿐이다(t344 리그 실측 15기종: ``Dimmer`` ·
``Zoom``). ``Iris`` 와 ``ColorRGB_*`` 의 콘솔 철자는 이 저장소에서 측정된 바가 없어
**판정하지 않고** :data:`~server.looks.instantiate.PRESENCE_UNREAD` 로 답한다 —
:mod:`server.design.capability_verdict` 의 어휘 표가 일부러 부분집합인 것과 같은 규율.
표를 늘리는 일은 추측이 아니라 실측이 선행한다.

**읽기 전용.** 콘솔에 아무것도 쓰지 않고, 명령줄을 만들지도 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass

from server.design.capability_join import RigCapabilities
from server.looks.instantiate import PRESENCE_ABSENT, PRESENCE_PRESENT, PRESENCE_UNREAD

__all__ = ["MEASURED_ATTRIBUTE_SPELLINGS", "RigAxisPresence"]

#: 콘솔이 답한 철자로 이 저장소에서 실측된 룩 속성 이름. 이 목록 밖은 판정하지 않는다.
MEASURED_ATTRIBUTE_SPELLINGS: tuple[str, ...] = ("Dimmer", "Zoom")


@dataclass(frozen=True)
class RigAxisPresence:
    """한 리그 판독을 축 판정으로 읽는다. ``presence`` 하나만 공개한다."""

    caps: RigCapabilities
    judged: tuple[str, ...] = MEASURED_ATTRIBUTE_SPELLINGS

    def presence(self, attribute: str) -> str:
        """이 리그가 그 속성을 조정할 수 있는가.

        :data:`~server.looks.instantiate.PRESENCE_ABSENT` 는 **적극적 관측**일 때만
        답한다. 넷 중 하나라도 걸리면 미판독이다:

        1. 판정 대상 철자가 아니다(위 독스트링).
        2. 읽힌 장비가 하나도 없다 — 빈 판독은 「능력 없는 리그」와 바이트 동일하다.
        3. 능력까지 못 데려간 fid 가 있다(``caps.unread``).
        4. 읽힌 장비 중 판독이 부분인 것이 있다(``FixtureCapability.whole`` 거짓) —
           잘린 목록에 없다는 것은 부재의 증거가 아니다.
        """
        wanted = attribute.strip().casefold()
        if not any(wanted == judged.casefold() for judged in self.judged):
            return PRESENCE_UNREAD
        fixtures = tuple(self.caps.fixtures.values())
        if any(fixture.has_attribute(attribute) for fixture in fixtures):
            return PRESENCE_PRESENT
        if not fixtures or self.caps.unread:
            return PRESENCE_UNREAD
        if any(not fixture.whole for fixture in fixtures):
            return PRESENCE_UNREAD
        return PRESENCE_ABSENT
