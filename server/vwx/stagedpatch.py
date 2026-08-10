"""장비 정보를 받아 **단계로** 패치까지 몰고, 마지막에 **실측으로 판정한다**.

[round24 후속] 사용자가 요청한 흐름이다: 정보를 넣고, 없는 타입은 사람이 콘솔에서
만들어 주고, 그다음은 앱이 알아서 패치한다. 실측에서 앱은 그 길을 **매번 새로
지어냈다** — 손으로 짠 Lua를 배포·실행하고, 콘솔이 명령을 받았다는 뜻인
``ok=true``를 작업 성공으로 읽어 "성공적으로 패치하였습니다"라고 보고했다.
콘솔은 40대 그대로였다.

이 모듈은 그 길을 **한 줄로 고정한다**:

    타입 확인 → 자리 확인 → FID 배정 → Lua 생성 → 실행 → **재조회 판정**

마지막 칸이 이 모듈의 존재 이유다. :func:`server.vwx.apply.verify_patch`\\ 는
플러그인의 종료 상태를 **인자로 받지 않는다** — 성공은 오직 관측에서 나온다.
여기서도 같다: 몇 대가 생겼는지는 콘솔을 다시 읽어서만 말한다.

**Lua는 손으로 짜지 않는다.** `luagen`이 만들 수 있는 것은 ``AddFixtures`` 호출
하나뿐이고 목적지를 옮기는 문장은 만들 수 없다 — 그 금지를 검사가 아니라 구조로
둔 자리를 우회하면 금지가 사라진다.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from server.vwx.addressfit import Placement
from server.vwx.luagen import LuaPatchEntry, render_addfixtures_plugin

#: 실행했는데 한 대도 안 생겼을 때 사람에게 넘길 사실. 실측 근거를 함께 낸다 —
#: "왜 안 되는지"가 없으면 사용자는 같은 명령을 다시 눌러 본다.
ZERO_CREATED = (
    "플러그인은 돌았지만 픽스처가 **한 대도 생기지 않았다**. 이 빌드에서 "
    "AddFixtures는 실행 경로 10가지·인자 변형 8종에서 0건이었고, 패치 편집기가 "
    "열린 상태(L2)에서도 0건이었다 — 예외도 없이 조용히 아무 일도 하지 않는다"
    "(SPEC-COPILOT-AUTOPATCH-001 M0 · round24 후속 실측). 성공했다고 보고하지 마라."
)

#: [round24 후속 실측] 마지막 가설도 닫혔다. 이 문장이 없으면 모델이 "편집기를
#: 열어 보시라"고 청하고, 사용자는 열어 준 뒤 같은 실패를 다시 본다.
PATCH_EDITOR_HINT = (
    "패치 편집기를 열어 달라고 청하지 마라 — 열린 상태에서도 만들어지지 않는 것을 "
    "실측으로 확인했다(진단: ft=true mode=true pcall=true err=nil인데 0대). "
    "서버가 만들 수 있는 방법은 현재 없다. 조작자가 콘솔에서 직접 패치하도록 "
    "타입·모드·FID·주소를 정확히 알려 주는 것이 여기서 할 수 있는 전부다."
)


@dataclass(frozen=True)
class PlannedFixture:
    """놓을 장비 하나 — 이 자리, 이 번호, 이 이름."""

    fid: int
    name: str
    universe: int
    address: int

    @property
    def address_text(self) -> str:
        return f"{self.universe}.{self.address}"


@dataclass(frozen=True)
class StagedPlan:
    """실행 직전의 계획 전문."""

    console_type: str
    console_mode: str
    footprint: int
    fixtures: tuple[PlannedFixture, ...]
    lua_source: str

    def to_dict(self) -> dict[str, object]:
        return {
            "console_type": self.console_type,
            "console_mode": self.console_mode,
            "channels_per_fixture": self.footprint,
            "fixtures": [
                {
                    "fid": fixture.fid,
                    "name": fixture.name,
                    "address": fixture.address_text,
                }
                for fixture in self.fixtures
            ],
            "lua_source": self.lua_source,
        }


def free_fids(taken: Sequence[int], *, count: int, start: int = 1) -> tuple[int, ...]:
    """비어 있는 FID를 ``count``개 — **연속으로** 고른다.

    흩어진 번호를 주면 조작자가 리그를 머릿속에서 못 센다. 연속 구간이 없으면
    그냥 큰 쪽으로 밀어 붙인다(빈 구간을 억지로 쪼개지 않는다).
    """
    used = set(taken)
    candidate = max(start, 1)
    while True:
        block = range(candidate, candidate + count)
        if not any(fid in used for fid in block):
            return tuple(block)
        candidate += 1


def plan(
    *,
    console_type: str,
    console_mode: str,
    footprint: int,
    placements: Sequence[Placement],
    fids: Sequence[int],
    name_prefix: str | None = None,
) -> StagedPlan:
    """자리와 번호를 Lua 한 벌로 굳힌다.

    자리 수와 번호 수가 어긋나면 **여기서 멈춘다.** 짧은 쪽에 맞춰 조용히 자르면
    요청한 대수보다 적게 만들어 놓고 성공이라 보고하게 된다.
    """
    if len(placements) != len(fids):
        raise ValueError(
            f"자리 {len(placements)}개와 FID {len(fids)}개가 맞지 않는다 — "
            "짧은 쪽에 맞추면 요청한 대수보다 적게 만든다"
        )
    if not placements:
        raise ValueError("놓을 자리가 없다")
    prefix = (name_prefix or console_type).strip() or console_type
    fixtures = tuple(
        PlannedFixture(
            fid=fid,
            name=f"{prefix} {fid}",
            universe=spot.universe,
            address=spot.address,
        )
        for spot, fid in zip(placements, fids, strict=True)
    )
    lua = render_addfixtures_plugin(
        LuaPatchEntry(
            console_type=console_type,
            console_mode=console_mode,
            fid=fixture.fid,
            name=fixture.name,
            universe=fixture.universe,
            address=fixture.address,
        )
        for fixture in fixtures
    )
    return StagedPlan(
        console_type=console_type,
        console_mode=console_mode,
        footprint=footprint,
        fixtures=fixtures,
        lua_source=lua,
    )


@dataclass(frozen=True)
class Outcome:
    """실행 뒤 **재조회로만** 내린 판정."""

    requested: int
    created: int
    #: 요청한 자리에 실제로 앉은 장비들.
    observed_addresses: tuple[str, ...] = ()
    #: 재조회가 전수였는가. 아니면 「없다」를 단정하지 않는다.
    read_complete: bool = True

    @property
    def status(self) -> str:
        if not self.read_complete and self.created < self.requested:
            return "unverified"
        if self.created == 0:
            return "created_nothing"
        if self.created < self.requested:
            return "created_partially"
        return "created"

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "requested": self.requested,
            "created": self.created,
            "observed_addresses": list(self.observed_addresses),
            "read_complete": self.read_complete,
        }


def judge(
    planned: Sequence[PlannedFixture],
    *,
    occupied_after: Sequence[tuple[int, int]],
    read_complete: bool = True,
) -> Outcome:
    """계획한 자리마다 **콘솔에 실제로 무언가 앉았는지**로만 센다.

    플러그인의 종료 상태는 인자에 없다. `apply.verify_patch`와 같은 규약이고,
    같은 이유다 — 이 빌드에서 ``AddFixtures``는 실패해도 ``nil``만 반환한다.
    """
    seats = set(occupied_after)
    hit = tuple(
        fixture.address_text for fixture in planned if (fixture.universe, fixture.address) in seats
    )
    return Outcome(
        requested=len(planned),
        created=len(hit),
        observed_addresses=hit,
        read_complete=read_complete,
    )
