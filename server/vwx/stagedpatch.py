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
    "픽스처가 **한 대도 생기지 않았다**. 성공했다고 보고하지 마라. 가장 흔한 원인은 "
    "실행 순간 콘솔의 **명령 목적지가 픽스처 계층이 아니었던 것**이다 — Patch 편집기가 "
    "열려 있어야 한다."
)

#: 성공에 필요한 축은 **하나**다: 실행 순간 콘솔의 명령 목적지가 픽스처 계층인가.
#:
#: 2026-08-18 재실측(라이브 onPC 2.4.2.2, 앱의 실제 배포+실행 경로):
#:   편집기 열림 + **서버 실행** -> 60 -> 62 생성됨
#:   목적지 Root  + 서버 실행    -> 0건 (Remove도 함께 no-op)
#: 서버가 목적지를 옮기려는 시도는 전부 실패한다:
#:   `ChangeDestination Patch/Stages/1/Fixtures` = Failed
#:   `ChangeDestination ShowData/Patch/Stages/1/Fixtures` = Failed
#:   `cd Patch` = OK지만 무효 · `Menu Patch` = Not implemented
#:
#: 이전 모델은 이 목적지 조건을 **사람의 발화**로 오인했다("사람이 직접 타이핑해야
#: 한다"). 그래서 조작자에게 명령을 타이핑시켰지만, 실제로 필요한 것은 편집기를
#: 열어 두는 것뿐이고 실행은 앱이 한다.
HANDOVER_STEPS: tuple[str, ...] = (
    "콘솔에서 Menu 키를 누르고 Patch를 엽니다 — **Fixtures 목록이 보이는 화면**까지.",
    # [round24 후속 실측] 표지는 프롬프트 문자열이다. 세 상태를 실물에서 구별했다:
    #   Admin[Fixture]>                                  편집기 닫힘
    #   Admin@ShowData/LivePatch/Stages>                 창은 떴으나 한 계층 위
    #   Admin@ShowData/LivePatch/Stages/Stage 1/Fixtures>  ← 이것이어야 한다
    # 서버는 이 값을 읽지 못한다(responder 화이트리스트에 없고, Lua `GetFocus()`는
    # 명령줄 위젯만 돌려준다 — 2026-08-18 실측) — 그래서 **부탁**한다.
    "명령줄 프롬프트가 «…/Stage 1/Fixtures>»로 끝나는지 확인합니다. "
    "«Admin[Fixture]>»나 «…/Stages>»면 목적지가 아직 픽스처 계층이 아닙니다 — "
    "Patch 창의 픽스처 목록을 한 번 누르면 들어갑니다.",
    "그 상태 그대로 두시면 됩니다 — 명령 입력은 앱이 합니다.",
    "준비되면 이 카드의 버튼을 눌러 주세요 — 앱이 실행하고 콘솔을 읽어 확인합니다.",
)

#: 목적지가 맞는지 사람이 눈으로 대조할 문자열 — 서버가 못 읽으므로 이것이 유일한 검사다.
DESTINATION_MARKER = "/Stage 1/Fixtures>"

HANDOVER_WHY = (
    "패치 생성은 콘솔의 **현재 명령 목적지**가 픽스처 계층일 때만 동작합니다. 그 목적지는 "
    "조작자가 Patch 편집기 안에 있을 때 놓이고, 서버는 목적지를 옮길 수 없습니다"
    "(실측: 편집기 열림 → 생성, 목적지 Root → 0건, ChangeDestination 전부 실패). "
    "실행은 앱이 하니 편집기만 열어 두시면 됩니다."
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
