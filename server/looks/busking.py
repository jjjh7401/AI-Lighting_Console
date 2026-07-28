"""버스킹 준비 마법사 — 장르 조회 계층 (SPEC-COPILOT-BUSKWIZ-001, M1).

REQ-BUSKWIZ-001 (절단 없는 결정론적 조회) · REQ-BUSKWIZ-002 (한/영 별칭 해석과
정직한 실패) · REQ-BUSKWIZ-003 (룩 계층 무변경 — 읽기 전용 순회).

이 모듈은 출하된 ``LookLibrary``를 읽기만 한다. 콘솔·리그·게이트·실행 포트 어느
것도 import하지 않으며, 그 경계는 ``test_architecture.py``가 지킨다.

@MX:NOTE: [AUTO] 장르 조회가 ``matching.match_looks``를 쓰지 않는 것은 취향이
  아니라 요구다. 그 경로는 결과를 ``MAX_TOOL_MATCHES``(=8)에서 자르고
  ``truncated`` 신호를 붙이는데, 그것은 "물어본 것 중 상위 몇 개"를 돌려주는
  도구의 올바른 규율이지 "이 장르 전부"를 돌려주는 도구의 것이 아니다. EDM은
  9룩이므로 그 경로를 타는 순간 **정확히 1건이 조용히 사라진다** — 8룩이
  돌아오고 번들이 만들어지고 실행이 성공하므로 아무도 알아채지 못한다.
  그래서 이 모듈은 라이브러리를 직접 순회하고, 반환 형상에 절단 신호를 두지
  않는다(신호가 있다는 것 자체가 자를 수 있는 경로를 탔다는 뜻이다).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace

from server.looks.instantiate import (
    CreatedPreset,
    LookInstantiation,
    LookInstantiationError,
    PoolIndex,
    build_instantiation,
    resolve_pools,
)
from server.looks.matching import EMPTY_QUERY, resolve_genre
from server.looks.resolver import RoleResolution, resolve_roles
from server.looks.schema import Look, LookLibrary

__all__ = [
    "EMPTY_QUERY",
    "UNRESOLVED_GENRE",
    "GenreBundle",
    "GenreSelection",
    "build_genre_bundle",
    "genres_in",
    "instantiate_genre",
    "looks_for_genre",
    "select_genre",
]

# 장르 축이 침묵한 이유. ``EMPTY_QUERY``(matching에서 재사용)와 나란히 두되
# 합치지 않는다 — "아무것도 안 물었다"와 "우리가 모르는 것을 물었다"는 서로
# 다른 사실이고, 사용자가 취할 조치도 다르다(전자는 장르를 말하면 되고,
# 후자는 후보 중에서 골라야 한다). 이 구분은 resolver가 미매핑 사유를
# 갈라 두는 것과 같은 규율이다.
UNRESOLVED_GENRE = "unresolved_genre"


@dataclass(frozen=True)
class GenreSelection:
    """한 번의 장르 해석 결과. 성공이면 ``looks``, 실패면 ``reason``+``candidates``.

    절단 신호 필드가 **없다**는 것이 이 형상의 계약이다(REQ-BUSKWIZ-001).
    """

    genre: str | None = None
    looks: tuple[Look, ...] = ()
    reason: str | None = None
    candidates: tuple[str, ...] = ()


def genres_in(library: LookLibrary) -> tuple[str, ...]:
    """라이브러리가 실제로 담고 있는 장르. 후보 목록의 유일한 출처다.

    상수로 박지 않는 이유: 라이브러리가 늘면 후보도 함께 늘어야 하고, 두
    곳에 적힌 목록은 한쪽만 갱신되는 순간 거짓말이 된다.
    """
    return tuple(sorted({look.genre for look in library.looks}))


def looks_for_genre(library: LookLibrary, genre: str) -> tuple[Look, ...]:
    """그 장르의 룩 **전량**을 결정론적 전순서로 반환한다.

    순서는 다이내믹스 오름차순 → 동률 시 ``look_id`` 사전순. 이것은 신규
    발명이 아니라 ``matching._ranked``의 타이브레이크 관례가 점수 균일 구간에서
    퇴화한 형태이며, 잔잔함에서 클라이맥스로 올라가는 배열이 버스킹 팔레트의
    자연스러운 읽기 순서이기도 하다.

    모르는 장르는 예외가 아니라 빈 튜플이다 — 해석은 ``select_genre``의 일이고,
    여기서는 "그런 룩이 없다"가 정직한 답이다.
    """
    return tuple(
        sorted(
            (look for look in library.looks if look.genre == genre),
            key=lambda look: (look.dynamics, look.look_id),
        )
    )


def select_genre(library: LookLibrary, query: str) -> GenreSelection:
    """사용자 발화에서 장르를 해석하고 그 장르의 룩 전량을 붙여 돌려준다.

    별칭 표는 ``matching``의 것을 그대로 쓴다(REQ-BUSKWIZ-002) — 여기서
    재정의하면 한/영 어휘가 두 곳에 살게 되고, 그 순간 둘은 갈라지기
    시작한다. 해석 실패는 **가장 비슷한 장르로 승격되지 않는다**: 과신 매칭의
    결과는 사용자가 원한 적 없는 장르의 팔레트가 쇼파일에 남는 것이다.

    한계 하나를 적어 둔다: ``resolve_genre``는 "장르어 0개"와 "장르어 2개
    이상"을 모두 ``None``으로 접는다. 둘을 가르려면 별칭 표를 다시 훑어야
    하는데 그것이 곧 재정의이므로, 이 모듈은 둘을 ``UNRESOLVED_GENRE`` 하나로
    보고한다. 빈 질의만은 표 없이 판별되므로 따로 센다.
    """
    candidates = genres_in(library)
    if not query or not query.strip():
        return GenreSelection(reason=EMPTY_QUERY, candidates=candidates)
    genre = resolve_genre(query)
    if genre is None:
        return GenreSelection(reason=UNRESOLVED_GENRE, candidates=candidates)
    return GenreSelection(genre=genre, looks=looks_for_genre(library, genre))


# -- M2: 슬롯 원장 + 다중 룩 번들 결합 ------------------------------------------


@dataclass(frozen=True)
class GenreBundle:
    """한 장르의 룩 전량을 담은 **하나의** 커맨드 번들과 룩별 계획.

    ``looks``는 룩 하나당 ``LookInstantiation`` 하나이며 조회 순서를 유지한다 —
    보고 계층(M3)이 "장르의 모든 룩이 정확히 한 번씩" 판정에 나타남을
    이 순서 위에서 세운다.
    """

    genre: str
    commands: tuple[str, ...] = ()
    looks: tuple[LookInstantiation, ...] = ()
    spans: tuple[tuple[int, int], ...] = ()
    """``looks``와 같은 길이·같은 순서. ``commands[start:end]``가 그 룩의 구간이다.

    실행 결과의 per-command status를 룩에 귀속시키는 유일한 다리 —
    보고 계층이 결합 규칙을 다시 구현하지 않게 한다."""

    @property
    def created_count(self) -> int:
        return sum(len(plan.created) for plan in self.looks)

    @property
    def skipped_count(self) -> int:
        """N in "N개 건너뜀" — 단위는 프리셋 저장 1회이지 룩이 아니다."""
        return sum(plan.skipped_count for plan in self.looks)

    @property
    def complete(self) -> bool:
        """룩 0개짜리 실행은 완전 성공이 아니다 — 만든 것이 없다."""
        return bool(self.looks) and all(plan.complete for plan in self.looks)


def _advance(pools: PoolIndex, created: tuple[CreatedPreset, ...]) -> PoolIndex:
    """이번 룩이 청구한 슬롯과 라벨을 원장에 누적한 **새** ``PoolIndex``.

    ``PoolBinding``/``PoolIndex``는 frozen인 채로 두고 바깥에서 감싼다 — 그
    자료구조를 고치는 순간 단일 룩 경로(``instantiate_look``)와 P1-1 소비자까지
    함께 흔들린다(spec.md §A PRESERVE).

    **라벨도 함께 누적하는 이유**: ``_plan_stores``의 충돌 검사는
    ``binding.labels``, 즉 **콘솔이 이미 갖고 있는 라벨**만 본다. 같은 번들이
    만들어 낼 라벨끼리는 비교 대상이 아니므로, 표시 이름이 같은 두 룩이 한
    장르에 있으면 서로를 모른 채 각자 저장된다. 현행 32룩에는 그런 이름이
    없지만 **막는 기제가 없던 것**이고, 0건 실측을 방어로 계산하지 않는다.
    """
    if not created:
        return pools
    bindings = dict(pools.bindings)
    for preset in created:
        binding = bindings[preset.family]
        if binding.occupied is None:
            # 도달 불가: 미관측 풀은 `_plan_stores`가 이미 건너뛰므로
            # CreatedPreset를 내지 않는다. None을 튜플로 승격하면 미관측이
            # 관측으로 둔갑하므로, 그 경우엔 원장을 전진시키지 않는다.
            continue
        bindings[preset.family] = replace(
            binding,
            occupied=binding.occupied + (preset.slot,),
            labels=binding.labels + (preset.label,),
        )
    return replace(pools, bindings=bindings)


def _merge(bundles: list[tuple[str, ...]]) -> tuple[tuple[str, ...], tuple[tuple[int, int], ...]]:
    """룩별 번들을 **하나의** 번들로 결합한다.

    단순 연접은 금지다(REQ-BUSKWIZ-006): 룩별 번들은 저마다 선두에 목적지
    커맨드를 갖는데, 2..N번째의 그것은 ``run_commands``의 dedupe에 걸려
    ``skipped_already_executed``로 접힌다. 그러면 번들의 문자열과 콘솔이 실제로
    받은 것이 어긋난다 — LOOKLIB M7이 실물에서 관측한 그 탈락이다. 목적지는
    **선두에 정확히 1회**만 둔다.

    목적지 문자열을 여기서 다시 적지 않는다: 첫 비어 있지 않은 룩 번들의 선두가
    정본이고, 뒤 번들은 **같은 선두를 가졌음을 확인한 뒤에만** 그 한 줄을
    떼어낸다. 리터럴을 복제하면 룩 계층이 바꿔도 여기가 모른다.

    결합된 번들과 함께 **룩별 구간**(`[시작, 끝)` 인덱스)을 돌려준다. 실행
    결과의 per-command status를 룩에 귀속시키려면 그 경계가 필요한데
    (REQ-BUSKWIZ-013 (d)는 룩별 판정을 **실행 결과에서** 산출하라고 요구한다),
    경계를 아는 유일한 자리가 여기다. 보고 계층이 이 규칙을 다시 구현하면
    두 곳이 갈라진다. 빈 룩 번들은 길이 0 구간을 받는다.
    """
    merged: list[str] = []
    spans: list[tuple[int, int]] = []
    destination: str | None = None
    for commands in bundles:
        start = len(merged)
        if not commands:
            spans.append((start, start))  # 정직한 빈 출력 — 그 룩은 세울 저장이 없었다
            continue
        if destination is None:
            destination = commands[0]
            merged.extend(commands)
        else:
            if commands[0] != destination:
                raise LookInstantiationError(
                    "look bundles disagree on the destination command: "
                    f"{destination!r} vs {commands[0]!r}"
                )
            merged.extend(commands[1:])
        spans.append((start, len(merged)))
    return tuple(merged), tuple(spans)


def build_genre_bundle(
    genre: str,
    looks: tuple[Look, ...],
    *,
    resolution: RoleResolution,
    pools: PoolIndex,
) -> GenreBundle:
    """이미 해석된 리그 하나로 룩 전량의 단일 번들을 만든다.

    리그 해석을 **인자로 받는다**는 것이 LOOKLIB이 예약한 "API 형상"의 실체다 —
    ``build_instantiation``이 해석 결과를 키워드 전용 파라미터로 받기 때문에
    한 번 해석한 리그를 N개 룩에 재사용할 수 있다.

    캡처 형상은 ``shared_capture`` **고정**이며 파라미터로 노출하지 않는다
    (REQ-BUSKWIZ-006 하위 절): per-family 형상은 룩마다 패밀리별 값 라인을 따로
    발화하는데, 서로 다른 룩의 값 라인이 문자열로 같아지는 경우가 실재한다
    (실측: edm 두 룩의 ``Attribute 'Dimmer' At 100``). 값 라인은 dedupe 면제
    집합에 없고 직전 ``ClearAll``은 면제라 살아남으므로, 두 번째 값 라인이
    탈락하면 **빈 프로그래머 상태로 ``Store``가 실행되고 콘솔은 성공으로
    답한다.**
    """
    plans: list[LookInstantiation] = []
    ledger = pools
    for look in looks:
        plan = build_instantiation(look, resolution=resolution, pools=ledger)
        plans.append(plan)
        ledger = _advance(ledger, plan.created)
    commands, spans = _merge([plan.commands for plan in plans])
    return GenreBundle(genre=genre, commands=commands, looks=tuple(plans), spans=spans)


def instantiate_genre(
    library: LookLibrary,
    genre: str,
    *,
    groups_section: Mapping[str, object],
    preset_pools_section: Mapping[str, object],
) -> GenreBundle:
    """리그 섹션 원본에서 시작하는 편의 래퍼 — 해석은 **각각 정확히 1회**."""
    return build_genre_bundle(
        genre,
        looks_for_genre(library, genre),
        resolution=resolve_roles(groups_section),
        pools=resolve_pools(preset_pools_section),
    )
