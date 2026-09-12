"""배치 생성 전에 먼저 묻는 두 가지 — 체인 순서와 나눠떨어짐.

리서치 두 편이 같은 전제를 말한다. 18번 문서 §9 항목 2 는 사용자에게
"몇 개 Pan/Tilt 를 만들까요?" **보다 먼저** "같은 방향으로 설치된 장비끼리
묶었나요?" 를 물으라고 하고, 19번 문서 §6 이 꼽은 pan/tilt 자동화 대표 실패
다섯 중 둘이 바로 그 질문으로 잡히는 것들이다:

* "group 순서가 실제 좌우와 반대라 left-to-right 가 right-to-left 로 보인다"
  → :func:`check_chain_order`
* "fixture count 가 12대 기준 matrix block 인데 실제는 8대라 chaser 간격이
  어색하다" → :func:`check_split`

둘 다 이미 손에 쥔 데이터만으로 판정된다. 앞의 것은 패치된 3D 좌표에서 나온
:func:`server.spatial.sorting.spatial_sorted_fids` 의 순서와 대조하는 것이고,
뒤의 것은 나눗셈이다. 180개 프리셋을 틀린 체인 위에 얹으면 틀린 프리셋이
180개 나온다 — 그래서 **생성 전에** 묻는다.

**둘 다 읽기 전용 권고다.** 체인을 고쳐 쓰지 않고, 나눗셈이 안 맞는다고
막지도 않는다. 판정을 돌려줄 뿐이고, 그걸 가지고 무엇을 할지는 호출자의
몫이다 — 사용자에게 되묻거나(18번 문서 §9 가 말하는 순서), 그대로 진행하거나.
결함을 발견해도 예외를 던지지 않는다. 예외는 닫힌 어휘 밖의 이름이나 1 미만의
개수처럼 **입력 자체가 성립하지 않을 때만** 나간다.

이미 있는 것을 다시 짓지 않는다:

* 좌표에서 나온 참 순서는 :mod:`server.spatial.sorting` 이 이미 만든다.
  네 개짜리 닫힌 정렬 어휘도 거기 것을 그대로 쓴다.
* 방향을 말하는 한국어/영어 어휘는 :mod:`server.spatial.choreography` 에
  이미 있다(한글 단어 경계 함정까지 처리된 채로). 자연어 질의는 호출자가
  :func:`~server.spatial.choreography.match_spatial_qualifier` 로 먼저
  정렬 이름으로 바꿔서 넘긴다 — 여기서 두 번째 방향 사전을 만들지 않는다.
* "같은 방향으로 설치되었나"의 물리적 축은 이 저장소가 이미 **거절**로
  다룬다. ``server/web/session.py`` 의 좌표 읽기는 ``Rotx``/``Roty`` 가
  0 이 아닌 기구를 조준 대상에서 빼고 그 사실을 답변에 적는다(조준식이
  ``Rotz`` 에 대해서만 실측되었기 때문이다). 18번 문서는 경고를 제안하지만
  우리는 이미 거절한다.
* 프리셋 덮어쓰기 보호는 ``SPEC-COPILOT-PRESETGUARD-001`` 이 이미 한다.
* Pan/Tilt 계산은 ``aim_pan_tilt`` 가 onPC 2.4.2 에 대고 실측한 것이다.
  18번 문서 §9 항목 6 은 그게 없다고 보고 operator calibration 을
  제안하지만, 우리는 갖고 있다.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from server.spatial.schema import SpatialAnalysis, SpatialAnalysisError
from server.spatial.sorting import spatial_sorted_fids

__all__ = [
    "CHAIN_ORDER_VERDICTS",
    "SPLIT_MODES",
    "SPLIT_VERDICTS",
    "ChainDivergence",
    "ChainOrderCheck",
    "SplitCheck",
    "check_chain_order",
    "check_split",
]

# -- 닫힌 판정 어휘 -------------------------------------------------------------
#
# ``server/prechk/verdicts.py`` 와 ``SPATIAL_LOW_CONFIDENCE_REASONS`` 의 규율을
# 그대로 따른다. 호출자가 분기하는 값이므로 자유 문자열이면 집계도 안 되고,
# 모르는 코드가 원문 그대로 사용자에게 닿는다.

#: 체인이 좌표에서 나온 순서와 어떻게 다른가.
#:
#: ``reversed`` 와 ``transposed`` 를 가르는 것이 이 검사의 존재 이유다. 둘은
#: 고치는 방법이 다르다 — 뒤집힌 체인은 **방향 단어**가 틀린 것이고(왼→오라고
#: 했는데 오→왼 체인을 쥐고 있다), 두 대가 자리를 맞바꾼 체인은 **그 두 대**가
#: 틀린 것이다(fid 배정이나 패치 좌표). "그냥 다르다"로 합치면 어느 쪽 수선을
#: 해야 하는지가 판정에서 사라진다.
CHAIN_ORDER_VERDICTS = frozenset(
    {
        # 좌표에서 나온 순서와 같다.
        "matches",
        # 정확히 뒤집힌 순서다. 전역적 결함이고, 고칠 곳은 방향 단어다.
        "reversed",
        # 같은 집합이 자리만 맞바꿨다. 어긋난 자리가 모두 상호 교환 쌍으로
        # 덮인다 — 이웃한 두 대가 바뀐 전형이 여기 온다.
        "transposed",
        # 같은 집합인데 위 둘 중 어느 형태도 아니다. 자리 목록은 나오지만
        # 한 번의 수선으로 설명되지 않는다.
        "reordered",
        # 애초에 같은 집합이 아니다. 순서를 비교할 수 없다.
        "membership_mismatch",
    }
)

#: 나눗셈 판정. ``over_split`` 은 fan 개수가 기구 수보다 많은 경우 — 빈 fan 이
#: 생기므로 "덜 고르다"가 아니라 아예 성립하지 않는 분할이고, 기구를 어떻게
#: 재배치해도 해결되지 않는다.
SPLIT_VERDICTS = frozenset({"even", "uneven", "over_split"})

#: 무엇을 요청했는가. ``fans`` = 몇 갈래로 나눌까(부채 개수), ``block`` = 한
#: 덩어리에 몇 대씩(matrix block 크기). 산술은 같고 결과를 세는 축이 반대다.
SPLIT_MODES = ("fans", "block")


@dataclass(frozen=True)
class ChainDivergence:
    """체인의 한 자리에서 관측된 어긋남 — 몇 번째 자리에, 무엇 대신 무엇이."""

    #: 0부터 세는 체인 위치.
    index: int
    proposed_fid: int
    expected_fid: int


@dataclass(frozen=True)
class ChainOrderCheck:
    """제안된 체인이 좌표에서 나온 순서와 맞는가에 대한 판정.

    ``expected`` 는 언제나 실려 나간다 — 판정이 "다르다"로 끝나면 호출자는
    바로 다음에 "그럼 뭐가 맞는데"를 물을 수밖에 없고, 그 답을 같은 결과에
    담지 않으면 호출자가 정렬을 한 번 더 돌리게 된다.

    ``low_confidence`` 는 분석 결과에서 그대로 옮겨 온다(``rows.py`` 의 관례).
    행 구조가 확립되지 않은 리그에서는 **참 순서 자체가 확립되지 않은 것**이라,
    거기서 나온 "당신 체인이 뒤집혔다"는 자신 있게 말할 수 있는 주장이 아니다.
    이 층은 깃발을 숨기지도, 계산을 거부하지도 않는다 — 실어 보낸다.
    """

    verdict: str
    sort: str
    proposed: tuple[int, ...]
    expected: tuple[int, ...]
    #: 어긋난 자리들. ``matches`` 와 ``membership_mismatch`` 에서는 비어 있다
    #: (앞은 어긋난 데가 없고, 뒤는 집합이 달라 자리를 맞댈 수 없다).
    #: ``reversed`` 에서는 거의 모든 자리가 실린다 — 사실이긴 하지만 수선할
    #: 곳은 그 자리들이 아니라 방향 단어다. 판정 이름이 그걸 말한다.
    divergences: tuple[ChainDivergence, ...] = ()
    #: 서로 자리를 맞바꾼 위치 쌍 ``(i, j)``, ``i < j``. ``transposed`` 에서만
    #: 채워진다. 이웃한 두 대가 바뀌었으면 ``j == i + 1`` 이다.
    swapped_positions: tuple[tuple[int, int], ...] = ()
    #: 이 리그에 없는 fid — 오타이거나 다른 리그의 번호다.
    unknown_fids: tuple[int, ...] = ()
    #: 분석에는 있는데 체인이 안 부른 fid. 결함이 아니라 **범위 신호**인 경우가
    #: 흔하다: 37대짜리 리그에서 무버 8대만 부채로 편다면, 그 8대로 분석을
    #: 다시 돌려서 넘기는 것이 맞다. 전체 순서를 부분집합으로 걸러내는 것과
    #: 부분집합을 정렬하는 것은 ``center_out`` 과 ``diagonal`` 에서 답이
    #: 갈린다(행 중심과 열 번호가 구성원에 따라 움직인다). 그래서 여기서
    #: 조용히 걸러내지 않고 집합이 다르다고 말한다.
    missing_fids: tuple[int, ...] = ()
    #: 체인이 두 번 부른 fid. 두 번 부른 기구는 부채에서 자리가 둘이 된다.
    duplicate_fids: tuple[int, ...] = ()
    low_confidence: bool = False
    confidence_reason: str | None = None

    @property
    def clean(self) -> bool:
        """체인이 좌표에서 나온 순서와 같은가."""
        return self.verdict == "matches"


@dataclass(frozen=True)
class SplitCheck:
    """요청한 분할이 고르게 떨어지는가에 대한 판정.

    안 떨어질 때 "안 떨어진다"만 말하면 호출자가 할 수 있는 일이 없다. 그래서
    세 가지를 같이 싣는다: 그대로 나눴을 때 실제로 나오는 덩어리 크기, 이
    기구 수에서 **고르게 떨어지는 요청값들**, 그리고 이 요청값을 그대로 쓰려면
    필요한 **기구 수**. 20번 문서 §6.2 가 폭 10 에 대해 말한 세 가지 —
    three fan 은 안 맞고 / two fan 은 5+5 / 12나 9면 three fan 이 맞는다 —
    가 이 세 필드다.
    """

    verdict: str
    mode: str
    count: int
    requested: int
    #: 그대로 나눴을 때 실제로 나오는 덩어리 크기들. 큰 것부터.
    block_sizes: tuple[int, ...]
    remainder: int
    #: 이 기구 수를 고르게 나누는 요청값 전부(= ``count`` 의 약수), 오름차순.
    #: 1 과 ``count`` 자신도 뺀 적 없이 싣는다 — 쓸모는 호출자가 판단한다.
    clean_requests: tuple[int, ...] = ()
    #: 요청값 바로 아래/위의 고르게 떨어지는 요청값. 없으면 ``None``.
    nearest_clean_request_below: int | None = None
    nearest_clean_request_above: int | None = None
    #: 요청값을 그대로 쓰면서 고르게 떨어지려면 필요한 기구 수, 현재 수의
    #: 아래/위로 가장 가까운 것. 아래쪽이 요청값보다 작아질 수밖에 없으면
    #: ``None`` 이다(0대로 나눌 수는 없다).
    clean_fixture_count_below: int | None = None
    clean_fixture_count_above: int | None = None

    @property
    def even(self) -> bool:
        return self.verdict == "even"


def _duplicates(fids: Sequence[int]) -> tuple[int, ...]:
    seen: set[int] = set()
    twice: set[int] = set()
    for fid in fids:
        if fid in seen:
            twice.add(fid)
        seen.add(fid)
    return tuple(sorted(twice))


def _swap_pairs(
    proposed: tuple[int, ...],
    expected: tuple[int, ...],
    divergent: Sequence[int],
) -> tuple[tuple[int, int], ...] | None:
    """어긋난 자리가 전부 상호 교환 쌍으로 덮이면 그 쌍들, 아니면 ``None``.

    자리 ``i`` 와 ``j`` 가 한 쌍이라는 것은 ``i`` 에 ``j`` 의 것이, ``j`` 에
    ``i`` 의 것이 들어가 있다는 뜻이다 — 두 대가 서로 자리를 바꾼 형태.
    하나라도 쌍에 못 들어가는 자리가 남으면 이 체인은 교환으로 설명되지 않으므로
    ``None`` 을 돌려주고 판정은 ``reordered`` 가 된다.
    """
    position_of = {fid: index for index, fid in enumerate(expected)}
    pending = set(divergent)
    pairs: list[tuple[int, int]] = []
    for index in divergent:
        if index not in pending:
            continue
        partner = position_of[proposed[index]]
        if partner == index or partner not in pending:
            return None
        if proposed[partner] != expected[index]:
            return None
        pending.discard(index)
        pending.discard(partner)
        pairs.append((min(index, partner), max(index, partner)))
    if pending:
        return None
    return tuple(sorted(pairs))


def check_chain_order(
    proposed: Sequence[int],
    analysis: SpatialAnalysis,
    sort: str,
) -> ChainOrderCheck:
    """제안된 fid 체인이 ``sort`` 방향의 좌표 순서와 맞는지 본다 — 읽기 전용.

    ``sort`` 는 닫힌 네 이름 중 하나여야 한다. 이름이 틀리면
    :func:`~server.spatial.sorting.spatial_sorted_fids` 가 던진다 — 기본값으로
    떨어지지 않는다. 자연어로 받은 방향은 호출자가
    :func:`~server.spatial.choreography.match_spatial_qualifier` 로 먼저
    이 어휘에 얹어서 넘긴다.

    **호출자가 할 일**: ``clean`` 이면 그대로 생성으로 간다. 아니면
    ``verdict`` 로 분기한다 — ``reversed`` 면 사용자에게 방향을 되묻고,
    ``transposed`` 면 ``swapped_positions`` 가 가리키는 두 대의 fid 배정이나
    좌표를 확인하게 하고, ``membership_mismatch`` 면 분석 범위를 맞춘다.
    이 함수는 그중 무엇도 대신 하지 않고 체인을 손대지도 않는다.
    """
    chain = tuple(proposed)
    expected = spatial_sorted_fids(analysis, sort)

    def _result(verdict: str, **fields) -> ChainOrderCheck:
        return ChainOrderCheck(
            verdict=verdict,
            sort=sort,
            proposed=chain,
            expected=expected,
            low_confidence=analysis.low_confidence,
            confidence_reason=analysis.confidence_reason,
            **fields,
        )

    known = set(expected)
    named = set(chain)
    duplicates = _duplicates(chain)
    unknown = tuple(sorted(named - known))
    missing = tuple(sorted(known - named))
    if duplicates or unknown or missing:
        # 집합이 다르면 자리를 맞댈 수 없다. 여기서 자리별 어긋남을 세면
        # 한 자리 밀린 것만으로 전부 어긋난 것처럼 읽힌다.
        return _result(
            "membership_mismatch",
            unknown_fids=unknown,
            missing_fids=missing,
            duplicate_fids=duplicates,
        )

    if chain == expected:
        return _result("matches")

    divergent = [index for index in range(len(chain)) if chain[index] != expected[index]]
    divergences = tuple(
        ChainDivergence(index=index, proposed_fid=chain[index], expected_fid=expected[index])
        for index in divergent
    )

    if len(chain) > 1 and chain == tuple(reversed(expected)):
        # 길이 2 에서는 뒤집힘과 이웃 교환이 같은 체인이다. 그래도 ``reversed``
        # 로 부르는 쪽이 맞다 — 두 형태의 수선(방향 뒤집기 / 두 대 맞바꾸기)이
        # 같은 결과를 내므로 고를 것이 없고, 방향 쪽이 먼저 의심할 곳이다.
        return _result("reversed", divergences=divergences)

    pairs = _swap_pairs(chain, expected, divergent)
    if pairs is not None:
        return _result("transposed", divergences=divergences, swapped_positions=pairs)
    return _result("reordered", divergences=divergences)


def _divisors(count: int) -> tuple[int, ...]:
    return tuple(candidate for candidate in range(1, count + 1) if count % candidate == 0)


def check_split(count: int, *, fans: int | None = None, block: int | None = None) -> SplitCheck:
    """``count`` 대를 ``fans`` 갈래로 / ``block`` 대씩 나눌 때 고른가 — 읽기 전용.

    둘 중 정확히 하나만 준다. 20번 문서 §6.2 의 실례로 읽으면: 폭 10 에
    ``fans=3`` 은 ``(4, 3, 3)`` 으로 안 떨어지고, 고르게 떨어지는 요청값은
    ``(1, 2, 5, 10)`` 이며(바로 아래가 2, 위가 5), ``fans=3`` 을 그대로
    쓰려면 기구 수가 9 나 12 여야 한다.

    **호출자가 할 일**: ``even`` 이면 그대로 간다. 아니면 사용자에게
    대안값을 보여준다 — 요청을 바꾸거나(``nearest_clean_request_*``) 대상
    기구를 바꾸거나(``clean_fixture_count_*``). 이 함수는 요청값을 몰래
    가장 가까운 약수로 바꾸지 않는다. 안 떨어지는 분할도 콘솔에서 실행은
    되고, 그게 의도일 수도 있다.
    """
    if count < 1:
        raise SpatialAnalysisError(f"fixture count must be at least 1, got {count!r}")
    if (fans is None) == (block is None):
        raise SpatialAnalysisError("give exactly one of fans= or block=")
    mode = "fans" if fans is not None else "block"
    requested = fans if fans is not None else block
    if requested is None or requested < 1:  # pragma: no branch - 위 분기가 None 을 걸렀다
        raise SpatialAnalysisError(f"{mode} must be at least 1, got {requested!r}")

    remainder = count % requested
    clean = _divisors(count)
    below = tuple(value for value in clean if value < requested)
    above = tuple(value for value in clean if value > requested)
    # 요청값을 그대로 쓰면서 고르게 떨어지는 기구 수 = 요청값의 배수.
    multiple_below = count // requested * requested
    fields = {
        "mode": mode,
        "count": count,
        "requested": requested,
        "remainder": remainder,
        "clean_requests": clean,
        "nearest_clean_request_below": below[-1] if below else None,
        "nearest_clean_request_above": above[0] if above else None,
        "clean_fixture_count_below": multiple_below if multiple_below >= requested else None,
        "clean_fixture_count_above": (count // requested + 1) * requested,
    }

    if mode == "fans" and requested > count:
        # 8대를 12갈래로 나눌 수는 없다. 빈 fan 이 생기는 것은 "덜 고르다"가
        # 아니라 성립하지 않는 분할이고, 기구를 재배치해도 달라지지 않는다.
        return SplitCheck(verdict="over_split", block_sizes=(), **fields)

    if mode == "fans":
        base = count // requested
        sizes = tuple([base + 1] * remainder + [base] * (requested - remainder))
    else:
        sizes = tuple([requested] * (count // requested) + ([remainder] if remainder else []))

    return SplitCheck(verdict="even" if remainder == 0 else "uneven", block_sizes=sizes, **fields)
