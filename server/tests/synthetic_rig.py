"""검증 하네스 전용 **합성** 리그 기하 — 실기 좌표가 아니다.

카드 t310. 가짜 콘솔(`fake_console.py`)의 `full` 리그에는 `DataPool` 만 있고
`Patch/Stages/1/Fixtures` 가 아예 없었다. 그래서 `get_spatial_context` 가
경로 해석에서 실패했고, 좌표를 읽는 모든 경로 — 그중 **곡 → 디자인 큐 시트**
전체 — 가 「3D 좌표를 읽지 못해 …」로 거절됐다. 사슬에서 디자인 단계만
가짜 콘솔로 한 번도 못 굴려 봤다는 뜻이라, 「가짜 콘솔로 검증했다」는 주장이
조용히 디자인 단계를 빼고 있었다.

여기서 만드는 좌표는 **지어낸 값**이다. 실기 grandMA3 에서 읽은 값이 아니고,
어떤 실측 기록도 아니다. 제품 코드(`server/**` 의 런타임 경로)는 좌표를
지어내면 안 된다 — 없으면 없다고 답하는 것이 규칙이다. 이 모듈은 **테스트
하네스**이고, 하네스가 무대를 하나 세우는 것은 정상이다. 그래서 이름에
`synthetic` 이 들어가고, 이 파일은 `server/tests/` 밖에서 임포트하지 않는다.

좌표계는 `server/spatial/pointing.py` 가 쓰는 것과 같은 미터 단위 무대 좌표다:
X 는 좌(−)/우(+), Y 는 객석(−)/업스테이지(+), Z 는 바닥(0)에서의 높이.
"""

from __future__ import annotations

from dataclasses import dataclass

#: 가짜 콘솔 `full` 리그의 그룹 이름과 같은 역할 어휘를 쓴다 — 그룹 풀과
#: 패치가 서로 다른 무대를 말하지 않도록.
ROLE_ORDER = ("Back Wash", "FOH Wash", "Side L", "Top", "Cyc", "Special")


@dataclass(frozen=True)
class SyntheticFixture:
    """합성 픽스처 한 대: FID, 이름, 그리고 미터 단위 (x, y, z)."""

    fid: int
    name: str
    role: str
    x: float
    y: float
    z: float


def _row(
    start_fid: int, role: str, count: int, *, y: float, z: float, x_from: float, x_to: float
) -> list[SyntheticFixture]:
    """``count`` 대를 x 축으로 균등 배치한다(1대면 중앙 대신 x_from)."""
    if count == 1:
        xs = [x_from]
    else:
        step = (x_to - x_from) / (count - 1)
        xs = [x_from + step * index for index in range(count)]
    return [
        SyntheticFixture(
            fid=start_fid + index,
            name=f"{role} {index + 1}",
            role=role,
            x=round(x, 2),
            y=y,
            z=z,
        )
        for index, x in enumerate(xs)
    ]


def synthetic_fixtures() -> tuple[SyntheticFixture, ...]:
    """16대짜리 합성 리그 — 역할 6종이 서로 다른 깊이·높이에 앉는다.

    16대인 이유는 하나다: 실기 콘솔은 `Patch/Stages/1/Fixtures` 스냅샷을
    19대 근처에서 자른다(`server/tests/test_autopatch_fid.py` 의 실측 주석).
    잘림 복구 경로는 그 자체로 별도의 검증 대상이라, 여기서는 잘림이 끼어들지
    않는 크기를 골라 **디자인 단계**만 재도록 했다.
    """
    fixtures: list[SyntheticFixture] = []
    fixtures += _row(1, "Back Wash", 4, y=6.0, z=6.0, x_from=-6.0, x_to=6.0)
    fixtures += _row(5, "FOH Wash", 4, y=-8.0, z=7.0, x_from=-4.5, x_to=4.5)
    # 사이드는 x 가 같고 깊이(y)로 벌어진다 — 좌측 붐 두 대.
    fixtures += _row(9, "Side L", 1, y=-1.0, z=4.0, x_from=-9.0, x_to=-9.0)
    side_downstage = fixtures[-1]
    fixtures.append(
        SyntheticFixture(fid=10, name="Side L 2", role="Side L", x=side_downstage.x, y=3.0, z=5.5)
    )
    fixtures += _row(11, "Top", 3, y=1.5, z=8.0, x_from=-3.0, x_to=3.0)
    fixtures += _row(14, "Cyc", 2, y=8.0, z=1.0, x_from=-4.0, x_to=4.0)
    fixtures += _row(16, "Special", 1, y=-2.0, z=6.0, x_from=0.0, x_to=0.0)
    return tuple(fixtures)


#: 카드 t315 — **배치 라벨은 같고 크기만 다른** 격자 리그 한 쌍.
#:
#: `server/spatial/topology.py` 의 `grid` 는 깊이·좌우 양쪽이 또렷하게 묶였다는
#: **구조** 판정이라, 크기는 보지 않는다. 그래서 아래 두 리그는 폭과 깊이가
#: 100배 차이나게 뒤집혀 있어도 같은 `grid` 라벨을 받는다 — 그것이 t315 가
#: 고치려는 구멍이고, 이 한 쌍이 그 구멍을 재는 계기다.
#:
#: 좌표는 위 모듈 도크대로 **지어낸 값**이다. 다만 두 모양 모두 실제로 걸리는
#: 리그를 흉내낸다: `wide` 는 좌우 붐 무리가 앞뒤 두 열로 앉은 흔한 박스 배치,
#: `deep` 은 센터라인을 따라 업스테이지로 뻗은 스파인 배치다.
_WIDE_GRID_POINTS: tuple[tuple[float, float, float], ...] = (
    # 좌측 무리(x≈−5)와 우측 무리(x≈+5)가 y=0.0 / y=1.0 두 열에 앉는다.
    (-5.0, 0.0, 5.0),
    (-5.0, 1.0, 5.0),
    (-4.0, 0.0, 5.0),
    (-4.0, 1.0, 5.0),
    (5.0, 0.0, 5.0),
    (5.0, 1.0, 5.0),
    (4.0, 0.0, 5.0),
    (4.0, 1.0, 5.0),
)

_DEEP_GRID_POINTS: tuple[tuple[float, float, float], ...] = (
    # 센터라인 양옆 두 줄(x=−0.5/+0.5)이 객석쪽(y≈−5)부터 업스테이지(y≈+5)까지
    # 네 깊이에 앉는다. 폭 span 1.0m — 「폭이 열린다」를 실을 폭이 없다.
    (-0.5, -5.0, 5.0),
    (0.5, -5.0, 5.0),
    (-0.5, -4.0, 5.0),
    (0.5, -4.0, 5.0),
    (-0.5, 4.0, 5.0),
    (0.5, 4.0, 5.0),
    (-0.5, 5.0, 5.0),
    (0.5, 5.0, 5.0),
)


def _grid_fixtures(
    points: tuple[tuple[float, float, float], ...], role: str
) -> tuple[SyntheticFixture, ...]:
    return tuple(
        SyntheticFixture(fid=index + 1, name=f"{role} {index + 1}", role=role, x=x, y=y, z=z)
        for index, (x, y, z) in enumerate(points)
    )


def synthetic_wide_grid_fixtures() -> tuple[SyntheticFixture, ...]:
    """폭으로 퍼진 격자 — 폭 10.0m, 깊이 1.0m (깊이/폭 = 0.1)."""
    return _grid_fixtures(_WIDE_GRID_POINTS, "Box Boom")


def synthetic_deep_grid_fixtures() -> tuple[SyntheticFixture, ...]:
    """깊이로 쌓인 격자 — 폭 1.0m, 깊이 10.0m (깊이/폭 = 10.0)."""
    return _grid_fixtures(_DEEP_GRID_POINTS, "Centre Spine")


#: 카드 t315 — **폭이 더 넓은 `depth_rows` 리그.** t315 의 규칙이 한 방향으로만
#: 뒤집는다는 것을 재는 계기다: 대칭으로 구현했다면 이 리그가 `ascending` 으로
#: 올라가고, 한 방향 규칙이면 `descending` 에 남는다.
#:
#: x 를 **행마다 엇물려** 21개 값이 전부 다르고 간격이 고르게 만들었다. 이유가
#: 있다: `topology._axis_buckets` 는 중앙값 간격의 4배를 넘는 간격에서 자르는데,
#: 여러 행이 x 를 공유하면 정렬된 x 열에 간격 0 이 섞여 중앙값이 0 이 되고,
#: 그러면 실제 간격 전부가 경계로 잡혀 좌우 판독이 **확신**해 버린다(그러면
#: `grid` 가 이기고 이 리그는 `depth_rows` 가 아니게 된다 — t315 실측). 간격을
#: 고르게 두면 튀는 간격이 없어 `weak_gap_separation` 으로 낮은 확신이 되고,
#: 깊이 열만 확신해 `depth_rows` 가 남는다.
_WIDE_DEPTH_ROW_DEPTHS = (-3.0, 0.0, 3.0)


def synthetic_wide_depth_row_fixtures() -> tuple[SyntheticFixture, ...]:
    """폭이 더 넓은 깊이 열 리그 — 폭 20.0m, 깊이 6.0m (깊이/폭 = 0.3)."""
    return tuple(
        SyntheticFixture(
            fid=index + 1,
            name=f"Truss {index + 1}",
            role="Top",
            x=round(-10.0 + index * 1.0, 3),
            y=_WIDE_DEPTH_ROW_DEPTHS[index % len(_WIDE_DEPTH_ROW_DEPTHS)],
            z=6.0,
        )
        for index in range(21)
    )


def _lua_node(fixture: SyntheticFixture) -> str:
    # 프로퍼티 키는 서버가 실제로 보내는 철자 그대로다
    # (`SPATIAL_FIXTURE_PROPERTIES = ("fid", "posx", "posy", "posz")`).
    # 실기 콘솔의 프로퍼티 조회는 대소문자를 가리지 않지만, 목 노드의
    # `Get` 은 정확히 일치해야 답한다 — 그래서 소문자로 고정한다.
    props = (
        f'{{ fid = "{fixture.fid}", posx = "{fixture.x}", '
        f'posy = "{fixture.y}", posz = "{fixture.z}" }}'
    )
    return f'node("{fixture.name}", "Fixture", {{}}, {props})'


def synthetic_patch_lua() -> str:
    """`Patch()` 루트 별칭이 답하는 `Stages/1/Fixtures` 트리를 만든다.

    응답기(`console/lua/copilot_responder.lua`)의 `ROOT_ALIASES` 는 경로 첫
    세그먼트 `Patch` 를 전역 `Patch()` 로 해석한다. 목 트리에는 그 전역이
    없어서 `Root()` 로 떨어졌고, `Root` 밑에도 `Patch` 가 없어 경로 해석이
    실패했다 — 그것이 이 카드가 쫓던 거절의 실제 원인이다.
    """
    entries = ",\n            ".join(_lua_node(fixture) for fixture in synthetic_fixtures())
    return (
        "local node = __NODE\n"
        '__PATCH = node("Patch", "Patch", {\n'
        '    node("Stages", "Pool", {\n'
        '        node("Stage 1", "Stage", {\n'
        '            node("Fixtures", "Pool", {\n'
        f"            {entries},\n"
        "            }),\n"
        "        }),\n"
        "    }),\n"
        "})\n"
        "function Patch() return __PATCH end\n"
    )
