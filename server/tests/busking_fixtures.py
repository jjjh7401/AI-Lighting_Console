"""BUSKWIZ 테스트 공용 픽스처 (M2·M3 공유).

`test_` 접두사를 쓰지 않는다 — pytest가 테스트 모듈로 수집하지 않게 하려는
것이며, 그래서 두 테스트 모듈이 같은 리그·룩 정의를 **한 곳에서** 가져간다.
픽스처가 갈라지면 두 마일스톤이 서로 다른 리그를 검증하게 된다.
"""

from __future__ import annotations

from server.looks.busking import GenreBundle, build_genre_bundle
from server.looks.instantiate import resolve_pools
from server.looks.resolver import resolve_roles
from server.looks.schema import AttributeValue, Look
from server.tests.test_looks_instantiate import DEFAULT_POOL_NAMES, _groups, _pools

# 역할 6종을 전부 덮는 리그 — 룩이 선언한 역할이 무엇이든 그룹이 붙는다.
FULL_RIG = (
    (11, "Back Wash"),
    (12, "FOH Wash"),
    (13, "Side L"),
    (14, "Top"),
    (15, "Cyc"),
    (16, "Special"),
)


def make_look(
    look_id: str,
    name: str,
    *,
    dynamics: int = 3,
    roles: tuple[str, ...] = ("백라이트",),
    attrs: tuple[tuple[str, float], ...] | None = None,
) -> Look:
    return Look(
        look_id=look_id,
        display_name=name,
        genre="rock",
        dynamics=dynamics,
        roles=roles,
        attributes=tuple(AttributeValue(name=n, value=v) for n, v in (attrs or (("Dimmer", 80),))),
    )


def pools_without(*families: str) -> dict:
    """지정한 패밀리의 풀이 **아예 없는** 리그 — `pool_unresolved` 유도."""
    dropped = {f.casefold() for f in families}
    kept = tuple((no, name) for no, name in DEFAULT_POOL_NAMES if name.casefold() not in dropped)
    return _pools(pools=kept)


def capped_pools() -> dict:
    """드릴다운이 상한에 걸린 리그 — 상한 신호가 보고까지 전파되는지 본다."""
    section = _pools()
    section["drilldown_capped"] = True
    return section


def make_bundle(
    looks,
    *,
    genre: str = "rock",
    groups: tuple[tuple[int | None, str], ...] = FULL_RIG,
    pools: dict | None = None,
) -> GenreBundle:
    return build_genre_bundle(
        genre,
        tuple(looks),
        resolution=resolve_roles(_groups(*groups)),
        pools=resolve_pools(pools if pools is not None else _pools()),
    )
