"""자식 목록을 ``offset`` 페이징으로 끝까지 걷는 이 저장소의 유일한 자리 (t131).

## 왜 여기인가

응답기는 한 응답에 자식을 다 싣지 않는다. 절단 축이 **둘**이고, 둘 다 실재한다:

- **개수 캡** — ``max_children = 24`` (``console/lua/copilot_responder.lua:33``)
- **페이로드 예산** — 절단 경계 ``[1200, 1208)`` 바이트 (t12 실측)

t131 실측(1.6.2, ``Patch/Stages/1/Fixtures``)에서 ``childCount 86`` 이 ``19`` · ``18``
두 창으로 왔다. **19 는 24보다 작다** — 개수 캡으로는 설명이 안 되고 바이트 축에
걸린 것이다. 그래서 「자식이 25개 이상일 때만 페이징한다」는 판별기는 틀리고,
창 크기를 「N개씩 온다」로 못박는 검사도 틀린다. 창 크기는 이름 길이에 따라 변한다.

## 왜 사본이 아니라 한 자리인가

이 루프는 이미 두 벌이 있었다 — ``web/presets_api.py`` 와 ``web/session.py``.
세 번째를 호출부마다 짓기 시작하면 무진전 방어(아래)를 빠뜨린 사본이 반드시
생기고, 그 사본은 **무한 루프**로 나타난다(t104: 낡은 응답기에 페이징을 걸면
실패가 아니라 루프였다). ``server/rig/section.py`` 가 술어를 한 자리로 모은 것과
같은 이유로, 전진 규율도 여기 하나만 둔다.

## 무진전(no-progress) 방어

에코 없는 응답기에 페이징을 걸면 매번 첫 창이 돌아온다. 「받았으니 전진했다」로
읽으면 영원히 돈다. 그래서 **전진의 증거는 ``offset`` 에코**다 — 응답의 ``offset``
이 우리가 요청한 값과 같을 때만 창을 이어 붙인다. 전진 못 하는 갈래 다섯:

1. 포트가 페이징을 모른다 (``TypeError``)
2. 후속 창 조회가 실패했다
3. 에코가 없거나 요청한 값과 다르다 (구버전 응답기)
4. 창이 비었다
5. 페이지 상한에 닿았다

다섯 갈래 전부 ``truncated=True`` 로 **정직하게 미완을 고지**한다. 부분을 전체로
꾸미지 않는 것이 이 모듈의 유일한 약속이다 — 「안 잘렸다」와 「이어 붙였다」는
다르고, 소비 지점(``server/rig/section.py``)은 그 차이에 기대어 fail-closed 한다.
"""

from __future__ import annotations

from typing import Protocol

__all__ = ["PAGE_CAP", "PagedStatePort", "claims_more", "paged_children"]

#: 후속 창 상한 — 이미 받은 첫 창에 더해 최대 10창을 더 읽는다(총 11창,
#: 264슬롯; 세션 판독기는 첫 창 포함 10창이라 한 창 더 여유가 있다). 상한
#: 초과는 완전 판독 주장 없이 ``truncated``로 남는다.
PAGE_CAP = 10


class PagedStatePort(Protocol):
    """``StateQueryPort`` + 선택적 §4.2 페이징(``offset``).

    운영 포트(``_GateStatePort``)는 ``offset`` 을 받는다. 그것을 모르는 낡은
    더블도 그대로 통한다 — 판독기가 ``TypeError`` 를 잡아 첫 창만 쓰고
    ``truncated`` 로 고지하지, 첫 창을 전체인 척하지 않는다.
    """

    def query_state(self, path: str, *, offset: int = 0) -> dict: ...


def claims_more(payload: dict, seen: int) -> bool:
    """절단 판정 이중 방어 — 응답기 truncated 플래그 또는 childCount 산술
    (세션 판독기와 동일, TRUNCATE-001)."""
    node = payload.get("node")
    child_count = node.get("childCount") if isinstance(node, dict) else None
    # bool은 int의 서브클래스 — childCount: true(True>0)가 허위 '더 있음'
    # 판정을 만들지 않게 명시 배제한다(SEC-TYPE-002).
    if isinstance(child_count, bool):
        child_count = None
    return bool(payload.get("truncated")) or (isinstance(child_count, int) and child_count > seen)


def paged_children(state_port: PagedStatePort, path: str, first: dict) -> tuple[list[dict], bool]:
    """``first`` 창 이후를 offset 페이징으로 이어 읽는다 — ``(children, truncated)``.

    ``first`` 는 호출부가 이미 받아 둔 첫 창이다 — 이 함수는 첫 조회를 다시 쏘지
    않는다(왕복 하나를 아끼고, 호출부가 첫 창으로 이미 내린 판정과 어긋나지
    않는다). 반환된 ``truncated`` 가 ``False`` 인 것과 「전부 모았다」는 **같은
    말이 아니다**: 완전성을 단언하려면 ``len(children) == node.childCount`` 를
    보라. 모듈 독스트링 § 무진전 방어에 강등 갈래가 있다.
    """
    children = [c for c in first.get("children", []) if isinstance(c, dict)]
    payload = first
    seen = len(payload.get("children", [])) if isinstance(payload.get("children"), list) else 0
    for _page in range(PAGE_CAP):
        if not claims_more(payload, seen):
            return children, False
        try:
            payload = state_port.query_state(path, offset=seen)
        except TypeError:
            return children, True  # 포트가 페이징을 모른다 — 첫 창만, 정직 고지
        except Exception:  # noqa: BLE001 — 후속 창의 모든 실패는 하나의 미완이다
            return children, True  # 후속 창 실패 — 받은 만큼만, 정직 고지
        echo = payload.get("offset") if isinstance(payload, dict) else None
        window = payload.get("children") if isinstance(payload, dict) else None
        if isinstance(echo, bool) or echo != seen or not isinstance(window, list) or not window:
            return children, True  # 무진전 — 에코 불일치/빈 창은 전진 불가
        children.extend(c for c in window if isinstance(c, dict))
        seen += len(window)
    return children, claims_more(payload, seen)  # 상한 도달 — 남은 주장만큼 절단
