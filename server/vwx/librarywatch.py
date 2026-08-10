"""사용자가 콘솔에서 픽스처 타입을 고르는 동안 **서버가 기다리다 이어받는다**.

MVR도 GDTF 파일도 없을 때의 갈래다. 콘솔에는 이미 방대한 내장 라이브러리가 있고
(실물 화면: ``Generic`` 한 제조사에만 136종), 사용자가 ``Patch > Insert New Fixture``
에서 고르는 것이 가장 빠르다. 서버는 그 선택을 **감지해서 다음 단계로 넘어간다** —
사용자에게 "골랐으면 알려 주세요"라고 다시 묻지 않는다.

**어떻게 감지하는가.** ``Patch/FixtureTypes``를 주기적으로 읽어 **직전 스냅샷과의
차이**를 본다. 사용자가 ``Select``를 누르면 그 타입이 쇼 파일에 들어오고 목록이 늘어난다.

**왜 이름을 안 믿고 스냅샷을 비교하는가.** 사용자가 무엇을 고를지 우리는 모른다.
도면이 ``"Sharpy"``라 적어도 사용자는 ``"Sharpy X Frame"``을 고를 수 있고, 그 판단이
옳을 수 있다 — 실물을 아는 쪽은 사용자다. **새로 들어온 것을 이름으로 검증하지 않고
그대로 받는다.** 대신 무엇이 들어왔는지 **되돌려 보여 주고** 확인을 받는다.

**비용.** 실측 왕복 단가는 66.25 ms다(``typemap.py`` 비용 근거). 열거 한 번이
왕복 ``1 + 타입 수``라 라이브러리 200종이어도 한 폴링이 약 13초, 이름만 세는
얕은 폴링(``query_state`` 1회)은 **66 ms**다. 그래서 **얕게 자주, 깊게 가끔** 본다.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from server.vwx.typemap import FIXTURE_TYPE_LIBRARY_ROOT, LibraryPort

#: 얕은 폴링 한 번의 실측 왕복 수 — ``query_state`` 하나다.
SHALLOW_POLL_ROUNDTRIPS = 1

#: 왕복 단가(ms). ``typemap.RECOVERY_COST_EVIDENCE_ROUNDTRIPS`` 주석과 같은 실측치다.
ROUNDTRIP_MS = 66.25

WATCH_IDLE = "idle"
WATCH_ADDED = "added"
WATCH_UNREADABLE = "unreadable"
WATCH_TRUNCATED_BASELINE = "truncated_baseline"


@dataclass(frozen=True)
class LibrarySnapshot:
    """``Patch/FixtureTypes``의 얕은 스냅샷 — 이름과 선언 총계만."""

    names: tuple[str, ...]
    declared_count: int | None
    #: 응답이 절단됐는가. 절단된 스냅샷을 기준선으로 삼으면 **회수가 추가로 보인다**.
    truncated: bool
    readable: bool
    #: 왔지만 **쓸 수 없던** 행 수 — 매핑이 아니거나 이름이 비었다. 버린 것을 세지
    #: 않으면 `declared_count`와 `len(names)`가 어긋난 이유를 절단으로 오인한다.
    unusable_row_count: int = 0

    @property
    def complete(self) -> bool:
        """이름 전수를 봤는가.

        절단이 없고, **버린 행이 없고**, 선언 총계와 관측 수가 같아야 한다. 셋 중
        하나라도 어긋나면 이 스냅샷을 기준선으로 차이를 판정하지 않는다.
        """
        return (
            self.readable
            and not self.truncated
            and self.unusable_row_count == 0
            and self.declared_count is not None
            and self.declared_count == len(self.names)
        )


@dataclass(frozen=True)
class WatchResult:
    """한 번의 관측 결과."""

    state: str
    added: tuple[str, ...]
    removed: tuple[str, ...]
    snapshot: LibrarySnapshot
    detail: str


def _as_str(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


def read_snapshot(port: LibraryPort) -> LibrarySnapshot:
    """얕은 판독 — ``query_state`` 한 번(왕복 1회).

    모드까지 내려가지 않는다. 「무엇이 새로 생겼는가」를 보는 데 모드는 필요 없고,
    깊은 열거는 타입 수만큼 왕복이 든다.
    """
    try:
        payload = port.query_state(FIXTURE_TYPE_LIBRARY_ROOT)
    except Exception:
        # 포트가 **던지면** 그것도 판독 실패다. 이 모듈은 예외를 밖으로 내지 않는다
        # (`reader.py`와 같은 HARD 규약) — 대화 한 턴이 통째로 죽는 것보다,
        # `readable=False`로 내고 `compare`가 `unreadable`로 **보고**하는 편이
        # 정직하다. 조용히 「변화 없음」으로 읽지 않는 것이 핵심이다.
        return LibrarySnapshot(names=(), declared_count=None, truncated=False, readable=False)
    if not isinstance(payload, Mapping) or payload.get("ok") is not True:
        return LibrarySnapshot(names=(), declared_count=None, truncated=False, readable=False)

    node = payload.get("node")
    declared = None
    if isinstance(node, Mapping):
        raw = node.get("childCount")
        if isinstance(raw, int):
            declared = raw

    children = payload.get("children")
    names: list[str] = []
    unusable = 0
    if isinstance(children, Sequence) and not isinstance(children, (str, bytes)):
        for child in children:
            if not isinstance(child, Mapping):
                unusable += 1
                continue
            name = _as_str(child.get("name"))
            if not name:
                unusable += 1
                continue
            names.append(name)

    return LibrarySnapshot(
        names=tuple(names),
        declared_count=declared,
        truncated=payload.get("truncated") is True,
        readable=True,
        unusable_row_count=unusable,
    )


def compare(before: LibrarySnapshot, after: LibrarySnapshot) -> WatchResult:
    """두 스냅샷의 차이 — 무엇이 들어왔고 무엇이 사라졌는가.

    **판독 실패와 「변화 없음」을 가른다.** 못 읽은 것을 「그대로다」라고 말하면
    사용자가 이미 고른 것을 서버가 못 본 채 계속 기다린다.

    **절단된 기준선도 가른다.** 절단 상태에서 잰 차이는 「사용자가 추가했다」와
    「가려져 있던 것이 보였다」를 구별할 수 없다.
    """
    if not after.readable:
        return WatchResult(
            state=WATCH_UNREADABLE,
            added=(),
            removed=(),
            snapshot=after,
            detail=(
                f"{FIXTURE_TYPE_LIBRARY_ROOT}를 읽지 못했다 — 변화 없음이 아니라 "
                "관측 실패다. 콘솔 연결과 responder를 확인하라."
            ),
        )

    added = tuple(n for n in after.names if n not in set(before.names))
    removed = tuple(n for n in before.names if n not in set(after.names))

    if not before.complete and added:
        return WatchResult(
            state=WATCH_TRUNCATED_BASELINE,
            added=added,
            removed=removed,
            snapshot=after,
            detail=(
                "기준선 스냅샷이 전수가 아니었다 — 늘어난 항목이 사용자가 추가한 것인지 "
                "가려져 있다가 보인 것인지 **구별할 수 없다**. 전수 기준선을 다시 잡아라."
            ),
        )

    if added or removed:
        return WatchResult(
            state=WATCH_ADDED,
            added=added,
            removed=removed,
            snapshot=after,
            detail=f"라이브러리가 바뀌었다 — 추가 {len(added)}종 · 제거 {len(removed)}종.",
        )

    return WatchResult(
        state=WATCH_IDLE,
        added=(),
        removed=(),
        snapshot=after,
        detail="변화 없음.",
    )


@dataclass(frozen=True)
class SelectionPrompt:
    """사용자에게 보낼 안내 — 콘솔에서 무엇을 하면 되는가."""

    instrument_type: str
    steps: tuple[str, ...]
    poll_note: str


def selection_prompt(instrument_type: str, *, poll_seconds: float = 2.0) -> SelectionPrompt:
    """콘솔에서 직접 고르게 하는 안내.

    절차는 ``patch_add_fixtures.html``의 *Insert a Device in the Patch*를 그대로 따른다.
    **서버가 대신 눌러 주지 않는다** — 그 경로는 미검증이고(`U-21`), 되돌릴 수 없는
    쓰기 화면을 자동으로 여는 것은 이 SPEC의 반자동 원칙에도 어긋난다.
    """
    return SelectionPrompt(
        instrument_type=instrument_type,
        steps=(
            "콘솔에서 Menu 키를 누르고 Patch를 탭한다.",
            "목록 아래 New Fixture 자리를 탭한 뒤 Insert New Fixture를 누른다.",
            "Library 탭을 고르고, 드라이브(Internal)와 소스(MA / User / Shares)를 확인한다.",
            f"검색창에 '{instrument_type}'을(를) 입력해 목록을 좁힌다.",
            "제조사 → 픽스처 → 모드 순으로 고르고 Select를 누른다.",
            "마법사가 열리면 **닫아도 된다** — 타입이 쇼에 들어온 것으로 충분하다.",
        ),
        poll_note=(
            f"{poll_seconds:g}초마다 {FIXTURE_TYPE_LIBRARY_ROOT}를 확인한다"
            f"(얕은 판독 {SHALLOW_POLL_ROUNDTRIPS}왕복 ≈ {ROUNDTRIP_MS:g} ms). "
            "선택이 감지되면 그 자리에서 이어서 진행한다 — 다시 알려 주지 않아도 된다."
        ),
    )


def watch_until_change(
    port: LibraryPort,
    baseline: LibrarySnapshot,
    *,
    attempts: int,
    sleep: Callable[[], None] | None = None,
) -> WatchResult:
    """변화가 잡힐 때까지 ``attempts``번 관측한다.

    **시간을 여기서 재지 않는다.** 대기는 ``sleep`` 콜러블이 지고, 이 함수는 순수하게
    「몇 번 볼 것인가」만 안다 — 테스트가 실제로 기다리지 않게 하기 위해서다.

    변화 없이 소진되면 :data:`WATCH_IDLE`을 낸다. **그것도 결과다** — 사용자가 아직
    안 골랐다는 뜻이고, 호출부가 계속 기다릴지 물어볼지 정한다.
    """
    latest = compare(baseline, baseline)
    for index in range(max(attempts, 1)):
        if index and sleep is not None:
            sleep()
        latest = compare(baseline, read_snapshot(port))
        if latest.state != WATCH_IDLE:
            return latest
    return latest
