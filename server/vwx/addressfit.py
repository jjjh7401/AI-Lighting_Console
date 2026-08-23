"""요청한 DMX 주소에 새 장비가 들어갈 자리가 있는가 — 그리고 없으면 어디로.

[round24 후속] 실측에서 앱은 충돌을 **찾아내고도** 산문으로 "결정해 주세요"라고
쓰고 턴을 끝냈다. 사용자는 다음 메시지를 새로 쳐야 했고, 그때는 앱이 원래 과제를
잊은 뒤였다. 없는 픽스처 타입 때와 **같은 실수**다 — 찾은 자리가 그 자리에서
물어야 한다. 이 모듈은 그 물음에 필요한 **사실**만 만든다(묻는 일은 도구 층).

**무엇을 확정으로 말할 수 있는가.** `server/prechk`의 `FootprintPolicy`는 기본으로
꺼져 있다 — 기존 장비를 그 모드에 잇는 연결이 실측으로 반증됐고(ASSUMPTION-27
NEGATIVE), 그래서 **기존 장비가 몇 채널을 먹는지**는 못 믿는다. 그 위에 폭 기반
겹침 판정을 세우면 없는 근거로 거절하게 된다.

그래서 이 모듈은 **한 축만** 쓴다: 기존 장비의 **시작 주소**는 `patch_raw`로 확실히
읽힌다. 그 시작 주소가 내가 차지할 구간 **안에** 들어오면, 그 장비의 폭이 얼마든
겹친다 — 폭을 몰라도 확정이다. 반대 방향(구간 앞에서 시작해 뒤로 뻗어 들어오는
장비)은 폭을 알아야 하므로 **못 잡는다.** 그 한계를 :attr:`Fit.blind_spot`\\ 에 적어
내보낸다 — 조용히 "깨끗하다"고 말하지 않는 것이 이 모듈의 전부다.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from server.prechk.patch import normalize_address

#: 유니버스 하나의 채널 수.
#:
#: **큰 주소 자체는 거절하지 않는다.** 콘솔이 유니버스별 실제 용량을 알려 주지
#: 않으므로(ASSUMPTION-33), 시작 주소가 이 값을 넘는다는 이유로 막으면 콘솔이
#: 받는 자리를 서버가 가로막게 된다. 자리를 **제안**할 때도 이 눈금 안에서만 찾는다.
#:
#: 거절하는 경우는 하나뿐이다: 요청한 자리에서 **폭이 유니버스 끝을 넘을 때**
#: :func:`evaluate` 가 `ok=False` 를 낸다(t15). 이것은 주소를 막는 것이 아니라
#: 「말없이 다른 유니버스로 옮기기」를 막는 것이다 — 옮기면 계획서와 콘솔이 갈리고,
#: 그 어긋남이 아무 데도 남지 않은 채 쓰기 경로까지 간다(실측: 계획 7.480 → 실제
#: 8.1, 그런데 `created` 보고). 옮기지 않고 사실을 내면 판단은 부르는 쪽 몫이 된다.
#:
#: 형제 파이프라인 `vwx/patchplan.plan_addresses` 는 이 거절을 하지 **않는다**.
#: 두 파이프라인이 같은 입력에 다른 판정을 낸다는 뜻이고, 이는 t15 에서 의식적으로
#: 내린 결정이다 — 근거는 `test_autopatch_verify.py` 의 유니버스 끝 표에 적었다.
UNIVERSE_CHANNELS = 512


@dataclass(frozen=True)
class Occupant:
    """이미 자리를 잡고 있는 장비 하나 — 시작 주소만 확실하다."""

    universe: int
    address: int
    name: str | None = None
    fixture_type: str | None = None


@dataclass(frozen=True)
class Placement:
    """새로 놓을 장비 하나의 자리."""

    universe: int
    address: int

    @property
    def text(self) -> str:
        return f"{self.universe}.{self.address}"


@dataclass(frozen=True)
class Fit:
    """요청한 자리에 대한 판정."""

    #: 요청한 시작 주소를 그대로 쓸 수 있는가.
    ok: bool
    requested: str
    #: 놓으려는 장비 수와 하나당 채널 수.
    count: int
    width: int
    #: 확정 충돌 — 내 구간 **안에서 시작하는** 기존 장비들.
    collisions: tuple[Occupant, ...] = ()
    #: 요청대로 놓았을 때의 자리들(충돌이 있어도 계산은 낸다 — 무엇이 겹치는지 보이려고).
    placements: tuple[Placement, ...] = ()
    #: 요청이 형태부터 틀렸을 때의 사유.
    error: str | None = None
    #: 이 판정이 **못 보는 것**. 조용히 지나가지 않기 위해 늘 채운다.
    blind_spot: str = (
        "구간보다 앞에서 시작해 뒤로 뻗어 들어오는 장비는 잡지 못한다 — "
        "기존 장비의 채널 폭은 콘솔 연결이 반증되어(ASSUMPTION-27) 믿을 수 없다. "
        "겹침 없음이 곧 안전 확정은 아니다."
    )

    @property
    def unreadable(self) -> bool:
        """주소를 **못 읽었는가**. 읽었는데 폭이 안 들어가는 것과 다른 일이다.

        판별자는 `placements` 다 — 파싱이 실패하면 자리를 계산하기 전에 돌아오므로
        비어 있고, 초과는 자리를 계산한 뒤라 채워져 있다. 둘을 한 문에 넣으면
        멀쩡히 읽힌 주소에 「주소를 못 읽었다」가 붙거나, 반대로 못 읽은 주소를
        두고 「자리가 비어 있다」고 말한다 — 읽지도 못한 자리의 점유는 알 수 없다.

        판정하는 자리가 셋이라(요청 · 답변 · patch_fixtures) 각자 쓰면 갈린다.
        한 곳만 고친 전례가 이미 있어(t15 → t26) 술어를 여기 한 번만 둔다.

        계약 — 이 술어는 **전역**이다. 모든 `Fit` 에 대해 True 아니면 False 를
        내며 「판별 불가」 상태가 없다. `ok` 가 참이면 error 가 없으므로 False,
        거짓이면 아래 셋 중 정확히 하나에 속한다:

          - error 있고 placements 없음   → 못 읽음   (이 술어가 True)
          - error 있고 placements 있음   → 읽었으나 폭 초과
          - collisions 있음              → 자리 점유

        셋은 서로 배타적이고 `not ok` 전체를 덮는다. 그래서 라벨을 정하는 쪽은
        이 술어 하나와 `collisions` 만 보면 되고, 제3의 상태를 새로 만들 필요가
        없다 — A2 의 「못 읽은 것을 비었다고 말한다」는 상태가 없어서가 아니라
        이 술어를 안 물어서 났다.
        """
        return bool(self.error) and not self.placements

    @property
    def span_text(self) -> str:
        if not self.placements:
            return self.requested
        first, last = self.placements[0], self.placements[-1]
        return f"{first.text} ~ {last.universe}.{last.address + self.width - 1}"


def occupants_from_patch_values(
    values: Iterable[tuple[str | None, str | None, str | None]],
) -> tuple[Occupant, ...]:
    """``(patch_raw, name, fixture_type)`` 묶음을 자리 임자 목록으로.

    읽지 못한 주소는 **버린다**. 0이나 1로 채우면 그 가짜 주소가 충돌 판정에
    그대로 들어간다(`normalize_address` 독스트링의 같은 이유).
    """
    seen: list[Occupant] = []
    for patch_raw, name, fixture_type in values:
        parsed = normalize_address(patch_raw)
        if not parsed.ok:
            continue
        assert parsed.universe is not None and parsed.address is not None
        seen.append(
            Occupant(
                universe=parsed.universe,
                address=parsed.address,
                name=name,
                fixture_type=fixture_type,
            )
        )
    return tuple(seen)


def _placements(universe: int, address: int, count: int, width: int) -> tuple[Placement, ...]:
    """등간격으로 이어 붙인 자리들.

    이어 깔다 경계를 넘으면 다음 유니버스로 넘긴다 — 이건 정당하다. 넘길 것이
    남아 있기 때문이다.

    **첫 자리는 옮기지 않는다.** 거기엔 이어 붙일 앞자리가 없다. 요청받은 주소를
    말없이 다른 유니버스로 바꿔치기하면 부르는 쪽은 자기가 준 주소가 지켜졌다고
    믿는다 — 점유 검사는 엉뚱한 선반을 뒤지고, 쓰기 경로는 엉뚱한 자리에 장비를
    심고서 `created` 를 낸다(t15 HIGH-1). 판정은 :func:`evaluate` 가 낸다.
    """
    spots: list[Placement] = []
    current_universe, current_address = universe, address
    for index in range(count):
        if index > 0 and current_address + width - 1 > UNIVERSE_CHANNELS:
            current_universe += 1
            current_address = 1
        spots.append(Placement(universe=current_universe, address=current_address))
        current_address += width
    return tuple(spots)


def _collisions(spots: Sequence[Placement], width: int, occupants: Sequence[Occupant]):
    """구간 **안에서 시작하는** 기존 장비 — 폭을 몰라도 확정인 축."""
    hit: list[Occupant] = []
    for occupant in occupants:
        for spot in spots:
            if occupant.universe != spot.universe:
                continue
            if spot.address <= occupant.address <= spot.address + width - 1:
                hit.append(occupant)
                break
    return tuple(hit)


def evaluate(
    requested: str | None,
    *,
    count: int,
    width: int,
    occupants: Sequence[Occupant],
) -> Fit:
    """요청한 자리를 판정한다."""
    if count < 1:
        return Fit(
            ok=False, requested=str(requested), count=count, width=width, error="수량이 1 미만이다"
        )
    if width < 1:
        return Fit(
            ok=False,
            requested=str(requested),
            count=count,
            width=width,
            error="채널 폭을 모른다 — 모드를 확정하기 전에는 자리를 판정할 수 없다",
        )
    parsed = normalize_address(requested)
    if not parsed.ok:
        return Fit(
            ok=False,
            requested=str(requested),
            count=count,
            width=width,
            error=parsed.error or "주소를 읽지 못했다",
        )
    assert parsed.universe is not None and parsed.address is not None
    spots = _placements(parsed.universe, parsed.address, count, width)
    hit = _collisions(spots, width, occupants)
    last_channel = parsed.address + width - 1
    overruns = last_channel > UNIVERSE_CHANNELS
    return Fit(
        ok=not hit and not overruns,
        requested=f"{parsed.universe}.{parsed.address}",
        count=count,
        width=width,
        collisions=hit,
        placements=spots,
        error=(
            f"요청한 자리에 실측 폭이 들어가지 않는다 — "
            f"{parsed.universe}.{parsed.address} 에서 {width}채널이면 "
            f"{last_channel}번 채널까지 뻗어 유니버스 끝({UNIVERSE_CHANNELS})을 넘는다. "
            "자리를 옮기지 않았다 — 주소를 바꿀지 모드를 바꿀지는 부르는 쪽이 정한다."
            if overruns
            else None
        ),
    )


def first_free(
    *,
    count: int,
    width: int,
    occupants: Sequence[Occupant],
    start_universe: int = 1,
    universes_to_scan: int = 8,
) -> Fit | None:
    """맨 앞에서부터 훑어 **비어 있는 첫 자리**를 낸다 — 없으면 ``None``.

    유니버스 시작(1번 주소)에서만 후보를 잡는다. 기존 장비 사이의 틈에 억지로
    끼워 넣으면 폭을 모르는 이웃과 겹칠 위험이 커지는데, 그 위험은 이 모듈이
    확인해 줄 수 없다(:attr:`Fit.blind_spot`). 빈 유니버스는 그 위험이 없다.
    """
    used = {occupant.universe for occupant in occupants}
    for offset in range(universes_to_scan):
        universe = start_universe + offset
        if universe in used:
            continue
        fit = evaluate(f"{universe}.1", count=count, width=width, occupants=occupants)
        if fit.ok:
            return fit
    return None
