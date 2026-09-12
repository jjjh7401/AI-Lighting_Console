from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from typing import NamedTuple

from server.design.cue_density import plan_cue_density, rotate_palette
from server.fx.instantiate import is_programmer_state
from server.looks.busking import VALUE_LINE_COLLISION, looks_for_genre
from server.looks.instantiate import _values_line
from server.looks.movement import (
    BAND_ORDER,
    MOVEMENT_STILL,
    MovementError,
    MovementPlan,
    band_for_dynamics,
    plan_movement,
)
from server.looks.resolver import GroupCandidate, RoleResolution, UnmappedRole, resolve_roles
from server.looks.schema import DYNAMICS_MAX, DYNAMICS_MIN, AttributeValue, Look, LookLibrary
from server.looks.section_intent import SectionIntent, intent_for_label, sorted_candidates
from server.looks.section_vocab import SECTION_TERMS, resolve_section_dynamics

_MILLISECONDS_PER_SECOND = Decimal("1000")
_SECONDS_PER_MINUTE = Decimal("60")
_MILLISECONDS_PER_MINUTE = 60_000
_MMSS_PATTERN = re.compile(r"^(?P<minutes>\d+):(?P<seconds>\d{2})(?P<fraction>\.\d{1,3})?$")
_SECONDS_PATTERN = re.compile(r"^\d+(?:\.\d+)?$")
_NAME_KEYS = ("name", "section", "label")
_START_KEYS = ("start", "start_time", "time")
EXPLICIT_DYNAMICS_REQUIRED = "explicit_dynamics_required"
UNMAPPED_LOOK = "unmapped_look"
SEQUENCE_UNAVAILABLE = "sequence_unavailable"
SEQUENCE_TRUNCATED = "sequence_truncated"
SEQUENCE_NUMBER_UNAVAILABLE = "sequence_number_unavailable"
EMPTY_SECTIONS = "empty_sections"
ROLE_UNMAPPED = "role_unmapped"
#: 이 구간이 앞 곡들이 이미 쓴 룩을 **다시** 골랐다는 표시 — 그 세기에 남은 룩이
#: 하나도 없었다는 뜻이다(정본 §7: 곡 사이 재사용은 결함). 큐는 그래도 나간다:
#: 재사용으로 내려앉는 것은 받아들이되, **조용히** 내려앉지는 않는다.
LOOK_POOL_EXHAUSTED = "look_pool_exhausted"
#: 이 큐가 선언된 움직임을 못 낸 이유. 셋 다 「조용히 버렸다」의 반대말이다 — 버리는
#: 것이 카드 t357 이 없애려는 결함이므로, 못 낸 것은 이름과 함께 밖으로 나간다.
MOVEMENT_BAND_STILL = "movement_band_still"
MOVEMENT_TURN_BOUNDARY = "movement_turn_boundary"
MOVEMENT_LINE_COLLISION = "movement_line_collision"
_DESTINATION = "ChangeDestination Root"
_CLEAR = "ClearAll"
_IMPLICIT_SYSTEM_CUE_COUNT = 2
TIMECODE_DESCOPE = "timecode_descope"
AUTO_ADVANCE_DESCOPE = "auto_advance_descope"
TRIGGER_TYPE_TIME = "Time"

#: 변형 표시로 고정한 표기 하나 — SALAMI 프라임(U+2032). 정본 §3 이 표기 셋(프라임 ·
#: RWC 의 A·B · Harmonix 숫자 접미사) 중 하나를 골라 고정하라고 지시한다. ASCII
#: 어포스트로피는 일부러 제외한다: MA3 명령줄의 인용 문자라서 라벨 어휘로 쓰면 큐 이름
#: 조립과 충돌한다.
VARIANT_PRIME = "′"

#: 아껴두기 사다리의 칸 이름, 회차마다 하나씩만 더하는 순서 그대로(정본 §7.1).
#: 여기 있는 셋은 **오늘의 어휘로 실제 발화되는** 것뿐이다 — 정본 표의 마지막 두 칸
#: (무빙 포지션 전환 · 블라인더/백색 플래시)과 앙코르의 스트로브는 이 카드에서 못 만든다:
#: `Pan`/`Tilt` 는 `MovementSpec` 안에서만 합법이고 v1 번들은 movement 를 발화하지 않으며
#: (카드 t357), 블라인더·스트로브는 역할 어휘에 이름이 없다(카드 t356, 감독 결정 선행).
#: 색 스냅도 뺀다 — 정본 §7 이 「코러스 1의 색은 되돌아와야 한다」고 못박으므로 지배색을
#: 갈아치우는 것은 상승이 아니라 위반이다.
LADDER_DIMMER_HIT = "dimmer_hit"
LADDER_ZOOM_PINCH = "zoom_pinch"
LADDER_IRIS_PINCH = "iris_pinch"
LADDER_RUNGS: tuple[str, ...] = (LADDER_DIMMER_HIT, LADDER_ZOOM_PINCH, LADDER_IRIS_PINCH)

_DIMMER = "Dimmer"
_ZOOM = "Zoom"
_IRIS = "Iris"
#: 한 칸이 움직이는 폭과 그 방향의 한계. 밝기는 천장을 향해 오르고(정본 §6: 코러스·드롭은
#: 80~100%), 줌·아이리스는 좁아지는 쪽으로 내려간다(§6 「점점 좁힘」).
_HIT_STEP = 5
_PINCH_STEP = -5
_DIMMER_CEILING = 100
_BEAM_FLOOR = 1
#: **찍는 액센트** — 정본 §6.1 의 일곱 중 오늘의 어휘가 실제로 발화하는 둘. 한 큐에
#: **하나**만 실린다(감독 결정 2026-09-12: 밝기만 누적하고 나머지는 큐당 하나). 회차가
#: 깊어지면 쌓지 않고 **갈아탄다** — 그래서 여기는 순서 있는 목록이고, 깊이가 그 안을 돈다.
_MARKING_ACCENTS: tuple[str, ...] = (LADDER_ZOOM_PINCH, LADDER_IRIS_PINCH)
#: 오를 수 있는 깊이의 상한 — 밝기의 머리 공간(천장까지의 걸음 수)에 액센트 갈아타기를
#: 더한 것. 정본 §6 의 「마지막 드롭은 전 리그 최대」와 같은 방향이고, 천장에서는 값이 더
#: 안 움직이므로 유한하다: 그 지점에서 비로소 큐를 못 세운다(마지막 수단의 건너뜀).
_MAX_CLIMB = _DIMMER_CEILING // _HIT_STEP + len(_MARKING_ACCENTS)


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

    reuse_reason: str | None = None
    """앞 곡의 룩으로 내려앉았으면 :data:`LOOK_POOL_EXHAUSTED`, 아니면 ``None`` (카드 t358).

    ``reason`` 과 갈라 두는 이유는 둘이 반대말이기 때문이다 — ``reason`` 은 **룩이 없다**,
    이 필드는 **룩은 있는데 새것이 아니다**. 합치면 큐가 나가는 갈래와 안 나가는 갈래가
    한 문자열에 섞이고, 보고에서 둘을 다시 가를 방법이 없어진다.
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
class SongCueBundle:
    song_title: str
    sequence_number: int
    sequence_name: str
    commands: tuple[str, ...]
    sections: tuple[SongCueSectionBundle, ...]
    is_error: bool = False
    reason: str | None = None
    withheld_movement: tuple[SongCueWithheldMovement, ...] = ()

    @property
    def movement_sections(self) -> tuple[SongCueSectionBundle, ...]:
        return tuple(section for section in self.sections if section.movement is not None)

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


class SongCueBundleError(ValueError):
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


def map_sections_to_looks(
    sections: Iterable[SongCueSection],
    library: LookLibrary,
    genre: str,
    explicit_dynamics: Mapping[int, int] | None = None,
    *,
    used_look_ids: Iterable[str] = (),
) -> tuple[SongCueLookSelection, ...]:
    """구간마다 룩 하나. ``used_look_ids`` 는 **앞 곡들이 이미 쓴** 룩 id (카드 t358).

    정본 §7 후반 — 곡 사이에서 룩·고보·이펙트를 재사용하지 않는다. 그 기억은 이 함수가
    들지 않고(세션이 든다: :class:`server.looks.song_history.SongLookMemory`) **인자로
    들어온다**. 여기서 들면 한 곡을 만드는 동안 기억이 자라 후렴 2회차가 1회차를 피하게
    되고, 그것은 정본이 미덕이라 부른 축을 깨는 것이다.

    기본값이 빈 것이므로 기억 없이 부른 호출은 고치기 전과 **바이트 동일**하다 —
    피할 것이 없으면 아래 재배열이 항등이다.
    """
    ordered_looks = looks_for_genre(library, genre)
    # frozenset — 구간마다 다시 훑지 않고, 곡 하나를 만드는 동안 **안 움직인다**.
    already_used = frozenset(used_look_ids)
    # 순차로 도는 것이 카드 t360 이다. 「앞 큐와 가장 대비되는 룩」은 앞 구간이 무엇을
    # 골랐는지 알아야 정해지므로, 구간을 서로 **독립으로** 볼 수 없다. 앞 큐는 **룩을
    # 고른** 마지막 구간이다 — 룩이 안 붙은 구간(세기 미해석·미매핑)은 무대에 그림을
    # 안 냈으므로 다음 구간이 대비할 대상이 아니다.
    selections: list[SongCueLookSelection] = []
    previous: Look | None = None
    # 라벨마다 **1회차가 고른 룩**. 정본 §7 [HARD]: 코러스 1의 색은 이후 코러스에서
    # 되돌아와야 한다. 회차 사이의 변화는 룩 교체가 아니라 사다리가 만든다(§7.1).
    first_of_label: dict[str, Look] = dict()
    for section in sections:
        selection = _map_section_to_look(
            section=section,
            ordered_looks=ordered_looks,
            explicit_dynamics=_explicit_dynamics_for(section, explicit_dynamics),
            already_used=already_used,
            previous=previous,
            returning=first_of_label.get(section.label),
        )
        selections.append(selection)
        if selection.look is not None:
            previous = selection.look
            first_of_label.setdefault(section.label, selection.look)
    return tuple(selections)


#: 업로드 경로에서 쪼갠 큐를 서로 다르게 만드는 것의 이름 — 팔레트의 색이 아니라
#: **같은 다이내믹스 안에서 쓸 수 있는 룩**이다. 사유 문면에만 쓰인다.
SONGCUE_VARIANT_LABEL = "쓸 수 있는 룩"


def split_selections_for_density(
    selections: Sequence[SongCueLookSelection],
    *,
    bpm: float | None,
    meter: object = "4/4",
    song_end_ms: int | None = None,
) -> tuple[tuple[SongCueLookSelection, ...], tuple[str, ...]]:
    """구간 선택 목록을 마디 경계에서 쪼갠 **큐** 선택 목록으로 넓힌다 (카드 t306).

    감독 인터뷰 경로(``_build_unified_song_plan``)가 이미 하는 것과 **같은 규칙**
    이다 — 마디 산술은 :func:`server.design.cue_density.plan_cue_density` 하나가
    갖고, 이어지는 큐의 회전은 :func:`~server.design.cue_density.rotate_palette`
    하나가 갖는다. 규칙을 두 벌 두면 갈라지고, 갈라진 순간 감독이 보는 두 경로가
    다시 서로 다른 설계를 낸다.

    두 경로의 **차이**는 「무엇을 돌리느냐」 하나다. 인터뷰 경로는 팔레트의 색을
    돌리고, 이 경로는 같은 다이내믹스에 맞는 룩 목록(``dynamics_matches``)을
    돌린다. 강도를 유지하고 그림만 바꾸는 정본의 축(Q060 "강도 유지, 색만 교체")
    은 그대로다 — 다이내믹스가 같으면 D 레벨이 같기 때문이다.

    회전은 ``look`` 뿐 아니라 ``dynamics_matches`` **순서**까지 돌린다. 저장 직전
    :func:`_select_bindable` 이 이 목록의 앞에서부터 「리그에 묶이는 첫 룩」을
    고르므로, 순서를 돌려야 이어지는 큐가 앞 큐와 다른 자리에서 탐색을 시작한다.

    쓸 수 있는 룩이 하나뿐인 구간은 돌려도 같은 룩이라 **쪼개지 않는다**
    — 그 사유는 돌려주는 ``notes`` 로 밖에 나간다. BPM 이 없으면 한 건도 쪼개지
    않으며 입력이 그대로 나온다(콘솔에 가는 명령은 바이트 동일).

    :param song_end_ms: 곡 끝. 주면 **마지막 구간도** 쪼갠다. 인터뷰 경로는 이
        값을 가진 적이 없어 마지막 구간을 늘 통째로 두지만, 확정 분석 기록은
        구간마다 ``end_ms`` 를 들고 있어 이 경로에서는 알 수 있다.
    """
    ordered = tuple(selections)
    if not ordered:
        return (), ()
    plan = plan_cue_density(
        [selection.section.start_ms for selection in ordered],
        bpm=bpm,
        meter=meter,
        palette_sizes=[len(selection.dynamics_matches) for selection in ordered],
        song_end_ms=song_end_ms,
        variant_label=SONGCUE_VARIANT_LABEL,
    )
    expanded: list[SongCueLookSelection] = []
    for split in plan.splits:
        source = ordered[split.source_index]
        section = replace(source.section, start_ms=split.start_ms)
        rotated = rotate_palette(source.dynamics_matches, split.unit_index)
        look = rotated[0] if rotated else source.look
        expanded.append(replace(source, section=section, look=look, dynamics_matches=rotated))
    return tuple(expanded), plan.notes


# @MX:ANCHOR: [AUTO] 곡→큐 번들의 유일한 조립 지점. 두 번 도는 것이 설계다 —
#   1회차로 「어느 큐가 실제로 저장되는가」를 알아내고, 그 답으로 움직임을 실을 큐 하나를
#   고른 뒤 2회차에서 최종 번들을 만든다.
# @MX:REASON: 움직임을 실을 큐는 **저장되는** 큐여야 한다(룩 미해석·역할 미매칭·값 충돌로
#   건너뛴 구간에 페이저를 실으면 아무 데도 안 간다). 그런데 그 세 갈래는 조립 도중에야
#   갈린다. 1회차는 순수하고(`emitted` 를 새로 만든다) 움직임 줄은 값 라인 판정에 참여하지
#   않으므로, 2회차의 저장/건너뜀 결정은 1회차와 같다 — 그 동일성은
#   `test_songcue_movement` 가 실측한다.
def build_songcue_bundle(
    song_title: str,
    selections: Iterable[SongCueLookSelection],
    *,
    sequences_section: Mapping[str, object],
    groups_section: Mapping[str, object],
    role_aliases: Mapping[str, str] | None = None,
) -> SongCueBundle:
    ordered = tuple(selections)
    if not ordered:
        raise SongCueBundleError(EMPTY_SECTIONS)

    sequence_number = select_sequence_number(sequences_section)
    sequence_name = _ascii_label(song_title, fallback=f"Song {sequence_number}")
    # ``role_aliases``: 쇼 단위 그룹명 → 역할 표 (t356). 없으면 힌트 매칭만 돈다.
    resolution = resolve_roles(groups_section, aliases=role_aliases)
    cue_names = _cue_names(tuple(selection.section for selection in ordered))

    dry = _assembled(
        song_title,
        ordered,
        cue_names,
        sequence_number=sequence_number,
        sequence_name=sequence_name,
        resolution=resolution,
        movements=dict(),
    )
    movements, withheld = _movement_carrier(dry)
    bundle = (
        dry
        if not movements
        else _assembled(
            song_title,
            ordered,
            cue_names,
            sequence_number=sequence_number,
            sequence_name=sequence_name,
            resolution=resolution,
            movements=movements,
        )
    )
    bundle = replace(bundle, withheld_movement=withheld)
    _guard_bundle_collision(bundle)
    return bundle


def _assembled(
    song_title: str,
    ordered: Sequence[SongCueLookSelection],
    cue_names: Sequence[str],
    *,
    sequence_number: int,
    sequence_name: str,
    resolution: RoleResolution,
    movements: Mapping[int, MovementPlan],
) -> SongCueBundle:
    commands: list[str] = [_DESTINATION]
    section_bundles: list[SongCueSectionBundle] = []
    emitted: dict[str, tuple[int, int, str]] = dict()
    sequence_labelled = False
    for cue_number, (selection, cue_name) in enumerate(
        zip(ordered, cue_names, strict=True), start=1
    ):
        section_bundle = _section_bundle(
            selection=selection,
            cue_number=cue_number,
            cue_name=cue_name,
            sequence_number=sequence_number,
            resolution=resolution,
            emitted=emitted,
            movement=movements.get(cue_number),
        )
        if section_bundle.commands:
            commands.extend(section_bundle.commands)
            if not sequence_labelled:
                store_index = _first_store_index(commands, sequence_number, cue_number)
                commands.insert(
                    store_index + 1, f"Label Sequence {sequence_number} '{sequence_name}'"
                )
                section_bundle = replace(
                    section_bundle, commands=tuple(commands[-len(section_bundle.commands) - 1 :])
                )
                sequence_labelled = True
        section_bundles.append(section_bundle)

    stored_commands = tuple(commands) if len(commands) > 1 else ()
    return SongCueBundle(
        song_title=song_title,
        sequence_number=sequence_number,
        sequence_name=sequence_name,
        commands=stored_commands,
        sections=tuple(section_bundles),
    )


# @MX:ANCHOR: [AUTO] 한 번들이 페이저를 **하나만** 낸다는 규칙이 여기서 집행된다.
# @MX:REASON: `run_commands` 의 중복 제거는 명령 지시 하나 전체를 범위로 하고, 면제 집합은
#   `Clear`·`ClearAll`·`Fixture <n>`·`Group <n>` 뿐이다(`server/fx/instantiate.py` 의
#   `_PROGRAMMER_STATE_COMMANDS`). 페이저를 만드는 데 반드시 필요한 `Step 2` 는 내용이 없는
#   줄이라 큐마다 다르게 만들 방법이 **없다** — 두 번째 큐의 `Step 2` 는 접히고, 그 큐는
#   스텝 하나만 가진 「페이저 아닌 것」을 저장한다. 저장된 페이저 큐는 빈 큐와 구별되지
#   않으므로 그 실패는 무대에서만 보인다. 그래서 대역이 가장 센 큐 하나가 페이저를 갖고,
#   나머지는 :data:`MOVEMENT_TURN_BOUNDARY` 로 보고된다. 이 경계를 넓히려면 명령 지시를
#   큐마다 쪼개거나(`server/orchestrator/tools.py` 의 `create_arrangement_groups` 가 쓰는
#   신선한 `ExecutionContext` 패턴) 면제 집합에 `Step <k>` 를 넣어야 하고, 둘 다 fx SPEC
#   쪽 결정이므로 이 카드에서 하지 않는다.
def _movement_carrier(
    bundle: SongCueBundle,
) -> tuple[dict[int, MovementPlan], tuple[SongCueWithheldMovement, ...]]:
    """움직임을 실을 큐 **하나**와, 못 실은 큐들의 사유.

    고르는 기준은 대역이다 — 가장 센 대역, 같으면 이른 큐. 정본 §6.4 가 「빠름 = 드롭
    전용」이라 했고 §12 항목 1의 목적이 「드롭을 드롭으로 만드는 것」이므로, 하나만 실을 수
    있다면 그 하나는 드롭이다.
    """
    candidates: list[tuple[int, int, MovementPlan]] = []
    withheld: list[SongCueWithheldMovement] = []
    for section in bundle.stored_sections:
        look = section.selection.look
        if look is None or not look.movement:
            continue
        band = band_for_dynamics(look.dynamics)
        if band == MOVEMENT_STILL:
            withheld.append(
                SongCueWithheldMovement(
                    section=section.section,
                    cue_number=section.cue_number,
                    band=band,
                    reason=MOVEMENT_BAND_STILL,
                    detail=f"look {look.look_id} sits at dynamics {look.dynamics}",
                )
            )
            continue
        try:
            plan = plan_movement(look, band=band)
        except MovementError as error:
            withheld.append(
                SongCueWithheldMovement(
                    section=section.section,
                    cue_number=section.cue_number,
                    band=band,
                    reason=error.reason,
                    detail=str(error),
                )
            )
            continue
        if plan is not None:
            candidates.append((BAND_ORDER.index(band), section.cue_number, plan))

    if not candidates:
        return dict(), tuple(withheld)
    carrier = max(candidates, key=lambda entry: (entry[0], -entry[1]))
    movements: dict[int, MovementPlan] = dict()
    movements[carrier[1]] = carrier[2]
    for _rank, cue_number, plan in candidates:
        if cue_number == carrier[1]:
            continue
        section = next(s for s in bundle.sections if s.cue_number == cue_number)
        withheld.append(
            SongCueWithheldMovement(
                section=section.section,
                cue_number=cue_number,
                band=plan.band,
                reason=MOVEMENT_TURN_BOUNDARY,
                detail=(
                    f"cue {carrier[1]} carries this bundle's one phaser (band "
                    f"{carrier[2].band}); a second `Step 2` line in the same instruction "
                    "turn is folded by the run_commands dedupe and the cue would store a "
                    "one-step non-phaser"
                ),
            )
        )
    return movements, tuple(withheld)


def _guard_bundle_collision(bundle: SongCueBundle) -> None:
    """면제 대상이 아닌 줄이 번들 안에서 두 번 나오면 거절한다.

    이 그물이 잡는 것은 위 :func:`_movement_carrier` 의 규칙이 깨진 경우다. 움직임이 없는
    번들에서는 값 라인이 `emitted` 로, Store 라인이 큐 번호로 이미 유일하므로 이 함수는
    아무것도 바꾸지 않는다 — 무회귀 성질.
    """
    seen: set[str] = set()
    for command in bundle.commands:
        if is_programmer_state(command):
            continue
        if command in seen:
            raise SongCueBundleError(
                f"{MOVEMENT_LINE_COLLISION}: {command!r} appears twice in one bundle; the "
                "run_commands dedupe drops the second occurrence and the affected Store "
                "runs against an incomplete programmer — silently, because a stored "
                "phaser cue is indistinguishable from an empty one"
            )
        seen.add(command)


def render_songcue_report(bundle: SongCueBundle) -> str:
    parts = [bundle.song_title, bundle.sequence_name]
    parts.extend(section.section.name for section in bundle.sections)
    parts.extend(skipped.detail for skipped in bundle.skipped)
    return "\n".join(part for part in parts if part)


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


def observed_user_cue_count(sequence_payload: Mapping[str, object]) -> int:
    if sequence_payload.get("truncated"):
        raise SequenceNumberError(SEQUENCE_TRUNCATED)
    node = sequence_payload.get("node")
    child_count = node.get("childCount") if isinstance(node, Mapping) else None
    if not isinstance(child_count, int):
        raise SequenceNumberError(SEQUENCE_UNAVAILABLE)
    return max(0, child_count - _IMPLICIT_SYSTEM_CUE_COUNT)


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


def plan_prepare_songcue_timing(
    bundle: SongCueBundle,
    request: Mapping[str, object],
    *,
    axes: SongCueTimingAxes | None = None,
) -> SongCueTimingPlan:
    return build_songcue_timing(
        bundle,
        timecode_number=_prepare_songcue_timecode_number(request),
        axes=axes,
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


def _map_section_to_look(
    *,
    section: SongCueSection,
    ordered_looks: Sequence[Look],
    explicit_dynamics: int | None,
    already_used: frozenset[str] = frozenset(),
    previous: Look | None = None,
    returning: Look | None = None,
) -> SongCueLookSelection:
    if explicit_dynamics is not None:
        requested_dynamics = (_validated_dynamics(explicit_dynamics, section.index),)
    elif section.dynamics is None:
        return SongCueLookSelection(
            section=section, requested_dynamics=(), reason=EXPLICIT_DYNAMICS_REQUIRED
        )
    else:
        requested_dynamics = section.dynamics

    matches = tuple(look for look in ordered_looks if look.dynamics in requested_dynamics)
    if not matches:
        return SongCueLookSelection(
            section=section, requested_dynamics=requested_dynamics, reason=UNMAPPED_LOOK
        )
    ranked, reuse_reason = _ranked_against_history(
        matches,
        already_used,
        previous=previous,
        intent=intent_for_label(section.label),
        returning=returning,
    )
    return SongCueLookSelection(
        section=section,
        requested_dynamics=requested_dynamics,
        look=ranked[0],
        dynamics_matches=ranked,
        reuse_reason=reuse_reason,
    )


def _ranked_against_history(
    matches: Sequence[Look],
    already_used: frozenset[str],
    *,
    previous: Look | None = None,
    intent: SectionIntent | None = None,
    returning: Look | None = None,
) -> tuple[tuple[Look, ...], str | None]:
    """후보를 줄 세운다 — 곡 사이 신선도(t358) 바깥, 구간 의도와 대비(t360) 안.

    **두 카드가 겹쳐 사는 자리이므로 순서에 계약이 있다.**

    1. 앞 곡이 안 쓴 룩이 앞, 쓴 룩이 뒤(카드 t358, 정본 §7 후반: 곡 사이 재사용은 결함).
       이것이 **가장 바깥**이다 — 곡 안에서 아무리 대비가 커도 앞 곡을 되쓰는 것보다
       먼저 오지 않는다.
    2. 각 묶음 **안에서** 정본 §6 의 구간 의도 → 앞 큐와의 대비 → 기존 전순서
       (``section_intent.ordering_key``). 카드 t360 이 여기를 채웠다.

    쓴 룩을 목록에서 **빼지 않는** 것은 t358 이 정한 형상 그대로다. 뒤에 남겨 두면 두
    성질이 함께 산다: 새 룩이 있으면 그것이 선두라 곡 B 가 곡 A 의 룩으로 열리지 않고,
    새 룩이 리그에 하나도 안 묶이면 :func:`_select_bindable` 이 뒤쪽의 쓴 룩을 찾아내
    큐가 사라지지 않는다. 빼 버리면 두 번째 성질이 「큐 없음」으로 바뀌는데, 재사용보다
    나쁘다.

    **고치기 전과 바이트 동일한 갈래**가 남아 있다: §6 행이 없는 라벨 + 앞 큐 없음이면
    ``ordering_key`` 가 ``(dynamics, look_id)`` 로 퇴화하고, 그 순서는
    ``busking.looks_for_genre`` 가 준 것과 같다.

    한계 하나를 적어 둔다: 밀도 경로(:func:`split_selections_for_density`)는 이 목록을
    **회전**시키므로, 한 구간이 여러 큐로 쪼개지면 여기서 정한 선두가 그대로 나가지
    않는다. 저장 직전 :func:`_select_bindable` 이 목록 앞에서부터 리그에 묶이는 첫 룩을
    다시 고르는 것도 같은 성질이다. 그 갈래는 여기서 막지 않고 **저장된 결과를 재서**
    보고한다(``prepare_songcue`` 의 ``cross_song_looks.reused_look_ids``) — 의도가 아니라
    실제로 나간 것을 재는 쪽이 참이다.
    """
    fresh = tuple(look for look in matches if look.look_id not in already_used)
    if not fresh:
        ranked = sorted_candidates(matches, previous=previous, intent=intent, returning=returning)
        return ranked, LOOK_POOL_EXHAUSTED
    stale = tuple(look for look in matches if look.look_id in already_used)
    ranked = sorted_candidates(
        fresh, previous=previous, intent=intent, returning=returning
    ) + sorted_candidates(stale, previous=previous, intent=intent, returning=returning)
    return ranked, None


# @MX:NOTE: [AUTO] 이 리그에서 룩이 「묶인다」는 것의 **유일한 정의**. 선택
#   (`_select_bindable`)과 저장(`_section_bundle`)이 같은 술어를 봐야 한다 —
#   둘이 갈리면 선택기가 고른 룩을 번들이 건너뛰고, 그 상태는 고치기 전보다 나쁘다.
#   역할 **하나만** 묶여도 참이라는 것이 이 규칙의 핵심이고, ballad 가 cyc 없는
#   리그에서도 멀쩡했던 이유다(첫 D1 룩이 배경+백라이트를 함께 갖고 있었다).
def _bound_groups(look: Look, resolution: RoleResolution) -> dict[str, tuple[GroupCandidate, ...]]:
    """이 룩의 역할 중 이 리그의 그룹에 묶인 것들.

    ``dict()`` 는 취향이 아니다 — 이 모듈은 매핑 리터럴을 **한 개도** 두지 않는
    규율이 있고(``test_songcue_sections`` 가 AST 로 잰다), 그래야 다이내믹스
    어휘가 ``matching`` 바깥에서 다시 정의될 자리가 생기지 않는다.
    """
    bound: dict[str, tuple[GroupCandidate, ...]] = dict()
    for role in look.roles:
        candidates = resolution.groups_for(role)
        if candidates:
            bound[role] = candidates
    return bound


def _select_bindable(look: Look, matches: Sequence[Look], resolution: RoleResolution) -> Look:
    """요청한 다이내믹스 안에서 이 리그에 실제로 묶이는 **첫** 룩.

    하나도 안 묶이면 ``look`` — 오늘의 선택 — 을 그대로 돌려준다. 그래야 큐를 못
    세우는 구간의 ``role_unmapped`` 보고가 지금과 같은 룩·같은 사유로 남는다.

    cyc 를 갖춘 리그에서는 첫 룩이 이미 묶이므로 이 함수가 그 룩을 돌려주고,
    저장되는 것은 고치기 전과 같다(무회귀 성질 —
    ``test_songcue_rig_aware_look.TestCycRigIsUnchanged`` 가 실측한다).
    """
    for candidate in matches:
        if _bound_groups(candidate, resolution):
            return candidate
    return look


def _section_bundle(
    *,
    selection: SongCueLookSelection,
    cue_number: int,
    cue_name: str,
    sequence_number: int,
    resolution: RoleResolution,
    emitted: dict[str, tuple[int, int, str]],
    movement: MovementPlan | None = None,
) -> SongCueSectionBundle:
    if selection.look is None:
        skipped = SongCueSkippedSection(
            section=selection.section,
            cue_number=cue_number,
            reason=selection.reason or UNMAPPED_LOOK,
            detail=selection.reason or UNMAPPED_LOOK,
        )
        return SongCueSectionBundle(
            section=selection.section,
            cue_number=cue_number,
            cue_name=cue_name,
            selection=selection,
            skipped=(skipped,),
        )

    look = _select_bindable(selection.look, selection.dynamics_matches, resolution)
    if look is not selection.look:
        # 보고에 실리는 선택과 번들이 실제로 세운 룩이 어긋나지 않게 한다.
        selection = replace(selection, look=look)
    bound = _bound_groups(look, resolution)
    unmapped: list[UnmappedRole] = []
    for role in look.roles:
        if role in bound:
            continue
        entry = resolution.unmapped_for(role)
        if entry is not None:
            unmapped.append(entry)
    groups = _selected_groups(bound)
    if not groups:
        skipped = SongCueSkippedSection(
            section=selection.section,
            cue_number=cue_number,
            reason=ROLE_UNMAPPED,
            detail="; ".join(entry.reason for entry in unmapped),
        )
        return SongCueSectionBundle(
            section=selection.section,
            cue_number=cue_number,
            cue_name=cue_name,
            selection=selection,
            skipped=(skipped,),
            unmapped=tuple(unmapped),
            bound=bound,
        )

    values, rungs = _distinct_values_line(look, selection.section, emitted)
    if values is None:
        previous_section, previous_cue, previous_look = emitted[_values_line(look.attributes)]
        skipped = SongCueSkippedSection(
            section=selection.section,
            cue_number=cue_number,
            reason=VALUE_LINE_COLLISION,
            detail=(
                f"value line matches section {previous_section} "
                f"cue {previous_cue} look {previous_look}; "
                f"ladder exhausted ({', '.join(LADDER_RUNGS)})"
            ),
            collides_with_section_index=previous_section,
            collides_with_cue_number=previous_cue,
        )
        return SongCueSectionBundle(
            section=selection.section,
            cue_number=cue_number,
            cue_name=cue_name,
            selection=selection,
            skipped=(skipped,),
            bound=bound,
        )
    emitted[values] = (selection.section.index, cue_number, look.look_id)
    # 움직임 줄은 **값 라인 뒤**에 온다: 기준 룩이 먼저 프로그래머에 실리고, 페이저는 그
    # 위에 더하는 액센트다(정본 §6.1 「한 큐에 하나만」과 같은 방향). 이 순서가 이 카드의
    # 유일한 미실측 가정이다 — 정적 Dimmer·색과 2스텝 Pan 을 한 캡처에 섞었을 때 정적
    # 값이 살아 있는지는 콘솔에서 확인해야 알 수 있고, 저장된 페이저 큐는 빈 큐와 구별되지
    # 않으므로 사후 판독으로는 못 가른다(`server/fx/instantiate.py` 머리의 @MX:WARN).
    commands = (
        _CLEAR,
        _selection_line(groups),
        values,
        *(movement.commands if movement is not None else ()),
        f"Store Sequence {sequence_number} Cue {cue_number} '{cue_name}'",
        _CLEAR,
    )
    return SongCueSectionBundle(
        section=selection.section,
        cue_number=cue_number,
        cue_name=cue_name,
        selection=selection,
        commands=commands,
        bound=bound,
        ladder=rungs,
        movement=movement,
    )


# @MX:ANCHOR: [AUTO] 값이 같은 구간을 **버리지 않는다** — 곡 안의 반복은 규범이고,
#   되돌아와야 하는 룩을 지우는 것이 결함이었다(정본 §7 · §12 항목 3).
# @MX:REASON: 고치기 전에는 값 라인이 앞 큐와 같으면 그 구간을 통째로 건너뛰었고, 실측
#   5구간 EDM 입력이 큐 3장이 됐다(후렴이 드롭과 값이 같아 둘이 사라졌다). 되돌리기 쉬운
#   유혹이 둘 있다 — (가) 충돌하면 다시 버리기, (나) 회차와 무관하게 늘 한 칸 올리기.
#   (가)는 이 카드가 없애려는 결함 그대로이고, (나)는 충돌이 없는 입력의 콘솔 명령까지
#   바꿔서 무회귀 성질을 깨뜨린다. 사다리는 **충돌이 방아쇠**이고 **칸은 회차가 정한다**.
def _distinct_values_line(
    look: Look,
    section: SongCueSection,
    emitted: Mapping[str, tuple[int, int, str]],
) -> tuple[str | None, tuple[str, ...]]:
    """앞선 큐와 겹치지 않는 값 라인과 그때 더한 사다리 칸들. 못 만들면 ``(None, ())``.

    기준 룩이 이미 유일하면 그대로 돌려준다 — 충돌이 없는 입력이 내는 명령은 고치기 전과
    **바이트 동일**하다. 겹치면 사다리를 오르는데, 시작 칸은 회차가 정하고(정본 §3: 세기는
    회차가 정한다) 거기서도 겹치면 한 칸씩 더 올린다. 마지막 칸까지 값이 안 달라지면 —
    이미 천장에 있거나 리그가 그 축을 안 갖고 있으면 — 그때만 큐를 못 세운다.

    **한 구간 안에서 쪼갠 큐끼리 겹치는 것은 사다리의 일이 아니다.** 정본 §7 의 상승은
    구간의 **반복 회차** 사이에서 일어난다. 마디 경계로 쪼갠 큐들은 같은 구간의 같은 회차
    이므로, 여기서 밝기를 올리면 구간 하나가 도중에 세어진다 — 밀도 경로의 축(강도는
    유지하고 그림만 교체)을 정면으로 어기는 것이다. 그래서 같은 구간끼리의 충돌은 예전처럼
    건너뛴다.
    """
    base = _values_line(look.attributes)
    previous = emitted.get(base)
    if previous is None:
        return base, ()
    if previous[0] == section.index:
        return None, ()
    for depth in range(_ladder_start(section), _MAX_CLIMB + 1):
        rungs = _climb_rungs(depth)
        candidate = _values_line(escalate_attributes(look.attributes, rungs))
        if candidate not in emitted:
            return candidate, rungs
    return None, ()


def _ladder_start(section: SongCueSection) -> int:
    """회차가 정하는 첫 칸 — 2회차는 한 칸, 3회차는 두 칸(정본 §7.1 표).

    1회차가 겹치는 것은 같은 라벨의 반복이 아니라 **다른 라벨과 값이 같은** 경우다(실측:
    후렴 1이 드롭과 같았다). 그때도 한 칸은 올린다 — 안 올리면 그 큐가 사라지고, 사라지는
    것을 없애는 것이 이 카드다. 낮은 칸으로는 내려가지 않는다: 뒤 회차가 앞 회차보다
    약해지면 상승이 아니다.
    """
    return max(1, section.instance - 1)


# @MX:ANCHOR: [AUTO] 한 큐에 **찍는 액센트는 하나** — 밝기만 누적한다(정본 §6.1 [HARD],
#   감독 결정 2026-09-12).
# @MX:REASON: 고치기 전에는 칸 목록의 앞자락을 그대로 잘라 썼기 때문에(`_LADDER_CLIMB[:n]`)
#   깊이가 3에 닿으면 줌 좁힘과 아이리스 좁힘이 **함께** 나갔다 — 실측(2026-09-12,
#   `051e98b`)에서 후렴 4회차 한 큐가 `Zoom At 13` 과 `Iris At 55` 를 같이 실었고 둘 다
#   실제로 값을 바꿨다. §6.1 은 「셋을 한꺼번에 쓰면 아무것도 안 찍힌다」고 못박는다.
#   되돌리기 쉬운 유혹은 「누적이 §7.1 의 문면이니 앞자락을 자르자」이다. 정본의 두 절이
#   부딪혔고 감독이 갈래를 정했다 — **누적하는 축은 밝기 하나**이고, 찍는 액센트는
#   갈아탄다. 밝기를 액센트와 같은 규율로 묶으면 t355 의 성질(반복 회차가 사라지지 않는다)
#   이 깨진다: 축이 하나도 남지 않는 회차가 생겨 큐가 다시 버려진다.
def _climb_rungs(depth: int) -> tuple[str, ...]:
    """깊이 하나가 내는 칸들 — 밝기 히트 여러 개 + 찍는 액센트 **최대 하나**.

    깊이 1은 밝기뿐이고(2회차), 깊이 2부터 액센트가 하나 붙는다. 더 깊어지면 밝기 히트가
    한 개씩 쌓이는 동안 액센트는 :data:`_MARKING_ACCENTS` 안에서 **갈아탄다** — 누적이
    아니라 교체다. 그래서 어느 깊이에서든 돌려주는 칸 중 찍는 액센트는 최대 하나다.

    밝기가 천장에 닿으면 그 뒤의 밝기 히트는 값을 안 바꾼다(:func:`_stepped` 가 자른다).
    그때는 액센트 교체만 값 라인을 가르고, 그것도 다 떨어지면 큐를 못 세운다.
    """
    if depth <= 1:
        return (LADDER_DIMMER_HIT,)
    hits = (LADDER_DIMMER_HIT,) * (depth - 1)
    return hits + (_MARKING_ACCENTS[(depth - 2) % len(_MARKING_ACCENTS)],)


def escalate_attributes(
    attributes: Sequence[AttributeValue], rungs: Sequence[str]
) -> tuple[AttributeValue, ...]:
    """기준 룩에 사다리 칸을 순서대로 더한 값들(정본 §7.1 아껴두기 사다리).

    받은 칸을 순서대로 다 더한다 — 무엇을 더할지 고르는 것은 여기가 아니라
    :func:`_climb_rungs` 의 일이다. 「한 큐에 찍는 액센트 하나」(§6.1)는 그쪽에서 지켜지고,
    이 함수는 **주어진 대로** 더하므로 손으로 액센트 둘을 넘기면 둘 다 나간다 — 그 성질이
    검사에서 대조군(누적 복원)을 만들 수 있게 한다.

    리그가 그 축을 안 갖거나 이미 한계에 닿은 칸은 **아무것도 바꾸지 않는다** — 없는 축에
    값을 만들어 보내지 않는 것이 이 계층의 규율이다(``Zoom``·``Iris`` 는 M0 프로브가 받은
    어휘이고, 룩이 안 실었으면 이 리그에서 그 칸은 없는 칸이다).
    """
    escalated = tuple(attributes)
    for rung in rungs:
        escalated = _rung_applied(escalated, rung)
    return escalated


def _rung_applied(values: Sequence[AttributeValue], rung: str) -> tuple[AttributeValue, ...]:
    if rung == LADDER_DIMMER_HIT:
        return _stepped(values, _DIMMER, _HIT_STEP, _DIMMER_CEILING)
    if rung == LADDER_ZOOM_PINCH:
        return _stepped(values, _ZOOM, _PINCH_STEP, _BEAM_FLOOR)
    if rung == LADDER_IRIS_PINCH:
        return _stepped(values, _IRIS, _PINCH_STEP, _BEAM_FLOOR)
    raise SongCueBundleError(f"unknown ladder rung: {rung!r}")


def _stepped(
    values: Sequence[AttributeValue], attribute: str, step: int, limit: int
) -> tuple[AttributeValue, ...]:
    """한 속성만 한 칸 움직인 값들 — 그 속성이 없거나 한계에 닿아 있으면 그대로."""
    stepped: list[AttributeValue] = []
    for value in values:
        if value.name != attribute:
            stepped.append(value)
            continue
        target = value.value + step
        bounded = min(target, limit) if step > 0 else max(target, limit)
        stepped.append(AttributeValue(attribute, bounded))
    return tuple(stepped)


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


def _selected_groups(bound: Mapping[str, tuple[GroupCandidate, ...]]) -> tuple[GroupCandidate, ...]:
    selected = sorted(
        {group.number: group for groups in bound.values() for group in groups}.items()
    )
    return tuple(group for _number, group in selected)


def _selection_line(groups: Sequence[GroupCandidate]) -> str:
    return "Group " + " + ".join(str(group.number) for group in groups)


def _first_store_index(commands: Sequence[str], sequence_number: int, cue_number: int) -> int:
    prefix = f"Store Sequence {sequence_number} Cue {cue_number} "
    for index, command in enumerate(commands):
        if command.startswith(prefix):
            return index
    raise SongCueBundleError(SEQUENCE_UNAVAILABLE)


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


def _cue_names(sections: Sequence[SongCueSection]) -> tuple[str, ...]:
    """중복 라벨을 회차로 가른 큐 이름.

    순번은 여기서 다시 세지 않고 :attr:`SongCueSection.instance` 를 읽는다 —
    카운터는 :func:`_numbered_by_label` 하나다. 파서를 거치지 않은 구간은 라벨이 비어 있어
    이름으로 센다(그쪽은 선언으로 1회차다).
    """
    totals: dict[str, int] = dict()
    for section in sections:
        key = section.label or section.name
        totals[key] = totals.get(key, 0) + 1
    names: list[str] = []
    for section in sections:
        fallback = f"Section {section.index + 1}"
        base = _ascii_label(section.name, fallback=fallback)
        if totals[section.label or section.name] > 1:
            base = f"{base} {section.instance}"
        names.append(base)
    return tuple(names)


def _ascii_label(value: str, *, fallback: str) -> str:
    normalised = unicodedata.normalize("NFKD", value)
    ascii_text = normalised.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^0-9A-Za-z _.-]+", " ", ascii_text.replace("'", " "))
    label = " ".join(cleaned.split())
    return label or fallback


def _explicit_dynamics_for(
    section: SongCueSection, explicit_dynamics: Mapping[int, int] | None
) -> int | None:
    if explicit_dynamics is None:
        return None
    return explicit_dynamics.get(section.index)


def _validated_dynamics(value: int, index: int) -> int:
    if isinstance(value, bool) or value < DYNAMICS_MIN or value > DYNAMICS_MAX:
        raise ValueError(
            f"section index {index} explicit dynamics must be "
            f"between {DYNAMICS_MIN} and {DYNAMICS_MAX}: {value!r}"
        )
    return value


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


def _prepare_songcue_timecode_number(request: Mapping[str, object]) -> int:
    timecode_number = request.get("timecode_number")
    if (
        isinstance(timecode_number, bool)
        or not isinstance(timecode_number, int)
        or timecode_number < 1
    ):
        raise ValueError("'timecode_number' must be a positive integer")
    return timecode_number


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
