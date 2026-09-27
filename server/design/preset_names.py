"""콘솔 프리셋 풀에서 **이름**으로 슬롯을 찾는다 — 판독 결과만 받는 순수 함수 (t477).

풀 판독(``query_state`` 페이징)은 세션이 하고, 이 모듈은 그 결과
``{슬롯 번호: 이름}`` 만 받는다. 그래서 콘솔 없이 시험할 수 있고, 같은 규칙을
여러 소비자가 나눠 쓴다:

* 포지션 라벨 → Position 풀 슬롯 (``ChatSession._resolve_position_preset_labels``, t232)
* 초안의 포지션·페이저 이름 → 풀 번호 (``ChatSession._resolve_draft_preset_names``, t477)
* 컬러 프리셋 이름 참조(t453 이 같은 판독 계열을 쓴다 — 새 규칙을 만들지 말고 여기를 쓴다)

## 규칙

1. **정확한 이름** — 콘솔 이름에서 ``#n`` 중복 접미를 뗀 베이스이름이 찾는 이름과
   같다(대소문자까지). t232 부터의 규칙 그대로다.
2. **첫 낱말**(``leading_token=True`` 일 때만) — 정확한 이름이 하나도 없을 때, 콘솔
   이름의 첫 낱말이 찾는 이름과 같다(대소문자 무시). 실기 포지션 이름은
   ``POS05 팬아웃 종점 (객석 상단) · 합성좌표`` 처럼 길어서(t469 run2 캡처) 감독이
   ``POS05`` 라고 적으면 1번 규칙으로는 못 찾는다. 이름 중간 낱말이나 부분
   문자열로는 찾지 않는다 — 그것은 짐작이다.

후보가 둘 이상이면 ``span`` (운영자가 고른 구간) 안에 정확히 하나가 있을 때만 그것을
쓰고, 아니면 모호로 거부한다. 번호를 지어내지 않는다.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

__all__ = [
    "NAME_ABSENT",
    "NAME_AMBIGUOUS",
    "POOL_UNREAD",
    "PresetNameMatch",
    "PresetPoolMatch",
    "match_preset_name",
    "match_preset_name_across_pools",
]

#: 못 찾은 이유. 세 갈래는 감독에게 다른 말로 나가야 한다 — 「저장 안 함」과
#: 「콘솔이 안 읽힘」과 「여러 개라 모름」은 할 일이 다르다(t232 시험의 요구).
NAME_ABSENT = "absent"
NAME_AMBIGUOUS = "ambiguous"
POOL_UNREAD = "pool_unread"


@dataclass(frozen=True)
class PresetNameMatch:
    """한 풀 안의 판정. ``slot`` 이 ``None`` 이면 ``kind`` 가 이유다."""

    slot: int | None
    #: 찾았을 때 어느 규칙으로 — ``"exact"`` | ``"leading_token"``.
    rule: str | None = None
    #: 찾은 슬롯의 콘솔 이름(감독이 반영 메모에서 무엇이 불렸는지 읽는다).
    name: str | None = None
    kind: str | None = None
    candidates: tuple[int, ...] = ()


@dataclass(frozen=True)
class PresetPoolMatch:
    """여러 풀을 걸친 판정. ``slot`` 이 ``None`` 이면 ``kind`` 가 이유다."""

    pool_no: int | None
    slot: int | None
    rule: str | None = None
    name: str | None = None
    kind: str | None = None
    #: 후보 ``(풀, 슬롯)`` — 모호할 때 사유에 적는다. 읽지 못한 풀 번호는 ``unread``.
    candidates: tuple[tuple[int, int], ...] = ()
    unread: tuple[int, ...] = ()


def _base(name: str) -> str:
    return name.split("#", 1)[0]


def _leading(name: str) -> str:
    words = _base(name).split()
    return words[0].casefold() if words else ""


def match_preset_name(
    pool: Mapping[int, str | None],
    name: str,
    *,
    span: tuple[int, int] | None = None,
    leading_token: bool = False,
) -> PresetNameMatch:
    """``pool`` (슬롯 → 이름)에서 ``name`` 의 슬롯 하나 — 규칙은 모듈 설명."""
    target = name.strip()
    named = {slot: text for slot, text in pool.items() if isinstance(text, str)}
    rule = "exact"
    candidates = sorted(slot for slot, text in named.items() if _base(text) == target)
    if not candidates and leading_token and target:
        rule = "leading_token"
        folded = target.casefold()
        candidates = sorted(slot for slot, text in named.items() if _leading(text) == folded)
    if not candidates:
        return PresetNameMatch(slot=None, kind=NAME_ABSENT)
    if len(candidates) > 1 and span is not None:
        inside = [slot for slot in candidates if span[0] <= slot <= span[1]]
        if len(inside) == 1:
            candidates = inside
    if len(candidates) > 1:
        return PresetNameMatch(slot=None, kind=NAME_AMBIGUOUS, candidates=tuple(candidates))
    slot = candidates[0]
    return PresetNameMatch(slot=slot, rule=rule, name=named[slot])


def match_preset_name_across_pools(
    pools: Mapping[int, Mapping[int, str | None] | None],
    name: str,
    *,
    leading_token: bool = False,
) -> PresetPoolMatch:
    """여러 풀(풀 번호 → 판독 결과, 못 읽었으면 ``None``)에서 ``name`` 하나.

    읽지 못한 풀이 하나라도 있으면 다른 풀에서 찾았어도 거부한다 — 그 풀에 같은
    이름이 있을 수 있어 「유일하다」고 말할 수 없다(모름 ≠ 없음).
    """
    unread = tuple(sorted(pool_no for pool_no, pool in pools.items() if pool is None))
    if unread:
        return PresetPoolMatch(pool_no=None, slot=None, kind=POOL_UNREAD, unread=unread)
    found: list[tuple[int, PresetNameMatch]] = []
    ambiguous: list[tuple[int, int]] = []
    for pool_no in sorted(pools):
        pool = pools[pool_no]
        assert pool is not None  # 위에서 걸렀다
        match = match_preset_name(pool, name, leading_token=leading_token)
        if match.slot is not None:
            found.append((pool_no, match))
        elif match.kind == NAME_AMBIGUOUS:
            ambiguous.extend((pool_no, slot) for slot in match.candidates)
    if ambiguous or len(found) > 1:
        candidates = tuple(sorted(ambiguous + [(p, m.slot) for p, m in found if m.slot]))
        return PresetPoolMatch(pool_no=None, slot=None, kind=NAME_AMBIGUOUS, candidates=candidates)
    if not found:
        return PresetPoolMatch(pool_no=None, slot=None, kind=NAME_ABSENT)
    pool_no, match = found[0]
    return PresetPoolMatch(pool_no=pool_no, slot=match.slot, rule=match.rule, name=match.name)
