"""부분 정보로 시작하는 패치 인테이크 — 빠진 것을 **오류가 아니라 질문**으로 낸다.

사용자가 *"이 조명 12대 콘솔에 올려줘"* 라고만 말해도 착수할 수 있어야 한다. 모자란
값은 실패가 아니라 **다음 질문**이다. 이 모듈은 그 질문을 만들고, 답이 모이면
:mod:`server.vwx.mvr` / 시트 경로와 **같은 어휘의 행**으로 펼친다.

**질문 순서는 grandMA3 Insert New Fixtures 마법사를 그대로 따른다**
(``patch_add_fixtures.html``):

    1. 픽스처 타입 선택      2. (선택) 이름
    3. 수량                  4. 첫 ID 번호
    5. (Full 모드) Layer/Class
    6. 첫 픽스처의 패치 주소  7. Apply

콘솔에서 사람이 밟는 순서와 같아야 사용자가 **자기가 아는 순서로** 답할 수 있다.

**설계 규약 셋**

* **추측한 값을 조용히 싣지 않는다.** 자동 배정은 사용자가 그 갈래를 고른 뒤에만 하고,
  결과를 :class:`Derivation`으로 되돌려 보여 준다.
* **막는 것과 안 막는 것을 가른다.** 필수만 ``blocking``이다. 나머지는 비워도 진행한다.
* **답은 누적된다.** :func:`assess`는 순수 함수이고 상태는 호출자가 든다 — 같은 요청에
  답을 더해 다시 부르면 남은 질문만 나온다.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields, replace

from server.vwx.mvr import (
    MVR_HEADERS,
    fits_in_one_universe,
    join_absolute,
    next_universe_start,
    split_absolute,
)

#: 질문 종류. 화면이 무엇을 띄울지 정한다.
QUESTION_CHOICE = "choice"
QUESTION_NUMBER = "number"
QUESTION_TEXT = "text"

#: 패치 배정 갈래 — 사용자가 고르는 값.
PATCH_MANUAL = "manual"
PATCH_NEXT_FREE = "next_free"

#: 자동 배정이 만들어 낸 값의 출처 라벨.
DERIVED_NEXT_FREE_ADDRESS = "next_free_address"
DERIVED_NEXT_FREE_FID = "next_free_fid"
DERIVED_SOLE_MODE = "sole_mode_in_library"
DERIVED_FOOTPRINT = "footprint_from_library"
DERIVED_CHANNEL_FROM_FID = "channel_from_fid"


@dataclass(frozen=True)
class LibraryOption:
    """콘솔 라이브러리(또는 동봉 GDTF)가 제공하는 타입 하나."""

    instrument_type: str
    gdtf_fixture: str = ""
    #: 모드 이름 -> DMX 채널 수. 채널 수를 모르면 값이 0이고 그 사실이 그대로 나간다.
    modes: Mapping[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class Occupancy:
    """지금 콘솔이 이미 쓰고 있는 것 — 자동 배정의 근거.

    비어 있으면 자동 배정은 **1부터** 시작한다. 그것이 빈 쇼의 참값이다.
    """

    used_absolute: frozenset[int] = frozenset()
    used_fids: frozenset[int] = frozenset()


#: 자동 배정 결과를 사용자에게 보여 줄 때 앞에서 몇 개까지 적을지.
_PREVIEW_LIMIT = 4

#: 빈 쇼 — 자동 배정이 1부터 시작하는 기준.
EMPTY_CONSOLE = Occupancy()


@dataclass(frozen=True)
class FixtureRequest:
    """사용자가 지금까지 말한 것. **전부 비어 있어도 된다.**"""

    instrument_type: str = ""
    gdtf_fixture: str = ""
    mode: str = ""
    quantity: int | None = None
    patch_mode: str = ""
    universe: str = ""
    address: str = ""
    absolute_address: str = ""
    first_fid: str = ""
    name_prefix: str = ""
    position: str = ""
    layer: str = ""


@dataclass(frozen=True)
class Choice:
    label: str
    value: str
    note: str = ""


@dataclass(frozen=True)
class Question:
    """빠진 값 하나에 대한 물음. **오류 메시지가 아니다.**"""

    field: str
    kind: str
    prompt: str
    why: str
    blocking: bool
    choices: tuple[Choice, ...] = ()
    default: str = ""


@dataclass(frozen=True)
class Derivation:
    """자동으로 채운 값 — 사용자가 확인할 수 있게 되돌려 보낸다."""

    field: str
    value: str
    source: str
    detail: str


@dataclass(frozen=True)
class IntakeResult:
    """한 번의 평가 결과."""

    questions: tuple[Question, ...]
    derivations: tuple[Derivation, ...]
    rows: tuple[dict[str, str], ...]
    ready: bool

    @property
    def blocking_questions(self) -> tuple[Question, ...]:
        return tuple(q for q in self.questions if q.blocking)


def _fuzzy(needle: str, hay: str) -> bool:
    a = "".join(ch for ch in needle.lower() if ch.isalnum())
    b = "".join(ch for ch in hay.lower() if ch.isalnum())
    return bool(a) and (a in b or b in a)


def _resolve_option(request: FixtureRequest, library: Sequence[LibraryOption]):
    """요청의 타입 문자열이 라이브러리의 어느 항목인가.

    **정확히 하나로 좁혀질 때만** 확정한다. 0건이면 「없음」, 2건 이상이면
    **고르라고 묻는다** — 첫 일치를 집지 않는다(그 붕괴가 이 SPEC의 반복 결함이다).
    """
    if not request.instrument_type:
        return None, tuple(library)
    exact = tuple(o for o in library if o.instrument_type == request.instrument_type)
    if len(exact) == 1:
        (only,) = exact
        return only, ()
    near = tuple(o for o in library if _fuzzy(request.instrument_type, o.instrument_type))
    if len(near) == 1:
        (only,) = near
        return only, ()
    return None, near or tuple(library)


def _next_free_block(size: int, count: int, occupancy: Occupancy) -> list[int]:
    """빈 절대주소에서 ``count``개 블록을 잡는다.

    유니버스를 걸치는 자리는 건너뛴다 — 주소 산술은 :mod:`server.vwx.mvr` 한 자리가
    진다(``fits_in_one_universe`` / ``next_universe_start``).
    """
    width = max(size, 1)
    starts: list[int] = []
    taken = set(occupancy.used_absolute)
    cursor = 1
    while len(starts) < count:
        if not fits_in_one_universe(cursor, width):
            cursor = next_universe_start(cursor)
            continue
        window = range(cursor, cursor + width)
        if any(channel in taken for channel in window):
            cursor += 1
            continue
        starts.append(cursor)
        taken.update(window)
        cursor += width
    return starts


def _next_free_fids(count: int, occupancy: Occupancy) -> list[int]:
    out: list[int] = []
    taken = set(occupancy.used_fids)
    candidate = 1
    while len(out) < count:
        if candidate not in taken:
            out.append(candidate)
            taken.add(candidate)
        candidate += 1
    return out


def _type_question(candidates: Sequence[LibraryOption], asked: str) -> Question:
    if asked and candidates:
        prompt = f"'{asked}'에 해당하는 픽스처 타입을 골라 주세요."
        why = (
            "라이브러리에서 하나로 좁혀지지 않았습니다. 이름이 비슷한 타입이 여럿일 때 "
            "먼저 걸린 것을 집으면 엉뚱한 타입으로 패치됩니다 — 그래서 물어봅니다."
        )
    elif asked:
        prompt = f"'{asked}'을(를) 라이브러리에서 찾지 못했습니다. 어떤 타입인가요?"
        why = "콘솔 라이브러리에 없는 타입은 패치할 수 없습니다. GDTF 임포트가 필요할 수 있습니다."
    else:
        prompt = "어떤 픽스처 타입인가요?"
        why = "grandMA3는 픽스처 타입을 먼저 고릅니다 — 모드와 채널 수가 여기서 정해집니다."
    return Question(
        field="instrument_type",
        kind=QUESTION_CHOICE if candidates else QUESTION_TEXT,
        prompt=prompt,
        why=why,
        blocking=True,
        choices=tuple(
            Choice(
                label=option.instrument_type,
                value=option.instrument_type,
                note=f"모드 {len(option.modes)}종" if option.modes else "",
            )
            for option in candidates
        ),
    )


def assess(
    request: FixtureRequest,
    library: Sequence[LibraryOption] = (),
    occupancy: Occupancy | None = None,
) -> IntakeResult:
    """지금까지 받은 것으로 평가한다 — 남은 질문과, 채워진 만큼의 행을 낸다.

    **예외를 던지지 않는다.** 모자라면 :class:`Question`이 나온다.
    """
    occupancy = occupancy if occupancy is not None else EMPTY_CONSOLE
    questions: list[Question] = []
    derivations: list[Derivation] = []

    option, candidates = _resolve_option(request, library)
    if option is None:
        questions.append(_type_question(candidates, request.instrument_type))

    # --- 모드 -------------------------------------------------------------
    mode = request.mode
    modes = dict(option.modes) if option else {}
    if option is not None and not mode:
        if len(modes) == 1:
            # 하나뿐임을 **코드가 단정한다** — `next(iter(...))`/`[0]`은 "여럿 중 첫 것"과
            # 구별되지 않아 모호성 등기 대상이 된다. 언팩은 그 모호성이 없다.
            ((mode, _width),) = modes.items()
            derivations.append(
                Derivation(
                    field="mode",
                    value=mode,
                    source=DERIVED_SOLE_MODE,
                    detail=f"'{option.instrument_type}'에 모드가 하나뿐입니다.",
                )
            )
        else:
            questions.append(
                Question(
                    field="mode",
                    kind=QUESTION_CHOICE,
                    prompt=f"'{option.instrument_type}'의 DMX 모드를 골라 주세요.",
                    why=(
                        "모드마다 채널 수가 달라 주소 간격이 달라집니다. "
                        "잘못 고르면 다음 픽스처와 주소가 겹칩니다."
                    ),
                    blocking=True,
                    choices=tuple(
                        Choice(
                            label=name,
                            value=name,
                            note=f"{width}채널" if width else "채널 수 미상",
                        )
                        for name, width in sorted(modes.items())
                    ),
                )
            )
    elif option is not None and mode and mode not in modes:
        questions.append(
            Question(
                field="mode",
                kind=QUESTION_CHOICE,
                prompt=(
                    f"'{mode}'은(는) '{option.instrument_type}'에 없는 모드입니다. "
                    "다시 골라 주세요."
                ),
                why="라이브러리에 없는 모드로는 패치할 수 없습니다.",
                blocking=True,
                choices=tuple(
                    Choice(label=name, value=name, note=f"{width}채널" if width else "")
                    for name, width in sorted(modes.items())
                ),
            )
        )
        mode = ""

    footprint = modes.get(mode, 0) if mode else 0
    if footprint:
        derivations.append(
            Derivation(
                field="footprint",
                value=str(footprint),
                source=DERIVED_FOOTPRINT,
                detail=f"'{mode}' 모드는 {footprint}채널입니다.",
            )
        )

    # --- 수량 -------------------------------------------------------------
    quantity = request.quantity
    if quantity is None or quantity < 1:
        questions.append(
            Question(
                field="quantity",
                kind=QUESTION_NUMBER,
                prompt="몇 대인가요?",
                why="grandMA3 마법사도 수량을 먼저 받고 그 수만큼 행을 만듭니다.",
                blocking=True,
                default="1",
            )
        )

    # --- 패치 갈래 --------------------------------------------------------
    patch_mode = request.patch_mode
    has_manual = bool(request.absolute_address) or bool(request.universe and request.address)
    if not patch_mode:
        patch_mode = PATCH_MANUAL if has_manual else ""
    if not patch_mode:
        questions.append(
            Question(
                field="patch_mode",
                kind=QUESTION_CHOICE,
                prompt="DMX 주소를 어떻게 정할까요?",
                why=(
                    "grandMA3는 첫 픽스처의 주소를 받아 나머지를 채널 수만큼 띄웁니다. "
                    "빈자리 자동 배정도 콘솔이 제공하는 방식입니다(Patch To Next Free Address)."
                ),
                blocking=True,
                choices=(
                    Choice(
                        label="시작 주소를 직접 지정",
                        value=PATCH_MANUAL,
                        note="예: 1.1 또는 절대주소 1",
                    ),
                    Choice(
                        label="빈자리에 자동 배정",
                        value=PATCH_NEXT_FREE,
                        note=f"현재 점유 {len(occupancy.used_absolute)}채널 기준",
                    ),
                ),
            )
        )
    elif patch_mode == PATCH_MANUAL and not has_manual:
        questions.append(
            Question(
                field="address",
                kind=QUESTION_TEXT,
                prompt="첫 픽스처의 주소를 알려 주세요. (예: 1.1)",
                why="MA3 Patch 표기는 `유니버스.주소`입니다. 절대주소 하나로 주셔도 됩니다.",
                blocking=True,
            )
        )

    # --- 라벨(막지 않는다) -------------------------------------------------
    if not request.position:
        questions.append(
            Question(
                field="position",
                kind=QUESTION_TEXT,
                prompt="행잉 포지션 이름이 있나요? (예: LX1, Backtruss)",
                why="리포트를 사람이 읽을 때 기준이 됩니다. 없어도 패치는 됩니다.",
                blocking=False,
            )
        )

    ready = not any(q.blocking for q in questions)
    if not ready:
        return IntakeResult(
            questions=tuple(questions),
            derivations=tuple(derivations),
            rows=(),
            ready=False,
        )

    # --- 펼치기 -----------------------------------------------------------
    assert option is not None and quantity is not None
    count = quantity

    if patch_mode == PATCH_NEXT_FREE:
        starts = _next_free_block(footprint or 1, count, occupancy)
        preview = starts[:_PREVIEW_LIMIT]
        derivations.append(
            Derivation(
                field="absolute_address",
                value=", ".join(f"{u}.{a}" for u, a in (split_absolute(s) for s in preview))
                + (" …" if len(starts) > len(preview) else ""),
                source=DERIVED_NEXT_FREE_ADDRESS,
                detail=f"빈자리 {count}블록을 잡았습니다(블록당 {footprint or 1}채널).",
            )
        )
    else:
        if request.absolute_address:
            first = int(request.absolute_address)
        else:
            first = join_absolute(int(request.universe), int(request.address))
        starts = [first + index * (footprint or 1) for index in range(count)]

    if request.first_fid:
        fids = [int(request.first_fid) + index for index in range(count)]
    else:
        fids = _next_free_fids(count, occupancy)
        derivations.append(
            Derivation(
                field="first_fid",
                value=str(fids[0]),
                source=DERIVED_NEXT_FREE_FID,
                detail=f"비어 있는 FID {fids[0]}부터 {count}개를 잡았습니다.",
            )
        )
    derivations.append(
        Derivation(
            field="channel",
            value=str(fids[0]),
            source=DERIVED_CHANNEL_FROM_FID,
            detail="Channel을 FID와 같게 둡니다 — 도면·콘솔 조인 키입니다.",
        )
    )

    rows: list[dict[str, str]] = []
    for index, (absolute, fid) in enumerate(zip(starts, fids, strict=True), start=1):
        universe, address = split_absolute(absolute)
        name = f"{request.name_prefix} {index}".strip() if request.name_prefix else ""
        row = dict.fromkeys(MVR_HEADERS, "")
        row.update(
            {
                "Device Type": "Light",
                "Fixture Name": name,
                "Instrument Type": option.instrument_type,
                "GDTF Fixture": request.gdtf_fixture or option.gdtf_fixture,
                "GDTF Fixture Mode": mode,
                "Fixture ID": str(fid),
                "Channel": str(fid),
                "Universe": str(universe),
                "U Address": str(address),
                "Absolute Address": str(absolute),
                "DMX Footprint": str(footprint) if footprint else "",
                "Unit Number": str(index),
                "Position": request.position,
                "Layer": request.layer or request.position,
            }
        )
        rows.append(row)

    return IntakeResult(
        questions=tuple(questions),
        derivations=tuple(derivations),
        rows=tuple(rows),
        ready=True,
    )


def apply_answer(request: FixtureRequest, field_name: str, value: str) -> FixtureRequest:
    """답 하나를 요청에 반영한다 — 모르는 필드는 **조용히 버리지 않고** 그대로 돌려준다."""
    if field_name == "quantity":
        return replace(request, quantity=int(value)) if value.isdigit() else request
    if field_name == "address" and "." in value:
        universe, _, address = value.partition(".")
        if universe.strip().isdigit() and address.strip().isdigit():
            return replace(
                request,
                universe=universe.strip(),
                address=address.strip(),
                patch_mode=PATCH_MANUAL,
            )
    if field_name == "address" and value.isdigit():
        return replace(request, absolute_address=value, patch_mode=PATCH_MANUAL)
    if field_name in _REQUEST_TEXT_FIELDS:
        return replace(request, **{field_name: value})
    return request


#: `quantity`는 정수라 따로 받는다 — 나머지는 전부 문자열 필드다.
_REQUEST_TEXT_FIELDS = frozenset(f.name for f in fields(FixtureRequest) if f.name != "quantity")
