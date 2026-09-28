from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from typing import NamedTuple

from server.looks.movement import (
    MovementPlan,
)
from server.looks.resolver import GroupCandidate, UnmappedRole
from server.looks.schema import Look
from server.looks.section_fade import SectionFade
from server.looks.section_intent import SectionIntent
from server.looks.section_vocab import (
    SECTION_TERMS,
    resolve_section_dynamics,
)

_MILLISECONDS_PER_SECOND = Decimal("1000")
_SECONDS_PER_MINUTE = Decimal("60")
_MILLISECONDS_PER_MINUTE = 60_000
_MMSS_PATTERN = re.compile(r"^(?P<minutes>\d+):(?P<seconds>\d{2})(?P<fraction>\.\d{1,3})?$")
_SECONDS_PATTERN = re.compile(r"^\d+(?:\.\d+)?$")
_NAME_KEYS = ("name", "section", "label")
_START_KEYS = ("start", "start_time", "time")
EXPLICIT_DYNAMICS_REQUIRED = "explicit_dynamics_required"
UNMAPPED_LOOK = "unmapped_look"
#: 역할 그룹이 리그에 없어 룩을 못 묶은 사유 종류. 카드 t480 D3 — 룩 라이브러리 조립기
#: 보고서(``songcue_report.py``)가 은퇴하면서 이 상수만 여기로 옮겼다(값 그대로).
#: 초안 적용(``cue_sheet_apply``)·리그 사전 점검(``rig_preflight``)이 같은 낱말을 쓴다.
ROLE_UNADDRESSED = "role_unaddressed"
SEQUENCE_UNAVAILABLE = "sequence_unavailable"
SEQUENCE_TRUNCATED = "sequence_truncated"
SEQUENCE_NUMBER_UNAVAILABLE = "sequence_number_unavailable"
ROLE_UNMAPPED = "role_unmapped"
TIMECODE_DESCOPE = "timecode_descope"
AUTO_ADVANCE_DESCOPE = "auto_advance_descope"
TRIGGER_TYPE_TIME = "Time"

#: 변형 표시로 고정한 표기 하나 — SALAMI 프라임(U+2032). 정본 §3 이 표기 셋(프라임 ·
#: RWC 의 A·B · Harmonix 숫자 접미사) 중 하나를 골라 고정하라고 지시한다. ASCII
#: 어포스트로피는 일부러 제외한다: MA3 명령줄의 인용 문자라서 라벨 어휘로 쓰면 큐 이름
#: 조립과 충돌한다.
VARIANT_PRIME = "′"

#: chorus 3 이 더하는 칸(정본 §7.1 표 「블라인더 또는 백색 플래시」). 이 룩 자신의 값을
#: 안 바꾸는 유일한 칸이다 — 블라인더는 다른 그룹(:data:`server.looks.roles`의
#: `블라인더`)이라 :func:`_rung_applied` 가 이 칸에서 ``values`` 를 그대로 돌려주고,
#: 실제 명령은 :func:`_accent_fixture_commands` 가 사다리와 별도로 만든다. 그래도
#: :data:`LADDER_RUNGS`·``ladder`` 보고에는 실린다 — 「이 큐가 블라인더를 켰다」는 사실은
#: 보고할 것이지 값 라인 계산 안에 숨길 것이 아니다.
LADDER_BLINDER_OR_FLASH = "blinder_or_flash"


#: **안전 바닥** — 감광 규칙이 내려갈 수 있는 가장 낮은 ``Dimmer`` 값(정본 §8 안전 한계).
#:
#: 이 값은 **정본 §6 표가 적은 가장 낮은 밝기**다: intro 행 20~40% 와 breakdown · bridge
#: 행 20~35% 의 아래끝이 둘 다 20 이고, 표 어디에도 그보다 낮은 숫자는 없다. 지어낸
#: 숫자가 아니라 인용이라는 것이 요점이다 — 이 저장소에는 **객석 형상도 광도 모형도
#: 없으므로**(실측: ``grep -rn "eye_height|눈높이|house_depth" server`` 0건,
#: ``server/looks/movement.py`` 머리에 기록) 「비상구 표지에 몇 lux 가 닿는다」는 주장은
#: 만들 수 없다. 만들 수 있는 것은 **우리가 얼마나 어둡게 만드는가의 상한**뿐이다.
#:
#: 이 바닥이 지키는 것과 안 지키는 것은 :func:`darkness_target` 독스트링에 적는다.
DARKNESS_FLOOR = 20


@dataclass(frozen=True)
class SongCueSection:
    name: str
    start_ms: int
    index: int
    dynamics: tuple[int, ...] | None
    requires_explicit_dynamics: bool
    label: str = ""
    instance: int = 1
    variant: str = ""
    """구간 하나를 적는 세 필드(정본 §3) — 라벨 + 회차 + 변형 표시.

    ``label`` 은 이름에서 변형 표시를 뗀 것, ``instance`` 는 **그 라벨의** 등장 순번(1부터),
    ``variant`` 는 변형이면 :data:`VARIANT_PRIME` 이고 아니면 빈 문자열이다. 조명 판정은
    ``label`` 로 의도를 정하고 ``instance`` 로 강도를 정한다.

    회차는 표준 데이터셋이 주지 않는다 — Harmonix 912곡 주석에서 1·2·3번째 후렴이 전부
    문자열 ``chorus`` 다. 그래서 후처리 카운터로 만들며, 그 카운터는
    :func:`_numbered_by_label` **하나**다.

    기본값이 「이름 없는 라벨 · 1회차 · 변형 없음」인 이유는 파서를 거치지 않고 손으로
    만드는 호출자(``server/web/session.py`` 의 타이밍 경로) 때문이다 — 그쪽은 회차를 쓰지
    않으므로 선언으로 1회차다.
    """


@dataclass(frozen=True)
class SongCueLookSelection:
    section: SongCueSection
    requested_dynamics: tuple[int, ...]
    look: Look | None = None
    reason: str | None = None
    dynamics_matches: tuple[Look, ...] = ()
    """요청한 다이내믹스에 맞는 룩 **전량**, 버스킹 순서 그대로.

    ``look`` 은 그 선두 — 리그를 모르는 자리에서 고를 수 있는 유일한 답이다.
    리그에 실제로 묶이는 룩을 이 중에서 고르는 것은 역할 해석을 가진
    ``_section_bundle`` 의 일이다. 기본값이 빈 튜플이므로, 이 필드 없이 만들어진
    선택(기존 호출자·테스트)은 예전과 똑같이 ``look`` 하나로 동작한다.
    """


@dataclass(frozen=True)
class SongCueSkippedSection:
    section: SongCueSection
    cue_number: int
    reason: str
    detail: str = ""
    collides_with_section_index: int | None = None
    collides_with_cue_number: int | None = None


@dataclass(frozen=True)
class SongCuePreDropDarkness:
    """드롭 앞 큐 하나에서 실제로 뺀 밝기 (정본 §8 [HARD], 카드 t363).

    ``before`` 와 ``after`` 는 그 큐의 ``Dimmer`` 값이고, ``row`` 는 ``after`` 를 정한
    §6 행의 이름이다. 셋을 함께 드는 이유는 하나다 — 「감광했다」는 주장은 두 숫자와
    그 숫자를 정한 문면 없이는 확인할 수 없다.

    ``drop_cue_number`` 는 이 감광이 **누구를 위한 것인지**다. 없으면 보고에서 어느
    드롭이 커졌는지 되짚을 수 없다.
    """

    section: SongCueSection
    cue_number: int
    drop_cue_number: int
    row: str
    before: float
    after: float


@dataclass(frozen=True)
class SongCueWithheldDarkness:
    """드롭 앞에서 밝기를 **못 뺀** 자리 하나와 그 이유 (정본 §8).

    ``cue_number`` 가 ``None`` 인 갈래가 하나 있다 — 드롭이 곡의 첫 구간이라 앞 큐가
    아예 없는 경우(:data:`DARKNESS_NO_PRECEDING_CUE`). 그때도 기록은 남는다: 「앞 큐가
    없어서 안 했다」와 「해야 하는데 안 했다」는 다른 사실이고, 둘 다 안 적으면 같은
    침묵이 된다.
    """

    section: SongCueSection
    cue_number: int | None
    drop_cue_number: int
    reason: str
    detail: str = ""


@dataclass(frozen=True)
class SongCueFrontFill:
    """프론트 필로 이 큐가 **더한** 그룹과 값 (정본 §6.2 [HARD], 카드 t377).

    셋을 함께 드는 이유는 :class:`SongCuePreDropDarkness` 와 같다 — 「채웠다」는 주장은
    무엇을·얼마로 채웠는지 없이는 확인할 수 없다.
    """

    section: SongCueSection
    cue_number: int
    groups: tuple[int, ...]
    dimmer: float


@dataclass(frozen=True)
class SongCueAccentFixture:
    """사다리의 찍는 액센트가 켠 블라인더·스트로브 그룹 (정본 §7.1 표, 카드 t378).

    ``rung`` 은 :data:`LADDER_BLINDER_OR_FLASH` 또는 :data:`LADDER_STROBE_HIT` 둘 중
    하나다 — §6.1 [HARD]가 큐당 액센트 하나로 못박으므로 이 필드도 하나만 든다.
    """

    section: SongCueSection
    cue_number: int
    rung: str
    groups: tuple[int, ...]
    dimmer: float


@dataclass(frozen=True)
class SongCueSectionBundle:
    section: SongCueSection
    cue_number: int
    cue_name: str
    selection: SongCueLookSelection
    commands: tuple[str, ...] = ()
    skipped: tuple[SongCueSkippedSection, ...] = ()
    unmapped: tuple[UnmappedRole, ...] = ()
    bound: Mapping[str, tuple[GroupCandidate, ...]] | None = None
    ladder: tuple[str, ...] = ()
    """이 큐가 기준 룩에 더한 사다리 칸들 — 안 올랐으면 빈 튜플(정본 §7.1).

    밖으로 내는 이유는 보고 하나다: 값이 같아 사라졌던 큐가 이제 저장되므로, 무엇을 더해서
    달라졌는지가 안 보이면 감독은 「같은 룩이 두 번 나갔다」와 구별할 수 없다.
    """

    movement: MovementPlan | None = None
    """이 큐가 실제로 낸 움직임 — 안 냈으면 ``None`` (정본 §6.4, 카드 t357).

    한 번들에서 이 필드가 채워지는 큐는 **하나**다. 왜 하나뿐인지는
    :func:`_movement_carrier` 에 적어 둔다.
    """

    fade: SectionFade | None = None
    """이 큐의 ``CueFade`` — 정본이 이 라벨에 페이드를 안 줬으면 ``None`` (카드 t363).

    ``None`` 이면 ``Store`` 줄에 아무것도 안 붙고, 그 명령은 고치기 전과 바이트 동일하다.
    """

    darkness: SongCuePreDropDarkness | None = None
    """이 큐가 드롭 앞에서 실제로 뺀 밝기 — 안 뺐으면 ``None`` (정본 §8 [HARD]).

    못 뺀 경우는 여기가 아니라 :attr:`SongCueBundle.withheld_darkness` 로 나간다 —
    ``movement`` 와 ``withheld_movement`` 가 갈라져 있는 것과 같은 형상이다.
    """

    darkness_withheld: SongCueWithheldDarkness | None = None
    """이 큐에서 감광을 못 한 이유 — 조립 도중에만 알 수 있는 셋 중 하나.

    번들 수준의 :attr:`SongCueBundle.withheld_darkness` 가 이것을 걷어 간다. 여기에
    한 번 놓는 이유는 :func:`_section_bundle` 이 큐 하나만 보기 때문이고, 곡 전체를
    보는 판정(감광했는데 그 큐가 안 저장됨)은 걷어 가는 쪽에서 붙는다.
    """

    front_fill: SongCueFrontFill | None = None
    """이 큐가 프론트 필로 **더한** 그룹·값 — 채울 것이 없었으면 ``None`` (정본 §6.2
    [HARD], 카드 t377).

    룩이 이미 프론트를 실었으면(:func:`_front_fill` 이 채울 것이 없다고 판단) ``None``
    이다 — 그때는 값 라인 자체에 프론트가 이미 있으므로 이 필드가 비어 있는 것 자체가
    "채울 필요가 없었다"는 보고다.
    """

    accent_fixture: SongCueAccentFixture | None = None
    """이 큐가 사다리의 찍는 액센트로 켠 블라인더·스트로브 그룹 — 안 켰으면 ``None``
    (정본 §7.1 표, 카드 t378).

    ``ladder`` 가 :data:`LADDER_BLINDER_OR_FLASH`/:data:`LADDER_STROBE_HIT` 를 실어도
    이 필드가 ``None`` 일 수 있다 — 리그에 그 그룹이 없으면(:func:`_accent_fixture_commands`)
    칸은 회전했지만 무대에는 아무것도 안 나갔다는 뜻이고, 그 구분이 이 필드의 존재
    이유다.
    """

    accent_withheld: SongCueWithheldAccent | None = None
    """이 큐에서 찍는 액센트를 못 채운 이유 — 조립 도중에만 알 수 있는 셋 중 하나
    (SPEC-LDACCENT-001).

    번들 수준의 :attr:`SongCueBundle.withheld_accents` 가 이것을 걷어 간다 —
    :attr:`darkness_withheld` 와 :attr:`SongCueBundle.withheld_darkness` 가 갈라져
    있는 것과 같은 형상이다.
    """


@dataclass(frozen=True)
class SongCueWithheldMovement:
    """움직임을 선언했는데 못 낸 큐 하나와 그 이유.

    버리지 않고 내보내는 이유가 이 카드의 요점이다 — 고치기 전에는 룩의 movement 가
    **조용히** 사라졌고, 조용한 것이 결함이었다. 여기에 실리면 보고에서 읽힌다.
    """

    section: SongCueSection
    cue_number: int
    band: str
    reason: str
    detail: str = ""


@dataclass(frozen=True)
class SongCueWithheldAccent:
    """찍는 액센트를 낼 자리인데 유효한 후보가 하나도 없어 못 채운 큐 하나와 그 이유
    (SPEC-LDACCENT-001).

    회전이 후보를 고르기 전에 무영향 칸(룩이 그 축을 안 실었거나, 리그에 그 그룹이
    없거나, 이 큐가 속한 섹션 라벨에 §6 행이 없는 칸)을 미리 거르고 나면, 이 회차가
    회전할 후보가 하나도 남지 않을 수 있다. 그때 셀 이름을 지어내는 대신 여기에
    「냈어야 했는데 못 냈다」를 남긴다 — :class:`SongCueWithheldMovement`·
    :class:`SongCueWithheldDarkness` 와 같은 보고 패턴이다.
    """

    section: SongCueSection
    cue_number: int
    reason: str
    detail: str = ""


@dataclass(frozen=True)
class SongCueClimaxReturn:
    """절정 지속시간 상한이 끼워 넣은 복귀 큐 — 어느 절정 큐 뒤에, 몇 박 뒤에,
    무슨 이유로 삽입됐는지(SPEC-LDCLIMAX-001 REQ-LDCLIMAX-010).

    :class:`SongCueWithheldMovement`/:class:`SongCueWithheldDarkness`/
    :class:`SongCueWithheldAccent` 와 같은 "조립 중에만 아는 부가 사실을 명시적으로
    보고한다" 패턴을 따르되, 이것은 유보가 아니라 **삽입** 보고라 별도 클래스로
    둔다.
    """

    source_section: SongCueSection
    source_cue_number: int
    rung: str
    """:data:`LADDER_BLINDER_OR_FLASH` 또는 :data:`LADDER_STROBE_HIT` — 이 상한이
    적용되는 두 칸(design.md §2 대조표)."""
    cap_beats: float
    """2.0(백색 플래시) 또는 4.0(최강 효과) — 정본 §6 상한 값의 상한 끝."""
    inserted_cue_number: int
    inserted_start_ms: int


@dataclass(frozen=True)
class SongCueWithheldClimaxReturn:
    """절정 지속시간 상한이 값 충돌 회피 넛지에도 불구하고 복귀 큐를 못 끼운
    자리 하나와 그 이유(SPEC-LDRETURN-001 REQ-003, REQ-008).

    :class:`SongCueWithheldMovement`/:class:`SongCueWithheldDarkness`/
    :class:`SongCueWithheldAccent` 와 같은 "조립 중에만 아는 부가 사실을
    명시적으로 보고한다" 패턴을 따르되, :class:`SongCueClimaxReturn` 과 같은
    필드 이름 규약(``source_section``/``source_cue_number``/``rung``/
    ``cap_beats``)을 공유한다 — 이것은 삽입이 아니라 **유보** 보고라 별도
    클래스로 둔다.
    """

    source_section: SongCueSection
    source_cue_number: int
    rung: str
    cap_beats: float
    reason: str
    detail: str = ""


@dataclass(frozen=True)
class SongCueBundle:
    song_title: str
    sequence_number: int
    sequence_name: str
    commands: tuple[str, ...]
    sections: tuple[SongCueSectionBundle, ...]
    is_error: bool = False
    reason: str | None = None
    withheld_movement: tuple[SongCueWithheldMovement, ...] = ()
    withheld_darkness: tuple[SongCueWithheldDarkness, ...] = ()
    withheld_accents: tuple[SongCueWithheldAccent, ...] = ()
    climax_returns: tuple[SongCueClimaxReturn, ...] = ()
    """절정 지속시간 상한이 끼워 넣은 복귀 큐 전량 — 안 끼웠으면 빈 튜플
    (SPEC-LDCLIMAX-001 REQ-LDCLIMAX-010). ``withheld_movement``/``withheld_darkness``/
    ``withheld_accents`` 와 같은 자리, 같은 "조용히 넘어가지 않는다" 보고 규율이다.
    """

    withheld_climax_returns: tuple[SongCueWithheldClimaxReturn, ...] = ()
    """값 충돌 회피 넛지가 실패해 못 끼운 복귀 큐 전량 — 안 유보했으면 빈 튜플
    (SPEC-LDRETURN-001 REQ-003, REQ-008). ``climax_returns`` 와 같은 자리, 같은
    "조용히 넘어가지 않는다" 보고 규율이다.
    """

    @property
    def movement_sections(self) -> tuple[SongCueSectionBundle, ...]:
        return tuple(section for section in self.sections if section.movement is not None)

    @property
    def darkened_sections(self) -> tuple[SongCueSectionBundle, ...]:
        return tuple(section for section in self.sections if section.darkness is not None)

    @property
    def front_filled_sections(self) -> tuple[SongCueSectionBundle, ...]:
        """프론트 필이 실제로 그룹을 더한 큐들 (카드 t377)."""
        return tuple(section for section in self.sections if section.front_fill is not None)

    @property
    def accent_fixture_sections(self) -> tuple[SongCueSectionBundle, ...]:
        """블라인더·스트로브가 실제로 켜진 큐들 (카드 t378)."""
        return tuple(section for section in self.sections if section.accent_fixture is not None)

    @property
    def skipped(self) -> tuple[SongCueSkippedSection, ...]:
        return tuple(skipped for section in self.sections for skipped in section.skipped)

    @property
    def stored_sections(self) -> tuple[SongCueSectionBundle, ...]:
        return tuple(section for section in self.sections if section.commands)


@dataclass(frozen=True)
class SongCueTimingAxes:
    timecode_go: bool = True
    auto_advance_go: bool = True
    timecode_skip_reason: str = (
        "ASSUMPTION-20 is GO in M4; DESCOPE branch retained for future rerun"
    )
    auto_advance_skip_reason: str = (
        "ASSUMPTION-22 is GO in M4; DESCOPE branch retained for future rerun"
    )


@dataclass(frozen=True)
class SongCueTimingSkip:
    axis: str
    reason: str


@dataclass(frozen=True)
class SongCueTimingPlan:
    commands: tuple[str, ...]
    timecode_commands: tuple[str, ...] = ()
    auto_advance_commands: tuple[str, ...] = ()
    skipped_axes: tuple[SongCueTimingSkip, ...] = ()


class SectionTimeError(ValueError):
    def __init__(
        self,
        *,
        index: int,
        reason: str,
        previous_start_ms: int | None,
        start_ms: int,
        sections: Sequence[SongCueSection],
    ) -> None:
        self.index = index
        self.reason = reason
        self.previous_start_ms = previous_start_ms
        self.start_ms = start_ms
        self.sections = tuple(sections)
        super().__init__(
            f"section index {index} {reason}: start_ms={start_ms}, "
            f"previous_start_ms={previous_start_ms}"
        )


class SequenceNumberError(ValueError):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class _RawSection(NamedTuple):
    name: str
    start: object


def normalise_start_ms(raw: object) -> int:
    if isinstance(raw, str):
        value = raw.strip()
        match = _MMSS_PATTERN.fullmatch(value)
        if match is not None:
            minutes = int(match.group("minutes"))
            seconds = Decimal(match.group("seconds") + (match.group("fraction") or ""))
            if seconds >= _SECONDS_PER_MINUTE:
                raise ValueError(f"section seconds out of range: {raw!r}")
            return (minutes * _MILLISECONDS_PER_MINUTE) + _seconds_to_milliseconds(seconds)
        if _SECONDS_PATTERN.fullmatch(value):
            return _seconds_to_milliseconds(_decimal_from(value, raw))
        raise ValueError(f"unsupported section time format: {raw!r}")

    if isinstance(raw, bool):
        raise ValueError(f"unsupported section time format: {raw!r}")
    if isinstance(raw, int | float | Decimal):
        return _seconds_to_milliseconds(_decimal_from(str(raw), raw))

    raise ValueError(f"unsupported section time format: {raw!r}")


def parse_sections(
    raw_sections: Iterable[Mapping[str, object] | Sequence[object]],
) -> tuple[SongCueSection, ...]:
    sections = _numbered_by_label(
        tuple(_parse_section(raw, index) for index, raw in enumerate(raw_sections))
    )
    previous: SongCueSection | None = None
    for section in sections:
        if previous is not None:
            if section.start_ms < previous.start_ms:
                raise SectionTimeError(
                    index=section.index,
                    reason="starts_before_previous",
                    previous_start_ms=previous.start_ms,
                    start_ms=section.start_ms,
                    sections=sections,
                )
            if section.start_ms == previous.start_ms:
                raise SectionTimeError(
                    index=section.index,
                    reason="duplicates_previous_start",
                    previous_start_ms=previous.start_ms,
                    start_ms=section.start_ms,
                    sections=sections,
                )
        previous = section
    return sections


# @MX:ANCHOR: [AUTO] 절정 지속시간 상한 — blinder_or_flash/strobe_hit 를 실은 큐마다
#   상한 박수 뒤에 통제된 룩으로 복귀하는 큐를 끼운다(정본 §6, SPEC-LDCLIMAX-001
#   REQ-LDCLIMAX-006~011).
# @MX:REASON: 사다리·프론트필·움직임·감광이 전부 확정된 **완성된 번들** 위에서만
#   "이 큐가 실제로 절정 칸을 실었는가"를 알 수 있다(design.md §2) — 조립 도중에
#   같은 판단을 하려면 SPEC-LDACCENT-001 §B1 이 이미 겪은 "여러 호출자에 컨텍스트를
#   빠짐없이 배선해야 하는" 취약점을 반복한다. 그래서 이 함수는 완성된
#   :class:`SongCueBundle` 을 받아 훑고, 필요할 때만 큐를 더한다 — 기존 큐의 값
#   결정 경로는 건드리지 않는다(REQ-LDCLIMAX-011). SPEC-LDRETURN-001 이 더한
#   분기(F4 후속) — 새로 끼우는 복귀 큐의 값이 이미 번들 안에 있으면
#   `_climax_return_bumped` 로 자신을 넛지하고(REQ-001~002), 넛지도 실패하면
#   삽입을 유보하고 명시적으로 보고한다(REQ-003, REQ-008) — 예외를 던지지 않는다.
def climax_cap_beats(rung: str) -> float:
    """절정 칸이 켜진 채 머무를 수 있는 박수 — 블라인더 2박, 스트로브 4박
    (REQ-LDCLIMAX-006·007).

    값은 이 함수 **한 곳**에만 있다. 대화 길 조립기(``server/design/
    song_cue_composer.py``, 카드 t462)도 이 함수를 불러 쓴다 — 두 길이 같은
    상한을 쓰게 하려고 값을 옮겨 적지 않았다.
    """
    return 2.0 if rung == LADDER_BLINDER_OR_FLASH else 4.0


# @MX:NOTE: [AUTO] §8 안전 한계의 **유일한** 집행 지점 — 감광이 내려갈 수 있는 바닥.
#   (여기도 ANCHOR 가 아니라 NOTE 다 — 위와 같은 파일 상한 사유.)
#   이 함수가 지키는 것과 **못 지키는 것**을 갈라 두지 않으면 다음 사람이 이
#   바닥을 광도 보장으로 읽는다. 지키는 것: 이 규칙이 내보내는 ``Dimmer`` 는 절대
#   :data:`DARKNESS_FLOOR` 아래로 안 간다 — 블랙아웃(§8 이 허용한 세 형태 중 하나)을
#   **일부러 안 만든다**는 뜻이기도 하다. 못 지키는 것: 비상구 표지에 실제로 닿는 빛의
#   양. 객석 형상도 광도 모형도 저장소에 없고(실측 0건), 없는 모형을 지어내면 그 숫자가
#   안전 주장으로 인용된다. 그리고 이 바닥은 **우리가 내리는 값**만 막는다 — 라이브러리가
#   스스로 20 아래로 저작한 룩은 이 규칙이 올리지 않는다(올리는 것은 감광이 아니다).
def darkness_target(intent: SectionIntent) -> int:
    """이 §6 행에서 감광이 내려갈 목표값 — 행의 바닥, 단 안전 바닥 위로 잘린다.

    목표를 「행의 바닥」으로 잡는 것은 숫자를 안 지어내기 위해서다. 정본은 §8 에
    **얼마나** 빼라는 수를 안 줬고, 그 구간에 대해 정본이 실제로 적은 가장 어두운 값은
    §6 표 그 행의 아래끝이다.
    """
    return max(intent.brightness[0], DARKNESS_FLOOR)


def select_sequence_number(sequences_section: Mapping[str, object]) -> int:
    unavailable = sequences_section.get("reason")
    if isinstance(unavailable, str) or sequences_section.get("ok") is False:
        raise SequenceNumberError(SEQUENCE_UNAVAILABLE)
    if sequences_section.get("truncated"):
        raise SequenceNumberError(SEQUENCE_TRUNCATED)
    occupied = _sequence_numbers(sequences_section)
    candidate = 1
    while candidate in occupied:
        candidate += 1
    return candidate


def build_songcue_timing(
    bundle: SongCueBundle,
    *,
    timecode_number: int,
    axes: SongCueTimingAxes | None = None,
) -> SongCueTimingPlan:
    if isinstance(timecode_number, bool) or timecode_number < 1:
        raise ValueError(f"timecode_number must be positive: {timecode_number!r}")
    selected_axes = axes or SongCueTimingAxes()
    timecode_commands: tuple[str, ...] = ()
    auto_advance_commands: tuple[str, ...] = ()
    skipped: list[SongCueTimingSkip] = []
    if selected_axes.timecode_go:
        timecode_commands = _timecode_commands(bundle, timecode_number)
    else:
        skipped.append(
            SongCueTimingSkip(axis=TIMECODE_DESCOPE, reason=selected_axes.timecode_skip_reason)
        )
    if selected_axes.auto_advance_go:
        auto_advance_commands = _auto_advance_commands(bundle)
    else:
        skipped.append(
            SongCueTimingSkip(
                axis=AUTO_ADVANCE_DESCOPE, reason=selected_axes.auto_advance_skip_reason
            )
        )
    return SongCueTimingPlan(
        commands=timecode_commands + auto_advance_commands,
        timecode_commands=timecode_commands,
        auto_advance_commands=auto_advance_commands,
        skipped_axes=tuple(skipped),
    )


def _parse_section(raw: Mapping[str, object] | Sequence[object], index: int) -> SongCueSection:
    section = _raw_section(raw)
    name = section.name.strip()
    if not name:
        raise ValueError(f"section index {index} has an empty name")
    dynamics = _section_dynamics(name)
    label, variant = _label_and_variant(name)
    return SongCueSection(
        name=name,
        start_ms=normalise_start_ms(section.start),
        index=index,
        dynamics=dynamics,
        requires_explicit_dynamics=dynamics is None,
        label=label,
        variant=variant,
    )


def _label_and_variant(name: str) -> tuple[str, str]:
    """이름을 라벨과 변형 표시로 가른다(정본 §3).

    변형은 라벨을 **바꾸지 않는다** — 마지막 후렴이 편곡이 달라도 후렴이므로, 프라임이
    붙은 이름은 같은 라벨의 다음 회차로 센다. 프라임만 남는 이름은 라벨이 없으므로
    변형으로 읽지 않는다.
    """
    stripped = name.rstrip(VARIANT_PRIME).strip()
    if stripped and stripped != name:
        return stripped, VARIANT_PRIME
    return name, ""


def _numbered_by_label(sections: Sequence[SongCueSection]) -> tuple[SongCueSection, ...]:
    """라벨마다 등장 순번을 붙인다 — 표준 데이터셋이 주지 않는 필드(정본 §3).

    저장소의 회차 카운터는 이 함수 **하나**다. 큐 이름의 중복 해소(:func:`_cue_names`)도
    같은 값을 읽는다 — 두 벌을 두면 이름이 가리키는 회차와 사다리가 오르는 회차가 갈리고,
    갈린 순간 감독이 화면에서 읽는 「후렴 2」와 콘솔에 실제로 나간 세기가 다른 것이 된다.
    """
    seen: dict[str, int] = dict()
    numbered: list[SongCueSection] = []
    for section in sections:
        seen[section.label] = seen.get(section.label, 0) + 1
        numbered.append(replace(section, instance=seen[section.label]))
    return tuple(numbered)


def _timecode_commands(bundle: SongCueBundle, timecode_number: int) -> tuple[str, ...]:
    timecode_name = _ascii_label(
        f"{bundle.sequence_name} Timecode", fallback=f"Timecode {timecode_number}"
    )
    return (
        f"Store Timecode {timecode_number}",
        f"Set Timecode {timecode_number} Property 'Name' '{timecode_name}'",
        f"Assign Sequence {bundle.sequence_number} At Timecode {timecode_number}",
    )


def _auto_advance_commands(bundle: SongCueBundle) -> tuple[str, ...]:
    commands: list[str] = []
    for section in bundle.stored_sections:
        commands.append(
            f"Set Cue {section.cue_number} Sequence {bundle.sequence_number} "
            f"Property 'TrigType' '{TRIGGER_TYPE_TIME}'"
        )
        commands.append(
            f"Set Cue {section.cue_number} Sequence {bundle.sequence_number} "
            f"Property 'TrigTime' {_format_seconds(section.section.start_ms)}"
        )
    return tuple(commands)


def _format_seconds(start_ms: int) -> str:
    seconds = Decimal(start_ms) / _MILLISECONDS_PER_SECOND
    if seconds == seconds.to_integral_value():
        return str(int(seconds))
    return format(seconds.normalize(), "f")


def _sequence_numbers(sequences_section: Mapping[str, object]) -> set[int]:
    listed = sequences_section.get("objects")
    if not isinstance(listed, list):
        listed = sequences_section.get("children")
    if not isinstance(listed, list):
        raise SequenceNumberError(SEQUENCE_UNAVAILABLE)
    occupied: set[int] = set()
    for entry in listed:
        if not isinstance(entry, Mapping):
            raise SequenceNumberError(SEQUENCE_NUMBER_UNAVAILABLE)
        number = entry.get("no", entry.get("i"))
        if not isinstance(number, int):
            raise SequenceNumberError(SEQUENCE_NUMBER_UNAVAILABLE)
        occupied.add(number)
    return occupied


def _ascii_label(value: str, *, fallback: str) -> str:
    normalised = unicodedata.normalize("NFKD", value)
    ascii_text = normalised.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^0-9A-Za-z _.-]+", " ", ascii_text.replace("'", " "))
    label = " ".join(cleaned.split())
    return label or fallback


def _raw_section(raw: Mapping[str, object] | Sequence[object]) -> _RawSection:
    if isinstance(raw, Mapping):
        return _RawSection(
            name=str(_first_present(raw, _NAME_KEYS)), start=_first_present(raw, _START_KEYS)
        )
    if isinstance(raw, str):
        raise ValueError("section entries must provide both name and start time")
    if len(raw) != 2:
        raise ValueError("section entries must provide exactly two values")
    name, start = raw
    return _RawSection(name=str(name), start=start)


def _first_present(values: Mapping[str, object], keys: Sequence[str]) -> object:
    for key in keys:
        if key in values:
            return values[key]
    raise ValueError(f"section entry is missing one of {keys!r}")


def _section_dynamics(name: str) -> tuple[int, ...] | None:
    """구간 이름 → 세기 대역. 판정은 ``section_vocab`` 하나가 갖는다 (카드 t362).

    한때 이 자리가 ``matching.resolve_dynamics`` 를 불렀다. 그 함수는 **운영자 질의**의
    판정이라 걸린 말의 대역을 전부 합집합하는데, 구간 라벨에서는 그것이 틀린 답이다 —
    ``Post-Chorus`` 가 ``post-chorus`` ∪ ``chorus`` = (3,4,5) 로 읽혀 후렴 대역의 룩이
    후주에 붙는다(실측: 고치기 전 ``Pre-Chorus`` 와 ``Post-Chorus`` 가 둘 다 (4,5) 였다).
    """
    if not SECTION_TERMS:
        raise RuntimeError("section vocabulary is empty")
    return resolve_section_dynamics(name)


def _decimal_from(value: str, raw: object) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"unsupported section time format: {raw!r}") from exc


def _seconds_to_milliseconds(seconds: Decimal) -> int:
    if seconds < 0:
        raise ValueError(f"section time must be non-negative: {seconds}")
    milliseconds = seconds * _MILLISECONDS_PER_SECOND
    if milliseconds != milliseconds.to_integral_value():
        raise ValueError(f"section time must resolve to a whole millisecond: {seconds}")
    return int(milliseconds)
