"""한 리그 단면이 **관측인가**를 답하는 술어 — 이 저장소의 유일한 자리 (t109).

## 왜 술어가 하나여야 하는가

이 저장소는 「재지 못함」을 「비었음」으로 읽는 결함을 **네 번** 겪었다:

1. GROUPGEN-001 실기 — 그룹의 ``childCount 0`` 은 「비었다」가 아니라
   「이 채널로는 안 보인다」였다
2. t95 — 내용이 확실히 있는 Group 도 ``COUNT 0`` 을 답한다. 이 채널의 0/빈값은
   부재의 증거가 아니다
3. t104 — ``introspect`` 27개는 「이게 전부」가 아니라 「나머지 111개는 도달
   불가」였다
4. t109(C3+C4) — 못 찾은 풀이 빈 풀로 둔갑하고, 판독 실패 단면이 빈 점유 집합이
   됐다

자리별로 고치면 다섯 번째 자리가 생길 때 또 난다. 그래서 술어를 여기 하나만
두고, 슬롯을 재는 자리는 **전부 이것을 부른다.**

## 이 술어가 답하는 정확한 질문

「이 단면을 근거로 **「이 슬롯은 비었다」**고 말할 수 있는가?」

말할 수 없는 경우가 둘이고, 사유가 다르므로 코드도 다르다:

- :data:`SECTION_UNREAD` — 단면이 **관측이 아니다.** 판독이 실패했거나, 애초에
  조회가 없었거나, 조회 대상을 못 찾았다. 이 풀에 대해 아는 것이 0이다.
- :data:`SECTION_TRUNCATED` — 목록이 잘렸다. 안 보이는 자리에 점유가 있을 수
  있으므로 어느 슬롯도 비었다고 말할 수 없다.

## 「빈 관측」과 「관측 없음」은 다르다

``{"objects": [], "truncated": False}`` 는 **정당한 빈 풀**이다 — 콘솔이
답했고, 그 답이 「없다」였다. 이 술어는 그것을 통과시킨다. 통과시키지 않으면
정상적인 첫 임포트가 영영 막힌다.

막는 것은 그 모양을 **관측 없이 지어낸** 경우다. 그래서 이 술어만으로는 부족하고,
**생산 지점이 위조하지 않는 것**이 짝으로 필요하다(t109 C3) — 지어낸 성공 단면은
어떤 소비 측 검사로도 진짜와 구별되지 않는다.

## 절단은 왜 여기 있나

두 사유의 결론이 같기 때문이다: 어느 쪽이든 **슬롯을 비었다고 못 말한다.** 사유를
가르는 것은 사람이 무엇을 고쳐야 하는지가 다르기 때문이다 — 판독 실패는 연결을,
절단은 페이징을 본다.
"""

from __future__ import annotations

from collections.abc import Mapping

__all__ = ["SECTION_TRUNCATED", "SECTION_UNREAD", "section_refusal"]

#: 단면이 관측이 아니다 — 이 풀에 대해 아는 것이 0이다.
SECTION_UNREAD = "section_unread"

#: 목록이 잘렸다 — 안 보이는 자리의 점유를 모른다.
SECTION_TRUNCATED = "section_truncated"


def section_refusal(section: Mapping[str, object]) -> tuple[str, str] | None:
    """이 단면으로 「슬롯이 비었다」를 말할 수 있는가. 말할 수 있으면 ``None``.

    말할 수 없으면 ``(코드, 사유)`` — 코드는 위 두 상수 중 하나다.

    판정 순서가 계약이다: **판독 실패가 절단보다 먼저다.** 판독이 실패한 단면에
    ``truncated`` 가 어떤 값으로 들어 있든 그것은 관측이 아니므로, 절단으로
    보고하면 사람이 페이징을 고치러 가서 안 낫는다.

    세 신호를 본다. 셋 다 실제로 이 저장소에서 나오는 모양이고, 하나만 보면
    나머지 둘이 새어 나간다:

    - ``ok`` 가 명시적으로 ``False`` — 포트가 실패를 실어 보냈다
    - ``reason`` 이 문자열 — 툴이 사유를 실어 보냈다
    - ``objects`` 가 목록이 **아니다**(키 부재 포함) — 실패 단면에는 그 키가
      아예 없다. 이것을 안 보면 ``.get("objects") or ()`` 가 빈 점유로 흘러
      슬롯 1..N 을 비었다고 답한다(t109 C4 가 정확히 그 자리였다)
    """
    if section.get("ok") is False:
        return (
            SECTION_UNREAD,
            "단면이 not-ok 로 왔다: " + str(section.get("reason") or "사유 없음"),
        )
    reason = section.get("reason")
    if isinstance(reason, str):
        return (SECTION_UNREAD, "단면을 못 읽었다: " + reason)
    if not isinstance(section.get("objects"), list):
        return (
            SECTION_UNREAD,
            "단면에 목록이 없다 — 조회가 없었거나 실패했다. 목록의 부재는 「비었다」가 아니다",
        )
    if section.get("truncated"):
        return (
            SECTION_TRUNCATED,
            "목록이 절단됐다 — 안 보이는 자리가 점유돼 있을 수 있으므로 어느 "
            "슬롯도 비었다고 말하지 않는다",
        )
    return None
