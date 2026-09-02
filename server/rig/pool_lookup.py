"""프리셋 풀 번호를 이름으로 찾는 이 저장소의 유일한 자리 (t231).

## 왜 여기인가

시트 쪽에 사본이 **다섯** 있었다(`server/orchestrator/tools.py` 의 5015 ·
5579 · 5657 · 5718 · 6752). 다섯 다 `name.casefold().startswith(family)` 한 줄에
첫 일치를 집었고, 다섯 다 **잘린 목록을 부재로 읽었다** — 페이징이 아예 없는
둘과, `paged_children` 을 부르고 절단 플래그를 버리는 셋.

대화 쪽은 같은 일을 이미 한 자리로 모아 두 축을 다 막고 있었다
(`server/web/session.py` `_resolve_named_pool_no` — 완전 일치 + 절단 거부,
2026-08-17 리뷰에서 사본 3본을 합친 것). 비대칭은 그래서 생겼다: **대화는
안전한 쪽으로 틀리고 시트는 위험한 쪽으로 틀린다.**

## 술어가 왜 둘인가 — 하나로 합치면 깨진다

`All` 조회는 계열 조회와 **다른 일**이다. 이 쇼파일의 풀 목록에 `All 1` ~ `All 5`
가 있어서, `all` 접두 조회에서 **다중 일치는 예외가 아니라 정상 상태**다. FX
목적지 해석이 그 다섯 중 첫째를 고르는 것을 의도하고
(`_fx_preset_destination` 독스트링), `server/tests/test_fx_tool.py` 가
`All 1`(21) · `All 2`(22) 둘을 실은 채 `Store Preset 21.` 을 단언해 그 의도를
계약으로 고정해 두었다.

그래서 「다중이면 거절」을 한 벌로 통일하면 FX 목적지 해석이 **항상 거절로
죽는다.** 두 의미를 이름으로 갈라 둔 이유가 이것이다:

- :func:`resolve_family_pool` — 계열 하나를 찾는다. **유일 일치를 요구**한다.
  후보가 둘이면 「후보가 둘이다」를 말하고 거절한다 — 조용히 첫째를 집지 않는다.
- :func:`resolve_all_pool` — `All` 계열 **중 첫째**를 고른다. 다중 일치가
  **정상**이고, 그것이 이 함수의 계약이다.

다음 사람이 「여기도 거절로 통일하자」로 두 번째 함수를 깨지 않도록,
그 의도를 검사가 고정한다(`test_pool_lookup.py`).

## 잘림은 부재가 아니다 — 다만 두 함수가 다르게 쓴다

둘 다 목록을 `paged_children` 으로 끝까지 걷는다. 그래도 미완이면:

- 계열 조회는 **항상 거절한다.** 보이는 창에 하나만 있어도 뒤에 둘째가 있을 수
  있어 **유일성을 세울 수 없다.**
- `All` 조회는 **보이는 창에 하나도 없을 때만** 거절한다. 이 함수가 요구하는
  것은 유일성이 아니라 **첫째**이고, 페이징이 순서를 보존하므로 보이는 창의 첫
  `All` 은 전체의 첫 `All` 이다 — 잘렸어도 그 답은 확정이다.

같은 사실(잘림)이 두 질문에 다른 무게를 갖는다. 한쪽 규율을 다른 쪽에 복사하면
한 번은 과잉 거절이 되고 한 번은 거짓 부재가 된다 — 어느 쪽도 「모름은 거부」가
아니다.
"""

from __future__ import annotations

from typing import Protocol

from server.rig.paging import paged_children

__all__ = [
    "POOL_AMBIGUOUS",
    "POOL_LIST_TRUNCATED",
    "POOL_LIST_UNREAD",
    "POOL_NOT_FOUND",
    "PoolLookupPort",
    "pool_slot_and_name",
    "resolve_all_pool",
    "resolve_family_pool",
]

#: `All` 계열 조회의 접두어. 이 값이 자리마다 다시 적히면 한쪽만 바뀐다.
ALL_POOL_PREFIX = "All"

#: 풀 목록 자체가 안 왔다 — 이 리그의 풀에 대해 아는 것이 0이다.
POOL_LIST_UNREAD = "pool_list_unread"

#: 목록이 잘렸다 — 안 보이는 자리에 대상 풀이 있을 수 있다.
POOL_LIST_TRUNCATED = "pool_list_truncated"

#: 온전한 목록에서 일치가 없다. 이것만이 정직한 「없다」다.
POOL_NOT_FOUND = "pool_not_found"

#: 계열 조회인데 후보가 둘 이상이다.
POOL_AMBIGUOUS = "pool_ambiguous"


class PoolLookupPort(Protocol):
    def query_state(self, path: str, *, offset: int = 0) -> dict: ...


def pool_slot_and_name(child: object) -> tuple[int | None, str]:
    """풀 목록의 자식 하나에서 (슬롯 번호, 이름).

    슬롯 규율은 `server/orchestrator/tools.py` `rig_object` 와 **같다** —
    응답기가 슬롯을 확정하지 못한 자식은 `i` 없이 오고, 정수로 못 읽는 값은
    주소가 아니다. 둘이 어긋나지 않는 것은 `test_pool_lookup.py` 가 같은
    코퍼스에 대고 재서 고정한다(읽어서 「같다」고 하지 않는다).
    """
    if not isinstance(child, dict):
        return None, ""
    name = str(child.get("name") or "")
    number = child.get("i")
    if number is None or isinstance(number, bool):
        return None, name
    try:
        return int(number), name
    except (TypeError, ValueError):
        return None, name


def _listed_pools(state_port: PoolLookupPort, pools_path: str):
    """(풀 목록, 잘렸나, 판독실패 사유).

    잘림은 **사유가 아니라 사실**로 돌려준다 — 두 술어가 잘림을 다르게 쓰기
    때문이다(아래 각 함수 참조). 판독 자체가 실패한 경우만 여기서 거절한다.
    """
    try:
        first = state_port.query_state(pools_path)
    except Exception as exc:  # noqa: BLE001 — 모든 포트 실패는 하나의 거절이다
        return [], False, (POOL_LIST_UNREAD, "프리셋 풀 목록이 오지 않았다: " + str(exc))
    if not isinstance(first, dict) or first.get("ok") is False:
        return [], False, (POOL_LIST_UNREAD, "프리셋 풀 목록이 오지 않았다")
    children, truncated = paged_children(state_port, pools_path, first)
    pools = []
    for child in children:
        number, name = pool_slot_and_name(child)
        if number is not None:
            pools.append((number, name))
    return pools, truncated, None


def resolve_family_pool(state_port: PoolLookupPort, pools_path: str, family: str):
    """계열 이름으로 풀 번호 하나를 찾는다 — **유일 일치를 요구한다**.

    반환은 `(pool_no, refusal)`. 하나는 반드시 `None` 이다.
    `refusal` 은 `(코드, 사람이 읽는 사유)`.

    접두 일치를 유지하는 이유: 완전 일치로 좁히면 `Color Presets` 같은 이름에서
    조용히 멈추는데, 그건 사유를 안 말하는 실패다. 접두를 유지하되 **다중을
    거절**하면 「후보가 둘이다」를 말할 수 있다.

    **잘린 목록은 거절한다** — 보이는 창에 하나만 있어도 뒤에 둘째가 있을 수
    있어 유일성을 세울 수 없기 때문이다. 다만 보이는 것만으로 이미 둘이면
    잘림과 무관하게 다중이 확정이므로 그쪽 사유가 이긴다(더 구체적인 쪽).
    """
    pools, truncated, refusal = _listed_pools(state_port, pools_path)
    if refusal is not None:
        return None, refusal
    needle = family.casefold()
    matches = [(no, name) for no, name in pools if name.casefold().startswith(needle)]
    if len(matches) > 1:
        listed = ", ".join(name + "(" + str(no) + ")" for no, name in matches)
        return None, (
            POOL_AMBIGUOUS,
            "'"
            + family
            + "' 로 시작하는 풀이 "
            + str(len(matches))
            + "개다 — 어느 것인지 고르지 않는다: "
            + listed,
        )
    if truncated:
        return None, (
            POOL_LIST_TRUNCATED,
            "풀 목록이 잘렸다 — 안 보이는 자리에 '"
            + family
            + "' 풀이 또 있을 수 있어 유일성을 세울 수 없다",
        )
    if not matches:
        return None, (
            POOL_NOT_FOUND,
            "풀 목록에 '" + family + "' 로 시작하는 풀이 없다 — 번호를 지어내지 않는다",
        )
    return matches[0][0], None


def resolve_all_pool(state_port: PoolLookupPort, pools_path: str):
    """`All` 계열 풀 **중 첫째**의 번호. 다중 일치가 **정상**이다.

    여기서 여러 개가 나오는 것은 결함이 아니라 이 리그의 모양이다 —
    `All 1` ~ `All 5` 가 함께 산다. 첫째를 고르는 것이 계약이고,
    :func:`resolve_family_pool` 의 「다중이면 거절」을 여기 적용하면
    FX 목적지 해석이 항상 죽는다. 모듈 독스트링 § 술어가 왜 둘인가 참조.

    **잘림을 계열 조회와 다르게 쓴다.** 이 함수가 요구하는 것은 유일성이 아니라
    **첫째**이고, 페이징은 순서를 보존하므로 보이는 창의 첫 `All` 은 전체의 첫
    `All` 이다 — 잘렸어도 그 답은 확정이다. 잘림이 하중을 지는 것은 **보이는
    창에 하나도 없을 때**뿐이다: 그때의 「없다」는 부재가 아니라 모름이다.
    """
    pools, truncated, refusal = _listed_pools(state_port, pools_path)
    if refusal is not None:
        return None, refusal
    needle = ALL_POOL_PREFIX.casefold()
    matches = [no for no, name in pools if name.casefold().startswith(needle)]
    if matches:
        return matches[0], None
    if truncated:
        return None, (
            POOL_LIST_TRUNCATED,
            "풀 목록이 잘렸고 보이는 창에 '"
            + ALL_POOL_PREFIX
            + "' 풀이 없다 — 안 보이는 자리에 있을 수 있어 「없다」고 말할 수 없다",
        )
    return None, (
        POOL_NOT_FOUND,
        "'" + ALL_POOL_PREFIX + "' 로 시작하는 풀이 없다 — 번호를 지어내지 않는다",
    )
